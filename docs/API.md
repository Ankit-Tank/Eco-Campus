# GhostWatt — API Reference

> **Base URL:** `http://localhost:8000`  
> **Interactive Swagger UI:** `http://localhost:8000/docs`  
> **ReDoc Documentation:** `http://localhost:8000/redoc`  
> **Authentication:** Protected endpoints require an `Authorization: Bearer <token>` HTTP header.  
> **Data Source:** Every response payload includes `"data_source": "simulated"` so frontend UIs can explicitly identify demo/simulated telemetry.

---

## 1. System & Health

### `GET /health`
Returns runtime server status and operational mode. No authentication required.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "app": "GhostWatt",
  "mode": "demo"
}
```

---

## 2. Authentication (`/auth`)

Role-based access control (RBAC) is enforced at the FastAPI dependency layer via `get_current_user` and `require_admin`.

### `POST /auth/login`
Authenticate using username or email and password. Generates a signed JWT bearer token.

**Request Body:**
```json
{
  "username_or_email": "admin@ghostwatt.demo",
  "password": "admin123"
}
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@ghostwatt.demo",
    "role": "admin",
    "is_active": true,
    "data_source": "simulated"
  },
  "data_source": "simulated"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials (`{"detail": "Invalid username/email or password"}`).

---

### `GET /auth/me`
Retrieve user profile for the currently authenticated bearer token.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "id": 2,
  "username": "student",
  "email": "student@ghostwatt.demo",
  "role": "student",
  "is_active": true,
  "data_source": "simulated"
}
```

---

## 3. Campus Dashboard (`/dashboard`)

### `GET /dashboard/summary`
Campus-wide overview metrics across electricity, water, financial cost, carbon emissions, and intuitive human-scale equivalents.

**Query Parameters:**
- `from` *(optional)*: Start timestamp (ISO 8601, e.g. `2026-10-01T00:00:00`)
- `to` *(optional)*: End timestamp (ISO 8601, e.g. `2026-10-14T23:59:59`)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "actual_kwh": 3719.64,
  "expected_kwh": 2686.07,
  "ghost_kwh": 1033.57,
  "water_litres": 15840.0,
  "emissions_co2_kg": 733.835,
  "cost_inr": 8785.35,
  "fan_equivalents": 41.0,
  "bucket_equivalents": 1056.0,
  "date_from": "2026-09-28T00:00:00",
  "date_to": "2026-10-11T23:45:00",
  "data_source": "simulated"
}
```

---

## 4. Electricity Time-Series (`/electricity`)

### `GET /electricity/series`
Retrieve 15-minute interval electricity meter readings with actual vs expected demand and ghost load calculations.

**Query Parameters:**
- `block` *(optional)*: Filter by campus block (`A`, `B`, `C`)
- `room` *(optional)*: Filter by room code (`A-101`) or room ID (`1`)
- `from` *(optional)*: Start timestamp (ISO 8601)
- `to` *(optional)*: End timestamp (ISO 8601)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "series": [
    {
      "timestamp": "2026-10-10T14:00:00",
      "room_id": 1,
      "room_code": "A-101",
      "actual_demand_kw": 3.75,
      "interval_kwh": 0.9375,
      "expected_demand_kw": 0.1,
      "ghost_load_kw": 3.65
    },
    {
      "timestamp": "2026-10-10T14:15:00",
      "room_id": 1,
      "room_code": "A-101",
      "actual_demand_kw": 3.75,
      "interval_kwh": 0.9375,
      "expected_demand_kw": 0.1,
      "ghost_load_kw": 3.65
    }
  ],
  "count": 2,
  "total_kwh": 1.875,
  "data_source": "simulated"
}
```

---

## 5. Ghost Load Intelligence (`/ghost` and `/ghost-load`)

### `GET /ghost/current`
Get instantaneous ghost load, room operating status, and diagnostic reason codes for all active rooms.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "rooms": [
    {
      "room_id": 1,
      "room_code": "A-101",
      "name": "Classroom 101",
      "block": "A",
      "room_type": "classroom",
      "actual_kw": 3.82,
      "expected_kw": 0.1,
      "ghost_kw": 3.72,
      "status": "Possible Idle Load",
      "in_session": false,
      "reason_code": "NO_CLASS_AC_ON",
      "reason_explanation": "Air conditioning running while room is unoccupied with no scheduled class."
    },
    {
      "room_id": 2,
      "room_code": "A-102",
      "name": "Classroom 102",
      "block": "A",
      "room_type": "classroom",
      "actual_kw": 0.12,
      "expected_kw": 0.1,
      "ghost_kw": 0.02,
      "status": "Within Expected Usage",
      "in_session": false,
      "reason_code": "SCHEDULED_CLASS_RUNNING",
      "reason_explanation": "Room consumption aligns with scheduled timetable parameters."
    }
  ],
  "total_ghost_kw": 8.45,
  "high_usage_count": 2,
  "idle_load_count": 3,
  "data_source": "simulated"
}
```

---

### `GET /ghost/ranking`
Ranks rooms descending by accumulated ghost energy (kWh) over a time window, including monetary loss and carbon footprint.

**Query Parameters:**
- `from` *(optional)*: Start timestamp (ISO 8601)
- `to` *(optional)*: End timestamp (ISO 8601)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "ranking": [
    {
      "rank": 1,
      "room_id": 1,
      "room_code": "A-101",
      "name": "Classroom 101",
      "block": "A",
      "total_actual_kwh": 412.5,
      "total_expected_kwh": 145.2,
      "total_ghost_kwh": 267.3,
      "cost_inr": 2272.05,
      "co2_kg": 189.78
    },
    {
      "rank": 2,
      "room_id": 5,
      "room_code": "B-201",
      "name": "Computer Science Lab 1",
      "block": "B",
      "total_actual_kwh": 650.0,
      "total_expected_kwh": 420.0,
      "total_ghost_kwh": 230.0,
      "cost_inr": 1955.0,
      "co2_kg": 163.3
    }
  ],
  "total_ghost_kwh": 1033.57,
  "total_cost_inr": 8785.35,
  "data_source": "simulated"
}
```

---

### `GET /ghost/switch-off-list`
Provides a prioritized triage list of rooms currently wasting power, ranked descending by instantaneous ghost load (kW) with recommended targets.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "items": [
    {
      "priority": 1,
      "room_code": "A-101",
      "room_name": "Classroom 101",
      "ghost_kw": 3.72,
      "actual_kw": 3.82,
      "expected_kw": 0.1,
      "potential_hourly_saving_inr": 31.62,
      "target_appliance": "Air Conditioners",
      "urgency": "CRITICAL"
    },
    {
      "priority": 2,
      "room_code": "B-201",
      "room_name": "Computer Science Lab 1",
      "ghost_kw": 2.4,
      "actual_kw": 2.8,
      "expected_kw": 0.4,
      "potential_hourly_saving_inr": 20.4,
      "target_appliance": "Lab Computers & AC",
      "urgency": "HIGH"
    }
  ],
  "total_potential_saving_inr_per_hour": 52.02,
  "data_source": "simulated"
}
```

---

### `GET /ghost/room/{id}/explain`
Detailed diagnostic explainability breakdown comparing actual demand against timetable expectations, identifying equipment drivers, and distinguishing legitimate sessions from unoccupied waste. Accepts room ID (`1`) or room code (`A-101`).

**Query Parameters:**
- `ts` *(optional)*: Evaluation timestamp (ISO 8601, e.g. `2026-10-10T14:30:00`)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "room_id": 1,
  "room_code": "A-101",
  "name": "Classroom 101",
  "timestamp": "2026-10-10T14:30:00",
  "actual_kw": 3.82,
  "expected_kw": 0.1,
  "ghost_kw": 3.72,
  "in_session": false,
  "activity": null,
  "expected_students": 0,
  "capacity": 40,
  "scaling_factor": 1.0,
  "equipment_breakdown": {
    "idle_baseline": 0.1
  },
  "reason_code": "NO_CLASS_AC_ON",
  "reason_explanation": "Air conditioning running while room is unoccupied with no scheduled class.",
  "is_legitimate": false,
  "explanation": "Excess demand of 3.72 kW detected in room A-101. Air conditioning running while room is unoccupied with no scheduled class.",
  "data_source": "simulated"
}
```

---

## 6. Rooms & Equipment CRUD (`/rooms`)

Read endpoints are open to all authenticated users. Create, Update, and Delete endpoints **strictly require Administrator privileges** (`role == "admin"`).

### `GET /rooms`
List all campus rooms with installed appliance inventory.

**Query Parameters:**
- `block` *(optional)*: Filter by block (`A`, `B`, `C`)

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": 1,
      "room_code": "A-101",
      "block": "A",
      "name": "Classroom 101",
      "room_type": "classroom",
      "capacity": 40,
      "idle_baseline_kw": 0.1,
      "is_active": true,
      "equipment": [
        {
          "id": 1,
          "room_id": 1,
          "kind": "light",
          "rated_kw": 0.04,
          "count": 6,
          "state": "OFF",
          "expected_in_class": 1.0,
          "data_source": "simulated"
        },
        {
          "id": 2,
          "room_id": 1,
          "kind": "ac",
          "rated_kw": 1.8,
          "count": 2,
          "state": "OFF",
          "expected_in_class": 1.0,
          "data_source": "simulated"
        }
      ],
      "data_source": "simulated"
    }
  ],
  "total": 1,
  "data_source": "simulated"
}
```

---

### `POST /rooms` *(Admin Only)*
Register a new room on campus.

**Request Body:**
```json
{
  "room_code": "C-305",
  "block": "C",
  "name": "Robotics Research Lab",
  "room_type": "lab",
  "capacity": 30,
  "idle_baseline_kw": 0.25
}
```

**Response `201 Created`:**
```json
{
  "id": 13,
  "room_code": "C-305",
  "block": "C",
  "name": "Robotics Research Lab",
  "room_type": "lab",
  "capacity": 30,
  "idle_baseline_kw": 0.25,
  "is_active": true,
  "equipment": [],
  "data_source": "simulated"
}
```

**Non-Admin Response `403 Forbidden`:**
```json
{
  "detail": "Admin access required: operation forbidden for non-admin accounts"
}
```

---

### `PUT /rooms/{room_id}` *(Admin Only)*
Update room properties.

**Request Body:**
```json
{
  "name": "Advanced Robotics Lab",
  "capacity": 35
}
```

**Response `200 OK`:** Returns updated `RoomResponse`.

---

### `DELETE /rooms/{room_id}` *(Admin Only)*
Delete a room and its associated equipment and timetables.

**Response `204 No Content`**

---

### Equipment Sub-Routes

- `GET /rooms/{room_id}/equipment`: List appliances for a room.
- `POST /rooms/{room_id}/equipment` *(Admin Only)*: Add equipment (`kind` must be one of: `light`, `fan`, `ac`, `projector`, `pc`, `lab_equipment`).
  ```json
  {
    "kind": "projector",
    "rated_kw": 0.35,
    "count": 1,
    "state": "OFF",
    "expected_in_class": 0.8
  }
  ```
  Returns `201 Created`.
- `PUT /rooms/equipment/{equipment_id}` *(Admin Only)*: Update appliance ratings or state. Returns `200 OK`.
- `DELETE /rooms/equipment/{equipment_id}` *(Admin Only)*: Remove equipment. Returns `204 No Content`.

---

## 7. Timetable Schedule Management (`/timetable`)

### `GET /timetable`
Retrieve weekly class schedules.

**Query Parameters:**
- `room_id` *(optional)*: Filter by room ID
- `day_of_week` *(optional)*: `0` (Mon) to `5` (Sat), `6` (Sun)

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": 1,
      "room_id": 1,
      "day_of_week": 0,
      "start_time": "09:00",
      "end_time": "11:00",
      "activity": "Computer Networks Lecture",
      "expected_students": 35,
      "is_active": true,
      "data_source": "simulated"
    }
  ],
  "total": 1,
  "data_source": "simulated"
}
```

---

### `POST /timetable` *(Admin Only)*
Create a scheduled session. Validates that `end_time` is strictly after `start_time`.

**Request Body:**
```json
{
  "room_id": 1,
  "day_of_week": 2,
  "start_time": "14:00",
  "end_time": "16:00",
  "activity": "Operating Systems Lab",
  "expected_students": 32
}
```

**Response `201 Created`:**
```json
{
  "id": 45,
  "room_id": 1,
  "day_of_week": 2,
  "start_time": "14:00",
  "end_time": "16:00",
  "activity": "Operating Systems Lab",
  "expected_students": 32,
  "is_active": true,
  "data_source": "simulated"
}
```

**Validation Error Response (`422 Unprocessable Entity` or `400 Bad Request`):**
If `end_time <= start_time`, request is rejected.

---

### `PUT /timetable/{entry_id}` *(Admin Only)*
Update schedule slot timing or activity. Returns `200 OK`.

### `DELETE /timetable/{entry_id}` *(Admin Only)*
Delete schedule slot. Returns `204 No Content`.

---

## 8. Runtime System Settings (`/settings`)

### `GET /settings`
Read system configuration parameters (tariffs, emission factors, equivalents).

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "settings": {
    "electricity_price_per_kwh": "8.50",
    "emissions_factor_kg_per_kwh": "0.71",
    "fan_watt_equivalent": "75.0",
    "bucket_litres": "15.0",
    "water_night_threshold_lph": "50.0",
    "water_low_flow_baseline_lph": "20.0"
  },
  "items": [
    {
      "key": "electricity_price_per_kwh",
      "value": "8.50",
      "description": "Electricity tariff in INR per kWh"
    }
  ],
  "data_source": "simulated"
}
```

---

### `PUT /settings` *(Admin Only)*
Update configuration parameters. Enforces that numerical settings must be **strictly positive numbers (> 0)**.

**Request Body:**
```json
{
  "settings": {
    "electricity_price_per_kwh": "9.25",
    "emissions_factor_kg_per_kwh": "0.73"
  }
}
```

**Response `200 OK`:** Returns updated `SettingsResponse`.

**Validation Rejection (`422 Unprocessable Entity` or `400 Bad Request`):**
If `electricity_price_per_kwh <= 0`, rejected with:
`"Setting 'electricity_price_per_kwh' must be a strictly positive number (> 0)"`.

---

## 9. Water Consumption & Leak Detection (`/water`)

### `GET /water/series`
Hourly simulated water flow readings per location against normal baseline.

**Query Parameters:**
- `location_id` *(optional)*: Water monitoring point ID
- `from` *(optional)*: Start timestamp (ISO 8601)
- `to` *(optional)*: End timestamp (ISO 8601)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "series": [
    {
      "timestamp": "2026-10-10T02:00:00",
      "location_id": 1,
      "location_name": "Main Water Meter - Block A",
      "flow_rate_lph": 120.0,
      "interval_litres": 120.0,
      "baseline_lph": 20.0
    }
  ],
  "count": 1,
  "total_litres": 120.0,
  "data_source": "simulated"
}
```

---

### `GET /water/alerts`
List night-flow leak alerts detected during the 1 AM – 4 AM quiescent window.

**Query Parameters:**
- `status` *(optional)*: Filter by `SUSPECTED`, `CONFIRMED`, `FALSE_ALARM`
- `location_id` *(optional)*: Filter by water location ID

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "alerts": [
    {
      "id": 1,
      "location_id": 1,
      "location_name": "Main Water Meter - Block A",
      "building": "Block A",
      "detected_at": "2026-10-10T04:00:00",
      "window_start": "2026-10-10T01:00:00",
      "window_end": "2026-10-10T04:00:00",
      "avg_flow_lph": 115.0,
      "baseline_lph": 20.0,
      "status": "SUSPECTED",
      "inspection_notes": "Sustained night flow detected between 01:00 and 04:00: observed avg 115.0 L/h against normal 20.0 L/h baseline. Potential pipe break, running urinal, or leaking cistern.",
      "resolved_at": null,
      "expected_litres": 60.0,
      "actual_litres": 345.0,
      "excess_litres": 285.0,
      "data_source": "simulated"
    }
  ],
  "count": 1,
  "data_source": "simulated"
}
```

---

### `PATCH /water/alerts/{id}` *(Admin Only)*
Triage and update inspection status of a suspected leak.

**Request Body:**
```json
{
  "status": "CONFIRMED",
  "inspection_notes": "Plumber inspected Ground Floor Restroom; replaced worn seal on automatic flush valve."
}
```

**Response `200 OK`:**
```json
{
  "id": 1,
  "location_id": 1,
  "location_name": "Main Water Meter - Block A",
  "building": "Block A",
  "detected_at": "2026-10-10T04:00:00",
  "window_start": "2026-10-10T01:00:00",
  "window_end": "2026-10-10T04:00:00",
  "avg_flow_lph": 115.0,
  "baseline_lph": 20.0,
  "status": "CONFIRMED",
  "inspection_notes": "Plumber inspected Ground Floor Restroom; replaced worn seal on automatic flush valve.",
  "resolved_at": "2026-10-12T12:00:00",
  "expected_litres": 60.0,
  "actual_litres": 345.0,
  "excess_litres": 285.0,
  "data_source": "simulated"
}
```

---

---

## 10. Simulation Control & Live Snapshot (`/sim` and `/live`)

The simulation engine maintains a virtual clock (`sim_state`) that advances in 15-minute intervals, generating telemetry from the equipment state model, applying scripted anomalies, and persisting meter and water readings. An asynchronous background task runs continuously when active with execution frequency governed by the simulation speed.

### `GET /live/snapshot`
High-performance consolidated campus snapshot (optimized for sub-100ms response latency). Open to any logged-in user (students and administrators).

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T10:15:00",
  "total_actual_kw": 28.45,
  "total_expected_kw": 21.30,
  "total_ghost_kw": 7.15,
  "actual_kw": 28.45,
  "expected_kw": 21.30,
  "ghost_kw": 7.15,
  "cost_per_hour": 60.78,
  "co2_per_hour": 5.077,
  "fan_equivalent": 95.3,
  "rooms": [
    {
      "room_id": 1,
      "room_code": "A-101",
      "name": "Classroom 101",
      "block": "A",
      "room_type": "classroom",
      "actual_kw": 3.82,
      "expected_kw": 0.1,
      "ghost_kw": 3.72,
      "status": "Possible Idle Load",
      "in_session": false,
      "reason_code": "NO_CLASS_AC_ON",
      "reason_explanation": "Air conditioning running while room is unoccupied with no scheduled class."
    },
    {
      "room_id": 2,
      "room_code": "A-102",
      "name": "Classroom 102",
      "block": "A",
      "room_type": "classroom",
      "actual_kw": 0.12,
      "expected_kw": 0.1,
      "ghost_kw": 0.02,
      "status": "Within Expected Usage",
      "in_session": false,
      "reason_code": null,
      "reason_explanation": null
    }
  ],
  "active_alerts": [
    {
      "type": "electricity",
      "severity": "warning",
      "title": "Excessive Load in A-101",
      "description": "Air conditioning running while room is unoccupied with no scheduled class.",
      "target": "Room A-101",
      "timestamp": "2026-10-12T10:15:00"
    },
    {
      "type": "water",
      "severity": "critical",
      "title": "Suspected Leak at Block C Washrooms & Cafeteria",
      "description": "Sustained night flow detected between 01:00 and 04:00.",
      "target": "Block C",
      "timestamp": "2026-10-12T04:00:00"
    }
  ],
  "accelerated_time": true,
  "data_source": "simulated"
}
```

---

### `POST /sim/start` *(Admin Only)*
Start automated background ticking of the virtual clock.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T10:15:00",
  "speed": 1.0,
  "running": true,
  "data_source": "simulated"
}
```

---

### `POST /sim/pause` *(Admin Only)*
Pause automated background ticking of the virtual clock.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T10:15:00",
  "speed": 1.0,
  "running": false,
  "data_source": "simulated"
}
```

---

### `POST /sim/speed` *(Admin Only)*
Set the simulation speed factor. Delays between background ticks are inversely proportional to speed. Rejects non-positive speed values (`<= 0`).

**Headers:**
`Authorization: Bearer <token>`

**Request Body:**
```json
{
  "speed": 5.0
}
```

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T10:15:00",
  "speed": 5.0,
  "running": true,
  "data_source": "simulated"
}
```

---

### `POST /sim/reset` *(Admin Only)*
Reset the virtual clock anchor and pause execution. Optionally specify an explicit target date.

**Headers:**
`Authorization: Bearer <token>`

**Request Body (optional):**
```json
{
  "to_date": "2026-10-12T00:00:00"
}
```

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T00:00:00",
  "speed": 1.0,
  "running": false,
  "data_source": "simulated"
}
```

---

### `GET /sim/state` *(Admin Only)*
Inspect current simulation state, speed factor, and active status.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "virtual_now": "2026-10-12T10:15:00",
  "speed": 1.0,
  "running": false,
  "data_source": "simulated"
}
```

---

### `POST /sim/scenario/demo` *(Admin Only)*
Resets the simulation to an evening timeframe (21:30), accelerates speed to 60x, starts the virtual clock, and injects an AC-left-on ghost event in room A-102.
This triggers an immediate `High Usage` / `TRIGGERED` alert status, enabling a rapid demo loop where an operator registers a switch-off action and sees savings verification complete within 2–3 seconds.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "status": "demo_scenario_active",
  "virtual_now": "2026-10-12T21:30:00",
  "speed": 60.0,
  "room_code": "A-102",
  "room_id": 2,
  "equipment_type": "ac",
  "actual_kw": 3.75,
  "expected_kw": 0.15,
  "ghost_kw": 3.60,
  "alert_status": "TRIGGERED",
  "message": "Demo scenario active. AC in room A-102 is left on at 21:30. Switch it off via POST /actions/switch-off to verify savings.",
  "data_source": "simulated"
}
```

---

## 11. Corrective Actions & Verified Savings Meter (`/actions` and `/savings`)

GhostWatt's core differentiator is closing the loop between identifying excess consumption and verifying that corrective actions actually reduced electricity usage without claiming credit for natural schedule transitions.

### `POST /actions/switch-off` *(Admin Only)*
Trigger an immediate corrective action to switch off a running appliance in a target room. The action is recorded with status `PENDING`, a claimed saving estimate is computed, and the appliance is set to `OFF` effective from the next simulation tick.

**Headers:**
`Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "room_id": 2,
  "equipment_id": 5,
  "notes": "Admin switching off overnight AC in A-102 via dashboard alert"
}
```

**Response `201 Created`:**
```json
{
  "id": 4,
  "room_id": 2,
  "room_code": "A-102",
  "room_name": "Classroom 102",
  "equipment_id": 5,
  "equipment_kind": "ac",
  "user_id": 1,
  "user_email": "admin@ghostwatt.demo",
  "action_type": "switch_off",
  "timestamp": "2026-10-12T10:15:00",
  "notes": "Admin switching off overnight AC in A-102 via dashboard alert",
  "verification_status": "PENDING",
  "claimed_reduction_kw": 3.6,
  "claimed_kwh_per_interval": 0.9,
  "data_source": "simulated"
}
```

**Error Responses:**
- `403 Forbidden`: Attempted by a student account (`{"detail": "Admin access required: operation forbidden for non-admin accounts"}`).
- `404 Not Found`: Room or equipment ID does not exist.

---

### `GET /actions`
Retrieve history of all corrective actions taken across campus, including author information, target equipment, and verification status.

**Query Parameters:**
- `room_id` *(optional)*: Filter by target room ID
- `limit` *(optional)*: Maximum items to return (default: `100`)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "actions": [
    {
      "id": 4,
      "room_id": 2,
      "room_code": "A-102",
      "room_name": "Classroom 102",
      "equipment_id": 5,
      "equipment_kind": "ac",
      "user_id": 1,
      "user_email": "admin@ghostwatt.demo",
      "action_type": "switch_off",
      "timestamp": "2026-10-12T10:15:00",
      "notes": "Admin switching off overnight AC in A-102 via dashboard alert",
      "verification_status": "VERIFIED",
      "claimed_reduction_kw": 3.6,
      "claimed_kwh_per_interval": 0.9,
      "data_source": "simulated"
    }
  ],
  "count": 1,
  "data_source": "simulated"
}
```

---

### `GET /actions/{action_id}`
Retrieve complete verification details and status for a single corrective action by ID.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "id": 1,
  "room_id": 2,
  "room_code": "A-102",
  "room_name": "Classroom A-102",
  "equipment_id": 4,
  "equipment_kind": "AC",
  "user_id": 1,
  "user_email": "admin@ghostwatt.demo",
  "action_type": "switch_off",
  "timestamp": "2026-10-12T21:30:00",
  "notes": "Patrol guard switched off forgotten AC unit in A-102.",
  "verification_status": "VERIFIED",
  "status": "VERIFIED",
  "claimed_reduction_kw": 3.6,
  "claimed_kwh_per_interval": 0.9,
  "data_source": "simulated"
}
```

---

### `GET /savings/summary`
Retrieve high-level Verified Savings metrics comparing claimed savings against verified savings backed by subsequent meter readings.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "claimed_kwh": 3.6,
  "verified_kwh": 2.7,
  "monetary_saving_inr": 22.95,
  "emissions_co2_kg": 1.917,
  "total_actions": 4,
  "verified_actions": 3,
  "partial_actions": 0,
  "unverified_actions": 1,
  "pending_actions": 0,
  "label": "Simulated Verified Savings",
  "data_source": "simulated"
}
```

---

### `GET /savings/records`
Detailed audit records of interval-by-interval verified savings, including pre-action vs post-action demand averages, credited kWh, monetary savings in rupees, and avoided emissions.

**Query Parameters:**
- `room_id` *(optional)*: Filter by target room ID
- `limit` *(optional)*: Maximum records to return (default: `100`)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "records": [
    {
      "id": 1,
      "action_id": 1,
      "room_id": 2,
      "room_code": "A-102",
      "equipment": "AC",
      "interval_start": "2026-10-11T22:00:00",
      "pre_avg_kw": 3.71,
      "post_avg_kw": 0.11,
      "reduction_kw": 3.6,
      "credited_kwh": 0.9,
      "monetary_saving_inr": 7.65,
      "emissions_kg": 0.639,
      "verification_status": "VERIFIED",
      "is_simulated": true,
      "data_source": "simulated"
    }
  ],
  "count": 1,
  "total_credited_kwh": 0.9,
  "total_monetary_saving_inr": 7.65,
  "total_emissions_kg": 0.639,
  "data_source": "simulated"
}
```

---

### `POST /savings/verify/{action_id}` *(Admin Only)*
Manually evaluate verification for a pending action once its post-action window has closed.

**Headers:**
`Authorization: Bearer <admin_token>`

**Response `200 OK`:**
```json
{
  "id": 2,
  "action_id": 4,
  "room_id": 2,
  "room_code": "A-102",
  "equipment": "AC",
  "interval_start": "2026-10-12T10:15:00",
  "pre_avg_kw": 3.75,
  "post_avg_kw": 0.15,
  "reduction_kw": 3.6,
  "credited_kwh": 0.9,
  "monetary_saving_inr": 7.65,
  "emissions_kg": 0.639,
  "verification_status": "VERIFIED",
  "is_simulated": true,
  "data_source": "simulated"
}
```

---

## 12. Student Water Complaints & Facilities Management (`/complaints`)

Students can report real or simulated water leakage incidents across campus with optional photo evidence. Facilities administrators triage complaints through a defined lifecycle with immutable audit history.

### `POST /complaints`
Submit a new student water or facility complaint. Supports `multipart/form-data` with optional photo upload.

**Headers:**
`Authorization: Bearer <token>`
`Content-Type: multipart/form-data`

**Form Parameters:**
- `building`: Campus building name (e.g. `Block C`)
- `location_detail`: Specific location (e.g. `2nd Floor Washroom (West Wing)`)
- `category`: Complaint category (`leaking_tap`, `broken_pipe`, `overflowing_tank`, `low_pressure`, `general_wastage`)
- `description`: Detailed text description of the issue
- `photo` *(optional)*: Photographic evidence (JPEG, PNG, WEBP, GIF; max 5MB)

**Response `201 Created`:**
```json
{
  "id": 2,
  "complaint_code": "WC-0002",
  "student_id": 2,
  "student_email": "student@ghostwatt.demo",
  "student_username": "student",
  "building": "Block C",
  "location_detail": "2nd Floor Washroom (West Wing)",
  "category": "leaking_tap",
  "description": "Urinal flush pipe continuously discharging water onto floor.",
  "attachment_path": "uploads/complaints/a1b2c3d4_photo.jpg",
  "assigned_to": null,
  "assigned_to_email": null,
  "status": "submitted",
  "created_at": "2026-10-12T10:15:00",
  "updated_at": "2026-10-12T10:15:00",
  "resolution_notes": "",
  "is_overdue": false,
  "history": [
    {
      "id": 2,
      "complaint_id": 2,
      "changed_by": 2,
      "changed_by_email": "student@ghostwatt.demo",
      "old_status": null,
      "new_status": "submitted",
      "note": "Complaint submitted by student",
      "changed_at": "2026-10-12T10:15:00"
    }
  ],
  "data_source": "simulated"
}
```

---

### `GET /complaints`
Retrieve complaints list.
- **Students:** See strictly only their own submitted complaints.
- **Administrators:** See campus-wide complaints with optional status, building, and category filters. Includes overdue metrics and frequently affected locations.

**Query Parameters (Admin Only):**
- `status` *(optional)*: Filter by lifecycle status (`submitted`, `acknowledged`, `assigned`, `in_progress`, `resolved`, `reopened`)
- `building` *(optional)*: Filter by building (`Block A`, `Block B`, `Block C`)
- `category` *(optional)*: Filter by issue category
- `limit` *(optional)*: Max results (default `100`)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "complaints": [
    {
      "id": 2,
      "complaint_code": "WC-0002",
      "student_id": 2,
      "student_email": "student@ghostwatt.demo",
      "student_username": "student",
      "building": "Block C",
      "location_detail": "2nd Floor Washroom (West Wing)",
      "category": "leaking_tap",
      "description": "Urinal flush pipe continuously discharging water.",
      "attachment_path": "uploads/complaints/a1b2c3d4_photo.jpg",
      "assigned_to": 1,
      "assigned_to_email": "admin@ghostwatt.demo",
      "status": "assigned",
      "created_at": "2026-10-12T10:15:00",
      "updated_at": "2026-10-12T10:30:00",
      "resolution_notes": "",
      "is_overdue": false,
      "history": [],
      "data_source": "simulated"
    }
  ],
  "count": 1,
  "overdue_count": 0,
  "frequently_affected_locations": [
    {
      "building": "Block C",
      "location_detail": "2nd Floor Washroom (West Wing)",
      "count": 3
    }
  ],
  "data_source": "simulated"
}
```

---

### `GET /complaints/{id}`
Retrieve a specific complaint by ID. Enforces privacy: returns `403 Forbidden` if a student attempts to view another student's complaint.

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
*(ComplaintResponse object)*

**Error Response:**
- `403 Forbidden`: `{"detail": "Forbidden: student cannot view another student's complaint"}`

---

### `PATCH /complaints/{id}` *(Admin Only)*
Triage complaint lifecycle status, assign to facility staff, and add resolution notes. All updates are logged in `complaint_history`.

**Valid Status Transitions:**
`submitted` → `acknowledged`, `assigned`, `in_progress`, `resolved`  
`acknowledged` → `assigned`, `in_progress`, `resolved`  
`assigned` → `in_progress`, `resolved`  
`in_progress` → `resolved`  
`resolved` → `reopened`  
`reopened` → `in_progress`, `assigned`, `resolved`

**Headers:**
`Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "status": "in_progress",
  "assigned_to": 1,
  "resolution_notes": "Plumber on site repairing pipe coupling",
  "notes": "Work commenced"
}
```

**Response `200 OK`:**
*(Updated ComplaintResponse object with updated history)*

---

### `GET /complaints/notifications/admin` *(Admin Only)*
Inspect automated internal notification records generated upon new student complaint submissions.

**Headers:**
`Authorization: Bearer <admin_token>`

**Response `200 OK`:**
```json
{
  "notifications": [
    {
      "id": 1,
      "title": "New Complaint: WC-0002",
      "message": "Student student@ghostwatt.demo reported leaking_tap in Block C (2nd Floor Washroom)",
      "notification_type": "complaint",
      "reference_id": "WC-0002",
      "is_read": false,
      "created_at": "2026-10-12T10:15:00",
      "data_source": "simulated"
    }
  ],
  "unread_count": 1,
  "count": 1,
  "data_source": "simulated"
}
```

---

## 13. Sustainability Reports & CSV Export (`/reports`)

Comprehensive executive reports combining electricity analytics, ghost load ranking, verified savings, water telemetry, and complaint metrics. Every single figure is explicitly tagged with its provenance (`simulated`, `calculated`, or `verified`).

### `GET /reports/summary`
Campus sustainability summary. Students receive a privacy-restricted version omitting administrative and internal staff details.

**Query Parameters:**
- `from` *(optional)*: Start date (ISO format)
- `to` *(optional)*: End date (ISO format)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "date_from": "2026-09-28T00:00:00",
  "date_to": "2026-10-12T10:15:00",
  "actual_kwh": 3719.64,
  "expected_kwh": 2686.07,
  "ghost_kwh": 1033.57,
  "cost_inr": 8785.35,
  "co2_kg": 733.835,
  "top_ghost_rooms": [
    {
      "rank": 1,
      "room_id": 1,
      "room_code": "A-101",
      "name": "Classroom 101",
      "block": "A",
      "ghost_kwh": 267.3,
      "cost_inr": 2272.05,
      "co2_kg": 189.783,
      "explanation": "Air conditioning operating during overnight unoccupied hours with zero scheduled classes.",
      "recommended_action": "Install 2-hour auto shut-off timers and enforce post-21:00 manual shutdown checklist.",
      "tag": "calculated"
    }
  ],
  "rooms_over_limit": [
    {
      "room_code": "A-101",
      "name": "Classroom 101",
      "actual_kwh": 412.5,
      "expected_kwh": 145.2,
      "ghost_kwh": 267.3,
      "excess_percentage": 184.1,
      "tag": "calculated"
    }
  ],
  "verified_savings": {
    "claimed_kwh": 3.6,
    "verified_kwh": 2.7,
    "monetary_saving_inr": 22.95,
    "emissions_co2_kg": 1.917,
    "action_count": 4,
    "verified_count": 3,
    "tag": "verified"
  },
  "water": {
    "total_litres": 15840.0,
    "tag_total": "simulated",
    "night_excess_litres": 680.0,
    "tag_excess": "calculated",
    "leak_alerts_count": 1,
    "active_alerts_count": 0,
    "tag_alerts": "calculated"
  },
  "complaints": {
    "total_complaints": 2,
    "resolved_complaints": 1,
    "open_complaints": 1,
    "tag": "calculated",
    "is_restricted": false,
    "own_complaints": null,
    "category_breakdown": {
      "leaking_tap": 2
    },
    "building_breakdown": {
      "Block C": 2
    }
  },
  "data_tags": {
    "actual_kwh": "simulated",
    "expected_kwh": "calculated",
    "ghost_kwh": "calculated",
    "cost_inr": "calculated",
    "co2_kg": "calculated",
    "top_ghost_rooms": "calculated",
    "rooms_over_limit": "calculated",
    "verified_savings": "verified",
    "total_water_litres": "simulated",
    "night_excess_litres": "calculated",
    "water_leak_alerts": "calculated",
    "complaints": "calculated"
  },
  "is_restricted": false,
  "data_source": "simulated"
}
```

---

### `GET /reports/export.csv`
Downloadable CSV report format with provenance tags (`simulated`, `calculated`, `verified`) labeled on every line item.

**Query Parameters:**
- `from` *(optional)*: Start date (ISO format)
- `to` *(optional)*: End date (ISO format)

**Headers:**
`Authorization: Bearer <token>`

**Response `200 OK`:**
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename=ghostwatt_sustainability_report_YYYYMMDD_HHMMSS.csv`

---

### `POST /reports/appliance-left-on`
Allows students and faculty to submit real-time observations of appliances left running in unoccupied rooms.
Generates an audit record, an `AL-XXXX` signal code, and an administrative notification for facility staff.

**Headers:**
`Authorization: Bearer <token>`

**Request Body:**
```json
{
  "room_id": 2,
  "equipment_type": "ac",
  "notes": "Spotted AC running at full blast while looking through classroom window after hours."
}
```

*Note: `equipment_type` and `appliance_kind` are accepted interchangeably.*

**Response `201 Created`:**
```json
{
  "status": "signal_recorded",
  "signal_id": "AL-0001",
  "complaint_id": 1,
  "complaint_code": "AL-0001",
  "category": "appliance_left_on",
  "room_code": "A-102",
  "block": "A",
  "equipment_type": "ac",
  "reported_by": "student@ghostwatt.demo",
  "created_at": "2026-10-12T21:35:00",
  "message": "Signal recorded for A-102. Notification sent to administrators.",
  "data_source": "simulated"
}
```

---

## 14. AI Sustainability Assistant (`/assistant`)

Natural language queries grounded in backend energy and water metrics powered by the Groq API (with deterministic template fallback).

### Architecture & Grounding Guarantees
- **Tool Grounding:** The assistant uses Groq function calling mapped to 6 whitelisted backend query functions:
  1. `top_ghost_rooms(period)`
  2. `explain_room_alert(room_id)`
  3. `verified_savings(period)`
  4. `block_wastage(period)`
  5. `open_complaints(user)`
  6. `recommended_actions()`
- **Number Guard:** Every numeric value in the LLM-generated explanation is strictly validated against the tool output. If any hallucinated or ungrounded number is detected, the LLM text is discarded and a deterministic template response is returned with `source: "fallback"`.
- **Role Enforcement:** Students can only view their own submitted water complaints. Querying other students' complaints or administrative operations results in an immediate access denial.
- **Graceful Fallback:** If the Groq API encounters a timeout (>8s), invalid API key, rate limit, or unsupported question, the assistant returns a template-based answer or a friendly listing of supported questions with `source: "fallback"`.

---

### `POST /assistant/ask`
Submit a natural language question to the AI Sustainability Assistant.

**Headers:**
`Authorization: Bearer <token>`

**Request Body:**
```json
{
  "question": "Which rooms have the highest ghost load?"
}
```

**Response `200 OK` (Groq Grounded):**
```json
{
  "answer": "Based on the latest 7-day readings, Classroom 101 (A-101) has the highest accumulated ghost load at 45.2 kWh, costing ₹384.20, followed by Computer Lab 1 (B-201) with 30.1 kWh.",
  "data_used": {
    "period": "7d",
    "top_rooms": [
      {
        "rank": 1,
        "room_code": "A-101",
        "name": "Classroom 101",
        "block": "A",
        "ghost_kwh": 45.2,
        "cost_inr": 384.2,
        "co2_kg": 32.09
      },
      {
        "rank": 2,
        "room_code": "B-201",
        "name": "Computer Science Lab 1",
        "block": "B",
        "ghost_kwh": 30.1,
        "cost_inr": 255.85,
        "co2_kg": 21.37
      }
    ],
    "total_ghost_kwh": 128.5
  },
  "source": "groq",
  "data_source": "simulated"
}
```

**Response `200 OK` (Fallback Mode — e.g. when API key is unset or timeout occurs):**
```json
{
  "answer": "Top rooms with the highest ghost load: 1. A-101 (Classroom 101) with 45.2 kWh (₹384.2); 2. B-201 (Computer Science Lab 1) with 30.1 kWh (₹255.85). Total waste: 128.5 kWh.",
  "data_used": {
    "period": "7d",
    "top_rooms": [
      {
        "rank": 1,
        "room_code": "A-101",
        "name": "Classroom 101",
        "block": "A",
        "ghost_kwh": 45.2,
        "cost_inr": 384.2,
        "co2_kg": 32.09
      }
    ],
    "total_ghost_kwh": 128.5
  },
  "source": "fallback",
  "data_source": "simulated"
}
```

---

### Example Questions & Tool Mappings

| Example Question | Selected Tool | Description |
| :--- | :--- | :--- |
| `"Which rooms have the highest ghost load?"` | `top_ghost_rooms(period)` | Ranks campus rooms by accumulated ghost kWh. |
| `"Why is room A-101 alerting?"` | `explain_room_alert(room_id)` | Diagnoses actual vs expected kW, reason code, and status. |
| `"How much energy have we saved through verified actions?"` | `verified_savings(period)` | Compares claimed savings with post-action verified power reductions. |
| `"Which block wastes the most electricity?"` | `block_wastage(period)` | Compares waste across Block A, Block B, and Block C. |
| `"What are the open water complaints?"` | `open_complaints(user)` | Fetches open complaints (students see own; admins see campus-wide). |
| `"What recommended actions should we take to reduce energy waste?"` | `recommended_actions()` | Prioritized switch-off actions ranked by potential kW reduction. |

---

### Student Privacy Refusal Example

When a student queries complaints filed by another user:
```json
{
  "question": "What complaints were filed by student2@ghostwatt.demo?"
}
```
**Response `200 OK`:**
```json
{
  "answer": "Access denied: Students are only permitted to view their own complaints.",
  "data_used": {
    "refusal": "Access denied: Students are only permitted to view their own complaints.",
    "role": "student",
    "count": 0
  },
  "source": "fallback",
  "data_source": "simulated"
}
```

---

### Unsupported Question Fallback Example

When an out-of-scope query is submitted:
```json
{
  "question": "What is the capital of France?"
}
```
**Response `200 OK`:**
```json
{
  "answer": "I can answer questions regarding campus electricity waste, ghost load diagnostics, verified savings, and water complaints. Here are examples of questions I can answer:\n1. 'Which rooms have the highest ghost load?'\n2. 'Why is room A-101 alerting?'\n3. 'How much energy have we saved through verified actions?'\n4. 'Which block wastes the most electricity?'\n5. 'What are the open water complaints?'\n6. 'What recommended actions should we take to reduce energy waste?'",
  "data_used": {},
  "source": "fallback",
  "data_source": "simulated"
}
```

---

## 15. Campus Sustainability Leaderboard (`/leaderboard`)

Ranks campus blocks (Block A, Block B, Block C) based on their Ghost Load efficiency score, letter grades, and wastage metrics. Enables friendly competition between campus departments to reduce energy waste.

### `GET /leaderboard/blocks`
Returns a ranked list of campus blocks with sustainability scores (0–100, higher is better), letter grades (`A+`, `A`, `B`, `C`, `D`), financial waste, CO2 emissions, and ceiling fan equivalents.

**Headers:**
`Authorization: Bearer <token>`

**Query Parameters:**
- `period` *(optional, default: `7d`)*: Time period window (`24h`, `7d`, `30d`, `all`).

**Response `200 OK`:**
```json
{
  "period": "7d",
  "blocks": [
    {
      "rank": 1,
      "block": "Block B",
      "name": "Mechanical & Civil Engineering",
      "actual_kwh": 945.20,
      "expected_kwh": 810.00,
      "ghost_kwh": 135.20,
      "waste_percentage": 14.30,
      "sustainability_score": 85.70,
      "grade": "A",
      "cost_inr": 1149.20,
      "co2_kg": 95.99,
      "fan_equivalents": 4.12,
      "fan_assumption": "Equivalent to 4.1 ceiling fans (75W) continuously running"
    },
    {
      "rank": 2,
      "block": "Block A",
      "name": "Administrative & Computer Science",
      "actual_kwh": 1420.50,
      "expected_kwh": 1050.00,
      "ghost_kwh": 370.50,
      "waste_percentage": 26.08,
      "sustainability_score": 73.92,
      "grade": "B",
      "cost_inr": 3149.25,
      "co2_kg": 263.06,
      "fan_equivalents": 11.28,
      "fan_assumption": "Equivalent to 11.3 ceiling fans (75W) continuously running"
    },
    {
      "rank": 3,
      "block": "Block C",
      "name": "Electrical & Electronics Engineering",
      "actual_kwh": 1350.00,
      "expected_kwh": 890.00,
      "ghost_kwh": 460.00,
      "waste_percentage": 34.07,
      "sustainability_score": 65.93,
      "grade": "C",
      "cost_inr": 3910.00,
      "co2_kg": 326.60,
      "fan_equivalents": 14.01,
      "fan_assumption": "Equivalent to 14.0 ceiling fans (75W) continuously running"
    }
  ],
  "best_block": "Block B",
  "worst_block": "Block C",
  "assumptions": {
    "fan": "Ceiling fan baseline of 75W continuous draw",
    "tariff": "Commercial campus tariff of Rs 8.50 per kWh",
    "emissions": "Regional grid emission factor of 0.71 kg CO2/kWh",
    "score": "Sustainability score = 100 - (ghost_kwh / actual_kwh * 100)"
  },
  "data_source": "simulated"
}
```

