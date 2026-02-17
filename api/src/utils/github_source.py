"""GitHub source code utilities — tarball-based file access."""

import io
import tarfile

import aiohttp
from src.utils.google_bucket import gcs_cache

TEN_YEARS = 10 * 365 * 24 * 60 * 60


@gcs_cache(bucket_name="pydocs-datalake", path="cache/github-tarballs", ttl=TEN_YEARS)
async def get_tarball(owner: str, repo: str, commit_sha: str, github_token: str) -> bytes:
    """Download a GitHub repo tarball at a specific commit SHA."""
    url = f"https://api.github.com/repos/{owner}/{repo}/tarball/{commit_sha}"
    headers = {"Authorization": f"Bearer {github_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, allow_redirects=True) as response:
            response.raise_for_status()
            return await response.read()


def _open_tarball(tarball_bytes: bytes) -> tarfile.TarFile:
    return tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz")


def get_file_tree(tarball_bytes: bytes) -> list[str]:
    """Extract flat list of file paths from a tarball (blobs only, no directories)."""
    paths = []
    with _open_tarball(tarball_bytes) as tar:
        for member in tar.getmembers():
            if member.isfile():
                # Strip the top-level directory (e.g., "owner-repo-sha/")
                parts = member.name.split("/", 1)
                if len(parts) == 2:
                    paths.append(parts[1])
    paths.sort()
    return paths


def get_file_content(tarball_bytes: bytes, file_path: str) -> str:
    """Extract a single file's content from a tarball."""
    with _open_tarball(tarball_bytes) as tar:
        while (member := tar.next()) is not None:
            if not member.isfile():
                continue
            parts = member.name.split("/", 1)
            if len(parts) == 2 and parts[1] == file_path:
                f = tar.extractfile(member)
                if f is None:
                    raise FileNotFoundError(f"Could not read file: {file_path}")
                return f.read().decode("utf-8", errors="replace")
    raise FileNotFoundError(f"File not found: {file_path}")
