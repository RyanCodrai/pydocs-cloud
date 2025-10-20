import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.routes.v1.apikeys.repository import APIKeyRepository
from src.routes.v1.apikeys.schema import APIKeyInput
from src.routes.v1.queries.repository import QueryRepository
from src.routes.v1.queries.schema import QueryInput, QueryOutput


# Repository Tests - Manual cleanup since we're testing repository directly
@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_create(db_session: AsyncSession):
    """Test creating a query via repository."""
    repository = QueryRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = QueryInput(user_id=user.id, query_text="test query", packages_detected=["numpy", "pandas"])

    query = await repository.create(data)

    assert query.user_id == user.id
    assert query.query_text == "test query"
    assert query.packages_detected == ["numpy", "pandas"]
    assert query.api_key_id is None  # No API key provided
    assert query.id is not None
    assert query.created_at is not None

    # Cleanup
    await repository.delete(query=query)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_create_with_api_key(db_session: AsyncSession):
    """Test creating a query with API key via repository."""
    repository = QueryRepository(db_session)
    api_key_repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create an API key
    api_key_data = APIKeyInput(user_id=user.id, key_name="Test API Key", is_active=True)
    api_key = await api_key_repository.create(api_key_data)

    data = QueryInput(
        user_id=user.id, api_key_id=api_key.id, query_text="test query with api key", packages_detected=["requests"]
    )

    query = await repository.create(data)

    assert query.user_id == user.id
    assert query.api_key_id == api_key.id
    assert query.query_text == "test query with api key"
    assert query.packages_detected == ["requests"]

    # Cleanup
    await repository.delete(query=query)
    await api_key_repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve(db_session: AsyncSession):
    """Test retrieving a query by ID via repository."""
    repository = QueryRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = QueryInput(user_id=user.id, query_text="retrieve test query", packages_detected=["matplotlib"])

    created_query = await repository.create(data)
    retrieved_query = await repository.retrieve(query_id=created_query.id)

    assert retrieved_query.id == created_query.id
    assert retrieved_query.query_text == "retrieve test query"
    assert retrieved_query.user_id == user.id

    # Cleanup
    await repository.delete(query=created_query)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve_nonexistent(db_session: AsyncSession):
    """Test retrieving non-existent query raises NoResultFound."""
    repository = QueryRepository(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(NoResultFound):
        await repository.retrieve(query_id=fake_id)


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve_by_user(db_session: AsyncSession):
    """Test retrieving queries by user ID via repository."""
    repository = QueryRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create multiple queries for the user
    data1 = QueryInput(user_id=user.id, query_text="Query 1", packages_detected=["numpy"])
    data2 = QueryInput(user_id=user.id, query_text="Query 2", packages_detected=["pandas"])
    data3 = QueryInput(user_id=user.id, query_text="Query 3", packages_detected=["scipy"])

    query1 = await repository.create(data1)
    query2 = await repository.create(data2)
    query3 = await repository.create(data3)

    # Test retrieving all queries
    all_queries = await repository.retrieve_by_user(user_id=user.id)
    assert len(all_queries) == 3
    assert all(query.user_id == user.id for query in all_queries)

    # Test that queries are ordered by created_at desc (most recent first)
    query_texts = [query.query_text for query in all_queries]
    assert query_texts == ["Query 3", "Query 2", "Query 1"]  # Most recent first

    # Test with limit
    limited_queries = await repository.retrieve_by_user(user_id=user.id, limit=2)
    assert len(limited_queries) == 2
    assert limited_queries[0].query_text == "Query 3"
    assert limited_queries[1].query_text == "Query 2"

    # Cleanup
    await repository.delete(query=query1)
    await repository.delete(query=query2)
    await repository.delete(query=query3)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve_by_user_with_since(db_session: AsyncSession):
    """Test retrieving queries by user with since parameter for rate limiting."""
    repository = QueryRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create queries with different timestamps
    data1 = QueryInput(user_id=user.id, query_text="Old Query", packages_detected=[])
    data2 = QueryInput(user_id=user.id, query_text="Recent Query", packages_detected=[])

    query1 = await repository.create(data1)

    # Wait a moment or manually set timestamp for testing
    await repository.create(data2)

    # Test retrieving queries since 1 hour ago (should get all)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_queries = await repository.retrieve_by_user(user_id=user.id, since=one_hour_ago)
    assert len(recent_queries) == 2

    # Test retrieving queries since future time (should get none)
    future_time = datetime.utcnow() + timedelta(hours=1)
    future_queries = await repository.retrieve_by_user(user_id=user.id, since=future_time)
    assert len(future_queries) == 0

    # Cleanup
    for query in recent_queries:
        await repository.delete(query=query)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve_by_api_key(db_session: AsyncSession):
    """Test retrieving queries by API key ID via repository."""
    repository = QueryRepository(db_session)
    api_key_repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create an API key
    api_key_data = APIKeyInput(user_id=user.id, key_name="Test API Key", is_active=True)
    api_key = await api_key_repository.create(api_key_data)

    # Create queries with and without the API key
    data1 = QueryInput(user_id=user.id, api_key_id=api_key.id, query_text="API Query 1", packages_detected=[])
    data2 = QueryInput(user_id=user.id, api_key_id=api_key.id, query_text="API Query 2", packages_detected=[])
    data3 = QueryInput(user_id=user.id, query_text="No API Query", packages_detected=[])  # No API key

    query1 = await repository.create(data1)
    query2 = await repository.create(data2)
    query3 = await repository.create(data3)

    # Test retrieving queries by API key
    api_key_queries = await repository.retrieve_by_api_key(api_key_id=api_key.id)
    assert len(api_key_queries) == 2
    assert all(query.api_key_id == api_key.id for query in api_key_queries)

    # Test that queries are ordered by created_at desc
    query_texts = [query.query_text for query in api_key_queries]
    assert query_texts == ["API Query 2", "API Query 1"]  # Most recent first

    # Test with limit
    limited_queries = await repository.retrieve_by_api_key(api_key_id=api_key.id, limit=1)
    assert len(limited_queries) == 1
    assert limited_queries[0].query_text == "API Query 2"

    # Cleanup
    await repository.delete(query=query1)
    await repository.delete(query=query2)
    await repository.delete(query=query3)
    await api_key_repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_retrieve_by_api_key_with_since(db_session: AsyncSession):
    """Test retrieving queries by API key with since parameter for rate limiting."""
    repository = QueryRepository(db_session)
    api_key_repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create an API key
    api_key_data = APIKeyInput(user_id=user.id, key_name="Rate Limit Test", is_active=True)
    api_key = await api_key_repository.create(api_key_data)

    # Create queries
    data1 = QueryInput(user_id=user.id, api_key_id=api_key.id, query_text="Rate Query 1", packages_detected=[])
    data2 = QueryInput(user_id=user.id, api_key_id=api_key.id, query_text="Rate Query 2", packages_detected=[])

    query1 = await repository.create(data1)
    query2 = await repository.create(data2)

    # Test retrieving queries since 1 minute ago (should get all)
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    recent_queries = await repository.retrieve_by_api_key(api_key_id=api_key.id, since=one_minute_ago)
    assert len(recent_queries) == 2

    # Test retrieving queries since future time (should get none)
    future_time = datetime.utcnow() + timedelta(minutes=1)
    future_queries = await repository.retrieve_by_api_key(api_key_id=api_key.id, since=future_time)
    assert len(future_queries) == 0

    # Cleanup
    await repository.delete(query=query1)
    await repository.delete(query=query2)
    await api_key_repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_query_repository_delete(db_session: AsyncSession):
    """Test deleting a query via repository."""
    repository = QueryRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = QueryInput(user_id=user.id, query_text="Delete Test", packages_detected=[])

    query = await repository.create(data)
    result = await repository.delete(query=query)

    assert result is True

    # Verify query is actually deleted
    with pytest.raises(NoResultFound):
        await repository.retrieve(query_id=query.id)

    # Cleanup user only (query was already deleted by the test)
    await db_session.delete(user)
    await db_session.commit()


# Schema Tests (synchronous)
def test_query_input_schema_valid_data():
    """Test QueryInput schema with valid data."""
    user_id = uuid.uuid4()
    api_key_id = uuid.uuid4()

    data = {
        "user_id": user_id,
        "api_key_id": api_key_id,
        "query_text": "test query",
        "packages_detected": ["numpy", "pandas"],
    }

    query_input = QueryInput(**data)

    assert query_input.user_id == user_id
    assert query_input.api_key_id == api_key_id
    assert query_input.query_text == "test query"
    assert query_input.packages_detected == ["numpy", "pandas"]


def test_query_input_schema_minimal_data():
    """Test QueryInput schema with minimal required data."""
    user_id = uuid.uuid4()

    data = {"user_id": user_id, "query_text": "minimal query"}

    query_input = QueryInput(**data)

    assert query_input.user_id == user_id
    assert query_input.api_key_id is None
    assert query_input.query_text == "minimal query"
    assert query_input.packages_detected == []  # Default empty list


def test_query_input_schema_missing_required_field():
    """Test QueryInput schema with missing required fields."""
    with pytest.raises(ValueError):
        QueryInput(query_text="missing user_id")  # Missing user_id

    with pytest.raises(ValueError):
        QueryInput(user_id=uuid.uuid4())  # Missing query_text


def test_query_input_schema_invalid_types():
    """Test QueryInput schema with invalid data types."""
    user_id = uuid.uuid4()

    with pytest.raises(ValueError):
        QueryInput(user_id="not_a_uuid", query_text="test")

    with pytest.raises(ValueError):
        QueryInput(user_id=user_id, query_text=123)  # query_text should be string

    with pytest.raises(ValueError):
        QueryInput(user_id=user_id, query_text="test", packages_detected="not_a_list")


def test_query_output_schema_valid_data():
    """Test QueryOutput schema with valid data."""
    query_id = uuid.uuid4()
    user_id = uuid.uuid4()
    api_key_id = uuid.uuid4()
    created_at = datetime.utcnow()

    data = {
        "id": query_id,
        "user_id": user_id,
        "api_key_id": api_key_id,
        "query_text": "test output query",
        "packages_detected": ["requests", "beautifulsoup4"],
        "created_at": created_at,
    }

    query_output = QueryOutput(**data)

    assert query_output.id == query_id
    assert query_output.user_id == user_id
    assert query_output.api_key_id == api_key_id
    assert query_output.query_text == "test output query"
    assert query_output.packages_detected == ["requests", "beautifulsoup4"]
    assert query_output.created_at == created_at


def test_query_output_schema_nullable_api_key():
    """Test QueryOutput schema with null API key."""
    query_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created_at = datetime.utcnow()

    data = {
        "id": query_id,
        "user_id": user_id,
        "api_key_id": None,
        "query_text": "no api key query",
        "packages_detected": [],
        "created_at": created_at,
    }

    query_output = QueryOutput(**data)

    assert query_output.id == query_id
    assert query_output.user_id == user_id
    assert query_output.api_key_id is None
    assert query_output.query_text == "no api key query"
    assert query_output.packages_detected == []
    assert query_output.created_at == created_at


def test_query_output_schema_missing_required_field():
    """Test QueryOutput schema with missing required fields."""
    with pytest.raises(ValueError):
        QueryOutput(user_id=uuid.uuid4(), query_text="test")  # Missing id, api_key_id, packages_detected, created_at


def test_query_output_schema_empty_packages():
    """Test QueryOutput schema with empty packages list."""
    query_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created_at = datetime.utcnow()

    data = {
        "id": query_id,
        "user_id": user_id,
        "api_key_id": None,
        "query_text": "no packages detected",
        "packages_detected": [],
        "created_at": created_at,
    }

    query_output = QueryOutput(**data)

    assert query_output.packages_detected == []
    assert isinstance(query_output.packages_detected, list)
