# EcoCampus Frontend

React + Vite, plain CSS, Lucide icons, Recharts (for the dashboard charts later).
Built to sit next to the FastAPI backend: `GhostWatt/frontend` and `GhostWatt/backend`.

## Run it

```bash
cd frontend
npm install
cp .env.example .env     # Windows: copy .env.example .env
npm run dev              # http://localhost:5173
```

## Two ways to run

| Mode | `.env` | What happens |
|------|--------|--------------|
| Frontend only | `VITE_USE_MOCK=true` | Fake data from `src/services/mock/`. No backend needed. OTP is always `123456`. |
| With backend | `VITE_USE_MOCK=false` | Calls FastAPI at `http://localhost:8000` through the Vite proxy (`/api`, `/uploads`). |

`VITE_DEMO_MODE=true` pre-fills the demo logins and shows the demo OTP on screen.

## Demo accounts (backend/scripts/seed.py must create these)

| Role | Login |
|------|-------|
| User (student) | mobile `9876543210` + OTP |
| Admin | `admin@ecocampus.demo` / `admin123`, mobile `9876500000` (for Forgot password) |

They are defined in `src/config.js`. Change them there and in `seed.py` together.

## How the frontend maps to the backend

One service file per backend route file, same name. To connect a page, fill in its service file.

| backend/app/routes/ | frontend/src/services/ | Page (later) |
|---|---|---|
| auth.py | authApi.js (done) | pages/Login.jsx (done) |
| dashboard.py | dashboardApi.js (login-page part done) | pages/Dashboard.jsx |
| electricity.py | electricityApi.js | pages/Electricity.jsx |
| ghost_load.py | ghostLoadApi.js | pages/GhostLoad.jsx |
| rooms.py, timetable.py | roomsApi.js, timetableApi.js | pages/RoomsTimetable.jsx |
| savings.py | savingsApi.js | pages/VerifiedSavings.jsx |
| water.py | waterApi.js | pages/Water.jsx |
| complaints.py | complaintsApi.js | pages/Complaints.jsx |
| reports.py | reportsApi.js | pages/Reports.jsx |
| settings.py | settingsApi.js | pages/Settings.jsx |
| simulator.py | simulatorApi.js | simulator controls in Topbar |
| assistant.py | assistantApi.js | pages/AskEcoCampus.jsx |

Other matches: `core/config.py` ↔ `src/config.js`, `core/deps.py` (role checks) ↔ `src/auth/RequireAuth.jsx`
(the UI only hides pages; the backend must still check the role on every request).

All `fetch()` calls live in `src/services/httpClient.js`. It adds the login token and the
`Accept-Language` header (`en` or `hi`) automatically, and supports file uploads (complaint photos).

## Auth endpoints the backend must provide (routes/auth.py)

Phone numbers are sent as `+91XXXXXXXXXX`. Every success returns JSON.

| Endpoint | Body | Returns |
|---|---|---|
| POST `/api/auth/student/otp/send` | `{ phone }` | `{ resend_after_seconds, dev_otp? }` |
| POST `/api/auth/student/otp/verify` | `{ phone, otp }` | `{ access_token, user: { id, name, role } }` |
| POST `/api/auth/admin/login` | `{ email, password }` | `{ access_token, user: { id, name, role } }` |
| POST `/api/auth/admin/forgot-password/send-otp` | `{ phone }` | `{ resend_after_seconds, dev_otp? }` |
| POST `/api/auth/admin/forgot-password/verify-otp` | `{ phone, otp }` | `{ reset_token }` |
| POST `/api/auth/admin/forgot-password/reset` | `{ reset_token, new_password }` | `{ message }` |

- `role` is `"student"` or `"admin"`. Students have no password. Students cannot use the admin endpoints.
- OTP: 6 digits, expires after about 5 minutes, limit the attempts, store it hashed.
- Password: at least 8 characters (`MIN_PASSWORD_LENGTH` in `src/config.js`).
- **SMS:** sending a real SMS needs an SMS provider (for example MSG91, Twilio or Fast2SMS).
  For the hackathon, the backend can return the code as `dev_otp` when a `DEBUG_OTP=true` setting is on.
  The login page then shows it on screen. Turn this off for any real use.

### Error format

Send errors as `{ "detail": { "code": "INVALID_OTP", "message": "..." } }`.
The frontend translates by `code`. Codes it knows: `INVALID_CREDENTIALS`, `INVALID_OTP`, `OTP_EXPIRED`,
`TOO_MANY_ATTEMPTS`, `WRONG_ROLE`, `RESET_SESSION_EXPIRED`. A plain string `detail` also works (shown in English).

## Login page numbers: GET /api/dashboard/public-impact (no login needed)

```json
{
  "is_simulated": true,
  "cards": [
    { "key": "carbon",      "value": 1240,  "unit": "kg",     "change_pct": 12, "equivalent_value": 87 },
    { "key": "electricity", "value": 3560,  "unit": "kwh",    "change_pct": 18, "equivalent_value": 12 },
    { "key": "water",       "value": 15200, "unit": "litres", "change_pct": 20, "equivalent_value": 76 },
    { "key": "waste",       "value": 320,   "unit": "kg",     "change_pct": 14 }
  ]
}
```

The backend sends numbers only. Labels and sentences (for example "Equivalent to 87 trees planted") are
written by the frontend in `src/i18n`, so they switch between English and Hindi. The first two cards show
on the left and the next two on the right. `unit` is `kg`, `kwh` or `litres`.

## Language (English / Hindi)

- English is the default. The choice is saved in the browser (`ec_language`), so it stays after login,
  logout and refresh.
- All text lives in `src/i18n/en.js` and `src/i18n/hi.js`. In a component: `const { t } = useLanguage()` then `t('auth.sendOtp')`.
- To add a sentence, add the same key to both files. If a Hindi key is missing, English is shown.
- Put `<LanguageToggle />` in the dashboard Topbar so people can switch after login.

## Campus photo

The login background is `src/assets/campus-bg.webp`. Replace that file to change it.

## Signed-in screens (admin + student)

- `/admin/overview`: Overview (KPIs, actual vs baseline chart, consumption by block, building table, CSV export). Other admin menu items are placeholders for now.
- `/student/home`, `/student/report`, `/student/my-reports`, `/student/impact`: student screens.
- Login sends everyone to `/dashboard`, which forwards to the right home by role.
- Pages live in `src/pages/admin` and `src/pages/student`. The sidebar is `src/layouts/AppShell.jsx` and the menus are in `src/layouts/nav.js`.
- Every page reads data through `src/services/*Api.js`. With `VITE_USE_MOCK=true` these use `src/services/mock/*`; with `false` they call the FastAPI routes documented above each service function.

Endpoints these screens expect (add them to the backend routes):

| Method | Path | Used by |
| --- | --- | --- |
| GET | `/api/dashboard/admin-overview?from&to&zone` | Admin Overview |
| GET | `/api/dashboard/student-home` | Student Home, Impact |
| GET | `/api/complaints/mine` | My Reports |
| POST | `/api/complaints` (multipart: title, category, location, description, image) | Report form |
