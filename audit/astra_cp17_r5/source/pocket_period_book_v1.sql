create or replace function erp.pocket_period_book_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' as $function$
 with sums as(
  select case when l.account_id=erp.account_id('WIP') and l.po_id is not null then 'WIP|'||l.po_id::text
   when l.account_id=erp.account_id('OTHER_EXPENSE') and l.po_id is null then 'OTHER_EXPENSE'
   when l.account_id=erp.account_id('OPENING_EQUITY') and l.po_id is null then 'OPENING_EQUITY'
   when l.account_id=erp.account_id('COGS') and l.po_id is null then 'COGS'
   else 'INVALID|'||l.account_id::text||'|'||coalesce(l.po_id::text,'') end key,sum(l.debit-l.credit) amount
  from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id
   join erp.journal_lines l on l.journal_entry_id=j.id where e.pool_id=p_pool group by 1
 ) select coalesce(jsonb_object_agg(key,amount) filter(where amount<>0),'{}'::jsonb) from sums;
$function$;
