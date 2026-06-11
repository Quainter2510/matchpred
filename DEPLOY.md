# 🚀 Размещение на сервере · ЧМ-2026

Инструкция по развёртыванию на сервере. Два пути:

- **Вариант A — VPS + Docker Compose** (рекомендуется для переноса на свой сервер).
- **Вариант B — Railway.app** (как в спецификации, managed-хостинг).

ЧМ стартует **11 июня 2026**. Деплой нужно завершить минимум за 5 дней до старта.

---

## 0. Что нужно подготовить заранее

| Что | Где взять |
|-----|-----------|
| Сервер (Ubuntu 22.04+, 1 vCPU / 1 GB RAM минимум) | любой VPS-провайдер |
| Домен с DNS-записью на IP сервера | регистратор домена |
| Telegram-бот (token + username) | [@BotFather](https://t.me/BotFather) → `/newbot` |
| Яндекс OAuth-приложение (client_id + secret) | https://oauth.yandex.ru/client/new |
| API-Football ключ | https://www.api-football.com (план с доступом к World Cup) |

### Секреты, которые нужно сгенерировать

```bash
# SECRET_KEY (JWT, ≥32 байта)
openssl rand -hex 32

# FERNET_KEY (шифрование OAuth-токенов)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Вариант A — VPS + Docker Compose

### A1. Установить Docker на сервере

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # перелогиниться после этой команды
```

### A2. Перенести проект на сервер

```bash
# с локальной машины
scp -r ./matchpred user@SERVER_IP:/opt/matchpred
# или: git clone <repo> /opt/matchpred
cd /opt/matchpred
```

### A3. Заполнить переменные окружения бэкенда

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Минимально обязательные значения:

```env
DATABASE_URL=postgresql+asyncpg://wc2026:wc2026@db:5432/wc2026
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<openssl rand -hex 32>
FERNET_KEY=<сгенерированный Fernet ключ>

TELEGRAM_BOT_TOKEN=<токен бота>
TELEGRAM_BOT_USERNAME=<username бота без @>

YANDEX_CLIENT_ID=<client id>
YANDEX_CLIENT_SECRET=<client secret>
YANDEX_REDIRECT_URI=https://ВАШ_ДОМЕН/api/v1/auth/yandex/callback

API_FOOTBALL_KEY=<ключ>
API_FOOTBALL_LEAGUE_ID=1      # FIFA World Cup; проверьте актуальный id в API
API_FOOTBALL_SEASON=2026

FRONTEND_URL=https://ВАШ_ДОМЕН
ENVIRONMENT=production
```

> ⚠️ `FRONTEND_URL` обязан совпадать с реальным доменом — он используется в CORS
> и в редиректе после Яндекс-логина.

### A4. Указать домен для сборки фронтенда

Vite «запекает» адрес API в бандл на этапе сборки. Передайте его через переменные
окружения compose (или создайте `.env` в корне рядом с `docker-compose.yml`):

```bash
# /opt/matchpred/.env  (читается docker compose)
VITE_API_BASE=https://ВАШ_ДОМЕН/api/v1
VITE_TELEGRAM_BOT=<username бота без @>
```

### A5. Запустить стек

```bash
docker compose up --build -d
docker compose ps          # все сервисы healthy
docker compose logs -f backend
```

Контейнер бэкенда сам выполняет `alembic upgrade head` при старте (см. `CMD` в
`backend/Dockerfile`). Проверить: `docker compose exec backend alembic current`.

### A6. Загрузить расписание ЧМ и создать турнир

```bash
docker compose exec backend python -m scripts.seed
```

Скрипт загрузит матчи из API-Football, создаст первую комнату
(`first_match_at` = время самого раннего матча) и **выведет временный пароль
комнаты** — сохраните его, потом смените в панели. Остальные комнаты суперадмин
создаёт из интерфейса.

> Если матчей ЧМ-2026 ещё нет в вашем тарифе API-Football (расписание
> публикуется ближе к турниру), скрипт сообщит, сколько фикстур вернул API.
> Можно создать комнату без матчей, задав дедлайн спецпрогнозов вручную, а матчи
> добавить позже через **Админ → Синхронизировать** или повторный seed:
> ```bash
> docker compose exec backend python -m scripts.seed --first-match-at 2026-06-11T16:00:00+00:00
> ```
> Если же фикстуры должны быть, но API вернул 0 — проверьте `API_FOOTBALL_KEY`,
> `API_FOOTBALL_LEAGUE_ID` и `API_FOOTBALL_SEASON` (теперь seed печатает ошибку API).

### A7. Поставить HTTPS-реверс-прокси (Caddy — проще всего)

`docker compose` отдаёт фронтенд на `:5173`, бэкенд на `:8000`. Поставьте перед
ними прокси с автоматическим Let's Encrypt. Пример `Caddyfile`:

```
ВАШ_ДОМЕН {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /docs* {
        reverse_proxy localhost:8000
    }
    handle {
        reverse_proxy localhost:5173
    }
}
```

```bash
sudo apt install -y caddy
sudo nano /etc/caddy/Caddyfile   # вставить блок выше
sudo systemctl restart caddy
```

Caddy сам получит TLS-сертификат. Теперь сайт доступен по `https://ВАШ_ДОМЕН`.

> Альтернатива — Nginx + certbot. Главное: `/api/*` → backend:8000, остальное →
> frontend:5173, и весь трафик по HTTPS (иначе httpOnly Secure cookie не работает).

---

## Вариант B — Railway.app

1. Создайте проект на [railway.app](https://railway.app), добавьте плагины
   **PostgreSQL** и **Redis** — они дадут `DATABASE_URL` и `REDIS_URL`.
   > Railway отдаёт `postgresql://…`; замените схему на
   > `postgresql+asyncpg://…` в переменной `DATABASE_URL` сервиса бэкенда.
2. **Backend service**: деплой из папки `backend/` (Dockerfile определится
   автоматически). Пропишите все переменные из `backend/.env.example`. Railway
   даёт HTTPS-домен автоматически (Let's Encrypt). Миграции выполнятся при старте.
3. **Frontend service**: деплой из папки `frontend/`. Задайте build-args
   `VITE_API_BASE=https://<backend-домен>/api/v1` и `VITE_TELEGRAM_BOT`.
4. Seed: в Railway → backend service → откройте shell и выполните
   `python -m scripts.seed`.

---

## 1. Настройка OAuth callback-URL (обязательно)

### Яндекс
Консоль приложения → **Redirect URI**:
```
https://ВАШ_ДОМЕН/api/v1/auth/yandex/callback
```
Скоупы: `login:info`, `login:email`, `login:avatar`. Тот же URL — в `.env`
(`YANDEX_REDIRECT_URI`).

### Telegram
В [@BotFather](https://t.me/BotFather) → `/setdomain` → укажите `ВАШ_ДОМЕН`.
Login Widget работает только с привязанным к боту доменом.

---

## 2. Первый запуск, суперадмин и комнаты

1. Откройте `https://ВАШ_ДОМЕН` → войдите через Telegram или Яндекс.
2. **Первый вошедший автоматически становится суперадмином** (назначается
   атомарно, без seed-скриптов и переменных окружения). Он вводит никнейм и
   попадает на экран **«Комнаты»**.
3. `scripts.seed` уже создал стартовую комнату с временным паролем (он напечатан
   в выводе seed). Суперадмин может:
   - открыть её в разделе **Комнаты → Управление → Пароль комнаты** и сменить
     пароль на постоянный;
   - и/или **создать новые комнаты** прямо на экране «Комнаты» (только суперадмин),
     каждой задать своё имя и пароль.
4. Раздайте пароль(и) комнат участникам **лично** (вне системы). Игроки заходят,
   на экране **«Комнаты»** находят нужную по названию и вступают по её паролю.
   Один участник может состоять в нескольких комнатах — прогнозы в каждой свои.

> **Кто вводит результаты.** Матчи и счёт — общие для всех комнат. Результат
> вводит суперадмин или админ любой комнаты в **Глобальной панели → Матчи и
> результаты**; пересчёт очков применяется ко всем комнатам сразу.

> **Миграция существующей установки.** При обновлении одно-турнирной версии
> `alembic upgrade head` (выполняется автоматически при старте контейнера)
> переносит прежний турнир в первую комнату вместе с участниками, прогнозами и
> спецпрогнозами — данные не теряются.

---

## 3. Чек-лист готовности к старту

- [ ] `backend/.env` заполнен, все секреты сгенерированы
- [ ] HTTPS работает (`https://ВАШ_ДОМЕН`), cookie ставятся как Secure
- [ ] `alembic current` показывает последнюю ревизию — head (миграции применены)
- [ ] `python -m scripts.seed` выполнен — матчи загружены, первая комната создана
- [ ] Redirect URI прописаны в консолях Яндекс и Telegram
- [ ] Первый вход выполнен → пользователь стал суперадмином
- [ ] Суперадмин установил постоянный пароль комнаты
- [ ] Пароли комнат розданы участникам вне системы
- [ ] (если нужен VK-бот) Callback API подтверждён — см. [BOT_VK.md](BOT_VK.md)
- [ ] `GET https://ВАШ_ДОМЕН/health` отвечает `{"status":"ok"}`

---

## 4. Эксплуатация

| Задача | Команда |
|--------|---------|
| Логи бэкенда | `docker compose logs -f backend` |
| Применить миграции вручную | `docker compose exec backend alembic upgrade head` |
| Повторная синхронизация матчей | панель **Админ → Матчи → Синхронизировать**, либо `scripts.seed` |
| Ввести результат вручную | панель **Админ → Матчи → Ввести счёт** (резерв, если API отстаёт) |
| Пересчитать очки | панель **Админ → Пересчёт** (идемпотентно) |
| Начислить за бомбардира | панель **Админ → Спецпрогнозы** после финала |
| Бэкап БД | `docker compose exec db pg_dump -U wc2026 wc2026 > backup.sql` |

**Автоматика:** APScheduler опрашивает API-Football каждые 5 минут в дни с
матчами (в остальные дни — раз в сутки) и автоматически пересчитывает очки по
завершённым матчам. Очки за чемпиона начисляются при пересчёте после ввода счёта
финала; очки за бомбардира — вручную через панель.

---

## 5. Частые проблемы

| Симптом | Причина / решение |
|---------|-------------------|
| После Яндекс-логина редирект «в никуда» | `FRONTEND_URL` и `VITE_API_BASE` не совпадают с реальным доменом |
| `Invalid state` на callback | Redis недоступен (state хранится в Redis 10 мин) |
| Telegram-виджет не появляется | не задан `VITE_TELEGRAM_BOT`, либо домен не привязан в BotFather |
| Cookie refresh не сохраняется | сайт открыт по HTTP, а не HTTPS (нужен Secure-контекст) |
| Синхронизация падает | неверный `API_FOOTBALL_KEY` или `API_FOOTBALL_LEAGUE_ID` |
| 403 на админских ручках | пользователь не суперадмин/админ турнира |
