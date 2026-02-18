from datetime import datetime

import aiohttp
from fastapi import HTTPException


async def get_commit_at_timestamp(github_url: str, timestamp: datetime, github_token: str) -> str:
    """Get the most recent commit SHA at or before the given timestamp."""
    # Extract owner/repo from github_url
    path = github_url.rstrip("/").split("github.com/")[-1]
    segments = path.split("/")
    owner, repo = segments[0], segments[1]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"until": timestamp.isoformat(), "per_page": "1"}
    headers = {"Authorization": f"Bearer {github_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params, headers=headers) as response:
            response.raise_for_status()
            commits = await response.json()

    if not commits:
        raise HTTPException(status_code=404, detail="No commits found for the given timestamp")

    return commits[0]["sha"]
