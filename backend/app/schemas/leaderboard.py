import uuid

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    place: int
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    total_points: int
    exact_scores_count: int


class MyLeaderboardEntry(LeaderboardEntry):
    pass
