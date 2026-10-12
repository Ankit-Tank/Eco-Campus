# GhostWatt

**Intelligent Campus Energy & Sustainability Platform**

> Detect Waste. Save Energy. Build a Greener Campus.

GhostWatt is a hackathon MVP (Kaushal 8.0) that identifies unnecessary campus electricity consumption, verifies real savings, monitors water usage, and answers sustainability questions through a Groq-powered AI assistant.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (frontend — built in a later phase)

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set GROQ_API_KEY and JWT_SECRET

python scripts/seed.py          # generate rooms, timetables, readings

uvicorn app.main:app --reload   # http://localhost:8000
# Interactive API docs: http://localhost:8000/docs
```

---

## Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | admin@ghostwatt.demo | admin123 |
| Student | student@ghostwatt.demo | student123 |

---

## Simulated Data Disclaimer

All electricity meter readings, water flow records, and campus timetables used in this application are **programmatically generated for demonstration purposes**. They are NOT measurements from real campus infrastructure. Every simulated reading is labelled `is_simulated: true` in the database and the API responses.

Ghost Load figures, savings calculations, and carbon estimates are derived from these simulated readings using configurable factors (see Settings page). They are modelling approximations, not audited energy assessments.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (never expose to browser) |
| `GROQ_MODEL` | Groq model name, e.g. `llama3-8b-8192` |
| `JWT_SECRET` | Long random string for JWT signing |
| `DB_URL` | SQLAlchemy DB URL (default: SQLite) |

---

## Carbon Calculation Assumptions

- Default electricity price: ₹8.50 per kWh (configurable)
- Default emissions factor: 0.71 kg CO₂ per kWh (configurable)
- Fan equivalent: 75 W per ceiling fan
- Bucket equivalent: 15 litres per bucket (configurable)

These are initial modelling values. Actual campus tariffs and grid emission factors vary.

---

## Future Integrations

- Real-time electricity meters via Modbus or MQTT
- Water flow sensors via IoT gateway
- Campus ERP timetable sync (REST/webhook)
- Building Management System (BACnet/API)
- Push notifications (FCM or email)

---

## See Also

- [docs/SPEC.md](docs/SPEC.md) — Full product specification
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Stack and data flow
- [docs/API.md](docs/API.md) — API endpoint reference
- [LIBRARIES.md](LIBRARIES.md) — All external libraries and APIs used
