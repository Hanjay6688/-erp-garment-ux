-- Minimal disposable PostgreSQL baseline for CP3 candidate tests.
-- This is test scaffolding only. It is never applied to ERP Enteng or canonical.

\set ON_ERROR_STOP on

create schema if not exists auth;
create schema if not exists extensions;
create schema if not exists erp;

create extension if not exists pgcrypto with schema extensions;

do $roles$
begin
  if not exists (select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname='service_role') then create role service_role nologin bypassrls; end if;
end;
$roles$;

create table erp.app_users (
  id uuid primary key default gen_random_uuid(),
  display_name text,
  role text not null default 'OWNER',
  is_active boolean not null default true
);

create table erp.contractors (
  id uuid primary key default gen_random_uuid(),
  contractor_code varchar(30) not null unique,
  contractor_name varchar(120) not null,
  contractor_type varchar(30) not null default 'MANDOR',
  attendance_required boolean not null default true,
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table erp.production_orders (
  id uuid primary key default gen_random_uuid(),
  po_number varchar(60) not null unique,
  contractor_id uuid references erp.contractors(id),
  status varchar(30) not null default 'IN_PROGRESS'
);

create table erp.cutting_groups (
  id uuid primary key default gen_random_uuid(),
  po_id uuid not null references erp.production_orders(id),
  total_pcs integer not null check (total_pcs > 0)
);

create or replace view erp.v_cutting_group_totals as
select id as cutting_group_id, total_pcs::bigint as total_pcs
from erp.cutting_groups;

create table erp.work_components (
  id uuid primary key default gen_random_uuid(),
  component_name text not null,
  component_category text not null default 'SEWING'
);

create table erp.po_work_component_snapshots (
  id uuid primary key default gen_random_uuid(),
  po_id uuid not null references erp.production_orders(id),
  work_component_id uuid not null references erp.work_components(id),
  rate_per_pcs_snapshot numeric(18,2) not null default 0
);

create table erp.work_completion_events (
  id uuid primary key default gen_random_uuid(),
  completion_number varchar(60) not null unique,
  po_id uuid not null references erp.production_orders(id),
  contractor_id uuid not null references erp.contractors(id),
  cutting_group_id uuid references erp.cutting_groups(id),
  physical_at timestamptz not null,
  status varchar(20) not null default 'DRAFT',
  notes text,
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table erp.work_completion_lines (
  id uuid primary key default gen_random_uuid(),
  completion_id uuid not null references erp.work_completion_events(id),
  po_component_snapshot_id uuid not null references erp.po_work_component_snapshots(id),
  work_component_id uuid not null references erp.work_components(id),
  qty_completed integer not null,
  qty_payable integer not null,
  rate_snapshot numeric(18,2) not null,
  amount_payable numeric(20,2) generated always as (qty_payable * rate_snapshot) stored,
  notes text
);

create table erp.payroll_settlements (
  id uuid primary key default gen_random_uuid(),
  payroll_number varchar(60) not null unique,
  contractor_id uuid not null references erp.contractors(id),
  period_start date not null,
  period_end date not null,
  status varchar(20) not null default 'DRAFT',
  attendance_total numeric(20,2) not null default 0,
  row_version bigint not null default 1
);

create table erp.payroll_attendance_items (
  id uuid primary key default gen_random_uuid(),
  payroll_id uuid not null references erp.payroll_settlements(id),
  worker_id uuid not null,
  attendance_record_id uuid not null,
  paid_fraction_snapshot numeric(6,4) not null,
  daily_rate_snapshot numeric(18,2) not null,
  amount numeric(20,2) generated always as (paid_fraction_snapshot * daily_rate_snapshot) stored
);

create table erp.chart_accounts (
  id uuid primary key default gen_random_uuid(),
  account_code text not null unique,
  account_name text not null
);

create table erp.accounting_account_mappings (
  mapping_key text primary key,
  account_id uuid not null references erp.chart_accounts(id)
);

insert into erp.chart_accounts(account_code,account_name) values
  ('1300','Work in process'),
  ('5200','Labor cost')
on conflict do nothing;

insert into erp.accounting_account_mappings(mapping_key,account_id)
select 'WIP',id from erp.chart_accounts where account_code='1300'
on conflict do nothing;
insert into erp.accounting_account_mappings(mapping_key,account_id)
select 'LABOR_COST',id from erp.chart_accounts where account_code='5200'
on conflict do nothing;

create table erp.journal_entries (
  id uuid primary key default gen_random_uuid(),
  journal_number varchar(70) not null unique,
  transaction_date date not null,
  posting_at timestamptz not null default now(),
  source_type varchar(50) not null,
  source_id uuid,
  description text not null,
  status varchar(20) not null default 'POSTED',
  reversal_of_id uuid references erp.journal_entries(id),
  created_by uuid references erp.app_users(id),
  economic_date date not null,
  period_shifted boolean generated always as (economic_date <> transaction_date) stored
);

create unique index uq_test_journal_one_posted_source
  on erp.journal_entries(source_type,source_id)
  where status='POSTED' and source_id is not null;

create table erp.journal_lines (
  id uuid primary key default gen_random_uuid(),
  journal_entry_id uuid not null references erp.journal_entries(id),
  account_id uuid not null references erp.chart_accounts(id),
  description text,
  debit numeric(20,2) not null default 0,
  credit numeric(20,2) not null default 0,
  customer_id uuid,
  vendor_id uuid,
  contractor_id uuid references erp.contractors(id),
  po_id uuid references erp.production_orders(id),
  product_id uuid
);

create table erp.idempotency_requests (
  id uuid primary key default gen_random_uuid(),
  actor_key text not null,
  operation_name text not null,
  client_request_id uuid not null,
  request_hash text not null,
  status text not null default 'IN_PROGRESS',
  response_payload jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(actor_key,operation_name,client_request_id)
);

create table erp.audit_logs (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid,
  action text not null,
  old_data jsonb,
  new_data jsonb,
  changed_by uuid,
  change_reason text,
  created_at timestamptz not null default now()
);

create table erp.schema_migrations (
  version text primary key,
  description text,
  installed_at timestamptz not null default now()
);

create or replace function erp.current_app_user_id()
returns uuid language sql stable as $$
  select nullif(current_setting('app.test_user_id',true),'')::uuid
$$;

create or replace function erp.require_internal()
returns void language plpgsql stable as $$ begin return; end $$;

create or replace function erp.require_owner_admin()
returns void language plpgsql stable as $$ begin return; end $$;

create or replace function erp.account_id(p_mapping_key text)
returns uuid language sql stable as $$
  select account_id from erp.accounting_account_mappings where mapping_key=p_mapping_key
$$;

create or replace function erp._idempotency_actor_key()
returns text language sql stable as $$
  select coalesce(erp.current_app_user_id()::text,'database:'||session_user)
$$;

create or replace function erp._request_hash(p_payload jsonb)
returns text language sql immutable set search_path=erp,public,extensions,pg_temp as $$
  select encode(extensions.digest(convert_to(coalesce(p_payload,'{}'::jsonb)::text,'UTF8'),'sha256'),'hex')
$$;

create or replace function erp._idempotency_begin(
  p_operation_name text,p_client_request_id uuid,p_request_hash text
)
returns jsonb language plpgsql security definer set search_path=erp,public,pg_temp as $$
declare v_actor text:=erp._idempotency_actor_key();v_row erp.idempotency_requests%rowtype;
begin
  if p_client_request_id is null then raise exception 'client_request_id is required'; end if;
  insert into erp.idempotency_requests(actor_key,operation_name,client_request_id,request_hash)
  values(v_actor,p_operation_name,p_client_request_id,p_request_hash)
  on conflict do nothing;
  select * into v_row from erp.idempotency_requests
  where actor_key=v_actor and operation_name=p_operation_name and client_request_id=p_client_request_id
  for update;
  if v_row.request_hash<>p_request_hash then raise exception 'client_request_id was already used with a different payload'; end if;
  if v_row.status='COMPLETED' then return v_row.response_payload; end if;
  return null;
end $$;

create or replace function erp._idempotency_complete(
  p_operation_name text,p_client_request_id uuid,p_response jsonb
)
returns jsonb language plpgsql security definer set search_path=erp,public,pg_temp as $$
declare v_actor text:=erp._idempotency_actor_key();
begin
  update erp.idempotency_requests set status='COMPLETED',response_payload=p_response,updated_at=now()
  where actor_key=v_actor and operation_name=p_operation_name and client_request_id=p_client_request_id and status='IN_PROGRESS';
  if not found then raise exception 'Idempotency request is missing or already completed'; end if;
  return p_response;
end $$;

create or replace function erp.post_journal(
  p_source_type text,p_source_id uuid,p_transaction_date date,p_description text,p_lines jsonb
)
returns uuid language plpgsql security definer set search_path=erp,public,pg_temp as $$
declare v_entry uuid:=gen_random_uuid();v_debit numeric;v_credit numeric;r jsonb;v_account uuid;
begin
  select coalesce(sum((x->>'debit')::numeric),0),coalesce(sum((x->>'credit')::numeric),0)
  into v_debit,v_credit from jsonb_array_elements(p_lines)x;
  if jsonb_typeof(p_lines)<>'array' or jsonb_array_length(p_lines)<2 or round(v_debit,2)<>round(v_credit,2) or v_debit<=0 then
    raise exception 'Journal is not balanced';
  end if;
  insert into erp.journal_entries(id,journal_number,transaction_date,economic_date,source_type,source_id,description,status)
  values(v_entry,'JRN-'||substr(v_entry::text,1,12),p_transaction_date,p_transaction_date,p_source_type,p_source_id,p_description,'POSTED');
  for r in select value from jsonb_array_elements(p_lines)
  loop
    v_account:=case when r?'account_id' then (r->>'account_id')::uuid else erp.account_id(r->>'mapping_key') end;
    insert into erp.journal_lines(journal_entry_id,account_id,description,debit,credit,contractor_id,po_id)
    values(v_entry,v_account,r->>'description',coalesce((r->>'debit')::numeric,0),coalesce((r->>'credit')::numeric,0),nullif(r->>'contractor_id','')::uuid,nullif(r->>'po_id','')::uuid);
  end loop;
  return v_entry;
end $$;

create or replace function erp.reverse_journal(p_journal_entry_id uuid,p_reason text)
returns uuid language plpgsql security definer set search_path=erp,public,pg_temp as $$
declare v_old erp.journal_entries%rowtype;v_lines jsonb;v_new uuid;
begin
  select * into v_old from erp.journal_entries where id=p_journal_entry_id for update;
  if v_old.id is null or v_old.status<>'POSTED' then raise exception 'Only posted journal can be reversed'; end if;
  select jsonb_agg(jsonb_build_object('account_id',account_id,'debit',credit,'credit',debit,'description','Reversal: '||coalesce(description,''),'contractor_id',contractor_id,'po_id',po_id) order by id)
  into v_lines from erp.journal_lines where journal_entry_id=v_old.id;
  v_new:=erp.post_journal('JOURNAL_REVERSAL',v_old.id,current_date,'Reversal: '||v_old.description||' | '||p_reason,v_lines);
  update erp.journal_entries set status='REVERSED' where id=v_old.id;
  update erp.journal_entries set reversal_of_id=v_old.id where id=v_new;
  return v_new;
end $$;
