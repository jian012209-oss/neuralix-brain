
import os
import hmac
import psycopg
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/v1/conversations",
    tags=["Conversations"]
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


class ConversationMessage(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    conversation_id: str = Field(min_length=1, max_length=200)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)


@router.post("")
def save_message(
    data: ConversationMessage,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO brain_conversations
                (user_id, conversation_id, role, content)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (
                    data.user_id,
                    data.conversation_id,
                    data.role,
                    data.content
                )
            )

            row = cur.fetchone()

    return {
        "success": True,
        "message_id": row[0],
        "created_at": row[1].isoformat()
    }


@router.get("/{user_id}/{conversation_id}")
def get_conversation(
    user_id: str,
    conversation_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, role, content, created_at
                FROM brain_conversations
                WHERE user_id = %s
                  AND conversation_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 500
                """,
                (user_id, conversation_id)
            )

            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "created_at": row[3].isoformat()
            }
            for row in rows
        ]
    }


@router.get("/{user_id}")
def list_conversations(
    user_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    conversation_id,
                    MAX(created_at) AS last_message_at,
                    COUNT(*) AS message_count
                FROM brain_conversations
                WHERE user_id = %s
                GROUP BY conversation_id
                ORDER BY last_message_at DESC
                LIMIT 100
                """,
                (user_id,)
            )

            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "conversations": [
            {
                "conversation_id": row[0],
                "last_message_at": row[1].isoformat(),
                "message_count": row[2]
            }
            for row in rows
        ]
    }
