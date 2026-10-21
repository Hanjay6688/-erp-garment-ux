-- Load only with the whole consumer coordinator, factual integration and
-- deferred closure. Missing callbacks below refuse; there are no OK stubs.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.validate_consumer_payload_v1(p jsonb,p_quote_required boolean)returns void
language plpgsql immutable security invoker set search_path=''as $$
declare key text;physical timestamptz;required text[]:=array['action','cohort_id','target_sale_id','cash_account_id',
 'restores_event_id','amount','physical_at','reason','reference'];
begin
 if p_quote_required is null then raise exception 'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS';end if;
 if p_quote_required then required:=array_append(required,'quote_sha256');end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&required or p-required<>'{}'::jsonb
  or p->>'action'is null or p->>'action'not in('APPLY','REFUND','UNDO')then
  raise exception 'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS';end if;
 foreach key in array required loop
  if jsonb_typeof(p->key)not in('string','null')then raise exception 'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS';end if;
 end loop;
 if jsonb_typeof(p->'reason')is distinct from'string'or p->>'reason'<>btrim(p->>'reason')
  or length(p->>'reason')not between 5 and 1000
  or jsonb_typeof(p->'physical_at')is distinct from'string'or btrim(p->>'physical_at')=''
  or (p->>'physical_at')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$'
  or p->>'reference'is not null and(length(p->>'reference')>100 or p->>'reference'<>btrim(p->>'reference'))
  or p_quote_required and(p->>'quote_sha256'is null or p->>'quote_sha256'!~'^[0-9a-f]{64}$')then
  raise exception 'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS';end if;
 physical:=(p->>'physical_at')::timestamptz;
 if not isfinite(physical)then raise exception 'CP7_CREDIT_CONSUMER_EXPLICIT_PHYSICAL_REQUIRED';end if;
 foreach key in array array['cohort_id','target_sale_id','cash_account_id','restores_event_id']loop
  if p->>key is not null and p->>key!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'then
   raise exception 'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS';end if;
 end loop;
 if p->>'action'='UNDO'then
  if p->>'restores_event_id'is null or p->>'cohort_id'is not null or p->>'target_sale_id'is not null
   or p->>'cash_account_id'is not null or p->>'amount'is not null then
   raise exception 'CP7_CREDIT_CONSUMER_UNDO_NAMES_ORIGINAL_ONLY';end if;
 else
  if p->>'cohort_id'is null or p->>'restores_event_id'is not null
   or p->>'amount'is null or p->>'amount'!~'^(0|[1-9][0-9]*)\.[0-9]{2}$'
   or(p->>'amount')::numeric<=0
   or(p->>'action'='APPLY')is distinct from(p->>'target_sale_id'is not null)
   or(p->>'action'='REFUND')is distinct from(p->>'cash_account_id'is not null)then
   raise exception 'CP7_CREDIT_CONSUMER_EXACT_POSITIVE_CHOICE_REQUIRED';end if;
 end if;
end $$;

create function cp7_credit.consumer_payload_kind_v1(p jsonb)returns text
language plpgsql stable security definer set search_path=''as $$
declare e cp7_credit.consumption_events;a jsonb;
begin
 -- Read no private selector before the current common sales/AR read gate.
 a:=erp.get_my_access_v1();
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or a->'allowed'is distinct from'true'::jsonb or not erp.has_permission('sales.invoice.view')
  or not erp.has_permission('finance.ar.view')then
  raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if p->>'action'='UNDO'then
  select *into strict e from cp7_credit.consumption_events where id=(p->>'restores_event_id')::uuid;
  if e.amount<=0 or e.restores_event_id is not null then raise exception 'CP7_CREDIT_CONSUMER_POSITIVE_ORIGINAL_REQUIRED';end if;
  return e.event_kind;
 end if;
 return p->>'action';
end $$;

-- Reuse the matching Native owning write/reversal authorities. A refund keeps
-- the existing explicit OWNER/ADMIN cash-out predicate from initial refunds.
-- This is read again after every possible owning lock wait and on replay.
create function cp7_credit.consumer_command_access_v1(p_action text,p_kind text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if p_action is null or p_kind is null or p_action not in('APPLY','REFUND','UNDO')or p_kind not in('APPLY','REFUND')
  or p_action<>'UNDO'and p_action<>p_kind then raise exception 'CP7_CREDIT_CONSUMER_ACTION_INVALID';end if;
 a:=cp7_sales.command_access(case when p_kind='APPLY'then case when p_action='UNDO'then'PAYMENT_REVERSE'else'PAYMENT'end
   else case when p_action='UNDO'then'RETURN_REVERSE'else'RETURN'end end);
 if p_kind='REFUND'then
  perform erp.require_owner_admin();
  if not erp.has_permission('finance.cash.view')then
   raise exception using errcode='42501',message='CP7_CREDIT_REFUND_CASH_ACCESS_REQUIRED';end if;
 end if;
 return jsonb_build_object('action',p_action,'event_kind',p_kind,'access',a);
end $$;

-- This is a genuine typed consumer capability, not a fabricated sales/BB
-- context. The exact Native guard derivation dispatches here only for this
-- backend/transaction and leaves all original fine-refusal branches in place.
create function cp7_credit.consumer_internal_allowed_v1()returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.consumer_execution_context;q cp7_credit.consumer_requests_v1;o cp7_credit.consumer_operations_v1;
begin
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null
  or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_CURRENT_ACTOR_REQUIRED';end if;
 select *into strict c from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=c.actor and request_id=c.request_id;
 select *into strict o from cp7_credit.consumer_operations_v1 where id=c.operation_id;
 if c.phase not in('LOCKED','POSTING','MATERIALIZED','COMPLETE')or q.response is not null
  or(c.actor,c.request_id,c.action,c.payload_sha256,c.quote_sha256,c.authority_snapshot)is distinct from
    (o.actor,o.request_id,o.action,o.payload_sha256,o.quote_sha256,o.authority_snapshot)
  or q.action<>o.action or cp7_credit.pg_jsonb_sha256(q.payload)<>o.payload_sha256
  or o.actor_app_user_id is distinct from erp.current_app_user_id()
  or q.payload->>'quote_sha256'<>o.quote_sha256
  or cp7_credit.consumer_command_access_v1(o.action,o.event_kind)is distinct from o.authority_snapshot then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_OWN_CURRENT_SCOPE_REQUIRED';end if;
 -- Do not call source/HPP collectors from require_internal's own dispatch:
 -- those Native readers can call require_internal themselves. This branch
 -- proves genuine pending typed operation ownership and current permissions;
 -- the poster's separate bound callback proves the full financial source.
 return true;
end $$;

create function cp7_credit.assert_consumer_bound_post_v1(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.consumer_posting_scope_v1;o cp7_credit.consumer_operations_v1;kind text;
begin
 perform cp7_credit.consumer_internal_allowed_v1();
 select *into strict s from cp7_credit.consumer_posting_scope_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 select *into strict o from cp7_credit.consumer_operations_v1 where id=s.operation_id;
 perform cp7_credit.assert_consumer_operation_bound_v1(o.id);
 kind:=case when o.action='UNDO'then'CP7_CUSTOMER_CREDIT_EVENT_REVERSE'
  when o.event_kind='APPLY'then'CP7_CUSTOMER_CREDIT_APPLY'else'CP7_CUSTOMER_CREDIT_REFUND'end;
 if(s.actor,s.request_id,s.operation_id,s.source_type,s.source_id,s.economic_date,s.transaction_date,s.lines_sha256_pg)
   is distinct from(o.actor,o.request_id,o.id,kind,o.id,o.economic_date,o.transaction_date,cp7_credit.native_lines_sha256(p_lines))
  or(p_type,p_source,p_economic)is distinct from(kind,o.id,o.economic_date)
  or cp7_credit.native_cent_lines(p_lines)is distinct from cp7_credit.consumer_operation_lines_v1(o.id)
  or not exists(select 1 from cp7_credit.consumer_execution_context c where c.backend_pid=s.backend_pid
   and c.transaction_id=s.transaction_id and c.actor=s.actor and c.operation_id=o.id and c.phase='POSTING')then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_EXACT_POST_SCOPE_REQUIRED';end if;
end $$;

create function cp7_credit.consumer_bound_book_date_v1(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;lawful date;period jsonb;
begin
 -- The unchanged Native poster has already acquired period SHARE here.
 perform cp7_credit.assert_consumer_bound_post_v1(p_type,p_source,p_economic,p_lines);
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_source;
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 if period is distinct from o.period_snapshot or lawful is null or o.transaction_date<lawful
  or o.transaction_date>erp._cp3_business_date(statement_timestamp())
  or o.transaction_date is distinct from(o.book_manifest->>'selected_book_date')::date then
  raise exception 'CP7_CREDIT_CONSUMER_DATE_REPLAN_REQUIRED';end if;
 return o.transaction_date;
end $$;

create function cp7_credit.consumer_bound_audit_v1()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.consumer_posting_scope_v1;o cp7_credit.consumer_operations_v1;
begin
 select *into strict s from cp7_credit.consumer_posting_scope_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 select *into strict o from cp7_credit.consumer_operations_v1 where id=s.operation_id;
 perform cp7_credit.assert_consumer_bound_post_v1(s.source_type,s.source_id,s.economic_date,cp7_credit.consumer_operation_lines_v1(o.id));
 return jsonb_build_object('book_date_basis','ACTUAL_CONSUMER_SOURCE_TARGET_AND_NATIVE_PERIOD',
  'operation_id',o.id,'cohort_id',o.cohort_id,'source_sale_id',o.source_sale_id,
  'target_sale_id',o.target_sale_id,'restores_event_id',o.restores_event_id,
  'projection_sha256',o.projection_sha256,'book_manifest',o.book_manifest);
end $$;

create function cp7_credit.consumer_command_v1(p_payload jsonb,p_request uuid,p_versions jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare q cp7_credit.consumer_requests_v1;authority jsonb;kind text;result jsonb;key text;operation uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_credit.validate_consumer_payload_v1(p_payload,true);
 -- Authenticate before resolving any private original-event selector.
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_CURRENT_ACTOR_REQUIRED';end if;
 kind:=cp7_credit.consumer_payload_kind_v1(p_payload);
 authority:=cp7_credit.consumer_command_access_v1(p_payload->>'action',kind);
 if p_request is null or jsonb_typeof(p_versions)is distinct from'object'or p_versions='{}'::jsonb then
  raise exception 'CP7_CREDIT_CONSUMER_REQUEST_AND_REVIEW_REQUIRED';end if;
 for key in select jsonb_object_keys(p_versions)loop
  if key!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'or jsonb_typeof(p_versions->key)is distinct from'string'
   or p_versions->>key!~'^[1-9][0-9]{0,18}$'or(p_versions->>key)::numeric>9223372036854775807 then
   raise exception 'CP7_CREDIT_CONSUMER_REVIEW_VERSIONS_INVALID';end if;
 end loop;
 perform cp7_credit.assert_no_ambient_native_context();
 perform cp7_credit.assert_consumer_scopes_clear_v1();
 insert into cp7_credit.consumer_requests_v1(actor,request_id,action,payload,expected_versions)
  values(auth.uid(),p_request,p_payload->>'action',p_payload,p_versions)on conflict do nothing;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=auth.uid()and request_id=p_request for update;
 if(q.action,q.payload,q.expected_versions)is distinct from(p_payload->>'action',p_payload,p_versions)then
  raise exception 'CP7_CREDIT_CONSUMER_REQUEST_CHANGED';end if;
 if cp7_credit.consumer_command_access_v1(q.action,kind)is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_ACCESS_CHANGED_AFTER_REQUEST_WAIT';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 perform cp7_credit.assert_consumer_scopes_clear_v1();
 if q.response is not null then
  operation:=cp7_credit.consumer_completed_operation_v1(q.actor,q.request_id,q.response);
  perform cp7_credit.assert_consumer_closed_v1(operation);
  if cp7_credit.consumer_command_access_v1(q.action,kind)is distinct from authority then
   raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_REPLAY_ACCESS_CHANGED';end if;
  return q.response;
 end if;
 insert into cp7_credit.consumer_execution_context(backend_pid,transaction_id,actor,request_id,action,phase,
  operation_id,payload_sha256,quote_sha256,authority_snapshot)
 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,q.action,'CLAIMED',null,
  cp7_credit.pg_jsonb_sha256(p_payload),p_payload->>'quote_sha256',authority);
 result:=cp7_credit.consumer_execute_v1(p_request);
 if result->>'kind'is distinct from'COMMITTED_OUTCOME'or result->>'request_id'is distinct from p_request::text
  or result->>'action'is distinct from q.action or result->>'operation_id'is null then
  raise exception 'CP7_CREDIT_CONSUMER_REAL_OUTCOME_REQUIRED';end if;
 operation:=(result->>'operation_id')::uuid;
 if not exists(select 1 from cp7_credit.consumer_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.actor=auth.uid()and c.request_id=p_request and c.operation_id=operation and c.phase='COMPLETE')then
  raise exception 'CP7_CREDIT_CONSUMER_COMPLETION_SCOPE_REQUIRED';end if;
 update cp7_credit.consumer_requests_v1 set response=result where actor=auth.uid()and request_id=p_request;
 delete from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 perform cp7_credit.assert_consumer_closed_v1(operation);
 if cp7_credit.consumer_command_access_v1(q.action,kind)is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_FINAL_ACCESS_CHANGED';end if;
 return result;
end $$;

do $private$declare sig text;begin
 foreach sig in array array['validate_consumer_payload_v1(jsonb,boolean)','consumer_payload_kind_v1(jsonb)',
 'consumer_command_access_v1(text,text)','consumer_internal_allowed_v1()',
 'assert_consumer_bound_post_v1(text,uuid,date,jsonb)','consumer_bound_book_date_v1(text,uuid,date,jsonb)',
 'consumer_bound_audit_v1()','consumer_command_v1(jsonb,uuid,jsonb)']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
alter function cp7_credit.consumer_command_v1(jsonb,uuid,jsonb)owner to cp7_credit_write;
-- Public quote/save facades are created last by the complete installer, after
-- all callbacks, current-reader derivations and deferred closure are verified.
