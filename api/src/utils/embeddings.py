"""Embedding utilities using Gemini."""

import aiohttp
from src.settings import settings
from src.utils.google_bucket import gcs_cache

TEN_YEARS = 10 * 365 * 24 * 60 * 60


@gcs_cache(bucket_name="pydocs-cache", path="embeddings", ttl=TEN_YEARS)
async def embed_text(text: str, task_type: str = "SEMANTIC_SIMILARITY") -> list[float]:
    headers = {
        "x-goog-api-key": settings.GOOGLE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": 3072,
    }
    async with aiohttp.ClientSession() as session:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            return data["embedding"]["values"]
