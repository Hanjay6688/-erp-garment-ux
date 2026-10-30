-- LOCAL PGLITE ONLY: Auth, opening/payroll calculation, calendar and HPP
-- dependencies below are explicit doubles, not qualified Native or real Auth.
create role anon;create role authenticated;create role service_role;
create schema erp;create schema auth;create schema extensions;create schema local_s03;
create schema cp7_hpp_close;
create schema cp7_payroll;
create table cp7_payroll.settlement_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 payroll_id uuid not null,action text not null,primary key(backend_pid,transaction_id));
create table cp7_payroll.settlement_requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,
 expected_version text not null,response jsonb,primary key(actor,request_id));
-- Exact E05 column names used only for an administrative context/metadata
-- control of the first generic Native cash inverse. This is not E05 runtime.
create schema cp7_installment;
create table cp7_installment.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,native_payment_id uuid,
 primary key(backend_pid,transaction_id));
create table cp7_installment.payments(id uuid primary key,payroll_id uuid not null,amount numeric(20,2)not null,payment_date date not null,
 cash_account_id uuid not null,cash_coa_id uuid not null,journal_id uuid not null unique,reversal_journal_id uuid unique,
 created_by uuid not null,request_id uuid not null,created_at timestamptz not null default statement_timestamp());
create sequence erp.audit_logs_id_seq;
create table local_s03.identity(actor uuid primary key,role_code text not null,active boolean not null default true,
 can_view boolean not null default true,can_manage boolean not null default true,row_version bigint not null default 1);
create table local_s03.hpp_calls(kind text,po_id uuid,book_date date);
create table local_s03.controls(fail_hpp boolean not null default false);
insert into local_s03.controls values(false);
create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('local_s03.actor',true),'')::uuid$$;
create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role','authenticated','sub',auth.uid())$$;
create function erp.current_app_user_id()returns uuid language sql stable as $$select actor from local_s03.identity where actor=auth.uid()and active$$;
create function erp.get_my_access_v1()returns jsonb language sql stable as $$select jsonb_build_object('allowed',active,
 'profile',jsonb_build_object('role_code',role_code,'row_version',row_version::text))from local_s03.identity where actor=auth.uid()$$;
create function erp.has_permission(p text)returns boolean language sql stable as $$select active and case p when'finance.hpp.view'then can_view when'finance.hpp.manage'then can_manage else false end from local_s03.identity where actor=auth.uid()$$;
create function erp.require_internal()returns void language plpgsql as $$begin if current_user<>'postgres'then raise exception 'LOCAL_INTERNAL_ROLE';end if;end$$;
create function erp.require_owner_admin()returns void language plpgsql as $$begin
 if not exists(select 1 from local_s03.identity where actor=auth.uid()and active and role_code in('OWNER','ADMIN'))then raise exception 'LOCAL_OWNER_ADMIN';end if;end$$;
create function extensions.digest(p bytea,alg text)returns bytea language plpgsql immutable as $$begin
 if alg<>'sha256'then raise exception 'LOCAL_ONLY_SHA256';end if;return sha256(p);end$$;
create function erp.bb_business_today_v1()returns date language sql stable as $$select(statement_timestamp()at time zone'Asia/Jakarta')::date$$;
-- Table-dependent account/calendar doubles are appended by local.test.ts after
-- the retained P00 column-model tables have been created.
