-- WIP owning-source protocol. Compose all reconciliation files and exact
-- Native/CP7 hooks atomically; this fragment cannot activate itself.
do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

-- Mutable operation capability, never a financial or completion witness.
create table cp7_credit.source_operation_work_v1(
 operation_id uuid primary key,operation_ordinal bigint not null check(operation_ordinal>0),predecessor_operation_id uuid,
 backend_pid integer not null,transaction_id bigint not null,
 actor uuid not null,request_id uuid not null,action text not null check(action in('RETURN_REVERSE','PAYMENT_REVERSE')),
 sale_id uuid not null,source_id uuid not null,expected_version text not null,payload jsonb not null,
 payload_sha256 text not null,authority_snapshot jsonb not null,
 phase text not null check(phase in('PREPARED','ENTERED','RECONCILING','RECONCILED','NATIVE_COMPLETE')),
 before_source jsonb not null,before_ordinal_input jsonb not null,before_ordinal_result jsonb not null,
 before_financial_profile jsonb not null,account_facts jsonb not null,period_snapshot jsonb not null,
 actual_source jsonb,actual_source_proof jsonb,actual_ordinal_input jsonb,actual_ordinal_result jsonb,
 plan_manifest jsonb,active_plan_id uuid,financial_marker_id uuid,actual_manifest_sha256 text,
 unique(backend_pid,transaction_id),unique(actor,request_id),unique(sale_id,operation_ordinal),
 check((operation_ordinal=1)=(predecessor_operation_id is null)),
 check(payload_sha256~'^[0-9a-f]{64}$'),
 check(jsonb_typeof(payload)='object'and jsonb_typeof(authority_snapshot)='object'),
 check(phase in('PREPARED','ENTERED')or(actual_source is not null and actual_source_proof is not null
  and actual_ordinal_input is not null and actual_ordinal_result is not null and plan_manifest is not null)),
 check(phase not in('RECONCILED','NATIVE_COMPLETE')or actual_manifest_sha256 is not null)
);

-- Complete immutable actual source and all-own-plans binding. This may precede
-- Native's final invoice status, like initial_return_materializations. It does
-- not claim a completed outer request. Deferred closure proves that separately.
create table cp7_credit.source_operation_materializations_v1(
 operation_id uuid primary key,operation_ordinal bigint not null check(operation_ordinal>0),predecessor_operation_id uuid,
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,request_id uuid not null,action text not null,
 sale_id uuid not null references erp.sales_headers(id),source_id uuid not null,
 expected_version text not null,payload jsonb not null,payload_sha256 text not null,
 authority_snapshot jsonb not null,before_source jsonb not null,before_ordinal_input jsonb not null,
 before_ordinal_result jsonb not null,before_financial_profile jsonb not null,account_facts jsonb not null,
 period_snapshot jsonb not null,actual_source jsonb not null,actual_source_proof jsonb not null,
 actual_ordinal_input jsonb not null,actual_ordinal_result jsonb not null,plan_manifest jsonb not null,
 financial_marker_id uuid unique references cp7_credit.financial_materializations(id),
 actual_objects jsonb not null,actual_manifest_sha256 text not null,
 recorded_at timestamptz not null default statement_timestamp(),unique(actor,request_id),unique(sale_id,operation_ordinal),
 check((operation_ordinal=1)=(predecessor_operation_id is null)),
 foreign key(predecessor_operation_id)references cp7_credit.source_operation_materializations_v1(operation_id),
 check(action in('RETURN_REVERSE','PAYMENT_REVERSE')),
 check(payload_sha256~'^[0-9a-f]{64}$'and actual_manifest_sha256~'^[0-9a-f]{64}$')
);
alter table cp7_credit.source_operation_work_v1 add foreign key(predecessor_operation_id)
 references cp7_credit.source_operation_materializations_v1(operation_id);

-- Every new plan in one source operation is excluded together on poster
-- reentry. The sidecar is immutable; completed historical plans never qualify.
create table cp7_credit.source_operation_plans_v1(
 plan_id uuid primary key references cp7_credit.recognition_plans(id),
 operation_id uuid not null references cp7_credit.source_operation_materializations_v1(operation_id)deferrable initially deferred,
 family_id uuid not null references cp7_credit.return_families(id),
 family_ordinal bigint not null check(family_ordinal>0),
 full_family_result jsonb not null,canonical_plan jsonb not null,
 before_retained_events jsonb not null,before_consumptions jsonb not null,
 source_binding_sha256 text not null check(source_binding_sha256~'^[0-9a-f]{64}$'),
 unique(operation_id,family_id)
);

create table cp7_credit.source_operation_completions_v1(
 operation_id uuid primary key references cp7_credit.source_operation_materializations_v1(operation_id),
 final_native_source jsonb not null,final_profile jsonb not null,final_manifest_sha256 text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check(final_manifest_sha256~'^[0-9a-f]{64}$')
);

-- Full actual journal payload is sealed immediately after every new part is
-- posted, so another poster reentry cannot adopt changed earlier own output.
create table cp7_credit.source_operation_part_seals_v1(
 part_id uuid primary key references cp7_credit.component_parts(id),
 operation_id uuid not null references cp7_credit.source_operation_materializations_v1(operation_id)deferrable initially deferred,
 plan_id uuid not null references cp7_credit.recognition_plans(id),
 component_id uuid not null references cp7_credit.recognition_components(id),
 journal_id uuid not null unique references erp.journal_entries(id),
 journal_link jsonb not null,actual_journal jsonb not null,actual_journal_sha256 text not null,
 source_binding_sha256 text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check(actual_journal_sha256~'^[0-9a-f]{64}$'and source_binding_sha256~'^[0-9a-f]{64}$')
);

do $protect_source_operations$declare t text;begin
 foreach t in array array['source_operation_work_v1','source_operation_materializations_v1','source_operation_plans_v1','source_operation_completions_v1','source_operation_part_seals_v1']loop
  execute 'alter table cp7_credit.'||t||' owner to postgres';
  execute 'alter table cp7_credit.'||t||' enable row level security';
  execute 'create policy deny_direct on cp7_credit.'||t||' for all to public using(false)with check(false)';
  execute 'revoke all on cp7_credit.'||t||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
  if t<>'source_operation_work_v1'then
   execute 'create trigger immutable_row before update or delete on cp7_credit.'||t||' for each row execute function cp7_credit.immutable_fact()';
   execute 'create trigger immutable_truncate before truncate on cp7_credit.'||t||' for each statement execute function cp7_credit.immutable_fact()';
  end if;
 end loop;
end $protect_source_operations$;
