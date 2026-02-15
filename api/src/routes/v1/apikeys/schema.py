import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    api_key: str = Field(default_factory=lambda: f"pydocs-{secrets.token_urlsafe(32)}")
    key_name: str
    user_id: UUID
    is_active: bool = True
    attributes: Attributes = Attributes()

    @property
    def key_hash(self) -> str:
        return hashlib.sha256(self.api_key.encode()).hexdigest()

    @property
    def key_prefix(self) -> str:
        return f"pydocs-...{self.api_key[-4:]}"

    def model_dump(self, *args, exclude: set = {"api_key"}, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["key_hash"] = self.key_hash
        data["key_prefix"] = self.key_prefix
        for field_name in exclude:
            data.pop(field_name, None)
        return data


class APIKeyUpdate(BaseModel):
    """Input schema for creating and updating API keys."""

    key_name: Optional[str] = None
    attributes: Optional[Attributes] = None


class APIKeyUpdateFull(APIKeyUpdate):
    """Input schema for creating and updating API keys."""

    is_active: Optional[bool] = None


class APIKeyOutput(BaseModel):
    """Output schema for API key responses."""

    id: UUID
    user_id: UUID
    key_name: str
    key_prefix: str
    created_at: datetime
    attributes: Optional[Attributes] = None


class APIKeyOutputFirstCreation(APIKeyOutput):
    api_key: str
