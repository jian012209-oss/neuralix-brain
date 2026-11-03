import os
from huggingface_hub import InferenceClient
from fastapi import HTTPException

MODEL_NAME = "BAAI/bge-small-en-v1.5"

def create_embedding(text: str):
    token = os.getenv("HF_TOKEN")

    if not token:
        raise HTTPException(
            status_code=500,
            detail="HF_TOKEN is not configured"
        )

    try:
        client = InferenceClient(
            model=MODEL_NAME,
            token=token
        )

        result = client.feature_extraction(text)

        embedding = result.tolist() if hasattr(result, "tolist") else result

        # Convert a single embedding into a flat list.
        if embedding and isinstance(embedding[0], list):
            embedding = embedding[0]

        if len(embedding) != 384:
            raise ValueError("Unexpected embedding dimensions")

        return embedding

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding service error: {str(error)}"
        )
