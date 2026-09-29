-- P11 reviewed draft transitions. Business effects remain accepted native calls.
create role cp7_sales_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_sales,auth to cp7_sales_write;
grant execute on function auth.uid() to cp7_sales_write;
create table cp7_sales.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,response jsonb,primary key(actor,request_id));
create table cp7_sales.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,sale_id uuid not null,action text not null check(action in('POST','CANCEL')),primary key(backend_pid,transaction_id));
alter table cp7_sales.requests owner to cp7_sales_write;
alter table cp7_sales.command_context owner to cp7_sales_write;
alter table cp7_sales.requests enable row level security;
alter table cp7_sales.command_context enable row level security;
revoke all on cp7_sales.requests,cp7_sales.command_context from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;

create function cp7_sales.command_access(p_action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 if not cp7_sales.access_now() or p_action is null or p_action not in('POST','CANCEL')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' else 'sales.invoice.edit_draft' end)
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 a:=erp.get_my_access_v1();return a;
end $$;

create function cp7_sales.apply_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;h erp.sales_headers;r jsonb;ident uuid:=(p_payload->>'sale_id')::uuid;native_request uuid;
begin
 a:=cp7_sales.command_access(p_action);
 if not exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and actor=auth.uid() and sale_id=ident and action=p_action)
 then raise exception using errcode='42501',message='CP7_SALES_PRIVATE_CONTEXT_REQUIRED';end if;
 -- Follow the native FG lock order, then recheck both authority and the exact
 -- document including child prices/allocations, not just its header revision.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into h from erp.sales_headers where id=ident for update;
 if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;
 perform 1 from erp.sales_items where sale_id=ident order by id for update;
 perform 1 from erp.sale_stock_allocations x where exists(select 1 from erp.sales_items i where i.id=x.sale_item_id and i.sale_id=ident) order by x.id for update;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if h.row_version::text is distinct from p_expected or cp7_sales.review_token(ident) is distinct from p_payload->>'review_token' then raise exception 'CP7_SALES_REVIEW_CHANGED';end if;
 if h.status<>'DRAFT' then raise exception 'CP7_SALES_DRAFT_ONLY';end if;
 perform set_config('app.change_reason',btrim(p_payload->>'change_reason'),true);
 native_request:=md5(auth.uid()::text||':'||p_action||':'||p_request::text)::uuid;
 if p_action='POST' then r:=erp.post_sale_v2(ident,native_request,p_expected::bigint);
 else r:=erp.cancel_sale_draft_v2(ident,btrim(p_payload->>'change_reason'),native_request,p_expected::bigint);end if;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 return jsonb_build_object('sale_id',ident,'status',r->'status','row_version',r->>'row_version');
end $$;

create function cp7_sales.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_sales.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_sales.command_access(p_action);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& array['sale_id','review_token','change_reason']
  or exists(select 1 from jsonb_each(p_payload) e where e.key not in('sale_id','review_token','change_reason') or jsonb_typeof(e.value)<>'string')
  or coalesce(p_payload->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'review_token','')!~'^[a-f0-9]{32}$'
  or length(btrim(p_payload->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 insert into cp7_sales.requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_sales.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_SALES_REQUEST_CHANGED';end if;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),(p_payload->>'sale_id')::uuid,p_action);
 r:=cp7_sales.apply_command(p_action,p_payload,p_request,p_expected);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.sales-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request);
 update cp7_sales.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_save_sale_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_sales.command(p_action,p_payload,p_request,p_expected)$$;
alter function cp7_sales.command_access(text) owner to cp7_sales_read;
alter function cp7_sales.apply_command(text,jsonb,uuid,text) owner to postgres;
alter function cp7_sales.command(text,jsonb,uuid,text) owner to cp7_sales_write;
grant create on schema public to cp7_sales_write;
alter function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) owner to cp7_sales_write;
revoke create on schema public from cp7_sales_write;
revoke all on function cp7_sales.command_access(text),cp7_sales.apply_command(text,jsonb,uuid,text),cp7_sales.command(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_sales.command_access(text),cp7_sales.apply_command(text,jsonb,uuid,text) to cp7_sales_write;
grant usage on schema cp7_sales to postgres;
grant select on cp7_sales.command_context to postgres;
grant execute on function cp7_sales.command_access(text),cp7_sales.review_token(uuid) to postgres;
revoke all on function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) to authenticated;
