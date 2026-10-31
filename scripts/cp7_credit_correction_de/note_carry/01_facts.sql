-- E1 candidate is a separate stage. D1 sources and its 13-case interface stay exact.
create schema cp7_credit_note_carry_de authorization postgres;
revoke all on schema cp7_credit_note_carry_de from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
create table cp7_credit_note_carry_de.work_v1(
 operation_id uuid primary key,backend_pid int not null,transaction_id bigint not null,actor uuid not null,request_id uuid not null,
 source_sale_id uuid not null,replacement_sale_id uuid,revision_id uuid not null,expected_version text not null,payload jsonb not null,
 authority jsonb not null,period jsonb not null,basis jsonb not null,review jsonb not null,graph jsonb not null,
 before_sources jsonb not null,before_materialized jsonb not null,phase text not null check(phase in('PREPARED','REVERSED','MATERIALIZED')),
 actual_source jsonb,actual_proof jsonb,unique(backend_pid,transaction_id),unique(actor,request_id)
);
create table cp7_credit_note_carry_de.operations_v1(
 operation_id uuid primary key,actor uuid not null,request_id uuid not null,source_sale_id uuid not null unique,
 replacement_sale_id uuid not null unique,revision_id uuid not null unique,payload jsonb not null,expected_version text not null,
 proof jsonb not null,response jsonb not null,recorded_at timestamptz not null default statement_timestamp(),unique(actor,request_id)
);
-- Assignment is separate from the immutable money event. Neither the original
-- APPLY nor its GL/source/customer/account/date is updated or reverse/recreated.
create table cp7_credit_note_carry_de.assignments_v1(
 operation_id uuid not null,event_id uuid not null,event_kind text not null check(event_kind='APPLY'),
 historical_target_id uuid not null,root_sale_id uuid not null,replacement_sale_id uuid not null,
 event_snapshot jsonb not null,journal_snapshot jsonb not null,event_sha256 text not null,journal_sha256 text not null,
 primary key(operation_id,event_id),unique(event_id,replacement_sale_id)
);
create function cp7_credit_note_carry_de.immutable_v1()returns trigger
language plpgsql security invoker set search_path=''as $$begin raise exception 'CP7_CREDIT_NOTE_CARRY_HISTORY_IMMUTABLE';end$$;
do $private$declare t text;begin
 foreach t in array array['work_v1','operations_v1','assignments_v1']loop
  execute 'alter table cp7_credit_note_carry_de.'||t||' owner to postgres';
  execute 'alter table cp7_credit_note_carry_de.'||t||' enable row level security';
  execute 'create policy deny_direct on cp7_credit_note_carry_de.'||t||' for all using(false)with check(false)';
  execute 'revoke all on cp7_credit_note_carry_de.'||t||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
  if t<>'work_v1'then
   execute 'create trigger immutable_row before update or delete on cp7_credit_note_carry_de.'||t||' for each row execute function cp7_credit_note_carry_de.immutable_v1()';
   execute 'create trigger immutable_truncate before truncate on cp7_credit_note_carry_de.'||t||' for each statement execute function cp7_credit_note_carry_de.immutable_v1()';
  end if;
 end loop;
end $private$;
create function cp7_credit_note_carry_de.has_root_v1(p_root uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_credit_note_carry_de.operations_v1 where source_sale_id=p_root)
 or exists(select 1 from cp7_credit_note_carry_de.work_v1 where source_sale_id=p_root and phase='MATERIALIZED')
$$;
create function cp7_credit_note_carry_de.proof_v1(p_root uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce((select proof from cp7_credit_note_carry_de.operations_v1 where source_sale_id=p_root),
  (select to_jsonb(w)from cp7_credit_note_carry_de.work_v1 w where source_sale_id=p_root and phase='MATERIALIZED'))
$$;
