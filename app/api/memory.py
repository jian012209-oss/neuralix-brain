
import os
import hmac
import psycopg

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/v1/memory",
    tags=["Memory"]
)


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


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise HTTPException(
            status_code=500,
            detail="Database not configured"
        )

    return psycopg.connect(database_url)


class MemoryInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    memory: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="general", max_length=100)


@router.post("")
def save_memory(
    data: MemoryInput,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO brain_memories
                (user_id, memory, category)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (data.user_id, data.memory, data.category)
            )

            memory_id = cur.fetchone()[0]

    return {
        "saved": True,
        "id": memory_id
    }


@router.get("/{user_id}")
def get_memories(
    user_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, memory, category, created_at
                FROM brain_memories
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,)
            )

            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "memories": [
            {
                "id": row[0],
                "memory": row[1],
                "category": row[2],
                "created_at": row[3].isoformat()
            }
            for row in rows
        ]
    }


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int,
    user_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM brain_memories
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (memory_id, user_id)
            )

            deleted = cur.fetchone()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    return {
        "deleted": True,
        "id": memory_id
    }
