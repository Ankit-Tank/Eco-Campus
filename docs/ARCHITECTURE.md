# GhostWatt — Architecture Overview

> **Rule:** Read this file and docs/SPEC.md before starting any task.

## Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11+, FastAPI, Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Data processing | Pandas, NumPy |
| AI Assistant | Groq API (server-side only) |
| File uploads | python-multipart |
| HTTP client | httpx |
| Testing | pytest |
| Frontend (later) | React + Vite, Recharts, Lucide |

## Folder Layout

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic Settings — reads .env
│   │   ├── security.py          # JWT encode/decode, password hashing
│   │   └── deps.py              # Reusable FastAPI dependencies (get_db, get_current_user)
│   ├── db/
│   │   ├── database.py          # SQLAlchemy engine, SessionLocal, Base
│   │   └── models.py            # ORM table definitions (all entities)
│   ├── schemas/                 # Pydantic request/response models (one file per domain)
│   ├── routes/                  # Thin HTTP handlers — call services, return schemas
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── electricity.py
│   │   ├── ghost_load.py
│   │   ├── rooms.py
│   │   ├── timetable.py
│   │   ├── savings.py
│   │   ├── water.py
│   │   ├── complaints.py
│   │   ├── reports.py
│   │   ├── settings.py
│   │   ├── simulator.py
│   │   └── assistant.py
│   └── services/                # Pure functions — NO FastAPI imports
│       ├── expected_demand.py   # Timetable-based expected kW per interval
│       ├── ghost_load.py        # Ghost Load = max(0, actual - expected)
│       ├── savings_verification.py  # Pre/post action average comparison
│       ├── water_analysis.py    # Night-flow leak detection
│       ├── carbon_calculator.py # kWh → CO₂, kWh → fan equivalents
│       ├── simulator.py         # Appliance toggle, reading injection
│       ├── data_generator.py    # Seed rooms, timetables, readings
│       ├── report_builder.py    # Aggregate data into report dicts
│       ├── assistant_tools.py   # Approved data-fetch functions for Groq
│       └── groq_assistant.py    # Groq API call with grounded context
├── scripts/
│   └── seed.py                  # CLI: python scripts/seed.py
├── data/generated_sample_data/  # CSV/JSON output from data_generator
├── uploads/complaints/          # Uploaded complaint photos
└── tests/
    ├── test_ghost_load.py
    ├── test_savings_verification.py
    ├── test_water_analysis.py
    └── test_permissions.py
```

## Data Flow

### Ghost Load Calculation
```
MeterReading (actual_demand_kw)
        │
        ▼
expected_demand.get_expected_kw(room_id, timestamp)
   uses: Timetable, Room.equipment_config, Settings (factors)
        │
        ▼
ghost_load.calculate(actual, expected)
   → ghost_kw = max(0, actual - expected)
   → ghost_kwh = ghost_kw * 0.25
   → cost = ghost_kwh * settings.electricity_price_per_kwh
   → co2  = ghost_kwh * settings.emissions_factor_kg_per_kwh
```

### Verified Savings Flow
```
User clicks "Mark Switched Off"
        │
        ▼
POST /simulator/action  → Action record created
        │
        ▼
savings_verification.verify(action_id, db)
   pre_avg  = mean(actual_demand_kw, 15 min before action)
   post_avg = mean(actual_demand_kw, 15 min after action)
   reduction = max(0, pre_avg - post_avg)
   credited_kwh = reduction * 0.25
        │
        ▼
SavingsRecord persisted (verification_status = "verified" | "no_reduction")
```

### AI Assistant Flow
```
POST /assistant/ask  { "question": "..." }
        │
        ▼
groq_assistant.answer(question, user_role, db)
   1. Map question → approved assistant_tools function
   2. Call function → structured data dict (real DB values)
   3. Build grounded prompt: data dict + question
   4. Call Groq API with grounded prompt
   5. Return { answer, data_used, grounded: true }
   (fallback: return canned answer if Groq unavailable)
```

## Key Rules

1. **Services are pure functions** — no FastAPI `Request`, `Depends`, or `Response` imports.
2. **Never hardcode prices or factors** — always read from the `settings` DB table via `config.py`.
3. **Simulated data is always labelled** — every `MeterReading` has `is_simulated: bool`.
4. **Groq never invents data** — all numbers come from the DB; Groq only narrates.
5. **Role checks in routes** — use `deps.require_admin` and `deps.require_student` decorators.
