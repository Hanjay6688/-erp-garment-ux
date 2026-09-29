create function cp7_material.balances(p_q text,p_location uuid,p_material uuid,p_zero boolean)
returns table(material_id uuid,material_sku text,material_name text,unit_code text,material_active boolean,
 roll_id uuid,roll_number text,location_id uuid,location_name text,location_active boolean,location_type text,
 zone_kind text,qty numeric,current_ma numeric,last_movement_at timestamptz,material_type text,roll_valid boolean)
language sql stable security invoker set search_path='' as $$
 with physical as (
  select sm.material_id,sm.roll_id,sm.location_id,sum(sm.qty_signed) qty,max(sm.physical_at) last_at
  from erp.material_stock_movements sm join erp.materials m on m.id=sm.material_id
  where (p_location is null or sm.location_id=p_location) and (p_material is null or sm.material_id=p_material)
   and sm.physical_at<=statement_timestamp()
  group by sm.material_id,sm.roll_id,sm.location_id
 )
 select m.id,m.material_sku::text,m.material_name::text,m.unit_code::text,m.is_active,
  x.roll_id,r.roll_number::text,l.id,l.location_name::text,l.is_active,l.location_type::text,z.zone_kind,x.qty,m.moving_average_cost,x.last_at,m.material_type::text,
  ((m.material_type='FABRIC' and r.id is not null and r.material_id=m.id) or (m.material_type<>'FABRIC' and x.roll_id is null))
 from physical x join erp.materials m on m.id=x.material_id join erp.locations l on l.id=x.location_id
 left join erp.material_rolls r on r.id=x.roll_id left join erp.bc_accessory_zones_v1 z on z.location_id=l.id
 where (p_zero or x.qty<>0) and (p_q='' or strpos(lower(m.material_sku||' '||m.material_name||' '||coalesce(r.roll_number,'')||' '||l.location_name),lower(p_q))>0)
$$;

create function cp7_material.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;rows jsonb;totals jsonb;total bigint;q text;loc uuid;mat uuid;zero boolean;n integer;off integer;
begin
 a:=cp7_material.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in ('q','location_id','material_id','show_zero','limit','offset')) then raise exception 'CP7_MATERIAL_QUERY';end if;
 if exists(select 1 from jsonb_each(p_query) e where e.key in ('q','location_id','material_id') and jsonb_typeof(e.value) not in ('string','null'))
  or(p_query ? 'show_zero' and jsonb_typeof(p_query->'show_zero')<>'boolean')
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_MATERIAL_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));loc:=nullif(p_query->>'location_id','')::uuid;mat:=nullif(p_query->>'material_id','')::uuid;
 zero:=coalesce((p_query->>'show_zero')::boolean,false);n:=coalesce((p_query->>'limit')::integer,50);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_MATERIAL_QUERY';end if;
 select count(*) into total from cp7_material.balances(q,loc,mat,zero);
 select coalesce(jsonb_agg(jsonb_build_object('material_id',x.material_id,'material_sku',x.material_sku,'material_name',x.material_name,'material_type',x.material_type,'unit_code',x.unit_code,
  'roll_id',x.roll_id,'roll_number',x.roll_number,'location_id',x.location_id,'location_name',x.location_name,
  'qty',x.qty::text,'last_movement_at',x.last_movement_at,'quality',case when x.qty<0 or not x.roll_valid then 'CONFLICT' else 'KNOWN' end,
  'availability',case when x.qty<0 or not x.roll_valid then 'REVIEW_REQUIRED' when not x.material_active then 'MATERIAL_INACTIVE'
   when not x.location_active then 'LOCATION_INACTIVE' when x.zone_kind is not null then 'SPECIAL_ZONE' when x.location_type<>'RAW_MATERIAL_WAREHOUSE' then 'LOCATION_REVIEW'
   when x.qty=0 then 'EMPTY' else 'ON_HAND' end)
  ||case when (a->>'can_value')::boolean then jsonb_build_object('valuation',jsonb_build_object(
   'state',case when x.current_ma is null then 'UNKNOWN' else 'KNOWN' end,'unit_cost',x.current_ma::text,'value',round(x.qty*x.current_ma,6)::text,'basis','CURRENT_MATERIAL_MOVING_AVERAGE')) else '{}'::jsonb end
  order by x.material_sku,x.roll_number nulls first,x.material_id,x.roll_id nulls first,x.location_id),'[]'::jsonb)
 into rows from (select * from cp7_material.balances(q,loc,mat,zero) order by material_sku,roll_number nulls first,material_id,roll_id nulls first,location_id limit n offset off) x;
 select coalesce(jsonb_agg(jsonb_build_object('unit_code',x.unit_code,'qty',x.qty::text,'quality',case when x.conflicts then 'CONFLICT' else 'KNOWN' end) order by x.unit_code),'[]'::jsonb)
 into totals from (select unit_code,sum(qty) qty,bool_or(qty<0 or not roll_valid) conflicts from cp7_material.balances(q,loc,mat,zero) group by unit_code) x;
 return jsonb_build_object('contract_version','cp7.material-workspace.v1','kind','LIVE_MATERIAL_LEDGER','read_at',statement_timestamp(),
  'capabilities',jsonb_build_object('transfer',a->'can_adjust','reverse_transfer',a->'can_reverse'),'quantity_basis','POSTED_PHYSICAL_LEDGER_CURRENT_KNOWLEDGE','financial_captured',a->'can_value','totals_by_unit',totals,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;

create function cp7_material.ledger(p_material uuid,p_roll uuid,p_location uuid,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;rows jsonb;total bigint;
begin
 a:=cp7_material.access_now();
 if p_material is null or p_location is null or p_offset is null or p_offset not between 0 and 1000000
  or p_limit is null or p_limit not between 1 and 100 then raise exception 'CP7_MATERIAL_LEDGER_SCOPE';end if;
 if not exists(select 1 from erp.materials m where m.id=p_material and ((m.material_type='FABRIC' and exists(select 1 from erp.material_rolls r where r.id=p_roll and r.material_id=m.id)) or (m.material_type<>'FABRIC' and p_roll is null)))
  or not exists(select 1 from erp.locations where id=p_location) then raise exception 'CP7_MATERIAL_LEDGER_SCOPE';end if;
 select count(*) into total from erp.material_stock_movements where material_id=p_material and roll_id is not distinct from p_roll and location_id=p_location and physical_at<=statement_timestamp();
 with prefix as (
  select sm.*,sum(sm.qty_signed) over(order by sm.physical_at,sm.system_created_at,sm.id rows unbounded preceding) running_qty
  from erp.material_stock_movements sm where sm.material_id=p_material and sm.roll_id is not distinct from p_roll and sm.location_id=p_location and sm.physical_at<=statement_timestamp()
 ), paged as (select * from prefix order by physical_at desc,system_created_at desc,id desc limit p_limit offset p_offset)
 select coalesce(jsonb_agg(jsonb_build_object('movement_id',x.id,'physical_at',x.physical_at,'recorded_at',x.system_created_at,
  'movement_type',x.movement_type,'qty_signed',x.qty_signed::text,'running_qty',x.running_qty::text,
  'source_type',x.source_type,'source_id',x.source_id,'reversal_of_id',x.reversal_of_id,'note',x.note)
  ||case when (a->>'can_value')::boolean then jsonb_build_object('valuation',jsonb_build_object('state',case when x.unit_cost_snapshot is null then 'UNKNOWN' else 'KNOWN' end,'unit_cost',x.unit_cost_snapshot::text,
   'movement_value',round(x.qty_signed*x.unit_cost_snapshot,6)::text,'basis','CURRENT_RESTATED_MOVEMENT_COST')) else '{}'::jsonb end
  order by x.physical_at desc,x.system_created_at desc,x.id desc),'[]'::jsonb) into rows from paged x;
 return jsonb_build_object('contract_version','cp7.material-ledger.v1','material_id',p_material,'roll_id',p_roll,'location_id',p_location,
  'read_at',statement_timestamp(),'financial_captured',a->'can_value','history_basis','CURRENT_RESTATED_NOT_AS_KNOWN',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end));
end $$;

create function public.erp_cp7_get_materials_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.workspace(p_query)$$;
create function public.erp_cp7_get_material_ledger_v1(p_material uuid,p_roll uuid,p_location uuid,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.ledger(p_material,p_roll,p_location,p_offset,p_limit)$$;
