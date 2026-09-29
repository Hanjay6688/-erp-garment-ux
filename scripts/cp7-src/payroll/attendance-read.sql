-- P12 attendance source reader candidate. Separate capability; no business DML.
create role cp7_attendance_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_attendance authorization cp7_attendance_read;
revoke all on schema cp7_attendance from public,anon,authenticated,service_role;
grant usage on schema erp,auth to cp7_attendance_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_attendance_read;
grant select on erp.contractors,erp.contractor_workers,erp.worker_daily_rate_versions,erp.worker_employment_periods,
 erp.attendance_periods,erp.attendance_records,erp.payroll_attendance_items,erp.payroll_settlements to cp7_attendance_read;

create function cp7_attendance.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.attendance.view') then raise exception using errcode='42501',message='CP7_ATTENDANCE_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_attendance.source_token(p_contractor uuid,p_start date,p_end date) returns text
language sql stable security invoker set search_path='' as $$
 select md5(jsonb_build_array(c.id,c.xmin::text,p_start,p_end,
  (select coalesce(jsonb_agg(jsonb_build_array(w.id,w.xmin::text) order by w.id),'[]') from erp.contractor_workers w where w.contractor_id=c.id),
  (select coalesce(jsonb_agg(jsonb_build_array(r.id,r.xmin::text) order by r.id),'[]') from erp.worker_daily_rate_versions r join erp.contractor_workers w on w.id=r.worker_id where w.contractor_id=c.id),
  (select coalesce(jsonb_agg(jsonb_build_array(e.id,e.xmin::text) order by e.id),'[]') from erp.worker_employment_periods e join erp.contractor_workers w on w.id=e.worker_id where w.contractor_id=c.id),
  (select coalesce(jsonb_agg(jsonb_build_array(p.id,p.xmin::text) order by p.id),'[]') from erp.attendance_periods p where p.contractor_id=c.id and p.period_start<=p_end and p.period_end>=p_start),
  (select coalesce(jsonb_agg(jsonb_build_array(a.id,a.xmin::text) order by a.id),'[]') from erp.attendance_records a where a.contractor_id=c.id and a.attendance_date between p_start and p_end),
  (select coalesce(jsonb_agg(jsonb_build_array(i.id,i.xmin::text,p.id,p.xmin::text) order by i.id),'[]') from erp.payroll_attendance_items i join erp.payroll_settlements p on p.id=i.payroll_id join erp.attendance_records a on a.id=i.attendance_record_id where a.contractor_id=c.id and a.attendance_date between p_start and p_end)
 )::text) from erp.contractors c where c.id=p_contractor and c.contractor_type='MANDOR'
$$;

create function cp7_attendance.worker_document(p_worker uuid,p_at date) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',w.id,'contractor_id',w.contractor_id,'code',w.worker_code,'name',w.worker_name,'job_description',w.job_description,
  'pay_scheme',w.pay_scheme,'active_now',w.is_active,'joined_at',w.joined_at,'left_at',w.left_at,'notes',w.notes,'row_version',w.row_version::text,
  'rate_at',p_at,'daily_rate_at_date',(select r.daily_rate::text from erp.worker_daily_rate_versions r where r.worker_id=w.id and r.effective_from<=p_at and(r.effective_to is null or r.effective_to>=p_at) order by r.effective_from desc limit 1),
  'employed_at_date',exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id and e.started_on<=p_at and(e.ended_on is null or e.ended_on>=p_at)))
 from erp.contractor_workers w where w.id=p_worker
$$;

create function cp7_attendance.period_document(p_period uuid) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',p.id,'contractor_id',p.contractor_id,'number',p.period_number,'period_start',p.period_start,'period_end',p.period_end,
  'pay_date',p.pay_date,'status',p.status,'correction_of_id',p.correction_of_period_id,'notes',p.notes,'row_version',p.row_version::text,
  'record_count',(select count(*)::text from erp.attendance_records a where a.attendance_period_id=p.id),
  'consuming_payroll_count',(select count(distinct h.id)::text from erp.payroll_attendance_items i join erp.payroll_settlements h on h.id=i.payroll_id join erp.attendance_records a on a.id=i.attendance_record_id where a.attendance_period_id=p.id and h.status<>'REVERSED'))
 from erp.attendance_periods p where p.id=p_period
$$;

create function cp7_attendance.workspace(p_section text,p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare access jsonb;q text;cid uuid;wid uuid;pid uuid;d1 date;d2 date;lim integer;off integer;total bigint;rows jsonb;contractor jsonb;worker jsonb;period jsonb;token text;
begin
 access:=cp7_attendance.access_now();
 if p_section is null or p_section not in('CONTRACTORS','WORKERS','RATES','EMPLOYMENT','PERIODS','RECORDS')
  or jsonb_typeof(p_query) is distinct from 'object'
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','contractor_id','worker_id','period_id','date_from','date_to','limit','offset'))
  or exists(select 1 from jsonb_each(p_query) e where e.key not in('limit','offset') and jsonb_typeof(e.value)<>'string')
  or(p_query?'limit' and(jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset' and(jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_ATTENDANCE_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));cid:=(p_query->>'contractor_id')::uuid;wid:=(p_query->>'worker_id')::uuid;pid:=(p_query->>'period_id')::uuid;
 d1:=(p_query->>'date_from')::date;d2:=(p_query->>'date_to')::date;lim:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or lim not between 1 and 100 or off not between 0 and 1000000
  or(p_section='CONTRACTORS' and(cid is not null or wid is not null or pid is not null or d1 is not null or d2 is not null))
  or(p_section<>'CONTRACTORS' and(cid is null or d1 is null or d2 is null or d2<d1 or(p_query->>'date_from')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or(p_query->>'date_to')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or(p_section in('RATES','EMPLOYMENT') and(wid is null or pid is not null or q<>''))
  or(p_section='RECORDS' and(pid is null or wid is not null or q<>''))
  or(p_section in('WORKERS','PERIODS') and(wid is not null or pid is not null)) then raise exception 'CP7_ATTENDANCE_QUERY';end if;
 if cid is not null then
  select jsonb_build_object('id',c.id,'name',c.contractor_name,'active_now',c.is_active,'attendance_required',c.attendance_required) into contractor from erp.contractors c where c.id=cid and c.contractor_type='MANDOR';
  if contractor is null then raise exception 'CP7_ATTENDANCE_CONTRACTOR';end if;
  token:=cp7_attendance.source_token(cid,d1,d2);
 end if;
 if wid is not null then
  worker:=cp7_attendance.worker_document(wid,d1);
  if worker is null or(worker->>'contractor_id')::uuid<>cid then raise exception 'CP7_ATTENDANCE_WORKER_PARENT';end if;
 end if;
 if pid is not null then
  period:=cp7_attendance.period_document(pid);
  if period is null or(period->>'contractor_id')::uuid<>cid or(period->>'period_start')::date<>d1 or(period->>'period_end')::date<>d2 then raise exception 'CP7_ATTENDANCE_PERIOD_PARENT';end if;
 end if;
 if p_section='CONTRACTORS' then
  with filtered as materialized(select c.* from erp.contractors c where c.contractor_type='MANDOR' and(q='' or strpos(lower(c.contractor_name),lower(q))>0)),page as(select * from filtered order by contractor_name,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'name',contractor_name,'active_now',is_active,'attendance_required',attendance_required) order by contractor_name,id),'[]') into total,rows from page;
 elsif p_section='WORKERS' then
  with filtered as materialized(select w.* from erp.contractor_workers w where w.contractor_id=cid and(q='' or strpos(lower(concat_ws(' ',w.worker_code,w.worker_name,w.job_description)),lower(q))>0)
   and exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id and e.started_on<=d2 and(e.ended_on is null or e.ended_on>=d1))),page as(select * from filtered order by worker_name,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(cp7_attendance.worker_document(id,d1) order by worker_name,id),'[]') into total,rows from page;
 elsif p_section='RATES' then
  with filtered as materialized(select r.* from erp.worker_daily_rate_versions r where r.worker_id=wid and r.effective_from<=d2 and(r.effective_to is null or r.effective_to>=d1)),page as(select * from filtered order by effective_from,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'worker_id',worker_id,'daily_rate',daily_rate::text,'date_from',effective_from,'date_to',effective_to,'reason',change_reason) order by effective_from,id),'[]') into total,rows from page;
 elsif p_section='EMPLOYMENT' then
  with filtered as materialized(select e.* from erp.worker_employment_periods e where e.worker_id=wid and e.started_on<=d2 and(e.ended_on is null or e.ended_on>=d1)),page as(select * from filtered order by started_on,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'worker_id',worker_id,'date_from',started_on,'date_to',ended_on,'start_reason',start_reason,'end_reason',end_reason) order by started_on,id),'[]') into total,rows from page;
 elsif p_section='PERIODS' then
  with filtered as materialized(select p.* from erp.attendance_periods p where p.contractor_id=cid and p.period_start<=d2 and p.period_end>=d1 and(q='' or strpos(lower(concat_ws(' ',p.period_number,p.notes)),lower(q))>0)),page as(select * from filtered order by period_start desc,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(cp7_attendance.period_document(id) order by period_start desc,id),'[]') into total,rows from page;
 else
  with filtered as materialized(select a.*,w.worker_name from erp.attendance_records a join erp.contractor_workers w on w.id=a.worker_id where a.attendance_period_id=pid),page as(select * from filtered order by attendance_date,worker_id,id limit lim offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'period_id',attendance_period_id,'worker_id',worker_id,'worker_name',worker_name,'date',attendance_date,'mark',status,'paid_fraction',paid_fraction::text,'lifecycle',coalesce(record_lifecycle,'LEGACY_POSTED'),'supersedes_id',supersedes_attendance_record_id,'notes',notes,'row_version',row_version::text) order by attendance_date,worker_id,id),'[]') into total,rows from page;
 end if;
 return jsonb_build_object('contract_version','cp7.attendance-workspace.v1','section',p_section,'date_from',d1,'date_to',d2,'source_token',token,'contractor',contractor,'worker',worker,'period',period,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',lim,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;

create function public.erp_cp7_get_attendance_workspace_v1(p_section text,p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_attendance.workspace(p_section,p_query)$$;
grant create on schema public to cp7_attendance_read;
alter function cp7_attendance.access_now() owner to cp7_attendance_read;
alter function cp7_attendance.source_token(uuid,date,date) owner to cp7_attendance_read;
alter function cp7_attendance.worker_document(uuid,date) owner to cp7_attendance_read;
alter function cp7_attendance.period_document(uuid) owner to cp7_attendance_read;
alter function cp7_attendance.workspace(text,jsonb) owner to cp7_attendance_read;
alter function public.erp_cp7_get_attendance_workspace_v1(text,jsonb) owner to cp7_attendance_read;
revoke create on schema public from cp7_attendance_read;
revoke all on all functions in schema cp7_attendance from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_attendance_workspace_v1(text,jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_attendance_workspace_v1(text,jsonb) to authenticated;
