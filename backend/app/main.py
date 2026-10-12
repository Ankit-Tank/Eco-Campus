"""
GhostWatt — app/main.py
FastAPI application entry point.
- CORS configured for Vite dev server (http://localhost:5173)
- Background simulation worker started on startup
- Routes registered with prefixes
- Tables created on startup
"""
import asyncio
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import SessionLocal, create_all_tables
from app.services.simulator import calculate_sleep_duration, get_or_create_sim_state, tick

# ---- Import routers ----
from app.routes import auth, dashboard, electricity, ghost_load, rooms, timetable
from app.routes import savings, water, complaints, reports, app_settings, simulator, assistant, live, actions, leaderboard

from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Background Simulation Task & Lifespan
# ---------------------------------------------------------------------------
_sim_task: Optional[asyncio.Task] = None


async def run_simulation_background_task():
    """Background asyncio worker advancing the virtual clock when active."""
    while True:
        try:
            with SessionLocal() as db:
                state = get_or_create_sim_state(db)
                if state.running:
                    tick(db, delta_minutes=15)
                speed = state.speed
            sleep_sec = calculate_sleep_duration(speed)
            await asyncio.sleep(sleep_sec)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all_tables()
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
# CORS — allow the Vite frontend dev server
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "app": settings.app_name,
        "mode": "demo",
    }


# ---------------------------------------------------------------------------
# Consistent JSON Error Responses for uncaught exceptions
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_message": str(exc) if settings.debug else "An unexpected internal server error occurred.",
            "data_source": "simulated",
        },
    )


# ---------------------------------------------------------------------------
# Static Files — uploads for complaints
# ---------------------------------------------------------------------------
import os
from fastapi.staticfiles import StaticFiles

uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# ---------------------------------------------------------------------------
# Routers (Registered both at root and with /api prefix for proxy transparency)
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

