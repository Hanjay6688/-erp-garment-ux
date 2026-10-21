-- Source-only until the complete owning installer admits this entire stage.
do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

-- This context only coordinates two already-authorized Native actions. It is
-- never an erp.require_internal capability and is never a financial witness.
create table cp7_credit.payment_source_context_v1(
 operation_id uuid primary key,backend_pid integer not null,transaction_id bigint not null,
 actor uuid not null,request_id uuid not null,unique(backend_pid,transaction_id),unique(actor,request_id),
 phase text not null check(phase in('PREPARED','INVERSE_ENTERED','INVERSE_EFFECT','INVERSE_COMPLETE',
  'REPLACEMENT_READY','REPLACEMENT_ENTERED','RECONCILING','RECONCILED','REPLACEMENT_COMPLETE')),
 inverse_native jsonb,inverse_final jsonb,replacement_before jsonb,replacement_draft jsonb,
 replacement_id uuid,time_neutral_id uuid,effective_inverse_id uuid,
 projected_input jsonb not null,projected_result jsonb not null
);

-- Actual snapshots captured at the real Native callbacks, not synthetic
-- source rows. Financial materialization and completed parent request are
-- independently mandatory at deferred closure. There are no new Native FKs.
create table cp7_credit.payment_source_legs_v1(
 operation_id uuid primary key,inverse_native jsonb not null,inverse_final jsonb not null,
 replacement_before jsonb not null,replacement_draft jsonb not null,replacement_id uuid not null unique,
 time_neutral_id uuid,effective_inverse_id uuid,
 check((time_neutral_id is null)=(effective_inverse_id is null)),
 recorded_at timestamptz not null default statement_timestamp()
);

alter table cp7_credit.source_operation_work_v1 drop constraint source_operation_work_v1_action_check;
alter table cp7_credit.source_operation_work_v1 add constraint source_operation_work_v1_action_check
 check(action in('RETURN_REVERSE','PAYMENT_REVERSE','PAYMENT_CORRECT'));
alter table cp7_credit.source_operation_materializations_v1 drop constraint source_operation_materializations_v1_action_check;
alter table cp7_credit.source_operation_materializations_v1 add constraint source_operation_materializations_v1_action_check
 check(action in('RETURN_REVERSE','PAYMENT_REVERSE','PAYMENT_CORRECT'));

do $protect$declare name text;begin
 foreach name in array array['payment_source_context_v1','payment_source_legs_v1']loop
  execute 'alter table cp7_credit.'||name||' owner to postgres';
  execute 'alter table cp7_credit.'||name||' enable row level security';
  execute 'create policy deny_direct on cp7_credit.'||name||' for all to public using(false)with check(false)';
  execute 'revoke all on cp7_credit.'||name||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $protect$;
create trigger immutable_row before update or delete on cp7_credit.payment_source_legs_v1
 for each row execute function cp7_credit.immutable_fact();
create trigger immutable_truncate before truncate on cp7_credit.payment_source_legs_v1
 for each statement execute function cp7_credit.immutable_fact();
