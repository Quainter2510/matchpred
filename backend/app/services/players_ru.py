"""Русские имена игроков РПЛ для спецпрогноза бомбардира.

API-Football отдаёт латиницу (часто «A. Batrakov»). Здесь курируемый словарь;
неизвестные игроки остаются латиницей (фолбэк). Сопоставление — по полному
нормализованному имени и по фамилии (последнее слово), т.к. в API имя нередко
сокращено до инициала. Фамилии, которые встречаются у нескольких игроков, в
фамильный индекс не попадают (во избежание путаницы).
"""
from app.services.players_catalog import normalize_name

# (русское имя, [латинские варианты])
_PLAYERS: list[tuple[str, list[str]]] = [
    ("Фёдор Чалов", ["Chalov", "Fedor Chalov"]),
    ("Алексей Батраков", ["Batrakov", "Aleksei Batrakov", "Alexey Batrakov"]),
    ("Иван Обляков", ["Oblyakov", "Ivan Oblyakov"]),
    ("Константин Тюкавин", ["Tyukavin", "Konstantin Tyukavin"]),
    ("Максим Глушенков", ["Glushenkov", "Maksim Glushenkov"]),
    ("Александр Соболев", ["Sobolev", "Aleksandr Sobolev"]),
    ("Матео Кассьерра", ["Cassierra", "Mateo Cassierra"]),
    ("Джон Кордоба", ["Cordoba", "Jhon Cordoba"]),
    ("Эдуард Сперцян", ["Spertsyan", "Eduard Spertsyan"]),
    ("Гамид Агаларов", ["Agalarov", "Gamid Agalarov"]),
    ("Далер Кузяев", ["Kuzyaev", "Daler Kuzyaev"]),
    ("Антон Заболотный", ["Zabolotny", "Zabolotnyi", "Anton Zabolotny"]),
    ("Сергей Пиняев", ["Pinyaev", "Sergei Pinyaev"]),
    ("Наир Тикнизян", ["Tiknizyan", "Nair Tiknizyan"]),
    ("Вильмар Барриос", ["Barrios", "Wilmar Barrios"]),
    ("Клаудиньо", ["Claudinho"]),
    ("Матвей Кисляк", ["Kislyak", "Matvei Kislyak"]),
    ("Иван Сергеев", ["Ivan Sergeev"]),
    ("Мохеби", ["Mohebi", "Saeid Mohebi"]),
    ("Дуглас Сантос", ["Douglas Santos"]),
    ("Вендел", ["Wendel"]),
    ("Педро", ["Pedro"]),
    ("Артём Дзюба", ["Dzyuba", "Artem Dzyuba"]),
]


def _surname(latin: str) -> str:
    parts = [p for p in normalize_name(latin).replace(".", " ").split() if len(p) > 1]
    return parts[-1] if parts else ""


_BY_FULL: dict[str, str] = {}
_BY_SURNAME: dict[str, str | None] = {}  # None — фамилия неоднозначна
for _ru, _aliases in _PLAYERS:
    for _a in _aliases:
        _BY_FULL[normalize_name(_a)] = _ru
        s = _surname(_a)
        if s:
            _BY_SURNAME[s] = _ru if s not in _BY_SURNAME else (
                _ru if _BY_SURNAME[s] == _ru else None
            )


def ru_player(name: str | None) -> str | None:
    """Русское имя игрока по латинскому (полное имя или фамилия), иначе None."""
    if not name:
        return None
    full = normalize_name(name)
    if full in _BY_FULL:
        return _BY_FULL[full]
    return _BY_SURNAME.get(_surname(name)) or None
