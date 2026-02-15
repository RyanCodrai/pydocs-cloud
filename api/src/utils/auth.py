from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.db.models import DBAPIKey, DBUser
from src.routes.v1.apikeys.service import APIKeyService, get_apikey_service
from src.routes.v1.users.service import UserService, get_user_service

security = HTTPBearer(auto_error=False)


class UnauthorisedException(HTTPException):
    def __init__(self, detail: str = "You don't have permission to access this resource") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self, detail: str = "Unable to authenticate Bearer token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_token(
    request: Request = None,
    websocket: WebSocket = None,
) -> HTTPAuthorizationCredentials:
    if request and "Authorization" in request.headers:
        token = request.headers.get("Authorization")[7:]
    elif websocket and "Authorization" in websocket.headers:
        token = websocket.headers.get("Authorization")[7:]
    elif websocket and "Authorization" in websocket.query_params:
        token = websocket.query_params.get("Authorization")
    else:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def authenticate_user(
    credentials: HTTPAuthorizationCredentials = Depends(get_token),
    user_service: UserService = Depends(get_user_service),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> DBUser:
    api_key = await api_key_service.retrieve_by_hash(api_key=credentials.credentials)
    return await user_service.retrieve(user_id=api_key.user_id)


async def authorise_user(
    user_id: uuid.UUID,
    user: DBUser = Depends(authenticate_user),
) -> DBUser:
    if user.id == user_id:
        return user
    raise UnauthorisedException


async def authorise_api_key(
    api_key_id: uuid.UUID,
    user: DBUser = Depends(authenticate_user),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> DBAPIKey:
    api_key = await api_key_service.retrieve(api_key_id=api_key_id)
    await authorise_user(user_id=api_key.user_id, user=user)
    return api_key
