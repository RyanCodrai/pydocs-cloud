"""Services module for release logic and orchestration.

This module contains service classes that act as intermediaries between API endpoints and the
repository layer. Service classes implement additional business logic, perform validations,
and handle errors from the repository layer. The service layer ensures that clean data
structures are returned to the API layer while abstracting away database operations.
"""

from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBRelease
from src.db.operations import get_db_session
from src.routes.v1.releases.repository import ReleaseRepository
from src.routes.v1.releases.schema import ReleaseInput


class ReleaseAlreadyExists(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=409, detail="Release already exists")


class ReleaseNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=404, detail="Release not found")


async def get_release_service(db_session: AsyncSession = Depends(get_db_session)) -> "ReleaseService":
    return ReleaseService(db_session=db_session)


class ReleaseService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = ReleaseRepository(db_session=db_session)

    async def create(self, data: ReleaseInput, commit: bool = True) -> DBRelease:
        try:
            return await self.repository.create(data=data, commit=commit)
        except IntegrityError as exc:
            raise ReleaseAlreadyExists from exc

    async def retrieve(self, release_id: UUID) -> DBRelease:
        try:
            return await self.repository.retrieve(release_id=release_id)
        except NoResultFound as exc:
            raise ReleaseNotFound from exc

    async def retrieve_by_package(self, ecosystem: str, package_name: str, limit: int | None = None) -> list[DBRelease]:
        return await self.repository.retrieve_by_package(ecosystem=ecosystem, package_name=package_name, limit=limit)

    async def upsert(self, data: ReleaseInput, commit: bool = True) -> DBRelease:
        return await self.repository.upsert(data=data, commit=commit)
