# OW-04b slice B (second and later returns): exact change inventory, not built yet

**Untuk Bos:** tahap B (retur kedua dan seterusnya) belum dibuat. Pemeriksaan sumber menunjukkan pekerjaannya jauh lebih
besar dari jatah 70 menit: ada sebelas titik pemeriksaan uang yang harus diubah bersama, dan bila hanya sebagian diubah,
retur kedua tetap ditolak. Dokumen ini mencatat titik-titik itu dengan tepat supaya pengerjaan berikutnya langsung jalan.
Retur kedua tetap ditolak dengan alasan yang jelas seperti sekarang.

Basis: `OW04B_MULTI_COHORT_DESIGN.md` slice B. References are to the frozen sources under
`scripts/cp7_customer_credit/` (E25j2: never edited). Each item becomes a counted substitution on the installed text
captured from the catalog, in a new stage.

## Stage placement

The new stage goes over `cp7_credit_remaining` (slice A), which itself sits over `cp7_credit_followups`, so there is one
linear chain. B patches different functions from A, except `build_initial_return_for_draft_v1`, which followups
patched for its detail; B captures the followups text. Pre-use removal restores the A/followups definitions exactly, then
calls `cp7_credit_remaining.composition.rollback_preuse`.

## What already supports several families (no change needed)

- Ordinal allocation `max+1` and the family registration (`04_register_and_materialize.sql:112-125`).
- `store_initial_plan_v1` (`04:132-137`) already proves the new family's wrapper `source_target` equals the actual kernel,
  and that **no other family has a reconciliation effect**. That is the "every earlier return fully reconciled" proof at
  registration, provided the before-events are right.
- The kernel call `recognition_plan_v1(before_events, added)` with `before_events = initial_base_events_v1(sale)` (all
  returns except the own draft) computes exactly `T_{n+1} = F(base ∪ families ≤ n+1) − F(base ∪ families ≤ n)`.
- `ow04_ordinal_wrapper.reconcile_v1` and `initial_ordinal_input_v1` are multi-family.

## Single-cohort assumptions that must change (11)

| # | Function (source) | Exact anchor | Change | Proof |
|---|---|---|---|---|
| B1 | `build_initial_return_for_draft_v1` (`02_initial_projection.sql:314`) | `  or exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=(p_legacy->>'sale_id')::uuid)` | Drop the cohort clause. APPLY, note revision and return correction stay. Also replace the followups detail so PRIOR_CREDIT_RETURN is no longer listed as a reason | Side by side: same message and detail for every remaining reason |
| B2 | same (`:336`) | ` perform cp7_credit.assert_zero_excess_v1(before_events);` | Call a new `assert_prior_families_reconciled_v1(sale,before_events)`. With no cohort it is **exactly** `assert_zero_excess_v1`. With prior cohorts: `reconcile_v1(initial_ordinal_input_v1(sale))` is supported, no family has an effect, the base without returns has zero excess, and `before_events` = base ∪ all prior family events (exact id set) | The first-return quote is byte-identical (FIRST_RETURN_QUOTES_UNCHANGED) |
| B3 | same (`:342`) | `if gross<0 or net<0 or paid<0 or paid>net or amount<0 or after_net<0 then` | Compare `paid − prior_I`, where prior_I is Σ retained I of prior families from `erp._cp7_current_credit_adjustment` or the profile. Keep `raw_paid` in the projection unchanged, because the Native guard compares it | `prior_I` equals the stored plans' net per family |
| B4 | same (`:387`) | `if issued<0 or issued>amount or paid-issued>after_net or paid-issued<0 then` | Use `paid-prior_I-issued` | — |
| B5 | same (`:419-422`) | `totals_before` / `totals_after` (`'credit_recognized','0.00'`, `effective_paid`) | Prior I in credit_recognized and effective_paid, so the screen shows the real before/after | Screen shows before E = P − prior I |
| B6 | `native_return_guard` (`03_native_initial_callbacks.sql:173`) | `  v:=p_raw_paid-(w.projected_kernel->>'net_current_k')::numeric;` | Reviewed branch only: also subtract prior_I as stored in the projection. The ORDINARY branch is untouched, so P11_RETURN_PAID_REFUSAL is still identical | Native then sees the effective paid ≤ net_after |
| B7 | `assert_source_admission` (`04:56-63`) | ` perform cp7_credit.assert_zero_excess_v1(p.before_events);` and `  or exists(select 1 from cp7_credit.cohorts other join cp7_credit.return_families f on f.id=other.family_id\n   where f.family_root_sale_id=w.source_sale_id and other.id<>p.cohort_id)` | Same replacement as B2. Drop the other-cohort clause **only** when every other cohort's family is reconciled. The APPLY clause stays | Same as B2 |
| B8 | `native_return_complete` (`04:260`) | ` result:=(w.projection->>'raw_paid')::numeric-full_k;` | Subtract the projection's prior_I | `result` = P − Σ I after |
| B9 | `_consumer_root_source_profile_v1` (installed; derived from `05_factual_profile.sql:131-200` by `consumer/composition.py`) | ` elsif n<>1 then raise exception 'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED';end if;` and the single `select c.*into strict ch` | Loop cohorts in family-ordinal order, with today's single-cohort body per cohort. Its before-events and preserved-source comparisons must use **family-prefix** versions (below), not `initial_base_events_v1(p_sale,ch.source_return_id)`, which would include later families. Replace `I = p.net_amount` with Σ over cohorts | Per cohort: components = wrapper target for its family, consumers proven, capacity per cohort. Per invoice: Σ I = F |
| B10 | new private functions | — | `family_before_events_v1(sale,ordinal)`: base events excluding returns of families ≥ ordinal. `family_preserved_source_v1(sale,ordinal)`: the preserved snapshot as it was when that family was settled (prior_returns and items of families < ordinal; payments and payment facts must match the stored snapshot) | With one family both equal today's `initial_base_events_v1(sale,return)` and `initial_preserved_source_v1(sale,return)` (asserted in a case) |
| B11 | detail classifier (`cp7_credit_followups.initial_family_reasons_v1`) and the screen | — | Stop listing PRIOR_CREDIT_RETURN where it no longer blocks. Update the screen's "fitur lanjutan belum ada" text for the remaining reasons. Quote shows "retur ke-n" | DOM and parser tests |

Each anchor in the table above was counted in its frozen source file and occurs exactly once (23 Oct 2026).

**Missed place found by the first CI run (b005aafe, run 39889035001):**
- **B12.** `opening_return_hpp_owner_v1` (`coordinator/03_opening_return_hpp.sql:32-33`) re-derives the guard's effective paid as `raw_paid − K`.
- It must expect `raw_paid − prior − K`, exactly as B6 now computes.
- Fixed by one counted substitution; the record is `ow04b-slice-b-b005aafe-first-failure.json`.

To verify during implementation (read, not yet confirmed): `finish_return_settlement` and `assert_initial_return_closed_v1`
(`06:63,216`) use `current_effective_paid`. That already sums all cohorts through the reader, so no change is expected.
`readers/02_materialized_profile.proposal.sql` loops cohorts (one INITIAL plan per cohort at `:148`), so no change is
expected. Each installed text must be re-captured, because the consumer, payment-correction, reconciliation, followups
and slice A compositions changed several of these functions.

## Cases (from the design, made concrete)

- Second return as CREDIT on the paid consumer fixture (1000 paid, return 200 gives credit 200). The second return of 100
  gives K = 100 with no effect on cohort 1's components. Σ I = 300 = F. AR = 0. The report proves the result.
- Second return as REFUND (with the dated cash guard); third return.
- Second return after cohort 1 was partly APPLY'd or refunded: K for family 2 unchanged by the consumption.
- Family 1 EMPTY (partly paid invoice), then family 2 with credit: already supported today; must stay byte-identical.
- First-return quote and Native44/63/87 single-family results byte-identical. Every protected refusal (APPLY target,
  note revision, return correction, ORDINARY return on a paid invoice = P11) identical side by side.
- **Race (required by the owner):** two concurrent *first* returns on one invoice, both reviewed before either commits.
  - Today the worker gets `CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED` (`ow04-qualification/cp7_ow04_race_cases.py:93`). After B1 that check no longer fires.
  - The worker must be refused by the binding to the invoice state before the return. The quote's `binding` already carries `immutable_source_sha256 = sha(before_events)` and `current_state_sha256`; after the holder's return both differ.
  - B must assert this in the settle path **before** any business row is written, for example by comparing the sealed quote binding with a fresh rebuild under the FG lock. The first-hit refusal code must be read from the source before writing the oracle.
  - Oracle: one return, one cohort, worker refused with that stale-binding code and no effect, final private state equal to the holder's.
  - The old suite stays unedited.

## Size

Re-estimated after reading the code: 16–24 writer hours as designed. B9 (the profile loop with family-prefix
snapshots) is about half of it. Expect 3–5 Native CI runs plus one browser run. Smallest safe first commit for the next
session: B10 and B2/B7 as private functions with a local check proving the one-family identity, then B1/B3–B6/B8, then B9,
then the cases and race.
