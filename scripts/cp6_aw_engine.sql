CREATE OR REPLACE FUNCTION erp.period_blockers_v1(p_through date, p_window_from date)
 RETURNS TABLE(family text, code text, severity text, scope text, impact_date date, reference jsonb, reason text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- One engine for close, preview and report confidence (S06/B04).
-- Open items (recost, laundry price, payroll due, dated integrity) use every fact dated on or before p_through.
-- Completeness (attendance cells) uses the window [p_window_from, p_through]; a null start means unbounded. Callers
-- pass erp.period_completeness_from_v1(), the first date this engine was responsible for, so a closed date inside
-- the engine's era is re-checked after a later correction (P-01). Before that start only cells that once had a
-- posted record and lost it (reversed, not replaced) are reported.
-- Stock history follows the posting guards' own order (P-04). A current-state check whose defect is scoped by a
-- dated detector is reported as INFO once the detector confirms it; every other failing current-state check blocks
-- every date and names its class (P-03). Unknown check names block (fail closed).
declare
  v_end timestamptz := ((p_through + 1)::timestamp AT TIME ZONE 'Asia/Jakarta');
  v_fg jsonb;
  v_material jsonb;
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

  -- FG history per SKU and per lot, in the order the posting guard uses (physical_at, system_created_at, id): every
  -- prefix, not the net per instant (P-04). Computed over the whole history once; a key blocks the dates from its
  -- first negative instant.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_fg from (
    select jsonb_build_object('level',s.lvl,'product_id',min(s.product_id::text),'lot_id',s.lot_id,
      'location_id',s.location_id,'quality_grade',s.quality_grade,
      'first_negative_at',min(s.physical_at) filter(where s.balance<0),
      'lowest_qty',min(s.balance)) k
    from (
      select 'SKU'::text lvl,m.product_id,null::uuid lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.product_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) balance
      from erp.fg_stock_movements m
      union all
      select 'LOT'::text,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.lot_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding)
      from erp.fg_stock_movements m where m.lot_id is not null
    ) s
    group by s.lvl,case when s.lvl='SKU' then s.product_id end,s.lot_id,s.location_id,s.quality_grade
    having bool_or(s.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'FG_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok barang jadi (%s) negatif sejak %s untuk produk %s di lokasi %s.',
      k->>'level',k->>'first_negative_at',k->>'product_id',k->>'location_id')
  from jsonb_array_elements(v_fg) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Material history on the cost engine's effective history and its exact order (reversed pairs excluded, a
  -- transfer-in ordered right after its transfer-out), per material, location and roll.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_material from (
    with active as (
      select m.*,row_number() over(partition by m.material_id,m.source_id,m.roll_id,m.physical_at,
          abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
      from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER' and m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ), pairs as (
      select i.id incoming,o.id outgoing,o.system_created_at out_created
      from active i join active o on o.material_id=i.material_id and o.source_id=i.source_id
        and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
        and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
        and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
      where i.movement_type='TRANSFER_IN' and i.qty_signed>0
        and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
        and o.location_id<>i.location_id
    ), history as (
      select m.material_id,m.location_id,m.roll_id,m.physical_at,
        sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
          order by m.physical_at,coalesce(p.out_created,m.system_created_at),coalesce(p.outgoing,m.id),
            (p.outgoing is not null) rows unbounded preceding) balance
      from erp.material_stock_movements m
      left join pairs p on p.incoming=m.id
      where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    )
    select jsonb_build_object('material_id',h.material_id,'location_id',h.location_id,'roll_id',h.roll_id,
      'first_negative_at',min(h.physical_at) filter(where h.balance<0),'lowest_qty',min(h.balance)) k
    from history h
    group by h.material_id,h.location_id,h.roll_id
    having bool_or(h.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'MATERIAL_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok bahan negatif sejak %s untuk bahan %s.',k->>'first_negative_at',k->>'material_id')
  from jsonb_array_elements(v_material) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- INTEGRITY (current state), classified (P-03). Queue checks are handled per date by RECOST above.
  return query
  with failing as (
    select distinct on (c.check_name) c.check_name,c.src,c.issue_count,c.details from (
      select 'run_v268_financial_report_checks' src,r.check_name,r.severity,r.issue_count,r.details from erp.run_v268_financial_report_checks() r
      union all
      select 'run_v267_financial_truth_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_v267_financial_truth_checks() r
      union all
      select 'run_integrity_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_integrity_checks() r
    ) c
    where c.issue_count>0 and c.severity in('CRITICAL','ERROR')
      and c.check_name not in('V268_COST_RECALC_EXHAUSTED','V268_COST_RECALC_PENDING','STALE_RECOST_QUEUE','FAILED_RECOST_QUEUE')
    order by c.check_name,c.src
  ), registry(check_name,check_class,dated_by) as (
    select * from erp.period_integrity_check_registry_v1()
  ), classified as (
    select f.*,coalesce(r.check_class,'UNCLASSIFIED') check_class,r.dated_by,
      case r.dated_by when 'FG_QTY_NEGATIVE_ASOF' then jsonb_array_length(v_fg)>0
                      when 'MATERIAL_QTY_NEGATIVE_ASOF' then jsonb_array_length(v_material)>0
                      else false end confirmed
    from failing f left join registry r on r.check_name=f.check_name
  )
  select 'INTEGRITY'::text,c.check_name,
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'INFO' else 'CRITICAL' end,
    'CURRENT_STATE'::text,null::date,
    jsonb_build_object('check_name',c.check_name,'issue_count',c.issue_count,'source',c.src,'class',c.check_class,
      'dated_by',c.dated_by,'dated_detector_confirmed',c.confirmed,
      'date_policy',case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'SCOPED_BY_DATED_DETECTOR'
                         else 'BLOCKS_EVERY_DATE' end),
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed
      then format('%s: dibatasi per tanggal oleh %s.',coalesce(c.details,c.check_name),c.dated_by)
      else coalesce(c.details,c.check_name) end
  from classified c;

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

  -- ATTENDANCE (window): eligible worker-days without a current posted record (owner: existing rule, OFF recorded).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_MISSING'::text,'POLICY'::text,'WINDOW'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
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

  -- ATTENDANCE (before the window): an eligible worker-day that had a posted record which was later reversed and
  -- never replaced. The date was complete when it was accepted; a later change removed it (P-01).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_REVERSED_UNREPLACED'::text,'POLICY'::text,'AS_OF'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) pada %s hari antara %s dan %s sudah dibatalkan dan belum dicatat ulang.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select distinct w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,r.attendance_date work_day
    from erp.attendance_records r
    join erp.contractor_workers w on w.id=r.worker_id
    join erp.contractors c on c.id=w.contractor_id
    where p_window_from is not null and r.attendance_date<p_window_from and r.attendance_date<=p_through
      and r.record_lifecycle='REVERSED'
      and c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id
        and r.attendance_date between e.started_on and coalesce(e.ended_on,r.attendance_date))
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=r.attendance_date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
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

  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_INVALID'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'rate',ldl.estimated_rate_snapshot::text),
    format('Harga laundry kiriman %s tidak valid (%s); harga harus angka hingga dan tidak negatif.',
      ld.delivery_number,ldl.estimated_rate_snapshot::text)
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and (ldl.estimated_rate_snapshot='NaN'::numeric or ldl.estimated_rate_snapshot<0);

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
  'info',coalesce(jsonb_agg(to_jsonb(b) order by b.family,b.code,b.reference::text) filter(where b.severity='INFO'),'[]'::jsonb))
from erp.period_blockers_v1(p_through,p_window_from) b
$function$

CREATE OR REPLACE FUNCTION erp.period_completeness_from_v1()
 RETURNS date
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- First date whose completeness this engine enforces (P-01). Before the first filing it is the day after the
-- current closed_through; afterwards it stays at the day after the first filing's previous cutoff, so every date
-- closed by the engine is re-checked after a later correction. A reopen below that day moves it back. Null means
-- unbounded (nothing was ever closed, or the first filing started from an empty cutoff).
select case
  when c.closed_through is null then null
  when f.id is null then c.closed_through+1
  when f.previous_closed_through is null then null
  else least(f.previous_closed_through+1,c.closed_through+1) end
from erp.accounting_period_control c
left join lateral (select x.id,x.previous_closed_through from erp.accounting_close_filings_v1 x
  order by x.filed_at,x.id limit 1) f on true
where c.singleton_id=1
$function$
