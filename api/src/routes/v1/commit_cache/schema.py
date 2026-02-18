from datetime import datetime

from pydantic import BaseModel


class CommitCacheInput(BaseModel):
    github_url: str
    timestamp: datetime
    commit_sha: str
