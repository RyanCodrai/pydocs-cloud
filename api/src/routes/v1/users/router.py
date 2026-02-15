"""Router module for API endpoints.

This module defines the FastAPI router and endpoints for user-related operations. It handles
HTTP requests, manages authentication and authorization, and coordinates with the operations
layer. The router ensures proper request handling while delegating business logic to the
operations layer.
"""

from fastapi import APIRouter, Depends
from src.db.models import DBUser
from src.routes.v1.users.schema import UserInput, UserOutput
from src.routes.v1.users.service import UserService, get_user_service
from src.utils.auth import authenticate_user, authorise_user

router = APIRouter()


@router.get("/users")
async def get_user(user: DBUser = Depends(authenticate_user)) -> UserOutput:
    return UserOutput(**user.model_dump())


@router.patch("/users/{user_id}")
async def update_user(
    update_user_data: UserInput,
    user_service: UserService = Depends(get_user_service),
    user: DBUser = Depends(authorise_user),
) -> UserOutput:
    user = await user_service.update(user_id=user.id, data=update_user_data)
    return UserOutput(**user.model_dump())
