-- Shared business oracles for native PostgreSQL and sequential PGlite.
-- Caller creates disposable invoices A/B (same customer) and C (other customer)
-- with total 100 each. Every case runs in an enclosing rollback-only transaction.
create or replace function pg_temp.k_payment(sale uuid,amount numeric,paid_at timestamptz,prior uuid default null)
returns uuid language plpgsql as $$
declare payment uuid:=gen_random_uuid();
begin
  insert into erp.sales_payments(id,sale_id,payment_number,payment_date,amount,
    cash_account_id,status,created_by,replaces_payment_id)
  values(payment,sale,'K-PAY-'||payment,paid_at,amount,
    (select id from erp.cash_accounts where is_active order by cash_account_code limit 1),
    'DRAFT',erp.current_app_user_id(),prior);
  perform erp.post_sales_payment(payment);
  return payment;
end $$;

create or replace function pg_temp.k_cash_days(customer uuid)
returns jsonb language sql as $$
  select coalesce(jsonb_agg(to_jsonb(d) order by d.economic_date,d.transaction_date),'[]')
  from(select j.economic_date,j.transaction_date,sum(l.debit-l.credit) cash
    from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
    where j.status in('POSTED','REVERSED') and l.customer_id=customer
      and l.account_id in(select coa_account_id from erp.cash_accounts)
    group by j.economic_date,j.transaction_date
    having sum(l.debit-l.credit)<>0) d
$$;

create or replace function pg_temp.k_boundary()
returns jsonb language sql as $$
  select jsonb_build_object(
    'payments',(select count(*) from erp.sales_payments),
    'facts',(select count(*) from erp.sales_payment_posting_facts),
    'inverses',(select count(*) from erp.sales_payment_reversal_facts),
    'journals',(select count(*) from erp.journal_entries),
    'lines',(select count(*) from erp.journal_lines),
    'stock_movements',(select count(*) from erp.fg_stock_movements),
    'qty',(select coalesce(sum(cached_qty_pcs),0) from erp.fg_lots))
$$;

create or replace function pg_temp.k_confidence()
returns text language sql as $$
  select erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date)
    #>>'{data_confidence,status}'
$$;

create or replace function pg_temp.k_case(kind text,a uuid,b uuid,foreign_sale uuid,customer uuid)
returns jsonb language plpgsql as $$
declare
  payment uuid; replacement uuid; next_payment uuid; original_clock timestamptz;
  before_book jsonb; after_book jsonb; before_boundary jsonb; after_boundary jsonb;
  zone text; observations jsonb:='[]'; rejected boolean; safe_code text;
  quantity_before numeric; journal uuid; inverse_day date; delta integer;
  old_period date; amount numeric; issues bigint;
begin
  perform set_config('TimeZone','UTC',true);
  original_clock:=((current_date-1)+time '12:00') at time zone 'UTC';
  if pg_temp.k_confidence()<>'READY' then raise exception 'K_FIXTURE_NOT_READY'; end if;
  select coalesce(sum(cached_qty_pcs),0) into quantity_before from erp.fg_lots;

  if kind in('LATE_ALLOCATION','MULTI_HOP','COHERENT_DATE_FAULT','ATOMIC_INVALID') then
    amount:=case when kind='MULTI_HOP' then 0.01 else 40 end;
    payment:=pg_temp.k_payment(a,amount,original_clock);
    before_book:=pg_temp.k_cash_days(customer);
    if kind='ATOMIC_INVALID' then
      before_boundary:=pg_temp.k_boundary(); rejected:=false;
      begin
        perform erp.reverse_sales_payment(payment,'K atomic cross-customer rejection');
        perform pg_temp.k_payment(foreign_sale,amount,original_clock,payment);
      exception when raise_exception then rejected:=true; get stacked diagnostics safe_code=returned_sqlstate;
      end;
      after_boundary:=pg_temp.k_boundary();
      if not rejected or before_boundary<>after_boundary
         or (select status from erp.sales_payments where id=payment)<>'POSTED' then
        raise exception 'K_ATOMIC_REPLACEMENT_ORACLE_FAILED';
      end if;
      return jsonb_build_object('status','PASS','rejected',true,'code',safe_code,
        'before',before_boundary,'after',after_boundary,'report',pg_temp.k_confidence());
    end if;
    perform erp.reverse_sales_payment(payment,'K late allocation correction');
    replacement:=pg_temp.k_payment(b,amount,original_clock,payment);
    if kind='MULTI_HOP' then
      perform erp.reverse_sales_payment(replacement,'K allocation back to first invoice');
      next_payment:=pg_temp.k_payment(a,amount,original_clock,replacement);
      before_boundary:=pg_temp.k_boundary();
      perform erp.reverse_sales_payment(payment,'K lost response replay');
      perform erp.reverse_sales_payment(replacement,'K second inverse replay');
      if pg_temp.k_boundary()<>before_boundary then raise exception 'K_RETRY_LEFT_RESIDUE'; end if;
      rejected:=false;
      begin
        perform pg_temp.k_payment(b,amount,original_clock,payment);
      exception when unique_violation then rejected:=true;
      end;
      if not rejected or pg_temp.k_boundary()<>before_boundary then
        raise exception 'K_DUPLICATE_REPLACEMENT_ORACLE_FAILED';
      end if;
    end if;
    after_book:=pg_temp.k_cash_days(customer);
    if before_book<>after_book or pg_temp.k_confidence()<>'READY'
       or (select coalesce(sum(cached_qty_pcs),0) from erp.fg_lots)<>quantity_before then
      raise exception 'K_PER_DATE_CASH_CONSERVATION_ORACLE_FAILED';
    end if;
    if kind='COHERENT_DATE_FAULT' then
      -- Privileged fault simulation in a disposable transaction. The posting
      -- fact, journal and self-checksum are changed consistently; the separate
      -- authoritative predecessor inverse must still expose the date drift.
      select original_journal_entry_id,journal_economic_date into journal,inverse_day
        from erp.sales_payment_posting_facts where payment_id=replacement;
      for delta in select unnest(array[-1,1]) loop
        perform set_config('session_replication_role','replica',true);
        update erp.journal_entries set economic_date=inverse_day+delta where id=journal;
        update erp.sales_payment_posting_facts set journal_economic_date=inverse_day+delta
          where payment_id=replacement;
        update erp.sales_payment_posting_facts f set lineage_sha256=encode(extensions.digest(
          convert_to(jsonb_build_array(f.payment_id,f.sale_id,f.customer_id,f.payment_number,
            f.payment_date,f.amount,f.cash_account_id,f.original_journal_entry_id,
            f.journal_economic_date,f.journal_transaction_date,f.journal_posting_at,
            f.replaces_payment_id,f.predecessor_reversal_journal_id,f.payment_snapshot)::text,'UTF8'),
          'sha256'),'hex') where payment_id=replacement;
        select issue_count into issues from erp.run_v268_financial_report_checks()
          where check_name='V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH';
        if issues<>1 or pg_temp.k_confidence()<>'BLOCKED' then
          raise exception 'K_COHERENT_DATE_FAULT_ESCAPED';
        end if;
        observations:=observations||jsonb_build_array(jsonb_build_object('days',delta,'issues',issues,'report','BLOCKED'));
      end loop;
      update erp.journal_entries set economic_date=inverse_day where id=journal;
      update erp.sales_payment_posting_facts set journal_economic_date=inverse_day where payment_id=replacement;
      update erp.sales_payment_posting_facts f set lineage_sha256=encode(extensions.digest(
        convert_to(jsonb_build_array(f.payment_id,f.sale_id,f.customer_id,f.payment_number,
          f.payment_date,f.amount,f.cash_account_id,f.original_journal_entry_id,
          f.journal_economic_date,f.journal_transaction_date,f.journal_posting_at,
          f.replaces_payment_id,f.predecessor_reversal_journal_id,f.payment_snapshot)::text,'UTF8'),
        'sha256'),'hex') where payment_id=replacement;
      perform set_config('session_replication_role','origin',true);
    end if;
    if pg_temp.k_confidence()<>'READY' then raise exception 'K_RESTORATION_NOT_READY'; end if;
    return jsonb_build_object('status','PASS','amount',amount,'before',before_book,'after',after_book,
      'report','READY','stock_unchanged',true,'faults',observations);
  elsif kind='CLOSED_PERIOD' then
    payment:=pg_temp.k_payment(a,40,original_clock);
    perform erp.reverse_sales_payment(payment,'K period boundary before replacement');
    select closed_through into old_period from erp.accounting_period_control where singleton_id=1;
    -- An isolated period-state control. The accounting resolver must not be
    -- bypassed to force a replacement into the predecessor inverse's GL date.
    update erp.accounting_period_control set closed_through=current_date where singleton_id=1;
    before_boundary:=pg_temp.k_boundary();rejected:=false;
    begin
      perform pg_temp.k_payment(b,40,original_clock,payment);
    exception when raise_exception then rejected:=true; get stacked diagnostics safe_code=returned_sqlstate;
    end;
    after_boundary:=pg_temp.k_boundary();
    if not rejected or before_boundary<>after_boundary then
      raise exception 'K_CLOSED_PERIOD_MUST_REJECT_ATOMICALLY';
    end if;
    update erp.accounting_period_control set closed_through=old_period where singleton_id=1;
    if pg_temp.k_confidence()<>'READY' then raise exception 'K_PERIOD_RESTORE_NOT_READY'; end if;
    return jsonb_build_object('status','PASS','classification','ISOLATED_PERIOD_STATE_CONTROL',
      'rejected',true,'code',safe_code,'before',before_boundary,'after',after_boundary,'report','READY');
  elsif kind='TIMEZONE' then
    foreach zone in array array['UTC','Asia/Jakarta','Europe/Paris','Asia/Kolkata',
      'Pacific/Kiritimati','Etc/GMT+12','America/New_York','Australia/Lord_Howe'] loop
      perform set_config('TimeZone',zone,true);
      payment:=pg_temp.k_payment(a,40,original_clock);
      if current_setting('TimeZone')<>zone or pg_temp.k_confidence()<>'READY' then
        raise exception 'K_TIMEZONE_POST_OR_REPORT_ORACLE_FAILED';
      end if;
      perform erp.reverse_sales_payment(payment,'K timezone invariant inverse');
      if current_setting('TimeZone')<>zone or pg_temp.k_confidence()<>'READY' then
        raise exception 'K_TIMEZONE_INVERSE_ORACLE_FAILED';
      end if;
      observations:=observations||jsonb_build_array(jsonb_build_object('timezone',zone,
        'post',true,'inverse',true,'caller_setting_preserved',true,'report','READY'));
    end loop;
    perform set_config('TimeZone','UTC',true);
    return jsonb_build_object('status','PASS','cases',observations,'count',8);
  else
    raise exception 'K_UNKNOWN_TEST_CASE';
  end if;
end $$;
