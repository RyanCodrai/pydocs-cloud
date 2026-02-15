import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class RateLimit(BaseModel):
    seconds: int
    limit: int

    @classmethod
    def per_minute(cls, limit: int) -> "RateLimit":
        return cls(seconds=60, limit=limit)

    @classmethod
    def per_hour(cls, limit: int) -> "RateLimit":
        return cls(seconds=3600, limit=limit)

    @classmethod
    def per_day(cls, limit: int) -> "RateLimit":
        return cls(seconds=86400, limit=limit)


class Attributes(BaseModel):
    rate_limits: list[RateLimit] = Field(default_factory=lambda: [RateLimit.per_day(limit=100)])

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump(*args, **kwargs)


class APIKeyInput(BaseModel):
    api_key: str = Field(default_factory=lambda: f"sdk-{secrets.token_urlsafe(32)}", exclude=True)
    key_name: str
    user_id: UUID
    is_active: bool = True
    attributes: Attributes = Attributes()

    @computed_field
    @property
    def key_hash(self) -> str:
        return hashlib.sha256(self.api_key.encode()).hexdigest()

    @computed_field
    @property
    def key_prefix(self) -> str:
        return f"sdk-...{self.api_key[-4:]}"


class APIKeyUpdate(BaseModel):
    key_name: Optional[str] = None
    attributes: Optional[Attributes] = None


class APIKeyUpdateFull(APIKeyUpdate):
    is_active: Optional[bool] = None


class APIKeyOutput(BaseModel):
    id: UUID
    key_name: str
    key_prefix: str
    created_at: datetime
    attributes: Optional[Attributes] = None


class APIKeyOutputFirstCreation(APIKeyOutput):
    api_key: str
