-- Private mode flag on Crash-Test jobs.
alter table crash_tests add column if not exists private boolean not null default false;
