-- ============================================================
-- RM Money — Despesas recorrentes (Fase 2)
-- Rode UMA VEZ no SQL Editor do Supabase (depois do schema.sql).
-- Seguro para rodar de novo (idempotente).
-- ============================================================

create table if not exists recurring_transactions (
  id           uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  member_id    uuid not null references family_members(id) on delete restrict,
  type         text not null default 'expense' check (type in ('expense','income')),
  description  text not null,
  amount       numeric(14,2) not null check (amount >= 0),
  currency     text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  country      text not null default 'BR' check (country in ('BR','JP','EU','US')),
  category_id  uuid references categories(id) on delete set null,
  account_id   uuid references accounts(id) on delete set null,
  periodicity  text not null default 'monthly' check (periodicity in ('monthly','yearly')),
  due_day      int check (due_day between 1 and 31),
  start_date   date not null default current_date,
  end_date     date,
  is_active    boolean not null default true,
  created_at   timestamptz not null default now()
);

-- liga cada lançamento gerado à sua recorrência (para saber o que já foi "pago")
alter table transactions add column if not exists recurring_id uuid references recurring_transactions(id) on delete set null;
create index if not exists idx_tx_hh_recurring on transactions (household_id, recurring_id);

-- Row Level Security
alter table recurring_transactions enable row level security;
drop policy if exists rec_all on recurring_transactions;
create policy rec_all on recurring_transactions for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());

grant select, insert, update, delete on recurring_transactions to authenticated;
