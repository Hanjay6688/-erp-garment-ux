CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_book_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('COGS')),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where l.po_id is null and l.product_id=p_product_id
    and (e.source_type<>'PRODUCT_CONVERSION' or erp.be_nonpo_admitted_v1(e.source_id))
    and (e.source_type<>'JOURNAL_REVERSAL' or o.source_type is distinct from 'PRODUCT_CONVERSION'
      or erp.be_nonpo_admitted_v1(o.source_id))
)
select (fg+cogs+other_out)::numeric,fg,cogs,other_out from book
$function$;
