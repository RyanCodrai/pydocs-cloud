from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.db.models import DBAPIKey, DBUser
from src.routes.v1.apikeys.service import APIKeyService, get_apikey_service
from src.routes.v1.queries.service import QueryService, get_query_service
from src.routes.v1.users.service import UserNotFound, UserService, get_user_service
from src.settings import settings

security = HTTPBearer(auto_error=False)


class UnauthorisedException(HTTPException):
    def __init__(self, detail: str = "You don't have permission to access this resource") -> None:
        # This indicates the server understood the request but refuses to authorize it
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class WaitlistedException(HTTPException):
    def __init__(self, detail: str = "Your account is on the waitlist") -> None:
        # 403 Forbidden - authenticated but not authorized
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self, detail: str = "Unable to authenticate Bearer token") -> None:
        # This indicates that the request lacks valid authentication credentials
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenAuthenticator:
    jwks_client = jwt.PyJWKClient(f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json")

    @classmethod
    async def authenticate(cls, token: HTTPAuthorizationCredentials) -> dict:
        try:
            signing_key = cls.jwks_client.get_signing_key_from_jwt(token.credentials).key
            return jwt.decode(
                jwt=token.credentials,
                key=signing_key,
                algorithms=settings.AUTH0_ALGORITHMS,
                audience=settings.AUTH0_CLIENT_ID,
                issuer=settings.AUTH0_ISSUER,
            )
        except Exception as exc:
            print(f"JWT decode error: {exc}")
            print(f"Settings - Domain: {settings.AUTH0_DOMAIN}")
            print(f"Settings - Audience: {settings.AUTH0_CLIENT_ID}")
            print(f"Settings - Issuer: {settings.AUTH0_ISSUER}")
            # Re-raise as UnauthenticatedException while preserving the original exception chain.
            # This allows for detailed server-side logging and debugging without exposing
            # sensitive information to clients. Only a generic error is sent to the client.
            raise UnauthenticatedException from exc


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
) -> DBUser:
    jwt_payload = await TokenAuthenticator.authenticate(credentials)
    email_address = jwt_payload.get("https://pydocs.ai/email")
    try:
        user = await user_service.retrieve_by_email(email_address=email_address)
    except UserNotFound:
        # Create new user and add to waitlist
        user = await user_service.create(email_address=email_address)

    # Check if user is on the waitlist
    if not user.is_active:
        raise WaitlistedException()

    return user


async def authorise_user(
    user_id: uuid.UUID,
    user: DBUser = Depends(authenticate_user),
) -> DBUser:
    # Authorise access if the authenticated user ID matches the requested user ID
    # This ensures users can only access their own data
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


async def authenticate_query(
    credentials: HTTPAuthorizationCredentials = Depends(get_token),
    user_service: UserService = Depends(get_user_service),
    api_key_service: APIKeyService = Depends(get_apikey_service),
    query_service: QueryService = Depends(get_query_service),
) -> tuple[DBUser, DBAPIKey]:
    # If token is an api key not a jason web token
    if credentials.credentials.startswith("pydocs"):
        api_key = await api_key_service.retrieve_by_hash(api_key=credentials.credentials)
        user = await user_service.retrieve(user_id=api_key.user_id)
        # Check rate-limits for this api key
        await query_service.check_api_key_rate_limits(api_key=api_key)
        await query_service.check_user_rate_limits(user_id=user.id)
        return user, api_key

    # Authenticate as jason web token
    jwt_payload = await TokenAuthenticator.authenticate(credentials)
    email_address = jwt_payload.get("https://pydocs.ai/email")
    try:
        user = await user_service.retrieve_by_email(email_address=email_address)
        await query_service.check_user_rate_limits(user_id=user.id)
    except UserNotFound:
        user = await user_service.create(email_address=email_address)
    return user, None
