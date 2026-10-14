-- D14-6 kasbon tunai (owner 15 Okt 2026: "Ya, buatkan (Disarankan)"); D14-2: paying wages before they are owed
-- is a kasbon, not a payroll payment; D14-3: cash/bank never negative (the dated cash guard covers GIVE).
--  GIVE     cash out to a contractor: Dr CONTRACTOR_RECEIVABLE (contractor) / Cr the chosen cash account, dated, through
--           the accepted Native erp.post_journal (source CP7_KASBON).
--  ALLOCATE reserve (or release with 0) part of a kasbon on one of that contractor's payroll drafts as a Native
--           CASH_ADVANCE deduction; the accepted Native payroll payment then posts Dr CONTRACTOR_PAYABLE /
--           Cr CONTRACTOR_RECEIVABLE and pays only the net (unchanged).
--  CANCEL   a kasbon with no deduction on a live payroll: the accepted Native erp.reverse_journal.
-- The kasbon link of a deduction lives here (deduction_links), not as a new column on erp.payroll_deductions, so the
-- Native row shape every reader snapshots stays the same. Declared Native deltas (cp7_kasbon_bundle.py): the
-- CASH_ADVANCE source check accepts a deduction without an opening balance (the deferred trigger below requires its
-- kasbon link instead), the opening-advance deduction guard lets such rows through to the kasbon guard, the payroll
-- check also checks kasbon deductions, and the AP_CASH_ADVANCE_SOURCE truth check accepts a linked kasbon.
create role cp7_kasbon_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_kasbon_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_kasbon authorization cp7_kasbon_read;
revoke all on schema cp7_kasbon from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_kasbon to postgres,cp7_kasbon_write;

create table cp7_kasbon.advances(
 id uuid primary key,number text not null unique,contractor_id uuid not null references erp.contractors(id),
 advance_date date not null,amount numeric(20,2) not null check(amount>0),
 cash_account_id uuid not null references erp.cash_accounts(id),cash_coa_id uuid not null references erp.chart_accounts(id),
 journal_id uuid not null unique references erp.journal_entries(id),reason text not null,
 status text not null default 'GIVEN' check(status in('GIVEN','CANCELLED')),
 cancel_journal_id uuid unique references erp.journal_entries(id),cancel_reason text,
 created_by uuid not null,request_id uuid not null,created_at timestamptz not null default clock_timestamp(),
 cancelled_by uuid,cancelled_at timestamptz,
 check((status='CANCELLED')=(cancel_journal_id is not null and cancelled_by is not null and cancelled_at is not null and cancel_reason is not null))
);
create table cp7_kasbon.deduction_links(
 deduction_id uuid primary key references erp.payroll_deductions(id) on delete cascade,
 advance_id uuid not null references cp7_kasbon.advances(id),payroll_id uuid not null references erp.payroll_settlements(id),
 created_by uuid not null,created_at timestamptz not null default clock_timestamp(),unique(advance_id,payroll_id)
);
create table cp7_kasbon.requests(
 actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_kasbon.command_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,action text not null,advance_id uuid,
 primary key(backend_pid,transaction_id)
);
alter table cp7_kasbon.advances owner to postgres;
alter table cp7_kasbon.deduction_links owner to postgres;
alter table cp7_kasbon.requests owner to postgres;
alter table cp7_kasbon.command_context owner to postgres;
alter table cp7_kasbon.advances enable row level security;
alter table cp7_kasbon.deduction_links enable row level security;
alter table cp7_kasbon.requests enable row level security;
alter table cp7_kasbon.command_context enable row level security;
create policy private_advances on cp7_kasbon.advances for all using(false)with check(false);
create policy private_links on cp7_kasbon.deduction_links for all using(false)with check(false);
create policy private_requests on cp7_kasbon.requests for all using(false)with check(false);
create policy private_context on cp7_kasbon.command_context for all using(false)with check(false);
revoke all on all tables in schema cp7_kasbon from public,anon,authenticated,service_role,cp7_capture,cp7_kasbon_read,cp7_kasbon_write;

create function cp7_kasbon.access_now(p_write boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_KASBON_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')
  or erp.has_permission('finance.payroll.view')is distinct from true
  or(p_write and erp.has_permission('finance.payroll.pay')is distinct from true)then
  raise exception using errcode='42501',message='CP7_KASBON_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_kasbon.in_context(p_action text)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_kasbon.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.action=p_action)$$;

-- One kasbon: given, recovered on PAID payrolls, reserved on live drafts/approved payrolls, still free to reserve.
create function cp7_kasbon.state(p_id uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',a.id,'number',a.number,'contractor_id',a.contractor_id,'advance_date',a.advance_date,
  'amount',a.amount::text,'status',a.status,'reason',a.reason,'cash_account_id',a.cash_account_id,'journal_id',a.journal_id,
  'cancel_journal_id',a.cancel_journal_id,
  'recovered',coalesce(sum(d.amount)filter(where p.status='PAID'),0)::numeric(20,2)::text,
  'reserved',coalesce(sum(d.amount)filter(where p.status not in('PAID','REVERSED')),0)::numeric(20,2)::text,
  'free',case when a.status='GIVEN'then(a.amount-coalesce(sum(d.amount)filter(where p.status<>'REVERSED'),0))::numeric(20,2)::text else'0.00'end,
  'allocations',coalesce(jsonb_agg(jsonb_build_object('deduction_id',d.id,'payroll_id',p.id,'payroll_number',p.payroll_number,
   'payroll_status',p.status,'amount',d.amount::text)order by p.payroll_number,d.id)filter(where d.id is not null),'[]'))
 from cp7_kasbon.advances a left join cp7_kasbon.deduction_links k on k.advance_id=a.id
 left join erp.payroll_deductions d on d.id=k.deduction_id left join erp.payroll_settlements p on p.id=d.payroll_id
 where a.id=p_id group by a.id $$;

-- Earnings of a payroll as the Native opening-advance guard computes them.
create function cp7_kasbon.earnings(p_payroll uuid)returns numeric
language sql stable security definer set search_path=''as $$
 select coalesce((select sum(amount)from erp.payroll_work_items where payroll_id=p.id),0)
  +case when c.attendance_required then coalesce((select sum(amount)from erp.payroll_attendance_items where payroll_id=p.id),0)else 0 end
  +coalesce((select sum(amount)from erp.payroll_reimbursements where payroll_id=p.id),0)+p.manual_adjustment
 from erp.payroll_settlements p join erp.contractors c on c.id=p.contractor_id where p.id=p_payroll $$;

create function cp7_kasbon.workspace(p_contractor uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c erp.contractors;advances jsonb;drafts jsonb;cash jsonb;open_from date;today date;
begin
 a:=cp7_kasbon.access_now(false);
 select *into c from erp.contractors where id=p_contractor;
 if c.id is null then raise exception 'CP7_KASBON_NOT_FOUND';end if;
 select coalesce(jsonb_agg(cp7_kasbon.state(x.id)order by x.advance_date desc,x.number desc),'[]')into advances
  from cp7_kasbon.advances x where x.contractor_id=c.id;
 select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'payroll_number',p.payroll_number,'status',p.status,'row_version',p.row_version::text,
   'period_start',p.period_start,'period_end',p.period_end,'earnings',cp7_kasbon.earnings(p.id)::numeric(20,2)::text,
   'deduction_total',p.deduction_total::text,'net_payable',p.net_payable::text)order by p.period_end desc,p.payroll_number),'[]')into drafts
  from erp.payroll_settlements p where p.contractor_id=c.id and p.status in('DRAFT','CALCULATED','REVIEW');
 select coalesce(jsonb_agg(x.v order by x.v->>'code'),'[]')into cash
  from(select cp7_misc.cash(k.id)v from erp.cash_accounts k)x where x.v->'eligible'='true'::jsonb;
 select closed_through+1 into open_from from erp.accounting_period_control where singleton_id=1;
 today:=(statement_timestamp()at time zone 'Asia/Jakarta')::date;
 if cp7_kasbon.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_KASBON_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.kasbon-workspace.v1','contractor',jsonb_build_object('id',c.id,'code',c.contractor_code,
   'name',c.contractor_name,'row_version',c.row_version::text),
  'advances',advances,'payroll_drafts',drafts,'cash_accounts',cash,'open_from',open_from,'today',today,
  'review_token',md5(jsonb_build_object('a',advances,'d',drafts)::text),
  'can_write',erp.has_permission('finance.payroll.pay')is true,'business_DML',false);
end $$;

-- Deduction rows that carry a kasbon (CASH_ADVANCE without an opening balance) are written only by ALLOCATE.
create function cp7_kasbon.guard_deduction()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare r erp.payroll_deductions;p erp.payroll_settlements;k cp7_kasbon.advances;v_other numeric;v_free numeric;c cp7_kasbon.command_context;
begin
 if tg_op='DELETE'then r:=old;else r:=new;end if;
 if not(r.deduction_type='CASH_ADVANCE'and r.opening_cash_advance_balance_id is null)
  and not(tg_op='UPDATE'and old.deduction_type='CASH_ADVANCE'and old.opening_cash_advance_balance_id is null)then
  if tg_op='DELETE'then return old;end if;return new;end if;
 -- Removing a reservation from a draft (release, or the draft itself going away) has no money effect.
 if tg_op='DELETE'then
  select *into p from erp.payroll_settlements where id=old.payroll_id;
  if p.id is not null and p.status not in('DRAFT','CALCULATED','REVIEW')then raise exception 'CP7_KASBON_DEDUCTION_LOCKED';end if;
  return old;
 end if;
 select *into c from cp7_kasbon.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and action='ALLOCATE';
 if c.actor is null or c.advance_id is null then raise exception using errcode='42501',message='CP7_KASBON_DEDUCTION_PRIVATE';end if;
 if tg_op='UPDATE'and(new.payroll_id<>old.payroll_id or new.deduction_type<>old.deduction_type
  or new.opening_cash_advance_balance_id is not null)then raise exception 'CP7_KASBON_DEDUCTION_IDENTITY';end if;
 if new.contractor_issue_item_id is not null or new.bs_resolution_id is not null or new.amount is null
  or new.amount::text in('NaN','Infinity','-Infinity')or new.amount<=0 or new.amount<>round(new.amount,2)then
  raise exception 'CP7_KASBON_AMOUNT: potongan kasbon harus positif, tepat dua desimal.';end if;
 select *into p from erp.payroll_settlements where id=new.payroll_id for update;
 if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW')then
  raise exception 'CP7_KASBON_PAYROLL_DRAFT_ONLY: kasbon hanya bisa dipotong pada payroll yang masih draf.';end if;
 select *into k from cp7_kasbon.advances where id=c.advance_id for update;
 if k.id is null or k.status<>'GIVEN'or k.contractor_id is distinct from p.contractor_id then
  raise exception 'CP7_KASBON_SOURCE: kasbon ini bukan milik mandor payroll tersebut atau sudah dibatalkan.';end if;
 select coalesce(sum(d.amount),0)into v_other from cp7_kasbon.deduction_links l join erp.payroll_deductions d on d.id=l.deduction_id
  join erp.payroll_settlements s on s.id=d.payroll_id where l.advance_id=k.id and d.id<>new.id and s.status<>'REVERSED';
 if new.amount>k.amount-v_other then
  raise exception 'CP7_KASBON_OVER_REMAINING: potongan % melebihi sisa kasbon % (%).',new.amount,k.number,k.amount-v_other;end if;
 select coalesce(sum(amount),0)into v_free from erp.payroll_deductions where payroll_id=p.id and id<>new.id;
 v_free:=cp7_kasbon.earnings(p.id)-v_free;
 if new.amount>greatest(v_free,0)then
  raise exception 'CP7_KASBON_OVER_EARNINGS: potongan % melebihi pendapatan payroll yang tersisa (%). Sisanya dipotong di payroll berikutnya.',new.amount,greatest(v_free,0);end if;
 return new;
end $$;
create trigger cp7_kasbon_deduction_guard before insert or update or delete on erp.payroll_deductions
 for each row execute function cp7_kasbon.guard_deduction();

-- At commit every kasbon deduction must carry its link.
create function cp7_kasbon.assert_linked()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if exists(select 1 from erp.payroll_deductions d where d.id=new.id and d.deduction_type='CASH_ADVANCE'and d.opening_cash_advance_balance_id is null)
  and not exists(select 1 from cp7_kasbon.deduction_links l where l.deduction_id=new.id)then
  raise exception 'CP7_KASBON_DEDUCTION_UNLINKED';end if;
 return null;
end $$;
create constraint trigger cp7_kasbon_deduction_linked after insert or update on erp.payroll_deductions
 deferrable initially deferred for each row execute function cp7_kasbon.assert_linked();

-- The kasbon journal and its inverse belong to this command only.
create function cp7_kasbon.guard_journal()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare e erp.journal_entries;mine boolean;
begin
 if tg_op='DELETE'then e:=old;else e:=new;end if;
 mine:=e.source_type='CP7_KASBON'or(e.reversal_of_id is not null and exists(select 1 from erp.journal_entries o where o.id=e.reversal_of_id and o.source_type='CP7_KASBON'));
 if mine and not(cp7_kasbon.in_context('GIVE')or cp7_kasbon.in_context('CANCEL'))then
  raise exception using errcode='42501',message='CP7_KASBON_JOURNAL_PRIVATE: jurnal kasbon hanya lewat perintah kasbon.';end if;
 if tg_op='DELETE'then return old;end if;return new;
end $$;
create trigger cp7_kasbon_journal_guard before insert or update or delete on erp.journal_entries
 for each row execute function cp7_kasbon.guard_journal();

-- Payroll approval/payment (Native check_opening_cash_advance_payroll_v1 calls this): every kasbon deduction is linked,
-- belongs to the payroll's contractor, the kasbon is still GIVEN, the payroll is not dated before the kasbon, and the
-- kasbon is not reserved beyond its amount.
create function cp7_kasbon.check_payroll(p_payroll uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare p erp.payroll_settlements;r record;
begin
 select *into p from erp.payroll_settlements where id=p_payroll;
 if exists(select 1 from erp.payroll_deductions d where d.payroll_id=p.id and d.deduction_type='CASH_ADVANCE'
  and d.opening_cash_advance_balance_id is null and not exists(select 1 from cp7_kasbon.deduction_links l where l.deduction_id=d.id))then
  raise exception 'CP7_KASBON_DEDUCTION_UNLINKED';end if;
 for r in select k.*,(select coalesce(sum(d2.amount),0)from cp7_kasbon.deduction_links l2 join erp.payroll_deductions d2 on d2.id=l2.deduction_id
    join erp.payroll_settlements s2 on s2.id=d2.payroll_id where l2.advance_id=k.id and s2.status<>'REVERSED')used
   from cp7_kasbon.advances k where exists(select 1 from cp7_kasbon.deduction_links l join erp.payroll_deductions d on d.id=l.deduction_id
    where d.payroll_id=p.id and l.advance_id=k.id)order by k.id for update of k loop
  if r.status<>'GIVEN'or r.contractor_id is distinct from p.contractor_id or r.used>r.amount
   or(p.payment_date is not null and p.payment_date<r.advance_date)then
   raise exception 'CP7_KASBON_PAYROLL_MISMATCH: kasbon % tidak cocok dengan payroll ini (mandor, status, tanggal, atau sisa).',r.number;end if;
 end loop;
end $$;

-- The AP_CASH_ADVANCE_SOURCE truth check (declared Native delta) accepts a CASH_ADVANCE deduction without an opening
-- balance only when it is a lawful kasbon deduction: linked, same contractor, kasbon still GIVEN (or the payroll
-- reversed), and a PAID payroll not dated before the kasbon.
create function cp7_kasbon.linked_ok(p_deduction uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from erp.payroll_deductions d join cp7_kasbon.deduction_links l on l.deduction_id=d.id
  join cp7_kasbon.advances k on k.id=l.advance_id join erp.payroll_settlements p on p.id=d.payroll_id
  where d.id=p_deduction and d.opening_cash_advance_balance_id is null and l.payroll_id=p.id and k.contractor_id=p.contractor_id
   and(k.status='GIVEN'or p.status='REVERSED')and(p.status<>'PAID'or p.payment_date>=k.advance_date))$$;

create function cp7_kasbon.command(p_action text,p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_kasbon.requests;w jsonb;contractor uuid;k cp7_kasbon.advances;pay erp.payroll_settlements;cash jsonb;
 v_amount numeric;v_date date;closed date;today date;v_id uuid;v_journal uuid;v_deduction uuid;answer jsonb;keys text[];
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_kasbon.access_now(true);
 keys:=case p_action when'GIVE'then array['contractor_id','cash_account_id','cash_review_token','advance_date','amount','reason']
  when'ALLOCATE'then array['contractor_id','advance_id','payroll_id','payroll_version','amount']
  when'CANCEL'then array['contractor_id','advance_id','reason']end;
 if keys is null or p_request is null or p_expected is null or p_expected!~'^[a-f0-9]{32}$'or jsonb_typeof(p)is distinct from'object'
  or not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or exists(select 1 from unnest(keys)x where x like'%_id'and(jsonb_typeof(p->x)is distinct from'string'
   or coalesce(p->>x,'')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'))
  or(p?'amount'and(jsonb_typeof(p->'amount')is distinct from'string'or coalesce(p->>'amount','')!~'^(0|[1-9][0-9]{0,14})(\.[0-9]{1,2})?$'))
  or(p?'reason'and(jsonb_typeof(p->'reason')is distinct from'string'or length(btrim(p->>'reason'))not between 5 and 500))
  or(p?'advance_date'and(jsonb_typeof(p->'advance_date')is distinct from'string'or coalesce(p->>'advance_date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or(p?'cash_review_token'and coalesce(p->>'cash_review_token','')!~'^[a-f0-9]{32}$')
  or(p?'payroll_version'and coalesce(p->>'payroll_version','')!~'^[1-9][0-9]{0,18}$')then
  raise exception 'CP7_KASBON_FIELDS';end if;
 insert into cp7_kasbon.requests values(auth.uid(),p_request,p_action,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_kasbon.requests where actor=auth.uid()and request_id=p_request for update;
 if old.action is distinct from p_action or old.payload is distinct from p or old.expected_version is distinct from p_expected then
  raise exception 'CP7_KASBON_REQUEST_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 contractor:=(p->>'contractor_id')::uuid;
 -- The payroll lock order: the contractor first (payroll writers lock it), then the kasbon rows.
 perform pg_advisory_xact_lock(hashtextextended('CP7_KASBON|'||contractor::text,0));
 perform 1 from erp.contractors where id=contractor for share;
 if not found then raise exception 'CP7_KASBON_NOT_FOUND';end if;
 if cp7_kasbon.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_KASBON_ACCESS_CHANGED';end if;
 w:=cp7_kasbon.workspace(contractor);
 if w->>'review_token'is distinct from p_expected then raise exception 'CP7_KASBON_STALE_REVIEW';end if;
 insert into cp7_kasbon.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action,
  case when p?'advance_id'then(p->>'advance_id')::uuid end);
 today:=(statement_timestamp()at time zone 'Asia/Jakarta')::date;
 select closed_through into closed from erp.accounting_period_control where singleton_id=1;
 if p_action='GIVE'then
  v_amount:=(p->>'amount')::numeric;v_date:=(p->>'advance_date')::date;
  if v_amount<=0 then raise exception 'CP7_KASBON_AMOUNT: nominal kasbon harus lebih dari 0.';end if;
  if v_date>today then raise exception 'CP7_KASBON_IN_FUTURE: tanggal kasbon % ada di masa depan.',v_date;end if;
  if v_date<=closed then raise exception 'CP7_KASBON_PERIOD_CLOSED: tanggal kasbon % ada di periode yang sudah ditutup. Pilih tanggal sesudah %.',v_date,closed;end if;
  perform 1 from erp.cash_accounts where id=(p->>'cash_account_id')::uuid for share;
  cash:=cp7_misc.cash((p->>'cash_account_id')::uuid);
  if cash is null or cash->'eligible'is distinct from'true'::jsonb or cash->>'review_token'is distinct from p->>'cash_review_token'then
   raise exception 'CP7_KASBON_CASH_SOURCE_CHANGED';end if;
  v_id:=gen_random_uuid();
  -- D14-3: the dated cash guard on the journal lines refuses a kasbon the bank cannot pay on that date or later.
  v_journal:=erp.post_journal('CP7_KASBON',v_id,v_date,'Kasbon tunai '||(w->'contractor'->>'name'),jsonb_build_array(
   jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_amount,'credit',0,'contractor_id',contractor),
   jsonb_build_object('account_id',(cash->>'account_id')::uuid,'debit',0,'credit',v_amount,'contractor_id',contractor)));
  if v_journal is null or(select economic_date from erp.journal_entries where id=v_journal)is distinct from v_date then
   raise exception 'CP7_KASBON_JOURNAL_DATE';end if;
  insert into cp7_kasbon.advances(id,number,contractor_id,advance_date,amount,cash_account_id,cash_coa_id,journal_id,reason,created_by,request_id)
   values(v_id,'KB-'||to_char(v_date,'YYYYMMDD')||'-'||upper(substr(replace(v_id::text,'-',''),1,6)),contractor,v_date,v_amount,
    (p->>'cash_account_id')::uuid,(cash->>'account_id')::uuid,v_journal,btrim(p->>'reason'),auth.uid(),p_request);
 elsif p_action='ALLOCATE'then
  select *into k from cp7_kasbon.advances where id=(p->>'advance_id')::uuid for update;
  if k.id is null or k.contractor_id<>contractor then raise exception 'CP7_KASBON_NOT_FOUND';end if;
  select *into pay from erp.payroll_settlements where id=(p->>'payroll_id')::uuid for update;
  if pay.id is null or pay.contractor_id<>contractor then raise exception 'CP7_KASBON_NOT_FOUND';end if;
  if pay.row_version::text is distinct from p->>'payroll_version'then raise exception 'CP7_KASBON_STALE_REVIEW';end if;
  v_amount:=(p->>'amount')::numeric;
  select l.deduction_id into v_deduction from cp7_kasbon.deduction_links l where l.advance_id=k.id and l.payroll_id=pay.id;
  if v_amount=0 then
   if v_deduction is null then raise exception 'CP7_KASBON_NOTHING_TO_RELEASE';end if;
   delete from erp.payroll_deductions where id=v_deduction;
  elsif v_deduction is null then
   insert into erp.payroll_deductions(payroll_id,deduction_type,amount,notes)
    values(pay.id,'CASH_ADVANCE',v_amount,'Kasbon tunai '||k.number)returning id into v_deduction;
   insert into cp7_kasbon.deduction_links(deduction_id,advance_id,payroll_id,created_by)values(v_deduction,k.id,pay.id,auth.uid());
  else update erp.payroll_deductions set amount=v_amount where id=v_deduction;
  end if;
  perform erp.recalculate_payroll(pay.id);
 elsif p_action='CANCEL'then
  select *into k from cp7_kasbon.advances where id=(p->>'advance_id')::uuid for update;
  if k.id is null or k.contractor_id<>contractor then raise exception 'CP7_KASBON_NOT_FOUND';end if;
  if k.status<>'GIVEN'then raise exception 'CP7_KASBON_ALREADY_CANCELLED';end if;
  if exists(select 1 from cp7_kasbon.deduction_links l join erp.payroll_settlements s on s.id=l.payroll_id
   join erp.payroll_deductions d on d.id=l.deduction_id where l.advance_id=k.id and s.status<>'REVERSED')then
   raise exception 'CP7_KASBON_IN_USE: kasbon % sudah dipotong atau dipesan di payroll. Lepaskan dulu potongannya dari payroll draf.',k.number;end if;
  v_journal:=erp.reverse_journal(k.journal_id,btrim(p->>'reason'));
  update cp7_kasbon.advances set status='CANCELLED',cancel_journal_id=v_journal,cancel_reason=btrim(p->>'reason'),
   cancelled_by=auth.uid(),cancelled_at=clock_timestamp()where id=k.id;
  v_id:=k.id;
 end if;
 delete from cp7_kasbon.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then raise exception 'CP7_KASBON_CONTEXT_LOST';end if;
 if cp7_kasbon.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_KASBON_ACCESS_CHANGED';end if;
 answer:=jsonb_build_object('contract_version','cp7.kasbon-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,
  'contractor_id',contractor,'advance',cp7_kasbon.state(coalesce(v_id,(p->>'advance_id')::uuid)),
  'payroll',case when p_action='ALLOCATE'then(select jsonb_build_object('id',s.id,'row_version',s.row_version::text,
   'deduction_total',s.deduction_total::text,'net_payable',s.net_payable::text)from erp.payroll_settlements s where s.id=(p->>'payroll_id')::uuid)end);
 update cp7_kasbon.requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_kasbon_v1(p_contractor uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_kasbon.workspace(p_contractor)$$;
create function public.erp_cp7_save_kasbon_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_kasbon.command(p_action,p_payload,p_request,p_expected)$$;
do $own$ declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_kasbon' loop
  execute format('alter function %s owner to postgres',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture,cp7_kasbon_read,cp7_kasbon_write',r.sig);
 end loop;
end $own$;
grant execute on function cp7_kasbon.workspace(uuid)to cp7_kasbon_read;
grant execute on function cp7_kasbon.command(text,jsonb,uuid,text)to cp7_kasbon_write;
grant create on schema public to cp7_kasbon_read,cp7_kasbon_write;
alter function public.erp_cp7_get_kasbon_v1(uuid)owner to cp7_kasbon_read;
alter function public.erp_cp7_save_kasbon_v1(text,jsonb,uuid,text)owner to cp7_kasbon_write;
revoke create on schema public from cp7_kasbon_read,cp7_kasbon_write;
revoke all on function public.erp_cp7_get_kasbon_v1(uuid),public.erp_cp7_save_kasbon_v1(text,jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_kasbon_v1(uuid),public.erp_cp7_save_kasbon_v1(text,jsonb,uuid,text)to authenticated;
