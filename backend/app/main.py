from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.routers import (
    admin,
    auth,
    leaderboard,
    matches,
    predictions,
    rooms,
    special,
)
from app.services.scheduler import start_scheduler, stop_scheduler

# Global default rate limit (per IP). Auth/predictions are the sensitive paths;
# 200/min comfortably covers normal leaderboard polling while capping abuse.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="ЧМ-2026 Prediction API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"
app.include_router(auth.router, prefix=API_V1)
app.include_router(rooms.router, prefix=API_V1)
app.include_router(matches.room_router, prefix=API_V1)
app.include_router(matches.admin_router, prefix=API_V1)
app.include_router(predictions.router, prefix=API_V1)
app.include_router(special.router, prefix=API_V1)
app.include_router(special.players_router, prefix=API_V1)
app.include_router(leaderboard.router, prefix=API_V1)
app.include_router(admin.router, prefix=API_V1)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/")
async def root():
    return {"name": "ЧМ-2026 Prediction API", "docs": "/docs"}
