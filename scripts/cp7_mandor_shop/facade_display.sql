-- Exact display projection only. Keep numeric cents inside PostgreSQL until
-- their final JSON strings; a browser must never round allocation amounts.
-- Existing private owners, permissions, locks and command bodies are unchanged.
create or replace function public.erp_cp7_get_mandor_shop_payroll_v1(p_payroll uuid,p_after uuid default null)
returns jsonb language sql stable security definer set search_path=''as $$
 with snapshot as materialized(
  select cp7_mandor_shop.workspace(p_payroll,p_after)as document
 )
 select jsonb_set(document,'{cards}',coalesce((
  select jsonb_agg(jsonb_set(card,'{allocations}',coalesce((
   select jsonb_agg(jsonb_set(assigned,'{allocation,amount}',
     to_jsonb(assigned#>>'{allocation,amount}'))order by allocation_order)
   from jsonb_array_elements(card->'allocations')with ordinality as allocation_rows(assigned,allocation_order)
  ),'[]'::jsonb))order by card_order)
  from jsonb_array_elements(document->'cards')with ordinality as cards(card,card_order)
 ),'[]'::jsonb))from snapshot
$$;
-- CREATE OR REPLACE preserves the already-reviewed owner and ACL. No new
-- role, grant, table, financial mutation or Native function is introduced.
