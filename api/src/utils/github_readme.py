"""GitHub README fetching utilities."""

import asyncio
from urllib.parse import urlparse

import aiohttp
from src.utils.google_bucket import gcs_cache

ONE_WEEK = 7 * 24 * 60 * 60


@gcs_cache(bucket_name="pydocs-datalake", path="cache/github-readmes", ttl=ONE_WEEK)
async def get_github_readme(repo_url: str, github_token: str) -> str | None:
    """Get the README content from a GitHub repository."""
    parsed = urlparse(repo_url)
    segments = parsed.path.strip("/").split("/")

    if len(segments) < 2:
        return None

    owner, repo = segments[0], segments[1]
    readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw", "Authorization": f"Bearer {github_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(readme_api_url, headers=headers) as response:
            if response.status == 404:
                return None  # No README
            response.raise_for_status()
            return await response.text()


async def get_readmes_for_repos(repo_urls: list[str], github_token: str) -> list[tuple[str, str]]:
    """Fetch READMEs for multiple repos concurrently."""
    readme_contents = await asyncio.gather(*[get_github_readme(url, github_token) for url in repo_urls])
    return [(url, content) for url, content in zip(repo_urls, readme_contents) if content]
