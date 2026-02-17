import fnmatch
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import numpy as np
from fastapi import HTTPException
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from src.db.operations import managed_session
from src.routes.v1.apikeys.service import APIKeyService
from src.routes.v1.commit_cache.service import CommitCacheService
from src.routes.v1.packages.schema import PackageUpdate
from src.routes.v1.packages.service import PackageService
from src.routes.v1.releases.service import ReleaseService
from src.routes.v1.users.service import UserService
from src.routes.v1.webhooks.schema import normalize_package_name
from src.settings import settings
from src.utils.app_lifespan import database
from src.utils.embeddings import embed_text
from src.utils.github_extraction import extract_github_candidates
from src.utils.github_readme import get_readmes_for_repos
from src.utils.github_source import get_file_content, get_file_tree, get_tarball
from src.utils.logger import logger
from starlette.requests import Request
from starlette.responses import PlainTextResponse


class SourcedTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with managed_session() as session:
                api_key_service = APIKeyService(db_session=session)
                api_key = await api_key_service.retrieve_by_hash(api_key=token)
                return AccessToken(token=token, client_id=str(api_key.user_id), scopes=[])
        except HTTPException:
            return None


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    async with database():
        yield


auth_settings = AuthSettings(issuer_url="https://api.sourced.dev", resource_server_url="https://mcp.sourced.dev")
allowed_hosts = ["localhost:*", "127.0.0.1:*"] if settings.ENVIRONMENT == "LOCAL" else ["mcp.sourced.dev"]
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts, allowed_origins=[]
)
mcp = FastMCP(
    "sourced",
    stateless_http=True,
    token_verifier=SourcedTokenVerifier(),
    auth=auth_settings,
    lifespan=lifespan,
    transport_security=transport_security,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


async def _find_github_repos(
    description: str | None,
    project_urls: dict[str, str],
    home_page: str | None,
    github_token: str,
) -> list[tuple[str, float]]:
    """Find and rank GitHub repositories from package metadata."""
    candidates = extract_github_candidates(description=description, project_urls=project_urls, home_page=home_page)
    if not candidates:
        return []

    repos_with_readmes = await get_readmes_for_repos(candidates, github_token)
    description_embedding = await embed_text(description)

    scored_repos = []
    for url, readme in repos_with_readmes:
        readme_embedding = await embed_text(readme)
        score = _cosine_similarity(description_embedding, readme_embedding)
        scored_repos.append((url, score))

    scored_repos.sort(key=lambda x: x[1], reverse=True)
    return scored_repos


async def _resolve_source_code(
    ecosystem: str, package_name: str, package_service: PackageService, github_token: str
) -> str:
    """Resolve the GitHub source code URL for a package, discovering it if needed."""
    package = await package_service.retrieve_by_ecosystem_and_name(ecosystem=ecosystem, package_name=package_name)

    if package.source_code:
        return package.source_code

    scored_repos = await _find_github_repos(
        description=package.description,
        project_urls=package.project_urls,
        home_page=package.home_page,
        github_token=github_token,
    )
    if not scored_repos:
        raise ValueError(f"No source code repository found for '{package_name}'")

    source_code = scored_repos[0][0]
    await package_service.update(package, PackageUpdate(source_code=source_code))
    return source_code


async def resolve_package(ecosystem: str, package_name: str, version: str | None = None) -> tuple[bytes, str]:
    """Resolve a package to a tarball and commit SHA.

    Returns (tarball_bytes, commit_sha).
    """
    if ecosystem not in {"pypi", "npm"}:
        raise ValueError(f"Ecosystem '{ecosystem}' is not supported")

    if ecosystem == "pypi":
        package_name = normalize_package_name(package_name)

    access_token = get_access_token()
    if not access_token:
        raise ValueError("Authentication required")

    user_id = access_token.client_id

    async with managed_session() as session:
        user = await UserService(db_session=session).retrieve(user_id=user_id)
        github_token = user.github_token

        package_service = PackageService(db_session=session)
        github_url = await _resolve_source_code(ecosystem, package_name, package_service, github_token)

        release_service = ReleaseService(db_session=session)
        releases = await release_service.retrieve_by_package(
            ecosystem=ecosystem, package_name=package_name, version=version, limit=1
        )
        if not releases:
            raise ValueError(f"No releases found for {ecosystem}/{package_name}")

        commit_cache_service = CommitCacheService(db_session=session)
        commit_sha = await commit_cache_service.get_commit_sha(
            github_url=github_url, timestamp=releases[0].last_seen, github_token=github_token
        )

    # Parse owner/repo from GitHub URL
    path = github_url.rstrip("/").split("github.com/")[-1]
    segments = path.split("/")
    owner, repo = segments[0], segments[1]

    tarball_bytes = await get_tarball(owner, repo, commit_sha, github_token)
    return tarball_bytes, commit_sha


@mcp.tool()
async def glob(
    ecosystem: str, package_name: str, pattern: str, path: str | None = None, version: str | None = None
) -> str:
    """Find files matching a glob pattern in a package's source code.

    Args:
        ecosystem: Package ecosystem (e.g. "pypi", "npm")
        package_name: Name of the package
        pattern: Glob pattern to match (e.g. "**/*.py", "src/*.ts")
        path: Optional directory to scope the search to
        version: Optional package version (defaults to latest)
    """
    try:
        tarball_bytes, _ = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    files = get_file_tree(tarball_bytes)

    if path:
        path = path.strip("/")
        files = [f for f in files if f.startswith(path + "/") or f == path]

    matches = [f for f in files if fnmatch.fnmatch(f, pattern)]
    if not matches:
        return "No files matched the pattern."
    return "\n".join(matches)


@mcp.tool()
async def grep(
    ecosystem: str,
    package_name: str,
    pattern: str,
    path: str | None = None,
    glob_pattern: str | None = None,
    version: str | None = None,
) -> str:
    """Search for a regex pattern in a package's source code.

    Args:
        ecosystem: Package ecosystem (e.g. "pypi", "npm")
        package_name: Name of the package
        pattern: Regex pattern to search for (e.g. "def get", "class.*Error")
        path: Optional directory to scope the search to
        glob_pattern: Optional glob to filter files (e.g. "*.py", "*.ts")
        version: Optional package version (defaults to latest)
    """
    try:
        tarball_bytes, _ = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    files = get_file_tree(tarball_bytes)

    if path:
        path = path.strip("/")
        files = [f for f in files if f.startswith(path + "/") or f == path]

    if glob_pattern:
        files = [f for f in files if fnmatch.fnmatch(f, glob_pattern)]

    # Cap file count to avoid excessive processing
    files = files[:50]

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    results = []
    for file_path in files:
        try:
            content = get_file_content(tarball_bytes, file_path)
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        for line_num, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                results.append(f"{file_path}:{line_num}:{line}")

    if not results:
        return "No matches found."
    return "\n".join(results)


@mcp.tool()
async def read(
    ecosystem: str,
    package_name: str,
    file_path: str,
    version: str | None = None,
    offset: int = 1,
    limit: int = 2000,
) -> str:
    """Read a file from a package's source code with line numbers.

    Args:
        ecosystem: Package ecosystem (e.g. "pypi", "npm")
        package_name: Name of the package
        file_path: Path to the file within the repository
        version: Optional package version (defaults to latest)
        offset: Line number to start reading from (1-indexed, default: 1)
        limit: Maximum number of lines to return (default: 2000)
    """
    try:
        tarball_bytes, _ = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    try:
        content = get_file_content(tarball_bytes, file_path)
    except FileNotFoundError as e:
        return f"Error: {e}"

    lines = content.splitlines()
    # Apply offset and limit (offset is 1-indexed)
    start = max(0, offset - 1)
    selected = lines[start : start + limit]

    # Format with line numbers (cat -n style)
    numbered = []
    for i, line in enumerate(selected, start=offset):
        numbered.append(f"     {i}\t{line}")
    return "\n".join(numbered)


def create_mcp_app():
    logger.info("MCP server application initialised")
    return mcp.streamable_http_app()
