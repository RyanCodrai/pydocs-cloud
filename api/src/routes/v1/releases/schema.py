"""Schema definitions for release webhook data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def parse_iso_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Release(BaseModel):
    id: str  # UUID from GENERATE_UUID()
    ecosystem: str  # Always 'pypi' for now
    name: str  # Package name
    version: str  # Version string (e.g., "1.0.0")
    description: str | None  # Package description
    home_page: str | None  # Homepage URL
    project_urls: str | None  # JSON string of project URLs
    timestamp: Annotated[datetime, BeforeValidator(parse_iso_timestamp)]  # Uploaded timestamp


class ReleaseInput(BaseModel):
    ecosystem: str
    package_name: str
    version: str
    first_seen: datetime
    last_seen: datetime

    @classmethod
    def from_release(cls, release: "Release") -> "ReleaseInput":
        return cls(
            ecosystem=release.ecosystem,
            package_name=release.name,
            version=release.version,
            first_seen=release.timestamp,
            last_seen=release.timestamp,
        )
