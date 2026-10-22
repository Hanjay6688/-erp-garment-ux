-- Pending whole consumer composition, exact current-reader/Native derivations
-- and Native qualification. No completion or permission success placeholder.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.consumer_outcome_v1(p_operation uuid,p_profiles jsonb,p_capacity jsonb)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.customer-credit-outcome.v1','kind','COMMITTED_OUTCOME',
  'action',o.action,'event_kind',o.event_kind,'request_id',o.request_id,'operation_id',o.id,
  'consumption_event_id',o.id,'journal_id',e.journal_id,'cohort_id',o.cohort_id,'source_sale_id',o.source_sale_id,
  'target_sale_id',o.target_sale_id,'cash_account_id',o.cash_account_id,'restores_event_id',o.restores_event_id,
  'amount',cp7_credit.cent_text(o.amount),'physical_at',cp7_credit.refund_physical_text(o.physical_at),
  'economic_date',o.economic_date,'transaction_date',o.transaction_date,'available_credit',p_capacity->'current_balance',
  'invoice_versions',(select jsonb_object_agg(key,value->'row_version')from jsonb_each(p_profiles)))
 from cp7_credit.consumer_operations_v1 o join cp7_credit.consumption_events e on e.id=o.id where o.id=p_operation
$$;

create function cp7_credit.consumer_completed_operation_v1(p_actor uuid,p_request uuid,p_response jsonb)returns uuid
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;c cp7_credit.consumer_completions_v1;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where actor=p_actor and request_id=p_request;
 select *into strict c from cp7_credit.consumer_completions_v1 where operation_id=o.id;
 if c.response is distinct from p_response or(p_response->>'operation_id',p_response->>'request_id')is distinct from
  (o.id::text,o.request_id::text)then raise exception 'CP7_CREDIT_CONSUMER_EXACT_COMPLETED_RECEIPT_REQUIRED';end if;
 return o.id;
end $$;

-- Historical facts stay valid after later lawful operations. This verifies the
-- old immutable completion against its own before/after snapshots and exact
-- journal/event, then separately checks current authoritative source/target
-- finances. It never forces today's status/version to equal an old receipt.
create function cp7_credit.assert_consumer_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;c cp7_credit.consumer_completions_v1;q cp7_credit.consumer_requests_v1;
 e cp7_credit.consumption_events;manifest jsonb;expected jsonb;profiles jsonb;profile jsonb;before_profile jsonb;native jsonb;
 sale text;net numeric;paid numeric;incoming numeric;issued numeric;effective numeric;after_version bigint;vectors jsonb;capacity jsonb;
begin
 perform cp7_credit.assert_consumer_operation_input_v1(p_operation);
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 select *into strict c from cp7_credit.consumer_completions_v1 where operation_id=o.id;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=o.actor and request_id=o.request_id;
 select *into strict e from cp7_credit.consumption_events where id=o.id;
 manifest:=cp7_credit.consumer_actual_manifest_v1(o.id);
 profiles:=c.final_profiles->'invoices';
 expected:=cp7_credit.consumer_outcome_v1(o.id,profiles,c.final_profiles->'source_capacity');
 if(q.action,q.payload->>'quote_sha256',cp7_credit.pg_jsonb_sha256(q.payload),q.expected_versions,q.response)
   is distinct from(o.action,o.quote_sha256,o.payload_sha256,o.projection->'expected_versions',expected)
  or c.response is distinct from expected
  or(c.consumption_event_id,c.journal_id,c.materialization_id,c.journal_lines_sha256_pg)is distinct from
   (e.id,e.journal_id,o.id,e.lines_sha256_pg)
  or c.actual_manifest is distinct from manifest or c.actual_manifest_sha256<>cp7_credit.pg_jsonb_sha256(manifest)
  or c.final_native is distinct from o.before_native
  or o.quote_sha256<>cp7_credit.consumer_quote_binding_v1(q.payload,o.locked_sources,o.projection)
  or cp7_credit.consumer_verify_posted_journal_v1(o.id,e.journal_id)<>e.lines_sha256_pg then
  raise exception 'CP7_CREDIT_CONSUMER_HISTORICAL_COMPLETION_CHANGED';end if;
 if (select jsonb_agg(key order by key)from jsonb_object_keys(profiles)key)is distinct from o.source_graph->'sale_ids'then
  raise exception 'CP7_CREDIT_CONSUMER_FINAL_INVOICE_SET_CHANGED';end if;
 for sale in select value from jsonb_array_elements_text(o.source_graph->'sale_ids')order by value loop
  profile:=profiles->sale;before_profile:=o.locked_sources#>array['sources',sale,'profile'];
  native:=o.locked_sources#>array['sources',sale,'native'];
  select coalesce(sum((v->>'line_total')::numeric),0)into net from jsonb_array_elements(native->'items')v;
  net:=net-(select coalesce(sum((v->>'refund_amount')::numeric),0)from jsonb_array_elements(native->'return_items')v
   where exists(select 1 from jsonb_array_elements(native->'returns')r where r->>'id'=v->>'return_id'and r->>'status'='POSTED'));
  select coalesce(sum((v->>'amount')::numeric),0)into paid from jsonb_array_elements(native->'payments')v where v->>'status'='POSTED';
  issued:=(before_profile->>'I')::numeric;incoming:=(before_profile->>'U')::numeric;
  if sale=o.target_sale_id::text then incoming:=incoming+o.amount;end if;
  effective:=paid+incoming-issued;
  after_version:=(o.projection#>>array['expected_versions',sale])::bigint
   +case when sale in(o.source_current_leaf_id::text,o.target_current_leaf_id::text)then 1 else 0 end;
  if profile->>'sale_id'<>sale or(profile->>'row_version')::bigint is distinct from after_version
   or(profile->>'net')::numeric is distinct from net or(profile->>'P')::numeric is distinct from paid
   or(profile->>'U')::numeric is distinct from incoming or(profile->>'I')::numeric is distinct from issued
   or(profile->>'E')::numeric is distinct from effective or(profile->>'AR')::numeric is distinct from net-effective
   or profile->>'status'is distinct from(case when effective=net then'PAID'when effective>0 then'PARTIAL_PAID'else'POSTED'end)
   or net<0 or effective<0 or effective>net then raise exception 'CP7_CREDIT_CONSUMER_HISTORICAL_FINANCIAL_EFFECT_CHANGED';end if;
  perform cp7_credit.assert_financial_materialization_provenance(profile->'materialized');
  -- Current validation follows all retained signed events and every joint cut.
  perform cp7_credit.consumer_invoice_profile_v1(sale::uuid);
 end loop;
 if c.final_profiles#>>'{source_capacity,source_prefixes_nonnegative}'is distinct from'true'
  or(c.final_profiles#>>'{source_capacity,current_balance}')::numeric is distinct from(o.projection#>>'{source_capacity_after,current_balance}')::numeric
  or(c.final_profiles#>>'{source_capacity,minimum_available}')::numeric is distinct from(o.projection#>>'{source_capacity_after,minimum_available}')::numeric then
  raise exception 'CP7_CREDIT_CONSUMER_HISTORICAL_CAPACITY_CHANGED';end if;
 if o.cash_coa_account_id is not null then
  if(c.final_profiles->>'cash_balance_after')::numeric is distinct from(o.projection->>'cash_balance_before')::numeric-o.amount then
   raise exception 'CP7_CREDIT_CONSUMER_HISTORICAL_CASH_EFFECT_CHANGED';end if;
 elsif c.final_profiles->>'cash_balance_after'is not null then raise exception 'CP7_CREDIT_CONSUMER_UNEXPECTED_CASH_EFFECT';end if;
 vectors:=cp7_credit.consumer_source_vectors_v1(o.cohort_id);
 capacity:=ow04_pure_kernel.credit_capacity_v1(vectors->'recognition',vectors->'consumptions',o.economic_date::text,o.transaction_date::text);
 if capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb then
  raise exception 'CP7_CREDIT_CONSUMER_CURRENT_HISTORICAL_JOINT_CAPACITY_UNFUNDED';end if;
 -- Leak checks are transaction facts, with no live-actor permission dependency.
 if exists(select 1 from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.consumer_posting_scope_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_CONSUMER_TEMPORARY_SCOPE_NOT_CLEARED';end if;
end $$;

create function cp7_credit.enforce_consumer_closed_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare fact jsonb:=to_jsonb(new);queued_actor uuid;queued_request uuid;
begin
 if tg_table_schema<>'cp7_credit'or tg_op not in('INSERT','UPDATE')
  or tg_when<>'AFTER'or tg_level<>'ROW'or tg_table_name not in
   ('consumer_requests_v1','consumer_operations_v1','consumer_completions_v1',
    'consumer_execution_context','consumer_posting_scope_v1','payment_consumer_headers_v1')then
  raise exception 'CP7_CREDIT_CONSUMER_VALIDATION_QUEUE_CHANGED';end if;
 if tg_table_name in('consumer_completions_v1','payment_consumer_headers_v1')then
  select o.actor,o.request_id into strict queued_actor,queued_request
   from cp7_credit.consumer_operations_v1 o where o.id=(fact->>'operation_id')::uuid;
 else
  queued_actor:=(fact->>'actor')::uuid;queued_request:=(fact->>'request_id')::uuid;
 end if;
 if queued_actor is null or queued_request is null then
  raise exception 'CP7_CREDIT_CONSUMER_VALIDATION_QUEUE_CHANGED';end if;
 insert into cp7_credit.consumer_validation_queue_v1(backend_pid,transaction_id,actor,request_id)
  values(pg_backend_pid(),txid_current(),queued_actor,queued_request)
  on conflict(backend_pid,transaction_id,actor,request_id)do nothing;
 return null;
end $$;

create function cp7_credit.drain_consumer_closed_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare pending cp7_credit.consumer_validation_queue_v1;operation uuid;removed bigint;
begin
 if tg_table_schema<>'cp7_credit'or tg_table_name<>'consumer_validation_queue_v1'
  or tg_op<>'INSERT'or tg_when<>'AFTER'or tg_level<>'ROW'then
  raise exception 'CP7_CREDIT_CONSUMER_VALIDATION_QUEUE_CHANGED';end if;
 select *into pending from cp7_credit.consumer_validation_queue_v1 q
  where q.queue_id=new.queue_id for update;
 if not found or to_jsonb(pending)is distinct from to_jsonb(new)
  or pending.backend_pid is distinct from pg_backend_pid()
  or pending.transaction_id is distinct from txid_current()then
  raise exception 'CP7_CREDIT_CONSUMER_VALIDATION_QUEUE_CHANGED';end if;
 select o.id into strict operation from cp7_credit.consumer_operations_v1 o
  where o.actor=pending.actor and o.request_id=pending.request_id;
 -- The unchanged complete historical/current proof always runs. Coalescing
 -- pending events never substitutes a hash, flag or earlier successful result.
 perform cp7_credit.assert_consumer_closed_v1(operation);
 delete from cp7_credit.consumer_validation_queue_v1 q where q.queue_id=pending.queue_id;
 get diagnostics removed=row_count;
 if removed<>1 then raise exception 'CP7_CREDIT_CONSUMER_VALIDATION_QUEUE_CHANGED';end if;
 return null;
end $$;

do $deferred$declare name text;begin
 foreach name in array array['consumer_requests_v1','consumer_operations_v1','consumer_completions_v1',
  'consumer_execution_context','consumer_posting_scope_v1']loop
  execute format('create trigger consumer_closed after insert or update on cp7_credit.%I for each row execute function cp7_credit.enforce_consumer_closed_v1()',name);
 end loop;
end $deferred$;
create constraint trigger consumer_closed after insert on cp7_credit.consumer_validation_queue_v1
 deferrable initially deferred for each row execute function cp7_credit.drain_consumer_closed_v1();

do $private$declare sig text;begin
 foreach sig in array array['consumer_outcome_v1(uuid,jsonb,jsonb)','consumer_completed_operation_v1(uuid,uuid,jsonb)',
 'assert_consumer_closed_v1(uuid)','enforce_consumer_closed_v1()','drain_consumer_closed_v1()']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
