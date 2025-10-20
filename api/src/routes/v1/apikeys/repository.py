"""Repository module for API Keys database operations.

This module provides a data access layer for API key management, handling CRUD operations
and usage tracking. The APIKeyRepository class works with DBAPIKey entities and focuses
purely on data persistence without additional business logic.
"""

import uuid
from typing import List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBAPIKey
from src.routes.v1.apikeys.schema import APIKeyInput, APIKeyUpdateFull


class APIKeyRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: APIKeyInput) -> DBAPIKey:
        """Create a new API key record."""
        api_key = DBAPIKey(**data.model_dump())
        self.db_session.add(api_key)
        await self.db_session.commit()
        await self.db_session.refresh(api_key)
        return api_key

    async def retrieve(self, api_key_id: uuid.UUID, include_inactive: bool = False) -> DBAPIKey:
        """Retrieve an API key by its ID."""
        statement = select(DBAPIKey).where(DBAPIKey.id == api_key_id)

        if not include_inactive:
            statement = statement.where(DBAPIKey.is_active)

        result = await self.db_session.exec(statement)
        return result.one()

    async def retrieve_by_hash(self, key_hash: str) -> DBAPIKey:
        """Retrieve an API key by its hash for authentication."""
        statement = select(DBAPIKey).where(DBAPIKey.key_hash == key_hash, DBAPIKey.is_active)
        result = await self.db_session.exec(statement)
        return result.one()

    async def retrieve_by_user(self, user_id: uuid.UUID, include_inactive: bool = False) -> List[DBAPIKey]:
        """Retrieve all API keys for a specific user."""
        statement = select(DBAPIKey).where(DBAPIKey.user_id == user_id)

        if not include_inactive:
            statement = statement.where(DBAPIKey.is_active)

        statement = statement.order_by(DBAPIKey.created_at.desc())
        result = await self.db_session.exec(statement)
        return result.all()

    async def update(self, api_key: DBAPIKey, data: APIKeyUpdateFull) -> DBAPIKey:
        """Update an API key with provided data."""
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(api_key, field, value)
        await self.db_session.commit()
        await self.db_session.refresh(api_key)
        return api_key

    async def delete(self, api_key: DBAPIKey) -> bool:
        """Delete an API key from the database."""
        await self.db_session.delete(api_key)
        await self.db_session.commit()
        return True
