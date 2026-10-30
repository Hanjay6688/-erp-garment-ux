create function cp7_credit_note_carry_de.assert_historical_v1(p_root uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare p jsonb:=cp7_credit_note_carry_de.proof_v1(p_root);old_doc jsonb;new_doc jsonb;row_value jsonb;actual_ids jsonb;expected_ids jsonb;
 assignment cp7_credit_note_carry_de.assignments_v1;begin
 perform cp7_credit_note_carry_de.assert_chain_v1(p_root);
 old_doc:=cp7_credit_note_carry_de.raw_document_v1(p_root);
 new_doc:=cp7_credit_note_carry_de.raw_document_v1((p->>'replacement_sale_id')::uuid);
 if old_doc is distinct from p#>'{actual_proof,original_document}'
  or new_doc-'sale'is distinct from(p#>'{actual_proof,replacement_document}')-'sale'
  or(new_doc->'sale')-array['status','row_version','updated_at']is distinct from(p#>'{actual_proof,replacement_document,sale}')-array['status','row_version','updated_at']then
  raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_HISTORY_CHANGED';end if;
 select coalesce(jsonb_agg(event_id order by event_id),'[]')into actual_ids from cp7_credit_note_carry_de.assignments_v1 where operation_id=(p->>'operation_id')::uuid;
 select coalesce(jsonb_agg((v#>>'{event,id}')::uuid order by(v#>>'{event,id}')::uuid),'[]')into expected_ids from jsonb_array_elements(p#>'{basis,incoming_facts}')v;
 if actual_ids is distinct from expected_ids then raise exception 'CP7_CREDIT_NOTE_CARRY_ASSIGNMENT_SET_CHANGED';end if;
 for assignment in select *from cp7_credit_note_carry_de.assignments_v1 where operation_id=(p->>'operation_id')::uuid loop
  if(assignment.root_sale_id,assignment.replacement_sale_id,assignment.event_kind)is distinct from(p_root,(p->>'replacement_sale_id')::uuid,'APPLY')
   or not exists(select 1 from jsonb_array_elements(p#>'{basis,incoming_facts}')v where v->'event'=assignment.event_snapshot and v->'journal'=assignment.journal_snapshot)
   or assignment.event_snapshot is distinct from(select to_jsonb(e)from cp7_credit.consumption_events e where e.id=assignment.event_id)
   or assignment.journal_snapshot is distinct from cp7_credit.materialized_journal_payload((assignment.event_snapshot->>'journal_id')::uuid)
   or assignment.event_sha256 is distinct from cp7_credit.pg_jsonb_sha256(assignment.event_snapshot)
   or assignment.journal_sha256 is distinct from cp7_credit.pg_jsonb_sha256(assignment.journal_snapshot)then
   raise exception 'CP7_CREDIT_NOTE_CARRY_IMMUTABLE_CONSUMER_CHANGED';end if;
 end loop;
end $$;
-- A consumer has already posted its signed event and complete financial fact
-- before its original status UPDATE. At that one owning phase the header must
-- still equal the fully checked old capture. This is no reader capability and
-- does not skip any current money, history, prefix or provenance assertion.
-- None of the helpers below calls assert_current_materialized_profile.
create function cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1(p_sale uuid,p_actual jsonb,p_status text)returns boolean
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare c cp7_credit.consumer_execution_context;q cp7_credit.consumer_requests_v1;o cp7_credit.consumer_operations_v1;
 h erp.sales_headers;e cp7_credit.consumption_events;before_profile jsonb;before_native jsonb;actual jsonb;root uuid;
 old_incoming numeric;incoming numeric;net numeric;old_status text;new_status text;begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or current_setting('transaction_isolation')is distinct from'read committed'then return false;end if;
 select *into c from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 if c.operation_id is null or c.phase is distinct from'MATERIALIZED'then return false;end if;
 select *into o from cp7_credit.consumer_operations_v1 where id=c.operation_id;
 select *into q from cp7_credit.consumer_requests_v1 where actor=c.actor and request_id=c.request_id;
 if o.id is null or q.actor is null or q.response is not null
  or(c.actor,c.request_id,c.action,c.payload_sha256,c.quote_sha256,c.authority_snapshot)is distinct from
   (o.actor,o.request_id,o.action,o.payload_sha256,o.quote_sha256,o.authority_snapshot)
  or o.event_kind is distinct from'APPLY'or o.action not in('APPLY','UNDO')
  or(o.target_sale_id,o.target_current_leaf_id)is distinct from(p_sale,p_sale)
  or exists(select 1 from cp7_credit.consumer_completions_v1 where operation_id=o.id)
  or exists(select 1 from cp7_credit.consumer_posting_scope_v1 where backend_pid=c.backend_pid and transaction_id=c.transaction_id)
  or exists(select 1 from cp7_credit_note_carry_de.work_v1 where backend_pid=c.backend_pid and transaction_id=c.transaction_id)
  or exists(select 1 from cp7_note.context where backend_pid=c.backend_pid and transaction_id=c.transaction_id)
  or exists(select 1 from cp7_sales.command_context where backend_pid=c.backend_pid and transaction_id=c.transaction_id)then return false;end if;
 if cp7_credit.consumer_internal_allowed_v1()is distinct from true then return false;end if;
 perform cp7_credit.assert_no_ambient_native_context();
 if(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from o.period_snapshot then return false;end if;
 perform cp7_credit.assert_consumer_operation_input_v1(o.id);
 select *into strict e from cp7_credit.consumption_events where id=o.id;
 perform cp7_credit.consumer_actual_manifest_v1(o.id);
 if e.lines_sha256_pg is distinct from cp7_credit.consumer_verify_posted_journal_v1(o.id,e.journal_id)then return false;end if;
 root:=cp7_credit_note_carry_de.root_v1(p_sale);
 if o.target_root_sale_id is distinct from root or not cp7_credit_note_carry_de.is_current_v1(p_sale)then return false;end if;
 before_profile:=o.locked_sources#>array['sources',p_sale::text,'profile'];
 before_native:=o.locked_sources#>array['sources',p_sale::text,'native'];
 if jsonb_typeof(before_profile)is distinct from'object'or jsonb_typeof(before_native)is distinct from'object'
  or(before_profile->>'sale_id',before_profile->>'root_sale_id',before_profile->>'current_leaf_id')is distinct from(p_sale::text,root::text,p_sale::text)
  or(before_profile->>'I')::numeric is distinct from 0::numeric then return false;end if;
 select *into strict h from erp.sales_headers where id=p_sale;
 if h.status is distinct from p_status or h.status is distinct from before_native#>>'{sale,status}'
  or h.row_version::text is distinct from before_native#>>'{sale,row_version}'
  or h.row_version::text is distinct from o.projection#>>array['expected_versions',p_sale::text]
  or cp7_credit.consumer_native_invariant_v1(p_sale)is distinct from o.before_native->p_sale::text then return false;end if;
 actual:=cp7_credit.inspect_current_materialized_profile(p_sale,root,p_sale);
 if p_actual is distinct from actual then return false;end if;
 old_incoming:=(before_profile->>'U')::numeric;incoming:=(actual->>'U')::numeric;
 net:=(cp7_credit_note_carry_de.proof_v1(root)#>>'{review,replacement_net}')::numeric;
 old_status:=case when old_incoming=net then'PAID'when old_incoming>0 then'PARTIAL_PAID'else'POSTED'end;
 new_status:=case when incoming=net then'PAID'when incoming>0 then'PARTIAL_PAID'else'POSTED'end;
 return old_incoming is not null and incoming is not null and net is not null
  and old_incoming>=0 and old_incoming<=net and incoming>=0 and incoming<=net
  and incoming=old_incoming+o.amount and(actual->>'I')::numeric=0
  and p_status=old_status and p_status<>new_status;
end $$;
create function cp7_credit_note_carry_de.assert_profile_v1(p_sale uuid,p_root uuid,p_leaf uuid,p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare p jsonb:=cp7_credit_note_carry_de.proof_v1(p_root);ar jsonb;gross numeric;incoming numeric;raw_ar numeric;status text;root uuid;f jsonb;events jsonb;result jsonb;begin
 if p is null or p_sale<>p_leaf or(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from(p_sale::text,p_root::text,p_leaf::text)
  or p_sale is distinct from(p->>'replacement_sale_id')::uuid then raise exception 'CP7_CREDIT_NOTE_CARRY_CURRENT_ASSIGNMENT_CHANGED';end if;
 perform cp7_credit_note_carry_de.assert_historical_v1(p_root);
 if exists(select 1 from cp7_credit.return_families where family_root_sale_id=p_root)
  or exists(select 1 from erp.sales_payments where sale_id in(p_root,p_sale))
  or exists(select 1 from erp.sales_returns where sale_id in(p_root,p_sale))then raise exception 'CP7_CREDIT_NOTE_CARRY_UNQUALIFIED_CHILD_HISTORY';end if;
 ar:=cp7_credit.consumer_invoice_ar_source_v1(p_sale);gross:=(ar->>'gross_amount')::numeric;incoming:=(p_actual->>'U')::numeric;
 if ar->>'account_id'is distinct from p#>>'{basis,ar_source,account_id}'or(ar->>'account_id')::uuid<>cp7_credit.account_by_mapping_v1('AR_CUSTOMER')
  or(ar->>'customer_id')is distinct from p#>>'{basis,customer_id}'or gross is distinct from(p#>>'{review,replacement_net}')::numeric
  or(p_actual->>'I')::numeric<>0 or incoming<0 or incoming>gross then raise exception 'CP7_CREDIT_NOTE_CARRY_CURRENT_MONEY_CHANGED';end if;
 events:=cp7_credit_note_carry_de.current_events_v1(p_sale);
 result:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit_note_carry_de.ordinal_v1(p_sale));
 if result->'arithmetic_supported'is distinct from'true'::jsonb then raise exception 'CP7_CREDIT_NOTE_CARRY_CURRENT_PREFIX_UNFUNDED';end if;
 select coalesce(sum(l.debit-l.credit),0)into raw_ar from erp.journal_lines l where l.account_id=(ar->>'account_id')::uuid
  and l.customer_id=(ar->>'customer_id')::uuid and l.journal_entry_id in(select substring(v->>'id'from 9)::uuid from jsonb_array_elements(events)v);
 select h.status into strict status from erp.sales_headers h where h.id=p_sale;
 if raw_ar is distinct from gross-incoming then
  raise exception 'CP7_CREDIT_NOTE_CARRY_RAW_AR_OR_STATUS_CHANGED';end if;
 for f in select value from jsonb_array_elements(p#>'{before_materialized,actual_objects}')loop
  if not exists(select 1 from jsonb_array_elements(p_actual->'actual_objects')v where v=f)then raise exception 'CP7_CREDIT_NOTE_CARRY_RETAINED_CREDIT_FACT_CHANGED';end if;
 end loop;
 for root in select value::uuid from jsonb_array_elements_text(p_actual->'upstream_root_ids')where value::uuid<>p_root loop
  perform cp7_credit.assert_current_materialized_profile(root,root,root);
 end loop;
 perform cp7_credit.assert_financial_materialization_provenance(p_actual);
 if status is distinct from(case when incoming=gross then'PAID'when incoming>0 then'PARTIAL_PAID'else'POSTED'end)
  and cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1(p_sale,p_actual,status)is distinct from true then
  raise exception 'CP7_CREDIT_NOTE_CARRY_RAW_AR_OR_STATUS_CHANGED';end if;
end $$;
create function cp7_credit_note_carry_de.invoice_profile_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare root uuid:=cp7_credit_note_carry_de.root_v1(p_sale);h erp.sales_headers;profile jsonb;net numeric;incoming numeric;begin
 select *into strict h from erp.sales_headers where id=p_sale;
 perform cp7_credit.assert_current_materialized_profile(p_sale,root,p_sale);
 profile:=cp7_credit.inspect_current_materialized_profile(p_sale,root,p_sale);
 select coalesce(sum(line_total),0)into net from erp.sales_items where sale_id=p_sale;
 incoming:=(profile->>'U')::numeric;
 return jsonb_build_object('sale_id',p_sale,'row_version',h.row_version::text,'status',h.status,
  'gross',cp7_credit.cent_text(net),'net',cp7_credit.cent_text(net),'P','0.00','U',cp7_credit.cent_text(incoming),'I','0.00',
  'E',cp7_credit.cent_text(incoming),'AR',cp7_credit.cent_text(net-incoming),'materialized',profile);
end $$;
create function cp7_credit_note_carry_de.assert_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare o cp7_credit_note_carry_de.operations_v1;q cp7_note.requests;p jsonb;expected jsonb;plan jsonb;begin
 select *into strict o from cp7_credit_note_carry_de.operations_v1 where operation_id=p_operation;
 select *into strict q from cp7_note.requests where actor=o.actor and request_id=o.request_id;p:=o.proof;
 expected:=jsonb_build_object('contract_version','cp7.note-correction-outcome.v1','kind','COMMITTED_OUTCOME','action','CORRECT','request_id',o.request_id,
  'root_sale_id',o.source_sale_id,'previous_sale_id',o.source_sale_id,'sale_id',o.replacement_sale_id,'revision_id',o.revision_id,'revision','1',
  'effective_at',(select sale_date from erp.sales_headers where id=o.source_sale_id));
 plan:=cp7_credit_note_carry_de.plan_v1(p->'basis',p#>>'{review,replacement_net}');
 if(q.payload,q.expected_version,q.response)is distinct from(o.payload,o.expected_version,expected)or o.response is distinct from expected
  or(p->>'operation_id',p->>'actor',p->>'request_id',p->>'source_sale_id',p->>'replacement_sale_id',p->>'revision_id',p->>'expected_version',p->'payload',p->>'phase')is distinct from
   (o.operation_id::text,o.actor::text,o.request_id::text,o.source_sale_id::text,o.replacement_sale_id::text,o.revision_id::text,o.expected_version,o.payload,'MATERIALIZED')
  or p->'review'is distinct from plan or o.payload->'credit_carry_review'is distinct from cp7_credit_note_carry_de.review_payload_v1(plan)
  or exists(select 1 from cp7_credit_note_carry_de.work_v1 where operation_id=o.operation_id)then raise exception 'CP7_CREDIT_NOTE_CARRY_HISTORICAL_RECEIPT_CHANGED';end if;
 perform cp7_credit_note_carry_de.assert_historical_v1(o.source_sale_id);
 perform cp7_credit.assert_current_materialized_profile(o.replacement_sale_id,o.source_sale_id,o.replacement_sale_id);
end $$;
create function cp7_credit_note_carry_de.enforce_closed_v1()returns trigger
language plpgsql security definer set search_path=''as $$
begin perform cp7_credit_note_carry_de.assert_closed_v1((to_jsonb(new)->>'operation_id')::uuid);return null;end$$;
do $closure$declare t text;begin
 foreach t in array array['work_v1','operations_v1','assignments_v1']loop
  execute 'create constraint trigger operation_closed after insert or update on cp7_credit_note_carry_de.'||t||' deferrable initially deferred for each row execute function cp7_credit_note_carry_de.enforce_closed_v1()';
 end loop;
end $closure$;

create function cp7_credit_note_carry_de.validate_current_v1(p_historical uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare a record;begin
 select *into strict a from cp7_credit.current_leaf_assignment(p_historical);
 if cp7_credit_note_carry_de.has_root_v1(a.root_sale_id)then perform cp7_credit.consumer_invoice_profile_v1(a.current_leaf_id);
 else perform cp7_credit.consumer_invoice_profile_v1(p_historical);end if;
end $$;
create function cp7_credit_note_carry_de.target_assignment_v1(p_selection jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare root uuid:=(p_selection->>'target_root_sale_id')::uuid;leaf uuid:=(p_selection->>'target_current_leaf_id')::uuid;
 p jsonb;historical uuid;event_id uuid;begin
 if root is null or not cp7_credit_note_carry_de.has_root_v1(root)then return null;end if;
 perform cp7_credit_note_carry_de.assert_chain_v1(root);p:=cp7_credit_note_carry_de.proof_v1(root);
 if leaf is distinct from(p->>'replacement_sale_id')::uuid or leaf is distinct from(p_selection->>'target_sale_id')::uuid then
  raise exception 'CP7_CREDIT_NOTE_CARRY_REVIEW_ASSIGNMENT_CHANGED';end if;
 event_id:=(p_selection->>'restores_event_id')::uuid;
 if event_id is not null then select target_sale_id into strict historical from cp7_credit.consumption_events where id=event_id;
 else historical:=leaf;end if;
 return jsonb_build_object('contract_version','cp7.note-credit-target-assignment.v1','root_sale_id',root,
  'historical_target_id',historical,'current_sale_id',leaf,'current_number',(select sale_number from erp.sales_headers where id=leaf),
  'revision_id',p->'revision_id','original_event_id',event_id,'proof_sha256',cp7_credit.pg_jsonb_sha256(p));
end $$;
