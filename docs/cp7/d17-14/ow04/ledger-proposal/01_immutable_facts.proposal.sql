-- OW04 INTERNAL PROPOSAL, OUTSIDE PRODUCT. Not an installer or a Native proof.
-- Keep this barrier until ALL interfaces in README.md have owning implementations.
do $not_an_installer$ begin
 raise exception 'OW04_PROPOSAL_NOT_INSTALLABLE_WITHOUT_COMPLETE_FEATURE';
end $not_an_installer$;

-- No new role, global account mapping, expiry policy, migration batch or public RPC.
-- Names are proposed private integration names. All money is exact stored cents.
create schema cp7_credit authorization postgres;
revoke all on schema cp7_credit from public,anon,authenticated,service_role;

create function cp7_credit.pg_jsonb_sha256(p jsonb) returns text
language sql immutable security invoker set search_path='' as $$
 select encode(pg_catalog.sha256(convert_to(p::text,'UTF8')),'hex')
$$;
-- Same PG jsonb::text codec as the pure kernel, with a DIFFERENT payload:
-- normalized support/component manifests, not an unnormalized source vector.

-- Unbounded numeric preserves the supplied value BEFORE the cent check. A
-- numeric(20,2) column would silently round 0.001 before its CHECK can reject it.
create domain cp7_credit.cent_amount as numeric
 check(value is null or(value::text not in('NaN','Infinity','-Infinity')
  and value*100=trunc(value*100)));
create function cp7_credit.cent_text(p cp7_credit.cent_amount)returns text
language sql immutable strict security invoker set search_path=''as $$
 select(case when p<0 then'-'else''end)||trunc(abs(p))::text||'.'||
  lpad(trunc((abs(p)-trunc(abs(p)))*100)::text,2,'0')
$$;

-- Mechanical storage bound, NOT a business amount cap: captured Native
-- post_journal declares BOTH journal totals numeric(20,2) (20ac3968–3969).
create function cp7_credit.native_journal_cent_max()returns numeric
language sql immutable security invoker set search_path=''as $$
 select 999999999999999999.99::numeric
$$;

create function cp7_credit.immutable_fact() returns trigger
language plpgsql security invoker set search_path='' as $$
begin raise exception 'CP7_CREDIT_HISTORY_IMMUTABLE';end $$;

-- Register EVERY logical return family, including a genuinely empty initial
-- target. This needs no credit account or settlement choice. New ordinals are
-- serialized under FG; corrections/replays inherit the original family ordinal.
-- Backfill must prove a unique qualified source order or refuse; never invent
-- historical posting order from UUID/timestamp convenience.
create table cp7_credit.return_families(
 id uuid primary key,
 family_root_sale_id uuid not null references erp.sales_headers(id),
 family_ordinal bigint not null check(family_ordinal>0),
 first_return_id uuid not null unique references erp.sales_returns(id),
 assignment_kind text not null check(assignment_kind in('NEW_POST','QUALIFIED_BACKFILL')),
 assignment_proof jsonb not null check(jsonb_typeof(assignment_proof)='object'),
 source_sha256 text not null check(source_sha256~'^[0-9a-f]{64}$'),
 actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default statement_timestamp(),
 unique(family_root_sale_id,family_ordinal)
);
create table cp7_credit.return_family_members(
 family_id uuid not null references cp7_credit.return_families(id)deferrable initially deferred,
 return_id uuid primary key references erp.sales_returns(id),
 member_kind text not null check(member_kind in('ORIGINAL','RETURN_CORRECTION','NOTE_REPLAY')),
 source_journal_id uuid not null unique references erp.journal_entries(id),
 source_sha256 text not null check(source_sha256~'^[0-9a-f]{64}$'),
 actual_lineage_snapshot jsonb not null check(jsonb_typeof(actual_lineage_snapshot)='object'),
 actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default statement_timestamp(),
 unique(family_id,return_id)
);
alter table cp7_credit.return_families add foreign key(id,first_return_id)
 references cp7_credit.return_family_members(family_id,return_id)deferrable initially deferred;

create table cp7_credit.cohorts(
 id uuid primary key,
 family_id uuid not null unique references cp7_credit.return_families(id),
 source_sale_id uuid not null references erp.sales_headers(id),
 source_return_id uuid not null unique references erp.sales_returns(id),
 customer_id uuid not null references erp.customers(id),
 ar_account_id uuid not null references erp.chart_accounts(id),
 source_ar_snapshot jsonb not null check(jsonb_typeof(source_ar_snapshot)='object'),
 credit_account_id uuid not null references erp.chart_accounts(id),
 credit_account_snapshot jsonb not null check(jsonb_typeof(credit_account_snapshot)='object'),
 initial_mode text not null check(initial_mode in('CREDIT','REFUND')),
 -- K=0 does NOT mean no recognition effect. +200/-200 still needs this fact.
 initial_net_amount cp7_credit.cent_amount not null check(initial_net_amount>=0),
 initial_plan_id uuid not null unique,
 source_sale_journal_id uuid not null references erp.journal_entries(id),
 source_return_journal_id uuid not null references erp.journal_entries(id),
 source_sale_sha256 text not null check(source_sale_sha256~'^[0-9a-f]{64}$'),
 source_return_sha256 text not null check(source_return_sha256~'^[0-9a-f]{64}$'),
 actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default statement_timestamp(),
 foreign key(family_id,source_return_id)references cp7_credit.return_family_members(family_id,return_id)
);

create table cp7_credit.recognition_plans(
 id uuid primary key,
 cohort_id uuid not null references cp7_credit.cohorts(id) deferrable initially deferred,
 plan_kind text not null check(plan_kind in('INITIAL','ADJUSTMENT')),
 -- Names/authority of owning facades remain the integrator's exact contract.
 owning_action text not null,
 actor uuid not null,request_id uuid not null,request_ordinal integer not null check(request_ordinal>0),
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 review_sha256 text not null check(review_sha256~'^[0-9a-f]{64}$'),
 -- Scope is the actual Native correction family, not merely active leaf rows.
 family_root_sale_id uuid not null references erp.sales_headers(id),
 before_events jsonb not null check(jsonb_typeof(before_events)='array'),
 added_events jsonb not null check(jsonb_typeof(added_events)='array'),
 kernel_result jsonb not null check(jsonb_typeof(kernel_result)='object'),
 kernel_version text not null check(kernel_version='ow04-2d-difference-v1'),
 before_source_sha256 text not null check(before_source_sha256~'^[0-9a-f]{64}$'),
 after_source_sha256 text not null check(after_source_sha256~'^[0-9a-f]{64}$'),
 support_sha256_pg text not null check(support_sha256_pg~'^[0-9a-f]{64}$'),
 components_sha256_pg text not null check(components_sha256_pg~'^[0-9a-f]{64}$'),
 parts_sha256_pg text not null check(parts_sha256_pg~'^[0-9a-f]{64}$'),
 -- Adjustments may have a negative net. Never overwrite initial_net_amount.
 net_amount cp7_credit.cent_amount not null,
 has_recognition_effect boolean not null,
 expected_component_count integer not null check(expected_component_count>=0),
 expected_part_count bigint not null check(expected_part_count>=0),
 recorded_at timestamptz not null default statement_timestamp(),
 unique(actor,request_id,request_ordinal),
 check(has_recognition_effect=(expected_component_count>0)),
 check(plan_kind<>'INITIAL'or net_amount>=0)
);
alter table cp7_credit.cohorts add foreign key(initial_plan_id)
 references cp7_credit.recognition_plans(id) deferrable initially deferred;

-- Exact kernel input event protocol from the independent pure-kernel proposal:
-- {id,kind:'NET'|'FUNDING',amount,economic_date,transaction_date,source_sha256}.
-- NET positive = gross AR, NET negative = return; FUNDING positive pays AR.
-- Inverse/restatement events carry signed amounts. No credit issuance in FUNDING.
create table cp7_credit.plan_support_events(
 plan_id uuid not null references cp7_credit.recognition_plans(id),
 event_id text not null check(length(event_id)>0),
 phase text not null check(phase in('BEFORE','ADDED')),
 kind text not null check(kind in('NET','FUNDING')),
 amount cp7_credit.cent_amount not null,
 economic_date date not null,transaction_date date not null,
 source_sha256 text not null check(source_sha256~'^[0-9a-f]{64}$'),
 journal_id uuid not null references erp.journal_entries(id),
 -- Immutable-source sidecar includes actual lines, dimensions, posting clock,
-- Native posting/reversal facts and CP7 correction links. Mutable status alone
-- is not the financial hash: original POSTED->REVERSED is a lawful transition.
 source_fact_snapshot jsonb not null check(jsonb_typeof(source_fact_snapshot)='object'),
 primary key(plan_id,event_id),check(transaction_date>=economic_date)
);
create index credit_support_journal on cp7_credit.plan_support_events(journal_id,plan_id);

create table cp7_credit.recognition_components(
 id uuid primary key,
 plan_id uuid not null references cp7_credit.recognition_plans(id),
 ordinal integer not null check(ordinal>0),
 economic_date date not null,transaction_date date not null,
 amount cp7_credit.cent_amount not null check(amount<>0),
 previous_economic_date date,previous_transaction_date date,
 corners jsonb not null check(jsonb_typeof(corners)='object'
  and corners?&array['d_here','d_prev_economic','d_prev_transaction','d_prev_both']
  and corners-array['d_here','d_prev_economic','d_prev_transaction','d_prev_both']='{}'::jsonb),
 -- Exact six-field component emitted by the pure kernel. Full JSON equality
-- to a freshly rebuilt authoritative plan is required before posting.
 kernel_component jsonb not null check(jsonb_typeof(kernel_component)='object'),
 component_sha256_pg text not null check(component_sha256_pg~'^[0-9a-f]{64}$'),
 unique(plan_id,ordinal),unique(plan_id,economic_date,transaction_date),
 check(transaction_date>=economic_date),
 check(previous_economic_date is null or previous_economic_date<economic_date),
 check(previous_transaction_date is null or previous_transaction_date<transaction_date)
);
create index credit_component_plan on cp7_credit.recognition_components(plan_id,id);

-- Mechanical parts preserve each component's sign, exact date pair and sum.
-- They are not separate credit cohorts or cash movements. Parts are allocated
-- by the server's immutable manifest, never supplied as arbitrary browser money.
create table cp7_credit.component_parts(
 id uuid primary key,
 component_id uuid not null references cp7_credit.recognition_components(id),
 ordinal bigint not null check(ordinal>0),
 amount cp7_credit.cent_amount not null check(amount<>0
  and abs(amount)<=cp7_credit.native_journal_cent_max()),
 unique(component_id,ordinal)
);
create index credit_part_component on cp7_credit.component_parts(component_id,id);

create table cp7_credit.component_journals(
 part_id uuid primary key references cp7_credit.component_parts(id),
 journal_id uuid not null unique references erp.journal_entries(id),
 economic_date date not null,transaction_date date not null,
 lines_sha256_pg text not null check(lines_sha256_pg~'^[0-9a-f]{64}$'),
 recorded_at timestamptz not null default statement_timestamp()
);

-- Consumption is separate from recognition: refunds/applications never reduce I.
-- Positive consumes, negative restores exactly one earlier immutable event.
-- Capacity must include every later economic/book cutoff AND joint rectangle.
create table cp7_credit.consumption_events(
 id uuid primary key,
 cohort_id uuid not null references cp7_credit.cohorts(id),
 event_kind text not null check(event_kind in('APPLY','REFUND')),
 amount cp7_credit.cent_amount not null check(amount<>0),
 economic_date date not null,transaction_date date not null,
 target_sale_id uuid references erp.sales_headers(id),
 cash_account_id uuid references erp.cash_accounts(id),
 restores_event_id uuid unique references cp7_credit.consumption_events(id),
 journal_id uuid not null unique references erp.journal_entries(id),
 source_sha256 text not null check(source_sha256~'^[0-9a-f]{64}$'),
 lines_sha256_pg text not null check(lines_sha256_pg~'^[0-9a-f]{64}$'),
 actor uuid not null,request_id uuid not null,reason text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check((amount<0)=(restores_event_id is not null)),
 check((event_kind='APPLY')=(target_sale_id is not null)),
 check((event_kind='REFUND')=(cash_account_id is not null)),
 check(transaction_date>=economic_date)
);
create index credit_consumption_cohort on cp7_credit.consumption_events(cohort_id,economic_date,transaction_date,id);
create index credit_consumption_target on cp7_credit.consumption_events(target_sale_id,id)where target_sale_id is not null;

-- Every snapshot input is a dependency, including prior returns, their cohorts,
-- already-reversed funding and incoming credit; do not invent FIFO allocations.
create table cp7_credit.plan_dependencies(
 plan_id uuid not null references cp7_credit.recognition_plans(id),
 dependency_kind text not null check(dependency_kind in(
  'SALE','RETURN','RETURN_FAMILY','PAYMENT','PAYMENT_REVERSAL','RECOGNITION_PLAN','INCOMING_APPLICATION','CORRECTION')),
 dependency_id uuid not null,
 dependency_sha256 text not null check(dependency_sha256~'^[0-9a-f]{64}$'),
 primary key(plan_id,dependency_kind,dependency_id)
);
create index credit_reverse_dependency on cp7_credit.plan_dependencies(dependency_kind,dependency_id,plan_id);

-- Ephemeral server-only operation context, NEVER a session GUC capability.
-- assert_owner_context and rebuild_locked_plan must validate actual authority,
-- complete source ownership, current token, period row and source locks anew.
create table cp7_credit.execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 -- Ordinary empty-target RETURN has an owning context without a financial plan.
 -- COMPONENT admission requires this to equal the actual immutable plan UUID.
 request_id uuid not null,plan_id uuid,
 owning_action text not null,payload_sha256 text not null,review_sha256 text not null,
 authority_snapshot jsonb not null,
 primary key(backend_pid,transaction_id)
);
-- A one-call posting scope is minted only AFTER rebuilding the whole plan.
create table cp7_credit.posting_scope(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,post_kind text not null check(post_kind in('COMPONENT','RETURN')),
 component_id uuid,part_id uuid,plan_id uuid,source_sale_id uuid not null,source_return_id uuid not null,
 source_type text not null,source_id uuid not null,
 economic_date date not null,transaction_date date not null,
 lines_sha256_pg text not null,
 primary key(backend_pid,transaction_id),
 check((post_kind='COMPONENT')=(component_id is not null and part_id is not null and plan_id is not null)),
 check(transaction_date>=economic_date)
);

-- Append-only history, including TRUNCATE. No browser/service/helper mutation.
do $lock_history$ declare t text;begin
 foreach t in array array['return_families','return_family_members','cohorts','recognition_plans','plan_support_events',
  'recognition_components','component_parts','component_journals','consumption_events','plan_dependencies']loop
  execute format('alter table cp7_credit.%I enable row level security',t);
  execute format('create policy no_direct_access on cp7_credit.%I for all to public using(false)with check(false)',t);
  execute format('create trigger immutable_row before update or delete on cp7_credit.%I for each row execute function cp7_credit.immutable_fact()',t);
  execute format('create trigger immutable_truncate before truncate on cp7_credit.%I for each statement execute function cp7_credit.immutable_fact()',t);
 end loop;
end $lock_history$;
alter table cp7_credit.execution_context enable row level security;
alter table cp7_credit.posting_scope enable row level security;
revoke all on all tables in schema cp7_credit from public,anon,authenticated,service_role,
 cp7_capture,cp7_sales_read,cp7_sales_write;
revoke all on all functions in schema cp7_credit from public,anon,authenticated,service_role,
 cp7_capture,cp7_sales_read,cp7_sales_write;

-- Mandatory deferred closure trigger, supplied by complete owning integration:
--  * family order/membership is actual Native correction lineage; gross-before-
--    returns F=0 and each family's NET<=0 at EVERY joint prefix; inverse floors
--    respect BOTH source axes; qualified backfill never fabricates source order;
--  * initial_plan belongs to cohort, INITIAL sum=cohort.initial_net_amount;
--  * complete kernel/support arrays and exact expected_component_count;
--  * each component has its exact deterministic part manifest, each part has
--    exactly one immutable, correctly shaped journal link, sum(parts)=component;
--  * I/current and both dated GL/AR/liability profiles reconcile;
--  * no open execution_context/posting_scope for this transaction at commit;
--  * all consumption capacities/final cash checks passed, including corrections.
-- This file intentionally does NOT install a placeholder trigger that returns OK.
