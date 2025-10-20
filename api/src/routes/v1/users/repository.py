"""Repository module for database operations.

This module provides a data access layer that abstracts database operations through a clean interface.
The UserCRUD class handles CRUD operations directly with database models, focusing purely on data
persistence without additional logic. It works with SQLModel entities and returns database models.
"""

import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.routes.v1.users.schema import UserInput


class UserRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, email_address: str) -> "DBUser":
        # Create a new user and add to the session
        user = DBUser(email_address=email_address)
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user

    async def retrieve(self, user_id: uuid.UUID) -> "DBUser":
        user_statement = select(DBUser).where(DBUser.id == user_id)
        user = await self.db_session.exec(user_statement)
        return user.one()

    async def retrieve_by_email(self, email_address: str) -> "DBUser":
        user_statement = select(DBUser).where(DBUser.email_address == email_address)
        user = await self.db_session.exec(user_statement)
        return user.one()

    async def update(self, user: DBUser, data: UserInput) -> "DBUser":
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user

    async def delete(self, user: DBUser) -> bool:
        await self.db_session.delete(user)
        await self.db_session.commit()
        return True
