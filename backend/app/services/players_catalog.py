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

# id, latin name, russian name, nationality, extra search aliases
_RAW: list[tuple[int, str, str, str, list[str]]] = [
    (-1, "Kylian Mbappé", "Килиан Мбаппе", "France", ["mbappe", "килиан"]),
    (-2, "Lamine Yamal", "Ламине Ямаль", "Spain", ["yamal", "ямаль", "ямал"]),
    (-3, "Erling Haaland", "Эрлинг Холанд", "Norway", ["haaland", "холанд", "халанд", "эрлинг"]),
    (-4, "Vinicius Junior", "Винисиус Жуниор", "Brazil", ["vinicius", "винисиус", "вінісіус", "жуниор"]),
    (-5, "Harry Kane", "Гарри Кейн", "England", ["kane", "кейн", "гарри"]),
    (-6, "Lautaro Martínez", "Лаутаро Мартинес", "Argentina", ["lautaro", "martinez", "мартинес", "лаутаро"]),
    (-7, "Alexander Isak", "Александер Исак", "Sweden", ["isak", "исак", "александер"]),
    (-8, "Victor Osimhen", "Виктор Осимхен", "Nigeria", ["osimhen", "осимхен", "виктор"]),
    (-9, "Álvaro Morata", "Альваро Мората", "Spain", ["morata", "мората", "альваро"]),
    (-10, "Niclas Füllkrug", "Никлас Фюллькруг", "Germany", ["fullkrug", "fuellkrug", "фюллькруг", "никлас"]),
    (-11, "Robert Lewandowski", "Роберт Левандовски", "Poland", ["lewandowski", "левандовски", "левандовський", "роберт"]),
    (-12, "Darwin Núñez", "Дарвин Нуньес", "Uruguay", ["nunez", "нуньес", "дарвин"]),
    (-13, "Jude Bellingham", "Джуд Беллингем", "England", ["bellingham", "беллингем", "джуд"]),
    (-14, "Federico Chiesa", "Федерико Кьеза", "Italy", ["chiesa", "кьеза", "федерико"]),
    (-15, "Gonçalo Ramos", "Гонсалу Рамуш", "Portugal", ["goncalo", "ramos", "рамуш", "рамос", "гонсалу"]),
    (-16, "Karim Adeyemi", "Карим Адейеми", "Germany", ["adeyemi", "адейеми", "карим"]),
    (-17, "Marcus Rashford", "Маркус Рэшфорд", "England", ["rashford", "рэшфорд", "рашфорд", "маркус"]),
    (-18, "Mykhaylo Mudryk", "Михайло Мудрик", "Ukraine", ["mudryk", "мудрик", "михаил", "михайло"]),
    (-19, "Artem Dovbyk", "Артем Довбик", "Ukraine", ["dovbyk", "довбик", "добык", "артем", "артём"]),
    (-20, "Pedri", "Педри", "Spain", ["pedri", "педри"]),
]


def _norm(s: str) -> str:
    """Lowercase and strip combining diacritics so 'mbappe' matches 'Mbappé'
    and 'и'/'й' variants collapse. Cyrillic base letters are preserved."""
    decomposed = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_CATALOG = [
    {
        "api_id": pid,
        "name": f"{name_ru} ({name_lat})",
        "team": team,
        "photo": None,
        "_haystack": _norm(" ".join([name_lat, name_ru, *aliases])),
    }
    for pid, name_lat, name_ru, team, aliases in _RAW
]


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
