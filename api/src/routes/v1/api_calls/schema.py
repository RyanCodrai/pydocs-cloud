from uuid import UUID

from pydantic import BaseModel


class ApiCallInput(BaseModel):
    user_id: UUID
    endpoint: str
