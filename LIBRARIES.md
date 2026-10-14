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
| **Model ID** | `openai/gpt-oss-120b` (default, set with `GROQ_MODEL`) | OpenAI's open-weight GPT-OSS 120B, listed as a production model on Groq's public model list (console.groq.com/docs/models). Any other Groq model that supports tool calling can be used by changing `GROQ_MODEL`. |
| **Model License** | Apache-2.0 (open weights) | Check OpenAI's gpt-oss license terms for your use. |
| **Why this setup** | Grounded, not free-form | The backend picks a whitelisted tool (`top_ghost_rooms`, `explain_room_alert`, `verified_savings`, `block_wastage`, `open_complaints`, `recommended_actions`), calculates every number itself, and the model only words the explanation. A number guard discards any answer containing a figure that is not in the tool output. |
| **Verification note** | Not tested with a live key in the audit | The audit environment had no Groq key or internet access to Groq, so the live call path was not exercised; the fallback path (no key / error) is covered by tests. Confirm your model id with `GET https://api.groq.com/openai/v1/models`. If the model id is wrong the assistant still answers using the template fallback and labels the answer `fallback`. |
| **Security & Key Isolation** | Zero Browser Exposure | `GROQ_API_KEY` is loaded strictly on the backend via environment variables and never exposed to the frontend or bundled into client assets. |
| **Offline Fallback** | Deterministic Rule Engine | If the Groq API key is absent, rate-limited, or timed out (> 8 s), the backend automatically falls back to deterministic template generation using the exact same whitelisted backend tools. |

---

## 3. Frontend Libraries (as installed in `frontend/package.json`)

| Library | Version | Purpose | License |
|---|---|---|---|
| [React](https://react.dev/) / react-dom | `^18.3.1` | Component-driven user interface | MIT |
| [React Router](https://reactrouter.com/) | `^6.28.0` | Client-side routing and role-based route guards | MIT |
| [Vite](https://vitejs.dev/) + [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | `^5.4.11` / `^4.3.4` | Build tool and dev server (proxies `/api` and `/uploads` to the backend) | MIT |
| [Recharts](https://recharts.org/) | `^2.15.0` | SVG charts for electricity series and baselines | MIT |
| [Lucide React](https://lucide.dev/) | `^0.468.0` | Icons | ISC |
| Google Fonts (Bricolage Grotesque, Figtree) | CDN | Typography (loaded by the browser from fonts.googleapis.com) | OFL |

Development / testing only: [vite-node](https://github.com/vitest-dev/vitest/tree/main/packages/vite-node) `^2.1.9` (runs `npm run check:api` and `npm run check:render`) and [jsdom](https://github.com/jsdom/jsdom) `^25.0.1` (headless DOM for the page-render check). Both are MIT licensed and are not part of the production bundle.

---

*Last updated: full backend + frontend integration audit.*
