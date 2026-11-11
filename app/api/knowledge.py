import os
import hmac
import json
import psycopg

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.engines.embedding_engine import create_embedding

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])


def authorize(api_key):
    expected = os.getenv("BRAIN_API_KEY", "")
    if not expected or not api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return psycopg.connect(database_url)


class KnowledgeInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=20000)
    category: str = Field(default="general", max_length=100)
    source: str | None = Field(default=None, max_length=500)
    metadata: dict = Field(default_factory=dict)


def to_vector_text(embedding):
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def split_into_chunks(text, chunk_size=1200, overlap=150):
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


@router.post("")
def save_document(
    data: KnowledgeInput,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    document_embedding = create_embedding(data.title + "\n" + data.content)
    document_vector = to_vector_text(document_embedding)
    chunks = split_into_chunks(data.content)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_documents
                    (user_id, title, content, embedding,
                     category, source, metadata, updated_at)
                VALUES
                    (%s, %s, %s, %s::vector,
                     %s, %s, %s::jsonb, NOW())
                RETURNING id
                """,
                (
                    data.user_id,
                    data.title,
                    data.content,
                    document_vector,
                    data.category,
                    data.source,
                    json.dumps(data.metadata)
                )
            )

            document_id = cur.fetchone()[0]

            for index, chunk in enumerate(chunks):
                chunk_embedding = create_embedding(
                    data.title + "\n" + chunk
                )

                cur.execute(
                    """
                    INSERT INTO knowledge_chunks
                        (document_id, user_id, chunk_index,
                         content, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    """,
                    (
                        document_id,
                        data.user_id,
                        index,
                        chunk,
                        to_vector_text(chunk_embedding)
                    )
                )

    return {
        "saved": True,
        "id": document_id,
        "category": data.category,
        "chunks_created": len(chunks),
        "embedding_dimensions": len(document_embedding)
    }


@router.get("/{user_id}")
def get_documents(
    user_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content, category, source, created_at
                FROM knowledge_documents
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id,)
            )
            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "documents": [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "category": row[3],
                "source": row[4],
                "created_at": row[5].isoformat()
            }
            for row in rows
        ]
    }


@router.get("/search/{user_id}")
def search_documents(
    user_id: str,
    q: str = Query(min_length=1, max_length=200),
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content, category, created_at
                FROM knowledge_documents
                WHERE user_id = %s
                  AND (title ILIKE %s OR content ILIKE %s)
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user_id, f"%{q}%", f"%{q}%")
            )
            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "query": q,
        "results": [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "category": row[3],
                "created_at": row[4].isoformat()
            }
            for row in rows
        ]
    }


@router.get("/semantic-search/{user_id}")
def semantic_search(
    user_id: str,
    q: str = Query(min_length=1, max_length=200),
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    query_vector = to_vector_text(create_embedding(q))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.document_id,
                    d.title,
                    c.content,
                    d.category,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE c.user_id = %s
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT 10
                """,
                (query_vector, user_id, query_vector)
            )
            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "query": q,
        "search_type": "semantic_chunks",
        "results": [
            {
                "document_id": row[0],
                "title": row[1],
                "content": row[2],
                "category": row[3],
                "similarity": round(float(row[4]), 4)
            }
            for row in rows
        ]
    }
