-- Human review decisions on Sentinel-flagged findings (audit trail: every decision is kept).
create table if not exists finding_reviews (
    id uuid primary key default gen_random_uuid(),
    crash_test_id uuid not null references crash_tests (id) on delete cascade,
    finding_id text not null,
    decision text not null check (decision in ('approve', 'reject')),
    note text,
    reviewer_id uuid references users (id) on delete set null,
    created_at timestamptz not null default now()
);
create index if not exists finding_reviews_lookup on finding_reviews (crash_test_id, finding_id, created_at);
alter table finding_reviews enable row level security;