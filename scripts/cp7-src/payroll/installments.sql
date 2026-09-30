-- E05 owner-approved cash installments against one immutable approved payroll.
-- Read capability has no native DML; command capability owns metadata only.
create role cp7_installment_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_installment_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_installment authorization cp7_installment_read;
revoke all on schema cp7_installment from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_installment to cp7_installment_write;
grant usage on schema erp,auth,cp7_misc,cp7_payroll to cp7_installment_read;
grant usage on schema auth to cp7_installment_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),cp7_misc.cash(uuid),cp7_payroll.settlement_token(uuid) to cp7_installment_read;
grant execute on function auth.uid() to cp7_installment_write;
grant select on erp.payroll_settlements,erp.payroll_work_items,erp.payroll_attendance_items,erp.payroll_reimbursements,erp.payroll_deductions,erp.contractors,erp.cash_accounts,erp.chart_accounts,erp.accounting_account_mappings,erp.journal_entries,erp.journal_lines to cp7_installment_read;
grant select on cp7_payroll.notes to cp7_installment_read;

create table cp7_installment.accounts(
 payroll_id uuid primary key references erp.payroll_settlements(id),
 approved_meaning jsonb not null,approved_net numeric(20,2) not null check(approved_net>0),
 payable_account_id uuid not null references erp.chart_accounts(id),
 created_by uuid not null,created_at timestamptz not null default statement_timestamp()
);
create table cp7_installment.payments(
 id uuid primary key,payroll_id uuid not null references cp7_installment.accounts(payroll_id),
 amount numeric(20,2) not null check(amount>0),payment_date date not null,
 cash_account_id uuid not null references erp.cash_accounts(id),cash_coa_id uuid not null references erp.chart_accounts(id),
 journal_id uuid not null unique references erp.journal_entries(id),
 reversal_journal_id uuid unique references erp.journal_entries(id),
 created_by uuid not null,request_id uuid not null,created_at timestamptz not null default statement_timestamp()
);
create table cp7_installment.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,response jsonb,primary key(actor,request_id));
create table cp7_installment.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,native_payment_id uuid,primary key(backend_pid,transaction_id));
alter table cp7_installment.accounts owner to postgres;
alter table cp7_installment.payments owner to postgres;
alter table cp7_installment.requests owner to cp7_installment_write;
alter table cp7_installment.command_context owner to cp7_installment_write;
alter table cp7_installment.accounts enable row level security;
alter table cp7_installment.payments enable row level security;
alter table cp7_installment.requests enable row level security;
alter table cp7_installment.command_context enable row level security;
create policy cp7_installment_accounts_deny on cp7_installment.accounts for all to public using(false)with check(false);
create policy cp7_installment_payments_deny on cp7_installment.payments for all to public using(false)with check(false);
create policy cp7_installment_requests_deny on cp7_installment.requests for all to public using(false)with check(false);
create policy cp7_installment_context_deny on cp7_installment.command_context for all to public using(false)with check(false);
revoke all on cp7_installment.accounts,cp7_installment.payments,cp7_installment.requests,cp7_installment.command_context from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_installment.requests,cp7_installment.command_context to cp7_installment_read;
grant select on cp7_installment.accounts,cp7_installment.payments to cp7_installment_read;

create function cp7_installment.access_now(p_action text default null) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from 'true'::jsonb or not erp.has_permission('finance.payroll.view')
  or(p_action is not null and(p_action not in('PAY','REVERSE_PAYMENT','REVERSE_PAYROLL')or not erp.has_permission('finance.payroll.pay')))
  or(p_action='REVERSE_PAYROLL'and not erp.has_permission('finance.payroll.approve'))then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_DENIED';end if;
 return a;
end $$;

-- The reviewed cash fingerprint includes native timestamptz fields. Keep its
-- rendering fixed across the UTC reader and the WIB payment transaction.
-- This adapter leaves the accepted miscellaneous-finance helper unchanged.
create function cp7_installment.cash(p_id uuid) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $$
 select cp7_misc.cash(p_id)
$$;

create function cp7_installment.meaning(p_id uuid) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $$
 select jsonb_build_object('header',to_jsonb(p)-array['status','payment_date','payment_cash_account_id','settled_at','updated_at','row_version'],
  'work',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from erp.payroll_work_items i where i.payroll_id=p.id),'[]'),
  'attendance',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from erp.payroll_attendance_items i where i.payroll_id=p.id),'[]'),
  'reimbursements',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from erp.payroll_reimbursements i where i.payroll_id=p.id),'[]'),
  'deductions',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from erp.payroll_deductions i where i.payroll_id=p.id),'[]'))
 from erp.payroll_settlements p where p.id=p_id
$$;

create function cp7_installment.require_context(p_id uuid) returns void
language plpgsql stable security definer set search_path='' as $$
declare c cp7_installment.command_context;
begin
 select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and(payload->>'payroll_id')::uuid=p_id;
 if c.actor is null or not exists(select 1 from cp7_installment.requests r where r.actor=c.actor and r.request_id=c.request_id and r.action=c.action and r.payload=c.payload and r.expected_version=c.expected_version and r.response is null)then raise exception using errcode='42501',message='CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED';end if;
 perform cp7_installment.access_now(c.action);
end $$;

-- This additional trigger preserves the accepted native lifecycle trigger.
-- Managed payment fields may change only inside the exact private command.
create function cp7_installment.guard_header() returns trigger
language plpgsql volatile security definer set search_path='' as $$
begin
 if exists(select 1 from cp7_installment.accounts where payroll_id=old.id)then
  if tg_op='DELETE'then raise exception 'CP7_INSTALLMENT_APPROVED_SOURCE_IMMUTABLE';end if;
  -- net_payable is generated after BEFORE triggers; freeze its exact component
  -- columns here and verify the computed value in the reviewed native meaning.
  if(to_jsonb(new)-array['status','payment_date','payment_cash_account_id','settled_at','updated_at','row_version','net_payable'])is distinct from(to_jsonb(old)-array['status','payment_date','payment_cash_account_id','settled_at','updated_at','row_version','net_payable'])then raise exception 'CP7_INSTALLMENT_APPROVED_SOURCE_IMMUTABLE';end if;
  perform cp7_installment.require_context(old.id);
 end if;
 if tg_op='DELETE'then return old;end if;return new;
end $$;
create trigger cp7_installment_managed_header before update or delete on erp.payroll_settlements for each row execute function cp7_installment.guard_header();

create function cp7_installment.guard_journal() returns trigger
language plpgsql volatile security definer set search_path='' as $$
declare p_id uuid;entry erp.journal_entries;c cp7_installment.command_context;
begin
 if tg_op='DELETE'then entry:=old;else entry:=new;end if;
 if tg_op='INSERT'and entry.source_type='PAYROLL_INSTALLMENT'then
  select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and action='PAY'and native_payment_id=entry.source_id;
  if c.actor is null then raise exception using errcode='42501',message='CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED';end if;
  p_id:=(c.payload->>'payroll_id')::uuid;
 else
  select p.payroll_id into p_id from cp7_installment.payments p where entry.id in(p.journal_id,p.reversal_journal_id)or entry.reversal_of_id=p.journal_id;
  if p_id is null and entry.source_type like 'PAYROLL_%'then select payroll_id into p_id from cp7_installment.accounts where payroll_id=entry.source_id;end if;
  if p_id is null and entry.reversal_of_id is not null then
   select a.payroll_id into p_id from erp.journal_entries original join cp7_installment.accounts a on a.payroll_id=original.source_id where original.id=entry.reversal_of_id and original.source_type like 'PAYROLL_%';
  end if;
 end if;
 if p_id is not null then perform cp7_installment.require_context(p_id);end if;
 if tg_op='DELETE'then return old;end if;return new;
end $$;
create trigger cp7_installment_managed_journal before insert or update or delete on erp.journal_entries for each row execute function cp7_installment.guard_journal();

create function cp7_installment.guard_child() returns trigger
language plpgsql volatile security definer set search_path='' as $$
begin
 if(tg_op<>'INSERT'and exists(select 1 from cp7_installment.accounts where payroll_id=old.payroll_id))or(tg_op<>'DELETE'and exists(select 1 from cp7_installment.accounts where payroll_id=new.payroll_id))then raise exception 'CP7_INSTALLMENT_APPROVED_SOURCE_IMMUTABLE';end if;
 if tg_op='DELETE'then return old;end if;return new;
end $$;
create trigger cp7_installment_managed_work before insert or update or delete on erp.payroll_work_items for each row execute function cp7_installment.guard_child();
create trigger cp7_installment_managed_attendance before insert or update or delete on erp.payroll_attendance_items for each row execute function cp7_installment.guard_child();
create trigger cp7_installment_managed_reimbursements before insert or update or delete on erp.payroll_reimbursements for each row execute function cp7_installment.guard_child();
create trigger cp7_installment_managed_deductions before insert or update or delete on erp.payroll_deductions for each row execute function cp7_installment.guard_child();

create function cp7_installment.guard_line() returns trigger
language plpgsql volatile security definer set search_path='' as $$
declare p_id uuid;j erp.journal_entries;c cp7_installment.command_context;
begin
 select * into j from erp.journal_entries where id=case when tg_op='DELETE'then old.journal_entry_id else new.journal_entry_id end;
 select p.payroll_id into p_id from cp7_installment.payments p where j.id in(p.journal_id,p.reversal_journal_id)or j.reversal_of_id=p.journal_id;
 if p_id is null and j.source_type like 'PAYROLL_%'then select payroll_id into p_id from cp7_installment.accounts where payroll_id=j.source_id;end if;
 if p_id is null and j.source_type='PAYROLL_INSTALLMENT'then
  select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and action='PAY'and native_payment_id=j.source_id;
  p_id:=(c.payload->>'payroll_id')::uuid;
 end if;
 if p_id is null and j.reversal_of_id is not null then select a.payroll_id into p_id from erp.journal_entries original join cp7_installment.accounts a on a.payroll_id=original.source_id where original.id=j.reversal_of_id and original.source_type like 'PAYROLL_%';end if;
 if p_id is not null then
  if tg_op<>'INSERT'then raise exception 'CP7_INSTALLMENT_NATIVE_JOURNAL_IMMUTABLE';end if;
  perform cp7_installment.require_context(p_id);
 end if;
 if tg_op='DELETE'then return old;end if;return new;
end $$;
create trigger cp7_installment_managed_line before insert or update or delete on erp.journal_lines for each row execute function cp7_installment.guard_line();

create function cp7_installment.assert_payment_amount(p_id uuid,p_amount numeric,p_final boolean) returns void
language plpgsql stable security definer set search_path='' as $$
declare remaining numeric;a cp7_installment.accounts;
begin
 perform cp7_installment.require_context(p_id);
 select * into a from cp7_installment.accounts where payroll_id=p_id;
 if a.payroll_id is null or a.approved_meaning is distinct from cp7_installment.meaning(p_id)then raise exception 'CP7_INSTALLMENT_APPROVED_SOURCE_CHANGED';end if;
 select a.approved_net-coalesce(sum(p.amount)filter(where p.reversal_journal_id is null),0)into remaining from cp7_installment.payments p where p.payroll_id=p_id;
 if p_amount is null or p_amount::text in('NaN','Infinity','-Infinity')or p_amount<=0 or p_amount<>round(p_amount,2)or p_amount>remaining or(p_final and p_amount<>remaining)then raise exception 'CP7_INSTALLMENT_AMOUNT_EXCEEDS_REMAINING';end if;
end $$;

-- E05_DERIVED_NATIVE_ROUTINES

create function cp7_installment.source(p_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare h erp.payroll_settlements;a cp7_installment.accounts;r record;paid numeric(20,2):=0;rows jsonb:='[]';journals jsonb;lines jsonb;fingerprint jsonb;orig erp.journal_entries;inverse erp.journal_entries;state text;
begin
 select * into h from erp.payroll_settlements where id=p_id;
 if h.id is null then raise exception 'CP7_INSTALLMENT_PAYROLL_NOT_FOUND';end if;
 select * into a from cp7_installment.accounts where payroll_id=p_id;
 if a.payroll_id is not null then
  if a.approved_net is distinct from h.net_payable or a.approved_meaning is distinct from cp7_installment.meaning(p_id)then raise exception 'CP7_INSTALLMENT_APPROVED_SOURCE_CHANGED';end if;
  for r in select p.*,c.cash_account_code,c.cash_account_name from cp7_installment.payments p join erp.cash_accounts c on c.id=p.cash_account_id where p.payroll_id=p_id order by p.payment_date,p.created_at,p.id loop
   select * into orig from erp.journal_entries where id=r.journal_id;
   if orig.id is null or orig.reversal_of_id is not null
    or not(orig.source_type='PAYROLL_INSTALLMENT'and orig.source_id=r.id)
    or orig.economic_date is distinct from r.payment_date
    or(select count(*)from erp.journal_lines where journal_entry_id=orig.id)<>2
    or not exists(select 1 from erp.journal_lines where journal_entry_id=orig.id and account_id=a.payable_account_id and contractor_id=h.contractor_id and debit=r.amount and credit=0)
    or not exists(select 1 from erp.journal_lines where journal_entry_id=orig.id and account_id=r.cash_coa_id and contractor_id=h.contractor_id and credit=r.amount and debit=0)then raise exception 'CP7_INSTALLMENT_NATIVE_PAYMENT_SOURCE_MISMATCH';end if;
   inverse:=null;
   if r.reversal_journal_id is null then
    if orig.status<>'POSTED'or exists(select 1 from erp.journal_entries where reversal_of_id=orig.id)then raise exception 'CP7_INSTALLMENT_NATIVE_PAYMENT_SOURCE_MISMATCH';end if;
    paid:=paid+r.amount;
   else
    select * into inverse from erp.journal_entries where id=r.reversal_journal_id;
    if orig.status<>'REVERSED'or inverse.id is null or inverse.status<>'POSTED'or inverse.reversal_of_id is distinct from orig.id
     or(select count(*)from erp.journal_lines where journal_entry_id=inverse.id)<>2
     or not exists(select 1 from erp.journal_lines where journal_entry_id=inverse.id and account_id=a.payable_account_id and contractor_id=h.contractor_id and credit=r.amount and debit=0)
     or not exists(select 1 from erp.journal_lines where journal_entry_id=inverse.id and account_id=r.cash_coa_id and contractor_id=h.contractor_id and debit=r.amount and credit=0)then raise exception 'CP7_INSTALLMENT_NATIVE_PAYMENT_INVERSE_MISMATCH';end if;
   end if;
   rows:=rows||jsonb_build_array(jsonb_build_object('id',r.id,'amount',r.amount::text,'payment_date',r.payment_date,'cash_account_id',r.cash_account_id,'cash_account_code',r.cash_account_code,'cash_account_name',r.cash_account_name,
    'journal_id',orig.id,'journal_number',orig.journal_number,'status',orig.status,'economic_date',orig.economic_date,'accounting_date',orig.transaction_date,'posting_at',orig.posting_at,'period_shifted',orig.period_shifted,
    'reversal_journal_id',inverse.id,'reversal_journal_number',inverse.journal_number,'reversal_economic_date',inverse.economic_date,'reversal_accounting_date',inverse.transaction_date,'reversal_posting_at',inverse.posting_at));
  end loop;
  if exists(select 1 from erp.journal_entries j where j.source_type='PAYROLL_PAYMENT'and j.source_id=p_id and j.reversal_of_id is null and not exists(select 1 from cp7_installment.payments p where p.payroll_id=p_id and p.journal_id=j.id))then raise exception 'CP7_INSTALLMENT_UNTRACKED_NATIVE_PAYMENT';end if;
  if paid>a.approved_net or h.status not in('APPROVED','PAID','REVERSED')or(h.status='PAID'and paid<>a.approved_net)or(h.status='APPROVED'and paid>=a.approved_net)or(h.status='REVERSED'and paid<>0)then raise exception 'CP7_INSTALLMENT_NATIVE_STATUS_MISMATCH';end if;
 else
  -- Historic native full payments remain native facts; they are never imported
  -- as invented installment records or silently reported as unpaid/zero.
  select coalesce(sum(l.credit),0)into paid from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
   where j.source_type='PAYROLL_PAYMENT'and j.source_id=p_id and j.status='POSTED';
  if(h.status='PAID'and paid<>h.net_payable)or(h.status<>'PAID'and paid<>0)then raise exception 'CP7_INSTALLMENT_LEGACY_PAYMENT_MISMATCH';end if;
 end if;
 state:=case when h.status='REVERSED'then 'REVERSED'when h.status='PAID'then 'PAID'when paid>0 then 'PARTIAL'when h.status='APPROVED'then 'UNPAID'else 'NOT_APPROVED'end;
 select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]')into journals from erp.journal_entries j
  where(j.source_id=p_id and j.source_type like 'PAYROLL_%')or j.id in(select p.journal_id from cp7_installment.payments p where p.payroll_id=p_id union select p.reversal_journal_id from cp7_installment.payments p where p.payroll_id=p_id);
 select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')into lines from erp.journal_lines l where l.journal_entry_id in(select(x->>'id')::uuid from jsonb_array_elements(journals)x);
 fingerprint:=jsonb_build_object('header',to_jsonb(h),'native_payroll_review',cp7_payroll.settlement_token(p_id),'approved_account',to_jsonb(a),'meaning',cp7_installment.meaning(p_id),'payments',rows,'journals',journals,'lines',lines,
  'cash_sources',coalesce((select jsonb_agg(cp7_installment.cash(p.cash_account_id)order by p.id)from cp7_installment.payments p where p.payroll_id=p_id),'[]'),
  'payable_mapping',coalesce((select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m where m.mapping_key='CONTRACTOR_PAYABLE'),'[]'));
 return jsonb_build_object('payroll_id',h.id,'payroll_number',h.payroll_number,'contractor_id',h.contractor_id,'contractor_name',(select contractor_name from erp.contractors where id=h.contractor_id),
  'native_status',h.status,'payment_state',state,'managed',a.payroll_id is not null,'approved_net',h.net_payable::text,'paid_amount',paid::text,
  'remaining_amount',case when h.status in('APPROVED','PAID')then(h.net_payable-paid)::text end,'row_version',h.row_version::text,'source_review_token',cp7_payroll.settlement_token(p_id),'review_token',md5(fingerprint::text),'payments',rows);
end $$;

create function cp7_installment.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$
declare id uuid;off integer;coff integer;q text;d jsonb;payments jsonb;cash jsonb;ct bigint;pt bigint;
begin
 perform cp7_installment.access_now();
 if jsonb_typeof(p_query)is distinct from 'object'or not p_query ? 'payroll_id'
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('payroll_id','payment_offset','cash_offset','cash_query'))
  or jsonb_typeof(p_query->'payroll_id')is distinct from 'string'
  or(p_query->>'payroll_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or exists(select 1 from jsonb_each(p_query)e where e.key in('payment_offset','cash_offset')and(jsonb_typeof(e.value)<>'number'or e.value::text!~'^[0-9]{1,7}$'))
  or(p_query ? 'cash_query'and jsonb_typeof(p_query->'cash_query')is distinct from 'string')then raise exception 'CP7_INSTALLMENT_QUERY';end if;
 id:=(p_query->>'payroll_id')::uuid;off:=coalesce((p_query->>'payment_offset')::integer,0);coff:=coalesce((p_query->>'cash_offset')::integer,0);q:=btrim(coalesce(p_query->>'cash_query',''));
 if off not between 0 and 1000000 or coff not between 0 and 1000000 or length(q)>120 then raise exception 'CP7_INSTALLMENT_QUERY';end if;
 d:=cp7_installment.source(id);pt:=jsonb_array_length(d->'payments');
 select coalesce(jsonb_agg(value order by ordinal),'[]')into payments from(select value,ordinal from jsonb_array_elements(d->'payments')with ordinality a(value,ordinal)order by ordinal limit 25 offset off)s;
 with eligible as materialized(select cp7_installment.cash(c.id)value from erp.cash_accounts c),all_rows as materialized(select value from eligible where value->'eligible'='true'::jsonb and(q=''or strpos(lower(concat_ws(' ',value->>'code',value->>'name')),lower(q))>0)),slice as(select value from all_rows order by value->>'code',value->>'id'limit 25 offset coff)
 select(select count(*)from all_rows),coalesce((select jsonb_agg(value order by value->>'code',value->>'id')from slice),'[]')into ct,cash;
 return jsonb_build_object('contract_version','cp7.payroll-installment-read.v1','captured_at',statement_timestamp(),'document',d-'payments',
  'payments',jsonb_build_object('rows',payments,'total',pt::text,'offset',off,'limit',25,'next_offset',case when off+jsonb_array_length(payments)<pt then off+jsonb_array_length(payments)end),
  'cash_accounts',jsonb_build_object('rows',cash,'total',ct::text,'offset',coff,'limit',25,'next_offset',case when coff+jsonb_array_length(cash)<ct then coff+jsonb_array_length(cash)end),
  'capabilities',jsonb_build_object('pay',erp.has_permission('finance.payroll.pay'),'reverse_payroll',erp.has_permission('finance.payroll.pay')and erp.has_permission('finance.payroll.approve')));
end $$;

create function cp7_installment.validate(p_action text,p jsonb,p_expected text) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare keys text[];k text;
begin
 keys:=array['payroll_id','review_token','change_reason'];
 if p_action='PAY'then keys:=keys||array['amount','payment_date','cash_account_id','cash_review_token'];
 elsif p_action='REVERSE_PAYMENT'then keys:=keys||array['payment_id'];
 elsif p_action is null or p_action<>'REVERSE_PAYROLL'then raise exception 'CP7_INSTALLMENT_ACTION';end if;
 if p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'or jsonb_typeof(p)is distinct from 'object'or not p ?& keys or exists(select 1 from jsonb_object_keys(p)x where x<>all(keys))then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
 foreach k in array keys loop
  if jsonb_typeof(p->k)is distinct from 'string'then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
  if k in('payroll_id','cash_account_id','payment_id')and(p->>k)!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
  if k in('review_token','cash_review_token')and(p->>k)!~'^[a-f0-9]{32}$'then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
 end loop;
 if length(btrim(p->>'change_reason'))not between 5 and 1000 then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
 if p_action='PAY'and((p->>'amount')!~'^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$'or(p->>'amount')::numeric<=0 or(p->>'payment_date')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')then raise exception 'CP7_INSTALLMENT_FIELDS';end if;
end $$;

create function cp7_installment.apply_command(p_action text,p jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' set TimeZone='Asia/Jakarta' as $$
declare ident uuid:=(p->>'payroll_id')::uuid;h erp.payroll_settlements;a jsonb;d jsonb;cash jsonb;acct cp7_installment.accounts;payment cp7_installment.payments;
 amount numeric(20,2);remaining numeric(20,2);payment_id uuid;journal_id uuid;inverse_id uuid;pay_date date;native_action text;r record;
begin
 a:=cp7_installment.access_now(p_action);perform cp7_installment.validate(p_action,p,p_expected);
 if not exists(select 1 from cp7_installment.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()and c.actor=auth.uid()and c.request_id=p_request and c.action=p_action and c.payload=p and c.expected_version=p_expected)then raise exception using errcode='42501',message='CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED';end if;
 select * into h from erp.payroll_settlements where id=ident for update;
 if h.id is null then raise exception 'CP7_INSTALLMENT_PAYROLL_NOT_FOUND';end if;
 perform cp7_installment.require_context(ident);
 perform pg_advisory_xact_lock(hashtextextended(h.contractor_id::text,0));
 perform 1 from erp.payroll_work_items where payroll_id=ident order by id for update;
 perform 1 from erp.payroll_attendance_items where payroll_id=ident order by id for update;
 perform 1 from erp.payroll_reimbursements where payroll_id=ident order by id for update;
 perform 1 from erp.payroll_deductions where payroll_id=ident order by id for update;
 perform 1 from erp.opening_subledger_balances b where exists(select 1 from erp.payroll_deductions x where x.payroll_id=ident and x.opening_cash_advance_balance_id=b.id)or exists(select 1 from erp.payroll_reimbursements x where x.payroll_id=ident and x.opening_payable_balance_id=b.id)order by b.id for update;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts c where c.id=(p->>'cash_account_id')::uuid or exists(select 1 from cp7_installment.payments x where x.payroll_id=ident and x.cash_account_id=c.id)order by c.id for share;
 perform 1 from erp.chart_accounts c where c.id in(select coa_account_id from erp.cash_accounts where id=(p->>'cash_account_id')::uuid union select cash_coa_id from cp7_installment.payments where payroll_id=ident union select account_id from erp.accounting_account_mappings where mapping_key='CONTRACTOR_PAYABLE')order by c.id for share;
 perform 1 from erp.journal_entries j where(j.source_id=ident and j.source_type like 'PAYROLL_%')or exists(select 1 from cp7_installment.payments x where x.payroll_id=ident and j.id in(x.journal_id,x.reversal_journal_id))order by j.id for update;
 perform 1 from erp.journal_lines l where exists(select 1 from erp.journal_entries j where j.id=l.journal_entry_id and((j.source_id=ident and j.source_type like 'PAYROLL_%')or exists(select 1 from cp7_installment.payments x where x.payroll_id=ident and j.id in(x.journal_id,x.reversal_journal_id))))order by l.id for update;
 if cp7_installment.access_now(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_CHANGED';end if;
 d:=cp7_installment.source(ident);
 if h.row_version::text is distinct from p_expected or d->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_INSTALLMENT_REVIEW_CHANGED';end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 native_action:=case when p_action='REVERSE_PAYROLL'then case when h.status='PAID'then 'REVERSE'else 'CANCEL'end else 'PAY'end;
 -- Keep the accepted native admission predicates unchanged. This trusted apply
 -- creates their exact transaction-local payroll context after its own checks.
 insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),auth.uid(),ident,native_action);
 if p_action='PAY'then
  if h.status<>'APPROVED'or h.net_payable<=0 then raise exception 'CP7_INSTALLMENT_APPROVED_POSITIVE_PAYROLL_ONLY';end if;
  cash:=cp7_installment.cash((p->>'cash_account_id')::uuid);
  if cash is null or cash->'eligible'is distinct from 'true'::jsonb or cash->>'review_token'is distinct from p->>'cash_review_token'then raise exception 'CP7_INSTALLMENT_CASH_SOURCE_CHANGED';end if;
  amount:=(p->>'amount')::numeric;
  begin pay_date:=(p->>'payment_date')::date;exception when datetime_field_overflow or invalid_datetime_format then raise exception 'CP7_INSTALLMENT_PAYMENT_DATE';end;
  if pay_date::text is distinct from p->>'payment_date'or pay_date>(statement_timestamp()at time zone 'Asia/Jakarta')::date then raise exception 'CP7_INSTALLMENT_PAYMENT_DATE';end if;
  if not(d->>'managed')::boolean then
   insert into cp7_installment.accounts(payroll_id,approved_meaning,approved_net,payable_account_id,created_by)
    values(ident,cp7_installment.meaning(ident),h.net_payable,erp.account_id('CONTRACTOR_PAYABLE'),auth.uid());
  end if;
  select * into acct from cp7_installment.accounts where payroll_id=ident;
  if erp.account_id('CONTRACTOR_PAYABLE')is distinct from acct.payable_account_id then raise exception 'CP7_INSTALLMENT_PAYABLE_MAPPING_CHANGED';end if;
  remaining:=(d->>'remaining_amount')::numeric;
  perform cp7_installment.assert_payment_amount(ident,amount,false);
  update erp.payroll_settlements set payment_date=pay_date,payment_cash_account_id=(p->>'cash_account_id')::uuid where id=ident;
  payment_id:=gen_random_uuid();
  update cp7_installment.command_context set native_payment_id=payment_id where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  if amount=remaining then
   perform cp7_installment.final_payment(ident,amount);
   select id into journal_id from erp.journal_entries where source_type='PAYROLL_INSTALLMENT'and source_id=payment_id and status='POSTED';
  else
   perform cp7_installment.check_payment(ident,amount);
   journal_id:=erp.post_journal('PAYROLL_INSTALLMENT',payment_id,pay_date,'Cicilan payroll '||h.payroll_number,jsonb_build_array(
    jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',amount,'credit',0,'contractor_id',h.contractor_id),
    jsonb_build_object('account_id',(cash->>'account_id')::uuid,'debit',0,'credit',amount,'contractor_id',h.contractor_id)));
  end if;
  if journal_id is null then raise exception 'CP7_INSTALLMENT_NATIVE_JOURNAL_MISSING';end if;
  insert into cp7_installment.payments(id,payroll_id,amount,payment_date,cash_account_id,cash_coa_id,journal_id,created_by,request_id)
   values(payment_id,ident,amount,pay_date,(p->>'cash_account_id')::uuid,(cash->>'account_id')::uuid,journal_id,auth.uid(),p_request);
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)values('payroll_settlements',ident,'POST',jsonb_build_object('lifecycle_action','PAY_INSTALLMENT','payment_id',payment_id,'amount',amount::text,'approved_net',h.net_payable::text,'approved_cost_unchanged',true),erp.current_app_user_id(),btrim(p->>'change_reason'));
 elsif p_action='REVERSE_PAYMENT'then
  if not(d->>'managed')::boolean or h.status not in('APPROVED','PAID')then raise exception 'CP7_INSTALLMENT_MANAGED_ACTIVE_PAYROLL_ONLY';end if;
  select * into payment from cp7_installment.payments where id=(p->>'payment_id')::uuid and payroll_id=ident for update;
  if payment.id is null or payment.reversal_journal_id is not null then raise exception 'CP7_INSTALLMENT_ACTIVE_PAYMENT_REQUIRED';end if;
  if h.status='PAID'then perform cp7_installment.reopen_settlement(ident,btrim(p->>'change_reason'));end if;
  perform erp.reverse_journal(payment.journal_id,btrim(p->>'change_reason'));
  select id into inverse_id from erp.journal_entries where reversal_of_id=payment.journal_id and status='POSTED';
  if inverse_id is null then raise exception 'CP7_INSTALLMENT_NATIVE_INVERSE_MISSING';end if;
  update cp7_installment.payments set reversal_journal_id=inverse_id where id=payment.id;payment_id:=payment.id;
  update erp.payroll_settlements set status='APPROVED',settled_at=null,updated_at=statement_timestamp()where id=ident;
 elsif p_action='REVERSE_PAYROLL'then
  if not(d->>'managed')::boolean or h.status not in('APPROVED','PAID')then raise exception 'CP7_INSTALLMENT_MANAGED_ACTIVE_PAYROLL_ONLY';end if;
  -- Native owning-flow dependency guard runs before any cash effect.
  if exists(select 1 from erp.attendance_hpp_pool_sources s join erp.attendance_hpp_pools hp on hp.id=s.pool_id where s.payroll_id=ident and hp.status='ACTIVE')then raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';end if;
  for r in select * from cp7_installment.payments where payroll_id=ident and reversal_journal_id is null order by created_at desc,id desc loop
   perform erp.reverse_journal(r.journal_id,btrim(p->>'change_reason'));
   select id into inverse_id from erp.journal_entries where reversal_of_id=r.journal_id and status='POSTED';
   if inverse_id is null then raise exception 'CP7_INSTALLMENT_NATIVE_INVERSE_MISSING';end if;
   update cp7_installment.payments set reversal_journal_id=inverse_id where id=r.id;
  end loop;
  if h.status='PAID'then perform erp.reverse_paid_payroll(ident,btrim(p->>'change_reason'));else perform erp.cancel_unpaid_payroll(ident,btrim(p->>'change_reason'));end if;
 end if;
 delete from cp7_payroll.settlement_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_installment.access_now(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_CHANGED';end if;
 d:=cp7_installment.source(ident);
 return jsonb_build_object('payroll_id',ident,'payment_id',payment_id,'native_status',d->>'native_status','payment_state',d->>'payment_state','row_version',d->>'row_version','review_token',d->>'review_token');
end $$;

create function cp7_installment.command(p_action text,p jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_installment.requests;d jsonb;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_installment.access_now(p_action);perform cp7_installment.validate(p_action,p,p_expected);
 if p_request is null then raise exception 'CP7_INSTALLMENT_REQUEST_REQUIRED';end if;
 insert into cp7_installment.requests values(auth.uid(),p_request,p_action,p,p_expected,null)on conflict do nothing;
 select * into old from cp7_installment.requests where actor=auth.uid()and request_id=p_request for update;
 if old.action is distinct from p_action or old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_INSTALLMENT_REQUEST_CHANGED';end if;
 if cp7_installment.access_now(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 insert into cp7_installment.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p_action,p,p_expected,null);
 d:=cp7_installment.apply_command(p_action,p,p_request,p_expected);
 delete from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_installment.access_now(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_CHANGED';end if;
 r:=jsonb_build_object('contract_version','cp7.payroll-installment-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'request_payload',p,'expected_version',p_expected)||d;
 update cp7_installment.requests set response=r where actor=auth.uid()and request_id=p_request;
 return r;
end $$;

create function public.erp_cp7_get_payroll_installments_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_installment.workspace(p_query)$$;
create function public.erp_cp7_save_payroll_installment_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_installment.command(p_action,p_payload,p_request,p_expected)$$;

do $owners$ declare r record;begin
 for r in select p.oid::regprocedure signature,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_installment'loop
  execute format('alter function %s owner to %I',r.signature,case when r.proname in('apply_command','check_payment','final_payment','reopen_settlement')then 'postgres'when r.proname='command'then 'cp7_installment_write'else 'cp7_installment_read'end);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture',r.signature);
 end loop;
end $owners$;
grant create on schema public to cp7_installment_read,cp7_installment_write;
alter function public.erp_cp7_get_payroll_installments_v1(jsonb)owner to cp7_installment_read;
alter function public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)owner to cp7_installment_write;
revoke create on schema public from cp7_installment_read,cp7_installment_write;
grant execute on function cp7_installment.access_now(text),cp7_installment.validate(text,jsonb,text),cp7_installment.apply_command(text,jsonb,uuid,text)to cp7_installment_write;
grant usage on schema cp7_installment,cp7_payroll,cp7_misc to postgres;
grant select on cp7_installment.requests,cp7_installment.command_context to postgres;
grant update(native_payment_id)on cp7_installment.command_context to postgres;
grant insert,delete on cp7_payroll.settlement_context to postgres;
grant execute on all functions in schema cp7_installment to postgres;
grant execute on function cp7_misc.cash(uuid)to postgres;
revoke all on function public.erp_cp7_get_payroll_installments_v1(jsonb),public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_payroll_installments_v1(jsonb),public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)to authenticated;
