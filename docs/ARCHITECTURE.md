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

### Ghost Load Calculation & Core Formulas
```
MeterReading (actual_demand_kw)
        │
        ▼
expected_demand.expected_kw(room, equipment, timetable, ts)
   uses: Timetable, Room.capacity, Equipment.rated_kw, Settings (factors)
        │
        ▼
ghost_load.calculate_ghost_load_kw(actual, expected)
   → ghost_kw = max(0, actual - expected)
   → ghost_kwh = ghost_kw * 0.25
   → cost = ghost_kwh * settings.electricity_price_per_kwh
   → co2  = ghost_kwh * settings.emissions_factor_kg_per_kwh
   → fans = (ghost_kw * 1000) / settings.fan_watt_equivalent
```

### Detailed Formula Reference

#### 1. Expected Demand ($Expected\_kW$)
- **No Class Scheduled:**
  $$\text{Expected Demand} = \text{Idle\_Baseline\_kW}$$
- **Class in Session:**
  $$\text{Scaling Factor} = \min\left(1.0, \max\left(0.1, \frac{\text{expected\_students}}{\text{room\_capacity}}\right)\right)$$
  $$\text{Scaled Equipment (lights, fans, PCs)} = \sum (\text{rated\_kw} \times \text{count} \times \text{expected\_in\_class} \times \text{Scaling Factor})$$
  $$\text{Fixed Equipment (AC, projector, lab)} = \sum (\text{rated\_kw} \times \text{count} \times \text{expected\_in\_class})$$
  $$\text{Expected Demand} = \text{Idle\_Baseline\_kW} + \text{Scaled Equipment} + \text{Fixed Equipment}$$

#### 2. Ghost Load Intelligence
- **Instantaneous Ghost Load:**
  $$\text{Ghost Load (kW)} = \max(0, \text{Actual Demand} - \text{Expected Demand})$$
- **Interval Energy (15-min step):**
  $$\text{Ghost Energy (kWh)} = \text{Ghost Load (kW)} \times 0.25\text{ h}$$
- **Financial Cost (INR):**
  $$\text{Cost (₹)} = \text{Ghost Energy (kWh)} \times \text{Tariff (₹8.50/kWh)}$$
- **Carbon Footprint:**
  $$\text{CO}_2\text{ (kg)} = \text{Ghost Energy (kWh)} \times \text{Grid Factor (0.71 kg/kWh)}$$
- **Ceiling Fan Equivalent:**
  $$\text{Fan Equivalents} = \frac{\text{Ghost Load (kW)} \times 1000}{\text{Fan Watts (75 W)}}\quad (\text{e.g. } 0.75\text{ kW} \rightarrow 10\text{ fans})$$
- **Water Bucket Equivalent:**
  $$\text{Bucket Equivalents} = \frac{\text{Volume (Litres)}}{\text{Bucket Capacity (15 L)}}$$

#### 3. Hysteresis & Debouncing Rule
- To eliminate false alarms from transient spikes or measurement noise, a Ghost Load Alert is triggered **only after 2 consecutive 15-minute intervals** above the configured threshold ($\ge 0.5\text{ kW}$):
  $$\text{Alert Status} = \begin{cases} \text{TRIGGERED} & \text{if consecutive intervals} \ge 2 \\ \text{PENDING\_CONFIRMATION} & \text{if consecutive intervals} = 1 \\ \text{CLEARED} & \text{otherwise} \end{cases}$$

#### 4. Reason Codes & Plain-English Explanations
| Reason Code | Condition | Explanation |
|---|---|---|
| `NO_CLASS_AC_ON` | Empty room, AC present, $\ge 1.2\text{ kW}$ ghost load | High power consumption consistent with air conditioning running in an unoccupied room with no scheduled class. |
| `LAB_AFTER_HOURS` | Lab room after 17:00 or before 08:00 | Computer workstations or specialized laboratory equipment left running outside scheduled lab session hours. |
| `OVER_EXPECTED_DURING_CLASS` | Class active, actual significantly exceeds expected | Electricity consumption significantly exceeded expected equipment demand during an active scheduled class. |
| `OUTSIDE_SCHEDULE` | Empty room outside scheduled hours | Unnecessary lighting, fans, or auxiliary appliances active outside scheduled timetable operating hours. |

#### 5. Room Status Classification
1. **In Session:** Class is actively scheduled and consumption is within normal limits.
2. **No Class:** Room is unoccupied with standard idle baseline consumption.
3. **Upcoming Class:** Class begins within the next 30–45 minutes.
4. **Within Expected Usage:** Room consumption matches expected baseline within tolerance.
5. **High Usage:** Ghost load exceeds the significant waste threshold ($\ge 0.5\text{ kW}$).
6. **Possible Idle Load:** Moderate excess above idle baseline in an empty room ($0.08\text{--}0.5\text{ kW}$).

#### 6. Water Monitoring & Night Leak Detection (1 AM – 4 AM)
- Quiescent monitoring window: $01:00\text{ to }04:00$ ($\text{LEAK\_HOURS} = \{1, 2, 3\}$).
- Alert Condition: $\text{avg\_flow} > \text{threshold\_lph (50 L/h)}$ OR $\text{avg\_flow} > \text{baseline\_lph} \times 2.0$.
$$\text{Expected Litres} = \text{Baseline (L/h)} \times \text{Duration (h)}$$
$$\text{Actual Litres} = \sum \text{Interval Litres}$$
$$\text{Excess Litres} = \max(0, \text{Actual Litres} - \text{Expected Litres})$$
- Generates `SUSPECTED` alert with detailed inspection notes when excess flow is confirmed.

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
