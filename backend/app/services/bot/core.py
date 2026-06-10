"""Transport-agnostic bot logic.

`handle_event` takes a normalized event (provider, external id, text, button
payload) and returns a Reply (text + optional buttons). A platform adapter (VK
now, Telegram later) turns events into this call and renders the Reply.
"""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, OAuthAccount, Room, User
from app.services import predictions as prediction_service
from app.services.bot import queries
from app.services.bot.state import (
    clear_state,
    consume_link_code,
    get_state,
    set_state,
)

# Day windows (inclusive), relative to today (UTC).
RESULTS_BACK, RESULTS_FWD = 3, 2
PREDICT_BACK, PREDICT_FWD = 0, 5

_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
_WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
_SCORE_RE = re.compile(r"^\s*(\d{1,2})\s+(\d{1,2})\s*$")
_CODE_RE = re.compile(r"^[0-9A-Fa-f]{6}$")
_STOP_WORDS = {"стоп", "stop", "отмена", "меню", "menu", "начать", "start"}


@dataclass
class Button:
    label: str
    payload: dict


@dataclass
class Reply:
    text: str
    buttons: list[list[Button]] = field(default_factory=list)


def _today() -> "datetime.date":
    return datetime.now(timezone.utc).date()


def _fmt_day(d) -> str:
    return f"{d.day} {_MONTHS[d.month]} ({_WEEKDAYS[d.weekday()]})"


def _btn_menu() -> list[Button]:
    return [Button("⬅️ Меню", {"a": "menu"})]


# ---------------- entry ----------------
async def handle_event(
    db: AsyncSession, provider: str, ext_id: str, text: str, payload: dict | None
) -> Reply:
    acc = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == str(ext_id),
        )
    )
    if not acc:
        return await _handle_unlinked(db, provider, ext_id, text)
    user = await db.get(User, acc.user_id)
    if not user:
        return Reply("Пользователь не найден. Обратитесь к организатору.")
    return await _handle_linked(db, provider, ext_id, user, text or "", payload)


async def _handle_unlinked(db: AsyncSession, provider: str, ext_id: str, text: str) -> Reply:
    code = (text or "").strip()
    if _CODE_RE.match(code):
        user_id = await consume_link_code(code)
        if user_id:
            db.add(
                OAuthAccount(
                    user_id=uuid.UUID(user_id),
                    provider=provider,
                    provider_user_id=str(ext_id),
                )
            )
            await db.commit()
            return Reply(
                "✅ Аккаунт привязан! Напишите любое сообщение, чтобы открыть меню.",
                [[Button("Открыть меню", {"a": "menu"})]],
            )
        return Reply("Код не найден или истёк. Получите новый код в профиле на сайте.")
    return Reply(
        "Здравствуйте! Чтобы делать прогнозы через бота, привяжите аккаунт:\n"
        "1. На сайте откройте Профиль → «Привязать ВК».\n"
        "2. Пришлите сюда полученный код (6 символов)."
    )


# ---------------- linked router ----------------
async def _handle_linked(
    db: AsyncSession, provider: str, ext_id: str, user: User, text: str, payload: dict | None
) -> Reply:
    state = await get_state(provider, ext_id)
    action = (payload or {}).get("a")

    # Sequential score entry has priority over free text.
    if state.get("flow") == "predict" and not action:
        if text.strip().lower() in _STOP_WORDS:
            await clear_state(provider, ext_id)
            return await _menu(db, provider, ext_id, user)
        return await _predict_input(db, provider, ext_id, user, state, text)

    if action in (None, "menu", "start"):
        return await _menu(db, provider, ext_id, user, rid=(payload or {}).get("rid"))
    if action == "switch":
        await set_state(provider, ext_id, {})
        return await _menu(db, provider, ext_id, user)
    if action == "table":
        return await _table(db, provider, ext_id, user)
    if action == "tour":
        return await _tour_days(db, provider, ext_id, user)
    if action == "tour_day":
        return await _tour_results(db, provider, ext_id, user, payload.get("d"))
    if action == "predict":
        return await _predict_days(db, provider, ext_id, user)
    if action == "predict_day":
        return await _predict_start(db, provider, ext_id, user, payload.get("d"))
    if action == "skip":
        return await _predict_advance(db, provider, ext_id, user, state, skipped=True)
    return await _menu(db, provider, ext_id, user)


# ---------------- room helpers ----------------
async def _current_room(db: AsyncSession, user: User, state: dict) -> Room | None:
    rooms = await queries.active_rooms(db, user.id)
    rid = state.get("room_id")
    room = next((r for r in rooms if str(r.id) == str(rid)), None)
    if not room and len(rooms) == 1:
        room = rooms[0]
    return room


async def _menu(
    db: AsyncSession, provider: str, ext_id: str, user: User, rid: str | None = None
) -> Reply:
    rooms = await queries.active_rooms(db, user.id)
    if not rooms:
        return Reply("Вы не состоите ни в одной активной комнате. Вступите в комнату на сайте.")

    state = await get_state(provider, ext_id)
    if rid:
        state["room_id"] = rid
    room = next((r for r in rooms if str(r.id) == str(state.get("room_id"))), None)
    if not room:
        if len(rooms) == 1:
            room = rooms[0]
        else:
            await set_state(provider, ext_id, {})
            return Reply(
                "Выберите комнату:",
                [[Button(r.name[:40], {"a": "menu", "rid": str(r.id)})] for r in rooms],
            )

    await set_state(provider, ext_id, {"room_id": str(room.id)})  # reset any flow
    buttons = [
        [Button("📊 Таблица", {"a": "table"})],
        [Button("📅 Итог тура", {"a": "tour"})],
        [Button("✍️ Сделать прогноз", {"a": "predict"})],
    ]
    if len(rooms) > 1:
        buttons.append([Button("🔄 Сменить комнату", {"a": "switch"})])
    return Reply(f"Комната: {room.name}\nВыберите действие:", buttons)


# ---------------- table ----------------
async def _table(db: AsyncSession, provider: str, ext_id: str, user: User) -> Reply:
    state = await get_state(provider, ext_id)
    room = await _current_room(db, user, state)
    if not room:
        return await _menu(db, provider, ext_id, user)
    rows = await queries.leaderboard(db, room.id)
    if not rows:
        return Reply("В комнате пока нет участников.", [_btn_menu()])
    lines = [f"🏆 Таблица — {room.name}"]
    for i, (nick, pts) in enumerate(rows[:50], start=1):
        prefix = _MEDALS.get(i, f"{i}.")
        lines.append(f"{prefix} {nick} — {pts}")
    return Reply("\n".join(lines), [_btn_menu()])


# ---------------- tour results ----------------
def _day_buttons(days, action: str) -> list[list[Button]]:
    return [[Button(_fmt_day(d), {"a": action, "d": d.isoformat()})] for d in days]


async def _tour_days(db: AsyncSession, provider: str, ext_id: str, user: User) -> Reply:
    today = _today()
    days = await queries.days_with_matches(
        db, today - timedelta(days=RESULTS_BACK), today + timedelta(days=RESULTS_FWD)
    )
    if not days:
        return Reply("В ближайшие дни нет матчей.", [_btn_menu()])
    return Reply("Выберите тур (итоги):", _day_buttons(days, "tour_day") + [_btn_menu()])


async def _tour_results(
    db: AsyncSession, provider: str, ext_id: str, user: User, day_iso: str
) -> Reply:
    state = await get_state(provider, ext_id)
    room = await _current_room(db, user, state)
    if not room:
        return await _menu(db, provider, ext_id, user)
    day = _parse_day(day_iso)
    if not day:
        return await _tour_days(db, provider, ext_id, user)

    players = await queries.tour_player_points(db, room.id, day)
    matches = await queries.tour_matches_for_user(db, room.id, user.id, day)

    lines = [f"📅 {_fmt_day(day)} — итоги ({room.name})", ""]
    lines.append(" · ".join(f"{n} — {p}" for n, p in players[:30]) or "—")
    lines.append("")
    lines.append("Матчи (ваши очки):")
    for m, pred in matches:
        if m.status == "finished" and m.home_score_ft is not None:
            score = f"{m.home_score_ft}:{m.away_score_ft}"
        else:
            score = "—:—"
        pts = "" if pred is None or pred.points_awarded is None else f" — +{pred.points_awarded}"
        guess = "" if pred is None else f" (ваш {pred.predicted_home}:{pred.predicted_away})"
        lines.append(f"{m.home_team} {score} {m.away_team}{guess}{pts}")

    buttons = [[Button("⬅️ К турам", {"a": "tour"})], _btn_menu()]
    return Reply("\n".join(lines), buttons)


# ---------------- predictions ----------------
async def _predict_days(db: AsyncSession, provider: str, ext_id: str, user: User) -> Reply:
    today = _today()
    days = await queries.days_with_matches(
        db, today - timedelta(days=PREDICT_BACK), today + timedelta(days=PREDICT_FWD)
    )
    if not days:
        return Reply("Нет матчей для прогноза в ближайшие дни.", [_btn_menu()])
    return Reply(
        "Выберите тур для прогноза:", _day_buttons(days, "predict_day") + [_btn_menu()]
    )


async def _predict_start(
    db: AsyncSession, provider: str, ext_id: str, user: User, day_iso: str
) -> Reply:
    state = await get_state(provider, ext_id)
    room = await _current_room(db, user, state)
    if not room:
        return await _menu(db, provider, ext_id, user)
    day = _parse_day(day_iso)
    if not day:
        return await _predict_days(db, provider, ext_id, user)

    now = datetime.now(timezone.utc)
    matches = [m for m in await queries.matches_of_day(db, day) if m.kickoff_at > now]
    if not matches:
        return Reply("Все матчи этого дня уже начались — приём закрыт.", [_btn_menu()])

    state = {
        "flow": "predict",
        "room_id": str(room.id),
        "queue": [str(m.id) for m in matches],
        "idx": 0,
    }
    await set_state(provider, ext_id, state)
    return _predict_prompt(matches[0], 0, len(matches))


def _predict_prompt(match: Match, idx: int, total: int) -> Reply:
    return Reply(
        f"Матч {idx + 1}/{total}:\n"
        f"⚽ {match.home_team} — {match.away_team}\n"
        f"Введите счёт через пробел, например «2 1».",
        [[Button("⏭️ Пропустить", {"a": "skip"})], [Button("⏹️ Стоп", {"a": "menu"})]],
    )


async def _predict_input(
    db: AsyncSession, provider: str, ext_id: str, user: User, state: dict, text: str
) -> Reply:
    m = _SCORE_RE.match(text or "")
    if not m:
        return Reply("Введите счёт в формате «2 1» (или «Стоп»).")
    home, away = int(m.group(1)), int(m.group(2))

    match = await _current_predict_match(db, state)
    if match is None:
        await clear_state(provider, ext_id)
        return await _menu(db, provider, ext_id, user)

    room = await db.get(Room, uuid.UUID(state["room_id"]))
    accepted, reason = await prediction_service.set_prediction(
        db, room=room, user=user, match=match, home=home, away=away
    )
    await db.commit()
    note = ""
    if not accepted:
        note = {
            "deadline_passed": "⚠️ Приём по этому матчу закрыт.",
            "room_archived": "⚠️ Комната в архиве.",
            "invalid_score": "⚠️ Счёт вне диапазона 0–20.",
        }.get(reason, "⚠️ Не принято.")
        if reason == "invalid_score":
            return Reply(note + " Введите счёт ещё раз, например «2 1».")
    else:
        note = f"✅ Принято: {match.home_team} {home}:{away} {match.away_team}"
    return await _predict_advance(db, provider, ext_id, user, state, prefix=note)


async def _predict_advance(
    db: AsyncSession,
    provider: str,
    ext_id: str,
    user: User,
    state: dict,
    *,
    skipped: bool = False,
    prefix: str = "",
) -> Reply:
    if state.get("flow") != "predict":
        return await _menu(db, provider, ext_id, user)
    idx = state.get("idx", 0) + 1
    queue = state.get("queue", [])
    if idx >= len(queue):
        await clear_state(provider, ext_id)
        done = (prefix + "\n\n" if prefix else "") + "Готово! Прогнозы тура сохранены."
        return Reply(done.strip(), [_btn_menu()])
    state["idx"] = idx
    await set_state(provider, ext_id, state)
    match = await _current_predict_match(db, state)
    if match is None:
        await clear_state(provider, ext_id)
        return await _menu(db, provider, ext_id, user)
    reply = _predict_prompt(match, idx, len(queue))
    if prefix:
        reply.text = f"{prefix}\n\n{reply.text}"
    return reply


async def _current_predict_match(db: AsyncSession, state: dict) -> Match | None:
    queue = state.get("queue", [])
    idx = state.get("idx", 0)
    if idx >= len(queue):
        return None
    return await db.get(Match, uuid.UUID(queue[idx]))


# ---------------- utils ----------------
def _parse_day(day_iso: str | None):
    if not day_iso:
        return None
    try:
        return datetime.fromisoformat(day_iso).date()
    except ValueError:
        try:
            return datetime.strptime(day_iso, "%Y-%m-%d").date()
        except ValueError:
            return None
