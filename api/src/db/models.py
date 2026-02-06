from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


# class DBUser(SQLModel, table=True):
#     __tablename__ = "users"
#     id: UUID = Field(default_factory=uuid4, primary_key=True)
#     email_address: str = Field(unique=True, index=True)
#     is_active: bool = Field(default=False)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


# class DBAPIKey(SQLModel, table=True):
#     __tablename__ = "api_keys"
#     id: UUID = Field(default_factory=uuid4, primary_key=True)
#     user_id: UUID = Field(foreign_key="users.id", index=True)
#     key_name: str  # User-friendly name like "Production API", "Dev Testing"
#     key_prefix: str  # e.g. "api_12xr2" - first 8-10 chars for display
#     key_hash: str = Field(index=True)  # Store hashed version of full key
#     is_active: bool = Field(default=True)
#     attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


# class DBQueryHistory(SQLModel, table=True):
#     __tablename__ = "queries"
#     id: UUID = Field(default_factory=uuid4, primary_key=True)
#     user_id: UUID = Field(foreign_key="users.id", index=True)
#     api_key_id: UUID | None = Field(default=None, foreign_key="api_keys.id", index=True)  # Nullable API key reference
#     query_text: str
#     packages_detected: list = Field(default_factory=list, sa_column=Column(JSON))  # JSON array of detected packages
#     credits_consumed: int = Field(default=1)
#     created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
#     updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class DBRelease(SQLModel, table=True):
    __tablename__ = "releases"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ecosystem: str = Field(index=True)
    package_name: str = Field(index=True)
    version: str
    first_seen: datetime  # When we first saw this version
    last_seen: datetime  # Most recent time we saw this version

    # Composite unique constraint acts as logical primary key
    __table_args__ = (UniqueConstraint("ecosystem", "package_name", "version", name="unique_release"),)


class DBPackage(SQLModel, table=True):
    __tablename__ = "packages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ecosystem: str = Field(index=True)
    package_name: str = Field(index=True)
    description: str | None = Field(default=None)
    home_page: str | None = Field(default=None)
    project_urls: dict[str, str] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    source_code: str | None = Field(default=None)
    first_seen: datetime
    last_seen: datetime
    # GitHub URL extraction pipeline fields
    source_code_candidates: list[str] = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )

    __table_args__ = (UniqueConstraint("ecosystem", "package_name", name="unique_package"),)


class DBSyncState(SQLModel, table=True):
    __tablename__ = "sync_state"

    key: str = Field(primary_key=True)  # e.g. "npm_changes_last_seq"
    value: str  # The stored state value (e.g. a sequence number)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
