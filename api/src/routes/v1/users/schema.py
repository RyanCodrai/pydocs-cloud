"""Schema module for data validation and serialization.

This module provides Pydantic models that define the structure and validation rules for data
passing through the Service layer. The models ensure type safety and data validation while
providing clean interfaces for serialisation.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserInput(BaseModel):
    # We will update more in future include proxy location, cookies etc
    is_active: Optional[bool] = None


class UserOutput(BaseModel):
    id: UUID
    email_address: str
