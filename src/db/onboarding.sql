-- ============================================================
-- RM Money — Onboarding self-service ("Criar minha família")
-- Rode UMA VEZ no SQL Editor do Supabase.
-- Cria uma função que monta uma NOVA família isolada para o usuário logado
-- (household + profile + categorias + metas + 1 membro). Security definer para
-- poder criar tudo respeitando o isolamento (cada um só vê a sua família).
-- ============================================================

create or replace function public.create_household(
  family_name text,
  base_currency text default 'BRL',
  member_name text default 'Eu'
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  h uuid;
  uid uuid := auth.uid();
  cur text := coalesce(nullif(base_currency, ''), 'BRL');
  mname text := coalesce(nullif(member_name, ''), 'Eu');
begin
  if uid is null then
    raise exception 'Usuário não autenticado';
  end if;

  -- já tem família? devolve a existente (idempotente)
  select household_id into h from public.profiles where id = uid;
  if h is not null then
    return h;
  end if;

  insert into households (name, base_currency)
    values (coalesce(nullif(family_name, ''), 'Minha família'), cur)
    returning id into h;

  insert into profiles (id, household_id, display_name, role)
    values (uid, h, mname, 'owner')
    on conflict (id) do update set household_id = excluded.household_id, role = 'owner';

  insert into family_members (household_id, name, default_country, default_currency, sort_order)
    values (h, mname, 'BR', cur, 1);

  insert into categories (household_id, name, icon, kind, sort_order) values
    (h,'Moradia','🏠','expense',1),(h,'Mercado','🛒','expense',2),(h,'Restaurantes','🍽️','expense',3),
    (h,'Transporte','🚌','expense',4),(h,'Saúde','🩺','expense',5),(h,'Educação','📚','expense',6),
    (h,'Lazer','🎮','expense',7),(h,'Compras','🛍️','expense',8),(h,'Assinaturas','📺','expense',9),
    (h,'Telefone','📱','expense',10),(h,'Internet','🌐','expense',11),(h,'Energia','⚡','expense',12),
    (h,'Água','💧','expense',13),(h,'Carro','🚗','expense',14),(h,'Presentes','🎁','expense',15),
    (h,'Outros','•','expense',16);
  insert into categories (household_id, name, icon, kind, sort_order) values
    (h,'Salário','💼','income',20),(h,'Extras','➕','income',21);

  insert into financial_goals (household_id, name, type, target_amount, currency, monthly_plan, priority) values
    (h,'Reserva de emergência','emergency', 0, cur, 0, 1),
    (h,'Entrada da casa','house', 0, cur, 0, 2);

  return h;
end $$;

grant execute on function public.create_household(text, text, text) to authenticated;
