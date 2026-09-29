-- Paged native worker/day matrix. Missing marks remain null. Existing draft
-- rows remain visible even when their worker no longer matches eligibility.
create function cp7_attendance.entry_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare cid uuid;pid uuid;start_date date;end_date date;lim integer;off integer;c erp.contractors;p erp.attendance_periods;rows jsonb;total bigint;
begin
 perform cp7_attendance.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['contractor_id','date_from','date_to']
  or exists(select 1 from jsonb_each(p_query) e where e.key<>all(array['contractor_id','date_from','date_to','period_id','limit','offset']) or case when e.key in('limit','offset') then jsonb_typeof(e.value)<>'number' when e.key='period_id' then jsonb_typeof(e.value) not in('string','null') else jsonb_typeof(e.value)<>'string' end)
  or coalesce(p_query->>'contractor_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p_query->>'period_id' is not null and p_query->>'period_id'!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or coalesce(p_query->>'date_from','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or coalesce(p_query->>'date_to','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or coalesce(p_query->>'limit','100')!~'^[1-9][0-9]{0,2}$' or coalesce(p_query->>'offset','0')!~'^(0|[1-9][0-9]{0,6})$' then raise exception 'CP7_ATTENDANCE_ENTRY_QUERY';end if;
 cid:=(p_query->>'contractor_id')::uuid;pid:=(p_query->>'period_id')::uuid;start_date:=(p_query->>'date_from')::date;end_date:=(p_query->>'date_to')::date;lim:=coalesce((p_query->>'limit')::integer,100);off:=coalesce((p_query->>'offset')::integer,0);
 if end_date<start_date or lim>100 or off>1000000 then raise exception 'CP7_ATTENDANCE_ENTRY_QUERY';end if;
 select * into c from erp.contractors where id=cid and contractor_type='MANDOR';if c.id is null then raise exception 'CP7_ATTENDANCE_CONTRACTOR';end if;
 if pid is not null then
  select * into p from erp.attendance_periods where id=pid;
  if p.id is null or p.contractor_id<>cid or p.period_start<>start_date or p.period_end<>end_date then raise exception 'CP7_ATTENDANCE_ENTRY_PARENT';end if;
 end if;
 with cells as materialized(
  select w.id worker_id,w.worker_name,w.worker_code,w.pay_scheme,start_date+days.n work_date,
   exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id and e.started_on<=start_date+days.n and(e.ended_on is null or e.ended_on>=start_date+days.n)) employed,
   ar.id record_id,ar.status,ar.paid_fraction,ar.notes,ar.record_lifecycle,ar.supersedes_attendance_record_id,ar.row_version
  from erp.contractor_workers w cross join generate_series(0,end_date-start_date) days(n)
  left join erp.attendance_records ar on ar.attendance_period_id=pid and ar.worker_id=w.id and ar.attendance_date=start_date+days.n
  where w.contractor_id=cid
 ), eligible as materialized(select * from cells where employed or record_id is not null),paged as(
  select * from eligible order by work_date,worker_name,worker_id limit lim offset off
 )
 select(select count(*) from eligible),coalesce(jsonb_agg(jsonb_build_object('id',x.worker_id::text||':'||x.work_date::text,'worker_id',x.worker_id,'worker_name',x.worker_name,'worker_code',x.worker_code,'pay_scheme',x.pay_scheme,'date',x.work_date,'eligible',x.employed,'required',c.attendance_required and x.employed and x.pay_scheme in('DAILY','HYBRID'),
  'daily_rate',(select v.daily_rate::text from erp.worker_daily_rate_versions v where v.worker_id=x.worker_id and v.effective_from<=x.work_date and(v.effective_to is null or v.effective_to>=x.work_date) order by v.effective_from desc limit 1),
  'record',case when x.record_id is null then null else jsonb_build_object('id',x.record_id,'mark',x.status,'paid_fraction',x.paid_fraction::text,'notes',x.notes,'lifecycle',x.record_lifecycle,'supersedes_id',x.supersedes_attendance_record_id,'row_version',x.row_version::text) end) order by x.work_date,x.worker_name,x.worker_id),'[]') into total,rows from paged x;
 return jsonb_build_object('contract_version','cp7.attendance-entry.v1','date_from',start_date,'date_to',end_date,'source_token',cp7_attendance.source_token(cid,start_date,end_date),'contractor',jsonb_build_object('id',c.id,'name',c.contractor_name,'active_now',c.is_active,'attendance_required',c.attendance_required),'period',case when pid is null then null else cp7_attendance.period_document(pid) end,'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',lim,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_attendance_entry_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_attendance.entry_workspace(p_query)$$;
alter function cp7_attendance.entry_workspace(jsonb) owner to cp7_attendance_read;
grant create on schema public to cp7_attendance_read;
alter function public.erp_cp7_get_attendance_entry_v1(jsonb) owner to cp7_attendance_read;
revoke create on schema public from cp7_attendance_read;
revoke all on function cp7_attendance.entry_workspace(jsonb) from public,anon,authenticated,service_role,cp7_capture,cp7_roster_write,cp7_attendance_write;
revoke all on function public.erp_cp7_get_attendance_entry_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_attendance_entry_v1(jsonb) to authenticated;
