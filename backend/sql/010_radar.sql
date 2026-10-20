-- Regulatory Change Radar: alerts and the human decisions on them (audit trail).
create table if not exists radar_alerts (
    id uuid primary key default gen_random_uuid(),
    key text not null unique,                 -- stable id from the engine, e.g. reg:sec-2023-cyber:0000320193
    stream text not null check (stream in ('regulatory', 'filing')),
    cik text not null,
    company text not null,
    title text not null,
    priority text not null check (priority in ('high', 'medium', 'low')),
    status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    payload jsonb not null,
    first_seen timestamptz not null default now(),
    last_seen timestamptz not null default now(),
    decided_at timestamptz,
    decided_by text,
    decided_by_email text,
    note text
);
create index if not exists radar_alerts_cik_idx on radar_alerts (cik);
create index if not exists radar_alerts_status_idx on radar_alerts (status);

create table if not exists radar_decisions (
    id bigserial primary key,
    alert_id uuid not null references radar_alerts (id) on delete cascade,
    decision text not null check (decision in ('approved', 'rejected')),
    note text,
    user_id text,
    user_email text,
    created_at timestamptz not null default now()
);
create index if not exists radar_decisions_alert_idx on radar_decisions (alert_id, created_at);

alter table radar_alerts enable row level security;
alter table radar_decisions enable row level security;