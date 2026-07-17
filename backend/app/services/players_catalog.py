"""Curated top-scorer candidates with Russian-language search.

Before the tournament API-Football has no World Cup squads loaded, so the live
`/players/profiles` search can return nothing for these names. This curated list
guarantees the well-known favourites are always findable — and findable by their
Russian spelling.

Each entry has a STABLE negative `api_id`. Stability matters: scoring matches a
prediction's `top_scorer_api_id` against the admin-entered result by id, so the
same id must come back every time someone picks the player. Negative ids never
collide with real API-Football ids (which are positive), so curated and live
results can safely coexist.
"""
import unicodedata

# curated_id, real_id (настоящий ID API-Football или None), latin, russian,
# nationality, extra search aliases.
#
# real_id связывает кураторскую запись с реальным игроком: участники, выбравшие
# игрока через живой поиск, сохраняют реальный ID, а через кураторский список —
# отрицательный. resolve_player/canonical_scorer_id сводят оба к одной записи,
# поэтому в списках и при начислении они считаются одним игроком, а голы берутся
# из снимка `/players/topscorers` (там реальные ID).
_RAW: list[tuple[int, int | None, str, str, str, list[str]]] = [
    (-1, 278, "Kylian Mbappé", "Килиан Мбаппе", "France", ["mbappe", "килиан"]),
    (-2, None, "Lamine Yamal", "Ламине Ямаль", "Spain", ["yamal", "ямаль", "ямал"]),
    (-3, None, "Erling Haaland", "Эрлинг Холанд", "Norway", ["haaland", "холанд", "халанд", "эрлинг"]),
    (-4, None, "Vinicius Junior", "Винисиус Жуниор", "Brazil", ["vinicius", "винисиус", "вінісіус", "жуниор"]),
    (-5, None, "Harry Kane", "Гарри Кейн", "England", ["kane", "кейн", "гарри"]),
    (-6, None, "Lautaro Martínez", "Лаутаро Мартинес", "Argentina", ["lautaro", "martinez", "мартинес", "лаутаро"]),
    (-7, None, "Alexander Isak", "Александер Исак", "Sweden", ["isak", "исак", "александер"]),
    (-8, None, "Victor Osimhen", "Виктор Осимхен", "Nigeria", ["osimhen", "осимхен", "виктор"]),
    (-9, None, "Álvaro Morata", "Альваро Мората", "Spain", ["morata", "мората", "альваро"]),
    (-10, None, "Niclas Füllkrug", "Никлас Фюллькруг", "Germany", ["fullkrug", "fuellkrug", "фюллькруг", "никлас"]),
    (-11, None, "Robert Lewandowski", "Роберт Левандовски", "Poland", ["lewandowski", "левандовски", "левандовський", "роберт"]),
    (-12, None, "Darwin Núñez", "Дарвин Нуньес", "Uruguay", ["nunez", "нуньес", "дарвин"]),
    (-13, None, "Jude Bellingham", "Джуд Беллингем", "England", ["bellingham", "беллингем", "джуд"]),
    (-14, None, "Federico Chiesa", "Федерико Кьеза", "Italy", ["chiesa", "кьеза", "федерико"]),
    (-15, None, "Gonçalo Ramos", "Гонсалу Рамуш", "Portugal", ["goncalo", "ramos", "рамуш", "рамос", "гонсалу"]),
    (-16, None, "Karim Adeyemi", "Карим Адейеми", "Germany", ["adeyemi", "адейеми", "карим"]),
    (-17, None, "Marcus Rashford", "Маркус Рэшфорд", "England", ["rashford", "рэшфорд", "рашфорд", "маркус"]),
    (-18, None, "Mykhaylo Mudryk", "Михайло Мудрик", "Ukraine", ["mudryk", "мудрик", "михаил", "михайло"]),
    (-19, None, "Artem Dovbyk", "Артем Довбик", "Ukraine", ["dovbyk", "довбик", "добык", "артем", "артём"]),
    (-20, None, "Pedri", "Педри", "Spain", ["pedri", "педри"]),
    (-21, 978, "Kai Havertz", "Кай Хаверц", "Germany", ["havertz", "хаверц", "кай"]),
    (-22, 874, "Cristiano Ronaldo", "Криштиану Роналду", "Portugal", ["ronaldo", "роналду", "роналдо", "криштиану", "криштиано"]),
    (-23, 19617, "Michael Olise", "Майкл Олисе", "France", ["olise", "олисе", "майкл", "микаэль"]),
]


def _norm(s: str) -> str:
    """Lowercase and strip combining diacritics so 'mbappe' matches 'Mbappé'
    and 'и'/'й' variants collapse. Cyrillic base letters are preserved."""
    decomposed = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_CATALOG = [
    {
        "api_id": curated_id,
        "name": f"{name_ru} ({name_lat})",
        "team": team,
        "photo": None,
        "_haystack": _norm(" ".join([name_lat, name_ru, *aliases])),
    }
    for curated_id, _real, name_lat, name_ru, team, aliases in _RAW
]

# Любой известный ID (кураторский отрицательный ИЛИ реальный из API-Football) →
# каноническая запись: canonical_id (стабильный кураторский), русское имя и
# real_id (для сопоставления с голами из снимка topscorers).
_BY_ID: dict[int, dict] = {}
for _cur, _real, _lat, _ru, _team, _aliases in _RAW:
    _rec = {
        "canonical_id": _cur,
        "name": f"{_ru} ({_lat})",
        "real_id": _real,
        "team": _team,
    }
    _BY_ID[_cur] = _rec
    if _real is not None:
        _BY_ID[_real] = _rec


def resolve_player(api_id: int | None) -> dict | None:
    """Каноническая запись игрока по любому из его ID (кураторский/реальный)
    или None, если игрок не в каталоге."""
    if api_id is None:
        return None
    return _BY_ID.get(api_id)


def canonical_scorer_id(api_id: int | None) -> int | None:
    """Свести ID к каноническому: реальный 278 и кураторский -1 → один и тот же
    (-1). Неизвестные ID возвращаются как есть — чтобы начисление продолжало
    работать и для игроков вне каталога."""
    rec = resolve_player(api_id)
    return rec["canonical_id"] if rec else api_id


def normalize_name(s: str) -> str:
    """Публичная нормализация имени (нижний регистр, без диакритики) — для
    сопоставления имён игроков со снимком бомбардиров вне модуля."""
    return _norm(s)


def search_curated(query: str) -> list[dict]:
    """Substring match (accent- and case-insensitive) over latin name, russian
    name and aliases. Returns API-shaped dicts ready to merge with live results."""
    q = _norm(query.strip())
    if not q:
        return []
    out = []
    for p in _CATALOG:
        if q in p["_haystack"]:
            out.append({k: v for k, v in p.items() if not k.startswith("_")})
    return out
