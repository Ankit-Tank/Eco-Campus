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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import SessionLocal, create_all_tables
from app.services.simulator import calculate_sleep_duration, get_or_create_sim_state, tick

# ---- Import routers ----
from app.routes import auth, dashboard, electricity, ghost_load, rooms, timetable
from app.routes import savings, water, complaints, reports, app_settings, simulator, assistant, live

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Campus Energy & Sustainability Platform",
    docs_url="/docs",
    redoc_url="/redoc",
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
# Background Simulation Task
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


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    create_all_tables()
    global _sim_task
    _sim_task = asyncio.create_task(run_simulation_background_task())


@app.on_event("shutdown")
async def on_shutdown():
    global _sim_task
    if _sim_task:
        _sim_task.cancel()
        try:
            await _sim_task
        except asyncio.CancelledError:
            pass


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
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router,         prefix="/auth",        tags=["Auth"])
app.include_router(dashboard.router,    prefix="/dashboard",   tags=["Dashboard"])
app.include_router(electricity.router,  prefix="/electricity", tags=["Electricity"])
app.include_router(ghost_load.router,   prefix="/ghost",       tags=["Ghost Load"])
app.include_router(ghost_load.router,   prefix="/ghost-load",  tags=["Ghost Load"])
app.include_router(rooms.router,        prefix="/rooms",       tags=["Rooms"])
app.include_router(timetable.router,    prefix="/timetable",   tags=["Timetable"])
app.include_router(savings.router,      prefix="/savings",     tags=["Savings"])
app.include_router(water.router,        prefix="/water",       tags=["Water"])
app.include_router(complaints.router,   prefix="/complaints",  tags=["Complaints"])
app.include_router(reports.router,      prefix="/reports",     tags=["Reports"])
app.include_router(app_settings.router, prefix="/settings",    tags=["Settings"])
app.include_router(simulator.router,    prefix="/sim",         tags=["Simulator"])
app.include_router(simulator.router,    prefix="/simulator",   tags=["Simulator"])
app.include_router(live.router,         prefix="/live",        tags=["Live"])
app.include_router(assistant.router,    prefix="/assistant",   tags=["Assistant"])
