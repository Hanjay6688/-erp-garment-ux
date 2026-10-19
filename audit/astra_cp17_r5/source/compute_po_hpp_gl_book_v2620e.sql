CREATE OR REPLACE FUNCTION erp.compute_po_hpp_gl_book_v2620e(p_po_id uuid)
 RETURNS TABLE(fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with lifecycle as(
  select e.id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  )
), historical_untagged as(
  select l.id
  from lifecycle l
  where not exists(
    select 1 from erp.journal_lines x
    where x.journal_entry_id=l.id
      and x.account_id in(
        erp.account_id('FG_INVENTORY'),erp.account_id('COGS'),
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      ) and x.po_id is not null
  ) and exists(
    select 1
    from erp.journal_entries e
    left join erp.journal_entries o on o.id=e.reversal_of_id
    where e.id=l.id and(
      (coalesce(o.source_type,e.source_type)='SALE' and exists(
        select 1 from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      )) or
      (coalesce(o.source_type,e.source_type)='SALES_RETURN' and exists(
        select 1 from erp.sales_return_items i
        join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      ))
    )
  )
), historical_book as(
  select coalesce(sum(
    erp.sale_lifecycle_po_hpp_amount_v2620d(id,p_po_id)
  ),0)::numeric cogs
  from historical_untagged
), direct_book as(
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
  where l.po_id=p_po_id and e.source_type<>'INITIAL_IMPORT_BS_VALUE'
), residual_close as(
  select coalesce(sum(e.residual_amount),0)::numeric amount
  from erp.po_wip_close_events e
  join erp.journal_entries j on j.id=e.journal_entry_id
    and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'
  where e.po_id=p_po_id
)
select round(d.fg-h.cogs,2),round(d.cogs+h.cogs,2),
  round(d.other_out-c.amount,2)
from direct_book d cross join historical_book h cross join residual_close c
$function$;
