-- Actual user-confirmed meals. Plans never create these rows automatically.
create table if not exists public.meal_records (
  record_id text primary key,
  user_id text not null,
  version integer not null,
  status text not null check (status in ('active','deleted')),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists meal_records_user_idx on public.meal_records(user_id, updated_at desc);

create table if not exists public.meal_record_versions (
  record_id text not null,
  version integer not null,
  user_id text not null,
  operation_key text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key (record_id, version)
);
create index if not exists meal_record_versions_user_idx on public.meal_record_versions(user_id, created_at desc);

alter table public.meal_records enable row level security;
alter table public.meal_record_versions enable row level security;
do $$
declare t text;
begin
  foreach t in array array['meal_records','meal_record_versions'] loop
    execute format('drop policy if exists %I on public.%I', t || '_owner', t);
    execute format('create policy %I on public.%I for all to authenticated using (auth.uid()::text = user_id) with check (auth.uid()::text = user_id)', t || '_owner', t);
  end loop;
end $$;
