-- Only runs an admin features appear as public demos. New runs stay private by default.
alter table crash_tests add column if not exists featured boolean not null default false;
create index if not exists crash_tests_featured on crash_tests (featured, status, updated_at);