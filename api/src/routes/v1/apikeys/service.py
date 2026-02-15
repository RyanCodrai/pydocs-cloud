"""Service module for API Key business logic.

This module provides the business logic layer for API key management. The APIKeyService class
handles key generation, hashing, validation, and orchestrates repository operations while
maintaining separation of concerns from the data access layer.
"""

import hashlib
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.exc import NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBAPIKey
from src.db.operations import get_db_session
from src.routes.v1.apikeys.repository import APIKeyRepository
from src.routes.v1.apikeys.schema import APIKeyInput, APIKeyOutput, APIKeyOutputFirstCreation, APIKeyUpdateFull


class InvalidAPIKeyException(HTTPException):
    """Raised when an API key is invalid, not found, or inactive."""

    def __init__(self) -> None:
        super().__init__(status_code=401, detail="Invalid API key", headers={"WWW-Authenticate": "Bearer"})


async def get_apikey_service(db_session: AsyncSession = Depends(get_db_session)) -> "APIKeyService":
    return APIKeyService(db_session=db_session)


class APIKeyService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = APIKeyRepository(db_session=db_session)

    async def create(self, user_id: uuid.UUID, key_name: str) -> APIKeyOutputFirstCreation:
        """Create a new API key and return the database record and full key."""
        api_key_input = APIKeyInput(user_id=user_id, key_name=key_name, is_active=True)
        api_key = await self.repository.create(api_key_input)
        return APIKeyOutputFirstCreation(**api_key.model_dump(), api_key=api_key_input.api_key)

    async def retrieve(self, api_key_id: uuid.UUID) -> APIKeyOutput:
        """Retrieve an API key by its ID."""
        try:
            data = await self.repository.retrieve(api_key_id)
            return APIKeyOutput(**data.model_dump())
        except NoResultFound as exc:
            raise InvalidAPIKeyException from exc

    async def retrieve_by_hash(self, api_key: str) -> DBAPIKey:
        """Retrieve and validate an API key by its full key value."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        try:
            return await self.repository.retrieve_by_hash(key_hash)
        except NoResultFound as exc:
            raise InvalidAPIKeyException from exc

    async def retrieve_by_user(self, user_id: uuid.UUID, include_inactive: bool = False) -> list[APIKeyOutput]:
        """Retrieve all API keys for a specific user."""
        api_keys = await self.repository.retrieve_by_user(user_id, include_inactive)
        return [APIKeyOutput(**key.model_dump()) for key in api_keys]

    async def update(self, api_key_id: uuid.UUID, update_data: APIKeyUpdateFull) -> APIKeyOutput:
        """Update an API key with new data."""
        try:
            api_key = await self.repository.retrieve(api_key_id)
            updated_api_key = await self.repository.update(api_key, update_data)
            return APIKeyOutput(**updated_api_key.model_dump())
        except NoResultFound as exc:
            raise InvalidAPIKeyException from exc

    async def delete(self, api_key_id: uuid.UUID, permanent: bool = False) -> bool:
        """Delete an API key. Soft delete by default, hard delete if permanent=True."""
        try:
            api_key = await self.repository.retrieve(api_key_id)
        except NoResultFound as exc:
            raise InvalidAPIKeyException from exc
        if permanent:
            await self.repository.delete(api_key)
            return True
        await self.repository.update(api_key, APIKeyUpdateFull(is_active=False))
        return True
