create or replace function cp7_stock_formula.save_settings(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.settings;cur_rev bigint;row cp7_stock_formula.settings;cfg jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 select*into prev from cp7_stock_formula.settings x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  cfg:=cp7_stock_formula.current_settings();
  if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
  return jsonb_build_object('replay',true,'settings',cfg);
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['expected_revision','service_level','window_days','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('expected_revision','service_level','window_days','reason'))
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'service_level')<>'string'or p->>'service_level'not in('0.90','0.95','0.99')
  or jsonb_typeof(p->'window_days')<>'number'or(p->>'window_days')!~'^[0-9]{1,3}$'or(p->>'window_days')::integer not between 14 and 365
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_SETTINGS_INVALID';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.settings x;
 if cur_rev<>(p->>'expected_revision')::bigint then raise exception using errcode='40001',message='CP7_FORMULA_SETTINGS_STALE';end if;
 insert into cp7_stock_formula.settings(revision,service_level,window_days,reason,actor,request_id,request_hash)
 values(cur_rev+1,(p->>'service_level')::numeric,(p->>'window_days')::integer,btrim(p->>'reason'),auth.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 return jsonb_build_object('replay',false,'settings',cp7_stock_formula.current_settings());
end $$;
