-- ============================================================
-- Cofre — Seed inicial (Fase 1)
-- Rode DEPOIS do schema.sql. Idempotente: só popula se ainda não houver família.
-- ============================================================

do $$
declare
  h uuid;
begin
  if exists (select 1 from households) then
    raise notice 'Já existe uma família cadastrada — seed ignorado.';
    return;
  end if;

  insert into households (name, base_currency) values ('Família', 'BRL') returning id into h;

  -- Membros
  insert into family_members (household_id, name, default_country, default_currency, color, sort_order) values
    (h, 'Plauto', 'JP', 'JPY', '#0E7C66', 1),
    (h, 'Esposa', 'BR', 'BRL', '#C2442E', 2),
    (h, 'Filho',  'BR', 'BRL', '#A9781F', 3);

  -- Categorias de despesa
  insert into categories (household_id, name, icon, kind, sort_order) values
    (h,'Moradia','🏠','expense',1),      (h,'Mercado','🛒','expense',2),
    (h,'Restaurantes','🍽️','expense',3), (h,'Transporte','🚌','expense',4),
    (h,'Saúde','🩺','expense',5),        (h,'Educação','📚','expense',6),
    (h,'Filho','🧒','expense',7),        (h,'Lazer','🎮','expense',8),
    (h,'Viagens','✈️','expense',9),      (h,'Compras','🛍️','expense',10),
    (h,'Roupas','👕','expense',11),      (h,'Assinaturas','📺','expense',12),
    (h,'Telefone','📱','expense',13),    (h,'Internet','🌐','expense',14),
    (h,'Energia','⚡','expense',15),     (h,'Água','💧','expense',16),
    (h,'Seguros','🛡️','expense',17),     (h,'Impostos','🧾','expense',18),
    (h,'Carro','🚗','expense',19),       (h,'Presentes','🎁','expense',20),
    (h,'Outros','•','expense',21);

  -- Categorias de receita
  insert into categories (household_id, name, icon, kind, sort_order) values
    (h,'Salário','💼','income',22),
    (h,'Renda extra','➕','income',23);

  -- Contas iniciais
  insert into accounts (household_id, name, type, country, currency) values
    (h,'Conta Brasil','checking','BR','BRL'),
    (h,'Carteira Japão','cash','JP','JPY'),
    (h,'Reserva','savings','BR','BRL');

  -- Taxa de câmbio inicial — AJUSTE os valores para a cotação real!
  insert into exchange_rates (household_id, from_currency, to_currency, rate) values
    (h,'BRL','JPY',26.0),
    (h,'JPY','BRL',0.0385);

  -- Metas iniciais (valores de exemplo — edite depois no app)
  insert into financial_goals (household_id, name, type, target_amount, currency, monthly_plan, config, priority) values
    (h,'Reserva de emergência','emergency', 60000, 'BRL', 2000,
       '{"months":6,"avg_monthly_expense":10000}'::jsonb, 1),
    (h,'Entrada da casa','house', 150000, 'BRL', 3000,
       '{"property_value":600000,"down_payment_pct":25}'::jsonb, 2);

  raise notice 'Seed concluído para a família %', h;
end $$;

-- ------------------------------------------------------------
-- Vincula o SEU login à família.
-- Rode isto DEPOIS de criar seu usuário em Authentication > Users
-- (pode rodar quantas vezes quiser; é idempotente). Ajuste o e-mail se preciso.
-- ------------------------------------------------------------
insert into profiles (id, household_id, display_name, role)
select u.id, (select id from households order by created_at limit 1), 'Plauto', 'owner'
from auth.users u
where u.email = 'SEU-EMAIL@exemplo.com'   -- troque pelo seu e-mail antes de rodar
on conflict (id) do update
  set household_id = excluded.household_id, role = excluded.role;
