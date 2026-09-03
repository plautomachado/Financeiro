-- ============================================================
-- Orçamento por PAÍS (Brasil × Japão × ...), cada um na sua moeda.
-- Permite a MESMA categoria orçada em países diferentes (ex.: Mercado
-- no Brasil em R$ e Mercado no Japão em ¥).
-- Rode uma vez no Supabase (SQL Editor).
-- ============================================================

-- 1) coluna de país no orçamento
alter table monthly_budgets
  add column if not exists country text not null default 'BR'
  check (country in ('BR','JP','EU','US'));

-- 2) a unicidade passa a incluir o país (categoria pode repetir em países diferentes)
alter table monthly_budgets
  drop constraint if exists monthly_budgets_household_id_year_month_category_id_key;

alter table monthly_budgets
  drop constraint if exists monthly_budgets_uq;

alter table monthly_budgets
  add constraint monthly_budgets_uq
  unique (household_id, year, month, category_id, country);
