do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

create function cp7_credit.source_operation_native_enter_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and action=p_action and source_id=p_source;
 perform cp7_credit.assert_source_operation_work_v1(w.operation_id);
 if w.phase<>'PREPARED'or w.before_source is distinct from cp7_credit.source_native_snapshot_v1(w.sale_id)
  or w.before_ordinal_input is distinct from cp7_credit.source_reconciliation_input_v1(w.sale_id)then
  raise exception 'CP7_CREDIT_SOURCE_NATIVE_ENTRY_CHANGED';end if;
 update cp7_credit.source_operation_work_v1 set phase='ENTERED'where operation_id=w.operation_id;
end $$;

create function cp7_credit.store_source_adjustments_v1(p_operation uuid,p_actual jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;inp jsonb;result jsonb;family jsonb;input_family jsonb;k jsonb;
 c cp7_credit.cohorts;manifest jsonb:='[]';components jsonb;parts jsonb;entry jsonb;x jsonb;y jsonb;phase text;
 plan uuid;component uuid;part uuid;request_ordinal integer:=0;component_ordinal integer;part_ordinal bigint;part_count bigint;
 amount numeric;piece numeric;binding text;
begin
 perform cp7_credit.assert_source_operation_work_v1(p_operation);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 if w.phase<>'ENTERED'or p_actual is distinct from cp7_credit.assert_source_actual_v1(w.operation_id)then
  raise exception 'CP7_CREDIT_SOURCE_ACTUAL_READ_CHANGED';end if;
 inp:=cp7_credit.source_reconciliation_input_v1(w.sale_id);result:=ow04_ordinal_wrapper.reconcile_v1(inp);
 if not coalesce((result->>'arithmetic_supported')::boolean,false)then raise exception 'CP7_CREDIT_SOURCE_ARITHMETIC_UNSUPPORTED';end if;
 for family in select value from jsonb_array_elements(result->'families')loop
  if not(family->>'has_reconciliation_effect')::boolean then continue;end if;
  if family->>'plan_kind'is distinct from'ADJUSTMENT'
   or exists(select 1 from jsonb_array_elements(family->'reconciliation_components')a where(a->>'amount')::numeric>=0)then
   raise exception 'CP7_CREDIT_SOURCE_RECONCILIATION_REVIEW_REQUIRED';end if;
  select ch.*into strict c from cp7_credit.cohorts ch where ch.family_id=(family#>>'{registration,family_id}')::uuid;
  if c.initial_mode<>'CREDIT'or exists(select 1 from cp7_credit.consumption_events where cohort_id=c.id)then
   raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO';end if;
  k:=cp7_credit.source_adjustment_kernel_v1(family);plan:=gen_random_uuid();request_ordinal:=request_ordinal+1;
  components:='[]';parts:='[]';component_ordinal:=0;
  for x in select value from jsonb_array_elements(k->'components')loop
   component:=gen_random_uuid();component_ordinal:=component_ordinal+1;amount:=(x->>'amount')::numeric;
   components:=components||jsonb_build_array(jsonb_build_object('id',component,'ordinal',component_ordinal,'component',x));
   part_count:=ceil(abs(amount)/cp7_credit.native_journal_cent_max())::bigint;
   for part_ordinal in 1..part_count loop
    part:=gen_random_uuid();piece:=sign(amount)*least(cp7_credit.native_journal_cent_max(),abs(amount)-(part_ordinal-1)*cp7_credit.native_journal_cent_max());
    parts:=parts||jsonb_build_array(jsonb_build_object('id',part,'component_id',component,'ordinal',part_ordinal,'amount',cp7_credit.cent_text(piece::cp7_credit.cent_amount)));
   end loop;
  end loop;
  manifest:=manifest||jsonb_build_array(jsonb_build_object('plan_id',plan,'family_id',c.family_id,
   'family_ordinal',(family#>>'{registration,ordinal}')::bigint,'cohort_id',c.id,'request_ordinal',request_ordinal,
   'kernel_sha256',cp7_credit.pg_jsonb_sha256(k),'components',components,'parts',parts));
 end loop;
 update cp7_credit.source_operation_work_v1 set phase='RECONCILING',actual_source=p_actual->'actual_source',
  actual_source_proof=p_actual->'actual_source_proof',actual_ordinal_input=inp,actual_ordinal_result=result,plan_manifest=manifest
  where operation_id=w.operation_id;
 binding:=cp7_credit.source_operation_binding_sha256_v1(w.operation_id);
 for entry in select value from jsonb_array_elements(manifest)loop
  select f into strict family from jsonb_array_elements(result->'families')f where f#>>'{registration,family_id}'=entry->>'family_id';
  select f into strict input_family from jsonb_array_elements(inp->'families')f where f->>'family_id'=entry->>'family_id';
  k:=cp7_credit.source_adjustment_kernel_v1(family);plan:=(entry->>'plan_id')::uuid;
  insert into cp7_credit.recognition_plans(id,cohort_id,plan_kind,owning_action,actor,request_id,request_ordinal,payload_sha256,review_sha256,
   family_root_sale_id,before_events,added_events,kernel_result,kernel_version,before_source_sha256,after_source_sha256,support_sha256_pg,
   components_sha256_pg,parts_sha256_pg,net_amount,has_recognition_effect,expected_component_count,expected_part_count)
  values(plan,(entry->>'cohort_id')::uuid,'ADJUSTMENT',w.action,w.actor,w.request_id,(entry->>'request_ordinal')::integer,w.payload_sha256,binding,
   w.sale_id,k->'before_events',k->'added_events',k,k->>'kernel_version',k->>'before_source_sha256',k->>'after_source_sha256',
   cp7_credit.pg_jsonb_sha256(k->'support'),cp7_credit.pg_jsonb_sha256(k->'components'),cp7_credit.pg_jsonb_sha256(entry->'parts'),
   (k->>'net_current_k')::numeric,true,jsonb_array_length(k->'components'),jsonb_array_length(entry->'parts'));
  for x in select value from jsonb_array_elements(entry->'components')loop
   y:=x->'component';
   insert into cp7_credit.recognition_components(id,plan_id,ordinal,economic_date,transaction_date,amount,previous_economic_date,previous_transaction_date,corners,kernel_component,component_sha256_pg)
   values((x->>'id')::uuid,plan,(x->>'ordinal')::integer,(y->>'economic_date')::date,(y->>'transaction_date')::date,(y->>'amount')::numeric,
    (y->>'previous_economic_date')::date,(y->>'previous_transaction_date')::date,y->'corners',y,cp7_credit.pg_jsonb_sha256(y));
  end loop;
  for x in select value from jsonb_array_elements(entry->'parts')loop
   insert into cp7_credit.component_parts(id,component_id,ordinal,amount)
    values((x->>'id')::uuid,(x->>'component_id')::uuid,(x->>'ordinal')::bigint,(x->>'amount')::numeric);
  end loop;
  select *into strict c from cp7_credit.cohorts where id=(entry->>'cohort_id')::uuid;
  foreach phase in array array['BEFORE','ADDED']loop
   for x in select value from jsonb_array_elements(case when phase='BEFORE'then k->'before_events'else k->'added_events'end)loop
    insert into cp7_credit.plan_support_events(plan_id,event_id,phase,kind,amount,economic_date,transaction_date,source_sha256,journal_id,source_fact_snapshot)
    values(plan,x->>'id',phase,x->>'kind',(x->>'amount')::numeric,(x->>'economic_date')::date,(x->>'transaction_date')::date,x->>'source_sha256',
     substring(x->>'id'from 9)::uuid,ow04_source_proposal.financial_journal_payload(substring(x->>'id'from 9)::uuid,c.ar_account_id));
   end loop;
  end loop;
  insert into cp7_credit.source_operation_plans_v1(plan_id,operation_id,family_id,family_ordinal,full_family_result,canonical_plan,
   before_retained_events,before_consumptions,source_binding_sha256)
  values(plan,w.operation_id,(entry->>'family_id')::uuid,(entry->>'family_ordinal')::bigint,family,k,
   input_family->'retained_recognition',input_family->'consumptions',binding);
 end loop;
 perform cp7_credit.assert_source_operation_plan_set_v1(w.operation_id);
 perform cp7_credit.source_adjustment_fresh_v1(w.operation_id);
end $$;

create function cp7_credit.materialize_source_operation_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;profile jsonb;objects jsonb;new_objects jsonb;x jsonb;marker uuid;
 binding text;manifest jsonb;manifest_sha text;
begin
 perform cp7_credit.assert_source_operation_work_v1(p_operation);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 perform cp7_credit.source_adjustment_fresh_v1(w.operation_id);
 perform cp7_credit.assert_source_operation_part_seals_v1(w.operation_id);
 profile:=cp7_credit.current_materialized_objects(w.sale_id,w.sale_id,w.sale_id);objects:=profile->'actual_objects';
 select coalesce(jsonb_agg(obj order by obj->>'object_kind'collate"C",obj->>'object_id'collate"C"),'[]')into new_objects
  from jsonb_array_elements(objects)obj where not exists(select 1 from cp7_credit.financial_materialization_objects old
   where old.object_kind=obj->>'object_kind'and old.object_id=(obj->>'object_id')::uuid);
 binding:=cp7_credit.source_operation_binding_sha256_v1(w.operation_id);
 if jsonb_array_length(new_objects)>0 then
  marker:=gen_random_uuid();
  insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,
   source_plan_sha256,actual_objects,actual_objects_sha256)
  values(marker,w.sale_id,w.actor,w.request_id,1,w.action,w.payload_sha256,binding,new_objects,cp7_credit.pg_jsonb_sha256(new_objects));
  for x in select value from jsonb_array_elements(new_objects)loop
   insert into cp7_credit.financial_materialization_objects(object_kind,object_id,materialization_id,fact_sha256)
    values(x->>'object_kind',(x->>'object_id')::uuid,marker,x->>'fact_sha256');
  end loop;
 end if;
 manifest:=jsonb_build_object('contract_version','ow04.source-operation-actual-manifest.v1','operation_id',w.operation_id,
  'source_binding_sha256',binding,'financial_marker_id',marker,'actual_objects',new_objects);
 manifest_sha:=cp7_credit.pg_jsonb_sha256(manifest);
 insert into cp7_credit.source_operation_materializations_v1(operation_id,operation_ordinal,predecessor_operation_id,backend_pid,transaction_id,
  actor,request_id,action,sale_id,source_id,expected_version,payload,payload_sha256,authority_snapshot,before_source,before_ordinal_input,
  before_ordinal_result,before_financial_profile,account_facts,period_snapshot,actual_source,actual_source_proof,actual_ordinal_input,
  actual_ordinal_result,plan_manifest,financial_marker_id,actual_objects,actual_manifest_sha256)
 values(w.operation_id,w.operation_ordinal,w.predecessor_operation_id,w.backend_pid,w.transaction_id,w.actor,w.request_id,w.action,w.sale_id,
  w.source_id,w.expected_version,w.payload,w.payload_sha256,w.authority_snapshot,w.before_source,w.before_ordinal_input,w.before_ordinal_result,
  w.before_financial_profile,w.account_facts,w.period_snapshot,w.actual_source,w.actual_source_proof,w.actual_ordinal_input,w.actual_ordinal_result,
  w.plan_manifest,marker,new_objects,manifest_sha);
 update cp7_credit.source_operation_work_v1 set phase='RECONCILED',active_plan_id=null,financial_marker_id=marker,actual_manifest_sha256=manifest_sha
  where operation_id=w.operation_id;
 delete from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor and request_id=w.request_id;
 perform cp7_credit.assert_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
end $$;

-- Exact Native before-E hook. Unregistered/EMPTY Native paths remain original;
-- a recognized source without the new owning request still fails at entry.
create function cp7_credit.source_operation_native_reconcile_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;actual jsonb;c record;
begin
 if not cp7_credit.source_operation_owns_v1(p_action,p_source)then return;end if;
 select *into strict w from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and action=p_action and source_id=p_source;
 actual:=cp7_credit.assert_source_actual_v1(w.operation_id);
 perform cp7_credit.store_source_adjustments_v1(w.operation_id,actual);
 for c in select cc.id from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_components cc on cc.plan_id=sp.plan_id
  where sp.operation_id=w.operation_id order by sp.family_ordinal,cc.ordinal loop
  perform cp7_credit.post_source_adjustment_component_v1(c.id);
 end loop;
 perform cp7_credit.materialize_source_operation_v1(w.operation_id);
end $$;

create function cp7_credit.source_operation_native_complete_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;profile jsonb;actual jsonb;manifest jsonb;header_proof jsonb;
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and action=p_action and source_id=p_source;
 perform cp7_credit.assert_source_operation_work_v1(w.operation_id);
 if w.phase<>'RECONCILED'then raise exception 'CP7_CREDIT_SOURCE_RECONCILIATION_NOT_COMPLETE';end if;
 perform cp7_credit.assert_source_native_trigger_census_v1();
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 header_proof:=cp7_credit.source_native_terminal_header_v1(w.actual_source,actual,(w.actual_source_proof->>'inverse_journal_id')::uuid);
 -- The first adapter does not adopt terminal cost/cache revaluations. The
 -- opaque support hash includes the very header metadata proven above;
 -- every raw physical/HPP/source row and complete book vector stays exact.
 if actual-array['sale','hpp_support']is distinct from w.actual_source-array['sale','hpp_support']then
  raise exception 'CP7_CREDIT_SOURCE_TERMINAL_EFFECT_UNQUALIFIED';end if;
 perform cp7_credit.source_first_nonpo_hpp_alignment_v1(actual);
 profile:=cp7_credit.inspect_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
 perform cp7_credit.assert_source_final_ar_status_v1(w.sale_id,actual,profile);
 manifest:=jsonb_build_object('contract_version','ow04.source-operation-completion.v1','operation_id',w.operation_id,
  'actual_manifest_sha256',w.actual_manifest_sha256,'final_native_source',actual,'final_profile',profile,'header_proof',header_proof);
 insert into cp7_credit.source_operation_completions_v1(operation_id,final_native_source,final_profile,final_manifest_sha256)
  values(w.operation_id,actual,profile,cp7_credit.pg_jsonb_sha256(manifest));
 update cp7_credit.source_operation_work_v1 set phase='NATIVE_COMPLETE'where operation_id=w.operation_id;
 perform cp7_credit.assert_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
end $$;

create function cp7_credit.source_request_finish_v1(p_request uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;c cp7_credit.source_operation_completions_v1;
begin
 select *into w from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 if not found then
  -- No newly owned source is expected on unchanged EMPTY/nonparticipant paths.
  if exists(select 1 from cp7_credit.source_operation_materializations_v1 where actor=auth.uid()and request_id=p_request)then
   raise exception 'CP7_CREDIT_SOURCE_OWN_WORK_MISSING';end if;
  return;
 end if;
 perform cp7_credit.assert_source_operation_work_v1(w.operation_id);
 select *into strict c from cp7_credit.source_operation_completions_v1 where operation_id=w.operation_id;
 if w.phase<>'NATIVE_COMPLETE'or c.final_native_source is distinct from cp7_credit.source_native_snapshot_v1(w.sale_id)
  or exists(select 1 from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_SOURCE_NATIVE_TAIL_NOT_COMPLETE';end if;
 perform cp7_credit.assert_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
 perform cp7_credit.assert_source_completion_v1(w.operation_id);
 delete from cp7_credit.source_operation_work_v1 where operation_id=w.operation_id;
end $$;

do $private_source_coordinator$declare sig text;begin
 foreach sig in array array['source_operation_native_enter_v1(text,uuid)','store_source_adjustments_v1(uuid,jsonb)',
  'materialize_source_operation_v1(uuid)','source_operation_native_reconcile_v1(text,uuid)',
  'source_operation_native_complete_v1(text,uuid)','source_request_finish_v1(uuid)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_coordinator$;
