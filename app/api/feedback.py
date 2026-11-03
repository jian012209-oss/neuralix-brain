
import os
import hmac
import psycopg

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/v1/feedback",
    tags=["Feedback"]
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


class FeedbackInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    message_id: str | None = Field(default=None, max_length=200)
    rating: int = Field(ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=5000)


@router.post("")
def submit_feedback(
    data: FeedbackInput,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO brain_feedback
                (user_id, message_id, rating, feedback)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    data.user_id,
                    data.message_id,
                    data.rating,
                    data.feedback
                )
            )

            feedback_id = cur.fetchone()[0]

    return {
        "success": True,
        "feedback_id": feedback_id,
        "rating": data.rating
    }


@router.get("/{user_id}")
def get_feedback(
    user_id: str,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, message_id, rating, feedback, created_at
                FROM brain_feedback
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,)
            )

            rows = cur.fetchall()

    return {
        "user_id": user_id,
        "feedback": [
            {
                "id": row[0],
                "message_id": row[1],
                "rating": row[2],
                "feedback": row[3],
                "created_at": row[4].isoformat()
            }
            for row in rows
        ]
    }
