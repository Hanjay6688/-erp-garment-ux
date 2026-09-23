# STATIC code map: engine query facts (laundry, payroll, stock as-of, recost impact, attendance flag)

Read-only map written by a Claude sub-agent on 23 September 2026. STATIC: not executed, not native. Line numbers refer to repo migrations and the decompressed catalog snapshot supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz (called BOOT inside). Paths under /tmp in the text were the writer container scratchpad and are not part of the repo.


**Main findings:**
- **Laundry owner estimates.** Setting a rate on a posted delivery line fires an existing trigger. That trigger posts the accrual and rebuilds PO HPP immediately; nothing is queued. Setting a rate on a PENDING receipt line fires nothing, so the caller must run the full sync sequence. In both cases a FINISHED PO also needs `sync_finished_po_wip_residual`, and no trigger calls it.
- **Null rates count as 0** in both the accrual and HPP engines.
- **Payroll coverage** must be tested by `payroll_attendance_items` linkage, not by contractor + period range.
- **FG negative history** is prevented as of physical time, but only inside `post_fg_movement`. The material insert trigger checks only the current balance.
- **FG_INVENTORY lines** carry either `po_id` or `product_id`, never both. `journal_lines` has no `material_id`.
- **Every code path writes `entity_type='PO'`** to the recost queue.
- **The only dated "attendance required" source** is `contractor_hpp_policy_versions`. Payroll itself uses the undated `contractors.attendance_required`.

### Legend (all line numbers are 1-based)
- **BOOT** = `/tmp/claude-0/-home-user--erp-garment-ux/6ab391f1-e30c-52b5-862e-6737ef5df873/scratchpad/work/boot.sql`
  - It is the catalog snapshot at v2.6.17a, captured 2026-09-03 (see `/home/user/-erp-garment-ux/supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.manifest.json`; the CI workflow `/home/user/-erp-garment-ux/.github/workflows/cp6-full-schema-validation.yml` applies migrations from `20260903022604` on top of it).
  - So for any object not redefined by a migration dated `20260903022604` or later, the BOOT version is the current one.
- **Migration aliases.** All are under `/home/user/-erp-garment-ux/supabase/migrations/`:
  - Your aliases: AC, AO, AP, AS, AM, M12, CP6L.
  - AF = `20260916014332_erp_v2_6_20af_cp6_posted_child_integrity.sql`
  - AG = `20260916050822_erp_v2_6_20ag_cp6_sale_reservation_lineage.sql`
  - AH = `20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql`
  - AJ = `20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.sql`
  - AR = `20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql`
  - AV = `20260923110000_erp_v2_6_20av_cp6_identity_new_stock_cutoff.sql`
  - V11 = `20260829204632_erp_v2_6_11_operational_reservations_and_completion_scope.sql`
  - V14 = `20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql`
  - V14C = `20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql`
  - V15 = `20260901161322_erp_v2_6_15_payroll_component_entitlement.sql`
  - V17 = `20260902104937_erp_v2_6_17_access_pattern_wip_control.sql`
  - V20B = `20260905170334_erp_v2_6_20b_cp6_reaudit_reliability_closure.sql`
  - V20F = `20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql`
  - T = `20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.sql`
  - X = `20260913202948_erp_v2_6_20x_cp6_internal_role_fail_closed.sql`
  - AB = `20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.sql`
- **`latest.json` is stale.** It was built before AV was last modified, so AV's redefinitions (`post_rework_completion`, `create_manual_bs_case_v2`, `edit_product_identity_effective`, …) are missing from it. None of AV's redefinitions touch laundry, payroll, the queue, `post_fg_movement` or `rebuild_po_hpp`.
- **No post-AC function patches affect these answers.** I checked every `pg_get_functiondef` use in migrations from AC onward: they only build rollback/verification capsules and patch opening functions. The one laundry-relevant patch is CP6L:935-979, which adds failed-wash cost into `rebuild_po_hpp`; later full rewrites include it.

---

## 1. Laundry unknown price and owner estimate

### (a) Current logic

**`erp.desired_laundry_accrual(uuid)`**
- Latest is CP6L:809-855: `LANGUAGE sql STABLE SECURITY DEFINER`, owner postgres, execute revoked from everyone including service_role (CP6L:856-858). AC and later do not redefine it.
- For each delivery line of a PO where `ld.status not in('DRAFT','REVERSED')` (CP6L:838):
  - `costed_qty` = Σ(good + bs) over receipt lines of POSTED receipts with `actual_cost_status in('ESTIMATED','FINAL')` (CP6L:819-822).
  - `unbilled_actual_estimate` = Σ `actual_cost` over lines of POSTED receipts that are `ESTIMATED` (CP6L:823-825).
- Amount = Σ(`unbilled_actual_estimate` + `greatest(qty_sent_pcs - costed_qty, 0) * coalesce(estimated_rate_snapshot, 0)`) (CP6L:840-843).
- Plus ESTIMATED failed-wash costs on REVERSED deliveries (CP6L:845-852).
- **Null delivery rate = 0.** FINAL (invoiced) cost is excluded because it already sits in AP.
- **Laundry claims are not subtracted.** Qty that was claimed MISSING/STUCK stays inside "qty_sent − costed".

**`erp.sync_laundry_accrual(uuid, date)`**
- Latest is AC:10850-10909, `SECURITY DEFINER`, `search_path ''`, default date = today in Jakarta.
- Steps:
  1. `require_internal()`.
  2. Advisory lock `'PO_HPP:'||po` (AC:10865).
  3. Lock `laundry_cost_accrual_state` (AC:10866-10870).
  4. Compute `v_new = coalesce(desired_laundry_accrual(po), 0)` and delta = new − old (AC:10871-10872).
  5. If |delta| ≤ 0.005, only update the state row (AC:10873-10879).
  6. Otherwise insert `laundry_cost_accrual_events(po_id, old_amount, new_amount, delta_amount, effective_date)` (AC:10880-10883), then call `post_journal('LAUNDRY_ESTIMATE_ACCRUAL', event_id, p_effective_date, ...)`:
     - Increase: **Dr WIP / Cr ACCRUED_MANUFACTURING**, both lines carrying `po_id`, amount `round(abs(delta), 2)` (AC:10885-10892).
     - Decrease: Dr ACCRUED_MANUFACTURING / Cr WIP (AC:10893-10900).
  7. Link `journal_entry_id` on the event and upsert the state (AC:10902-10907).
- Table shapes: events BOOT:1028-1037, state BOOT:1041-1045. The state row holds one cumulative number per PO with no date.

**`erp.sync_laundry_accrual_after_rate_change()`**
- Latest is AC:10911-10916, `SECURITY DEFINER`, `search_path erp,public`. The BOOT:24649-24654 predecessor used server-local dates.
- Logic:
  - If `NEW.estimated_rate_snapshot IS NOT DISTINCT FROM OLD.estimated_rate_snapshot`, return with no effect.
  - Otherwise read the delivery's `po_id`, `status` and `(physical_at AT TIME ZONE 'Asia/Jakarta')::date`.
  - If status is not DRAFT/REVERSED:
    - call `sync_laundry_accrual(po, COALESCE(delivery_date, today))`;
    - if `EXISTS fg_lots WHERE po_id=po`, call `rebuild_po_hpp(po, 'Laundry estimate rate corrected')`, then `propagate_conversion_hpp_for_po(po)`, then `sync_po_hpp_to_gl(po, COALESCE(delivery_date, today))`.
- **Trigger binding:** BOOT:30489 `CREATE TRIGGER trg_sync_laundry_accrual_after_rate_change AFTER UPDATE OF estimated_rate_snapshot ON erp.laundry_delivery_lines FOR EACH ROW`. No migration drops or redefines it.
- It fires only when `estimated_rate_snapshot` is in the UPDATE's SET list.
- There is **no equivalent trigger on `laundry_receipt_lines`.**

**`erp.guard_child_by_parent_status()`**
- Latest is AG:150-208; AF:175 is the earlier version, and BOOT:9013 is the original.
- Not SECURITY DEFINER.
- If `current_user in ('postgres','service_role','supabase_admin')` it returns immediately (AG:161-163), so a postgres-owned SECURITY DEFINER caller bypasses it.
- Otherwise it locks both the old and new parent `FOR SHARE` and requires the parent status to be in the allowed list (AG:164-186). The sales_items extra check (AG:190-204) does not apply here.
- Bindings (BOOT):
  - 30487: `trg_parent_status_guard_laundry_delivery_lines BEFORE INSERT OR DELETE OR UPDATE ... ('laundry_deliveries','delivery_id','DRAFT')`
  - 30497: `trg_parent_status_guard_laundry_receipt_lines ... ('laundry_receipts','receipt_id','DRAFT')`
- Net effect: ordinary users can edit lines only while the parent is DRAFT.

**All triggers on the two line tables:**
- Delivery lines: audit (BOOT:30485), parent guard (30487), rate trigger (30489).
- Receipt lines: audit (30495), parent guard (30497), `trg_validate_laundry_receipt_line BEFORE INSERT OR UPDATE` (30499).
- No migration adds triggers on either line table.

### (b) Columns

**`laundry_deliveries`** (BOOT:1049-1063, plus `row_version bigint` from CP6L:487-489)
- Columns: id, delivery_number, po_id, vendor_id, target_dyeing_color, target_wash_process_id, special_instruction, **physical_at timestamptz not null**, status, portal_visible, created_by, created_at, updated_at.
- Status CHECK: DRAFT, SENT, PARTIAL_RETURN, RETURNED, CLOSED, REVERSED (BOOT:3327).

**`laundry_delivery_lines`** (BOOT:1067-1075)
- Columns: id, delivery_id, cutting_group_id, qty_sent_pcs (>0, BOOT:3331), **estimated_rate_snapshot numeric(18,2) null**, **estimated_cost_status varchar default 'PENDING'** (PENDING / ESTIMATED / FINAL, BOOT:3329), notes.
- Unique (delivery_id, cutting_group_id) (BOOT:2911).
- **No date column** — use the delivery's `physical_at`.

**`laundry_receipts`** (BOOT:1108-1118)
- Columns: id, receipt_number, delivery_id, **physical_at timestamptz not null**, status (DRAFT / POSTED / REVERSED, BOOT:3347), created_by, created_at, updated_at, row_version.

**`laundry_receipt_lines`** (BOOT:1091-1104)
- Columns: id, receipt_id, delivery_line_id, actual_wash_process_id, qty_good_received, qty_bs_laundry, qty_stuck, qty_missing (all ≥ 0), **actual_rate_snapshot numeric(18,2)**, **actual_cost_status** default PENDING (PENDING / ESTIMATED / FINAL, BOOT:3335), **actual_cost numeric(20,2)**, notes. No date column.
- Validator invariant (CP6L:1363-1470, latest): outside the failed-wash and FINAL-with-cost branches,
  - rate null ⇒ `actual_cost := null` and status forced to PENDING (1458-1463);
  - rate set ⇒ `actual_cost := (good + bs) * rate`, and PENDING flips to ESTIMATED (1464-1467).
  - So in practice **PENDING ⇔ null actual rate and null cost.**

**How rates are set:**
- Legacy `post_laundry_delivery`: fills the delivery rate from `laundry_vendor_rate_versions` only when the line's rate is null and `target_wash_process_id` is set. It sets `estimated_cost_status='ESTIMATED'` only when a rate is found (AC:4103-4110). Otherwise the line stays null/PENDING.
  - A line whose rate was typed on the draft keeps status PENDING with a non-null rate. That UI path is **UNCERTAIN**.
- CP6 facade `save_laundry_qc_action_v1` requires exactly one effective rate (AC:8935-8941) and inserts lines with rate + 'ESTIMATED' (AC:9063-9068). Receipts behave the same (AC:9154-9160, 9233).
- So unknown prices come only from legacy paths.
- **Neither accrual nor HPP ever reads `estimated_cost_status`.** The only other reference in migrations is a column list at CP6L:3371. Only `estimated_rate_snapshot` matters.

### (c) How HPP reads laundry cost (`rebuild_po_hpp`)

Latest definition: AP:5329-~5700.

- **PO-level total** (AP:5418-5432):
  - Delivery lines of non-REVERSED deliveries. Note the filter is `ld.status<>'REVERSED'`, so DRAFT is included here, unlike the accrual.
  - `qty_costed_actual` = good + bs of POSTED receipts with ESTIMATED/FINAL.
  - `actual_cost` = Σ `coalesce(lrl.actual_cost, 0)` for the same lines.
  - Total = Σ(`actual_cost + greatest(qty_sent - qty_costed_actual, 0) * coalesce(estimated_rate_snapshot, 0)`).
  - **PENDING receipt qty is not "costed"**, so it falls back to the delivery rate, and a **null delivery rate gives 0**.
  - Failed-wash additions: AP:5434-5449.
- **Pending flag** `v_pending` (AP:5431, patched by V20B:484-491):
  - `has_pending_receipt` (POSTED receipt with PENDING or ESTIMATED), or `qty_sent > qty_costed`.
  - This sets `cost_state='ESTIMATED'` (AP:5491). It does **not** single out null-rate lines.
- **Cutting-group level:** AP:5535-5557, same formula.
- **CP6 lineage per lot** (AP:5580-5601):
  - If the receipt line is ESTIMATED/FINAL with cost: use `actual_cost / (good + bs)`.
  - Otherwise use `coalesce(rl.actual_rate_snapshot, dl.estimated_rate_snapshot, 0)` × lot qty — PENDING with no delivery rate gives **0**.
  - Failed-wash lot cost: `cp6_lot_failed_wash_cost_v2620e` (AJ:592).
- **Allocation and component:** allocation at AP:5610-5615; the component row reads "PENDING uses estimate" (AP:5644-5649).
- **Behaviour notes:**
  - It returns early if the PO has no PRODUCTION lots (AP:5473-5475).
  - Every call inserts a new `hpp_versions` row per lot (AP:5632-5637).
  - Lock order: `pocket_period_lock_v1()` (a *try*-lock that raises `POCKET_PERIOD_BUSY`, AP:555-560), then `FG_HPP_SALES_V2620C`, then `PO_HPP:po` (AP:5390-5394).
  - `sync_laundry_accrual` takes `PO_HPP` first. The existing post paths use the same order.

### (d) What an owner estimate would trigger

Assume a postgres-owned SECURITY DEFINER function. Inside it `current_user = postgres`, so every `current_user`-based guard is bypassed. `require_internal` (CP6L:1475-1532, patched X:248-259) checks `session_user`, the JWT role or `current_app_role()`, so the invoking user must be OWNER, ADMIN or STAFF.

**Case 1 — delivery line on a posted delivery with a null rate**

Statement: `UPDATE laundry_delivery_lines SET estimated_rate_snapshot = r, estimated_cost_status = 'ESTIMATED'`

- **BEFORE:** the parent guard is bypassed.
- **AFTER:** the audit row (which uses `app.change_reason`), then the rate trigger. The rate changed and the delivery is not DRAFT/REVERSED, so:
  1. `sync_laundry_accrual(po, delivery date)` posts **`LAUNDRY_ESTIMATE_ACCRUAL` Dr WIP(po_id) / Cr ACCRUED_MANUFACTURING(po_id)** for the whole-PO delta.
     - The economic date passed to `post_journal` is the delivery's Jakarta date.
     - `post_journal` stores `economic_date` = that date and `transaction_date = resolve_accounting_transaction_date(date)` (AC:4056-4059).
     - If the date is ≤ `closed_through`, the GL date becomes `greatest(business today, closed_through + 1)` and a period-shift audit row is written (BOOT:17066-17080; patched T:335-341 and AB:255-268; audit at AC:4071-4074).
  2. If the PO has `fg_lots`, `rebuild_po_hpp`, `propagate_conversion_hpp_for_po` and `sync_po_hpp_to_gl` run **synchronously**. They are **not queued** (the queue is used only by material recost, see §4).
     - `sync_po_hpp_to_gl` (latest AS:373-467) posts `PO_HPP_GL_SYNC`: FG_INVENTORY, COGS and OTHER_EXPENSE/OTHER_INCOME against WIP, every line `po_id` only (AS:435-449, 451-458).
     - Its date is the delivery date, unless `invoice_recost_economic_date_v1()` returns an invoice context for the current transaction (AS:391; AO:127-137).
- **Multi-row UPDATE:** row-level AFTER triggers run at end of statement and see every row. The first call books the full delta; later calls find delta 0 but still re-run `rebuild_po_hpp`, creating extra `hpp_versions`.
- **Gap:** the trigger does **not** call `sync_finished_po_wip_residual` (AC:10806-10848). For a FINISHED PO, the added WIP less the amount pushed to FG/COGS stays as WIP residual. Other paths do call it: AO:473-475, `process_cost_recalc_queue` AC:5866-5867, pocket sync AP:735-737.

**Case 2 — receipt line on a POSTED receipt with status PENDING**

Statement: `UPDATE laundry_receipt_lines SET actual_rate_snapshot = r` (optionally also `actual_wash_process_id`)

- **BEFORE:**
  - Parent guard bypassed.
  - `validate_laundry_receipt_line` re-checks capacity (CP6L:1387-1398), computes `actual_cost = (good + bs) * r`, and flips PENDING → ESTIMATED.
  - Setting `actual_cost_status='ESTIMATED'` without a rate is reverted to PENDING (CP6L:1458-1463).
- **AFTER:** audit only. **No accrual, HPP or GL is triggered.** Accrual state and HPP stay stale until someone calls the syncs.
- For reference, `post_vendor_invoice` edits receipt lines the same way and then calls the syncs explicitly (AC:5752-5756, 5772-5786). The vendor-invoice reversal also restores prior snapshots explicitly (AC:7640-7710).

**Minimal correct sequence** (mirrors `post_laundry_receipt` AC:4219-4224, `post_vendor_invoice` AC:5780-5785, and the pocket sync AP:733-737):
```sql
perform set_config('app.change_reason', :reason, true);
-- delivery line (trigger does steps A+B automatically):
update erp.laundry_delivery_lines set estimated_rate_snapshot=:rate, estimated_cost_status='ESTIMATED'
 where id=:line and estimated_rate_snapshot is null;
-- receipt line (no trigger; do A+B yourself):
update erp.laundry_receipt_lines set actual_rate_snapshot=:rate where id=:rline and actual_cost_status='PENDING';
-- per distinct PO, ordered by po_id:
perform erp.sync_laundry_accrual(:po, :econ_date);                          -- A (receipt case)
if exists(select 1 from erp.fg_lots where po_id=:po) then                   -- B (receipt case)
  perform erp.rebuild_po_hpp(:po, :reason);
  perform erp.propagate_conversion_hpp_for_po(:po);
  perform erp.sync_po_hpp_to_gl(:po, :econ_date);
end if;
if (select status from erp.production_orders where id=:po)='FINISHED' then  -- C (both cases; not in trigger)
  perform erp.sync_finished_po_wip_residual(:po, :econ_date, :reason);
end if;
```
- **Choice of `:econ_date` is a design decision (UNCERTAIN).** Existing code uses the receipt date for receipts (AC:4219) and the delivery date inside the trigger.
- Optional: a `cost_adjustments` row with `component_type='LAUNDRY'` (pattern at AC:5758-5759) gives traceability, but it moves `hpp cost_state` to 'ADJUSTED' when nothing is pending (AP:5491).

### (e) SQL: unknown-price laundry facts dated on or before D

A sargable form of the date test is `physical_at < ((:d + 1)::timestamp AT TIME ZONE 'Asia/Jakarta')`.

```sql
-- delivery lines (canonical unknown = rate IS NULL; PENDING-with-rate is informational only)
select ld.po_id, ld.id delivery_id, ld.delivery_number, ld.status, ld.physical_at,
       erp._cp3_business_date(ld.physical_at) business_date,
       ldl.id delivery_line_id, ldl.cutting_group_id, ldl.qty_sent_pcs,
       ldl.estimated_rate_snapshot, ldl.estimated_cost_status,
       coalesce(rc.costed_qty,0) costed_qty,
       greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0) uncosted_qty   -- mirrors CP6L:842 / AP:5430
from erp.laundry_delivery_lines ldl
join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
  from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lrl.delivery_line_id=ldl.id and lr.status='POSTED'
    and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
where ld.status not in('DRAFT','REVERSED')
  and (ldl.estimated_rate_snapshot is null or ldl.estimated_cost_status='PENDING')
  and erp._cp3_business_date(ld.physical_at) <= :d;
  -- optional: and greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0)>0

-- PENDING receipt lines of POSTED receipts
select ld.po_id, lr.id receipt_id, lr.receipt_number, lr.physical_at,
       erp._cp3_business_date(lr.physical_at) business_date,
       lrl.id receipt_line_id, lrl.delivery_line_id, lrl.qty_good_received, lrl.qty_bs_laundry,
       lrl.actual_wash_process_id, lrl.actual_rate_snapshot, lrl.actual_cost,
       ldl.estimated_rate_snapshot fallback_delivery_rate   -- HPP/accrual fall back to this (AP:5430, AP:5584)
from erp.laundry_receipt_lines lrl
join erp.laundry_receipts lr on lr.id=lrl.receipt_id
join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
where lr.status='POSTED' and lrl.actual_cost_status='PENDING'
  and erp._cp3_business_date(lr.physical_at) <= :d;
  -- optional: and lrl.qty_good_received+lrl.qty_bs_laundry>0  (stuck/missing-only lines carry no cost)
```

---

## 2. Payroll completeness

### (a) Tables and views

**`payroll_settlements`** (BOOT:1739-1760)
- Columns: id, payroll_number (unique, BOOT:2965), contractor_id, period_start, period_end (CHECK end ≥ start, BOOT:3543), status, labor_total, attendance_total, reimburse_total, deduction_total, manual_adjustment, net_payable (generated), settled_at, notes, created_at, updated_at, payment_cash_account_id, payment_date (default today in Jakarta, AC:11768), row_version.
- Indexes: (contractor_id, period_start, period_end) and (contractor_id, period_end, status) (BOOT:4917-4919).

**`payroll_attendance_items`** (BOOT:1699-1711; the snapshot columns were added in M12:1596-1600)
- Columns: id, payroll_id, worker_id, **attendance_record_id**, paid_fraction_snapshot, daily_rate_snapshot, amount (generated), worker_rate_version_id, attendance_date_snapshot, worker_name_snapshot, job_description_snapshot.
- Unique (payroll_id, attendance_record_id) (BOOT:2963); index on attendance_record_id (BOOT:4909).
- Trigger `validate_payroll_attendance_unique` allows only one non-REVERSED payroll per record (BOOT:25677-25690; trigger BOOT:30705).

**`payroll_work_items`** (BOOT:1763-1773)
- Columns: id, payroll_id, po_id, work_component_id, source_type (PRODUCTION / REWORK, BOOT:3553), **source_id** (work_completion_lines.id or rework_component_lines.id), qty_payable > 0, rate_snapshot, amount (generated).
- Unique (payroll_id, source_type, source_id, work_component_id) (BOOT:2967).

**Other payroll children:**
- `payroll_deductions` (BOOT:1715-1725, plus `opening_cash_advance_balance_id` from AP:187) and `payroll_reimbursements` (BOOT:1727-1737).
- All four child tables are guarded by `guard_child_by_parent_status('payroll_settlements','payroll_id','DRAFT,CALCULATED,REVIEW')` (BOOT:30703, 30709, 30715, 30733).

**`v_payroll_eligible_work_lines`** (BOOT:29289-29333, security_invoker; not redefined in migrations)
- Columns: source_type, source_id, contractor_id, po_id, cutting_group_id, bs_case_id, work_component_id, **eligible_at**, source_qty, eligible_qty, allocated_qty, **remaining_qty**, held_qty, rate_snapshot, remaining_amount, eligibility_reason.
- PRODUCTION rows come from `v_payroll_production_work_eligibility` (BOOT:28451-28515 = V15:36-122):
  - `eligible_at` = `work_completion_events.physical_at` (POSTED events only).
  - `remaining_qty = greatest(qty_payable - Σqty in payroll_work_items of payrolls with status <> 'REVERSED', 0)`.
  - Laundry no longer gates eligibility (`held_qty` is always 0; comments at V15:124+).
- REWORK rows:
  - `eligible_at = coalesce(ro.completed_at, ro.physical_sent_at)`.
  - Only when destination is CONTRACTOR, `ro.status='COMPLETED'`, `cost_posted`, and `bs.status='RESOLVED'`.
- The view already filters `remaining_qty > 0` for both sources.
- Consequence: qty that sits in a DRAFT/CALCULATED/REVIEW payroll counts as allocated.

### (b) Status lifecycle

- CHECK values: DRAFT, CALCULATED, REVIEW, APPROVED, PAID, REVERSED (BOOT:3547). **There is no CANCELLED; cancellation means REVERSED.**
- Transitions:

| Step | From → to | Function | What else happens |
|---|---|---|---|
| Create | → DRAFT | direct insert | Insert must be a zero-value DRAFT (BOOT:9379-9414, trigger BOOT:30723) |
| Calculate | → CALCULATED | `recalculate_payroll` (BOOT:16187-16192) | `attendance_total` counts only when the current `contractors.attendance_required` is true |
| Review | CALCULATED → REVIEW | direct update | The only direct transition allowed; APPROVED, PAID and REVERSED rows are frozen (`guard_payroll_lifecycle` BOOT:10297-10320) |
| Approve | CALCULATED/REVIEW → APPROVED | `approve_payroll` (AP:4565-4654) | Posts PAYROLL_ATTENDANCE_ACCRUAL (Dr WIP no po_id / Cr CONTRACTOR_PAYABLE), EXTRA_ACCRUAL and MANUAL_REDUCTION, **all at `p.period_end`** (AP:4613-4644) |
| Pay | APPROVED → PAID | `post_payroll_payment` (AP:4672-4768) | Journals at `payment_date` |
| Cancel | DRAFT/CALCULATED/REVIEW/APPROVED → REVERSED | `cancel_unpaid_payroll` (AC:2264-2318) | Reverses accrual journals |
| Reverse paid | PAID → REVERSED | `reverse_paid_payroll` (AP:4769-4837) | |

- **"Not approved"** = DRAFT, CALCULATED, REVIEW.
- **Complete for cost** = APPROVED or PAID.
- **Terminal** = REVERSED. PAID is final unless reversed.
- REVERSED payrolls are ignored by the overlap guard (BOOT:10325-10340), by attendance uniqueness, and by eligibility allocations.

### (c) SQL sketches

```sql
-- (i) unfinished payrolls due by D
select id,payroll_number,contractor_id,period_start,period_end,status
from erp.payroll_settlements
where status in('DRAFT','CALCULATED','REVIEW') and period_end<=:d;
-- also consider payrolls with period_start<=:d<period_end: approve_payroll books attendance at period_end (AP:4615),
-- so attendance days <=D in an approved straddling payroll are accrued AFTER D (cutoff issue).
```

For (ii), use **linkage** through `payroll_attendance_items.attendance_record_id` on a non-REVERSED payroll. This is correct because `populate_payroll_draft` (AC:3056-3160) snapshots specific record ids and does so only when `contractors.attendance_required` (AC:3096-3126). The contractor + period-range test would wrongly count as covered a record that was posted, or corrected with a new record id, after the payroll was populated.

Use range coverage only as a diagnostic: a range-covered but unlinked record means a payroll that needs re-population or cancellation.

The filter mirrors the populate filter (AC:3116-3125). Use `paid_fraction > 0`, not a status list: `normalize_attendance_paid_fraction` (BOOT:11960-11964) zeroes only ABSENT/OFF and caps HALF_DAY at 0.5; SICK and LEAVE keep their fraction.

```sql
-- (ii)
select ar.id,ar.contractor_id,ar.worker_id,ar.attendance_date,ar.status,ar.paid_fraction,
  exists(select 1 from erp.payroll_settlements ps where ps.contractor_id=ar.contractor_id
         and ps.status<>'REVERSED' and ar.attendance_date between ps.period_start and ps.period_end) range_covered_but_unlinked
from erp.attendance_records ar
join erp.contractor_workers cw on cw.id=ar.worker_id
join erp.contractors c on c.id=ar.contractor_id
left join erp.attendance_periods ap on ap.id=ar.attendance_period_id
where ar.attendance_date> :from and ar.attendance_date<=:d
  and coalesce(ar.record_lifecycle,'POSTED')='POSTED'
  and (ar.attendance_period_id is null or ap.status='POSTED')
  and cw.pay_scheme in('DAILY','HYBRID')          -- current value, not dated (UNCERTAIN historically)
  and ar.paid_fraction>0
  and c.attendance_required                         -- what payroll uses; dated alternative in §5
  and not exists(select 1 from erp.payroll_attendance_items pai
     join erp.payroll_settlements ps on ps.id=pai.payroll_id
     where pai.attendance_record_id=ar.id and ps.status<>'REVERSED');

-- (iii)
select e.* from erp.v_payroll_eligible_work_lines e
where erp._cp3_business_date(e.eligible_at)<=:d and e.remaining_qty>0;   -- allocated_qty=0 => wholly uncovered
```
- `merge_eligible_work_into_payroll_v2` and populate both admit a line only when `(eligible_at AT TIME ZONE 'Asia/Jakarta')::date <= period_end` (AC:3025-3027, 3092).

### (d) Can a record already used by a payroll be changed?

Direct changes by ordinary users: no.
- `trg_guard_attendance_after_payroll_use BEFORE DELETE OR UPDATE` on `attendance_records` (BOOT:30263; function BOOT:8799-8819) raises if any non-REVERSED payroll links the record.
- It is **bypassed when `current_user` is postgres, service_role or supabase_admin.**

Posted periods are also immutable:
- `guard_attendance_record_period_and_dates` (M12:840-901) and `guard_attendance_period_lifecycle` (M12:753-775), unless `app.attendance_period_lifecycle='on'`.

The SECURITY DEFINER workflows re-check payroll use themselves:
- `reverse_attendance_period_v1`: "requires its consuming payroll to be reversed first" (BOOT:17439-17447).
- Correction posting in `post_attendance_period_v1` (BOOT:12510-12521).
- Correction draft save (BOOT:21230).

So the payroll must be reversed first. A future SECURITY DEFINER function that edits records directly would bypass the trigger.

---

## 3. Stock quantity as of a date

### (a) Movement tables

**`fg_stock_movements`** (BOOT:907-925)
- Columns: id, product_id (not null), lot_id (nullable), location_id (not null), quality_grade (default GRADE_A), movement_type (CHECK list at V11:302-306 / BOOT:3287), **qty_signed integer** (≠ 0; positive = in, negative = out, BOOT:3289), unit_hpp_snapshot, customer_id, source_type, source_id, **physical_at timestamptz**, system_created_at, created_by, reversal_of_id, notes, book_order.
- Key: (product, location, grade) and (lot, location, grade); chronological indexes at BOOT:4771-4775.

**`material_stock_movements`** (BOOT:1359-1377)
- Columns: id, material_id (not null), roll_id (nullable), location_id (nullable; OUT rows require it, AM:393), movement_type (list at BOOT:3429), **qty_signed numeric(18,6)** (≠ 0, same sign rule), input_unit_cost, unit_cost_snapshot, original_unit_cost_snapshot, source_type, source_id, **physical_at**, system_created_at, created_by, reversal_of_id, is_cost_recalculated, note.
- Key: (material, location, roll).

**Traps when computing an as-of balance:**
- `SALE_RESERVE` rows (draft-sale reservations) are negative FG rows dated at `sale_date`; their release reversal uses the original `physical_at` (BOOT:5881-5885, 5788-5792). The HPP target engine adds them back as still owned (`compute_po_hpp_gl_targets_v2620d`, V20F:213 ff.).
- `reverse_fg_movement` dates the reversal at `clock_timestamp()` (BOOT:18005-18026).
- A material reversal may be dated at or after its source (`guard_material_reversal_chronology` BOOT:10009-10028). The cost engine excludes both the source and its reversal (AO:244-247), whereas a raw sum by `physical_at` does not.

### (b) Negative-stock guards

**FG:** yes, as of physical time, but only inside `post_fg_movement` (AC:3643-3723). There is no table trigger.
- First it checks the current cached balance and the lot's cached qty (AC:3670-3679, 3681-3694).
- After insert, it calls `assert_fg_chronological_nonnegative` (AC:3705-3707; body BOOT:6702-6738). That function takes the running sum ordered by `(physical_at, system_created_at, id)` for (product, location, grade), and for (lot, location, grade), and raises if the minimum is negative.
- It is skipped when `p_allow_negative`. I found no caller passing true.
- Direct DML is blocked for non-system roles by `guard_system_managed_table` (BOOT:11106; trigger BOOT:30447). The future-date guard is at BOOT:30445.
- No migration updates `fg_stock_movements.physical_at`. The only updates touch `unit_hpp_snapshot` and SALE_RESERVE→SALE.

**Material:** the insert trigger checks the **current total only**.
- `trg_guard_material_negative_stock BEFORE INSERT` (BOOT:30593; latest body AM:378-416) sums all `qty_signed` for (material, roll or no-roll, location) with no time filter.
- Bypass: MATERIAL_PURCHASE_REVERSAL when `erp.allow_source_replacement_negative='on'` (AM:399-402).
- History checks happen only when `_recalculate_material_cost_core` runs (called via `recalculate_material_cost` by most posting paths, e.g. AC:3336):
  - Effective history per location/roll, excluding reversed pairs: `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY` (AO:240-251).
  - Material-level chronological check (AO:366-368).
- **UNCERTAIN:** whether every material insert path calls recalc.

### (c) GL line dimensions

Confirmed: `journal_lines` has customer_id, vendor_id, contractor_id, po_id and product_id, and **no material_id** (BOOT:993-1005; no migration adds one).

**FG_INVENTORY lines carry either `po_id` or `product_id`, never both:**

| Path | FG_INVENTORY dimension | Citation |
|---|---|---|
| `post_qc` and the laundry Final-SKU path | No journal of their own; value reaches GL through `sync_po_hpp_to_gl` → `po_id` only | `post_qc` AC:4927-4990 (post_fg_movement then rebuild + sync at 4970-4987). Final SKU: AC:9694-9776 → V17:1623-1657 → `post_fg_partial_completion_v2` → AC:3911 `post_qc` |
| `sync_po_hpp_to_gl` | `po_id` only | AS:435-449 |
| `post_sale` | non-PO lots: `product_id`; PO lots: `po_id` | AG:414-421; AG:475-481 |
| `post_sales_return` | same split | AH:338-340; AH:396-398 |
| `post_fg_adjustment` | non-native lots: `product_id`; native PO lots go through `sync_po_hpp_to_gl` | AC:3593-3607; AC:3615-3620 |
| `post_product_conversion` | `product_id` on both legs (to/from), no `po_id` | AC:4896-4906 |
| Non-PO product HPP sync | `product_id` | V20F:744-746 |
| `sync_opening_lot_hpp_to_gl` | `product_id` | AP:5953 |
| `post_opening_balance` | `product_id` | AR:425 |
| Journal reversals | copy every dimension | BOOT:5350-5355 |

**WIP lines — `po_id` yes:**
- cutting issue AC:3454; cutting returns AC:3505; contractor non-accessory issue AC:3354 (PO mandatory, AC:3318-3326)
- work completion AC:5804; laundry accrual AC:10889/10898; vendor invoice AC:5761
- HPP sync AS:447-449; finished residual AC:10838-10843
- accessory reimbursement AC:3248; attendance-pool debit V14C:1572-1579; pocket period AP:722-728
- opening balance AR:426/439; `recost_initial_import_origins` AP:6459
- material revaluation counterpart AS:334-340
- rework completion (AV ~743-755, `b.po_id`; `po_id` is null for manual BS — **UNCERTAIN** whether such rework can post cost)

**WIP lines — no `po_id`:**
- `PAYROLL_ATTENDANCE_ACCRUAL` (AP:4618, "unassigned WIP")
- `ATTENDANCE_HPP_POOL` credit lines (V14C:1600-1606)
- `post_opening_financial_correction` (AC:4565/4571)

**MATERIAL_INVENTORY lines:**
- With `po_id`: cutting (AC:3455, 3504), contractor issue (AC:3350/3355), revaluation (AS:334/340).
- No dimensions at all: purchases (BOOT:13772), material adjustments (BOOT:13690), opening balance (AR:409), initial-import recost (AP:6455/6460), and account-keyed adjustment revaluation (T:183-219; AO:166-171).

---

## 4. Recost queue impact

### (a) Columns and entity_type

**`cost_recalc_queue`** (BOOT:585-599)
- Columns: id bigint, entity_type, entity_id uuid, **recalc_from timestamptz (nullable)**, reason, status (PENDING / RUNNING / DONE / FAILED, BOOT:3205), queued_at, started_at, completed_at, error_message, attempt_count, last_attempt_at, next_attempt_at.
- CHECK on entity_type allows MATERIAL, PO, LOT, SALE (BOOT:3203). The table is system-managed (BOOT:30365).

**Every code path writes 'PO':**
- The only inserts are the two literal `'PO'` inserts in `_recalculate_material_cost_core`. Latest: AO:434-441 (cutting groups) and AO:443-451 (contractor issues). Predecessors: BOOT:5731/5740, AC:1743/1752, AM:669/678. There are none in AP–AV.
- `recalc_from = min(msm.physical_at)` of that material's movements for the PO.
- A row is skipped if an open row exists (PENDING, RUNNING, or FAILED with `attempt_count < 3`).
- `process_cost_recalc_queue` raises for any non-PO type (AC:5862-5870) and retries FAILED rows only while `attempt_count < 3` (AC:5856).
- AO also marks PENDING/FAILED rows DONE inline when an invoice-date context exists (AO:458-479).
- Legacy non-PO rows are possible only as historical data (**UNCERTAIN**, data-dependent).
- Existing monitors: `get_owner_financial_snapshot_v2` open count (AC:2841-2842); `run_integrity_checks` STALE/FAILED (AC:7860-7864).

### (b) SQL sketch

```sql
select q.id,q.entity_id po_id,q.status,q.attempt_count,q.recalc_from,q.queued_at,q.error_message,r.reasons
from erp.cost_recalc_queue q
cross join lateral (select array_remove(array[
  case when q.recalc_from is not null and erp._cp3_business_date(q.recalc_from)<=:d then 'RECALC_FROM' end,
  case when exists(select 1 from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
       where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id
         and erp._cp3_business_date(m.physical_at)<=:d) then 'CUTTING_MATERIAL' end,
  case when exists(select 1 from erp.material_stock_movements m
       join erp.contractor_material_issue_items ii on ii.id=m.source_id
       join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
       where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id
         and erp._cp3_business_date(m.physical_at)<=:d) then 'CONTRACTOR_MATERIAL' end,
  case when exists(select 1 from erp.fg_lots fl where fl.po_id=q.entity_id
         and erp._cp3_business_date(fl.produced_at)<=:d) then 'FG_LOT' end,
  case when exists(select 1 from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
       where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED') and je.economic_date<=:d) then 'PO_JOURNAL' end
 ],null) reasons) r
where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED')
  and cardinality(r.reasons)>0;
```

Exact source columns:
- `material_stock_movements(source_type, source_id, physical_at)`: BOOT:1359. Links go through `cutting_groups.po_id` (BOOT:715) or `contractor_material_issue_items.issue_id` → `contractor_material_issues.po_id` (BOOT:487).
- `fg_lots(po_id, produced_at)`: BOOT:889.
- `journal_entries.economic_date` (BOOT:975-989). REVERSED originals stay dated facts, and their reversals are separate POSTED rows (BOOT:5355).
- There is no index on `economic_date`; the existing index is `(transaction_date, status)`, BOOT:4787. `journal_lines(po_id)` is indexed (BOOT:4805).

Optional extra PO facts:
- `pocket_period_destinations.po_id` (AP:296-301), which feeds `rebuild_po_hpp` (AP:5391).
- Laundry delivery/receipt and `work_completion_events.physical_at`.

---

## 5. Attendance-required flag

**Dated source:** `contractor_hpp_policy_versions` (V14:123-144 = BOOT:451-463)
- Columns: id, contractor_id, effective_from date, effective_to date (inclusive), contractor_role_snapshot (must be 'MANDOR', V14:136-137), **attendance_required_snapshot boolean**, is_special, reason, row_version, created_by, created_at.
- Unique (contractor_id, effective_from); lookup index (contractor_id, effective_from desc, effective_to).
- There is no overlap trigger. Written only by `set_contractor_hpp_policy_v1`, which:
  - closes the prior open version at `new_from - 1` and caps the new one at `next_from - 1` (V14C:255-276);
  - requires the payload flag to equal the current contractor master flag (V14C:233-235).

**Version effective on date d** (same predicate as V14C:239-246):
```sql
select p.* from erp.contractor_hpp_policy_versions p
where p.contractor_id=:c and p.effective_from<=:d and (p.effective_to is null or p.effective_to>=:d)
order by p.effective_from desc, p.id desc limit 1;
```
- The HPP manifest uses a stricter full-period cover: `effective_from <= period_start and (effective_to is null or effective_to >= period_end)` (V14C:876-884; BOOT:28688-28699).

**Payroll and attendance posting ignore the dated flag.** They use the undated `contractors.attendance_required` (BOOT:552-562; default true):
- `populate_payroll_draft` AC:3096-3099
- `recalculate_payroll` BOOT:16192
- `post_attendance_period_v1` BOOT:~12450-12456
- `guard_opening_cash_advance_deduction_v1` AP:4884

**UNCERTAIN / drift risk:** master-data import upserts can change the master flag with no new policy version (AP:2149). Policy rows exist only for MANDOR contractors, so there is no fallback other than the current master flag.

**`worker_is_employed_on(worker, date)`** (M12:438-455; current BOOT:27588-27600, `LANGUAGE sql STABLE`):
```sql
select exists(select 1 from erp.worker_employment_periods e
  where e.worker_id = p_worker_id
    and p_effective_date >= e.started_on
    and (e.ended_on is null or p_effective_date <= e.ended_on))
```
- `worker_employment_periods` table: BOOT:2496-2507; unique (worker_id, started_on); guarded by a trigger (BOOT:30987).
- Enforced on every attendance insert or update (M12:869-871) and used for the posting cell completeness check (BOOT:~12460-12475).
- Related dated rate lookup: `worker_daily_rate_at` (BOOT:27554-27567) over `worker_daily_rate_versions` (BOOT:2483-2492).
- `contractor_workers.pay_scheme` is not dated (BOOT:531-548, 3195).
- Business date helper: `_cp3_business_date(ts)` = `(ts at time zone 'Asia/Jakarta')::date`, immutable (V14C:56-64).