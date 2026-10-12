# LIBRARIES.md — GhostWatt External Dependencies

> Updated as each phase is implemented.

---

## Backend

| Library / API | Version pinned? | Purpose | License |
|---|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | latest | HTTP API framework | MIT |
| [Uvicorn](https://www.uvicorn.org/) | latest (standard extras) | ASGI server | BSD |
| [SQLAlchemy](https://www.sqlalchemy.org/) | latest | ORM + SQLite access | MIT |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | latest | Config from .env | MIT |
| [python-jose](https://github.com/mpdavis/python-jose) | latest (cryptography extras) | JWT encode/decode | MIT |
| [passlib](https://passlib.readthedocs.io/) | latest (bcrypt extras) | Password hashing | BSD |
| [pandas](https://pandas.pydata.org/) | latest | Data manipulation, historical summaries | BSD |
| [numpy](https://numpy.org/) | latest | Numerical calculations | BSD |
| [httpx](https://www.python-httpx.org/) | latest | Async HTTP client (Groq fallback, testing) | BSD |
| [groq](https://github.com/groq/groq-python) | latest | Groq API SDK — AI Assistant | Apache 2.0 |
| [python-multipart](https://andrew-d.github.io/python-multipart/) | latest | File upload parsing (complaint photos) | Apache 2.0 |
| [pytest](https://pytest.org/) | latest | Unit and integration testing | MIT |

## External APIs

| API | Purpose | Key storage |
|---|---|---|
| [Groq API](https://groq.com/) | LLM inference for AI Assistant (llama3-8b-8192) | Backend `.env` only — never exposed to browser |

## Frontend (planned — built in later phases)

| Library | Purpose |
|---|---|
| React + Vite | UI framework and build tool |
| Recharts | Interactive charts |
| Lucide React | Icon set |

---

*Last updated: Phase 1 scaffold*
