"""Schema definitions for release data."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator
from src.routes.v1.webhooks.schema import parse_timestamp
from src.utils.pypi import NormalizedPypiPackageName


class ReleaseInput(BaseModel):
    ecosystem: str
    package_name: NormalizedPypiPackageName
    version: str
    first_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
    last_seen: Annotated[datetime, BeforeValidator(parse_timestamp)]
