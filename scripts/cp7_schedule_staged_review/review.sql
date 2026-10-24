create schema cp7_schedule_staged_review authorization cp7_capture;
revoke all on schema cp7_schedule_staged_review from public,anon,authenticated,service_role;
create function cp7_schedule_staged_review.current_source()returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();c jsonb;
begin
 c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 if jsonb_typeof(c#>'{facts,products}')is distinct from'array'
  or jsonb_array_length(c#>'{facts,products}')>(b->>'job_targets')::integer then
  raise exception 'CP7_SCHEDULE_STAGED_PRODUCT_SCOPE_LIMIT';
 end if;
 return c;
end;
$$;
create function cp7_schedule_staged_review.workspace(p_source_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r record;c jsonb;hash text;plan jsonb;outcome jsonb;
 p jsonb;bound_id text;bound_root text;model text;choices jsonb;requirements jsonb:='[]';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.run_id id,j.id job_id,j.state job_state,j.reference facts,j.captured_at,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash,
  jsonb_build_object('wip',cp7_wip.normalize_production(j.reference->'production_sources'))result
 into r from cp7_analysis_stage.jobs j where j.request_id=p_source_request and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if r.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(r.job_id);
 c:=cp7_schedule_staged_review.current_source();hash:=cp7_supply_native.fingerprint(c);plan:=cp7_schedule_native.source_at((c->>'captured_at')::timestamptz);
 -- Form guidance belongs to the immutable source being reviewed. A fresh
 -- source check must not silently rebind quantities or an unfinished form.
 for p in select value from jsonb_array_elements(r.result->'wip'->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0
  order by value->>'key'loop
  bound_id:=case split_part(p->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(p->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(p->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(r.facts->>'captured_at')::timestamptz;
  model:=cp7_schedule_native.position_model(r.facts,p);
  select coalesce(jsonb_agg(jsonb_build_object('target_key',(x->>'root_id')||':'||(x->>'size_id'),
   'product_version_id',x->'id','sku',x->'sku','product_name',x->'product_name')order by x->>'root_id'),'[]')into choices
   from jsonb_array_elements(r.facts->'facts'->'products')x
   where p->'eligible_company_wip'='true'::jsonb and x->>'size_id'=p->>'size_id'and x->>'model_id'=model
    and(bound_root is null or x->>'root_id'=bound_root);
  requirements:=requirements||jsonb_build_array(jsonb_build_object('position_key',p->'key','pool_key',p->'pool_key',
   'stage',p->'stage','size_id',p->'size_id','ownership',p->'ownership','eligible_company_wip',p->'eligible_company_wip',
   'remaining_pcs',p->'remaining_pcs','remaining_route',cp7_schedule_native.route(p->>'stage'),'target_candidates',choices));
 end loop;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged.v1','source_run',r.id,'source_request_id',p_source_request,'analysis_state',r.job_state,'current_source_hash',hash,
  'source_hash',r.dependency_hash,'captured_at',cp7_planning.utc(r.captured_at),'staged_review_contract','cp7.schedule-staged-review.v1','analysis_source_hash',r.analysis_source_hash,'history_capture_state',r.facts->'status','production_capture_state',r.result#>'{wip,status}','position_requirements',requirements,
  'source_state',case when hash=r.dependency_hash and cp7_analysis_native.fingerprint(c)=r.analysis_source_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'plan',plan,'revision',coalesce(plan->>'revision','0'),
  'plan_state',case when plan='null'::jsonb then 'UNREVIEWED'when plan->>'source_hash'=hash then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end,
  'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;
create function cp7_schedule_staged_review.save(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_schedule_native.commands%rowtype;run record;
 p cp7_schedule_native.plans%rowtype;c jsonb;wip jsonb;hash text;revision bigint;expected bigint;reason text;config jsonb;outcome jsonb;
 selected jsonb;position jsonb;bound_id text;bound_root text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);if p_request is null then raise exception 'CP7_SCHEDULE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['source_run','source_hash','expected_revision','config','reason','staged_review_contract']);
 if p_payload->>'staged_review_contract'is distinct from'cp7.schedule-staged-review.v1'then raise exception 'CP7_SCHEDULE_STAGED_CONTRACT';end if;
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
 select j.run_id id,j.id job_id,j.state job_state,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash
 into run from cp7_analysis_stage.jobs j where j.run_id=(p_payload->>'source_run')::uuid
  and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if run.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(run.job_id);
 c:=cp7_schedule_staged_review.current_source();hash:=cp7_supply_native.fingerprint(c);
 if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'
  or cp7_analysis_native.fingerprint(c)<>run.analysis_source_hash then raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
 wip:=cp7_wip.normalize_production(c->'production_sources');config:=cp7_schedule_native.validate(p_payload->'config',c,wip);
 -- A selected destination is metadata, never authority to move a physically
 -- bound opening/non-PO source to a different product root with the same model.
 for selected in select value from jsonb_array_elements(config->'positions')where value->'target_key'<>'null'::jsonb loop
  position:=(select value from jsonb_array_elements(wip->'positions')where value->>'key'=selected->>'position_key');
  bound_id:=case split_part(position->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(position->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(position->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(c->>'captured_at')::timestamptz;
  if bound_root is not null and selected->>'target_key'<>bound_root||':'||(position->>'size_id')then
   raise exception 'CP7_SCHEDULE_NATIVE_TARGET_BOUND';end if;
 end loop;
 reason:=btrim(p_payload->>'reason');if jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null or length(reason)not between 1 and 1000 then
  raise exception 'CP7_SCHEDULE_REASON';end if;
 insert into cp7_schedule_native.plans(revision,source_run,source_hash,config,reason,actor,request_id)
 values(revision+1,run.id,hash,config,reason,(a->>'actor')::uuid,p_request)returning *into p;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged-outcome.v1','plan_id',p.id,'revision',p.revision::text,
  'source_hash',hash,'request_id',p_request,'quality','SELECTED_ASSUMPTIONS','staged_review_contract','cp7.schedule-staged-review.v1','source_run',run.id,'production_go',false);
 insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if cp7_supply_native.fingerprint(cp7_schedule_staged_review.current_source())<>hash then
  raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';
 end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;
alter function cp7_schedule_staged_review.current_source() owner to cp7_capture;
revoke all on function cp7_schedule_staged_review.current_source() from public,anon,authenticated,service_role;
alter function cp7_schedule_staged_review.workspace(uuid) owner to cp7_capture;
revoke all on function cp7_schedule_staged_review.workspace(uuid) from public,anon,authenticated,service_role;
alter function cp7_schedule_staged_review.save(jsonb,uuid) owner to cp7_capture;
revoke all on function cp7_schedule_staged_review.save(jsonb,uuid) from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_staged_production_schedule_v1(p_source_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_schedule_staged_review.workspace(p_source_request)$$;
alter function public.erp_cp7_get_staged_production_schedule_v1(uuid) owner to cp7_capture;
revoke all on function public.erp_cp7_get_staged_production_schedule_v1(uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_staged_production_schedule_v1(uuid) to authenticated;
create function public.erp_cp7_save_staged_production_schedule_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_schedule_staged_review.save(p_payload,p_request)$$;
alter function public.erp_cp7_save_staged_production_schedule_v1(jsonb,uuid) owner to cp7_capture;
revoke all on function public.erp_cp7_save_staged_production_schedule_v1(jsonb,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_save_staged_production_schedule_v1(jsonb,uuid) to authenticated;
revoke create on schema public from cp7_capture;
