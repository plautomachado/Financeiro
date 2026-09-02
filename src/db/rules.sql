-- ============================================================
-- RM Money — Regras de categorização (Fase 3)
-- Rode UMA VEZ no SQL Editor do Supabase. Idempotente.
-- ============================================================

create table if not exists categorization_rules (
  id           uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  match_text   text not null,                                   -- se a descrição CONTÉM este texto...
  category_id  uuid references categories(id) on delete cascade, -- ...usa esta categoria
  member_id    uuid references family_members(id) on delete set null,
  priority     int not null default 0,
  is_active    boolean not null default true,
  created_at   timestamptz not null default now()
);

alter table categorization_rules enable row level security;
drop policy if exists rules_all on categorization_rules;
create policy rules_all on categorization_rules for all to authenticated
  using (household_id = public.current_household_id())
  with check (household_id = public.current_household_id());

grant select, insert, update, delete on categorization_rules to authenticated;
