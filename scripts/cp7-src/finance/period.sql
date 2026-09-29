-- Bounded period control: accepted close/reopen functions own all business writes.
create role cp7_period_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_period_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_period authorization cp7_period_read;
revoke all on schema cp7_period from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_period to cp7_period_write;
grant usage on schema erp,auth to cp7_period_read,cp7_period_write;
grant usage on schema cp7_finance to cp7_period_read;
grant execute on function cp7_finance.exact_numbers(jsonb) to cp7_period_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_period_read,cp7_period_write;
grant execute on function erp.accounting_close_preflight_v1(date) to cp7_period_read;
grant select on erp.accounting_period_control,erp.accounting_close_filings_v1,erp.account_daily_balances to cp7_period_read;
grant execute on function erp.close_accounting_through(date,text),erp.reopen_accounting_through(date,text) to cp7_period_write;
create table cp7_period.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,response jsonb,primary key(actor,request_id));
alter table cp7_period.requests owner to cp7_period_write;
alter table cp7_period.requests enable row level security;
revoke all on cp7_period.requests from public,anon,authenticated,service_role,cp7_capture,cp7_period_read;

create function cp7_period.access_now() returns void
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_PERIOD_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.reports.view') or not erp.has_permission('finance.period_close.manage') then raise exception using errcode='42501',message='CP7_PERIOD_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_PERIOD_OWNER_ADMIN_REQUIRED';end if;
end $$;

create function cp7_period.workspace(p_through date) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare control jsonb;preflight jsonb;balances jsonb;filing jsonb;token text;
begin
 perform cp7_period.access_now();
 if p_through is null or p_through>(statement_timestamp() at time zone 'Asia/Jakarta')::date then raise exception 'CP7_PERIOD_REVIEW_DATE';end if;
 select jsonb_build_object('closed_through',c.closed_through,'version_token',md5(jsonb_build_array(c.closed_through,extract(epoch from c.updated_at),c.updated_by,c.change_reason)::text)) into control from erp.accounting_period_control c where c.singleton_id=1;
 if control is null then raise exception 'CP7_PERIOD_CONTROL_MISSING';end if;
 preflight:=erp.accounting_close_preflight_v1(p_through);
 if preflight is null or jsonb_typeof(preflight) is distinct from 'object' or octet_length(preflight::text)>1000000 then raise exception 'CP7_PERIOD_REVIEW_INCOMPLETE';end if;
 select coalesce(jsonb_agg(jsonb_build_array(b.account_id,b.balance) order by b.account_id),'[]') into balances
 from(select a.account_id,sum(a.debit_total-a.credit_total) balance from erp.account_daily_balances a where a.balance_date<=p_through group by a.account_id)b;
 select jsonb_build_object('id',f.id,'closed_through',f.closed_through,'filed_at',f.filed_at) into filing from erp.accounting_close_filings_v1 f where f.closed_through=(control->>'closed_through')::date order by f.filed_at desc,f.id desc limit 1;
 token:=md5(jsonb_build_array(p_through,control,preflight,balances)::text);
 return jsonb_build_object('contract_version','cp7.period-control.v1','captured_at',statement_timestamp(),'through',p_through,'control',control,
  'review_token',token,'preflight',cp7_finance.exact_numbers(preflight),'current_filing',filing);
end $$;

-- Only this helper obtains the same native control-row lock. It grants no ERP
-- DML to the facade role and rechecks access after the actual lock wait.
create function cp7_period.lock_current() returns void
language plpgsql volatile security definer set search_path='' as $$
begin
 perform cp7_period.access_now();
 perform 1 from erp.accounting_period_control where singleton_id=1 for update;
 if not found then raise exception 'CP7_PERIOD_CONTROL_MISSING';end if;
 perform cp7_period.access_now();
end $$;

create function cp7_period.command(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare v_actor uuid;saved cp7_period.requests;state jsonb;after_state jsonb;target date;review_day date;outcome jsonb;
begin
 perform cp7_period.access_now();v_actor:=auth.uid();
 if p_request is null or p_action not in('CLOSE','REOPEN') or p_action is null or jsonb_typeof(p_payload) is distinct from 'object'
  or not p_payload ?& array['through','review_through','review_token','reason']
  or exists(select 1 from jsonb_object_keys(p_payload)k where k not in('through','review_through','review_token','reason'))
  or jsonb_typeof(p_payload->'through') not in('string','null')
  or exists(select 1 from jsonb_each(p_payload)e where e.key in('review_through','review_token','reason') and jsonb_typeof(e.value)<>'string')
  or (p_payload->>'review_through')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or(p_payload->>'through' is not null and(p_payload->>'through')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  or(p_payload->>'review_token')!~'^[a-f0-9]{32}$' or length(btrim(p_payload->>'reason')) not between 1 and 1000 then raise exception 'CP7_PERIOD_COMMAND';end if;
 target:=(p_payload->>'through')::date;review_day:=(p_payload->>'review_through')::date;
 if p_action='CLOSE' and(target is null or target<>review_day) then raise exception 'CP7_PERIOD_CLOSE_REVIEW_DATE';end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('cp7.period.request:'||v_actor::text||':'||p_request::text,0));
 perform cp7_period.access_now();
 select * into saved from cp7_period.requests where requests.actor=v_actor and request_id=p_request;
 if found then
  if saved.action<>p_action or saved.payload<>p_payload then raise exception 'CP7_PERIOD_REQUEST_CHANGED';end if;
  if saved.response is null then raise exception 'CP7_PERIOD_REQUEST_INCOMPLETE';end if;
  return saved.response;
 end if;
 perform cp7_period.lock_current();perform cp7_period.access_now();
 state:=cp7_period.workspace(review_day);
 if state->>'review_token'<>p_payload->>'review_token' then raise exception 'CP7_PERIOD_REVIEW_CHANGED';end if;
 insert into cp7_period.requests(actor,request_id,action,payload) values(v_actor,p_request,p_action,p_payload);
 if p_action='CLOSE' then perform erp.close_accounting_through(target,p_payload->>'reason');
 else
  if state->'control'->>'closed_through' is null then raise exception 'CP7_PERIOD_NOT_CLOSED';end if;
  perform erp.reopen_accounting_through(target,p_payload->>'reason');
 end if;
 perform cp7_period.access_now();after_state:=cp7_period.workspace(review_day);
 if (after_state->'control'->>'closed_through')::date is distinct from target then raise exception 'CP7_PERIOD_OUTCOME_MISMATCH';end if;
 outcome:=jsonb_build_object('contract_version','cp7.period-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'closed_through',target,
  'version_token',after_state->'control'->>'version_token','filing_id',case when p_action='CLOSE' then after_state->'current_filing'->'id' else 'null'::jsonb end);
 if p_action='CLOSE' and outcome->>'filing_id' is null then raise exception 'CP7_PERIOD_FILING_MISSING';end if;
 update cp7_period.requests set response=outcome where requests.actor=v_actor and request_id=p_request;
 return outcome;
end $$;

create function public.erp_cp7_get_period_control_v1(p_through date) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_period.workspace(p_through)$$;
create function public.erp_cp7_save_period_control_v1(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_period.command(p_action,p_payload,p_request)$$;
grant create on schema public to cp7_period_read,cp7_period_write;
alter function cp7_period.access_now() owner to cp7_period_read;
alter function cp7_period.workspace(date) owner to cp7_period_read;
alter function cp7_period.lock_current() owner to postgres;
alter function cp7_period.command(text,jsonb,uuid) owner to cp7_period_write;
alter function public.erp_cp7_get_period_control_v1(date) owner to cp7_period_read;
alter function public.erp_cp7_save_period_control_v1(text,jsonb,uuid) owner to cp7_period_write;
revoke create on schema public,cp7_period from cp7_period_read,cp7_period_write;
revoke all on all functions in schema cp7_period from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_period.access_now(),cp7_period.workspace(date),cp7_period.lock_current() to cp7_period_write;
revoke all on function public.erp_cp7_get_period_control_v1(date),public.erp_cp7_save_period_control_v1(text,jsonb,uuid) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_period_control_v1(date),public.erp_cp7_save_period_control_v1(text,jsonb,uuid) to authenticated;
