-- LOCAL counter instrumentation on the DECLARED consumer-context table only.
-- It is not installed by the product or any actual Native qualification.
create sequence local_e_phase.sentinel start 7;
select setval('local_e_phase.sentinel',7,true);
create function local_e_phase.truth()returns jsonb language plpgsql volatile as $$
declare t record;rows jsonb:='{}';sequences jsonb:='{}';one jsonb;begin
 for t in select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where c.relkind in('r','p')and n.nspname not in('pg_catalog','information_schema')and n.nspname!~'^pg_'
  and(n.nspname,c.relname)<>('local_e_phase','observations')order by 1,2 loop
  execute format('select coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),''[]'')from %I.%I r',t.nspname,t.relname)into one;
  rows:=rows||jsonb_build_object(t.nspname||'.'||t.relname,one);
 end loop;
 for t in select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where c.relkind='S'and n.nspname!~'^pg_'order by 1,2 loop
  execute format('select jsonb_build_array(last_value::text,is_called)from %I.%I',t.nspname,t.relname)into one;
  sequences:=sequences||jsonb_build_object(t.nspname||'.'||t.relname,one);
 end loop;
 return jsonb_build_object('rows',rows,'all_local_sequences',sequences);
end$$;
-- Privileged CORRUPTION MODEL only: rebind the declared pending metadata and
-- its real hashes so the signed-delta test reaches the actual deep predicate.
-- This is not a capability available to an app actor, nor catalog resealing.
create function local_e_phase.rebind_pending_metadata()returns void language plpgsql volatile as $$
declare o cp7_credit.consumer_operations_v1;q cp7_credit.consumer_requests_v1;binding text;object jsonb;begin
 select op.*into strict o from cp7_credit.consumer_operations_v1 op join cp7_credit.consumer_execution_context c on c.operation_id=op.id where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current();
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=o.actor and request_id=o.request_id;
 binding:=cp7_credit.consumer_quote_binding_v1(q.payload,o.locked_sources,o.projection);
 q.payload:=q.payload||jsonb_build_object('quote_sha256',binding);
 update cp7_credit.consumer_requests_v1 set payload=q.payload where actor=o.actor and request_id=o.request_id;
 update cp7_credit.consumer_operations_v1 set locked_sources_sha256=cp7_credit.pg_jsonb_sha256(locked_sources),
  payload_sha256=cp7_credit.pg_jsonb_sha256(q.payload),quote_sha256=binding where id=o.id;
 update cp7_credit.consumer_execution_context set payload_sha256=cp7_credit.pg_jsonb_sha256(q.payload),quote_sha256=binding where operation_id=o.id;
 update cp7_credit.consumption_events e set source_sha256=cp7_credit.pg_jsonb_sha256(to_jsonb(op))from cp7_credit.consumer_operations_v1 op where op.id=o.id and e.id=op.id;
 select cp7_credit.materialized_fact('CONSUMPTION',e.id,jsonb_build_object('event',to_jsonb(e),'actual',cp7_credit.materialized_journal_payload(e.journal_id)))into object from cp7_credit.consumption_events e where e.id=o.id;
 update cp7_credit.financial_materializations set payload_sha256=cp7_credit.pg_jsonb_sha256(q.payload),actual_objects=jsonb_build_array(object),actual_objects_sha256=cp7_credit.pg_jsonb_sha256(jsonb_build_array(object))where id=o.id;
 update cp7_credit.financial_materialization_objects set fact_sha256=object->>'fact_sha256'where materialization_id=o.id;
end$$;
create function local_e_phase.materialized_probe()returns trigger language plpgsql volatile as $$
declare target uuid:=new.operation_id;sale uuid;root uuid;actual jsonb;baseline jsonb;rule jsonb;message text;state text;detail text;raw_ar numeric;begin
 select target_current_leaf_id,target_root_sale_id into strict sale,root from cp7_credit.consumer_operations_v1 where id=target;
 actual:=cp7_credit.inspect_current_materialized_profile(sale,root,sale);
 select coalesce(sum(l.debit-l.credit),0)into raw_ar from erp.journal_lines l where l.account_id=cp7_credit.account_by_mapping_v1('AR_CUSTOMER')and l.customer_id=(local_e_phase.config()->>'customer')::uuid
  and l.journal_entry_id in(select substring(v->>'id'from 9)::uuid from jsonb_array_elements(cp7_credit_note_carry_de.current_events_v1(sale))v);
 if actual->>'U'is distinct from'0.00'or raw_ar<>550.00
  or(select status from erp.sales_headers where id=sale)is distinct from'PARTIAL_PAID'
  or cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1(sale,actual,'PARTIAL_PAID')is distinct from true then
  raise exception 'LOCAL_MATERIALIZED_PROBE_NOT_THE_ACTUAL_OWNED_POINT';end if;
 perform cp7_credit_note_carry_de.assert_profile_v1(sale,root,sale,actual);
 insert into local_e_phase.observations values('OWNED_MATERIALIZED_POSITIVE',jsonb_build_object('context_phase',new.phase,'operation_id',target,
  'U',actual->'U','raw_AR',raw_ar,'header_status_still_before_original_update','PARTIAL_PAID','expected_after_original_update','POSTED',
  'full_profile_returned',true,'actual_Native_credit',0));
 baseline:=local_e_phase.truth();
 for rule in select value from jsonb_array_elements(jsonb_build_array(
  jsonb_build_object('name','WRONG_ACTOR','sql','update local_e_phase.settings set value=jsonb_set(value,''{actor}'',to_jsonb(''00000000-0000-4000-8000-ffffffffffff''::text))'),
  jsonb_build_object('name','WRONG_PHASE','sql','update cp7_credit.consumer_execution_context set phase=''COMPLETE'''),
  jsonb_build_object('name','WRONG_BACKEND','sql','update cp7_credit.consumer_execution_context set backend_pid=backend_pid+1'),
  jsonb_build_object('name','WRONG_TRANSACTION','sql','update cp7_credit.consumer_execution_context set transaction_id=transaction_id+1'),
  jsonb_build_object('name','RECEIPT_ALREADY_PRESENT','sql','update cp7_credit.consumer_requests_v1 set response=''{}''::jsonb'),
  jsonb_build_object('name','COMPLETION_ALREADY_PRESENT','sql','insert into cp7_credit.consumer_completions_v1(operation_id)select operation_id from cp7_credit.consumer_execution_context'),
  jsonb_build_object('name','POSTING_SCOPE_NOT_CLEARED','sql','insert into cp7_credit.consumer_posting_scope_v1(backend_pid,transaction_id,operation_id)select backend_pid,transaction_id,operation_id from cp7_credit.consumer_execution_context'),
  jsonb_build_object('name','OLD_ROW_VERSION_CHANGED','sql',format('update erp.sales_headers set row_version=row_version+1 where id=%L::uuid',sale)),
  jsonb_build_object('name','OLD_STATUS_CHANGED','sql',format('update erp.sales_headers set status=''PAID'' where id=%L::uuid',sale)),
  jsonb_build_object('name','CURRENT_ACCESS_CHANGED','sql','update local_e_phase.settings set value=jsonb_set(value,''{authority}'',''{}''::jsonb)'),
  jsonb_build_object('name','CURRENT_PERIOD_CHANGED','sql','update erp.accounting_period_control set change_reason=''CORRUPTED LOCAL PERIOD'''),
  jsonb_build_object('name','IMMUTABLE_INPUT_CHANGED','sql','update cp7_credit.consumer_requests_v1 set payload=jsonb_set(payload,''{reason}'',''"Changed exact request reason"''::jsonb)'),
  jsonb_build_object('name','POSTED_JOURNAL_KIND_CHANGED','sql',format('update erp.journal_entries set source_type=''LOCAL_WRONG_KIND'' where source_id=%L::uuid',target)),
  jsonb_build_object('name','POSTED_JOURNAL_LINES_CHANGED','sql',format('update erp.journal_lines set credit=credit+0.01 where journal_entry_id in(select journal_id from cp7_credit.consumption_events where id=%L::uuid)',target)),
  jsonb_build_object('name','POSTED_JOURNAL_DATE_CHANGED','sql',format('update erp.journal_entries set transaction_date=transaction_date+1 where source_id=%L::uuid',target)),
  jsonb_build_object('name','MATERIALIZATION_CHANGED','sql',format('update cp7_credit.financial_materializations set actual_objects_sha256=repeat(''f'',64)where id=%L::uuid',target)),
  jsonb_build_object('name','NATIVE_STOCK_FACT_CHANGED','sql','insert into erp.fg_stock_movements(id)values(''00000000-0000-4000-8000-eeeeeeeeeeee'')'),
  jsonb_build_object('name','EXACT_SIGNED_DELTA_CHANGED_WITH_CONSISTENT_METADATA_HASHES','sql',format('update cp7_credit.consumer_operations_v1 set locked_sources=jsonb_set(locked_sources,array[''sources'',%L,''profile'',''U''],''"79.99"''::jsonb)where id=%L::uuid;select local_e_phase.rebind_pending_metadata()',sale::text,target)),
  jsonb_build_object('name','FABRICATED_PROFILE_ARGUMENT','sql','select 1','profile_corruption',true)
 ))loop
  message:=null;state:=null;detail:=null;
  begin
   execute rule->>'sql';
   actual:=cp7_credit.inspect_current_materialized_profile(sale,root,sale);
   if rule->>'profile_corruption'='true'then actual:=actual||jsonb_build_object('U','0.01');end if;
   perform cp7_credit_note_carry_de.assert_profile_v1(sale,root,sale,actual);
   raise exception 'LOCAL_NEGATIVE_WAS_ACCEPTED'using detail=rule->>'name';
  exception when others then
   get stacked diagnostics message=message_text,state=returned_sqlstate,detail=pg_exception_detail;
   if message='LOCAL_NEGATIVE_WAS_ACCEPTED'or state not in('P0001','P0002','42501')then raise;end if;
  end;
  if local_e_phase.truth()is distinct from baseline then raise exception 'LOCAL_COUNTER_CHANGED_FULL_ROWS_OR_SEQUENCES'using detail=rule->>'name';end if;
  insert into local_e_phase.observations values(rule->>'name',jsonb_build_object('refusal',message,'sqlstate',state,
   'detail',detail,'all_local_rows_and_sequences_restored',true,'Native_credit',0));
 end loop;
 return null;
end$$;
create trigger local_e_phase_probe after update on cp7_credit.consumer_execution_context
 for each row when(new.phase='MATERIALIZED'and old.phase is distinct from new.phase)
 execute function local_e_phase.materialized_probe();
