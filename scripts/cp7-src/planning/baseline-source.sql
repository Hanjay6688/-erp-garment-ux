-- Native P06 source slice: dated targets are scenarios, never production orders.
-- WIP/calendar/matching are explicitly missing until their authoritative adapter
-- is qualified. Nothing below treats missing supply as zero or enables apply.
create schema cp7_baseline_native authorization cp7_capture;
revoke all on schema cp7_baseline_native from public,anon,authenticated,service_role;
create table cp7_baseline_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_baseline_native.runs owner to cp7_capture;
alter table cp7_baseline_native.runs enable row level security;
create policy cp7_baseline_native_no_access on cp7_baseline_native.runs for all to public using(false)with check(false);
revoke all on cp7_baseline_native.runs from public,anon,authenticated,service_role;
create trigger immutable_baseline_run before update or delete on cp7_baseline_native.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_baseline_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with c as materialized(select cp7_planning.history_source()value),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)
 select value||jsonb_build_object('profiles',cp7_profile.source(coalesce(ids,array[]::uuid[]),(value->>'captured_at')::timestamptz),
  'production_policies',cp7_identity.workspace_data(coalesce((select array_agg(distinct(s->>'sku_id')::uuid)
   from jsonb_array_elements(value->'facts'->'products')p cross join lateral jsonb_array_elements(p->'commercial')s),array[]::uuid[]),
   (value->>'captured_at')::timestamptz))from c cross join roots
$$;

-- One pass over the history rows. Profiles, current stock and production
-- policies were rescanned per row and rows grew by copy; the maps below are
-- built where each scan first ran, so a non-array still fails at the same
-- statement. A scalar subquery that could see two rows (profile per root,
-- stock per target) refuses as that subquery did; the policy lookup keeps its
-- LIMIT 1, the first policy in array order whose members contain the root.
create function cp7_baseline_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb;r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;hash text;total numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;
begin
 h:=cp7_planning.history_build(c,q);
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex');
 for r in select value from jsonb_array_elements(h->'history'->'rows')order by value->>'target_key'loop
  root:=split_part(r->>'target_key',':',1);
  if profiles is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into profiles,profiles_repeated
    from(select x->>'root_id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'profiles')with ordinality a(x,o)
     where x->>'root_id'is not null group by 1)f;
  end if;
  if profiles_repeated?root then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  p:=profiles->root;
  if stocks is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into stocks,stocks_repeated
    from(select x->>'target_key' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(h->'current_stock')with ordinality a(x,o)
     where x->>'target_key'is not null group by 1)f;
  end if;
  if stocks_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  stock:=stocks->(r->>'target_key');
  refs:=r->'refs';cfg:=case when p->>'quality'='SELECTED_ASSUMPTION'then p->'config'else null end;
  profile_refs:=case when cfg is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object('kind','PLANNING_PROFILE','id',p->>'profile_id','revision',p->>'revision'))end;
  select coalesce(sum((value->>'gross_observed_pcs')::numeric),0)into total from jsonb_array_elements(r->'days')where value->>'state'='AVAILABLE';
  own:=jsonb_build_object('available_total_pcs',total::text,'available_days',(r->>'available_days')::text,'capture_complete',true,'refs',refs);
  manual:=case when cfg->>'mean_mode'='SELECTED_MANUAL'then jsonb_build_object('daily_pcs',cfg->'daily_pcs',
   'assumption_id',p->>'profile_id','selected',true,'refs',profile_refs)else null end;
  estimate:=cp7_demand.estimate(jsonb_build_object('contract_version','cp7.demand-estimate-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',r->>'target_key','size_id',r->>'size_id',
   'minimum_own_available_days',coalesce(cfg->'minimum_available_days','"1"'::jsonb),
   'own',case when cfg is null then null else own end,'analog',null,'manual',manual,'refs',refs||profile_refs));
  target:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode','DAYS','daily_mean',estimate->'daily_pcs',
   'lead_days',cfg->'lead_days','review_days',cfg->'review_days','buffer_days',cfg->'buffer_days',
   'quantile',null,'horizon_samples','[]'::jsonb,'refs',refs||profile_refs));
  -- (value->'members')?root: string array elements, object keys, or the string itself.
  if policies is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into policies
    from(select m.k,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')with ordinality a(x,o)
     cross join lateral(select e#>>'{}' k from jsonb_array_elements(case when jsonb_typeof(x->'members')='array'then x->'members'end)e
       where jsonb_typeof(e)='string'
      union select jsonb_object_keys(case when jsonb_typeof(x->'members')='object'then x->'members'end)
      union select x->'members'#>>'{}' where jsonb_typeof(x->'members')='string')m group by 1)f;
  end if;
  policy:=policies->root;
  state:=case when policy->'policy'->>'quality'='KNOWN'then policy->'policy'->>'state'else null end;
  rows:=array_append(rows,jsonb_build_object('target_key',r->>'target_key','size_id',r->>'size_id',
   'sku',stock->>'sku','product_name',stock->>'product_name','available_fg_pcs',stock->>'native_available_pcs',
   'profile',p,'demand_estimate',estimate,'target',target,'production_policy',policy,
   'start_new_pcs',case when state in('PAUSED','STOPPED')then '0'else null end,
   'final_gap_pcs',null,'supply_state','UNKNOWN','capacity_state','UNKNOWN','timeline_state','UNKNOWN',
   'reason',case when state in('PAUSED','STOPPED')then 'PRODUCTION_DISABLED_EXISTING_STOCK_STILL_SELLABLE'
    when state is null then 'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE'
    else 'AUTHORITATIVE_WIP_MATCHING_CALENDAR_CAPACITY_NOT_CAPTURED'end,
   'refs',refs||profile_refs));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-baseline.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS','history_run_result',h,
  'rows',to_jsonb(rows),'target_basis','DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS','apply_enabled',false,
  'model_basis','BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN','production_go',false);
end $$;

create function cp7_baseline_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_baseline_native.runs%rowtype;c jsonb;hash text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();select *into r from cp7_baseline_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_BASELINE_RUN_UNAVAILABLE';end if;
 c:=cp7_baseline_native.source();hash:=encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex');
 outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,'source_state',
  case when c->>'status'='COMPLETE'and hash=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_BASELINE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_baseline_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_baseline_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_BASELINE_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:BASELINE:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_BASELINE_ACCESS_CHANGED';end if;
 select *into r from cp7_baseline_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_BASELINE_REQUEST_CHANGED';end if;return cp7_baseline_native.serve(r.id);
 end if;
 with source as materialized(select cp7_baseline_native.source()c),calculated as materialized(select c,cp7_baseline_native.build(c,q)result from source)
 insert into cp7_baseline_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'from calculated returning *into r;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_BASELINE_ACCESS_CHANGED';end if;
 return cp7_baseline_native.serve(r.id);
end $$;

alter function cp7_baseline_native.source()owner to cp7_capture;
alter function cp7_baseline_native.build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_baseline_native.serve(uuid)owner to cp7_capture;
alter function cp7_baseline_native.capture(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_baseline_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_baseline_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_baseline_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_baseline_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_baseline_native.serve(p_run)$$;
alter function public.erp_cp7_capture_baseline_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_baseline_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_baseline_v1(jsonb,uuid),public.erp_cp7_read_baseline_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_baseline_v1(jsonb,uuid),public.erp_cp7_read_baseline_v1(uuid)to authenticated;
