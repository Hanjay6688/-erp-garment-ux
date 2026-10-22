-- Installed only by the complete source-derived owning composition.
do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

-- An outgoing consumer changes the Native review epoch even when source
-- P/I/U/status do not change. Retain its actual whole before/after headers.
-- Both actual Native touch and the poster use statement_timestamp(); their
-- approved installed definitions are checked before this stage. No Native relation/FK/trigger
-- or public capability is added. Each fact still needs real owning closure.
create table cp7_credit.payment_consumer_headers_v1(
 operation_id uuid primary key,sale_id uuid not null,
 before_row_version bigint not null,before_header jsonb not null,after_header jsonb not null,
 backend_pid integer not null,transaction_id bigint not null,statement_started_at timestamptz not null,
 unique(sale_id,before_row_version),
 check(before_header->>'id'=sale_id::text and after_header->>'id'=sale_id::text),
 check((before_header->>'row_version')::bigint=before_row_version),
 check((after_header->>'row_version')::bigint=before_row_version+1)
);
alter table cp7_credit.payment_consumer_headers_v1 owner to postgres;
alter table cp7_credit.payment_consumer_headers_v1 enable row level security;
create policy deny_direct on cp7_credit.payment_consumer_headers_v1 for all to public using(false)with check(false);
revoke all on cp7_credit.payment_consumer_headers_v1 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
create trigger immutable_row before update or delete on cp7_credit.payment_consumer_headers_v1
 for each row execute function cp7_credit.immutable_fact();
create trigger immutable_truncate before truncate on cp7_credit.payment_consumer_headers_v1
 for each statement execute function cp7_credit.immutable_fact();

create function cp7_credit.payment_consumer_header_proof_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h cp7_credit.payment_consumer_headers_v1;o cp7_credit.consumer_operations_v1;
 q cp7_credit.consumer_requests_v1;c cp7_credit.consumer_completions_v1;
 ctx cp7_credit.consumer_execution_context;manifest jsonb;profile jsonb;
begin
 select *into strict h from cp7_credit.payment_consumer_headers_v1 where operation_id=p_operation;
 select *into strict o from cp7_credit.consumer_operations_v1 where id=h.operation_id;
 select *into strict q from cp7_credit.consumer_requests_v1 where actor=o.actor and request_id=o.request_id;
 perform cp7_credit.assert_consumer_operation_input_v1(o.id);
 manifest:=cp7_credit.consumer_actual_manifest_v1(o.id);
 if o.source_sale_id<>h.sale_id or o.source_root_sale_id<>h.sale_id or o.source_current_leaf_id<>h.sale_id
  or o.target_sale_id=h.sale_id
  or h.before_header is distinct from o.locked_sources#>array['sources',h.sale_id::text,'native','sale']
  or h.before_row_version is distinct from(o.projection#>>array['expected_versions',h.sale_id::text])::bigint
  or h.after_header-array['row_version','updated_at']is distinct from h.before_header-array['row_version','updated_at']
  or(h.after_header->>'row_version')::bigint<>h.before_row_version+1
  or(h.after_header->>'updated_at')::timestamptz is distinct from h.statement_started_at then
  raise exception 'CP7_CREDIT_PAYMENT_CONSUMER_HEADER_FACT_CHANGED'using detail=jsonb_build_object(
   'source_identity_matches',(o.source_sale_id,o.source_root_sale_id,o.source_current_leaf_id)=(h.sale_id,h.sale_id,h.sale_id),
   'before_header_matches',h.before_header=o.locked_sources#>array['sources',h.sale_id::text,'native','sale'],
   'review_epoch_matches',h.before_row_version=(o.projection#>>array['expected_versions',h.sale_id::text])::bigint,
   'unchanged_header_fields',h.after_header-array['row_version','updated_at']=h.before_header-array['row_version','updated_at'],
   'actual_clock',h.after_header->'updated_at','captured_statement_clock',h.statement_started_at)::text;end if;
 select *into c from cp7_credit.consumer_completions_v1 where operation_id=o.id;
 if c.operation_id is null or q.response is null then
  -- A MATERIALIZED event is actual, but is not a completed operation. Its
  -- only temporary reader is this real pending outer operation, actor/PID/tx.
  select *into strict ctx from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
   and transaction_id=txid_current()and actor=auth.uid()and operation_id=o.id;
  if ctx.phase not in('MATERIALIZED','COMPLETE')or q.response is not null
   or(h.backend_pid,h.transaction_id,h.statement_started_at)is distinct from
     (pg_backend_pid(),txid_current(),statement_timestamp())
   or not cp7_credit.consumer_internal_allowed_v1()then
   raise exception 'CP7_CREDIT_PAYMENT_CONSUMER_HEADER_PENDING_SCOPE_REQUIRED';end if;
 end if;
 if c.operation_id is not null then
  profile:=c.final_profiles#>array['invoices',h.sale_id::text];
  if c.actual_manifest is distinct from manifest or c.actual_manifest_sha256<>cp7_credit.pg_jsonb_sha256(manifest)
   or c.final_native is distinct from o.before_native
   or(c.consumption_event_id,c.journal_id,c.materialization_id,c.journal_lines_sha256_pg)is distinct from
     (o.id,(manifest->>'journal_id')::uuid,o.id,cp7_credit.consumer_verify_posted_journal_v1(o.id,(manifest->>'journal_id')::uuid))
   or c.response is distinct from cp7_credit.consumer_outcome_v1(o.id,c.final_profiles->'invoices',c.final_profiles->'source_capacity')
   or q.response is not null and q.response is distinct from c.response
   or(profile->>'row_version')::bigint is distinct from(h.after_header->>'row_version')::bigint
   or profile->>'status'is distinct from h.after_header->>'status'
   or(profile->>'U')::numeric is distinct from 0::numeric then
   raise exception 'CP7_CREDIT_PAYMENT_CONSUMER_HEADER_COMPLETION_CHANGED';end if;
 end if;
 return to_jsonb(h);
end $$;

create function cp7_credit.payment_consumer_header_capture_v1(p_operation uuid,p_sale uuid,p_before jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;ctx cp7_credit.consumer_execution_context;actual jsonb;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 -- Scope is outgoing use of an actually completed owning correction. Other
 -- source/target and original18 consumer operations retain exact old behavior.
 if p_sale<>o.source_current_leaf_id or not exists(
  select 1 from cp7_credit.source_operation_materializations_v1 m
   join cp7_credit.source_operation_completions_v1 c on c.operation_id=m.operation_id
   where m.sale_id=p_sale and m.action='PAYMENT_CORRECT')then return;end if;
 select *into strict ctx from cp7_credit.consumer_execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and operation_id=o.id;
 if ctx.phase<>'MATERIALIZED'or not cp7_credit.consumer_internal_allowed_v1()then
  raise exception 'CP7_CREDIT_PAYMENT_CONSUMER_HEADER_CAPTURE_SCOPE_REQUIRED';end if;
 select to_jsonb(h)into strict actual from erp.sales_headers h where id=p_sale;
 insert into cp7_credit.payment_consumer_headers_v1 values(o.id,p_sale,(p_before->>'row_version')::bigint,
  p_before,actual,pg_backend_pid(),txid_current(),statement_timestamp());
 perform cp7_credit.payment_consumer_header_proof_v1(o.id);
end $$;

create function cp7_credit.payment_consumer_source_continues_v1(p_sale uuid,p_before jsonb,p_after jsonb)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare header jsonb:=p_before->'sale';last_header jsonb:=p_after->'sale';h cp7_credit.payment_consumer_headers_v1;
begin
 if p_before is not null and p_before=p_after then return true;end if;
 if p_before is null or p_after is null or p_before-'sale'is distinct from p_after-'sale'
  or header->>'id'is distinct from p_sale::text or last_header->>'id'is distinct from p_sale::text
  or(header->>'row_version')::bigint is null or(last_header->>'row_version')::bigint is null
  or(header->>'row_version')::bigint>=(last_header->>'row_version')::bigint then return false;end if;
 while(header->>'row_version')::bigint<(last_header->>'row_version')::bigint loop
  select *into h from cp7_credit.payment_consumer_headers_v1
   where sale_id=p_sale and before_row_version=(header->>'row_version')::bigint;
  if h.operation_id is null or h.before_header is distinct from header then return false;end if;
  perform cp7_credit.payment_consumer_header_proof_v1(h.operation_id);
  header:=h.after_header;
 end loop;
 return header=last_header;
end $$;

create function cp7_credit.enforce_payment_consumer_header_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_credit.payment_consumer_header_proof_v1(new.operation_id);
 return null;
end $$;
-- Every actual header insert also schedules the same full consumer proof.
-- Keep the header-specific deferred proof; avoid duplicating full closure for
-- each header when the operation is already pending. A later insert following
-- SET CONSTRAINTS still schedules a fresh complete validation.
create trigger payment_consumer_header_queue after insert on cp7_credit.payment_consumer_headers_v1
 for each row execute function cp7_credit.enforce_consumer_closed_v1();
create constraint trigger payment_consumer_header_closed after insert on cp7_credit.payment_consumer_headers_v1
 deferrable initially deferred for each row execute function cp7_credit.enforce_payment_consumer_header_v1();
