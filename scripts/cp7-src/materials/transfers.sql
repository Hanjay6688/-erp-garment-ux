create function cp7_material.transfer_header(h erp.material_transfers) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'number',h.transfer_number,'from_location_id',h.from_location_id,'to_location_id',h.to_location_id,
  'from_location_name',(select location_name from erp.locations where id=h.from_location_id),
  'to_location_name',(select location_name from erp.locations where id=h.to_location_id),
  'physical_at',h.physical_at,'status',h.status,'row_version',h.row_version::text,'notes',h.notes,
  'line_count',(select count(*)::text from erp.material_transfer_items where transfer_id=h.id))
$$;
create function cp7_material.transfers(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;s text;n integer;off integer;chosen uuid;total bigint;rows jsonb;detail jsonb:=null;h erp.material_transfers;items jsonb;
begin
 a:=cp7_material.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','status','limit','offset','transfer_id'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','status','transfer_id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_MATERIAL_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));s:=coalesce(p_query->>'status','ALL');n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);chosen:=nullif(p_query->>'transfer_id','')::uuid;
 if length(q)>120 or s not in('ALL','DRAFT','POSTED','REVERSED') or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_MATERIAL_QUERY';end if;
 select count(*) into total from erp.material_transfers t where (s='ALL' or t.status::text=s) and (q='' or strpos(lower(t.transfer_number),lower(q))>0);
 select coalesce(jsonb_agg(cp7_material.transfer_header(x) order by x.physical_at desc,x.id),'[]'::jsonb)
 into rows from (select t.* from erp.material_transfers t where (s='ALL' or t.status::text=s) and (q='' or strpos(lower(t.transfer_number),lower(q))>0)
  order by t.physical_at desc,t.id limit n offset off) x;
 if chosen is not null then
  select * into h from erp.material_transfers where id=chosen;
  if not found then raise exception 'CP7_MATERIAL_TRANSFER_NOT_FOUND';end if;
  if (select count(*) from erp.material_transfer_items where transfer_id=chosen)>100 then raise exception 'CP7_MATERIAL_DOCUMENT_TOO_LARGE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_sku',m.material_sku,'material_name',m.material_name,
   'unit_code',m.unit_code,'roll_id',i.roll_id,'roll_number',r.roll_number,'qty',i.qty::text,'notes',i.notes) order by i.id),'[]'::jsonb)
  into items from erp.material_transfer_items i join erp.materials m on m.id=i.material_id left join erp.material_rolls r on r.id=i.roll_id where i.transfer_id=chosen;
  detail:=cp7_material.transfer_header(h)||jsonb_build_object('items',items);
 end if;
 return jsonb_build_object('contract_version','cp7.material-transfers.v1','read_at',statement_timestamp(),
  'capabilities',jsonb_build_object('transfer',a->'can_adjust','reverse_transfer',a->'can_reverse'),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);
end $$;
create function public.erp_cp7_get_material_transfers_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.transfers(p_query)$$;

create function cp7_material.locations(p_q text,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare total bigint;rows jsonb;
begin
 perform cp7_material.access_now();
 if p_q is null or length(p_q)>120 or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 100 then raise exception 'CP7_MATERIAL_QUERY';end if;
 select count(*) into total from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id) and (p_q='' or strpos(lower(l.location_code||' '||l.location_name),lower(p_q))>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'code',x.location_code,'name',x.location_name) order by x.location_name,x.id),'[]'::jsonb)
 into rows from (select l.* from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id) and (p_q='' or strpos(lower(l.location_code||' '||l.location_name),lower(p_q))>0)
  order by l.location_name,l.id limit p_limit offset p_offset) x;
 return jsonb_build_object('contract_version','cp7.material-locations.v1','rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,
  'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end);
end $$;
create function public.erp_cp7_get_material_locations_v1(p_q text,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.locations(p_q,p_offset,p_limit)$$;
