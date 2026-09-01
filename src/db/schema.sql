-- ============================================================
-- Cofre — Schema do MVP (Fase 1)
-- Rode este arquivo no SQL Editor do Supabase (uma vez).
-- Cria as tabelas do núcleo + Row Level Security (isolamento por família).
-- Seguro para rodar de novo (idempotente).
-- ============================================================

create extension if not exists pgcrypto;

-- ---------- Households & perfis (acesso) ----------
create table if not exists households (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  base_currency text not null default 'BRL' check (base_currency in ('BRL','JPY','EUR','USD')),
  created_at    timestamptz not null default now()
);

create table if not exists profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  household_id uuid not null references households(id) on delete cascade,
  display_name text,
  role         text not null default 'member' check (role in ('owner','member')),
  created_at   timestamptz not null default now()
);

-- Helper: household do usuário logado (security definer p/ evitar recursão de RLS)
create or replace function public.current_household_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select household_id from public.profiles where id = auth.uid()
$$;

-- ---------- Membros da família ----------
create table if not exists family_members (
  id               uuid primary key default gen_random_uuid(),
  household_id     uuid not null references households(id) on delete cascade,
  name             text not null,
  default_country  text not null default 'BR' check (default_country in ('BR','JP','EU','US')),
  default_currency text not null default 'BRL' check (default_currency in ('BRL','JPY','EUR','USD')),
  color            text,
  is_active        boolean not null default true,
  sort_order       int not null default 0,
  created_at       timestamptz not null default now()
);

-- ---------- Categorias e subcategorias ----------
create table if not exists categories (
  id           uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  name         text not null,
  icon         text,
  kind         text not null default 'expense' check (kind in ('expense','income','both')),
  is_active    boolean not null default true,
  sort_order   int not null default 0,
  created_at   timestamptz not null default now()
);

create table if not exists subcategories (
  id           uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  category_id  uuid not null references categories(id) on delete cascade,
  name         text not null,
  is_active    boolean not null default true,
  created_at   timestamptz not null default now()
);

-- ---------- Contas ----------
create table if not exists accounts (
  id              uuid primary key default gen_random_uuid(),
  household_id    uuid not null references households(id) on delete cascade,
  name            text not null,
  type            text not null default 'checking' check (type in ('checking','savings','cash','investment')),
  country         text not null default 'BR' check (country in ('BR','JP','EU','US')),
  currency        text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  initial_balance numeric(14,2) not null default 0,
  member_id       uuid references family_members(id) on delete set null,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now()
);

-- ---------- Taxas de câmbio (histórico de referência) ----------
-- rate: valor_to = valor_from * rate   (ex.: from=BRL, to=JPY, rate=26 -> 1 R$ = 26 ¥)
create table if not exists exchange_rates (
  id            uuid primary key default gen_random_uuid(),
  household_id  uuid not null references households(id) on delete cascade,
  from_currency text not null check (from_currency in ('BRL','JPY','EUR','USD')),
  to_currency   text not null check (to_currency in ('BRL','JPY','EUR','USD')),
  rate          numeric(18,8) not null check (rate > 0),
  rate_date     date not null default current_date,
  source        text not null default 'manual',
  created_at    timestamptz not null default now(),
  unique (household_id, from_currency, to_currency, rate_date)
);

-- ---------- Metas ----------
create table if not exists financial_goals (
  id            uuid primary key default gen_random_uuid(),
  household_id  uuid not null references households(id) on delete cascade,
  name          text not null,
  type          text not null default 'custom' check (type in ('emergency','house','investment','custom')),
  target_amount numeric(14,2),
  currency      text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  start_date    date not null default current_date,
  target_date   date,
  monthly_plan  numeric(14,2),
  config        jsonb not null default '{}'::jsonb,   -- casa: {property_value, down_payment_pct}; reserva: {months, avg_monthly_expense}
  priority      int not null default 0,
  is_active     boolean not null default true,
  created_at    timestamptz not null default now()
);

-- ---------- Transações (núcleo) ----------
-- amount_base é DERIVADO (coluna gerada): nunca duplicamos o valor original.
create table if not exists transactions (
  id                uuid primary key default gen_random_uuid(),
  household_id      uuid not null references households(id) on delete cascade,
  member_id         uuid not null references family_members(id) on delete restrict,
  type              text not null check (type in ('expense','income','transfer','contribution')),
  amount_original   numeric(14,2) not null check (amount_original >= 0),
  currency_original text not null check (currency_original in ('BRL','JPY','EUR','USD')),
  country           text not null check (country in ('BR','JP','EU','US')),
  exchange_rate     numeric(18,8) not null default 1 check (exchange_rate > 0),  -- original -> base
  base_currency     text not null check (base_currency in ('BRL','JPY','EUR','USD')),
  amount_base       numeric(14,2) generated always as (round(amount_original * exchange_rate, 2)) stored,
  category_id       uuid references categories(id) on delete set null,
  subcategory_id    uuid references subcategories(id) on delete set null,
  account_id        uuid references accounts(id) on delete set null,
  goal_id           uuid references financial_goals(id) on delete set null,  -- para aportes
  description        text,
  note              text,
  occurred_on       date not null default current_date,
  created_by        uuid references auth.users(id) on delete set null,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists idx_tx_hh_date   on transactions (household_id, occurred_on);
create index if not exists idx_tx_hh_member on transactions (household_id, member_id);
create index if not exists idx_tx_hh_cat    on transactions (household_id, category_id);
create index if not exists idx_tx_hh_type   on transactions (household_id, type);
create index if not exists idx_tx_hh_goal   on transactions (household_id, goal_id);

-- ---------- Orçamento mensal ----------
create table if not exists monthly_budgets (
  id             uuid primary key default gen_random_uuid(),
  household_id   uuid not null references households(id) on delete cascade,
  year           int not null,
  month          int not null check (month between 1 and 12),
  category_id    uuid not null references categories(id) on delete cascade,
  planned_amount numeric(14,2) not null default 0,
  currency       text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  created_at     timestamptz not null default now(),
  unique (household_id, year, month, category_id)
);

-- ---------- View: aportes por meta (sem duplicar dados; herda o RLS de transactions) ----------
create or replace view goal_contributions
with (security_invoker = on) as
  select id as transaction_id, household_id, goal_id, member_id,
         amount_original, currency_original, amount_base,
         occurred_on as contributed_on, note
  from transactions
  where type = 'contribution' and goal_id is not null;

-- ---------- updated_at automático ----------
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists trg_tx_updated on transactions;
create trigger trg_tx_updated before update on transactions
  for each row execute function public.set_updated_at();

-- ============================================================
-- Row Level Security — cada família só enxerga os próprios dados
-- ============================================================
alter table households      enable row level security;
alter table profiles        enable row level security;
alter table family_members  enable row level security;
alter table categories      enable row level security;
alter table subcategories   enable row level security;
alter table accounts        enable row level security;
alter table exchange_rates  enable row level security;
alter table financial_goals enable row level security;
alter table transactions    enable row level security;
alter table monthly_budgets enable row level security;

-- profiles: cada um enxerga/edita o próprio
drop policy if exists profiles_self_select on profiles;
drop policy if exists profiles_self_insert on profiles;
drop policy if exists profiles_self_update on profiles;
create policy profiles_self_select on profiles for select to authenticated using (id = auth.uid());
create policy profiles_self_insert on profiles for insert to authenticated with check (id = auth.uid());
create policy profiles_self_update on profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- households: por associação
drop policy if exists households_select on households;
drop policy if exists households_update on households;
create policy households_select on households for select to authenticated using (id = public.current_household_id());
create policy households_update on households for update to authenticated using (id = public.current_household_id()) with check (id = public.current_household_id());

-- demais tabelas: filtro pelo household do usuário
drop policy if exists fm_all   on family_members;
drop policy if exists cat_all  on categories;
drop policy if exists sub_all  on subcategories;
drop policy if exists acc_all  on accounts;
drop policy if exists fx_all   on exchange_rates;
drop policy if exists goal_all on financial_goals;
drop policy if exists tx_all   on transactions;
drop policy if exists bud_all  on monthly_budgets;
create policy fm_all   on family_members  for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy cat_all  on categories      for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy sub_all  on subcategories   for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy acc_all  on accounts        for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy fx_all   on exchange_rates  for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy goal_all on financial_goals for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy tx_all   on transactions    for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());
create policy bud_all  on monthly_budgets for all to authenticated using (household_id = public.current_household_id()) with check (household_id = public.current_household_id());

-- Grants (o RLS continua sendo o filtro real linha a linha)
grant usage on schema public to authenticated;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant select on goal_contributions to authenticated;
