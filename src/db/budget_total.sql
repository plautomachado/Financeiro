-- ============================================================
-- Teto do mês (orçamento TOTAL, sem dividir por categoria).
-- É uma linha de monthly_budgets com category_id NULL, por país.
-- Rode uma vez no Supabase (SQL Editor).
-- ============================================================

-- permite orçamento sem categoria (o teto do mês)
alter table monthly_budgets alter column category_id drop not null;

-- no máximo 1 teto por (família, ano, mês, país)
create unique index if not exists monthly_budgets_total_uq
  on monthly_budgets (household_id, year, month, country)
  where category_id is null;
