create or replace function cp7_stock_formula.save_material(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.material_settings;mat record;cur_rev integer;row cp7_stock_formula.material_settings;lead numeric;manual numeric;
 moq numeric;usage_month numeric;buffer numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['material_id','expected_revision','lead_days','manual_point','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('material_id','expected_revision','lead_days','manual_point','reason','moq',
   'usage_month_qty','buffer_days'))
  or jsonb_typeof(p->'material_id')<>'string'or(p->>'material_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'lead_days')not in('string','null')or coalesce(p->>'lead_days','1')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'
  or jsonb_typeof(p->'manual_point')not in('string','null')or coalesce(p->>'manual_point','0')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'
  or(p?'moq'and(jsonb_typeof(p->'moq')not in('string','null')or coalesce(p->>'moq','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'usage_month_qty'and(jsonb_typeof(p->'usage_month_qty')not in('string','null')or coalesce(p->>'usage_month_qty','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'buffer_days'and(jsonb_typeof(p->'buffer_days')not in('string','null')or coalesce(p->>'buffer_days','0')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'))
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 select m.id,m.material_type::text material_type into mat from erp.materials m
  where m.id=(p->>'material_id')::uuid and m.is_active and m.material_type in('FABRIC','ACCESSORY');
 if mat.id is null then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 a:=cp7_stock_formula.material_access_now(mat.material_type,true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 lead:=(p->>'lead_days')::numeric;manual:=(p->>'manual_point')::numeric;
 moq:=(p->>'moq')::numeric;usage_month:=(p->>'usage_month_qty')::numeric;buffer:=(p->>'buffer_days')::numeric;
 if(lead is not null and(lead<=0 or lead>365))or(moq is not null and moq<=0)or(usage_month is not null and usage_month<=0)
  or(buffer is not null and buffer>365)
  or(mat.material_type='FABRIC'and(manual is not null or moq is not null or usage_month is not null or buffer is not null))then
  raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.material_settings x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'material_id',prev.material_id,'revision',prev.revision);
 end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.material_settings x where x.material_id=mat.id;
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MATERIAL_STALE';end if;
 insert into cp7_stock_formula.material_settings(material_id,revision,lead_days,manual_point,moq,usage_month_qty,buffer_days,reason,actor,request_id,request_hash)
 values(mat.id,cur_rev+1,lead,manual,moq,usage_month,buffer,btrim(p->>'reason'),auth.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'material_id',row.material_id,'revision',row.revision,
  'evaluation',(select to_jsonb(e)from cp7_stock_formula.material_evaluations e where e.material_id=mat.id));
end $$;
