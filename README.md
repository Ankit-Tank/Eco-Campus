# GhostWatt

**Intelligent Campus Energy & Sustainability Platform**

> *Detect Waste. Verify Real Savings. Eliminate Nocturnal Leaks. Build a Greener Campus.*

GhostWatt is a full-featured campus sustainability intelligence engine built for the **Kaushal 8.0 Hackathon**. It continuously monitors electrical and water consumption across campus buildings, differentiates productive academic energy from **Ghost Load** (appliances left running in empty rooms), verifies real savings after corrective actions, triages water leaks, and provides a zero-hallucination AI assistant powered by the Groq LPU API and Qwen 3.8.

---

## Table of Contents
1. [Core Features](#core-features)
2. [Quick Start & Setup](#quick-start--setup)
3. [Demo Accounts & RBAC](#demo-accounts--rbac)
4. [Environment Configuration](#environment-configuration)
5. [Telemetry Simulator & Demo Scenario](#telemetry-simulator--demo-scenario)
6. [Simulated vs Real Data Architecture](#simulated-vs-real-data-architecture)
7. [Engineering Assumptions & Equivalents](#engineering-assumptions--equivalents)
8. [Future Production Integrations (Meters, ERP, BMS)](#future-production-integrations-meters-erp-bms)
9. [Documentation & References](#documentation--references)

---

## Core Features

- **Ghost Load Intelligence:** Calculates real-time expected demand by combining room baselines, installed appliance power ratings, and scheduled academic timetable occupancy. Excess consumption is classified into plain-English reasons (`NO_CLASS_AC_ON`, `LAB_AFTER_HOURS`, `OVER_EXPECTED_DURING_CLASS`, `OUTSIDE_SCHEDULE`).
- **Closed-Loop Savings Verification:** When facility operators or students switch off forgotten equipment, GhostWatt tracks post-action intervals. Savings are only credited if actual demand drops below the pre-action level and cannot be attributed to a class naturally ending.
- **Water Night-Flow Leak Detection:** Analyzes nocturnal flow curves (02:00–05:00 AM) against low-flow baselines to identify pipe fractures and continuous overflows before structural damage occurs.
- **Facility Maintenance Lifecycle:** Students submit water and electrical waste reports with location details and photos. Admins assign, triage, and resolve tickets with full immutable audit history.
- **Campus Block Leaderboard:** Ranks Block A, Block B, and Block C based on efficiency scores (0–100) and sustainability letter grades (`A+` to `D`).
- **Grounded AI Assistant:** Powered by Groq Cloud and `qwen/qwen3.8-27b` using strict tool calling and a numerical guardrail that discards hallucinations.

---

## Quick Start & Setup

### Prerequisites
- **Python:** 3.11 or higher (Python 3.14 fully supported)
- **Node.js:** 18+ (for frontend dashboard)
- **SQLite:** 3.35+ (bundled with Python; WAL mode enabled automatically)

### Step 1: Clone and Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Ankit-Tank/GhostWatt.git
cd GhostWatt/backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd.exe):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create `.env` from the provided template:

```bash
cp .env.example .env
```

Edit `.env` to configure your settings (see [Environment Configuration](#environment-configuration)):
```env
JWT_SECRET=super_secret_jwt_key_change_in_production
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

### Step 4: Seed Database

Seed the SQLite database with 12 campus rooms across 3 blocks (A, B, C), appliance inventory, academic timetables, and 14 days of realistic 15-minute telemetry:

```bash
python -m scripts.seed
```

### Step 5: Start Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

- **API Base URL:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Alternative ReDoc:** `http://localhost:8000/redoc`

### Step 6: Run Backend Test Suite

Run the full pytest suite (111 tests covering RBAC, algorithms, savings verification, simulator, and API routes):

```bash
pytest -v
```

---

## Demo Accounts & RBAC

Role-Based Access Control (RBAC) is enforced in FastAPI dependency layers (`require_admin` vs `get_current_user`), not merely in the UI.

| Role | Email / Username | Password | Permissions |
|---|---|---|---|
| **Facility Administrator** | `admin@ghostwatt.demo` | `admin123` | Full access: simulator control, trigger demo scenario, approve actions, modify settings, triage water leaks, update complaints, view all reports |
| **Student / Faculty** | `student@ghostwatt.demo` | `student123` | Analytics view, leaderboard, live snapshot, report appliances left on, submit water complaints (privacy-restricted to own tickets) |

---

## Environment Configuration

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `GhostWatt` | Application display name |
| `APP_VERSION` | `0.1.0` | Semantic platform version |
| `DEBUG` | `false` | Enable verbose diagnostic logging |
| `DB_URL` | `sqlite:///./ghostwatt.db` | Database connection string (SQLite WAL mode) |
| `JWT_SECRET` | `change_this_to_a_long_random_secret` | Cryptographic secret key for signing bearer tokens |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token validity window |
| `GROQ_API_KEY` | `""` | Groq Cloud API key for LPU AI Assistant |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Model identifier used for tool calling and reasoning |
| `DEFAULT_ELECTRICITY_PRICE_PER_KWH` | `8.50` | Default commercial tariff in INR (₹) per kWh |
| `DEFAULT_EMISSIONS_FACTOR_KG_PER_KWH` | `0.71` | Regional grid carbon intensity (kg CO₂ / kWh) |
| `DEFAULT_FAN_WATT_EQUIVALENT` | `75.0` | Standard ceiling fan rated wattage (W) |
| `DEFAULT_BUCKET_LITRES` | `15.0` | Volume of standard utility bucket in litres |
| `DEFAULT_LOW_FLOW_THRESHOLD_LPH` | `50.0` | Nocturnal water leak threshold (Litres / hour) |

*Note: Calculation parameters stored in the database `settings` table take precedence at runtime over defaults.*

---

## Telemetry Simulator & Demo Scenario

GhostWatt includes an in-memory simulation engine that models time progression, appliance states, and sensor telemetry without requiring physical hardware.

### Simulator Mechanics
- **Virtual Clock:** Maintained in the `sim_state` database table (`virtual_now`, `speed`, `running`).
- **Speed Multipliers:** Scalable from `1.0x` (real-time) to `120.0x` (1 real second = 2 simulated minutes).
- **Interactive Appliance States:** Toggling appliances (`SET /sim/appliance`) immediately alters actual demand on subsequent ticks.
- **Background Worker:** Asyncio background task advances the virtual clock at the configured rate and triggers automatic post-action savings verification.

### 3-Second Live Hackathon Demo Scenario
To demonstrate the full detection-and-verification lifecycle in under 30 seconds:

1. **Trigger Demo Reset (Admin):**
   ```http
   POST /sim/scenario/demo
   Authorization: Bearer <admin_token>
   ```
   - Resets virtual clock to an evening time (`21:30:00`).
   - Sets simulator speed to `60.0x`.
   - Forces an air conditioner in Classroom **A-102** to the `ON` state outside scheduled hours.
   - Injects readings causing the **`High Usage` / `TRIGGERED`** alert to fire immediately.

2. **Student Observes and Signals:**
   ```http
   POST /reports/appliance-left-on
   Authorization: Bearer <student_token>
   {
     "room_id": 2,
     "equipment_type": "ac",
     "notes": "AC left running after evening tutorial."
   }
   ```
   - Generates signal `AL-0001` visible on admin dashboard.

3. **Admin Switches Off Appliance:**
   ```http
   POST /actions/switch-off
   Authorization: Bearer <admin_token>
   {
     "room_id": 2,
     "equipment_id": 4,
     "notes": "Patrol guard turned off AC."
   }
   ```
   - Action logged with `verification_status: "PENDING"`.

4. **Automated Verification in Seconds:**
   - Because the simulation clock runs at 60x, the 15-minute verification window elapses in ~2.5 seconds.
   - Query `GET /actions/{id}` or `GET /savings/records`:
   - Status updates to **`VERIFIED`**, crediting exact kWh reduction and rupees saved.

---

## Simulated vs Real Data Architecture

GhostWatt was built for production readiness while demonstrating via simulated data:

1. **Explicit Data Provenance:**
   - Every JSON response returned by the backend includes `"data_source": "simulated"`.
   - All rows generated by the simulator or seed script carry `is_simulated = True`.
   - Financial and emissions calculations are tagged as `calculated`, and post-action savings are tagged as `verified`.
2. **Deterministic Baseline Models:**
   - Expected demand curves are computed using pure mathematical models based on room metadata, rated equipment wattage, and scheduled student capacity.
   - In a live deployment, physical smart meters simply insert rows into the existing `meter_readings` table—no algorithm rewrites required.

---

## Engineering Assumptions & Equivalents

All sustainability metrics returned by GhostWatt include human-readable equivalence metrics and explicit assumption strings:

| Metric | Factor / Baseline | Explanation & Assumption String |
|---|---|---|
| **Ceiling Fan Equivalent** | `75 W` continuous | Computes how many standard 75W ceiling fans could be operated continuously using the wasted energy: `(kW * 1000) / 75.0`. |
| **Water Bucket Equivalent** | `15 Litres` per bucket | Converts lost water volume into standard utility buckets: `litres / 15.0`. |
| **Commercial Electricity Tariff** | `₹8.50 / kWh` | Representative Indian state commercial educational institution tariff. |
| **Grid Carbon Intensity** | `0.71 kg CO₂ / kWh` | Central Electricity Authority (CEA) baseline carbon intensity factor for regional power grids. |
| **Night Leak Threshold** | `50 L/h` between 02:00–05:00 | Flow rate exceeding this volume during inactive night hours flags a suspected leak. |
| **Hysteresis Alert Rule** | `2 consecutive intervals` | Alerts trigger only when a room exceeds its ghost threshold for two sequential 15-minute readings to prevent false alarms from transient spikes. |

---

## Future Production Integrations (Meters, ERP, BMS)

GhostWatt is architected to seamlessly transition from synthetic simulation to real campus operational technology:

```
[ Modbus/BACnet Meters ] ──> [ MQTT / HTTP Adapter ] ──┐
[ Water Pulse Counters ] ──> [ LoRaWAN Gateway      ] ──┼──> [ GhostWatt Backend ]
[ Campus ERP Timetables] ──> [ REST / Webhook Sync  ] ──┤      (FastAPI + SQLite/Postgres)
[ Building Management  ] <── [ Modbus Relay Coils   ] ──┘
```

1. **Real Electricity Meters (Modbus / BACnet):**
   - Sub-meters (Schneider, Siemens, Secure Meters) transmit active power (kW) and energy (kWh) over RS-485 Modbus RTU or BACnet/IP.
   - A lightweight edge agent publishes 15-minute interval readings directly into GhostWatt via a telemetry ingestion endpoint (`POST /ingest/readings`).
2. **Campus ERP Timetable Sync:**
   - Connects to university academic management systems (SAP, Ellucian, Google Classroom, custom ERP) via webhooks or daily automated cron sync.
   - Dynamically updates room timetable slots and expected student counts without manual intervention.
3. **Building Management System (BMS) Closed-Loop Actuation:**
   - GhostWatt's verified switch-off engine can trigger automated relay coils or smart circuit breakers (e.g. KNX, Zigbee, or Modbus relays) to power down unattended rooms automatically after grace periods.
4. **Ultrasonic Water Flow Meters & LoRaWAN:**
   - Digital water meters with pulse outputs or LoRaWAN transmitters stream hourly consumption from overhead tanks and main washroom risers.

---

## Documentation & References

- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — 3-Minute Hackathon Demo Script & Judge FAQ
- [docs/API.md](docs/API.md) — Complete API Reference with JSON Request & Response Schemas
- [LIBRARIES.md](LIBRARIES.md) — External Dependencies, Groq API details, and Model Inventory
- [docs/SPEC.md](docs/SPEC.md) — Full System Specification & Functional Requirements
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Technical Architecture and Component Breakdown

---

*GhostWatt — Kaushal 8.0 Hackathon Submission*
