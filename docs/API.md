# GhostWatt — API Reference

> **Status:** Skeleton — each phase appends endpoint docs with example request/response.
> Base URL: `http://localhost:8000`
> All protected routes require `Authorization: Bearer <token>` header.

---

## Health

### GET /health
Returns server status. No authentication required.

```
Response 200:
{ "status": "ok", "version": "0.1.0", "mode": "demo" }
```

---

## Auth  `POST /auth/...`

<!-- Phase 3: append login, token-refresh, me endpoints here -->

---

## Dashboard  `GET /dashboard/...`

<!-- Phase 3: append summary-cards, live-metrics endpoints here -->

---

## Electricity  `GET /electricity/...`

<!-- Phase 3: append readings, room-comparison, history endpoints here -->

---

## Ghost Load  `GET /ghost-load/...`

<!-- Phase 2 / Phase 3: append current-load, room-ranking, 24h-chart endpoints here -->

---

## Rooms  `GET|POST|PUT /rooms/...`

<!-- Phase 3: append room list, create, update endpoints here -->

---

## Timetable  `GET|POST|PUT /timetable/...`

<!-- Phase 3: append timetable CRUD endpoints here -->

---

## Verified Savings  `GET|POST /savings/...`

<!-- Phase 5: append savings list, verification-trigger endpoints here -->

---

## Water  `GET /water/...`

<!-- Phase 6: append flow readings, leak-alerts endpoints here -->

---

## Complaints  `GET|POST|PUT /complaints/...`

<!-- Phase 6: append submit, list, update-status endpoints here -->

---

## Reports  `GET /reports/...`

<!-- Phase 6: append electricity-report, water-report, CSV-export endpoints here -->

---

## Settings  `GET|PUT /settings/...`

<!-- Phase 3: append get-all, update-setting endpoints here (admin only) -->

---

## Simulator  `POST /simulator/...`

<!-- Phase 7: append toggle-appliance, inject-reading endpoints here -->

---

## AI Assistant  `POST /assistant/ask`

<!-- Phase 6: append ask endpoint with grounded response schema here -->
