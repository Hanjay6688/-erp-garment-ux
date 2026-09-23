# STATIC code map: accounting close preflight design inputs (S06/B04)

Read-only map written by a Claude sub-agent on 23 September 2026 from repo migrations and the catalog snapshot. STATIC: not executed, not native. Kept as the source of the file:line facts used by docs/cp6-aw-design.md.


Nothing in the repo was modified.

**File aliases used below** (all under `supabase/migrations/` unless noted):
- **AC** = `20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql`
- **AO** = `20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql`
- **AP** = `20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql`
- **AS** = `20260922210815_erp_v2_6_20as_cp6_event_dates_product_identity.sql`
- **AM** = `20260921214120_erp_v2_6_20am_cp6_transfer_integrity.sql`
- **AG** = `20260916050822_erp_v2_6_20ag_cp6_sale_reservation_lineage.sql`
- **M** = `20260911092622_erp_v2_6_20m_cp6_subledger_exact_cent_closure.sql`
- **M12** = `20260830140645_erp_v2_6_12_attendance_and_stock_explainability.sql`
- **M14** = `20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql`
- **M14c** = `20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql`
- **CP6L** = `20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql`
- **T/AB/Z** = the `20t` / `20ab` / `20z` migrations
- **BOOT** = `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`

**About BOOT.** It is a read-only catalog dump of the base schema, captured 2026-09-03 at CP4.5a. Line numbers are in the decompressed file. It is the only source in the repo for base-schema tables and functions. Later ALTERs are covered only where I cite them.

**Two index caveats:**
- **Functions patched after their last CREATE.** Several functions are patched with `pg_get_functiondef` + `replace` after their last CREATE, so `latest.json` does not show their current body. The ones that matter here:
  - `_v268_financial_report_checks_pre_scope`: last CREATE is M:168, then patched by P/Q/R/S/T/U/V/W/Y.
  - `resolve_accounting_transaction_date`: base body BOOT:17066, patched at T:335-342 and AB:260.
- **Base-only function.** `resolve_accounting_transaction_date` is not in the index.

---

### 1. Recost impact dates

**The queue table**
- Definition: `cost_recalc_queue` is at BOOT:585-598. Columns are `entity_type`, `entity_id`, `recalc_from timestamptz`, `reason`, `status`, `queued_at`, `started_at`, `completed_at`, `error_message`, `attempt_count`, `last_attempt_at`, `next_attempt_at`.
- Constraints: `entity_type` must be MATERIAL/PO/LOT/SALE (BOOT:3203). `status` must be PENDING/RUNNING/DONE/FAILED (BOOT:3205).
- The trigger `guard_system_managed_table` protects the table (BOOT:30365). Authenticated users can only SELECT it (BOOT:33613).

**Only one function inserts queue rows: `_recalculate_material_cost_core`** (AO:181; base and repo scan).
- AO:434-441: `insert … select distinct 'PO',cg.po_id,min(msm.physical_at),'Material moving-average/backdate recalculation'`. Joins cutting-group movements (`CUTTING_GROUP`, `CUTTING_GROUP_RETURN`) to `cutting_groups.po_id`.
- AO:443-451: the same for `CONTRACTOR_MATERIAL_ISSUE_ITEM` via `contractor_material_issues.po_id`.
- `entity_type` is always `'PO'` and `entity_id` is the PO id. Rows are inserted only when the PO already has `fg_lots` (AO:439, 449). The processor raises on any other entity type (AC:5869).
- **What `recalc_from` means:** the earliest `physical_at` of any cutting or contractor-issue movement of *this material* for *this PO*.
  - It is not the date of the movement that changed, and it is not `p_recalc_from`.
  - The query has no filter on reversals.
- **Deduplication:** no row is inserted if the PO already has a row that is PENDING or RUNNING, or FAILED with fewer than 3 attempts: `not exists(… q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3))` (AO:440, 450).
  - The existing row's `recalc_from` is never lowered, so it can understate the earliest affected date.
  - A row that has failed 3 times does not stop a new PENDING row from being inserted.

**Processor: `process_cost_recalc_queue(p_limit)`** (AC:5841-5880)
- Picks rows `where status='PENDING' or (status='FAILED' and attempt_count<3 and next_attempt_at due)` with `for update skip locked` (AC:5855-5857).
- Then runs `rebuild_po_hpp` → `propagate_conversion_hpp_for_po` → `sync_po_hpp_to_gl(po, erp._cp3_business_date(statement_timestamp()))` (AC:5863-5865). The economic date is the day it is processed, not `recalc_from`.
- For a FINISHED PO it also calls `sync_finished_po_wip_residual(…, today, 'Post-close HPP/material recost residual adjustment')` (AC:5867).
- Failures are retried with backoff, 3 attempts maximum (AC:5874-5875).
- RUNNING is set and cleared inside the same transaction (AC:5861, 5871/5874), so other sessions never see a committed RUNNING row.
- No cron schedule exists in the repo; only scripts call it (`scripts/cp6_final_gap_native.py:137` and others). Authenticated users are granted EXECUTE (BOOT:36315; ACL pin AC:1093).

**The invoice path drains the queue inline**
- In the core function, when `v_invoice_date:=erp.invoice_recost_economic_date_v1()` is not null (AO:458), it processes every queue row for POs that use this material, with `q.status in('PENDING','FAILED')` and no attempt filter, so it also revives rows that failed 3 times (AO:459-479).
- It uses the invoice date for `sync_po_hpp_to_gl` and `sync_finished_po_wip_residual`, then marks the rows DONE (AO:476-477).
- So invoice and cost-correction transactions leave no open queue row. Rows stay PENDING or FAILED only when a non-invoice path triggered the recalculation.

**Non-invoice paths that trigger recalculation** (callers of `recalculate_material_cost`):
- In repo: `post_cutting_material_issue`, `post_cutting_material_returns`, `post_contractor_material_issue`, `post_material_transfer_v2`, `reverse_material_transfer_v2`, `post_opening_balance`, `replace_material_purchase`, `reverse_cutting_material_flow_before_sewing_v2`, `refresh_material_purchase_item_cost`.
- Base only: `post_material_purchase`, `post_material_adjustment`, `reverse_material_movement`, `_reverse_material_purchase_stock_at_source_time`.
- Wrappers:
  - `recalculate_material_cost(uuid)` (BOOT:16124-16170) uses the earliest `physical_at` among not-yet-recalculated movements.
  - `recalculate_material_cost(uuid,timestamptz)` (BOOT:16174-16183).

**How the core function handles closed periods**
- Reads `closed_through … for share` (AO:209).
- Uses the material cost checkpoint only when `checkpoint_date<=v_closed and _cp3_business_date(p_recalc_from)>checkpoint_date` (AO:253-298).
- Otherwise it replays the full history and rewrites `unit_cost_snapshot` in place, including movements on or before the closed date (AO:300-384).
- It then calls `sync_material_cost_revaluation` (AO:432) and finally `refresh_material_cost_checkpoint(material, v_closed)` (AO:481-483).

**How invoice paths set economic and GL dates**
- Context table `invoice_recost_execution_context(transaction_id, invoice_date, source_id)` (AO:127-131). `invoice_recost_economic_date_v1()` returns `select invoice_date … where transaction_id=txid_current()` (AO:134-137).
- `post_material_supplier_invoice` (AO:709-842):
  - Context is set to `h.invoice_date` (AO:736); a future `invoice_date` or `received_at` is rejected (AO:737-738).
  - `refresh_material_purchase_item_cost` (AO:821) calls `recalculate_material_cost(material, receipt physical_at)` (AP:2631).
  - The AP/GRNI cent journal is posted at `h.invoice_date` via `_cp6_apply_supplier_cent_event` (AO:840, then `post_journal(p_source,p_id,p_date…)` at AC:1364).
- `post_material_purchase_cost_correction` (AO:627-707): context is `h.invoice_date` (AO:649); calls `recalculate_material_cost(m, p.physical_at)` (AO:695); cent event at `invoice_date` (AO:705).
- The reversals use today's business date, not the original date: `reverse_material_purchase_cost_correction` (AO:868) and `reverse_material_supplier_invoice` (AO:960).
- Event tables filled from this context:
  - `material_cost_revaluation_events`: journal economic date is `coalesce(invoice ctx, today)` (AS:349-354). **`effective_date` is then overwritten with the journal's GL `transaction_date`** (AS:355-356).
  - `sync_po_hpp_to_gl`: `p_effective_date:=coalesce(invoice ctx, p_effective_date)` (AS:391). **`po_hpp_gl_events.effective_date` is also overwritten with the GL date** (AS:452-458).
  - `material_adjustment_revaluation_facts.effective_date` keeps the economic date `v_date` and is not shifted (AO:169-173).

**Where the GL date comes from**
- `post_journal` (AC:3956-4076) takes `FOR SHARE` on the control row (AC:4012), then calls `resolve_accounting_transaction_date` (AC:4056).
- Effective body of `resolve_accounting_transaction_date` (BOOT:17066-17080 after the T and AB patches):
  - `select closed_through … where singleton_id=1` (no lock).
  - If `p_economic_date<=v_closed`, it returns `greatest(today, v_closed+1)`.
- The journal stores `economic_date=p_transaction_date` and `transaction_date=GL date` (AC:4058-4059).
- `period_shifted` is a generated column (BOOT:987-988). A shifted posting writes an audit row "Late/backdated posting" (AC:4071-4074).
- `account_daily_balances` is keyed by GL date (AC:4067-4069).

**Date columns that show whether an open queue row reaches dates ≤ D**
- `cost_recalc_queue.recalc_from` → `erp._cp3_business_date(recalc_from) <= D`. This is cheap but a weak bound, because of the deduplication and the "any material" semantics above.
- `material_stock_movements.physical_at` of the PO's consumption movements (joined through `cutting_groups.po_id` or `contractor_material_issues.po_id`).
- `fg_lots.produced_at` (BOOT:897): the PO's HPP is re-allocated to all lots, including lots produced before the movement.
- Sale dates for the PO's lots (COGS).
- `journal_lines.po_id` joined to `journal_entries.transaction_date` / `economic_date`.
- `po_hpp_gl_events.effective_date` and `material_cost_revaluation_events.effective_date`: both hold the GL date. For the economic date, read the `journal_entry_id` → `journal_entries.economic_date`.
- `cost_adjustments.economic_date` (BOOT:566-580).

**What happens when a recost runs after the period is closed**
- **GL.** The queue path posts every delta on the processing day. Economic date equals GL date, so the journal is not flagged `period_shifted`. The only visible trace is the residual reason text (AC:5867). The invoice path keeps the invoice date as the economic date and shifts the GL date into the open period.
- **Subledger history is rewritten in place, with no period control:**
  - `material_stock_movements.unit_cost_snapshot` and `material_cost_history` (AO:374-381), unless the checkpoint applies;
  - `hpp_versions` and `fg_stock_movements.unit_hpp_snapshot` (`rebuild_po_hpp`, AP:5634-5665).
- No function blocks backdated material movements with `physical_at` inside a closed period.

### 2. Integrity check functions

None of these check functions takes a date argument.

**`_v268_financial_report_checks_pre_scope()`** (M:168, plus patches)
- CRITICAL: `V268_DAILY_BALANCE_LEDGER_MISMATCH` (M:215), `V268_UNBALANCED_POSTED_JOURNAL` (220), `V268_BALANCE_SHEET_EQUATION` (233), `V2620L_NONFINITE_LEDGER_MONEY` (239), `V2620L_NEGATIVE_VENDOR_AP` (253), `V268_AR_GL_SUBLEDGER_MISMATCH` (264), `V268_ACTIVE_SALE_MISSING_JOURNAL` (276), `V268_POSTED_SALES_RETURN_MISSING_JOURNAL` (290), `V268_POSTED_CUSTOMER_PAYMENT_MISSING_JOURNAL` (300), `V268_PRODUCTION_FG_WITHOUT_CURRENT_HPP` (308), `V268_COST_RECALC_EXHAUSTED` (315), `V268_LIABILITY_VIEW_HELPER_PRIVILEGE` (326), `V268_BROWSER_DIRECT_FINANCIAL_WRITE` (336).
- WARNING: `V268_COST_RECALC_PENDING` (320).
- Queue check wording: `V268_COST_RECALC_EXHAUSTED` = `status='FAILED' and attempt_count>=3`; `V268_COST_RECALC_PENDING` = `status in('PENDING','RUNNING') or (FAILED and attempt_count<3)` (M:315-322).
- It also imports a subset of `run_v267` (M:268-272):
  - Explicit names: `V267_GRNI_GL_SUBLEDGER_MISMATCH`, `V267_AP_GL_SUBLEDGER_MISMATCH`, `V267_PAYMENT_EXCEEDS_FINAL_AP`, plus `V267_INVOICE_MATCH_OVER_RECEIPT` (Q:163-170).
  - Prefixes: `V2620M_%`, plus N/O/P (P:198-212), R, S, T, U, V, W, Y (added by patches R:157, S:154, T:327-331, U:268-278, V:203, W:237, Y:365-370).
  - **The `AP_*` checks (initial import, prepayment, pocket) are not imported.**

**`run_v268_financial_report_checks()`** (AP:3315)
- Takes the pre-scope results minus four names (AP:3327-3332), then adds, all CRITICAL:
  - `V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE` (3335)
  - `V2620C_PO_HPP_TARGET_STATE_MISMATCH` (3345), `V2620C_HPP_COMPONENT_SUM_MISMATCH` (3357), `V2620C_PO_HPP_BOOK_MISMATCH` (3366), `V2620C_WIP_SOURCE_CONSERVATION_MISMATCH` (3375), `V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH` (3477), `V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH` (3498), `V2620C_DRAFT_SALE_VALUE_LEAK` (3519), `V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH` (3532), `V2620C_HPP_STATE_HAS_SUBCENT` (3544)
  - `V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH` (3553), `V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH` (4119)
  - `V268_ACTIVE_SALE_MISSING_JOURNAL` (3608) and `V268_POSTED_SALES_RETURN_MISSING_JOURNAL` (3618), both redefined
  - `V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH` (3628), `V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH` (4095)
  - `V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE` (3644), `V2620E_OPENING_HPP_LINEAGE_MISMATCH` (3656), `V2620E_OPENING_FG_GL_MISMATCH` (3704), `V2620E_REDISPATCH_EVENT_MISMATCH` (4017)
  - `V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH` (3724), `V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH` (3818), `V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH` (3829)
  - `V2620H_FAILED_WASH_RETURN_TIME_MISMATCH` (3907), `V2620H_CUSTOMER_AR_STATUS_MISMATCH` (3919), `V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH` (3935)
  - `V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH` (3964)
- Its only caller is `get_owner_financial_snapshot_v2` (AC:2827, 2831).

**`run_v267_financial_truth_checks()`** (AP:2634), all CRITICAL:
- `V267_*`: `GRNI_MAPPING_INVALID` (2640), `MISSING_GRNI_MAPPING` (2648), `ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS` (2653), `POSTED_INVOICE_MISSING_JOURNAL` (2665), `INVOICE_MATCH_OVER_RECEIPT` (2676), `PAYMENT_EXCEEDS_FINAL_AP` (2682), `LEGACY_CORRECTION_ON_GRNI` (2689), `POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT` (2697), `GRNI_GL_SUBLEDGER_MISMATCH` (2707), `AP_GL_SUBLEDGER_MISMATCH` (2717), `BROWSER_ROLE_DIRECT_INVOICE_WRITE` (2734).
- `V2620M_*` (2741-2839); `V2620P`/`O`/`R` (2848-2950).
- Business-date checks: `V2620Y_*` (2961-2979), `V2620W_SCRAP` (2991), `V2620V_MISC_FINANCE` (3000), `V2620U_*` (3009-3025), `V2620T_*` (3034-3049), `V2620S` (3058), `V2620N` (3067).
- `AP_OPENING_RECEIPT_SOURCE_DRIFT`/`AP_OPENING_RECEIPT_JOURNAL_DRIFT` (3090-3106), `AP_CASH_ADVANCE_*` (3116-3130).
- It also unions `initial_prepayment_checks_v1` (AP:1387), `pocket_fabric_checks_v1` (AP:1008) and `pocket_period_checks_v1` (AP:829), all with `AP_*` CRITICAL checks.

**`run_integrity_checks()`** (AC:7781-7866)
- ERROR: `UNBALANCED_POSTED_JOURNALS`, `NEGATIVE_MATERIAL_LOCATION_BALANCE`, `NEGATIVE_FG_BALANCE`, `FG_CACHE_MISMATCH`, `DUPLICATE_CURRENT_HPP`, `LAUNDRY_OVER_RETURN`, `QC_SOURCE_OVER_ALLOCATION`, `PAYROLL_ATTENDANCE_DUPLICATE`, `REWORK_PAYROLL_BEFORE_COST_POST`, `PAYROLL_PAID_NEGATIVE_NET`, `KASBON_PAID_OVERSETTLED`, `KASBON_STATUS_MISMATCH`, `REWORK_*` (3 checks), `BS_RESOLUTION_OVER_QTY`.
- WARN: `STALE_RECOST_QUEUE` (7860) and `FAILED_RECOST_QUEUE` (7863).

**Standalone check functions** (nothing calls them):
- `run_v256_integrity_checks` (AC:7868): `ACCOUNT_DAILY_BALANCE_MISMATCH`, `FUTURE_*` (4 checks), `CLOSED_PERIOD_LATE_POSTING_LEAK` (AC:7913-7921, reads the current `closed_through` and `updated_at`).
- `run_v257_integrity_checks` (AC:7925): work, QC, future-date and `FINISHED_PO_*` checks, all ERROR.
- `run_v259_integrity_checks` (CP6L:1671): identity and rate overlaps, including `LAUNDRY_RATE_OVERLAP`.
- `run_v262_integrity_checks` (AC:8040): lower-case names, CRITICAL, plus one WARNING.
- `run_v263a_payroll_integrity_checks` (`20260901161322…:150`).

**Functions that already take a date**
- `get_owner_financial_snapshot_v2(p_from,p_to,p_as_of)`: balances as of `p_as_of`; only one check is limited to the period, `V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH` (AC:2833-2840).
- `refresh_material_cost_checkpoint(material, D)` (AM:699-837): validates the transfer pairing, negative location/roll history and consistency of `material_cost_history` for movements before `D+1` in Asia/Jakarta, and raises `AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW` or "history is incomplete". Close already runs it for every material (AC:2418-2420), so **it is today's only per-date stock-cost integrity gate.**
- Base reports: `get_balance_sheet(p_as_of)` (BOOT:8361), `get_profit_loss(p_from,p_to)` (BOOT:29082), `get_fg_mutation_book(p_from,p_to)` (BOOT:28992).

**Which checks could be evaluated as of D** (my classification from the SQL):
- **Can be evaluated as of D** (the data is a ledger or dated facts):
  - Daily-balance, unbalanced-journal and non-finite checks, the balance-sheet equation over `balance_date<=D`, negative vendor AP.
  - Negative material/FG balance using `physical_at < D+1`.
  - The material checkpoint history validation.
  - Business-date conformity checks (`V2620S`/`T`/`U`/`V`/`W`/`Y`, `V2620K`/`J`/`I`) filtered to documents dated ≤ D.
  - Laundry custody and failed-wash timing checks (`V2620G`, `V2620H_FAILED_WASH`, redispatch).
- **Current state only** (cumulative state tables or current document status):
  - All `V2620C` PO HPP state/book/target checks, the HPP component-sum and sub-cent checks, `V2620F` book, `V268_PRODUCTION_FG_WITHOUT_CURRENT_HPP`.
  - `V2620C_WIP_SOURCE_CONSERVATION` (current source sums compared with the all-dates WIP book).
  - Subledger-versus-GL checks for AR, AP, GRNI and payment status (the GL side could be dated; the subledger side uses current status).
  - `FG_CACHE_MISMATCH`.
  - Privilege and mapping checks, which have no date.
  - Queue checks, which are global today and could only be scoped through `recalc_from`.

### 3. Attendance

**Tables**
- `attendance_periods`, one per contractor with `period_start`, `period_end`, `pay_date` and status DRAFT/POSTED/CORRECTED/REVERSED (M12:699-723). Active periods may not overlap (M12:728-750).
- `attendance_records` (BOOT:293-309):
  - status: PRESENT, ABSENT, HALF_DAY, SICK, LEAVE, OFF (BOOT:3119);
  - `record_lifecycle`: NULL means legacy posted; otherwise DRAFT/POSTED/CORRECTED/REVERSED (M12:803-826);
  - `uq_attendance_current_worker_date` covers rows where lifecycle is null or POSTED (M12:829-831).
- `worker_employment_periods` (M12:340-358) and `worker_is_employed_on` (M12:438-455).
- `contractor_workers.pay_scheme`: DAILY, PIECE, HYBRID or NONE (BOOT:531-547, 3195).
- `contractors.attendance_required` is a current flag, not dated (BOOT:557).
- `contractor_hpp_policy_versions` is dated and has `attendance_required_snapshot` (M14:123-141).
- Worker daily rates are dated (M12:76).

**Working days**
- **The database has no calendar or holiday table** (grep found nothing).
- A non-working day is recorded per worker per day as status `OFF` with `paid_fraction` 0 (M12:990-993, 1232-1237).
- The UI has a hard-coded `HOLIDAYS` constant labelled "contoh kebijakan" (`src/attendance/AttendancePage.tsx:157-158`). It is not stored anywhere.
- Rule written in the code: "A missing cell is unrecorded, never silently inferred as ABSENT/OFF" (M12:1253-1255).

**Existing rule for empty cells**
- `post_attendance_period_v1` (M12:1358-1381) counts empty cells as follows:
  - contractor has `attendance_required`;
  - loop over `generate_series(period_start, period_end)`;
  - workers with `pay_scheme in ('DAILY','HYBRID')` and `worker_is_employed_on(w,day)`;
  - no DRAFT record for that worker and day.
  - It then raises "unrecorded eligible worker/day cells" (M12:1379-1380).
- Posting also requires a daily rate for every such cell (M12:1383-1398).
- For the close gate, the same pattern would run over the close window and accept records with `coalesce(record_lifecycle,'POSTED')='POSTED'`. It would also need to decide what a DRAFT period covering the day means. Payroll uses the same attendance filter (AC:3116-3125).

### 4. Payroll

- `payroll_settlements` (BOOT:1739-1758): per contractor, with `period_start`, `period_end`, `status` DRAFT/CALCULATED/REVIEW/APPROVED/PAID/REVERSED (BOOT:3547), `payment_date`, `settled_at`.
- Non-reversed payrolls for one contractor may not overlap (`guard_payroll_period_overlap`, BOOT:10325-10342).
- The lifecycle guard freezes APPROVED, PAID and REVERSED (BOOT:10297-10321).
- **There is no global payroll period.** The attendance HPP pool manifest matches payrolls with `status in ('APPROVED','PAID') and ps.period_start=p_period_start and ps.period_end=p_period_end` (M14c:897-899), and pools are unique per exact period (M14:596-598).
- `approve_payroll` (AP:4565-4654):
  - requires CALCULATED or REVIEW (4581-4583);
  - takes the business-period lock (4586);
  - refuses if an ACTIVE HPP pool exists for the same period (4587-4594);
  - sets APPROVED (4611);
  - **posts accrual journals dated `p.period_end`** (4613-4644).
- **"Not approved" = status DRAFT, CALCULATED or REVIEW, with `[period_start, period_end]` overlapping the window.**
- A contractor with posted attendance or eligible work but no payroll row at all is invisible to a status check. Two possible sources:
  - `payroll_attendance_items.attendance_record_id` of non-reversed payrolls;
  - `v_payroll_eligible_work_lines`, filtered by `remaining_qty>0` and `eligible_at<=D` (used at AC:3090-3093).
- A payroll whose `period_end` falls after D puts its accrual after D.

### 5. Laundry with unknown price

**Tables**
- `laundry_vendor_rate_versions`: `vendor_id`, `wash_process_id`, `rate_per_pcs`, `effective_from`, `effective_to` (BOOT:1122-1130).
  - Owners and admins edit it directly through RLS grants (BOOT:31469-31475, 34059-34063) or through the base function `apply_bulk_rate_change` (BOOT:6400).
- `laundry_delivery_lines.estimated_rate_snapshot` and `estimated_cost_status` PENDING/ESTIMATED/FINAL (BOOT:1067-1074, 3329).
- `laundry_receipt_lines.actual_rate_snapshot`, `actual_cost_status` PENDING/ESTIMATED/FINAL, `actual_cost` (BOOT:1091-1103, 3335).

**Status meaning**
- **PENDING means the price is unknown.**
  - Receipt line: a null rate forces `actual_cost_status:='PENDING'` and `actual_cost:=null` (CP6L:1458-1463); with a rate it becomes ESTIMATED (1464-1466).
  - Delivery line: the legacy `post_laundry_delivery` looks up the rate and sets ESTIMATED only if one is found (AC:4103-4110); otherwise the line stays PENDING with a null rate.
- The legacy RPCs are granted to `service_role` only (AC:69-70, 126).
- The CP6 path `save_laundry_qc_action_v1` fails unless exactly one rate is effective ("Exactly one authoritative … Laundry rate", AC:8941, 9160). It writes ESTIMATED (AC:9063-9068, 9223-9232).
- ESTIMATED turns FINAL only when `post_vendor_invoice` posts (AC:5755). That function also posts a `cost_adjustments` row with `economic_date=invoice_date` (5759) and a journal and accrual/HPP sync at `invoice_date` (5767, 5780, 5784).

**How an unknown price is hidden today**
- `desired_laundry_accrual` uses `coalesce(estimated_rate_snapshot,0)` (CP6L:842), so an unknown price accrues 0.
- `rebuild_po_hpp` also treats it as 0 and marks `cost_state='ESTIMATED'`. That label mixes "unknown" with "estimated" (AP:5419-5432, 5491).
- The base `get_hpp_completeness` raises its laundry reason only when the accrual is above 0.005 (BOOT:29046-ish), so unknown prices are not flagged by that reason.

**Finding unknown-price laundry facts in a period**
- Deliveries not DRAFT or REVERSED, with a line where `estimated_rate_snapshot is null` / `estimated_cost_status='PENDING'`, filtered by `_cp3_business_date(laundry_deliveries.physical_at)`.
- POSTED receipts with a line in `actual_cost_status='PENDING'`, filtered by `laundry_receipts.physical_at`.

**Owner estimate**
- **There is no owner-estimate mechanism for laundry.**
  - Once a delivery is posted, the line rate cannot be changed from the browser: `guard_child_by_parent_status` allows changes only while the parent is DRAFT (BOOT:30487; AG:150-186). Server paths running as `postgres` or `service_role` bypass this guard (AG:161-163), but no server function edits it.
  - The trigger `sync_laundry_accrual_after_rate_change` (BOOT:30489; AC:10911-10916) is therefore reachable only while the delivery is DRAFT.
- A precedent exists for materials only: `price_source` MANUAL_ESTIMATE and `price_state` ESTIMATED/FINAL (AC:10075-10116).

### 6. GRNI

- `v_material_grni_aging` (BOOT:30015-30039) is `v_material_purchase_liability_status` filtered to `WHERE status='POSTED' AND grni_estimated_amount > 0.005`.
  - The underlying view is at BOOT:29965-30012.
  - Its `unfinalized_days` uses `CURRENT_DATE - h.physical_at::date`, which follows the session time zone, not Asia/Jakarta (BOOT:30001).
  - The GRNI amount comes from `material_purchase_grni_total` (BOOT:29416-29430).
- In the snapshot:
  - GRNI appears in `financial_position.grni_estimated_liability` from the GL (AC:2749-2750, 2863);
  - and in `supplier_exposure.unfinalized_receipt_count` / `oldest_unfinalized_days` from the aging view (AC:2820-2821, 2889-2891).
- **Open GRNI is not counted in `data_confidence`** (AC:2853-2858).
  - Only GRNI *integrity* reaches it: `V267_GRNI_GL_SUBLEDGER_MISMATCH` is CRITICAL through the pre-scope.
  - `V267_GRNI_MAPPING_INVALID`, `V267_MISSING_GRNI_MAPPING` and `V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS` are not imported into the pre-scope.
- The UI mock labels "GRNI > 30 hari" as a WARNING (`src/financeData.ts:213`).

### 7. Locks and concurrency

**Locks on `accounting_period_control`**
- FOR UPDATE:
  - `close_accounting_through` (AC:2410)
  - `reopen_accounting_through` (AC:5944)
- FOR SHARE:
  - `post_journal` (AC:4012)
  - `_recalculate_material_cost_core` (AO:209)
  - `post_material_transfer_v2` (AM:187)
  - `reverse_material_transfer_v2` (AM:319)
  - `guard_material_negative_stock`, a BEFORE INSERT trigger on `material_stock_movements` (AM:389; BOOT:30593)
- No lock:
  - `resolve_accounting_transaction_date` (BOOT:17066). Its only caller is `post_journal`, after that function's FOR SHARE, so it is safe in practice.
  - `run_v256_integrity_checks`, which is read-only (AC:7914).
- **No posting function reads `closed_through` without that protection.**

**Posting functions that never reach the control row** (transitive call graph, approximate):
- `post_attendance_period_v1`, `reverse_attendance_period_v1`, `save_attendance_period_v1`
- `populate_payroll_draft`, `merge_eligible_work_into_payroll_v2`
- `post_fg_movement`, `reverse_fg_movement`
- `record_sewing_terminal_v1` and its reversal (these use per-day advisory locks, `_cp3_lock_business_date`)
- `resolve_bs_case_disposition_v2`, `reverse_bs_disposition_v2`
- `apply_bulk_rate_change`, `apply_initial_import_receipts_v1`

These write dated facts that are not serialized with close. Laundry posting and `process_cost_recalc_queue` reach the lock only when they actually post a journal.

**Other locking facts**
- Payroll and HPP pool functions share `_cp3_lock_business_period`, an advisory lock per date (M14c:113-133). The callers are listed by the index; attendance posting does not use it.
- **Deadlock risk (lock-order inversion):**
  - close locks the control row FOR UPDATE, then each material FOR UPDATE via `refresh_material_cost_checkpoint` (AM:721);
  - `replace_material_purchase` locks materials FOR UPDATE first (AC:6056) and reaches the control row later.
- Legacy attendance rows (period NULL and lifecycle NULL) can be deleted directly by authenticated users under the guard (M12:850-857; grants BOOT:33267). This is from the CP4.5a snapshot and was not re-checked against later RLS changes.

### 8. Close and reopen: definitions and callers

- **`close_accounting_through(date,text)`** (AC:2398-2425):
  - `require_owner_admin` (2406);
  - `p_closed_through>=erp._cp3_business_date(statement_timestamp())` raises (2408);
  - reason is required (2409);
  - `FOR UPDATE` (2410);
  - moving the date backwards is refused, but the same date is allowed (2411-2413);
  - update (2414-2416);
  - checkpoint refresh for every material (2418-2420);
  - audit row (2422-2423).
  - History: Z patched `current_date` out (Z:175-182); AC is the latest CREATE.
- **`reopen_accounting_through(date,text)`** (AC:5934-5958): `FOR UPDATE` (5944); the new date may be null or earlier than the current one (5946-5951); no checkpoint refresh. Old checkpoints are ignored anyway through `checkpoint_date<=v_closed` (AO:256).
- ACL: `authenticated=X/postgres` (BOOT:35919, 36345; pins AC:45, 89).
- Callers:
  - **no SQL function and no public facade** — none of the ~50 `public.erp_*` wrappers wraps close, reopen or the snapshot;
  - the UI is a simulation only (`src/FinancePages.tsx:274-282`, `src/financeData.ts:210-216`);
  - test and audit scripts (`scripts/cp6_*`, list in `docs/cp6-au-r1-handoff.md:252-257`).
- A prior analysis of this gap (AUD-S06), with a proposed `accounting_close_preflight_v1`, is in `docs/cp6-au-r1-handoff.md:204-275`. It exists only as documentation; no such SQL function exists.

### Open questions and missing base-schema objects

**Missing from repo migrations** (read from BOOT or not found at all):
- Base-only functions, read from BOOT: `resolve_accounting_transaction_date`, `recalculate_material_cost` (both overloads), `guard_payroll_*`, `recalculate_payroll`, `get_hpp_completeness`, `material_purchase_grni_total`, `material_purchase_invoice_capacity`, `apply_bulk_rate_change`.
- Base-only views: `v_material_*`, `v_payroll_eligible_work_lines`.
- Base tables: `cost_recalc_queue`, `accounting_period_control`, `journal_entries`, `payroll_*`, `laundry_*`, `contractors`, `contractor_workers`.
- Not checked against the live catalog: whether later migrations altered base RLS or grants.
- Not found anywhere: a working calendar, a holiday table, or a laundry owner-estimate object.

**Questions for the design:**
1. **What counts as "affects ≤ D" for a queue row?** Options are `recalc_from`, which is weak because of the deduplication; PO consumption, FG production or sale dates ≤ D; or PO journals dated ≤ D. HPP is re-allocated across all lots of the PO.
2. **Should an exhausted FAILED row (3 attempts or more) block?** The invoice path revives such rows.
3. **Which checks can be scoped to D, and how?** Most HPP, subledger and GRNI checks are current-state only.
4. **Should the `AP_*` checks and the three excluded `V267` checks become close blockers?**
5. **What defines a working day?** Is it "an eligible DAILY/HYBRID worker with no record" as in M12:1358? Should `attendance_required` come from `contractors` (current) or `contractor_hpp_policy_versions` (dated)? Do legacy NULL-lifecycle rows count as posted?
6. **How should payrolls that straddle D, and contractors with no payroll row, be handled?**
7. **Laundry:** does an ESTIMATED status from a rate version count as "known"? Where should the owner estimate live?
8. **Serialization:** should close also take `_cp3_lock_business_period` over the window, or should attendance, FG and BS writers take the control row FOR SHARE?
9. **The in-place subledger rewrite of closed dates** (material cost snapshots, `hpp_versions`) is not period-controlled.