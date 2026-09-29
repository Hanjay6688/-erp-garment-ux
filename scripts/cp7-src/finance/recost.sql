-- Queue control delegates all costing, propagation and posting to the accepted
-- native processor. A batch is an upper bound, never a promise of selected IDs.
create role cp7_recost_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_recost_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_recost authorization cp7_recost_read;
revoke all on schema cp7_recost from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_recost to cp7_recost_write;
grant usage on schema erp,auth to cp7_recost_read,cp7_recost_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_recost_read,cp7_recost_write;
grant select on erp.cost_recalc_queue,erp.production_orders to cp7_recost_read;
grant execute on function erp.process_cost_recalc_queue(integer) to cp7_recost_write;
create table cp7_recost.requests(actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id));
alter table cp7_recost.requests owner to cp7_recost_write;
alter table cp7_recost.requests enable row level security;
revoke all on cp7_recost.requests from public,anon,authenticated,service_role,cp7_capture,cp7_recost_read;

create function cp7_recost.access_now(p_write boolean) returns void
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if p_write is null or auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_RECOST_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.hpp.view') or(p_write and not erp.has_permission('finance.hpp.manage')) then raise exception using errcode='42501',message='CP7_RECOST_ACCESS_DENIED';end if;
 if p_write and coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN','STAFF') then raise exception using errcode='42501',message='CP7_RECOST_NATIVE_ROLE_REQUIRED';end if;
end $$;

create function cp7_recost.workspace(p_offset integer) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare totals jsonb;rows jsonb;n bigint;
begin
 perform cp7_recost.access_now(false);
 if p_offset is null or p_offset<0 or p_offset>1000000 then raise exception 'CP7_RECOST_QUERY';end if;
 select jsonb_build_object('pending',count(*) filter(where status='PENDING')::text,'running',count(*) filter(where status='RUNNING')::text,
  'failed',count(*) filter(where status='FAILED')::text,'done',count(*) filter(where status='DONE')::text,
  'eligible',count(*) filter(where status='PENDING' or(status='FAILED' and attempt_count<3 and coalesce(next_attempt_at,statement_timestamp())<=statement_timestamp()))::text,
  'exhausted',count(*) filter(where status='FAILED' and attempt_count>=3)::text) into totals from erp.cost_recalc_queue;
 select count(*) into n from erp.cost_recalc_queue where status<>'DONE';
 select coalesce(jsonb_agg(x.row order by x.queued_at,x.id),'[]') into rows from(
  select q.queued_at,q.id,jsonb_build_object('id',q.id::text,'entity_type',q.entity_type,'entity_id',q.entity_id,'po_number',p.po_number,
   'status',q.status,'reason',q.reason,'recalc_from',q.recalc_from,'queued_at',q.queued_at,'attempt_count',q.attempt_count,
   'next_attempt_at',q.next_attempt_at,'error_message',left(q.error_message,2000),'error_truncated',coalesce(length(q.error_message)>2000,false),
   'eligible',q.status='PENDING' or(q.status='FAILED' and q.attempt_count<3 and coalesce(q.next_attempt_at,statement_timestamp())<=statement_timestamp())) row
  from erp.cost_recalc_queue q left join erp.production_orders p on q.entity_type='PO' and p.id=q.entity_id
  where q.status<>'DONE' order by q.queued_at,q.id limit 25 offset p_offset
 )x;
 return jsonb_build_object('contract_version','cp7.recost-queue.v1','captured_at',statement_timestamp(),'scope','CURRENT_QUEUE_ALL_ENTITIES',
  'batch_semantics','AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS','counts',totals,
  'page',jsonb_build_object('rows',rows,'total',n::text,'offset',p_offset,'limit',25,'next_offset',case when p_offset+jsonb_array_length(rows)<n then p_offset+jsonb_array_length(rows) end));
end $$;

create function cp7_recost.command(p_payload jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare actor_id uuid;saved cp7_recost.requests;completed integer;outcome jsonb;
begin
 perform cp7_recost.access_now(true);actor_id:=auth.uid();
 if p_request is null or jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& array['limit','reason']
  or exists(select 1 from jsonb_object_keys(p_payload)k where k not in('limit','reason'))
  or p_payload->'limit' is distinct from '20'::jsonb or jsonb_typeof(p_payload->'reason') is distinct from 'string'
  or length(btrim(p_payload->>'reason')) not between 1 and 1000 then raise exception 'CP7_RECOST_COMMAND';end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('cp7.recost.request:'||actor_id::text||':'||p_request::text,0));
 perform cp7_recost.access_now(true);
 select * into saved from cp7_recost.requests where actor=actor_id and request_id=p_request;
 if found then
  if saved.payload<>p_payload then raise exception 'CP7_RECOST_REQUEST_CHANGED';end if;
  if saved.response is null then raise exception 'CP7_RECOST_REQUEST_INCOMPLETE';end if;
  return saved.response;
 end if;
 insert into cp7_recost.requests(actor,request_id,payload) values(actor_id,p_request,p_payload);
 completed:=erp.process_cost_recalc_queue(20);
 perform cp7_recost.access_now(true);
 if completed is null or completed<0 or completed>20 then raise exception 'CP7_RECOST_OUTCOME';end if;
 outcome:=jsonb_build_object('contract_version','cp7.recost-outcome.v1','kind','COMMITTED_OUTCOME','action','PROCESS_ELIGIBLE',
  'request_id',p_request,'limit',20,'completed',completed,'processed_at',statement_timestamp(),
  'batch_semantics','AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS','queue_after',cp7_recost.workspace(0));
 update cp7_recost.requests set response=outcome where actor=actor_id and request_id=p_request;
 return outcome;
end $$;

create function public.erp_cp7_get_recost_queue_v1(p_offset integer default 0) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_recost.workspace(p_offset)$$;
create function public.erp_cp7_process_recost_v1(p_payload jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_recost.command(p_payload,p_request)$$;
grant create on schema public to cp7_recost_read,cp7_recost_write;
alter function cp7_recost.access_now(boolean) owner to cp7_recost_read;
alter function cp7_recost.workspace(integer) owner to cp7_recost_read;
alter function cp7_recost.command(jsonb,uuid) owner to cp7_recost_write;
alter function public.erp_cp7_get_recost_queue_v1(integer) owner to cp7_recost_read;
alter function public.erp_cp7_process_recost_v1(jsonb,uuid) owner to cp7_recost_write;
revoke create on schema public,cp7_recost from cp7_recost_read,cp7_recost_write;
revoke all on all functions in schema cp7_recost from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_recost.access_now(boolean),cp7_recost.workspace(integer) to cp7_recost_write;
revoke all on function public.erp_cp7_get_recost_queue_v1(integer),public.erp_cp7_process_recost_v1(jsonb,uuid) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_recost_queue_v1(integer),public.erp_cp7_process_recost_v1(jsonb,uuid) to authenticated;
