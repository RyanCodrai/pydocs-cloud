"""Schema definitions for webhook payloads."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def parse_timestamp(value: str | datetime) -> datetime:
    """Parse ISO timestamp to timezone-naive datetime."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


class ReleaseWebhookPayload(BaseModel):
    id: str  # UUID from GENERATE_UUID()
    ecosystem: str  # Always 'pypi' for now
    name: str  # Package name
    version: str  # Version string (e.g., "1.0.0")
    description: str | None  # Package description
    home_page: str | None  # Homepage URL
    project_urls: str | None  # JSON string of project URLs
    timestamp: Annotated[datetime, BeforeValidator(parse_timestamp)]  # upload_time from BigQuery (ISO format string)
