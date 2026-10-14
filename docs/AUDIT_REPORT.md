# Eco-Campus: Full Audit Report

Scope: backend first, then frontend, then the integration between them, against the Kaushal 8.0 PS-04 requirements (`docs/SPEC.md`).
No git commits, pushes or remote changes were made; every change is in the local project files.

## 1. Architecture summary

**Backend** (`backend/`, FastAPI + SQLAlchemy + SQLite, Python 3.12)
- `app/routes/*`: thin HTTP layer (auth, dashboard, electricity, ghost_load, rooms, timetable, actions, savings, water, complaints, reports, app_settings, simulator, live, leaderboard, assistant). Every router is mounted at `/x` and `/api/x`.
- `app/services/*`: pure logic (expected demand, ghost load, savings verification, water analysis, carbon/equivalents, simulator with a virtual 15-minute clock, data generator, report builder, assistant tools, Groq assistant with a number guard and template fallback).
- `app/core/*`: config, JWT/bcrypt, `get_current_user` / `require_admin` dependencies (roles are enforced server-side).
- `app/db/*`: models and the startup migration. SQLite in WAL mode.

**Frontend** (`frontend/`, React 18 + Vite + React Router + Recharts + lucide-react, plain CSS)
- `services/*` is the only layer that talks to the API (`httpClient.js` adds the JWT, language header, timeout, error mapping); each service can be switched to mock data with `VITE_USE_MOCK`.
- `pages/admin/*` (overview, electricity, water, alerts and savings, maintenance, reports, simulator, settings, and now rooms and timetable), `pages/student/*` (home, assistant chat, my reports, impact, and now campus live), shared leaderboard, English and Hindi translations.

## 2. Issues found

### Security (backend)
| # | Issue | Severity |
|---|---|---|
| S1 | `Authorization: Bearer mock-admin-token` (and `mock-student-token`) was accepted as a real admin/student login. | Critical |
| S2 | Admin password reset was unauthenticated and not tied to any account: anyone could call `verify-otp` with the public demo OTP and reset the first admin's password. | Critical |
| S3 | Hardcoded master passwords: `admin123` / `demo` were accepted for any admin account even after the real password was changed; `admin@ecocampus.demo` silently mapped to the admin. | High |
| S4 | Every mobile number logged into the same single student account, so all students shared data (defeats the privacy rule). | High |
| S5 | Default JWT secret was a public placeholder. | High |
| S6 | Complaint photo upload used the client's filename (crashed with HTTP 500 on `../x.png`), had no content check and trusted the extension only. | Medium |
| S7 | No brute-force protection on login/OTP; CORS origins hardcoded; no `nosniff` header on served uploads. | Medium |
| S8 | A reset token could not be told apart from a login token (fixed while rewriting S2). | n/a |

### Data integrity and correctness (backend)
- D1: **4,552 duplicate meter-reading groups and 564 duplicate water-reading groups** in the shipped database (re-running a simulated period inserted rows again), double-counting kWh and litres in every total.
- D2: Queries without an upper bound included "future" readings beyond the simulation clock (122 rows in the shipped DB).
- D3: Settings accepted `nan` / `inf` / text, which turned costs and equivalents into `null` in every dashboard response.
- D4: Invalid `from` / `to` / `ts` / `period` values were silently ignored (returned all data); `from > to` returned an empty 200; a date-only `to` dropped the whole last day.
- D5: Timetable accepted `25:99`; a room with history could be deleted and crash with a 500; complaints could be assigned to a student account; complaints without a location or description were created with made-up text.
- D6: Leak detection ignored every water setting (hardcoded 50 L/h and 20 L/h baseline); the water bucket size was hardcoded to 15 in two places.
- D7: Switching the same appliance off twice created a second "claimed" saving.
- D8: Simulator ticks could run concurrently (background clock and `/sim/tick`), appliance switch-offs were lost on restart, and DB work ran on the event loop.
- D9: The dev database file and uploads folder were resolved relative to the current directory (starting uvicorn from another folder created an empty database).
- D10: The old test suite wrote into the real `eco-campus.db` (the shipped DB has tariff 9.25 and CO2 0.75 instead of the documented defaults, plus test complaints/actions).
- D11: Title and description of a complaint: when both were entered, the title was thrown away.

### Fabricated numbers (violates "every number comes from data")
- F1: `/dashboard/admin-overview`: KPIs, block shares and building names/values were hardcoded constants, and the chart fell back to invented values.
- F2: `/dashboard/student-home`: fake stats and fake recent reports for new students; impact figures were fixed constants (`accepted * 85 kWh`).
- F3: `/dashboard/public-impact`: invented floors (`max(1240, ...)`) and a made-up waste figure.

### Frontend
- E1: **`frontend/.env` had `VITE_USE_MOCK=true`: the app never called the backend.**
- E2: Student form offered 9 issue types but the backend accepted 5: the other 4 failed with HTTP 400.
- E3: My Reports filters used statuses the backend never produces (`accepted`, `rejected`) and missed `acknowledged`, `assigned`, `reopened`; there was no way to see history.
- E4: Settings page edited keys the backend does not have (`low_flow_threshold_lph`, `night_flow_baseline_lph`), so water settings were never saved.
- E5: Simulator page called `/sim/appliance` (did not exist) and sent `timestamp` to a reset endpoint that read `to_date`.
- E6: Admin reports and overview used today's real date for ranges while data lives on the simulation clock (empty results once the dates drift apart).
- E7: Alerts page always showed "UNSCHEDULED_LOAD" instead of the real reason code.
- E8: Admin could not assign complaints, mark notifications read, or see the most-affected locations. Browser `alert()` was used for errors.
- E9: Validation errors from FastAPI (list format) showed a generic message; DELETE (204) responses broke the JSON parser; no request timeout.
- E10: The demo admin email in the frontend differed from the seeded one.
- E11: Vite proxy was hardcoded to `localhost:8000` (IPv6 resolution problems, blocked ports).

### Features implemented in the backend but not available in the frontend (now integrated)
| Backend feature | Frontend integration |
|---|---|
| Rooms CRUD, equipment CRUD, timetable CRUD (spec section 6) | New admin page **Rooms and Timetable** (`/admin/rooms`) |
| Complaint assignment (`assigned_to`) and staff list | Assignee dropdown and "Assigned" column in Maintenance |
| Frequently affected locations and overdue count | Hotspots line in Maintenance |
| Admin notifications | Unread list with mark-one / mark-all read |
| Complaint history, reopen | Expandable report with status history and "Report again" on My Reports |
| `building` field | Optional building select on the report form (from the rooms' blocks) |
| Live snapshot, savings summary, water alerts (read-only for students; spec section 2) | New student page **Campus Live** (`/student/campus`) |
| Simulator appliance control | Existing simulator page now works (endpoint added) |

## 3. Changes made

**Backend (modified):** `app/main.py`, `core/config.py`, `core/deps.py`, `db/database.py`, `db/models.py`, `routes/auth.py`, `routes/complaints.py`, `routes/dashboard.py`, `routes/electricity.py`, `routes/water.py`, `routes/reports.py`, `routes/ghost_load.py`, `routes/leaderboard.py`, `routes/rooms.py`, `routes/simulator.py`, `routes/actions.py`, `routes/app_settings.py`, `schemas/{auth,complaints,dashboard,rooms,settings,simulator,timetable}.py`, `services/{simulator,water_analysis,data_generator}.py`, `requirements.txt`, `.env.example`, `tests/conftest.py`.
**Backend (new):** `core/dates.py`, `core/phone.py`, `services/otp_store.py`, `services/rate_limit.py`, `services/campus_metrics.py`, `tests/test_audit_fixes.py`.
**Frontend (modified):** `.env`, `.env.example`, `vite.config.js`, `package.json`, `config.js`, `services/{httpClient,complaintsApi,roomsApi,timetableApi}.js`, `utils/format.js`, `i18n/{en,hi}.app.js`, `layouts/nav.js`, `App.jsx`, `styles/app.css` (additions only, theme untouched), `components/student/{ReportForm.jsx,categoryIcons.js}`, `pages/student/StudentMyReports.jsx`, `pages/admin/{AdminMaintenance,AdminOverview,AdminReports,AdminSettings,AdminAlerts}.jsx`.
**Frontend (new):** `pages/admin/AdminRooms.jsx`, `pages/student/StudentCampus.jsx`, `scripts/api-contract.mjs`, `scripts/render-check.mjs`.
**Docs:** `README.md`, `LIBRARIES.md`, `docs/API.md`, this report.

Other improvements: DB migration at startup (adds `users.phone` / `full_name`, removes duplicate readings, adds unique indexes), bundle split (main JS 747 kB to 192 kB), request timeout, accessible expand/collapse controls, inline errors instead of `alert()`.

## 4. Testing performed

| Check | Result |
|---|---|
| Backend `pytest` (111 original + 68 new regression tests) | **179 passed** (runs on a throwaway DB copy; real DB verified unchanged) |
| Frontend `vite build` | passes |
| `npm run check:api`: real frontend service functions vs live backend, admin + student + triage flow | **18 / 18** |
| `npm run check:render`: all 16 pages mounted headless against live backend, plus 4 interactions | **20 / 20** |
| Live exploit reproduction before the fix (mock token, unauthenticated reset) and after | both now rejected (`401` / `400`) |

## 5. Not verified / limitations
- **Real Groq calls were not tested** (no key or Groq access here). The model default is `openai/gpt-oss-120b`. The previous value `qwen/qwen3.8-27b` was not found on Groq's published list, so make sure your own `backend/.env` no longer sets it; confirm with your key. The fallback path is tested.
- **No real browser was available**: layout, colours, responsiveness, charts (Recharts needs real layout) and the Hindi UI were not checked visually. The render check proves pages mount with real data and have no errors, not that they look right.
- Real SMS delivery does not exist (demo OTP only). With `DEMO_MODE=false`, OTPs are printed in the server log.
- OTP and rate-limit state is in memory (single process). Issued JWTs stay valid until expiry after a password reset (no revocation list). Tokens live in `localStorage`.
- Complaint photos are served without authentication (`/uploads/...`, random file names).
- Student "impact" links reports to rooms by room codes written in the report location text, and to water alerts by building name; it is intentionally conservative and mostly zero until an admin acts.
- Your shipped DB has a 9.25 tariff and 0.75 CO2 factor, test complaints and a simulation clock at 2026-10-20. Run `python -m scripts.seed` for a clean demo, or reset the values in Settings.

## 6. Recommendations
1. Reseed before a demo (`python -m scripts.seed`), set a real `JWT_SECRET`, and decide whether `DEMO_MODE` stays on.
2. Verify your Groq key and model id once; keep the fallback.
3. Click through every page in a real browser on a laptop and a phone before judging.
4. Later: refresh tokens, upload auth, Redis-backed limits, an SMS provider, real meter ingestion (see README).
