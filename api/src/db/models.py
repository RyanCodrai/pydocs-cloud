from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class DBRelease(SQLModel, table=True):
    __tablename__ = "releases"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ecosystem: str
    package_name: str
    version: str
    first_seen: datetime = Field(index=True)  # When we first saw this version
    last_seen: datetime = Field(index=True)  # Most recent time we saw this version

    __table_args__ = (UniqueConstraint("ecosystem", "package_name", "version", name="unique_release"),)


class DBPackage(SQLModel, table=True):
    __tablename__ = "packages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ecosystem: str
    package_name: str
    description: str | None = Field(default=None)
    home_page: str | None = Field(default=None)
    project_urls: dict[str, str] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    source_code: str | None = Field(default=None)
    first_seen: datetime | None = Field(default=None, index=True)
    last_seen: datetime | None = Field(default=None, index=True)

    __table_args__ = (UniqueConstraint("ecosystem", "package_name", name="unique_package"),)


class DBCommitCache(SQLModel, table=True):
    __tablename__ = "commit_cache"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    github_url: str
    timestamp: datetime
    commit_sha: str
    __table_args__ = (UniqueConstraint("github_url", "timestamp", name="unique_commit_cache"),)


class DBKvStore(SQLModel, table=True):
    __tablename__ = "kv_store"

    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DBUser(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email_address: str = Field(unique=True, index=True)
    github_token: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, index=True, sa_column_kwargs={"onupdate": datetime.utcnow}
    )


class DBAPIKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    key_name: str
    key_prefix: str
    key_hash: str
    is_active: bool = Field(default=True)
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    __table_args__ = (Index("ix_api_keys_key_hash_is_active", "key_hash", "is_active"),)


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
