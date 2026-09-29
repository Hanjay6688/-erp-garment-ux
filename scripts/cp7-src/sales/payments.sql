-- Source-bound cash receipt reader and immutable command validation.
-- This increment supports ordinary cash/bank payments only. Opening advances
-- and allocation replacements retain their separate accepted native workflows.
grant select on erp.cash_accounts to cp7_sales_read;

create function cp7_sales.validate_payment(p jsonb,p_reverse boolean) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare k text;allowed text[];
begin
 allowed:=array['sale_id','review_token','change_reason']||case when p_reverse then array['payment_id'] else array['payment_number','payment_date','amount','cash_account_id','payment_method','reference_number','notes'] end;
 if jsonb_typeof(p) is distinct from 'object' or not p ?& allowed or exists(select 1 from jsonb_object_keys(p) x where not x=any(allowed)) then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
 foreach k in array allowed loop
  if k in('notes','reference_number') then
   if jsonb_typeof(p->k) not in('string','null') or length(p->>k)>case when k='notes' then 2000 else 100 end then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
  elsif jsonb_typeof(p->k) is distinct from 'string' then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
 end loop;
 if (p->>'sale_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p->>'review_token')!~'^[a-f0-9]{32}$' or length(btrim(p->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
 if p_reverse then
  if (p->>'payment_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
 else
  if length(btrim(p->>'payment_number')) not between 1 and 60
   or(p->>'amount')!~'^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$' or(p->>'amount')::numeric<=0
   or(p->>'cash_account_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(p->>'payment_method') not in('CASH','BANK_TRANSFER')
   or length(p->>'payment_date') not between 20 and 40 or(p->>'payment_date')!~'(Z|[+-][0-9]{2}:[0-9]{2})$' then raise exception 'CP7_SALES_PAYMENT_FIELDS';end if;
 end if;
end $$;

create function cp7_sales.cash_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare h erp.sales_headers;ident uuid;po integer;pn integer;bo integer;bn integer;q text;payments jsonb;banks jsonb;pt bigint;bt bigint;can_create boolean;
begin
 if not cp7_sales.access_now() or not erp.has_permission('sales.payment.view') then raise exception using errcode='42501',message='CP7_SALES_CASH_DENIED';end if;
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ? 'sale_id'
  or exists(select 1 from jsonb_object_keys(p_query) x where x not in('sale_id','payment_offset','payment_limit','bank_q','bank_offset','bank_limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','bank_q') and jsonb_typeof(e.value)<>'string')
  or exists(select 1 from jsonb_each(p_query) e where e.key in('payment_offset','payment_limit','bank_offset','bank_limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_CASH_QUERY';end if;
 ident:=(p_query->>'sale_id')::uuid;po:=coalesce((p_query->>'payment_offset')::integer,0);pn:=coalesce((p_query->>'payment_limit')::integer,25);bo:=coalesce((p_query->>'bank_offset')::integer,0);bn:=coalesce((p_query->>'bank_limit')::integer,25);q:=btrim(coalesce(p_query->>'bank_q',''));
 if ident is null or po not between 0 and 1000000 or bo not between 0 and 1000000 or pn not between 1 and 100 or bn not between 1 and 100 or length(q)>120 then raise exception 'CP7_SALES_CASH_QUERY';end if;
 select * into h from erp.sales_headers where id=ident;if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;
 select count(*) into pt from erp.sales_payments where sale_id=ident;
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.payment_number,'physical_at',x.payment_date,'amount',x.amount::text,'cash_account_id',x.cash_account_id,'cash_account_name',(select cash_account_name from erp.cash_accounts where id=x.cash_account_id),'method',x.payment_method,'reference',x.reference_number,'notes',x.notes,'status',x.status,'replaces_payment_id',x.replaces_payment_id) order by x.payment_date desc,x.id),'[]') into payments
 from(select * from erp.sales_payments where sale_id=ident order by payment_date desc,id limit pn offset po)x;
 can_create:=erp.has_permission('sales.payment.create') and erp.has_permission('sales.payment.post');
 with eligible as materialized(select id,cash_account_code,cash_account_name,account_kind from erp.cash_accounts where is_active and can_create and(q='' or strpos(lower(concat_ws(' ',cash_account_code,cash_account_name)),lower(q))>0)),
 sliced as(select * from eligible order by cash_account_code,id limit bn offset bo)
 select(select count(*) from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',cash_account_code,'name',cash_account_name,'kind',account_kind) order by cash_account_code,id) from sliced),'[]') into bt,banks;
 return jsonb_build_object('contract_version','cp7.sales-cash.v1','sale_id',ident,'row_version',h.row_version::text,'review_token',cp7_sales.review_token(ident),
  'payments',jsonb_build_object('rows',payments,'total',pt::text,'offset',po,'limit',pn,'next_offset',case when po+jsonb_array_length(payments)<pt then po+jsonb_array_length(payments) else null end),
  'cash_accounts',jsonb_build_object('rows',banks,'total',bt::text,'offset',bo,'limit',bn,'next_offset',case when bo+jsonb_array_length(banks)<bt then bo+jsonb_array_length(banks) else null end));
end $$;
create function public.erp_cp7_get_sales_cash_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_sales.cash_workspace(p_query)$$;
alter function cp7_sales.validate_payment(jsonb,boolean) owner to cp7_sales_read;
alter function cp7_sales.cash_workspace(jsonb) owner to cp7_sales_read;
grant create on schema public to cp7_sales_read;
alter function public.erp_cp7_get_sales_cash_v1(jsonb) owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on function cp7_sales.validate_payment(jsonb,boolean),cp7_sales.cash_workspace(jsonb),public.erp_cp7_get_sales_cash_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function cp7_sales.validate_payment(jsonb,boolean) to cp7_sales_write;
grant execute on function public.erp_cp7_get_sales_cash_v1(jsonb) to authenticated;
