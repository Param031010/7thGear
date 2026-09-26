# WorkFlowOS

AI-powered desktop workflow automation. You give the agent a goal in plain
language, it drafts a high-level plan with Gemini, you approve it, and it
executes step by step — deciding the next action after every tool result
instead of blindly walking a fixed script. When reality doesn't match the
plan (a duplicate record, a missing match, an unexpected API response) the
agent **replans** instead of failing or corrupting data.

```
Goal → Plan → Approval → Execute → Observe → Update State → Decide Next Action → Replan / Complete
```

Example: give it the goal *"Process today's internship applications and
notify the hiring team"* and it will search Gmail, read each application,
extract candidate info from the attached resume, check a tracker spreadsheet
for an existing record, insert or update accordingly, and post a summary to
Slack — asking for your approval before it starts, and pausing to ask you a
question if it hits something it can't resolve on its own.

## Project status

The full architecture works end-to-end today in **DEMO_MODE** (the default):
planner, executor, replanner, state manager, tool registry, WebSocket event
stream, Supabase persistence, and the Electron/React UI all run against local
fixtures for Gmail, Sheets, and Slack that behave *statefully* — a
"duplicate candidate" scenario genuinely triggers a replanning decision, not
a scripted animation.

Gmail, Google Sheets, Slack, the document tool (PyMuPDF resume parsing), and
the Playwright browser tool are all **real, live integrations**, not mocks —
see `backend/tools/gmail.py`, `sheets.py`, `slack.py`, `document.py`,
`browser.py`. Only Windows desktop automation via `pywinauto`
(`backend/tools/desktop.py`) is still a scaffold: it drives real OS windows
and is meant as a last-resort fallback, not something exercised by default.

## How the agent stays safe

Gemini never executes code or shell commands directly — on every turn it can
only select a tool name from a fixed registry and produce JSON arguments,
which are validated against that tool's Pydantic schema *before* anything
runs (`backend/tools/base.py`). If a step fails or produces an unexpected
result, the executor hands control to the replanner rather than pressing on
blindly, and workflows that touch real external systems require explicit
user approval before executing.

## Architecture

```
Electron + React (frontend/)
        │  HTTP + WebSocket
        ▼
     FastAPI (backend/)
        │
        ├── agent/          planner, executor, replanner, state, orchestrator, prompts
        ├── tools/           tool registry + gmail / sheets / slack / browser / desktop / document / user
        ├── repositories/    the only code that talks to Supabase directly
        └── api/             REST routes + WebSocket connection manager
        ▼
Supabase PostgreSQL (supabase/migrations/)
```

### Agent loop (`backend/agent/`)

| Module | Responsibility |
|---|---|
| `planner.py` | Turns a natural-language goal into an ordered list of step objectives via Gemini |
| `executor.py` | Picks the next tool call for the current step, validates arguments, invokes it |
| `observer.py` | Interprets a tool's result against the step's objective |
| `replanner.py` | Called when a step's outcome doesn't match expectations — revises the remaining plan instead of failing |
| `state.py` | Persists/reloads run state (facts, execution history) to Supabase so a run survives a backend restart |
| `orchestrator.py` | Drives the full plan → approve → execute → observe → replan loop and emits WebSocket events |

### Tools (`backend/tools/`)

Each tool is a registered, schema-validated capability the agent can invoke by name (`backend/tools/registry.py`):

| Tool | Real implementation | Demo/mock fallback |
|---|---|---|
| Gmail search / read / download attachment | `gmail.py` (Gmail API, OAuth2) | `mock/mock_gmail.py` (`backend/fixtures/gmail_inbox.json`) |
| Sheets search / insert / update | `sheets.py` (Google Sheets API) | `mock/mock_sheets.py` (`backend/fixtures/tracker_seed.json`) |
| Slack send | `slack.py` (`slack_sdk` Web API) | `mock/mock_slack.py` |
| Browser navigate / click / type / get text | `browser.py` (Playwright) | always real |
| Desktop open app / get window / click / type / hotkey | `desktop.py` (`pywinauto`) | scaffold — last-resort fallback, not exercised by default |
| Document extract text / fields | `document.py` (PyMuPDF, with an offline regex fallback) | always real |
| Ask user | `user.py` | surfaces a question to the human in the UI and pauses the run |

`DEMO_MODE=true` swaps Gmail/Sheets/Slack for their mock counterparts automatically in `registry.py` — no other code changes needed to go from demo to real.

### Frontend (`frontend/`)

An Electron desktop shell wrapping a React app with two routes: a `Landing`
page and the main `Chat` interface, where a goal you type becomes a plan
card you approve, followed by a live execution timeline (via WebSocket) and
floating widget panels showing agent state, tool calls, and status.

## Data model

`supabase/migrations/0001_init.sql` defines the schema — Supabase (via
`supabase-py`, REST API, not a direct Postgres connection) is the single
source of truth for every run:

| Table | Purpose |
|---|---|
| `workflows` | Saved workflow definitions: goal, generated plan (JSONB), status |
| `workflow_steps` | Ordered step objectives belonging to a workflow |
| `workflow_runs` | One row per execution of a goal: status, current step, timestamps |
| `execution_events` | Every tool call's input/output/status/error — the audit trail behind the live timeline |
| `agent_state` | The run's facts and execution history, reloaded on backend restart so runs survive a crash |
| `approvals` | Approval requests and the human's response, keyed to a run |

## Project structure

```
7thGear/
├── README.md                 you are here
└── Crox-AI-main/             the WorkFlowOS project
    ├── backend/
    │   ├── agent/             planner / executor / replanner / state / orchestrator
    │   ├── api/                REST routes + WebSocket manager
    │   ├── tools/               tool registry, real + mock implementations
    │   ├── repositories/        Supabase data access
    │   ├── integrations/        Google OAuth, Supabase storage
    │   ├── models/               Pydantic schemas
    │   ├── fixtures/             demo-mode sample data
    │   ├── tests/                pytest suite (34 tests)
    │   └── main.py                FastAPI app entrypoint
    ├── frontend/
    │   ├── src/                  React app (pages, components, services)
    │   └── electron/              Electron main/preload processes
    └── supabase/
        └── migrations/            SQL schema
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project (free tier is fine)
- A Gemini API key ([aistudio.google.com](https://aistudio.google.com/app/apikey))

## Installation

```bash
# Backend
cd Crox-AI-main/backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
playwright install chromium   # only needed for the browser tool

# Frontend
cd ../frontend
npm install
```

## Environment variables

Copy `Crox-AI-main/backend/.env.example` to `Crox-AI-main/backend/.env` and fill in:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-lite-latest

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_SHEETS_SPREADSHEET_ID=

SLACK_BOT_TOKEN=

DEMO_MODE=true

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

`SUPABASE_URL` is the **Project URL** from Project Settings → API
(`https://<project-ref>.supabase.co`) — not the Postgres connection string
from Database settings. The backend talks to Supabase entirely through
`supabase-py` (REST API via URL + service role key), so a database password
is never needed.

`.env` is gitignored — never commit it. The Electron renderer never sees
these values; only the FastAPI backend does.

### Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. Project Settings → API: copy the **Project URL** into `SUPABASE_URL` and
   the **service_role** key (not the anon key) into
   `SUPABASE_SERVICE_ROLE_KEY`.
3. Run `Crox-AI-main/supabase/migrations/0001_init.sql` via the SQL editor in
   the Supabase dashboard (or `supabase db push` with the CLI).
4. A **Storage** bucket named `resumes` is created automatically (public) the
   first time `gmail.download_attachment` runs in real mode.

### Gemini setup

Get a key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
and put it in `GEMINI_API_KEY`. Without it, planning/replanning calls return
a clear 503 instead of a raw error — the document tool still works via its
offline regex fallback.

### Google OAuth setup (real Gmail/Sheets — not required for DEMO_MODE)

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the
   **Gmail API** and **Google Sheets API**.
2. Configure the OAuth consent screen, add scopes `gmail.readonly` and
   `spreadsheets`, and add your Gmail account as a test user if the app is
   in Testing status.
3. Credentials → Create Credentials → OAuth client ID → **Desktop app**.
   Copy the Client ID/Secret into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.
4. Set `DEMO_MODE=false` and start the backend. The first Gmail/Sheets call
   opens a browser for one-time consent and caches the refresh token to
   `.token_cache/google_token.json` (gitignored).

The candidate tracker spreadsheet is created automatically on first use
(header row `record_id, name, email, phone, college, skills, status,
resume_url`); set `GOOGLE_SHEETS_SPREADSHEET_ID` to pin an existing sheet
instead.

### Slack setup (real Slack — not required for DEMO_MODE)

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps),
   add the **`chat:write`** bot token scope, and install it to your
   workspace.
2. Copy the **Bot User OAuth Token** (`xoxb-...`) into `SLACK_BOT_TOKEN`.
3. Invite the bot into whatever channel it should post to
   (`/invite @your-bot-name`) — `chat.postMessage` fails with
   `not_in_channel` otherwise.

## Running it

```bash
# Backend
cd Crox-AI-main/backend
.venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/health` — it should return
`{"status": "ok", "demo_mode": true}`.

```bash
# Frontend (Electron + Vite, hot reload)
cd Crox-AI-main/frontend
npm run electron:dev
```

Or run the pieces separately: `npm run dev` (Vite dev server) and, in
another terminal, `npm run electron` (points at the built `dist/`, so run
`npm run build` first for that path).

## Demo mode walkthrough

With `DEMO_MODE=true`, try the goal **"Process today's internship
applications"**. The fixture inbox (`backend/fixtures/gmail_inbox.json`) has
two sample applications, and the tracker (`backend/fixtures/tracker_seed.json`)
is pre-seeded with "Rahul Sharma" — so when the agent processes his
application it should find the existing record and choose to *update*
instead of *insert*, avoiding a duplicate. Watch this happen live in the
execution timeline, or see it asserted directly in
`backend/tests/test_replanning_duplicate_candidate.py`.

## Real API mode

Set `DEMO_MODE=false` once your Google OAuth credentials and
`SLACK_BOT_TOKEN` are in `.env` — the tool registry swaps every tool over to
its real implementation automatically. The one-time Google browser consent
flow needs a real desktop session, so run it locally rather than on a
headless server the first time.

## Testing

```bash
cd Crox-AI-main/backend
.venv\Scripts\activate
pytest -q
```

34 tests cover the tool registry and argument validation, mock tool
behavior, the document tool's PyMuPDF + regex-fallback extraction, state
persistence and restart recovery, the executor, the planner/replanner
against a mocked Gemini client, and the full orchestrator loop — including
the duplicate-candidate replanning scenario end-to-end.

```bash
cd Crox-AI-main/frontend
npm run build   # type-checks (tsc) and builds the renderer bundle
```

## Troubleshooting

- **503 "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set..."** — fill
  in `Crox-AI-main/backend/.env` and restart the backend.
- **503 "GEMINI_API_KEY is not set..."** — same, for planning/replanning
  calls.
- **Electron window doesn't load anything** — make sure the backend is
  running on `BACKEND_HOST:BACKEND_PORT` and that it matches
  `WORKFLOWOS_BACKEND_URL` (defaults to `http://127.0.0.1:8000`).
- **`playwright` errors about missing browser binaries** — run
  `playwright install chromium` inside the backend venv.

## Future scope

- Full accessibility-API-driven desktop automation (currently a scaffold)
- Computer-vision-based UI fallback for actions with no reliable API,
  accessibility, or browser path
- Broader connector library (CRM, ERP, additional email/chat platforms)
- Multi-user support and per-user workflow libraries
