-- R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): Ringkasan Gudang (menu warehouse-dashboard) reads real stock.
--
-- One read-only facade, public.erp_cp7_get_warehouse_summary_v1(p_query), for a user with warehouse.dashboard.view.
-- Per location and per kind it sums exactly the rows of the detail screens, with their own Native tables, filters and
-- rounding, so the summary equals what each detail screen shows:
--  * materials (warehouse.material.view): the balances of Bahan & Roll (cp7_material.balances of
--    scripts/cp7-src/materials/read.sql: erp.material_stock_movements with physical_at <= statement_timestamp(), per
--    material x roll x location, nonzero), without ACCESSORY materials (they are counted once, under accessories);
--    quantity per kind (FABRIC or other material) and unit, rolls = valid fabric roll balances above zero; value per row
--    round(qty x moving average, 6).
--  * accessories (warehouse.accessory.view): the stock list of erp.get_accessory_service_workspace_v1 (ACCESSORY
--    materials at active RAW_MATERIAL_WAREHOUSE locations, all posted movements, nonzero per material x location); value
--    per row round(qty x moving average, 2).
--  * finished goods (warehouse.fg.view): the positions of Ringkasan Barang Jadi (cp7_fg.positions of
--    scripts/cp7-src/fg/read.sql: physical = available + active SALE_RESERVE), per location and grade; value per position
--    as cp7_fg.lot_value (current HPP version, unknown while the lot's cost is pending), round(qty x HPP, 6).
-- Values only with finance.hpp.view. A section the user may not see in its detail screen is null, and its locations are
-- not listed. The attention list holds only facts the Native tables state, each behind the key of the screen that shows
-- it (see INTEGRATION.md): balances that need review, accessories outside the accessory locations, fabric below the
-- minimum written in Kain & Benchmark (also needs master.fabric.view), draft receipts, draft transfers, draft material
-- counts and draft FG adjustments (Stock Adjustment needs warehouse.stock.adjust).
--
-- Everything is computed in one SQL statement of a STABLE function, so one answer is one snapshot: a stock movement
-- committed while the read runs is either wholly in it or wholly out of it. No table, no write (business_DML false).
-- No TimeZone of its own: like the detail reads it runs in the caller's session (the Native HPP completeness it calls
-- for values must see the same session as Ringkasan Barang Jadi).
create role cp7_warehouse_summary_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_warehouse_summary authorization cp7_warehouse_summary_read;
revoke all on schema cp7_warehouse_summary from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_warehouse_summary to postgres;

create function cp7_warehouse_summary.access_now()returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_access jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_WAREHOUSE_SUMMARY_DENIED';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed'is distinct from'true'::jsonb or erp.has_permission('warehouse.dashboard.view')is not true then
  raise exception using errcode='42501',message='CP7_WAREHOUSE_SUMMARY_DENIED';end if;
 return jsonb_build_object('role_code',v_access->'profile'->>'role_code',
  'materials',erp.has_permission('warehouse.material.view')is true,
  'accessories',erp.has_permission('warehouse.accessory.view')is true,
  'finished_goods',erp.has_permission('warehouse.fg.view')is true,
  'values',erp.has_permission('finance.hpp.view')is true,
  'procurement',erp.has_permission('warehouse.procurement.view')is true,
  'stock_adjust',erp.has_permission('warehouse.stock.adjust')is true,
  'fabric_master',erp.has_permission('master.fabric.view')is true);
end $$;

create function cp7_warehouse_summary.workspace(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_access jsonb;v_mat boolean;v_acc boolean;v_fg boolean;v_value boolean;v_proc boolean;v_adjust boolean;v_fabric boolean;
 v_q text;v_n integer;v_off integer;v_out jsonb;
begin
 v_access:=cp7_warehouse_summary.access_now();
 if jsonb_typeof(p_query)is distinct from'object'or exists(select 1 from jsonb_object_keys(p_query)k where k not in('q','limit','offset'))
  or(p_query?'q'and jsonb_typeof(p_query->'q')not in('string','null'))
  or(p_query?'limit'and(jsonb_typeof(p_query->'limit')<>'number'or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset'and(jsonb_typeof(p_query->'offset')<>'number'or(p_query->>'offset')!~'^[0-9]{1,7}$'))then
  raise exception 'CP7_WAREHOUSE_SUMMARY_QUERY';end if;
 v_q:=btrim(coalesce(p_query->>'q',''));v_n:=coalesce((p_query->>'limit')::integer,25);v_off:=coalesce((p_query->>'offset')::integer,0);
 if length(v_q)>120 or v_n not between 1 and 100 or v_off not between 0 and 1000000 then raise exception 'CP7_WAREHOUSE_SUMMARY_QUERY';end if;
 v_mat:=(v_access->>'materials')::boolean;v_acc:=(v_access->>'accessories')::boolean;v_fg:=(v_access->>'finished_goods')::boolean;
 v_value:=(v_access->>'values')::boolean;v_proc:=(v_access->>'procurement')::boolean;v_adjust:=(v_access->>'stock_adjust')::boolean;
 v_fabric:=(v_access->>'fabric_master')::boolean;

 with
 -- The locations the search names (name or code); totals follow the search, the attention list does not.
 loc as materialized(
  select l.id,l.location_code::text location_code,l.location_name::text location_name,l.location_type::text location_type,l.is_active,z.zone_kind::text zone_kind
  from erp.locations l left join erp.bc_accessory_zones_v1 z on z.location_id=l.id
  where v_q=''or strpos(lower(concat_ws(' ',l.location_name,l.location_code)),lower(v_q))>0),
 -- Bahan & Roll balances (cp7_material.balances('',null,null,false)).
 mat_sum as materialized(
  select sm.material_id,sm.roll_id,sm.location_id,sum(sm.qty_signed)qty
  from erp.material_stock_movements sm join erp.materials m on m.id=sm.material_id
  where v_mat and sm.physical_at<=statement_timestamp()
  group by sm.material_id,sm.roll_id,sm.location_id),
 mat as materialized(
  select x.material_id,x.roll_id,x.location_id,x.qty,m.material_type::text material_type,m.unit_code::text unit_code,m.moving_average_cost unit_cost,
   l.is_active location_active,l.location_type::text location_type,
   ((m.material_type='FABRIC'and r.id is not null and r.material_id=m.id)or(m.material_type<>'FABRIC'and x.roll_id is null))roll_valid
  from mat_sum x join erp.materials m on m.id=x.material_id join erp.locations l on l.id=x.location_id
  left join erp.material_rolls r on r.id=x.roll_id
  where x.qty<>0),
 mat_f as materialized(
  select x.*,case when x.material_type='FABRIC'then'FABRIC'else'OTHER'end kind,
   case when x.unit_cost is not null then round(x.qty*x.unit_cost,6)end stock_value
  from mat x join loc on loc.id=x.location_id where x.material_type<>'ACCESSORY'),
 -- Aksesori stock list (erp.get_accessory_service_workspace_v1, cte "stock" without its search).
 acc as materialized(
  select m.id material_id,s.location_id,m.unit_code::text unit_code,sum(s.qty_signed)qty,m.moving_average_cost unit_cost
  from erp.material_stock_movements s join erp.materials m on m.id=s.material_id and m.material_type='ACCESSORY'
  join erp.locations l on l.id=s.location_id and l.location_type='RAW_MATERIAL_WAREHOUSE'and l.is_active
  where v_acc
  group by m.id,m.unit_code,m.moving_average_cost,s.location_id having sum(s.qty_signed)<>0),
 acc_f as materialized(select x.*,round(x.qty*x.unit_cost,2)stock_value from acc x join loc on loc.id=x.location_id),
 -- Ringkasan Barang Jadi positions (cp7_fg.positions('',false)).
 fg_sum as materialized(
  select fm.product_id,fm.lot_id,fm.location_id,fm.quality_grade::text quality_grade,sum(fm.qty_signed)::numeric available_qty,
   coalesce(sum(abs(fm.qty_signed))filter(where fm.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv
    where rv.reversal_of_id=fm.id and rv.physical_at<=statement_timestamp())),0)::numeric reserved_qty
  from erp.fg_stock_movements fm where v_fg and fm.physical_at<=statement_timestamp()
  group by fm.product_id,fm.lot_id,fm.location_id,fm.quality_grade),
 fg as materialized(
  select x.product_id,x.lot_id,x.location_id,x.quality_grade,x.available_qty,x.reserved_qty,x.available_qty+x.reserved_qty physical_qty,
   coalesce(lt.id is not null and lt.product_id=p.id,false)lineage_valid
  from fg_sum x join erp.products p on p.id=x.product_id join erp.sizes sz on sz.id=p.size_id join erp.brands br on br.id=p.brand_id
  join erp.locations l on l.id=x.location_id left join erp.fg_lots lt on lt.id=x.lot_id
  where x.available_qty+x.reserved_qty<>0 or x.available_qty<>0 or x.reserved_qty<>0),
 -- cp7_fg.lot_value per lot of the listed positions (finance.hpp.view only).
 fg_lot as materialized(
  select lt.id lot_id,h.hpp_per_pcs,
   (h.id is null or h.hpp_per_pcs is null or h.cost_state='ESTIMATED'or erp.bd_lot_laundry_unknown_v1(lt.id)
    or(lt.po_id is not null and not exists(select 1 from erp.get_hpp_completeness(lt.po_id)hc where hc.pending_reason_count=0)))pending
  from(select distinct x.lot_id from fg x join loc on loc.id=x.location_id where v_value and x.lot_id is not null)d
  join erp.fg_lots lt on lt.id=d.lot_id
  left join lateral(select hv.id,hv.hpp_per_pcs,hv.cost_state from erp.hpp_versions hv where hv.lot_id=lt.id and hv.is_current order by hv.version_no desc limit 1)h on true),
 fg_f as materialized(
  select x.*,case when k.pending is false then round(x.physical_qty*k.hpp_per_pcs,6)end stock_value
  from fg x join loc on loc.id=x.location_id left join fg_lot k on k.lot_id=x.lot_id),
 -- Per location (total_row 0) and over all searched locations (total_row 1).
 mat_lines as(
  select grouping(x.location_id)total_row,x.location_id,x.kind,x.unit_code,sum(x.qty)qty,
   count(*)filter(where x.kind='FABRIC'and x.roll_valid and x.qty>0)rolls,count(*)balances,bool_or(x.qty<0 or not x.roll_valid)conflict
  from mat_f x group by grouping sets((x.location_id,x.kind,x.unit_code),(x.kind,x.unit_code))),
 mat_part as(
  select grouping(x.location_id)total_row,x.location_id,coalesce(sum(x.stock_value),0)stock_value,count(*)filter(where x.stock_value is null)unknown
  from mat_f x group by grouping sets((x.location_id),())),
 mat_json as(
  select v.total_row,v.location_id,jsonb_build_object('lines',coalesce((select jsonb_agg(jsonb_build_object('kind',ml.kind,'unit_code',ml.unit_code,
    'qty',ml.qty::text,'rolls',ml.rolls::text,'balances',ml.balances::text,'quality',case when ml.conflict then'CONFLICT'else'KNOWN'end)order by ml.kind,ml.unit_code)
    from mat_lines ml where ml.total_row=v.total_row and ml.location_id is not distinct from v.location_id),'[]'::jsonb))
   ||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value',v.stock_value::text,'unknown_count',v.unknown::text,
    'basis','CURRENT_MATERIAL_MOVING_AVERAGE'))else'{}'::jsonb end part
  from mat_part v),
 acc_lines as(
  select grouping(x.location_id)total_row,x.location_id,x.unit_code,sum(x.qty)qty,count(distinct x.material_id)items,count(*)balances,bool_or(x.qty<0)conflict
  from acc_f x group by grouping sets((x.location_id,x.unit_code),(x.unit_code))),
 acc_part as(
  select grouping(x.location_id)total_row,x.location_id,coalesce(sum(x.stock_value),0)stock_value,count(*)filter(where x.stock_value is null)unknown
  from acc_f x group by grouping sets((x.location_id),())),
 acc_json as(
  select v.total_row,v.location_id,jsonb_build_object('lines',coalesce((select jsonb_agg(jsonb_build_object('unit_code',al.unit_code,'qty',al.qty::text,
    'items',al.items::text,'balances',al.balances::text,'quality',case when al.conflict then'CONFLICT'else'KNOWN'end)order by al.unit_code)
    from acc_lines al where al.total_row=v.total_row and al.location_id is not distinct from v.location_id),'[]'::jsonb))
   ||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value',v.stock_value::text,'unknown_count',v.unknown::text,
    'basis','CURRENT_MATERIAL_MOVING_AVERAGE'))else'{}'::jsonb end part
  from acc_part v),
 fg_grades as(
  select grouping(x.location_id)total_row,x.location_id,x.quality_grade,sum(x.physical_qty)physical_qty
  from fg_f x group by grouping sets((x.location_id,x.quality_grade),(x.quality_grade))),
 fg_part as(
  select grouping(x.location_id)total_row,x.location_id,coalesce(sum(x.physical_qty),0)physical_qty,coalesce(sum(x.reserved_qty),0)reserved_qty,
   coalesce(sum(x.available_qty),0)available_qty,count(*)positions,coalesce(bool_or(x.available_qty<0 or x.physical_qty<0 or not x.lineage_valid),false)conflict,
   coalesce(sum(x.stock_value),0)stock_value,count(*)filter(where x.stock_value is null)unknown
  from fg_f x group by grouping sets((x.location_id),())),
 fg_json as(
  select v.total_row,v.location_id,jsonb_build_object('physical_qty',v.physical_qty::text,'reserved_qty',v.reserved_qty::text,'available_qty',v.available_qty::text,
    'positions',v.positions::text,'quality',case when v.conflict then'CONFLICT'else'KNOWN'end,
    'grades',coalesce((select jsonb_agg(jsonb_build_object('quality_grade',fgr.quality_grade,'physical_qty',fgr.physical_qty::text)order by fgr.quality_grade)
     from fg_grades fgr where fgr.total_row=v.total_row and fgr.location_id is not distinct from v.location_id),'[]'::jsonb))
   ||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value',v.stock_value::text,'unknown_count',v.unknown::text,
    'basis','CURRENT_RESTATED_LOT_VALUE'))else'{}'::jsonb end part
  from fg_part v),
 -- A location is listed when a section the user may see holds stock there.
 hit as(select x.location_id from mat_f x union select x.location_id from acc_f x union select x.location_id from fg_f x),
 shown as materialized(select loc.* from loc join hit on hit.location_id=loc.id),
 paged as materialized(select * from shown order by location_name,location_code,id limit v_n offset v_off),
 page_rows as(
  select coalesce(jsonb_agg(jsonb_build_object('location_id',pg.id,'location_code',pg.location_code,'location_name',pg.location_name,
    'location_type',pg.location_type,'is_active',pg.is_active,'zone_kind',pg.zone_kind,
    'materials',case when v_mat then coalesce((select mj.part from mat_json mj where mj.total_row=0 and mj.location_id=pg.id),
      jsonb_build_object('lines','[]'::jsonb)||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value','0','unknown_count','0','basis','CURRENT_MATERIAL_MOVING_AVERAGE'))else'{}'::jsonb end)end,
    'accessories',case when v_acc then coalesce((select aj.part from acc_json aj where aj.total_row=0 and aj.location_id=pg.id),
      jsonb_build_object('lines','[]'::jsonb)||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value','0','unknown_count','0','basis','CURRENT_MATERIAL_MOVING_AVERAGE'))else'{}'::jsonb end)end,
    'finished_goods',case when v_fg then coalesce((select fj.part from fg_json fj where fj.total_row=0 and fj.location_id=pg.id),
      jsonb_build_object('physical_qty','0','reserved_qty','0','available_qty','0','positions','0','quality','KNOWN','grades','[]'::jsonb)
      ||case when v_value then jsonb_build_object('valuation',jsonb_build_object('value','0','unknown_count','0','basis','CURRENT_RESTATED_LOT_VALUE'))else'{}'::jsonb end)end)
   order by pg.location_name,pg.location_code,pg.id),'[]'::jsonb)body,count(*)n
  from paged pg),
 -- Fabric below the minimum stock written in Kain & Benchmark (erp.fabric_master_profiles), over every location of Bahan & Roll.
 low as materialized(
  select m.id material_id,m.material_sku::text material_sku,m.material_name::text material_name,m.unit_code::text unit_code,
   coalesce((select sum(x.qty)from mat x where x.material_id=m.id),0)qty,fp.minimum_stock_qty minimum_qty
  from erp.materials m join erp.fabric_master_profiles fp on fp.material_id=m.id
  where v_mat and v_fabric and m.material_type='FABRIC'and m.is_active and fp.minimum_stock_qty>0),
 low_hit as materialized(select * from low y where y.qty<y.minimum_qty),
 attention as(
  select coalesce(jsonb_agg(t.item order by t.ord),'[]'::jsonb)body from(values
   (1,case when v_mat then jsonb_build_object('kind','MATERIAL_BALANCE_REVIEW','menu','materials-rolls',
     'count',(select count(*)from mat x where x.material_type<>'ACCESSORY'and(x.qty<0 or not x.roll_valid))::text)end),
   (2,case when v_mat then jsonb_build_object('kind','ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS','menu','materials-rolls',
     'count',(select count(*)from mat x where x.material_type='ACCESSORY'and not(x.location_type='RAW_MATERIAL_WAREHOUSE'and x.location_active))::text)end),
   (3,case when v_acc then jsonb_build_object('kind','ACCESSORY_NEGATIVE','menu','accessories',
     'count',(select count(*)from acc x where x.qty<0)::text)end),
   (4,case when v_fg then jsonb_build_object('kind','FG_POSITION_REVIEW','menu','fg-summary',
     'count',(select count(*)from fg x where x.available_qty<0 or x.physical_qty<0 or not x.lineage_valid)::text)end),
   (5,case when v_mat and v_fabric then jsonb_build_object('kind','FABRIC_BELOW_MINIMUM','menu','materials-rolls',
     'count',(select count(*)from low_hit)::text,
     'rows',(select coalesce(jsonb_agg(jsonb_build_object('material_id',y.material_id,'material_sku',y.material_sku,'material_name',y.material_name,
       'unit_code',y.unit_code,'qty',y.qty::text,'minimum_qty',y.minimum_qty::text)order by y.material_sku,y.material_id),'[]'::jsonb)
      from(select * from low_hit w order by w.material_sku,w.material_id limit 10)y))end),
   (6,case when v_proc then jsonb_build_object('kind','RECEIPT_DRAFT','menu','procurement',
     'count',(select count(*)from erp.material_purchase_headers ph where ph.status='DRAFT')::text)end),
   (7,case when v_mat then jsonb_build_object('kind','MATERIAL_TRANSFER_DRAFT','menu','materials-rolls',
     'count',(select count(*)from erp.material_transfers mt where mt.status='DRAFT')::text)end),
   (8,case when v_mat and v_adjust then jsonb_build_object('kind','MATERIAL_COUNT_DRAFT','menu','stock-adjustment',
     'count',(select count(*)from erp.material_adjustments ma where ma.status='DRAFT')::text)end),
   (9,case when v_fg and v_adjust then jsonb_build_object('kind','FG_ADJUSTMENT_DRAFT','menu','stock-adjustment',
     'count',(select count(*)from erp.fg_adjustments fa where fa.status='DRAFT')::text)end)
  )t(ord,item)where t.item is not null)
 select jsonb_build_object('contract_version','cp7.warehouse-summary.v1','kind','LIVE_WAREHOUSE_SUMMARY','read_at',statement_timestamp(),
  'business_DML',false,'financial_captured',v_value,'q',v_q,
  'sections',jsonb_build_object('materials',v_mat,'accessories',v_acc,'finished_goods',v_fg),
  'totals',jsonb_build_object(
   'materials',case when v_mat then(select mj.part from mat_json mj where mj.total_row=1)end,
   'accessories',case when v_acc then(select aj.part from acc_json aj where aj.total_row=1)end,
   'finished_goods',case when v_fg then(select fj.part from fg_json fj where fj.total_row=1)end),
  'page',jsonb_build_object('rows',pr.body,'total',(select count(*)from shown)::text,'offset',v_off,'limit',v_n,
   'next_offset',case when v_off+pr.n<(select count(*)from shown)then v_off+pr.n end),
  'attention',(select a.body from attention a))
 into v_out from page_rows pr;
 return v_out;
end $$;

create function public.erp_cp7_get_warehouse_summary_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_warehouse_summary.workspace(p_query)$$;
alter function cp7_warehouse_summary.access_now()owner to postgres;
alter function cp7_warehouse_summary.workspace(jsonb)owner to postgres;
grant create on schema public to cp7_warehouse_summary_read;
alter function public.erp_cp7_get_warehouse_summary_v1(jsonb)owner to cp7_warehouse_summary_read;
revoke create on schema public from cp7_warehouse_summary_read;
revoke all on function cp7_warehouse_summary.access_now(),cp7_warehouse_summary.workspace(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_warehouse_summary_read;
grant execute on function cp7_warehouse_summary.workspace(jsonb)to cp7_warehouse_summary_read;
revoke all on function public.erp_cp7_get_warehouse_summary_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_warehouse_summary_v1(jsonb)to authenticated;
