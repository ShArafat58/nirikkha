-- Demo checkout: simulated subscriptions (no money, no card/account/PIN data is ever collected).
create table if not exists payment_simulations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users (id) on delete cascade,
    plan text not null check (plan in ('free', 'analyst_pro', 'team', 'enterprise')),
    method text not null check (method in ('mobile_banking', 'card', 'bank_transfer', 'none')),
    amount_usd numeric(10, 2) not null default 0,
    reference text not null unique,
    status text not null default 'succeeded' check (status in ('succeeded')),
    created_at timestamptz not null default now()
);
create index if not exists payment_simulations_user on payment_simulations (user_id, created_at);
alter table payment_simulations enable row level security;