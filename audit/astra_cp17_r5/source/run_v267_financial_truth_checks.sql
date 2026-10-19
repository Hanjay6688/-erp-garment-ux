CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'V267_GRNI_MAPPING_INVALID','CRITICAL',count(*)::bigint,
         'GRNI_MATERIAL must map to an active CREDIT liability account'
  from erp.accounting_account_mappings m
  join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='GRNI_MATERIAL'
    and not(a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable)

  union all
  select 'V267_MISSING_GRNI_MAPPING','CRITICAL',case when exists(
    select 1 from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'
  ) then 0 else 1 end::bigint,'GRNI mapping is required'

  union all
  select 'V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','CRITICAL',count(*)::bigint,
         'Posted estimated receipts require an AP-to-GRNI reclassification journal'
  from erp.material_purchase_headers h
  where h.status='POSTED' and erp.material_purchase_grni_total(h.id)>0.005
    and not exists(
      select 1 from erp.journal_entries j
      where (j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' or (
        j.source_type='OPENING_UNINVOICED_RECEIPT' and exists(select 1 from erp.initial_import_receipt_headers r where r.purchase_id=h.id))) and j.source_id=h.id
        and j.status in('POSTED','REVERSED')
    )

  union all
  select 'V267_POSTED_INVOICE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted supplier invoice requires an AP/GRNI journal'
  from erp.material_supplier_invoices h
  where h.status='POSTED'
    and exists(select 1 from erp.material_supplier_invoice_lines l where l.invoice_id=h.id and(l.net_amount<>0 or l.grni_clear_amount_snapshot<>0))
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id and j.status='POSTED'
    )

  union all
  select 'V267_INVOICE_MATCH_OVER_RECEIPT','CRITICAL',count(*)::bigint,
         'Posted supplier-invoice quantity exceeds receipt quantity net of GRNI-backed returns'
  from erp.material_purchase_items i
  where erp.material_purchase_posted_invoice_qty(i.id)>erp.material_purchase_invoice_capacity(i.id)

  union all
  select 'V267_PAYMENT_EXCEEDS_FINAL_AP','CRITICAL',count(*)::bigint,
         'Supplier payment must never consume GRNI or exceed final AP'
  from erp.material_purchase_headers h
  where coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)
        >round(erp.material_purchase_final_ap_total(h.id),2)

  union all
  select 'V267_LEGACY_CORRECTION_ON_GRNI','CRITICAL',count(*)::bigint,
         'Legacy price corrections may only touch DIRECT_FINAL receipt items'
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_cost_corrections c on c.id=ci.correction_id
  join erp.material_purchase_items i on i.id=ci.purchase_item_id
  where c.status='POSTED' and i.invoice_match_state<>'DIRECT_FINAL'

  union all
  select 'V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','CRITICAL',count(*)::bigint,
         'Posted supplier returns require AP/GRNI quantity and amount snapshots'
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns rh on rh.id=ri.return_id
  where rh.status='POSTED' and(
    ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
    or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
  )

  union all
  select 'V267_GRNI_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('GRNI_MATERIAL')),0)
    -coalesce((select sum(round(erp.material_purchase_grni_total(h.id),2))
      from erp.material_purchase_headers h where h.status='POSTED'),0)
  )<>0 then 1 else 0 end::bigint,
  'GRNI general ledger must equal estimated unmatched receipt liability'

  union all
  select 'V267_AP_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('AP_SUPPLIER')),0)
    -coalesce((select sum(greatest(
      round(erp.material_purchase_final_ap_total(h.id),2)
      -coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),0
    )) from erp.material_purchase_headers h where h.status='POSTED'),0)
    -coalesce((select sum(b.original_amount-b.settled_amount)
      from erp.opening_subledger_balances b
      join erp.opening_balance_items i on i.id=b.opening_item_id
      join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
      where b.party_type='SUPPLIER' and b.direction='PAYABLE'),0)
  )<>0 then 1 else 0 end::bigint,
  'Supplier AP general ledger must equal final-invoice subledger net of payment/returns'

  union all
  select 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','CRITICAL',count(*)::bigint,
         'Supplier invoice aggregate must be writable only through v2 RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.table_name in('material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')
  union all
  select 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','CRITICAL',count(*)::bigint,
    'Supplier payment status and capacity must equal the rounded final liability of each purchase'
  from erp.material_purchase_headers h
  cross join lateral(select round(erp.material_purchase_final_ap_total(h.id),2) payable,
    coalesce((select sum(p.amount) from erp.supplier_payments p
      where p.purchase_id=h.id and p.status='POSTED'),0) paid) x
  where h.status='POSTED' and(
    x.paid<0 or x.paid>x.payable
    or x.paid::text in('NaN','Infinity','-Infinity')
    or x.payable::text in('NaN','Infinity','-Infinity')
    or(h.payment_status='PAID' and x.paid<>x.payable)
    or(h.payment_status='PARTIAL' and not(x.paid>0 and x.paid<x.payable))
    or(h.payment_status='UNPAID' and x.paid<>0))

  union all
  select 'V2620M_OPENING_SUBLEDGER_STATE','CRITICAL',count(*)::bigint,
    'Every posted financial opening requires one source-matched balance, exact settlements, and exact status'
  from erp.opening_balance_items i
  join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
  left join erp.opening_subledger_balances b on b.opening_item_id=i.id
  cross join lateral(select coalesce((select c.corrected_amount
      from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED'
      order by c.correction_seq desc limit 1),i.amount) original,
    coalesce((select sum(s.amount) from erp.opening_subledger_settlements s
      where s.balance_id=b.id and s.status='POSTED'),0)
    +coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
      where d.opening_cash_advance_balance_id=b.id and p.status='PAID'),0)
    +coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
      where r.opening_payable_balance_id=b.id and p.status='PAID'),0) paid) x
  where i.balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE',
    'CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(
    b.id is null or (select count(*) from erp.opening_subledger_balances bx where bx.opening_item_id=i.id)<>1
    or b.original_amount is distinct from x.original
    or b.settled_amount is distinct from x.paid
    or b.original_amount::text in('NaN','Infinity','-Infinity')
    or b.settled_amount::text in('NaN','Infinity','-Infinity')
    or b.original_amount<0 or b.settled_amount<0 or b.settled_amount>b.original_amount
    or b.status is distinct from case when x.paid=x.original then 'SETTLED'
      when x.paid>0 then 'PARTIAL' else 'OPEN' end
    or b.party_type is distinct from split_part(i.balance_type,'_',1)
    or b.direction is distinct from split_part(i.balance_type,'_',2)
    or b.customer_id is distinct from i.customer_id
    or b.supplier_id is distinct from i.supplier_id
    or b.vendor_id is distinct from i.vendor_id
    or b.contractor_id is distinct from i.contractor_id)

  union all
  select 'V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each supplier or opening settlement must match its own original and inverse money, accounts, party, and lifecycle'
  from(
    select p.id,p.status,p.amount,p.cash_account_id,'SUPPLIER_PAYMENT'::text source_type,
      erp.account_id('AP_SUPPLIER') balance_account,false incoming,
      null::uuid customer_id,null::uuid vendor_id,null::uuid contractor_id
    from erp.supplier_payments p
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',
      erp.account_id(case when b.party_type='CUSTOMER' then 'AR_CUSTOMER'
        when b.party_type='SUPPLIER' then 'AP_SUPPLIER'
        when b.party_type='VENDOR' then 'AP_VENDOR'
        when b.direction='RECEIVABLE' then 'CONTRACTOR_RECEIVABLE' else 'CONTRACTOR_PAYABLE' end),
      b.direction='RECEIVABLE',b.customer_id,b.vendor_id,b.contractor_id
    from erp.opening_subledger_settlements s
    join erp.opening_subledger_balances b on b.id=s.balance_id
  ) x
  left join erp.cash_accounts ca on ca.id=x.cash_account_id
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or (ca.id is null and erp.initial_prepayment_account_v1(x.id) is null and erp.bb_opening_credit_account_v1(x.id) is null)
    or (select count(*) from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED'))
      <>case when x.status='DRAFT' then 0 else 1 end
    or exists(
      select 1 from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED') and(
        j.status is distinct from x.status
        or (select count(*) from erp.journal_lines l where l.journal_entry_id=j.id)<>2
        or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(
          l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
          or l.contractor_id is distinct from x.contractor_id
          or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
                l.debit=case when x.incoming then x.amount else 0 end and
                l.credit=case when x.incoming then 0 else x.amount end)
            or (l.account_id=x.balance_account and
                l.debit=case when x.incoming then 0 else x.amount end and
                l.credit=case when x.incoming then x.amount else 0 end))))
        or (select count(*) from erp.journal_entries inv where inv.reversal_of_id=j.id)
          <>case when x.status='REVERSED' then 1 else 0 end
        or exists(select 1 from erp.journal_entries inv where inv.reversal_of_id=j.id and(
          inv.source_type<>'JOURNAL_REVERSAL' or inv.status<>'POSTED'
          or (select count(*) from erp.journal_lines l where l.journal_entry_id=inv.id)<>2
          or exists(select 1 from erp.journal_lines l where l.journal_entry_id=inv.id and(
            l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
            or l.contractor_id is distinct from x.contractor_id
            or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
                  l.credit=case when x.incoming then x.amount else 0 end and
                  l.debit=case when x.incoming then 0 else x.amount end)
              or (l.account_id=x.balance_account and
                  l.credit=case when x.incoming then 0 else x.amount end and
                  l.debit=case when x.incoming then x.amount else 0 end))))))
      ))

  union all
  select 'V2620M_ORPHAN_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,
    'A supplier payment or opening settlement journal must retain its business source'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED') and(
    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))
    or(j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and not exists(
      select 1 from erp.opening_subledger_settlements s where s.id=j.source_id)))

  union all
  select 'V2620P_SUPPLIER_RETURN_MATCH_STATE','CRITICAL',count(*)::bigint,
    'Supplier invoice match and price states must equal posted invoice quantity against current return-adjusted capacity'
  from erp.material_purchase_items i
  cross join lateral(select erp.material_purchase_invoice_capacity(i.id) capacity,
    erp.material_purchase_posted_invoice_qty(i.id) matched) x
  where i.invoice_match_state<>'DIRECT_FINAL' and(
    i.invoice_match_state is distinct from case when x.matched<=0 then 'UNMATCHED'
      when x.matched<x.capacity then 'PARTIAL' else 'MATCHED' end
    or i.price_state is distinct from case when x.matched<=0 then 'ESTIMATED'
      when x.matched<x.capacity then 'PARTIAL' else 'FINAL' end)

  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,
    'Posted supplier-return AP/GRNI snapshots must partition each line and AP relief must not exceed invoiced quantity'
  from erp.material_purchase_items i
  where exists(
    select 1
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED' and(
      ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
      or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
      or ri.ap_relief_qty_snapshot<0 or ri.grni_relief_qty_snapshot<0
      or ri.ap_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.ap_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or abs(ri.ap_relief_qty_snapshot+ri.grni_relief_qty_snapshot-ri.qty)>0.000001
      or abs(ri.ap_relief_amount_snapshot
        -ri.ap_relief_qty_snapshot*ri.supplier_credit_unit_price)>0.000001
      or abs(ri.grni_relief_amount_snapshot
        -ri.grni_relief_qty_snapshot*i.unit_price)>0.000001
    )
  ) or coalesce((
    select sum(ri.ap_relief_qty_snapshot)
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED'
  ),0)>case when i.invoice_match_state='DIRECT_FINAL' then i.qty
    else erp.material_purchase_posted_invoice_qty(i.id) end+0.000001
  or i.id in(
    with legacy_capacity as(
      select pi.id purchase_item_id,
        case when pi.invoice_match_state='DIRECT_FINAL' then pi.qty else
          coalesce((
            select sum(il.qty_invoiced)
            from erp.material_supplier_invoice_lines il
            join erp.material_supplier_invoices ih on ih.id=il.invoice_id
            where il.purchase_item_id=pi.id and ih.status='POSTED'
              and not exists(
                select 1 from erp.supplier_cent_posting_facts f
                where f.source_type='MATERIAL_SUPPLIER_INVOICE'
                  and f.source_id=ih.id and f.phase='POST'
              )
          ),0)
        end-coalesce((
          select sum(ri.ap_relief_qty_snapshot)
          from erp.material_supplier_return_items ri
          join erp.material_supplier_returns rh on rh.id=ri.return_id
          where ri.purchase_item_id=pi.id and rh.status='POSTED'
            and not exists(
              select 1 from erp.supplier_cent_posting_facts f
              where f.source_type='MATERIAL_SUPPLIER_RETURN'
                and f.source_id=rh.id and f.phase='POST'
            )
        ),0) opening_capacity
      from erp.material_purchase_items pi
    ), allocation_events as(
      select il.purchase_item_id,f.recorded_at,f.source_id,
        0 event_order,sum(il.qty_invoiced)::numeric delta,'INVOICE'::text event_kind
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_invoices ih
        on ih.id=f.source_id and ih.status='POSTED'
      join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.phase='POST'
        and pi.invoice_match_state<>'DIRECT_FINAL'
      group by il.purchase_item_id,f.recorded_at,f.source_id
      union all
      select ri.purchase_item_id,f.recorded_at,f.source_id,
        1 event_order,-sum(ri.ap_relief_qty_snapshot)::numeric,'RETURN'::text
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_returns rh
        on rh.id=f.source_id and rh.status='POSTED'
      join erp.material_supplier_return_items ri on ri.return_id=rh.id
      where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST'
      group by ri.purchase_item_id,f.recorded_at,f.source_id
    ), running_capacity as(
      select e.purchase_item_id,e.event_kind,l.opening_capacity+
        sum(e.delta) over(
          partition by e.purchase_item_id
          order by e.recorded_at,e.event_order,e.source_id
          rows between unbounded preceding and current row
        ) capacity_after
      from allocation_events e
      join legacy_capacity l using(purchase_item_id)
    )
    select purchase_item_id from running_capacity
    where event_kind='RETURN' and capacity_after < -0.000001
  )

  union all
  select 'V2620R_SUPPLIER_INVOICE_SOURCE_STATE','CRITICAL',count(*)::bigint,
    'Every posted supplier invoice must reference only posted material receipts'
  from erp.material_supplier_invoices ih
  where ih.status='POSTED' and exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=pi.purchase_id
    where il.invoice_id=ih.id and ph.status<>'POSTED'
  )

  union all
  select 'V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Opening settlement cash and subledger dates must follow the Jakarta physical event'
  from erp.journal_entries j
    join erp.opening_subledger_settlements h on h.id=j.source_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Vendor payment cash and AP dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.vendor_payments h on h.id=j.source_id
    where j.source_type='VENDOR_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.payment_date)

  union all
  select 'V2620Y_SALES_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Original customer payment cash, AR and immutable fact dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.sales_payments h on h.id=j.source_id
    join erp.sales_payment_posting_facts f on f.payment_id=h.id
    where j.source_type='SALES_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and f.replaces_payment_id is null
      and (j.economic_date is distinct from erp._cp3_business_date(f.payment_date)
        or f.journal_economic_date is distinct from erp._cp3_business_date(f.payment_date))

  union all
  select 'V2620W_SCRAP_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Paid scrap economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.scrap_sales h on h.id=j.source_id
  where j.source_type='SCRAP_SALE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620V_MISC_FINANCE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Misc finance economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.misc_finance_transactions h on h.id=j.source_id
  where j.source_type='MISC_FINANCE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material adjustment journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_adjustments h on h.id=j.source_id
  where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Generic journal reversals must use the canonical Jakarta date of posting_at'
  from erp.journal_entries j
  where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
    and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620U_MATERIAL_RECEIPT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material receipt and GRNI journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_purchase_headers h on h.id=j.source_id
  where j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')
    and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Journal economic dates may not exceed the canonical Jakarta day of the recorded posting instant'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED')
    and j.economic_date>erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','CRITICAL',count(*)::bigint,
    'Material adjustment revaluation must conserve document cents at original and corrected valuation endpoints'
  from erp.material_adjustments h
  cross join lateral(select erp._cp6_material_adjustment_revaluation_state(h.id) s) x
  where h.status in('POSTED','REVERSED')
    and (x.s->'target' is distinct from x.s->'book' or (x.s->>'incomplete_cost')::bigint>0)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Append-only material adjustment revaluation facts must match their protected original journal'
  from erp.material_adjustment_revaluation_facts f
  left join erp.journal_entries j on j.id=f.journal_entry_id
  where j.id is null or j.status<>'POSTED' or j.source_type<>'MATERIAL_ADJUSTMENT_REVALUATION'
    or j.source_id is distinct from f.id or j.economic_date is distinct from f.effective_date
    or erp._cp6_supplier_cent_ledger(array[f.journal_entry_id]) is distinct from f.ledger_delta

  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Supplier payment original journals must retain the canonical Jakarta business date in every lifecycle state'
  from erp.supplier_payments p
  join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
    and j.status in('POSTED','REVERSED')
  where p.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Supplier cent posting and linked inverse must retain their exact source and ledger vector'
  from erp.supplier_cent_posting_facts f
  where f.ledger_delta is distinct from erp._cp6_supplier_cent_ledger(array[f.journal_entry_id,f.adjustment_journal_entry_id])
    or(f.phase='POST' and f.adjustment_journal_entry_id is not null)
    or not exists(select 1 from(
      select 'MATERIAL_PURCHASE_COST_CORRECTION'::text source_type,id,status from erp.material_purchase_cost_corrections
      union all select 'MATERIAL_SUPPLIER_INVOICE',id,status from erp.material_supplier_invoices
      union all select 'MATERIAL_SUPPLIER_RETURN',id,status from erp.material_supplier_returns
    ) s where s.source_type=f.source_type and s.id=f.source_id
      and s.status=case when exists(select 1 from erp.supplier_cent_posting_facts r
        where r.source_type=f.source_type and r.source_id=f.source_id and r.phase='REVERSE') then 'REVERSED' else 'POSTED' end)
    or(f.journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.journal_entry_id and(
        (f.phase='POST' and j.source_type=f.source_type and j.source_id=f.source_id)
        or(f.phase='REVERSE' and j.source_type='JOURNAL_REVERSAL' and exists(select 1
          from erp.journal_entries original where original.id=j.reversal_of_id
            and original.source_type=f.source_type and original.source_id=f.source_id)))))
    or(f.adjustment_journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.adjustment_journal_entry_id and j.source_type='CENT_INVERSE:'||f.source_type
        and j.source_id=f.source_id))

  union all
  select 'AP_OPENING_RECEIPT_SOURCE_DRIFT','CRITICAL',count(*)::bigint,
    'Imported receipts require an exact posted opening layer and no additional purchase movement'
  from erp.initial_import_receipt_headers rh join erp.material_purchase_headers h on h.id=rh.purchase_id
  where h.status<>'POSTED' or h.supplier_id<>rh.supplier_id or erp._cp3_business_date(h.physical_at)<>rh.cutover_date
    or not exists(select 1 from erp.initial_import_receipt_lines l where l.purchase_id=h.id)
    or exists(select 1 from erp.material_purchase_items pi left join erp.initial_import_receipt_lines l on l.purchase_item_id=pi.id
      left join erp.opening_balance_items oi on oi.id=l.opening_item_id left join erp.opening_balance_headers oh on oh.id=oi.opening_id
      where pi.purchase_id=h.id and (l.purchase_id is distinct from h.id or (l.opening_item_id is not null and oh.status is distinct from 'POSTED')
        or (l.opening_item_id is not null and oi.balance_type is distinct from 'MATERIAL')
        or pi.qty is distinct from coalesce(oi.qty,0)+coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0)+coalesce((select sum(material_qty) from erp.be_pocket_receipt_origins_v1 where purchase_item_id=pi.id),0)
        or (l.opening_item_id is not null and (pi.material_id is distinct from oi.material_id or erp.bb_receipt_opening_unit_cost_v1(pi.id) is distinct from oi.unit_cost_snapshot
        or oi.location_id is distinct from h.location_id))
        or (l.opening_item_id is not null and (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'
          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1)
        or exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=pi.id)))
  union all
  select 'AP_OPENING_RECEIPT_JOURNAL_DRIFT','CRITICAL',count(*)::bigint,
    'Imported GRNI opening has exact value, opening equity offset, and cutover date'
  from erp.initial_import_receipt_headers rh
  cross join lateral(select round(sum((qty-erp.bb_receipt_invoiced_qty_v1(id))*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v
  where (v.value>0 and not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_UNINVOICED_RECEIPT'
    and j.source_id=rh.purchase_id and j.status='POSTED' and j.economic_date=rh.cutover_date
    and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(erp.account_id('OPENING_EQUITY')::text,v.value,erp.account_id('GRNI_MATERIAL')::text,-v.value)))
    or exists(select 1 from erp.journal_entries j where j.source_id=rh.purchase_id and j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS'))

  union all
  select 'AP_CASH_ADVANCE_CAPACITY','CRITICAL',count(*)::bigint,
    'Cash advance settlements plus unpaid payroll reservations must not exceed the current opening source'
  from erp.opening_subledger_balances b cross join lateral(select erp.opening_cash_advance_state_v1(b.id) s) x
  where x.s is not null and (x.s->>'available_amount')::numeric<0
  union all
  select 'AP_CASH_ADVANCE_SOURCE','CRITICAL',count(*)::bigint,
    'Cash payroll deductions must reference a posted cash advance belonging to the same contractor'
  from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
  left join erp.opening_subledger_balances b on b.id=d.opening_cash_advance_balance_id
  left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
  where d.deduction_type='CASH_ADVANCE' and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'
    or s.party_id is distinct from p.contractor_id or b.contractor_id is distinct from p.contractor_id
    or (p.status='PAID' and p.payment_date<s.cutover_date))
  union all
  select 'AP_CASH_ADVANCE_PAYROLL_JOURNAL','CRITICAL',count(*)::bigint,
    'Cash advance payroll settles receivable/payable once, with exact date and contractor dimensions'
  from erp.payroll_settlements p
  cross join lateral(select coalesce(sum(amount),0) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE') d
  where (d.amount>0 and p.status='PAID' and not exists(select 1 from erp.journal_entries j
    where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION' and j.source_id=p.id and j.status='POSTED'
      and j.economic_date=p.payment_date
      and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
        erp.account_id('CONTRACTOR_PAYABLE')::text,d.amount,erp.account_id('CONTRACTOR_RECEIVABLE')::text,-d.amount)
      and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.contractor_id is distinct from p.contractor_id)))
    or((p.status<>'PAID' or d.amount=0) and exists(select 1 from erp.journal_entries j where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION'
      and j.source_id=p.id and j.status='POSTED'))

 union all select * from erp.initial_prepayment_checks_v1()
UNION ALL SELECT * FROM erp.pocket_period_checks_v1()
 UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1();

$function$;
