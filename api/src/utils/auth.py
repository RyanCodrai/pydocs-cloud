from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


class UnauthenticatedException(HTTPException):
    def __init__(self, detail: str = "Unable to authenticate Bearer token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_bearer_token(header_value: str) -> str:
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthenticatedException(detail="Invalid authorization scheme")
    return token


async def get_token(
    request: Request = None,
) -> HTTPAuthorizationCredentials:
    if request and "Authorization" in request.headers:
        token = _extract_bearer_token(request.headers.get("Authorization"))
    else:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
