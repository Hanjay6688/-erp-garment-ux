-- Versioned, explicitly selected working-calendar/yield assumptions. These are
-- planning metadata bound to a real global source; never native production facts.
create schema cp7_schedule_native authorization cp7_capture;
revoke all on schema cp7_schedule_native from public,anon,authenticated,service_role;
create table cp7_schedule_native.plans(
 id uuid primary key default gen_random_uuid(),revision bigint not null unique check(revision>0),
 source_run uuid not null,source_hash text not null,config jsonb not null,reason text not null,
 actor uuid not null,request_id uuid not null,recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_schedule_native.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 primary key(actor,request_id)
);
alter table cp7_schedule_native.plans owner to cp7_capture;
alter table cp7_schedule_native.commands owner to cp7_capture;
alter table cp7_schedule_native.plans enable row level security;
alter table cp7_schedule_native.commands enable row level security;
create policy cp7_schedule_no_access on cp7_schedule_native.plans for all to public using(false)with check(false);
create policy cp7_schedule_command_no_access on cp7_schedule_native.commands for all to public using(false)with check(false);
revoke all on cp7_schedule_native.plans,cp7_schedule_native.commands from public,anon,authenticated,service_role;
create trigger immutable_schedule before update or delete on cp7_schedule_native.plans
 for each row execute function cp7_private.immutable_run();
create trigger immutable_schedule_command before update or delete on cp7_schedule_native.commands
 for each row execute function cp7_private.immutable_run();

create function cp7_schedule_native.access_now(writing boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 a:=cp7_private.access_now();
 if writing and not erp.has_permission('master.product.manage')then
  raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_schedule_native.route(stage text)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case stage when 'CUT_UNASSIGNED'then '["SEWING","LAUNDRY","QC"]'::jsonb
  when 'SEWING_UNRESOLVED'then '["SEWING","LAUNDRY","QC"]'::jsonb
  when 'SEWING_ACTIVE'then '["SEWING","LAUNDRY","QC"]'::jsonb
  when 'LAUNDRY_OUTSTANDING'then '["LAUNDRY","QC"]'::jsonb
  when 'AWAIT_QC'then '["QC"]'::jsonb
  when 'REWORK'then '["REWORK","QC"]'::jsonb
  when 'REWASH'then '["REWASH","QC"]'::jsonb else null end
$$;

create function cp7_schedule_native.position_model(c jsonb,p jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case split_part(p->>'pool_key',':',1)
  when 'CUT'then(select x->>'model_id'from jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'groups')x
   where x->>'id'=split_part(p->>'pool_key',':',2))
  when 'OPEN'then(select x->>'model_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
   where x->>'id'=split_part(p->>'pool_key',':',2))
  when 'NONPO'then(select product->>'model_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
   join jsonb_array_elements(c->'facts'->'products')product on product->>'id'=x->>'product_id'
   where x->>'id'=split_part(p->>'pool_key',':',2))else null end
$$;

create function cp7_schedule_native.validate(config jsonb,c jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare hi timestamptz;lo timestamptz:=(c->>'captured_at')::timestamptz;previous timestamptz;
 win jsonb;selected jsonb;p jsonb;target jsonb;step jsonb;seen jsonb:='{}';windows_seen jsonb:='{}';
 stages jsonb;qty numeric;num numeric;den numeric;k text;model text;starts timestamptz;ends timestamptz;
begin
 perform cp7_wip.fields(config,array['basis','resource_scope','work_centre_key','through_at','unit_minutes','windows','positions']);
 if config->>'basis'is distinct from 'SELECTED_ASSUMPTIONS'
  or config->>'resource_scope'is distinct from 'SINGLE_HOMOGENEOUS_SELECTED_CENTRE'
  or wip->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_SCHEDULE_SOURCE_OR_BASIS';end if;
 perform cp7_wip.key(config->'work_centre_key');hi:=cp7_demand.instant(config->'through_at');
 if hi<=lo or hi>lo+interval '3660 days'then raise exception 'CP7_SCHEDULE_HORIZON';end if;
 if config->'unit_minutes'<>'null'::jsonb and cp7_demand.decimal(config->'unit_minutes')=0 then
  raise exception 'CP7_SCHEDULE_UNIT_TIME';end if;
 perform cp7_demand.items(config->'windows',1000);perform cp7_demand.items(config->'positions',1000);
 for win in select value from jsonb_array_elements(config->'windows')order by cp7_demand.instant(value->'starts_at'),value->>'key'loop
  perform cp7_wip.fields(win,array['key','starts_at','ends_at','other_load_minutes']);k:=cp7_wip.key(win->'key');
  starts:=cp7_demand.instant(win->'starts_at');ends:=cp7_demand.instant(win->'ends_at');
  if windows_seen?k or starts<lo or ends>hi or starts>=ends or starts<previous then
   raise exception 'CP7_SCHEDULE_WINDOW';end if;
  windows_seen:=windows_seen||jsonb_build_object(k,true);previous:=ends;
  if win->'other_load_minutes'<>'null'::jsonb then perform cp7_demand.decimal(win->'other_load_minutes');end if;
 end loop;
 for selected in select value from jsonb_array_elements(config->'positions')loop
  perform cp7_wip.fields(selected,array['position_key','target_key','eligible_input_pcs','yield_numerator','yield_denominator','remaining_steps']);
  k:=cp7_wip.key(selected->'position_key');
  if seen?k then raise exception 'CP7_SCHEDULE_DUPLICATE_POSITION';end if;seen:=seen||jsonb_build_object(k,true);
  p:=(select value from jsonb_array_elements(wip->'positions')where value->>'key'=k);
  if p is null or cp7_schedule_native.route(p->>'stage')is null or cp7_wip.pcs(p->'remaining_pcs')=0 then
   raise exception 'CP7_SCHEDULE_NATIVE_POSITION';end if;
  -- Customer work consumes the selected shared centre but can never become
  -- company supply or receive a company target/yield assumption.
  if p->'eligible_company_wip'<>'true'::jsonb and(selected->'target_key'<>'null'::jsonb
   or selected->'yield_numerator'<>'null'::jsonb or selected->'yield_denominator'<>'null'::jsonb)then
   raise exception 'CP7_SCHEDULE_CUSTOMER_WORK_ONLY';end if;
  qty:=cp7_wip.pcs(selected->'eligible_input_pcs');
  if qty>cp7_wip.pcs(p->'remaining_pcs')then raise exception 'CP7_SCHEDULE_NATIVE_QUANTITY';end if;
  if(selected->'yield_numerator'='null'::jsonb)is distinct from(selected->'yield_denominator'='null'::jsonb)then
   raise exception 'CP7_SCHEDULE_YIELD';end if;
  if selected->'yield_numerator'<>'null'::jsonb then
   num:=cp7_wip.pcs(selected->'yield_numerator');den:=cp7_wip.pcs(selected->'yield_denominator');
   if den=0 or num>den then raise exception 'CP7_SCHEDULE_YIELD';end if;
  end if;
  if selected->'target_key'<>'null'::jsonb then
   perform cp7_wip.key(selected->'target_key');
   target:=(select value from jsonb_array_elements(c->'facts'->'products')
    where(value->>'root_id')||':'||(value->>'size_id')=selected->>'target_key');
   model:=cp7_schedule_native.position_model(c,p);
   if target is null or target->>'size_id'<>p->>'size_id'or model is null or model<>target->>'model_id'then
    raise exception 'CP7_SCHEDULE_NATIVE_TARGET_MODEL_SIZE';end if;
  end if;
  stages:=cp7_schedule_native.route(p->>'stage');
  if stages is null or jsonb_typeof(selected->'remaining_steps')is distinct from 'array'
   or jsonb_array_length(selected->'remaining_steps')<>jsonb_array_length(stages)then
   raise exception 'CP7_SCHEDULE_REMAINING_ROUTE';end if;
  for step in select value from jsonb_array_elements(selected->'remaining_steps')with ordinality order by ordinality loop
   perform cp7_wip.fields(step,array['stage','remaining_minutes']);
   if step->'remaining_minutes'<>'null'::jsonb then perform cp7_wip.pcs(step->'remaining_minutes');end if;
  end loop;
  if(select jsonb_agg(value->'stage'order by ordinality)from jsonb_array_elements(selected->'remaining_steps')with ordinality)
   is distinct from stages then raise exception 'CP7_SCHEDULE_REMAINING_ROUTE';end if;
 end loop;
 return config;
end $$;

create function cp7_schedule_native.source_at(p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce((select jsonb_build_object('plan_id',id,'revision',revision::text,'source_run',source_run,
  'source_hash',source_hash,'config',config,'recorded_at',cp7_planning.utc(recorded_at))
  from cp7_schedule_native.plans where recorded_at<=p_at order by revision desc limit 1),'null'::jsonb)
$$;

create function cp7_schedule_native.workspace(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_supply_native.runs%rowtype;c jsonb;hash text;plan jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_supply_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_SUPPLY_RUN_UNAVAILABLE';end if;
 c:=cp7_supply_native.source();hash:=cp7_supply_native.fingerprint(c);plan:=cp7_schedule_native.source_at((c->>'captured_at')::timestamptz);
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule.v1','source_run',p_run,'current_source_hash',hash,
  'source_state',case when hash=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'plan',plan,'revision',coalesce(plan->>'revision','0'),
  'plan_state',case when plan='null'::jsonb then 'UNREVIEWED'when plan->>'source_hash'=hash then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end,
  'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_schedule_native.save(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_schedule_native.commands%rowtype;run cp7_supply_native.runs%rowtype;
 p cp7_schedule_native.plans%rowtype;c jsonb;wip jsonb;hash text;revision bigint;expected bigint;reason text;config jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);if p_request is null then raise exception 'CP7_SCHEDULE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['source_run','source_hash','expected_revision','config','reason']);
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select *into old from cp7_schedule_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_SCHEDULE_REQUEST_CHANGED';end if;return old.result;
 end if;
 if jsonb_typeof(p_payload->'expected_revision')is distinct from 'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'
  or jsonb_typeof(p_payload->'source_hash')is distinct from 'string'or p_payload->>'source_hash'!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_SCHEDULE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:GLOBAL',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into revision from cp7_schedule_native.plans x;
 if expected<>revision then raise exception 'CP7_SCHEDULE_REVISION_CHANGED';end if;
 select *into run from cp7_supply_native.runs where id=(p_payload->>'source_run')::uuid and actor=(a->>'actor')::uuid;
 if run.id is null then raise exception using errcode='42501',message='CP7_SUPPLY_RUN_UNAVAILABLE';end if;
 c:=cp7_supply_native.source();hash:=cp7_supply_native.fingerprint(c);
 if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'then raise exception 'CP7_SCHEDULE_SOURCE_CHANGED';end if;
 wip:=cp7_wip.normalize_production(c->'production_sources');config:=cp7_schedule_native.validate(p_payload->'config',c,wip);
 reason:=btrim(p_payload->>'reason');if jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null or length(reason)not between 1 and 1000 then
  raise exception 'CP7_SCHEDULE_REASON';end if;
 insert into cp7_schedule_native.plans(revision,source_run,source_hash,config,reason,actor,request_id)
 values(revision+1,run.id,hash,config,reason,(a->>'actor')::uuid,p_request)returning *into p;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-outcome.v1','plan_id',p.id,'revision',p.revision::text,
  'source_hash',hash,'request_id',p_request,'quality','SELECTED_ASSUMPTIONS','production_go',false);
 insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

alter function cp7_schedule_native.access_now(boolean)owner to cp7_capture;
alter function cp7_schedule_native.route(text)owner to cp7_capture;
alter function cp7_schedule_native.position_model(jsonb,jsonb)owner to cp7_capture;
alter function cp7_schedule_native.validate(jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_schedule_native.source_at(timestamptz)owner to cp7_capture;
alter function cp7_schedule_native.workspace(uuid)owner to cp7_capture;
alter function cp7_schedule_native.save(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_schedule_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_production_schedule_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_schedule_native.workspace(p_run)$$;
create function public.erp_cp7_save_production_schedule_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_schedule_native.save(p_payload,p_request)$$;
alter function public.erp_cp7_get_production_schedule_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_save_production_schedule_v1(jsonb,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_get_production_schedule_v1(uuid),public.erp_cp7_save_production_schedule_v1(jsonb,uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_production_schedule_v1(uuid),public.erp_cp7_save_production_schedule_v1(jsonb,uuid)to authenticated;
