-- P11 reviewed draft transitions. Business effects remain accepted native calls.
create role cp7_sales_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_sales,auth to cp7_sales_write;
grant execute on function auth.uid() to cp7_sales_write;
create table cp7_sales.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id));
create table cp7_sales.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,sale_id uuid,action text not null check(action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')),primary key(backend_pid,transaction_id));
alter table cp7_sales.requests owner to cp7_sales_write;
alter table cp7_sales.command_context owner to cp7_sales_write;
alter table cp7_sales.requests enable row level security;
alter table cp7_sales.command_context enable row level security;
revoke all on cp7_sales.requests,cp7_sales.command_context from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;

create function cp7_sales.command_access(p_action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 -- Read the complete current access once per invocation. access_now() already
 -- obtains that same document; invoking it here and then reading it again
 -- multiplies full permission-list reads in each native account/HPP guard.
 -- This is never a command/transaction cache: every post-wait guard invocation
 -- still reads current authority and calls the native fine permission checks.
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if not erp.has_permission('finance.ar.view') or p_action is null or p_action not in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' when p_action='CREATE' then 'sales.invoice.create' when p_action='PAYMENT' then 'sales.payment.create' when p_action='PAYMENT_REVERSE' then 'sales.payment.reverse' when p_action='RETURN' then 'sales.return.create' when p_action='RETURN_REVERSE' then 'sales.return.reverse' when p_action='SALE_REVERSE' then 'sales.invoice.reverse' else 'sales.invoice.edit_draft' end)
  or(p_action in('PAYMENT','PAYMENT_REVERSE') and not erp.has_permission('sales.payment.view'))
  or(p_action='PAYMENT' and not erp.has_permission('sales.payment.post'))
  or(p_action in('RETURN','RETURN_REVERSE') and not erp.has_permission('sales.return.view'))
  or(p_action='RETURN' and not erp.has_permission('sales.return.post'))
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 if p_action in('PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE') and coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_SALES_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $$;

-- require_internal only needs an authorization decision. Rebuilding the full
-- profile/permission-list document for every Native account lookup multiplied
-- that read thousands of times in one historical correction. Keep the complete
-- command_access document at every owning command and post-wait comparison.
-- This private admission still reads Native current permissions on every call:
-- there is no request/transaction cache, GUC capability or stored authority.
create function cp7_sales.command_allowed(p_action text) returns boolean
language plpgsql stable security invoker set search_path='' as $$
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 -- Native has_permission's positive invoice-view result also requires the
 -- same unique active app user and active role as get_my_access.allowed.
 if not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if not erp.has_permission('finance.ar.view') or p_action is null or p_action not in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' when p_action='CREATE' then 'sales.invoice.create' when p_action='PAYMENT' then 'sales.payment.create' when p_action='PAYMENT_REVERSE' then 'sales.payment.reverse' when p_action='RETURN' then 'sales.return.create' when p_action='RETURN_REVERSE' then 'sales.return.reverse' when p_action='SALE_REVERSE' then 'sales.invoice.reverse' else 'sales.invoice.edit_draft' end)
  or(p_action in('PAYMENT','PAYMENT_REVERSE') and not erp.has_permission('sales.payment.view'))
  or(p_action='PAYMENT' and not erp.has_permission('sales.payment.post'))
  or(p_action in('RETURN','RETURN_REVERSE') and not erp.has_permission('sales.return.view'))
  or(p_action='RETURN' and not erp.has_permission('sales.return.post'))
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 if p_action in('PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE') and coalesce(erp.current_app_role(),'') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_SALES_OWNER_ADMIN_REQUIRED';end if;
 return true;
end $$;

create function cp7_sales.apply_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;h erp.sales_headers;r jsonb;ident uuid:=(p_payload->>'sale_id')::uuid;native_request uuid;payment_id uuid;payment erp.sales_payments;return_id uuid;returned erp.sales_returns;line jsonb;allocation record;
begin
 a:=cp7_sales.command_access(p_action);
 if not exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and actor=auth.uid() and sale_id is not distinct from ident and action=p_action)
 then raise exception using errcode='42501',message='CP7_SALES_PRIVATE_CONTEXT_REQUIRED';end if;
 -- Follow the native FG lock order, then recheck both authority and the exact
 -- document including child prices/allocations, not just its header revision.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if p_action<>'CREATE' then
 -- Native cash functions lock payment before invoice. Preserve that order
 -- while the shared FG lock serializes ordinary invoice/return adapters.
 if p_action in('PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE') then perform 1 from erp.sales_payments where sale_id=ident order by id for update;end if;
 if p_action in('RETURN','RETURN_REVERSE','SALE_REVERSE') then perform 1 from erp.sales_returns where sale_id=ident order by id for update;end if;
 select * into h from erp.sales_headers where id=ident for update;
 if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;
 perform 1 from erp.sales_items where sale_id=ident order by id for update;
 perform 1 from erp.sale_stock_allocations x where exists(select 1 from erp.sales_items i where i.id=x.sale_item_id and i.sale_id=ident) order by x.id for update;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if h.row_version::text is distinct from p_expected or cp7_sales.review_token(ident) is distinct from p_payload->>'review_token' then raise exception 'CP7_SALES_REVIEW_CHANGED';end if;
 if p_action in('EDIT','POST','CANCEL') and h.status<>'DRAFT' then raise exception 'CP7_SALES_DRAFT_ONLY';end if;
 if p_action in('PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE') and h.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'CP7_SALES_ACTIVE_ONLY';end if;
 end if;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 perform set_config('app.change_reason',btrim(p_payload->>'change_reason'),true);
 native_request:=md5(auth.uid()::text||':'||p_action||':'||p_request::text)::uuid;
 if p_action in('CREATE','EDIT') then
  perform cp7_sales.validate_draft(p_payload,p_action='EDIT');
  perform 1 from erp.products where id in(select (value->>'product_id')::uuid from jsonb_array_elements(p_payload->'items')) order by id for share;
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x where not exists(select 1 from erp.products p where p.id=(x->>'product_id')::uuid and p.is_active)) then raise exception 'CP7_SALES_PRODUCT_UNAVAILABLE';end if;
  perform 1 from erp.customers where id=(p_payload->>'customer_id')::uuid for share;
  perform 1 from erp.locations where id=(p_payload->>'source_location_id')::uuid for share;
  if (p_payload->>'sale_date')::timestamptz>statement_timestamp() then raise exception 'CP7_SALES_FUTURE_DATE';end if;
  r:=erp.save_sale_draft_v2((p_payload-'review_token'-'change_reason')||jsonb_build_object('reason',btrim(p_payload->>'change_reason')),native_request,p_expected::bigint);
  ident:=(r->>'sale_id')::uuid;
 elsif p_action='PAYMENT' then
  perform 1 from erp.cash_accounts where id=(p_payload->>'cash_account_id')::uuid for share;
  if not exists(select 1 from erp.cash_accounts where id=(p_payload->>'cash_account_id')::uuid and is_active) then raise exception 'CP7_SALES_CASH_UNAVAILABLE';end if;
  if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
  insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
  values(ident,btrim(p_payload->>'payment_number'),(p_payload->>'payment_date')::timestamptz,(p_payload->>'amount')::numeric,(p_payload->>'cash_account_id')::uuid,p_payload->>'payment_method',p_payload->>'reference_number',p_payload->>'notes','DRAFT',erp.current_app_user_id()) returning id into payment_id;
  perform erp.post_sales_payment(payment_id);
 elsif p_action='PAYMENT_REVERSE' then
  payment_id:=(p_payload->>'payment_id')::uuid;select * into payment from erp.sales_payments where id=payment_id;
  if payment.id is null or payment.sale_id<>ident or payment.status<>'POSTED' then raise exception 'CP7_SALES_PAYMENT_SOURCE_CHANGED';end if;
  perform erp.reverse_sales_payment(payment_id,btrim(p_payload->>'change_reason'));
 elsif p_action='RETURN' then
  if(p_payload->>'physical_at')::timestamptz>statement_timestamp() then raise exception 'CP7_SALES_RETURN_FUTURE_DATE';end if;
  perform 1 from erp.locations where id in(select (value->>'location_id')::uuid from jsonb_array_elements(p_payload->'items')) order by id for share;
  if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
  insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
  values(btrim(p_payload->>'return_number'),ident,h.customer_id,(p_payload->>'physical_at')::timestamptz,p_payload->>'notes','DRAFT',erp.current_app_user_id()) returning id into return_id;
  for line in select value from jsonb_array_elements(p_payload->'items') loop
   select a.id,a.lot_id,i.product_id into allocation from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where a.id=(line->>'allocation_id')::uuid and i.sale_id=ident;
   if not found then raise exception 'CP7_SALES_RETURN_ALLOCATION_CHANGED';end if;
   insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
   values(return_id,allocation.id,allocation.product_id,allocation.lot_id,(line->>'location_id')::uuid,(line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes');
  end loop;
  perform erp.post_sales_return(return_id);
 elsif p_action='RETURN_REVERSE' then
  return_id:=(p_payload->>'return_id')::uuid;select * into returned from erp.sales_returns where id=return_id;
  if returned.id is null or returned.sale_id<>ident or returned.status<>'POSTED' then raise exception 'CP7_SALES_RETURN_SOURCE_CHANGED';end if;
  perform erp.reverse_sales_return(return_id,btrim(p_payload->>'change_reason'));
 elsif p_action='SALE_REVERSE' then
  perform erp.reverse_sale(ident,btrim(p_payload->>'change_reason'));
  select jsonb_build_object('status',status,'row_version',row_version::text) into r from erp.sales_headers where id=ident;
 elsif p_action='POST' then r:=erp.post_sale_v2(ident,native_request,p_expected::bigint);
 else r:=erp.cancel_sale_draft_v2(ident,btrim(p_payload->>'change_reason'),native_request,p_expected::bigint);end if;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if p_action in('PAYMENT','PAYMENT_REVERSE') then
  select * into h from erp.sales_headers where id=ident;select * into payment from erp.sales_payments where id=payment_id;
  return jsonb_build_object('sale_id',ident,'status',h.status,'row_version',h.row_version::text,'payment_id',payment.id,'payment_status',payment.status);
 end if;
 if p_action in('RETURN','RETURN_REVERSE') then
  select * into h from erp.sales_headers where id=ident;select * into returned from erp.sales_returns where id=return_id;
  return jsonb_build_object('sale_id',ident,'status',h.status,'row_version',h.row_version::text,'return_id',returned.id,'return_status',returned.status);
 end if;
 return jsonb_build_object('sale_id',ident,'status',r->'status','row_version',r->>'row_version');
end $$;

create function cp7_sales.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_sales.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_sales.command_access(p_action);
 if p_request is null or (p_action='CREATE' and p_expected is not null) or(p_action<>'CREATE' and(p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$')) then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 if p_action in('CREATE','EDIT') then
  perform cp7_sales.validate_draft(p_payload,p_action='EDIT');
 elsif p_action in('PAYMENT','PAYMENT_REVERSE') then
  perform cp7_sales.validate_payment(p_payload,p_action='PAYMENT_REVERSE');
 elsif p_action in('RETURN','RETURN_REVERSE') then
  perform cp7_sales.validate_return(p_payload,p_action='RETURN_REVERSE');
 else
  if jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& array['sale_id','review_token','change_reason']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('sale_id','review_token','change_reason') or jsonb_typeof(e.value)<>'string')
   or coalesce(p_payload->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or coalesce(p_payload->>'review_token','')!~'^[a-f0-9]{32}$'
   or length(btrim(p_payload->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 end if;
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
alter function cp7_sales.command_allowed(text) owner to cp7_sales_read;
alter function cp7_sales.apply_command(text,jsonb,uuid,text) owner to postgres;
alter function cp7_sales.command(text,jsonb,uuid,text) owner to cp7_sales_write;
grant create on schema public to cp7_sales_write;
alter function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) owner to cp7_sales_write;
revoke create on schema public from cp7_sales_write;
revoke all on function cp7_sales.command_access(text),cp7_sales.apply_command(text,jsonb,uuid,text),cp7_sales.command(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
revoke all on function cp7_sales.command_allowed(text) from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function cp7_sales.command_access(text),cp7_sales.apply_command(text,jsonb,uuid,text),cp7_sales.validate_draft(jsonb,boolean) to cp7_sales_write;
grant usage on schema cp7_sales to postgres;
grant select on cp7_sales.command_context to postgres;
grant execute on function cp7_sales.command_access(text),cp7_sales.review_token(uuid) to postgres;
grant execute on function cp7_sales.command_allowed(text) to postgres;
revoke all on function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text) to authenticated;
