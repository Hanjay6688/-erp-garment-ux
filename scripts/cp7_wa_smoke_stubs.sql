-- WA stack smoke (scripts/cp7_wa_stack_smoke.py): the few ERP objects alerts.sql reads, as small stand-ins on a bare
-- Supabase stack. Not product SQL; never installed anywhere but the disposable CI stack. The real readers are tested
-- in the full Native suite.
create role cp7_capture nologin;
create role cp7_reminder nologin;
create role cp7_payable_read nologin;
create schema erp;
create table erp.test_users(sub uuid primary key,role_code text not null,active boolean not null default true,perms text[] not null);
create table erp.locations(id uuid primary key default gen_random_uuid(),location_code text not null,location_name text not null,
 location_type text not null,is_active boolean not null default true);
create table erp.materials(id uuid primary key default gen_random_uuid(),material_sku text not null,material_name text not null,
 material_type text not null,unit_code text not null,is_active boolean not null default true);
create table erp.fabric_master_profiles(material_id uuid primary key references erp.materials(id),minimum_stock_qty numeric not null);
create table erp.material_stock_movements(id uuid primary key default gen_random_uuid(),material_id uuid not null references erp.materials(id),
 roll_id uuid,location_id uuid not null references erp.locations(id),qty_signed numeric not null,physical_at timestamptz not null);
create table erp.manual_reminders(id uuid primary key default gen_random_uuid(),owner_user_id uuid not null,title text not null,
 note text not null default '',due_at timestamptz not null,priority text not null default 'NORMAL',status text not null default 'OPEN');
create function erp.get_my_access_v1()returns jsonb language plpgsql stable security definer set search_path=''as $f$
declare u erp.test_users;begin
 select*into u from erp.test_users where sub=auth.uid();
 if not found then return jsonb_build_object('allowed',false,'reason','APP_USER_NOT_FOUND');end if;
 if not u.active then return jsonb_build_object('allowed',false,'reason','APP_USER_INACTIVE');end if;
 return jsonb_build_object('allowed',true,'profile',jsonb_build_object('id',u.sub,'role_code',u.role_code),'permissions',to_jsonb(u.perms));
end$f$;
create function erp.has_permission(p text)returns boolean language sql stable security definer set search_path=''as $f$
 select coalesce((select p=any(u.perms)and u.active from erp.test_users u where u.sub=auth.uid()),false)$f$;
revoke all on function erp.get_my_access_v1(),erp.has_permission(text)from public;
create table public.wa_smoke_ar(doc jsonb not null);
create table public.wa_smoke_ap(r jsonb not null);
revoke all on public.wa_smoke_ar,public.wa_smoke_ap from public,anon,authenticated,service_role;
create function public.erp_cp7_get_sales_v1(p jsonb)returns jsonb language sql stable security definer set search_path=''as $f$
 select jsonb_build_object('contract_version','cp7.sales-workspace.v1','page',jsonb_build_object(
  'rows',coalesce((select jsonb_agg(doc)from public.wa_smoke_ar),'[]'),'total',(select count(*)from public.wa_smoke_ar)::text))$f$;
revoke all on function public.erp_cp7_get_sales_v1(jsonb)from public,anon,authenticated,service_role;
create schema cp7_reminder_native;
create function cp7_reminder_native.receivable_source()returns jsonb language plpgsql stable security invoker set search_path=''as $f$
declare native jsonb;at date:=(statement_timestamp()at time zone'Asia/Jakarta')::date;c jsonb;
begin
 if not erp.has_permission('finance.ar.view')then raise exception using errcode='42501',message='CP7_REMINDER_AR_ACCESS_DENIED';end if;
 native:=public.erp_cp7_get_sales_v1('{}');
 select coalesce(jsonb_agg(jsonb_build_object('key','AR:'||(x->>'id'),'source_id',x->>'id','state',
  case when(x->'financial'->>'open_balance')::numeric=0 then'ZERO_BALANCE'when(x->>'due_date')::date<at then'OVERDUE'
   when(x->>'due_date')::date=at then'DUE_TODAY'else'NOT_DUE_YET'end)),'[]')into c from jsonb_array_elements(native->'page'->'rows')x;
 return jsonb_build_object('as_of',at,'pages',jsonb_build_array(native),'conditions',c);
end$f$;
create function cp7_reminder_native.payable_source()returns jsonb language plpgsql stable security definer set search_path=''as $f$
begin
 if not erp.has_permission('finance.ap.view')then raise exception using errcode='42501',message='CP7_REMINDER_AP_ACCESS_DENIED';end if;
 return jsonb_build_object('as_of',(statement_timestamp()at time zone'Asia/Jakarta')::date,'rows',coalesce((select jsonb_agg(r)from public.wa_smoke_ap),'[]'));
end$f$;
revoke all on function cp7_reminder_native.receivable_source(),cp7_reminder_native.payable_source()from public,anon,authenticated,service_role;
-- WA-2b: which staged jobs exist, and the public analysis/reminder functions the analysis tick calls (never reached on
-- this stack: it holds no analysis job, so the tick answers NO_OWNER_ANALYSIS_YET).
create schema cp7_analysis_stage;
create table cp7_analysis_stage.jobs(id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,query jsonb not null,
 run_id uuid not null unique,state text not null,captured_at timestamptz not null,created_at timestamptz not null default now(),updated_at timestamptz not null default now());
revoke all on schema cp7_analysis_stage from public,anon,authenticated,service_role;
revoke all on cp7_analysis_stage.jobs from public,anon,authenticated,service_role;
create function public.erp_cp7_request_staged_analysis_v1(p_query jsonb,p_request uuid)returns jsonb language plpgsql security definer set search_path=''as $f$
begin raise exception 'WA_SMOKE_NOT_AVAILABLE';end$f$;
create function public.erp_cp7_staged_snapshot_freshness_v1(p_run uuid)returns jsonb language plpgsql security definer set search_path=''as $f$
begin raise exception 'WA_SMOKE_NOT_AVAILABLE';end$f$;
create function public.erp_cp7_step_reminder_conditions_v2(p_run uuid)returns jsonb language plpgsql security definer set search_path=''as $f$
begin raise exception 'WA_SMOKE_NOT_AVAILABLE';end$f$;
create function public.erp_cp7_read_reminder_conditions_v2(p_query jsonb)returns jsonb language plpgsql security definer set search_path=''as $f$
begin raise exception 'WA_SMOKE_NOT_AVAILABLE';end$f$;
create function public.erp_cp7_recheck_reminder_v2(p_run uuid,p_condition text)returns jsonb language plpgsql security definer set search_path=''as $f$
begin raise exception 'WA_SMOKE_NOT_AVAILABLE';end$f$;
revoke all on function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid),public.erp_cp7_staged_snapshot_freshness_v1(uuid),
 public.erp_cp7_step_reminder_conditions_v2(uuid),public.erp_cp7_read_reminder_conditions_v2(jsonb),public.erp_cp7_recheck_reminder_v2(uuid,text)
 from public,anon,authenticated,service_role;
