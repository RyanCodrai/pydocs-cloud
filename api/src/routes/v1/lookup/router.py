from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage
from src.db.operations import get_db_session
from src.routes.v1.webhooks.schema import normalize_package_name
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()

SUPPORTED_ECOSYSTEMS = {"pypi", "npm"}


class PackageNotFoundError(HTTPException):
    def __init__(self, package_name: str, ecosystem: str):
        super().__init__(status_code=404, detail=f"Package '{package_name}' not found in {ecosystem}")


class SourceCodeNotFoundError(HTTPException):
    def __init__(self, package_name: str):
        super().__init__(status_code=404, detail=f"No source code repository found for '{package_name}'")


class PackageLookupResponse(BaseModel):
    package_name: str
    description: str | None = None
    home_page: str | None = None
    project_urls: dict[str, str] = {}
    first_seen: datetime
    last_seen: datetime


@service_tag(ServiceType.RELEASES)
@router.get("/lookup/{ecosystem}/{package_name:path}", response_model=PackageLookupResponse)
async def lookup_package(
    ecosystem: str,
    package_name: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> PackageLookupResponse:
    """Look up package metadata by ecosystem and name."""
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

    if not package.project_urls:
        raise SourceCodeNotFoundError(package_name)

    return PackageLookupResponse(
        package_name=package.package_name,
        description=package.description,
        home_page=package.home_page,
        project_urls=package.project_urls,
        first_seen=package.first_seen,
        last_seen=package.last_seen,
    )
