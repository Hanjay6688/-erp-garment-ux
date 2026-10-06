-- Record one new cash/bank payment of a posted material receipt's supplier AP.
-- CP7 already reads, corrects and reverses supplier payments; without this
-- entry the operator could not settle supplier AP in the application at all.
-- The new row is only a Native DRAFT: Native erp.post_supplier_payment stays
-- the single AP-capacity, account and journal authority. No ERP DML grant is
-- given to an App principal; the definer is the narrow postgres helper.
create schema cp7_supplier_payment_create authorization cp7_invoice_read;
revoke all on schema cp7_supplier_payment_create from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_supplier_payment_create to cp7_invoice_write;
grant usage on schema cp7_supplier_payment_create to postgres;
create table cp7_supplier_payment_create.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
create table cp7_supplier_payment_create.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,payload jsonb not null,primary key(backend_pid,transaction_id)
);
alter table cp7_supplier_payment_create.requests owner to cp7_invoice_write;
alter table cp7_supplier_payment_create.context owner to cp7_invoice_write;
alter table cp7_supplier_payment_create.requests enable row level security;
alter table cp7_supplier_payment_create.context enable row level security;
create policy supplier_payment_create_requests_deny on cp7_supplier_payment_create.requests for all to public using(false)with check(false);
create policy supplier_payment_create_context_deny on cp7_supplier_payment_create.context for all to public using(false)with check(false);
revoke all on all tables in schema cp7_supplier_payment_create from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_supplier_payment_create.context to postgres;

-- Paying money uses the same current authority as correcting or reversing it:
-- OWNER/ADMIN with finance.ap.pay on top of procurement and AP view.
create function cp7_supplier_payment_create.access_now()returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_invoice.payment_access();
 if a->'reverse_payment'is distinct from'true'::jsonb then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CREATE_DENIED';end if;
 return a;
end $$;

create function cp7_supplier_payment_create.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 if jsonb_typeof(p)is distinct from'object'
  or not(p?&array['purchase_id','review_token','amount','cash_account_id','payment_date','note'])
  or(select count(*)from jsonb_object_keys(p))<>6
  or exists(select 1 from jsonb_each(p)where jsonb_typeof(value)<>'string')
  or coalesce(p->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or coalesce(p->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'or(p->>'amount')::numeric<=0
  or coalesce(p->>'cash_account_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'payment_date','')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.[0-9]{1,6})?(Z|[+-]\d{2}:\d{2})$'
  or length(btrim(p->>'note'))not between 5 and 500 then
  raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS';end if;
 perform(p->>'payment_date')::timestamptz;
end $$;

-- One token over the complete Native receipt, its AP answer and every payment
-- row of that receipt, hashed in UTC. Any payment, reversal, credit or receipt
-- change in between retires the reviewed amount instead of paying twice.
create function cp7_supplier_payment_create.review(p_purchase uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.material_purchase_headers;s erp.suppliers;ap jsonb;payments jsonb;
begin
 perform cp7_invoice.payment_access();
 select *into h from erp.material_purchase_headers where id=p_purchase;
 if h.id is null or h.supplier_id is null then raise exception 'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND';end if;
 select *into s from erp.suppliers where id=h.supplier_id;
 ap:=cp7_invoice.payment_ap(h.id);
 select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')into payments from erp.supplier_payments p where p.purchase_id=h.id;
 return jsonb_build_object('purchase',jsonb_build_object('id',h.id,'number',h.purchase_number,'status',h.status,'physical_at',h.physical_at,
   'supplier_id',s.id,'supplier_name',s.supplier_name),'Native_AP',ap,
  'eligible',h.status='POSTED'and ap is not null and coalesce((ap->>'remaining')::numeric,0)>0,
  'review_token',md5(jsonb_build_object('purchase',to_jsonb(h),'ap',ap,'payments',payments)::text));
end $$;

create function cp7_supplier_payment_create.workspace(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r jsonb;q text;off integer;rows jsonb;total bigint;
begin
 a:=cp7_invoice.payment_access();
 if jsonb_typeof(p_query)is distinct from'object'or not(p_query?'purchase_id')
  or exists(select 1 from jsonb_object_keys(p_query)x where x not in('purchase_id','bank_q','bank_offset'))
  or jsonb_typeof(p_query->'purchase_id')is distinct from'string'or coalesce(p_query->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p_query?'bank_q'and jsonb_typeof(p_query->'bank_q')is distinct from'string')
  or(p_query?'bank_offset'and(jsonb_typeof(p_query->'bank_offset')is distinct from'number'or coalesce(p_query->>'bank_offset','')!~'^(0|[1-9][0-9]{0,6})$'))then
  raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_QUERY';end if;
 q:=btrim(coalesce(p_query->>'bank_q',''));off:=coalesce((p_query->>'bank_offset')::integer,0);
 if length(q)>120 or off>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_QUERY';end if;
 r:=cp7_supplier_payment_create.review((p_query->>'purchase_id')::uuid);
 select count(*)into total from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind)order by c.cash_account_code,c.id),'[]')into rows
  from(select c.*from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
   where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0)
   order by c.cash_account_code,c.id limit 25 offset off)c;
 if cp7_invoice.payment_access()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return r||jsonb_build_object('contract_version','cp7.supplier-payment-create-workspace.v1','captured_at',statement_timestamp(),
  'can_create',a->'reverse_payment','cash_accounts',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',25,
   'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $$;

create function cp7_supplier_payment_create.apply(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h erp.material_purchase_headers;r jsonb;payment uuid;after jsonb;at timestamptz;
begin
 a:=cp7_supplier_payment_create.access_now();perform cp7_supplier_payment_create.validate(p);
 if not exists(select 1 from cp7_supplier_payment_create.context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request and payload=p)then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CREATE_PRIVATE_CONTEXT_REQUIRED';end if;
 -- Same order as Native posting and the correction: payments, then receipt.
 perform 1 from erp.supplier_payments where purchase_id=(p->>'purchase_id')::uuid order by id for update;
 select *into h from erp.material_purchase_headers where id=(p->>'purchase_id')::uuid for update;
 if h.id is null then raise exception 'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts where id=(p->>'cash_account_id')::uuid for share;
 perform 1 from erp.chart_accounts where id in(select coa_account_id from erp.cash_accounts where id=(p->>'cash_account_id')::uuid
  union select account_id from erp.accounting_account_mappings where mapping_key='AP_SUPPLIER')order by id for share;
 -- Locks may have waited: authority and the reviewed Native state are read again now.
 if cp7_supplier_payment_create.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 r:=cp7_supplier_payment_create.review(h.id);
 if r->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 if h.status<>'POSTED'or not(r->'eligible')::boolean then raise exception 'CP7_SUPPLIER_PAYMENT_NOTHING_PAYABLE';end if;
 if(p->>'amount')::numeric>(r->'Native_AP'->>'remaining')::numeric then raise exception 'CP7_SUPPLIER_PAYMENT_EXCEEDS_REMAINING';end if;
 if not exists(select 1 from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.id=(p->>'cash_account_id')::uuid and c.is_active and ca.is_active and ca.is_postable)then raise exception 'CP7_SUPPLIER_PAYMENT_CASH_ACCOUNT_INACTIVE';end if;
 at:=(p->>'payment_date')::timestamptz;
 if at>statement_timestamp()then raise exception 'CP7_SUPPLIER_PAYMENT_DATE_FUTURE';end if;
 -- Money paid before the goods arrived is an advance, a different document.
 if at<h.physical_at then raise exception 'CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT';end if;
 insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id,notes,status,created_by)
  values(h.id,'B-'||replace(p_request::text,'-',''),at,(p->>'amount')::numeric,(p->>'cash_account_id')::uuid,btrim(p->>'note'),'DRAFT',erp.current_app_user_id())
  returning id into payment;
 perform erp.post_supplier_payment(payment);
 if not exists(select 1 from erp.supplier_payments where id=payment and purchase_id=h.id and status='POSTED')
  or not exists(select 1 from erp.journal_entries where source_type='SUPPLIER_PAYMENT'and source_id=payment and status='POSTED')then
  raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_POST_INCOMPLETE';end if;
 if cp7_supplier_payment_create.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 after:=cp7_invoice.payment_ap(h.id);
 return jsonb_build_object('contract_version','cp7.supplier-payment-create.v1','kind','COMMITTED_OUTCOME','action','CREATE',
  'request_id',p_request,'request_payload',p,'purchase_id',h.id,'payment_id',payment,'status','POSTED',
  'amount',(p->>'amount')::numeric(20,2)::text,'remaining_after',(after->>'remaining')::numeric(20,2)::text);
end $$;

create function cp7_supplier_payment_create.command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;saved cp7_supplier_payment_create.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_payment_create.access_now();perform cp7_supplier_payment_create.validate(p);
 if p_request is null then raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS';end if;
 insert into cp7_supplier_payment_create.requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into saved from cp7_supplier_payment_create.requests where actor=auth.uid()and request_id=p_request for update;
 if cp7_supplier_payment_create.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if saved.payload is distinct from p then raise exception 'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_supplier_payment_create.context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p);
 r:=cp7_supplier_payment_create.apply(p,p_request);
 delete from cp7_supplier_payment_create.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_supplier_payment_create.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 update cp7_supplier_payment_create.requests set response=r where actor=auth.uid()and request_id=p_request;return r;
end $$;

alter function cp7_supplier_payment_create.access_now()owner to cp7_invoice_read;
alter function cp7_supplier_payment_create.validate(jsonb)owner to cp7_invoice_read;
alter function cp7_supplier_payment_create.review(uuid)owner to postgres;
alter function cp7_supplier_payment_create.workspace(jsonb)owner to postgres;
alter function cp7_supplier_payment_create.apply(jsonb,uuid)owner to postgres;
alter function cp7_supplier_payment_create.command(jsonb,uuid)owner to cp7_invoice_write;
revoke all on all functions in schema cp7_supplier_payment_create from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_supplier_payment_create.access_now(),cp7_supplier_payment_create.validate(jsonb),cp7_supplier_payment_create.apply(jsonb,uuid)to cp7_invoice_write;
grant execute on function cp7_supplier_payment_create.access_now(),cp7_supplier_payment_create.validate(jsonb)to postgres;
grant execute on function cp7_supplier_payment_create.workspace(jsonb)to cp7_invoice_read;
revoke create on schema cp7_supplier_payment_create from cp7_invoice_write;
grant create on schema public to cp7_invoice_write,cp7_invoice_read;
create function public.erp_cp7_create_supplier_payment_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_payment_create.command(p_payload,p_request)$$;
create function public.erp_cp7_get_supplier_payment_create_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_payment_create.workspace(p_query)$$;
alter function public.erp_cp7_create_supplier_payment_v1(jsonb,uuid)owner to cp7_invoice_write;
alter function public.erp_cp7_get_supplier_payment_create_v1(jsonb)owner to cp7_invoice_read;
revoke create on schema public from cp7_invoice_write,cp7_invoice_read;
revoke all on function public.erp_cp7_create_supplier_payment_v1(jsonb,uuid),public.erp_cp7_get_supplier_payment_create_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_create_supplier_payment_v1(jsonb,uuid),public.erp_cp7_get_supplier_payment_create_v1(jsonb)to authenticated;
