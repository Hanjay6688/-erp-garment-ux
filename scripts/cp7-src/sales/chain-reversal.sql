-- One explicitly reviewed sale/payment/return cancellation transaction.
-- Reuse the admitted owning commands. No Native helper or guard is replaced.
create schema cp7_sales_chain authorization cp7_sales_read;
revoke all on schema cp7_sales_chain from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_sales_chain to postgres,cp7_sales_write;
create table cp7_sales_chain.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 expected_version text not null,response jsonb,primary key(actor,request_id)
);
create table cp7_sales_chain.history(
 actor uuid not null,request_id uuid not null,sale_id uuid not null references erp.sales_headers,
 reviewed_source jsonb not null,steps jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id),unique(sale_id)
);
alter table cp7_sales_chain.requests owner to postgres;
alter table cp7_sales_chain.history owner to postgres;
alter table cp7_sales_chain.requests enable row level security;
alter table cp7_sales_chain.history enable row level security;
create policy private_requests on cp7_sales_chain.requests for all using(false)with check(false);
create policy private_history on cp7_sales_chain.history for all using(false)with check(false);
revoke all on all tables in schema cp7_sales_chain from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_sales_chain.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_sales.command_access('SALE_REVERSE');
 if cp7_sales.command_access('PAYMENT_REVERSE')is distinct from a
  or cp7_sales.command_access('RETURN_REVERSE')is distinct from a
  or erp.has_permission('finance.hpp.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_SALES_CHAIN_DENIED';end if;
 return a;
end $$;

create function cp7_sales_chain.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_SALES_CHAIN_HISTORY_IMMUTABLE';end $$;
create trigger immutable_history before update or delete on cp7_sales_chain.history
 for each row execute function cp7_sales_chain.immutable();
create trigger immutable_history_truncate before truncate on cp7_sales_chain.history
 for each statement execute function cp7_sales_chain.immutable();

create function cp7_sales_chain.snapshot(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('sale_id',h.id,'number',h.sale_number,'status',h.status,
  'row_version',h.row_version::text,'review_token',cp7_sales.review_token(h.id),
  'payments',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'number',p.payment_number,
   'physical_at',p.payment_date,'amount',p.amount::text)order by p.payment_date desc,p.id)
   from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),'[]'),
  'returns',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'number',r.return_number,
   'physical_at',r.physical_at,'line_count',(select count(*)::text from erp.sales_return_items i where i.return_id=r.id))
   order by r.physical_at desc,r.id)from erp.sales_returns r where r.sale_id=h.id and r.status='POSTED'),'[]'),
  'pending_children',coalesce((select jsonb_agg(x order by x->>'kind',x->>'id')from(
   select jsonb_build_object('kind','PAYMENT','id',p.id,'number',p.payment_number)as x
    from erp.sales_payments p where p.sale_id=h.id and p.status='DRAFT'
   union all select jsonb_build_object('kind','RETURN','id',r.id,'number',r.return_number)
    from erp.sales_returns r where r.sale_id=h.id and r.status='DRAFT')pending),'[]'))
 from erp.sales_headers h where h.id=p_sale
$$;

create function cp7_sales_chain.token(p_sale uuid)returns text
language sql stable security definer set search_path=''as $$
 select md5(jsonb_build_object('source',cp7_sales_chain.snapshot(h.id),
  'header',to_jsonb(h),
  'payments',(select jsonb_agg(to_jsonb(p)order by p.id)from erp.sales_payments p where p.sale_id=h.id),
  'returns',(select jsonb_agg(to_jsonb(r)order by r.id)from erp.sales_returns r where r.sale_id=h.id),
  'return_items',(select jsonb_agg(to_jsonb(i)order by i.id)from erp.sales_return_items i
   where exists(select 1 from erp.sales_returns r where r.id=i.return_id and r.sale_id=h.id)),
  'stock',(select jsonb_agg(to_jsonb(m)order by m.id)from erp.fg_stock_movements m where exists(
   select 1 from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
   where i.sale_id=h.id and a.lot_id=m.lot_id)),
  'hpp',(select jsonb_agg(to_jsonb(v)order by v.id)from erp.hpp_versions v where v.is_current and exists(
   select 1 from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
   where i.sale_id=h.id and a.lot_id=v.lot_id)),
  'cash',(select jsonb_agg(to_jsonb(c)order by c.id)from erp.cash_accounts c where exists(
   select 1 from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'and p.cash_account_id=c.id)),
  'accounts',(select jsonb_agg(to_jsonb(c)order by c.id)from erp.chart_accounts c where c.id in(
   select account_id from erp.accounting_account_mappings union select coa_account_id from erp.cash_accounts
    where id in(select cash_account_id from erp.sales_payments where sale_id=h.id and status='POSTED'))),
  'mappings',(select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m),
  'period',(select jsonb_agg(to_jsonb(c))from erp.accounting_period_control c))::text)
 from erp.sales_headers h where h.id=p_sale
$$;

create function cp7_sales_chain.workspace(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;source jsonb;
begin
 a:=cp7_sales_chain.access_now();source:=cp7_sales_chain.snapshot(p_sale);
 if source is null then raise exception 'CP7_SALES_CHAIN_NOT_FOUND';end if;
 if cp7_sales_chain.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sales-chain-workspace.v1','captured_at',clock_timestamp(),
  'source',source,'chain_token',cp7_sales_chain.token(p_sale),
  'eligible',source->>'status'in('POSTED','PARTIAL_PAID','PAID')and jsonb_array_length(source->'pending_children')=0);
end $$;

create function cp7_sales_chain.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
declare key text;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['sale_id','review_token','chain_token','payment_ids','return_ids','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>6
  or jsonb_typeof(p->'sale_id')is distinct from'string'
  or coalesce(p->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'chain_token')is distinct from'string'or coalesce(p->>'chain_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_SALES_CHAIN_FIELDS';end if;
 foreach key in array array['payment_ids','return_ids']loop
  if jsonb_typeof(p->key)is distinct from'array'then raise exception 'CP7_SALES_CHAIN_FIELDS';end if;
  if exists(select 1 from jsonb_array_elements(p->key)x where jsonb_typeof(x)is distinct from'string'
   or (x#>>'{}')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
   or(select count(*)from jsonb_array_elements(p->key))<>(select count(distinct lower(x#>>'{}'))from jsonb_array_elements(p->key)x)then
   raise exception 'CP7_SALES_CHAIN_FIELDS';end if;
 end loop;
end $$;

create function cp7_sales_chain.command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_sales_chain.requests;h erp.sales_headers;source jsonb;payments jsonb;returns jsonb;
 child jsonb;intent jsonb;result jsonb;steps jsonb:='[]';child_request uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_sales_chain.access_now();perform cp7_sales_chain.validate(p);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_SALES_CHAIN_FIELDS';end if;
 insert into cp7_sales_chain.requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_sales_chain.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_SALES_CHAIN_REQUEST_CHANGED';end if;
 if cp7_sales_chain.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 -- Acquire the same FG/payment/return/header order as the owning adapter.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.sales_payments where sale_id=(p->>'sale_id')::uuid order by id for update;
 perform 1 from erp.sales_returns where sale_id=(p->>'sale_id')::uuid order by id for update;
 select *into h from erp.sales_headers where id=(p->>'sale_id')::uuid for update;
 if h.id is null then raise exception 'CP7_SALES_CHAIN_NOT_FOUND';end if;
 perform 1 from erp.sales_items where sale_id=h.id order by id for update;
 perform 1 from erp.sale_stock_allocations x where exists(select 1 from erp.sales_items i where i.id=x.sale_item_id and i.sale_id=h.id)order by x.id for update;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts c where exists(select 1 from erp.sales_payments x where x.sale_id=h.id and x.status='POSTED'and x.cash_account_id=c.id)order by c.id for share;
 perform 1 from erp.chart_accounts c where c.id in(select coa_account_id from erp.cash_accounts
  where id in(select cash_account_id from erp.sales_payments where sale_id=h.id and status='POSTED')
  union select account_id from erp.accounting_account_mappings)order by c.id for share;
 -- Recheck the complete reviewed source only after every possible wait.
 if cp7_sales_chain.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 source:=cp7_sales_chain.snapshot(h.id);
 if h.row_version::text is distinct from p_expected or source->>'review_token'is distinct from p->>'review_token'
  or cp7_sales_chain.token(h.id)is distinct from p->>'chain_token'then raise exception 'CP7_SALES_CHAIN_STALE_REVIEW';end if;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_SALES_ACTIVE_ONLY';end if;
 if jsonb_array_length(source->'pending_children')<>0 then raise exception 'CP7_SALES_CHAIN_PENDING_CHILD';end if;
 select coalesce(jsonb_agg(x->'id'order by ordinal),'[]')into payments from jsonb_array_elements(source->'payments')with ordinality e(x,ordinal);
 select coalesce(jsonb_agg(x->'id'order by ordinal),'[]')into returns from jsonb_array_elements(source->'returns')with ordinality e(x,ordinal);
 if payments is distinct from p->'payment_ids'or returns is distinct from p->'return_ids'then raise exception 'CP7_SALES_CHAIN_CHILDREN_CHANGED';end if;
 -- Every nested receipt has a deterministic distinct key. All are committed
 -- with the outer receipt or rolled back with it, including the final sale.
 for child in select value from jsonb_array_elements(source->'payments')loop
  select *into strict h from erp.sales_headers where id=h.id;
  intent:=jsonb_build_object('sale_id',h.id,'review_token',cp7_sales.review_token(h.id),'payment_id',child->>'id','change_reason',btrim(p->>'change_reason'));
  child_request:=md5(auth.uid()::text||':SALE_CHAIN:'||p_request::text||':PAYMENT:'||(child->>'id'))::uuid;
  result:=public.erp_cp7_save_sale_v1('PAYMENT_REVERSE',intent,child_request,h.row_version::text);
  steps:=steps||jsonb_build_array(jsonb_build_object('action','PAYMENT_REVERSE','id',child->>'id','status',result->>'payment_status'));
 end loop;
 for child in select value from jsonb_array_elements(source->'returns')loop
  select *into strict h from erp.sales_headers where id=h.id;
  intent:=jsonb_build_object('sale_id',h.id,'review_token',cp7_sales.review_token(h.id),'return_id',child->>'id','change_reason',btrim(p->>'change_reason'));
  child_request:=md5(auth.uid()::text||':SALE_CHAIN:'||p_request::text||':RETURN:'||(child->>'id'))::uuid;
  result:=public.erp_cp7_save_sale_v1('RETURN_REVERSE',intent,child_request,h.row_version::text);
  steps:=steps||jsonb_build_array(jsonb_build_object('action','RETURN_REVERSE','id',child->>'id','status',result->>'return_status'));
 end loop;
 select *into strict h from erp.sales_headers where id=h.id;
 intent:=jsonb_build_object('sale_id',h.id,'review_token',cp7_sales.review_token(h.id),'change_reason',btrim(p->>'change_reason'));
 child_request:=md5(auth.uid()::text||':SALE_CHAIN:'||p_request::text||':SALE:'||h.id::text)::uuid;
 result:=public.erp_cp7_save_sale_v1('SALE_REVERSE',intent,child_request,h.row_version::text);
 steps:=steps||jsonb_build_array(jsonb_build_object('action','SALE_REVERSE','id',h.id,'status',result->>'status'));
 if result->>'status'is distinct from'REVERSED'or exists(select 1 from jsonb_array_elements(steps)x where x->>'status'is distinct from'REVERSED')then
  raise exception 'CP7_SALES_CHAIN_INCOMPLETE';end if;
 if cp7_sales_chain.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 insert into cp7_sales_chain.history(actor,request_id,sale_id,reviewed_source,steps,reason)
  values(auth.uid(),p_request,h.id,source,steps,btrim(p->>'change_reason'));
 result:=jsonb_build_object('contract_version','cp7.sales-chain-outcome.v1','kind','COMMITTED_OUTCOME',
  'action','SALE_CHAIN_REVERSE','request_id',p_request,'sale_id',h.id,'status','REVERSED',
  'row_version',result->>'row_version','steps',steps);
 update cp7_sales_chain.requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $$;

create function public.erp_cp7_get_sales_chain_v1(p_sale uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_sales_chain.workspace(p_sale)$$;
create function public.erp_cp7_reverse_sales_chain_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_sales_chain.command(p_payload,p_request,p_expected)$$;
alter function cp7_sales_chain.access_now()owner to postgres;
alter function cp7_sales_chain.immutable()owner to postgres;
alter function cp7_sales_chain.snapshot(uuid)owner to postgres;
alter function cp7_sales_chain.token(uuid)owner to postgres;
alter function cp7_sales_chain.workspace(uuid)owner to postgres;
alter function cp7_sales_chain.validate(jsonb)owner to postgres;
alter function cp7_sales_chain.command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_sales_read,cp7_sales_write;
alter function public.erp_cp7_get_sales_chain_v1(uuid)owner to cp7_sales_read;
alter function public.erp_cp7_reverse_sales_chain_v1(jsonb,uuid,text)owner to cp7_sales_write;
revoke create on schema public from cp7_sales_read,cp7_sales_write;
revoke all on all functions in schema cp7_sales_chain from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant execute on function cp7_sales_chain.workspace(uuid)to cp7_sales_read;
grant execute on function cp7_sales_chain.command(jsonb,uuid,text)to cp7_sales_write;
-- The coordinator's postgres owner is not a superuser. Enter through the
-- existing facade owned by cp7_sales_write so its invoker command retains
-- private request/context ownership. Do not grant postgres private table DML
-- or direct invoker execution; every current-authority and Native guard runs.
grant execute on function public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)to postgres;
revoke all on function public.erp_cp7_get_sales_chain_v1(uuid),public.erp_cp7_reverse_sales_chain_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_sales_chain_v1(uuid),public.erp_cp7_reverse_sales_chain_v1(jsonb,uuid,text)to authenticated;
