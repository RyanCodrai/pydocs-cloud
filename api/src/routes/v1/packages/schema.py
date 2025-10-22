"""Schema definitions for package data."""

from datetime import datetime

from pydantic import BaseModel


class PackageInput(BaseModel):
    ecosystem: str
    package_name: str
    source_code: str | None = None
    source_code_stars: int | None = None
    first_seen: datetime
    last_seen: datetime
    pydocs_rank: int | None = None
