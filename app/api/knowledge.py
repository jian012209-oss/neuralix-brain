
import os
import hmac
import psycopg

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.engines.embedding_engine import create_embedding

router = APIRouter(
    prefix="/v1/knowledge",
    tags=["Knowledge"]
)


# -------------------------
# SECURITY
# -------------------------

def authorize(api_key):
    expected = os.getenv("BRAIN_API_KEY", "")

    if not expected or not api_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    if not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )


# -------------------------
# DATABASE CONNECTION
# -------------------------

def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise HTTPException(
            status_code=500,
            detail="Database not configured"
        )

    return psycopg.connect(database_url)


# -------------------------
# INPUT MODEL
# -------------------------

class KnowledgeInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=20000)


# -------------------------
# SAVE DOCUMENT + EMBEDDING
# -------------------------

@router.post("")
def save_document(
    data: KnowledgeInput,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    embedding = create_embedding(
        data.title + "\n" + data.content
    )

    embedding_text = "[" + ",".join(
        str(float(value)) for value in embedding
    ) + "]"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_documents
                (user_id, title, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                RETURNING id
                """,
                (
                    data.user_id,
                    data.title,
                    data.content,
                    embedding_text
                )
            )

            document_id = cur.fetchone()[0]

    return {
        "saved": True,
        "id": document_id,
        "embedding_created": True,
        "embedding_dimensions": len(embedding)
    }


# -------------------------
# GET DOCUMENTS
# -------------------------

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
                SELECT id, title, content, created_at
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
                "created_at": row[3].isoformat()
            }
            for row in rows
        ]
    }


# -------------------------
# KEYWORD SEARCH
# -------------------------

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
                SELECT id, title, content, created_at
                FROM knowledge_documents
                WHERE user_id = %s
                AND (
                    title ILIKE %s
                    OR content ILIKE %s
                )
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (
                    user_id,
                    f"%{q}%",
                    f"%{q}%"
                )
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
                "created_at": row[3].isoformat()
            }
            for row in rows
        ]
    }


# -------------------------
# SEMANTIC SEARCH
# -------------------------

@router.get("/semantic-search/{user_id}")
def semantic_search(
    user_id: str,
    q: str = Query(min_length=1, max_length=200),
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    # Convert the question into an embedding
    query_embedding = create_embedding(q)

    embedding_text = "[" + ",".join(
        str(float(value)) for value in query_embedding
    ) + "]"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    title,
                    content,
                    created_at,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_documents
                WHERE user_id = %s
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 10
                """,
                (
                    embedding_text,
                    user_id,
                    embedding_text
                )
            )

            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "query": q,
        "search_type": "semantic",
        "results": [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": row[3].isoformat(),
                "similarity": round(float(row[4]), 4)
            }
            for row in rows
        ]
    }
