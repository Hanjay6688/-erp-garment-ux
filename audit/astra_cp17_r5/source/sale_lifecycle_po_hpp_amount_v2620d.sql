create function erp.sale_lifecycle_po_hpp_amount_v2620d(
  p_journal_id uuid,p_po_id uuid
)
returns numeric
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_origin_type text;
  v_origin_id uuid;
  v_book numeric(20,2):=0;
  v_fg_book numeric(20,2):=0;
  v_po_book numeric(20,2):=0;
  v_po_fg_book numeric(20,2):=0;
  v_tagged integer:=0;
  v_untagged integer:=0;
  v_raw_total numeric:=0;
  v_result numeric(20,2):=0;
begin
  select coalesce(o.source_type,e.source_type),coalesce(o.source_id,e.source_id)
  into v_origin_type,v_origin_id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.id=p_journal_id and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  );
  if v_origin_type is null then
    return null;
  end if;

  select
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0),
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0),
    count(*) filter(where l.account_id=erp.account_id('COGS') and l.po_id is not null),
    count(*) filter(where l.account_id=erp.account_id('COGS') and l.po_id is null)
  into v_book,v_fg_book,v_tagged,v_untagged
  from erp.journal_lines l where l.journal_entry_id=p_journal_id;
  if abs(v_book+v_fg_book)>0.005 then
    return null;
  end if;
  if abs(v_book)<=0.005 then return 0; end if;
  if v_tagged>0 and v_untagged>0 then
    return null;
  end if;

  if v_tagged>0 then
    select coalesce(sum(l.debit-l.credit),0) into v_po_book
    from erp.journal_lines l
    where l.journal_entry_id=p_journal_id and l.po_id=p_po_id
      and l.account_id=erp.account_id('COGS');
    select coalesce(sum(l.debit-l.credit),0) into v_po_fg_book
    from erp.journal_lines l
    where l.journal_entry_id=p_journal_id and l.po_id=p_po_id
      and l.account_id=erp.account_id('FG_INVENTORY');
    if abs(v_po_book+v_po_fg_book)>0.005 then
      return null;
    end if;
    return round(v_po_book,2);
  end if;

  if v_origin_type='SALE' then
    select coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0) into v_raw_total
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    where i.sale_id=v_origin_id;
    with weights as(
      select fl.po_id,sum(a.qty_pcs*a.unit_hpp_snapshot)::numeric raw_value
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      join erp.fg_lots fl on fl.id=a.lot_id
      where i.sale_id=v_origin_id and fl.po_id is not null
      group by fl.po_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by po_id rows unbounded preceding) cumulative_value,
        sum(raw_value) over() total_value
      from weights w
    )
    select round(v_book*cumulative_value/nullif(total_value,0),2)
          -round(v_book*(cumulative_value-raw_value)/nullif(total_value,0),2)
    into v_result from ordered where po_id=p_po_id;
  else
    select coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0) into v_raw_total
    from erp.sales_return_items i where i.return_id=v_origin_id;
    with weights as(
      select fl.po_id,sum(i.qty_pcs*i.unit_hpp_snapshot)::numeric raw_value
      from erp.sales_return_items i
      join erp.fg_lots fl on fl.id=i.lot_id
      where i.return_id=v_origin_id and fl.po_id is not null
      group by fl.po_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by po_id rows unbounded preceding) cumulative_value,
        sum(raw_value) over() total_value
      from weights w
    )
    select round(v_book*cumulative_value/nullif(total_value,0),2)
          -round(v_book*(cumulative_value-raw_value)/nullif(total_value,0),2)
    into v_result from ordered where po_id=p_po_id;
  end if;
  if v_raw_total<=0 then
    return null;
  end if;
  return coalesce(v_result,0);
end
$function$;
