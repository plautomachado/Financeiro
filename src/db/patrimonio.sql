-- ============================================================
-- RM Money — Patrimônio (Fase 2)
-- Rode UMA VEZ no SQL Editor do Supabase. Idempotente.
-- ============================================================

create table if not exists assets (
  id            uuid primary key default gen_random_uuid(),
  household_id  uuid not null references households(id) on delete cascade,
  name          text not null,
  type          text not null default 'available'
                check (type in ('available','reserve','house','investment','other')),
  country       text not null default 'BR' check (country in ('BR','JP','EU','US')),
  currency      text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  current_value numeric(14,2) not null default 0,
  member_id     uuid references family_members(id) on delete set null,
  note          text,
  is_active     boolean not null default true,
  updated_at    timestamptz not null default now(),
  created_at    timestamptz not null default now()
);

create table if not exists monthly_snapshots (
  id             uuid primary key default gen_random_uuid(),
  household_id   uuid not null references households(id) on delete cascade,
  year           int not null,
  month          int not null check (month between 1 and 12),
  net_worth_base numeric(14,2) not null default 0,
  br_base        numeric(14,2) not null default 0,
  jp_base        numeric(14,2) not null default 0,
  base_currency  text not null default 'BRL',
  created_at     timestamptz not null default now(),
  unique (household_id, year, month)
);

alter table assets enable row level security;
alter table monthly_snapshots enable row level security;
drop policy if exists assets_all on assets;
drop policy if exists snap_all on monthly_snapshots;
create policy assets_all on assets for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());
create policy snap_all on monthly_snapshots for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());

grant select, insert, update, delete on assets to authenticated;
grant select, insert, update, delete on monthly_snapshots to authenticated;
