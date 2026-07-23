# ⚽ ЧМ-2026 — Сайт прогнозов · AGENTS.md

> Этот файл — главный источник правды для агента. Читай его целиком перед тем как писать любой код.
> Связанные файлы: **DEPLOY.md** — развёртывание, **BOT_VK.md** — VK-бот.

---

## Контекст проекта

Платформа прогнозов на футбол: пользователи делают прогнозы на счёт матчей, система тянет реальные результаты через API-Football и строит турнирные таблицы. Поддерживаются разные **типы турниров** (см. ниже).

**Архитектура: турниры (исторически «комнаты»).** Каждый турнир — отдельное соревнование (таблица `rooms`): свой тип, привязка к реальной лиге+сезону, пул матчей, пароль, участники, правила начисления очков, прогнозы, спецпрогнозы и таблица лидеров. Один пользователь может состоять в нескольких турнирах. Создаёт турниры только суперадмин. (В коде и БД сущность зовётся `room`/«комната»; в UI — «турнир».)

**Матчи — общая дедуплицированная таблица**, но каждый матч помечен `league_id`/`season`; турнир отбирает свой пул матчей через `services/tournament.py` (`tournament_match_conditions(room)`). Результат матча глобален: один ввод счёта затрагивает все турниры над этой лигой. **Это заменило прежний инвариант «матчи общие для всех комнат» — теперь любое чтение матчей в контексте турнира обязано скоупиться резолвером.**

### Типы турниров (`tournament_type`, `services/tournament.py`)

| Тип | Лига | Тур | Спецпрогноз | Положение |
|-----|------|-----|-------------|-----------|
| `world_cup` | ЧМ (1) | суточный (10:00 МСК) | чемпион (авто) + бомбардир (вручную) | группы + плей-офф |
| `rpl` | РПЛ (235) | неделя (среда→среда) | лидер лиги (вручную) | одна лиговая таблица |
| `ucl` | ЛЧ (2) | неделя (суббота→суббота) | победитель/чемпион (вручную) | швейцарская таблица + плей-офф |
| `custom` | топ-5+РПЛ+ЛЧ | неделя (по метке матча) | нет | список выбранных матчей |

Тип задаёт лигу и схему туров (зашиты в коде); сезон и длительность (окно туров/дат) задаёт админ при создании. `custom` — матчи выбираются вручную (join-таблица `tournament_matches`).

REST API (Python/FastAPI) + фронтенд (React SPA) + VK-бот сообщества. API версионировано `/api/v1/`.

---

## Технологический стек

| Слой | Технология |
|------|-----------|
| Бэкенд | FastAPI 0.111 (Python 3.11+) |
| ORM | SQLAlchemy 2.x (async) |
| Миграции | Alembic |
| БД | PostgreSQL 15+ |
| Кэш / состояние ботов | Redis 7+ |
| Планировщик | APScheduler 3.x |
| HTTP-клиент | httpx (async) |
| Шифрование OAuth-токенов | cryptography (Fernet) |
| Хэширование паролей комнат | passlib[bcrypt] |
| Обработка аватаров | Pillow |
| Валидация | Pydantic v2 |
| Rate limiting | slowapi (200 req/min на IP, глобально) |
| Фронтенд | React 18 + TypeScript + Vite |
| Запросы (фронт) | TanStack Query v5 |
| Роутинг (фронт) | React Router v6 |
| CSS | Tailwind CSS 3.x |
| Стейт-менеджер | Zustand |
| Контейнеры | Docker + Docker Compose |

---

## Структура репозитория

```
backend/
├── app/
│   ├── main.py                # FastAPI app + routers + /api/v1/media (аватары)
│   ├── config.py              # pydantic-settings: DATABASE_URL, SECRET_KEY, VK_*, …
│   ├── database.py            # async engine, AsyncSession factory
│   ├── dependencies.py        # get_current_user(_optional) / require_superadmin /
│   │                          # require_room_member / require_room_admin; is_any_admin (для /auth/me)
│   ├── redis_client.py        # клиент Redis + кэш leaderboard (по комнате)
│   ├── security.py            # JWT, bcrypt, Fernet
│   ├── models/
│   │   ├── user.py            # User, OAuthAccount
│   │   ├── room.py            # Room, RoomMember
│   │   ├── match.py           # Match (глобальные) + RoomMatchMultiplier (коэффициент по комнате)
│   │   └── prediction.py      # Prediction, SpecialPrediction, AuditLog
│   ├── schemas/               # Pydantic request/response модели
│   ├── routers/
│   │   ├── auth.py            # /auth/* (Яндекс, Telegram, refresh, профиль, аватар, VK-код)
│   │   ├── rooms.py           # /rooms/* (CRUD комнат, вступление, участники, правила)
│   │   ├── matches.py         # /rooms/{id}/matches/* (чтение) + /matches/* (глобальный админ)
│   │   ├── predictions.py     # /rooms/{id}/predictions/*
│   │   ├── special.py         # /rooms/{id}/special-prediction/*, /players/search
│   │   ├── leaderboard.py     # /rooms/{id}/leaderboard
│   │   ├── standings.py       # /rooms/{id}/standings — положение ЧМ (группы + плей-офф)
│   │   ├── players.py         # /rooms/{id}/players/{uid} — профиль игрока в комнате
│   │   ├── admin.py           # /admin/* (sync, recalculate, scorer-result, журнал)
│   │   └── bots.py            # /bots/vk/callback — VK Callback API
│   └── services/
│       ├── oauth/             # telegram.py (HMAC-верификация), yandex.py
│       ├── football_api.py    # клиент API-Football (httpx async); fetch_fixtures(league, season)
│       ├── tournament.py      # конфиг типов турниров (лига, схема туров, спецпрогноз) +
│       │                      # tournament_match_conditions/match_belongs — скоуп матчей турнира
│       ├── scoring.py         # чистые функции начисления очков (unit-тесты обязательны)
│       ├── tours.py           # tour_key: матч → дата тура (суточная/недельная по схеме лиги)
│       ├── recalc.py          # оркестрация пересчёта по всем комнатам + rescore
│       ├── simulation.py      # режим симуляции суперадмина (X-Sim-Now, read-only)
│       ├── predictions.py     # set_prediction — общая запись прогноза (REST и боты)
│       ├── sync.py            # применение фикстур API-Football к БД
│       ├── scheduler.py       # APScheduler: тик 5 мин + ежедневный синк + бомбардиры 10:00 МСК
│       ├── audit.py           # запись в audit_log
│       ├── players_catalog.py # каталог бомбардиров (рус. поиск) + canonical_scorer_id (реальный↔кураторский ID)
│       ├── top_scorers.py     # снимок бомбардиров в Redis (суточный) + догрузка
│       │                      # голов выбранных участниками игроков вне топ-листа
│       └── bot/               # транспортно-независимое ядро ботов (см. BOT_VK.md)
│           ├── core.py        # меню, сценарии, конечный автомат (состояние в Redis)
│           ├── queries.py     # read-запросы
│           ├── state.py       # состояние диалога + одноразовые коды привязки
│           ├── teams.py       # названия команд
│           └── vk_client.py   # отправка сообщений в VK
├── alembic/versions/          # 0001…0013 (rooms — 0004, room_match_multipliers — 0009, winner_team — 0010, tournaments: типы+league_id/season — 0012, tournament_matches — 0013)
├── tests/                     # test_scoring.py, test_auth.py, test_simulation.py (без БД)
├── scripts/
│   ├── seed.py                # фикстуры из API-Football + первая комната
│   └── fetch_team_fixtures.py # разово: матчи 48 сборных за сезон → team_matches
├── Dockerfile                 # выполняет alembic upgrade head при старте
├── .env.example
└── requirements.txt

frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx              # кнопки OAuth: Telegram, Яндекс
│   │   ├── AuthCallback.tsx       # приём access_token из fragment (Яндекс)
│   │   ├── TelegramAuthCallback.tsx # redirect-режим Telegram (мобильные браузеры)
│   │   ├── SetupProfile.tsx       # форма никнейма (первый вход)
│   │   ├── RoomsHub.tsx           # публичное лобби: поиск/вступление/создание комнат
│   │   ├── Tournament.tsx         # экран комнаты: таблица + спецпрогнозы + туры (вкладки)
│   │   ├── Tour.tsx               # матчи дня
│   │   ├── PredictMatch.tsx       # форма ввода счёта
│   │   ├── MatchPredictions.tsx   # прогнозы участников на матч
│   │   ├── PlayerProfile.tsx      # профиль игрока в комнате (место, статистика, прогнозы)
│   │   ├── Profile.tsx            # свой профиль: никнейм, аватар, привязка VK
│   │   ├── SpecialPredictionCard.tsx
│   │   └── admin/
│   │       ├── Admin.tsx          # глобальная панель (только суперадмин): матчи, пересчёт, журнал, симуляция
│   │       ├── AdminMatches.tsx   # результаты + синхронизация (без коэффициентов — они в комнате)
│   │       ├── AdminSettings.tsx
│   │       ├── AdminAuditLog.tsx  # журнал (только суперадмин) + CSV-экспорт
│   │       ├── AdminSimulation.tsx # вкладка «Симуляция» (только суперадмин)
│   │       └── RoomAdmin.tsx      # управление комнатой: участники, пароль, регламент, коэффициенты, бомбардир
│   ├── components/                # Sidebar, MatchCard, ScoreStepper, Countdown,
│   │                              # LeaderboardTable, WcStandings (вкладка «ЧМ-2026» +
│   │                              # бомбардиры), MultiplierBadge, AuthModal, SimBanner,
│   │                              # ViewAsBanner, PlayerSearch, Avatar (фолбэк битых
│   │                              # аватарок), CountrySelect, Flag, TeamName, …
│   ├── api/
│   │   ├── client.ts              # axios + JWT + auto-refresh + заголовок X-Sim-Now
│   │   └── endpoints.ts           # типизированные вызовы API
│   ├── store/                     # auth.ts (user, loadMe), sim.ts (симуляция),
│   │                              # viewAs.ts (режим обычного пользователя)
│   └── utils/                     # scoring.ts (превью очков), dates.ts (sim-aware now),
│                                  # stage.ts, countries.ts
└── vite.config.ts
```

---

## База данных

### users

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| nickname | VARCHAR(24) UNIQUE NOT NULL | генерируется при OAuth, меняется в профиле (3–24) |
| avatar_url | TEXT NULLABLE | из OAuth-провайдера или загруженный (256×256 JPEG в `media/avatars/`) |
| system_role | 'superadmin' \| 'user' | DEFAULT 'user' |
| created_at | TIMESTAMPTZ | |
| is_active | BOOLEAN DEFAULT true | |

### oauth_accounts

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| provider | VARCHAR(20) | `telegram`, `yandex` или `vk` (привязка через бота) |
| provider_user_id | VARCHAR(100) | |
| access_token_enc / refresh_token_enc | TEXT NULLABLE | зашифрованы Fernet |
| expires_at | TIMESTAMPTZ NULLABLE | |

`UNIQUE(provider, provider_user_id)`

### rooms

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| name | VARCHAR(100) NOT NULL | индекс по имени (поиск в лобби) |
| password_hash | TEXT NOT NULL | bcrypt-хэш пароля для вступления |
| first_match_at | TIMESTAMPTZ NOT NULL | дедлайн спецпрогнозов комнаты |
| created_by | UUID FK → users NULLABLE | NULL у комнаты из seed |
| created_at | TIMESTAMPTZ | |
| is_active | BOOLEAN DEFAULT true | false = архив: read-only, очки не начисляются |
| rules_text | TEXT NULLABLE | регламент (кнопка «i»); NULL = стандартное описание из очков |
| points_exact / points_diff / points_outcome | SMALLINT | очки за точный счёт / разницу / исход (по умолч. 5/2/1) |
| points_champion / points_scorer | SMALLINT | очки за чемпиона/лидера/победителя (points_champion) и бомбардира (по умолч. 10/10) |
| tournament_type | VARCHAR(20) | `world_cup│rpl│ucl│custom` (по умолч. world_cup) |
| league_id / season | INT NULLABLE | реальная лига+сезон API-Football (NULL у custom) |
| tour_anchor | SMALLINT NULLABLE | якорный день недели туров (Пн=0…Вс=6); NULL = суточная группировка (ЧМ) |
| starts_on / ends_on | DATE NULLABLE | окно включения матчей по метке тура (NULL = весь турнир) |
| special_kind | VARCHAR(20) | вид спецпрогноза: `wc│leader│stage_or_champion│none` (по умолч. wc) |
| special_result_team | VARCHAR(100) NULLABLE | вручную заданный ответ спецпрогноза (лидер лиги / победитель) |

### room_members

| Поле | Тип | Описание |
|------|-----|---------|
| room_id + user_id | составной PK, FK CASCADE | |
| room_role | 'admin' \| 'player' | |
| joined_at | TIMESTAMPTZ | |
| total_points | INT DEFAULT 0 | |
| exact_scores_count | INT DEFAULT 0 | тайбрейк |
| participation_confirmed | BOOLEAN DEFAULT false | визуальная галочка подтверждения |

Индекс: `(room_id, total_points, exact_scores_count)`.

### matches — глобальные

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| api_football_id | INT UNIQUE NULLABLE | null если добавлен вручную |
| league_id / season | INT NULLABLE | реальная лига+сезон API-Football — по ним турнир отбирает свой пул матчей (`services/tournament.py`) |
| round | VARCHAR(40) NULLABLE | сырой `round` из API (напр. "Regular Season - 5") — для выбора длительности «с тура по тур» |
| match_date | DATE NOT NULL | метка тура — группировка по «турам»; производна от `kickoff_at` по схеме лиги (суточная/недельная, см. `services/tours.py`), **не** календарная дата UTC |
| kickoff_at | TIMESTAMPTZ NOT NULL | UTC, дедлайн прогноза |
| stage | VARCHAR(40) NOT NULL | |
| group_name | VARCHAR(20) NULLABLE | буква группы (из /standings) |
| home_team / away_team | VARCHAR(100) NOT NULL | |
| home_score_ft / away_score_ft | INT NULLABLE | у live-матчей здесь текущий счёт |
| status | VARCHAR(20) DEFAULT 'scheduled' | `scheduled│live│finished│cancelled` |
| winner_team | VARCHAR(100) NULLABLE | команда-победитель (учитывает пенальти/допвремя); нужна **только** для начисления чемпиона по финалу при ничьей в ОВ. Из API-Football (`teams.*.winner`) или указывается суперадмином при вводе счёта |
| updated_at | TIMESTAMPTZ | |

> ⚠️ Счёт ET/PKS (допвремя, пенальти) **не хранить** — прогнозы и очки строго по
> основному времени. Исключение — `winner_team`: это лишь *кто прошёл дальше*,
> без счёта, и читается только при начислении чемпиона.
> Коэффициент матча — **не глобальный**, он в `room_match_multipliers` (по комнате).

### room_match_multipliers — коэффициент матча по комнате

| Поле | Тип | Описание |
|------|-----|---------|
| room_id + match_id | составной PK, FK CASCADE | |
| multiplier | SMALLINT DEFAULT 1 | бонусный коэффициент 0/1/2/3; 0 — аннулирование в этой комнате |

Отсутствие строки = коэффициент 1. Задаёт **админ комнаты** для своей комнаты.
Индекс по `match_id` (для пересчёта матча по всем комнатам). При значении 1 строка удаляется.

### tournament_matches — набор матчей кастомного турнира

| Поле | Тип | Описание |
|------|-----|---------|
| room_id + match_id | составной PK, FK CASCADE | |
| added_at | TIMESTAMPTZ | |

Явный набор матчей для типа `custom` (админ выбирает матчи из разных лиг). Для лиговых типов (ЧМ/РПЛ/ЛЧ) не используется — там набор выводится по `league_id/season/окну`. Индекс по `match_id`.

### team_matches — справочник матчей сборных (форма)

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| api_football_id | INT UNIQUE NOT NULL | |
| kickoff_at | TIMESTAMPTZ NOT NULL | |
| competition | VARCHAR(100) NULLABLE | название турнира из API |
| home_team / away_team | VARCHAR(100) NOT NULL | индексы по обоим полям |
| home_score / away_score | INT NULLABLE | |
| status | VARCHAR(20) DEFAULT 'scheduled' | |

Матчи 48 сборных за сезон во **всех турнирах, кроме самого ЧМ** (его матчи в
`matches` и подмешиваются при чтении `/form`). Заполняется разово скриптом
`scripts/fetch_team_fixtures.py` (~50 запросов, upsert — можно перезапускать).
**Не участвует** в прогнозах, очках и турах — только блок «последние матчи»
на странице прогноза.

### predictions

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| room_id | UUID FK → rooms CASCADE | |
| user_id | UUID FK → users CASCADE | |
| match_id | UUID FK → matches CASCADE | |
| predicted_home / predicted_away | SMALLINT NOT NULL | 0–20 |
| created_at / updated_at | TIMESTAMPTZ | |
| points_awarded | SMALLINT NULLABLE | null = не пересчитано |
| is_exact | BOOLEAN NULLABLE | |

`UNIQUE(room_id, user_id, match_id)`. Индексы: `(room_id, match_id)`, `(room_id, user_id)`.

### special_predictions

| Поле | Тип | Описание |
|------|-----|---------|
| id | UUID PK | |
| room_id | UUID FK → rooms CASCADE | |
| user_id | UUID FK → users CASCADE | |
| champion_team | VARCHAR(100) NULLABLE | |
| top_scorer_name | VARCHAR(150) NULLABLE | |
| top_scorer_api_id | INT NULLABLE | ID в API-Football |
| locked_at | TIMESTAMPTZ NULLABLE | = room.first_match_at |
| champion_points / scorer_points | SMALLINT NULLABLE | null = не начислено |

`UNIQUE(room_id, user_id)` — один спецпрогноз на пользователя в каждой комнате.

### audit_log

| Поле | Тип | Описание |
|------|-----|---------|
| id | BIGINT PK AUTOINCREMENT | |
| created_at | TIMESTAMPTZ NOT NULL | UTC |
| actor_id | UUID FK → users NULLABLE | NULL для системных событий (APScheduler) |
| actor_nickname | VARCHAR(24) NULLABLE | снимок никнейма на момент события |
| event_type | VARCHAR(50) NOT NULL | |
| target_id | UUID NULLABLE | |
| details | JSONB NULLABLE | |

**Значения `event_type`** (русские подписи — `EVENT_LABELS_RU` в `routers/admin.py`, синхронизировать с фронтом):
`user_registered`, `superadmin_assigned`, `superadmin_transferred`, `role_changed`,
`member_removed`, `match_result_set`, `match_result_updated`, `multiplier_changed`,
`prediction_set`, `prediction_updated`, `scores_recalculated`, `scorer_result_set`,
`leader_result_set`, `champion_selected`, `top_scorer_selected`, `room_created`,
`room_deleted`, `room_joined`, `room_password_changed`, `room_rules_changed`,
`api_sync`, `nickname_changed`

Индексы: `(created_at)`, `(event_type)`, `(actor_id)`.
**Только запись** — никакого UPDATE/DELETE на этой таблице.

---

## Роли и права

**Суперадмин** (`system_role`) — единственный в системе, назначается атомарно первому вошедшему. **Единолично управляет глобальными матчами**: вводит/правит счёт, синхронизирует с API-Football, пересчитывает, создаёт/редактирует матчи. Создаёт/удаляет/архивирует комнаты, меняет их правила очков, входит в любую комнату без пароля (как админ), видит журнал, передаёт роль. Только он видит чужие прогнозы до дедлайна (в «Режиме суперадмина»).

**Админ комнаты** (`room_role='admin'`) — управляет **только своей** комнатой: участники, пароль, регламент, **коэффициенты матчей своей комнаты** и **итоговый бомбардир своей комнаты**. Счёт матчей менять не может (это глобальный факт — только суперадмин). **Чужие прогнозы до дедлайна не видит** (как обычный игрок).

**Игрок** — участник комнаты, делает прогнозы.

| Действие | Суперадмин | Админ комнаты | Игрок |
|----------|-----------|-------|-------|
| Создать / удалить / архивировать комнату | ✓ | — | — |
| Изменить правила очков комнаты | ✓ | — | — |
| Изменить регламент (rules_text) | ✓ | ✓ (своя комната) | — |
| Сменить пароль комнаты | ✓ | ✓ (своя) | — |
| Участники: роль / удаление / галочка | ✓ | ✓ (своя) | — |
| Войти в комнату без пароля | ✓ | — | — |
| Матчи: создать / редактировать / **результат** | ✓ | — | — |
| Синхронизация / пересчёт | ✓ | — | — |
| **Коэффициент матча/тура** | ✓ (своя) | ✓ (своя комната) | — |
| **Итоговый бомбардир/лидер/победитель** | ✓ (своя) | ✓ (своя комната) | — |
| Передать роль суперадмина | ✓ | — | — |
| Журнал (audit_log) + CSV-экспорт | ✓ | — | — |
| Режим симуляции (X-Sim-Now) | ✓ | — | — |
| Переключатель режима игрока/суперадмина (X-View-As) | ✓ | — | — |
| Прогноз на матч (до kickoff) | ✓ | ✓ | ✓ |
| Спецпрогноз (до дедлайна комнаты) | ✓ | ✓ | ✓ |
| Видеть прогнозы других на матч | всегда (режим SA) | после kickoff | после kickoff |
| Видеть спецпрогнозы других | всегда (режим SA) | после дедлайна | после дедлайна |
| Никнейм / аватар / привязка VK | ✓ | ✓ | ✓ |

### Назначение суперадмина

> **Ни seed-скриптов, ни переменных окружения для создания суперадмина не нужно.**

Логика в `_upsert_oauth_user` (`routers/auth.py`):
1. Если OAuth-аккаунт уже существует — обычный вход.
2. Иначе `LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE`; если `COUNT(*) = 0` —
   новый пользователь создаётся с `system_role='superadmin'` + событие
   `superadmin_assigned`. Гонка исключена блокировкой.
3. Никнейм генерируется автоматически из имени провайдера (пользователь меняет его на `/setup-profile`).

**Передача роли:** `POST /admin/superadmin/transfer {target_user_id}` — текущий суперадмин становится `'user'`. В системе всегда ровно один суперадмин.

---

## REST API — полный контракт

Базовый путь: `/api/v1/`. Формат: JSON. Защита: Bearer JWT (access). Документация: `/docs`.

Обозначения доступа: **Pub** — без токена; **Auth** — любой вошедший;
**Member** — участник комнаты (суперадмин проходит без членства);
**RAdmin** — админ комнаты или суперадмин;
**SA** — только суперадмин (глобальные матчи: счёт, синхронизация, пересчёт, журнал).

### Авторизация и профиль — `/auth`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/auth/yandex/login` | Pub | Redirect на Яндекс OAuth (CSRF state в Redis, 10 мин) |
| GET | `/auth/yandex/callback` | Pub | Redirect на `{FRONTEND_URL}/auth/callback#access_token=…&is_new_user=…` + refresh-cookie |
| GET | `/auth/telegram/login` | Pub | Данные для рендера Login Widget |
| GET | `/auth/telegram/oauth-redirect` | Pub | Redirect на oauth.telegram.org (мобильные браузеры) |
| GET | `/auth/telegram/callback` | Pub | Redirect-режим виджета → `{FRONTEND_URL}/telegram-auth?token=…` |
| POST | `/auth/telegram/verify` | Pub | Верификация данных виджета (HMAC) → `{access_token, is_new_user}` |
| POST | `/auth/refresh` | Pub | Новый access по refresh-cookie |
| POST | `/auth/logout` | Pub | Удалить refresh-cookie |
| GET | `/auth/me` | Auth | `{id, nickname, avatar_url, system_role, has_rooms, is_any_admin, vk_linked}` |
| PATCH | `/auth/me` | Auth | Сменить `nickname` (3–24, уникальный) |
| POST | `/auth/me/avatar` | Auth | multipart-загрузка аватара (≤5 МБ, кроп до 256×256 JPEG) |
| POST | `/auth/vk/link-code` | Auth | Одноразовый код (10 мин, Redis) для привязки VK через бота → `{code, bot_url}` |

### Комнаты — `/rooms`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms?q=` | Pub | Лобби: активные турниры, поиск по имени. Вошедшим — `is_member`/`my_role`; всегда `tournament_type`/`special_kind` |
| GET | `/rooms/my` | Auth | Мои турниры (включая архивные) |
| GET | `/rooms/tournament-types` | SA | Список типов турниров для панели создания `[{id, label, special_kind, has_league, needs_season}]` |
| GET | `/rooms/available-rounds?type=&season=` | SA | Туры лиги с датами (из API-Football) для выбора длительности «с тура по тур» |
| GET | `/rooms/custom-leagues` | SA | Лиги для выбора матчей кастомного турнира (топ-5+РПЛ+ЛЧ) |
| POST | `/rooms` | SA | Создать турнир `{name, password, tournament_type, season?, starts_on?, ends_on?, first_match_at?, scoring?}`; создатель — первый админ |
| DELETE | `/rooms/{id}` | SA | Удалить комнату (каскадно с прогнозами) |
| GET | `/rooms/{id}` | Member | Детали: счётчик участников, моя роль, правила очков, регламент |
| POST | `/rooms/{id}/join` | Auth | `{password}` → вступить игроком; суперадмин — без пароля, админом |
| PATCH | `/rooms/{id}/archive` | SA | `{archived}` — архивировать / восстановить |
| PATCH | `/rooms/{id}/rules` | SA | Изменить очки `{points_exact, points_diff, points_outcome, points_champion, points_scorer}` |
| PATCH | `/rooms/{id}/rules-text` | RAdmin | Регламент; пустая строка = сброс к стандартному описанию |
| GET | `/rooms/{id}/members` | RAdmin | Участники с ролями и очками |
| PATCH | `/rooms/{id}/members/{uid}/role` | RAdmin | `{role: 'admin'│'player'}` |
| PATCH | `/rooms/{id}/members/{uid}/participation` | RAdmin | `{confirmed}` — галочка подтверждения |
| DELETE | `/rooms/{id}/members/{uid}` | RAdmin | Удалить из комнаты (не из системы); **удаляет и его прогнозы/спецпрогноз в этой комнате** — осиротевших записей не остаётся |
| PATCH | `/rooms/{id}/password` | RAdmin | `{new_password}` |
| GET | `/rooms/{id}/custom-candidates?league_id=&season=&start=&end=` | RAdmin | Матчи лиги/сезона в окне дат — кандидаты для кастомного турнира (нужен предварительный `/admin/sync-league`) |
| GET | `/rooms/{id}/custom-matches` | RAdmin | Матчи, включённые в кастомный турнир |
| POST | `/rooms/{id}/custom-matches` | RAdmin | `{match_id}` — добавить матч в кастомный турнир |
| DELETE | `/rooms/{id}/custom-matches/{match_id}` | RAdmin | Убрать матч (удаляет его прогнозы в турнире, снимает начисленные очки) |

### Матчи (чтение в контексте комнаты) — `/rooms/{id}/matches`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms/{id}/matches/days` | Member | `[{date, match_count, my_predictions_count, first_kickoff_at, multiplier, finished_count, my_points, members_filled, members_total}]` (multiplier = общий для дня или null; my_points — мои очки за завершённые матчи дня; members_* — заполняемость тура, только для админов комнаты, иначе null) |
| GET | `/rooms/{id}/matches?date=` | Member | Матчи на дату + мой прогноз в этой комнате |
| GET | `/rooms/{id}/matches/{mid}` | Member | Один матч + мой прогноз |
| GET | `/rooms/{id}/matches/{mid}/form` | Member | Форма обеих сборных: последние сыгранные матчи 2026 года (≤7 на команду) — справочник `team_matches` + завершённые матчи ЧМ из `matches` (новые матчи ЧМ вытесняют старые; после турнира список замирает). Учитывает симуляцию |
| GET | `/rooms/{id}/matches/{mid}/predictions` | Member | **Все участники комнаты**; у не сделавших прогноз `predicted_*` = null (фронт показывает прочерки). 403 до kickoff (раскрывает только суперадмин в режиме SA — у админа комнаты привилегии нет) |
| PATCH | `/rooms/{id}/matches/{mid}/multiplier` | RAdmin | `{multiplier: 0│1│2│3}` — коэффициент **этой комнаты** для матча; завершённый матч авто-пересчитывается только в этой комнате (`rescore_match_in_room`) |
| PATCH | `/rooms/{id}/matches/tour/{date}/multiplier` | RAdmin | Коэффициент комнаты на весь тур (все матчи даты) |

### Матчи (глобальный админ) — `/matches`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/matches?date=` | SA | Глобальный список для панели (без коэффициента — он по комнатам) |
| POST | `/matches` | SA | Создать матч вручную |
| PATCH | `/matches/{mid}` | SA | Редактировать время/команды/стадию |
| POST | `/matches/{mid}/result` | SA | `{home_score_ft, away_score_ft, winner_team?}` — счёт только основного времени. `winner_team` (опц.) — победитель при ничьей в ОВ, для чемпиона по финалу. Начисляет очки во всех комнатах (каждая по своему коэффициенту); изменение уже введённого счёта снимает старые очки и начисляет заново (`rescore_match`) |

### Прогнозы — `/rooms/{id}/predictions`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| POST | `/rooms/{id}/predictions/batch` | Member | `{predictions:[{match_id, home, away}]}` → по каждому `{accepted, reason}` (`room_archived│deadline_passed│invalid_score│match_not_found`) |
| PUT | `/rooms/{id}/predictions/{match_id}/users/{uid}` | Superadmin (режим SA) | Прогноз за участника **без проверки дедлайна**. Работает и на завершённом матче: старые очки снимаются, начисляются заново по новому прогнозу. 409 `room_archived│invalid_score` |
| GET | `/rooms/{id}/predictions/my` | Member | Все мои прогнозы в комнате с очками |
| GET | `/rooms/{id}/predictions/tour/{date}` | Member | `{date, points, exact_count}` |
| GET | `/rooms/{id}/predictions/tour/{date}/all` | Member | Итоги тура: все участники с очками за завершённые матчи дня `[{user_id, nickname, avatar_url, points, exact_count, predictions_count, match_count, matches: [{match_id, kickoff_at, home_team, away_team, status, home_score, away_score, started, predicted_*, points_awarded, is_exact}]}]`; пропущенный прогноз = 0; чужие прогнозы на не начавшиеся матчи скрыты (`predicted_* = null`). Сортировка: очки → точные → ник. Учитывает симуляцию |

### Спецпрогнозы — `/rooms/{id}/special-prediction`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms/{id}/special-prediction/my` | Member | Мой спецпрогноз + `locked` |
| PUT | `/rooms/{id}/special-prediction` | Member | Создать/обновить. 403 после `first_match_at` или в архиве |
| GET | `/rooms/{id}/special-prediction/all` | Member | Все спецпрогнозы комнаты (после дедлайна; раскрывает раньше только суперадмин) |
| POST | `/rooms/{id}/special-prediction/scorer-result` | RAdmin | `{player_api_id, player_name}` → начислить очки за бомбардира (ЧМ) **только в этом турнире** |
| POST | `/rooms/{id}/special-prediction/leader-result` | RAdmin | `{team}` → начислить очки за лидера лиги/победителя (РПЛ/ЛЧ) **только в этом турнире** |
| GET | `/players/search?q=` | Auth | Автодополнение бомбардира (≥3 символа, API-Football) |

### Таблица лидеров — `/rooms/{id}/leaderboard`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms/{id}/leaderboard` | Member | `[{place, user_id, nickname, avatar_url, total_points, exact_scores_count, has_champion, has_scorer, champion_correct, scorer_correct, participation_confirmed, champion_team*, top_scorer_name*}]` — поля со звёздочкой видны после старта турнира. Кэш Redis 60 сек по комнате |
| GET | `/rooms/{id}/leaderboard/me` | Member | Моя строка таблицы |

### Турнирное положение (тип-зависимо) — `/rooms/{id}/standings`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms/{id}/standings` | Member | `{groups: [{name, teams, matches}], playoff: [{stage, matches}]}`, **зависит от типа**: ЧМ — группы+плей-офф (шахматки); РПЛ — одна лиговая таблица (`groups[0]`, playoff пуст); ЛЧ — швейцарская таблица общего этапа + плей-офф; custom — просто список выбранных матчей (`playoff[0].stage="Матчи"`). Считается из матчей **этого турнира**; очки 3/1/0 и разница — по завершённым; уважает симуляцию |
| GET | `/rooms/{id}/standings/top-scorers` | Member | `{updated_at, top: [{name, photo, team, goals}]×5, predicted: [{name, photo, goals, backers}]}`. Топ-5 бомбардиров турнира + игроки из спецпрогнозов **этой комнаты** (только текущих участников; с голами и числом выбравших). ID канонизируется (реальный API-ID и кураторский = один игрок), имена — русские из каталога. Голы — по real_id; для кураторских игроков без real_id реальный ID разрешается по имени при обновлении снимка (`/players/profiles`, кэш в Redis, карта `resolved` в снимке), фолбэк — по фамилии (`_surname_key`). Топ-лист API ограничен ~20 строками, поэтому снимок при обновлении дополняется статистикой выбранных участниками игроков (`/players?id=`). Из суточного снимка в Redis (`top_scorers:snapshot`), читатель к API не ходит. Обновляется кроном в 10:00 МСК и при `/admin/sync` |

### Профиль игрока — `/rooms/{id}/players`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| GET | `/rooms/{id}/players/{uid}` | Member | Место, очки, статистика попаданий (точный/разница/исход), спецпрогноз (после старта), все прогнозы (чужие будущие скрыты; свои и для RAdmin — видны) |

### Глобальный админ и суперадмин — `/admin`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| POST | `/admin/sync` | SA | Синхронизация всех активных лиг с API-Football + пересчёт + обновление снимка бомбардиров |
| POST | `/admin/sync-league` | SA | `{league_id, season}` — синхронизировать одну лигу (для панели выбора матчей кастома) |
| POST | `/admin/recalculate` | SA | Пересчитать все незакрытые очки (идемпотентно) |
| POST | `/admin/superadmin/transfer` | SA | `{target_user_id}` — передать роль |
| GET | `/admin/audit-log` | SA | `?event_type=&actor_id=&limit=50(≤200)&offset=0`, сортировка `created_at DESC` |
| GET | `/admin/audit-log/export` | SA | Те же фильтры → CSV (UTF-8 BOM, `;`-разделитель) |

### Боты — `/bots`

| Метод | Путь | Доступ | Описание |
|-------|------|--------|---------|
| POST | `/bots/vk/callback` | Pub (VK_SECRET) | VK Callback API: confirmation + `message_new`. См. **BOT_VK.md** |

Прочее: `GET /health`, `GET /` (вне `/api/v1`); статика аватаров — `GET /api/v1/media/avatars/{uid}.jpg`.

### Режим симуляции (заголовок `X-Sim-Now`)

Любой GET-запрос суперадмина может нести заголовок `X-Sim-Now: <ISO-datetime>` —
read-эндпоинты комнат (`matches`, `predictions`, `special-prediction`,
`leaderboard`, `players`) отвечают так, как выглядела бы система в этот момент
(см. раздел «Бизнес-правила → Режим симуляции»). Для не-суперадмина заголовок
молча игнорируется. **Мутации (POST/PUT/PATCH/DELETE) с этим заголовком
отклоняются middleware с 403** — режим строго read-only.

### Режим игрока по умолчанию (заголовок `X-View-As: player`)

С заголовком `X-View-As: player` room-контекст
(`require_room_member`/`require_room_admin`) считает суперадмина обычным
участником — чужие прогнозы и спецпрогнозы скрыты до дедлайна,
`members_filled/members_total` в `/matches/days` равны null, управление
комнатой отвечает 403, в комнаты без членства не пускает. Для не-суперадмина
заголовок молча игнорируется.

**Фронт шлёт этот заголовок по умолчанию** — суперадмин изначально видит сайт
как обычный игрок. Полные права включаются чекбоксом «Режим суперадмина» в
глобальной панели (фронт: `store/viewAs.ts`, ключ `admin_mode` в localStorage);
пока режим включён, заголовок не шлётся и сверху висит индиговый баннер
`ViewAsBanner` с кнопкой возврата в режим игрока. **Глобальная панель
(`require_superadmin`) заголовок не учитывает** — она доступна суперадмину
всегда, именно там живёт переключатель. Вступление в комнату без
пароля (superadmin bypass в `/rooms/{id}/join`) от заголовка тоже не зависит.

---

## Бизнес-правила

### Туры

Схема тура зависит от лиги (`services/tours.py`, чистые функции, тесты `tests/test_tours.py` + `tests/test_tournament.py`):

- **Суточная** (ЧМ): тур с **10:00 до 10:00 следующего дня по Москве (UTC+3)**, обозначается датой первого дня. Из-за разницы часовых поясов группировка по календарной дате UTC рвала бы единый вечер матчей на две даты.
- **Недельная** (лиги — РПЛ/ЛЧ/топ-5): тур = игровая неделя, обозначается датой якорного дня (РПЛ — среда, ЛЧ — суббота, топ-5 — вторник), внутри той же границы 10:00 МСК.

Дата тура хранится в `matches.match_date` и **производна от `kickoff_at`** по схеме лиги: `tour_key(kickoff, anchor)` (anchor=None — суточная; иначе снап «футбольного дня» назад к якорному дню недели). Схема лиги — `league_tour_anchor(league_id)`. Применяется при синхронизации и при создании/редактировании матча. Вся группировка по турам (`/matches/days`, `predictions/tour/{date}`, `standings`, коэффициент тура) опирается на это поле.

### Прогнозы на матч

- Объект: счёт основного времени (90 мин). Доп. время и пенальти **не учитываются**. Матч 1:1 с победой в пенальти → в системе результат 1:1.
- Дедлайн: строго до `kickoff_at`, проверяется **только на бэкенде** (`services/predictions.py::set_prediction` — общая точка для REST и ботов). До дедлайна менять можно сколько угодно.
- Исключение: **суперадмин** (в режиме SA) может задать/поправить прогноз участника и после дедлайна (`admin_set_prediction`, кнопка ✎ на странице прогнозов матча) — в том числе на завершённом матче: ранее начисленные очки снимаются с участника и начисляются заново по новому прогнозу (`score_match`). Действие пишется в журнал с `admin_override: true` и прежним счётом.
- Один прогноз на матч **в каждой комнате** (`UNIQUE(room_id, user_id, match_id)`). Повторная отправка обновляет существующий.
- Счёт 0–20. В архивной комнате прогнозы не принимаются.
- Прогнозы других скрыты до `kickoff_at`. Раскрывает только суперадмин (в «Режиме суперадмина»); **админ комнаты их не видит**.

### Спецпрогнозы

Вид спецпрогноза зависит от типа турнира (`room.special_kind`). Свои в каждом турнире; дедлайн — `room.first_match_at`. Хранятся в `special_predictions` (поле `champion_team` — универсальный «выбор команды»: чемпион ЧМ / лидер РПЛ / победитель ЛЧ; `top_scorer_*` — только ЧМ).

- **`wc` (ЧМ):** чемпион + бомбардир. Чемпион — **автоматически** при пересчёте после финала (`stage='final'` в лиге ЧМ), при любом исходе: победитель = `final.winner_team` (пенальти/допвремя), иначе по счёту ОВ. Бомбардир — **вручную по комнатам**: `POST /rooms/{id}/special-prediction/scorer-result` (RAdmin).
- **`leader` (РПЛ):** лидер лиги на финальный момент — **вручную по комнатам**: `POST /rooms/{id}/special-prediction/leader-result {team}` (RAdmin), начисляет `points_champion` угадавшим (`recalc.score_leader`).
- **`stage_or_champion` (ЛЧ):** победитель общего этапа / чемпион — так же вручную через `leader-result`.
- **`none` (custom):** спецпрогноза нет.

Начисление за команду (leader/champion вручную) идёт через один и тот же `leader-result`/`score_leader`. Спецпрогнозы других скрыты до дедлайна (раскрывает раньше только суперадмин); в таблице лидеров до старта видны только флажки «выбран/не выбран».

### Начисление очков

Базовые значения (по умолчанию, настраиваются на комнату):

| Тип | Условие | Очков |
|-----|---------|-------|
| Точный счёт | predicted = real (оба гола) | `points_exact` (5) |
| Разница мячей | (pred_h − pred_a) = (real_h − real_a) | `points_diff` (2) |
| Победитель / ничья | sign(pred_h − pred_a) = sign(real_h − real_a) | `points_outcome` (1) |
| Промах | — | 0 |
| Чемпион турнира | = победитель финала | `points_champion` (10) |
| Лучший бомбардир | = указанный админом игрок | `points_scorer` (10) |

**Коэффициент матча** (`room_match_multipliers`, 0/1/2/3) — **свойство комнаты**: задаётся админом комнаты на матч или на весь тур и действует только в его комнате (у каждой комнаты свой). Очки за матч умножаются на него. **×0 — аннулирование**: очки 0, и точный счёт не идёт в тайбрейк. Изменение коэффициента у завершённого матча пересчитывает уже начисленные очки **только в этой комнате** (`rescore_match_in_room`). Отсутствие записи = коэффициент 1.

**Тайбрейк:** (1) больше `total_points`; (2) больше `exact_scores_count`; (3) алфавит по никнейму.

### Пересчёт (services/recalc.py)

Результат матча — глобальный факт: один ввод счёта начисляет очки **во всех активных комнатах**, каждая по своим правилам. Архивные комнаты заморожены (не начисляется и не снимается).

- `score_match` — начисляет по прогнозам с `points_awarded IS NULL` (идемпотентно), коэффициент берёт из `room_match_multipliers` по комнате. Только для `status='finished'` — у live-матчей в тех же колонках текущий счёт.
- `rescore_match` — при исправлении уже введённого счёта (суперадмином): снимает прежние очки во всех активных комнатах, затем начисляет заново.
- `rescore_match_in_room` — при смене коэффициента **админом комнаты** на завершённом матче: снимает и начисляет заново только в этой комнате.
- `recalculate_all` — по всем завершённым матчам + чемпион. Вызывается из `/admin/recalculate`, `/admin/sync` и шедулера.
- Любое начисление инвалидирует Redis-кэш leaderboard.

`services/scoring.py` — **только чистые функции** без сайд-эффектов; unit-тесты (`tests/test_scoring.py`) обязательны при изменении.

### Режим симуляции (services/simulation.py)

Инструмент суперадмина «посмотреть, как будет выглядеть система» в будущий
момент (матч начался, 3 тура сыграны, турнир завершён). Управляется вкладкой
**Глобальная панель → Симуляция**; фронт хранит момент в `store/sim.ts`
(localStorage) и шлёт его заголовком `X-Sim-Now` на все запросы (кроме
`/auth/*`), сверху всех страниц висит янтарный баннер с кнопкой выхода.

Правила оверлея:
- реальный финальный счёт всегда остаётся; матч, начавшийся к sim-моменту,
  первые `MATCH_DURATION` (2 часа) идёт со статусом `live` — фейковый текущий
  счёт растёт пропорционально сыгранному времени (реальный live-счёт
  сохраняется как есть), — затем становится `finished` с **детерминированным
  фейковым** финальным счётом (из UUID матча, стабилен между запросами);
- очки начисляются **только за `finished`** (live-матчи не влияют на таблицу)
  и пересчитываются в памяти теми же чистыми функциями `scoring.py`
  (правила комнаты + коэффициент матча), таблица лидеров пересортируется;
  Redis-кэш не читается и не пишется;
- очки за чемпиона/бомбардира **не симулируются** — берутся уже начисленные
  из БД; дедлайны (kickoff, `first_match_at`) сравниваются с sim-моментом;
- **ничего не пишется**: ни БД, ни журнал; мутации с заголовком блокирует
  middleware (403); фронт также считает `now` от sim-момента
  (`utils/dates.ts::nowMs`) — отсчёты и блокировки форм соответствуют
  симулируемому времени.

Юнит-тесты — `tests/test_simulation.py` (без БД).

---

## Авторизация

### Telegram Login Widget

- Десктоп: виджет на `/login` → `POST /auth/telegram/verify` с `{id, first_name, hash, auth_date, …}`.
- Мобильные браузеры (виджет не рендерится): `GET /auth/telegram/oauth-redirect` → oauth.telegram.org → `GET /auth/telegram/callback` → redirect на `/telegram-auth?token=…`.
- Бэкенд: `HMAC-SHA256(sorted_fields, SHA256(bot_token))` → сравнить с `hash`; `auth_date` не старше 86400 сек.

### Яндекс OAuth 2.0

- Scope: `login:info, login:email, login:avatar`. CSRF `state` — Redis, 10 мин, однократный.
- Access token возвращается фронту во fragment (`#access_token=…`), refresh — httpOnly cookie.

### VK (только привязка, не вход)

- Кнопка в профиле → `POST /auth/vk/link-code` → одноразовый код (Redis, 10 мин) → пользователь отправляет код VK-боту → запись в `oauth_accounts` с `provider='vk'`.

### JWT

- Access: HS256, 15 минут, payload `{sub, nickname, system_role, type:'access'}`.
- Refresh: 30 дней, `httpOnly Secure(prod) SameSite=Lax` cookie.
- Роли в комнате токену не доверяются — `require_room_member`/`require_room_admin` перечитывают `room_members` из БД на каждый запрос.

---

## Пользовательские сценарии

### Первый вход
1. Аноним попадает в **публичное лобби** `/rooms` — список комнат виден без входа; окно авторизации (AuthModal) появляется при попытке действия.
2. OAuth (Telegram / Яндекс) → JWT; `is_new_user=true` → `/setup-profile` (никнейм).
3. В лобби найти комнату по названию → вступить по паролю комнаты (выдаётся админом лично). Суперадмин входит без пароля.
4. Корень `/` редиректит: аноним → `/rooms`; участник одной комнаты или с сохранённым `last_room_id` → сразу в комнату; иначе → лобби.

### Прогноз
`/room/:roomId` (вкладки: таблица / прогнозы) → тур → счёт (степпер 0–20) → `POST …/predictions/batch`. После kickoff форма блокируется.

### Ввод результата (глобальный админ)
Глобальная панель `/admin` → Матчи → счёт основного времени → автопересчёт всех комнат. Исправление счёта допустимо — очки пересчитаются (`match_result_updated` в журнале).

### Данные обновляются сами
Фронт перезапрашивает данные каждые 5 минут (TanStack Query refetch); APScheduler опрашивает API-Football каждые 5 минут в игровые дни (см. ниже).

---

## Интерфейс

SPA, левый sidebar (на мобиле — нижняя панель). Иерархия:

```
/rooms (публичное лобби)
/login, /auth/callback, /telegram-auth, /setup-profile
/profile                     — никнейм, аватар, привязка VK
/admin/*                     — глобальная панель (только SA): матчи/результаты,
                               синхронизация, пересчёт, журнал, симуляция
/room/:roomId                — комната: таблица лидеров + спецпрогнозы + туры
/room/:roomId/tour/:date     — матчи дня
/room/:roomId/match/:id/predict
/room/:roomId/match/:id/predictions
/room/:roomId/player/:userId — профиль игрока в комнате
/room/:roomId/admin/*        — управление комнатой (RAdmin): участники, пароль, регламент,
                               коэффициенты матчей, итоговый бомбардир
```

---

## Безопасность

- **Пароли комнат:** bcrypt. Никогда не возвращаются в ответах API.
- **OAuth-токены в БД:** Fernet. Ключ — только в `.env`.
- **JWT:** HS256, secret ≥ 32 байта.
- **CSRF OAuth:** `state` в Redis, 10 мин, однократный.
- **Telegram:** HMAC + `auth_date` ≤ 86400 сек.
- **VK Callback:** проверка `VK_SECRET` в каждом событии.
- **Дедлайн прогноза:** только на бэкенде. Фронтенд — UX-подсказка.
- **Rate limiting:** slowapi, 200 req/min на IP (глобальный default).
- **Секреты:** `.env` + pydantic-settings. В git — только `.env.example`.

---

## Производительность

- Leaderboard → Redis-кэш 60 сек **по комнате** (`leaderboard_cache_key(room_id)`), инвалидация при любом начислении.
- Индексы: `matches(match_date)`, `matches(kickoff_at)`, `predictions(room_id, match_id)`, `predictions(room_id, user_id)`, `room_members(room_id, total_points, exact_scores_count)`, `rooms(name)`.
- APScheduler: тик каждые 5 мин, но внутри — дешёвая проверка по БД (`_should_poll`): опрос API-Football только если сегодня есть матч, есть live-матч или недавно начавшийся. Ежедневный полный синк в 03:00 UTC (с подтяжкой букв групп из /standings). Снимок бомбардиров (`/players/topscorers` → Redis `top_scorers:snapshot`) обновляется кроном в 07:00 UTC (10:00 МСК) и при `/admin/sync`; читатель к API не ходит.
- Без `API_FOOTBALL_KEY` шедулер отключён — ручной ввод результатов остаётся.

---

## Переменные окружения

Актуальный список — `backend/.env.example`. Группы: `DATABASE_URL`, `REDIS_URL`; JWT (`SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`); Telegram (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`); Яндекс (`YANDEX_CLIENT_ID/SECRET/REDIRECT_URI`); VK-бот (`VK_GROUP_TOKEN`, `VK_GROUP_ID`, `VK_CONFIRMATION`, `VK_SECRET`, `VK_API_VERSION`); API-Football (`API_FOOTBALL_KEY`, `API_FOOTBALL_LEAGUE_ID`, `API_FOOTBALL_SEASON`); `FERNET_KEY`; `FRONTEND_URL`, `ENVIRONMENT`.

Фронтенд (build-time): `VITE_API_BASE`, `VITE_TELEGRAM_BOT`.

---

## Инварианты (нельзя нарушать)

1. **Дедлайн прогноза проверяется только на бэкенде** — единая точка `set_prediction`.
2. **Доп. время и пенальти не учитываются в прогнозах и очках** — счёт ET/PKS нигде не хранится. Единственное исключение — `matches.winner_team` (кто прошёл дальше, без счёта): читается только при начислении чемпиона по финалу.
3. **Суперадмин назначается атомарно** (LOCK TABLE) и всегда ровно один.
4. **audit_log — только запись.**
5. **Пароли комнат не возвращаются в API.**
6. **Чужие прогнозы — строго после kickoff**, спецпрогнозы — после `first_match_at`. Раньше дедлайна их раскрывает **только суперадмин** (в режиме SA); **админ комнаты — нет** (видит как обычный игрок).
7. **scoring.py — чистые функции**, тесты обязательны.
8. **Архивная комната заморожена**: не принимает прогнозы и не участвует в начислении/снятии очков.
9. **Результат матча глобален и вводится только суперадмином** — один счёт затрагивает все активные турниры над этой лигой (каждый по своему коэффициенту); правки кода пересчёта обязаны сохранять идемпотентность. **Коэффициент матча и итоговый бомбардир/лидер — по турнирам** (`room_match_multipliers`, `/scorer-result`, `/leader-result`), ими управляет админ комнаты только в своём турнире.
11. **Матчи скоупятся по турниру.** Любое чтение матчей в контексте турнира обязано проходить через `tournament_match_conditions(room)` (или `_get_tournament_match`) — иначе в турнир протечёт чужая лига. Глобальны только: `recalculate_all`, синк, `/matches` (админ-список суперадмина), `_should_poll`.
10. **Режим симуляции строго read-only**: ни одной записи в БД/журнал/кэш; мутации с заголовком `X-Sim-Now` отклоняются; для не-суперадмина заголовок игнорируется.

---

*Prediction Site · AGENTS.md · v6.0 (платформа турниров: ЧМ/РПЛ/ЛЧ/custom, июль 2026)*
