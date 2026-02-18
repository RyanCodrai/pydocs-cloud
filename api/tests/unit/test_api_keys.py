import uuid

import pytest
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
from src.routes.v1.apikeys.service import APIKeyNotFound, APIKeyService


# Repository Tests - Manual cleanup since we're testing repository directly
@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_create(db_session: AsyncSession):
    """Test creating an API key via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Test API Key", is_active=True)

    api_key = await repository.create(data)

    assert api_key.user_id == user.id
    assert api_key.key_name == "Test API Key"
    assert api_key.is_active is True
    assert api_key.id is not None
    assert api_key.key_hash is not None
    assert api_key.key_prefix is not None
    # Test new attributes field - it comes back as a dict from database
    assert api_key.attributes is not None
    assert isinstance(api_key.attributes, dict)
    assert "rate_limits" in api_key.attributes
    assert len(api_key.attributes["rate_limits"]) == 1
    assert api_key.attributes["rate_limits"][0]["seconds"] == 86400  # 1 day
    assert api_key.attributes["rate_limits"][0]["limit"] == 100

    # Cleanup
    await repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_create_with_custom_attributes(db_session: AsyncSession):
    """Test creating an API key with custom rate limits via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create custom attributes with multiple rate limits
    custom_attributes = Attributes(rate_limits=[RateLimit.per_hour(50), RateLimit.per_day(500)])

    data = APIKeyInput(user_id=user.id, key_name="Custom Rate Limits Key", is_active=True, attributes=custom_attributes)

    api_key = await repository.create(data)

    assert api_key.user_id == user.id
    assert api_key.key_name == "Custom Rate Limits Key"
    assert api_key.attributes is not None
    assert "rate_limits" in api_key.attributes
    assert len(api_key.attributes["rate_limits"]) == 2

    # Verify the rate limits
    rate_limits = api_key.attributes["rate_limits"]
    assert any(rl["seconds"] == 3600 and rl["limit"] == 50 for rl in rate_limits)  # hourly
    assert any(rl["seconds"] == 86400 and rl["limit"] == 500 for rl in rate_limits)  # daily

    # Cleanup
    await repository.delete(api_key=api_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve(db_session: AsyncSession):
    """Test retrieving an API key by ID via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Retrieve Test", is_active=True)

    created_key = await repository.create(data)
    retrieved_key = await repository.retrieve(api_key_id=created_key.id)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_name == "Retrieve Test"
    assert retrieved_key.user_id == user.id
    assert retrieved_key.attributes is not None
    assert isinstance(retrieved_key.attributes, dict)
    assert "rate_limits" in retrieved_key.attributes

    # Cleanup
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

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Hash Test", is_active=True)

    created_key = await repository.create(data)
    retrieved_key = await repository.retrieve_by_hash(key_hash=data.key_hash)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_hash == data.key_hash

    # Cleanup
    await repository.delete(api_key=created_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_hash_nonexistent(db_session: AsyncSession):
    """Test retrieving API key by non-existent hash raises NoResultFound."""
    repository = APIKeyRepository(db_session)
    fake_hash = "nonexistent_hash"

    with pytest.raises(NoResultFound):
        await repository.retrieve_by_hash(key_hash=fake_hash)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_hash_inactive(db_session: AsyncSession):
    """Test retrieving inactive API key by hash raises NoResultFound."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(
        user_id=user.id,
        key_name="Inactive Test",
        is_active=False,  # Create as inactive
    )

    created_key = await repository.create(data)

    # Should not find inactive key
    with pytest.raises(NoResultFound):
        await repository.retrieve_by_hash(key_hash=data.key_hash)

    # Cleanup
    await repository.delete(api_key=created_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_retrieve_by_user(db_session: AsyncSession):
    """Test retrieving API keys by user ID via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    # Create multiple API keys for the user
    data1 = APIKeyInput(user_id=user.id, key_name="Key 1", is_active=True)
    data2 = APIKeyInput(user_id=user.id, key_name="Key 2", is_active=True)
    data3 = APIKeyInput(user_id=user.id, key_name="Key 3", is_active=False)

    key1 = await repository.create(data1)
    key2 = await repository.create(data2)
    key3 = await repository.create(data3)

    # Test retrieving only active keys
    active_keys = await repository.retrieve_by_user(user_id=user.id, include_inactive=False)
    assert len(active_keys) == 2
    assert all(key.is_active for key in active_keys)
    assert all(key.attributes is not None for key in active_keys)

    # Test retrieving all keys
    all_keys = await repository.retrieve_by_user(user_id=user.id, include_inactive=True)
    assert len(all_keys) == 3

    # Cleanup
    await repository.delete(api_key=key1)
    await repository.delete(api_key=key2)
    await repository.delete(api_key=key3)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_update(db_session: AsyncSession):
    """Test updating an API key via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Original Name", is_active=True)

    api_key = await repository.create(data)
    assert api_key.is_active is True

    # Update the API key using APIKeyUpdateFull
    update_data = APIKeyUpdateFull(is_active=False)
    updated_key = await repository.update(api_key=api_key, data=update_data)

    assert updated_key.is_active is False
    assert updated_key.id == api_key.id
    # Attributes should remain unchanged
    assert updated_key.attributes == api_key.attributes

    # Cleanup
    await repository.delete(api_key=updated_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_update_attributes(db_session: AsyncSession):
    """Test updating an API key's attributes via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Attributes Test", is_active=True)

    api_key = await repository.create(data)
    original_attributes = api_key.attributes

    # Update with new attributes
    new_attributes = Attributes(rate_limits=[RateLimit.per_day(200)])
    update_data = APIKeyUpdateFull(attributes=new_attributes)
    updated_key = await repository.update(api_key=api_key, data=update_data)

    assert updated_key.attributes != original_attributes
    assert updated_key.attributes["rate_limits"][0]["limit"] == 200

    # Cleanup
    await repository.delete(api_key=updated_key)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_repository_delete(db_session: AsyncSession):
    """Test deleting an API key via repository."""
    repository = APIKeyRepository(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    data = APIKeyInput(user_id=user.id, key_name="Delete Test", is_active=True)

    api_key = await repository.create(data)
    result = await repository.delete(api_key=api_key)

    assert result is True

    # Verify API key is actually deleted
    with pytest.raises(NoResultFound):
        await repository.retrieve(api_key_id=api_key.id)

    # Cleanup user only (API key was already deleted by the test)
    await db_session.delete(user)
    await db_session.commit()


# Service Tests - Use authenticated_user fixture where possible, manual cleanup for create tests
@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_create(db_session: AsyncSession):
    """Test creating an API key via service."""
    service = APIKeyService(db_session)

    # Create a test user first
    user = DBUser(email_address=f"test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    await db_session.flush()

    result = await service.create(user_id=user.id, key_name="Service Test")

    assert isinstance(result, APIKeyOutputFirstCreation)
    assert result.key_name == "Service Test"
    assert result.user_id == user.id
    assert result.api_key is not None
    assert result.api_key.startswith("PD-")
    assert result.key_prefix is not None
    assert result.id is not None
    assert result.created_at is not None
    # Test attributes is present
    assert result.attributes is not None
    assert result.attributes.rate_limits is not None
    assert len(result.attributes.rate_limits) == 1
    assert result.attributes.rate_limits[0].seconds == 86400
    assert result.attributes.rate_limits[0].limit == 100

    # Hard delete cleanup using service
    await service.delete(api_key_id=result.id, permanent=True)
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving an API key by ID via service."""
    service = APIKeyService(db_session)

    # Create API key via repository to get the ID
    data = APIKeyInput(user_id=authenticated_user.id, key_name="Retrieve Test", is_active=True)
    repository = APIKeyRepository(db_session)
    created_key = await repository.create(data)

    retrieved_key = await service.retrieve(api_key_id=created_key.id)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_name == "Retrieve Test"
    assert retrieved_key.attributes is not None
    assert retrieved_key.attributes.rate_limits is not None

    # Cleanup API key (user will be cleaned up by fixture)
    await repository.delete(api_key=created_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_nonexistent_raises_exception(db_session: AsyncSession):
    """Test retrieving non-existent API key raises APIKeyNotFound."""
    service = APIKeyService(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(APIKeyNotFound) as exc_info:
        await service.retrieve(api_key_id=fake_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "API key not found"


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_hash(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving an API key by hash via service."""
    service = APIKeyService(db_session)

    # Create API key via repository to have it in database
    data = APIKeyInput(user_id=authenticated_user.id, key_name="Hash Test", is_active=True)
    repository = APIKeyRepository(db_session)
    created_key = await repository.create(data)

    # Test retrieving by the raw API key
    retrieved_key = await service.retrieve_by_hash(api_key=data.api_key)

    assert retrieved_key.id == created_key.id
    assert retrieved_key.key_hash == data.key_hash

    # Cleanup API key (user will be cleaned up by fixture)
    await repository.delete(api_key=created_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_hash_nonexistent_raises_exception(db_session: AsyncSession):
    """Test retrieving API key by non-existent hash raises APIKeyNotFound."""
    service = APIKeyService(db_session)
    fake_key = "PD-fake_key_that_does_not_exist"

    with pytest.raises(APIKeyNotFound) as exc_info:
        await service.retrieve_by_hash(api_key=fake_key)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "API key not found"


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_retrieve_by_user(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving API keys by user via service."""
    service = APIKeyService(db_session)

    # Create API keys via repository
    repository = APIKeyRepository(db_session)
    data1 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 1", is_active=True)
    data2 = APIKeyInput(user_id=authenticated_user.id, key_name="Key 2", is_active=True)

    key1 = await repository.create(data1)
    key2 = await repository.create(data2)

    # Test service retrieval
    results = await service.retrieve_by_user(user_id=authenticated_user.id, include_inactive=False)

    assert len(results) == 2
    assert all(isinstance(result, APIKeyOutput) for result in results)
    assert all(result.user_id == authenticated_user.id for result in results)
    assert all(result.attributes is not None for result in results)

    # Cleanup API keys (user will be cleaned up by fixture)
    await repository.delete(api_key=key1)
    await repository.delete(api_key=key2)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_deactivate(authenticated_user: DBUser, db_session: AsyncSession):
    """Test deactivating an API key via service."""
    service = APIKeyService(db_session)

    # Create API key via repository
    repository = APIKeyRepository(db_session)
    data = APIKeyInput(user_id=authenticated_user.id, key_name="Deactivate Test", is_active=True)
    created_key = await repository.create(data)

    # Deactivate via service
    result = await service.delete(api_key_id=created_key.id)

    assert result is True

    # Verify the key was deactivated (soft deleted)
    updated_key = await repository.retrieve(api_key_id=created_key.id, include_inactive=True)
    assert updated_key.is_active is False

    # Hard delete cleanup for test cleanup
    await repository.delete(api_key=updated_key)


@pytest.mark.asyncio(loop_scope="function")
async def test_apikey_service_deactivate_nonexistent_raises_exception(db_session: AsyncSession):
    """Test deactivating non-existent API key raises APIKeyNotFound."""
    service = APIKeyService(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(APIKeyNotFound) as exc_info:
        await service.delete(api_key_id=fake_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "API key not found"



# Schema Tests (synchronous)
def test_ratelimit_schema_per_minute():
    """Test RateLimit per_minute class method."""
    rate_limit = RateLimit.per_minute(10)

    assert rate_limit.seconds == 60
    assert rate_limit.limit == 10


def test_ratelimit_schema_per_hour():
    """Test RateLimit per_hour class method."""
    rate_limit = RateLimit.per_hour(100)

    assert rate_limit.seconds == 3600
    assert rate_limit.limit == 100


def test_ratelimit_schema_per_day():
    """Test RateLimit per_day class method."""
    rate_limit = RateLimit.per_day(1000)

    assert rate_limit.seconds == 86400
    assert rate_limit.limit == 1000


def test_ratelimit_schema_custom():
    """Test RateLimit with custom seconds and limit."""
    rate_limit = RateLimit(seconds=300, limit=25)  # 5 minutes, 25 requests

    assert rate_limit.seconds == 300
    assert rate_limit.limit == 25


def test_attributes_schema_default():
    """Test Attributes schema with default rate limits."""
    attributes = Attributes()

    assert len(attributes.rate_limits) == 1
    assert attributes.rate_limits[0].seconds == 86400
    assert attributes.rate_limits[0].limit == 100


def test_attributes_schema_custom_rate_limits():
    """Test Attributes schema with custom rate limits."""
    rate_limits = [RateLimit.per_minute(10), RateLimit.per_hour(100), RateLimit.per_day(1000)]
    attributes = Attributes(rate_limits=rate_limits)

    assert len(attributes.rate_limits) == 3
    assert attributes.rate_limits[0].seconds == 60
    assert attributes.rate_limits[0].limit == 10
    assert attributes.rate_limits[1].seconds == 3600
    assert attributes.rate_limits[1].limit == 100
    assert attributes.rate_limits[2].seconds == 86400
    assert attributes.rate_limits[2].limit == 1000


def test_attributes_schema_model_dump():
    """Test Attributes model_dump behavior."""
    # Test with explicitly set rate_limits (not relying on default)
    attributes = Attributes(rate_limits=[RateLimit.per_day(100)])
    dumped = attributes.model_dump()

    assert "rate_limits" in dumped
    assert len(dumped["rate_limits"]) == 1
    assert dumped["rate_limits"][0]["seconds"] == 86400
    assert dumped["rate_limits"][0]["limit"] == 100


def test_apikey_input_schema_auto_generation():
    """Test APIKeyInput automatically generates API key."""
    data = APIKeyInput(key_name="Test Key")

    assert data.api_key is not None
    assert data.api_key.startswith("PD-")
    assert len(data.api_key) > 10  # Should be substantial length
    # Test default attributes
    assert data.attributes is not None
    assert len(data.attributes.rate_limits) == 1
    assert data.attributes.rate_limits[0].seconds == 86400
    assert data.attributes.rate_limits[0].limit == 100


def test_apikey_input_schema_with_provided_key():
    """Test APIKeyInput with provided API key."""
    provided_key = "PD-test_key_123"
    data = APIKeyInput(api_key=provided_key, key_name="Test Key")

    assert data.api_key == provided_key


def test_apikey_input_schema_with_custom_attributes():
    """Test APIKeyInput with custom attributes."""
    custom_attributes = Attributes(rate_limits=[RateLimit.per_hour(50), RateLimit.per_day(200)])
    data = APIKeyInput(key_name="Test Key", attributes=custom_attributes)

    assert data.attributes is not None
    assert len(data.attributes.rate_limits) == 2
    assert data.attributes.rate_limits[0].seconds == 3600
    assert data.attributes.rate_limits[0].limit == 50
    assert data.attributes.rate_limits[1].seconds == 86400
    assert data.attributes.rate_limits[1].limit == 200


def test_apikey_input_schema_properties():
    """Test APIKeyInput computed properties."""
    data = APIKeyInput(key_name="Test Key")

    # Test key_hash property
    assert data.key_hash is not None
    assert len(data.key_hash) == 64  # SHA-256 hash length

    # Test key_prefix property
    assert data.key_prefix is not None
    assert data.key_prefix.endswith("...")
    assert len(data.key_prefix) == 13  # 10 chars + "..."


def test_apikey_input_schema_model_dump_excludes_raw_key():
    """Test APIKeyInput model_dump excludes raw API key by default."""
    data = APIKeyInput(key_name="Test Key")
    dumped = data.model_dump()

    assert "api_key" not in dumped
    assert "key_hash" in dumped  # Your current implementation includes this
    assert "key_prefix" in dumped
    assert "key_name" in dumped
    assert "attributes" in dumped
    assert "rate_limits" in dumped["attributes"]


def test_apikey_input_schema_model_dump_includes_raw_key_when_excluded_empty():
    """Test APIKeyInput model_dump includes raw API key when exclude is empty."""
    data = APIKeyInput(key_name="Test Key")
    dumped = data.model_dump(exclude={})

    assert "api_key" in dumped
    assert "key_hash" in dumped
    assert "key_prefix" in dumped
    assert "key_name" in dumped
    assert "attributes" in dumped


def test_apikey_input_schema_model_dump_excludes_sensitive_data():
    """Test APIKeyInput model_dump excludes sensitive data by default."""
    data = APIKeyInput(key_name="Test Key")
    dumped = data.model_dump()

    assert "api_key" not in dumped  # Raw key should be excluded
    assert "key_hash" in dumped  # Your implementation includes this by default
    assert "key_prefix" in dumped  # Prefix is OK to show
    assert "key_name" in dumped  # Name is OK to show
    assert "attributes" in dumped  # Attributes is OK to show


def test_apikey_output_schema_valid_data():
    """Test APIKeyOutput schema with valid data."""
    api_key_id = uuid.uuid4()
    user_id = uuid.uuid4()
    from datetime import datetime

    attributes = Attributes(rate_limits=[RateLimit.per_day(100)])

    data = {
        "id": api_key_id,
        "user_id": user_id,
        "key_name": "Test Key",
        "key_prefix": "PD-abc123...",
        "created_at": datetime.utcnow(),
        "attributes": attributes,
    }

    output = APIKeyOutput(**data)

    assert output.id == api_key_id
    assert output.user_id == user_id
    assert output.key_name == "Test Key"
    assert output.key_prefix == "PD-abc123..."
    assert output.created_at is not None
    assert output.attributes is not None
    assert len(output.attributes.rate_limits) == 1


def test_apikey_output_schema_no_sensitive_fields():
    """Test APIKeyOutput schema doesn't include sensitive fields."""
    api_key_id = uuid.uuid4()
    user_id = uuid.uuid4()
    from datetime import datetime

    attributes = Attributes()

    data = {
        "id": api_key_id,
        "user_id": user_id,
        "key_name": "Test Key",
        "key_prefix": "PD-abc123...",
        "created_at": datetime.utcnow(),
        "attributes": attributes,
    }

    output = APIKeyOutput(**data)

    # Verify sensitive fields are not accessible
    assert not hasattr(output, "key_hash")
    assert not hasattr(output, "api_key")
    assert not hasattr(output, "is_active")
    assert not hasattr(output, "updated_at")


def test_apikey_output_schema_missing_required_field():
    """Test APIKeyOutput schema with missing required fields."""
    with pytest.raises(ValueError):
        APIKeyOutput(id=uuid.uuid4())  # Missing other required fields


def test_apikey_output_schema_with_none_attributes():
    """Test APIKeyOutput schema with None attributes."""
    api_key_id = uuid.uuid4()
    user_id = uuid.uuid4()
    from datetime import datetime

    data = {
        "id": api_key_id,
        "user_id": user_id,
        "key_name": "Test Key",
        "key_prefix": "PD-abc123...",
        "created_at": datetime.utcnow(),
        "attributes": None,
    }

    output = APIKeyOutput(**data)
    assert output.attributes is None


def test_apikey_output_first_creation_includes_api_key():
    """Test APIKeyOutputFirstCreation includes the actual API key."""
    api_key_id = uuid.uuid4()
    user_id = uuid.uuid4()
    from datetime import datetime

    attributes = Attributes()

    data = {
        "id": api_key_id,
        "user_id": user_id,
        "key_name": "Test Key",
        "key_prefix": "PD-abc123...",
        "created_at": datetime.utcnow(),
        "api_key": "PD-test_key_12345",
        "attributes": attributes,
    }

    output = APIKeyOutputFirstCreation(**data)

    assert output.id == api_key_id
    assert output.user_id == user_id
    assert output.key_name == "Test Key"
    assert output.api_key == "PD-test_key_12345"
    assert output.attributes is not None
    assert len(output.attributes.rate_limits) == 1
    assert not hasattr(output, "key_hash")  # Should not have sensitive fields


def test_apikey_update_schema():
    """Test APIKeyUpdate schema validation."""
    # Test with key_name only
    update = APIKeyUpdate(key_name="Updated Key Name")
    assert update.key_name == "Updated Key Name"
    assert update.attributes is None

    # Test with attributes only
    new_attributes = Attributes(rate_limits=[RateLimit.per_day(500)])
    update = APIKeyUpdate(attributes=new_attributes)
    assert update.key_name is None
    assert update.attributes is not None
    assert update.attributes.rate_limits[0].limit == 500

    # Test with both
    update = APIKeyUpdate(key_name="Updated Key", attributes=Attributes(rate_limits=[RateLimit.per_hour(25)]))
    assert update.key_name == "Updated Key"
    assert update.attributes.rate_limits[0].seconds == 3600
    assert update.attributes.rate_limits[0].limit == 25


def test_apikey_update_full_schema():
    """Test APIKeyUpdateFull schema validation."""
    update = APIKeyUpdateFull(
        key_name="Updated Key", is_active=False, attributes=Attributes(rate_limits=[RateLimit.per_day(250)])
    )

    assert update.key_name == "Updated Key"
    assert update.is_active is False
    assert update.attributes is not None
    assert update.attributes.rate_limits[0].limit == 250


def test_multiple_rate_limits_schema():
    """Test schema with multiple rate limits."""
    attributes = Attributes(rate_limits=[RateLimit.per_minute(5), RateLimit.per_hour(100), RateLimit.per_day(1000)])

    data = APIKeyInput(key_name="Multi-limit Key", attributes=attributes)

    assert len(data.attributes.rate_limits) == 3

    # Verify each rate limit
    minute_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 60)
    hour_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 3600)
    day_limit = next(rl for rl in data.attributes.rate_limits if rl.seconds == 86400)

    assert minute_limit.limit == 5
    assert hour_limit.limit == 100
    assert day_limit.limit == 1000


def test_empty_rate_limits_schema():
    """Test schema with empty rate limits list."""
    attributes = Attributes(rate_limits=[])
    data = APIKeyInput(key_name="No Limits Key", attributes=attributes)

    assert len(data.attributes.rate_limits) == 0

    # Should still serialize properly
    dumped = data.model_dump()
    assert "attributes" in dumped
    assert "rate_limits" in dumped["attributes"]
    assert len(dumped["attributes"]["rate_limits"]) == 0
