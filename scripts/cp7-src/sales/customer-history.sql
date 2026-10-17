-- R3-03 (owner D16-1, 16 Okt 2026: "selesain biar gausa sembunyiin"): Riwayat Pelanggan reads real data.
--
-- One read-only facade, public.erp_cp7_get_customer_history_v1(p_query jsonb), with two modes:
--  * list (no customer_id): customers whose code or name contains q, paged, each with its document counts and, with
--    finance.ar.view, the open balance of its active invoices;
--  * customer (customer_id): the customer, its counts and totals, and its timeline newest first, paged: every invoice
--    (sales_headers), payment (sales_payments), return (sales_returns) and every cancellation of one of them, with the
--    current status of each document and, with finance.ar.view, the amounts. The invoices named on the page come with
--    their current status and, with finance.ar.view, total / returned / paid / balance.
-- The invoice figures are the definitions of cp7_sales.header (scripts/cp7-src/sales/read.sql), which the receivables
-- screen (src/ConnectedReceivablesPage.tsx) shows: gross = sum(line_total); returned = refund of POSTED returns;
-- paid = sum(round(amount,2)) of POSTED payments; net = max(gross - returned, 0); balance = net - paid for an active
-- receivable (POSTED, PARTIAL_PAID, PAID) and none otherwise. A customer's totals add up its active invoices only; opening
-- balances and book adjustments that are not invoices stay in the financial reports, as on the receivables screen.
-- An event's time is the document's own time (sale_date, payment_date, physical_at); a cancellation's time is when the
-- Native audit log (erp.audit_logs, written by the erp.audit_row_change trigger on each of the three tables, system
-- managed) recorded the change of the document's status to CANCELLED / REVERSED. The WIB date is given beside it.
-- Access: sales.history.view to read; amounts only with finance.ar.view (SALES_KASIR has the first, not the second);
-- can_export says whether sales.history.export is held (the screen exports only the rows it shows; no server write).
-- The workspace is STABLE: every statement of one answer reads the same snapshot, so a payment committed while it reads
-- is either wholly in the answer or wholly absent. No business table is written (business_DML false).
create role cp7_customer_history_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_customer_history authorization cp7_customer_history_read;
revoke all on schema cp7_customer_history from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_customer_history to postgres;

create function cp7_customer_history.access_now()returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_access jsonb;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CUSTOMER_HISTORY_DENIED';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed'is distinct from'true'::jsonb or not erp.has_permission('sales.history.view')then
  raise exception using errcode='42501',message='CP7_CUSTOMER_HISTORY_DENIED';end if;
 return jsonb_build_object('financial',erp.has_permission('finance.ar.view'),'export',erp.has_permission('sales.history.export'));
end $$;

-- One row per invoice of the customer, with the figures of cp7_sales.header.
create function cp7_customer_history.invoices(p_customer uuid)
returns table(sale_id uuid,sale_number text,sale_date timestamptz,due_date date,sale_status text,location_id uuid,
 qty_pcs bigint,line_count bigint,gross numeric,returned numeric,paid numeric,net numeric,open_balance numeric,state text)
language sql stable security definer set search_path=''as $$
 select h.id,h.sale_number::text,h.sale_date,h.due_date,h.status::text,h.source_location_id,
  coalesce(li.qty,0)::bigint,coalesce(li.n,0)::bigint,
  round(coalesce(li.gross,0),2),round(coalesce(rf.refund,0),2),round(coalesce(pd.paid,0),2),
  round(greatest(coalesce(li.gross,0)-coalesce(rf.refund,0),0),2),
  case when h.status in('POSTED','PARTIAL_PAID','PAID')then round(greatest(coalesce(li.gross,0)-coalesce(rf.refund,0),0)-coalesce(pd.paid,0),2)end,
  case when h.status='DRAFT'then'DRAFT_PREVIEW'when h.status in('POSTED','PARTIAL_PAID','PAID')then'ACTIVE_RECEIVABLE'else'INACTIVE_DOCUMENT'end
 from erp.sales_headers h
 left join lateral(select sum(si.line_total)gross,sum(si.qty_pcs)qty,count(*)n from erp.sales_items si where si.sale_id=h.id)li on true
 left join lateral(select sum(ri.refund_amount)refund from erp.sales_return_items ri join erp.sales_returns rh on rh.id=ri.return_id
  where rh.sale_id=h.id and rh.status='POSTED')rf on true
 left join lateral(select sum(round(sp.amount,2))paid from erp.sales_payments sp where sp.sale_id=h.id and sp.status='POSTED')pd on true
 where h.customer_id=p_customer
$$;

-- When the Native audit log recorded a document's status becoming p_status (the first such change).
create function cp7_customer_history.ended_at(p_table text,p_id uuid,p_status text)returns timestamptz
language sql stable security definer set search_path=''as $$
 select min(al.changed_at)from erp.audit_logs al where al.entity_type=p_table and al.entity_id=p_id and al.action='UPDATE'
  and al.new_data->>'status'=p_status and al.old_data->>'status'is distinct from p_status
$$;

-- Every event of the customer: invoices, payments, returns, and the cancellation of any of them.
create function cp7_customer_history.events(p_customer uuid)
returns table(ev_kind text,ev_rank integer,doc_kind text,doc_id uuid,doc_number text,event_at timestamptz,invoice_id uuid,
 invoice_number text,doc_status text,qty bigint,pay_method text,amount numeric,location_id uuid)
language sql stable security definer set search_path=''as $$
 with inv as(select * from cp7_customer_history.invoices(p_customer)),
 pay as(select sp.id,sp.payment_number::text pnum,sp.payment_date,sp.sale_id,sp.status::text pstatus,sp.payment_method::text pmethod,round(sp.amount,2)pamount
  from erp.sales_payments sp where sp.sale_id in(select inv.sale_id from inv)),
 ret as(select rh.id,rh.return_number::text rnum,rh.physical_at,rh.sale_id,rh.status::text rstatus,
   (select coalesce(sum(ri.qty_pcs),0)from erp.sales_return_items ri where ri.return_id=rh.id)::bigint rqty,
   (select round(coalesce(sum(ri.refund_amount),0),2)from erp.sales_return_items ri where ri.return_id=rh.id)rrefund
  from erp.sales_returns rh where rh.sale_id in(select inv.sale_id from inv))
 select'INVOICE',1,'INVOICE',inv.sale_id,inv.sale_number,inv.sale_date,inv.sale_id,inv.sale_number,inv.sale_status,inv.qty_pcs,null::text,inv.gross,inv.location_id
  from inv
 union all
 select'PAYMENT',2,'PAYMENT',pay.id,pay.pnum,pay.payment_date,pay.sale_id,inv.sale_number,pay.pstatus,null::bigint,pay.pmethod,pay.pamount,null::uuid
  from pay join inv on inv.sale_id=pay.sale_id
 union all
 select'RETURN',3,'RETURN',ret.id,ret.rnum,ret.physical_at,ret.sale_id,inv.sale_number,ret.rstatus,ret.rqty,null::text,ret.rrefund,null::uuid
  from ret join inv on inv.sale_id=ret.sale_id
 union all
 select'CANCELLATION',4,'INVOICE',inv.sale_id,inv.sale_number,cp7_customer_history.ended_at('sales_headers',inv.sale_id,inv.sale_status),
  inv.sale_id,inv.sale_number,inv.sale_status,inv.qty_pcs,null::text,inv.gross,inv.location_id
  from inv where inv.sale_status in('CANCELLED','REVERSED')
 union all
 select'CANCELLATION',4,'PAYMENT',pay.id,pay.pnum,cp7_customer_history.ended_at('sales_payments',pay.id,'REVERSED'),
  pay.sale_id,inv.sale_number,pay.pstatus,null::bigint,pay.pmethod,pay.pamount,null::uuid
  from pay join inv on inv.sale_id=pay.sale_id where pay.pstatus='REVERSED'
 union all
 select'CANCELLATION',4,'RETURN',ret.id,ret.rnum,cp7_customer_history.ended_at('sales_returns',ret.id,'REVERSED'),
  ret.sale_id,inv.sale_number,ret.rstatus,ret.rqty,null::text,ret.rrefund,null::uuid
  from ret join inv on inv.sale_id=ret.sale_id where ret.rstatus='REVERSED'
$$;

-- A customer's identity, counts and, with finance.ar.view, the totals of its active invoices. Reads no location.
create function cp7_customer_history.summary(p_customer uuid,p_financial boolean)returns jsonb
language sql stable security definer set search_path=''as $$
 with inv as(select * from cp7_customer_history.invoices(p_customer)),
 counted as(select
  (select count(*)from inv)invoices,
  (select count(*)from erp.sales_payments sp where sp.sale_id in(select inv.sale_id from inv))payments,
  (select count(*)from erp.sales_returns rh where rh.sale_id in(select inv.sale_id from inv))returns,
  (select count(*)from inv where inv.sale_status in('CANCELLED','REVERSED'))
   +(select count(*)from erp.sales_payments sp where sp.sale_id in(select inv.sale_id from inv)and sp.status='REVERSED')
   +(select count(*)from erp.sales_returns rh where rh.sale_id in(select inv.sale_id from inv)and rh.status='REVERSED')cancellations,
  (select max(inv.sale_date)from inv)last_invoice_at),
 money as(select round(coalesce(sum(inv.gross),0),2)gross,round(coalesce(sum(inv.returned),0),2)returned,
  round(coalesce(sum(inv.net),0),2)net,round(coalesce(sum(inv.paid),0),2)paid,round(coalesce(sum(inv.open_balance),0),2)open_balance,
  count(*)active from inv where inv.state='ACTIVE_RECEIVABLE')
 select jsonb_build_object('id',cu.id,'code',cu.customer_code,'name',cu.customer_name,'is_active',cu.is_active,
   'counts',jsonb_build_object('invoices',counted.invoices::text,'payments',counted.payments::text,'returns',counted.returns::text,
    'cancellations',counted.cancellations::text),'last_invoice_at',counted.last_invoice_at)
  ||case when p_financial then jsonb_build_object('financial',jsonb_build_object('basis','CURRENT_NATIVE_DOCUMENT',
    'active_invoices',money.active::text,'invoice_total',money.gross::text,'return_total',money.returned::text,'net_total',money.net::text,
    'paid_total',money.paid::text,'open_balance',money.open_balance::text))else'{}'::jsonb end
 from erp.customers cu cross join counted cross join money where cu.id=p_customer
$$;

create function cp7_customer_history.workspace(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare v_access jsonb;v_financial boolean;v_q text;v_customer uuid;v_limit integer;v_offset integer;v_total bigint;
 v_rows jsonb;v_profile jsonb;v_invoices jsonb;v_missing bigint;v_cust erp.customers;
begin
 v_access:=cp7_customer_history.access_now();v_financial:=(v_access->>'financial')::boolean;
 if jsonb_typeof(p_query)is distinct from'object'
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('q','customer_id','offset','limit'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('q','customer_id')and jsonb_typeof(e.value)not in('string','null'))
  or(p_query?'limit'and(jsonb_typeof(p_query->'limit')<>'number'or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset'and(jsonb_typeof(p_query->'offset')<>'number'or(p_query->>'offset')!~'^[0-9]{1,7}$'))
  or coalesce((p_query->>'customer_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',false)then
  raise exception 'CP7_CUSTOMER_HISTORY_QUERY';end if;
 v_q:=btrim(coalesce(p_query->>'q',''));v_customer:=(p_query->>'customer_id')::uuid;
 v_limit:=coalesce((p_query->>'limit')::integer,25);v_offset:=coalesce((p_query->>'offset')::integer,0);
 if length(v_q)>120 or v_limit not between 1 and 100 or v_offset not between 0 and 1000000 or(v_customer is not null and v_q<>'')then
  raise exception 'CP7_CUSTOMER_HISTORY_QUERY';end if;

 if v_customer is null then
  select count(*)into v_total from erp.customers x
   where v_q=''or strpos(lower(concat_ws(' ',x.customer_code,x.customer_name)),lower(v_q))>0;
  select coalesce(jsonb_agg(cp7_customer_history.summary(x.id,v_financial)order by x.customer_name,x.customer_code,x.id),'[]'::jsonb)into v_rows
   from(select y.id,y.customer_name,y.customer_code from erp.customers y
    where v_q=''or strpos(lower(concat_ws(' ',y.customer_code,y.customer_name)),lower(v_q))>0
    order by y.customer_name,y.customer_code,y.id limit v_limit offset v_offset)x;
  return jsonb_build_object('contract_version','cp7.customer-history.v1','mode','LIST','read_at',statement_timestamp(),
   'financial_captured',v_financial,'can_export',(v_access->>'export')::boolean,'read_only',true,'business_DML',false,
   'page',jsonb_build_object('rows',v_rows,'total',v_total::text,'offset',v_offset,'limit',v_limit,
    'next_offset',case when v_offset+jsonb_array_length(v_rows)<v_total then v_offset+jsonb_array_length(v_rows)end));
 end if;

 select * into v_cust from erp.customers where id=v_customer;
 if v_cust.id is null then raise exception 'CP7_CUSTOMER_HISTORY_NOT_FOUND';end if;
 -- The customer's counts and totals.
 v_profile:=cp7_customer_history.summary(v_cust.id,v_financial);
 -- The timeline page, newest first (same snapshot as the totals above). Only this statement reads erp.locations.
 with ev as materialized(select * from cp7_customer_history.events(v_cust.id))
 select(select count(*)from ev),(select count(*)from ev where ev.event_at is null),
  (select coalesce(jsonb_agg(jsonb_build_object('id',x.ev_kind||':'||x.doc_id,'kind',x.ev_kind,'document',x.doc_kind,'document_id',x.doc_id,
     'number',x.doc_number,'at',x.event_at,'wib_date',to_char(x.event_at at time zone'Asia/Jakarta','YYYY-MM-DD'),
     'invoice_id',x.invoice_id,'invoice_number',x.invoice_number,'status',x.doc_status,'qty_pcs',x.qty::text,'method',x.pay_method,
     'location_name',x.location_name)
    ||case when v_financial then jsonb_build_object('financial',jsonb_build_object('amount',x.amount::text))else'{}'::jsonb end
    order by x.event_at desc nulls last,x.ev_rank desc,x.doc_id),'[]'::jsonb)
   from(select ev.*,lo.location_name::text location_name from ev left join erp.locations lo on lo.id=ev.location_id
    order by ev.event_at desc nulls last,ev.ev_rank desc,ev.doc_id limit v_limit offset v_offset)x)
 into v_total,v_missing,v_rows;
 -- A cancelled document whose cancellation the audit log does not hold cannot be placed: say so instead of guessing.
 if v_missing>0 then raise exception 'CP7_CUSTOMER_HISTORY_INCOMPLETE';end if;
 -- The invoices named on this page, with their current status and figures.
 select coalesce(jsonb_agg(jsonb_build_object('id',i.sale_id,'number',i.sale_number,'status',i.sale_status,'physical_at',i.sale_date,
    'due_date',i.due_date,'qty_pcs',i.qty_pcs::text)
   ||case when v_financial then jsonb_build_object('financial',jsonb_build_object('basis','CURRENT_NATIVE_DOCUMENT','state',i.state,
     'gross_total',i.gross::text,'return_total',i.returned::text,'net_total',i.net::text,'paid_total',i.paid::text,
     'open_balance',i.open_balance::text))else'{}'::jsonb end
   order by i.sale_date desc,i.sale_id),'[]'::jsonb)into v_invoices
  from cp7_customer_history.invoices(v_cust.id)i
  where i.sale_id in(select(r->>'invoice_id')::uuid from jsonb_array_elements(v_rows)r);
 return jsonb_build_object('contract_version','cp7.customer-history.v1','mode','CUSTOMER','read_at',statement_timestamp(),
  'financial_captured',v_financial,'can_export',(v_access->>'export')::boolean,'read_only',true,'business_DML',false,
  'customer',v_profile,
  'timeline',jsonb_build_object('rows',v_rows,'total',v_total::text,'offset',v_offset,'limit',v_limit,
   'next_offset',case when v_offset+jsonb_array_length(v_rows)<v_total then v_offset+jsonb_array_length(v_rows)end),
  'invoices',v_invoices);
end $$;

create function public.erp_cp7_get_customer_history_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_customer_history.workspace(p_query)$$;
alter function cp7_customer_history.access_now()owner to postgres;
alter function cp7_customer_history.invoices(uuid)owner to postgres;
alter function cp7_customer_history.ended_at(text,uuid,text)owner to postgres;
alter function cp7_customer_history.events(uuid)owner to postgres;
alter function cp7_customer_history.summary(uuid,boolean)owner to postgres;
alter function cp7_customer_history.workspace(jsonb)owner to postgres;
grant create on schema public to cp7_customer_history_read;
alter function public.erp_cp7_get_customer_history_v1(jsonb)owner to cp7_customer_history_read;
revoke create on schema public from cp7_customer_history_read;
revoke all on function cp7_customer_history.access_now(),cp7_customer_history.invoices(uuid),cp7_customer_history.ended_at(text,uuid,text),
 cp7_customer_history.events(uuid),cp7_customer_history.summary(uuid,boolean),cp7_customer_history.workspace(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_customer_history_read;
grant execute on function cp7_customer_history.workspace(jsonb)to cp7_customer_history_read;
revoke all on function public.erp_cp7_get_customer_history_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_customer_history_v1(jsonb)to authenticated;
