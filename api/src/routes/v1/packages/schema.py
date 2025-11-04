"""Schema definitions for package data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator
from src.db.models import PackageStatus
from src.routes.v1.webhooks.schema import parse_timestamp


class PackageInput(BaseModel):
    ecosystem: str
    package_name: str
    description: str | None = None
    home_page: str | None = None
    project_urls: dict[str, str] = {}
    source_code: str | None = None
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    source_code_candidates: list[str] = []
    status: PackageStatus = PackageStatus.PENDING_EXTRACTION
