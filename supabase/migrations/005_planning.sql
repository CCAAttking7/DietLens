-- DietLens meal plans, shopping lists, and inventory.
-- Apply after 0001_dietlens_core.sql (Supabase SQL Editor: New snippet).
create table if not exists public.plans (
  plan_id text primary key,
  user_id text not null,
  version integer not null,
  status text not null check (status in ('draft','confirmed','superseded','cancelled')),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists plans_user_idx on public.plans(user_id, updated_at desc);

create table if not exists public.shopping_lists (
  list_id text primary key,
  user_id text not null,
  plan_id text not null,
  plan_version integer not null,
  status text not null check (status in ('active','stale','cancelled')),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (plan_id, plan_version)
);
create index if not exists shopping_lists_user_idx on public.shopping_lists(user_id, updated_at desc);

create table if not exists public.inventory_items (
  inventory_id text primary key,
  user_id text not null,
  ingredient_id text not null,
  unit text not null,
  version integer not null default 1,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, ingredient_id, unit)
);
create index if not exists inventory_items_user_idx on public.inventory_items(user_id, updated_at desc);

alter table public.plans enable row level security;
alter table public.shopping_lists enable row level security;
alter table public.inventory_items enable row level security;

do $$
declare t text;
begin
  foreach t in array array['plans','shopping_lists','inventory_items'] loop
    execute format('drop policy if exists %I on public.%I', t || '_owner', t);
    execute format('create policy %I on public.%I for all to authenticated using (auth.uid()::text = user_id) with check (auth.uid()::text = user_id)', t || '_owner', t);
  end loop;
end $$;
