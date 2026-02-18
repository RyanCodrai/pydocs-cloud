import uuid

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBUser
from src.routes.v1.users.repository import UserRepository
from src.routes.v1.users.schema import UserInput, UserOutput
from src.routes.v1.users.service import UserAlreadyExists, UserNotFound, UserService


# Repository Tests - Manual cleanup since we're testing repository directly
@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_create(db_session: AsyncSession):
    """Test creating a user via repository."""
    repository = UserRepository(db_session)
    email = f"test-{uuid.uuid4()}@example.com"

    user = await repository.create(email_address=email)

    assert user.email_address == email
    assert user.id is not None
    assert user.is_active is True

    # Cleanup
    await repository.delete(user=user)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_create_duplicate_email(db_session: AsyncSession):
    """Test creating users with duplicate emails raises IntegrityError."""
    repository = UserRepository(db_session)
    email = f"duplicate-{uuid.uuid4()}@example.com"

    # Create first user
    user1 = await repository.create(email_address=email)

    # Attempt to create second user with same email should raise IntegrityError
    with pytest.raises(IntegrityError):
        await repository.create(email_address=email)

    # Rollback the session after the IntegrityError to reset its state
    await db_session.rollback()

    # Cleanup - only need to clean up the first user since second one failed
    await repository.delete(user=user1)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_retrieve(db_session: AsyncSession):
    """Test retrieving a user by ID via repository."""
    repository = UserRepository(db_session)
    email = f"retrieve-{uuid.uuid4()}@example.com"

    created_user = await repository.create(email_address=email)
    retrieved_user = await repository.retrieve(user_id=created_user.id)

    assert retrieved_user.id == created_user.id
    assert retrieved_user.email_address == email

    # Cleanup
    await repository.delete(user=created_user)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_retrieve_nonexistent(db_session: AsyncSession):
    """Test retrieving non-existent user raises NoResultFound."""
    repository = UserRepository(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(NoResultFound):
        await repository.retrieve(user_id=fake_id)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_retrieve_by_email(db_session: AsyncSession):
    """Test retrieving a user by email via repository."""
    repository = UserRepository(db_session)
    email = f"email-lookup-{uuid.uuid4()}@example.com"

    created_user = await repository.create(email_address=email)
    retrieved_user = await repository.retrieve_by_email(email_address=email)

    assert retrieved_user.id == created_user.id
    assert retrieved_user.email_address == email

    # Cleanup
    await repository.delete(user=created_user)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_retrieve_by_email_nonexistent(db_session: AsyncSession):
    """Test retrieving user by non-existent email raises NoResultFound."""
    repository = UserRepository(db_session)

    with pytest.raises(NoResultFound):
        await repository.retrieve_by_email(email_address=f"nonexistent-{uuid.uuid4()}@example.com")


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_update(db_session: AsyncSession):
    """Test updating a user via repository."""
    repository = UserRepository(db_session)
    email = f"update-{uuid.uuid4()}@example.com"

    user = await repository.create(email_address=email)
    assert user.is_active is True

    # Update user to inactive
    update_data = UserInput(is_active=False)
    updated_user = await repository.update(user=user, data=update_data)

    assert updated_user.is_active is False
    assert updated_user.id == user.id

    # Cleanup
    await repository.delete(user=updated_user)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_repository_delete(db_session: AsyncSession):
    """Test deleting a user via repository."""
    repository = UserRepository(db_session)
    email = f"delete-{uuid.uuid4()}@example.com"

    user = await repository.create(email_address=email)
    result = await repository.delete(user=user)

    assert result is True

    # Verify user is actually deleted
    with pytest.raises(NoResultFound):
        await repository.retrieve(user_id=user.id)

    # No cleanup needed - user was deleted by the test


# Service Tests - Use authenticated_user fixture where possible, manual cleanup for create tests
@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_create(db_session: AsyncSession):
    """Test creating a user via service."""
    service = UserService(db_session)
    email = f"service-create-{uuid.uuid4()}@example.com"

    user = await service.create(email_address=email)

    assert user.email_address == email
    assert user.id is not None
    assert user.is_active is True

    # Manual cleanup since we're testing the create method
    await service.delete(user_id=user.id, permanent=True)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_create_duplicate_raises_exception(db_session: AsyncSession):
    """Test creating duplicate user raises UserAlreadyExists."""
    service = UserService(db_session)
    email = f"duplicate-service-{uuid.uuid4()}@example.com"

    # Create first user
    user1 = await service.create(email_address=email)
    user1_id = user1.id  # Store the ID before rollback

    # Attempt to create duplicate should raise UserAlreadyExists
    with pytest.raises(UserAlreadyExists) as exc_info:
        await service.create(email_address=email)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "User already exists"

    # Rollback the session after the UserAlreadyExists exception to reset its state
    await db_session.rollback()

    # Cleanup - only need to clean up the first user since second one failed
    await service.delete(user_id=user1_id, permanent=True)


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_retrieve(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving a user by ID via service."""
    service = UserService(db_session)

    retrieved_user = await service.retrieve(user_id=authenticated_user.id)

    assert retrieved_user.id == authenticated_user.id
    assert retrieved_user.email_address == authenticated_user.email_address


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_retrieve_nonexistent_raises_exception(db_session: AsyncSession):
    """Test retrieving non-existent user raises UserNotFound."""
    service = UserService(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(UserNotFound) as exc_info:
        await service.retrieve(user_id=fake_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_retrieve_by_email(authenticated_user: DBUser, db_session: AsyncSession):
    """Test retrieving a user by email via service."""
    service = UserService(db_session)

    retrieved_user = await service.retrieve_by_email(email_address=authenticated_user.email_address)

    assert retrieved_user.id == authenticated_user.id
    assert retrieved_user.email_address == authenticated_user.email_address


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_retrieve_by_email_nonexistent_raises_exception(db_session: AsyncSession):
    """Test retrieving user by non-existent email raises UserNotFound."""
    service = UserService(db_session)

    with pytest.raises(UserNotFound) as exc_info:
        await service.retrieve_by_email(email_address=f"nonexistent-service-{uuid.uuid4()}@example.com")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_update(authenticated_user: DBUser, db_session: AsyncSession):
    """Test updating a user via service."""
    service = UserService(db_session)
    assert authenticated_user.is_active is True

    # Update user to inactive
    update_data = UserInput(is_active=False)
    updated_user = await service.update(user_id=authenticated_user.id, data=update_data)

    assert updated_user.is_active is False
    assert updated_user.id == authenticated_user.id


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_update_nonexistent_user_raises_exception(db_session: AsyncSession):
    """Test updating non-existent user raises UserNotFound."""
    service = UserService(db_session)
    fake_id = uuid.uuid4()
    update_data = UserInput(is_active=False)

    with pytest.raises(UserNotFound) as exc_info:
        await service.update(user_id=fake_id, data=update_data)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_delete(authenticated_user: DBUser, db_session: AsyncSession):
    """Test soft deleting a user via service."""
    service = UserService(db_session)
    assert authenticated_user.is_active is True

    result = await service.delete(user_id=authenticated_user.id)

    assert result is True

    # Verify user is soft deleted (inactive) not hard deleted
    updated_user = await service.retrieve(user_id=authenticated_user.id)
    assert updated_user.is_active is False


@pytest.mark.asyncio(loop_scope="function")
async def test_user_service_delete_nonexistent_user_raises_exception(db_session: AsyncSession):
    """Test deleting non-existent user raises UserNotFound."""
    service = UserService(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(UserNotFound) as exc_info:
        await service.delete(user_id=fake_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


# Schema Tests (these are synchronous, no asyncio decorator needed)
def test_user_input_schema_valid_data():
    """Test UserInput schema with valid data."""
    data = {"is_active": True}
    user_input = UserInput(**data)

    assert user_input.is_active is True


def test_user_input_schema_empty_data():
    """Test UserInput schema with empty data (all optional)."""
    user_input = UserInput()

    assert user_input.is_active is None


def test_user_input_schema_invalid_type():
    """Test UserInput schema with invalid data type."""
    with pytest.raises(ValueError):
        UserInput(is_active="not_a_boolean")


def test_user_output_schema_valid_data():
    """Test UserOutput schema with valid data."""
    user_id = uuid.uuid4()
    data = {"id": user_id, "email_address": "test@example.com"}
    user_output = UserOutput(**data)

    assert user_output.id == user_id
    assert user_output.email_address == "test@example.com"


def test_user_output_schema_missing_required_field():
    """Test UserOutput schema with missing required fields."""
    with pytest.raises(ValueError):
        UserOutput(id=uuid.uuid4())  # Missing email_address

    with pytest.raises(ValueError):
        UserOutput(email_address="test@example.com")  # Missing id
