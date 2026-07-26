"""Справочник команд для UI: русское имя + логотип (по английскому имени из
матчей). Публичный — это справочные данные, кэшируются на клиенте."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Team
from app.services.teams_ru import club_ru

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamOut(BaseModel):
    name_en: str
    name_ru: str | None = None
    logo: str | None = None


def _logo_url(t: Team) -> str | None:
    if t.logo_local:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/api/v1/media/teams/{t.logo_local}"
    return t.logo_url


@router.get("", response_model=list[TeamOut])
async def list_teams(db: AsyncSession = Depends(get_db)):
    teams = (await db.execute(select(Team))).scalars().all()
    return [
        TeamOut(name_en=t.name_en, name_ru=club_ru(t.name_en), logo=_logo_url(t))
        for t in teams
    ]
