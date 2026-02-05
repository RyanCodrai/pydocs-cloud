import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.routes.v1.packages.service import PackageService, get_package_service
from src.utils.embeddings import embed_text
from src.utils.github_extraction import extract_github_candidates
from src.utils.github_readme import get_readmes_for_repos
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()


class LookupResponse(BaseModel):
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


@service_tag(ServiceType.RELEASES)
@router.get("/lookup/{package_name}", response_model=LookupResponse)
async def lookup_github_urls(
    package_name: str,
    package_service: PackageService = Depends(get_package_service),
) -> LookupResponse:
    """Look up GitHub repository URLs for a package, ranked by similarity."""
    package = await package_service.retrieve_by_ecosystem_and_name(ecosystem="pypi", package_name=package_name)
    scored_repos = await find_github_repos(
        description=package.description, project_urls=package.project_urls, home_page=package.home_page
    )
    if not scored_repos:
        raise HTTPException(status_code=404, detail="No GitHub repository found")
    best_url, _ = scored_repos[0]
    return LookupResponse(github_url=best_url)
