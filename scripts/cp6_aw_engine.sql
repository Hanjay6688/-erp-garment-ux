CREATE OR REPLACE FUNCTION erp.period_blockers_v1(p_through date, p_window_from date)
 RETURNS TABLE(family text, code text, severity text, scope text, impact_date date, reference jsonb, reason text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- One engine for close, preview and report confidence (S06/B04).
-- Open items (recost, laundry price, payroll due, dated integrity) use every fact dated on or before p_through.
-- Completeness (attendance cells) uses the window [p_window_from, p_through]; a null start means unbounded.
-- Current-state integrity checks cannot be dated and therefore apply to every date (scope CURRENT_STATE).
declare
  v_end timestamptz := ((p_through + 1)::timestamp AT TIME ZONE 'Asia/Jakarta');
begin
  if p_through is null then raise exception 'PERIOD_BLOCKERS_DATE_REQUIRED'; end if;

  -- RECOST: open queue rows whose PO has a dated fact on or before the date.
  return query
  select 'RECOST'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'RECOST_FAILED_EXHAUSTED' else 'RECOST_PENDING' end,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,
    'AS_OF'::text, f.first_date,
    jsonb_build_object('queue_id',q.id,'po_id',q.entity_id,'po_number',po.po_number,'status',q.status,
      'attempt_count',q.attempt_count,'recalc_from',q.recalc_from,'facts',f.facts),
    format('Hitung ulang biaya PO %s belum selesai (status %s, percobaan %s); PO ini punya fakta pada atau sebelum %s.',
      coalesce(po.po_number,q.entity_id::text),q.status,q.attempt_count,p_through)
  from erp.cost_recalc_queue q
  left join erp.production_orders po on po.id=q.entity_id
  cross join lateral (
    select min(x.d) first_date, jsonb_agg(distinct x.k) facts from (
      select 'RECALC_FROM' k, erp._cp3_business_date(q.recalc_from) d where q.recalc_from is not null and q.recalc_from<v_end
      union all
      select 'CUTTING_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
        where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'CONTRACTOR_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m
        join erp.contractor_material_issue_items ii on ii.id=m.source_id
        join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
        where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'FG_LOT', min(erp._cp3_business_date(fl.produced_at))
        from erp.fg_lots fl where fl.po_id=q.entity_id and fl.produced_at<v_end having count(*)>0
      union all
      select 'PO_JOURNAL', min(je.economic_date)
        from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED') and je.economic_date<=p_through
        having count(*)>0
    ) x
  ) f
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and f.first_date is not null;

  -- A queue row for another entity type cannot be scoped to a date: conservative, every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status),
    format('Antrean hitung ulang %s %s belum selesai dan tidak dapat dibatasi ke tanggal.',q.entity_type,q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type<>'PO' and q.status in('PENDING','RUNNING','FAILED');

  -- INTEGRITY (current state): failing CRITICAL/ERROR checks, queue checks excluded (handled per date above).
  return query
  select distinct on (c.check_name) 'INTEGRITY'::text,c.check_name,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('check_name',c.check_name,'issue_count',c.issue_count,'source',c.src),
    coalesce(c.details,c.check_name)
  from (
    select 'run_v268_financial_report_checks' src,r.check_name,r.severity,r.issue_count,r.details from erp.run_v268_financial_report_checks() r
    union all
    select 'run_v267_financial_truth_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_v267_financial_truth_checks() r
    union all
    select 'run_integrity_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_integrity_checks() r
  ) c
  where c.issue_count>0 and c.severity in('CRITICAL','ERROR')
    and c.check_name not in('V268_COST_RECALC_EXHAUSTED','V268_COST_RECALC_PENDING','STALE_RECOST_QUEUE','FAILED_RECOST_QUEUE')
  order by c.check_name,c.src;

  -- INTEGRITY (dated): GL inventory balance negative at any balance date on or before the date.
  return query
  select 'INTEGRITY'::text,'GL_INVENTORY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,min(g.balance_date),
    jsonb_build_object('account',g.mapping_key,'first_negative_date',min(g.balance_date),'lowest_balance',min(g.balance)),
    format('Saldo buku %s negatif sejak %s (terendah %s).',g.mapping_key,min(g.balance_date),min(g.balance))
  from (
    select k.mapping_key,a.balance_date,
      sum(a.debit_total-a.credit_total) over(partition by a.account_id order by a.balance_date) balance
    from erp.account_daily_balances a
    join (values('MATERIAL_INVENTORY'),('WIP'),('FG_INVENTORY')) k(mapping_key) on a.account_id=erp.account_id(k.mapping_key)
    where a.balance_date<=p_through
  ) g
  where g.balance<-0.005
  group by g.mapping_key;

  -- INTEGRITY (dated): FG quantity negative after any physical instant on or before the date.
  return query
  select 'INTEGRITY'::text,'FG_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(min(s.physical_at)),
    jsonb_build_object('product_id',s.product_id,'location_id',s.location_id,'quality_grade',s.quality_grade,
      'first_negative_at',min(s.physical_at),'lowest_qty',min(s.balance)),
    format('Stok barang jadi negatif sejak %s untuk produk %s di lokasi %s.',min(s.physical_at),s.product_id,s.location_id)
  from (
    select i.product_id,i.location_id,i.quality_grade,i.physical_at,
      sum(i.qty) over(partition by i.product_id,i.location_id,i.quality_grade order by i.physical_at) balance
    from (
      select m.product_id,m.location_id,m.quality_grade,m.physical_at,sum(m.qty_signed) qty
      from erp.fg_stock_movements m where m.physical_at<v_end
      group by 1,2,3,4
    ) i
  ) s
  where s.balance<0
  group by s.product_id,s.location_id,s.quality_grade;

  -- INTEGRITY (dated): material quantity negative on the cost engine's effective history (reversed pairs excluded).
  return query
  select 'INTEGRITY'::text,'MATERIAL_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(min(s.physical_at)),
    jsonb_build_object('material_id',s.material_id,'location_id',s.location_id,'roll_id',s.roll_id,
      'first_negative_at',min(s.physical_at),'lowest_qty',min(s.balance)),
    format('Stok bahan negatif sejak %s untuk bahan %s.',min(s.physical_at),s.material_id)
  from (
    select i.material_id,i.location_id,i.roll_id,i.physical_at,
      sum(i.qty) over(partition by i.material_id,i.location_id,i.roll_id order by i.physical_at) balance
    from (
      select m.material_id,m.location_id,m.roll_id,m.physical_at,sum(m.qty_signed) qty
      from erp.material_stock_movements m
      where m.physical_at<v_end and m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
      group by 1,2,3,4
    ) i
  ) s
  where s.balance<-0.000001
  group by s.material_id,s.location_id,s.roll_id;

  -- ATTENDANCE (window): eligible worker-days without a current posted record (owner: existing rule, OFF recorded).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_MISSING'::text,'POLICY'::text,'WINDOW'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10]),
    format('Absensi %s (%s) kosong %s hari antara %s dan %s; hari libur dicatat OFF.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,gs.d::date as work_day
    from erp.contractor_workers w
    join erp.contractors c on c.id=w.contractor_id
    join erp.worker_employment_periods e on e.worker_id=w.id
    cross join lateral generate_series(
      greatest(e.started_on,coalesce(p_window_from,e.started_on))::timestamp,
      least(coalesce(e.ended_on,p_through),p_through)::timestamp,interval '1 day') gs(d)
    where c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=gs.d::date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- PAYROLL: payroll due on or before the date that is not approved (owner: labour recognised at period_end).
  return query
  select 'PAYROLL'::text,'PAYROLL_NOT_APPROVED'::text,'POLICY'::text,'AS_OF'::text,ps.period_end,
    jsonb_build_object('payroll_id',ps.id,'payroll_number',ps.payroll_number,'contractor_id',ps.contractor_id,
      'period_start',ps.period_start,'period_end',ps.period_end,'status',ps.status),
    format('Payroll %s (%s s/d %s) masih %s; belum disetujui.',ps.payroll_number,ps.period_start,ps.period_end,ps.status)
  from erp.payroll_settlements ps
  where ps.status in('DRAFT','CALCULATED','REVIEW') and ps.period_end<=p_through;

  -- PAYROLL: paid attendance on or before the date that no non-reversed payroll has taken (linkage, not date range).
  return query
  select 'PAYROLL'::text,'PAYROLL_ATTENDANCE_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,min(ar.attendance_date),
    jsonb_build_object('contractor_id',ar.contractor_id,'worker_id',ar.worker_id,'worker_name',w.worker_name,
      'records',count(*),'first_date',min(ar.attendance_date),'last_date',max(ar.attendance_date)),
    format('Absensi %s: %s hari berbayar antara %s dan %s belum masuk payroll.',w.worker_name,count(*),min(ar.attendance_date),max(ar.attendance_date))
  from erp.attendance_records ar
  join erp.contractor_workers w on w.id=ar.worker_id
  join erp.contractors c on c.id=ar.contractor_id
  where ar.attendance_date<=p_through and coalesce(ar.record_lifecycle,'POSTED')='POSTED'
    and ar.paid_fraction>0 and w.pay_scheme in('DAILY','HYBRID') and c.attendance_required
    and not exists(select 1 from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id
      where pai.attendance_record_id=ar.id and ps.status<>'REVERSED')
  group by ar.contractor_id,ar.worker_id,w.worker_name;

  -- PAYROLL: eligible piece or rework work on or before the date that no non-reversed payroll has taken.
  return query
  select 'PAYROLL'::text,'PAYROLL_WORK_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,
    min(erp._cp3_business_date(e.eligible_at)),
    jsonb_build_object('contractor_id',e.contractor_id,'lines',count(*),'remaining_qty',sum(e.remaining_qty),
      'remaining_amount',sum(e.remaining_amount),'first_eligible_at',min(e.eligible_at)),
    format('Hasil kerja kontraktor %s: %s baris (%s pcs) pada atau sebelum %s belum masuk payroll.',
      e.contractor_id,count(*),sum(e.remaining_qty),p_through)
  from erp.v_payroll_eligible_work_lines e
  where e.eligible_at<v_end and e.remaining_qty>0
  group by e.contractor_id;

  -- LAUNDRY: sent quantity still costed at an unknown (null) delivery rate on or before the date.
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'uncosted_qty',greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0)),
    format('Harga laundry kiriman %s belum diketahui untuk %s pcs; isi estimasi owner.',
      ld.delivery_number,greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0))
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where ld.status not in('DRAFT','REVERSED') and ldl.estimated_rate_snapshot is null
    and ld.physical_at<v_end and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0;

  -- GRNI: owner allows close with an estimate; reported, never blocking.
  return query
  select 'GRNI'::text,'GRNI_ESTIMATE_OPEN'::text,'INFO'::text,'CURRENT_STATE'::text,
    erp._cp3_business_date(min(g.physical_at)),
    jsonb_build_object('receipts',count(*),'estimated_amount',sum(g.grni_estimated_amount)),
    format('%s penerimaan bahan masih memakai estimasi GRNI (total %s); boleh ditutup dengan estimasi.',count(*),sum(g.grni_estimated_amount))
  from erp.v_material_grni_aging g
  where g.physical_at<v_end
  having count(*)>0;
end
$function$

CREATE OR REPLACE FUNCTION erp.period_readiness_v1(p_through date, p_window_from date)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
select jsonb_build_object(
  'engine','PERIOD_READINESS_V1','through',p_through,'window_from',p_window_from,
  'status',case when coalesce(bool_or(b.severity in('CRITICAL','POLICY')),false) then 'BLOCKED'
                when coalesce(bool_or(b.severity='RECALC'),false) then 'RECALC_PENDING' else 'READY' end,
  'blocker_count',count(*) filter(where b.severity<>'INFO'),
  'critical_count',count(*) filter(where b.severity='CRITICAL'),
  'policy_count',count(*) filter(where b.severity='POLICY'),
  'recalc_count',count(*) filter(where b.severity='RECALC'),
  'blockers',coalesce(jsonb_agg(to_jsonb(b) order by b.family,b.code,b.impact_date nulls first,b.reference::text) filter(where b.severity<>'INFO'),'[]'::jsonb),
  'info',coalesce(jsonb_agg(to_jsonb(b) order by b.family,b.code) filter(where b.severity='INFO'),'[]'::jsonb))
from erp.period_blockers_v1(p_through,p_window_from) b
$function$
