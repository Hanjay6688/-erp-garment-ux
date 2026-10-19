CREATE OR REPLACE FUNCTION erp._v268_financial_report_checks_pre_scope()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
begin
  perform erp.require_owner_admin();

  return query
  with expected_daily as(
    select je.transaction_date balance_date,jl.account_id,
           sum(jl.debit)::numeric debit_total,sum(jl.credit)::numeric credit_total
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status in('POSTED','REVERSED')
    group by je.transaction_date,jl.account_id
  ), daily_mismatch as(
    select 1
    from expected_daily e
    full join erp.account_daily_balances a
      on a.balance_date=e.balance_date and a.account_id=e.account_id
    where abs(coalesce(e.debit_total,0)-coalesce(a.debit_total,0))<>0
       or abs(coalesce(e.credit_total,0)-coalesce(a.credit_total,0))<>0
  ), bs as(
    select
      coalesce(sum(case when ca.account_type='ASSET' then adb.debit_total-adb.credit_total else 0 end),0)::numeric assets,
      coalesce(sum(case when ca.account_type='LIABILITY' then adb.credit_total-adb.debit_total else 0 end),0)::numeric liabilities,
      coalesce(sum(case when ca.account_type='EQUITY' then adb.credit_total-adb.debit_total else 0 end),0)::numeric equity,
      coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then adb.credit_total-adb.debit_total else 0 end),0)::numeric current_earnings
    from erp.account_daily_balances adb
    join erp.chart_accounts ca on ca.id=adb.account_id
  ), ar as(
    select
      coalesce((select sum(a.debit_total-a.credit_total) from erp.account_daily_balances a
                where a.account_id=erp.account_id('AR_CUSTOMER')),0)::numeric gl_amount,
      coalesce((select sum(
        round(erp.sale_net_total(h.id),2)-coalesce((select sum(round(p.amount,2))
          from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),0)
      ) from erp.sales_headers h
          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric
      +coalesce((select sum(b.original_amount-b.settled_amount)
        from erp.opening_subledger_balances b
        join erp.opening_balance_items i on i.id=b.opening_item_id
        join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
        where b.party_type='CUSTOMER' and b.direction='RECEIVABLE'),0) as subledger_amount
  )
  select 'V268_DAILY_BALANCE_LEDGER_MISMATCH','CRITICAL',count(*)::bigint,
         'account_daily_balances must exactly equal posted/reversed journal lines by GL date and account'
  from daily_mismatch

  union all
  select 'V268_UNBALANCED_POSTED_JOURNAL','CRITICAL',count(*)::bigint,
         'Every posted/reversed journal entry must remain debit-equals-credit'
  from(
    select je.id from erp.journal_entries je
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status in('POSTED','REVERSED')
    group by je.id having count(jl.id)<2
      or sum(jl.debit) is distinct from sum(jl.credit)
      or sum(jl.debit)::text in('NaN','Infinity','-Infinity')
      or sum(jl.credit)::text in('NaN','Infinity','-Infinity')
  ) q

  union all
  select 'V268_BALANCE_SHEET_EQUATION','CRITICAL',
         case when abs(assets-liabilities-equity-current_earnings)<>0 then 1 else 0 end::bigint,
         'Assets must equal liabilities plus recorded equity plus current earnings'
  from bs

  union all
  select 'V2620L_NONFINITE_LEDGER_MONEY','CRITICAL',count(*)::bigint,
         'Posted money and daily balances must be finite cent amounts'
  from(
    select 1 from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
    where j.status in('POSTED','REVERSED') and(
      l.debit::text in('NaN','Infinity','-Infinity')
      or l.credit::text in('NaN','Infinity','-Infinity'))
    union all
    select 1 from erp.account_daily_balances a where
      a.debit_total::text in('NaN','Infinity','-Infinity')
      or a.credit_total::text in('NaN','Infinity','-Infinity')
  ) invalid_money

  union all
  select 'V2620L_NEGATIVE_VENDOR_AP','CRITICAL',count(*)::bigint,
         'Each laundry vendor payable must remain finite and nonnegative; advances need a separate workflow'
  from(
    select l.vendor_id from erp.journal_lines l
    join erp.journal_entries j on j.id=l.journal_entry_id
    where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR')
    group by l.vendor_id having sum(l.credit-l.debit)<0
      or sum(l.credit-l.debit)::text in('NaN','Infinity','-Infinity')
  ) negative_vendor

  union all
  select 'V268_AR_GL_SUBLEDGER_MISMATCH' ,'CRITICAL',
         case when round(gl_amount,2) is distinct from round(subledger_amount,2) then 1 else 0 end::bigint,
         'Customer AR general ledger must equal active sales net of posted returns and customer payments'
  from ar

  union all
  select r.check_name,r.severity,r.issue_count,r.details
  from erp.run_v267_financial_truth_checks() r
  where r.check_name in('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH',
    'V267_PAYMENT_EXCEEDS_FINAL_AP') or r.check_name like 'V2620M_%'

  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero active sale requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and(
      coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)>0.005
      or coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
                   from erp.sale_stock_allocations a
                   join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),0)>0.005
    )
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted sales return requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and coalesce((select sum(i.refund_amount+i.qty_pcs*i.unit_hpp_snapshot)
                  from erp.sales_return_items i where i.return_id=h.id),0)>0.005
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_CUSTOMER_PAYMENT_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every posted non-zero customer payment requires its SALES_PAYMENT journal'
  from erp.sales_payments p
  where p.status='POSTED' and p.amount>0.005
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALES_PAYMENT' and j.source_id=p.id and j.status='POSTED')

  union all
  select 'V268_PRODUCTION_FG_WITHOUT_CURRENT_HPP','CRITICAL',count(*)::bigint,
         'Every active production FG lot must have exactly one current HPP version'
  from erp.fg_lots l
  where l.lot_origin='PRODUCTION' and l.initial_qty_pcs>0
    and (select count(*) from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1

  union all
  select 'V268_COST_RECALC_EXHAUSTED','CRITICAL',count(*)::bigint,
         'A permanently failed HPP recalc means owner profitability is not reliable'
  from erp.cost_recalc_queue q where q.status='FAILED' and q.attempt_count>=3

  union all
  select 'V268_COST_RECALC_PENDING','WARNING',count(*)::bigint,
         'Pending/running/retryable HPP recalc means profitability is provisional until the queue clears'
  from erp.cost_recalc_queue q
  where q.status in('PENDING','RUNNING') or(q.status='FAILED' and q.attempt_count<3)

  union all
  select 'V268_LIABILITY_VIEW_HELPER_PRIVILEGE','CRITICAL',count(*)::bigint,
         'Authenticated browser role needs EXECUTE on pure read helpers used by security-invoker liability views'
  from(values
    ('erp.material_purchase_grni_total(uuid)'),
    ('erp.material_purchase_final_ap_total(uuid)'),
    ('erp.material_purchase_total_liability(uuid)')
  ) f(signature)
  where not has_function_privilege('authenticated',f.signature,'EXECUTE')

  union all
  select 'V268_BROWSER_DIRECT_FINANCIAL_WRITE','CRITICAL',count(*)::bigint,
         'Browser roles must not directly mutate posted-source financial tables'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in(
      'journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines',
      'sales_headers','sales_items','sales_returns','sales_return_items',
      'sales_payments','supplier_payments'
    )
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE');
end;
$function$;
