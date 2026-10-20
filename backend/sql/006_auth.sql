-- Accounts, plan requests and per-user usage. Passwords and security answers are argon2id hashes only.
-- Date of birth is never stored: only the result of the 18+ check.
create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,                       -- lower-case
    name text not null,
    organization text,
    job_role text,
    password_hash text not null,
    security_question text not null,
    security_answer_hash text not null,
    role text not null default 'user' check (role in ('user', 'demo', 'admin')),
    plan text not null default 'free' check (plan in ('free', 'analyst_pro', 'team', 'enterprise')),
    adult_verified boolean not null default false,
    login_failures int not null default 0,
    login_locked_until timestamptz,
    reset_failures int not null default 0,
    reset_locked_until timestamptz,
    created_at timestamptz not null default now(),
    last_login_at timestamptz
);

create table if not exists plan_requests (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users (id) on delete cascade,
    plan text not null check (plan in ('free', 'analyst_pro', 'team', 'enterprise')),
    kind text not null check (kind in ('upgrade', 'pilot')),
    note text,
    status text not null default 'open' check (status in ('open', 'contacted', 'closed')),
    created_at timestamptz not null default now()
);

alter table crash_tests add column if not exists user_id uuid references users (id) on delete set null;
create index if not exists crash_tests_user on crash_tests (user_id, created_at);

alter table users enable row level security;
alter table plan_requests enable row level security;