-- P12 ordinary attendance source lifecycle. Native formulas, completeness and
-- correction/payroll lineage guards remain the authority.
create role cp7_attendance_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_attendance,auth,erp to cp7_attendance_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_attendance_write;
create table cp7_attendance.command_requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id));
create table cp7_attendance.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,contractor_id uuid not null,period_id uuid,action text not null check(action in('PREVIEW','SAVE','POST','REVERSE')),permission text not null check(permission in('finance.attendance.create','finance.attendance.edit_draft','finance.attendance.post','finance.attendance.reverse')),owner_required boolean not null,primary key(backend_pid,transaction_id));
alter table cp7_attendance.command_requests owner to cp7_attendance_write;
alter table cp7_attendance.command_context owner to cp7_attendance_write;
alter table cp7_attendance.command_requests enable row level security;
alter table cp7_attendance.command_context enable row level security;
revoke all on cp7_attendance.command_requests,cp7_attendance.command_context from public,anon,authenticated,service_role,cp7_capture,cp7_attendance_read,cp7_roster_write;

create function cp7_attendance.command_access(p_action text,p_document jsonb,p_expected text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;permission text;owner_needed boolean;
begin
 a:=cp7_attendance.access_now();
 permission:=case p_action when 'PREVIEW' then case when p_expected is null then 'finance.attendance.create' else 'finance.attendance.edit_draft' end when 'SAVE' then case when p_expected is null then 'finance.attendance.create' else 'finance.attendance.edit_draft' end when 'POST' then 'finance.attendance.post' when 'REVERSE' then 'finance.attendance.reverse' end;
 if permission is null or not erp.has_permission(permission) then raise exception using errcode='42501',message='CP7_ATTENDANCE_WRITE_DENIED';end if;
 owner_needed:=p_action='REVERSE' or p_document->>'correction_of_period_id' is not null or exists(select 1 from erp.attendance_periods where id=(p_document->>'period_id')::uuid and correction_of_period_id is not null);
 if owner_needed and coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_ATTENDANCE_OWNER_ADMIN_REQUIRED';end if;
 return a||jsonb_build_object('attendance_permission',permission,'attendance_owner_required',owner_needed);
end $$;

create function cp7_attendance.validate_command(p_action text,p_payload jsonb,p_expected text) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare d jsonb;line jsonb;required text[];allowed text[];
begin
 if p_action is null or p_action not in('PREVIEW','SAVE','POST','REVERSE') or jsonb_typeof(p_payload) is distinct from 'object'
  or not p_payload ?& array['contractor_id','date_from','date_to','source_token','document']
  or exists(select 1 from jsonb_each(p_payload) e where e.key<>all(array['contractor_id','date_from','date_to','source_token','document']) or(e.key<>'document' and jsonb_typeof(e.value)<>'string'))
  or jsonb_typeof(p_payload->'document') is distinct from 'object'
  or coalesce(p_payload->>'contractor_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'source_token','')!~'^[a-f0-9]{32}$'
  or coalesce(p_payload->>'date_from','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or coalesce(p_payload->>'date_to','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or(p_payload->>'date_to')::date<(p_payload->>'date_from')::date
  or(p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$') then raise exception 'CP7_ATTENDANCE_FIELDS';end if;
 d:=p_payload->'document';
 required:=case when p_action in('PREVIEW','SAVE') then array['contractor_id','period_number','period_start','period_end','pay_date','reason','attendance'] else array['period_id','reason'] end;
 allowed:=required||case when p_action in('PREVIEW','SAVE') then array['period_id','correction_of_period_id','notes'] else array[]::text[] end;
 if not d ?& required or exists(select 1 from jsonb_each(d) e where e.key<>all(allowed))
  or exists(select 1 from jsonb_each(d) e where case when e.key='attendance' then jsonb_typeof(e.value)<>'array' when e.key in('period_id','correction_of_period_id','notes') then jsonb_typeof(e.value) not in('string','null') else jsonb_typeof(e.value)<>'string' end)
  or length(btrim(d->>'reason')) not between 5 and 1000
  or exists(select 1 from jsonb_each_text(d) e where e.key in('period_id','correction_of_period_id','contractor_id') and e.value is not null and e.value!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or exists(select 1 from jsonb_each_text(d) e where e.key in('period_start','period_end','pay_date') and e.value!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  or((d->>'period_id' is null) is distinct from (p_expected is null))
  or(p_action in('POST','REVERSE') and p_expected is null)
  or(p_action in('PREVIEW','SAVE') and(d->>'contractor_id' is distinct from p_payload->>'contractor_id' or d->>'period_start' is distinct from p_payload->>'date_from' or d->>'period_end' is distinct from p_payload->>'date_to')) then raise exception 'CP7_ATTENDANCE_FIELDS';end if;
 if p_action in('PREVIEW','SAVE') then
  for line in select value from jsonb_array_elements(d->'attendance') loop
   if jsonb_typeof(line) is distinct from 'object' or not line ?& array['worker_id','attendance_date','status','paid_fraction']
    or exists(select 1 from jsonb_each(line) e where e.key<>all(array['worker_id','attendance_date','status','paid_fraction','notes','supersedes_attendance_record_id']) or case when e.key in('notes','supersedes_attendance_record_id') then jsonb_typeof(e.value) not in('string','null') else jsonb_typeof(e.value)<>'string' end)
    or coalesce(line->>'worker_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    or coalesce(line->>'attendance_date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
    or coalesce(line->>'status','') not in('PRESENT','ABSENT','HALF_DAY','SICK','LEAVE','OFF')
    or coalesce(line->>'paid_fraction','')!~'^(0([.][0-9]{1,4})?|1([.]0{1,4})?)$'
    or(line->>'supersedes_attendance_record_id' is not null and line->>'supersedes_attendance_record_id'!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') then raise exception 'CP7_ATTENDANCE_LINE_FIELDS';end if;
   if(line->>'status'='HALF_DAY' and(line->>'paid_fraction')::numeric>0.5) or(line->>'status' in('ABSENT','OFF') and(line->>'paid_fraction')::numeric<>0) then raise exception 'CP7_ATTENDANCE_LINE_FRACTION';end if;
  end loop;
 end if;
end $$;

create function cp7_attendance.apply_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;d jsonb:=p_payload->'document';cid uuid:=(p_payload->>'contractor_id')::uuid;pid uuid:=(d->>'period_id')::uuid;p erp.attendance_periods;ctx cp7_attendance.command_context;native jsonb;
begin
 a:=cp7_attendance.command_access(p_action,d,p_expected);
 select * into ctx from cp7_attendance.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and actor=auth.uid() and action=p_action and contractor_id=cid and period_id is not distinct from pid;
 if ctx.actor is null or ctx.permission is distinct from a->>'attendance_permission' or ctx.owner_required is distinct from(a->>'attendance_owner_required')::boolean then raise exception using errcode='42501',message='CP7_ATTENDANCE_PRIVATE_CONTEXT_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended(cid::text,0));
 perform 1 from erp.contractors where id=cid and contractor_type='MANDOR' for share;
 if not found then raise exception 'CP7_ATTENDANCE_CONTRACTOR';end if;
 if pid is not null then
  select * into p from erp.attendance_periods where id=pid for update;
  if p.id is null or p.contractor_id<>cid then raise exception 'CP7_ATTENDANCE_PERIOD_PARENT';end if;
  if p.row_version::text is distinct from p_expected then raise exception 'CP7_ATTENDANCE_VERSION_CHANGED';end if;
  if p_action in('PREVIEW','SAVE') and p.status<>'DRAFT' then raise exception 'CP7_ATTENDANCE_DRAFT_ONLY';end if;
  if p_action in('POST','REVERSE') and(p.period_start::text is distinct from p_payload->>'date_from' or p.period_end::text is distinct from p_payload->>'date_to') then raise exception 'CP7_ATTENDANCE_PERIOD_DATES';end if;
 end if;
 perform 1 from erp.contractor_workers where contractor_id=cid order by id for share;
 if cp7_attendance.command_access(p_action,d,p_expected) is distinct from a then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_CHANGED';end if;
 if cp7_attendance.source_token(cid,(p_payload->>'date_from')::date,(p_payload->>'date_to')::date) is distinct from p_payload->>'source_token' then raise exception 'CP7_ATTENDANCE_REVIEW_CHANGED';end if;
 if p_action in('PREVIEW','SAVE') then
  native:=erp.save_attendance_period_v1(d,p_request,p_expected::bigint,p_action='PREVIEW');
  if p_action='SAVE' then pid:=(native->>'period_id')::uuid;end if;
 elsif p_action='POST' then native:=erp.post_attendance_period_v1(pid,d->>'reason',p_request,p_expected::bigint);
 elsif p_action='REVERSE' then native:=erp.reverse_attendance_period_v1(pid,d->>'reason',p_request,p_expected::bigint);
 end if;
 if cp7_attendance.command_access(p_action,d,p_expected) is distinct from a then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_CHANGED';end if;
 if p_action='PREVIEW' then
  if native->'preview_only' is distinct from 'true'::jsonb then raise exception 'CP7_ATTENDANCE_NATIVE_PREVIEW';end if;
  return jsonb_build_object('contract_version','cp7.attendance-preview.v1','kind','READ_ONLY_PREVIEW','contractor_id',cid,'period_id',pid,'source_token',p_payload->>'source_token','line_count',native->>'line_count','paid_day_equivalent',native->>'paid_day_equivalent','estimated_amount',native->>'estimated_amount');
 end if;
 select * into p from erp.attendance_periods where id=pid;
 if p.id is null or p.contractor_id<>cid or native->>'period_id' is distinct from p.id::text or native->>'row_version' is distinct from p.row_version::text or p.status is distinct from case p_action when 'SAVE' then 'DRAFT' when 'POST' then 'POSTED' when 'REVERSE' then 'REVERSED' end then raise exception 'CP7_ATTENDANCE_NATIVE_OUTCOME';end if;
 return jsonb_build_object('contract_version','cp7.attendance-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'period_id',p.id,'contractor_id',cid,'row_version',p.row_version::text,'status',p.status,'source_token',cp7_attendance.source_token(cid,(p_payload->>'date_from')::date,(p_payload->>'date_to')::date));
end $$;

create function cp7_attendance.attendance_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_attendance.command_requests;result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_attendance.validate_command(p_action,p_payload,p_expected);
 a:=cp7_attendance.command_access(p_action,p_payload->'document',p_expected);
 if p_action<>'PREVIEW' then
  if p_request is null then raise exception 'CP7_ATTENDANCE_REQUEST_REQUIRED';end if;
  insert into cp7_attendance.command_requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
  select * into old from cp7_attendance.command_requests where actor=auth.uid() and request_id=p_request for update;
  if old.action is distinct from p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_ATTENDANCE_REQUEST_CHANGED';end if;
  if cp7_attendance.command_access(p_action,p_payload->'document',p_expected) is distinct from a then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_CHANGED';end if;
  if old.response is not null then return old.response;end if;
 end if;
 insert into cp7_attendance.command_context values(pg_backend_pid(),txid_current(),auth.uid(),(p_payload->>'contractor_id')::uuid,(p_payload->'document'->>'period_id')::uuid,p_action,a->>'attendance_permission',(a->>'attendance_owner_required')::boolean);
 result:=cp7_attendance.apply_command(p_action,p_payload,p_request,p_expected);
 delete from cp7_attendance.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if cp7_attendance.command_access(p_action,p_payload->'document',p_expected) is distinct from a then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_CHANGED';end if;
 if p_action<>'PREVIEW' then update cp7_attendance.command_requests set response=result where actor=auth.uid() and request_id=p_request;end if;
 return result;
end $$;

create function public.erp_cp7_save_attendance_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$begin
 if p_action='PREVIEW' then raise exception 'CP7_ATTENDANCE_USE_PREVIEW';end if;
 return cp7_attendance.attendance_command(p_action,p_payload,p_request,p_expected);
end $$;
create function public.erp_cp7_preview_attendance_v1(p_payload jsonb,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_attendance.attendance_command('PREVIEW',p_payload,null,p_expected)$$;
alter function cp7_attendance.command_access(text,jsonb,text) owner to cp7_attendance_read;
alter function cp7_attendance.validate_command(text,jsonb,text) owner to cp7_attendance_write;
alter function cp7_attendance.apply_command(text,jsonb,uuid,text) owner to postgres;
alter function cp7_attendance.attendance_command(text,jsonb,uuid,text) owner to cp7_attendance_write;
grant create on schema public to cp7_attendance_write;
alter function public.erp_cp7_save_attendance_v1(text,jsonb,uuid,text) owner to cp7_attendance_write;
alter function public.erp_cp7_preview_attendance_v1(jsonb,text) owner to cp7_attendance_write;
revoke create on schema public from cp7_attendance_write;
revoke all on function cp7_attendance.command_access(text,jsonb,text),cp7_attendance.validate_command(text,jsonb,text),cp7_attendance.apply_command(text,jsonb,uuid,text),cp7_attendance.attendance_command(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture,cp7_attendance_read,cp7_roster_write,cp7_payroll_write,cp7_payroll_read;
grant execute on function cp7_attendance.command_access(text,jsonb,text) to cp7_attendance_write,postgres;
grant execute on function cp7_attendance.apply_command(text,jsonb,uuid,text) to cp7_attendance_write;
grant select on cp7_attendance.command_context to postgres;
revoke all on function public.erp_cp7_save_attendance_v1(text,jsonb,uuid,text),public.erp_cp7_preview_attendance_v1(jsonb,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_attendance_v1(text,jsonb,uuid,text),public.erp_cp7_preview_attendance_v1(jsonb,text) to authenticated;
