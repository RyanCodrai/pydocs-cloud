"""Schema definitions for package data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator
from src.routes.v1.webhooks.schema import parse_timestamp


class PackageInput(BaseModel):
    ecosystem: str
    package_name: str
    description: str | None = None
    home_page: str | None = None
    project_urls: str | None = None
    source_code: str | None = None
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]


class PackageUpdate(BaseModel):
    ecosystem: str | None = None
    package_name: str | None = None
    source_code: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
