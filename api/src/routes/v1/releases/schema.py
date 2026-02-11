"""Schema definitions for release data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, model_validator
from src.routes.v1.webhooks.schema import normalize_package_name, parse_timestamp


class ReleaseInput(BaseModel):
    ecosystem: str
    package_name: str
    version: str
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]

    @model_validator(mode="after")
    def normalize_name(self):
        if self.ecosystem == "pypi":
            self.package_name = normalize_package_name(self.package_name)
        return self
