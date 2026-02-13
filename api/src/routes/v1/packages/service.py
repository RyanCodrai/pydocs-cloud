"""Services module for package logic and orchestration.

This module contains service classes that act as intermediaries between API endpoints and the
repository layer. Service classes implement additional business logic, perform validations,
and handle errors from the repository layer. The service layer ensures that clean data
structures are returned to the API layer while abstracting away database operations.
"""

from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage
from src.db.operations import get_db_session
from src.routes.v1.packages.repository import PackageRepository
from src.routes.v1.packages.schema import PackageInput


class PackageAlreadyExists(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=409, detail="Package already exists")


class PackageNotFound(HTTPException):
    def __init__(self, package_name: str, ecosystem: str) -> None:
        super().__init__(status_code=404, detail=f"Package '{package_name}' not found in {ecosystem}")


async def get_package_service(db_session: AsyncSession = Depends(get_db_session)) -> "PackageService":
    return PackageService(db_session=db_session)


class PackageService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = PackageRepository(db_session=db_session)

    async def create(self, data: PackageInput, commit: bool = True) -> DBPackage:
        try:
            return await self.repository.create(data=data, commit=commit)
        except IntegrityError as exc:
            raise PackageAlreadyExists from exc

    async def retrieve(self, package_id: UUID) -> DBPackage:
        try:
            return await self.repository.retrieve(package_id=package_id)
        except NoResultFound as exc:
            raise PackageNotFound from exc

    async def retrieve_by_ecosystem_and_name(self, ecosystem: str, package_name: str) -> DBPackage:
        try:
            return await self.repository.retrieve_by_ecosystem_and_name(ecosystem=ecosystem, package_name=package_name)
        except NoResultFound as exc:
            raise PackageNotFound(package_name=package_name, ecosystem=ecosystem) from exc

    async def retrieve_unprocessed(self, ecosystem: str, limit: int = 100) -> list[str]:
        return await self.repository.retrieve_unprocessed(ecosystem=ecosystem, limit=limit)

    async def register(self, ecosystem: str, package_name: str, commit: bool = True) -> None:
        await self.repository.register(ecosystem=ecosystem, package_name=package_name, commit=commit)

    async def delete_by_ecosystem_and_name(self, ecosystem: str, package_name: str, commit: bool = True) -> None:
        await self.repository.delete_by_ecosystem_and_name(ecosystem=ecosystem, package_name=package_name, commit=commit)

    async def upsert(self, data: PackageInput, commit: bool = True) -> DBPackage:
        return await self.repository.upsert(data=data, commit=commit)
