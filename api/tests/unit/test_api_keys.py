import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.routes.v1.apikeys.repository import APIKeyRepository
from src.routes.v1.apikeys.schema import (
    APIKeyInput,
    APIKeyOutput,
    APIKeyOutputFirstCreation,
    APIKeyUpdate,
    APIKeyUpdateFull,
    Attributes,
    RateLimit,
)
from src.routes.v1.apikeys.service import APIKeyService, InvalidAPIKeyException


# Repository Tests
@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_create(db_session: AsyncSession):
    """Test creating an API key via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Test API Key")

    api_key = await repository.create(data)

    assert api_key.user_id == user.id
    assert api_key.key_name == "Test API Key"
    assert api_key.is_active is True
    assert api_key.id is not None
    assert api_key.key_hash is not None
    assert api_key.key_prefix is not None
    assert api_key.attributes is not None
    assert isinstance(api_key.attributes, dict)
    assert "rate_limits" in api_key.attributes
    assert len(api_key.attributes["rate_limits"]) == 1
    assert api_key.attributes["rate_limits"][0]["seconds"] == 86400
    assert api_key.attributes["rate_limits"][0]["limit"] == 100

    await repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_create_with_custom_attributes(db_session: AsyncSession):
    """Test creating an API key with custom rate limits via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    custom_attributes = Attributes(rate_limits=[RateLimit.per_hour(50), RateLimit.per_day(500)])
    data = APIKeyInput(user_id=user.id, key_name="Custom Rate Limits Key", attributes=custom_attributes)

    api_key = await repository.create(data)

    assert api_key.user_id == user.id
    assert api_key.key_name == "Custom Rate Limits Key"
    assert api_key.attributes is not None
    assert "rate_limits" in api_key.attributes
    assert len(api_key.attributes["rate_limits"]) == 2

    rate_limits = api_key.attributes["rate_limits"]
    assert any(rl["seconds"] == 3600 and rl["limit"] == 50 for rl in rate_limits)
    assert any(rl["seconds"] == 86400 and rl["limit"] == 500 for rl in rate_limits)

    await repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve(db_session: AsyncSession):
    """Test retrieving an API key by ID via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Retrieve Test")
    created_key = await repository.create(data)
    retrieved_key = await repository.retrieve(api_key_id=created_key.id)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_name == "Retrieve Test"
    assert retrieved_key.user_id == user.id
    assert retrieved_key.attributes is not None
    assert isinstance(retrieved_key.attributes, dict)
    assert "rate_limits" in retrieved_key.attributes

    await repository.delete(api_key=created_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_nonexistent(db_session: AsyncSession):
    """Test retrieving non-existent API key raises NoResultFound."""
    repository = APIKeyRepository(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(NoResultFound):
        await repository.retrieve(api_key_id=fake_id)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_hash(db_session: AsyncSession):
    """Test retrieving an API key by hash via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Hash Test")
    created_key = await repository.create(data)
    retrieved_key = await repository.retrieve_by_hash(key_hash=data.key_hash)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_hash == data.key_hash

    await repository.delete(api_key=created_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_hash_nonexistent(db_session: AsyncSession):
    """Test retrieving API key by non-existent hash raises NoResultFound."""
    repository = APIKeyRepository(db_session)

    with pytest.raises(NoResultFound):
        await repository.retrieve_by_hash(key_hash="nonexistent_hash")


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_hash_inactive(db_session: AsyncSession):
    """Test retrieving inactive API key by hash raises NoResultFound."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Inactive Test", is_active=False)
    created_key = await repository.create(data)

    with pytest.raises(NoResultFound):
        await repository.retrieve_by_hash(key_hash=data.key_hash)

    await repository.delete(api_key=created_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_user(db_session: AsyncSession):
    """Test retrieving API keys by user ID via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data1 = APIKeyInput(user_id=user.id, key_name="Key 1")
    data2 = APIKeyInput(user_id=user.id, key_name="Key 2")
    data3 = APIKeyInput(user_id=user.id, key_name="Key 3", is_active=False)

    key1 = await repository.create(data1)
    key2 = await repository.create(data2)
    key3 = await repository.create(data3)

    active_keys = await repository.retrieve_by_user(user_id=user.id, include_inactive=False)
    assert len(active_keys) == 2
    assert all(key.is_active for key in active_keys)

    all_keys = await repository.retrieve_by_user(user_id=user.id, include_inactive=True)
    assert len(all_keys) == 3

    await repository.delete(api_key=key1)
    await repository.delete(api_key=key2)
    await repository.delete(api_key=key3)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_update(db_session: AsyncSession):
    """Test updating an API key via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Original Name")
    api_key = await repository.create(data)
    assert api_key.is_active is True

    update_data = APIKeyUpdateFull(is_active=False)
    updated_key = await repository.update(api_key=api_key, data=update_data)

    assert updated_key.is_active is False
    assert updated_key.id == api_key.id
    assert updated_key.attributes == api_key.attributes

    await repository.delete(api_key=updated_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_update_attributes(db_session: AsyncSession):
    """Test updating an API key's attributes via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Attributes Test")
    api_key = await repository.create(data)
    original_attributes = api_key.attributes

    new_attributes = Attributes(rate_limits=[RateLimit.per_day(200)])
    update_data = APIKeyUpdateFull(attributes=new_attributes)
    updated_key = await repository.update(api_key=api_key, data=update_data)

    assert updated_key.attributes != original_attributes
    assert updated_key.attributes["rate_limits"][0]["limit"] == 200

    await repository.delete(api_key=updated_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_delete(db_session: AsyncSession):
    """Test deleting an API key via repository."""
    repository = APIKeyRepository(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Delete Test")
    api_key = await repository.create(data)
    result = await repository.delete(api_key=api_key)

    assert result is True

    with pytest.raises(NoResultFound):
        await repository.retrieve(api_key_id=api_key.id)

    await db_session.delete(user)
    await db_session.commit()


# Service Tests
@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_create(db_session: AsyncSession):
    """Test creating an API key via service."""
    service = APIKeyService(db_session)

    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    result = await service.create(user_id=user.id, key_name="Service Test")

    assert isinstance(result, APIKeyOutputFirstCreation)
    assert result.key_name == "Service Test"
    assert result.api_key is not None
    assert result.api_key.startswith("sdk-")
    assert result.key_prefix is not None
    assert result.id is not None
    assert result.created_at is not None
    assert result.attributes is not None
    assert result.attributes.rate_limits is not None
    assert len(result.attributes.rate_limits) == 1
    assert result.attributes.rate_limits[0].seconds == 86400
    assert result.attributes.rate_limits[0].limit == 100

    await service.delete(api_key_id=result.id, permanent=True)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving an API key by ID via service."""
    service = APIKeyService(db_session)

    data = APIKeyInput(user_id=authenticated_user.id, key_name="Retrieve Test")
    repository = APIKeyRepository(db_session)
    created_key = await repository.create(data)

    retrieved_key = await service.retrieve(api_key_id=created_key.id)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_name == "Retrieve Test"
    assert retrieved_key.attributes is not None

    await repository.delete(api_key=created_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_nonexistent(db_session: AsyncSession):
    """Test retrieving non-existent API key raises InvalidAPIKeyException."""
    service = APIKeyService(db_session)

    with pytest.raises(InvalidAPIKeyException) as exc_info:
        await service.retrieve(api_key_id=uuid.uuid4())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API key"


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_hash(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving an API key by hash via service."""
    service = APIKeyService(db_session)

    data = APIKeyInput(user_id=authenticated_user.id, key_name="Hash Test")
    repository = APIKeyRepository(db_session)
    created_key = await repository.create(data)

    retrieved_key = await service.retrieve_by_hash(api_key=data.api_key)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_hash == data.key_hash

    await repository.delete(api_key=created_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_hash_nonexistent(db_session: AsyncSession):
    """Test retrieving API key by non-existent hash raises InvalidAPIKeyException."""
    service = APIKeyService(db_session)

    with pytest.raises(InvalidAPIKeyException) as exc_info:
        await service.retrieve_by_hash(api_key="sdk-fake_key_that_does_not_exist")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API key"


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_user(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving API keys by user via service."""
    service = APIKeyService(db_session)
    repository = APIKeyRepository(db_session)

    data1 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 1")
    data2 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 2")

    key1 = await repository.create(data1)
    key2 = await repository.create(data2)

    results = await service.retrieve_by_user(user_id=authenticated_user.id, include_inactive=False)

    assert len(results) == 2
    assert all(isinstance(result, APIKeyOutput) for result in results)

    await repository.delete(api_key=key1)
    await repository.delete(api_key=key2)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_deactivate(authenticated_user: DBUser, db_session: AsyncSession):
    """Test deactivating an API key via service."""
    service = APIKeyService(db_session)
    repository = APIKeyRepository(db_session)

    data = APIKeyInput(user_id=authenticated_user.id, key_name="Deactivate Test")
    created_key = await repository.create(data)

    result = await service.delete(api_key_id=created_key.id)

    assert result is True

    updated_key = await repository.retrieve(api_key_id=created_key.id, include_inactive=True)
    assert updated_key.is_active is False

    await repository.delete(api_key=updated_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_deactivate_nonexistent(db_session: AsyncSession):
    """Test deactivating non-existent API key raises InvalidAPIKeyException."""
    service = APIKeyService(db_session)

    with pytest.raises(InvalidAPIKeyException) as exc_info:
        await service.delete(api_key_id=uuid.uuid4())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API key"


# Router Tests
@pytest.mark.asyncio(loop_scope="function")
async def test_list_api_keys_success(client: AsyncClient, authenticated_user: DBUser, db_session: AsyncSession):
    """Test GET /users/{user_id}/api-keys returns user's API keys."""
    repository = APIKeyRepository(db_session)
    data1 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 1")
    data2 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 2")

    key1 = await repository.create(data1)
    key2 = await repository.create(data2)

    response = await client.get(f"/api/v1/users/{authenticated_user.id}/api-keys")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2

    required_fields = {"id", "key_name", "key_prefix", "created_at", "attributes"}
    forbidden_fields = {"key_hash", "api_key", "is_active", "updated_at", "user_id"}

    for key in data:
        assert required_fields.issubset(key.keys())
        assert not any(field in key for field in forbidden_fields)
        assert "rate_limits" in key["attributes"]

    await repository.delete(api_key=key1)
    await repository.delete(api_key=key2)


@pytest.mark.asyncio(loop_scope="function")
async def test_list_api_keys_empty(client: AsyncClient, authenticated_user: DBUser):
    """Test GET /users/{user_id}/api-keys with no API keys."""
    response = await client.get(f"/api/v1/users/{authenticated_user.id}/api-keys")

    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_list_api_keys_unauthenticated(client: AsyncClient):
    """Test GET /users/{user_id}/api-keys without authentication."""
    client.headers.pop("Authorization", None)

    response = await client.get(f"/api/v1/users/{uuid.uuid4()}/api-keys")

    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_api_key_success(client: AsyncClient, authenticated_user: DBUser, db_session: AsyncSession):
    """Test DELETE /users/{user_id}/api-keys/{api_key_id} with valid API key."""
    repository = APIKeyRepository(db_session)
    data = APIKeyInput(user_id=authenticated_user.id, key_name="Delete Test")
    created_key = await repository.create(data)

    response = await client.delete(f"/api/v1/users/{authenticated_user.id}/api-keys/{created_key.id}")

    assert response.status_code == 204

    retrieved_key = await repository.retrieve(api_key_id=created_key.id, include_inactive=True)
    assert retrieved_key.is_active is False

    await repository.delete(api_key=retrieved_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_api_key_nonexistent(client: AsyncClient, authenticated_user: DBUser):
    """Test DELETE /users/{user_id}/api-keys/{api_key_id} with non-existent API key."""
    response = await client.delete(f"/api/v1/users/{authenticated_user.id}/api-keys/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_api_key_unauthorized_different_user(
    client: AsyncClient, authenticated_user: DBUser, db_session: AsyncSession
):
    """Test DELETE /users/{user_id}/api-keys/{api_key_id} with API key belonging to different user."""
    other_user = DBUser(email_address=f"other-{uuid.uuid4()}@example.com")
    db_session.add(other_user)
    await db_session.flush()

    repository = APIKeyRepository(db_session)
    data = APIKeyInput(user_id=other_user.id, key_name="Other User Key")
    other_key = await repository.create(data)

    response = await client.delete(f"/api/v1/users/{authenticated_user.id}/api-keys/{other_key.id}")

    assert response.status_code == 404

    await repository.delete(api_key=other_key)
    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_api_key_unauthenticated(client: AsyncClient):
    """Test DELETE /users/{user_id}/api-keys/{api_key_id} without authentication."""
    client.headers.pop("Authorization", None)

    response = await client.delete(f"/api/v1/users/{uuid.uuid4()}/api-keys/{uuid.uuid4()}")

    assert response.status_code == 401


# Schema Tests
def test_ratelimit_per_minute():
    """Test RateLimit per_minute class method."""
    rate_limit = RateLimit.per_minute(10)
    assert rate_limit.seconds == 60
    assert rate_limit.limit == 10


def test_ratelimit_per_hour():
    """Test RateLimit per_hour class method."""
    rate_limit = RateLimit.per_hour(100)
    assert rate_limit.seconds == 3600
    assert rate_limit.limit == 100


def test_ratelimit_per_day():
    """Test RateLimit per_day class method."""
    rate_limit = RateLimit.per_day(1000)
    assert rate_limit.seconds == 86400
    assert rate_limit.limit == 1000


def test_ratelimit_custom():
    """Test RateLimit with custom seconds and limit."""
    rate_limit = RateLimit(seconds=300, limit=25)
    assert rate_limit.seconds == 300
    assert rate_limit.limit == 25


def test_attributes_default():
    """Test Attributes schema with default rate limits."""
    attributes = Attributes()
    assert len(attributes.rate_limits) == 1
    assert attributes.rate_limits[0].seconds == 86400
    assert attributes.rate_limits[0].limit == 100


def test_attributes_custom_rate_limits():
    """Test Attributes schema with custom rate limits."""
    rate_limits = [RateLimit.per_minute(10), RateLimit.per_hour(100), RateLimit.per_day(1000)]
    attributes = Attributes(rate_limits=rate_limits)
    assert len(attributes.rate_limits) == 3


def test_attributes_model_dump():
    """Test Attributes model_dump behavior."""
    attributes = Attributes(rate_limits=[RateLimit.per_day(100)])
    dumped = attributes.model_dump()
    assert "rate_limits" in dumped
    assert len(dumped["rate_limits"]) == 1


def test_apikey_input_auto_generation():
    """Test APIKeyInput automatically generates API key."""
    user_id = uuid.uuid4()
    data = APIKeyInput(key_name="Test Key", user_id=user_id)

    assert data.api_key is not None
    assert data.api_key.startswith("sdk-")
    assert len(data.api_key) > 10
    assert data.attributes is not None
    assert len(data.attributes.rate_limits) == 1


def test_apikey_input_with_provided_key():
    """Test APIKeyInput with provided API key."""
    user_id = uuid.uuid4()
    provided_key = "sdk-test_key_123"
    data = APIKeyInput(api_key=provided_key, key_name="Test Key", user_id=user_id)

    assert data.api_key == provided_key


def test_apikey_input_with_custom_attributes():
    """Test APIKeyInput with custom attributes."""
    user_id = uuid.uuid4()
    custom_attributes = Attributes(rate_limits=[RateLimit.per_hour(50), RateLimit.per_day(200)])
    data = APIKeyInput(key_name="Test Key", user_id=user_id, attributes=custom_attributes)

    assert len(data.attributes.rate_limits) == 2
    assert data.attributes.rate_limits[0].seconds == 3600
    assert data.attributes.rate_limits[0].limit == 50


def test_apikey_input_computed_fields():
    """Test APIKeyInput computed properties."""
    user_id = uuid.uuid4()
    data = APIKeyInput(key_name="Test Key", user_id=user_id)

    assert data.key_hash is not None
    assert len(data.key_hash) == 64  # SHA-256 hex digest

    assert data.key_prefix is not None
    assert data.key_prefix.startswith("sdk-...")
    assert data.key_prefix == f"sdk-...{data.api_key[-4:]}"


def test_apikey_input_model_dump_excludes_raw_key():
    """Test APIKeyInput model_dump excludes raw API key."""
    user_id = uuid.uuid4()
    data = APIKeyInput(key_name="Test Key", user_id=user_id)
    dumped = data.model_dump()

    assert "api_key" not in dumped
    assert "key_hash" in dumped
    assert "key_prefix" in dumped
    assert "key_name" in dumped
    assert "attributes" in dumped


def test_apikey_output_valid_data():
    """Test APIKeyOutput schema with valid data."""
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "key_name": "Test Key",
        "key_prefix": "sdk-...abcd",
        "created_at": datetime.utcnow(),
        "attributes": Attributes(),
    }

    output = APIKeyOutput(**data)

    assert output.key_name == "Test Key"
    assert output.key_prefix == "sdk-...abcd"
    assert output.created_at is not None
    assert output.attributes is not None


def test_apikey_output_no_sensitive_fields():
    """Test APIKeyOutput schema doesn't include sensitive fields."""
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "key_name": "Test Key",
        "key_prefix": "sdk-...abcd",
        "created_at": datetime.utcnow(),
        "attributes": Attributes(),
    }

    output = APIKeyOutput(**data)

    assert not hasattr(output, "key_hash")
    assert not hasattr(output, "api_key")
    assert not hasattr(output, "is_active")
    assert not hasattr(output, "user_id")


def test_apikey_output_missing_required_field():
    """Test APIKeyOutput schema with missing required fields."""
    with pytest.raises(ValueError):
        APIKeyOutput(id=uuid.uuid4())


def test_apikey_output_with_none_attributes():
    """Test APIKeyOutput schema with None attributes."""
    from datetime import datetime

    output = APIKeyOutput(
        id=uuid.uuid4(),
        key_name="Test Key",
        key_prefix="sdk-...abcd",
        created_at=datetime.utcnow(),
        attributes=None,
    )
    assert output.attributes is None


def test_apikey_output_first_creation_includes_api_key():
    """Test APIKeyOutputFirstCreation includes the actual API key."""
    from datetime import datetime

    output = APIKeyOutputFirstCreation(
        id=uuid.uuid4(),
        key_name="Test Key",
        key_prefix="sdk-...abcd",
        created_at=datetime.utcnow(),
        api_key="sdk-test_key_12345",
        attributes=Attributes(),
    )

    assert output.api_key == "sdk-test_key_12345"
    assert output.key_name == "Test Key"
    assert not hasattr(output, "key_hash")


def test_apikey_update_schema():
    """Test APIKeyUpdate schema validation."""
    update = APIKeyUpdate(key_name="Updated Key Name")
    assert update.key_name == "Updated Key Name"
    assert update.attributes is None

    update = APIKeyUpdate(attributes=Attributes(rate_limits=[RateLimit.per_day(500)]))
    assert update.key_name is None
    assert update.attributes.rate_limits[0].limit == 500


def test_apikey_update_full_schema():
    """Test APIKeyUpdateFull schema validation."""
    update = APIKeyUpdateFull(
        key_name="Updated Key",
        is_active=False,
        attributes=Attributes(rate_limits=[RateLimit.per_day(250)]),
    )

    assert update.key_name == "Updated Key"
    assert update.is_active is False
    assert update.attributes.rate_limits[0].limit == 250


def test_multiple_rate_limits():
    """Test schema with multiple rate limits."""
    attributes = Attributes(rate_limits=[RateLimit.per_minute(5), RateLimit.per_hour(100), RateLimit.per_day(1000)])
    user_id = uuid.uuid4()
    data = APIKeyInput(key_name="Multi-limit Key", user_id=user_id, attributes=attributes)

    assert len(data.attributes.rate_limits) == 3

    minute_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 60)
    hour_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 3600)
    day_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 86400)

    assert minute_limit.limit == 5
    assert hour_limit.limit == 100
    assert day_limit.limit == 1000


def test_empty_rate_limits():
    """Test schema with empty rate limits list."""
    attributes = Attributes(rate_limits=[])
    user_id = uuid.uuid4()
    data = APIKeyInput(key_name="No Limits Key", user_id=user_id, attributes=attributes)

    assert len(data.attributes.rate_limits) == 0

    dumped = data.model_dump()
    assert "attributes" in dumped
    assert "rate_limits" in dumped["attributes"]
    assert len(dumped["attributes"]["rate_limits"]) == 0
