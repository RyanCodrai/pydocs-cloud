import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage
from src.db.operations import get_db_session
from src.routes.v1.webhooks.schema import normalize_package_name
from src.utils.embeddings import embed_text
from src.utils.github_extraction import extract_github_candidates
from src.utils.github_readme import get_readmes_for_repos

router = APIRouter()

SUPPORTED_ECOSYSTEMS = {"pypi", "npm"}


class PackageNotFoundError(HTTPException):
    def __init__(self, package_name: str, ecosystem: str):
        super().__init__(status_code=404, detail=f"Package '{package_name}' not found in {ecosystem}")


class SourceCodeNotFoundError(HTTPException):
    def __init__(self, package_name: str):
        super().__init__(status_code=404, detail=f"No source code repository found for '{package_name}'")


class PackageLookupResponse(BaseModel):
    github_url: str


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


async def find_github_repos(
    description: str | None,
    project_urls: dict[str, str],
    home_page: str | None,
) -> list[tuple[str, float]]:
    """Find and rank GitHub repositories from package metadata."""
    candidates = extract_github_candidates(description=description, project_urls=project_urls, home_page=home_page)

    if not candidates:
        return []

    repos_with_readmes = await get_readmes_for_repos(candidates)
    description_embedding = await embed_text(description)

    scored_repos = []
    for url, readme in repos_with_readmes:
        readme_embedding = await embed_text(readme)
        score = cosine_similarity(description_embedding, readme_embedding)
        scored_repos.append((url, score))

    scored_repos.sort(key=lambda x: x[1], reverse=True)
    return scored_repos


@router.get("/lookup/{ecosystem}/{package_name:path}", response_model=PackageLookupResponse)
async def lookup_package(
    ecosystem: str,
    package_name: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> PackageLookupResponse:
    """Look up the best matching GitHub repository for a package."""
    if ecosystem not in SUPPORTED_ECOSYSTEMS:
        raise PackageNotFoundError(package_name, ecosystem)

    if ecosystem == "pypi":
        package_name = normalize_package_name(package_name)

    stmt = select(DBPackage).where(
        DBPackage.ecosystem == ecosystem,
        DBPackage.package_name == package_name,
    )

    result = await db_session.exec(stmt)
    package = result.scalar_one_or_none()
    if package is None:
        raise PackageNotFoundError(package_name, ecosystem)

    scored_repos = await find_github_repos(
        description=package.description,
        project_urls=package.project_urls,
        home_page=package.home_page,
    )

    if not scored_repos:
        raise SourceCodeNotFoundError(package_name)

    best_url, _ = scored_repos[0]
    return PackageLookupResponse(github_url=best_url)
