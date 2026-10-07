-- One authoritative compiler into the frozen analysis.v2 contract. Operational
-- quantities come from the Native composed result, never a client calculator.
-- The material-requirements module creates the private compiler schema.

create function cp7_analysis_native.source_within(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_netting_native.source_within(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;
create function cp7_analysis_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_analysis_native.source_within(1000,5000)
$$;
create function cp7_analysis_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('source',cp7_netting_native.fingerprint(c),
  'engine',c->'analysis_engine_signature','financial_source',c->'financial_source'->'source_hash',
  'material_source',(c->'material_source')-'captured_at','fabric_source',(c->'fabric_source')-'captured_at')::text,'UTF8'),'sha256'),'hex')
$$;
-- Finance on demand. A run captured without the protected owner report is
-- marked in its facts; every later read compares it with the same
-- operational-only source, never with the ledger. Older runs carry no mark.
create function cp7_analysis_native.finance_mode(facts jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when facts->>'financial_capture'='DEFERRED'then 'DEFERRED'else 'INCLUDED'end
$$;
create function cp7_analysis_native.fact(value text,unit text,refs jsonb,assumptions jsonb default '[]')returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when value is null then jsonb_build_object('state','UNKNOWN','unit',unit,'reason','SOURCE_INPUT_NOT_PROVEN','refs',refs)
  when jsonb_array_length(assumptions)>0 then jsonb_build_object('state','ASSUMED','value',value,'unit',unit,'refs',refs,'assumption_ids',assumptions)
  else jsonb_build_object('state','KNOWN','value',value,'unit',unit,'refs',refs)end
$$;

create function cp7_analysis_native.build(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare n jsonb:=cp7_netting_native.build(c,q);scenario jsonb:=n->'schedule_run_result';wip jsonb:=scenario->'wip';
 p jsonb;r jsonb;product jsonb;stock jsonb;hist jsonb;eta jsonb;e jsonb;event jsonb;commercial jsonb;policy text;
 refs jsonb;row_aids jsonb;plan_refs jsonb:='[]';plan_aids jsonb:='[]';assumptions jsonb:='[]';sources jsonb:='[]';recommendations jsonb:='[]';
 edges jsonb:='[]';actions jsonb:='[]';timeline jsonb:='[]';models jsonb:='[]';materials jsonb:='[]';metrics jsonb:='[]';
 dependencies jsonb:='[]';warnings jsonb:='["MATERIAL_FEASIBILITY_NOT_PROVEN","ADAPTIVE_MODEL_PROMOTION_NOT_PROVEN","FINANCIAL_DOMAIN_NOT_CAPTURED"]';
 known_targets jsonb:='{}';target_timeline jsonb;v jsonb;part jsonb;k text;part_hash text;count_facts integer:=0;part_count integer;
 complete boolean:=c->>'status'='COMPLETE'and wip->>'status'='COMPLETE';hash text:=cp7_analysis_native.fingerprint(c);
 allocation_known boolean:=n->'allocation'->>'status'='SCENARIO';allocated numeric;load numeric;captured text:=c->>'captured_at';
 supply_match text;scenario_revision bigint:=coalesce((c->'schedule'->>'revision')::bigint,0);
 fabric_plan jsonb:=cp7_fabric_native.plan(c,n);
 -- Keep ordered result chunks in SQL arrays and flatten once. Growing jsonb
 -- concatenations repeatedly copied all previously compiled targets.
 assumptions_acc jsonb[]:='{}';sources_acc jsonb[]:='{}';recommendations_acc jsonb[]:='{}';
 edges_acc jsonb[]:='{}';actions_acc jsonb[]:='{}';timeline_acc jsonb[]:='{}';models_acc jsonb[]:='{}';
 materials_acc jsonb[]:='{}';metrics_acc jsonb[]:='{}';warnings_acc jsonb[];
 materials_null boolean:=false;known_keys text[]:='{}';
 products_by_root jsonb;stock_by_target jsonb;history_by_target jsonb;
 -- P19: maps built once. A non-simple per-row query that references a large
 -- jsonb variable copies it into each custom plan, so the per-target timeline
 -- query referencing n was quadratic. Per-row queries now see only small values.
 edges_by_target jsonb;match_results_by_target jsonb;
 etas_by_position jsonb;inputs_by_source jsonb;directed_source_keys jsonb;source_inputs jsonb;
begin
 if scenario_revision>9007199254740991 then raise exception 'CP7_ANALYSIS_REVISION_RANGE';end if;
 warnings_acc:=array[warnings];
 -- Retain duplicates instead of silently choosing a row. Each original scalar
 -- lookup still refuses an ambiguous *visited* key with SQLSTATE 21000.
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into products_by_root from(
  select x->>'root_id'k,jsonb_agg(x)items from jsonb_array_elements(c->'facts'->'products')x
  where x->>'root_id'is not null group by x->>'root_id')i;
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into stock_by_target from(
  select x->>'target_key'k,jsonb_agg(x)items from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'current_stock')x
  where x->>'target_key'is not null group by x->>'target_key')i;
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into history_by_target from(
  select x->>'target_key'k,jsonb_agg(x)items from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'history'->'rows')x
  where x->>'target_key'is not null group by x->>'target_key')i;
 -- Every edge and match result of one target, in original array order. The
 -- frozen timeline query reads only this subset, so its first-edge and
 -- CONFIRMED_TARGET lookups give exactly what the whole arrays gave.
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into edges_by_target from(
  select x->>'target_key'k,jsonb_agg(x order by o)items from jsonb_array_elements(coalesce(n->'allocation'->'allocation'->'edges','[]'))with ordinality e(x,o)
  where x->>'target_key'is not null group by x->>'target_key')i;
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into match_results_by_target from(
  select x->>'target_key'k,jsonb_agg(x order by o)items from jsonb_array_elements(n->'match_results')with ordinality e(x,o)
  where x->>'target_key'is not null group by x->>'target_key')i;
 -- Every result per position is kept; a visited ambiguous position still
 -- refuses with SQLSTATE 21000 like the former scalar subquery.
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into etas_by_position from(
  select x->>'position_key'k,jsonb_agg(x->'result'order by o)items from jsonb_array_elements(coalesce(scenario->'etas','[]'))with ordinality e(x,o)
  where x->>'position_key'is not null group by x->>'position_key')i;
 select coalesce(jsonb_object_agg(i.k,true),'{}'::jsonb)into directed_source_keys from(
  select distinct x->>'key'k from jsonb_array_elements(coalesce(n->'matching'->'sources','[]'))x
  where x->>'key'is not null and x->>'confirmed_target'is not null)i;
 if c->'schedule'<>'null'::jsonb then
  plan_aids:=jsonb_build_array(c->'schedule'->>'plan_id');
  plan_refs:=jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision'));
  assumptions_acc:=array_append(assumptions_acc,jsonb_build_array(jsonb_build_object('id',c->'schedule'->>'plan_id',
   'label','Jadwal, waktu sisa dan perkiraan hasil bagus yang dipilih; bukan hasil produksi aktual',
   'origin','OWNER_INPUT','confirmed_for_operation',false)));
 end if;
 -- Retained result rows without an authoritative production state cannot be
 -- relabelled ACTIVE to fit the frozen contract. Keep the missing root visible
 -- as source review, with its exact Native product reference.
 for r in select value from jsonb_array_elements(n->'rows')order by value->>'target_key'loop
  refs:=r->'refs';policy:=r->'production_policy'->'policy'->>'state';
  if policy is null then
   warnings_acc:=array_append(warnings_acc,jsonb_build_array('PRODUCTION_POLICY_UNREVIEWED:'||(r->>'target_key')));
   actions_acc:=array_append(actions_acc,jsonb_build_array(jsonb_build_object('key','review-policy-'||(r->>'target_key'),
    'intent','REVIEW_SOURCE','source_keys','[]'::jsonb,'target_keys','[]'::jsonb,'primary_reason','PRODUCTION_POLICY_UNREVIEWED',
    'conditional',false,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
     'basis',jsonb_build_array('Status produksi produk perlu diperiksa'),'rule_version','native-review-1'))));continue;
  end if;
  product:=products_by_root->split_part(r->>'target_key',':',1);
  stock:=stock_by_target->(r->>'target_key');hist:=history_by_target->(r->>'target_key');
  if jsonb_array_length(product)>1 or jsonb_array_length(stock)>1 or jsonb_array_length(hist)>1 then
   raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';
  end if;
  product:=product->0;stock:=stock->0;hist:=hist->0;
  row_aids:=plan_aids;
  if r->'profile'->>'quality'='SELECTED_ASSUMPTION'then
   row_aids:=row_aids||jsonb_build_array(r->'profile'->>'profile_id');
   assumptions_acc:=array_append(assumptions_acc,jsonb_build_array(jsonb_build_object('id',r->'profile'->>'profile_id',
    'label','Aturan permintaan dan target yang dipilih untuk '||(r->>'sku'),
    'origin','OWNER_INPUT','confirmed_for_operation',false)));
  end if;
  commercial:=product->'commercial'->0;known_keys:=array_append(known_keys,r->>'target_key');
  recommendations_acc:=array_append(recommendations_acc,jsonb_build_array(jsonb_build_object(
   'target',jsonb_build_object('kind','PRODUCT','key',r->'target_key','brand_id',product->'brand_id',
    'product_id',product->'root_id','product_version_id',product->'id','size_id',r->'size_id',
    'commercial_identity',jsonb_build_object('state',case when commercial is null then 'LEGACY_UNMAPPED'else 'RESOLVED'end,
     'sku_id',commercial->'sku_id','sku_version_id',commercial->'version_id',
     'membership_version_id',case when commercial is null then null else(commercial->>'version_id')||':'||(product->>'root_id')end,
     'grouping_basis','CURRENT_RESTATED')),
   'production_state',policy,'actual_fg',cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
   'target_qty',cp7_analysis_native.fact(r->'target'->>'target_pcs','PCS',refs,row_aids),
   'q_base',cp7_analysis_native.fact(r->>'base_gap_pcs','PCS',refs,row_aids),
   'q_conditional',cp7_analysis_native.fact(r->>'conditional_gap_pcs','PCS',refs,row_aids),
   'suggested_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'rounding_extra',cp7_analysis_native.fact(null,'PCS',refs),
   'feasible_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'unresolved_qty',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then r->>'base_gap_pcs'else null end,'PCS',refs,row_aids),
   'reason_codes',jsonb_build_array('MATERIAL_FEASIBILITY_NOT_PROVEN'),'assumption_ids',row_aids)));
  if r->'demand_estimate'->>'daily_pcs'is not null and r->'target'->>'horizon_days'is not null then
  models_acc:=array_append(models_acc,jsonb_build_array(jsonb_build_object('target_key',r->'target_key','method_id',coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY'),
   'version','native-available-history-fallback-1','mode','FALLBACK',
   'demand_rate',cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids),
   'observed_days',hist->'available_days','stockout_days',hist->'stockout_days','unknown_days',hist->'unknown_days',
   'horizon_days',ceil((r->'target'->>'horizon_days')::numeric),
   'selection_reason','Native available-history/manual fallback; no backtest promotion without earlier-known training evidence',
   'validation_fold_ids','[]'::jsonb,'scores','[]'::jsonb)));
  end if;
  v:=cp7_analysis_native.material_needs(c,r,row_aids);
  if v is null then materials_null:=true;elsif not materials_null then materials_acc:=array_append(materials_acc,'[]'::jsonb||v);end if;
  v:=cp7_fabric_native.needs(c,r,row_aids,fabric_plan);
  if v is null then materials_null:=true;elsif not materials_null then materials_acc:=array_append(materials_acc,'[]'::jsonb||v);end if;
  metrics_acc:=array_append(metrics_acc,jsonb_build_array(jsonb_build_object('metric_id','AVAILABLE_FG_PCS:'||(r->>'target_key'),'version','native-availability-1',
   'value',cp7_analysis_native.fact(r->>'available_fg_pcs','PCS',refs),'formula_ref','NATIVE_PHYSICAL_MINUS_ACTIVE_DRAFT_RESERVATIONS_ONCE',
   'operands',jsonb_build_array(cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
    cp7_analysis_native.fact(stock->'availability'->>'reserved_pcs','PCS',stock->'refs')),
   'readiness','READY','scope_kind','TARGET','scope_key',r->'target_key',
   'period_start',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,
   'period_end',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,'knowledge_mode','CURRENT')));
  actions_acc:=array_append(actions_acc,jsonb_build_array(jsonb_build_object('key','review-material-'||(r->>'target_key'),'intent','REVIEW_SOURCE',
   'source_keys','[]'::jsonb,'target_keys',jsonb_build_array(r->'target_key'),'primary_reason','MATERIAL_FEASIBILITY_NOT_PROVEN',
   'conditional',true,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
    'basis',jsonb_build_array('Periksa bahan dan batas produksi baru'),'rule_version','native-review-1'))));
  timeline:='[]';
  -- P19: n below is only this target's edges and match results (see
  -- edges_by_target); the frozen timeline text is unchanged.
  declare n jsonb:=jsonb_build_object('allocation',jsonb_build_object('allocation',jsonb_build_object('edges',
   coalesce(edges_by_target->(r->>'target_key'),'[]'::jsonb))),'match_results',coalesce(match_results_by_target->(r->>'target_key'),'[]'::jsonb));
  begin
  -- Build each chronological row once in original event order. Repeated
  -- concatenation copied the entire growing multi-target timeline per event.
  -- This aggregate retains every row, field, reference and decimal operand.
  with events as materialized(
   select x.value event,x.value->'event' e,x.ordinality ordinal
    from jsonb_array_elements(coalesce(r->'timeline'->'events','[]'))with ordinality x),
  classified as materialized(
   select events.*,case when events.e->>'kind'='SUPPLY'then coalesce(
    (select x->>'match'from jsonb_array_elements(coalesce(n->'allocation'->'allocation'->'edges','[]'))x
     where 'supply-'||(x->>'key')=events.e->>'key'and x->>'target_key'=r->>'target_key'limit 1),
    case when exists(select 1 from jsonb_array_elements(n->'match_results')x
     where 'supply-'||(x->>'position_key')=events.e->>'key'and x->>'target_key'=r->>'target_key'and x->'result'->>'match'='CONFIRMED_TARGET')then'CONFIRMED_TARGET'end)
    else null end supply_match from events)
  select coalesce(jsonb_agg(jsonb_build_object('date',((t.e->>'at')::timestamptz at time zone 'Asia/Jakarta')::date::text,
    'target_key',r->'target_key','demand',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'then t.e->>'qty_pcs'else '0'end,'PCS',t.e->'refs',row_aids),
    'directed_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CANDIDATE_MATCH'then '0'
     when t.supply_match='CONFIRMED_TARGET'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'candidate_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CONFIRMED_TARGET'then '0'
     when t.supply_match='CANDIDATE_MATCH'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'proposed_new_supply',cp7_analysis_native.fact(null,'PCS',t.e->'refs'),'balance_end',cp7_analysis_native.fact(t.event->>'balance_pcs','PCS',t.e->'refs',row_aids),
    'mode','BACKLOG','assumed',true,'unmet_demand',cp7_analysis_native.fact(t.event->>'new_unmet_pcs','PCS',t.e->'refs',row_aids),
    'backlog_qty',cp7_analysis_native.fact(case when t.event->>'balance_pcs'is not null then greatest(0,-(t.event->>'balance_pcs')::numeric)::text else null end,'PCS',t.e->'refs',row_aids),
    'min_intraday_balance',cp7_analysis_native.fact(r->'timeline'->>'minimum_balance_pcs','PCS',t.e->'refs',row_aids),
    'first_gap_at',r->'timeline'->'first_known_gap'->'at','timing_basis','DATE_POLICY',
    'timing_policy_id','selected-native-each24h-from-capture-1','event_refs',t.e->'refs')order by t.ordinal),'[]'::jsonb)into target_timeline from classified t;
  timeline:=timeline||target_timeline;
  end;
  timeline_acc:=array_append(timeline_acc,timeline);
 end loop;
 select coalesce(jsonb_object_agg(t.key,true),'{}'::jsonb)into known_targets from unnest(known_keys)t(key);
 for e in select value from jsonb_array_elements(coalesce(n->'allocation'->'allocation'->'edges','[]'))loop
  if not(known_targets? (e->>'target_key'))then raise exception 'CP7_ANALYSIS_EDGE_TARGET_UNPROVEN';end if;
  eta:=etas_by_position->(e->>'position_key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;
  edges_acc:=array_append(edges_acc,jsonb_build_array(jsonb_build_object('source_key',e->'position_key','target_key',e->'target_key','size_id',e->'size_id',
   'input_qty',cp7_analysis_native.fact(e->>'input_pcs','PCS',e->'refs'),
   'projected_output_qty',cp7_analysis_native.fact(e->>'projected_good_pcs','PCS',e->'refs',plan_aids),
   'match',e->'match','eligible_at',eta->'eta','assumption_ids',plan_aids,'refs',e->'refs')));
 end loop;
 select coalesce(jsonb_agg(x.value order by p.ordinality,x.ordinality),'[]'::jsonb)into edges
  from unnest(edges_acc)with ordinality p(items,ordinality)cross join lateral jsonb_array_elements(p.items)with ordinality x;
 select coalesce(jsonb_object_agg(i.k,i.v),'{}'::jsonb)into inputs_by_source from(
  select x->>'source_key'k,jsonb_agg(x->'input_qty'->'value')v from jsonb_array_elements(edges)x where x->>'source_key'is not null group by x->>'source_key')i;
 for p in select value from jsonb_array_elements(coalesce(wip->'positions','[]'))
  where value->'eligible_company_wip'='true'::jsonb and cp7_wip.pcs(value->'remaining_pcs')>0 loop
  eta:=etas_by_position->(p->>'key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;source_inputs:=inputs_by_source->(p->>'key');
  select sum(i.qty::numeric)into allocated from jsonb_array_elements_text(coalesce(source_inputs,'[]'))i(qty);
  sources_acc:=array_append(sources_acc,jsonb_build_array(jsonb_build_object('source_key',p->'key','size_id',p->'size_id','stage',p->'stage',
   'supply_kind',case when directed_source_keys?(p->>'key')then 'DIRECTED'else 'CANDIDATE'end,
   'physical_remaining',cp7_analysis_native.fact(p->>'remaining_pcs','PCS',p->'refs'),
   'eligible_input',cp7_analysis_native.fact(p->'projection'->>'eligible_input_pcs','PCS',p->'refs',plan_aids),
   'eligible_projected',cp7_analysis_native.fact(p->'projection'->>'projected_good_pcs','PCS',p->'refs',plan_aids),
   'allocated',cp7_analysis_native.fact(case when allocation_known then coalesce(allocated,0)::text else null end,'PCS',p->'refs'),
   'eta',eta->'eta','eta_basis',case when eta->>'status'='CONDITIONAL'then 'ASSUMED'when eta->>'status'='KNOWN'then 'CONFIRMED_PLAN'else 'UNKNOWN'end,'refs',p->'refs')));
 end loop;
 for part in select value from jsonb_array_elements(c->'fabric_source'->'selected')loop
  if known_targets?(part->>'target_key')then
   assumptions_acc:=array_append(assumptions_acc,jsonb_build_array(jsonb_build_object('id',part->>'id',
    'label','Pemakaian kain per PCS untuk '||(part->>'target_key')||' yang dipilih; bukan konsumsi, pemasangan atau alokasi aktual',
    'origin','OWNER_INPUT','confirmed_for_operation',false)));
  end if;
 end loop;
 for k,part in select key,value from jsonb_each(jsonb_build_object('native_operational',c->'facts','native_production',c->'production_sources'->'facts',
  'native_matching',c->'matching_products','planning_profiles',c->'profiles','production_policy',c->'production_policies'->'rows',
  'selected_schedule',c->'schedule','dated_capacity_clock',c->'planning_time_bucket','analysis_engine',c->'analysis_engine_signature',
  'native_material_requirements',(c->'material_source')-'captured_at',
  'selected_fabric_requirements',(c->'fabric_source')-'captured_at'))loop
  part_hash:=encode(extensions.digest(convert_to(part::text,'UTF8'),'sha256'),'hex');
  if k in('native_operational','native_production')then
   with recursive objects(value)as(select part union all
    select x.value from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='object')
   select coalesce(sum(jsonb_array_length(x.value)),0)::integer into part_count
    from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='array';
  else part_count:=case jsonb_typeof(part)when 'array'then jsonb_array_length(part)when 'object'then 1 else 0 end;end if;
  count_facts:=count_facts+part_count;
  dependencies:=dependencies||jsonb_build_array(jsonb_build_object('domain',k,'revision',part_hash,
   'completeness',case when complete then 'COMPLETE'else 'PARTIAL'end,'fact_count',part_count,'source_hash',part_hash));
 end loop;
 select sum((x->>'existing_load_minutes')::numeric)into load from jsonb_array_elements(coalesce(scenario->'capacity'->'inputs'->'windows','[]'))x;
 -- Flatten each ordered chunk array once, straight from the SQL array (no
 -- jsonb[] -> jsonb round trip). Order stays chunk order, then element order.
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into assumptions from unnest(assumptions_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into sources from unnest(sources_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into recommendations from unnest(recommendations_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into actions from unnest(actions_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into timeline from unnest(timeline_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into models from unnest(models_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 if materials_null then materials:=null;else
  select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into materials from unnest(materials_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 end if;
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into metrics from unnest(metrics_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)into warnings from unnest(warnings_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o);
 v:=jsonb_build_object('contract_version','cp7.analysis.v2','run_id',p_run,'status',case when complete then 'PARTIAL'else 'BLOCKED'end,
  'snapshot',jsonb_build_object('snapshot_id',captured,'effective_as_of',captured,'known_as_of',captured,'generated_at',captured,'timezone','Asia/Jakarta',
   'knowledge_mode','CURRENT','capture_complete',complete,'fact_count',count_facts,'source_hash',hash),
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','native-available-history-fallback-1',
   'template','native-report-1','access_epoch',encode(extensions.digest(convert_to(a::text,'UTF8'),'sha256'),'hex')),
  'scope',jsonb_build_object('actor_scope_id',a->>'actor','allocation_scope_id','GLOBAL_NATIVE_PLANNING','display_filter','ALL'),
  'quality',jsonb_build_object('quantity',case when complete then 'COMPLETE'else 'UNKNOWN'end,
   'demand',case when jsonb_array_length(recommendations)=0 or exists(select 1 from jsonb_array_elements(n->'rows')x where x->'demand_estimate'->>'daily_pcs'is null)then 'UNKNOWN'else 'ASSUMED'end,
   'identity',case when exists(select 1 from jsonb_array_elements(coalesce(n->'match_results','[]'))x where x->'result'->>'match'in('UNKNOWN','NEEDS_CHECK'))then 'UNKNOWN'when complete then 'COMPLETE'else 'UNKNOWN'end,
   'timing',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'materials','UNKNOWN',
   'capacity',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'financial','UNKNOWN'),
  'scenario',jsonb_build_object('id',coalesce(c->'schedule'->>'plan_id','unreviewed-'||hash),'version',scenario_revision,'kind','CONDITIONAL','assumption_ids',plan_aids),
  'sources',sources,'recommendations',recommendations,'timeline',timeline,'actions',actions,'financial_readiness','BLOCKED',
  'stale',jsonb_build_object('is_stale',false,'reasons','[]'::jsonb),'assumptions',assumptions,'dependencies',dependencies,
  'policy_basis',jsonb_build_object('lead_time_new_days',cp7_analysis_native.fact(null,'DAY','[]'),'review_days',cp7_analysis_native.fact(null,'DAY','[]'),
   'buffer_mode','DAYS','buffer_days',cp7_analysis_native.fact(null,'DAY','[]'),'service_target',cp7_analysis_native.fact(null,'PROBABILITY','[]'),
   'rounding_multiple',cp7_analysis_native.fact(null,'PCS','[]')),
  'demand_models',models,'material_needs',materials,
  'capacity_checks',jsonb_build_array(jsonb_build_object('stage','SELECTED_HOMOGENEOUS_CENTRE','calendar_version',coalesce(c->'schedule'->>'plan_id','UNREVIEWED'),
   'available',cp7_analysis_native.fact(scenario->'capacity'->>'capacity_pcs','PCS',plan_refs,plan_aids),
   'existing_load',cp7_analysis_native.fact(load::text,'MINUTE',plan_refs,plan_aids),'feasible_new',cp7_analysis_native.fact(null,'PCS',plan_refs),
   'status',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end)),
  'metrics',metrics,'plan_comparisons','[]'::jsonb,'generation_warnings',warnings,'allocation_edges',edges);
 return v||jsonb_build_object('semantic_hash',encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex'));
end $$;

create table cp7_analysis_native.runs(id uuid primary key,actor uuid not null,request_id uuid not null,query jsonb not null,
 captured_at timestamptz not null,access_at_capture jsonb not null,facts jsonb not null,result jsonb not null,
 dependency_hash text not null,unique(actor,request_id));
alter table cp7_analysis_native.runs owner to cp7_capture;
alter table cp7_analysis_native.runs enable row level security;
create policy cp7_analysis_no_access on cp7_analysis_native.runs for all to public using(false)with check(false);
revoke all on cp7_analysis_native.runs from public,anon,authenticated,service_role;
create trigger immutable_analysis_run before update or delete on cp7_analysis_native.runs for each row execute function cp7_private.immutable_run();
create function cp7_analysis_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_native.runs%rowtype;c jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_analysis_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 c:=cp7_analysis_native.source_for(r.query,cp7_analysis_native.finance_mode(r.facts));
 if r.facts->'financial_source' is not null and r.facts->'financial_source'<>'null'::jsonb and coalesce(c->'financial_source','null')='null'::jsonb then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';
 end if;
 if coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')<>'null'::jsonb
  and coalesce(c->'financial_source'->'report'->'close_preflight','null')='null'::jsonb then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';
 end if;
 outcome:=jsonb_build_object('contract_version','cp7.native-analysis-run.v1','run_id',r.id,'request_id',r.request_id,
  'analysis',r.result,'product_labels',coalesce((select jsonb_agg(jsonb_build_object('target_key',x->>'root_id'||':'||(x->>'size_id'),
   'sku',coalesce(x->'commercial'->0->>'sku',x->>'sku'),'product_name',x->>'product_name')order by x->>'root_id')
   from jsonb_array_elements(r.facts->'facts'->'products')x),'[]'::jsonb),
  'source_state',case when cp7_analysis_native.fingerprint(c)=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'query',r.query,'financial_source',r.facts->'financial_source','apply_enabled',false,'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return outcome;
end $$;
create function cp7_analysis_native.capture(p_query jsonb,p_request uuid,p_finance text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_analysis_native.runs%rowtype;run_id uuid:=gen_random_uuid();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_finance is null or p_finance not in('INCLUDED','DEFERRED')then raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into r from cp7_analysis_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 -- One UUID is one request: the same query and the same finance mode.
 if found then if r.query<>q or cp7_analysis_native.finance_mode(r.facts)<>p_finance then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;return cp7_analysis_native.serve(r.id);end if;
 with source as materialized(select cp7_analysis_native.source_for(q,p_finance)c),calculated as materialized(select c,cp7_analysis_native.build(c,q,run_id,a)result from source)
 insert into cp7_analysis_native.runs(id,actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select run_id,(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,cp7_analysis_native.fingerprint(c)from calculated returning *into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return cp7_analysis_native.serve(r.id);
end $$;
alter function cp7_analysis_native.source_within(integer,integer)owner to cp7_capture;
alter function cp7_analysis_native.source()owner to cp7_capture;
alter function cp7_analysis_native.material_source(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_analysis_native.material_needs(jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_analysis_native.fingerprint(jsonb)owner to cp7_capture;
alter function cp7_analysis_native.finance_mode(jsonb)owner to cp7_capture;
alter function cp7_analysis_native.fact(text,text,jsonb,jsonb)owner to cp7_capture;
alter function cp7_analysis_native.build(jsonb,jsonb,uuid,jsonb)owner to cp7_capture;
alter function cp7_analysis_native.serve(uuid)owner to cp7_capture;
alter function cp7_analysis_native.capture(jsonb,uuid,text)owner to cp7_capture;
revoke all on all functions in schema cp7_analysis_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_analysis_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.capture(p_query,p_request,'INCLUDED')$$;
-- Stock and planning screens: the same compiler without the owner report or
-- the all-book provenance scan. No financial amount is substituted.
create function public.erp_cp7_capture_operational_analysis_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.capture(p_query,p_request,'DEFERRED')$$;
create function public.erp_cp7_read_analysis_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.serve(p_run)$$;
alter function public.erp_cp7_capture_analysis_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_operational_analysis_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_analysis_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_analysis_v1(jsonb,uuid),public.erp_cp7_capture_operational_analysis_v1(jsonb,uuid),public.erp_cp7_read_analysis_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_analysis_v1(jsonb,uuid),public.erp_cp7_capture_operational_analysis_v1(jsonb,uuid),public.erp_cp7_read_analysis_v1(uuid)to authenticated;
