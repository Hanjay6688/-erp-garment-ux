-- OW06 / D17-14(5): one real supplier transfer, explicit receipt allocations.
-- Native payment rows retain the authoritative per-receipt AP subledger. Only
-- the declared current-transaction capability delegates their journals to one
-- aggregate Native journal. No clearing account, browser ERP DML or GUC bypass.
create schema cp7_supplier_transfer authorization postgres;
revoke all on schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;

create table cp7_supplier_transfer.requests_v1(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
create table cp7_supplier_transfer.transfers_v1(
 id uuid primary key,supplier_id uuid not null,number text not null unique,
 payment_date timestamptz not null,amount numeric(20,2)not null check(amount>0),
 cash_account_id uuid not null,note text not null check(length(btrim(note))between 5 and 500),
 status text not null check(status in('DRAFT','POSTED','REVERSED')),
 journal_id uuid,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(actor,request_id)
);
-- ERP identifiers deliberately have no cross-schema FK: no extra ERP RI
-- triggers are installed. The complete final-state proof checks every link.
create table cp7_supplier_transfer.allocations_v1(
 transfer_id uuid not null references cp7_supplier_transfer.transfers_v1,
 purchase_id uuid not null,payment_id uuid not null unique,
 amount numeric(20,2)not null check(amount>0),primary key(transfer_id,purchase_id)
);
create table cp7_supplier_transfer.corrections_v1(
 original_id uuid primary key references cp7_supplier_transfer.transfers_v1,
 replacement_id uuid not null unique references cp7_supplier_transfer.transfers_v1,
 actor uuid not null,request_id uuid not null,reason text not null,
 time_neutral_id uuid,effective_inverse_id uuid,
 recorded_at timestamptz not null default clock_timestamp(),
 check(original_id<>replacement_id),
 check((time_neutral_id is null)=(effective_inverse_id is null))
);
create table cp7_supplier_transfer.context_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,payload jsonb not null,transfer_id uuid,
 phase text not null check(phase in('LOCKED','POST','REVERSE','COMPLETE')),
 primary key(backend_pid,transaction_id)
);
alter table cp7_supplier_transfer.requests_v1 enable row level security;
alter table cp7_supplier_transfer.transfers_v1 enable row level security;
alter table cp7_supplier_transfer.allocations_v1 enable row level security;
alter table cp7_supplier_transfer.corrections_v1 enable row level security;
alter table cp7_supplier_transfer.context_v1 enable row level security;
create policy deny_requests on cp7_supplier_transfer.requests_v1 for all using(false)with check(false);
create policy deny_transfers on cp7_supplier_transfer.transfers_v1 for all using(false)with check(false);
create policy deny_allocations on cp7_supplier_transfer.allocations_v1 for all using(false)with check(false);
create policy deny_corrections on cp7_supplier_transfer.corrections_v1 for all using(false)with check(false);
create policy deny_context on cp7_supplier_transfer.context_v1 for all using(false)with check(false);
revoke all on all tables in schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;

create function cp7_supplier_transfer.access_now_v1(p_write boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_invoice.payment_access();
 if p_write and a->'reverse_payment'is distinct from'true'::jsonb then
  raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_DENIED';end if;
 return a;
end $$;

create function cp7_supplier_transfer.context_allows_v1(p_transfer uuid,p_phase text)returns boolean
language plpgsql volatile security definer set search_path=''as $$
begin
 return exists(select 1 from cp7_supplier_transfer.context_v1 c
  where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.transfer_id=p_transfer and c.phase=p_phase
  and exists(select 1 from cp7_supplier_transfer.requests_v1 r
    where r.actor=c.actor and r.request_id=c.request_id and r.payload=c.payload and r.response is null));
end $$;

create function cp7_supplier_transfer.deny_individual_v1(p_payment uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.payment_id=p_payment)then
  raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: pembayaran ini alokasi satu transfer; buka Transfer supplier untuk membatalkan atau mengoreksi seluruh transfer.';
 end if;
end $$;

-- Called only after all original Native posting validations have passed.
create function cp7_supplier_transfer.delegate_post_v1(p_payment uuid,p_cash_coa uuid)returns boolean
language plpgsql volatile security definer set search_path=''as $$
declare a cp7_supplier_transfer.allocations_v1;t cp7_supplier_transfer.transfers_v1;p erp.supplier_payments;
begin
 select *into a from cp7_supplier_transfer.allocations_v1 where payment_id=p_payment;
 if not found then return false;end if;
 perform cp7_supplier_transfer.access_now_v1(true);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=a.transfer_id;
 select *into strict p from erp.supplier_payments where id=p_payment;
 if not cp7_supplier_transfer.context_allows_v1(t.id,'POST')or t.status<>'DRAFT'
  or p.status<>'DRAFT'or p.purchase_id<>a.purchase_id or p.amount<>a.amount
  or p.payment_date<>t.payment_date or p.cash_account_id<>t.cash_account_id
  or p_cash_coa is distinct from(select coa_account_id from erp.cash_accounts where id=t.cash_account_id)
  or exists(select 1 from erp.initial_import_prepayment_payments where payment_id=p.id)then
  raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_PRIVATE_POST_REQUIRED';end if;
 return true;
end $$;

-- Native still owns child status, receipt status and its audit row. This helper
-- only reverses the one shared journal once, within the owning parent command.
create function cp7_supplier_transfer.delegate_reverse_v1(p_payment uuid,p_reason text)returns boolean
language plpgsql volatile security definer set search_path=''as $$
declare a cp7_supplier_transfer.allocations_v1;t cp7_supplier_transfer.transfers_v1;j erp.journal_entries;
begin
 select *into a from cp7_supplier_transfer.allocations_v1 where payment_id=p_payment;
 if not found then return false;end if;
 perform cp7_supplier_transfer.access_now_v1(true);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=a.transfer_id;
 if not cp7_supplier_transfer.context_allows_v1(t.id,'REVERSE')or t.status<>'POSTED'
  or not exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current()and btrim(c.payload->>'reason')=p_reason)then
  raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: balik seluruh Transfer supplier melalui dokumen asal.';end if;
 select *into strict j from erp.journal_entries where id=t.journal_id;
 if j.source_type<>'CP7_SUPPLIER_TRANSFER'or j.source_id<>t.id then raise exception 'CP7_SUPPLIER_TRANSFER_JOURNAL_CHANGED';end if;
 if j.status='POSTED'then perform erp.reverse_journal(j.id,p_reason);
 elsif j.status<>'REVERSED'or(select count(*)from erp.journal_entries where reversal_of_id=j.id and status='POSTED')<>1 then
  raise exception 'CP7_SUPPLIER_TRANSFER_INVERSE_INCOMPLETE';end if;
 return true;
end $$;

create function cp7_supplier_transfer.protect_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ident uuid;
begin
 if tg_op in('DELETE','TRUNCATE')then raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
 if tg_table_name='transfers_v1'then ident:=new.id;
 elsif tg_table_name='corrections_v1'then ident:=new.replacement_id;
 else ident:=new.transfer_id;end if;
 if tg_table_name='transfers_v1'then
  if tg_op='INSERT'then
   if new.status<>'DRAFT'or new.journal_id is not null or not cp7_supplier_transfer.context_allows_v1(ident,'POST')then
    raise exception 'CP7_SUPPLIER_TRANSFER_PRIVATE_DRAFT_REQUIRED';end if;
  elsif(to_jsonb(new)-array['status','journal_id'])is distinct from(to_jsonb(old)-array['status','journal_id'])
   or not((old.status='DRAFT'and new.status='POSTED'and old.journal_id is null and new.journal_id is not null
     and cp7_supplier_transfer.context_allows_v1(ident,'POST'))
    or(old.status='POSTED'and new.status='REVERSED'and new.journal_id=old.journal_id
     and cp7_supplier_transfer.context_allows_v1(ident,'REVERSE')))then
   raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
 elsif tg_op<>'INSERT'or not cp7_supplier_transfer.context_allows_v1(ident,'POST')then
  raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';
 end if;
 return new;
end $$;

create trigger transfer_private_write before insert or update or delete on cp7_supplier_transfer.transfers_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger transfer_no_truncate before truncate on cp7_supplier_transfer.transfers_v1 for each statement execute function cp7_supplier_transfer.protect_v1();
create trigger allocation_private_write before insert or update or delete on cp7_supplier_transfer.allocations_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger allocation_no_truncate before truncate on cp7_supplier_transfer.allocations_v1 for each statement execute function cp7_supplier_transfer.protect_v1();
create trigger correction_private_write before insert or update or delete on cp7_supplier_transfer.corrections_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger correction_no_truncate before truncate on cp7_supplier_transfer.corrections_v1 for each statement execute function cp7_supplier_transfer.protect_v1();

create function cp7_supplier_transfer.review_v1(p_supplier uuid,p_transfer uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s erp.suppliers;t cp7_supplier_transfer.transfers_v1;ap jsonb;state jsonb;
begin
 perform cp7_supplier_transfer.access_now_v1(false);
 select *into s from erp.suppliers where id=p_supplier;
 if s.id is null then raise exception 'CP7_SUPPLIER_TRANSFER_SUPPLIER_NOT_FOUND';end if;
 if p_transfer is not null then
  select *into t from cp7_supplier_transfer.transfers_v1 where id=p_transfer and supplier_id=p_supplier;
  if not found then raise exception 'CP7_SUPPLIER_TRANSFER_NOT_FOUND';end if;
 end if;
 ap:=public.erp_get_supplier_credit_v1(jsonb_build_object('supplier_id',p_supplier,'page',1))->'purchases';
 state:=jsonb_build_object('supplier',to_jsonb(s),'ap',ap,'transfer',to_jsonb(t),
  'headers',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.material_purchase_headers h where h.supplier_id=p_supplier),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.supplier_payments p join erp.material_purchase_headers h on h.id=p.purchase_id where h.supplier_id=p_supplier),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.purchase_id),'[]')from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=p_transfer),
  'journal',(select to_jsonb(j)from erp.journal_entries j where j.id=t.journal_id),
  'inverse',(select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]')from erp.journal_entries j where j.reversal_of_id=t.journal_id),
  'lines',(select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.id=t.journal_id or j.reversal_of_id=t.journal_id));
 return jsonb_build_object('supplier',jsonb_build_object('id',s.id,'name',s.supplier_name),
  'Native_AP',ap,'review_token',md5(state::text));
end $$;

create function cp7_supplier_transfer.detail_v1(p_transfer uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare t cp7_supplier_transfer.transfers_v1;j erp.journal_entries;inv erp.journal_entries;rows jsonb;
begin
 perform cp7_supplier_transfer.access_now_v1(false);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=p_transfer;
 perform cp7_supplier_transfer.assert_transfer_v1(t.id);
 select *into strict j from erp.journal_entries where id=t.journal_id;
 select *into inv from erp.journal_entries where reversal_of_id=j.id;
 select jsonb_agg(jsonb_build_object('purchase_id',a.purchase_id,'purchase_number',h.purchase_number,
  'payment_id',a.payment_id,'amount',a.amount::text)order by h.physical_at,h.id)into rows
  from cp7_supplier_transfer.allocations_v1 a join erp.material_purchase_headers h on h.id=a.purchase_id where a.transfer_id=t.id;
 return jsonb_build_object('id',t.id,'number',t.number,'supplier_id',t.supplier_id,'status',t.status,
  'payment_date',t.payment_date,'amount',t.amount::text,'cash_account_id',t.cash_account_id,
  'cash_name',(select cash_account_name from erp.cash_accounts where id=t.cash_account_id),'note',t.note,
  'journal',jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,'economic_date',j.economic_date,
   'accounting_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted),
  'inverse',case when inv.id is null then null else jsonb_build_object('id',inv.id,'number',inv.journal_number,'status',inv.status,
   'economic_date',inv.economic_date,'accounting_date',inv.transaction_date,'posting_at',inv.posting_at,'period_shifted',inv.period_shifted)end,'allocations',rows,
  'previous_id',(select original_id from cp7_supplier_transfer.corrections_v1 where replacement_id=t.id),
  'replacement_id',(select replacement_id from cp7_supplier_transfer.corrections_v1 where original_id=t.id));
end $$;

create function cp7_supplier_transfer.validate_v1(p jsonb)returns void
language plpgsql immutable security definer set search_path=''as $$
declare a jsonb;keys text[];
begin
 if jsonb_typeof(p)is distinct from'object'or p->>'action'not in('CREATE','CORRECT','REVERSE')then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 keys:=case when p->>'action'='REVERSE'then array['action','supplier_id','transfer_id','review_token','reason']
  when p->>'action'='CORRECT'then array['action','supplier_id','transfer_id','review_token','reason','amount','cash_account_id','payment_date','allocations']
  else array['action','supplier_id','review_token','reason','amount','cash_account_id','payment_date','allocations']end;
 if not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or exists(select 1 from jsonb_each(p)where key<>'allocations'and jsonb_typeof(value)<>'string')
  or coalesce(p->>'supplier_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'or length(btrim(p->>'reason'))not between 5 and 500
  or(p->>'action'<>'CREATE'and coalesce(p->>'transfer_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 if p->>'action'='REVERSE'then return;end if;
 if coalesce(p->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'or(p->>'amount')::numeric<=0
  or coalesce(p->>'cash_account_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'payment_date','')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.[0-9]{1,6})?(Z|[+-]\d{2}:\d{2})$'
  or jsonb_typeof(p->'allocations')is distinct from'array'then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 perform(p->>'payment_date')::timestamptz;
 if jsonb_array_length(p->'allocations')<1 then raise exception 'CP7_SUPPLIER_TRANSFER_ALLOCATIONS_REQUIRED';end if;
 for a in select value from jsonb_array_elements(p->'allocations')loop
  if jsonb_typeof(a)is distinct from'object'or not(a?&array['purchase_id','amount'])
   or(select count(*)from jsonb_object_keys(a))<>2 or exists(select 1 from jsonb_each(a)where jsonb_typeof(value)<>'string')
   or coalesce(a->>'purchase_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or coalesce(a->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'or(a->>'amount')::numeric<=0 then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 end loop;
 if(select count(distinct value->>'purchase_id')from jsonb_array_elements(p->'allocations'))<>jsonb_array_length(p->'allocations')then raise exception 'CP7_SUPPLIER_TRANSFER_DUPLICATE_RECEIPT';end if;
 if(select sum((value->>'amount')::numeric)from jsonb_array_elements(p->'allocations'))<>(p->>'amount')::numeric then raise exception 'CP7_SUPPLIER_TRANSFER_ALLOCATION_TOTAL';end if;
end $$;

-- End-state detector and guard. It is also wired into the existing Native
-- financial detector, so old/corrupt facts are checked without a write.
create function cp7_supplier_transfer.valid_transfer_v1(p_transfer uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_supplier_transfer.transfers_v1 t
  join erp.journal_entries j on j.id=t.journal_id join erp.cash_accounts c on c.id=t.cash_account_id
  where t.id=p_transfer and t.status in('POSTED','REVERSED')and j.source_type='CP7_SUPPLIER_TRANSFER'and j.source_id=t.id
   and j.reversal_of_id is null and j.status=t.status and j.economic_date=erp._cp3_business_date(t.payment_date)
   and(select count(*)from erp.journal_entries jj where jj.source_type='CP7_SUPPLIER_TRANSFER'and jj.source_id=t.id)=1
   and(select count(*)from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id)>0
   and(select sum(a.amount)from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id)=t.amount
   and not exists(select 1 from cp7_supplier_transfer.allocations_v1 a
    left join erp.supplier_payments p on p.id=a.payment_id left join erp.material_purchase_headers h on h.id=a.purchase_id
    where a.transfer_id=t.id and(p.id is null or h.id is null or p.purchase_id<>a.purchase_id or h.supplier_id<>t.supplier_id
     or p.status<>t.status or p.amount<>a.amount or p.cash_account_id<>t.cash_account_id or p.payment_date<>t.payment_date
     or exists(select 1 from erp.journal_entries jj where jj.source_type='SUPPLIER_PAYMENT'and jj.source_id=p.id)))
   and(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id)=2
   and exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=erp.account_id('AP_SUPPLIER')and l.debit=t.amount and l.credit=0)
   and exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=c.coa_account_id and l.debit=0 and l.credit=t.amount)
   and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
    and(l.customer_id is not null or l.vendor_id is not null or l.contractor_id is not null or l.po_id is not null or l.product_id is not null))
   and(select count(*)from erp.journal_entries v where v.reversal_of_id=j.id)=case when t.status='REVERSED'then 1 else 0 end
   and not exists(select 1 from erp.journal_entries v where v.reversal_of_id=j.id and(v.status<>'POSTED'or v.source_type<>'JOURNAL_REVERSAL'or v.source_id<>j.id
    or(select count(*)from erp.journal_lines l where l.journal_entry_id=v.id)<>2
    or exists(select 1 from erp.journal_lines l where l.journal_entry_id=v.id and not exists(
     select 1 from erp.journal_lines o where o.journal_entry_id=j.id and o.account_id=l.account_id and o.debit=l.credit and o.credit=l.debit
      and(o.customer_id,o.vendor_id,o.contractor_id,o.po_id,o.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))))
 )$$;

create function cp7_supplier_transfer.assert_transfer_v1(p_transfer uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_supplier_transfer.valid_transfer_v1(p_transfer)is distinct from true then raise exception 'CP7_SUPPLIER_TRANSFER_FINAL_STATE_INVALID';end if;
end $$;

create function cp7_supplier_transfer.final_guard_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if tg_table_name='context_v1'then
  if exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=new.backend_pid and c.transaction_id=new.transaction_id)then raise exception 'CP7_SUPPLIER_TRANSFER_CONTEXT_OPEN';end if;
 elsif tg_table_name='transfers_v1'then perform cp7_supplier_transfer.assert_transfer_v1(new.id);
 elsif tg_table_name='allocations_v1'then perform cp7_supplier_transfer.assert_transfer_v1(new.transfer_id);
 else
  perform cp7_supplier_transfer.assert_transfer_v1(new.original_id);perform cp7_supplier_transfer.assert_transfer_v1(new.replacement_id);
  if cp7_supplier_transfer.valid_correction_v1(new.original_id)is distinct from true then raise exception 'CP7_SUPPLIER_TRANSFER_CORRECTION_INVALID';end if;
 end if;
 return null;
end $$;
create constraint trigger final_transfer after insert or update on cp7_supplier_transfer.transfers_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger final_allocation after insert on cp7_supplier_transfer.allocations_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger final_correction after insert on cp7_supplier_transfer.corrections_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger closed_context after insert on cp7_supplier_transfer.context_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();

create function cp7_supplier_transfer.apply_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r jsonb;old cp7_supplier_transfer.transfers_v1;h erp.material_purchase_headers;
 alloc jsonb;ident uuid;child uuid;journal uuid;inverse erp.journal_entries;original erp.journal_entries;
 neutral uuid;effective uuid;lines jsonb;at timestamptz;cash uuid;item record;old_allocations jsonb;
begin
 a:=cp7_supplier_transfer.access_now_v1(true);perform cp7_supplier_transfer.validate_v1(p);
 if not exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.request_id=p_request and c.payload=p and c.phase='LOCKED')then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_PRIVATE_COMMAND_REQUIRED';end if;
 if p->>'action'<>'CREATE'then
  select *into old from cp7_supplier_transfer.transfers_v1 where id=(p->>'transfer_id')::uuid for update nowait;
  if old.id is null or old.supplier_id<>(p->>'supplier_id')::uuid or old.status<>'POSTED'then raise exception 'CP7_SUPPLIER_TRANSFER_POSTED_REQUIRED';end if;
  perform cp7_supplier_transfer.assert_transfer_v1(old.id);
 end if;
 -- Legacy writers lock a payment before a receipt and can later need the
 -- global envelope. Do not wait on their rows while holding that envelope.
 perform 1 from erp.supplier_payments s where s.purchase_id in(
   select(value->>'purchase_id')::uuid from jsonb_array_elements(coalesce(p->'allocations','[]'))
   union select x.purchase_id from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id)
   order by s.id for update nowait;
 perform 1 from erp.material_purchase_headers s where s.id in(
   select(value->>'purchase_id')::uuid from jsonb_array_elements(coalesce(p->'allocations','[]'))
   union select x.purchase_id from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id)
   order by s.id for update nowait;
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 r:=cp7_supplier_transfer.review_v1((p->>'supplier_id')::uuid,old.id);
 if r->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_TRANSFER_STALE_REVIEW';end if;
 if p->>'action'='CORRECT'then
  select jsonb_agg(jsonb_build_object('purchase_id',x.purchase_id,'amount',x.amount::text)order by x.purchase_id)into old_allocations from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id;
  select jsonb_agg(value order by value->>'purchase_id')into alloc from jsonb_array_elements(p->'allocations');
  if old_allocations=alloc and old.amount=(p->>'amount')::numeric and old.payment_date=(p->>'payment_date')::timestamptz and old.cash_account_id=(p->>'cash_account_id')::uuid then raise exception 'CP7_SUPPLIER_TRANSFER_CORRECTION_UNCHANGED';end if;
 end if;
 perform cp7_guard.begin_compound('OW06 supplier transfer');
 if old.id is not null then
  update cp7_supplier_transfer.context_v1 set phase='REVERSE',transfer_id=old.id where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  for item in select payment_id from cp7_supplier_transfer.allocations_v1 where transfer_id=old.id order by payment_id loop
   perform erp.reverse_supplier_payment(item.payment_id,btrim(p->>'reason'));
  end loop;
  update cp7_supplier_transfer.transfers_v1 set status='REVERSED'where id=old.id;
  if p->>'action'='CORRECT'then
   select *into strict original from erp.journal_entries where id=old.journal_id;
   select *into strict inverse from erp.journal_entries where reversal_of_id=original.id;
   -- Same economic-date restatement as the existing supplier correction.
   if original.economic_date<>inverse.economic_date then
    select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
     'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inverse.id;
    neutral:=erp.post_journal('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL',old.id,inverse.economic_date,'Koreksi transfer supplier: waktu pembalikan | '||btrim(p->>'reason'),lines);
    select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
     'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inverse.id;
    effective:=erp.post_journal('CP7_SUPPLIER_TRANSFER_EFFECTIVE',old.id,original.economic_date,'Koreksi transfer supplier: waktu ekonomi asal | '||btrim(p->>'reason'),lines);
   end if;
  end if;
 end if;
 if p->>'action'<>'REVERSE'then
  at:=(p->>'payment_date')::timestamptz;
  if at>statement_timestamp()then raise exception 'CP7_SUPPLIER_TRANSFER_DATE_FUTURE';end if;
  lock table erp.accounting_account_mappings in share mode nowait;
  perform 1 from erp.cash_accounts where id=(p->>'cash_account_id')::uuid for share nowait;
  perform 1 from erp.chart_accounts where id in(
   (select coa_account_id from erp.cash_accounts where id=(p->>'cash_account_id')::uuid),erp.account_id('AP_SUPPLIER'))order by id for share nowait;
  select c.coa_account_id into cash from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
   where c.id=(p->>'cash_account_id')::uuid and c.is_active and ca.is_active and ca.is_postable;
  if cash is null then raise exception 'CP7_SUPPLIER_TRANSFER_CASH_ACCOUNT_INACTIVE';end if;
  ident:=gen_random_uuid();
  update cp7_supplier_transfer.context_v1 set phase='POST',transfer_id=ident where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  insert into cp7_supplier_transfer.transfers_v1(id,supplier_id,number,payment_date,amount,cash_account_id,note,status,actor,request_id)
   values(ident,(p->>'supplier_id')::uuid,'TRS-'||replace(p_request::text,'-',''),at,(p->>'amount')::numeric,(p->>'cash_account_id')::uuid,btrim(p->>'reason'),'DRAFT',auth.uid(),p_request);
  for alloc in select value from jsonb_array_elements(p->'allocations')order by value->>'purchase_id'loop
   select *into h from erp.material_purchase_headers where id=(alloc->>'purchase_id')::uuid;
   if h.id is null or h.status<>'POSTED'or h.supplier_id<>(p->>'supplier_id')::uuid then raise exception 'CP7_SUPPLIER_TRANSFER_SAME_SUPPLIER_POSTED_RECEIPTS_REQUIRED';end if;
   if at<h.physical_at then raise exception 'CP7_SUPPLIER_TRANSFER_BEFORE_RECEIPT';end if;
   if(alloc->>'amount')::numeric>round(erp.material_purchase_final_ap_total(h.id),2)-coalesce((select sum(s.amount)from erp.supplier_payments s where s.purchase_id=h.id and s.status='POSTED'),0)then raise exception 'CP7_SUPPLIER_TRANSFER_EXCEEDS_REMAINING';end if;
   child:=gen_random_uuid();
   insert into erp.supplier_payments(id,purchase_id,payment_number,payment_date,amount,cash_account_id,notes,status,created_by)
    values(child,h.id,'TRS-A-'||replace(child::text,'-',''),at,(alloc->>'amount')::numeric,(p->>'cash_account_id')::uuid,btrim(p->>'reason'),'DRAFT',erp.current_app_user_id());
   insert into cp7_supplier_transfer.allocations_v1 values(ident,h.id,child,(alloc->>'amount')::numeric);
   perform erp.post_supplier_payment(child);
  end loop;
  journal:=erp.post_journal('CP7_SUPPLIER_TRANSFER',ident,erp._cp3_business_date(at),'Transfer supplier '||(select number from cp7_supplier_transfer.transfers_v1 where id=ident),
   jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',(p->>'amount')::numeric,'credit',0),jsonb_build_object('account_id',cash,'debit',0,'credit',(p->>'amount')::numeric)));
  update cp7_supplier_transfer.transfers_v1 set status='POSTED',journal_id=journal where id=ident;
  if old.id is not null then insert into cp7_supplier_transfer.corrections_v1(original_id,replacement_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
   values(old.id,ident,auth.uid(),p_request,btrim(p->>'reason'),neutral,effective);end if;
  perform cp7_supplier_transfer.assert_transfer_v1(ident);
 else ident:=old.id;end if;
 if old.id is not null then perform cp7_supplier_transfer.assert_transfer_v1(old.id);end if;
 perform cp7_guard.end_compound();
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-transfer-outcome.v1','kind','COMMITTED_OUTCOME','action',p->>'action',
  'request_id',p_request,'request_payload',p,'supplier_id',p->>'supplier_id','transfer_id',ident,
  'original_transfer_id',old.id,'status',case when p->>'action'='REVERSE'then'REVERSED'else'POSTED'end);
end $$;

create function cp7_supplier_transfer.command_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;s cp7_supplier_transfer.requests_v1;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_transfer.access_now_v1(true);perform cp7_supplier_transfer.validate_v1(p);
 if p_request is null then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 insert into cp7_supplier_transfer.requests_v1 values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict s from cp7_supplier_transfer.requests_v1 where actor=auth.uid()and request_id=p_request for update;
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 if s.payload is distinct from p then raise exception 'CP7_SUPPLIER_TRANSFER_REQUEST_CHANGED';end if;
 if s.response is not null then return s.response;end if;
 insert into cp7_supplier_transfer.context_v1 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p,null,'LOCKED');
 r:=cp7_supplier_transfer.apply_v1(p,p_request);
 delete from cp7_supplier_transfer.context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 update cp7_supplier_transfer.requests_v1 set response=r where actor=auth.uid()and request_id=p_request;
 return r;
end $$;

revoke all on all functions in schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;
create function public.erp_cp7_save_supplier_transfer_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_transfer.command_v1(p_payload,p_request)$$;
revoke all on function public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)to authenticated;
