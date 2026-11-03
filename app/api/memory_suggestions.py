
import os
import hmac
import json

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

router = APIRouter(
    prefix="/v1/memory",
    tags=["Memory Suggestions"]
)


def authorize(api_key):
    expected = os.getenv("BRAIN_API_KEY", "")

    if not expected or not api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class SuggestionInput(BaseModel):
    conversation: str = Field(min_length=20, max_length=12000)


@router.post("/suggest")
def suggest_memories(
    data: SuggestionInput,
    x_brain_api_key: str = Header(default=None)
):
    authorize(x_brain_api_key)

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key is not configured"
        )

    prompt = """
Analyze this conversation and suggest only useful,
long-term memories that could improve future assistance.

Possible categories:
- preference
- project
- learning
- general

Rules:
1. Return only facts clearly supported by the conversation.
2. Do not include temporary information.
3. Do not include passwords, API keys, tokens, or secrets.
4. Do not suggest sensitive personal information.
5. Do not invent facts.
6. Return at most 5 suggestions.
7. If nothing is worth remembering, return an empty list.

Return valid JSON in this exact format:
{
  "suggestions": [
    {
      "memory": "The suggested memory",
      "category": "preference"
    }
  ]
}

CONVERSATION:
""" + data.conversation

    try:
        client = genai.Client(api_key=api_key)

        model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.1-flash-lite"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1000
            )
        )

        result = json.loads(response.text or "{}")
        suggestions = result.get("suggestions", [])

        if not isinstance(suggestions, list):
            raise ValueError("Invalid suggestions format")

        allowed_categories = {
            "preference",
            "project",
            "learning",
            "general"
        }

        clean_suggestions = []

        for item in suggestions[:5]:
            if not isinstance(item, dict):
                continue

            memory = item.get("memory")
            category = item.get("category", "general")

            if not isinstance(memory, str) or not memory.strip():
                continue

            if category not in allowed_categories:
                category = "general"

            clean_suggestions.append({
                "memory": memory.strip()[:1000],
                "category": category
            })

        return {
            "success": True,
            "saved": False,
            "suggestions": clean_suggestions,
            "message": "Review and approve suggestions before saving."
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Memory suggestion generation failed. Check Gemini availability and Render logs."
        )
