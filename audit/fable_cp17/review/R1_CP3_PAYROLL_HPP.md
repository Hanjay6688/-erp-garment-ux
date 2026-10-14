# R1 — CP3 / CP3.5 attendance → HPP → payroll entitlements, and the CP7 P12 seam

Candidate: commit `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, read-only checkout
`scratchpad/frozen` (all paths below are relative to that root; `MIG=` `supabase/migrations`, `REL=` `supabase/release/cp6-t3`, `CP7=` `scripts/cp7-src/payroll`).
Reviewer: source reading only, no database run. Every statement cites file:line; items I could not resolve from the tree are in §E.

Scope reminder (what "installed definition" means here): CP3 objects were created by `v2.6.14a..d` and then several
payroll lifecycle functions were re-emitted by CP6 release files (AC, AP, BB, BC) and by the CP4 HPP hook (`v2.6.16`).
The newest emission wins; §A names it. CP7 P12 is *not* a migration: it is a set of SQL bundles under `scripts/cp7-src/payroll/`
assembled by `scripts/cp7_*_bundle.py` and installed into a disposable copy per CI run. The P12 bundle also *patches* two native
functions (`erp.require_internal`, `erp.require_owner_admin`) at install time (`scripts/cp7_settlement_bundle.py:32-66`).

---

## A) Object map (table/function → file:line, installed definition)

### A.1 CP3 tables (created once, never re-emitted)

| Object | Created | Notes |
|---|---|---|
| `erp.contractor_hpp_policy_versions` | `MIG/20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql:123-144` | effective-dated, `unique(contractor_id,effective_from)`; `contractor_role_snapshot='MANDOR'` check |
| `erp.sewing_terminal_events` (SELESAI_DIJAHIT facts + REVERSAL rows) | `…14…foundation.sql:289-327` | `uq_sewing_terminal_source_completion` (:318) one SELESAI_DIJAHIT per work completion; `uq_sewing_terminal_one_reversal` (:322) |
| `erp.attendance_hpp_pools` | `…14…foundation.sql:561-603`; status set widened to `VOIDED` by `MIG/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql:307-325` | `uq_attendance_hpp_one_active_period` on **exact** `(period_start,period_end)` where ACTIVE (:598); `numerator_amount numeric(20,2)`, `denominator_qty bigint`, `unit_cost_per_sewn_pcs numeric(28,12)` (:569-571) |
| `erp.attendance_hpp_pool_sources` | `…14…foundation.sql:605-622` | one row per (pool, payroll); snapshot of policy flags; `original_debit_journal_line_id` |
| `erp.attendance_hpp_pool_allocations` | `…14…foundation.sql:624-640` | one row per (pool_source, sewing event); `allocated_amount numeric(20,2)` |
| `erp.attendance_hpp_journal_line_links` | `…14…foundation.sql:642-665` | DESTINATION_DEBIT / SOURCE_CREDIT lineage |
| `erp.v_attendance_hpp_active_allocation_by_po` | `…14…foundation.sql:667-684` | read model, security_invoker |
| `erp.v_attendance_hpp_active_allocation_by_po_group` | `MIG/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql:151-166` | per PO + cutting group |
| `uq_attendance_hpp_one_direct_correction` | `MIG/20260901023100_erp_v2_6_14b_attendance_hpp_candidate_hardening.sql:10-12` | one successor per cancelled pool |
| `erp.cp3_r4_rollback_capsule` | `MIG/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql:45-53` | stores pre-14d function bytes (incl. Enteng `reverse_journal`) |
| RLS + revokes on all six CP3 tables | `…14…foundation.sql:1594-1607` | RLS enabled, **no policies**, all grants revoked from public/anon/authenticated/service_role |

Attendance source tables (CP2/v2.6.12, pre-CP3): `erp.attendance_periods` `MIG/20260830140645_erp_v2_6_12_attendance_and_stock_explainability.sql:699-725`
(overlap guard :728-751, lifecycle guard :753-776); `erp.attendance_records` alters :803-838 (partial unique
`uq_attendance_current_worker_date` :829-831); `erp.payroll_attendance_items` snapshot columns :1596-1600.
Base tables `erp.payroll_settlements`, `erp.payroll_work_items`, `erp.payroll_deductions`, `erp.payroll_reimbursements`,
`erp.work_completion_events/lines`, `erp.journal_entries/lines`, `erp.idempotency_requests` and the view
`erp.v_payroll_eligible_work_lines` are **not defined anywhere in this tree** (they belong to the encrypted CP2/Enteng base, see
`docs/cp3-5-code-ownership.md:34-45`). Their columns are only inferable from callers.

### A.2 CP3 functions — installed definition

| Function | Installed definition | Superseded versions |
|---|---|---|
| `erp._cp3_business_date(timestamptz)` → `(ts at time zone 'Asia/Jakarta')::date` | `14c:56-64` | — |
| `erp._cp3_lock_business_date / _cp3_lock_business_period` (advisory lock per day, max 367 days) | `14c:99-134` | — |
| `erp._cp3_lock_manifest_contractors` | `14c:136-165` | — |
| `erp.set_contractor_hpp_policy_v1` | `14c:167-305` **patched in place by** `14d:276-320` (contractor advisory lock before row lock; `_cp3_r4_active_pool_affects_contractor` overlap guard) | `14:146-287` |
| `erp.record_sewing_terminal_v1` | `14c:613-756` | `14:329-463` |
| `erp.reverse_sewing_terminal_v1` | `14c:758-850` | `14:465-558` |
| `erp._build_attendance_hpp_manifest_v1` | `14c:852-982` | `14:686-817` |
| `erp._assert_attendance_hpp_manifest_v1` | `14c:984-1086` | `14b:17-87`, `14:819-881` |
| `erp.preview_attendance_hpp_pool_v1` | `14c:1088-1184` | `14:883-979` |
| `erp.create_attendance_hpp_pool_v1` | `14c:1186-1367` | `14:981-1166` |
| `erp.validate_attendance_hpp_pool_v1` | `14c:1369-1514` | `14:1168-1316` |
| `erp.activate_attendance_hpp_pool_v1` | `14c:1516-1686` **patched by** `v2.6.16:327-375` (captures journal `transaction_date`, then per PO `rebuild_po_hpp` → `propagate_conversion_hpp_for_po` → `sync_po_hpp_to_gl`) | `14:1318-1488` |
| `erp.cancel_attendance_hpp_pool_v1` | `14c:1688-1813` **patched by** `14d:347-349` (private reverse primitive) and `v2.6.16:377-420` (HPP/GL re-sync per PO) | `14:1490-1592` |
| `erp.attendance_hpp_exclusion_summary_v1` | `14c:1815-1903` (private; no public wrapper anywhere) | `14b:92-171` |
| `erp._cp3_r4_active_pool_affects_contractor` | `14d:97-197` | — |
| `erp._cp3_r4_reverse_journal_internal` | cloned at install from the *pre-14d Enteng* `reverse_journal` body (`14d:168-196`); **body not in tree** | — |
| `erp.reverse_journal` (generic, protected source types) | `REL/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql:5136-5165` (keeps the 14d guard at :5158-5160) | `14d:200-217` |
| `erp.reverse_work_completion` (sewing-event guard) | `REL/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql:7717-7779` (guard :7735-7746) | patched by `14d:322-345` |
| `erp.approve_payroll` | `REL/20260925030000_erp_v2_6_20bc_cp6_accessory_service_returns.sql:3186-3260` (R4 exact-period ACTIVE-pool guard :3207-3214; attendance accrual Dr WIP / Cr CONTRACTOR_PAYABLE dated `period_end` :3233-3243) | `14c:328-408` +`14d:258-274`, AC:2115, AP:4565, BB:3109 |
| `erp.post_payroll_payment` | `REL/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql:3201-3305` (future-date check in WIB :3220; accrual-presence check :3226-3236; CASH_ADVANCE journal :3246-3252) | `14c:410-493`, AC:4687, AP:4672 |
| `erp.cancel_unpaid_payroll` | `REL/…20ac…sql:2264-2320` (ACTIVE-pool guard :2283-2289; uses `_cp3_r4_reverse_journal_internal` :2297) | `14c:495-549` |
| `erp.reverse_paid_payroll` | `REL/…20bb…sql:3307-3380` (ACTIVE-pool guard :3324-3330; reverses accrual+deductions+payment :3332-3339) | `14c:551-611`, AC:7077, AP:4769 |
| `erp.populate_payroll_draft` | `REL/…20bc…sql:2874-3027` | `v2.6.12:1609`, AC:3056 |
| `erp.merge_eligible_work_into_payroll_v2` | `REL/20260924010100_erp_v2_6_20ax_cp6_fg_unsourced_receipts.sql:752-845` | AC:2964 |
| `erp.v_payroll_production_work_eligibility` (component entitlement rule) | `MIG/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql:37-127` | — |
| `erp.post_journal` | `REL/…20ac…sql:3956-4075` (rounds each line to cents :3992-3993; one POSTED journal per source :4000-4002; `economic_date` vs `transaction_date` via `erp.resolve_accounting_transaction_date` :4047-4050 — resolver body **not in tree**) | 20l:108 |
| `erp.rebuild_po_hpp` (per-lot HPP incl. attendance) | `REL/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql:4628-5012` (ACTIVE pool totals :4772-4778; per-group :4875-4878; per-lot `cp6_lot_attendance_cost_v2620c` :4929; conservation :4982-4989) | v2.6.16 patches, 20aj, AP, AY, BD |
| `erp.cp6_lot_attendance_cost_v2620c` (interval allocation of pool cost to FG lots) | `MIG/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql:259-315` | — |
| `erp.sync_po_hpp_to_gl` | `REL/20260924010200_erp_v2_6_20ay_cp6_hpp_dated_from_goods.sql:637-1069` | — |
| Public CP4 wrappers `public.erp_{set_contractor_hpp_policy,record_sewing_terminal,reverse_sewing_terminal,preview/create/activate/cancel_attendance_hpp_pool}_v1` | `v2.6.16:427-544` (granted to `authenticated, service_role`) | — |
| Detectors: `PAYROLL_ATTENDANCE_DUPLICATE` | `REL/…20ac…sql:7811-7812` (re-emitted BC:3130) | — |
| Close-readiness `PAYROLL_ATTENDANCE_UNCOVERED`, `ATTENDANCE_CELL_*` | `REL/20260924010000_erp_v2_6_20aw_cp6_close_readiness_engine.sql:565-632` | — |
| Posted-child integrity includes ACTIVE pool allocations in PO cost | `REL/20260916014332_erp_v2_6_20af_cp6_posted_child_integrity.sql:303-308` | — |

### A.3 CP7 P12 objects (bundles, not migrations)

| Object | File:line |
|---|---|
| Roles `cp7_payroll_read` (bypassrls), schema `cp7_payroll`, grants on `erp.v_payroll_eligible_work_lines` + closure | `CP7/source.sql:3-15` |
| `cp7_payroll.access_now / source_lines / source_cards / source_workspace`; `public.erp_cp7_get_nota_sources_v1` | `CP7/source.sql:17-85`, `CP7/ownership.sql:1-13` |
| Roles `cp7_nota_write`, `cp7_payroll_header` (bypassrls; `insert(id,payroll_number,contractor_id,period_start,period_end,notes)` + `update(id)` on `erp.payroll_settlements`) | `CP7/notes.sql:3-11` |
| `cp7_payroll.notes / card_claims / note_requests / execution_context` | `CP7/notes.sql:13-24` |
| `cp7_payroll.note_capture` (WIB period-end check :56), `note_payroll`, `note_header` (direct insert into `erp.payroll_settlements` :80-81), `note_allocation`, `note_verify_allocation`, `note_command` (POST calls `erp.merge_eligible_work_into_payroll_v2` with a fresh `gen_random_uuid()` :164) | `CP7/notes.sql:42-168` |
| `cp7_payroll.settlement_token` (xmin-based review token :7-17), `settlement_document`, `settlement_rows`, `settlement_workspace`; `public.erp_cp7_get_payroll_workspace_v1` | `CP7/settlement-read.sql:7-110` |
| Role `cp7_payroll_write`, `settlement_requests`, `settlement_context`, `settlement_access`, `require_settlement_context`, `settlement_meaning`, `apply_settlement` (:51-101; PAY writes `erp.payroll_settlements.payment_date/payment_cash_account_id` directly :92 then `erp.post_payroll_payment` :93), `settlement_command` (:105-130), `public.erp_cp7_save_payroll_v1` | `CP7/settlement-write.sql` |
| `cp7_payroll.rebuild_nonwork` = `erp.populate_payroll_draft` text with the work delete/insert removed; built at bundle time | `scripts/cp7_settlement_bundle.py:16-30` |
| Native admission patch (`settlement_context` → `require_internal` / `require_owner_admin`) | `scripts/cp7_settlement_bundle.py:32-66`; predecessor `erp.require_internal` text `scripts/cp7-src/procurement/accepted-deltas.sql:10-56` |
| Attendance reader (`cp7_attendance`, `source_token` xmin :20-31, `workspace` :50-108) | `CP7/attendance-read.sql` |
| Attendance entry matrix | `CP7/attendance-entry.sql` |
| Attendance writer (`apply_command` :64-98 → native `erp.save_attendance_period_v1 / post_attendance_period_v1 / reverse_attendance_period_v1`) | `CP7/attendance-write.sql` |
| Roster/rate writer (`apply_roster` :22-50 → native `erp.set_worker_daily_rate_v1 / save_worker_roster_v1`) | `CP7/roster-write.sql` |
| E05 installments: `cp7_installment.accounts / payments`, triggers on `erp.payroll_settlements`, `erp.journal_entries`, `erp.journal_lines`, payroll child tables (:85-139), `source` (:167-230), `apply_command` (:261-348; direct `payment_date` write :305, direct `status='APPROVED'` write :330, ACTIVE-pool guard :334) | `CP7/installments.sql` |

No CP7 bundle and no frontend file references the CP3 pool RPCs (`grep -ril attendance_hpp scripts/cp7-src src` → only
`installments.sql:334` for the guard string). The only route to the pool lifecycle is the CP4 public wrapper set.

---

## B) Invariants and where the code enforces them

| Invariant | Enforced by | Verdict from source |
|---|---|---|
| INV-U01 balanced journal | `post_journal` `REL/…20ac…sql:3996-3999`; pool journal built with Σdebit(dest)=Σcredit(source) `14c:1566-1591`; validate re-checks debit=credit=numerator `14c:1472-1478` | enforced |
| INV-U02 / INV-C01 one effect per request | native `_idempotency_begin/_complete` (body not in tree) used by every CP3 RPC (`14c:206-208, 653-655, 798-800, 1213-1215, 1548-1550, 1715-1717`); CP7 `(actor,request_id)` tables `CP7/settlement-write.sql:119-123`, `CP7/notes.sql:117-121`, `CP7/attendance-write.sql:106-110`, `CP7/installments.sql:356-360`; same UUID + different payload → `*_REQUEST_CHANGED` | enforced on CP7 side; native hash-mismatch behaviour **unverifiable** (§E) |
| INV-U03 reversal is exact inverse | pool cancel = `_cp3_r4_reverse_journal_internal(post_journal_entry_id)` `14c:1783` (+14d patch) — primitive body not in tree; payroll reversal loops all POSTED journals `REL/…20bb…sql:3332-3339` | mechanics present; **dates of reversal unknown** (R1-04) |
| INV-U04 control = subledger | pool credit lines keep `contractor_id` dim `14c:1578-1587`; destination debits keep `po_id` `14c:1566-1577` | enforced (dimensions carried) |
| INV-U06 no float, cents once | manifest in cents `14c:925-942`; allocation by cumulative floor of cents `14c:1298-1312`; exact per-source reconciliation `14c:1314-1323`; `post_journal` rounds each line `:3992-3993`. Preview returns `numerator_cents/100.0` and a 12-decimal unit cost as JSON numbers `14c:1174-1182` | enforced in storage; **surface returns JSON numbers** (R1-10) |
| INV-U08 payment never creates cost | attendance accrual only in `approve_payroll` (`REL/…20bc…sql:3233-3243`); `post_payroll_payment` asserts the accrual already exists and posts only settlement journals (`REL/…20bb…sql:3226-3236, 3238-3258`) | enforced |
| INV-S06 one PCS counted once (denominator) | `uq_sewing_terminal_source_completion` `14:318`; cumulative cap vs cutting group `14c:703-712`; `max(l.qty_completed)` cap `14c:688-695` | enforced per cutting group; **not enforced across overlapping pools** (R1-01) |
| INV-H02 cost flows, none appears/vanishes | pool Dr WIP(po)/Cr WIP(unassigned); `rebuild_po_hpp` conservation `REL/…20be…sql:4982-4989`; `cp6_lot_attendance_cost_v2620c` leaves unfinished intervals in WIP `MIG/…20c…sql:259-315` | enforced for pooled cost; **approved attendance cost that never enters a pool has no detector** (R1-01) |
| INV-H03 recost dated from goods | activation/cancel hand the journal `transaction_date` to `sync_po_hpp_to_gl` (`v2.6.16:343-366, 395-420`), which dates FG/COGS legs from physical facts (`REL/…20ay…sql:702-715, 756-1031`) | enforced given a correct reversal date (R1-04) |
| INV-T01 WIB business date | `_cp3_business_date` `14c:56-64`; manifest/validate/record/reverse use it (`14c:666-669, 905, 1431`); `populate_payroll_draft` work filter `REL/…20bc…sql:2910`; `note_capture` `CP7/notes.sql:56`; `post_payroll_payment` future check `REL/…20bb…sql:3220`. Event numbers formatted in UTC (`14c:719`) — cosmetic only | enforced |
| INV-T02 closed period | `post_journal` keeps `economic_date`, shifts `transaction_date` (`REL/…20ac…sql:4047-4050, 4068-4074`); `sync_po_hpp_to_gl` caps dates when E closed (`REL/…20ay…sql:711-715`) | enforced (resolver body not in tree) |
| INV-T03 no future physical | `post_payroll_payment` rejects `payment_date > today(WIB)` `REL/…20bb…sql:3220`; `installments.sql:296`; **no check that payment_date ≥ period_end / approval** (R1-05) | partially |
| INV-K01 posted docs immutable | pools: status machine + `validate` (`14c:1388-1394` STALE); attendance: `guard_attendance_period_lifecycle` `v2.6.12:753-776`; payroll APPROVED/PAID locked in `populate` `REL/…20bc…sql:2890-2892`, `merge` `REL/…20ax…sql:783-785`; installments add header/child/journal guards `CP7/installments.sql:85-139` | enforced |
| INV-K02 correction dated at economic date | depends on reversal primitive date (R1-04) and on `sync_po_hpp_to_gl` input date | **unverifiable for cancel path** |
| INV-K04 direct Native writes outside Native writers | CP7 `note_header` inserts `erp.payroll_settlements` (`CP7/notes.sql:80-81`), `apply_settlement` PAY updates `payment_date/payment_cash_account_id` (`CP7/settlement-write.sql:92`), installments update `payment_date` (`:305`) and `status='APPROVED'` (`:330`) — all commented but not written to a lineage table | **NOT ENFORCED IN CODE** (declared in comments only) |
| INV-K07 append-only fact tables | CP3 tables have RLS + zero grants (`14:1594-1607`) but **no UPDATE/DELETE-rejecting trigger**; `sewing_terminal_events` reversals are new rows (`14c:813-823`) | NOT ENFORCED IN CODE (protected by privilege only) |
| INV-C02 row_version / review_token | all CP3 RPCs take `p_expected_version` (`14c:768, 1522, 1694`); CP7 `review_token` from xmin of header + children (`CP7/settlement-read.sql:7-17`) | enforced; see R1-09 for xmin brittleness |
| INV-C03 concurrency | per-day advisory locks `14c:99-134`; contractor locks `14c:136-165`; period lock in approve/pay/cancel/reverse (`REL/…20bc…sql:3206`, `REL/…20bb…sql:3217, 3323`, `REL/…20ac…sql:2282`); R4 lock-order fix `14d:276-300` | enforced |
| INV-A01 permission checked start and end | CP7 re-checks `access` after locks and after native action (`CP7/settlement-write.sql:61, 99`; `CP7/notes.sql:166`) | enforced on CP7; CP3 checks once at entry |
| INV-A02 fail-closed roles | `require_owner_admin` null-safe rewrite `v2.6.16:124-148`; CP7 `access_now` requires `auth.uid()` + `authenticated` + permission (`CP7/source.sql:17-27`) | enforced |
| INV-A05 RLS/grants as declared | CP3: private (`14:1594-1621`, `14c:1907-1912`); CP4 wrappers granted to `authenticated, service_role` (`v2.6.16:538-544`); CP7: nologin owners, `revoke all … from public,anon,authenticated,service_role,cp7_capture`, only `public.erp_cp7_*` granted to `authenticated` (`CP7/ownership.sql`, `CP7/settlement-write.sql:136-146`) | enforced as declared |
| INV-L03 unknown ≠ zero | preview raises on zero denominator (`14c:1170-1172`), on missing policy for paid payrolls (`14c:1103-1119`); exclusion summary exists but is private (`14c:1815-1903`, revoked `14b:173-174`, no wrapper in `v2.6.16:427-544`) | partially (R1-07) |
| INV-POL01/02 no invented policy | Mandor eligibility is an explicit effective-dated policy row (`14:123-141`), pool refuses without it (`14c:1103-1119`) | enforced |
| INV-D01 detectors | `PAYROLL_ATTENDANCE_DUPLICATE` `REL/…20ac…sql:7811-7812`; `PAYROLL_ATTENDANCE_UNCOVERED` `REL/…20aw…sql:620-632`; AF posted-child integrity counts ACTIVE allocations `REL/…20af…sql:303-308`. **No detector** for (a) APPROVED/PAID attendance accrual not consumed by any ACTIVE pool, (b) ACTIVE pool whose manifest no longer matches (`validate_attendance_hpp_pool_v1` is never called by any integrity runner — grep across `REL/*`, `scripts/cp7-src/finance/period.sql`), (c) sewing event allocated by two ACTIVE pools | NOT ENFORCED IN CODE |
| Owner rule "upah = selesai dijahit − komponen BS/Stuck belum dikerjakan; GOOD bukan pengali" (`pack/kontrak/ERP_V3_2_Master_Pulih_20260923.md:3824`) | `v2.6.15:37-127` (per-component `qty_payable` immediately eligible; laundry not a gate) | enforced |
| Owner rule "denominator = all valid SELESAI_DIJAHIT incl. Afui" (`Master…:470`) applies to **kain kantong**; attendance HPP instead excludes `is_special` from numerator **and** denominator (`14c:869-877, 898-914`) | two different pooling rules, each explicit | consistent with separate decisions; flag for owner awareness only (§D) |

---

## C) Suspected defects

### R1-01 — Overlapping (non-identical) pool periods are not mutually exclusive; payrolls with a different period silently never enter any pool
- **Severity hypothesis:** S1 (cost stuck in WIP / denominators shared across pools), escalating to **S0** because no detector exists for either state.
- **Where:**
  - exact-period uniqueness only: `14:598` (`uq_attendance_hpp_one_active_period(period_start,period_end)`), `14c:1223-1230` (DRAFT/ACTIVE dup check is `=`/`=`), `14c:1555-1562`;
  - manifest selects payrolls by **exact** `ps.period_start = p_period_start and ps.period_end = p_period_end` (`14c:884-886`) but sewing events by **date range** (`14c:905`), with no exclusion of events already allocated by another ACTIVE pool (`14c:891-918`);
  - `approve_payroll` R4 guard is exact-match only (`REL/…20bc…sql:3207-3214`); `_cp3_r4_active_pool_affects_contractor` does handle overlap for *policies* (`14d:97-197`) but nothing equivalent exists for pools vs pools or pools vs payroll periods.
- **Why it matters:** (a) a contractor whose payroll period differs from the pool period (e.g. weekly vs monthly, or a CP7 Nota that created a header with its own `period_start/period_end`, `CP7/notes.sql:80-81`) is approved with `Dr WIP / Cr CONTRACTOR_PAYABLE` and that WIP never leaves "unassigned" unless someone later creates a pool with *that* exact period — which would then re-use sewing events already consumed by the first pool; (b) two ACTIVE pools `[1,31]` and `[15,31]` are both admitted and both allocate the same `sewing_terminal_events`; `rebuild_po_hpp` sums both (`REL/…20be…sql:4772-4778`) so the lot HPP carries two different "cost per sewn pc" bases over the same pieces. Neither state raises; the only readiness check is `PAYROLL_ATTENDANCE_UNCOVERED` (attendance→payroll), there is none for payroll→pool.
- **Probe (disposable copy, as owner/admin):**
  1. Two normal Mandors A, B with policies; approve A's payroll for `[2026-09-01,2026-09-30]` (attendance 300.00); B's payroll for `[2026-09-15,2026-09-30]` (attendance 100.00). Record SELESAI_DIJAHIT A: 10 pcs on 09-10; B: 10 pcs on 09-20.
  2. `create_attendance_hpp_pool_v1({period 09-01..09-30})` → activate. Expect numerator 300 (B excluded), denominator 20 (B's pcs included). Confirm with `select numerator_amount,denominator_qty from erp.attendance_hpp_pools`.
  3. `create_attendance_hpp_pool_v1({period 09-15..09-30})` → activate. **Confirms defect** if it succeeds (expected: it does — no overlap check) and `select count(*) from erp.attendance_hpp_pool_allocations where sewing_terminal_event_id=<B's event>` returns 2.
  4. `select sum(jl.debit-jl.credit) from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id where jl.account_id=erp.account_id('WIP') and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','ATTENDANCE_HPP_POOL') and jl.contractor_id=<B>` after step 2 only → 100.00 stays in WIP; run every detector (`run_v263a_payroll_integrity_checks`, close readiness `period_blockers_v1`) → **confirms "no detector"** if all are 0 rows.
- **Refutes:** step 3 raising, or a readiness blocker naming B's accrual.

### R1-02 — Adding a policy for a contractor that was silently excluded leaves an ACTIVE pool with a stale basis and no guard
- **Severity hypothesis:** S1 (detectable by `validate_attendance_hpp_pool_v1`, but nothing calls it; so effectively undetected → S0 risk).
- **Where:** sewing events of a Mandor with **no** policy row are dropped from the denominator by the inner lateral join (`14c:898-903` is `join lateral … limit 1`, not `left join`); preview only raises for missing policies of contractors **with** a paid/approved payroll (`14c:1103-1119`). After activation, `set_contractor_hpp_policy_v1`'s R4 guard looks for the contractor in pool child tables (`14d:97-197`); an excluded contractor has no rows there → guard returns false → policy accepted (`14d:302-320`). `validate_attendance_hpp_pool_v1` would now raise `STALE_POOL_INPUT` (`14c:1388-1394`) but is only invoked by activate.
- **Probe:** Mandor C with sewing events in the period and no policy row; Mandor A with payroll + policy. Create+activate pool (C excluded). Then `set_contractor_hpp_policy_v1` for C effective `period_start-1`. Expect **accepted**. Then `select erp.validate_attendance_hpp_pool_v1(<pool>)` → expect `STALE_POOL_INPUT`. Confirms: pool stays ACTIVE with a basis no longer reproducible; nothing in integrity runners reports it.
- **Refutes:** the policy write being rejected, or any detector row.

### R1-03 — Attendance double-pay across overlapping payroll periods relies on a base-schema trigger that is not in the tree
- **Severity hypothesis:** S1 if the overlap trigger exists (detected by `PAYROLL_ATTENDANCE_DUPLICATE`, `REL/…20ac…sql:7811-7812`); S0 if it does not (CP7 `note_header` can create arbitrary headers).
- **Where:** `populate_payroll_draft` (`REL/…20bc…sql:2934-2943`) and its CP7 derivative `rebuild_nonwork` insert **every** POSTED attendance record in `[period_start,period_end]` for the contractor with no `not exists (… other non-REVERSED payroll …)` filter (contrast the ACCESSORY_BOM branch which has one, `:2957-2965`). CP7 `note_header` inserts a header with the note's own period (`CP7/notes.sql:80-81`); `P12_NOTA_HANDOFF.md` asserts "Native payroll period overlap blocks multiple active payroll headers" but no such trigger/function exists in any file of this tree (`grep -ri "payroll.*overlap" supabase scripts` → only `attendance_periods`).
- **Probe:** for one Mandor insert/approve payroll `[09-01,09-15]`, then via `erp_cp7_save_nota_v1 SAVE/POST` (or direct `note_header`) create a payroll `[09-10,09-20]`, PREPARE it (`erp_cp7_save_payroll_v1 'PREPARE'`), then `select attendance_record_id,count(*) from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id where ps.status<>'REVERSED' group by 1 having count(*)>1`. Any row **confirms** double entitlement; `run_v263a_payroll_integrity_checks()` must then show `PAYROLL_ATTENDANCE_DUPLICATE>0` (that is the only safety net).
- **Refutes:** header insert rejected by a base trigger (record its name for §E).

### R1-04 — Economic date of pool cancellation and of the follow-up HPP/GL re-sync depends on an unreviewed primitive
- **Severity hypothesis:** S1 (INV-K02 / POLA-05 if the reversal is dated "today").
- **Where:** `cancel_attendance_hpp_pool_v1` reverses via `_cp3_r4_reverse_journal_internal` (`14d:347-349`), which is a byte clone of the **pre-14d Enteng `reverse_journal`** taken from `erp.cp3_r4_rollback_capsule` at install (`14d:168-196`); that body is not in the repository. `v2.6.16:395-420` then reads the reversal journal's `transaction_date` and calls `sync_po_hpp_to_gl(po, that date)`. If the primitive dates the reversal at `current_date` instead of the original economic date, the removal of attendance cost from FG/COGS is booked on the cancellation day, not in the period (INV-K02), and `sync_po_hpp_to_gl` caps all legs at that date (`REL/…20ay…sql:711-715`).
- **Probe:** activate a pool with `period_end=2026-08-31` (period open), FG sold in September; on 2026-10-14 cancel it. `select economic_date,transaction_date from erp.journal_entries where id=(select cancellation_journal_entry_id from erp.attendance_hpp_pools where id=<pool>)` and the `PO_HPP_GL_SYNC` journals created in the same transaction. **Confirms** if `economic_date` is 2026-10-14 while the original was 2026-08-31. Also run `select pg_get_functiondef('erp._cp3_r4_reverse_journal_internal(uuid,text)'::regprocedure)` and attach the text to the audit record.
- **Refutes:** economic_date equals the original journal's economic_date.

### R1-05 — Payroll payment date is not constrained to be on/after the accrual (period_end) or the approval
- **Severity hypothesis:** S1 (chronological negative payable per contractor; INV-P02-style "date ≥ source date" not enforced).
- **Where:** `post_payroll_payment` only checks `payment_date is null` and `payment_date > today(WIB)` (`REL/…20bb…sql:3219-3220`); CP7 PAY passes any canonical date (`CP7/settlement-write.sql:92, 113-116`); installments likewise (`CP7/installments.sql:296-297`). The accrual is dated `period_end` (`REL/…20bc…sql:3235`).
- **Probe:** approve payroll `[09-01,09-30]`; PAY with `payment_date='2026-09-05'`. Expect **accepted**. Then daily CONTRACTOR_PAYABLE balance for that contractor on 2026-09-05 is negative (`erp.account_daily_balances` or a running sum over `journal_lines` ordered by `je.transaction_date`). Confirms if accepted and negative.
- **Refutes:** rejection.

### R1-06 — SELESAI_DIJAHIT quantity cap uses `max(qty_completed)` of component lines — allowed by design but under-specified
- **Severity hypothesis:** S2 (policy clarity), S1 if a completion with partial components (e.g. 100 pcs of component X, 20 of Y) should not count 100 "fully sewn" pcs.
- **Where:** `14c:688-695` (`select max(l.qty_completed) … v_qty > v_max_line_qty → raise`). The owner rule (`Master…:3824`, `v2.6.15:1-11`) defines wages per component; "SELESAI_DIJAHIT" is a separate operator-entered quantity with no requirement that *all* components are complete.
- **Probe:** post a work completion with lines X=100, Y=20; `record_sewing_terminal_v1(qty_pcs=100)` → accepted. Owner must say whether 100 or 20 is "selesai dijahit" for attendance HPP.

### R1-07 — Exclusions from the denominator are invisible to every caller (INV-L03)
- **Severity hypothesis:** S2 (misleading READY preview), S1 when exclusions are policy gaps rather than intended Special.
- **Where:** `attendance_hpp_exclusion_summary_v1` exists (`14c:1815-1903`) but is revoked from all roles (`14b:173-174`) and has no `public.erp_*` wrapper (`v2.6.16:427-544` lists seven wrappers, none for it). `preview_attendance_hpp_pool_v1` returns `status:'READY'` without exclusion counts (`14c:1174-1182`).
- **Probe:** Mandor without policy has 50 pcs sewn in the period; call `public.erp_preview_attendance_hpp_pool_v1` → READY with denominator excluding 50 and no mention. Confirms surface gap.

### R1-08 — `_cp3_lock_business_period` hard limit of 367 days is applied to every payroll approval/payment/cancel/reversal
- **Severity hypothesis:** S2 (flow blocked, fail-closed).
- **Where:** `14c:122` raises for `period_end - period_start > 366`; callers `REL/…20bc…sql:3206`, `REL/…20bb…sql:3217, 3323`, `REL/…20ac…sql:2282`. A legacy or cutover payroll spanning >367 days cannot be approved, paid, cancelled or reversed.
- **Probe:** payroll `[2025-01-01,2026-02-01]` → `approve_payroll` raises `CP3 business period lock is bounded to 367 calendar days`.

### R1-09 — Review tokens are built from `xmin::text`
- **Severity hypothesis:** S2 (false `*_REVIEW_CHANGED`/`CP7_NOTA_SOURCE_CHANGED` after VACUUM FREEZE / pg_upgrade / wraparound; not a money defect).
- **Where:** `CP7/settlement-read.sql:10-14`, `CP7/attendance-read.sql:22-28`, `CP7/source.sql:36`.
- **Probe:** `vacuum (freeze) erp.payroll_settlements;` between read and PAY → expect `CP7_PAYROLL_REVIEW_CHANGED`.

### R1-10 — Money leaves the server as JSON numbers in the CP3 preview/create responses
- **Severity hypothesis:** S2 (INV-UI01; CP7 convention is strings).
- **Where:** `14c:1174-1182` (`numerator_amount`, `unit_cost_per_sewn_pcs` as numeric → JSON number through `public.erp_preview_attendance_hpp_pool_v1`), `14c:1352-1361`.
- **Probe:** payroll with attendance 9007199254740993 cents equivalent; compare JSON text vs JS `Number`.

### R1-11 — CP7 writes Native `erp.payroll_settlements` columns directly without lineage (INV-K04)
- **Severity hypothesis:** S3 (documentation/lineage), S1 if the direct `status='APPROVED'` write in installments bypasses a native status trigger.
- **Where:** `CP7/notes.sql:80-81` (header insert), `CP7/settlement-write.sql:92`, `CP7/installments.sql:305, 330`. Comments justify them; no `audit_logs`/lineage row is written for the direct writes themselves (the native functions called afterwards write their own).
- **Probe:** after `REVERSE_PAYMENT` on a PAID managed payroll, `select action,new_data from erp.audit_logs where entity_id=<payroll> order by changed_at` — check whether the PAID→APPROVED transition has an audit row; also confirm `cp7_installment.reopen_settlement` (derived at bundle time, not in tree) reversed the non-cash settlement journals.

### R1-12 — `rebuild_nonwork` and the E05 "derived native routines" are generated from a frozen catalogue, not from the installed function
- **Severity hypothesis:** S1 install-time fail-closed (`CP7_PAYROLL_PREDECESSOR_CHANGED`) or S3 doc drift.
- **Where:** `scripts/cp7_settlement_bundle.py:9-13, 28` asserts the installed `populate_payroll_draft` equals the P00 catalogue text; BC re-emitted that function (`REL/…20bc…sql:2874-3027`). If the catalogue predates BC the P12 bundle cannot install on a BC-level database; if it postdates, fine. `cp7_installment.{check_payment,final_payment,reopen_settlement}` are marked `-- E05_DERIVED_NATIVE_ROUTINES` (`CP7/installments.sql:152`) and their text is not in the tree.
- **Probe:** on the disposable copy at the frozen ledger, run the P12 settlement bundle; record whether the guard at `scripts/cp7_settlement_bundle.py:53-58` passes, and dump `pg_get_functiondef` of the three derived installment routines for review.

---

## D) Seams to CP7 (what P12 assumes about CP3 data)

1. **Entitlement source** — P12 reads `erp.v_payroll_eligible_work_lines` (base view, not in tree) and joins work/rework/repair sources (`CP7/source.sql:29-45`). It assumes the view already nets all non-REVERSED payroll allocations and exposes `remaining_qty`, `rate_snapshot`, `eligible_at`. Posting a Nota calls `erp.merge_eligible_work_into_payroll_v2` (`CP7/notes.sql:164`), which re-reads the same view under row locks (`REL/…20ax…sql:795-822`), so the view is the single truth; CP7 only verifies afterwards (`note_verify_allocation`, `CP7/notes.sql:97-107`).
2. **Period semantics** — P12 treats the payroll period as "everything eligible up to `period_end` (WIB)" with **no lower bound** (`CP7/notes.sql:56`; same as native `REL/…20bc…sql:2910`, `REL/…20ax…sql:816-818`), but attendance items **are** bounded by `[period_start,period_end]` (`REL/…20bc…sql:2938`). A Nota header's period therefore drives attendance inclusion and the CP3 pool matching (R1-01, R1-03). P12 lets the user pick `period_start/period_end` freely (`CP7/notes.sql:128-130`).
3. **Status assumptions** — P12 treats `DRAFT/CALCULATED/REVIEW` as editable (`CP7/settlement-write.sql:73`, `CP7/notes.sql:70`), `APPROVED` as payable, `PAID` as reversible; it relies on the native R4 guards to refuse while an ACTIVE pool consumes the payroll (`REL/…20bb…sql:3324-3330`, `REL/…20ac…sql:2283-2289`). Because **no CP7 page or bundle exposes the pool lifecycle**, a PAID payroll inside an ACTIVE pool cannot be reversed from the P12 UI; the operator would have to call `public.erp_cancel_attendance_hpp_pool_v1` out of band (which also rebuilds HPP and posts GL, `v2.6.16:395-420`). Same for attendance correction (`v2.6.12:1351-1361` requires consuming payroll REVERSED first).
4. **Cost recognition** — P12's APPROVE re-runs `rebuild_nonwork` then compares `settlement_meaning` before/after (`CP7/settlement-write.sql:82-88`) and calls `erp.approve_payroll`, assuming the native function recognizes attendance cost exactly once into WIP (true: `REL/…20bc…sql:3233-3243`) and that a later pool moves it to PO WIP. P12 never checks whether a pool exists; so cost can stay in unassigned WIP indefinitely (R1-01).
5. **Payment** — P12 assumes `post_payroll_payment` settles the full net and only validates `payment_date ≤ today(WIB)` (`REL/…20bb…sql:3220`); it supplies date/cash account by direct UPDATE (`CP7/settlement-write.sql:92`). Installments (E05) wrap this with their own `cp7_installment.payments` ledger and triggers on native tables (`CP7/installments.sql:85-139`), and assume `erp.journal_entries.period_shifted` exists (`CP7/installments.sql:196`; also read by `scripts/cp7-src/finance/journal.sql:23`) — no migration in the tree adds that column (§E).
6. **Timezone** — P12 serializes `eligible_at` in UTC and compares dates in WIB (`CP7/source.sql:57, 62`; `CP7/notes.sql:56`); it matches `_cp3_business_date`. Fixture clock pitfalls documented in `docs/cp7/P12_SOURCE_HANDOFF.md` (run15/16) were test-side only.
7. **Admission into native guards** — P12 extends `erp.require_internal`/`require_owner_admin` with a `cp7_payroll.settlement_context` branch (`scripts/cp7_settlement_bundle.py:32-46`), so native payroll functions accept an `authenticated` JWT with `finance.payroll.*` permissions only inside a P12 transaction. CP3 pool RPCs are **not** in that admission list; the pool wrappers still require `OWNER/ADMIN` app role (`v2.6.16:124-148, 427-544`).
8. **Special Mandor** — P12 shows `attendance_required` from the contractor master (`CP7/settlement-read.sql:21, 30`) but the CP3 pool uses the dated `contractor_hpp_policy_versions` snapshot; a flag flip on the master without a new policy version is refused by `set_contractor_hpp_policy_v1` only when a policy write is attempted (`14c:224-227`). P12 has no screen for the policy table.

---

## E) Things I could not determine from this tree

1. Bodies of base objects: `erp.payroll_settlements` (status default, triggers, any period-overlap guard), `erp.payroll_attendance_items.amount` (generated? rounding?), `erp.recalculate_payroll`, `erp.v_payroll_eligible_work_lines`, `erp._idempotency_begin/_complete/_request_hash` (does a same-UUID/different-hash call raise?), `erp.resolve_accounting_transaction_date`, `erp.reverse_journal` pre-14d (→ `_cp3_r4_reverse_journal_internal`), `erp.bump_row_version`. These live in the encrypted CP2/Enteng recovery set (`docs/cp3-5-code-ownership.md:34-45`). Everything in R1-03, R1-04 and INV-C01 hinges on them; the probes above dump them.
2. Whether `erp.journal_entries.period_shifted` is a real column on the hosted ledger (`CP7/installments.sql:196`, `scripts/cp7-src/finance/journal.sql:23` read it; only an audit-log JSON key of that name is created in `REL/…20ac…sql:4073`). If absent, `cp7_installment.source` fails at runtime.
3. Whether the P00 catalogue copy of `populate_payroll_draft` equals the BC emission (`REL/…20bc…sql:2874`), i.e. whether the P12 bundle installs on a BC-level database (R1-12).
4. Rounding point of attendance amounts: roster accepts rates with 6 decimals and fractions with 4 (`CP7/roster-write.sql`, `CP7/attendance-write.sql` regexes), so `rate×fraction` has up to 10 decimals; where the cent rounding happens (per item, per payroll, or at `approve_payroll`'s `round(attendance_total,2)` `REL/…20bc…sql:3229`) depends on the unseen `payroll_attendance_items.amount` definition. Preview tolerates a 1-cent drift (`14c:1128`). Probe: 3 workers × rate 100.123456 × fraction 0.3333 → compare `attendance_total`, Σ`amount`, WIP debit.
5. Whether any scheduled or CI integrity runner calls `erp.validate_attendance_hpp_pool_v1` on ACTIVE pools (none found in `REL/*`, `scripts/cp7-src/finance/*.sql`, `scripts/cp7-src/transactions/*.sql`); confirms R1-02's "no detector" only on the hosted schedule.
6. Frontend: no `src/**` file references the CP4 pool wrappers or `SELESAI_DIJAHIT` (grep empty), so I could not confirm how operators record SELESAI_DIJAHIT or run pools in the final product; `docs/cp7/P12_NOTA_HANDOFF.md` only forbids restoring the old QC/GOOD denominator.
7. Evidence of the CP3 R4/R5 concurrency proof (`scripts/cp3_r4_full_schema_concurrency.py`, `supabase/tests/cp3_r4_full_schema_seed.sql`) covers two scenarios (lines 435, 523); I did not re-execute them and did not find a case for overlapping pool periods or for the policy-after-activation path (R1-01/R1-02).
