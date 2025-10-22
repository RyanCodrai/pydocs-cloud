"""Schema definitions for release webhook data."""

from datetime import datetime

from pydantic import BaseModel


class Release(BaseModel):
    """Release data from BigQuery export (webhook payload)."""

    id: str  # UUID from GENERATE_UUID()
    ecosystem: str  # Always 'pypi' for now
    name: str  # Package name
    version: str  # Version string (e.g., "1.0.0")
    description: str | None  # Package description
    home_page: str | None  # Homepage URL
    project_urls: str | None  # JSON string of project URLs
    timestamp: str  # upload_time from BigQuery (ISO format string)


class ReleaseInput(BaseModel):
    ecosystem: str
    package_name: str
    version: str
    first_seen: datetime
    last_seen: datetime
