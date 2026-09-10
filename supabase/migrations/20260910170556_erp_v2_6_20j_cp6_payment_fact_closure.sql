-- ERP Garment v2.6.20j / independent CP6 I audit closure.
-- VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
--
-- I-01 is closed by an append-only posted-payment fact that preserves the
-- original invoice, customer, amount, cash account, business clock, journal,
-- and complete payment snapshot. Allocation correction is explicit: reverse
-- the old payment, then post one linked replacement for another invoice owned
-- by the same customer with the same cash fact.
-- I-02 is closed by a separate append-only reversal fact. Both economic and
-- ledger dates are reconciled to the exact inverse journal, and reversal cannot
-- precede the original posting chronology.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_v2620j$
declare
  r record;
  c record;
  v_actual text;
  v_count bigint;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20i') then
    raise exception 'ERP v2.6.20j requires exact v2.6.20i first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20j')
     or to_regclass('erp.cp6_v2620j_rollback_capsule') is not null
     or to_regclass('erp.sales_payment_posting_facts') is not null
     or to_regclass('erp.sales_payment_reversal_facts') is not null
     or exists(select 1 from information_schema.columns
       where table_schema='erp' and table_name='sales_payments'
         and column_name='replaces_payment_id') then
    raise exception 'ERP v2.6.20j already recorded or prior repair residue exists; never replay';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations m
      where m.name='erp_v2_6_20i_cp6_h2_audit_closure'
        and encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683',
             '60fa613e31d13f7db3efff7f1e0daee956886afe2676c61ee05661bb55211a1c'))<>1 then
    raise exception 'ERP v2.6.20j requires one exact I platform-ledger row';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20j refuses an active CP6 execution context';
  end if;
  if (select count(*) from erp.cp6_v2620i_rollback_capsule)<>1 then
    raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: I capsule cardinality';
  end if;
  select i.*,
    encode(extensions.digest(convert_to(i.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
    encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
    pg_get_userbyid(p.proowner) installed_owner,
    case when p.proacl is null then null else
      array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
  into c from erp.cp6_v2620i_rollback_capsule i
  left join pg_proc p on p.oid=to_regprocedure(i.object_regidentity);
  if c.object_regidentity is distinct from 'erp.run_v268_financial_report_checks()'
     or c.definition_sha256 is distinct from '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
     or c.definition_actual is distinct from '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
     or c.installed_definition_sha256 is distinct from 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1'
     or c.installed_actual is distinct from 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1'
     or c.owner_snapshot is distinct from 'postgres'
     or c.installed_owner is distinct from 'postgres'
     or c.acl_snapshot is distinct from
       array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]
     or c.installed_acl is distinct from c.acl_snapshot then
    raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: I capsule/function';
  end if;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_sales_payment(uuid,text)','09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6',
      array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity);
    if v_actual is distinct from r.sha256
       or (select pg_get_userbyid(p.proowner) from pg_proc p
           where p.oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select case when p.proacl is null then null else
             array(select a::text from unnest(p.proacl) a order by a::text) end
           from pg_proc p where p.oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: J predecessor %',r.identity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v268_financial_report_checks()
  where check_name='V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH';
  if v_count is distinct from 0 then
    raise exception 'ERP v2.6.20j refuses dirty I payment lineage: % issue(s)',v_count;
  end if;
end
$guard_v2620j$;

create table erp.cp6_v2620j_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp(),
  boundary_snapshot jsonb
);
alter table erp.cp6_v2620j_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620j_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620j_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.post_sales_payment(uuid)'::regprocedure,
  'erp.reverse_sales_payment(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure
);

alter table erp.sales_payments add column replaces_payment_id uuid;
alter table erp.sales_payments add constraint sales_payments_replaces_not_self
  check(replaces_payment_id is null or replaces_payment_id<>id);
alter table erp.sales_payments add constraint sales_payments_replaces_payment_fkey
  foreign key(replaces_payment_id) references erp.sales_payments(id) on delete restrict;
create unique index uq_sales_payments_one_replacement
  on erp.sales_payments(replaces_payment_id) where replaces_payment_id is not null;

create table erp.sales_payment_posting_facts(
  payment_id uuid primary key references erp.sales_payments(id) on delete restrict,
  sale_id uuid not null references erp.sales_headers(id) on delete restrict,
  customer_id uuid not null references erp.customers(id) on delete restrict,
  payment_number varchar(60) not null,
  payment_date timestamptz not null,
  amount numeric(20,2) not null check(amount>0),
  cash_account_id uuid not null references erp.cash_accounts(id) on delete restrict,
  original_journal_entry_id uuid not null unique references erp.journal_entries(id) on delete restrict,
  journal_economic_date date not null,
  journal_transaction_date date not null,
  journal_posting_at timestamptz not null,
  replaces_payment_id uuid unique,
  predecessor_reversal_journal_id uuid unique references erp.journal_entries(id) on delete restrict,
  payment_snapshot jsonb not null,
  lineage_sha256 text not null check(lineage_sha256~'^[0-9a-f]{64}$'),
  recorded_at timestamptz not null default clock_timestamp(),
  recorded_by uuid references erp.app_users(id),
  constraint sales_payment_posting_fact_replacement_pair check(
    (replaces_payment_id is null)=(predecessor_reversal_journal_id is null)
  )
);
alter table erp.sales_payment_posting_facts add constraint sales_payment_posting_fact_predecessor_fkey
  foreign key(replaces_payment_id) references erp.sales_payment_posting_facts(payment_id) on delete restrict;
alter table erp.sales_payment_posting_facts enable row level security;
revoke all on table erp.sales_payment_posting_facts from public,anon,authenticated,service_role;

create table erp.sales_payment_reversal_facts(
  payment_id uuid primary key references erp.sales_payment_posting_facts(payment_id) on delete restrict,
  original_journal_entry_id uuid not null unique references erp.journal_entries(id) on delete restrict,
  reversal_journal_entry_id uuid not null unique references erp.journal_entries(id) on delete restrict,
  reversal_economic_date date not null,
  reversal_transaction_date date not null,
  reversal_posting_at timestamptz not null,
  lineage_sha256 text not null check(lineage_sha256~'^[0-9a-f]{64}$'),
  recorded_at timestamptz not null default clock_timestamp(),
  recorded_by uuid references erp.app_users(id)
);
alter table erp.sales_payment_reversal_facts enable row level security;
revoke all on table erp.sales_payment_reversal_facts from public,anon,authenticated,service_role;

-- Existing I-clean history becomes the initial independent fact ledger. Any
-- ambiguity was rejected by the I oracle before this backfill is allowed.
with prepared as(
  select p.id payment_id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,
    p.amount,p.cash_account_id,o.id original_journal_entry_id,
    o.economic_date journal_economic_date,o.transaction_date journal_transaction_date,
    o.posting_at journal_posting_at,to_jsonb(p)-'status' payment_snapshot,p.created_by recorded_by
  from erp.sales_payments p
  join erp.sales_headers h on h.id=p.sale_id
  join erp.journal_entries o on o.source_type='SALES_PAYMENT' and o.source_id=p.id
  where p.status in('POSTED','REVERSED')
)
insert into erp.sales_payment_posting_facts(
  payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,
  original_journal_entry_id,journal_economic_date,journal_transaction_date,
  journal_posting_at,replaces_payment_id,predecessor_reversal_journal_id,
  payment_snapshot,lineage_sha256,recorded_by
)
select x.*,encode(extensions.digest(convert_to(jsonb_build_array(
  x.payment_id,x.sale_id,x.customer_id,x.payment_number,x.payment_date,x.amount,
  x.cash_account_id,x.original_journal_entry_id,x.journal_economic_date,
  x.journal_transaction_date,x.journal_posting_at,null,null,x.payment_snapshot
)::text,'UTF8'),'sha256'),'hex'),p.recorded_by
from(
  select payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,
    original_journal_entry_id,journal_economic_date,journal_transaction_date,
    journal_posting_at,null::uuid replaces_payment_id,
    null::uuid predecessor_reversal_journal_id,payment_snapshot
  from prepared
) x join prepared p using(payment_id);

with prepared as(
  select p.id payment_id,o.id original_journal_entry_id,r.id reversal_journal_entry_id,
    r.economic_date reversal_economic_date,r.transaction_date reversal_transaction_date,
    r.posting_at reversal_posting_at,p.created_by recorded_by
  from erp.sales_payments p
  join erp.journal_entries o on o.source_type='SALES_PAYMENT' and o.source_id=p.id
  join erp.journal_entries r on r.source_type='JOURNAL_REVERSAL'
    and r.source_id=o.id and r.reversal_of_id=o.id
  where p.status='REVERSED'
)
insert into erp.sales_payment_reversal_facts(
  payment_id,original_journal_entry_id,reversal_journal_entry_id,
  reversal_economic_date,reversal_transaction_date,reversal_posting_at,
  lineage_sha256,recorded_by
)
select payment_id,original_journal_entry_id,reversal_journal_entry_id,
  reversal_economic_date,reversal_transaction_date,reversal_posting_at,
  encode(extensions.digest(convert_to(jsonb_build_array(
    payment_id,original_journal_entry_id,reversal_journal_entry_id,
    reversal_economic_date,reversal_transaction_date,reversal_posting_at
  )::text,'UTF8'),'sha256'),'hex'),recorded_by
from prepared;

do $backfill_guard_v2620j$
declare v_count bigint;
begin
  if (select count(*) from erp.sales_payment_posting_facts)<>
       (select count(*) from erp.sales_payments where status in('POSTED','REVERSED'))
     or (select count(*) from erp.sales_payment_reversal_facts)<>
       (select count(*) from erp.sales_payments where status='REVERSED') then
    raise exception 'ERP v2.6.20j payment fact backfill cardinality mismatch';
  end if;
  select count(*) into v_count
  from erp.sales_payment_reversal_facts r
  join erp.sales_payment_posting_facts f using(payment_id)
  where r.original_journal_entry_id<>f.original_journal_entry_id
     or r.reversal_economic_date<f.journal_economic_date
     or r.reversal_posting_at<f.journal_posting_at;
  if v_count<>0 then
    raise exception 'ERP v2.6.20j refuses impossible historical payment reversal chronology';
  end if;
end
$backfill_guard_v2620j$;

create function erp.guard_sales_payment_fact_append_only()
returns trigger language plpgsql security definer set search_path='pg_catalog'
as $function$
begin
  raise exception using errcode='42501',
    message='POSTED_PAYMENT_FACT_APPEND_ONLY: use linked reversal/replacement';
end
$function$;
revoke all on function erp.guard_sales_payment_fact_append_only() from public,anon,authenticated,service_role;
create trigger trg_sales_payment_posting_fact_append_only
before update or delete on erp.sales_payment_posting_facts
for each row execute function erp.guard_sales_payment_fact_append_only();
create trigger trg_sales_payment_reversal_fact_append_only
before update or delete on erp.sales_payment_reversal_facts
for each row execute function erp.guard_sales_payment_fact_append_only();

create function erp.guard_sales_payment_posted_identity_v2620j()
returns trigger language plpgsql security definer set search_path='pg_catalog'
as $function$
begin
  if tg_op='INSERT' then
    if new.status<>'DRAFT' then
      raise exception using errcode='42501',message='PAYMENT_MUST_START_DRAFT';
    end if;
    return new;
  end if;
  if tg_op='DELETE' then
    if old.status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_PAYMENT_IDENTITY_IMMUTABLE';
    end if;
    return old;
  end if;
  if old.status='DRAFT' and new.status='DRAFT' then return new; end if;
  if old.status='DRAFT' and new.status='POSTED'
     and (pg_catalog.to_jsonb(new)-'status') is not distinct from
       (pg_catalog.to_jsonb(old)-'status')
     and exists(
       select 1 from erp.sales_payment_posting_facts f
       where f.payment_id=new.id
         and f.payment_snapshot=pg_catalog.to_jsonb(new)-'status'
     ) then
    return new;
  end if;
  if old.status='POSTED' and new.status='REVERSED'
     and (pg_catalog.to_jsonb(new)-'status') is not distinct from
       (pg_catalog.to_jsonb(old)-'status')
     and exists(select 1 from erp.sales_payment_reversal_facts r where r.payment_id=new.id) then
    return new;
  end if;
  raise exception using errcode='42501',
    message='POSTED_PAYMENT_IDENTITY_IMMUTABLE: reverse and post one linked replacement';
end
$function$;
revoke all on function erp.guard_sales_payment_posted_identity_v2620j() from public,anon,authenticated,service_role;
create trigger trg_cp6_v2620j_sales_payment_identity
before insert or update or delete on erp.sales_payments
for each row execute function erp.guard_sales_payment_posted_identity_v2620j();

create or replace function erp.post_sales_payment(p_payment_id uuid)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  prior_payment erp.sales_payments%rowtype;
  prior_fact erp.sales_payment_posting_facts%rowtype;
  prior_reversal erp.sales_payment_reversal_facts%rowtype;
  j erp.journal_entries%rowtype;
  v_cash uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_amount numeric(20,2);
  v_journal uuid;
  v_snapshot jsonb;
  v_digest text;
begin
  perform erp.require_internal();
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Sales payment must be DRAFT'; end if;
  v_amount:=round(p.amount,2)::numeric(20,2);
  if p.amount is distinct from v_amount or v_amount<=0 then
    raise exception 'Customer payment must be a positive exact two-decimal amount';
  end if;
  if p.payment_date::date>current_date then
    raise exception 'Customer payment business date cannot be in the future';
  end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Sale must be posted and still unpaid before payment';
  end if;
  if p.replaces_payment_id is not null then
    if p.replaces_payment_id=p.id then raise exception 'Payment cannot replace itself'; end if;
    perform pg_advisory_xact_lock(hashtextextended('SALES_PAYMENT_REPLACEMENT|'||p.replaces_payment_id::text,0));
    select * into prior_payment from erp.sales_payments
    where id=p.replaces_payment_id for update;
    select * into prior_fact from erp.sales_payment_posting_facts
    where payment_id=p.replaces_payment_id;
    select * into prior_reversal from erp.sales_payment_reversal_facts
    where payment_id=p.replaces_payment_id;
    if prior_payment.id is null or prior_payment.status<>'REVERSED'
       or prior_fact.payment_id is null or prior_reversal.payment_id is null then
      raise exception 'Replacement requires one fully reversed posted payment';
    end if;
    if prior_fact.customer_id is distinct from h.customer_id
       or prior_fact.sale_id=p.sale_id
       or prior_fact.amount is distinct from v_amount
       or prior_fact.cash_account_id is distinct from p.cash_account_id
       or prior_fact.payment_date is distinct from p.payment_date then
      raise exception 'Allocation replacement must preserve customer, amount, cash account and original payment clock while changing invoice';
    end if;
    if exists(select 1 from erp.sales_payment_posting_facts f
      where f.replaces_payment_id=p.replaces_payment_id) then
      raise exception 'Reversed payment already owns a linked replacement';
    end if;
  end if;
  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(sp.amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.id and sp.status='POSTED';
  if v_paid>=v_total then
    raise exception 'Sale has no remaining receivable after returns/credits. Net sale %, already paid %',v_total,v_paid;
  end if;
  if v_paid+v_amount>v_total then
    raise exception 'Customer payment exceeds exact remaining receivable. Net sale %, already paid %, requested %',v_total,v_paid,v_amount;
  end if;
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  v_journal:=erp.post_journal('SALES_PAYMENT',p_payment_id,p.payment_date::date,'Customer payment',jsonb_build_array(
    jsonb_build_object('account_id',v_cash,'debit',v_amount,'credit',0,'customer_id',h.customer_id),
    jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_amount,'customer_id',h.customer_id)));
  select * into strict j from erp.journal_entries where id=v_journal;
  v_snapshot:=to_jsonb(p)-'status';
  v_digest:=encode(extensions.digest(convert_to(jsonb_build_array(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,
    p.cash_account_id,j.id,j.economic_date,j.transaction_date,j.posting_at,
    p.replaces_payment_id,prior_reversal.reversal_journal_entry_id,v_snapshot
  )::text,'UTF8'),'sha256'),'hex');
  insert into erp.sales_payment_posting_facts(
    payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,
    original_journal_entry_id,journal_economic_date,journal_transaction_date,
    journal_posting_at,replaces_payment_id,predecessor_reversal_journal_id,
    payment_snapshot,lineage_sha256,recorded_by
  ) values(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,p.cash_account_id,
    j.id,j.economic_date,j.transaction_date,j.posting_at,p.replaces_payment_id,
    prior_reversal.reversal_journal_entry_id,v_snapshot,v_digest,erp.current_app_user_id()
  );
  update erp.sales_payments set status='POSTED' where id=p_payment_id;
  v_paid:=v_paid+v_amount;
  update erp.sales_headers
  set status=case when v_paid=v_total then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;

create or replace function erp.reverse_sales_payment(p_payment_id uuid,p_reason text)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  f erp.sales_payment_posting_facts%rowtype;
  j erp.journal_entries%rowtype;
  r erp.journal_entries%rowtype;
  v_journal uuid;
  v_reversal_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_digest text;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran customer wajib diisi'; end if;
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran customer tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran customer yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.id is null then raise exception 'Penjualan sumber pembayaran tidak ditemukan'; end if;
  select * into f from erp.sales_payment_posting_facts where payment_id=p.id;
  if f.payment_id is null or f.payment_snapshot is distinct from to_jsonb(p)-'status'
     or f.sale_id is distinct from p.sale_id or f.customer_id is distinct from h.customer_id
     or f.amount is distinct from p.amount or f.payment_date is distinct from p.payment_date
     or f.cash_account_id is distinct from p.cash_account_id then
    raise exception 'Immutable payment posting fact is missing or inconsistent; reversal stopped';
  end if;
  v_journal:=f.original_journal_entry_id;
  select * into j from erp.journal_entries where id=v_journal for update;
  if j.id is null or j.source_type<>'SALES_PAYMENT' or j.source_id<>p.id
     or j.status<>'POSTED' or j.economic_date<>f.journal_economic_date
     or j.transaction_date<>f.journal_transaction_date or j.posting_at<>f.journal_posting_at then
    raise exception 'Jurnal pembayaran customer tidak cocok dengan immutable fact; reversal dibatalkan';
  end if;
  v_reversal_journal:=erp.reverse_journal(v_journal,p_reason);
  select * into strict r from erp.journal_entries where id=v_reversal_journal;
  if r.economic_date<f.journal_economic_date or r.posting_at<f.journal_posting_at then
    raise exception 'Payment reversal chronology cannot precede original posting';
  end if;
  v_digest:=encode(extensions.digest(convert_to(jsonb_build_array(
    p.id,j.id,r.id,r.economic_date,r.transaction_date,r.posting_at
  )::text,'UTF8'),'sha256'),'hex');
  insert into erp.sales_payment_reversal_facts(
    payment_id,original_journal_entry_id,reversal_journal_entry_id,
    reversal_economic_date,reversal_transaction_date,reversal_posting_at,
    lineage_sha256,recorded_by
  ) values(
    p.id,j.id,r.id,r.economic_date,r.transaction_date,r.posting_at,
    v_digest,erp.current_app_user_id()
  );
  update erp.sales_payments set status='REVERSED' where id=p.id;

  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments where sale_id=h.id and status='POSTED';
  if v_paid>v_total then
    raise exception 'Payment reversal exposed an unsupported customer overpayment. Net sale %, still paid %',v_total,v_paid;
  end if;
  update erp.sales_headers
  set status=case when v_paid=v_total and v_total>=0 then 'PAID'
    when v_paid>0 and v_paid<v_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('sales_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;

do $patch_report_v2620j$
declare v_definition text; v_anchor text; v_replacement text; v_actual text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure),
    encode(extensions.digest(convert_to(pg_get_functiondef(
      'erp.run_v268_financial_report_checks()'::regprocedure),'UTF8'),'sha256'),'hex')
  into v_definition,v_actual;
  if v_actual<>'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: J report predecessor (%)',v_actual;
  end if;
  v_anchor:=$anchor$  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,$anchor$;
  v_replacement:=$replacement$  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,
    'Posted payment invoice/cash identity and reversal dates must match append-only facts; correction requires one linked replacement'
  from(
    select p.id
    from erp.sales_payments p
    left join erp.sales_headers h on h.id=p.sale_id
    left join erp.sales_payment_posting_facts f on f.payment_id=p.id
    left join erp.journal_entries o on o.id=f.original_journal_entry_id
    left join erp.sales_payment_reversal_facts rf on rf.payment_id=p.id
    left join erp.journal_entries r on r.id=rf.reversal_journal_entry_id
    left join erp.sales_payment_posting_facts pf on pf.payment_id=f.replaces_payment_id
    left join erp.sales_payment_reversal_facts prf on prf.payment_id=f.replaces_payment_id
    where
      (p.status='DRAFT' and(f.payment_id is not null or rf.payment_id is not null))
      or
      (p.status in('POSTED','REVERSED') and(
        f.payment_id is null or h.id is null
        or f.sale_id is distinct from p.sale_id
        or f.customer_id is distinct from h.customer_id
        or f.payment_number is distinct from p.payment_number
        or f.payment_date is distinct from p.payment_date
        or f.amount is distinct from p.amount
        or f.cash_account_id is distinct from p.cash_account_id
        or f.replaces_payment_id is distinct from p.replaces_payment_id
        or f.payment_snapshot is distinct from to_jsonb(p)-'status'
        or f.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
          f.payment_id,f.sale_id,f.customer_id,f.payment_number,f.payment_date,f.amount,
          f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,
          f.journal_transaction_date,f.journal_posting_at,f.replaces_payment_id,
          f.predecessor_reversal_journal_id,f.payment_snapshot
        )::text,'UTF8'),'sha256'),'hex')
        or o.id is null or o.source_type<>'SALES_PAYMENT' or o.source_id is distinct from p.id
        or o.status is distinct from case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
        or o.economic_date is distinct from f.journal_economic_date
        or o.transaction_date is distinct from f.journal_transaction_date
        or o.posting_at is distinct from f.journal_posting_at
        or ((f.replaces_payment_id is null)<>(f.predecessor_reversal_journal_id is null))
        or (f.replaces_payment_id is not null and(
          pf.payment_id is null or prf.payment_id is null
          or f.predecessor_reversal_journal_id is distinct from prf.reversal_journal_entry_id
          or pf.sale_id=f.sale_id or pf.customer_id is distinct from f.customer_id
          or pf.amount is distinct from f.amount
          or pf.cash_account_id is distinct from f.cash_account_id
          or pf.payment_date is distinct from f.payment_date
        ))
        or (p.status='POSTED' and(
          rf.payment_id is not null or exists(
            select 1 from erp.journal_entries x where x.source_type='JOURNAL_REVERSAL'
              and(x.source_id=o.id or x.reversal_of_id=o.id)
          )
        ))
        or (p.status='REVERSED' and(
          rf.payment_id is null or r.id is null
          or rf.original_journal_entry_id is distinct from o.id
          or r.source_type<>'JOURNAL_REVERSAL' or r.source_id is distinct from o.id
          or r.reversal_of_id is distinct from o.id or r.status<>'POSTED'
          or r.economic_date is distinct from rf.reversal_economic_date
          or r.transaction_date is distinct from rf.reversal_transaction_date
          or r.posting_at is distinct from rf.reversal_posting_at
          or rf.reversal_economic_date<f.journal_economic_date
          or rf.reversal_posting_at<f.journal_posting_at
          or rf.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
            rf.payment_id,rf.original_journal_entry_id,rf.reversal_journal_entry_id,
            rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at
          )::text,'UTF8'),'sha256'),'hex')
        ))
      ))
    union all
    select f.payment_id from erp.sales_payment_posting_facts f
    left join erp.sales_payments p on p.id=f.payment_id where p.id is null
    union all
    select r.payment_id from erp.sales_payment_reversal_facts r
    left join erp.sales_payments p on p.id=r.payment_id
    left join erp.sales_payment_posting_facts f on f.payment_id=r.payment_id
    where p.id is null or f.payment_id is null or p.status<>'REVERSED'
  ) payment_fact_faults

  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: J report insertion anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_report_v2620j$;

-- Snapshot every rollback-sensitive table after the new nullable link and
-- historical fact backfill exist. A pre-use J rollback may proceed only if this
-- exact boundary remains unchanged.
do $capture_boundary_v2620j$
declare v_table text; v_hash text; v_snapshot jsonb:='{}';
begin
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances',
    'sales_headers','sales_items','sale_stock_allocations',
    'sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations',
    'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
    'laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule',
    'sales_payment_posting_facts','sales_payment_reversal_facts'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620j_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620j$;

do $installed_guard_v2620j$
declare r record; v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620j_rollback_capsule)<>3 then
    raise exception 'ERP v2.6.20j incomplete rollback capsule';
  end if;
  for r in select c.*,p.proowner,p.proacl
    from erp.cp6_v2620j_rollback_capsule c
    join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else
             array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'ERP v2.6.20j changed owner/ACL for %',r.object_regidentity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v268_financial_report_checks()
  where check_name='V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH';
  if v_count is distinct from 0 then
    raise exception 'ERP v2.6.20j immutable payment reconciliation failed: % issue(s)',v_count;
  end if;
  update erp.cp6_v2620j_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620j$;

insert into erp.schema_migrations(version,description) values(
  'v2.6.20j',
  'CP6 I closure: append-only payment invoice facts, linked allocation replacement and authoritative inverse chronology'
);
commit;
