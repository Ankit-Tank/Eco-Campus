# Eco-Campus 

Intelligent campus sustainability platform for monitoring electricity and water usage, detecting ghost loads, verifying savings, and supporting maintenance workflows with a grounded AI assistant.

## Highlights

- Ghost load detection using timetable-aware expected demand models
- Verified savings tracking after corrective actions
- Night-flow water leak detection and alerts
- Student reporting + admin triage workflows
- Role-based access control (admin/student)
- React dashboard with mock mode and backend-integrated mode
- Grounded assistant integration via Groq API

## Tech Stack

### Backend
- Python, FastAPI, SQLAlchemy, SQLite
- JWT auth (`python-jose`), password hashing (`passlib`)
- Data processing with Pandas/NumPy
- Test suite with `pytest`

### Frontend
- React + Vite
- Recharts + Lucide icons
- Plain CSS, modular services, i18n support (EN/HI)

## Repository Structure

```text
Eco-Campus/
├── backend/
│   ├── app/
│   │   ├── core/        # config, auth, dependencies
│   │   ├── db/          # engine + ORM models
│   │   ├── routes/      # API routes by domain
│   │   ├── schemas/     # request/response models
│   │   └── services/    # business logic and analytics
│   ├── scripts/         # seed script
│   ├── tests/           # backend test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/       # admin/student pages
│   │   ├── services/    # API + mock services
│   │   ├── components/  # reusable UI blocks
│   │   ├── auth/        # route guards/session helpers
│   │   └── i18n/        # language resources
│   └── package.json
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md
│   └── SPEC.md
└── README.md
```

## Quick Start

## 1) Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed
uvicorn app.main:app --reload --port 8000
```

Backend URLs:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 2) Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL:
- App: `http://localhost:5173`

## Frontend Run Modes

- `VITE_USE_MOCK=true`: run UI with mock data only
- `VITE_USE_MOCK=false`: call FastAPI backend via `/api` proxy
- `VITE_DEMO_MODE=true`: prefilled demo login/OTP hints for demos

## Demo Accounts (seeded backend)

- Admin: `admin@ghostwatt.demo` / `admin123`
- Student: `student@ghostwatt.demo` / `student123`

## Core Backend Domains

- `auth`: login, profile, and token handling
- `dashboard`: sustainability summary and KPI endpoints
- `electricity` / `ghost_load`: consumption + anomaly intelligence
- `water`: leak analysis and alerts
- `reports` / `complaints`: reporting workflows
- `actions` / `savings`: switch-off actions and savings verification
- `simulator` / `live`: virtual-time demo orchestration
- `assistant`: grounded assistant APIs
- `leaderboard`: block-level sustainability ranking

## Testing

From `backend/`:

```bash
pytest -v
```

## Documentation

- Architecture: `/docs/ARCHITECTURE.md`
- API reference: `/docs/API.md`
- System specification: `/docs/SPEC.md`
- Demo script: `/docs/DEMO_SCRIPT.md`
- Libraries and models: `/LIBRARIES.md`

## License

This project is licensed under the terms in `/LICENSE`.
