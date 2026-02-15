import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from src.routes.v1.apikeys.service import APIKeyService, get_apikey_service
from src.routes.v1.auth.schema import AuthTokenOutput, GitHubCodeInput
from src.routes.v1.users.schema import UserInput
from src.routes.v1.users.service import UserNotFound, UserService, get_user_service
from src.settings import settings

router = APIRouter()


class GitHubAuthError(HTTPException):
    def __init__(self, detail: str = "GitHub authentication failed") -> None:
        super().__init__(status_code=401, detail=detail)


async def exchange_code_for_token(code: str, redirect_uri: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_APP_CLIENT_ID,
                "client_secret": settings.GITHUB_APP_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        ) as response:
            data = await response.json()

    access_token = data.get("access_token")
    if not access_token:
        raise GitHubAuthError

    return access_token


async def get_github_email(access_token: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        ) as response:
            if response.status != 200:
                raise GitHubAuthError(detail="Failed to fetch GitHub user email")
            emails = await response.json()

    primary_email = next((e["email"] for e in emails if e.get("primary")), None)
    if not primary_email:
        raise GitHubAuthError
    return primary_email


async def get_or_create_user(user_service: UserService, email: str, github_token: str) -> "DBUser":
    try:
        user = await user_service.retrieve_by_email(email_address=email)
    except UserNotFound:
        user = await user_service.create(email_address=email)
    user = await user_service.update(user_id=user.id, data=UserInput(github_token=github_token))
    return user


@router.post("/auth/token")
async def exchange_token(
    body: GitHubCodeInput,
    user_service: UserService = Depends(get_user_service),
    api_key_service: APIKeyService = Depends(get_apikey_service),
) -> AuthTokenOutput:
    github_access_token = await exchange_code_for_token(body.code, body.redirect_uri)
    email = await get_github_email(github_access_token)
    user = await get_or_create_user(user_service, email, github_access_token)
    api_key_output = await api_key_service.create(user_id=user.id, key_name="mcp")
    return AuthTokenOutput(api_key=api_key_output.api_key)
