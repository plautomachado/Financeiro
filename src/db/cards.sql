-- ============================================================
-- RM Money — Cartões & parcelamentos (Fase 2)
-- Rode UMA VEZ no SQL Editor do Supabase (depois do schema.sql).
-- Seguro para rodar de novo (idempotente).
-- ============================================================

create table if not exists credit_cards (
  id           uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  name         text not null,
  currency     text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  card_limit   numeric(14,2),
  closing_day  int check (closing_day between 1 and 31),
  due_day      int check (due_day between 1 and 31),
  member_id    uuid references family_members(id) on delete set null,
  is_active    boolean not null default true,
  created_at   timestamptz not null default now()
);

create table if not exists installments (
  id                 uuid primary key default gen_random_uuid(),
  household_id       uuid not null references households(id) on delete cascade,
  member_id          uuid not null references family_members(id) on delete restrict,
  description        text not null,
  total_amount       numeric(14,2) not null check (total_amount >= 0),
  currency           text not null default 'BRL' check (currency in ('BRL','JPY','EUR','USD')),
  country            text not null default 'BR' check (country in ('BR','JP','EU','US')),
  installments_count int not null check (installments_count >= 1),
  first_date         date not null default current_date,
  category_id        uuid references categories(id) on delete set null,
  credit_card_id     uuid references credit_cards(id) on delete set null,
  account_id         uuid references accounts(id) on delete set null,
  created_at         timestamptz not null default now()
);

-- ligações nas transações geradas
alter table transactions add column if not exists credit_card_id uuid references credit_cards(id) on delete set null;
alter table transactions add column if not exists installment_id uuid references installments(id) on delete cascade;
alter table transactions add column if not exists installment_no int;
create index if not exists idx_tx_hh_card on transactions (household_id, credit_card_id);
create index if not exists idx_tx_hh_installment on transactions (household_id, installment_id);

-- Row Level Security
alter table credit_cards enable row level security;
alter table installments enable row level security;
drop policy if exists card_all on credit_cards;
drop policy if exists inst_all on installments;
create policy card_all on credit_cards for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());
create policy inst_all on installments for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());

grant select, insert, update, delete on credit_cards to authenticated;
grant select, insert, update, delete on installments to authenticated;
