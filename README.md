# 7thGear

AI-powered desktop workflow automation. You give the agent a goal, it drafts a
high-level plan, you approve it, and it executes step by step — deciding the
next action after every tool result rather than blindly following a fixed
script. When reality doesn't match the plan (a duplicate record, a missing
match, an unexpected API response) the agent replans instead of failing or
corrupting data.

```
Goal -> Plan -> Approval -> Execute -> Observe -> Update State -> Decide Next Action -> Replan / Complete
```

The full project lives in [`Crox-AI-main/`](Crox-AI-main/) — see
[`Crox-AI-main/README.md`](Crox-AI-main/README.md) for architecture details,
prerequisites, and setup instructions.

## Structure

```
Crox-AI-main/
├── backend/     FastAPI + agent (planner/executor/replanner) + tool integrations
├── frontend/    Electron + React UI
└── supabase/    Database migrations
```

## Setup

Copy `Crox-AI-main/backend/.env.example` to `Crox-AI-main/backend/.env` and
fill in your own Gemini, Supabase, Google, and Slack credentials — `.env` is
gitignored and never committed.
