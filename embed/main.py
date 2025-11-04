import logging
import os
from typing import List

from embeddings import QwenEmbed8
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()
model = QwenEmbed8(model_path="qwen-0.6b-int8")


class EmbeddingRequest(BaseModel):
    input: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]


@app.post("/embeddings", response_model=EmbeddingResponse)
async def get_embeddings(request: EmbeddingRequest):
    if not request.input:
        raise HTTPException(status_code=400, detail="input required")
    try:
        # model.embed returns a numpy array of shape (batch_size, embedding_dim)
        embeddings = model.embed(request.input)
        # Convert to list format: [[embedding1], [embedding2], ...]
        return {"embeddings": embeddings.tolist()}
    except Exception as e:
        logging.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}
