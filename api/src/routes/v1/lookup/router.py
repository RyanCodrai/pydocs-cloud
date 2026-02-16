import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from src.db.models import DBUser
from src.routes.v1.lookup.schema import LookupParams, PackageLookupResponse
from src.routes.v1.packages.schema import PackageUpdate
from src.routes.v1.packages.service import PackageService, get_package_service
from src.routes.v1.releases.service import ReleaseService, get_release_service
from src.utils.auth import authenticate_user
from src.utils.embeddings import embed_text
from src.utils.github_commits import get_commit_at_timestamp
from src.utils.github_extraction import extract_github_candidates
from src.utils.github_readme import get_readmes_for_repos

router = APIRouter()

SUPPORTED_ECOSYSTEMS = {"pypi", "npm"}


class EcosystemNotFoundError(HTTPException):
    def __init__(self, ecosystem: str):
        super().__init__(status_code=404, detail=f"Ecosystem '{ecosystem}' is not supported")


class SourceCodeNotFoundError(HTTPException):
    def __init__(self, package_name: str):
        super().__init__(status_code=404, detail=f"No source code repository found for '{package_name}'")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


async def find_github_repos(
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
        score = cosine_similarity(description_embedding, readme_embedding)
        scored_repos.append((url, score))

    scored_repos.sort(key=lambda x: x[1], reverse=True)
    return scored_repos


async def resolve_source_code(params: LookupParams, package_service: PackageService, github_token: str) -> str:
    """Resolve the GitHub source code URL for a package, discovering it if needed."""
    package = await package_service.retrieve_by_ecosystem_and_name(
        ecosystem=params.ecosystem, package_name=params.package_name
    )

    if package.source_code:
        return package.source_code

    scored_repos = await find_github_repos(
        description=package.description,
        project_urls=package.project_urls,
        home_page=package.home_page,
        github_token=github_token,
    )
    if not scored_repos:
        raise SourceCodeNotFoundError(params.package_name)

    source_code = scored_repos[0][0]
    await package_service.update(package, PackageUpdate(source_code=source_code))
    return source_code


def get_lookup_params(ecosystem: str, package_name: str, version: str | None = None) -> LookupParams:
    if ecosystem not in SUPPORTED_ECOSYSTEMS:
        raise EcosystemNotFoundError(ecosystem)
    return LookupParams(ecosystem=ecosystem, package_name=package_name, version=version)


@router.get("/lookup/{ecosystem}/{package_name:path}", response_model=PackageLookupResponse)
async def lookup_package(
    params: LookupParams = Depends(get_lookup_params),
    package_service: PackageService = Depends(get_package_service),
    release_service: ReleaseService = Depends(get_release_service),
    user: DBUser = Depends(authenticate_user),
) -> PackageLookupResponse:
    """Look up the best matching GitHub repository for a package."""
    github_url = await resolve_source_code(params, package_service, user.github_token)

    releases = await release_service.retrieve_by_package(
        ecosystem=params.ecosystem, package_name=params.package_name, version=params.version, limit=1
    )
    if not releases:
        raise HTTPException(status_code=404, detail="No releases found for this package")

    commit_sha = await get_commit_at_timestamp(
        github_url=github_url, timestamp=releases[0].last_seen, github_token=user.github_token
    )

    return PackageLookupResponse(github_url=github_url, commit_sha=commit_sha)
