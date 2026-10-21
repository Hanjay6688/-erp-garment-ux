-- Private read-only equivalents of the exact, verified Native PO book.
-- Never execute independently or create an ambient Native admission.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

-- Source-derived guard, checked against the actual composed predecessor.
-- Root must first capture/verify the actual composed predecessor as usual.
-- Expected bodies include the R5 wrappers installed by cp7_f03_bundle.extension.
do $po_hpp_sources$begin
 if not exists(select 1 from pg_proc p where p.oid=to_regprocedure('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)')
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='00d43f50037e277b6eae966523e9d1d7c87423013dc282fedfec206056bb069b'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig @>array['search_path=""'])then
  raise exception 'CP7_CREDIT_PO_HPP_NATIVE_READER_SOURCE_CHANGED: erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid=to_regprocedure('erp.compute_po_hpp_gl_book_v2620d(uuid)')
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='64bd4d606e5ab90d4a7b31497c904504bad1045d78b7d1b895f93f292b079e03'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig @>array['search_path=""'])then
  raise exception 'CP7_CREDIT_PO_HPP_NATIVE_READER_SOURCE_CHANGED: erp.compute_po_hpp_gl_book_v2620d(uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid=to_regprocedure('erp.compute_po_hpp_gl_book_v2620e(uuid)')
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='e4e5dd17097409fde8f15e10abf2108661c088c656fb2255553014d6c2785919'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig @>array['search_path=""'])then
  raise exception 'CP7_CREDIT_PO_HPP_NATIVE_READER_SOURCE_CHANGED: erp.compute_po_hpp_gl_book_v2620e(uuid)';end if;
end $po_hpp_sources$;

-- Derived from the Native sources recorded in HPP_BOOK_SOURCE_TRACE.json.
-- Caller resolves the four account IDs on the server under the existing
-- accounting_account_mappings SHARE lock. Neither helper grants admission.
-- The old v2620d book is retained only as source trace; current returns use e.

create function cp7_credit.initial_po_hpp_lifecycle_amount_v1(
 p_journal uuid,p_po uuid,p_fg uuid,p_cogs uuid
)returns numeric
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $function$
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
  where e.id=p_journal and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  );
  if v_origin_type is null then
    return null;
  end if;

  select
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=p_cogs),0),
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=p_fg),0),
    count(*) filter(where l.account_id=p_cogs and l.po_id is not null),
    count(*) filter(where l.account_id=p_cogs and l.po_id is null)
  into v_book,v_fg_book,v_tagged,v_untagged
  from erp.journal_lines l where l.journal_entry_id=p_journal;
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
    where l.journal_entry_id=p_journal and l.po_id=p_po
      and l.account_id=p_cogs;
    select coalesce(sum(l.debit-l.credit),0) into v_po_fg_book
    from erp.journal_lines l
    where l.journal_entry_id=p_journal and l.po_id=p_po
      and l.account_id=p_fg;
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
    into v_result from ordered where po_id=p_po;
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
    into v_result from ordered where po_id=p_po;
  end if;
  if v_raw_total<=0 then
    return null;
  end if;
  return coalesce(v_result,0);
end
$function$;

create function cp7_credit.initial_po_hpp_book_v1(
 p_po uuid,p_fg uuid,p_cogs uuid,p_expense uuid,p_income uuid
)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $function$
with native_book(fg_value,cogs_value,other_out_value)as(
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
        p_fg,p_cogs,
        p_expense,p_income
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
        where i.sale_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po
      )) or
      (coalesce(o.source_type,e.source_type)='SALES_RETURN' and exists(
        select 1 from erp.sales_return_items i
        join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po
      ))
    )
  )
), historical_book as(
  select coalesce(sum(
    cp7_credit.initial_po_hpp_lifecycle_amount_v1(id,p_po,p_fg,p_cogs)
  ),0)::numeric cogs
  from historical_untagged
), direct_book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=p_fg),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=p_cogs),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        p_expense,p_income
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  where l.po_id=p_po and e.source_type<>'INITIAL_IMPORT_BS_VALUE'
), residual_close as(
  select coalesce(sum(e.residual_amount),0)::numeric amount
  from erp.po_wip_close_events e
  join erp.journal_entries j on j.id=e.journal_entry_id
    and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'
  where e.po_id=p_po
)
select round(d.fg-h.cogs,2),round(d.cogs+h.cogs,2),
  round(d.other_out-c.amount,2)
from direct_book d cross join historical_book h cross join residual_close c
)
select jsonb_build_object('hpp_total_cost',b.fg_value+b.cogs_value+b.other_out_value,
 'fg_value',b.fg_value,'cogs_value',b.cogs_value,'other_out_value',b.other_out_value)
from native_book b
$function$;

create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $function$
 select jsonb_build_object('mappings',(select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m
  where m.mapping_key in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME')),
  'accounts',(select jsonb_agg(to_jsonb(c)order by c.id)from erp.chart_accounts c where c.id in(
   select m.account_id from erp.accounting_account_mappings m where m.mapping_key in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME'))))
$function$;

-- A numerically unchanged sibling adjustment/reversal is still a different
-- source. Seal actual rows, not only balances. Own transient return DRAFTs
-- are deliberately excluded from the before-source profile.
create function cp7_credit.initial_hpp_support_v1(p_product uuid,p_po uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $function$
 with lots as(select fl.id from erp.fg_lots fl where(p_po is not null and fl.po_id=p_po)
  or(p_po is null and fl.po_id is null and fl.product_id=p_product)),conversions as(
  select a.conversion_id id from erp.product_conversion_allocations a where a.source_lot_id in(select id from lots)
   or a.destination_lot_id in(select id from lots)
  union select s.conversion_id from erp.be_conversion_sources_v1 s where s.source_lot_id in(select id from lots)
 ),book_ids as(
  select l.journal_entry_id id from erp.journal_lines l where(p_po is not null and l.po_id=p_po)
   or(p_po is null and l.po_id is null and l.product_id=p_product)
  union select e.id from erp.journal_entries e left join erp.journal_entries o on o.id=e.reversal_of_id
   where(e.source_type in('SALE','SALES_RETURN')or(e.source_type='JOURNAL_REVERSAL'and o.source_type in('SALE','SALES_RETURN')))
    and((coalesce(o.source_type,e.source_type)='SALE'and exists(select 1 from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=coalesce(o.source_id,e.source_id)and a.lot_id in(select id from lots)))
     or(coalesce(o.source_type,e.source_type)='SALES_RETURN'and exists(select 1 from erp.sales_return_items i
      where i.return_id=coalesce(o.source_id,e.source_id)and i.lot_id in(select id from lots))))
  union select e.journal_entry_id from erp.po_wip_close_events e where p_po is not null and e.po_id=p_po
 ),support(kind,identity,fact)as(
  select 'LOT',l.id::text,to_jsonb(l)from erp.fg_lots l where l.id in(select id from lots)
  union all select 'HPP',h.id::text,to_jsonb(h)from erp.hpp_versions h where h.lot_id in(select id from lots)
  union all select 'MOVEMENT',m.id::text,to_jsonb(m)from erp.fg_stock_movements m where m.lot_id in(select id from lots)
  union all select 'ALLOCATION',a.id::text,jsonb_build_object('allocation',to_jsonb(a),'item',to_jsonb(i),'sale',to_jsonb(h))
   from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers h on h.id=i.sale_id
   where a.lot_id in(select id from lots)and h.status in('POSTED','PARTIAL_PAID','PAID')
  union all select 'RETURN',i.id::text,jsonb_build_object('item',to_jsonb(i),'return',to_jsonb(h))
   from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id where i.lot_id in(select id from lots)and h.status<>'DRAFT'
  union all select 'CONVERSION',c.id::text,to_jsonb(c)from erp.product_conversions c where c.id in(select id from conversions)
  union all select 'CONVERSION_ALLOCATION',a.id::text,to_jsonb(a)from erp.product_conversion_allocations a where a.conversion_id in(select id from conversions)
  union all select 'CONVERSION_SOURCE',s.conversion_id::text,to_jsonb(s)from erp.be_conversion_sources_v1 s where s.conversion_id in(select id from conversions)
  union all select 'COST_SOURCE',s.document_id::text,to_jsonb(s)from erp.be_conversion_cost_sources_v1 s where s.conversion_id in(select id from conversions)
  union all select 'COST_EVENT',e.id::text,to_jsonb(e)from erp.be_conversion_cost_events_v1 e join erp.be_conversion_cost_sources_v1 s
   on s.document_id=e.document_id where s.conversion_id in(select id from conversions)
  union all select 'JOURNAL',j.id::text,to_jsonb(j)from erp.journal_entries j where j.id in(select id from book_ids)
  union all select 'JOURNAL_LINE',l.id::text,to_jsonb(l)from erp.journal_lines l where l.journal_entry_id in(select id from book_ids)
  union all select 'RESIDUAL_CLOSE',e.journal_entry_id::text,to_jsonb(e)from erp.po_wip_close_events e where p_po is not null and e.po_id=p_po
 )select jsonb_build_object('sha256',cp7_credit.pg_jsonb_sha256(coalesce(jsonb_agg(
   jsonb_build_array(kind,identity,fact)order by kind,identity,fact),'[]')),'row_count',count(*))from support
$function$;

alter function cp7_credit.initial_hpp_support_v1(uuid,uuid)owner to postgres;
alter function cp7_credit.initial_hpp_account_facts_v1()owner to postgres;
revoke all on function cp7_credit.initial_hpp_support_v1(uuid,uuid),cp7_credit.initial_hpp_account_facts_v1()from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
alter function cp7_credit.initial_po_hpp_lifecycle_amount_v1(uuid,uuid,uuid,uuid)owner to postgres;
alter function cp7_credit.initial_po_hpp_book_v1(uuid,uuid,uuid,uuid,uuid)owner to postgres;
revoke all on function cp7_credit.initial_po_hpp_lifecycle_amount_v1(uuid,uuid,uuid,uuid),
 cp7_credit.initial_po_hpp_book_v1(uuid,uuid,uuid,uuid,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
