-- Read the active operator through the same private helpers as WIP and purchasing.
do $planner_identity$
declare
    item_ record;
    r_ name;
    f_ record;
    accessor_ record;
    changed_ text;
    roles_ constant name[]:=array['cp7_capture','cp7_plan_writer','cp7_policy']::name[];
    memberships_ jsonb;
    owners_ jsonb;
begin
    if session_user <> 'postgres' or current_user <> 'postgres' or current_setting('is_superuser') <> 'off' then
        raise exception 'Expected the managed Enteng Uji installer';
    end if;
    foreach r_ in array roles_ loop
        if pg_has_role('postgres',r_,'SET') or pg_has_role('postgres',r_,'USAGE') or
            not exists(select from pg_roles where rolname=r_ and not (rolcanlogin or rolsuper or rolcreaterole or rolcreatedb) and rolbypassrls)
            or exists(select from unnest(array['anon','authenticated','service_role']) a where pg_has_role(a,r_,'SET')) then
            raise exception 'Expected a private Planner role';
        end if;
    end loop;
    for accessor_ in select * from (values
        ('uid','uuid','9ab5ea099e74ec09e83b1505c51a3647791195aed7c742dcc3f257dfc7d2f300'),
        ('jwt','jsonb','fed2a8ac0349ffaba807c1b574698bfb1348825b8ef5163ad72d8408386f5e3e')
    ) v(method,returns,pin) loop
        if not exists(select from pg_proc p where p.oid=to_regprocedure('cp7_request_context.'||accessor_.method||'()')
            and p.proowner='postgres'::regrole and not p.prosecdef and p.provolatile='s'
            and p.pronargs=0 and p.prorettype::regtype::text=accessor_.returns and p.proconfig=array['search_path=""']::text[]
            and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=accessor_.pin
            and not exists(select from unnest(array['anon','authenticated','service_role']) a
               where has_schema_privilege(a,'cp7_request_context','USAGE') or has_function_privilege(a,p.oid,'EXECUTE'))) then
            raise exception 'Unexpected operator identity reader';
        end if;
    end loop;
    select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) into memberships_ from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_);
    select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) into owners_ from pg_namespace
        where nspname=any(array['cp7_cutting_yield','cp7_plan_native','cp7_profile','cp7_yield_policy']);
    grant cp7_capture,cp7_plan_writer,cp7_policy to postgres with inherit false, set true granted by postgres;
    grant usage on schema cp7_request_context to cp7_capture,cp7_plan_writer,cp7_policy;
    grant execute on function cp7_request_context.uid() to cp7_capture,cp7_plan_writer,cp7_policy;
    grant execute on function cp7_request_context.jwt() to cp7_plan_writer;
    for item_ in select * from (values
      ('cp7_cutting_yield.capture(jsonb,uuid)','cp7_capture','cp7_capture',1,'393cee71a8608272db424722a08997e748ff57edb6dd49dc1f7e39cf45e1458b'),
      ('cp7_plan_native.access_now(text)','cp7_plan_writer','cp7_plan_writer',3,'02d5ea663edcb58f095efe6d040dd4b0238d163dc8ec87e8df65a5063e41ad43'),
      ('cp7_profile.apply(jsonb,uuid)','cp7_policy','cp7_policy',4,'2f7f79238f20621615e064b846b5d76799252ba92cbb7a19b888a1bac688dda9'),
      ('cp7_yield_policy.apply(jsonb,uuid)','cp7_policy','cp7_policy',4,'a6dc7ae026feafdab2cd252d5b315050cb9da4c25fb5d38a2a0776f0dc5e6dbd')
    ) v(signature,owner_role,schema_owner,calls,pin) loop
        select p.oid,p.prosrc body,to_jsonb(p)-'prosrc' metadata,pg_get_functiondef(p.oid) ddl,
            n.nspname schema_name,has_schema_privilege(p.proowner,n.oid,'CREATE') can_create into strict f_
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where p.oid=to_regprocedure(item_.signature) and pg_get_userbyid(p.proowner)=item_.owner_role
              and pg_get_userbyid(n.nspowner)=item_.schema_owner and not p.prosecdef
              and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=item_.pin;
        if regexp_count(f_.body,'\mauth\.(uid|jwt)\(\)',1,'i')<>item_.calls or position('cp7_request_context.' in f_.body)>0
            or exists(select from unnest(array['anon','authenticated','service_role']) a
              where has_schema_privilege(a,f_.schema_name,'USAGE') and has_function_privilege(a,f_.oid,'EXECUTE')) then
            raise exception 'Planner operator route changed for %',item_.signature;
        end if;
        changed_:=regexp_replace(f_.body,'\mauth\.(uid|jwt)\(\)','cp7_request_context.\1()','gi');
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('grant create on schema %I to %I',f_.schema_name,item_.owner_role);
        end if;
        execute format('set local role %I',item_.owner_role);
        execute replace(f_.ddl,f_.body,changed_);
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('revoke create on schema %I from %I',f_.schema_name,item_.owner_role);
        end if;
        execute 'reset role';
        if not exists(select from pg_proc p where p.oid=f_.oid and p.prosrc=changed_ and to_jsonb(p)-'prosrc'=f_.metadata) then
            raise exception 'Planner operator routine metadata changed';
        end if;
    end loop;
    revoke cp7_capture,cp7_plan_writer,cp7_policy from postgres granted by postgres restrict;
    if memberships_ is distinct from (select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_))
       or owners_ is distinct from (select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) from pg_namespace
        where nspname=any(array['cp7_cutting_yield','cp7_plan_native','cp7_profile','cp7_yield_policy'])) then
        raise exception 'Planner operator release changed an existing schema or left installer rights open';
    end if;
end $planner_identity$;
do $planning_admission$ begin
 if to_regnamespace('cp7_schedule_staged_review') is not null or
    pg_has_role('postgres','cp7_capture','SET') or pg_has_role('postgres','cp7_capture','USAGE') or
    has_schema_privilege('cp7_capture','public','CREATE') then
    raise exception 'Unexpected Planner release authority'; end if;
 end $planning_admission$;
grant cp7_capture to postgres with inherit false,set true granted by postgres;
create schema cp7_schedule_staged_review authorization cp7_capture;
set local role cp7_capture;
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

reset role;
grant create on schema public to cp7_capture;
set local role cp7_capture;

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

reset role;
revoke create on schema public from cp7_capture;
revoke cp7_capture from postgres granted by postgres restrict;
do $planning_closed$ begin
 if pg_has_role('postgres','cp7_capture','SET') or pg_has_role('postgres','cp7_capture','USAGE') or
    has_schema_privilege('cp7_capture','public','CREATE') then
    raise exception 'Temporary Planner installer rights remain'; end if;
 end $planning_closed$;
