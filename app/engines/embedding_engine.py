from functools import lru_cache

from fastembed import TextEmbedding
from fastapi import HTTPException

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Load the local embedding model once
    and reuse it for future requests.
    """
    return TextEmbedding(
        model_name=MODEL_NAME
    )


def create_embedding(text: str):
    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    try:
        model = get_embedding_model()

        results = list(
            model.embed([text])
        )

        if not results:
            raise ValueError("No embedding was generated")

        embedding = results[0].tolist()

        if len(embedding) != 384:
            raise ValueError(
                f"Expected 384 dimensions, got {len(embedding)}"
            )

        return embedding

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Local embedding error: {str(error)}"
        )
