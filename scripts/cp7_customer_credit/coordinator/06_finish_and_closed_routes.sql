do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.assert_refund_operation_v1(p_operation uuid,p_cohort uuid,p_phase text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.initial_refund_operations;w cp7_credit.initial_return_work;m cp7_credit.initial_return_materializations;
 ch cp7_credit.cohorts;a jsonb;manifest jsonb;book_plan jsonb;floor date;count_c bigint;
begin
 if p_phase not in('PREPOST','POSTPOST')or p_phase is null then raise exception 'CP7_CREDIT_REFUND_PHASE_REQUIRED';end if;
 select *into strict o from cp7_credit.initial_refund_operations where id=p_operation and cohort_id=p_cohort;
 select *into strict ch from cp7_credit.cohorts where id=p_cohort;
 select *into strict w from cp7_credit.initial_return_work where refund_operation_id=o.id and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=w.operation_id and refund_operation_id=o.id;
 perform cp7_credit.assert_owner_context(ch.initial_plan_id);
 if w.phase<>'MATERIALIZED'or w.origin<>'REVIEWED_SETTLEMENT'or w.settlement->>'mode'<>'REFUND'
  or(w.actor,w.request_id,w.cohort_id,w.plan_id,w.payload_sha256,w.quote_sha256,w.source_lock_sha256,w.projection_sha256)is distinct from
   (o.actor,o.request_id,o.cohort_id,o.initial_plan_id,o.payload_sha256,o.quote_sha256,o.source_lock_sha256,o.projection_sha256)
  or o.full_amount<>(w.actual_kernel->>'net_current_k')::numeric or o.full_amount<=0
  or(o.root_sale_id,o.current_leaf_id)is distinct from(w.source_sale_id,w.source_sale_id)
  or o.authority_snapshot is distinct from w.authority_snapshot or o.cash_account_snapshot is distinct from w.cash_account_snapshot then
  raise exception 'CP7_CREDIT_REFUND_OPERATION_BINDING_CHANGED';end if;
 select transaction_date into strict floor from erp.journal_entries where id=ch.source_return_journal_id
  and source_type='SALES_RETURN'and source_id=w.return_id and status='POSTED';
 book_plan:=cp7_credit.initial_refund_book_plan_v1(w.actual_kernel,o.full_amount,o.physical_at,
  erp.resolve_accounting_transaction_date((o.physical_at at time zone'Asia/Jakarta')::date),floor);
 if floor is distinct from(w.projection->>'planned_book_date')::date or o.required_book_floor is distinct from(book_plan->>'selected_book_date')::date
  or book_plan->>'selected_book_date'is null or o.book_floor_manifest is distinct from book_plan
  or w.projection->'refund_book_plan'is distinct from book_plan then
  raise exception 'CP7_CREDIT_REFUND_CAUSAL_BOOK_FLOOR_CHANGED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id);
 perform cp7_credit.assert_current_source_plan_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into manifest
  from jsonb_array_elements(a->'actual_objects')x where x->>'object_kind'<>'CONSUMPTION';
 if cp7_credit.pg_jsonb_sha256(manifest)is distinct from o.recognition_manifest_sha256
  or m.recognition_manifest_sha256 is distinct from o.recognition_manifest_sha256 then raise exception 'CP7_CREDIT_REFUND_RECOGNITION_CHANGED';end if;
 select count(*)into count_c from cp7_credit.consumption_events where cohort_id=p_cohort;
 if p_phase='PREPOST'and count_c<>0 or p_phase='POSTPOST'and(count_c<>1 or not exists(select 1 from cp7_credit.consumption_events ce
  where ce.id=o.id and ce.cohort_id=p_cohort and ce.event_kind='REFUND'and ce.amount=o.full_amount and ce.source_sha256=cp7_credit.pg_jsonb_sha256(to_jsonb(o))))then
  raise exception 'CP7_CREDIT_REFUND_OWN_CONSUMPTION_CHANGED';end if;
 if cp7_credit.return_command_access('REFUND')is distinct from w.authority_snapshot then raise exception using errcode='42501',message='CP7_CREDIT_REFUND_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.initial-refund-operation-proof.v1','operation_id',o.id::text,
  'cohort_id',ch.id::text,'actor',o.actor::text,'request_id',o.request_id::text,'backend_pid',o.backend_pid::text,'transaction_id',o.transaction_id::text,
  'phase',p_phase,'owning_action','RETURN_SETTLEMENT','stage','NATIVE','initial_plan_id',ch.initial_plan_id::text,'family_id',ch.family_id::text,
  'family_root_sale_id',o.root_sale_id::text,'current_leaf_id',o.current_leaf_id::text,'source_sale_id',ch.source_sale_id::text,'source_return_id',ch.source_return_id::text,
  'full_k',cp7_credit.cent_text(o.full_amount),'cash_account_id',o.cash_account_id::text,'physical_at',cp7_credit.refund_physical_text(o.physical_at),
  'reason',o.reason,'reference',o.reference,'payload_sha256',o.payload_sha256,'quote_sha256',o.quote_sha256,'source_lock_sha256',o.source_lock_sha256,
  'projection_sha256',o.projection_sha256,'recognition_manifest_sha256',o.recognition_manifest_sha256,'materialization_ordinal',o.materialization_ordinal::text,
  'required_book_floor',o.required_book_floor::text,'authority_sha256',cp7_credit.pg_jsonb_sha256(o.authority_snapshot),'cash_snapshot_sha256',cp7_credit.pg_jsonb_sha256(o.cash_account_snapshot),
  'book_floor_manifest_sha256',cp7_credit.pg_jsonb_sha256(o.book_floor_manifest));
end $$;

create function cp7_credit.native_return_leave(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;h erp.sales_headers;net numeric;paid numeric;
begin
 if cp7_credit.is_unchanged_native_return_v1(p_return)then return;end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 if w.phase<>'COMPLETE'or not exists(select 1 from cp7_credit.return_native_scope n where n.backend_pid=w.backend_pid and n.transaction_id=w.transaction_id
  and n.return_id=p_return and n.completed)then raise exception 'CP7_CREDIT_NATIVE_COMPLETION_REQUIRED';end if;
 select *into strict h from erp.sales_headers where id=w.source_sale_id;
 net:=(w.projection->>'net_after')::numeric;paid:=cp7_credit.current_effective_paid(w.source_sale_id);
 if h.status is distinct from(case when paid=net then'PAID'when paid>0 and paid<net then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_NATIVE_STATUS_CHANGED';end if;
 if exists(select 1 from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_POSTING_SCOPE_LEAK';end if;
 delete from cp7_credit.return_native_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id and return_id=p_return;
 delete from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
 if w.origin='ORDINARY'then delete from cp7_credit.initial_return_work where operation_id=w.operation_id;end if;
end $$;

create function cp7_credit.finish_return_settlement(p_request uuid,p_inner jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;m cp7_credit.initial_return_materializations;a jsonb;manifest jsonb;result jsonb;h erp.sales_headers;
begin
 select *into strict w from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=w.operation_id;
 if w.phase<>'COMPLETE'or w.origin<>'REVIEWED_SETTLEMENT'
  or not exists(select 1 from cp7_sales.requests q where q.actor=w.actor and q.request_id=w.request_id and q.action='RETURN'
   and q.payload=w.legacy_payload and q.expected_version=w.expected_version and q.response=p_inner)
  or(p_inner->>'action',p_inner->>'request_id',p_inner->>'sale_id',p_inner->>'return_id',p_inner->>'return_status')is distinct from
   ('RETURN',w.request_id::text,w.source_sale_id::text,w.return_id::text,'POSTED')then raise exception 'CP7_CREDIT_EXACT_COMPLETED_INNER_RECEIPT_REQUIRED';end if;
 perform cp7_credit.assert_initial_work_v1(w.return_id,false);
 if exists(select 1 from cp7_credit.return_native_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id);
 perform cp7_credit.assert_current_source_plan_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 manifest:=jsonb_build_object('contract_version','ow04.completed-initial-return-manifest.v1','operation_id',w.operation_id,
  'actual_source_fact',ow04_source_proposal.return_fact_v1(w.return_id),'verified_member',ow04_source_proposal.verify_return_member_v1(w.return_id),
  'actual_objects',a->'actual_objects','projection_actual_proof_sha256',m.projection_actual_proof_sha256,'inner_receipt',p_inner);
 select *into strict h from erp.sales_headers where id=w.source_sale_id;
 result:=jsonb_build_object('contract_version','cp7.sales-return-settlement-outcome.v1','kind','COMMITTED_OUTCOME','action','RETURN_SETTLEMENT',
  'request_id',w.request_id,'sale_id',w.source_sale_id,'return_id',w.return_id,'return_status','POSTED','row_version',h.row_version::text,
  'family_ordinal',w.family_ordinal::text,'credit_id',w.cohort_id,'refund_event_id',w.refund_operation_id,'quote_sha256',w.quote_sha256,
  'projection_sha256',w.projection_sha256,'actual_manifest_sha256',ow04_source_proposal.sha(manifest),
  'projection_actual_proof_sha256',m.projection_actual_proof_sha256,'production_go',false);
 insert into cp7_credit.initial_return_completions(operation_id,actor,request_id,source_sale_id,source_return_id,origin,inner_receipt,outer_receipt,final_manifest,final_manifest_sha256)
 values(w.operation_id,w.actor,w.request_id,w.source_sale_id,w.return_id,w.origin,p_inner,result,manifest,ow04_source_proposal.sha(manifest));
 update cp7_credit.return_command_scope set stage='COMPLETE',actual_manifest_sha256=ow04_source_proposal.sha(manifest)
  where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor and request_id=w.request_id;
 update cp7_credit.initial_return_work set actual_manifest_sha256=ow04_source_proposal.sha(manifest)where operation_id=w.operation_id;
 if cp7_credit.return_command_access(w.settlement->>'mode')is distinct from w.authority_snapshot then raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_BEFORE_RECEIPT';end if;
 delete from cp7_credit.initial_return_work where operation_id=w.operation_id;
 return result;
end $$;

create function cp7_credit.assert_completed_return_receipt(p_request uuid,p_payload jsonb,p_expected text,p_receipt jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.initial_return_materializations;c cp7_credit.initial_return_completions;q cp7_credit.return_requests;
begin
 select *into strict m from cp7_credit.initial_return_materializations where actor=auth.uid()and request_id=p_request and origin='REVIEWED_SETTLEMENT';
 select *into strict c from cp7_credit.initial_return_completions where operation_id=m.operation_id;
 select *into strict q from cp7_credit.return_requests where actor=m.actor and request_id=m.request_id;
 if(q.payload,q.expected_version)is distinct from(p_payload,p_expected)or cp7_credit.pg_jsonb_sha256(p_payload)<>m.payload_sha256
  or m.expected_version<>p_expected or m.quote_sha256<>p_payload->>'quote_sha256'or c.outer_receipt is distinct from p_receipt
  or q.response is not null and q.response is distinct from p_receipt
  or not exists(select 1 from cp7_sales.requests i where i.actor=m.actor and i.request_id=m.request_id and i.action='RETURN'
   and i.payload=m.legacy_payload and i.expected_version=m.expected_version and i.response=c.inner_receipt)
  or c.final_manifest_sha256<>ow04_source_proposal.sha(c.final_manifest)then raise exception 'CP7_CREDIT_COMPLETED_RECEIPT_BINDING_CHANGED';end if;
 -- Recovery validates immutable historical completion; later permitted master
 -- changes do not mint another event or replace a lost request. Current rights
 -- remain a fresh owning check at every replay wait.
 perform cp7_credit.return_command_access(p_payload#>>'{settlement,mode}');
end $$;

-- Explicit incomplete source routes. Empty registered families do not blanket
-- block Native ordinary payments/returns: a source mutation can continue iff
-- its complete after-profile remains identically empty on every joint cut.
create function cp7_credit.native_source_enter(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid;a jsonb;families boolean;finished boolean:=false;
begin
 if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id,status='REVERSED'and p_action='PAYMENT_REVERSE'into strict sale,finished from erp.sales_payments where id=p_source;
 elsif p_action='RETURN_REVERSE'then select sale_id,status='REVERSED'into strict sale,finished from erp.sales_returns where id=p_source;
 elsif p_action='SALE_REVERSE'then select id,status='REVERSED'into strict sale,finished from erp.sales_headers where id=p_source;
 else raise exception 'CP7_CREDIT_SOURCE_ACTION_UNIMPLEMENTED';end if;
 if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
 -- Original Native require_internal/owner checks still surround this callback.
 a:=cp7_sales.command_access(p_action);
 select exists(select 1 from cp7_credit.return_families where family_root_sale_id=sale)into families;
 if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=sale)
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then
  raise exception 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION';end if;
 if finished then return;end if; -- Native early replay has no completion hook.
 insert into cp7_credit.source_mutation_scope values(pg_backend_pid(),txid_current(),auth.uid(),p_action,p_source,sale,a,families);
 if families then perform cp7_credit.assert_simple_native_base_v1(sale);perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(sale));end if;
 if cp7_sales.command_access(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
end $$;

create function cp7_credit.native_source_complete(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.source_mutation_scope;sale uuid;
begin
 select *into s from cp7_credit.source_mutation_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if s.source_id is null then
  if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id into strict sale from erp.sales_payments where id=p_source;
  elsif p_action='RETURN_REVERSE'then select sale_id into strict sale from erp.sales_returns where id=p_source;
  elsif p_action='SALE_REVERSE'then sale:=p_source;
  else raise exception 'CP7_CREDIT_SOURCE_ACTION_UNIMPLEMENTED';end if;
  if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
  raise exception 'CP7_CREDIT_PARTICIPATING_SOURCE_SCOPE_REQUIRED';
 end if;
 if(s.action,s.source_id)is distinct from(p_action,p_source)then raise exception 'CP7_CREDIT_SOURCE_SCOPE_CHANGED';end if;
 if cp7_sales.command_access(p_action)is distinct from s.authority_snapshot then raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
 if s.had_families then
  perform cp7_credit.assert_simple_native_base_v1(s.sale_id);
  perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(s.sale_id));
 end if;
 delete from cp7_credit.source_mutation_scope where backend_pid=s.backend_pid and transaction_id=s.transaction_id;
end $$;

-- current_effective_paid is defined ONCE in05: P plus the shared authoritative
-- root-aware adjustment. Legacy fast paths and orphan detection belong ONLY
-- to that shared core; this coordinator must not introduce a competing one.

-- Deferred factual closure has no live actor/context/permission dependency.
-- Every new immutable object must belong to an actual completed owning return.
create function cp7_credit.assert_initial_return_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.initial_return_materializations;c cp7_credit.initial_return_completions;q cp7_sales.requests;a jsonb;h erp.sales_headers;net numeric;paid numeric;
begin
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=p_operation;
 select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;
 if q.action<>'RETURN'or q.payload is distinct from m.legacy_payload or q.expected_version is distinct from m.expected_version
  or(q.response->>'sale_id',q.response->>'return_id',q.response->>'return_status',q.response->>'action',q.response->>'request_id')is distinct from
   (m.source_sale_id::text,m.source_return_id::text,'POSTED','RETURN',m.request_id::text)then raise exception 'CP7_CREDIT_FINAL_INNER_RECEIPT_REQUIRED';end if;
 if m.origin='REVIEWED_SETTLEMENT'then
  select *into strict c from cp7_credit.initial_return_completions where operation_id=m.operation_id;
  if c.inner_receipt is distinct from q.response or c.final_manifest_sha256 is distinct from ow04_source_proposal.sha(c.final_manifest)
   or not exists(select 1 from cp7_credit.return_requests o where o.actor=m.actor and o.request_id=m.request_id and o.expected_version=m.expected_version
    and cp7_credit.pg_jsonb_sha256(o.payload)=m.payload_sha256 and o.response=c.outer_receipt)then raise exception 'CP7_CREDIT_FINAL_OUTER_RECEIPT_REQUIRED';end if;
 end if;
 if exists(select 1 from cp7_credit.initial_return_work where operation_id=m.operation_id)
  or exists(select 1 from cp7_credit.execution_context where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.return_native_scope where actor=m.actor and return_id=m.source_return_id)
  or exists(select 1 from cp7_credit.return_command_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.posting_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where actor=m.actor and request_id=m.request_id)then raise exception 'CP7_CREDIT_FINAL_PRIVATE_SCOPE_LEAK';end if;
 select *into strict h from erp.sales_headers where id=m.source_sale_id;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_CREDIT_NEW_RETURN_FINAL_ACTIVE_SALE_REQUIRED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(m.source_sale_id,m.source_sale_id,m.source_sale_id);
 perform cp7_credit.assert_current_source_plan_profile(m.source_sale_id,m.source_sale_id,m.source_sale_id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=h.id)
  -(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED');
 paid:=(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=h.id and status='POSTED')+(a->>'U')::numeric-(a->>'I')::numeric;
 if net<0 or paid<0 or paid>net or h.status<>(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_AR_OR_STATUS_MISMATCH';end if;
 if m.cohort_id is not null and m.settlement->>'mode'='REFUND'and not exists(select 1 from cp7_credit.consumption_events ce
  where ce.id=m.refund_operation_id and ce.cohort_id=m.cohort_id and ce.amount=(m.actual_kernel->>'net_current_k')::numeric)then
  raise exception 'CP7_CREDIT_FINAL_FULL_REFUND_MISSING';end if;
end $$;

create function cp7_credit.enforce_initial_return_closure_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare id uuid;row jsonb:=to_jsonb(new);family uuid;plan uuid;
begin
 if tg_table_name in('initial_return_materializations','initial_return_completions')then id:=(row->>'operation_id')::uuid;
 elsif tg_table_name='initial_refund_operations'then select operation_id into id from cp7_credit.initial_return_materializations where refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materializations'then select operation_id into id from cp7_credit.initial_return_materializations where materialization_id=(row->>'id')::uuid or refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materialization_objects'then select operation_id into id from cp7_credit.initial_return_materializations where materialization_id=(row->>'materialization_id')::uuid or refund_operation_id=(row->>'materialization_id')::uuid;
 else
  case tg_table_name
   when'return_families'then family:=(row->>'id')::uuid;
   when'return_family_members'then family:=(row->>'family_id')::uuid;
   when'cohorts'then family:=(row->>'family_id')::uuid;
   when'recognition_plans'then plan:=(row->>'id')::uuid;
   when'plan_support_events'then plan:=(row->>'plan_id')::uuid;
   when'recognition_components'then plan:=(row->>'plan_id')::uuid;
   when'component_parts'then select plan_id into plan from cp7_credit.recognition_components where id=(row->>'component_id')::uuid;
   when'component_journals'then select cc.plan_id into plan from cp7_credit.component_parts pp join cp7_credit.recognition_components cc on cc.id=pp.component_id where pp.id=(row->>'part_id')::uuid;
   when'consumption_events'then select family_id into family from cp7_credit.cohorts where id=(row->>'cohort_id')::uuid;
   when'plan_dependencies'then plan:=(row->>'plan_id')::uuid;
   else raise exception 'CP7_CREDIT_CLOSURE_TABLE_UNRECOGNIZED';
  end case;
  select operation_id into id from cp7_credit.initial_return_materializations where family_id=family or plan_id=plan;
 end if;
 if id is null then raise exception 'CP7_CREDIT_UNOWNED_IMMUTABLE_FACT';end if;
 perform cp7_credit.assert_initial_return_closed_v1(id);return null;
end $$;

do $deferred$declare t text;begin
 foreach t in array array['return_families','return_family_members','cohorts','recognition_plans','plan_support_events','recognition_components','component_parts','component_journals',
  'consumption_events','plan_dependencies','financial_materializations','financial_materialization_objects','initial_refund_operations','initial_return_materializations','initial_return_completions']loop
  execute format('create constraint trigger initial_return_closed after insert on cp7_credit.%I deferrable initially deferred for each row execute function cp7_credit.enforce_initial_return_closure_v1()',t);
 end loop;
end $deferred$;
