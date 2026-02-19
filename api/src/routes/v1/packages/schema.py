"""Schema definitions for package data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, model_validator
from src.routes.v1.webhooks.schema import normalize_package_name, parse_timestamp


class PackageUpdate(BaseModel):
    description: str | None = None
    home_page: str | None = None
    project_urls: dict[str, str] | None = None
    source_code: str | None = None
    status: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class PackageInput(BaseModel):
    ecosystem: str
    package_name: str
    description: str | None = None
    home_page: str | None = None
    project_urls: dict[str, str] = {}
    source_code: str | None = None
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]

    @model_validator(mode="after")
    def normalize_name(self):
        if self.ecosystem == "pypi":
            self.package_name = normalize_package_name(self.package_name)
        return self
