"""
Eco-Campus - app/main.py
FastAPI application entry point.
- CORS origins come from CORS_ORIGINS (defaults to the Vite dev / preview servers)
- Background simulation worker started on startup (runs off the event loop)
- Tables are created / migrated on startup
- Routes registered both at the root and under /api (so the Vite proxy and direct calls both work)
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.db.database import SessionLocal, create_all_tables
from app.services.simulator import (
    calculate_sleep_duration,
    get_or_create_sim_state,
    restore_overrides_from_actions,
    tick,
)

# ---- Import routers ----
from app.routes import auth, dashboard, electricity, ghost_load, rooms, timetable
from app.routes import savings, water, complaints, reports, app_settings, simulator, assistant, live, actions, leaderboard

log = logging.getLogger("eco_campus")

# ---------------------------------------------------------------------------
# Background simulation task & lifespan
# ---------------------------------------------------------------------------
_sim_task: Optional[asyncio.Task] = None


def _advance_clock_once() -> float:
    """Blocking work for one background iteration. Returns how long to sleep afterwards."""
    with SessionLocal() as db:
        state = get_or_create_sim_state(db)
        if state.running:
            tick(db, delta_minutes=15)
        return calculate_sleep_duration(state.speed)


async def run_simulation_background_task():
    """Advance the virtual clock while the simulator is running (DB work happens in a thread)."""
    while True:
        try:
            sleep_sec = await asyncio.to_thread(_advance_clock_once)
            await asyncio.sleep(sleep_sec)
        except asyncio.CancelledError:
            break
        except Exception:  # keep the clock alive, but never swallow the reason silently
            log.exception("Simulation tick failed; retrying in 2s")
            await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all_tables()
    with SessionLocal() as db:
        get_or_create_sim_state(db)
        restored = restore_overrides_from_actions(db)
        if restored:
            log.info("Restored %d appliance switch-off(s) after restart", restored)
    global _sim_task
    _sim_task = asyncio.create_task(run_simulation_background_task())
    yield
    if _sim_task:
        _sim_task.cancel()
        try:
            await _sim_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Campus Energy & Sustainability Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


# ---------------------------------------------------------------------------
# Health check - no auth required
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"], include_in_schema=False)
def health():
    db_ok = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "version": settings.app_version,
        "app": settings.app_name,
        "mode": "demo" if settings.demo_mode else "standard",
    }


# ---------------------------------------------------------------------------
# Consistent JSON error responses for uncaught exceptions
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_message": str(exc) if settings.debug else "An unexpected internal server error occurred.",
            "data_source": "simulated",
        },
    )


# ---------------------------------------------------------------------------
# Static files - complaint photographs (served from backend/uploads regardless of cwd)
# ---------------------------------------------------------------------------
uploads_dir = str(settings.uploads_path)
os.makedirs(os.path.join(uploads_dir, "complaints"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# ---------------------------------------------------------------------------
# Routers (registered both at root and with /api prefix for proxy transparency)
# ---------------------------------------------------------------------------
api_routers = [
    (auth.router, "/auth", ["Auth"]),
    (dashboard.router, "/dashboard", ["Dashboard"]),
    (electricity.router, "/electricity", ["Electricity"]),
    (ghost_load.router, "/ghost", ["Ghost Load"]),
    (ghost_load.router, "/ghost-load", ["Ghost Load"]),
    (rooms.router, "/rooms", ["Rooms"]),
    (timetable.router, "/timetable", ["Timetable"]),
    (actions.router, "/actions", ["Actions"]),
    (savings.router, "/savings", ["Savings"]),
    (water.router, "/water", ["Water"]),
    (complaints.router, "/complaints", ["Complaints"]),
    (reports.router, "/reports", ["Reports"]),
    (app_settings.router, "/settings", ["Settings"]),
    (simulator.router, "/sim", ["Simulator"]),
    (simulator.router, "/simulator", ["Simulator"]),
    (live.router, "/live", ["Live"]),
    (assistant.router, "/assistant", ["Assistant"]),
    (leaderboard.router, "/leaderboard", ["Leaderboard"]),
]

for router_obj, prefix, router_tags in api_routers:
    app.include_router(router_obj, prefix=prefix, tags=list(router_tags))  # type: ignore[arg-type]
    app.include_router(router_obj, prefix=f"/api{prefix}", tags=list(router_tags))  # type: ignore[arg-type]
