-- Owning supplier-payment history and reviewed inverse. No alternate AP formula
-- or payment writer: amounts come from the accepted supplier-credit reader and
-- every financial inverse comes from erp.reverse_supplier_payment.
grant select on erp.supplier_payments,erp.cash_accounts,erp.journal_entries,erp.journal_lines to cp7_invoice_read;
grant execute on function public.erp_get_supplier_credit_v1(jsonb) to cp7_invoice_read;
create table cp7_invoice.payment_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
alter table cp7_invoice.payment_requests owner to cp7_invoice_write;
alter table cp7_invoice.payment_requests enable row level security;
revoke all on cp7_invoice.payment_requests from public,anon,authenticated,service_role,cp7_capture,cp7_invoice_read;

create function cp7_invoice.payment_access() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 a:=cp7_invoice.access_now();
 return a||jsonb_build_object('reverse_payment',
  a->'profile'->>'role_code' in('OWNER','ADMIN') and erp.has_permission('finance.ap.pay'));
end $$;

create function cp7_invoice.payment_ap(p_purchase uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare h erp.material_purchase_headers;r jsonb;answer jsonb;
begin
 perform cp7_invoice.payment_access();
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found or h.supplier_id is null then raise exception 'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND';end if;
 r:=public.erp_get_supplier_credit_v1(jsonb_build_object('supplier_id',h.supplier_id,'page',1));
 select value into answer from jsonb_array_elements(r->'purchases') where value->>'id'=h.id::text;
 if h.status='POSTED' and answer is null then raise exception 'CP7_SUPPLIER_PAYMENT_AP_UNAVAILABLE';end if;
 return answer;
end $$;

create function cp7_invoice.payment_detail(p_payment uuid,p_ap jsonb) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare p erp.supplier_payments;h erp.material_purchase_headers;c erp.cash_accounts;
 j erp.journal_entries;inverse erp.journal_entries;n bigint;state jsonb;r jsonb;
 previous_zone text:=current_setting('TimeZone');
begin
 perform cp7_invoice.payment_access();
 -- Hash the full original rows in one stable timezone, restoring the caller's
 -- zone before any Native inverse. No timestamp or dependency is dropped.
 perform set_config('TimeZone','UTC',true);
 select * into p from erp.supplier_payments where id=p_payment;
 if not found then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select * into h from erp.material_purchase_headers where id=p.purchase_id;
 if h.id is null or(p_ap is not null and p_ap->>'id' is distinct from h.id::text)
  or(h.status='POSTED' and p_ap is null) then raise exception 'CP7_SUPPLIER_PAYMENT_AP_UNAVAILABLE';end if;
 select * into c from erp.cash_accounts where id=p.cash_account_id;
 select count(*) into n from erp.journal_entries where source_type='SUPPLIER_PAYMENT' and source_id=p.id and reversal_of_id is null;
 if n>1 then raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
 select * into j from erp.journal_entries where source_type='SUPPLIER_PAYMENT' and source_id=p.id and reversal_of_id is null;
 if j.id is not null then
  select count(*) into n from erp.journal_entries where reversal_of_id=j.id;
  if n>1 then raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
  select * into inverse from erp.journal_entries where reversal_of_id=j.id;
 end if;
 if p.amount<=0 or p.amount<>round(p.amount,2) or p.status not in('DRAFT','POSTED','REVERSED')
  or(p.status='DRAFT' and j.id is not null)
  or(p.status='POSTED' and(j.id is null or j.status<>'POSTED' or inverse.id is not null))
  or(p.status='REVERSED' and(j.id is null or j.status<>'REVERSED' or inverse.id is null or inverse.status<>'POSTED')) then
  raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
 state:=jsonb_build_object('payment',to_jsonb(p),'purchase',to_jsonb(h),'cash',to_jsonb(c),'Native_AP',p_ap,
  'journal',to_jsonb(j),'inverse',to_jsonb(inverse),'lines',
  (select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from erp.journal_lines l where l.journal_entry_id in(j.id,inverse.id)));
 r:=jsonb_build_object('id',p.id,'number',p.payment_number,'status',p.status,'payment_date',p.payment_date,
  'amount',p.amount::numeric(20,2)::text,'cash_account_id',p.cash_account_id,'cash_code',c.cash_account_code,'cash_name',c.cash_account_name,
  'journal',case when j.id is null then null else jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,
   'economic_date',j.economic_date,'accounting_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted)end,
  'inverse',case when inverse.id is null then null else jsonb_build_object('id',inverse.id,'number',inverse.journal_number,'status',inverse.status,
   'economic_date',inverse.economic_date,'accounting_date',inverse.transaction_date,'posting_at',inverse.posting_at,'period_shifted',inverse.period_shifted)end,
  'review_token',md5(state::text));
 perform set_config('TimeZone',previous_zone,true);return r;
exception when others then perform set_config('TimeZone',previous_zone,true);raise;
end $$;

create function cp7_invoice.payment_workspace(p_purchase uuid,p_q text,p_offset integer,p_payment uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;h erp.material_purchase_headers;s erp.suppliers;ap jsonb;rows jsonb;total bigint;q text;
begin
 a:=cp7_invoice.payment_access();q:=btrim(coalesce(p_q,''));
 if p_purchase is null or length(q)>120 or p_offset is null or p_offset not between 0 and 1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found or h.supplier_id is null then raise exception 'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND';end if;
 select * into s from erp.suppliers where id=h.supplier_id;ap:=cp7_invoice.payment_ap(h.id);
 if p_payment is not null then
  if q<>'' then raise exception 'CP7_SUPPLIER_PAYMENT_EXACT_QUERY';end if;
  select ((n-1)/25)*25 into p_offset from(select id,row_number()over(order by payment_date,created_at,id)n from erp.supplier_payments where purchase_id=h.id)x where id=p_payment;
  if p_offset is null or p_offset>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 end if;
 select count(*) into total from erp.supplier_payments where purchase_id=h.id and(q='' or strpos(lower(payment_number),lower(q))>0);
 select coalesce(jsonb_agg(cp7_invoice.payment_detail(p.id,ap)order by p.payment_date,p.created_at,p.id),'[]')into rows
  from(select * from erp.supplier_payments where purchase_id=h.id and(q='' or strpos(lower(payment_number),lower(q))>0)
   order by payment_date,created_at,id limit 25 offset p_offset)p;
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-payment-read.v1','captured_at',statement_timestamp(),'query',q,'selected_payment_id',p_payment,
  'purchase',jsonb_build_object('id',h.id,'number',h.purchase_number,'status',h.status,'supplier_id',s.id,'supplier_name',s.supplier_name),
  'Native_AP',ap,'capabilities',jsonb_build_object('reverse',a->'reverse_payment'),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',25,
   'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows)else null end));
end $$;

-- Like the receipt inverse adapter, this narrow postgres helper locks Native
-- sources without granting ERP UPDATE/INSERT/DELETE to either CP7 principal.
create function cp7_invoice.reverse_payment_locked(p_payload jsonb) returns uuid
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;p erp.supplier_payments;h erp.material_purchase_headers;d jsonb;journal uuid;inverse uuid;
begin
 a:=cp7_invoice.payment_access();
 if a->'reverse_payment' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_REVERSE_DENIED';end if;
 select * into p from erp.supplier_payments where id=(p_payload->>'payment_id')::uuid for update;
 if p.id is null or p.purchase_id is distinct from(p_payload->>'purchase_id')::uuid then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
 perform 1 from erp.initial_import_prepayments x join erp.initial_import_prepayment_payments l on l.advance_id=x.id where l.payment_id=p.id for update of x;
 perform 1 from erp.journal_entries x where x.source_type='SUPPLIER_PAYMENT'and x.source_id=p.id order by x.id for update;
 perform 1 from erp.journal_lines l join erp.journal_entries x on x.id=l.journal_entry_id where x.source_type='SUPPLIER_PAYMENT'and x.source_id=p.id order by l.id for update of l;
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if p.status<>'POSTED' or h.status<>'POSTED' then raise exception 'CP7_SUPPLIER_PAYMENT_POSTED_REQUIRED';end if;
 d:=cp7_invoice.payment_detail(p.id,cp7_invoice.payment_ap(h.id));
 if d->>'review_token' is distinct from p_payload->>'review_token' then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 journal:=(d->'journal'->>'id')::uuid;
 perform erp.reverse_supplier_payment(p.id,p_payload->>'reason');
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 select id into inverse from erp.journal_entries where reversal_of_id=journal and status='POSTED';
 if inverse is null or not exists(select 1 from erp.supplier_payments where id=p.id and status='REVERSED')then raise exception 'CP7_SUPPLIER_PAYMENT_INVERSE_INCOMPLETE';end if;
 return inverse;
end $$;
alter function cp7_invoice.reverse_payment_locked(jsonb)owner to postgres;

create function cp7_invoice.reverse_payment_request(p_payload jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_invoice.payment_requests;r jsonb;inverse uuid;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_invoice.payment_access();
 if a->'reverse_payment' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_REVERSE_DENIED';end if;
 if p_request is null or jsonb_typeof(p_payload)is distinct from'object' or not p_payload?&array['purchase_id','payment_id','review_token','reason']
  or exists(select 1 from jsonb_each(p_payload)e where e.key not in('purchase_id','payment_id','review_token','reason')or jsonb_typeof(e.value)<>'string' or nullif(btrim(e.value#>>'{}'),'')is null)
  or length(p_payload->>'reason')>1000 or p_payload->>'review_token'!~'^[a-f0-9]{32}$' then raise exception 'CP7_SUPPLIER_PAYMENT_FIELDS';end if;
 insert into cp7_invoice.payment_requests values(auth.uid(),p_request,p_payload,null)on conflict do nothing;
 select * into old from cp7_invoice.payment_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload<>p_payload then raise exception 'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED';end if;
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 inverse:=cp7_invoice.reverse_payment_locked(p_payload);
 r:=jsonb_build_object('contract_version','cp7.supplier-payment-outcome.v1','kind','COMMITTED_OUTCOME','action','REVERSE',
  'request_id',p_request,'request_payload',p_payload,'purchase_id',p_payload->>'purchase_id','payment_id',p_payload->>'payment_id',
  'status','REVERSED','inverse_journal_id',inverse);
 update cp7_invoice.payment_requests set response=r where actor=auth.uid()and request_id=p_request;return r;
end $$;

create function public.erp_cp7_get_supplier_payments_v1(p_purchase uuid,p_q text,p_offset integer,p_payment uuid default null) returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_invoice.payment_workspace(p_purchase,p_q,p_offset,p_payment)$$;
create function public.erp_cp7_reverse_supplier_payment_v1(p_payload jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_invoice.reverse_payment_request(p_payload,p_request)$$;
