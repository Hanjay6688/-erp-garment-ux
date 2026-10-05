-- An ordinary payment is corrected by one Native inverse and one Native post
-- in the same transaction. Native allocation-replacement and advance lineage
-- keep their separate meaning; no posted payment field is overwritten.
create schema cp7_payment_correction authorization cp7_sales_read;
revoke all on schema cp7_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_payment_correction to cp7_sales_write;
grant usage on schema cp7_payment_correction to postgres;
create table cp7_payment_correction.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 expected_version text not null,response jsonb,primary key(actor,request_id)
);
create table cp7_payment_correction.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,payload jsonb not null,expected_version text not null,
 primary key(backend_pid,transaction_id)
);
create table cp7_payment_correction.links(
 original_id uuid primary key references erp.sales_payments(id),
 replacement_id uuid not null unique references erp.sales_payments(id),
 sale_id uuid not null references erp.sales_headers(id),actor uuid not null,
 request_id uuid not null,reason text not null,
 time_neutral_id uuid references erp.journal_entries(id),
 effective_inverse_id uuid references erp.journal_entries(id),
 recorded_at timestamptz not null default statement_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),
 check((time_neutral_id is null)=(effective_inverse_id is null)),unique(actor,request_id)
);
alter table cp7_payment_correction.requests owner to cp7_sales_write;
alter table cp7_payment_correction.context owner to cp7_sales_write;
alter table cp7_payment_correction.links owner to cp7_sales_write;
alter table cp7_payment_correction.requests enable row level security;
alter table cp7_payment_correction.context enable row level security;
alter table cp7_payment_correction.links enable row level security;
create policy payment_correction_requests_deny on cp7_payment_correction.requests for all to public using(false)with check(false);
create policy payment_correction_context_deny on cp7_payment_correction.context for all to public using(false)with check(false);
create policy payment_correction_links_deny on cp7_payment_correction.links for all to public using(false)with check(false);
revoke all on all tables in schema cp7_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_payment_correction.context,cp7_payment_correction.links to postgres;

create function cp7_payment_correction.access_now()returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_sales.command_access('PAYMENT');
 if cp7_sales.command_access('PAYMENT_REVERSE')is distinct from a then
  raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 return a;
end $$;

create function cp7_payment_correction.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['sale_id','payment_id','review_token','replacement','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>5 then raise exception 'CP7_PAYMENT_CORRECTION_FIELDS';end if;
 perform cp7_sales.validate_payment(p-'replacement',true);
 if jsonb_typeof(p->'replacement')is distinct from'object'
  or not(p->'replacement'?&array['payment_number','payment_date','amount','cash_account_id','payment_method','reference_number','notes'])
  or(select count(*)from jsonb_object_keys(p->'replacement'))<>7 then raise exception 'CP7_PAYMENT_CORRECTION_FIELDS';end if;
 perform cp7_sales.validate_payment((p-'replacement'-'payment_id')||(p->'replacement'),false);
end $$;

create function cp7_payment_correction.document(p erp.sales_payments)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',p.id,'number',p.payment_number,'physical_at',p.payment_date,
  'amount',p.amount::text,'cash_account_id',p.cash_account_id,
  'cash_account_name',(select cash_account_name from erp.cash_accounts where id=p.cash_account_id),
  'method',p.payment_method,'reference',p.reference_number,'notes',p.notes,
  'status',p.status,'replaces_payment_id',p.replaces_payment_id)
$$;
create function cp7_payment_correction.link_value(p cp7_payment_correction.links)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('original_id',p.original_id,'replacement_id',p.replacement_id,
  'sale_id',p.sale_id,'actor_scope_id',p.actor,'request_id',p.request_id,'reason',p.reason,
  'recorded_at',p.recorded_at,'time_restatement',case when p.time_neutral_id is null then null else(
   select jsonb_build_object('neutral_journal_id',n.id,'neutral_number',n.journal_number,
    'neutral_economic_date',n.economic_date,'neutral_transaction_date',n.transaction_date,
    'effective_journal_id',e.id,'effective_number',e.journal_number,
    'effective_economic_date',e.economic_date,'effective_transaction_date',e.transaction_date)
   from erp.journal_entries n join erp.journal_entries e on e.id=p.effective_inverse_id
   where n.id=p.time_neutral_id)end)
$$;

-- The public reader delegates only this guarded, source-bound read to the
-- existing non-superuser Native owner. No new ERP table grant is needed.
create function cp7_payment_correction.workspace(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare original erp.sales_payments;h erp.sales_headers;cash jsonb;previous jsonb:='null';following jsonb:='null';
 prev cp7_payment_correction.links;nxt cp7_payment_correction.links;eligible boolean;a jsonb;
begin
 if not cp7_sales.access_now()or not erp.has_permission('sales.payment.view')then
  raise exception using errcode='42501',message='CP7_SALES_CASH_DENIED';end if;
 a:=erp.get_my_access_v1();
 if jsonb_typeof(p_query)is distinct from'object'or not(p_query?&array['sale_id','payment_id'])
  or exists(select 1 from jsonb_object_keys(p_query)x where x not in('sale_id','payment_id','bank_q','bank_offset','bank_limit'))
  or jsonb_typeof(p_query->'sale_id')is distinct from'string'or jsonb_typeof(p_query->'payment_id')is distinct from'string'
  or coalesce(p_query->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_query->>'payment_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  raise exception 'CP7_PAYMENT_CORRECTION_QUERY';end if;
 cash:=cp7_sales.cash_workspace((p_query-'payment_id')||jsonb_build_object('payment_limit',1));
 select *into original from erp.sales_payments where id=(p_query->>'payment_id')::uuid and sale_id=(p_query->>'sale_id')::uuid;
 if original.id is null then raise exception 'CP7_SALES_PAYMENT_SOURCE_CHANGED';end if;
 select *into strict h from erp.sales_headers where id=original.sale_id;
 eligible:=original.status='POSTED'and h.status in('POSTED','PARTIAL_PAID','PAID')
  and length(btrim(original.payment_number))between 1 and 60
  and original.cash_account_id is not null and original.replaces_payment_id is null
  and original.payment_method in('CASH','BANK_TRANSFER')
  and not exists(select 1 from erp.initial_import_prepayment_payments where sales_payment_id=original.id)
  and not exists(select 1 from cp7_payment_correction.links where original_id=original.id);
 select *into prev from cp7_payment_correction.links where replacement_id=original.id and sale_id=h.id;
 select *into nxt from cp7_payment_correction.links where original_id=original.id and sale_id=h.id;
 if prev.original_id is not null then previous:=jsonb_build_object('link',cp7_payment_correction.link_value(prev),
  'document',(select cp7_payment_correction.document(p)from erp.sales_payments p where id=prev.original_id and sale_id=h.id));end if;
 if nxt.original_id is not null then following:=jsonb_build_object('link',cp7_payment_correction.link_value(nxt),
  'document',(select cp7_payment_correction.document(p)from erp.sales_payments p where id=nxt.replacement_id and sale_id=h.id));end if;
 if erp.get_my_access_v1()is distinct from a or not cp7_sales.access_now()or not erp.has_permission('sales.payment.view')then
  raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sales-payment-correction-workspace.v1',
  'captured_at',statement_timestamp(),'sale_id',h.id,'row_version',h.row_version::text,
  'review_token',cp7_sales.review_token(h.id),'document',cp7_payment_correction.document(original),
  'eligible',coalesce(eligible,false),'previous',previous,'next',following,'cash_accounts',cash->'cash_accounts');
end $$;

create function cp7_payment_correction.protect_link()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if tg_op<>'INSERT'then raise exception 'CP7_PAYMENT_CORRECTION_LINK_IMMUTABLE';end if;
 if not exists(select 1 from cp7_payment_correction.context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.actor=auth.uid()and c.actor=new.actor
  and c.request_id=new.request_id and c.payload->>'sale_id'=new.sale_id::text
  and c.payload->>'payment_id'=new.original_id::text and btrim(c.payload->>'change_reason')=new.reason)
  or not exists(select 1 from erp.sales_payments where id=new.original_id and sale_id=new.sale_id and status='REVERSED')
  or not exists(select 1 from erp.sales_payments where id=new.replacement_id and sale_id=new.sale_id and status='POSTED'and replaces_payment_id is null)then
  raise exception using errcode='42501',message='CP7_PAYMENT_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 if new.time_neutral_id is not null and(not exists(select 1 from erp.journal_entries where id=new.time_neutral_id and source_type='PAYMENT_CORRECTION_TIME_NEUTRAL'and source_id=new.original_id and status='POSTED')
  or not exists(select 1 from erp.journal_entries where id=new.effective_inverse_id and source_type='PAYMENT_CORRECTION_EFFECTIVE'and source_id=new.original_id and status='POSTED'))then
  raise exception 'CP7_PAYMENT_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 return new;
end $$;
create trigger payment_correction_link_immutable before insert or update or delete on cp7_payment_correction.links
 for each row execute function cp7_payment_correction.protect_link();
create trigger payment_correction_link_no_truncate before truncate on cp7_payment_correction.links
 for each statement execute function cp7_payment_correction.protect_link();

create function cp7_payment_correction.apply(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;original erp.sales_payments;h erp.sales_headers;intent jsonb;posted jsonb;link cp7_payment_correction.links;
 original_journal erp.journal_entries;inverse_journal erp.journal_entries;lines jsonb;neutral uuid;effective uuid;
begin
 a:=cp7_payment_correction.access_now();perform cp7_payment_correction.validate(p);
 if not exists(select 1 from cp7_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request and payload=p and expected_version=p_expected)
  or exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception using errcode='42501',message='CP7_PAYMENT_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.sales_payments where sale_id=(p->>'sale_id')::uuid order by id for update;
 select *into h from erp.sales_headers where id=(p->>'sale_id')::uuid for update;
 select *into original from erp.sales_payments where id=(p->>'payment_id')::uuid;
 if h.id is null or original.id is null or original.sale_id<>h.id then raise exception 'CP7_SALES_PAYMENT_SOURCE_CHANGED';end if;
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if h.row_version::text is distinct from p_expected or cp7_sales.review_token(h.id)is distinct from p->>'review_token'then raise exception 'CP7_SALES_REVIEW_CHANGED';end if;
 if original.status<>'POSTED'or h.status not in('POSTED','PARTIAL_PAID','PAID')or original.cash_account_id is null
  or original.replaces_payment_id is not null or original.payment_method is null or original.payment_method not in('CASH','BANK_TRANSFER')
  or exists(select 1 from erp.initial_import_prepayment_payments where sales_payment_id=original.id)
  or exists(select 1 from cp7_payment_correction.links where original_id=original.id)then raise exception 'CP7_PAYMENT_CORRECTION_ORDINARY_ONLY';end if;
 if p->'replacement'->>'payment_number'is distinct from original.payment_number then raise exception 'CP7_PAYMENT_CORRECTION_NUMBER';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)order by id for share;
 perform 1 from erp.chart_accounts where id in(
  select coa_account_id from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)
  union select account_id from erp.accounting_account_mappings where mapping_key='AR_CUSTOMER')order by id for share;
 if (p->'replacement'->>'amount')::numeric=original.amount
  and(p->'replacement'->>'payment_date')::timestamptz=original.payment_date
  and(p->'replacement'->>'cash_account_id')::uuid=original.cash_account_id
  and p->'replacement'->>'payment_method'is not distinct from original.payment_method
  and p->'replacement'->>'reference_number'is not distinct from original.reference_number
  and p->'replacement'->>'notes'is not distinct from original.notes then raise exception 'CP7_PAYMENT_CORRECTION_UNCHANGED';end if;
 -- Reuse both owning actions without extending their Native guard admission.
 -- The original review is checked again by the inverse; the replacement gets
 -- the real post-inverse revision/token. No client guesses the next version.
 intent:=p-'replacement';
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'PAYMENT_REVERSE');
 perform cp7_sales.apply_command('PAYMENT_REVERSE',intent,p_request,p_expected);
 select *into strict original_journal from erp.journal_entries where source_type='SALES_PAYMENT'and source_id=original.id and reversal_of_id is null;
 select *into strict inverse_journal from erp.journal_entries where reversal_of_id=original_journal.id and source_type='JOURNAL_REVERSAL'and source_id=original_journal.id;
 if original_journal.status<>'REVERSED'or inverse_journal.status<>'POSTED'then raise exception 'CP7_PAYMENT_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 if original_journal.economic_date<>inverse_journal.economic_date then
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines
   from erp.journal_lines l where l.journal_entry_id=inverse_journal.id;
  neutral:=erp.post_journal('PAYMENT_CORRECTION_TIME_NEUTRAL',original.id,inverse_journal.economic_date,'Koreksi pembayaran: pindahkan waktu ekonomi pembalikan | '||btrim(p->>'change_reason'),lines);
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines
   from erp.journal_lines l where l.journal_entry_id=inverse_journal.id;
  effective:=erp.post_journal('PAYMENT_CORRECTION_EFFECTIVE',original.id,original_journal.economic_date,'Koreksi pembayaran: waktu ekonomi kejadian asal | '||btrim(p->>'change_reason'),lines);
 end if;
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 select *into strict h from erp.sales_headers where id=h.id;
 intent:=(p-'replacement'-'payment_id')||(p->'replacement')||jsonb_build_object(
  'review_token',cp7_sales.review_token(h.id),'payment_number',left(original.payment_number,20)||' · K-'||replace(p_request::text,'-',''));
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'PAYMENT');
 posted:=cp7_sales.apply_command('PAYMENT',intent,p_request,h.row_version::text);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 insert into cp7_payment_correction.links(original_id,replacement_id,sale_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
  values(original.id,(posted->>'payment_id')::uuid,h.id,auth.uid(),p_request,btrim(p->>'change_reason'),neutral,effective)returning *into link;
 return posted||jsonb_build_object('original_payment_id',original.id,'original_payment_status','REVERSED','link',cp7_payment_correction.link_value(link));
end $$;

create function cp7_payment_correction.command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;saved cp7_payment_correction.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_payment_correction.access_now();perform cp7_payment_correction.validate(p);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 insert into cp7_payment_correction.requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into saved from cp7_payment_correction.requests where actor=auth.uid()and request_id=p_request for update;
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if saved.payload is distinct from p or saved.expected_version is distinct from p_expected then raise exception 'CP7_SALES_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_payment_correction.context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p,p_expected);
 r:=cp7_payment_correction.apply(p,p_request,p_expected);
 delete from cp7_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.sales-payment-correction.v1','kind','COMMITTED_OUTCOME','action','PAYMENT_CORRECT','request_id',p_request);
 update cp7_payment_correction.requests set response=r where actor=auth.uid()and request_id=p_request;return r;
end $$;

alter function cp7_payment_correction.access_now()owner to cp7_sales_read;
alter function cp7_payment_correction.validate(jsonb)owner to cp7_sales_read;
alter function cp7_payment_correction.document(erp.sales_payments)owner to cp7_sales_read;
alter function cp7_payment_correction.link_value(cp7_payment_correction.links)owner to postgres;
alter function cp7_payment_correction.workspace(jsonb)owner to postgres;
alter function cp7_payment_correction.protect_link()owner to postgres;
alter function cp7_payment_correction.apply(jsonb,uuid,text)owner to postgres;
alter function cp7_payment_correction.command(jsonb,uuid,text)owner to cp7_sales_write;
revoke all on all functions in schema cp7_payment_correction from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_payment_correction.access_now(),cp7_payment_correction.validate(jsonb),cp7_payment_correction.apply(jsonb,uuid,text)to cp7_sales_write;
grant execute on function cp7_payment_correction.access_now(),cp7_payment_correction.validate(jsonb),cp7_payment_correction.document(erp.sales_payments),cp7_payment_correction.link_value(cp7_payment_correction.links)to postgres;
grant execute on function cp7_sales.validate_payment(jsonb,boolean),cp7_sales.access_now(),cp7_sales.cash_workspace(jsonb)to postgres;
grant insert,delete on cp7_sales.command_context to postgres;
grant insert on cp7_payment_correction.links to postgres;
grant execute on function cp7_payment_correction.link_value(cp7_payment_correction.links)to cp7_sales_write;
grant execute on function cp7_payment_correction.workspace(jsonb)to cp7_sales_read;
revoke create on schema cp7_payment_correction from cp7_sales_write;
grant create on schema public to cp7_sales_write;
create function public.erp_cp7_correct_sales_payment_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_payment_correction.command(p_payload,p_request,p_expected)$$;
alter function public.erp_cp7_correct_sales_payment_v1(jsonb,uuid,text)owner to cp7_sales_write;
revoke create on schema public from cp7_sales_write;
grant create on schema public to cp7_sales_read;
create function public.erp_cp7_get_sales_payment_correction_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_payment_correction.workspace(p_query)$$;
alter function public.erp_cp7_get_sales_payment_correction_v1(jsonb)owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on function public.erp_cp7_correct_sales_payment_v1(jsonb,uuid,text),public.erp_cp7_get_sales_payment_correction_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_correct_sales_payment_v1(jsonb,uuid,text),public.erp_cp7_get_sales_payment_correction_v1(jsonb)to authenticated;
