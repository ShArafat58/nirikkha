-- Crash-Test runs: status + per-node events for polling, final report, cache key.
create table if not exists crash_tests (
    id uuid primary key default gen_random_uuid(),
    cik text not null,
    as_of date not null,
    decision text not null default '',          -- stored AFTER PII redaction
    decision_hash text not null,
    status text not null check (status in ('queued', 'running', 'done', 'failed', 'blocked')),
    events jsonb not null default '[]'::jsonb,
    report jsonb,
    error text,
    source text not null default 'live',        -- live | precomputed
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists crash_tests_lookup on crash_tests (cik, as_of, decision_hash, status);
create index if not exists crash_tests_active on crash_tests (status, updated_at);
alter table crash_tests enable row level security;