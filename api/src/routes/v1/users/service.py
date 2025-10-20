"""Services module for additional logic and orchestration.

This module contains service classes that act as intermediaries between API endpoints and the
repository layer. Service classes implement additional business logic, perform validations,
and handle errors from the repository layer. The service layer ensures that clean data
structures are returned to the API layer while abstracting away database operations.
"""

import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.db.operations import get_db_session
from src.routes.v1.users.repository import UserRepository
from src.routes.v1.users.schema import UserInput


class UserAlreadyExists(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=409, detail="User already exists")


class UserNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=404, detail="User not found")


async def get_user_service(db_session: AsyncSession = Depends(get_db_session)) -> "UserService":
    return UserService(db_session=db_session)


class UserService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = UserRepository(db_session=db_session)

    async def create(self, email_address: str) -> DBUser:
        try:
            user = await self.repository.create(email_address=email_address)
        except IntegrityError as exc:
            raise UserAlreadyExists from exc
        return user

    async def retrieve(self, user_id: uuid.UUID) -> DBUser:
        try:
            return await self.repository.retrieve(user_id=user_id)
        except NoResultFound as exc:
            raise UserNotFound from exc

    async def retrieve_by_email(self, email_address: str) -> DBUser:
        try:
            return await self.repository.retrieve_by_email(email_address=email_address)
        except NoResultFound as exc:
            raise UserNotFound from exc

    async def update(self, user_id: uuid.UUID, data: UserInput) -> DBUser:
        user = await self.retrieve(user_id=user_id)
        return await self.repository.update(user=user, data=data)

    async def delete(self, user_id: uuid.UUID, permanent: bool = False) -> bool:
        user = await self.retrieve(user_id=user_id)
        if permanent:
            await self.repository.delete(user=user)
            return True
        await self.repository.update(user=user, data=UserInput(is_active=False))
        return True
