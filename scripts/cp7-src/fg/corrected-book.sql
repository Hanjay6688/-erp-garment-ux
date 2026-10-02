-- Effective original-source cards. Prefixes always include the complete scope
-- before display filters/paging; manual order of unrelated cards is preserved.
create function cp7_fg.corrected_book_rows()returns setof jsonb
language sql stable security invoker set search_path=''as $$
 with movements as materialized(
  select m.*,coalesce(l.origin_id,m.id)origin_id,l.correction_id,l.recorded_at correction_recorded_at,
   case when m.movement_type='SALE_RESERVE'or exists(select 1 from erp.fg_stock_movements o
    where o.id=m.reversal_of_id and o.movement_type='SALE_RESERVE')then-m.qty_signed else 0 end reservation_delta
  from erp.fg_stock_movements m left join cp7_fg.correction_movements l on l.member_id=m.id
  where m.physical_at<=statement_timestamp()
 ), effective as materialized(
  select origin_id,sum(qty_signed)qty_signed,sum(reservation_delta)reservation_delta,
   count(distinct correction_id)correction_count,max(correction_recorded_at)correction_recorded_at,
   jsonb_agg(jsonb_build_object('id',id,'physical_at',physical_at,'recorded_at',system_created_at,
    'lot_id',lot_id,'source_type',source_type,'source_id',source_id,'reversal_of_id',reversal_of_id,
    'available_delta',qty_signed::text,'reservation_delta',reservation_delta::text)
    order by system_created_at,id)audit_movements
  from movements group by origin_id
 ), source as materialized(
  select o.*,e.qty_signed effective_qty,e.reservation_delta,e.correction_count,e.correction_recorded_at,e.audit_movements
  from effective e join erp.fg_stock_movements o on o.id=e.origin_id
 ), prefix as(
  select m.*,sum(effective_qty+reservation_delta)over book book_physical_after,
   sum(effective_qty)over book book_available_after,sum(reservation_delta)over book book_reserved_after,
   sum(effective_qty+reservation_delta)over official official_physical_after,
   sum(effective_qty)over official official_available_after,sum(reservation_delta)over official official_reserved_after
  from source m
  window book as(partition by product_id,location_id,quality_grade order by book_order,id rows unbounded preceding),
   official as(partition by product_id,location_id,quality_grade order by physical_at,system_created_at,id rows unbounded preceding)
 )
 select jsonb_build_object('id',m.id,'book_order',m.book_order::text,'physical_at',m.physical_at,
  'recorded_at',m.system_created_at,'product_id',m.product_id,'brand_id',b.id,'brand_name',b.brand_name,
  'commercial_sku',erp.bf_commercial_sku_at_v1(p.id,m.physical_at),'product_name',p.product_name,'size_code',s.size_code,
  'lot_id',m.lot_id,'lot_number',l.lot_number,'location_id',m.location_id,'location_name',loc.location_name,
  'quality_grade',m.quality_grade,'customer_id',m.customer_id,'customer_name',c.customer_name,
  'movement_type',m.movement_type,'source_type',m.source_type,'source_id',m.source_id,'reversal_of_id',m.reversal_of_id,'notes',m.notes,
  'physical_delta',(m.effective_qty+m.reservation_delta)::text,'reservation_delta',m.reservation_delta::text,
  'available_delta',m.effective_qty::text,'book_physical_before',(m.book_physical_after-m.effective_qty-m.reservation_delta)::text,
  'book_physical_after',m.book_physical_after::text,'book_available_after',m.book_available_after::text,
  'book_reserved_after',m.book_reserved_after::text,'official_physical_after',m.official_physical_after::text,
  'official_available_after',m.official_available_after::text,'official_reserved_after',m.official_reserved_after::text,
  'original_physical_delta',(m.qty_signed+case when m.movement_type='SALE_RESERVE'or exists(select 1 from erp.fg_stock_movements o
    where o.id=m.reversal_of_id and o.movement_type='SALE_RESERVE')then-m.qty_signed else 0 end)::text,
  'correction_count',m.correction_count::text,'correction_recorded_at',m.correction_recorded_at,
  'audit_movements',m.audit_movements)
 from prefix m join erp.products p on p.id=m.product_id join erp.brands b on b.id=p.brand_id join erp.sizes s on s.id=p.size_id
 join erp.locations loc on loc.id=m.location_id left join erp.fg_lots l on l.id=m.lot_id left join erp.customers c on c.id=m.customer_id
$$;

create function cp7_fg.corrected_book_workspace(p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;validated jsonb;rows jsonb;total bigint;n integer;off integer;
begin
 a:=cp7_fg.book_access();
 -- Reuse the complete existing closed-query/type/limit/permission validator.
 validated:=cp7_fg.book_workspace(p_query);n:=(validated->'page'->>'limit')::integer;off:=(validated->'page'->>'offset')::integer;
 with filtered as materialized(
  select value r from cp7_fg.corrected_book_rows()value where
   (p_query->>'from'is null or(value->>'physical_at')::timestamptz>=(p_query->>'from')::timestamptz)
   and(p_query->>'to'is null or(value->>'physical_at')::timestamptz<(p_query->>'to')::timestamptz)
   and(coalesce(jsonb_array_length(p_query->'brand_ids'),0)=0 or p_query->'brand_ids'@>jsonb_build_array(value->>'brand_id'))
   and(coalesce(jsonb_array_length(p_query->'customer_ids'),0)=0 or p_query->'customer_ids'@>jsonb_build_array(value->>'customer_id'))
   and(coalesce(jsonb_array_length(p_query->'movement_types'),0)=0 or p_query->'movement_types'@>jsonb_build_array(value->>'movement_type'))
   and(btrim(coalesce(p_query->>'q',''))=''or strpos(lower(concat_ws(' ',value->>'brand_name',value->>'commercial_sku',
    value->>'product_name',value->>'size_code',value->>'lot_number',value->>'location_name',value->>'customer_name',
    value->>'source_type',value->>'source_id',value->>'notes')),lower(btrim(p_query->>'q')))>0)
 ),page as(select r from filtered order by(r->>'book_order')::bigint,r->>'id'limit n offset off)
 select(select count(*)from filtered),coalesce(jsonb_agg(r order by(r->>'book_order')::bigint,r->>'id'),'[]')into total,rows from page;
 return(validated-'page')||jsonb_build_object('contract_version','cp7.fg-book.v2',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,
  'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $$;
create function public.erp_cp7_get_fg_book_v2(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_fg.corrected_book_workspace(p_query)$$;
grant create on schema public to cp7_fg_read;
alter function cp7_fg.corrected_book_rows()owner to cp7_fg_read;
alter function cp7_fg.corrected_book_workspace(jsonb)owner to cp7_fg_read;
alter function public.erp_cp7_get_fg_book_v2(jsonb)owner to cp7_fg_read;
revoke create on schema public from cp7_fg_read;
revoke all on function cp7_fg.corrected_book_rows(),cp7_fg.corrected_book_workspace(jsonb)from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_fg_book_v2(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_fg_book_v2(jsonb)to authenticated;
