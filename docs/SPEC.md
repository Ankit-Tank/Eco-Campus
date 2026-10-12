# GhostWatt — Intelligent Campus Energy & Sustainability Platform

## 1. Project Overview

GhostWatt is a web-based campus sustainability platform designed to identify unnecessary electricity consumption, reduce resource wastage, and measure the environmental impact of corrective actions. Its primary focus is electricity monitoring through a unique feature called **Ghost Load Intelligence**, which compares actual electricity consumption against the amount of electricity reasonably expected to be used according to classroom timetables, occupancy, room type, and electrical equipment.

Instead of simply displaying how much electricity a campus has consumed, GhostWatt identifies how much consumption exceeds the expected requirement, estimates its financial and environmental cost, and recommends actions to reduce it.

The secondary module focuses on water conservation. It monitors water consumption, flags unusual flow patterns that may indicate leaks, and allows students to submit water-wastage complaints directly to the administration.

The platform will combine these capabilities with role-based login, interactive dashboards, live-style counters, historical graphs, an **AI Assistant powered by the Groq API**, downloadable reports, and a Verified Savings Meter that distinguishes claimed savings from savings supported by subsequent meter readings.

The application will be developed as a functional software-only MVP for the Kaushal 8.0 hackathon. Physical sensors and real campus infrastructure will not be required. Simulated electricity-meter readings, water-flow records, and classroom timetables will be used to demonstrate the system, with a clear indication whenever data is simulated.

**Core principle: Don't just show how much electricity was consumed. Show how much electricity could have been avoided, why it exceeded expected usage, and whether corrective action actually reduced consumption.**

## 2. Login Page and Role-Based Authentication

GhostWatt must begin with a modern, visually attractive login page that allows users to enter the system as either a **Student** or an **Admin**. The login page should display the GhostWatt logo, a tagline such as "Detect Waste. Save Energy. Build a Greener Campus.", a sustainability-themed illustration, role-selection cards, username or email and password fields, a show/hide password control, and a prominent login button.

After authentication, both roles should access the same application platform and its common monitoring features, while administrative actions remain restricted to authorized administrators.

**Student permissions:** View dashboard, Ghost Load alerts, AI Assistant, savings, reports, submit water complaints, track own complaints.

**Admin permissions:** Campus-wide monitoring, room timetables, electricity limits, Ghost Load alerts, complaint management, maintenance assignments, corrective actions, system settings, campus-wide reports.

The application must enforce role-based permissions in the backend, rather than merely hiding buttons in the interface.

## 3. Common Dashboard After Login

A persistent left sidebar should contain: Overview, Electricity Monitoring, Ghost Load Analysis, Rooms and Timetable, Verified Savings, Water Monitoring, Water Complaints, Reports, Ask GhostWatt, Settings.

The dashboard should contain summary cards for actual electricity consumption, expected electricity consumption, estimated Ghost Load, water consumption, and electricity-related carbon emissions.

## 4. Primary Module — Electricity Monitoring

The system monitors approximately 10–15 rooms across three campus blocks. Historical data at 15-minute intervals with deliberate waste scenarios.

## 5. Core Differentiator — Ghost Load Intelligence

**Ghost Load (kW) = max(0, Actual Demand − Expected Demand)**

**Estimated Ghost Load (kWh) = Ghost Load (kW) × 0.25 hours**

Initial demo settings: ₹8.50 per kWh, 0.71 kg CO₂ per kWh — both configurable by admin.

## 6. Expected Electricity Limits and Room Timetable

Statuses: "In Session," "No Class," "Upcoming Class," "Within Expected Usage," "High Usage," "Possible Idle Load."

## 7. Live Simulation and Interactive Demonstration

Users can toggle simulated appliances ON/OFF. Dashboard reflects changes in subsequent readings.

## 8. Verified Savings Meter

**Verified Power Reduction (kW) = max(0, Average Pre-Action Demand − Average Post-Action Demand)**

**Verified Energy Saving (kWh) = Verified Power Reduction (kW) × 0.25 hours**

Savings labelled **"Simulated Verified Savings"**.

## 9. Secondary Module — Water Monitoring

Hourly simulated water-flow data. Flag unusual flow between 1 AM–4 AM vs configurable low-flow baseline.

## 10. Student Water Complaints and Admin Management

Complaint lifecycle: Submitted → Acknowledged → Assigned → In Progress → Resolved → Reopened.

## 11. AI Assistant — Powered by Groq API

Controlled data-grounding workflow. Backend retrieves data → Groq explains results. Groq must never invent numerical values. Graceful fallback if API unavailable.

## 12. Reports and Sustainability Impact

On-screen report and CSV export. Distinguish actual meter readings, simulated data, calculated estimates.

## 13. Human-Readable Environmental Impact

Ghost Load expressed as equivalent ceiling fans (75 W each). Water expressed as equivalent buckets (configurable volume).

## 14. Visual Design

- **Ink Navy #0F1E2E:** navigation, dark panels
- **Amber #F2A413:** expected electricity
- **Violet #5B3FD9:** Ghost Load (hatched pattern)
- **Teal #0F8FA0:** water monitoring
- **Green #1F8A5B:** verified savings
- Fonts: Bricolage Grotesque (headings), Figtree (body)

## 15. Technical Architecture

- **Frontend:** React + Vite, Recharts, Lucide icons
- **Backend:** Python FastAPI, SQLite, SQLAlchemy, Pandas/NumPy
- **AI:** Groq API (backend only — key never exposed to browser)
- **Auth:** JWT tokens, bcrypt password hashing

## 16. Data Model

- **Users:** id, username/email, password_hash, role, is_active
- **Rooms:** id, block, name, room_type, capacity, equipment_config (JSON), idle_baseline_kw
- **Timetables:** id, room_id, day_of_week, start_time, end_time, activity, expected_students
- **MeterReadings:** id, room_id, timestamp, actual_demand_kw, interval_kwh, source, is_simulated
- **Actions:** id, room_id, user_id, action_type, equipment, timestamp, notes, verification_status
- **WaterReadings:** id, location_id, timestamp, flow_rate_lph, interval_litres, expected_baseline_lph, source
- **Complaints:** id, student_id, building, location, category, description, attachment_path, assigned_to, status, created_at, updated_at, resolution_notes
- **SavingsRecords:** id, action_id, pre_avg_kw, post_avg_kw, credited_kwh, monetary_saving, emissions_kg, verification_status
- **Settings:** key, value, description, updated_at

## 17. Development Phases

1. Data generator and schema
2. Ghost Load engine
3. API and authentication
4. Dashboard (frontend)
5. Verified savings
6. Water, complaints, reports, Groq assistant

## 18. Acceptance Criteria

1. Role-based login works
2. Dashboard shows actual vs expected from generated data
3. Ghost Load calculations are explainable at room level
4. Live-style metrics update
5. Mark-switched-off triggers verification workflow
6. Claimed vs verified savings are separate
7. Carbon calculations use configurable factors
8. Student can submit complaint; admin can manage
9. Night-flow data triggers leak alert
10. Sustainability report generates from calculated data
11. Groq assistant answers using backend data with fallback
12. README covers setup, demo accounts, simulated-data disclaimer
13. LIBRARIES.md is complete

## 19. Libraries and APIs

See LIBRARIES.md. Groq API key stored in backend .env, never committed.
