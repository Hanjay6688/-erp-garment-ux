-- Registered identities for a physical count, including no prior movement at
-- this warehouse. This projection is not stock and supplies no invented cost.
create function cp7_material.count_options(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;loc uuid;loc_name text;q text;off integer;n integer;total bigint;rows jsonb;
begin
 a:=cp7_material.access_now();
 if a->'can_adjust' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_MATERIAL_ADJUST_DENIED';end if;
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ? 'location_id'
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('location_id','q','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','location_id') and jsonb_typeof(e.value)<>'string')
  or exists(select 1 from jsonb_each(p_query) e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_COUNT_OPTIONS_QUERY';end if;
 loc:=(p_query->>'location_id')::uuid;q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 if loc is null or length(q)>120 or off not between 0 and 1000000 or n not between 1 and 100 then raise exception 'CP7_COUNT_OPTIONS_QUERY';end if;
 select l.location_name into loc_name from erp.locations l where l.id=loc and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id);
 if not found then raise exception 'CP7_COUNT_ORDINARY_WAREHOUSE_REQUIRED';end if;
 with choices as materialized(
  select m.id material_id,m.material_sku,m.material_name,m.material_type,m.unit_code,r.id roll_id,r.roll_number
  from erp.materials m left join erp.material_rolls r on m.material_type='FABRIC' and r.material_id=m.id
  where m.is_active and(m.material_type<>'FABRIC' or r.id is not null)
   and(q='' or strpos(lower(m.material_sku||' '||m.material_name||' '||coalesce(r.roll_number,'')),lower(q))>0)
 ) select(select count(*) from choices),
  (select coalesce(jsonb_agg(to_jsonb(c) order by c.material_sku,c.material_id,c.roll_number nulls first,c.roll_id nulls first),'[]')
   from(select * from choices order by material_sku,material_id,roll_number nulls first,roll_id nulls first limit n offset off)c)
 into total,rows;
 return jsonb_build_object('contract_version','cp7.material-count-options.v1','selection_basis','REGISTERED_IDENTITY_NOT_STOCK','read_at',statement_timestamp(),
  'location_id',loc,'location_name',loc_name,'query',q,'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_material_count_options_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.count_options(p_query)$$;
