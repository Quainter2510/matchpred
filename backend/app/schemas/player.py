import uuid
from datetime import date, datetime

from pydantic import BaseModel


class PlayerProfileMatch(BaseModel):
    match_id: uuid.UUID
    match_date: date
    kickoff_at: datetime
    stage: str
    group_name: str | None = None
    home_team: str
    away_team: str
    status: str
    home_score_ft: int | None = None
    away_score_ft: int | None = None
    started: bool
    # Prediction is hidden (null) for not-yet-started matches of other players.
    predicted_home: int | None = None
    predicted_away: int | None = None
    points_awarded: int | None = None
    is_exact: bool | None = None


class PlayerProfile(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    place: int | None = None
    total_points: int
    exact_scores_count: int
    is_self: bool
    # Special predictions are revealed only after the tournament starts.
    specials_revealed: bool = False
    first_match_at: datetime
    champion_team: str | None = None
    top_scorer_name: str | None = None
    matches: list[PlayerProfileMatch]
