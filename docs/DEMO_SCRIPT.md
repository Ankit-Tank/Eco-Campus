# GhostWatt — 3-Minute Hackathon Demo Script

> **Demo Persona:** Sustainability Officer & Facility Manager demonstrating GhostWatt to university leadership and hackathon judges.  
> **Total Duration:** 3 minutes (180 seconds).  
> **Objective:** Prove that GhostWatt solves the invisible campus energy crisis by isolating Ghost Load from scheduled classes, closing the loop with verified physical savings, detecting nocturnal water leaks, and providing an AI assistant with zero hallucinations.

---

## Quick Reference Setup

Before starting the presentation:
1. Ensure the backend server is running:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
2. Open Swagger UI at [`http://localhost:8000/docs`](http://localhost:8000/docs) (or the frontend UI if attached).
3. Have demo accounts ready:
   - **Admin:** `admin@ghostwatt.demo` / `admin123`
   - **Student:** `student@ghostwatt.demo` / `student123`

---

## Walkthrough Breakdown

```
[00:00 - 00:45] Act I: The Invisible Crisis & Campus Overview
[00:45 - 01:45] Act II: Live Ghost Load Detection & Closed-Loop Verification
[01:45 - 02:30] Act III: Night-Flow Water Leaks & Student Crowdsourcing
[02:30 - 03:00] Act IV: Grounded AI Assistant & Architecture Wrap-Up
```

---

### Act I: The Invisible Crisis & Campus Overview (0:00 – 0:45)

**Spoken Narration:**
> "Universities spend tens of lakhs every month on electricity, but campus facilities have a blind spot: they can't tell the difference between productive energy used during a lecture and **Ghost Load**—air conditioners, projectors, and computers humming in empty rooms after hours.
>
> GhostWatt changes this. Instead of dumb threshold alarms, GhostWatt compares real-time meter telemetry against live academic timetables and occupancy models to isolate pure waste."

**Screen Action / Endpoint Call:**
- Call `GET /live/snapshot` or `GET /dashboard/summary`:
  - Show campus KPIs: **Actual kWh**, **Expected kWh**, and **Ghost Load kWh**.
  - Highlight the intuitive human-scale equivalents:
    - *"Notice how our waste is translated into physical terms: equivalent to 14 ceiling fans running 24/7, and 120 buckets of potable water lost."*
- Call `GET /leaderboard/blocks`:
  - Show the Block Sustainability Leaderboard:
    - *"Block B has an 'A' grade with only 14% waste, while Block C is trailing with a 'C' grade. This fosters inter-departmental accountability."*

---

### Act II: Live Ghost Load Detection & Closed-Loop Verification (0:45 – 1:45)

**Spoken Narration:**
> "Let's see GhostWatt in action with a live scenario. It's 9:30 PM on campus. All classes have ended, but an air conditioner was left running in Classroom A-102."

**Step 1 — Inject Live Demo Event:**
- Execute:
  ```http
  POST /sim/scenario/demo
  Authorization: Bearer <admin_token>
  ```
- **Show Response:**
  - Simulation clock resets to `21:30:00`.
  - Simulation speed accelerates to `60x` (1 real second = 1 minute of simulation).
  - Room `A-102` immediately registers `actual_kw: 3.75` vs `expected_kw: 0.15`.
  - Alert status fires: `TRIGGERED (High Usage)`.

**Step 2 — Student Crowdsourcing Signal:**
- Execute:
  ```http
  POST /reports/appliance-left-on
  Authorization: Bearer <student_token>
  {
    "room_id": 2,
    "equipment_type": "ac",
    "notes": "Saw AC running through classroom window after hours."
  }
  ```
- **Show Response:**
  - Generates signal `AL-0001` and alerts facilities staff via `GET /complaints/notifications/admin`.

**Step 3 — Corrective Action (The Closed Loop):**
- Execute:
  ```http
  POST /actions/switch-off
  Authorization: Bearer <admin_token>
  {
    "room_id": 2,
    "equipment_id": 4,
    "notes": "Night security switched off AC in A-102"
  }
  ```
- **Show Response:**
  - Action recorded as `PENDING`. Claimed reduction: `3.60 kW`.
  - Simulator sets physical appliance to `OFF`.

**Step 4 — Automated Verification in Seconds:**
- Wait 2–3 seconds (simulation advances at 60x speed).
- Call `GET /actions/{action_id}` and `GET /savings/records`:
  - *"Watch the verification engine: because our simulation runs at 60x, the 15-minute post-action window elapses in seconds."*
  - Status transitions to **`VERIFIED`**.
  - Show `credited_kwh`, `monetary_saving_inr`, and `emissions_kg`.
  - Point out: *"GhostWatt never credits savings if a drop was caused by a class ending. Every rupee saved is mathematically proven."*

---

### Act III: Night-Flow Water Leaks & Student Crowdsourcing (1:45 – 2:30)

**Spoken Narration:**
> "Electricity isn't the only resource leaking away. Water pipe fractures and stuck flush valves run silently all night."

**Screen Action / Endpoint Call:**
- Call `GET /water/alerts`:
  - Show the automated night-flow alert:
    - Flow rate at 03:00 AM exceeded baseline threshold (e.g. 180 L/h vs 30 L/h expected).
    - Status: `SUSPECTED` with excess litres calculated in bucket equivalents (e.g. `24.0 buckets`).
- Call `PATCH /water/alerts/{id}`:
  - Admin triages the alert to `CONFIRMED` with inspection notes: *"Plumber repaired cracked elbow under Block C riser."*
- Call `POST /complaints`:
  - Show student complaint submission with location, category (`leaking_tap`), and photo attachment support.
  - Call `GET /complaints`:
    - Demonstrate privacy: student sees only their own tickets; admin sees campus-wide SLA and overdue tracking.

---

### Act IV: Grounded AI Assistant & Architecture Wrap-Up (2:30 – 3:00)

**Spoken Narration:**
> "Finally, how do campus leaders interrogate this data? Meet our AI Sustainability Assistant, powered by the Groq LPU API and Qwen 3.8."

**Step 1 — Natural Language Query with Tool Calling:**
- Call `POST /assistant/ask`:
  ```json
  {
    "question": "Which rooms have the highest ghost load right now?"
  }
  ```
- **Show Response:**
  - Ultra-fast response (< 500 ms) powered by Groq.
  - Inspect `data_used`: proves the model called `top_ghost_rooms("24h")`.
  - Highlight the **Number Guard**:
    - *"Every single number in the assistant's answer was validated against the database. If the model hallucinates a number, GhostWatt's guardrail discards the text and falls back to a deterministic template."*

**Step 2 — Student Privacy Refusal:**
- Call `POST /assistant/ask` with student token:
  ```json
  {
    "question": "Show me complaints filed by other students."
  }
  ```
- **Show Response:**
  - Clean refusal: *"Access denied: Students are only permitted to view their own complaints."*

**Closing Line:**
> "GhostWatt doesn't just display energy charts—it verifies physical savings, eliminates water waste, and empowers every student and facility manager on campus. Thank you!"

---

## Judge FAQ Cheatsheet

| Question | Winning Answer |
|---|---|
| **"How does this differ from standard BMS / IoT dashboards?"** | Conventional dashboards only display raw kW. They cannot tell if a 5 kW load is a scheduled lab session or forgotten appliances. GhostWatt integrates timetable intelligence, calculates expected demand dynamically, and features an automated verification engine that proves savings post-action. |
| **"How do you prevent false savings when classes end?"** | Our savings verification formula calculates: `reduction = min(max(0, pre_avg - post_avg), max(0, pre_avg - expected_kw))`. If expected demand drops because a class ended, zero savings are credited. |
| **"Can this integrate with real campus infrastructure?"** | Yes. The modular architecture connects to Modbus/BACnet energy meters via standard MQTT/HTTP ingestion adapters, ERP timetables via REST sync, and existing campus BMS controllers. |
| **"Why Groq and Qwen 3.8?"** | Groq LPU hardware gives sub-second token latency, critical for interactive conversational queries during facility audits. Qwen 3.8 excels at strict tool calling and zero hallucination adherence. |
