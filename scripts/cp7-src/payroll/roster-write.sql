-- P12 roster/rate adapter. Native OWNER/ADMIN authority is preserved in
-- addition to current create/edit and attendance-view permissions.
create role cp7_roster_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_attendance,auth,erp to cp7_roster_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_roster_write;
create table cp7_attendance.roster_requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id));
alter table cp7_attendance.roster_requests owner to cp7_roster_write;
alter table cp7_attendance.roster_requests enable row level security;
revoke all on cp7_attendance.roster_requests from public,anon,authenticated,service_role,cp7_capture,cp7_attendance_read;

create function cp7_attendance.roster_access(p_action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;permission text;
begin
 a:=cp7_attendance.access_now();
 permission:=case p_action when 'CREATE_WORKER' then 'finance.attendance.create' when 'UPDATE_WORKER' then 'finance.attendance.edit_draft' when 'SET_RATE' then 'finance.attendance.edit_draft' end;
 if permission is null or not erp.has_permission(permission) then raise exception using errcode='42501',message='CP7_ROSTER_WRITE_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_ROSTER_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $$;

create function cp7_attendance.apply_roster(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;d jsonb:=p_payload->'document';cid uuid:=(p_payload->>'contractor_id')::uuid;wid uuid;w erp.contractor_workers;native jsonb;result jsonb;
begin
 a:=cp7_attendance.roster_access(p_action);
 -- Shared contractor advisory order serializes the connected payroll source
 -- rebuild with roster/rate changes; the native worker lock follows it.
 perform pg_advisory_xact_lock(hashtextextended(cid::text,0));
 perform 1 from erp.contractors where id=cid and contractor_type='MANDOR' for share;
 if not found then raise exception 'CP7_ROSTER_CONTRACTOR';end if;
 if p_action<>'CREATE_WORKER' then
  wid:=(d->>'worker_id')::uuid;select * into w from erp.contractor_workers where id=wid for update;
  if w.id is null or w.contractor_id<>cid then raise exception 'CP7_ROSTER_WORKER_PARENT';end if;
  if w.row_version::text is distinct from p_expected then raise exception 'CP7_ROSTER_VERSION_CHANGED';end if;
 end if;
 if cp7_attendance.roster_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_ROSTER_ACCESS_CHANGED';end if;
 if cp7_attendance.source_token(cid,(p_payload->>'date_from')::date,(p_payload->>'date_to')::date) is distinct from p_payload->>'source_token' then raise exception 'CP7_ROSTER_REVIEW_CHANGED';end if;
 if p_action='SET_RATE' then
  native:=erp.set_worker_daily_rate_v1(wid,(d->>'daily_rate')::numeric,(d->>'effective_from')::date,d->>'reason',p_request,p_expected::bigint);
 else
  if(d->>'contractor_id')::uuid is distinct from cid then raise exception 'CP7_ROSTER_CONTRACTOR_CHANGED';end if;
  -- The native writer always sets worker_code from the payload; an update
  -- carries the locked row's code so a rename never erases it.
  native:=erp.save_worker_roster_v1(case when p_action='UPDATE_WORKER' then d||jsonb_build_object('worker_code',w.worker_code) else d end,p_request,p_expected::bigint);
  wid:=(native->>'worker_id')::uuid;
 end if;
 select * into w from erp.contractor_workers where id=wid;
 if w.id is null or w.contractor_id<>cid or native->>'worker_id' is distinct from w.id::text or native->>'row_version' is distinct from w.row_version::text then raise exception 'CP7_ROSTER_NATIVE_OUTCOME';end if;
 if cp7_attendance.roster_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_ROSTER_ACCESS_CHANGED';end if;
 result:=jsonb_build_object('contract_version','cp7.roster-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'worker_id',w.id,'contractor_id',cid,'row_version',w.row_version::text,'status',case when w.is_active then 'ACTIVE' else 'INACTIVE' end,
  'source_token',cp7_attendance.source_token(cid,(p_payload->>'date_from')::date,(p_payload->>'date_to')::date));
 return result;
end $$;

create function cp7_attendance.roster_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_attendance.roster_requests;d jsonb;required text[];allowed text[];result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_attendance.roster_access(p_action);
 if p_request is null or jsonb_typeof(p_payload) is distinct from 'object'
  or not p_payload ?& array['contractor_id','date_from','date_to','source_token','document']
  or exists(select 1 from jsonb_each(p_payload) e where e.key<>all(array['contractor_id','date_from','date_to','source_token','document']) or(e.key<>'document' and jsonb_typeof(e.value)<>'string'))
  or jsonb_typeof(p_payload->'document') is distinct from 'object'
  or coalesce(p_payload->>'contractor_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'source_token','')!~'^[a-f0-9]{32}$'
  or coalesce(p_payload->>'date_from','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or coalesce(p_payload->>'date_to','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or(p_payload->>'date_to')::date<(p_payload->>'date_from')::date
  or(p_action='CREATE_WORKER' and p_expected is not null)
  or(p_action<>'CREATE_WORKER' and(p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$')) then raise exception 'CP7_ROSTER_FIELDS';end if;
 d:=p_payload->'document';
 if p_action='SET_RATE' then required:=array['worker_id','daily_rate','effective_from','reason'];allowed:=required;
 else
  required:=array['contractor_id','worker_name','job_description','pay_scheme','joined_at','is_active','reason']||case when p_action='CREATE_WORKER' then array['initial_daily_rate','rate_effective_from'] else array['worker_id'] end;
  allowed:=required||array['notes','left_at']||case when p_action='CREATE_WORKER' then array['worker_code'] else array['reactivated_at'] end;
 end if;
 if not d ?& required or exists(select 1 from jsonb_each(d) e where e.key<>all(allowed))
  or exists(select 1 from jsonb_each(d) e where case when e.key='is_active' then jsonb_typeof(e.value)<>'boolean' when e.key in('notes','left_at','reactivated_at','worker_code') then jsonb_typeof(e.value) not in('string','null') else jsonb_typeof(e.value)<>'string' end)
  or length(btrim(d->>'reason')) not between 5 and 1000
  or(p_action<>'CREATE_WORKER' and coalesce(d->>'worker_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or exists(select 1 from jsonb_each_text(d) e where e.key in('joined_at','left_at','reactivated_at','rate_effective_from','effective_from') and e.value is not null and e.value!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  or exists(select 1 from jsonb_each_text(d) e where e.key in('initial_daily_rate','daily_rate') and e.value!~'^(0|[1-9][0-9]{0,17})([.][0-9]{1,6})?$') then raise exception 'CP7_ROSTER_FIELDS';end if;
 insert into cp7_attendance.roster_requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_attendance.roster_requests where actor=auth.uid() and request_id=p_request for update;
 if old.action is distinct from p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_ROSTER_REQUEST_CHANGED';end if;
 if cp7_attendance.roster_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_ROSTER_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 result:=cp7_attendance.apply_roster(p_action,p_payload,p_request,p_expected);
 if cp7_attendance.roster_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_ROSTER_ACCESS_CHANGED';end if;
 update cp7_attendance.roster_requests set response=result where actor=auth.uid() and request_id=p_request;
 return result;
end $$;

create function public.erp_cp7_save_roster_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_attendance.roster_command(p_action,p_payload,p_request,p_expected)$$;
alter function cp7_attendance.roster_access(text) owner to cp7_attendance_read;
alter function cp7_attendance.apply_roster(text,jsonb,uuid,text) owner to postgres;
alter function cp7_attendance.roster_command(text,jsonb,uuid,text) owner to cp7_roster_write;
grant create on schema public to cp7_roster_write;
alter function public.erp_cp7_save_roster_v1(text,jsonb,uuid,text) owner to cp7_roster_write;
revoke create on schema public from cp7_roster_write;
revoke all on function cp7_attendance.roster_access(text),cp7_attendance.apply_roster(text,jsonb,uuid,text),cp7_attendance.roster_command(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture,cp7_payroll_read,cp7_payroll_write,cp7_nota_write,cp7_payroll_header;
grant usage on schema cp7_attendance to postgres;
grant execute on function cp7_attendance.roster_access(text),cp7_attendance.source_token(uuid,date,date) to postgres;
grant execute on function cp7_attendance.roster_access(text),cp7_attendance.apply_roster(text,jsonb,uuid,text) to cp7_roster_write;
revoke all on function public.erp_cp7_save_roster_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_roster_v1(text,jsonb,uuid,text) to authenticated;
