-- One native physical-source universe, one selected remaining-work scenario and
-- one server allocation. Consumer filters and match labels never enter this API.
create schema cp7_netting_native authorization cp7_capture;
revoke all on schema cp7_netting_native from public,anon,authenticated,service_role;

create function cp7_netting_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_schedule_native.source()c),
 wanted as materialized(
  select x->>'id'id from source,jsonb_array_elements(c->'facts'->'products')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'bs')x
 ),products as materialized(
  select p.id,coalesce(p.identity_root_id,p.id)root_id,p.model_id,p.size_id,p.brand_id,p.color_name,
   p.effective_from,p.effective_to,p.created_at
  from erp.products p join wanted w on w.id=p.id::text cross join source
  where p.created_at<=(c->>'captured_at')::timestamptz order by p.id limit 5001
 )select c||jsonb_build_object('matching_products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'))from source
$$;

create function cp7_netting_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('work_source',cp7_schedule_native.fingerprint(c),
  'matching_products',c->'matching_products')::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_netting_native.bound_product(c jsonb,p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare id text;rw jsonb;bs jsonb;facts jsonb:=c->'production_sources'->'facts';
begin
 if split_part(p->>'pool_key',':',1)='OPEN'then
  select x->>'product_id'into id from jsonb_array_elements(facts->'other'->'origins')x
   where x->>'id'=split_part(p->>'pool_key',':',2);
 elsif split_part(p->>'pool_key',':',1)='NONPO'then
  select x->>'product_id'into id from jsonb_array_elements(facts->'other'->'bs')x
   where x->>'id'=split_part(p->>'pool_key',':',2);
 elsif p->>'stage'='REWORK'then
  select x into rw from jsonb_array_elements((facts->'cutting'->'reworks')||(facts->'other'->'reworks'))x
   where x->>'id'=split_part(p->>'key',':',2);
  select x->>'product_id'into id from jsonb_array_elements((facts->'cutting'->'bs')||(facts->'other'->'bs'))x
   where x->>'id'=rw->>'bs_case_id';
 end if;
 return(select x from jsonb_array_elements(c->'matching_products')x where x->>'id'=id);
end $$;

-- The matching facts plus, per captured position text, the model matches()
-- derives: coalesce(bound_product model, position_model). bound_product and
-- cp7_schedule_native.position_model are evaluated here from lazy id maps,
-- each built where that function's first scan of the array ran, so a
-- non-array still fails at the same position. A scalar subquery that could
-- see two rows (matching product, position_model's group/origin/NONPO join)
-- refuses as that subquery did; SELECT INTO lookups keep the first row.
create function cp7_netting_native.matching_models(c jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare p jsonb;product jsonb;g jsonb;rw jsonb;constraints jsonb;refs jsonb;sources jsonb[]:='{}';targets jsonb[]:='{}';
 model text;bound_model text;confirmed text;quality text;id text;kind text;part text;facts jsonb:=c->'production_sources'->'facts';
 by_id jsonb;by_id_repeated jsonb;origins jsonb;origins_repeated jsonb;other_bs jsonb;reworks jsonb;all_bs jsonb;
 groups jsonb;groups_repeated jsonb;nonpo jsonb;root_models jsonb;position_texts text[]:='{}';position_models text[]:='{}';
begin
 if jsonb_array_length(c->'matching_products')>5000 then raise exception 'CP7_NETTING_MATCH_SOURCE_LIMIT';end if;
 for product in select value from jsonb_array_elements(c->'facts'->'products')order by value->>'root_id'loop
  if by_id is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_id,by_id_repeated
    from(select x->>'id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'matching_products')with ordinality a(x,o)
     where x->>'id'is not null group by 1)f;
  end if;
  g:=by_id->(product->>'id');
  if g is null then raise exception 'CP7_NETTING_NATIVE_PRODUCT_MISSING';end if;
  refs:=jsonb_build_array(cp7_wip.ref('erp.products',g->>'id',g->>'effective_from'));
  constraints:=jsonb_build_array(
   jsonb_build_object('field','brand','value',g->'brand_id','required',true,'basis','FACT'),
   jsonb_build_object('field','color','value',g->'color_name','required',true,'basis','FACT'));
  targets:=array_append(targets,jsonb_build_object('key',(g->>'root_id')||':'||(g->>'size_id'),
   'size_id',g->'size_id','constraints',constraints,'refs',refs));
 end loop;
 for p in select value from jsonb_array_elements(wip->'positions')order by value->>'key'loop
  -- cp7_netting_native.bound_product(c,p)
  id:=null;kind:=split_part(p->>'pool_key',':',1);part:=split_part(p->>'pool_key',':',2);
  if kind='OPEN'then
   if origins is null then
    select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into origins,origins_repeated
     from(select x->>'id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(facts->'other'->'origins')with ordinality a(x,o)
      where x->>'id'is not null group by 1)f;
   end if;
   id:=origins->part->>'product_id';
  elsif kind='NONPO'then
   if other_bs is null then
    select coalesce(jsonb_object_agg(f.k,f.v),'{}')into other_bs
     from(select x->>'id' k,(array_agg(x order by o))[1] v from jsonb_array_elements(facts->'other'->'bs')with ordinality a(x,o)
      where x->>'id'is not null group by 1)f;
   end if;
   id:=other_bs->part->>'product_id';
  elsif p->>'stage'='REWORK'then
   if reworks is null then
    select coalesce(jsonb_object_agg(f.k,f.v),'{}')into reworks
     from(select x->>'id' k,(array_agg(x order by o))[1] v from jsonb_array_elements((facts->'cutting'->'reworks')||(facts->'other'->'reworks'))with ordinality a(x,o)
      where x->>'id'is not null group by 1)f;
   end if;
   rw:=reworks->split_part(p->>'key',':',2);
   if all_bs is null then
    select coalesce(jsonb_object_agg(f.k,f.v),'{}')into all_bs
     from(select x->>'id' k,(array_agg(x order by o))[1] v from jsonb_array_elements((facts->'cutting'->'bs')||(facts->'other'->'bs'))with ordinality a(x,o)
      where x->>'id'is not null group by 1)f;
   end if;
   id:=all_bs->(rw->>'bs_case_id')->>'product_id';
  end if;
  if by_id is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_id,by_id_repeated
    from(select x->>'id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'matching_products')with ordinality a(x,o)
     where x->>'id'is not null group by 1)f;
  end if;
  if by_id_repeated?id then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  product:=by_id->id;
  -- cp7_schedule_native.position_model(c,p)
  model:=null;
  if kind='CUT'then
   if groups is null then
    select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into groups,groups_repeated
     from(select x->>'id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(facts->'cutting'->'groups')with ordinality a(x,o)
      where x->>'id'is not null group by 1)f;
   end if;
   if groups_repeated?part then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
   model:=groups->part->>'model_id';
  elsif kind='OPEN'then
   if origins_repeated?part then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
   model:=origins->part->>'model_id';
  elsif kind='NONPO'then
   if nonpo is null then
    select coalesce(jsonb_object_agg(f.k,jsonb_build_object('n',f.n,'model_id',f.m)),'{}')into nonpo
     from(select x->>'id' k,count(*)n,(array_agg(y->>'model_id'))[1] m from jsonb_array_elements(facts->'other'->'bs')x
      join jsonb_array_elements(c->'facts'->'products')y on y->>'id'=x->>'product_id' where x->>'id'is not null group by 1)f;
   end if;
   if(nonpo->part->>'n')::bigint>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
   model:=nonpo->part->>'model_id';
  end if;
  bound_model:=coalesce(product->>'model_id',model);quality:=null;
  constraints:='[]';refs:=p->'refs';confirmed:=null;
  if product is not null then
   if product->>'size_id'<>p->>'size_id'then raise exception 'CP7_NETTING_NATIVE_SOURCE_SIZE';end if;
   model:=product->>'model_id';confirmed:=(product->>'root_id')||':'||(product->>'size_id');
   -- Another captured product of this root with a different model: the
   -- lowest and highest model of the root bound every model it has.
   if root_models is null then
    select coalesce(jsonb_object_agg(f.k,jsonb_build_array(f.lo,f.hi)),'{}')into root_models
     from(select x->>'root_id' k,min(x->>'model_id')lo,max(x->>'model_id')hi from jsonb_array_elements(c->'facts'->'products')x
      where x->>'root_id'is not null and x->>'model_id'is not null group by 1)f;
   end if;
   if root_models->(product->>'root_id')->>0<>model or root_models->(product->>'root_id')->>1<>model then quality:='CONFLICT';end if;
   constraints:=jsonb_build_array(
    jsonb_build_object('field','brand','value',product->'brand_id','required',true,'basis','FACT'),
    jsonb_build_object('field','color','value',product->'color_name','required',true,'basis','FACT'));
   refs:=refs||jsonb_build_array(cp7_wip.ref('erp.products',product->>'id',product->>'effective_from'));
  elsif kind='CUT'then
   g:=groups->part;
   if g->>'pattern_id'is not null and g->>'pattern_revision_snapshot'is not null then
    constraints:=constraints||jsonb_build_array(jsonb_build_object('field','pattern_revision',
     'value',(g->>'pattern_id')||':'||(g->>'pattern_revision_snapshot'),'required',false,'basis','FACT'));
   end if;
  end if;
  -- Brand/color are critical target attributes. An unbound cut cannot acquire
  -- them from a tariff SKU, a similar name or the user's target selection.
  sources:=array_append(sources,jsonb_build_object('key',p->'key','size_id',p->'size_id',
   'quality',coalesce(quality,case when model is null then 'UNKNOWN'else 'COMPLETE'end),
   'confirmed_target',confirmed,'constraints',constraints,'refs',refs));
  position_texts:=array_append(position_texts,p::text);position_models:=array_append(position_models,bound_model);
 end loop;
 return jsonb_build_object('matching',jsonb_build_object('snapshot_id',wip->'snapshot_id','sources',to_jsonb(sources),'targets',to_jsonb(targets)),
  'models',(select coalesce(jsonb_object_agg(u.k,u.m),'{}')from unnest(position_texts,position_models)u(k,m)));
end $$;

create function cp7_netting_native.matching(c jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 return cp7_netting_native.matching_models(c,wip)->'matching';
end $$;

create function cp7_netting_native.matches(c jsonb,p jsonb,t jsonb,matching jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb;target jsonb;model text;product jsonb;
begin
 s:=(select x from jsonb_array_elements(matching->'sources')x where x->>'key'=p->>'key');
 target:=(select x from jsonb_array_elements(matching->'targets')x where x->>'key'=t->>'target_key');
 product:=cp7_netting_native.bound_product(c,p);
 model:=coalesce(product->>'model_id',cp7_schedule_native.position_model(c,p));
 if model is null then return jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));end if;
 if not exists(select 1 from jsonb_array_elements(c->'facts'->'products')x
  where(x->>'root_id')||':'||(x->>'size_id')=t->>'target_key'and x->>'model_id'=model)then
  return jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));end if;
 return cp7_wip.match_target(s,target);
end $$;

create function cp7_netting_native.timeline(c jsonb,r jsonb,etas jsonb,edges jsonb,matching jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cfg jsonb:=r->'profile'->'config';rate numeric;horizon numeric;remaining numeric;duration numeric;qty numeric;
 ready timestamptz:=(c->>'captured_at')::timestamptz;deadline timestamptz;at_time timestamptz;
 events jsonb[]:='{}';e jsonb;eta jsonb;i integer:=0;seq integer:=0;eta_at jsonb;eta_repeated jsonb;
begin
 if r->'target'->>'status'is distinct from 'SCENARIO'or r->'demand_estimate'->>'daily_pcs'is null then
  return jsonb_build_object('status','UNKNOWN','reason','SELECTED_TARGET_OR_DEMAND_UNKNOWN');end if;
 if r->>'available_fg_pcs'like '-%'then return jsonb_build_object('status','UNKNOWN',
  'reason','NATIVE_RESERVATIONS_EXCEED_ON_HAND_SIGNED_GAP_PRESERVED');end if;
 rate:=cp7_demand.decimal(r->'demand_estimate'->'daily_pcs');
 horizon:=cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days');
 deadline:=ready+(horizon::text||' days')::interval;remaining:=horizon;
 while remaining>0 loop
  duration:=least(1,remaining);i:=i+1;
  if i>3660 then raise exception 'CP7_NETTING_TIMELINE_HORIZON_LIMIT';end if;
  at_time:=least(deadline,ready+(i::text||' days')::interval);qty:=ceil(rate*duration*1000000000000)/1000000000000;
  events:=array_append(events,jsonb_build_object('key','forecast-day-'||i,'at',cp7_planning.utc(at_time),
   'sequence',(10000+i)::text,'kind','DEMAND','qty_pcs',qty::numeric(42,12)::text,'refs',r->'refs'));
  remaining:=remaining-duration;
 end loop;
 for e in select value from jsonb_array_elements(edges)where value->>'target_key'=r->>'target_key'order by value->>'key'loop
  -- One ETA per edge position. The map is built where the per-edge scan
  -- first ran; a repeated position key fails as that scan did.
  if eta_at is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
     where value->>'position_key'is not null group by 1)f;
  end if;
  if eta_repeated?(e->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta_at->(e->>'position_key');
  if eta->'at'='null'::jsonb then continue;end if;
  at_time:=cp7_demand.instant(eta->'at');
  if at_time>deadline then continue;end if;
  seq:=seq+1;events:=array_append(events,jsonb_build_object('key','supply-'||(e->>'key'),
   'at',cp7_planning.utc(at_time),'sequence',seq::text,'kind','SUPPLY','qty_pcs',e->'projected_good_pcs','refs',e->'refs'));
 end loop;
 return cp7_baseline.timeline(jsonb_build_object('contract_version','cp7.timeline-input.v1',
  'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','target_key',r->'target_key',
  'size_id',r->'size_id','mode','BACKLOG','initial_fg_pcs',r->'available_fg_pcs',
  'from_at',cp7_planning.utc(ready),'through_at',cp7_planning.utc(deadline),'events',to_jsonb(events),'refs',r->'refs'))
  ||jsonb_build_object('timing_basis','SELECTED_DAILY_RESIDUAL_AT_EACH_24H_END_FROM_CAPTURE',
   'unmet_mode_basis','EXPLICIT_TECHNICAL_BACKLOG_SCENARIO','buffer_consumed_as_demand',false);
end $$;

create function cp7_netting_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare scenario jsonb;wip jsonb;matching jsonb;models jsonb;p jsonb;t jsonb;m jsonb;s jsonb;tf jsonb;eta jsonb;
 r jsonb;cfg jsonb;line jsonb;alloc jsonb;edges jsonb:='[]';etas jsonb;targets jsonb;
 matches jsonb;hash text;policy text;ready timestamptz;model text;compatible jsonb;
 deadline timestamptz;helps timestamptz;raw_need numeric;directed numeric;candidate numeric;gap numeric;
 budget numeric:=0;all_targets_known boolean:=true;supplies_complete boolean:=true;refs jsonb;production_status text;
 supplies jsonb;net jsonb;raw_net jsonb;directed_edges jsonb;line_edges jsonb;
 eta_list jsonb[]:='{}';target_list jsonb[]:='{}';review_list jsonb[]:='{}';row_list jsonb[]:='{}';
 baseline_lines jsonb[]:='{}';baseline_rows text[]:='{}';planned_index jsonb;
 pair_rows jsonb[]:='{}';eligible jsonb[]:='{}';open_work jsonb[];open_index integer[];supply_list jsonb[];edge_list jsonb[];
 row_keys text[];row_target_keys jsonb[];row_at jsonb;model_targets jsonb;candidates jsonb;leaders integer[];
 eta_at jsonb;eta_repeated jsonb;source_at jsonb;source_repeated jsonb;target_at jsonb;target_repeated jsonb;
 planned_at jsonb;planned_repeated jsonb;i integer;j integer;n integer;first_repeated integer;
 unknown_model jsonb:=jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));
 model_mismatch jsonb:=jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));
begin
 scenario:=cp7_schedule_native.build(c,q);wip:=scenario->'wip';hash:=cp7_netting_native.fingerprint(c);
 ready:=(c->>'captured_at')::timestamptz;
 if wip->>'status'is distinct from 'COMPLETE'then
  return jsonb_build_object('contract_version','cp7.native-netting.v1','captured_at',c->>'captured_at',
   'source_hash',hash,'status','UNKNOWN','schedule_run_result',scenario,'rows','[]'::jsonb,
   'allocation',jsonb_build_object('status','UNKNOWN','reason','NATIVE_QUANTITY_CAPTURE_INCOMPLETE'),
   'apply_enabled',false,'production_go',false);
 end if;
 if jsonb_array_length(wip->'positions')*jsonb_array_length(scenario->'supply_run_result'->'baseline_run_result'->'rows')>100000
  or jsonb_array_length(wip->'positions')>1000 then raise exception 'CP7_NETTING_WORK_LIMIT';end if;
 m:=cp7_netting_native.matching_models(c,wip);matching:=m->'matching';models:=m->'models';
 for eta in select value from jsonb_array_elements(scenario->'etas')loop
  eta_list:=array_append(eta_list,jsonb_build_object('position_key',eta->'position_key',
   'at',case when eta->'result'->>'status'in('KNOWN','CONDITIONAL')then cp7_planning.utc((eta->'result'->>'eta')::timestamptz)else null end,
   'refs',eta->'refs'));
 end loop;
 etas:=to_jsonb(eta_list);
 -- Every per-row scan of an array this function composed (ETAs, matching
 -- sources/targets, its own targets) is one map of that array. A key held
 -- twice refuses where the scalar subquery over that array refused; a single
 -- key reads the same element. Composed arrays cannot fail to unnest.
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
  from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
   where value->>'position_key'is not null group by 1)f;
 -- Existing work is timed in one shared queue. Its projected supply budget is
 -- separate from AFTER-existing-work free capacity for new starts.
 for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb loop
  if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta_at->(p->>'key');eligible:=array_append(eligible,p);
  if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
   budget:=budget+cp7_wip.pcs(p->'projection'->'projected_good_pcs');
  elsif cp7_wip.pcs(p->'remaining_pcs')>0 then supplies_complete:=false;end if;
 end loop;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into target_at,target_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'targets')
   where value->>'key'is not null group by 1)f;
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  cfg:=r->'profile'->'config';policy:=r->'production_policy'->'policy'->>'state';
  if r->'target'->>'status'is distinct from 'SCENARIO'or r->>'available_fg_pcs'is null then
   all_targets_known:=false;review_list:=array_append(review_list,jsonb_build_object('target_key',r->'target_key','reason','DEMAND_TARGET_STOCK_OR_PRODUCTION_POLICY_UNREVIEWED'));continue;end if;
  if policy is null then all_targets_known:=false;review_list:=array_append(review_list,jsonb_build_object('target_key',r->'target_key','reason','PRODUCTION_POLICY_UNREVIEWED'));end if;
  production_status:=case when policy='ACTIVE'then 'ACTIVE'when policy in('PAUSED','STOPPED')then 'STOP'else 'UNKNOWN'end;
  raw_net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
   'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
   'target_key',r->'target_key','size_id',r->'size_id','deadline',cp7_planning.utc(ready),
   'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies','[]'::jsonb,'refs',r->'refs'));
  raw_need:=cp7_wip.pcs(raw_net->'q_base_pcs');
  deadline:=ready+((cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days'))::text||' days')::interval;
  helps:=ready+(cp7_demand.decimal(cfg->'lead_days')::text||' days')::interval;
  line:=cp7_netting_native.timeline(c,r,etas,'[]'::jsonb,matching,wip);
  if target_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  tf:=target_at->(r->>'target_key');
  select jsonb_agg(x order by x::text)into refs from(select distinct value x from jsonb_array_elements((r->'refs')||(tf->'refs')))u;
  target_list:=array_append(target_list,jsonb_build_object('key',r->'target_key','size_id',r->'size_id',
   'need_pcs',raw_need::text,'deadline',cp7_planning.utc(deadline),
   'risk_at',coalesce(line->'first_known_gap'->'at',to_jsonb(cp7_planning.utc(deadline))),
   'helps_at',cp7_planning.utc(helps),'production_status',production_status,'refs',refs));
  baseline_lines:=array_append(baseline_lines,line);baseline_rows:=array_append(baseline_rows,r::text);
 end loop;
 targets:=to_jsonb(target_list);
 -- Model is an additional Native hard constraint absent from the retained
 -- five-field pure matcher. A source with a Native product binding can only
 -- match that root; unbound critical brand/color remains NEEDS_CHECK.
 -- Evaluate each immutable pair once, in matches() order: eligible positions
 -- outer, targets inner, each in array order. Per position the source and its
 -- model, per target the matching target are read once; a pair keeps only
 -- the model test and the five-field match. A target key repeated among the
 -- matching targets refuses at its first row, after the rows before it.
 -- Results are kept per position in target order; the index never enters
 -- the returned contract.
 select coalesce(array_agg(value->>'target_key' order by o),'{}'),coalesce(array_agg(value->'target_key' order by o),'{}')into row_keys,row_target_keys
  from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality a(value,o);
 n:=cardinality(row_keys);
 select coalesce(min(u.j),n+1)into first_repeated from unnest(row_keys)with ordinality u(k,j)where target_repeated?u.k;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into source_at,source_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'sources')
   where value->>'key'is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.m,f.ks),'{}')into model_targets
  from(select x->>'model_id' m,jsonb_object_agg((x->>'root_id')||':'||(x->>'size_id'),true)ks from jsonb_array_elements(c->'facts'->'products')x
   where x->>'model_id'is not null and(x->>'root_id')||':'||(x->>'size_id')is not null group by 1)f;
 -- cp7_wip.match_target checks the source and the target independently, and
 -- its verdict reads only the source's quality, size, confirmed target and
 -- constraints. A position with the same source facts and model as an earlier
 -- one (its leader) therefore has the leader's verdicts once one call of its
 -- own has proven its source; that call refuses as its first pair would.
 select coalesce(array_agg(f.leader order by f.i),'{}')into leaders
  from(select g.i,case when g.facts is null then g.i else min(g.i)over(partition by g.facts)end leader
   from(select e.i,case when e.s is not null and e.model is not null then
      jsonb_build_array(e.s->'quality',e.s->'size_id',e.s->'confirmed_target',e.s->'constraints',e.model)::text end facts
     from(select x.i,source_at->(x.p->>'key') s,models->>(x.p::text) model from unnest(eligible)with ordinality x(p,i))e)g)f;
 i:=0;
 foreach p in array eligible loop
  exit when n=0;
  i:=i+1;
  if source_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  s:=source_at->(p->>'key');model:=models->>(p::text);compatible:=model_targets->model;
  if leaders[i]<i then
   select min(u.j)into j from unnest(row_keys)with ordinality u(k,j)where coalesce(compatible?u.k,false);
   if j is not null then m:=cp7_wip.match_target(s,target_at->row_keys[j]);end if;
   pair_rows:=array_append(pair_rows,pair_rows[leaders[i]]);
  else
   select coalesce(jsonb_agg(case when model is null then unknown_model when not coalesce(compatible?u.k,false)then model_mismatch
     else cp7_wip.match_target(s,target_at->u.k)end order by u.j),'[]')into m
    from unnest(row_keys)with ordinality u(k,j)where u.j<first_repeated;
   pair_rows:=array_append(pair_rows,m);
   if first_repeated<=n then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  end if;
 end loop;
 select coalesce(jsonb_agg(jsonb_build_object('position_key',e.p->'key','target_key',k.tk,'result',x.m)order by e.i,x.j),'[]')into matches
  from unnest(eligible,pair_rows)with ordinality e(p,pr,i)
  cross join lateral jsonb_array_elements(e.pr)with ordinality x(m,j)
  join unnest(row_target_keys)with ordinality k(tk,j)on k.j=x.j;
 if not all_targets_known then alloc:=jsonb_build_object('status','UNKNOWN','reason','GLOBAL_TARGET_NEEDS_OR_POLICY_NOT_FULLY_REVIEWED');
 elsif scenario->>'schedule_state'<>'SELECTED_ASSUMPTIONS'then alloc:=jsonb_build_object('status','UNKNOWN','reason','SOURCE_BOUND_WORK_YIELD_NOT_REVIEWED');
 elsif not supplies_complete then alloc:=jsonb_build_object('status','UNKNOWN','reason','EXISTING_SUPPLY_YIELD_OR_SHARED_ETA_UNKNOWN');
 else
  -- Exact Native model mismatch must remain a hard conflict inside the kernel,
  -- too. Bound product sources already have exact destination; every unbound
  -- source requires missing brand/color proof and cannot generate an edge.
  alloc:=cp7_baseline.allocate(jsonb_build_object('contract_version','cp7.allocation-input.v1',
   'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',c->'schedule'->'plan_id',
   'complete_scope',true,'positions',wip,'matching',matching,'etas',etas,'targets',targets,
   'capacity_pcs',budget::text,'refs',jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision'))));
  edges:=coalesce(alloc->'allocation'->'edges','[]'::jsonb);
 end if;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}')into candidates
  from(select value->>'target_key' k,jsonb_agg(value order by o)v from jsonb_array_elements(edges)with ordinality a(value,o)
   where value->>'target_key'is not null and value->>'match'='CANDIDATE_MATCH'group by 1)f;
 select coalesce(jsonb_object_agg(f.k,f.j),'{}')into row_at
  from(select u.k,min(u.j)j from unnest(row_keys)with ordinality u(k,j)where u.k is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}'),
  coalesce(jsonb_object_agg(f.k,f.j),'{}')into planned_at,planned_repeated,planned_index
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v,min(o)j from jsonb_array_elements(targets)with ordinality a(value,o)
   where value->>'key'is not null group by 1)f;
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  if planned_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  t:=planned_at->(r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   -- A fully emptied position stays in the graph as evidence; it is no supply
   -- (the budget loop above skips it too) and must not make the target UNKNOWN.
   -- The open eligible positions are the same for every target: they are
   -- read once, at the first target that reads them, in array order.
   if open_work is null then
    open_work:='{}';open_index:='{}';i:=0;
    foreach p in array eligible loop
     i:=i+1;
     if cp7_wip.pcs(p->'remaining_pcs')>0 then open_work:=array_append(open_work,p);open_index:=array_append(open_index,i);end if;
    end loop;
   end if;
   -- A pair result depends on the target only through its key.
   j:=(row_at->>(r->>'target_key'))::integer;supply_list:='{}';edge_list:='{}';i:=0;
   foreach p in array open_work loop
    i:=i+1;m:=pair_rows[open_index[i]]->(j-1);
    if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'key');
    if m->>'match'='CONFIRMED_TARGET'then
     supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'key','snapshot_id',wip->'snapshot_id',
      'target_key',r->'target_key','size_id',r->'size_id','kind','DIRECTED',
      'qty_pcs',case when p->'projection'->>'quality'='SCENARIO'then p->'projection'->'projected_good_pcs'else null end,
      'eta',coalesce(eta->'at','null'::jsonb),'eligible',true,'refs',p->'refs'));
     if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
      edge_list:=array_append(edge_list,jsonb_build_object('key',p->'key','position_key',p->'key',
       'target_key',r->'target_key','projected_good_pcs',p->'projection'->'projected_good_pcs','refs',p->'refs'));
     end if;
    end if;
   end loop;
   for p in select value from jsonb_array_elements(candidates->(r->>'target_key'))loop
    if eta_repeated?(p->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'position_key');
    supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'position_key','snapshot_id',wip->'snapshot_id',
     'target_key',r->'target_key','size_id',r->'size_id','kind','ALLOCATED_CANDIDATE','qty_pcs',p->'projected_good_pcs',
     'eta',eta->'at','eligible',true,'refs',p->'refs'));
   end loop;
   supplies:=to_jsonb(supply_list);directed_edges:=to_jsonb(edge_list);
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
    'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
    'target_key',r->'target_key','size_id',r->'size_id','deadline',t->'deadline',
    'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',supplies,'refs',r->'refs'));
   gap:=(net->>'q_base_pcs')::numeric;directed:=coalesce((net->>'directed_on_time_pcs')::numeric,0);
   candidate:=coalesce((net->>'candidate_on_time_pcs')::numeric,0);
  end if;
  -- The timeline reads only this target's edges, in the same order.
  if t is null then line:=jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED');
  else
   line_edges:=directed_edges||coalesce(candidates->(r->>'target_key'),'[]'::jsonb);
   -- With no supply edges all six immutable arguments equal the first call.
   -- Reuse only that invocation's result; no persisted cache or guard removal.
   -- planned_repeated above rejects duplicate planned keys, but a row skipped
   -- before planning can share its key with a planned one: reuse only when
   -- this is the very row the first call read (same jsonb text).
   if line_edges='[]'::jsonb and baseline_rows[(planned_index->>(r->>'target_key'))::integer]=r::text then
    line:=baseline_lines[(planned_index->>(r->>'target_key'))::integer];
   else line:=cp7_netting_native.timeline(c,r,etas,line_edges,matching,wip);end if;
  end if;
  row_list:=array_append(row_list,r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
   'base_gap_pcs',net->'q_base_pcs','conditional_gap_pcs',case when alloc->>'status'='SCENARIO'then net->'q_conditional_pcs'else null end,
   'net',net,
   'candidate_allocated_good_pcs',case when alloc->>'status'='SCENARIO'then candidate::text else null end,
   'timeline',line,'start_new_pcs',case when t->>'production_status'='STOP'then '0'else null end,
   'material_state','UNKNOWN','new_start_capacity',scenario->'capacity','apply_enabled',false,
   'netting_basis','NATIVE_AVAILABLE_FG_ONCE_SOURCE_BOUND_YIELD_AND_ONE_SHARED_REMAINING_CALENDAR',
   'reason','SCENARIO_EXISTING_SUPPLY_DISTINCT_FROM_NEW_START_MATERIAL_FEASIBILITY'));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-netting.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'status',case when all_targets_known and alloc->>'status'='SCENARIO'then 'SCENARIO'else 'PARTIAL'end,
  'schedule_run_result',scenario,'matching',matching,'match_results',matches,'rows',to_jsonb(row_list),'allocation',alloc,
  'review_queue',to_jsonb(review_list),'existing_timed_projected_good_budget_pcs',budget::text,
  'new_start_capacity',scenario->'capacity','material_state','UNKNOWN','apply_enabled',false,'production_go',false);
end $$;

create table cp7_netting_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_netting_native.runs owner to cp7_capture;
alter table cp7_netting_native.runs enable row level security;
create policy cp7_netting_no_access on cp7_netting_native.runs for all to public using(false)with check(false);
revoke all on cp7_netting_native.runs from public,anon,authenticated,service_role;
create trigger immutable_netting_run before update or delete on cp7_netting_native.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_netting_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_netting_native.runs%rowtype;c jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_netting_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_NETTING_RUN_UNAVAILABLE';end if;
 c:=cp7_netting_native.source();outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,
  'source_state',case when cp7_netting_native.fingerprint(c)=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_netting_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_netting_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_NETTING_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:NETTING:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 select *into r from cp7_netting_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_NETTING_REQUEST_CHANGED';end if;return cp7_netting_native.serve(r.id);
 end if;
 with source as materialized(select cp7_netting_native.source()c),
 calculated as materialized(select c,cp7_netting_native.build(c,q)result from source)
 insert into cp7_netting_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'
 from calculated returning *into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 return cp7_netting_native.serve(r.id);
end $$;

alter function cp7_netting_native.source()owner to cp7_capture;
alter function cp7_netting_native.fingerprint(jsonb)owner to cp7_capture;
alter function cp7_netting_native.bound_product(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.matching_models(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.matching(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.matches(jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.serve(uuid)owner to cp7_capture;
alter function cp7_netting_native.capture(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_netting_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_netting_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_netting_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_netting_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_netting_native.serve(p_run)$$;
alter function public.erp_cp7_capture_netting_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_netting_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_netting_v1(jsonb,uuid),public.erp_cp7_read_netting_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_netting_v1(jsonb,uuid),public.erp_cp7_read_netting_v1(uuid)to authenticated;
