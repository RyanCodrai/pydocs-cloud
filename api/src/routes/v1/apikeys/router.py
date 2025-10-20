"""Router module for API Key endpoints.

This module defines the FastAPI router and endpoints for API key-related operations. It handles
HTTP requests, manages authentication and authorization, and coordinates with the service
layer. The router ensures proper request handling while delegating business logic to the
service layer.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from src.db.models import DBAPIKey, DBUser
from src.routes.v1.apikeys.schema import APIKeyInput, APIKeyOutput, APIKeyUpdate
from src.routes.v1.apikeys.service import APIKeyService, get_apikey_service
from src.utils.auth import authorise_api_key, authorise_user
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()


@service_tag(ServiceType.USER)
@router.post("/users/{user_id}/api-keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyInput,
    user: DBUser = Depends(authorise_user),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> dict:
    """Create a new API key for the user. Returns the key once - store it safely!"""
    api_key = await api_key_service.create(user_id=user.id, key_name=api_key_data.key_name)
    return api_key.model_dump(exclude={"key_hash"})


@service_tag(ServiceType.USER)
@router.get("/users/{user_id}/api-keys", response_model=List[APIKeyOutput])
async def list_api_keys(
    user: DBUser = Depends(authorise_user),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> List[APIKeyOutput]:
    """List all active API keys for the user."""
    return await api_key_service.retrieve_by_user(user.id, include_inactive=False)


@service_tag(ServiceType.USER)
@router.patch("/users/{user_id}/api-keys/{api_key_id}", response_model=APIKeyOutput)
async def update_api_key(
    update_data: APIKeyUpdate,
    api_key: DBAPIKey = Depends(authorise_api_key),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> APIKeyOutput:
    """Update an API key."""
    return await api_key_service.update(api_key.id, update_data)


@service_tag(ServiceType.USER)
@router.delete("/users/{user_id}/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key: DBAPIKey = Depends(authorise_api_key),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> None:
    """Deactivate an API key (soft delete)."""
    await api_key_service.delete(api_key.id)
