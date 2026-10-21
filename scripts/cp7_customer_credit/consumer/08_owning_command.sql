-- Pending complete composition and actual Native qualification. This file is
-- not loaded by the qualified installer; do not expose its public wire early.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.consumer_quote_binding_v1(p_payload jsonb,p_locked jsonb,p_projection jsonb)returns text
language sql immutable security invoker set search_path=''as $$
 select cp7_credit.pg_jsonb_sha256(jsonb_build_object('contract_version','ow04.consumer-review-binding.v1',
  'payload',p_payload-'quote_sha256','locked',p_locked,'projection',p_projection))
$$;

create function cp7_credit.assert_consumer_scopes_clear_v1()returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if exists(select 1 from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.consumer_posting_scope_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.source_mutation_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_CONSUMER_AMBIENT_OR_LEAKED_PRIVATE_SCOPE';end if;
end $$;

create function cp7_credit.consumer_quote_v1(p_payload jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare locked jsonb;projection jsonb;selection jsonb;binding text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_credit.validate_consumer_payload_v1(p_payload,false);
 perform cp7_credit.consumer_payload_kind_v1(p_payload);
 perform cp7_credit.assert_no_ambient_native_context();
 perform cp7_credit.assert_consumer_scopes_clear_v1();
 locked:=cp7_credit.consumer_lock_sources_v1(p_payload);
 projection:=cp7_credit.consumer_projection_v1(p_payload,locked);selection:=locked->'selection';
 binding:=cp7_credit.consumer_quote_binding_v1(p_payload,locked,projection);
 return jsonb_build_object('contract_version','cp7.customer-credit-review.v1','read_only',true,
  'selection',selection,'physical_at',projection->'physical_at','economic_date',projection->'economic_date',
  'transaction_date',projection->'transaction_date','book_basis',projection->'book_manifest',
  'available_credit_after',projection#>'{source_capacity_after,current_balance}',
  'expected_versions',projection->'expected_versions','quote_sha256',binding);
end $$;

-- Immutable envelope/data agreement, usable for old receipts without a live
-- actor or a pending context. Live source/permission proof remains separate.
create function cp7_credit.assert_consumer_operation_input_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;q cp7_credit.consumer_requests_v1;selection jsonb;projection jsonb;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=o.actor and request_id=o.request_id;
 selection:=o.locked_sources->'selection';projection:=o.projection;
 perform cp7_credit.validate_consumer_payload_v1(q.payload,true);
 if q.action is distinct from q.payload->>'action'or q.action<>o.action
  or o.payload_sha256<>cp7_credit.pg_jsonb_sha256(q.payload)
  or o.quote_sha256 is distinct from q.payload->>'quote_sha256'
  or o.locked_sources_sha256<>cp7_credit.pg_jsonb_sha256(o.locked_sources)
  or o.source_graph_sha256<>cp7_credit.pg_jsonb_sha256(o.source_graph)
  or o.projection_sha256<>cp7_credit.pg_jsonb_sha256(projection)
  or o.quote_sha256<>cp7_credit.consumer_quote_binding_v1(q.payload,o.locked_sources,projection)
  or q.expected_versions is distinct from projection->'expected_versions'
  or o.source_graph is distinct from o.locked_sources->'graph'
  or(o.period_snapshot,o.authority_snapshot)is distinct from(o.locked_sources->'period',o.locked_sources->'authority')
  or(o.action,o.event_kind,o.cohort_id,o.customer_id,o.source_sale_id,o.source_root_sale_id,o.source_current_leaf_id,
      o.target_sale_id,o.target_root_sale_id,o.target_current_leaf_id,o.cash_account_id,o.amount,o.restores_event_id)
   is distinct from(selection->>'action',selection->>'event_kind',(selection->>'cohort_id')::uuid,(selection->>'customer_id')::uuid,
      (selection->>'source_sale_id')::uuid,(selection->>'source_root_sale_id')::uuid,(selection->>'source_current_leaf_id')::uuid,
      (selection->>'target_sale_id')::uuid,(selection->>'target_root_sale_id')::uuid,(selection->>'target_current_leaf_id')::uuid,
      (selection->>'cash_account_id')::uuid,(selection->>'amount')::numeric,(selection->>'restores_event_id')::uuid)
  or(o.physical_at,o.economic_date,o.transaction_date,o.reason,o.reference,o.credit_account_id,o.target_ar_account_id,o.cash_coa_account_id)
   is distinct from((q.payload->>'physical_at')::timestamptz,(projection->>'economic_date')::date,(projection->>'transaction_date')::date,
      q.payload->>'reason',q.payload->>'reference',(projection#>>'{credit_account,account,id}')::uuid,
      (projection#>>'{target_ar_source,account_id}')::uuid,(projection#>>'{cash_account,account,id}')::uuid)
  or(o.credit_account_snapshot,o.target_ar_snapshot,o.cash_account_snapshot,o.book_manifest,o.before_native)is distinct from
    (projection->'credit_account',nullif(projection->'target_ar_source','null'::jsonb),nullif(projection->'cash_account','null'::jsonb),
      projection->'book_manifest',projection->'before_native')then
  raise exception 'CP7_CREDIT_CONSUMER_IMMUTABLE_INPUT_AGREEMENT_CHANGED';end if;
end $$;

create function cp7_credit.assert_consumer_operation_bound_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;c cp7_credit.consumer_execution_context;q cp7_credit.consumer_requests_v1;
 selection jsonb;projection jsonb;period jsonb;
begin
 perform cp7_credit.assert_consumer_operation_input_v1(p_operation);
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 select *into strict c from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and operation_id=o.id;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=o.actor and request_id=o.request_id;
 if c.phase not in('LOCKED','POSTING')or q.response is not null
  or(c.actor,c.request_id,c.action,c.payload_sha256,c.quote_sha256,c.authority_snapshot)is distinct from
   (o.actor,o.request_id,o.action,o.payload_sha256,o.quote_sha256,o.authority_snapshot)
  or cp7_credit.consumer_command_access_v1(o.action,o.event_kind)is distinct from o.authority_snapshot
  or cp7_credit.pg_jsonb_sha256(q.payload)<>o.payload_sha256
  or o.locked_sources_sha256<>cp7_credit.pg_jsonb_sha256(o.locked_sources)
  or o.source_graph_sha256<>cp7_credit.pg_jsonb_sha256(o.source_graph)
  or o.projection_sha256<>cp7_credit.pg_jsonb_sha256(o.projection)
  or exists(select 1 from cp7_credit.consumption_events where id=o.id)
  or exists(select 1 from erp.journal_entries where source_id=o.id and source_type in
   ('CP7_CUSTOMER_CREDIT_APPLY','CP7_CUSTOMER_CREDIT_REFUND','CP7_CUSTOMER_CREDIT_EVENT_REVERSE'))then
  raise exception 'CP7_CREDIT_CONSUMER_OWN_LOCKED_OPERATION_REQUIRED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 selection:=cp7_credit.consumer_selection_v1(q.payload);
 if selection is distinct from o.locked_sources->'selection'or period is distinct from o.period_snapshot
  or cp7_credit.consumer_joined_graph_v1(o.source_sale_id,o.target_sale_id)is distinct from o.source_graph
  or cp7_credit.consumer_capture_sources_v1(o.source_graph)is distinct from o.locked_sources->'sources'then
  raise exception 'CP7_CREDIT_CONSUMER_LOCKED_SOURCE_CHANGED';end if;
 if o.cash_coa_account_id is not null and cp7_credit.consumer_cash_balance_v1(o.cash_coa_account_id)
  is distinct from(o.projection->>'cash_balance_before')::numeric then raise exception 'CP7_CREDIT_CONSUMER_LOCKED_CASH_CHANGED';end if;
 -- Rebuild reads only already-locked data; it acquires no earlier-order locks.
 projection:=cp7_credit.consumer_projection_v1(q.payload,o.locked_sources);
 if projection is distinct from o.projection or q.expected_versions is distinct from projection->'expected_versions'
  or o.quote_sha256 is distinct from cp7_credit.consumer_quote_binding_v1(q.payload,o.locked_sources,projection)
  or(o.cohort_id,o.customer_id,o.source_sale_id,o.source_root_sale_id,o.source_current_leaf_id,
     o.target_sale_id,o.target_root_sale_id,o.target_current_leaf_id,o.cash_account_id,o.amount,o.restores_event_id)
   is distinct from((selection->>'cohort_id')::uuid,(selection->>'customer_id')::uuid,(selection->>'source_sale_id')::uuid,
     (selection->>'source_root_sale_id')::uuid,(selection->>'source_current_leaf_id')::uuid,(selection->>'target_sale_id')::uuid,
     (selection->>'target_root_sale_id')::uuid,(selection->>'target_current_leaf_id')::uuid,(selection->>'cash_account_id')::uuid,
     (selection->>'amount')::numeric,(selection->>'restores_event_id')::uuid)
  or(o.credit_account_snapshot,o.target_ar_snapshot,o.cash_account_snapshot,o.book_manifest,o.before_native)is distinct from
    (projection->'credit_account',nullif(projection->'target_ar_source','null'::jsonb),nullif(projection->'cash_account','null'::jsonb),
     projection->'book_manifest',projection->'before_native')then
  raise exception 'CP7_CREDIT_CONSUMER_EXACT_SOURCE_PROJECTION_CHANGED';end if;
end $$;

create function cp7_credit.consumer_verify_posted_journal_v1(p_operation uuid,p_journal uuid)returns text
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;j erp.journal_entries;kind text;expected jsonb;actual jsonb;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 select *into strict j from erp.journal_entries where id=p_journal;
 kind:=case when o.action='UNDO'then'CP7_CUSTOMER_CREDIT_EVENT_REVERSE'
  when o.event_kind='APPLY'then'CP7_CUSTOMER_CREDIT_APPLY'else'CP7_CUSTOMER_CREDIT_REFUND'end;
 if(j.source_type,j.source_id,j.status,j.reversal_of_id,j.economic_date,j.transaction_date)is distinct from
   (kind,o.id,'POSTED',null::uuid,o.economic_date,o.transaction_date)
  or(select count(*)from erp.journal_entries where source_type=kind and source_id=o.id)<>1
  or exists(select 1 from erp.journal_entries where reversal_of_id=j.id or(source_type='JOURNAL_REVERSAL'and source_id=j.id))
  or(select count(*)from erp.journal_lines where journal_entry_id=j.id)<>2
  or exists(select 1 from erp.journal_lines where journal_entry_id=j.id and(vendor_id is not null
   or contractor_id is not null or po_id is not null or product_id is not null))then
  raise exception 'CP7_CREDIT_CONSUMER_POSTED_NATIVE_JOURNAL_CHANGED';end if;
 select jsonb_agg(v order by v->>'account_id'collate"C")into expected
  from jsonb_array_elements(cp7_credit.consumer_operation_lines_v1(o.id))v;
 select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'description',l.description,
  'debit',l.debit,'credit',l.credit)order by l.account_id::text collate"C")into actual
  from erp.journal_lines l where l.journal_entry_id=j.id;
 if actual is distinct from expected then raise exception 'CP7_CREDIT_CONSUMER_POSTED_NATIVE_LINES_CHANGED';end if;
 return cp7_credit.native_lines_sha256(actual);
end $$;

create function cp7_credit.consumer_document_ar_v1(p_sale uuid,p_customer uuid,p_ar uuid)returns numeric
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 with recursive originals(id)as(
  select substring(v->>'id'from 9)::uuid from jsonb_array_elements(cp7_credit.initial_base_events_v1(p_sale))v
  union select cj.journal_id from cp7_credit.component_journals cj join cp7_credit.component_parts part on part.id=cj.part_id
   join cp7_credit.recognition_components component on component.id=part.component_id
   join cp7_credit.recognition_plans plan on plan.id=component.plan_id join cp7_credit.cohorts c on c.id=plan.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_sale
 ),walk(id)as(select id from originals union select j.id from walk w join erp.journal_entries j
  on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
 select coalesce(sum(l.debit-l.credit),0)from walk w join erp.journal_entries j on j.id=w.id
  join erp.journal_lines l on l.journal_entry_id=j.id where j.status in('POSTED','REVERSED')
   and l.customer_id=p_customer and l.account_id=p_ar
$$;

create function cp7_credit.consumer_invoice_profile_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;profile jsonb;ar_source jsonb;gross numeric;net numeric;paid numeric;
 effective numeric;actual_ar numeric;issued numeric;incoming numeric;
begin
 select *into strict h from erp.sales_headers where id=p_sale;
 perform cp7_credit.assert_current_materialized_profile(h.id,h.id,h.id);
 profile:=cp7_credit.inspect_current_materialized_profile(h.id,h.id,h.id);
 ar_source:=cp7_credit.consumer_invoice_ar_source_v1(h.id);
 gross:=(ar_source->>'gross_amount')::numeric;
 net:=gross-(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
  where r.sale_id=h.id and r.status='POSTED');
 select coalesce(sum(amount),0)into paid from erp.sales_payments where sale_id=h.id and status='POSTED';
 issued:=(profile->>'I')::numeric;incoming:=(profile->>'U')::numeric;effective:=paid+incoming-issued;
 actual_ar:=cp7_credit.consumer_document_ar_v1(h.id,h.customer_id,(ar_source->>'account_id')::uuid);
 if net<0 or effective<0 or effective>net or actual_ar is distinct from net-effective
  or h.status is distinct from(case when effective=net then'PAID'when effective>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_CONSUMER_FINAL_DOCUMENT_AR_OR_STATUS_CHANGED';end if;
 return jsonb_build_object('sale_id',h.id,'row_version',h.row_version::text,'status',h.status,
  'gross',cp7_credit.cent_text(gross::cp7_credit.cent_amount),'net',cp7_credit.cent_text(net::cp7_credit.cent_amount),
  'P',cp7_credit.cent_text(paid::cp7_credit.cent_amount),'U',cp7_credit.cent_text(incoming::cp7_credit.cent_amount),
  'I',cp7_credit.cent_text(issued::cp7_credit.cent_amount),'E',cp7_credit.cent_text(effective::cp7_credit.cent_amount),
  'AR',cp7_credit.cent_text(actual_ar::cp7_credit.cent_amount),'materialized',profile);
end $$;

create function cp7_credit.consumer_actual_manifest_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;e cp7_credit.consumption_events;object jsonb;f cp7_credit.financial_materializations;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 select *into strict e from cp7_credit.consumption_events where id=o.id;
 perform cp7_credit.consumer_event_data_v1(e.id);
 select *into strict f from cp7_credit.financial_materializations where id=o.id;
 object:=cp7_credit.materialized_fact('CONSUMPTION',e.id,jsonb_build_object('event',to_jsonb(e),
  'actual',cp7_credit.materialized_journal_payload(e.journal_id)));
 if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256)
  is distinct from(o.source_root_sale_id,o.actor,o.request_id,1,'CREDIT_'||o.action,o.payload_sha256,o.projection_sha256)
  or f.actual_objects is distinct from jsonb_build_array(object)
  or f.actual_objects_sha256<>cp7_credit.pg_jsonb_sha256(f.actual_objects)
  or not exists(select 1 from cp7_credit.financial_materialization_objects mo where mo.object_kind='CONSUMPTION'
   and mo.object_id=e.id and mo.materialization_id=f.id and mo.fact_sha256=object->>'fact_sha256')
  or(select count(*)from cp7_credit.financial_materialization_objects where materialization_id=f.id)<>1 then
  raise exception 'CP7_CREDIT_CONSUMER_ACTUAL_MATERIALIZATION_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.consumer-actual-manifest.v1','operation_id',o.id,
  'operation_sha256',cp7_credit.pg_jsonb_sha256(to_jsonb(o)),'consumption_event_id',e.id,
  'journal_id',e.journal_id,'materialization_id',f.id,'actual_objects',f.actual_objects);
end $$;

create function cp7_credit.consumer_execute_v1(p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.consumer_execution_context;q cp7_credit.consumer_requests_v1;o cp7_credit.consumer_operations_v1;
 locked jsonb;projection jsonb;selection jsonb;binding text;operation uuid:=gen_random_uuid();lines jsonb;kind text;journal uuid;
 line_hash text;event cp7_credit.consumption_events;object jsonb;manifest jsonb;result jsonb;profiles jsonb:='{}';
 final_native jsonb:='{}';sale text;changed uuid[];header erp.sales_headers;net numeric;effective numeric;vectors jsonb;capacity jsonb;
begin
 select *into strict c from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=c.actor and request_id=c.request_id;
 if c.phase<>'CLAIMED'or c.operation_id is not null or q.response is not null
  or(c.action,c.payload_sha256,c.quote_sha256)is distinct from(q.action,cp7_credit.pg_jsonb_sha256(q.payload),q.payload->>'quote_sha256')then
  raise exception 'CP7_CREDIT_CONSUMER_PENDING_OUTER_REQUIRED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 if exists(select 1 from cp7_credit.consumer_posting_scope_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_CONSUMER_NESTED_POST_SCOPE';end if;
 locked:=cp7_credit.consumer_lock_sources_v1(q.payload);
 projection:=cp7_credit.consumer_projection_v1(q.payload,locked);selection:=locked->'selection';
 binding:=cp7_credit.consumer_quote_binding_v1(q.payload,locked,projection);
 if binding is distinct from c.quote_sha256 or q.expected_versions is distinct from projection->'expected_versions'
  or locked->'authority'is distinct from c.authority_snapshot then raise exception 'CP7_CREDIT_CONSUMER_REVIEW_CHANGED';end if;
 insert into cp7_credit.consumer_operations_v1(id,actor,actor_app_user_id,request_id,action,event_kind,cohort_id,customer_id,
  source_sale_id,source_root_sale_id,source_current_leaf_id,target_sale_id,target_root_sale_id,target_current_leaf_id,
  cash_account_id,credit_account_id,target_ar_account_id,cash_coa_account_id,amount,restores_event_id,physical_at,economic_date,transaction_date,
  reason,reference,payload_sha256,quote_sha256,source_graph,source_graph_sha256,locked_sources,locked_sources_sha256,
  projection,projection_sha256,period_snapshot,book_manifest,authority_snapshot,credit_account_snapshot,target_ar_snapshot,cash_account_snapshot,before_native)
 values(operation,c.actor,erp.current_app_user_id(),c.request_id,c.action,selection->>'event_kind',(selection->>'cohort_id')::uuid,
  (selection->>'customer_id')::uuid,(selection->>'source_sale_id')::uuid,(selection->>'source_root_sale_id')::uuid,
  (selection->>'source_current_leaf_id')::uuid,(selection->>'target_sale_id')::uuid,(selection->>'target_root_sale_id')::uuid,
  (selection->>'target_current_leaf_id')::uuid,(selection->>'cash_account_id')::uuid,(projection#>>'{credit_account,account,id}')::uuid,
  (projection#>>'{target_ar_source,account_id}')::uuid,(projection#>>'{cash_account,account,id}')::uuid,
  (selection->>'amount')::numeric,(selection->>'restores_event_id')::uuid,(q.payload->>'physical_at')::timestamptz,
  (projection->>'economic_date')::date,(projection->>'transaction_date')::date,q.payload->>'reason',q.payload->>'reference',
  c.payload_sha256,c.quote_sha256,locked->'graph',cp7_credit.pg_jsonb_sha256(locked->'graph'),locked,cp7_credit.pg_jsonb_sha256(locked),
  projection,cp7_credit.pg_jsonb_sha256(projection),locked->'period',projection->'book_manifest',c.authority_snapshot,
  projection->'credit_account',nullif(projection->'target_ar_source','null'::jsonb),nullif(projection->'cash_account','null'::jsonb),projection->'before_native');
 update cp7_credit.consumer_execution_context set phase='LOCKED',operation_id=operation
  where backend_pid=c.backend_pid and transaction_id=c.transaction_id;
 select *into strict o from cp7_credit.consumer_operations_v1 where id=operation;
 perform cp7_credit.assert_consumer_operation_bound_v1(o.id);
 lines:=cp7_credit.consumer_operation_lines_v1(o.id);
 kind:=case when o.action='UNDO'then'CP7_CUSTOMER_CREDIT_EVENT_REVERSE'
  when o.event_kind='APPLY'then'CP7_CUSTOMER_CREDIT_APPLY'else'CP7_CUSTOMER_CREDIT_REFUND'end;
 insert into cp7_credit.consumer_posting_scope_v1 values(c.backend_pid,c.transaction_id,c.actor,c.request_id,o.id,
  kind,o.id,o.economic_date,o.transaction_date,cp7_credit.native_lines_sha256(lines));
 update cp7_credit.consumer_execution_context set phase='POSTING'where backend_pid=c.backend_pid and transaction_id=c.transaction_id;
 journal:=cp7_credit._post_consumer_bound_v1(kind,o.id,o.economic_date,'Pemakaian atau pembatalan kredit pelanggan',lines);
 line_hash:=cp7_credit.consumer_verify_posted_journal_v1(o.id,journal);
 insert into cp7_credit.consumption_events(id,cohort_id,event_kind,amount,economic_date,transaction_date,target_sale_id,
  cash_account_id,restores_event_id,journal_id,source_sha256,lines_sha256_pg,actor,request_id,reason)
 values(o.id,o.cohort_id,o.event_kind,o.amount,o.economic_date,o.transaction_date,o.target_sale_id,o.cash_account_id,
  o.restores_event_id,journal,cp7_credit.pg_jsonb_sha256(to_jsonb(o)),line_hash,o.actor,o.request_id,o.reason);
 select *into strict event from cp7_credit.consumption_events where id=o.id;
 object:=cp7_credit.materialized_fact('CONSUMPTION',event.id,jsonb_build_object('event',to_jsonb(event),
  'actual',cp7_credit.materialized_journal_payload(journal)));
 insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,
  payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
 values(o.id,o.source_root_sale_id,o.actor,o.request_id,1,'CREDIT_'||o.action,o.payload_sha256,o.projection_sha256,
  jsonb_build_array(object),cp7_credit.pg_jsonb_sha256(jsonb_build_array(object)));
 insert into cp7_credit.financial_materialization_objects values('CONSUMPTION',o.id,o.id,object->>'fact_sha256');
 delete from cp7_credit.consumer_posting_scope_v1 where backend_pid=c.backend_pid and transaction_id=c.transaction_id;
 update cp7_credit.consumer_execution_context set phase='MATERIALIZED'where backend_pid=c.backend_pid and transaction_id=c.transaction_id;
 select array_agg(distinct x order by x)into changed from unnest(array[o.source_current_leaf_id,o.target_current_leaf_id])x where x is not null;
 for header in select *from erp.sales_headers where id=any(changed)order by id loop
  net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=header.id)
   -(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
     where r.sale_id=header.id and r.status='POSTED');
  effective:=cp7_credit.current_effective_paid(header.id);
  if net<0 or effective<0 or effective>net then raise exception 'CP7_CREDIT_CONSUMER_FINAL_EFFECTIVE_PAID_INVALID';end if;
  -- Native bump_row_version/touch and all Native HPP callbacks remain active.
  update erp.sales_headers set status=case when effective=net then'PAID'when effective>0 then'PARTIAL_PAID'else'POSTED'end where id=header.id;
 end loop;
 for sale in select value from jsonb_array_elements_text(o.source_graph->'sale_ids')order by value loop
  profiles:=profiles||jsonb_build_object(sale,cp7_credit.consumer_invoice_profile_v1(sale::uuid));
  final_native:=final_native||jsonb_build_object(sale,cp7_credit.consumer_native_invariant_v1(sale::uuid));
  if final_native->sale is distinct from o.before_native->sale then
   raise exception 'CP7_CREDIT_CONSUMER_CHANGED_NATIVE_STOCK_HPP_OR_PAYMENT';end if;
  if(profiles#>>array[sale,'row_version'])::bigint is distinct from
   ((o.projection#>>array['expected_versions',sale])::bigint+case when sale::uuid=any(changed)then 1 else 0 end)then
   raise exception 'CP7_CREDIT_CONSUMER_REVIEW_EPOCH_NOT_RETIRED_EXACTLY';end if;
 end loop;
 vectors:=cp7_credit.consumer_source_vectors_v1(o.cohort_id);
 capacity:=ow04_pure_kernel.credit_capacity_v1(vectors->'recognition',vectors->'consumptions',o.economic_date::text,o.transaction_date::text);
 if capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb then raise exception 'CP7_CREDIT_CONSUMER_FINAL_CAPACITY_UNFUNDED';end if;
 if o.cash_coa_account_id is not null then perform cp7_guard.check_cash(o.cash_coa_account_id,o.economic_date,o.transaction_date);end if;
 if o.cash_coa_account_id is not null and cp7_credit.consumer_cash_balance_v1(o.cash_coa_account_id)
  is distinct from (o.projection->>'cash_balance_before')::numeric-o.amount then
  raise exception 'CP7_CREDIT_CONSUMER_EXACT_CASH_EFFECT_CHANGED';end if;
 perform cp7_credit.credit_account_facts_v1(o.credit_account_id);
 if cp7_credit.consumer_command_access_v1(o.action,o.event_kind)is distinct from o.authority_snapshot then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_FINAL_ACCESS_CHANGED';end if;
 manifest:=cp7_credit.consumer_actual_manifest_v1(o.id);
 result:=cp7_credit.consumer_outcome_v1(o.id,profiles,capacity);
 insert into cp7_credit.consumer_completions_v1(operation_id,consumption_event_id,journal_id,materialization_id,journal_lines_sha256_pg,
  actual_manifest,actual_manifest_sha256,final_native,final_profiles,response)
 values(o.id,o.id,journal,o.id,line_hash,manifest,cp7_credit.pg_jsonb_sha256(manifest),final_native,
  jsonb_build_object('invoices',profiles,'source_capacity',capacity,'cash_balance_after',case when o.cash_coa_account_id is not null then
   cp7_credit.cent_text(cp7_credit.consumer_cash_balance_v1(o.cash_coa_account_id)::cp7_credit.cent_amount)end),result);
 update cp7_credit.consumer_execution_context set phase='COMPLETE'where backend_pid=c.backend_pid and transaction_id=c.transaction_id;
 return result;
end $$;

do $private$declare sig text;begin
 foreach sig in array array['consumer_quote_binding_v1(jsonb,jsonb,jsonb)','assert_consumer_scopes_clear_v1()',
 'consumer_quote_v1(jsonb)','assert_consumer_operation_input_v1(uuid)','assert_consumer_operation_bound_v1(uuid)','consumer_verify_posted_journal_v1(uuid,uuid)',
 'consumer_document_ar_v1(uuid,uuid,uuid)','consumer_invoice_profile_v1(uuid)','consumer_actual_manifest_v1(uuid)','consumer_execute_v1(uuid)']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
