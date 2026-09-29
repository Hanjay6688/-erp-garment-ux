create function cp7_material.count_header(h erp.material_adjustments) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'number',h.adjustment_number,'location_id',h.location_id,'location_name',(select location_name from erp.locations where id=h.location_id),
  'physical_at',h.physical_at,'reason_code',h.reason_code,'status',h.status,'row_version',h.row_version::text,'notes',h.notes,
  'managed_count',exists(select 1 from cp7_material.count_documents where adjustment_id=h.id),
  'line_count',(select count(*)::text from erp.material_adjustment_items where adjustment_id=h.id))
$$;
create function cp7_material.count_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;n integer;off integer;chosen uuid;total bigint;rows jsonb;detail jsonb:=null;h erp.material_adjustments;items jsonb;proof jsonb;editable jsonb:=null;
begin
 a:=cp7_material.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_COUNT_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);chosen:=(p_query->>'adjustment_id')::uuid;
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_COUNT_QUERY';end if;
 select count(*) into total from erp.material_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0;
 select coalesce(jsonb_agg(cp7_material.count_header(x) order by x.physical_at desc,x.id),'[]') into rows
 from (select * from erp.material_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0 order by physical_at desc,id limit n offset off) x;
 if chosen is not null then
  select * into h from erp.material_adjustments where id=chosen;
  if not found then raise exception 'CP7_COUNT_NOT_FOUND';end if;
  if (select count(*) from erp.material_adjustment_items where adjustment_id=chosen)>100 then raise exception 'CP7_COUNT_DOCUMENT_TOO_LARGE';end if;
  select input into proof from cp7_material.count_documents where adjustment_id=chosen;
  select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
   'roll_id',i.roll_id,'roll_number',r.roll_number,'qty_signed',i.qty_signed::text,'notes',i.notes,
   'physical_qty',(select e->>'physical_qty' from jsonb_array_elements(proof->'items') e where (e->>'material_id')::uuid=i.material_id and (e->>'roll_id')::uuid is not distinct from i.roll_id))
   ||case when a->'can_value'='true'::jsonb then jsonb_build_object('valuation',jsonb_build_object('input_unit_cost',i.input_unit_cost::text,
     'restated_value',(select round(sum(s.qty_signed*s.unit_cost_snapshot),6)::text from erp.material_stock_movements s where s.source_type='MATERIAL_ADJUSTMENT_ITEM' and s.source_id=i.id and s.reversal_of_id is null),
     'basis','CURRENT_RESTATED_DOCUMENT_NOT_STOCK')) else '{}'::jsonb end order by i.id),'[]')
   into items from erp.material_adjustment_items i join erp.materials m on m.id=i.material_id left join erp.material_rolls r on r.id=i.roll_id where i.adjustment_id=chosen;
  -- The current browser editor preserves one complete physical-count input.
  -- Larger/imported source bindings remain readable; never drop hidden inputs.
  if h.status='DRAFT' and jsonb_array_length(proof->'items')=1 and jsonb_array_length(items)=1
   and (a->'can_value'='true'::jsonb or proof->'items'->0->>'input_unit_cost' is null)
   and cp7_material.count_signature(chosen)=(select source_signature from cp7_material.count_documents where adjustment_id=chosen) then
   editable:=jsonb_build_object('physical_qty',proof->'items'->0->>'physical_qty')
    ||case when a->'can_value'='true'::jsonb then jsonb_build_object('input_unit_cost',proof->'items'->0->>'input_unit_cost') else '{}'::jsonb end;
  end if;
  detail:=cp7_material.count_header(h)||jsonb_build_object('items',items,'edit',editable);
 end if;
 return jsonb_build_object('contract_version','cp7.material-counts.v1','read_at',statement_timestamp(),'financial_captured',a->'can_value',
  'capabilities',jsonb_build_object('adjust',a->'can_adjust','reverse',a->'can_reverse'),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);
end $$;
create function public.erp_cp7_get_material_counts_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.count_workspace(p_query)$$;
