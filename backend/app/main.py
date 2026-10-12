"""
GhostWatt — app/main.py
FastAPI application entry point.
- CORS configured for Vite dev server (http://localhost:5173)
- Routes registered with prefixes
- Tables created on startup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import create_all_tables

# ---- Import routers (stubs imported now; real logic added per phase) ----
from app.routes import auth, dashboard, electricity, ghost_load, rooms, timetable
from app.routes import savings, water, complaints, reports, app_settings, simulator, assistant

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
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    create_all_tables()


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
app.include_router(ghost_load.router,   prefix="/ghost-load",  tags=["Ghost Load"])
app.include_router(rooms.router,        prefix="/rooms",       tags=["Rooms"])
app.include_router(timetable.router,    prefix="/timetable",   tags=["Timetable"])
app.include_router(savings.router,      prefix="/savings",     tags=["Savings"])
app.include_router(water.router,        prefix="/water",       tags=["Water"])
app.include_router(complaints.router,   prefix="/complaints",  tags=["Complaints"])
app.include_router(reports.router,      prefix="/reports",     tags=["Reports"])
app.include_router(app_settings.router, prefix="/settings",    tags=["Settings"])
app.include_router(simulator.router,    prefix="/simulator",   tags=["Simulator"])
app.include_router(assistant.router,    prefix="/assistant",   tags=["Assistant"])
