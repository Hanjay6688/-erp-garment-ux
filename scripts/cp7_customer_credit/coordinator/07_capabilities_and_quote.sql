do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.get_initial_return_quote_v1(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare choice jsonb;legacy jsonb;b jsonb;k text;keys text[];
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_query->>'kind'='ACCOUNT_OPTIONS'then return cp7_credit.initial_account_options_v1(p_query);end if;
 if jsonb_typeof(p_query)is distinct from'object'or not p_query?&array['sale_id','expected_version','review_token','return_payload','settlement']
  or p_query-array['sale_id','expected_version','review_token','return_payload','settlement']<>'{}'::jsonb then raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 choice:=p_query->'settlement';
 if jsonb_typeof(choice)is distinct from'object'or not choice?&array['mode','credit_account_id','cash_account_id','refund_physical_at','reference']
  or choice-array['mode','credit_account_id','cash_account_id','refund_physical_at','reference']<>'{}'::jsonb
  or jsonb_typeof(p_query->'expected_version')is distinct from'string'or p_query->>'expected_version'!~'^[1-9][0-9]{0,18}$'
  or(p_query->>'expected_version')::numeric>9223372036854775807 then raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 for k in select jsonb_object_keys(choice)loop
  if jsonb_typeof(choice->k)not in('string','null')then raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 end loop;
 if choice->>'mode'is not null and choice->>'mode'not in('CREDIT','REFUND')
  or choice->>'mode'is distinct from'REFUND'and(choice->>'cash_account_id'is not null or choice->>'refund_physical_at'is not null or choice->>'reference'is not null)
  or length(choice->>'reference')>100 then raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 foreach k in array array['credit_account_id','cash_account_id']loop
  if choice->>k is not null and choice->>k!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'then raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 end loop;
 if jsonb_typeof(p_query->'return_payload')is distinct from'object'or p_query->'return_payload'?|array['sale_id','review_token']then
  raise exception 'CP7_CREDIT_QUOTE_FIELDS';end if;
 legacy:=p_query->'return_payload'||jsonb_build_object('sale_id',p_query->'sale_id','review_token',p_query->'review_token');
 b:=cp7_credit.build_initial_return_v1(legacy,p_query->>'expected_version',choice);
 return b->'quote';
end $$;

-- The outer role cannot read this postgres-owned RLS-denied table. Preserve
-- its complete current-backend/transaction leak check through a void-only
-- capability; never grant table SELECT or let RLS turn a leak into no rows.
create function cp7_credit.assert_return_native_scope_cleared_v1()returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if exists(select 1 from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED';end if;
end $$;

create function cp7_credit.close_completed_return_receipt_v1(p_request uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.initial_return_materializations;
begin
 select *into strict m from cp7_credit.initial_return_materializations where actor=auth.uid()and request_id=p_request;
 perform cp7_credit.assert_initial_return_closed_v1(m.operation_id);
 perform cp7_credit.return_command_access(m.settlement->>'mode');
end $$;

-- Must be composed into owning wrapper02 immediately AFTER writing its actual
-- outer receipt and clearing its temporary scope, BEFORE it returns. No false
-- pending receipt is treated as final factual closure. See the exact derived
-- replacement in 08_outer_wrapper.sql (no change to the public wire).

create function cp7_credit.enforce_initial_scope_cleared_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare row jsonb:=to_jsonb(new);pid integer:=(row->>'backend_pid')::integer;tx bigint:=(row->>'transaction_id')::bigint;
begin
 if exists(select 1 from cp7_credit.initial_return_work where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.source_mutation_scope where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.execution_context where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.return_native_scope where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.return_command_scope where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=pid and transaction_id=tx)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where backend_pid=pid and transaction_id=tx)then
  raise exception 'CP7_CREDIT_PRIVATE_TRANSACTION_SCOPE_LEAK';end if;
 return null;
end $$;
do $scope_closure$declare t text;begin
 foreach t in array array['initial_return_work','source_mutation_scope','execution_context','return_native_scope','return_command_scope','posting_scope','initial_refund_posting_scope']loop
  execute format('create constraint trigger initial_scope_cleared after insert on cp7_credit.%I deferrable initially deferred for each row execute function cp7_credit.enforce_initial_scope_cleared_v1()',t);
 end loop;
end $scope_closure$;

-- Explicit private owners and grants. New financial facts stay postgres-owned
-- and RLS-denied. Only the new request/scope writer owns its own new mutable
-- outer tables. It receives no ERP DML or generic sales/journal capability.
do $role$begin
 if not exists(select 1 from pg_roles where rolname='cp7_credit_write')then
  create role cp7_credit_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
 end if;
 if exists(select 1 from pg_roles where rolname='cp7_credit_write'and(rolcanlogin or rolinherit or rolsuper or rolcreatedb or rolcreaterole or rolreplication or rolbypassrls))then
  raise exception 'CP7_CREDIT_WRITE_ROLE_METADATA';end if;
end $role$;
alter table cp7_credit.return_requests owner to cp7_credit_write;
alter table cp7_credit.return_command_scope owner to cp7_credit_write;
alter table cp7_credit.return_native_scope owner to postgres;
grant usage on schema cp7_credit,cp7_sales,auth to cp7_credit_write;
grant execute on function auth.uid(),auth.jwt()to cp7_credit_write;
grant execute on function cp7_sales.validate_return(jsonb,boolean),cp7_sales.preclaim_credit_return(uuid,jsonb,text),
 cp7_sales.execute_preclaimed_credit_return(uuid,jsonb,text)to cp7_credit_write;
grant execute on function cp7_credit.pg_jsonb_sha256(jsonb),cp7_credit.validate_return_settlement_payload(jsonb),cp7_credit.return_command_access(text),
 cp7_credit.assert_no_ambient_native_context(),cp7_credit.assert_return_native_scope_cleared_v1(),cp7_credit.seal_return_settlement(uuid),cp7_credit.finish_return_settlement(uuid,jsonb),
 cp7_credit.assert_completed_return_receipt(uuid,jsonb,text,jsonb),cp7_credit.close_completed_return_receipt_v1(uuid)to cp7_credit_write;
grant usage on schema cp7_credit to cp7_sales_write;
grant execute on function cp7_credit.assert_pending_return_outer(uuid,jsonb,text),cp7_credit.assert_locked_return_outer(uuid,jsonb,text)to cp7_sales_write;
alter function cp7_credit.return_settlement_command(jsonb,uuid,text)owner to cp7_credit_write;
alter function cp7_sales.preclaim_credit_return(uuid,jsonb,text)owner to cp7_sales_write;
alter function cp7_sales.execute_preclaimed_credit_return(uuid,jsonb,text)owner to cp7_sales_write;
revoke all on function cp7_credit.return_settlement_command(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

-- Every function this slice creates or replaces has explicit postgres owner
-- and no outsider EXECUTE, except the fixed invoker outer writer above.
do $private_functions$declare sig text;begin
 foreach sig in array array[
 'initial_base_events_v1(uuid,uuid)','initial_preserved_source_v1(uuid,uuid)','assert_zero_excess_v1(jsonb)','initial_event_semantics_v1(jsonb)','review_before_own_draft_v1(uuid,uuid)',
 'has_ow04_participation_v1(uuid)','is_unchanged_native_return_v1(uuid)',
 'account_by_mapping_v1(text)','credit_account_facts_v1(uuid)','cash_account_facts_v1(uuid)','initial_hpp_projection_v1(jsonb)',
 'initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)','initial_po_hpp_lifecycle_amount_v1(uuid,uuid,uuid,uuid)','initial_po_hpp_book_v1(uuid,uuid,uuid,uuid,uuid)','initial_hpp_support_v1(uuid,uuid)','initial_hpp_account_facts_v1()',
 'component_movements_v1(jsonb)','initial_refund_book_plan_v1(jsonb,numeric,timestamp with time zone,date,date)','build_initial_return_v1(jsonb,text,jsonb)','build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)',
 'initial_choice_v1(jsonb)','initial_line_semantics_v1(jsonb)','assert_initial_work_v1(uuid,boolean)','assert_return_owner_context(uuid)',
 'seal_return_settlement(uuid)','assert_sealed_return_source(uuid)','native_return_enter(uuid)','native_return_guard(uuid,numeric,numeric,numeric)',
 'bound_book_date(text,uuid,date,jsonb)','post_return_journal(text,uuid,date,text,jsonb)','assert_owner_context(uuid)','actual_own_return_events_v1(uuid)',
 'rebuild_locked_plan(uuid)','assert_source_admission(uuid)','check_credit_account(uuid)','store_initial_plan_v1(uuid)','materialize_initial_objects_v1(uuid)',
 'native_return_complete(uuid,numeric,numeric)','initial_ordinal_input_v1(uuid,uuid)','assert_simple_native_base_v1(uuid)','assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)',
 'assert_financial_materialization_provenance(jsonb)','current_effective_paid(uuid)','assert_refund_operation_v1(uuid,uuid,text)','native_return_leave(uuid)',
 'finish_return_settlement(uuid,jsonb)','assert_completed_return_receipt(uuid,jsonb,text,jsonb)','native_source_enter(text,uuid)','native_source_complete(text,uuid)',
 'assert_initial_return_closed_v1(uuid)','enforce_initial_return_closure_v1()','get_initial_return_quote_v1(jsonb)','close_completed_return_receipt_v1(uuid)',
 'enforce_initial_scope_cleared_v1()','assert_return_native_scope_cleared_v1()']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_functions$;
