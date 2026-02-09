"""Schema definitions for package data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator
from src.routes.v1.webhooks.schema import NormalizedPypiPackageName, parse_timestamp


class PackageInput(BaseModel):
    ecosystem: str
    package_name: NormalizedPypiPackageName
    description: str | None = None
    home_page: str | None = None
    project_urls: dict[str, str] = {}
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
