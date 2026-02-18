"""Embedding utilities using Vertex AI."""

import os

import aiohttp
import google.auth
import google.auth.transport.requests
from src.utils.google_bucket import gcs_cache

TEN_YEARS = 10 * 365 * 24 * 60 * 60


def _get_access_token() -> str:
    """Get access token from ADC."""
    credentials, _ = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


@gcs_cache(bucket_name="pydocs-datalake", path="cache/embeddings", ttl=TEN_YEARS)
async def embed_text(text: str) -> list[float]:
    """Generate embeddings using Vertex AI."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "pydocs-prod")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west2")

    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/text-embedding-005:predict"

    headers = {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }
    payload = {"instances": [{"content": text}]}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            return data["predictions"][0]["embeddings"]["values"]
