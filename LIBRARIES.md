# LIBRARIES.md — GhostWatt External Dependencies & Model Inventory

> Complete inventory of backend libraries, external APIs, and AI models utilized in GhostWatt.
> All libraries are vetted for open-source licenses (MIT, Apache-2.0, BSD) suitable for academic, hackathon, and production deployment.

---

## 1. Backend Core Libraries

| Library | Version Installed | Purpose | License |
|---|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | `0.143.0` | High-performance asynchronous HTTP API framework, OpenAPI generation, routing, and dependency injection | MIT |
| [Starlette](https://www.starlette.io/) | `1.7.0` | ASGI toolkit beneath FastAPI powering requests, responses, status codes, and test client | BSD-3-Clause |
| [Uvicorn](https://www.uvicorn.org/) | `0.54.0` | Lightning-fast ASGI production web server with standard event loop and HTTP protocol implementations | BSD-3-Clause |
| [SQLAlchemy](https://www.sqlalchemy.org/) | `2.1.4` | Enterprise Object Relational Mapper (ORM), SQL schema modeling, and SQLite engine integration | MIT |
| [Pydantic](https://docs.pydantic.dev/) | `2.14.1` | Robust runtime data validation, schema enforcement, and serialization | MIT |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | `2.15.0` | Type-safe application configuration loader from `.env` and environment variables | MIT |
| [python-jose](https://github.com/mpdavis/python-jose) | `3.5.0` | Cryptographic JWT signing and decoding (HMAC-SHA256) for stateless authentication | MIT |
| [cryptography](https://cryptography.io/) | `50.0.2` | Core cryptographic primitives and backend engine for token and security workflows | Apache-2.0 / BSD |
| [passlib](https://passlib.readthedocs.io/) | `1.7.4` | Password hashing framework providing salt generation and verification abstraction | BSD |
| [bcrypt](https://github.com/pyca/bcrypt/) | `5.0.0` | Modern, secure password hashing function with adaptive work factor | Apache-2.0 |
| [pandas](https://pandas.pydata.org/) | `3.0.6` | Tabular data analysis, time-series resampling, and sustainability summary aggregations | BSD-3-Clause |
| [numpy](https://numpy.org/) | `2.5.4` | High-efficiency vectorized numerical mathematics, baseline deviation models, and array operations | BSD-3-Clause |
| [httpx](https://www.python-httpx.org/) | `0.28.1` | Next-generation asynchronous HTTP client for unit testing and outbound AI requests | BSD-3-Clause |
| [python-multipart](https://andrew-d.github.io/python-multipart/) | `0.0.32` | Multipart form data and file streaming parser for facility complaint photo uploads | Apache-2.0 |
| [groq](https://github.com/groq/groq-python) | `1.7.0` | Official Python SDK for Groq Cloud API, handling ultra-fast LPU inference and native tool calling | Apache-2.0 |
| [pytest](https://pytest.org/) | `9.1.1` | Unit, integration, permission, and simulation testing framework | MIT |

---

## 2. External AI Inference API & Chosen Model

| Component | Specification | Details |
|---|---|---|
| **API Provider** | [Groq Cloud](https://groq.com/) | Hardware-accelerated Language Processing Unit (LPU) cloud inference engine delivering ultra-low token latency (< 500 ms round trip). |
| **Model ID** | `qwen/qwen3.8-27b` | **Qwen 3.8 27B Parameter Model** on Groq Cloud. |
| **Model License** | Apache-2.0 / Open Weights | Permissive open-weights license permitting commercial, academic, and hackathon applications. |
| **Rationale & Selection** | Why `qwen/qwen3.8-27b`? | 1. **Reliable Tool Calling:** Consistently selects the exact appropriate tool function (`top_ghost_rooms`, `explain_room_alert`, `verified_savings`, `block_wastage`, `open_complaints`, `recommended_actions`) without formatting hallucinations.<br>2. **Extreme Speed on Groq LPU:** Delivers 500+ tokens/second, enabling real-time conversational responses during live campus facility walkthroughs.<br>3. **High Reasoning Fidelity:** Exceptional instruction following for numerical synthesis, enabling the model to faithfully summarize tool metrics without inventing figures.<br>4. **Number Guard Compliance:** Synthesizes clear explanations using strictly the values provided by the backend functions. |
| **Security & Key Isolation** | Zero Browser Exposure | `GROQ_API_KEY` is loaded strictly on the backend via environment variables and never exposed to the frontend or bundled into client assets. |
| **Offline Fallback** | Deterministic Rule Engine | If the Groq API key is absent, rate-limited, or timed out (> 8 s), the backend automatically falls back to deterministic template generation using the exact same whitelisted backend tools. |

---

## 3. Frontend Technology (Planned Stack)

| Library | Version / Channel | Purpose | License |
|---|---|---|---|
| [React](https://react.dev/) | 18+ | Component-driven user interface architecture | MIT |
| [Vite](https://vitejs.dev/) | Latest | Next-generation frontend build tooling and rapid HMR development server | MIT |
| [Recharts](https://recharts.org/) | Latest | Declarative SVG charting library for electricity series and baseline comparison curves | MIT |
| [Lucide React](https://lucide.dev/) | Latest | Clean, lightweight icon suite for energy, water, alerts, and navigation | ISC |

---

*Last updated: Backend Complete & Production-Verified*
