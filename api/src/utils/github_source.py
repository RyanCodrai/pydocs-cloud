"""GitHub source code utilities — tarball-based file access."""

import asyncio
import io
import stat
import tarfile
from pathlib import PurePosixPath

from dulwich.client import get_transport_and_path_from_url
from dulwich.object_store import iter_tree_contents
from dulwich.repo import MemoryRepo

from src.utils.google_bucket import gcs_cache

TEN_YEARS = 10 * 365 * 24 * 60 * 60

BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".tiff", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz",
    ".exe", ".dll", ".so", ".dylib", ".a", ".o",
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg",
    ".db", ".sqlite", ".sqlite3",
    ".bin", ".dat", ".pkl", ".npy", ".npz",
    ".mo",
})


def _fetch_tarball_sync(owner: str, repo: str, commit_sha: str) -> bytes:
    """Fetch repo contents via Git pack protocol and build a tarball."""
    mem_repo = MemoryRepo()
    client, path = get_transport_and_path_from_url(
        f"https://github.com/{owner}/{repo}.git"
    )

    commit_id = commit_sha.encode("ascii")

    def determine_wants(refs, depth=None):
        return [commit_id]

    client.fetch(path, mem_repo, determine_wants=determine_wants, depth=1)

    commit_obj = mem_repo.object_store[commit_id]
    prefix = f"{owner}-{repo}-{commit_sha[:7]}"

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for entry in iter_tree_contents(mem_repo.object_store, commit_obj.tree):
            if not stat.S_ISREG(entry.mode):
                continue
            file_path = entry.path.decode("utf-8", errors="replace")
            suffix = PurePosixPath(file_path).suffix.lower()
            if suffix in BINARY_EXTENSIONS:
                continue

            blob = mem_repo.object_store[entry.sha]
            data = blob.data

            info = tarfile.TarInfo(name=f"{prefix}/{file_path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

    return buf.getvalue()


@gcs_cache(bucket_name="pydocs-datalake", path="cache/github-tarballs", ttl=TEN_YEARS, version=2)
async def get_tarball(owner: str, repo: str, commit_sha: str, github_token: str) -> bytes:
    """Fetch a GitHub repo's files at a specific commit via Git pack protocol."""
    return await asyncio.to_thread(_fetch_tarball_sync, owner, repo, commit_sha)


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
