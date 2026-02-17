from typing import Literal
from uuid import UUID

from pydantic import BaseModel

FeedbackType = Literal["bug", "improvement", "question", "other"]


class FeedbackInput(BaseModel):
    user_id: UUID
    feedback_type: FeedbackType
    text: str
