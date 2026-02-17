from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBFeedback
from src.routes.v1.feedback.schema import FeedbackInput


class FeedbackRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: FeedbackInput) -> DBFeedback:
        feedback = DBFeedback(**data.model_dump())
        self.db_session.add(feedback)
        await self.db_session.commit()
        await self.db_session.refresh(feedback)
        return feedback
