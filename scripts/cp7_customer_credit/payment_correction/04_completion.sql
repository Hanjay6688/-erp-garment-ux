do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

create function cp7_credit.payment_source_consumers_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;e record;actual jsonb;expected jsonb;
begin
 perform cp7_credit.payment_source_assert_pending_v1(p_operation);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=w.sale_id)then
  raise exception 'CP7_CREDIT_SOURCE_INCOMING_HISTORY_ADAPTER_REQUIRED';end if;
 select coalesce(jsonb_agg(cp7_credit.materialized_fact('CONSUMPTION',ce.id,
  jsonb_build_object('event',to_jsonb(ce),'actual',cp7_credit.materialized_journal_payload(ce.journal_id)))order by ce.id),'[]')into actual
  from cp7_credit.consumption_events ce join cp7_credit.cohorts ch on ch.id=ce.cohort_id where ch.source_sale_id=w.sale_id;
 select coalesce(jsonb_agg(x order by(x->>'object_id')::uuid),'[]')into expected
  from jsonb_array_elements(w.before_financial_profile->'actual_objects')x where x->>'object_kind'='CONSUMPTION';
 if actual is distinct from expected then raise exception 'CP7_CREDIT_PAYMENT_SIGNED_CONSUMER_SET_CHANGED';end if;
 for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts ch on ch.id=ce.cohort_id
  where ch.source_sale_id=w.sale_id order by ce.id loop perform cp7_credit.consumer_event_data_v1(e.id);end loop;
end $$;

-- Correction journal kinds may enter the factual vector only with their real
-- immutable Native link or this exact still-pending, proved owning operation.
-- This helper does not grant command authority and does not call a current
-- profile recursively. Historical source proofs separately verify all vectors.
create function cp7_credit.payment_link_source_check_v1(p_sale uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare l cp7_payment_correction.links;m cp7_credit.source_operation_materializations_v1;legs cp7_credit.payment_source_legs_v1;
 accepted uuid[]:='{}';n integer;
begin
 for l in select *from cp7_payment_correction.links where sale_id=p_sale order by original_id loop
  select *into strict m from cp7_credit.source_operation_materializations_v1 where action='PAYMENT_CORRECT'and sale_id=p_sale
   and source_id=l.original_id and actor=l.actor and request_id=l.request_id;
  select *into strict legs from cp7_credit.payment_source_legs_v1 where operation_id=m.operation_id;
  if(l.replacement_id,l.time_neutral_id,l.effective_inverse_id,l.reason)is distinct from
   (legs.replacement_id,legs.time_neutral_id,legs.effective_inverse_id,btrim(m.payload->>'change_reason'))then
   raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_LINK_BINDING_CHANGED';end if;
  accepted:=accepted||array_remove(array[legs.time_neutral_id,legs.effective_inverse_id],null);
 end loop;
 for legs in select ls.*from cp7_credit.payment_source_legs_v1 ls join cp7_credit.source_operation_work_v1 w on w.operation_id=ls.operation_id
  join cp7_credit.payment_source_context_v1 c on c.operation_id=w.operation_id
  join cp7_payment_correction.context pc on(pc.backend_pid,pc.transaction_id,pc.actor,pc.request_id,pc.payload,pc.expected_version)=
   (w.backend_pid,w.transaction_id,w.actor,w.request_id,w.payload,w.expected_version)
  join cp7_payment_correction.requests q on(q.actor,q.request_id,q.payload,q.expected_version)=(w.actor,w.request_id,w.payload,w.expected_version)
  where w.sale_id=p_sale and w.action='PAYMENT_CORRECT'and w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()
   and w.actor=auth.uid()and q.response is null and c.phase in('RECONCILING','RECONCILED','REPLACEMENT_COMPLETE')loop
  accepted:=accepted||array_remove(array[legs.time_neutral_id,legs.effective_inverse_id],null);
 end loop;
 if exists(select 1 from erp.journal_entries j join erp.sales_payments p on p.id=j.source_id
  where p.sale_id=p_sale and j.source_type in('PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')
   and not(j.id=any(accepted)))then raise exception 'CP7_CREDIT_PAYMENT_UNOWNED_TIME_JOURNAL';end if;
end $$;

create function cp7_credit.payment_source_completion_manifest_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;c cp7_credit.source_operation_completions_v1;legs cp7_credit.payment_source_legs_v1;
 l cp7_payment_correction.links;
begin
 select *into strict m from cp7_credit.source_operation_materializations_v1 where operation_id=p_operation and action='PAYMENT_CORRECT';
 select *into strict c from cp7_credit.source_operation_completions_v1 where operation_id=m.operation_id;
 select *into strict legs from cp7_credit.payment_source_legs_v1 where operation_id=m.operation_id;
 select *into strict l from cp7_payment_correction.links where original_id=m.source_id and replacement_id=legs.replacement_id
  and sale_id=m.sale_id and actor=m.actor and request_id=m.request_id;
 if(l.time_neutral_id,l.effective_inverse_id,l.reason)is distinct from
   (legs.time_neutral_id,legs.effective_inverse_id,btrim(m.payload->>'change_reason'))then
  raise exception 'CP7_CREDIT_PAYMENT_COMPLETED_NATIVE_LINK_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.completed-payment-source.v1','operation_id',m.operation_id,
  'actual_manifest_sha256',m.actual_manifest_sha256,'actual_link',to_jsonb(l),
  'final_native_source',c.final_native_source,'final_profile',c.final_profile,
  'header_proof',cp7_credit.payment_terminal_header_v1(m.actual_source,c.final_native_source,legs.replacement_id));
end $$;

create function cp7_credit.payment_source_finish_v1(p_request uuid,p_posted jsonb,p_link cp7_payment_correction.links)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;profile jsonb;manifest jsonb;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and request_id=p_request;
 if not found then return;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 if c.phase<>'REPLACEMENT_COMPLETE'or w.phase<>'RECONCILED'
  or(p_posted->>'payment_id',p_posted->>'sale_id',p_posted->>'payment_status')is distinct from
   (c.replacement_id::text,w.sale_id::text,'POSTED')
  or(p_link.original_id,p_link.replacement_id,p_link.sale_id,p_link.actor,p_link.request_id)is distinct from
   (w.source_id,c.replacement_id,w.sale_id,w.actor,w.request_id)
  or(select to_jsonb(l)from cp7_payment_correction.links l where original_id=w.source_id)is distinct from to_jsonb(p_link)then
  raise exception 'CP7_CREDIT_PAYMENT_PARENT_NATIVE_RESULT_CHANGED';end if;
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 perform cp7_credit.payment_terminal_header_v1(w.actual_source,actual,c.replacement_id);
 profile:=cp7_credit.inspect_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
 perform cp7_credit.assert_source_final_ar_status_v1(w.sale_id,actual,profile);
 -- Insert only after the ACTUAL parent link exists. The manifest includes
 -- that immutable link; it was never pretended present at Native post time.
 manifest:=jsonb_build_object('contract_version','ow04.completed-payment-source.v1','operation_id',w.operation_id,
  'actual_manifest_sha256',w.actual_manifest_sha256,'actual_link',to_jsonb(p_link),'final_native_source',actual,'final_profile',profile,
  'header_proof',cp7_credit.payment_terminal_header_v1(w.actual_source,actual,c.replacement_id));
 insert into cp7_credit.source_operation_completions_v1(operation_id,final_native_source,final_profile,final_manifest_sha256)
 values(w.operation_id,actual,profile,cp7_credit.pg_jsonb_sha256(manifest));
 update cp7_credit.source_operation_work_v1 set phase='NATIVE_COMPLETE'where operation_id=w.operation_id;
 perform cp7_credit.assert_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
 perform cp7_credit.assert_source_completion_v1(w.operation_id);
 if exists(select 1 from cp7_sales.command_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_guard.compound_scope where txid=w.transaction_id)then
  raise exception 'CP7_CREDIT_PAYMENT_NATIVE_TAIL_SCOPE_LEAK';end if;
 delete from cp7_credit.payment_source_context_v1 where operation_id=w.operation_id;
 delete from cp7_credit.source_operation_work_v1 where operation_id=w.operation_id;
end $$;

create function cp7_credit.assert_payment_source_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;c cp7_credit.source_operation_completions_v1;
 legs cp7_credit.payment_source_legs_v1;q cp7_payment_correction.requests;l cp7_payment_correction.links;expected jsonb;
begin
 select *into strict m from cp7_credit.source_operation_materializations_v1 where operation_id=p_operation and action='PAYMENT_CORRECT';
 select *into strict c from cp7_credit.source_operation_completions_v1 where operation_id=m.operation_id;
 select *into strict legs from cp7_credit.payment_source_legs_v1 where operation_id=m.operation_id;
 select *into strict q from cp7_payment_correction.requests where actor=m.actor and request_id=m.request_id;
 select *into strict l from cp7_payment_correction.links where original_id=m.source_id;
 perform cp7_credit.assert_source_completion_v1(m.operation_id);
 expected:=jsonb_build_object('contract_version','cp7.sales-payment-correction.v1','kind','COMMITTED_OUTCOME','action','PAYMENT_CORRECT',
  'request_id',m.request_id,'sale_id',m.sale_id,'status',c.final_native_source#>>'{sale,status}',
  'row_version',c.final_native_source#>>'{sale,row_version}','payment_id',legs.replacement_id,'payment_status','POSTED',
  'original_payment_id',m.source_id,'original_payment_status','REVERSED','link',cp7_payment_correction.link_value(l));
 if(q.payload,q.expected_version,q.response)is distinct from(m.payload,m.expected_version,expected)
  or exists(select 1 from cp7_credit.source_operation_work_v1 where operation_id=m.operation_id)
  or exists(select 1 from cp7_credit.payment_source_context_v1 where operation_id=m.operation_id
   or(backend_pid,transaction_id)=(m.backend_pid,m.transaction_id))
  or exists(select 1 from cp7_payment_correction.context where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_sales.command_context where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_credit.execution_context where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=m.backend_pid and transaction_id=m.transaction_id)then
  raise exception 'CP7_CREDIT_PAYMENT_FINAL_RECEIPT_OR_SCOPE_NOT_CLOSED';end if;
 perform cp7_credit.assert_current_materialized_profile(m.sale_id,m.sale_id,m.sale_id);
end $$;

create function cp7_credit.enforce_payment_source_closed_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_credit.assert_payment_source_closed_v1(new.operation_id);return null;
end $$;
create constraint trigger payment_source_closed after insert or update on cp7_credit.payment_source_context_v1
 deferrable initially deferred for each row execute function cp7_credit.enforce_payment_source_closed_v1();
create constraint trigger payment_source_closed after insert on cp7_credit.payment_source_legs_v1
 deferrable initially deferred for each row execute function cp7_credit.enforce_payment_source_closed_v1();
