
declare
  v_assets numeric:=0;v_liabilities numeric:=0;v_equity numeric:=0;v_current_earnings numeric:=0;
  v_cash numeric:=0;v_ar numeric:=0;v_material numeric:=0;v_wip numeric:=0;v_fg numeric:=0;
  v_ap numeric:=0;v_grni numeric:=0;
  v_sales_revenue numeric:=0;v_cogs numeric:=0;v_other_income numeric:=0;v_opex numeric:=0;v_net_profit numeric:=0;
  v_gross_sales numeric:=0;v_discounts numeric:=0;v_sales_returns numeric:=0;
  v_operational_net_sales numeric:=0;v_sales_revenue_bridge numeric:=0;
  v_qc_good numeric:=0;v_qc_bs numeric:=0;
  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;
  v_laundry_outstanding numeric:=0;
  v_failed_checks jsonb:='[]'::jsonb;
  v_grni_docs bigint:=0;v_grni_oldest integer:=0;v_ap_docs bigint:=0;v_ap_overdue numeric:=0;
  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;
begin
  perform erp.require_owner_admin();
  if p_from is null or p_to is null or p_as_of is null then raise exception 'p_from, p_to and p_as_of are required'; end if;
  if p_from>p_to then raise exception 'p_from cannot be after p_to'; end if;
  if p_to>p_as_of then raise exception 'p_to cannot be after p_as_of'; end if;

  select
    coalesce(sum(case when ca.account_type='ASSET' then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='LIABILITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EQUITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_assets,v_liabilities,v_equity,v_current_earnings
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date<=p_as_of;

  select coalesce(sum(a.debit_total-a.credit_total),0) into v_cash
  from erp.account_daily_balances a
  where a.balance_date<=p_as_of and a.account_id in(
    select ca.coa_account_id from erp.cash_accounts ca
    union select erp.account_id('CASH')
  );
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_ar
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AR_CUSTOMER');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_material
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('MATERIAL_INVENTORY');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_wip
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('WIP');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_fg
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('FG_INVENTORY');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_ap
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AP_SUPPLIER');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_grni
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('GRNI_MATERIAL');

  select
    coalesce(sum(case when a.account_id=erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when a.account_id=erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='REVENUE' and a.account_id<>erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EXPENSE' and a.account_id<>erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_sales_revenue,v_cogs,v_other_income,v_opex,v_net_profit
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date between p_from and p_to;

  with sale_events as(
    select original.source_id sale_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALE' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALE'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.qty_pcs*i.unit_price_snapshot),0),
         coalesce(sum(e.event_sign*i.discount_amount),0)
  into v_gross_sales,v_discounts
  from sale_events e join erp.sales_items i on i.sale_id=e.sale_id;

  with return_events as(
    select original.source_id return_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALES_RETURN' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALES_RETURN'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.refund_amount),0) into v_sales_returns
  from return_events e join erp.sales_return_items i on i.return_id=e.return_id;
  v_operational_net_sales:=round(v_gross_sales-v_discounts-v_sales_returns,2);
  v_sales_revenue_bridge:=round(v_operational_net_sales-v_sales_revenue,2);

  select coalesce(sum(i.qty_good_pcs),0),coalesce(sum(i.qty_bs_pcs),0)
  into v_qc_good,v_qc_bs
  from erp.qc_inspection_items i join erp.qc_inspections h on h.id=i.inspection_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;
  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;

  select greatest(coalesce(sum(case
    when w.stage_to='LAUNDRY' then w.qty_pcs
    when w.stage_from='LAUNDRY' then -w.qty_pcs
    else 0 end),0),0)
  into v_laundry_outstanding
  from erp.wip_stage_events w
  where erp._cp3_business_date(w.physical_at)<=p_as_of
    and w.source_type in(
      'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
    );

  select count(*)::bigint,coalesce(max(unfinalized_days),0)::integer
  into v_grni_docs,v_grni_oldest from erp.v_material_grni_aging;
  select count(*)::bigint,coalesce(sum(case when days_overdue>0 then outstanding_amount else 0 end),0)
  into v_ap_docs,v_ap_overdue from erp.v_supplier_ap_aging where outstanding_amount>0.005;

  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;
  if abs(v_sales_revenue_bridge)>0.005 then
    v_critical:=v_critical+1;
    v_failed_checks:=v_failed_checks||jsonb_build_array(jsonb_build_object(
      'check_name','V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH',
      'severity','CRITICAL','issue_count',1,
      'details','Signed Sale/Sales-return lifecycle events do not reconcile to SALES_REVENUE for the selected posting period'
    ));
  end if;
  select count(*)::bigint into v_pending from erp.cost_recalc_queue
  where status in('PENDING','RUNNING') or(status='FAILED' and attempt_count<3);

  return jsonb_build_object(
    'basis',jsonb_build_object(
      'period_from',p_from,'period_to',p_to,'balance_sheet_as_of',p_as_of,
      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE',
      'performance_lifecycle_basis','SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD',
      'performance_reconciliation_basis','OPERATIONAL_NET_SALES_MINUS_SALES_REVENUE_GL',
      'quality_event_basis','CURRENT_OPERATIONAL_STATE_WITH_EVENT_DATE_CUTOFF',
      'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'
    ),
    'data_confidence',jsonb_build_object(
      'status',case when v_critical>0 then 'BLOCKED'
                    when v_pending>0 then 'RECALC_PENDING' else 'READY' end,
      'critical_issue_count',v_critical,'warning_issue_count',v_warning,
      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks
    ),
    'financial_position',jsonb_build_object(
      'assets',round(v_assets,2),'cash',round(v_cash,2),'customer_ar',round(v_ar,2),
      'material_inventory',round(v_material,2),'wip_inventory',round(v_wip,2),'fg_inventory',round(v_fg,2),
      'liabilities',round(v_liabilities,2),'supplier_final_ap',round(v_ap,2),
      'grni_estimated_liability',round(v_grni,2),'recorded_equity',round(v_equity,2),
      'current_earnings',round(v_current_earnings,2),
      'liabilities_plus_equity',round(v_liabilities+v_equity+v_current_earnings,2),
      'balance_difference',round(v_assets-v_liabilities-v_equity-v_current_earnings,2)
    ),
    'performance',jsonb_build_object(
      'sales_revenue_gl',round(v_sales_revenue,2),'cogs_gl',round(v_cogs,2),
      'gross_profit',round(v_sales_revenue-v_cogs,2),
      'gross_margin_pct',case when abs(v_sales_revenue)>0.005 then round((v_sales_revenue-v_cogs)*100/v_sales_revenue,4) else null end,
      'other_income',round(v_other_income,2),'operating_and_other_expense',round(v_opex,2),
      'net_profit',round(v_net_profit,2),
      'net_margin_pct',case when abs(v_sales_revenue)>0.005 then round(v_net_profit*100/v_sales_revenue,4) else null end,
      'gross_sales_before_discount',round(v_gross_sales,2),'line_discounts',round(v_discounts,2),
      'posted_sales_returns',round(v_sales_returns,2),
      'operational_net_sales',v_operational_net_sales,
      'sales_revenue_bridge_delta',v_sales_revenue_bridge,
      'sales_revenue_reconciled',abs(v_sales_revenue_bridge)<=0.005
    ),
    'quality',jsonb_build_object(
      'qc_good_pcs',v_qc_good,'qc_bs_pcs',v_qc_bs,
      'qc_defect_rate_pct',case when v_qc_good+v_qc_bs>0 then round(v_qc_bs*100/(v_qc_good+v_qc_bs),4) else null end,
      'laundry_good_received_pcs',v_laundry_good,'laundry_bs_pcs',v_laundry_bs,
      'laundry_bs_rate_on_resolved_receipts_pct',case when v_laundry_good+v_laundry_bs>0 then round(v_laundry_bs*100/(v_laundry_good+v_laundry_bs),4) else null end,
      'laundry_outstanding_pcs',v_laundry_outstanding,
      'legacy_receipt_stuck_pcs',v_laundry_stuck,'legacy_receipt_missing_pcs',v_laundry_missing
    ),
    'supplier_exposure',jsonb_build_object(
      'unfinalized_receipt_count',v_grni_docs,'oldest_unfinalized_days',v_grni_oldest,
      'open_final_ap_document_count',v_ap_docs,'overdue_final_ap_amount',round(v_ap_overdue,2)
    )
  );
end
