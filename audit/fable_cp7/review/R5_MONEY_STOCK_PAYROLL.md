# R5 — Money / Stock / Payroll sub-review of d0b9e9c2 (read-only, source-level)

Scope: scripts/cp7-src/{finance,invoices,procurement,supplier-returns,sales,fg,materials,wip,payroll,planning}, src/ finance components.
Paths below are relative to the candidate checkout `scratchpad/cand`. Base (pre-CP7) erp.* functions were only grepped in supabase/migrations where CP7 delegates to them.

## 1. Suspected defects / risks (priority order)

D1 (medium-low) Payroll PAY date: two inconsistent clocks.
- scripts/cp7-src/payroll/settlement-write.sql:92 sets payment_date from payload (format-only check at :118) and calls erp.post_payroll_payment; native (supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql:23) rejects `payment_date>current_date` = server TZ (UTC on Supabase), so a WIB-today payment between 00:00–07:00 WIB is refused as "future".
- scripts/cp7-src/payroll/installments.sql:296 uses `(statement_timestamp() at time zone 'Asia/Jakarta')::date`. Same business action, two rules. Safe direction (false refusal) but violates "tanggal ekonomi WIB".

D2 (medium-low) Receipt correction replays overpayment onto another receipt without the before-receipt rule.
- scripts/cp7-src/procurement/correction.sql:461-476 `replay_payment` inserts erp.supplier_payments with the ORIGINAL payment_date onto target receipt `credit->>'purchase_id'` (:986-1000) and posts it; no `payment_date >= target.physical_at` check, whereas the app create path refuses `CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT` (invoices/payment-create.sql:128). A "credit" piece can be dated before the goods of the target receipt arrived (an advance, by the project's own comment at :127).

D3 (medium-low) Native negative-stock guard disabled during receipt correction.
- scripts/cp7-src/procurement/correction.sql:784 `set_config('erp.allow_source_replacement_negative','on',true)`. Compensated by location_floor/shifted_floor/roll_use (:195-230) but those cover only non-roll materials by material+location and roll "movable" check; any path not covered by these prefix checks would be admitted. Needs runtime probe P6.

D4 (low) Native function body text-patching at install.
- scripts/cp7-src/sales/correction.sql:140-170 (and sales/return-correction.sql:200-210) copies erp.reverse_* definitions via pg_get_functiondef and `replace()` of `clock_timestamp()`/`statement_timestamp() AT TIME ZONE` with historical dates. Guards raise CP7_NOTE_NATIVE_*_CHANGED when the expected text is absent, but a future native edit that keeps the token yet changes semantics would be silently patched. Fragile but fail-closed on token absence.

D5 (low) Supplier credit re-allocation journals dated `today`, not the return's physical date.
- scripts/cp7-src/procurement/supplier-credit-authority.sql:79-88 post BF_SUPPLIER_CREDIT_MOVE at `today` (business date) with two AP_SUPPLIER lines (debit=credit same account, no vendor_id/po_id dimension). Net-zero on GL; the only effect is the per-receipt payable split. Acceptable, but per-receipt AP ageing (AP-5) changes on the allocation day, not the return day.

D6 (low, legacy) UNKNOWN wage → 0 in dead UI module.
- src/attendance/domain.ts:238 `rateSnapshot ?? rateForDate(...)?.dailyRate ?? 0`; src/attendance/AttendancePage.tsx:387 same. No non-test import of src/attendance/domain found (grep), so not reachable from CP7 pages; CP7 payroll uses payroll/source.sql rate_snapshot as text with no coalesce.

D7 (info) HALF_DAY paid_fraction ≤ 0.5 and ABSENT/OFF = 0 are hard-coded in scripts/cp7-src/payroll/attendance-write.sql:59. Not in OWNER_DECISIONS_20261008 / cp6-d11 / framework-v2 (grep half_day/paid_fraction: none) but mirrors native rule supabase/migrations/20260830140645_...:998-999, so it is inherited, not invented. No other payroll multipliers/penalties/rounding constants found in payroll/*.sql (grep of numeric literals; only 2-dp cents checks :162, :258).

D8 (info) finance/recost.sql:28 cp7_recost.workspace is `security definer` (other readers are invoker) — it does call access_now(false) first; no defect, but inconsistent with the stated pattern.

No float/double/real column or cast found in cp7-src (grep). All `round()` on money is 2-dp validation or display (`<>round(x,2)` guards: invoices/payments.sql:60, installments.sql:162, procurement/correction.sql:738, supplier-credit-authority.sql:61); 6-dp rounding only on displayed stock values (fg/bootstrap.sql:64, materials/read.sql:42,70, procurement/correction.sql:1114) never stored. Divisions: finance/analysis.sql:28,30 produce percentages rounded 4dp, labelled rounding_scale 4, null when base ≤0 — not money.

## 2. Properties confirmed by source

Finance
- Debit=credit enforced by native erp.post_journal (supabase/migrations/20260911070622_..._exact_ledger_conservation.sql:156 `if v_debit<>v_credit or v_debit<=0 then raise`). All CP7 postings go through erp.post_journal / erp.reverse_journal (grep: no `insert into erp.journal_*` in cp7-src). Journal reader reports `unbalanced_journal_count` (finance/journal.sql:52-53,72) as a monitor, not the enforcement.
- Profit is NOT computed in CP7; finance/read.sql:46 and analysis.sql:21-22 delegate to erp.get_owner_financial_snapshot_v2 and pass `gross_profit`/`sales_revenue_gl` through `exact_numbers` (read.sql:22-32 converts every jsonb number to text → no JS float). Growth/margin null when base not >0 (analysis.sql:28,30).
- UNKNOWN ≠ 0: fg/bootstrap.sql:58-65 lot value `state=UNKNOWN`, unit_cost/value null when hpp pending/ESTIMATED/laundry unknown/completeness pending; materials/read.sql:42 same for moving average; src/skuHpp.ts:9-10 null → "Belum tersedia"; ConnectedFinanceOverviewPage.tsx:80-96 renders numbers only when `data&&snapshot&&confidence`, margins null → "Belum dapat dihitung"; on fetch error setData(null)+alert (:57-58). UI money formatting is string-based (procurementContract.ts:114-118), no Number().
- Only coalesce(...,0) hits on money in non-planning cp7-src: sales/correction.sql:299-300 (discount_amount null→0, legitimate) and sum-of-payments/cash-balance aggregates (sales/read.sql:38, finance/analysis.sql:32-34, installments.sql:161) where empty set = truly zero.
- WIB: all user-facing date bounds use `(statement_timestamp() at time zone 'Asia/Jakarta')::date` (finance/read.sql:45, journal.sql:43, analysis.sql:18, period.sql:34, installments.sql:296). Future-date refusals: payment-create.sql:126, payment-correction.sql:170, misc.sql:157, fg/adjustments.sql:46. Closed-period handling delegated to native (journal header exposes `period_shifted`, journal.sql:23).
- Period close/reopen: review_token binds through+control+preflight+balances (period.sql:42), rechecked under native control-row lock (:81-83); outcome mismatch raises (:91).

AP
- GRNI/late invoice is native (`MATERIAL_PURCHASE_GRNI_RECLASS` recognised in correction.sql:358,383; erp.material_purchase_grni_total used by reminders/payable-source.sql:7,110). CP7 invoice finalize delegates to erp.finalize_material_purchase_invoice_v2 (invoices/command.sql:29) after exact-decimal checks (:26). Receipt correction runs recost with economic date = business date of least(old,new receipt time) (correction.sql:767,780).
- Idempotency: every command keeps a (actor,request_id) request row and refuses changed payloads (payment-create.sql:150-153, payment-correction.sql:209-211, recost.sql:62-68, period.sql:75-79); supplier payments locked `for update` per receipt before amount check (payment-create.sql:110-122) → no double pay beyond `Native_AP.remaining`; replay links are unique (sales/correction.sql:35-37 primary key/unique; procurement/correction.sql payment_replays).
- Supplier payment from app: one transaction: insert DRAFT → erp.post_supplier_payment → verify POSTED + journal exists (payment-create.sql:129-135). Correction: erp.reverse_supplier_payment, then NEUTRAL/EFFECTIVE pair re-dates the inverse to the original economic date when they differ (payment-correction.sql:174-184), then replacement posted (:188-192).
- AP-5 (SELF_CHECK_FORMULAS_20261006.md:79): implemented in reminders/payable-source.sql:38-52 `payable_due_rule` — oldest-due-first within receipt, `OPEN_PORTION_DUE_MISSING` when due unknown, labelled rule-result; rounding 2dp (:47).
- Supplier credit: full replacement under STALE_VERSION (supplier-credit-authority.sql:54), prior moves inverted first (:77-84), same-supplier POSTED targets only (:69-71), total ≤ credit (:73), target payable ≥ paid after move (:94-96).

AR
- Draft reservation is native: CP7 only validates (sales/drafts.sql) and calls erp.save_sale_draft_v2/post_sale_v2 (sales/commands.sql:100,133); native post checks reservation == items (migrations/20260916050822_...:289-297).
- Partial return keeps lot: return lines are allocation-bound (sales/returns.sql:54-59 `allocated_qty>returned_qty` eligibility; cost from native normalizer, :2). Note correction replays returns matched by same lot_id + location + lineage (sales/correction.sql:276-287) with qty ≤ allocation minus already returned (:286-287).
- Price correction of a returned line: refused `CP7_NOTE_RETURNED_LINE_PRICE_CHANGED` when net unit price differs (sales/correction.sql:295-301); drafts/pending children block (:239-246).

Stock / HPP / production
- PCS conservation: wip/graph.sql:137 `CP7_WIP_CONSERVATION` (sum of stage outputs == input_pcs). Running-prefix never-negative checks on backdated receipt correction: procurement/correction.sql:195-230.
- Root physical vs commercial SKU: FG adjustments keyed on physical product_id+lot_id (fg/adjustments.sql:53); commercial SKU only displayed via erp.bf_commercial_sku_at_v1(product, sale_date) (sales/returns.sql:54).
- Recost: CP7 only drives erp.process_cost_recalc_queue(20) with idempotent request row (finance/recost.sql:69); ordering/chronology is native (`recalc_from` exposed :40). Not re-verified here.
- P08: planning/fabric-requirements.sql:202-207, :332, :377, :409-413 — any unproven physical fabric → `FABRIC_PHYSICAL_NOT_PROVEN` / `FABRIC_PHYSICAL_SOURCE_NOT_CAPTURED` (UNKNOWN with reason), never 0.
- PL-8: planning/supply-source.sql:140-152 exhaustion_proofs(group_id, facts_hash sha256 of the group's own captured fact rows incl. `completed_by_clock`, kernel_version sha256 of all reachable cp7 function defs + server_version_num :160-171, :214-226), append-only trigger :152, lookup requires exact (group, kernel, facts_hash) with a single consistent verdict (:228-231).

Payroll
- Worker code: CP7 roster facade forces `worker_code` from stored row on UPDATE (payroll/roster-write.sql:43-45) and delegates uniqueness to erp.save_worker_roster_v1; employment periods drive `employed_at_date` (attendance-read.sql:37).
- Installments: amount 2dp, ≤ remaining, final must equal remaining (installments.sql:162), only APPROVED and net_payable>0 (:291); each payment journal verified as exactly 2 lines payable/cash (:181-183, :191-193).

## 3. Runtime probes (expected outcomes)

P1 Payroll PAY clock: at 02:00 WIB (19:00 UTC prev day) call erp_cp7_save_payroll_settlement_v1('PAY', {payment_date: <WIB today>, ...}) on an APPROVED payroll → expect native "Tanggal pembayaran payroll berada di masa depan" (defect D1). Same date via erp_cp7_save_payroll_installment_v1 PAY → accepted. Expected if fixed: both accepted.
P2 Replay before receipt: supplier S has receipt A (physical 2026-09-01, paid 1,000,000 on 2026-09-02) and receipt B (physical 2026-09-10). Receipt-fix A down to 400,000 with credit allocation {B: 600,000}. Expect a POSTED supplier_payment on B dated 2026-09-02 < B.physical_at (D2). Compare with erp_cp7_create_supplier_payment_v1 on B with payment_date 2026-09-02 → `CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT`.
P3 Journal balance via facade: call erp_cp7_get_journal_book_v1({from,to}) after any CP7 write batch → `totals.unbalanced_journal_count` must be '0'; then attempt erp.post_journal with unequal lines → expect 'Journal is not balanced'.
P4 UNKNOWN not zero: lot with hpp_versions.cost_state='ESTIMATED' → erp_cp7_get_fg_book_v1 lot `value` must be null and `state`='UNKNOWN'; SKU HPP page shows "Belum tersedia". Revoke finance.reports.view → erp_cp7_get_finance_report_v1 raises 42501 CP7_FINANCE_ACCESS_DENIED and the overview page shows alert, no Rp figures.
P5 Returned-line price correction: sale with 1 posted partial return (2 of 5 pcs), then nota correction changing unit_price of that line → `CP7_NOTE_RETURNED_LINE_PRICE_CHANGED`; correcting a different line → replayed return attaches to same lot_id, AR = new net − refund, HPP movement at lot cost (fg_stock_movements unit cost equals original lot hpp, not current average).
P6 Negative-guard bypass: receipt with 100 m fabric (non-roll) at L1; transfer 60 m L1→L2 on day+1; receipt-fix qty to 50 m → expect `CP7_RECEIPT_FIX_*` refusal from shifted_floor (<0); confirm no material_stock_movements row leaves L1 prefix negative after commit (select min running prefix per material/location).
P7 Idempotency: call erp_cp7_create_supplier_payment_v1 twice with same p_request → second returns the saved outcome, exactly one supplier_payments row; same request id with changed amount → `CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED`.
P8 PL-8 binding: capture supply with a spent group → exhaustion_proofs row; reverse one of its movements (backdated) → next capture must re-classify (no `hit`), new proof row appended, old row still present (update/delete raise via trigger).
P9 AP-5: receipt with invoices I1 (due 09-05, 300k) and I2 (due 09-20, 700k), payment 300k → reminder due = 09-20; payment 299,999.99 → due = 09-05 (cents boundary); reverse payment → back to 09-05.
P10 Finance analysis division guard: baseline period with net-negative revenue → `revenue_growth_pct` null (not negative/inf).

## 4. Not determined (needs base-schema review or runtime)
- Chronological order of erp.process_cost_recalc_queue (recalc_from handling) and erp.get_owner_financial_snapshot_v2 formula (laba = pendapatan − HPP − beban) — native, not re-read.
- Native closed-period behaviour for NEUTRAL/EFFECTIVE restatements posted into a closed original period (`period_shifted` semantics).
- Negative-net payroll (deductions > wages): CP7 installments refuse (net_payable>0) but settlement PAY path delegates to native; carry-over rule not visible in CP7 sources; owner decision for negative balance not found in the oracle docs.
- Draft reservation double-booking across two concurrent drafts: native save_sale_draft_v2 (migration 20260829204632) not re-read.
- erp.save_worker_roster_v1 worker_code uniqueness constraint text.
