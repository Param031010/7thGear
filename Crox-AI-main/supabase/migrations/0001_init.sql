-- WorkFlowOS initial schema
-- Source of truth for workflow definitions, runs, execution events, agent state, and approvals.

create extension if not exists pgcrypto;

create table if not exists workflows (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    goal text not null,
    plan jsonb not null,
    status text not null default 'draft',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists workflow_steps (
    id uuid primary key default gen_random_uuid(),
    workflow_id uuid references workflows(id) on delete cascade,
    step_order integer,
    objective text not null,
    status text default 'pending',
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

create table if not exists workflow_runs (
    id uuid primary key default gen_random_uuid(),
    workflow_id uuid references workflows(id) on delete set null,
    goal text not null,
    status text not null default 'pending',
    current_step text,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz default now()
);

create table if not exists execution_events (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references workflow_runs(id) on delete cascade,
    event_type text not null,
    tool_name text,
    input jsonb,
    output jsonb,
    status text,
    error text,
    created_at timestamptz default now()
);

create table if not exists agent_state (
    id uuid primary key default gen_random_uuid(),
    run_id uuid unique references workflow_runs(id) on delete cascade,
    state jsonb not null default '{}'::jsonb,
    facts jsonb not null default '{}'::jsonb,
    execution_history jsonb not null default '[]'::jsonb,
    updated_at timestamptz default now()
);

create table if not exists approvals (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references workflow_runs(id) on delete cascade,
    approval_type text not null,
    status text not null default 'pending',
    response jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_workflow_runs_workflow_id on workflow_runs(workflow_id);
create index if not exists idx_execution_events_run_id on execution_events(run_id);
create index if not exists idx_agent_state_run_id on agent_state(run_id);
create index if not exists idx_approvals_run_id on approvals(run_id);
