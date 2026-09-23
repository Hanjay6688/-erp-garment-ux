# AW design: per-date close readiness engine (AUD-S06 + AUD-B04)

Status: writer design notes (Claude, 23 September 2026), frozen with the Claude writer at the A+B decision
(handoff §18). Code: `scripts/cp6_aw_engine.sql`, `scripts/cp6_aw_definitions.py`; local smoke:
`scripts/cp6_aw_local_smoke.py`, `docs/evidence/cp6-aw/local_pg16_smoke.json`. Not packaged, not native, not reviewed.
Where the "Refinements from the code map" section at the end differs from an earlier line, the refinement is what the
code implements. Code-fact sources: `docs/evidence/cp6-aw/static_code_map_s06.md` and
`docs/evidence/cp6-aw/static_code_map_engine_queries.md` (read-only sub-agent maps, STATIC, not native).


Successor on AU + AV rev2. Version v2.6.20aw. One engine, read by close (command), preview (facade) and the report
(get_owner_financial_snapshot_v2 data_confidence). CP7 wires UI/BR/reminder to the same engine later.

## Owner policy (recorded)
- Blockers: recost pending/failed for the period; stock/journal mismatch; attendance empty on a working day;
  payroll not approved; laundry price unknown until owner enters an estimate. GRNI may close with estimate.
  Period-scoped. "kapan pun koreksi masuk, laporan menunjukkan angka sebenarnya".
- Payroll straddling D: labour recognised at payroll period_end (existing). Payroll with period_end > D does not block.
  Payroll with period_end <= D must be APPROVED/PAID. Worker-days <= D with attendance / eligible work that no
  non-reversed payroll covers still block.
- Working day: existing rule. Every eligible DAILY/HYBRID worker-day (employed, attendance-required contractor) in
  the window needs a current posted record (OFF for holidays). No calendar table.

## Windows
- Open-item families use everything dated <= D: recost queue, laundry unknown price, payroll period_end <= D not approved,
  dated integrity.
- Completeness families (attendance cells, payroll coverage) use W = (C, D], C = closed_through read under the lock
  (close) or current closed_through (report). For a report date X <= C the window is empty: completeness was enforced
  at close; later corrections surface through open-item families.
- Current-state integrity checks cannot be dated: they block every date (label CURRENT_STATE, conservative).

## Atomicity
- Preflight is STABLE: all its statements share the snapshot of the calling statement.
- close: FOR UPDATE on accounting_period_control, then one statement calls preflight -> snapshot taken after the lock.
- Producers that read closed_through take FOR SHARE (post_journal, recost core, transfers, negative-stock trigger):
  serialized. Producers that never read closed_through do not depend on close, so ordering them after close is a
  valid serial order; their dated facts become late changes (same as after close).
- Race cases to prove (CROSS-T06): backdated material issue (queue row for <= D) vs close, both orders, commit and abort;
  attendance reversal vs close.

## Filing
- accounting_close_filings_v1 insert-only: closed_through, previous, closed_at, closed_by, reason, engine, preflight
  jsonb (READY), balances jsonb (GL per account as of D from account_daily_balances). Filed snapshot never overwritten;
  current-corrected read = engine at D now.

## Families and codes (severity)
- RECOST: RECOST_PENDING (RECALC), RECOST_FAILED_EXHAUSTED (CRITICAL). Affects <= D if the PO has consumption movement,
  fg lot, journal line (economic_date) or recalc_from on or before D.
- INTEGRITY_CURRENT (CRITICAL): failing CRITICAL checks of run_v268_financial_report_checks except the two queue checks;
  AP_* checks and V267_GRNI_MAPPING_INVALID / V267_MISSING_GRNI_MAPPING / V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS
  from run_v267_financial_truth_checks; ERROR checks of run_integrity_checks except the two queue checks.
- INTEGRITY_DATED (CRITICAL): negative FG qty at any instant <= D; negative material qty at any instant <= D;
  negative GL inventory (MATERIAL/WIP/FG) at any balance date <= D. Each check stays inside one side (physical or GL).
  REJECTED: "zero physical qty but GL value" per date. Physical and GL dates legitimately differ: a late fact dated in
  a closed period posts its GL at max(today, closed+1), so between the physical and GL dates such a check would block
  closing D forever for a legitimate posting. B04 is proven instead by late-invoice scenarios whose as-of values and
  confidence are compared on the same dates (estimate 100 -> invoice 107, 1-3 months late, part WIP/FG/sold,
  queue pending, Jakarta/UTC/Kiritimati, closed-period boundary).
- ATTENDANCE (POLICY): ATTENDANCE_CELL_MISSING per worker/date in W.
- PAYROLL (POLICY): PAYROLL_NOT_APPROVED (period_end <= D), PAYROLL_ATTENDANCE_UNCOVERED (W),
  PAYROLL_WORK_UNCOVERED (eligible_at <= D).
- LAUNDRY (POLICY): LAUNDRY_PRICE_UNKNOWN (delivery/receipt line PENDING, dated <= D).
- GRNI (INFO): open estimated GRNI count/amount; never blocks.

## Report mapping
- status BLOCKED if any CRITICAL or POLICY blocker; RECALC_PENDING if only RECALC; else READY.
- Keep existing keys; add engine, as_of, window_from, blockers. V2620D sales bridge stays report-scoped.

## Open points (writer decisions, to review)
- Owner estimate for unknown laundry price: RPC + insert-only estimate table; mechanics pending code map.

## Acceptance cases (probe before on AU+AV, after on AU+AV+AW)
S06 table (GPT audit §6) + owner policy. Real business paths where possible; administrative fixtures labelled.
1. RECOST_IN_PERIOD: backdated material issue (real RPC) makes the core queue a PO row whose consumption <= D -> close
   refused atomically (closed_through and journals unchanged), preview BLOCKED/RECALC with the PO, report RECALC_PENDING.
2. RECOST_AFTER_PERIOD: queue row for a PO whose facts are all after D (the old S06 fixture shape) -> close accepted,
   report READY for D. Control against over-blocking.
3. RECOST_EXHAUSTED_IN_PERIOD: attempt_count>=3 on a PO with facts <= D -> refused, CRITICAL.
4. LATE_INVOICE (B04): estimate 100, consumption, FG, part sold, invoice 107 one to three months later: as-of values on
   dates before/after invoice follow ERP-DEC01; confidence equals engine; queue pending only while unprocessed.
5. HISTORICAL_WRONG_TODAY_CLEAN: dated negative (FG qty or GL inventory) at a date <= D, repaired later -> D BLOCKED.
   Reverse control: defect dated after D only -> D READY.
6. CRITICAL_NON_QUEUE: a current-state CRITICAL check fails -> preview, close and report agree, owner-readable reason.
7. PROCESSED_AFTER_CLOSE: close D READY; late change queues a recost for <= D; process queue: GL delta in open period,
   filing row for D unchanged, current-corrected engine for D READY after processing.
8. RACES (two sessions): posting-vs-close and worker-vs-close, both commit orders and abort.
9. POLICY: attendance empty cell in W blocks; OFF recorded passes; payroll period_end <= D not approved blocks;
   straddling payroll does not block; attendance/work uncovered by payroll blocks; laundry PENDING blocks until owner
   estimate; GRNI open estimate does not block (INFO).
10. ACCESS: non-owner preview and close refused with no effect; public facade and backend return the same result.
11. Regression: AR174, AT16/AU15 + races, AV probe after, 326 + AS34 with per-case disposition of every moved case
    (8 modules call close mid-scenario); 12 HOLD kept.

## Refinements from the code map (notes/aw_code_facts.md)
- LAUNDRY_PRICE_UNKNOWN reduces to one query: delivery lines of non-DRAFT/non-REVERSED deliveries dated <= D with
  estimated_rate_snapshot IS NULL and uncosted qty > 0 (qty_sent - good+bs of POSTED receipt lines ESTIMATED/FINAL).
  A PENDING receipt line falls back to the delivery rate in both accrual (CP6L:840-843) and HPP (AP:5430, 5584), so it
  is unknown only when the delivery rate is null, which the delivery query already covers. PENDING-with-rate = known.
- Owner estimate = set the delivery line rate. The existing trigger posts the accrual (delivery date) and rebuilds
  HPP synchronously; the RPC must also call sync_finished_po_wip_residual for a FINISHED PO (the trigger does not).
  Record an insert-only estimate row (who, when, rate, reason). Only lines whose rate is still null; a known rate is
  never overwritten by this RPC.
- PAYROLL: (i) DRAFT/CALCULATED/REVIEW with period_end <= D; (ii) attendance records <= D, current posted,
  paid_fraction > 0, DAILY/HYBRID, contractor attendance_required (master flag, as payroll uses), with no link in
  payroll_attendance_items of a non-REVERSED payroll (linkage, not range); (iii) v_payroll_eligible_work_lines with
  business date of eligible_at <= D (view already remaining_qty > 0; qty in a DRAFT payroll counts as allocated, and
  that draft is caught by (i) when period_end <= D). Open items -> all dates <= D.
- ATTENDANCE cells in W: contractors.attendance_required (master flag, same as posting), pay_scheme DAILY/HYBRID,
  worker_is_employed_on(day), no record with coalesce(record_lifecycle,'POSTED')='POSTED' whose period (if any) is POSTED.
- DATED stock: FG chronological negativity is already prevented inside post_fg_movement (assert at AC:3705); keep the
  check as insurance mirroring assert_fg_chronological_nonnegative ordering (physical_at, system_created_at, id).
  Material insert trigger checks only the current total, so the dated material check is meaningful; mirror the cost
  engine's effective history (exclude reversed source+reversal pairs, AO:240-251).
- RECOST impact SQL: sub-agent sketch §4(b) (recalc_from, cutting/contractor consumption, fg_lots, PO journals by
  economic_date). journal_entries.economic_date has no index: acceptable for close/report frequency; note it.
