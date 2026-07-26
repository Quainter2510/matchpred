"""Русские названия футбольных клубов (для UI, бота и эндпоинта /teams).

API-Football отдаёт только английские названия — русские берём отсюда. Ключи —
канонические английские имена из API (в нижнем регистре) и частые варианты
(алиасы), т.к. написание в разных эндпоинтах чуть отличается. Неизвестные клубы
остаются латиницей (фолбэк). Сборные (ЧМ) — отдельно в `bot/teams.py` и
`frontend/utils/countries.ts`.
"""
from app.services.players_catalog import normalize_name

# (русское имя, [английские имена/алиасы])
_CLUBS: list[tuple[str, list[str]]] = [
    # ---- РПЛ ----
    ("Зенит", ["Zenit", "Zenit St. Petersburg", "FC Zenit"]),
    ("Спартак Москва", ["Spartak Moscow", "Spartak Moskva", "FC Spartak Moscow"]),
    ("ЦСКА", ["CSKA Moscow", "PFC CSKA Moscow", "CSKA Moskva"]),
    ("Локомотив", ["Lokomotiv", "Lokomotiv Moscow", "FC Lokomotiv Moscow", "Lokomotiv Moskva"]),
    ("Динамо Москва", ["Dynamo", "Dinamo", "Dynamo Moscow", "Dinamo Moscow", "FC Dynamo Moscow"]),
    ("Краснодар", ["Krasnodar", "FC Krasnodar"]),
    ("Рубин", ["Rubin Kazan", "FC Rubin Kazan", "Rubin"]),
    ("Ростов", ["Rostov", "FC Rostov", "FK Rostov"]),
    ("Ахмат", ["Akhmat Grozny", "FC Akhmat", "Akhmat"]),
    ("Крылья Советов", ["Krylia Sovetov", "Krylya Sovetov", "Krylya Sovetov Samara", "Krylia Sovetov Samara"]),
    ("Динамо Махачкала", ["Dynamo Makhachkala", "Dinamo Makhachkala"]),
    ("Факел", ["Fakel Voronezh", "Fakel"]),
    ("Оренбург", ["Orenburg", "FC Orenburg"]),
    ("Пари НН", ["Pari Nizhniy Novgorod", "Nizhny Novgorod", "Pari NN", "FC Nizhny Novgorod"]),
    ("Химки", ["Khimki", "FC Khimki"]),
    ("Акрон", ["Akron Togliatti", "Akron", "Akron Tolyatti"]),
    ("Сочи", ["Sochi", "PFC Sochi", "FC Sochi"]),
    ("Балтика", ["Baltika", "Baltika Kaliningrad", "FC Baltika"]),
    ("Родина", ["Rodina Moskva", "Rodina Moscow", "Rodina"]),
    # ---- АПЛ ----
    ("Арсенал", ["Arsenal"]),
    ("Астон Вилла", ["Aston Villa"]),
    ("Борнмут", ["Bournemouth", "AFC Bournemouth"]),
    ("Брентфорд", ["Brentford"]),
    ("Брайтон", ["Brighton", "Brighton & Hove Albion", "Brighton Hove Albion"]),
    ("Челси", ["Chelsea"]),
    ("Кристал Пэлас", ["Crystal Palace"]),
    ("Эвертон", ["Everton"]),
    ("Фулхэм", ["Fulham"]),
    ("Ипсвич", ["Ipswich", "Ipswich Town"]),
    ("Лестер", ["Leicester", "Leicester City"]),
    ("Ливерпуль", ["Liverpool"]),
    ("Манчестер Сити", ["Manchester City"]),
    ("Манчестер Юнайтед", ["Manchester United"]),
    ("Ньюкасл", ["Newcastle", "Newcastle United"]),
    ("Ноттингем Форест", ["Nottingham Forest"]),
    ("Саутгемптон", ["Southampton"]),
    ("Тоттенхэм", ["Tottenham", "Tottenham Hotspur"]),
    ("Вест Хэм", ["West Ham", "West Ham United"]),
    ("Вулверхэмптон", ["Wolves", "Wolverhampton", "Wolverhampton Wanderers"]),
    # ---- Ла Лига ----
    ("Алавес", ["Alaves", "Deportivo Alaves"]),
    ("Атлетик", ["Athletic Club", "Athletic Bilbao"]),
    ("Атлетико", ["Atletico Madrid", "Atletico de Madrid"]),
    ("Барселона", ["Barcelona", "FC Barcelona"]),
    ("Сельта", ["Celta Vigo", "Celta de Vigo"]),
    ("Эспаньол", ["Espanyol"]),
    ("Хетафе", ["Getafe"]),
    ("Жирона", ["Girona"]),
    ("Лас-Пальмас", ["Las Palmas"]),
    ("Леганес", ["Leganes"]),
    ("Мальорка", ["Mallorca"]),
    ("Осасуна", ["Osasuna"]),
    ("Райо Вальекано", ["Rayo Vallecano"]),
    ("Бетис", ["Real Betis", "Betis"]),
    ("Реал Мадрид", ["Real Madrid"]),
    ("Реал Сосьедад", ["Real Sociedad"]),
    ("Севилья", ["Sevilla", "Sevilla FC"]),
    ("Валенсия", ["Valencia"]),
    ("Вальядолид", ["Valladolid", "Real Valladolid"]),
    ("Вильярреал", ["Villarreal"]),
    # ---- Серия A ----
    ("Аталанта", ["Atalanta"]),
    ("Болонья", ["Bologna"]),
    ("Кальяри", ["Cagliari"]),
    ("Комо", ["Como"]),
    ("Эмполи", ["Empoli"]),
    ("Фиорентина", ["Fiorentina"]),
    ("Дженоа", ["Genoa"]),
    ("Верона", ["Verona", "Hellas Verona"]),
    ("Интер", ["Inter", "Inter Milan", "Internazionale"]),
    ("Ювентус", ["Juventus"]),
    ("Лацио", ["Lazio"]),
    ("Лечче", ["Lecce"]),
    ("Милан", ["Milan", "AC Milan"]),
    ("Монца", ["Monza"]),
    ("Наполи", ["Napoli"]),
    ("Парма", ["Parma"]),
    ("Рома", ["Roma", "AS Roma"]),
    ("Торино", ["Torino"]),
    ("Удинезе", ["Udinese"]),
    ("Венеция", ["Venezia"]),
    # ---- Бундеслига ----
    ("Аугсбург", ["Augsburg", "FC Augsburg"]),
    ("Бавария", ["Bayern Munich", "Bayern München", "FC Bayern Munich"]),
    ("Бохум", ["Bochum", "VfL Bochum"]),
    ("Боруссия Дортмунд", ["Borussia Dortmund"]),
    ("Боруссия Мёнхенгладбах", ["Borussia Monchengladbach", "Borussia M.Gladbach", "Monchengladbach"]),
    ("Вердер", ["Werder Bremen", "SV Werder Bremen"]),
    ("Фрайбург", ["Freiburg", "SC Freiburg"]),
    ("Хайденхайм", ["Heidenheim", "1. FC Heidenheim"]),
    ("Хоффенхайм", ["Hoffenheim", "1899 Hoffenheim", "TSG Hoffenheim"]),
    ("Хольштайн Киль", ["Holstein Kiel"]),
    ("Байер", ["Bayer Leverkusen", "Leverkusen"]),
    ("Майнц", ["Mainz", "Mainz 05", "1. FSV Mainz 05"]),
    ("РБ Лейпциг", ["RB Leipzig"]),
    ("Санкт-Паули", ["St. Pauli", "FC St. Pauli", "St Pauli"]),
    ("Штутгарт", ["Stuttgart", "VfB Stuttgart"]),
    ("Унион Берлин", ["Union Berlin", "1. FC Union Berlin"]),
    ("Вольфсбург", ["Wolfsburg", "VfL Wolfsburg"]),
    ("Айнтрахт Франкфурт", ["Eintracht Frankfurt"]),
    # ---- Лига 1 ----
    ("Анже", ["Angers", "Angers SCO"]),
    ("Осер", ["Auxerre", "AJ Auxerre"]),
    ("Брест", ["Brest", "Stade Brestois 29"]),
    ("Гавр", ["Le Havre", "Le Havre AC"]),
    ("Ланс", ["Lens", "RC Lens"]),
    ("Лилль", ["Lille", "LOSC Lille"]),
    ("Лион", ["Lyon", "Olympique Lyonnais"]),
    ("Марсель", ["Marseille", "Olympique Marseille", "Olympique de Marseille"]),
    ("Монако", ["Monaco", "AS Monaco"]),
    ("Монпелье", ["Montpellier", "Montpellier HSC"]),
    ("Нант", ["Nantes", "FC Nantes"]),
    ("Ницца", ["Nice", "OGC Nice"]),
    ("ПСЖ", ["Paris Saint Germain", "Paris Saint-Germain", "PSG"]),
    ("Реймс", ["Reims", "Stade de Reims"]),
    ("Ренн", ["Rennes", "Stade Rennais"]),
    ("Сент-Этьен", ["Saint Etienne", "AS Saint-Etienne", "Saint-Etienne"]),
    ("Страсбур", ["Strasbourg", "RC Strasbourg"]),
    ("Тулуза", ["Toulouse", "Toulouse FC"]),
    # ---- Прочие клубы ЛЧ (не из топ-5) ----
    ("Спортинг", ["Sporting CP", "Sporting Lisbon"]),
    ("Бенфика", ["Benfica", "SL Benfica"]),
    ("Порту", ["Porto", "FC Porto"]),
    ("ПСВ", ["PSV Eindhoven", "PSV"]),
    ("Фейеноорд", ["Feyenoord"]),
    ("Аякс", ["Ajax"]),
    ("Селтик", ["Celtic"]),
    ("Брюгге", ["Club Brugge", "Club Brugge KV"]),
    ("Шахтёр", ["Shakhtar Donetsk", "Shakhtar"]),
    ("Ред Булл Зальцбург", ["Red Bull Salzburg", "RB Salzburg", "Salzburg"]),
    ("Спарта Прага", ["Sparta Prague", "Sparta Praha"]),
    ("Слован Братислава", ["Slovan Bratislava"]),
    ("Янг Бойз", ["Young Boys", "BSC Young Boys"]),
    ("Динамо Загреб", ["Dinamo Zagreb", "GNK Dinamo Zagreb"]),
    ("Црвена Звезда", ["Red Star Belgrade", "Crvena Zvezda"]),
    ("Галатасарай", ["Galatasaray"]),
    ("Штурм", ["Sturm Graz", "SK Sturm Graz"]),
    ("Копенгаген", ["Copenhagen", "FC Copenhagen"]),
]

# Английский (нормализованный) → русское имя.
_BY_NAME: dict[str, str] = {}
for _ru, _aliases in _CLUBS:
    _BY_NAME[normalize_name(_ru)] = _ru
    for _n in _aliases:
        _BY_NAME[normalize_name(_n)] = _ru


def club_ru(name: str | None) -> str | None:
    """Русское имя клуба по английскому (или None, если клуба нет в словаре)."""
    if not name:
        return None
    return _BY_NAME.get(normalize_name(name))
