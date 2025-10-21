import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.db.operations import get_db_session
from src.main import application
from src.routes.v1.users.service import UserNotFound, UserService
from src.settings import settings
from src.utils.auth import authenticate_user, authorise_user
from src.utils.logger import logger


def pytest_configure(config):
    """Pytest hook that runs before test collection.
    We use this to load our test environment variables.
    This runs in the same Python session as the tests,
    before any test modules or fixtures are imported.
    """
    print("\n------------ Loading test environment ------------")
    test_env_path = Path(__file__).parent / "test.env"
    if not load_dotenv(str(test_env_path), override=True):
        raise RuntimeError(
            f"Failed to load test environment variables from {test_env_path}",
        )
    print(f"Test environment loaded from {test_env_path}")
    print("--------------------------------------------------\n")


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Create engine for test database
    async_engine = create_async_engine(settings.DATABASE_URL)

    AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Provide session to test
    async with AsyncSessionLocal() as session:
        yield session

    await async_engine.dispose()


@pytest_asyncio.fixture
async def user_service(db_session: AsyncSession) -> UserService:
    return UserService(db_session=db_session)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Replace the db session that's used in the application
    def get_session_override() -> AsyncSession:
        return db_session

    application.dependency_overrides[get_db_session] = get_session_override
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_user(user_service: UserService):
    # Create test user
    user = await user_service.create(email_address=f"{uuid.uuid4()}@unique.com")

    # Mock authentication
    async def mock_authenticate_user() -> DBUser:
        return user

    application.dependency_overrides[authenticate_user] = mock_authenticate_user
    # Return user for test
    yield user
    # Cleanup
    try:
        await user_service.delete(user_id=user.id, permanent=True)
    except UserNotFound:
        logger.warning(f"User {user.id} already deleted")


@pytest_asyncio.fixture
async def authorised_user(authenticated_user: DBUser) -> DBUser:
    # Mock authentication
    async def mock_authorise_user() -> DBUser:
        return authenticated_user

    application.dependency_overrides[authorise_user] = mock_authorise_user
    return authenticated_user
