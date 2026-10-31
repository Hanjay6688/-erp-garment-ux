create table cp7_credit_correction_de.work_v1(
 operation_id uuid primary key,operation_ordinal bigint not null check(operation_ordinal>0),predecessor_id uuid,backend_pid int not null,transaction_id bigint not null,actor uuid not null,request_id uuid not null,
 sale_id uuid not null,return_id uuid not null,replacement_id uuid,expected_version text not null,payload jsonb not null,
 authority jsonb not null,period jsonb not null,before_source jsonb not null,before_input jsonb not null,before_profile jsonb not null,
 review jsonb not null,phase text not null check(phase in('PREPARED','REVERSED','POSTING','POSTED','RECONCILING','MATERIALIZED')),
 actual_source jsonb,actual_input jsonb,actual_result jsonb,manifest jsonb,actual_objects jsonb,
 check((operation_ordinal=1)=(predecessor_id is null)),
 unique(backend_pid,transaction_id),unique(actor,request_id),unique(sale_id,operation_ordinal)
);
create table cp7_credit_correction_de.operations_v1(
 operation_id uuid primary key,operation_ordinal bigint not null check(operation_ordinal>0),predecessor_id uuid,actor uuid not null,request_id uuid not null,sale_id uuid not null,
 return_id uuid not null,replacement_id uuid not null,expected_version text not null,payload jsonb not null,
 proof jsonb not null,response jsonb not null,recorded_at timestamptz not null default statement_timestamp(),check((operation_ordinal=1)=(predecessor_id is null)),unique(actor,request_id),unique(sale_id,operation_ordinal)
);
create table cp7_credit_correction_de.plans_v1(plan_id uuid primary key,operation_id uuid not null,family_id uuid not null,
 canonical jsonb not null,request_ordinal int not null,unique(operation_id,family_id));
create table cp7_credit_correction_de.parts_v1(part_id uuid primary key,operation_id uuid not null,plan_id uuid not null,
 journal_id uuid not null unique,journal_link jsonb not null,journal_snapshot jsonb not null);
create table cp7_credit_correction_de.posting_v1(backend_pid int not null,transaction_id bigint not null,actor uuid not null,
 operation_id uuid not null,source_type text not null,source_id uuid not null,economic_date date not null,
 transaction_date date not null,lines_sha256 text not null,primary key(backend_pid,transaction_id));

create function cp7_credit_correction_de.immutable_v1()returns trigger
language plpgsql security invoker set search_path=''as $$begin raise exception 'CP7_CREDIT_DE_HISTORY_IMMUTABLE';end$$;
do $private$declare t text;begin
 foreach t in array array['work_v1','operations_v1','plans_v1','parts_v1','posting_v1']loop
  execute 'alter table cp7_credit_correction_de.'||t||' owner to postgres';
  execute 'alter table cp7_credit_correction_de.'||t||' enable row level security';
  execute 'create policy deny_direct on cp7_credit_correction_de.'||t||' for all using(false)with check(false)';
  execute 'revoke all on cp7_credit_correction_de.'||t||' from public,anon,authenticated,service_role';
  if t in('operations_v1','plans_v1','parts_v1')then
   execute 'create trigger immutable_row before update or delete on cp7_credit_correction_de.'||t||' for each row execute function cp7_credit_correction_de.immutable_v1()';
   execute 'create trigger immutable_truncate before truncate on cp7_credit_correction_de.'||t||' for each statement execute function cp7_credit_correction_de.immutable_v1()';
  end if;
 end loop;
end $private$;

create function cp7_credit_correction_de.participates_v1(p_return uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_credit.return_family_members m join cp7_credit.cohorts c on c.family_id=m.family_id where m.return_id=p_return)
$$;

create function cp7_credit_correction_de.active_v1()returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_credit_correction_de.work_v1 w where w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()and w.actor=auth.uid())
$$;

create function cp7_credit_correction_de.assert_work_v1()returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare w cp7_credit_correction_de.work_v1;q cp7_sales_return_correction.requests;
begin
 select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict q from cp7_sales_return_correction.requests where actor=w.actor and request_id=w.request_id;
 if q.payload is distinct from w.payload or q.expected_version is distinct from w.expected_version or q.response is not null
  or cp7_sales_return_correction.access_now()is distinct from w.authority
  or(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period
  or not exists(select 1 from cp7_sales.command_context c where c.backend_pid=w.backend_pid and c.transaction_id=w.transaction_id
   and c.actor=w.actor and c.sale_id=w.sale_id and c.action in('RETURN','RETURN_REVERSE'))then
  raise exception 'CP7_CREDIT_DE_OWN_PENDING_CONTEXT_REQUIRED';end if;
end $$;
