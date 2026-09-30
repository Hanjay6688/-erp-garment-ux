-- Integrator-owned native producer. All facts are captured before a kernel
-- runs. The request may select dates/identity basis, never its trusted scope.
create schema cp7_planning authorization cp7_capture;
revoke all on schema cp7_planning from public,anon,authenticated,service_role;
grant select on erp.sales_returns,erp.sales_return_items,erp.sale_stock_allocations,
 erp.journal_entries to cp7_capture;

create table cp7_planning.history_runs(
 id uuid primary key default gen_random_uuid(),
 actor uuid not null,request_id uuid not null,query jsonb not null,
 captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,
 unique(actor,request_id)
);
alter table cp7_planning.history_runs owner to cp7_capture;
alter table cp7_planning.history_runs enable row level security;
create policy cp7_planning_no_operational_access on cp7_planning.history_runs
 for all to public using(false)with check(false);
revoke all on cp7_planning.history_runs from public,anon,authenticated,service_role;
create trigger cp7_planning_history_immutable before update or delete on cp7_planning.history_runs
 for each row execute function cp7_private.immutable_run();

create function cp7_planning.utc(t timestamptz)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC' as $$
 select to_char(t at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$$;

create function cp7_planning.history_query(q jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='Asia/Jakarta' as $$
declare lo date;hi date;basis text;
begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');basis:=q->>'group_mode';
 if hi<lo or hi-lo>3660 or hi>=(clock_timestamp()at time zone 'Asia/Jakarta')::date
  or basis is null or basis not in('AS_SOLD','RESTATED')then raise exception 'CP7_PLANNING_HISTORY_QUERY';end if;
 return jsonb_build_object('from_date',lo::text,'through_date',hi::text,'group_mode',basis);
end $$;
