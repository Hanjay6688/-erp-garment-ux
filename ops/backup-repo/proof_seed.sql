-- Synthetic ERP-like objects for the off-site backup proof (owner D13-8d). Runs on a disposable Supabase Postgres
-- container only; never on Enteng or any hosted database. Values are synthetic.
create role erp_proof_app nologin;
create schema erp_proof;
grant usage on schema erp_proof to anon, authenticated, service_role, erp_proof_app;
create type erp_proof.doc_status as enum ('DRAFT', 'POSTED', 'VOID');
create table erp_proof.docs(
  id bigint generated always as identity primary key,
  no text not null unique,
  status varchar(10) not null default 'DRAFT' check (status in ('DRAFT', 'POSTED', 'VOID')),
  amount numeric(14, 2) not null check (amount >= 0),
  created_at timestamptz not null default now());
alter table erp_proof.docs enable row level security;
create policy docs_read on erp_proof.docs for select to authenticated using (status <> 'VOID');
grant select on erp_proof.docs to authenticated;
grant select, insert, update on erp_proof.docs to service_role;
create function erp_proof.post_doc(p_id bigint) returns erp_proof.doc_status
  language plpgsql security definer set search_path = pg_catalog, erp_proof
  as $$ begin update erp_proof.docs set status = 'POSTED' where id = p_id; return 'POSTED'; end $$;
revoke execute on function erp_proof.post_doc(bigint) from public, anon;
grant execute on function erp_proof.post_doc(bigint) to authenticated;
create view erp_proof.open_docs with (security_invoker = true) as
  select id, no, amount from erp_proof.docs where status = 'DRAFT';
grant select on erp_proof.open_docs to authenticated;
alter default privileges in schema erp_proof grant select on tables to erp_proof_app;
insert into erp_proof.docs(no, status, amount)
  select 'D-' || g, case when g % 3 = 0 then 'POSTED' else 'DRAFT' end, g * 1.25 from generate_series(1, 2000) g;
