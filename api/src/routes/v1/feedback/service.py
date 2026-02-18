import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBFeedback
from src.routes.v1.feedback.repository import FeedbackRepository
from src.routes.v1.feedback.schema import FeedbackInput, FeedbackType


class FeedbackService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = FeedbackRepository(db_session=db_session)

    async def create(self, user_id: uuid.UUID, feedback_type: FeedbackType, text: str) -> DBFeedback:
        feedback_input = FeedbackInput(user_id=user_id, feedback_type=feedback_type, text=text)
        return await self.repository.create(feedback_input)
