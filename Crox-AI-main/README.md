# WorkFlowOS

AI-powered desktop workflow automation. You give the agent a goal, Gemini drafts a
high-level plan, you approve it, and the agent executes it -- deciding the next action
after every tool result rather than blindly walking a fixed script. When reality
doesn't match the plan (a duplicate record, a missing match, an unexpected API
response) the agent replans instead of failing or corrupting data.

```
Goal -> Plan -> Approval -> Execute -> Observe -> Update State -> Decide Next Action -> Replan / Complete
```

## Project status

This build implements the full architecture end-to-end. Planner, executor,
replanner, state manager, tool registry, WebSocket event stream, Supabase
persistence, and the Electron UI (Dashboard / Workflows / Workflow Details /
Execution Details / Settings) all work in **DEMO_MODE**, where Gmail, Google
Sheets, and Slack run against local fixtures/mocks that behave statefully (a
"duplicate candidate" scenario genuinely triggers a replanning decision).

Gmail, Google Sheets, Slack, the document tool (PyMuPDF resume parsing), and the
Playwright browser tool are all real, live integrations, not mocked -- see
`backend/tools/gmail.py`, `sheets.py`, `slack.py`, `document.py`, `browser.py`.
Only Windows desktop automation via pywinauto (`backend/tools/desktop.py`) is
still a scaffold, since it drives real OS windows and is meant as a last-resort
fallback per the spec, not something to exercise by default.

## Architecture

```
Electron + React (frontend/)
       |  HTTP + WebSocket
       v
FastAPI (backend/)
       |
       +-- agent/        planner, executor, replanner, state, orchestrator, prompts
       +-- tools/         tool registry + gmail/sheets/slack/browser/desktop/document/user
       +-- repositories/  the only code that talks to Supabase directly
       +-- api/           REST routes + WebSocket connection manager
       v
Supabase PostgreSQL (supabase/migrations/)
```

Gemini never executes code or shell commands -- it only ever selects a registered
tool name and produces JSON arguments, which are validated against that tool's
Pydantic schema before anything runs (`backend/tools/base.py`).

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project (free tier is fine)
- A Gemini API key ([aistudio.google.com](https://aistudio.google.com/app/apikey))

## Installation

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
playwright install chromium   # only needed for the browser tool

# Frontend
cd ../frontend
npm install
```

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
GEMINI_API_KEY=

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

SLACK_BOT_TOKEN=

DEMO_MODE=true

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

`SUPABASE_URL` is the **Project URL** from Project Settings -> API
(`https://<project-ref>.supabase.co`) -- not the Postgres connection string from
Database settings. This app talks to Supabase entirely through `supabase-py`
(the REST API via URL + service role key), never a direct Postgres connection, so
the DB password isn't needed anywhere.

Never commit `.env` -- it's gitignored. The Electron renderer never sees these
values; only the FastAPI backend does.

## Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. Project Settings -> API: copy the **Project URL** into `SUPABASE_URL` and the
   **service_role** key (not the anon key) into `SUPABASE_SERVICE_ROLE_KEY`.
3. Run the migration in `supabase/migrations/0001_init.sql` via the SQL editor in
   the Supabase dashboard (or `supabase db push` if you use the CLI). It creates:
   `workflows`, `workflow_steps`, `workflow_runs`, `execution_events`, `agent_state`,
   `approvals`.
4. A **Storage** bucket named `resumes` is created automatically (public) the first
   time `gmail.download_attachment` runs in real mode -- resume PDFs are uploaded
   there and their public URL is what gets stored in the tracker sheet's
   `resume_url` column, not a local file path.

Supabase is the source of truth for every run -- a run can be resumed after a
backend restart because its `agent_state` row is reloaded from there
(`AgentStateManager.load`, see `backend/tests/test_state.py` for a test of this).

## Gemini setup

Get a key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
and put it in `GEMINI_API_KEY`. Without it, planning/replanning calls return a clear
503 (`GeminiNotConfigured`) instead of a raw error -- the document tool still works
via its offline regex fallback. Uses the current `google-genai` SDK (the older
`google-generativeai` package is fully end-of-life and isn't used here).

## Google OAuth setup (for real Gmail/Sheets -- not required for DEMO_MODE)

Implemented in `backend/integrations/google_oauth.py` / `backend/tools/gmail.py` /
`backend/tools/sheets.py`. One-time setup:

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the
   **Gmail API** and **Google Sheets API** for your project.
2. Configure the OAuth consent screen (External or Internal), add scopes
   `gmail.readonly` and `spreadsheets`, and add your Gmail account as a test user
   if the app is in Testing status.
3. Credentials -> Create Credentials -> OAuth client ID -> **Desktop app** type.
   Copy the Client ID/Secret into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.
4. Set `DEMO_MODE=false` and start the backend. The first time a Gmail/Sheets tool
   runs, `run_local_server()` opens your browser for a one-time consent screen and
   caches the resulting refresh token to `.token_cache/google_token.json`
   (gitignored) -- subsequent runs reuse it silently.

The candidate tracker spreadsheet is created automatically on first use (title
"WorkFlowOS Candidate Tracker", header row `record_id, name, email, phone, college,
skills, status, resume_url`) and its id is cached to
`.token_cache/sheets_spreadsheet_id.txt`. Set `GOOGLE_SHEETS_SPREADSHEET_ID` in
`.env` instead if you want to pin an existing sheet.

## Slack setup (for real Slack -- not required for DEMO_MODE)

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps) (from
   scratch), add the **`chat:write`** bot token scope under OAuth & Permissions,
   and install the app to your workspace.
2. Copy the **Bot User OAuth Token** (starts with `xoxb-`) into `SLACK_BOT_TOKEN`.
3. Invite the bot into whatever channel it should post to, e.g.
   `/invite @your-bot-name` in that channel -- `chat.postMessage` fails with
   `not_in_channel` otherwise.

`backend/tools/slack.py` uses `slack_sdk`'s async Web API client.

## Running the backend

```bash
cd backend
.venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/health` -- it should return
`{"status": "ok", "demo_mode": true}`. If Supabase isn't configured yet, every
Supabase-backed endpoint returns a clean `503` explaining what's missing rather than
crashing.

## Running the frontend

```bash
cd frontend
npm run electron:dev   # starts Vite + Electron together, with hot reload
```

Or run the pieces separately: `npm run dev` (Vite dev server) and, in another
terminal, `npm run electron` (points at the built `dist/`, so run `npm run build`
first for that path).

## Demo mode

With `DEMO_MODE=true` (the default), `gmail.*` and `sheets.*` and `slack.*` resolve
to `backend/tools/mock/*`, backed by fixtures in `backend/fixtures/`:

- `gmail_inbox.json` -- two sample internship application emails
- `tracker_seed.json` -- a candidate tracker pre-seeded with "Rahul Sharma"
- `resumes/*.txt` -- resume text for both applicants

Try the goal **"Process today's internship applications"** from the Workflows page.
Rahul Sharma's application already exists in the tracker, so the agent should search,
find the existing record, and choose `ALTERNATIVE_ACTION` (update instead of insert)
rather than creating a duplicate -- watch this happen live in Execution Details, or
see it asserted directly in
`backend/tests/test_replanning_duplicate_candidate.py`.

## Real API mode

Gmail, Sheets, and Slack are all implemented for real (see above). Set
`DEMO_MODE=false` once your Google OAuth credentials and `SLACK_BOT_TOKEN` are in
`.env`; the registry (`backend/tools/registry.py`) swaps every tool over
automatically, no other code changes needed. The one-time Google browser consent
flow needs a real desktop session (it opens a browser window), so run this on
your machine rather than a headless server the first time.

## Testing

```bash
cd backend
.venv\Scripts\activate
pytest -q
```

34 tests cover: tool registry + argument validation, mock tool behavior, the
document tool's PyMuPDF + regex-fallback extraction, state persistence and restart
recovery, the executor, the planner and replanner against a mocked Gemini client,
and the full orchestrator loop -- including the duplicate-candidate replanning
scenario end-to-end with real mock tools.

```bash
cd frontend
npm run build   # type-checks (tsc) and builds the renderer bundle
```

## Troubleshooting

- **503 "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set..."** -- fill in
  `backend/.env` and restart the backend.
- **503 "GEMINI_API_KEY is not set..."** -- same, for planning/replanning calls.
- **Electron window doesn't load anything** -- make sure the backend is running on
  `BACKEND_HOST:BACKEND_PORT` and matches `WORKFLOWOS_BACKEND_URL` (defaults to
  `http://127.0.0.1:8000`, set via env var before launching Electron if you changed
  the backend port).
- **`playwright` errors about missing browser binaries** -- run
  `playwright install chromium` inside the backend venv.
