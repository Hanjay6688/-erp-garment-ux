do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.assert_owner_context(p_plan uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare p cp7_credit.recognition_plans;w cp7_credit.initial_return_work;e cp7_credit.execution_context;
begin
 select *into strict p from cp7_credit.recognition_plans where id=p_plan;
 select *into strict w from cp7_credit.initial_return_work where plan_id=p.id and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 perform cp7_credit.assert_return_owner_context(w.return_id);
 select *into strict e from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if(p.plan_kind,p.owning_action,p.actor,p.request_id,p.payload_sha256,p.review_sha256)is distinct from
  ('INITIAL','RETURN_SETTLEMENT',w.actor,w.request_id,w.payload_sha256,w.quote_sha256)
  or(e.plan_id,e.request_id,e.payload_sha256,e.review_sha256,e.authority_snapshot)is distinct from
   (p.id,w.request_id,w.payload_sha256,w.quote_sha256,w.authority_snapshot)then raise exception 'CP7_CREDIT_INITIAL_PLAN_OWNER_MISMATCH';end if;
end $$;

create function cp7_credit.actual_own_return_events_v1(p_return uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')from erp.sales_returns r,
  lateral jsonb_array_elements(cp7_credit.initial_base_events_v1(r.sale_id))x
  where r.id=p_return and x->>'id'in(select'journal:'||j.id::text from erp.journal_entries j
   where j.source_type='SALES_RETURN'and j.source_id=r.id and j.reversal_of_id is null)
$$;

create function cp7_credit.rebuild_locked_plan(p_plan uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;fresh jsonb;ordinal_result jsonb;family_result jsonb;
begin
 perform cp7_credit.assert_owner_context(p_plan);
 select *into strict w from cp7_credit.initial_return_work where plan_id=p_plan;
 -- All source locks were acquired by sealer, prior to period. This reentry
 -- performs ONLY reads. Newly appearing source sets differ and refuse.
 if cp7_credit.initial_preserved_source_v1(w.source_sale_id,w.return_id)is distinct from w.source_snapshot->'preserved_source'
  or cp7_credit.initial_base_events_v1(w.source_sale_id,w.return_id)is distinct from w.source_snapshot->'before_events'then
  raise exception 'CP7_CREDIT_LOCKED_PLAN_SOURCE_CHANGED';end if;
 fresh:=ow04_pure_kernel.recognition_plan_v1(w.source_snapshot->'before_events',cp7_credit.actual_own_return_events_v1(w.return_id));
 ordinal_result:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit.initial_ordinal_input_v1(w.source_sale_id,p_plan));
 select f into strict family_result from jsonb_array_elements(ordinal_result->'families')f where f->'registration'->>'family_id'=w.family_id::text;
 if family_result->'source_target'is distinct from fresh or not(ordinal_result->>'arithmetic_supported')::boolean then
  raise exception 'CP7_CREDIT_PENDING_ORDINAL_TARGET_CHANGED';end if;
 if fresh->'components'is distinct from w.projected_kernel->'components'
  or fresh->'net_current_k'is distinct from w.projected_kernel->'net_current_k'
  or fresh->'has_recognition_effect'is distinct from w.projected_kernel->'has_recognition_effect'then
  raise exception 'CP7_CREDIT_PROJECTED_ACTUAL_KERNEL_CHANGED';end if;
 return fresh;
end $$;

create function cp7_credit.assert_source_admission(p_plan uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;p cp7_credit.recognition_plans;k numeric;r numeric;
begin
 perform cp7_credit.assert_owner_context(p_plan);
 select *into strict p from cp7_credit.recognition_plans where id=p_plan;
 select *into strict w from cp7_credit.initial_return_work where plan_id=p_plan;
 perform cp7_credit.assert_zero_excess_v1(p.before_events);
 k:=(p.kernel_result->>'net_current_k')::numeric;r:=(w.projection->>'return_amount')::numeric;
 if p.plan_kind<>'INITIAL'or k<0 or k>r or w.origin<>'REVIEWED_SETTLEMENT'
  or p.added_events is distinct from cp7_credit.actual_own_return_events_v1(w.return_id)
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=w.source_sale_id)
  or exists(select 1 from cp7_credit.recognition_plans other where other.cohort_id=p.cohort_id and other.id<>p.id)
  or exists(select 1 from cp7_credit.cohorts other join cp7_credit.return_families f on f.id=other.family_id
   where f.family_root_sale_id=w.source_sale_id and other.id<>p.cohort_id)then raise exception 'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID';end if;
 if ow04_source_proposal.verify_return_member_v1(w.return_id)->>'member_kind'<>'ORIGINAL'then
  raise exception 'CP7_CREDIT_INITIAL_ORIGINAL_MEMBER_REQUIRED';end if;
end $$;

create function cp7_credit.check_credit_account(p_cohort uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.cohorts;w cp7_credit.initial_return_work;now_facts jsonb;
begin
 select *into strict c from cp7_credit.cohorts where id=p_cohort;
 select *into strict w from cp7_credit.initial_return_work where cohort_id=c.id and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 perform cp7_credit.assert_owner_context(c.initial_plan_id);
 now_facts:=cp7_credit.credit_account_facts_v1(c.credit_account_id);
 if now_facts->'account'is distinct from c.credit_account_snapshot->'account'
  or c.credit_account_snapshot is distinct from w.credit_account_snapshot
  or c.ar_account_id is distinct from(w.projection->>'ar_account_id')::uuid
  or c.ar_account_id=c.credit_account_id then raise exception 'CP7_CREDIT_ACCOUNT_SOURCE_CHANGED';end if;
end $$;

create function cp7_credit.store_initial_plan_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;fact jsonb;assignment jsonb;member jsonb;actual_added jsonb;actual_k jsonb;mapping jsonb;
 family uuid:=gen_random_uuid();cohort uuid;plan uuid;first_j uuid;ordinal bigint;previous_family uuid;ordinal_input jsonb;ordinal_result jsonb;family_result jsonb;
 x jsonb;phase text;component uuid;part uuid;n integer:=0;i bigint;parts jsonb;amount numeric;piece numeric;part_count bigint:=0;
begin
 select *into strict w from cp7_credit.initial_return_work where operation_id=p_operation;
 perform cp7_credit.assert_return_owner_context(w.return_id);
 fact:=ow04_source_proposal.return_fact_v1(w.return_id);
 if fact->>'sale_id'<>w.source_sale_id::text or fact->>'family_root_sale_id'<>w.source_sale_id::text then
  raise exception 'CP7_CREDIT_ACTUAL_FAMILY_SOURCE_MISMATCH';end if;
 actual_added:=cp7_credit.actual_own_return_events_v1(w.return_id);
 actual_k:=ow04_pure_kernel.recognition_plan_v1(w.source_snapshot->'before_events',actual_added);
 if actual_k->'components'is distinct from w.projected_kernel->'components'
  or actual_k->'net_current_k'is distinct from w.projected_kernel->'net_current_k'
  or actual_k->'has_recognition_effect'is distinct from w.projected_kernel->'has_recognition_effect'
  or(fact->>'financial_state'='NO_JOURNAL')is distinct from(w.projection->>'journal_effect'='NO_JOURNAL')then
  raise exception 'CP7_CREDIT_ACTUAL_RETURN_FINANCIAL_DECISION_CHANGED';end if;
 if fact->>'financial_state'='JOURNAL'and not exists(select 1 from erp.journal_entries j where j.id=(fact->>'source_journal_id')::uuid
  and j.economic_date=(w.projection->>'economic_date')::date and j.transaction_date=(w.projection->>'planned_book_date')::date
  and cp7_credit.initial_line_semantics_v1((select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,
   'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'product_id',l.product_id,'po_id',l.po_id,'debit',l.debit,'credit',l.credit))
   from erp.journal_lines l where l.journal_entry_id=j.id))=cp7_credit.initial_line_semantics_v1(w.projection->'lines'))then
  raise exception 'CP7_CREDIT_ACTUAL_RETURN_JOURNAL_MAPPING_CHANGED';end if;
 mapping:=jsonb_build_object('contract_version','ow04.projected-to-actual-return-proof.v1','projection_sha256',w.projection_sha256,
  'draft_sha256',w.projection->'draft_sha256','actual_return_id',w.return_id,'actual_financial_fact',fact,
  'actual_events',actual_added,'projected_kernel_components',w.projected_kernel->'components','actual_kernel_components',actual_k->'components',
  'actual_item_mapping',(select jsonb_agg(jsonb_build_object('allocation_id',ri.sale_stock_allocation_id,'actual_return_item_id',ri.id,
   'actual_original_movement_id',(select m.id from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=ri.id and m.reversal_of_id is null))
   order by ri.sale_stock_allocation_id)from erp.sales_return_items ri where ri.return_id=w.return_id));
 select coalesce(max(family_ordinal),0)+1 into ordinal from cp7_credit.return_families where family_root_sale_id=w.source_sale_id;
 select id into previous_family from cp7_credit.return_families where family_root_sale_id=w.source_sale_id and family_ordinal=ordinal-1;
 if exists(select 1 from erp.sales_returns r where r.sale_id=w.source_sale_id and r.status<>'DRAFT'and r.id<>w.return_id
  and not exists(select 1 from cp7_credit.return_family_members m where m.return_id=r.id))then
  raise exception 'CP7_CREDIT_LEGACY_RETURN_ORDER_NOT_QUALIFIED';end if;
 assignment:=jsonb_build_object('contract_version','ow04.return-family-assignment.v1','family_id',family,'family_root_sale_id',w.source_sale_id,
  'family_ordinal',ordinal::text,'first_return_id',w.return_id,'previous_family_id',previous_family,'actor',w.actor,'request_id',w.request_id);
 insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,assignment_kind,assignment_proof,source_sha256,actor,request_id)
 values(family,w.source_sale_id,ordinal,w.return_id,'NEW_POST',assignment,ow04_source_proposal.sha(assignment),w.actor,w.request_id);
 member:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',family,'family_root_sale_id',w.source_sale_id,
  'return_id',w.return_id,'sale_id',w.source_sale_id,'member_kind','ORIGINAL','predecessor_return_id',null,'native_lineage_id',null,'return_item_lineage','{}'::jsonb,
  'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id','financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 insert into cp7_credit.return_family_members(family_id,return_id,member_kind,source_journal_id,source_sha256,actual_lineage_snapshot,actor,request_id,financial_state,financial_source_proof)
 values(family,w.return_id,'ORIGINAL',(fact->>'source_journal_id')::uuid,ow04_source_proposal.sha(member),member,w.actor,w.request_id,fact->>'financial_state',fact->'no_journal_proof');
 update cp7_credit.initial_return_work set family_id=family,family_ordinal=ordinal,actual_fact=fact,actual_event=actual_added,actual_kernel=actual_k,
  projection_actual_proof=mapping where operation_id=w.operation_id;
 if w.origin='REVIEWED_SETTLEMENT'then
  update cp7_credit.return_command_scope set family_id=family,family_ordinal=ordinal where backend_pid=w.backend_pid and transaction_id=w.transaction_id;
 end if;
 perform ow04_source_proposal.verify_return_member_v1(w.return_id);
 ordinal_input:=cp7_credit.initial_ordinal_input_v1(w.source_sale_id);
 ordinal_result:=ow04_ordinal_wrapper.reconcile_v1(ordinal_input);
 select f into strict family_result from jsonb_array_elements(ordinal_result->'families')f where f->'registration'->>'family_id'=family::text;
 if family_result->'source_target'is distinct from actual_k or not(ordinal_result->>'arithmetic_supported')::boolean
  or exists(select 1 from jsonb_array_elements(ordinal_result->'families')f where f->'registration'->>'family_id'<>family::text
   and(f->>'has_reconciliation_effect')::boolean)then raise exception 'CP7_CREDIT_INITIAL_ORDINAL_TARGET_CHANGED';end if;
 update cp7_credit.initial_return_work set source_snapshot=source_snapshot||jsonb_build_object('actual_ordinal_input',ordinal_input,'actual_ordinal_result',ordinal_result)
  where operation_id=w.operation_id;
 if not(actual_k->>'has_recognition_effect')::boolean then return;end if;
 if w.origin<>'REVIEWED_SETTLEMENT'or w.settlement->>'mode'is null then raise exception 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;
 cohort:=gen_random_uuid();plan:=gen_random_uuid();
 select id into strict first_j from erp.journal_entries where source_type='SALE'and source_id=w.source_sale_id and reversal_of_id is null and status='POSTED';
 -- IDs are planned before inserts solely for deferred circular FK ownership.
 -- They never stand in for a Native source journal UUID in a read-only quote.
 insert into cp7_credit.cohorts(id,family_id,source_sale_id,source_return_id,customer_id,ar_account_id,source_ar_snapshot,credit_account_id,
  credit_account_snapshot,initial_mode,initial_net_amount,initial_plan_id,source_sale_journal_id,source_return_journal_id,
  source_sale_sha256,source_return_sha256,actor,request_id,source_return_financial_state,source_return_financial_proof)
 values(cohort,family,w.source_sale_id,w.return_id,(fact->>'customer_id')::uuid,(w.projection->>'ar_account_id')::uuid,w.source_snapshot->'source'->'ar_account',
  (w.settlement->>'credit_account_id')::uuid,w.credit_account_snapshot,w.settlement->>'mode',(actual_k->>'net_current_k')::numeric,plan,first_j,
  (fact->>'source_journal_id')::uuid,ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(first_j,(w.projection->>'ar_account_id')::uuid)),
  fact->>'financial_source_sha256',w.actor,w.request_id,fact->>'financial_state',fact->'no_journal_proof');
 -- Parts hash is finalized before the immutable plan row. Child creation below
 -- needs its parent, so preallocate the complete manifest in local JSON first.
 parts:='[]';
 for x in select value from jsonb_array_elements(actual_k->'components')loop
  n:=n+1;component:=gen_random_uuid();amount:=(x->>'amount')::numeric;
  for i in 1..ceil(abs(amount)/cp7_credit.native_journal_cent_max())::bigint loop
   piece:=sign(amount)*least(cp7_credit.native_journal_cent_max(),abs(amount)-(i-1)*cp7_credit.native_journal_cent_max());part:=gen_random_uuid();part_count:=part_count+1;
   parts:=parts||jsonb_build_array(jsonb_build_object('id',part,'component_id',component,'ordinal',i,'amount',cp7_credit.cent_text(piece),'component_ordinal',n,'component',x));
  end loop;
 end loop;
 insert into cp7_credit.recognition_plans(id,cohort_id,plan_kind,owning_action,actor,request_id,request_ordinal,payload_sha256,review_sha256,family_root_sale_id,
  before_events,added_events,kernel_result,kernel_version,before_source_sha256,after_source_sha256,support_sha256_pg,components_sha256_pg,parts_sha256_pg,
  net_amount,has_recognition_effect,expected_component_count,expected_part_count)
 values(plan,cohort,'INITIAL','RETURN_SETTLEMENT',w.actor,w.request_id,1,w.payload_sha256,w.quote_sha256,w.source_sale_id,actual_k->'before_events',actual_k->'added_events',actual_k,
  actual_k->>'kernel_version',actual_k->>'before_source_sha256',actual_k->>'after_source_sha256',cp7_credit.pg_jsonb_sha256(actual_k->'support'),cp7_credit.pg_jsonb_sha256(actual_k->'components'),
  cp7_credit.pg_jsonb_sha256((select jsonb_agg(z-'component'-'component_ordinal'order by(z->>'component_ordinal')::integer,(z->>'ordinal')::bigint)from jsonb_array_elements(parts)z)),
  (actual_k->>'net_current_k')::numeric,true,jsonb_array_length(actual_k->'components'),part_count);
 for x in select jsonb_build_object('component',z->'component','component_id',z->'component_id','ord',z->'component_ordinal')
  from jsonb_array_elements(parts)z group by z->'component',z->'component_id',z->'component_ordinal'order by(z->>'component_ordinal')::integer loop
  insert into cp7_credit.recognition_components(id,plan_id,ordinal,economic_date,transaction_date,amount,previous_economic_date,previous_transaction_date,corners,kernel_component,component_sha256_pg)
  values((x->>'component_id')::uuid,plan,(x->>'ord')::integer,(x->'component'->>'economic_date')::date,(x->'component'->>'transaction_date')::date,
   (x->'component'->>'amount')::numeric,(x->'component'->>'previous_economic_date')::date,(x->'component'->>'previous_transaction_date')::date,
   x->'component'->'corners',x->'component',cp7_credit.pg_jsonb_sha256(x->'component'));
 end loop;
 for x in select value from jsonb_array_elements(parts)loop
  insert into cp7_credit.component_parts values((x->>'id')::uuid,(x->>'component_id')::uuid,(x->>'ordinal')::bigint,(x->>'amount')::numeric);
 end loop;
 foreach phase in array array['BEFORE','ADDED']loop
  for x in select value from jsonb_array_elements(case when phase='BEFORE'then actual_k->'before_events'else actual_k->'added_events'end)loop
   insert into cp7_credit.plan_support_events(plan_id,event_id,phase,kind,amount,economic_date,transaction_date,source_sha256,journal_id,source_fact_snapshot)
   values(plan,x->>'id',phase,x->>'kind',(x->>'amount')::numeric,(x->>'economic_date')::date,(x->>'transaction_date')::date,x->>'source_sha256',
    substring(x->>'id'from 9)::uuid,ow04_source_proposal.financial_journal_payload(substring(x->>'id'from 9)::uuid,(w.projection->>'ar_account_id')::uuid));
  end loop;
 end loop;
 insert into cp7_credit.plan_dependencies values(plan,'SALE',w.source_sale_id,ow04_source_proposal.sha(w.source_snapshot->'preserved_source'->'sale')),
  (plan,'RETURN',w.return_id,fact->>'financial_source_sha256'),(plan,'RETURN_FAMILY',family,ow04_source_proposal.sha(assignment));
 for x in select value from jsonb_array_elements(w.source_snapshot->'preserved_source'->'payments')loop
  insert into cp7_credit.plan_dependencies values(plan,'PAYMENT',(x->>'id')::uuid,ow04_source_proposal.sha(x));
 end loop;
 update cp7_credit.initial_return_work set cohort_id=cohort,plan_id=plan where operation_id=w.operation_id;
 update cp7_credit.execution_context set plan_id=plan where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
end $$;

create function cp7_credit.materialize_initial_objects_v1(p_operation uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;a jsonb;objects jsonb;new_objects jsonb;materialization uuid:=gen_random_uuid();x jsonb;
begin
 select *into strict w from cp7_credit.initial_return_work where operation_id=p_operation;
 perform cp7_credit.assert_return_owner_context(w.return_id);
 a:=cp7_credit.current_materialized_objects(w.source_sale_id,w.source_sale_id,w.source_sale_id);objects:=a->'actual_objects';
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into new_objects
  from jsonb_array_elements(objects)x where not exists(select 1 from cp7_credit.financial_materialization_objects o
   where o.object_kind=x->>'object_kind'and o.object_id=(x->>'object_id')::uuid);
 if jsonb_array_length(new_objects)=0 then raise exception 'CP7_CREDIT_NEW_MATERIALIZATION_EMPTY';end if;
 insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
 values(materialization,w.source_sale_id,w.actor,w.request_id,1,case when w.origin='ORDINARY'then'RETURN'else'RETURN_SETTLEMENT'end,
  w.payload_sha256,w.projection_sha256,new_objects,cp7_credit.pg_jsonb_sha256(new_objects));
 for x in select value from jsonb_array_elements(new_objects)loop
  insert into cp7_credit.financial_materialization_objects values(x->>'object_kind',(x->>'object_id')::uuid,materialization,x->>'fact_sha256');
 end loop;
 update cp7_credit.initial_return_work set materialization_id=materialization,phase='MATERIALIZED'where operation_id=w.operation_id;
 return a;
end $$;

create function cp7_credit.native_return_complete(p_return uuid,p_refund numeric,p_net_after numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;x record;a jsonb;recognition_sha text;refund_op uuid;full_k numeric;result numeric;
begin
 if cp7_credit.is_unchanged_native_return_v1(p_return)then
  return(select coalesce(sum(p.amount),0)from erp.sales_payments p join erp.sales_returns r on r.sale_id=p.sale_id where r.id=p_return and p.status='POSTED');
 end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 if w.phase<>'ENTERED'or(p_refund,p_net_after)is distinct from((w.projection->>'return_amount')::numeric,(w.projection->>'net_after')::numeric)then
  raise exception 'CP7_CREDIT_NATIVE_COMPLETION_TOTALS_CHANGED';end if;
 perform cp7_credit.store_initial_plan_v1(w.operation_id);
 select *into strict w from cp7_credit.initial_return_work where operation_id=w.operation_id;
 if w.plan_id is not null then
  for x in select id from cp7_credit.recognition_components where plan_id=w.plan_id order by ordinal loop perform cp7_credit.post_component(x.id);end loop;
 end if;
 a:=cp7_credit.materialize_initial_objects_v1(w.operation_id);
 recognition_sha:=cp7_credit.pg_jsonb_sha256(a->'actual_objects');
 full_k:=(w.actual_kernel->>'net_current_k')::numeric;
 if w.settlement->>'mode'='REFUND'then
  if full_k<=0 or w.cohort_id is null then raise exception 'CP7_CREDIT_NO_ZERO_OR_UNBOUND_REFUND';end if;
  refund_op:=gen_random_uuid();
  update cp7_credit.initial_return_work set refund_operation_id=refund_op where operation_id=w.operation_id;
 end if;
 select *into strict w from cp7_credit.initial_return_work where operation_id=w.operation_id;
 insert into cp7_credit.initial_return_materializations(operation_id,actor,request_id,source_sale_id,source_return_id,family_id,family_ordinal,cohort_id,plan_id,origin,
  expected_version,legacy_payload,settlement,payload_sha256,quote_sha256,authority_snapshot,source_snapshot,source_lock_sha256,projection,projection_sha256,
  prior_causal,prior_causal_manifest,period_snapshot,actual_fact,actual_event,actual_kernel,projection_actual_proof,projection_actual_proof_sha256,
  recognition_manifest_sha256,materialization_id,refund_operation_id)
 values(w.operation_id,w.actor,w.request_id,w.source_sale_id,w.return_id,w.family_id,w.family_ordinal,w.cohort_id,w.plan_id,w.origin,w.expected_version,w.legacy_payload,w.settlement,
  w.payload_sha256,w.quote_sha256,w.authority_snapshot,w.source_snapshot,w.source_lock_sha256,w.projection,w.projection_sha256,w.prior_causal,w.prior_causal_manifest,w.period_snapshot,
  w.actual_fact,w.actual_event,w.actual_kernel,w.projection_actual_proof,ow04_source_proposal.sha(w.projection_actual_proof),recognition_sha,w.materialization_id,refund_op);
 if refund_op is not null then
  insert into cp7_credit.initial_refund_operations(id,cohort_id,initial_plan_id,actor,request_id,backend_pid,transaction_id,root_sale_id,current_leaf_id,full_amount,
   cash_account_id,physical_at,reason,reference,payload_sha256,quote_sha256,source_lock_sha256,projection_sha256,recognition_manifest_sha256,required_book_floor,
   materialization_ordinal,authority_snapshot,cash_account_snapshot,book_floor_manifest)
  values(refund_op,w.cohort_id,w.plan_id,w.actor,w.request_id,w.backend_pid,w.transaction_id,w.source_sale_id,w.source_sale_id,full_k,(w.settlement->>'cash_account_id')::uuid,
   (w.settlement->>'refund_physical_at')::timestamptz,btrim(w.legacy_payload->>'change_reason'),w.settlement->>'reference',w.payload_sha256,w.quote_sha256,
   w.source_lock_sha256,w.projection_sha256,recognition_sha,(w.projection->'refund_book_plan'->>'selected_book_date')::date,
   2,w.authority_snapshot,w.cash_account_snapshot,w.projection->'refund_book_plan');
  perform cp7_credit.post_initial_refund(refund_op,w.cohort_id);
 end if;
 perform cp7_credit.assert_current_materialized_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id);
 result:=(w.projection->>'raw_paid')::numeric-full_k;
 if result<0 or result>p_net_after then raise exception 'CP7_CREDIT_ACTUAL_EFFECTIVE_PAID_INVALID';end if;
 update cp7_credit.return_native_scope set completed=true,guard_effective_paid=result where backend_pid=w.backend_pid and transaction_id=w.transaction_id and return_id=p_return;
 update cp7_credit.initial_return_work set phase='COMPLETE'where operation_id=w.operation_id;
 perform cp7_credit.assert_return_owner_context(p_return);return result;
end $$;
