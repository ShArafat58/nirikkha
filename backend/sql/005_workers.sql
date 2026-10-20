-- Analysis workers (machines that run queued Crash-Tests) report a heartbeat here.
create table if not exists workers (
    worker_id text primary key,
    last_seen timestamptz not null default now(),
    current_job uuid,
    rerank_enabled boolean not null default true
);
alter table workers enable row level security;