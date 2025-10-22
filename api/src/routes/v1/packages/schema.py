"""Schema definitions for package data."""

from datetime import datetime

from pydantic import BaseModel


class PackageInput(BaseModel):
    ecosystem: str
    package_name: str
    description: str | None = None
    home_page: str | None = None
    project_urls: str | None = None
    source_code: str | None = None
    first_seen: datetime
    last_seen: datetime


class PackageUpdate(BaseModel):
    ecosystem: str | None = None
    package_name: str | None = None
    source_code: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
