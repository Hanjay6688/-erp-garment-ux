-- Correct one ordinary supplier payment in one transaction. Preserve the
-- Native original, create a new Native draft/post, and retain immutable links.
-- Imported advances keep their separate allocation/reconciliation meaning.
create schema cp7_supplier_payment_correction authorization cp7_invoice_read;
revoke all on schema cp7_supplier_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_supplier_payment_correction to cp7_invoice_write;
grant usage on schema cp7_supplier_payment_correction to postgres;
create table cp7_supplier_payment_correction.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
create table cp7_supplier_payment_correction.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,payload jsonb not null,primary key(backend_pid,transaction_id)
);
create table cp7_supplier_payment_correction.links(
 original_id uuid primary key references erp.supplier_payments(id),
 replacement_id uuid not null unique references erp.supplier_payments(id),
 purchase_id uuid not null references erp.material_purchase_headers(id),actor uuid not null,
 request_id uuid not null,reason text not null,
 time_neutral_id uuid references erp.journal_entries(id),effective_inverse_id uuid references erp.journal_entries(id),
 recorded_at timestamptz not null default statement_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),
 check((time_neutral_id is null)=(effective_inverse_id is null)),unique(actor,request_id)
);
alter table cp7_supplier_payment_correction.requests owner to cp7_invoice_write;
alter table cp7_supplier_payment_correction.context owner to cp7_invoice_write;
alter table cp7_supplier_payment_correction.links owner to cp7_invoice_write;
alter table cp7_supplier_payment_correction.requests enable row level security;
alter table cp7_supplier_payment_correction.context enable row level security;
alter table cp7_supplier_payment_correction.links enable row level security;
create policy supplier_payment_correction_requests_deny on cp7_supplier_payment_correction.requests for all to public using(false)with check(false);
create policy supplier_payment_correction_context_deny on cp7_supplier_payment_correction.context for all to public using(false)with check(false);
create policy supplier_payment_correction_links_deny on cp7_supplier_payment_correction.links for all to public using(false)with check(false);
revoke all on all tables in schema cp7_supplier_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_supplier_payment_correction.context,cp7_supplier_payment_correction.links to postgres;

create function cp7_supplier_payment_correction.access_now()returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_invoice.payment_access();
 if a->'reverse_payment'is distinct from'true'::jsonb then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CORRECTION_DENIED';end if;
 return a;
end $$;

create function cp7_supplier_payment_correction.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['purchase_id','payment_id','review_token','replacement','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>5
  or jsonb_typeof(p->'purchase_id')is distinct from'string'or coalesce(p->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'payment_id')is distinct from'string'or coalesce(p->>'payment_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_FIELDS';end if;
 if jsonb_typeof(p->'replacement')is distinct from'object'
  or not(p->'replacement'?&array['amount','cash_account_id','payment_date'])
  or(select count(*)from jsonb_object_keys(p->'replacement'))<>3
  or exists(select 1 from jsonb_each(p->'replacement')where jsonb_typeof(value)<>'string')
  or coalesce(p->'replacement'->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'
  or(p->'replacement'->>'amount')::numeric<=0
  or coalesce(p->'replacement'->>'cash_account_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->'replacement'->>'payment_date','')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.[0-9]{1,6})?(Z|[+-]\d{2}:\d{2})$'then
  raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_FIELDS';end if;
 perform(p->'replacement'->>'payment_date')::timestamptz;
end $$;

create function cp7_supplier_payment_correction.link_value(p cp7_supplier_payment_correction.links)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('original_id',p.original_id,'replacement_id',p.replacement_id,
  'purchase_id',p.purchase_id,'actor_scope_id',p.actor,'request_id',p.request_id,'reason',p.reason,'recorded_at',p.recorded_at,
  'time_restatement',case when p.time_neutral_id is null then null else(
   select jsonb_build_object('neutral_journal_id',n.id,'neutral_number',n.journal_number,
    'neutral_economic_date',n.economic_date,'neutral_transaction_date',n.transaction_date,
    'effective_journal_id',e.id,'effective_number',e.journal_number,
    'effective_economic_date',e.economic_date,'effective_transaction_date',e.transaction_date)
   from erp.journal_entries n join erp.journal_entries e on e.id=p.effective_inverse_id where n.id=p.time_neutral_id)end)
$$;

create function cp7_supplier_payment_correction.workspace(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;original erp.supplier_payments;h erp.material_purchase_headers;ap jsonb;d jsonb;
 prev cp7_supplier_payment_correction.links;nxt cp7_supplier_payment_correction.links;
 previous jsonb:='null';following jsonb:='null';q text;off integer;rows jsonb;total bigint;
begin
 a:=cp7_invoice.payment_access();
 if jsonb_typeof(p_query)is distinct from'object'or not(p_query?&array['purchase_id','payment_id'])
  or exists(select 1 from jsonb_object_keys(p_query)x where x not in('purchase_id','payment_id','bank_q','bank_offset'))
  or jsonb_typeof(p_query->'purchase_id')is distinct from'string'or coalesce(p_query->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p_query->'payment_id')is distinct from'string'or coalesce(p_query->>'payment_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p_query?'bank_q'and jsonb_typeof(p_query->'bank_q')is distinct from'string')
  or(p_query?'bank_offset'and(jsonb_typeof(p_query->'bank_offset')is distinct from'number'or coalesce(p_query->>'bank_offset','')!~'^(0|[1-9][0-9]{0,6})$'))then
  raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_QUERY';end if;
 q:=btrim(coalesce(p_query->>'bank_q',''));off:=coalesce((p_query->>'bank_offset')::integer,0);
 if length(q)>120 or off>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_QUERY';end if;
 select *into original from erp.supplier_payments where id=(p_query->>'payment_id')::uuid and purchase_id=(p_query->>'purchase_id')::uuid;
 if original.id is null then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select *into strict h from erp.material_purchase_headers where id=original.purchase_id;
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 select *into prev from cp7_supplier_payment_correction.links where replacement_id=original.id and purchase_id=h.id;
 select *into nxt from cp7_supplier_payment_correction.links where original_id=original.id and purchase_id=h.id;
 if prev.original_id is not null then previous:=jsonb_build_object('link',cp7_supplier_payment_correction.link_value(prev),'document',cp7_invoice.payment_detail(prev.original_id,ap));end if;
 if nxt.original_id is not null then following:=jsonb_build_object('link',cp7_supplier_payment_correction.link_value(nxt),'document',cp7_invoice.payment_detail(nxt.replacement_id,ap));end if;
 select count(*)into total from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind)order by c.cash_account_code,c.id),'[]')into rows
  from(select c.*from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
   where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0)
   order by c.cash_account_code,c.id limit 25 offset off)c;
 if cp7_invoice.payment_access()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-payment-correction-workspace.v1','captured_at',statement_timestamp(),
  'purchase_id',h.id,'Native_AP',ap,'document',d,'can_correct',a->'reverse_payment',
  'eligible',original.status='POSTED'and h.status='POSTED'and original.cash_account_id is not null
   and not exists(select 1 from erp.initial_import_prepayment_payments where payment_id=original.id)
   and not exists(select 1 from cp7_supplier_payment_correction.links where original_id=original.id),
  'previous',previous,'next',following,'cash_accounts',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',25,
   'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $$;

create function cp7_supplier_payment_correction.protect_link()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if tg_op<>'INSERT'then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_LINK_IMMUTABLE';end if;
 if not exists(select 1 from cp7_supplier_payment_correction.context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.actor=new.actor and c.request_id=new.request_id and c.payload->>'purchase_id'=new.purchase_id::text
  and c.payload->>'payment_id'=new.original_id::text and btrim(c.payload->>'change_reason')=new.reason)
  or not exists(select 1 from erp.supplier_payments where id=new.original_id and purchase_id=new.purchase_id and status='REVERSED')
  or not exists(select 1 from erp.supplier_payments where id=new.replacement_id and purchase_id=new.purchase_id and status='POSTED')then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 if new.time_neutral_id is not null and(not exists(select 1 from erp.journal_entries where id=new.time_neutral_id and source_type='SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL'and source_id=new.original_id and status='POSTED')
  or not exists(select 1 from erp.journal_entries where id=new.effective_inverse_id and source_type='SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE'and source_id=new.original_id and status='POSTED'))then
  raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 return new;
end $$;
create trigger supplier_payment_correction_link_immutable before insert or update or delete on cp7_supplier_payment_correction.links for each row execute function cp7_supplier_payment_correction.protect_link();
create trigger supplier_payment_correction_link_no_truncate before truncate on cp7_supplier_payment_correction.links for each statement execute function cp7_supplier_payment_correction.protect_link();

create function cp7_supplier_payment_correction.apply(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;original erp.supplier_payments;h erp.material_purchase_headers;ap jsonb;d jsonb;
 o erp.journal_entries;inv erp.journal_entries;lines jsonb;neutral uuid;effective uuid;replacement uuid;link cp7_supplier_payment_correction.links;
begin
 a:=cp7_supplier_payment_correction.access_now();perform cp7_supplier_payment_correction.validate(p);
 if not exists(select 1 from cp7_supplier_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request and payload=p)then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.supplier_payments where purchase_id=(p->>'purchase_id')::uuid order by id for update;
 select *into h from erp.material_purchase_headers where id=(p->>'purchase_id')::uuid for update;
 select *into original from erp.supplier_payments where id=(p->>'payment_id')::uuid;
 if h.id is null or original.id is null or original.purchase_id<>h.id then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if original.status<>'POSTED'or h.status<>'POSTED'or original.cash_account_id is null
  or exists(select 1 from erp.initial_import_prepayment_payments where payment_id=original.id)
  or exists(select 1 from cp7_supplier_payment_correction.links where original_id=original.id)then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_ORDINARY_ONLY';end if;
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 if d->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)order by id for share;
 perform 1 from erp.chart_accounts where id in(select coa_account_id from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)
  union select account_id from erp.accounting_account_mappings where mapping_key='AP_SUPPLIER')order by id for share;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 -- A cash/master lock may itself have waited after the first source review.
 -- Rebind the full Native source/AP/journal token to the now-locked rows.
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 if d->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 -- The create path's dating rules: never in the future, and a changed time never
 -- before the goods arrived (money paid earlier is an advance, another document).
 if(p->'replacement'->>'payment_date')::timestamptz>statement_timestamp()then raise exception 'CP7_SUPPLIER_PAYMENT_DATE_FUTURE';end if;
 if(p->'replacement'->>'payment_date')::timestamptz<>original.payment_date and(p->'replacement'->>'payment_date')::timestamptz<h.physical_at then raise exception 'CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT';end if;
 if(p->'replacement'->>'amount')::numeric=original.amount and(p->'replacement'->>'payment_date')::timestamptz=original.payment_date
  and(p->'replacement'->>'cash_account_id')::uuid=original.cash_account_id then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_UNCHANGED';end if;
 perform erp.reverse_supplier_payment(original.id,btrim(p->>'change_reason'));
 select *into strict o from erp.journal_entries where source_type='SUPPLIER_PAYMENT'and source_id=original.id and reversal_of_id is null;
 select *into strict inv from erp.journal_entries where reversal_of_id=o.id and source_type='JOURNAL_REVERSAL'and source_id=o.id;
 if o.status<>'REVERSED'or inv.status<>'POSTED'then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 if o.economic_date<>inv.economic_date then
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inv.id;
  neutral:=erp.post_journal('SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL',original.id,inv.economic_date,'Koreksi pembayaran supplier: pindahkan waktu pembalikan | '||btrim(p->>'change_reason'),lines);
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inv.id;
  effective:=erp.post_journal('SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE',original.id,o.economic_date,'Koreksi pembayaran supplier: waktu ekonomi asal | '||btrim(p->>'change_reason'),lines);
 end if;
 -- The new row is only a Native DRAFT; Native posting decides AP capacity,
 -- account eligibility, canonical business date and closed-period treatment.
 insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id)
  values(h.id,'K-'||replace(p_request::text,'-',''),(p->'replacement'->>'payment_date')::timestamptz,
   (p->'replacement'->>'amount')::numeric,(p->'replacement'->>'cash_account_id')::uuid)returning id into replacement;
 perform erp.post_supplier_payment(replacement);
 if not exists(select 1 from erp.supplier_payments where id=replacement and purchase_id=h.id and status='POSTED')then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_POST_INCOMPLETE';end if;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 insert into cp7_supplier_payment_correction.links(original_id,replacement_id,purchase_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
  values(original.id,replacement,h.id,auth.uid(),p_request,btrim(p->>'change_reason'),neutral,effective)returning *into link;
 return jsonb_build_object('contract_version','cp7.supplier-payment-correction.v1','kind','COMMITTED_OUTCOME','action','CORRECT',
  'request_id',p_request,'request_payload',p,'purchase_id',h.id,'original_payment_id',original.id,'payment_id',replacement,
  'original_status','REVERSED','status','POSTED','link',cp7_supplier_payment_correction.link_value(link));
end $$;

create function cp7_supplier_payment_correction.command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;saved cp7_supplier_payment_correction.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_payment_correction.access_now();perform cp7_supplier_payment_correction.validate(p);
 if p_request is null then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_FIELDS';end if;
 insert into cp7_supplier_payment_correction.requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into saved from cp7_supplier_payment_correction.requests where actor=auth.uid()and request_id=p_request for update;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if saved.payload is distinct from p then raise exception 'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_supplier_payment_correction.context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p);
 r:=cp7_supplier_payment_correction.apply(p,p_request);
 delete from cp7_supplier_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 update cp7_supplier_payment_correction.requests set response=r where actor=auth.uid()and request_id=p_request;return r;
end $$;

alter function cp7_supplier_payment_correction.access_now()owner to cp7_invoice_read;
alter function cp7_supplier_payment_correction.validate(jsonb)owner to cp7_invoice_read;
alter function cp7_supplier_payment_correction.link_value(cp7_supplier_payment_correction.links)owner to postgres;
alter function cp7_supplier_payment_correction.workspace(jsonb)owner to postgres;
alter function cp7_supplier_payment_correction.protect_link()owner to postgres;
alter function cp7_supplier_payment_correction.apply(jsonb,uuid)owner to postgres;
alter function cp7_supplier_payment_correction.command(jsonb,uuid)owner to cp7_invoice_write;
revoke all on all functions in schema cp7_supplier_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_supplier_payment_correction.access_now(),cp7_supplier_payment_correction.validate(jsonb),cp7_supplier_payment_correction.apply(jsonb,uuid)to cp7_invoice_write;
grant execute on function cp7_supplier_payment_correction.access_now(),cp7_supplier_payment_correction.validate(jsonb),cp7_supplier_payment_correction.link_value(cp7_supplier_payment_correction.links)to postgres;
grant execute on function cp7_supplier_payment_correction.workspace(jsonb)to cp7_invoice_read;
grant insert on cp7_supplier_payment_correction.links to postgres;
revoke create on schema cp7_supplier_payment_correction from cp7_invoice_write;
grant create on schema public to cp7_invoice_write,cp7_invoice_read;
create function public.erp_cp7_correct_supplier_payment_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_payment_correction.command(p_payload,p_request)$$;
create function public.erp_cp7_get_supplier_payment_correction_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_payment_correction.workspace(p_query)$$;
alter function public.erp_cp7_correct_supplier_payment_v1(jsonb,uuid)owner to cp7_invoice_write;
alter function public.erp_cp7_get_supplier_payment_correction_v1(jsonb)owner to cp7_invoice_read;
revoke create on schema public from cp7_invoice_write,cp7_invoice_read;
revoke all on function public.erp_cp7_correct_supplier_payment_v1(jsonb,uuid),public.erp_cp7_get_supplier_payment_correction_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_correct_supplier_payment_v1(jsonb,uuid),public.erp_cp7_get_supplier_payment_correction_v1(jsonb)to authenticated;
