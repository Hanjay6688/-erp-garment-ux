-- Derived FG evaluations only; no posted stock, production or ledger writes.
create table cp7_reorder_caller.evaluations(
 target_key text primary key,root_id uuid not null unique,
 threshold_hash text not null check(threshold_hash~'^[0-9a-f]{64}$'),
 row jsonb not null check(jsonb_typeof(row)='object'),captured_at timestamptz not null,
 check(row->>'target_key'=target_key and row->>'root_id'=root_id::text)
);
create table cp7_reorder_caller.use_marks(id boolean primary key check(id),used_at timestamptz not null);
alter table cp7_reorder_caller.evaluations owner to cp7_capture;
alter table cp7_reorder_caller.use_marks owner to cp7_capture;
alter table cp7_reorder_caller.evaluations enable row level security;
alter table cp7_reorder_caller.use_marks enable row level security;
create policy reorder_evaluation_no_access on cp7_reorder_caller.evaluations for all to public using(false)with check(false);
create policy reorder_caller_use_no_access on cp7_reorder_caller.use_marks for all to public using(false)with check(false);
revoke all on cp7_reorder_caller.evaluations,cp7_reorder_caller.use_marks from public,anon,authenticated,service_role,cp7_alert;
create trigger reorder_caller_use_immutable before update or delete on cp7_reorder_caller.use_marks
 for each row execute function cp7_reorder_reader.immutable_use();

-- The latest full FG read supplies the stock clock. A semantic row need not
-- be rewritten merely because another minute passed with identical values.
create function cp7_reorder_caller.wire_row(r jsonb,p_at timestamptz)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_set(r,'{projection,stock_checked_at}',to_jsonb(cp7_planning.utc(p_at)))
$$;
alter function cp7_reorder_caller.wire_row(jsonb,timestamp with time zone)owner to cp7_capture;
revoke all on function cp7_reorder_caller.wire_row(jsonb,timestamp with time zone)from public,anon,authenticated,service_role,cp7_alert;
