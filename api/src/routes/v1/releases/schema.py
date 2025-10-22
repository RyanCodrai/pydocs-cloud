"""Schema definitions for release data."""

from datetime import datetime

from pydantic import BaseModel


class ReleaseInput(BaseModel):
    ecosystem: str
    package_name: str
    version: str
    first_seen: datetime
    last_seen: datetime
