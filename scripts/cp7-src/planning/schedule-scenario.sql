-- Server-owned composition of selected calendar/yield metadata with captured
-- native physical positions. Unknown remaining work blocks shared free capacity.
create function cp7_schedule_native.source_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_supply_native.source_within(p_products)c)
 select c||jsonb_build_object('schedule',cp7_schedule_native.source_at((c->>'captured_at')::timestamptz),
  'planning_time_bucket',cp7_planning.utc(date_trunc('minute',(c->>'captured_at')::timestamptz)))from source
$$;
create function cp7_schedule_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_schedule_native.source_within(1000)
$$;

create function cp7_schedule_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 -- Retain the raw capture clock in the Original. Only usable planning time
 -- belongs in the dependency hash: a minute before a future window cannot
 -- consume capacity. Active windows, the horizon and the business day can.
 with clock as(select(c->>'captured_at')::timestamptz at),
 windows as(select cp7_demand.instant(value->'starts_at') starts_at,
  cp7_demand.instant(value->'ends_at') ends_at
  from jsonb_array_elements(coalesce(c#>'{schedule,config,windows}','[]'::jsonb))),
 frontier as(select min(greatest(w.starts_at,date_trunc('minute',clock.at))) next_at
  from clock cross join windows w where w.ends_at>clock.at)
 select encode(extensions.digest(convert_to(jsonb_build_object('native_source',cp7_supply_native.fingerprint(c),
  'schedule',c->'schedule','planning_clock',jsonb_build_object(
   'business_day',(clock.at at time zone 'Asia/Jakarta')::date,
   'next_usable_frontier',frontier.next_at,
   'horizon_expired',case when c#>'{schedule,config,through_at}'is null then null
    else cp7_demand.instant(c#>'{schedule,config,through_at}')<=clock.at end))::text,'UTF8'),'sha256'),'hex')
 from clock cross join frontier
$$;

create function cp7_schedule_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare supply jsonb;plan jsonb:=c->'schedule';cfg jsonb;wip jsonb;p jsonb;selected jsonb;step jsonb;win jsonb;
 refs jsonb;plans_refs jsonb;yield_inputs jsonb[]:='{}';work jsonb;windows jsonb;window_acc jsonb[]:='{}';capacity_windows jsonb[]:='{}';
 etas jsonb[]:='{}';rows jsonb:='[]';by_position jsonb;repeated jsonb;capacity jsonb;eta jsonb;source_state text;hash text;ready timestamptz;cursor_at timestamptz;
 through_at timestamptz;starts timestamptz;ends timestamptz;load numeric:=0;remaining_load numeric;
 minutes numeric;external_load numeric;used numeric;queue_known boolean:=true;other_load_placed boolean:=true;
 window_start timestamptz[]:='{}';window_end timestamptz[]:='{}';wi integer:=1;wj integer;need numeric;covered numeric;usable jsonb;
begin
 supply:=cp7_supply_native.build(c,q);wip:=supply->'wip';hash:=cp7_schedule_native.fingerprint(c);
 source_state:=case when plan='null'::jsonb then 'UNREVIEWED'
  when plan->>'source_hash'=cp7_supply_native.fingerprint(c)then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end;
 if wip->>'status'is distinct from 'COMPLETE'or source_state<>'SELECTED_ASSUMPTIONS'then
  return jsonb_build_object('contract_version','cp7.native-planning-scenario.v1','captured_at',c->>'captured_at',
   'source_hash',hash,'planning_time_bucket',c->'planning_time_bucket','supply_run_result',supply,
   'schedule',plan,'schedule_state',source_state,'status','UNKNOWN','wip',wip,'etas','[]'::jsonb,
   'capacity',jsonb_build_object('status','UNKNOWN','capacity_pcs',null),
   'allocation',jsonb_build_object('status','UNKNOWN','reason','AUTHORITATIVE_REVIEWED_GLOBAL_MATCHING_NOT_COMPOSED'),
   'final_gap_pcs',null,'apply_enabled',false,'production_go',false);
 end if;
 cfg:=plan->'config';ready:=(c->>'captured_at')::timestamptz;cursor_at:=ready;
 through_at:=cp7_demand.instant(cfg->'through_at');
 plans_refs:=jsonb_build_array(jsonb_build_object('kind','PLANNING_SCHEDULE','id',plan->>'plan_id','revision',plan->>'revision'));
 -- ALL positive working positions matter to the shared queue, including customer
 -- work. Ownership excludes supply, never an existing job from shared load.
 -- Missing or partial
 -- remaining work is unknown load, not a free slot for some other SKU.
 for p in select value from jsonb_array_elements(wip->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0 loop
  -- One selected row per captured position. The map is built where the
  -- per-position scan first ran; a repeated key fails as that scan did.
  if by_position is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_position,repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(cfg->'positions')
     where value->>'position_key'is not null group by 1)f;
  end if;
  if repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  selected:=by_position->(p->>'key');
  if selected is null or cp7_wip.pcs(selected->'eligible_input_pcs')<>cp7_wip.pcs(p->'remaining_pcs')then
   queue_known:=false;
  elsif exists(select 1 from jsonb_array_elements(selected->'remaining_steps')where value->'remaining_minutes'='null'::jsonb)then
   queue_known:=false;
  else
   select load+coalesce(sum(cp7_wip.pcs(value->'remaining_minutes')),0)into load
    from jsonb_array_elements(selected->'remaining_steps');
  end if;
  if p->'eligible_company_wip'='true'::jsonb and selected is not null and selected->'yield_numerator'<>'null'::jsonb then
   yield_inputs:=array_append(yield_inputs,jsonb_build_object('position_key',p->>'key',
    'eligible_input_pcs',selected->'eligible_input_pcs','numerator',selected->'yield_numerator',
    'denominator',selected->'yield_denominator','basis','ASSUMED','assumption_id',plan->>'plan_id',
    'refs',(p->'refs')||plans_refs));
  end if;
 end loop;
 wip:=cp7_wip.project_yield(wip,to_jsonb(yield_inputs));remaining_load:=load;
 for win in select value from jsonb_array_elements(cfg->'windows')order by cp7_demand.instant(value->'starts_at'),value->>'key'loop
  starts:=greatest(ready,cp7_demand.instant(win->'starts_at'));ends:=cp7_demand.instant(win->'ends_at');
  if ends<=starts then continue;end if;
  window_acc:=array_append(window_acc,jsonb_build_object('start',cp7_planning.utc(starts),'end',cp7_planning.utc(ends)));
  window_start:=array_append(window_start,starts);window_end:=array_append(window_end,ends);
  minutes:=extract(epoch from ends-starts)/60;
  if win->'other_load_minutes'='null'::jsonb then
   external_load:=null;other_load_placed:=false;
  else external_load:=cp7_demand.decimal(win->'other_load_minutes');
   if external_load>0 then other_load_placed:=false;end if;
  end if;
  used:=least(remaining_load,greatest(0,minutes-coalesce(external_load,minutes)));
  remaining_load:=remaining_load-used;
  capacity_windows:=array_append(capacity_windows,jsonb_build_object('key',win->'key',
   'starts_at',cp7_planning.utc(starts),'ends_at',cp7_planning.utc(ends),
   -- The retained decimal kernel admits twelve decimal places. Duration/60
   -- can recur; round LOAD upward so serialization never creates free time.
   'existing_load_minutes',case when queue_known and external_load is not null
    then(ceil((external_load+used)*1000000000000)/1000000000000)::numeric(42,12)::text else null end,
   'refs',plans_refs));
 end loop;
 windows:=to_jsonb(window_acc);
 if through_at<=ready then
  capacity:=jsonb_build_object('status','UNKNOWN','capacity_pcs',null,'reason','SELECTED_CALENDAR_EXPIRED');
 else
  capacity:=cp7_baseline.capacity(jsonb_build_object('contract_version','cp7.capacity-input.v1',
   'snapshot_id',wip->>'snapshot_id','scope_id','GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS',
   'work_centre_id',cfg->>'work_centre_key','from_at',cp7_planning.utc(ready),'through_at',cfg->'through_at',
   'unit_minutes',cfg->'unit_minutes','unit_time_basis',case when cfg->'unit_minutes'='null'::jsonb then 'UNKNOWN'else 'SELECTED_ASSUMPTION'end,
   'windows',to_jsonb(capacity_windows),'refs',plans_refs));
  if remaining_load>0 then capacity:=capacity||jsonb_build_object('status','UNKNOWN','capacity_pcs',null,
   'reason','CAPTURED_REMAINING_WORK_EXCEEDS_SELECTED_CALENDAR');end if;
 end if;
 for p in select value from jsonb_array_elements(wip->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0 order by value->>'key'loop
  -- One selected row per captured position. The map is built where the
  -- per-position scan first ran; a repeated key fails as that scan did.
  if by_position is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_position,repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(cfg->'positions')
     where value->>'position_key'is not null group by 1)f;
  end if;
  if repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  selected:=by_position->(p->>'key');
  refs:=(p->'refs')||plans_refs;
  if not queue_known or not other_load_placed or through_at<=ready then
   eta:=jsonb_build_object('status','UNKNOWN','eta',null,'on_time',null,'reason',
    case when not queue_known then 'SHARED_NATIVE_REMAINING_QUEUE_NOT_FULLY_REVIEWED'
     when not other_load_placed then 'OTHER_LOAD_DATED_PLACEMENT_NOT_SELECTED'else 'SELECTED_CALENDAR_EXPIRED'end);
  else
   -- The ETA kernel skips every window that ends at or before the cursor and
   -- every window after the minutes run out, and these windows were built
   -- above and passed the capacity checks. So it is handed the usable part:
   -- from the first window ending after the cursor through the window that
   -- covers this position's minutes with a minute to spare, plus one. A
   -- calendar over the kernel's 1000-window limit goes whole, refused as before.
   if cardinality(window_acc)>1000 then usable:=windows;
   else
    while wi<=cardinality(window_end)and window_end[wi]<=cursor_at loop wi:=wi+1;end loop;
    select coalesce(sum(cp7_wip.pcs(value->'remaining_minutes')),0)into need from jsonb_array_elements(selected->'remaining_steps');
    wj:=wi;covered:=0;
    while wj<=cardinality(window_end)and covered<=need+1 loop
     covered:=covered+extract(epoch from window_end[wj]-greatest(window_start[wj],cursor_at))/60;wj:=wj+1;
    end loop;
    usable:=to_jsonb(window_acc[wi:wj]);
   end if;
   work:='[]';
   for step in select value from jsonb_array_elements(selected->'remaining_steps')with ordinality order by ordinality loop
    work:=work||jsonb_build_array(jsonb_build_object('stage',step->'stage','remaining_minutes',step->'remaining_minutes',
     'basis','ASSUMED','assumption_id',plan->>'plan_id','calendar_version',(plan->>'plan_id')||':'||(plan->>'revision'),
     'windows',usable,'refs',refs));
   end loop;
   eta:=cp7_wip.remaining_eta(cursor_at,through_at,work);
   if eta->>'status'in('KNOWN','CONDITIONAL')then cursor_at:=(eta->>'eta')::timestamptz;
   else queue_known:=false;end if;
  end if;
  etas:=array_append(etas,jsonb_build_object('position_key',p->'key','target_key',selected->'target_key',
   'result',eta,'refs',refs));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-planning-scenario.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'planning_time_bucket',c->'planning_time_bucket','supply_run_result',supply,
  'schedule',plan,'schedule_state',source_state,'status','SCENARIO','wip',wip,'etas',to_jsonb(etas),'capacity',capacity,
  'resource_basis','SINGLE_HOMOGENEOUS_SELECTED_CENTRE_ALL_CAPTURED_REMAINING_WORK_BEFORE_NEW_STARTS',
  'queue_order','STABLE_NATIVE_POSITION_KEY_SELECTED_SCENARIO_NOT_FACTORY_OPTIMIZER',
  'allocation',jsonb_build_object('status','UNKNOWN','reason','AUTHORITATIVE_REVIEWED_GLOBAL_MATCHING_NOT_COMPOSED'),
  'final_gap_pcs',null,'apply_enabled',false,'production_go',false);
end $$;

create table cp7_schedule_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_schedule_native.runs owner to cp7_capture;
alter table cp7_schedule_native.runs enable row level security;
create policy cp7_schedule_run_no_access on cp7_schedule_native.runs for all to public using(false)with check(false);
revoke all on cp7_schedule_native.runs from public,anon,authenticated,service_role;
create trigger immutable_schedule_run before update or delete on cp7_schedule_native.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_schedule_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_schedule_native.runs%rowtype;c jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_schedule_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_RUN_UNAVAILABLE';end if;
 c:=cp7_schedule_native.source();outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,
  'source_state',case when cp7_schedule_native.fingerprint(c)=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_schedule_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_schedule_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_SCHEDULE_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:CAPTURE:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select *into r from cp7_schedule_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_SCHEDULE_REQUEST_CHANGED';end if;return cp7_schedule_native.serve(r.id);
 end if;
 with source as materialized(select cp7_schedule_native.source()c),
 calculated as materialized(select c,cp7_schedule_native.build(c,q)result from source)
 insert into cp7_schedule_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'
 from calculated returning *into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return cp7_schedule_native.serve(r.id);
end $$;

alter function cp7_schedule_native.source_within(integer)owner to cp7_capture;
alter function cp7_schedule_native.source()owner to cp7_capture;
alter function cp7_schedule_native.fingerprint(jsonb)owner to cp7_capture;
alter function cp7_schedule_native.build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_schedule_native.serve(uuid)owner to cp7_capture;
alter function cp7_schedule_native.capture(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_schedule_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_planning_scenario_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_schedule_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_planning_scenario_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_schedule_native.serve(p_run)$$;
alter function public.erp_cp7_capture_planning_scenario_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_planning_scenario_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_planning_scenario_v1(jsonb,uuid),public.erp_cp7_read_planning_scenario_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_planning_scenario_v1(jsonb,uuid),public.erp_cp7_read_planning_scenario_v1(uuid)to authenticated;
