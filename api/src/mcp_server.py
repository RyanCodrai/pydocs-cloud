import glob as glob_module
import io
import re
import tarfile
import uuid
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
from src.routes.v1.feedback.schema import FeedbackType
from src.routes.v1.feedback.service import FeedbackService
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
from src.utils.registry_source import get_npm_tarball, get_pypi_tarball
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
    "sourced.dev",
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
) -> str | None:
    """Resolve the GitHub source code URL for a package, discovering it if needed.

    Returns the GitHub URL if found, or None if no repository exists.
    """
    package = await package_service.retrieve_by_ecosystem_and_name(ecosystem=ecosystem, package_name=package_name)

    if package.status == "processed":
        return package.source_code  # URL or None — we already checked

    # status == "unprocessed": run the GitHub candidate extraction pipeline
    scored_repos = await _find_github_repos(
        description=package.description,
        project_urls=package.project_urls,
        home_page=package.home_page,
        github_token=github_token,
    )

    if scored_repos:
        source_code = scored_repos[0][0]
        await package_service.update(package, PackageUpdate(source_code=source_code, status="processed"))
        return source_code

    # No repo found — mark as processed so we don't retry
    await package_service.update(package, PackageUpdate(status="processed"))
    return None


async def resolve_package(ecosystem: str, package_name: str, version: str | None = None) -> tuple[bytes, str, str]:
    """Resolve a package to a tarball and version/commit identifier.

    Returns (tarball_bytes, identifier, source_label).
    """
    if ecosystem not in {"pypi", "npm"}:
        raise ValueError(f"Ecosystem '{ecosystem}' is not supported")

    if ecosystem == "pypi":
        package_name = normalize_package_name(package_name)

    access_token = get_access_token()
    if not access_token:
        raise ValueError("Authentication required")

    user_id = uuid.UUID(access_token.client_id)

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

        release = releases[0]

        if github_url:
            # GitHub path: resolve commit and download from GitHub
            commit_cache_service = CommitCacheService(db_session=session)
            commit_sha = await commit_cache_service.get_commit_sha(
                github_url=github_url, timestamp=release.last_seen, github_token=github_token
            )

            path = github_url.rstrip("/").split("github.com/")[-1]
            segments = path.split("/")
            owner, repo = segments[0], segments[1]

            tarball_bytes = await get_tarball(owner, repo, commit_sha, github_token)
            source_label = f"Source: GitHub repository archive ({owner}/{repo}@{commit_sha[:8]})"
            return tarball_bytes, commit_sha, source_label

    # Fallback: download sdist/tarball directly from the registry
    release_version = version or release.version
    if ecosystem == "pypi":
        tarball_bytes = await get_pypi_tarball(package_name, release_version)
        source_label = f"Source: PyPI sdist ({package_name}=={release_version})"
    else:
        tarball_bytes = await get_npm_tarball(package_name, release_version)
        source_label = f"Source: npm registry tarball ({package_name}@{release_version})"
    return tarball_bytes, release_version, source_label


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
        tarball_bytes, _, source_label = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    files = get_file_tree(tarball_bytes)

    if path:
        path = path.strip("/")
        files = [f for f in files if f.startswith(path + "/") or f == path]

    regex = re.compile(glob_module.translate(pattern, recursive=True, include_hidden=True))
    matches = [f for f in files if regex.match(f)]
    if not matches:
        return "No files matched the pattern."

    total = len(matches)
    MAX_RESULTS = 100
    output = "\n".join(matches[:MAX_RESULTS])
    if total > MAX_RESULTS:
        output += f"\n\n... and {total - MAX_RESULTS} more files ({total} total). Use the `path` parameter to narrow your search."
    output += f"\n\n{source_label}"
    return output


def _compile_re2(pattern: str, case_insensitive: bool = False, multiline: bool = False):
    """Compile a regex with google-re2, falling back to stdlib re if unsupported."""
    try:
        import re2

        opts = re2.Options()
        if case_insensitive:
            opts.case_sensitive = False
        if multiline:
            opts.dot_nl = True

        # Prepend (?m) so ^ and $ match line boundaries when searching whole files
        effective_pattern = f"(?m){pattern}" if not multiline else pattern
        return re2.compile(effective_pattern, options=opts), True
    except (ImportError, re2.error):
        # Fall back to stdlib re (e.g. for backreferences, lookaround)
        flags = 0
        if case_insensitive:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.DOTALL | re.MULTILINE
        return re.compile(pattern, flags), False


def _is_binary(data: bytes, sample_size: int = 8192) -> bool:
    """Check if data looks like a binary file."""
    return b"\x00" in data[:sample_size]


def _byte_offset_to_line_num(data: bytes, offset: int) -> int:
    """Convert a byte offset to a 1-indexed line number."""
    return data[:offset].count(b"\n") + 1


def _extract_line_at_offset(data: bytes, offset: int) -> str:
    """Extract and decode the line containing the given byte offset."""
    line_start = data.rfind(b"\n", 0, offset) + 1
    line_end = data.find(b"\n", offset)
    if line_end == -1:
        line_end = len(data)
    return data[line_start:line_end].decode("utf-8", errors="replace")


@mcp.tool()
async def grep(
    ecosystem: str,
    package_name: str,
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    version: str | None = None,
    output_mode: str = "files_with_matches",
    head_limit: int = 0,
    offset: int = 0,
    case_insensitive: bool = False,
    multiline: bool = False,
) -> str:
    """Search for a regex pattern in a package's source code.

    Args:
        ecosystem: Package ecosystem (e.g. "pypi", "npm")
        package_name: Name of the package
        pattern: Regex pattern to search for (e.g. "def get", "class.*Error")
        path: Optional directory to scope the search to
        glob: Optional glob to filter files (e.g. "*.py", "*.ts")
        version: Optional package version (defaults to latest)
        output_mode: Output mode: "files_with_matches" (default, file paths only), "content" (file:line_num:line), "count" (file:count)
        head_limit: Limit output to first N entries after offset (0 = unlimited)
        offset: Skip first N entries before applying head_limit
        case_insensitive: Case insensitive search (default: false)
        multiline: Enable multiline mode where . matches newlines and patterns can span lines (default: false)
    """
    if output_mode not in ("files_with_matches", "content", "count"):
        return "Error: output_mode must be one of: files_with_matches, content, count"

    try:
        tarball_bytes, _, source_label = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    try:
        regex, using_re2 = _compile_re2(pattern, case_insensitive, multiline)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    if path:
        path = path.strip("/")

    glob_regex = None
    if glob:
        glob_regex = re.compile(glob_module.translate(glob, recursive=True, include_hidden=True))

    entries: list[str] = []
    entry_count = 0
    # Target number of entries we need after applying offset
    target = (offset + head_limit) if head_limit > 0 else 0

    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:") as tar:
        while (member := tar.next()) is not None:
            if not member.isfile():
                continue
            parts = member.name.split("/", 1)
            if len(parts) != 2:
                continue
            file_path = parts[1]

            if path and not (file_path.startswith(path + "/") or file_path == path):
                continue
            if glob_regex and not glob_regex.match(file_path):
                continue

            try:
                f = tar.extractfile(member)
                if f is None:
                    continue
                raw = f.read()
            except OSError:
                continue

            # Skip binary files
            if _is_binary(raw):
                continue

            # Search raw bytes — no decode needed for match detection
            if output_mode == "files_with_matches":
                if regex.search(raw if using_re2 else raw.decode("utf-8", errors="replace")):
                    entry_count += 1
                    if entry_count > offset:
                        entries.append(file_path)
                    if target and entry_count >= target:
                        break

            elif output_mode == "count":
                text = raw if using_re2 else raw.decode("utf-8", errors="replace")
                matches = regex.findall(text)
                if matches:
                    entry_count += 1
                    if entry_count > offset:
                        entries.append(f"{file_path}:{len(matches)}")
                    if target and entry_count >= target:
                        break

            elif output_mode == "content":
                text = raw if using_re2 else raw.decode("utf-8", errors="replace")
                for m in regex.finditer(text):
                    entry_count += 1
                    if entry_count > offset:
                        if using_re2:
                            line_num = _byte_offset_to_line_num(raw, m.start())
                            line = _extract_line_at_offset(raw, m.start())
                        else:
                            line_num = text[: m.start()].count("\n") + 1
                            line_start = text.rfind("\n", 0, m.start()) + 1
                            line_end = text.find("\n", m.start())
                            if line_end == -1:
                                line_end = len(text)
                            line = text[line_start:line_end]
                        entries.append(f"{file_path}:{line_num}:{line}")
                    if target and entry_count >= target:
                        break
                if target and entry_count >= target:
                    break

    if not entries:
        return "No matches found."

    # Join and truncate at 30,000 chars
    MAX_OUTPUT_CHARS = 30_000
    output = "\n".join(entries)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n\n... output truncated at 30,000 characters."
    output += f"\n\n{source_label}"
    return output


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
        tarball_bytes, _, source_label = await resolve_package(ecosystem, package_name, version)
    except (HTTPException, ValueError) as e:
        return f"Error: {e}"

    try:
        content = get_file_content(tarball_bytes, file_path)
    except FileNotFoundError as e:
        return f"Error: {e}"

    # Size guard: if using default offset/limit, check raw file size (256KB limit)
    MAX_FILE_SIZE = 256 * 1024
    content_bytes = len(content.encode("utf-8"))
    is_default = offset == 1 and limit == 2000
    if is_default and content_bytes > MAX_FILE_SIZE:
        if content_bytes >= 1024 * 1024:
            size_str = f"{content_bytes / (1024 * 1024):.1f}MB"
        else:
            size_str = f"{content_bytes / 1024:.0f}KB"
        return (
            f"File content ({size_str}) exceeds maximum allowed size (256KB). "
            "Please use offset and limit parameters to read specific portions of the file, "
            "or use the grep tool to search for specific content."
        )

    lines = content.splitlines()

    # Truncate each line at 2,000 characters
    lines = [line[:2000] for line in lines]

    # Apply offset and limit (offset is 1-indexed)
    start = max(0, offset - 1)
    selected = lines[start : start + limit]

    # Format with line numbers (cat -n style)
    total_lines = len(lines)
    num_lines = len(selected)
    numbered = []
    for i, line in enumerate(selected, start=offset):
        numbered.append(f"     {i}\t{line}")
    output = "\n".join(numbered)

    # Append metadata so the caller knows the file size and what slice was returned
    output += f"\n\n[Lines {offset}-{offset + num_lines - 1} of {total_lines} total]"

    # Token guard: estimate tokens (~4 chars per token) and reject if too large
    MAX_TOKENS = 25_000
    estimated_tokens = len(output) // 4
    if estimated_tokens > MAX_TOKENS:
        return (
            f"File content ({estimated_tokens} tokens) exceeds maximum allowed tokens ({MAX_TOKENS}). "
            "Please use offset and limit parameters to read specific portions of the file, "
            "or use the grep tool to search for specific content."
        )

    output += f"\n\n{source_label}"
    return output


@mcp.tool()
async def submit_feedback(feedback_type: FeedbackType, text: str) -> str:
    """Submit feedback about sourced.dev.

    Args:
        feedback_type: Type of feedback ("bug", "improvement", "question", "other")
        text: The feedback content
    """
    access_token = get_access_token()
    if not access_token:
        return "Error: Authentication required"

    user_id = uuid.UUID(access_token.client_id)

    async with managed_session() as session:
        feedback_service = FeedbackService(db_session=session)
        await feedback_service.create(user_id=user_id, feedback_type=feedback_type, text=text)

    return "Feedback submitted successfully. Thank you!"


def create_mcp_app():
    logger.info("MCP server application initialised")
    return mcp.streamable_http_app()
