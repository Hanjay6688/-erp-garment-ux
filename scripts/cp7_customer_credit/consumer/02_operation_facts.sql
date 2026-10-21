-- Pending complete owning consumer composition. No public entry point, Native
-- admission or financial writer is installed by this fragment. Keep the barrier
-- and leave SQL_FILES unchanged until the whole coordinator and closure exist.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

-- The outer writer owns only request/temporary context rows. A UUID identifies
-- one exact action/payload/version envelope; replay does not create a new event.
create table cp7_credit.consumer_requests_v1(
 actor uuid not null,request_id uuid not null,
 action text not null check(action in('APPLY','REFUND','UNDO')),
 payload jsonb not null check(jsonb_typeof(payload)='object'),
 expected_versions jsonb not null check(jsonb_typeof(expected_versions)='object'),
 response jsonb check(response is null or jsonb_typeof(response)='object'),
 primary key(actor,request_id)
);
create table cp7_credit.consumer_execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,action text not null check(action in('APPLY','REFUND','UNDO')),
 phase text not null check(phase in('CLAIMED','LOCKED','POSTING','MATERIALIZED','COMPLETE')),
 operation_id uuid unique,
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 quote_sha256 text not null check(quote_sha256~'^[0-9a-f]{64}$'),
 authority_snapshot jsonb not null check(jsonb_typeof(authority_snapshot)='object'),
 primary key(backend_pid,transaction_id),
 foreign key(actor,request_id)references cp7_credit.consumer_requests_v1(actor,request_id),
 check((phase='CLAIMED')=(operation_id is null))
);

-- Immutable operation-derived source. Neither a matching row nor a hash is a
-- live capability: the owning callbacks must prove the pending outer request,
-- PID/transaction, current permissions, locked source set and projection again.
-- Cash account and target AR are actual source snapshots, never new defaults.
create table cp7_credit.consumer_operations_v1(
 id uuid primary key,
 actor uuid not null,actor_app_user_id uuid not null,request_id uuid not null,
 action text not null check(action in('APPLY','REFUND','UNDO')),
 event_kind text not null check(event_kind in('APPLY','REFUND')),
 cohort_id uuid not null references cp7_credit.cohorts(id),
 customer_id uuid not null references erp.customers(id),
 source_sale_id uuid not null references erp.sales_headers(id),
 source_root_sale_id uuid not null references erp.sales_headers(id),
 source_current_leaf_id uuid not null references erp.sales_headers(id),
 target_sale_id uuid references erp.sales_headers(id),
 target_root_sale_id uuid references erp.sales_headers(id),
 target_current_leaf_id uuid references erp.sales_headers(id),
 cash_account_id uuid references erp.cash_accounts(id),
 credit_account_id uuid not null references erp.chart_accounts(id),
 target_ar_account_id uuid references erp.chart_accounts(id),
 cash_coa_account_id uuid references erp.chart_accounts(id),
 amount cp7_credit.cent_amount not null check(amount<>0),
 restores_event_id uuid unique references cp7_credit.consumption_events(id),
 physical_at timestamptz not null check(isfinite(physical_at)),
 economic_date date not null check(isfinite(economic_date)),
 transaction_date date not null check(isfinite(transaction_date)),
 reason text not null check(reason=btrim(reason)and length(reason)between 5 and 1000),
 reference text check(length(reference)<=100),
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 quote_sha256 text not null check(quote_sha256~'^[0-9a-f]{64}$'),
 source_graph jsonb not null check(jsonb_typeof(source_graph)='object'),
 source_graph_sha256 text not null check(source_graph_sha256~'^[0-9a-f]{64}$'),
 locked_sources jsonb not null check(jsonb_typeof(locked_sources)='object'),
 locked_sources_sha256 text not null check(locked_sources_sha256~'^[0-9a-f]{64}$'),
 projection jsonb not null check(jsonb_typeof(projection)='object'),
 projection_sha256 text not null check(projection_sha256~'^[0-9a-f]{64}$'),
 period_snapshot jsonb not null check(jsonb_typeof(period_snapshot)='object'),
 book_manifest jsonb not null check(jsonb_typeof(book_manifest)='object'),
 authority_snapshot jsonb not null check(jsonb_typeof(authority_snapshot)='object'),
 credit_account_snapshot jsonb not null check(jsonb_typeof(credit_account_snapshot)='object'),
 target_ar_snapshot jsonb check(target_ar_snapshot is null or jsonb_typeof(target_ar_snapshot)='object'),
 cash_account_snapshot jsonb check(cash_account_snapshot is null or jsonb_typeof(cash_account_snapshot)='object'),
 before_native jsonb not null check(jsonb_typeof(before_native)='object'),
 recorded_at timestamptz not null default statement_timestamp(),
 unique(actor,request_id),
 foreign key(actor,request_id)references cp7_credit.consumer_requests_v1(actor,request_id),
 check((action='UNDO')=(amount<0)),
 check((action='UNDO')=(restores_event_id is not null)),
 check(action<>'APPLY'or event_kind='APPLY'),
 check(action<>'REFUND'or event_kind='REFUND'),
 check((event_kind='APPLY')=(target_sale_id is not null)),
 check((event_kind='APPLY')=(target_root_sale_id is not null)),
 check((event_kind='APPLY')=(target_current_leaf_id is not null)),
 check((event_kind='APPLY')=(target_ar_account_id is not null)),
 check((event_kind='APPLY')=(target_ar_snapshot is not null)),
 check((event_kind='REFUND')=(cash_account_id is not null)),
 check((event_kind='REFUND')=(cash_coa_account_id is not null)),
 check((event_kind='REFUND')=(cash_account_snapshot is not null)),
 check(target_ar_account_id is distinct from credit_account_id),
 check(cash_coa_account_id is distinct from credit_account_id),
 check(economic_date=(physical_at at time zone'Asia/Jakarta')::date),
 check(transaction_date>=economic_date)
);
alter table cp7_credit.consumer_execution_context add foreign key(operation_id)
 references cp7_credit.consumer_operations_v1(id)deferrable initially deferred;

-- A one-call scope binds the exact actual Native journal request. It does not
-- extend the old RETURN/COMPONENT scopes or create a session/GUC capability.
create table cp7_credit.consumer_posting_scope_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,operation_id uuid not null references cp7_credit.consumer_operations_v1(id),
 source_type text not null check(source_type in('CP7_CUSTOMER_CREDIT_APPLY',
  'CP7_CUSTOMER_CREDIT_REFUND','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')),
 source_id uuid not null,economic_date date not null,transaction_date date not null,
 lines_sha256_pg text not null check(lines_sha256_pg~'^[0-9a-f]{64}$'),
 primary key(backend_pid,transaction_id),check(source_id=operation_id),
 check(transaction_date>=economic_date)
);

-- Completion is an actual fact, separate from the operation's planned inputs.
-- The complete coordinator must also seal every affected recognition plan and
-- marker, verify final Native status/stock/HPP and clear all temporary scopes.
create table cp7_credit.consumer_completions_v1(
 operation_id uuid primary key references cp7_credit.consumer_operations_v1(id),
 consumption_event_id uuid not null unique references cp7_credit.consumption_events(id),
 journal_id uuid not null unique references erp.journal_entries(id),
 materialization_id uuid not null unique references cp7_credit.financial_materializations(id),
 journal_lines_sha256_pg text not null check(journal_lines_sha256_pg~'^[0-9a-f]{64}$'),
 actual_manifest jsonb not null check(jsonb_typeof(actual_manifest)='object'),
 actual_manifest_sha256 text not null check(actual_manifest_sha256~'^[0-9a-f]{64}$'),
 final_native jsonb not null check(jsonb_typeof(final_native)='object'),
 final_profiles jsonb not null check(jsonb_typeof(final_profiles)='object'),
 response jsonb not null check(jsonb_typeof(response)='object'),
 recorded_at timestamptz not null default statement_timestamp(),
 check(consumption_event_id=operation_id),check(materialization_id=operation_id)
);

do $private$declare name text;begin
 foreach name in array array['consumer_requests_v1','consumer_execution_context',
  'consumer_operations_v1','consumer_posting_scope_v1','consumer_completions_v1']loop
  execute format('alter table cp7_credit.%I owner to postgres',name);
  execute format('alter table cp7_credit.%I enable row level security',name);
  execute format('create policy no_direct_access on cp7_credit.%I for all to public using(false)with check(false)',name);
  execute format('revoke all on cp7_credit.%I from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write',name);
 end loop;
 foreach name in array array['consumer_requests_v1','consumer_execution_context']loop
  execute format('alter table cp7_credit.%I owner to cp7_credit_write',name);
  execute format('grant select on cp7_credit.%I to postgres',name);
 end loop;
 foreach name in array array['consumer_operations_v1','consumer_completions_v1']loop
  execute format('create trigger immutable_row before update or delete on cp7_credit.%I for each row execute function cp7_credit.immutable_fact()',name);
  execute format('create trigger immutable_truncate before truncate on cp7_credit.%I for each statement execute function cp7_credit.immutable_fact()',name);
 end loop;
end $private$;

-- The postgres sealer advances this outer-owned context but cannot mint an
-- outer request. The name ends in _context so the unchanged Native one-probe
-- guard verifier can census its exact typed branch with its existing grammar.
grant update(phase,operation_id)on cp7_credit.consumer_execution_context to postgres;
grant trigger on cp7_credit.consumer_requests_v1,cp7_credit.consumer_execution_context to postgres;

-- No success-placeholder trigger is supplied. Before installation, the owning
-- bundle must implement and attach complete context-free deferred closure for
-- all five tables, integrate new materialization/consumption dispatch, and add
-- every temporary scope to the final leak census. A table is not proof of use.
