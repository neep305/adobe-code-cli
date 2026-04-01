# Adobe Experience Cloud CLI

**Unified CLI and Web UI for Adobe Experience Platform (AEP)** — schema design, data validation, batch ingestion, dataflow monitoring, and AI-assisted workflows.

| | |
|---|---|
| **Package** | `adobe-experience-cloud-cli` (PyPI name) |
| **Version** | 0.2.0 |
| **Python** | 3.10+ |
| **License** | MIT |

## What you get

- **`aep` CLI** — Typer-based commands for AEP APIs, schema tools, dataflows, destinations, LLM-assisted planning (`aep assistant`, `aep ai`, etc.).
- **Web UI** — FastAPI backend + Next.js 14 (App Router) frontend: auth, analyze, batches, dataflows, datasets, schemas, settings. Optional **standalone** mode serves the static UI from the same port as the API (no Docker/Node required at runtime after build).
- **Shared config** — AEP OAuth server-to-server credentials and AI provider keys via environment variables or `~/.adobe/credentials.json` (see `.env.example`).

## Quick start (CLI only)

```bash
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -e ".[dev]"
cp .env.example .env       # edit with AEP + AI keys
aep init                   # optional interactive setup
aep --help
```

Install with Web UI dependencies (SQLite standalone stack):

```bash
pip install -e ".[dev,web]"
```

## Web UI quick start

| Mode | When to use |
|------|-------------|
| **Standalone** | Single `python` process; API + prebuilt static UI on one port (default **8000**). Best for demos and local use. |
| **Dev** | Backend + `next dev` on **3000** for frontend hot reload. |
| **Docker** | PostgreSQL + Redis + services — see [`web/README.md`](web/README.md) and `web/docker-compose.yml`. |

**Standalone (typical local flow)**

```bash
pip install -e ".[dev,web]"
cp .env.example .env        # root: AEP + AI keys
cd web/frontend && npm install && npm run build && cd ../..
# from repo root, with WEB_MODE=standalone (see web/.env.example)
cd web/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or use the packaged helper if configured:

```bash
aep web start --mode standalone
```

Open **http://localhost:8000** — register/sign in, then use the dashboard.

**Auth API (current behavior)**

- `POST /api/auth/register` — JSON: `{ "login_id", "name", "password" }`. `login_id` is stored in the `users.email` column (plain ID; not required to be an e-mail address). Legacy clients may still send `email` / `username`; the server normalizes them.
- `POST /api/auth/login` — `application/x-www-form-urlencoded` with `username` (same ID) and `password`.

More detail: [`web/README.md`](web/README.md), [`web/backend/README.md`](web/backend/README.md), [`BUILD.md`](BUILD.md) (packaging and release build).

## Configuration

Copy [`.env.example`](.env.example) to `.env` at the repo root. Minimum for AEP + AI:

- `AEP_CLIENT_ID`, `AEP_CLIENT_SECRET`, `AEP_ORG_ID`, `AEP_TECHNICAL_ACCOUNT_ID`
- `AEP_SANDBOX_NAME`, `AEP_TENANT_ID` (for schema operations)
- `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` (see `AI_PROVIDER` / `AI_MODEL`)

Optional: **LangSmith** — `LANGSMITH_TRACING_V2`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (see [`docs/LANGSMITH_SETUP.md`](docs/LANGSMITH_SETUP.md)).

Web backend has its own settings in [`web/backend/app/config.py`](web/backend/app/config.py); use [`web/.env.example`](web/.env.example) when running under `web/`.

## Development

```bash
# Tests (package)
pytest

# Web auth API tests
pytest web/backend/tests/test_auth_api.py

# Format / lint (from dev extras)
black src tests
ruff check src tests
mypy src
```

## Documentation map

| Doc | Purpose |
|-----|---------|
| [`docs/README.md`](docs/README.md) | Index: install, Adobe setup, LLM mode |
| [`docs/install.md`](docs/install.md) | Environment and installation |
| [`docs/ADOBE_SETUP.md`](docs/ADOBE_SETUP.md) | Developer Console credentials |
| [`docs/LLM_MODE.md`](docs/LLM_MODE.md) | AI providers and agent behavior |
| [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) | Product vision, features, KPIs |
| [`BUILD.md`](BUILD.md) | Web UI static build and distribution |
| [`web/README.md`](web/README.md) | Web architecture, APIs, Docker |
| [`CLAUDE.md`](CLAUDE.md) | Contributor notes for AI-assisted coding |

## Repository layout (short)

```
├── src/adobe_experience/   # CLI, agents, AEP clients, i18n
├── tests/                    # Package tests
├── web/
│   ├── backend/              # FastAPI app
│   ├── frontend/             # Next.js (static export → out/)
│   └── docker-compose.yml
├── docs/                     # User and setup guides
└── examples/                 # Sample flows and data
```

## Links

- **Homepage / issues**: see [`pyproject.toml`](pyproject.toml) `[project.urls]`

---

*For deeper feature narrative and goals, see [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md).*
