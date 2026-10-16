-- CP1–CP7 audit fixes on dated balances (owner D14-3; Astra FIN02 / Fable FABLE-008;
-- Sol SOL-001). The accepted native writers keep their definitions; these guards
-- sit on the native rows every writer must touch, so every caller is covered.
--  * Cash/bank: no posting may leave a cash account's balance below zero on its
--    economic date or any later date (D14-3: "tidak boleh minus"), nor on its book
--    (transaction) date or any later date, the date the owner's cash report uses
--    (D15-1, Fable FABLE-013). A compound correction (inverse, then replacement)
--    is judged on its end state, not half way (Sol SOL-R1-001): see compound scope.
--  * Laundry claim: a SETTLED claim cannot be dated before its claim/source, and
--    the vendor's dated payable may not go below zero from that date on.
-- Concurrency: one transaction-scoped advisory lock per cash account / vendor is
-- taken before the dated balance is read, so two payments cannot both pass.
create role cp7_guard nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_guard authorization cp7_guard;
revoke all on schema cp7_guard from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_guard to postgres;

-- Lowest balance of one account (debit minus credit) on any economic date on or
-- after p_from, counting every posted line (reversed originals and their
-- reversals both stay, as in the native ledger). Null when nothing is dated.
create function cp7_guard.min_debit_balance_from(p_account uuid,p_from date) returns numeric
language sql stable security definer set search_path='' as $$
 select min(x.running) from(
  select d.on_day,sum(d.delta) over(order by d.on_day) running from(
   select je.economic_date as on_day,sum(jl.debit-jl.credit) as delta
   from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
   where jl.account_id=p_account and je.status in('POSTED','REVERSED')
   group by je.economic_date) d) x
 where x.on_day>=p_from $$;

-- Same on the book date (journal_entries.transaction_date): a document dated in a
-- closed period is recognised on the first open day (erp.resolve_accounting_
-- transaction_date), and account_daily_balances and the owner's cash reader use it.
create function cp7_guard.min_debit_balance_by_book_from(p_account uuid,p_from date) returns numeric
language sql stable security definer set search_path='' as $$
 select min(x.running) from(
  select d.on_day,sum(d.delta) over(order by d.on_day) running from(
   select je.transaction_date as on_day,sum(jl.debit-jl.credit) as delta
   from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
   where jl.account_id=p_account and je.status in('POSTED','REVERSED')
   group by je.transaction_date) d) x
 where x.on_day>=p_from $$;

-- Same for one vendor's AP_VENDOR balance (credit minus debit).
create function cp7_guard.min_vendor_ap_from(p_vendor uuid,p_from date) returns numeric
language sql stable security definer set search_path='' as $$
 select min(x.running) from(
  select d.on_day,sum(d.delta) over(order by d.on_day) running from(
   select je.economic_date as on_day,sum(jl.credit-jl.debit) as delta
   from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
   where jl.account_id=erp.account_id('AP_VENDOR') and jl.vendor_id=p_vendor and je.status in('POSTED','REVERSED')
   group by je.economic_date) d) x
 where x.on_day>=p_from $$;

-- One cash account on both dates (D15-1). Raises CP7_CASH_NEGATIVE naming the date basis.
create function cp7_guard.check_cash(p_account uuid,p_economic date,p_book date) returns void
language plpgsql stable security definer set search_path='' as $$
declare v_cash erp.cash_accounts%rowtype;v_min numeric;
begin
 select * into v_cash from erp.cash_accounts c where c.coa_account_id=p_account order by c.id limit 1;
 if v_cash.id is null then return;end if;
 v_min:=cp7_guard.min_debit_balance_from(p_account,p_economic);
 if v_min is not null and v_min<0 then
  raise exception 'CP7_CASH_NEGATIVE: saldo % (%) menjadi minus % pada tanggal % atau sesudahnya (tanggal ekonomi). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.',
   v_cash.cash_account_name,v_cash.cash_account_code,round(v_min,2),p_economic;
 end if;
 v_min:=cp7_guard.min_debit_balance_by_book_from(p_account,p_book);
 if v_min is not null and v_min<0 then
  raise exception 'CP7_CASH_NEGATIVE: saldo % (%) menjadi minus % pada tanggal buku % atau sesudahnya (laporan kas harian). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.',
   v_cash.cash_account_name,v_cash.cash_account_code,round(v_min,2),p_book;
 end if;
end $$;

-- Compound scope (Sol SOL-R1-001). A correction that first reverses an income and then
-- posts its replacement (customer payment correction, misc correction, sales note
-- correction) would otherwise be judged on the half-way balance, before the
-- replacement exists. Such a command opens a scope; while it is open the line guard
-- still takes the account lock at once (same lock order) but records the account
-- instead of judging it; end_compound() judges every touched account on both dates
-- from the earliest touched day. Only postgres (the owning CP7 commands) can open or
-- close a scope; a scope still open at commit refuses the whole transaction.
create table cp7_guard.compound_scope(txid bigint primary key,label text not null,depth integer not null default 1 check(depth>=0),
 started_at timestamptz not null default clock_timestamp());
create table cp7_guard.compound_touch(txid bigint not null,account_id uuid not null,economic_date date not null,book_date date not null);
revoke all on cp7_guard.compound_scope,cp7_guard.compound_touch from public,anon,authenticated,service_role,cp7_capture;

create function cp7_guard.begin_compound(p_label text) returns void
language plpgsql volatile security definer set search_path='' as $$
begin
 if nullif(btrim(p_label),'') is null then raise exception 'CP7_GUARD_COMPOUND_LABEL';end if;
 insert into cp7_guard.compound_scope(txid,label) values(pg_catalog.txid_current(),p_label)
 on conflict(txid) do update set depth=cp7_guard.compound_scope.depth+1;
end $$;

create function cp7_guard.end_compound() returns void
language plpgsql volatile security definer set search_path='' as $$
declare v_depth integer;r record;
begin
 update cp7_guard.compound_scope set depth=depth-1 where txid=pg_catalog.txid_current() returning depth into v_depth;
 if v_depth is null then raise exception 'CP7_GUARD_COMPOUND_NOT_OPEN';end if;
 if v_depth>0 then return;end if;
 for r in select t.account_id,min(t.economic_date) economic_from,min(t.book_date) book_from
  from cp7_guard.compound_touch t where t.txid=pg_catalog.txid_current() group by t.account_id order by t.account_id loop
  perform cp7_guard.check_cash(r.account_id,r.economic_from,r.book_from);
 end loop;
 delete from cp7_guard.compound_touch where txid=pg_catalog.txid_current();
 delete from cp7_guard.compound_scope where txid=pg_catalog.txid_current();
end $$;

create function cp7_guard.compound_closed() returns trigger
language plpgsql volatile security definer set search_path='' as $$
begin
 if exists(select 1 from cp7_guard.compound_scope s where s.txid=new.txid) then
  raise exception 'CP7_GUARD_COMPOUND_OPEN: perintah koreksi % tidak menutup pemeriksaan kas; seluruh transaksi dibatalkan.',new.label;
 end if;
 return null;
end $$;

create constraint trigger cp7_guard_compound_closed after insert on cp7_guard.compound_scope
 deferrable initially deferred for each row execute function cp7_guard.compound_closed();

create function cp7_guard.guard_cash_line() returns trigger
language plpgsql volatile security definer set search_path='' as $$
declare v_economic date;v_book date;
begin
 if new.credit<=0 then return new;end if;
 if not exists(select 1 from erp.cash_accounts c where c.coa_account_id=new.account_id) then return new;end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('CP7_CASH|'||new.account_id::text,0));
 select je.economic_date,je.transaction_date into v_economic,v_book from erp.journal_entries je where je.id=new.journal_entry_id;
 if exists(select 1 from cp7_guard.compound_scope s where s.txid=pg_catalog.txid_current()) then
  insert into cp7_guard.compound_touch values(pg_catalog.txid_current(),new.account_id,v_economic,coalesce(v_book,v_economic));
  return new;
 end if;
 perform cp7_guard.check_cash(new.account_id,v_economic,coalesce(v_book,v_economic));
 return new;
end $$;

create trigger cp7_guard_cash_not_negative after insert on erp.journal_lines
 for each row when(new.credit>0) execute function cp7_guard.guard_cash_line();

-- Earliest lawful settlement day of a laundry claim: its own WIB opening day, its
-- delivery's and its receipt's WIB physical days (the latest of those that exist).
create function cp7_guard.laundry_claim_floor(p_opened timestamptz,p_delivery uuid,p_receipt_line uuid) returns date
language sql stable security definer set search_path='' as $$
 select max(d) from(
  select (p_opened at time zone 'Asia/Jakarta')::date d
  union all select (ld.physical_at at time zone 'Asia/Jakarta')::date from erp.laundry_deliveries ld where ld.id=p_delivery
  union all select (lr.physical_at at time zone 'Asia/Jakarta')::date from erp.laundry_receipt_lines l
   join erp.laundry_receipts lr on lr.id=l.receipt_id where l.id=p_receipt_line) x $$;

create function cp7_guard.guard_laundry_claim_date() returns trigger
language plpgsql volatile security definer set search_path='' as $$
declare v_floor date;v_min numeric;
begin
 if new.status<>'SETTLED' or old.status is not distinct from new.status then return new;end if;
 v_floor:=cp7_guard.laundry_claim_floor(new.opened_at,new.delivery_id,new.receipt_line_id);
 if new.resolution_date is null or (v_floor is not null and new.resolution_date<v_floor) then
  raise exception 'CP7_LAUNDRY_CLAIM_BEFORE_SOURCE: klaim % diselesaikan tanggal %, sebelum klaim/sumbernya ada (%).',new.claim_number,new.resolution_date,v_floor;
 end if;
 if new.compensation_amount>0 then
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('VENDOR_AP|'||new.vendor_id::text,0));
  v_min:=cp7_guard.min_vendor_ap_from(new.vendor_id,new.resolution_date);
  if v_min is not null and v_min<0 then
   raise exception 'CP7_LAUNDRY_CLAIM_AP_NOT_AVAILABLE: kompensasi klaim % pada % membuat hutang vendor minus % pada tanggal itu atau sesudahnya.',new.claim_number,new.resolution_date,round(v_min,2);
  end if;
 end if;
 return new;
end $$;

create trigger cp7_guard_laundry_claim_date before update of status on erp.laundry_claims
 for each row execute function cp7_guard.guard_laundry_claim_date();

-- Detector (read only): rows already in the books that the guards above would refuse
-- today, e.g. data posted before the guards were installed. Same rules as the guards:
--  CASH_NEGATIVE: a cash/bank ledger account whose balance is below zero on some economic
--   day (first such day, lowest balance); CASH_NEGATIVE_BOOK_DATE: the same on the book
--   (transaction) date, the basis of the owner's daily cash report (D15-1);
--  PAYROLL_PAID_BEFORE_ACCRUAL: a PAID payroll dated before its latest payable source
--   (cp7_payroll.payment_floor, the rule of the payment-date guard);
--  LAUNDRY_CLAIM_BEFORE_SOURCE / LAUNDRY_CLAIM_AP_NEGATIVE: a SETTLED claim dated before
--   its claim/source, or whose compensation leaves the vendor's dated payable below zero.
-- Owned by postgres and executable by nobody else: the installer/auditor runs it.
create function cp7_guard.findings()
returns table(kind text,subject_id uuid,label text,on_day date,amount numeric,floor_day date)
language sql stable security definer set search_path='' as $$
 with banks as(
  select distinct on(c.coa_account_id) c.coa_account_id account_id,c.id,c.cash_account_code||' · '||c.cash_account_name label
  from erp.cash_accounts c order by c.coa_account_id,c.id),
 days as(
  select b.id,b.label,d.on_day,sum(d.delta) over(partition by b.id order by d.on_day) running
  from banks b join lateral(
   select je.economic_date on_day,sum(jl.debit-jl.credit) delta
   from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
   where jl.account_id=b.account_id and je.status in('POSTED','REVERSED') group by je.economic_date) d on true),
 book_days as(
  select b.id,b.label,d.on_day,sum(d.delta) over(partition by b.id order by d.on_day) running
  from banks b join lateral(
   select je.transaction_date on_day,sum(jl.debit-jl.credit) delta
   from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
   where jl.account_id=b.account_id and je.status in('POSTED','REVERSED') group by je.transaction_date) d on true)
 select 'CASH_NEGATIVE'::text,id,label,min(on_day) filter(where running<0),min(running),null::date
 from days group by id,label having min(running)<0
 union all
 select 'CASH_NEGATIVE_BOOK_DATE',id,label,min(on_day) filter(where running<0),min(running),null::date
 from book_days group by id,label having min(running)<0
 union all
 select 'PAYROLL_PAID_BEFORE_ACCRUAL',p.id,p.payroll_number,p.payment_date,null::numeric,f.floor_day
 from erp.payroll_settlements p cross join lateral(select cp7_payroll.payment_floor(p.id) floor_day) f
 where p.status='PAID' and p.payment_date<f.floor_day
 union all
 select 'LAUNDRY_CLAIM_BEFORE_SOURCE',c.id,c.claim_number,c.resolution_date,c.compensation_amount,f.floor_day
 from erp.laundry_claims c cross join lateral(select cp7_guard.laundry_claim_floor(c.opened_at,c.delivery_id,c.receipt_line_id) floor_day) f
 where c.status='SETTLED' and (c.resolution_date is null or c.resolution_date<f.floor_day)
 union all
 select 'LAUNDRY_CLAIM_AP_NEGATIVE',c.id,c.claim_number,c.resolution_date,m.lowest,null::date
 from erp.laundry_claims c cross join lateral(select cp7_guard.min_vendor_ap_from(c.vendor_id,c.resolution_date) lowest) m
 where c.status='SETTLED' and c.compensation_amount>0 and c.resolution_date is not null and m.lowest<0
 order by 1,4,3 $$;

do $own$ declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_guard' loop
  execute format('alter function %s owner to postgres',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture',r.sig);
 end loop;
end $own$;
