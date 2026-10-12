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

## 12. Future Modules (Upcoming Phases)

- **Phase 6:** Complaints & Feedback (`/complaints`) — `POST /complaints`, `GET /complaints`, `PUT /complaints/{id}/status`
- **Phase 6:** Reports & CSV Export (`/reports`) — `GET /reports/electricity`, `GET /reports/water`, `GET /reports/export`
- **Phase 6:** AI Sustainability Assistant (`/assistant`) — `POST /assistant/ask`
- **Phase 7:** Interactive Simulator Control (`/simulator`) — `POST /simulator/action`, `POST /simulator/inject`
