from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from src.db.operations import managed_session
from src.routes.v1.apikeys.service import APIKeyService
from src.settings import settings
from src.utils.app_lifespan import database
from src.utils.logger import logger
from starlette.requests import Request
from starlette.responses import PlainTextResponse


class SourcedTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with managed_session() as session:
                api_key_service = APIKeyService(db_session=session)
                api_key = await api_key_service.retrieve_by_hash(api_key=token)
                return AccessToken(token=token, client_id=str(api_key.user_id), scopes=[])
        except HTTPException:
            return None


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    async with database():
        yield


auth_settings = AuthSettings(issuer_url="https://api.sourced.dev", resource_server_url="https://mcp.sourced.dev")
allowed_hosts = ["localhost:*", "127.0.0.1:*"] if settings.ENVIRONMENT == "LOCAL" else ["mcp.sourced.dev"]
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts, allowed_origins=[]
)
mcp = FastMCP(
    "sourced",
    stateless_http=True,
    token_verifier=SourcedTokenVerifier(),
    auth=auth_settings,
    lifespan=lifespan,
    transport_security=transport_security,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.tool()
def clean_the_couch() -> str:
    """Clean the couch."""
    return "Jeff is cleaning the couch!"


def create_mcp_app():
    logger.info("MCP server application initialised")
    return mcp.streamable_http_app()
