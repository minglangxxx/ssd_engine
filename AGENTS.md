# AGENTS.md

## Repo overview

Three independent services, no shared build system:

| Service | Tech | Entrypoint | Default port |
|---------|------|------------|-------------|
| backend | Flask 3.1 + SQLAlchemy + MySQL 8 | `backend/run.py` | 5000 |
| frontend | React 18 + Vite 5 + TypeScript + Ant Design 5 | `frontend/src/main.tsx` | 3000 |
| agent | Flask 3.1 + psutil (runs on target hosts) | `agent/agent_server.py` | 8080 |

Data flow: Frontend → `/api` proxy → Backend → HTTP → Agent → fio/nvme-cli/psutil.

## Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py                    # start server
python verify_integration.py     # integration smoke test (uses SQLite, no MySQL needed)
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # dev server on :3000, proxies /api → :5000
npm run build     # tsc -b && vite build → dist/
npm run preview   # preview production build
```

### Agent
```bash
cd agent
pip install -r requirements.txt
python agent_server.py
```

## What's missing (verify before assuming)

- **No linter, formatter, typecheck, or test runner** exists for any service. There is no `npm run lint`, `ruff`, `mypy`, `pytest`, `eslint`, or `prettier` config. Do not run commands that don't exist.
- **No CI workflows** (`.github/workflows/` is empty).
- **No pre-commit hooks**.
- The only automated verification is `backend/verify_integration.py` — it spins up a fake Agent HTTP server on port 18080, uses an in-memory SQLite DB, mocks OpenAI, and exercises device/task/trend/analysis/stop/retry flows end-to-end.

## Backend architecture

- **App factory**: `backend/app/__init__.py:create_app()` — loads Config, inits SQLAlchemy + Flask-Migrate, registers `/api` blueprint, runs `db.create_all()`, starts APScheduler.
- **Config**: `backend/app/config.py` loads from `.env` via `python-dotenv`. `DATABASE_URL` env var overrides individual `MYSQL_*` vars.
- **Blueprint registration**: `backend/app/api/__init__.py` — all route modules imported at bottom (`analysis, data, device, internal_ingest, monitor, nvme, task`).
- **Models**: one file per table in `backend/app/models/`. All must be imported in `__init__.py` for `db.create_all()` to see them.
- **Services**: business logic in `backend/app/services/`. Routes call services directly — no DI container.
- **Error handling**: raise `ApiError(code, message, status_code)` from anywhere; global handler converts to JSON. Use `success_response(data)` for normal returns.
- **Pagination**: `get_pagination_params()` reads `?page=&pageSize=` from query string (default 1/10, max 100).
- **Scheduler**: APScheduler runs at `Asia/Shanghai` timezone. Two jobs: daily 02:00 data lifecycle cleanup, periodic agent status check.
- **DB init**: run `backend/init_mysql.sql` in MySQL before first start. It uses stored procedures (`add_column_if_missing`, `add_index_if_missing`) for idempotent schema evolution — safe to re-run.

## Frontend architecture

- **Path alias**: `@/` maps to `frontend/src/` (configured in both `vite.config.ts` and `tsconfig.json`).
- **Request layer**: `src/utils/request.ts` — Axios instance with `baseURL: '/api'`, 30s timeout. Response interceptor unwraps `response.data` automatically. All API modules use this shared instance.
- **API modules**: `src/api/` — one file per domain (task, device, monitor, nvme, analysis, data). Functions return backend JSON directly (interceptor already unwrapped).
- **State**: Zustand stores in `src/stores/`.
- **Routing**: all pages under `AppLayout` in `src/App.tsx`. No lazy loading.
- **Locale**: Ant Design configured with `zhCN` locale.

## Agent architecture

- **Single-file Flask app**: `agent_server.py` registers all routes inline. No blueprints.
- **Background thread**: starts at import time (`threading.Thread(daemon=True).start()`). Collects CPU/memory/network/disk every 1s into a `MonitorRingBuffer` (deque, default 3600 entries). If `BACKEND_URL` is set, also enqueues data for batch HTTP upload.
- **SMART collection**: separate cycle (default 60s), uses `nvme-cli` via `smart_collector.py`.
- **FIO execution**: `executor/fio_runner.py` — spawns fio subprocess, parses JSON output, maintains task state.
- **Config**: `agent/config.py` reads from `agent/.env` first, then env vars. `AGENT_DEVICE_IP` must match the `ip` field in Backend's `devices` table for ingest to work.

## Key conventions

- **Language**: UI text, comments, READMEs, and error messages are in Chinese. Follow this convention.
- **No shared package manager**: each service has its own `requirements.txt` or `package.json`. No workspace root manifest.
- **Backend response format**: `success_response(data)` returns plain JSON; errors return `{"error": {"code": "...", "message": "..."}}`. Frontend error interceptor reads `error.response.data.error.message`.
- **IngestService concurrency**: uses optimistic locking with CAS (version field on `data_records`), max 5 retries. Don't assume simple inserts for concurrent writes.
- **Agent port per device**: Backend's `devices` table stores `agent_port` per device. Do not hardcode 8080.
- **AI analysis**: async — POST returns immediately with `analyzing` status, frontend polls GET. Prompts live in `backend/app/prompts/` (system_prompt.md + user_prompt_template.md).

## Startup order

1. MySQL (run `init_mysql.sql` if first time)
2. Backend (`python run.py`)
3. Agent (`python agent_server.py`) — optional, only needed for real device testing
4. Frontend (`npm run dev`) — optional, only for UI work

For backend-only work, steps 1-2 suffice. For frontend-only work, steps 2+4 suffice (Vite proxies to backend).

## Quick verification

```bash
cd backend && python verify_integration.py
```

Runs without MySQL or a real Agent. Exercises: device registration, agent status refresh, task create/get/list, trend fetch, AI analysis (mocked), stop, retry. Prints JSON summary on success, exits non-zero on failure.
