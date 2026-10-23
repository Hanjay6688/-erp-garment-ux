# OW-04b parts 1–2: design for several credits on one invoice (design only, nothing built)

**Ringkasan untuk Bos (bahasa sehari-hari):**
1. Ini baru rancangan; belum ada yang dibuat. Retur kedua, retur pada invoice yang dibayar pakai saldo kredit, Edit
   retur dan Benerin nota pada invoice yang ikut saldo kredit, serta pembayaran sisa tagihan sesudah saldo kredit
   dipakai, saat ini masih ditolak sistem.
2. Usul urutan: (A) pembayaran sisa tagihan, paling kecil dan langsung berguna; (B) retur kedua dan seterusnya; (C) retur
   pada invoice yang dibayar pakai saldo; (D) Edit retur; (E) Benerin nota.
3. Tiap tahap diuji sendiri. Tahap yang belum selesai tetap ditolak dengan alasan yang jelas, jadi saldo kredit dan
   piutang tidak bisa salah hitung.
4. Perkiraan kerja: A sekitar 1–1,5 hari, B 2–3 hari, C 1,5–2,5 hari, D 3–4,5 hari, E 4,5–7 hari. Tiap tahap butuh
   beberapa kali uji CI (uji otomatis di GitHub).
5. Sebelum D dan E dimulai, saya perlu Bos menjawab tiga pertanyaan pilihan A/B di bagian 8.

Basis: retest `docs/cp7/d17-14/UJI_ULANG_CLAUDE.md` (OW-04 parts 1–2) and the open payment limit in `OW04B.md`.
Prior design: `SIGNED_RECOGNITION_DESIGN.md` and `NEXT_CONTRACT_GAPS.md`. Those documents already contain the
arithmetic and its counterexamples; this file turns them into delivery slices. All file:line references are to the
frozen base sources under `scripts/cp7_customer_credit/`, which E25j2 says must not be edited. Every change below is a
counted substitution in a new Native stage over the latest qualified stage of the linear chain, using the
`cp7_credit_followups` pattern. Facts I read directly in source are stated as facts. Effort and CI counts are
estimates.

## 1. What "cohort accounting" means here

- **Family.** A logical return: the root return plus its later corrections. A family gets a fixed ordinal per root invoice
  under the FG lock (`04_register_and_materialize.sql:112` already allocates `max+1`). Families that produced no credit
  (EMPTY) still take an ordinal.
- **Cohort.** The credit object created when a family's recognition is non-zero. It stores mode (CREDIT/REFUND), customer,
  liability account and plans. Its INITIAL plan comes from settling the return. Later ADJUSTMENT plans come from source
  mutations, posted through the existing reconciliation operation in `reconciliation/05_source_adjustments.sql`.
- **Excess funding.** `F(e,b) = max(0, funding(e,b) − net_invoice(e,b))`. An event counts when its economic date is ≤ e
  and its book date is ≤ b. Funding is the ordinary payments P plus incoming credit U (APPLY into this invoice).
- **Family target.** `T_i = F(base ∪ families ≤ i) − F(base ∪ families < i)`, as computed by
  `ow04_ordinal_wrapper.reconcile_v1`. Adding a later family never changes an earlier family's target. This is why
  slice B can be small.
- **Retained recognition.** `I_i` is the signed components actually posted for family i. Consumption `C_c` is the
  APPLY, REFUND and UNDO events against cohort c.

The balances can be proven because these identities can be checked by machine at every (economic, book) date corner:

| ID | Identity | Existing checker |
|---|---|---|
| I1 | For every family i, the posted components equal the target vector: wrapper `reconciliation_components = []` | `reconcile_v1` (`has_reconciliation_effect=false`) |
| I2 | Per invoice, `Σ_i I_i(e,b) = F(e,b)`. AR per invoice is `max(0, net − funding)`, never negative | follows from I1 and the telescoping sum. The OW-08a report reads `U−I` via `erp._cp7_current_credit_adjustment` |
| I3 | Base without returns has zero excess on all corners | `assert_zero_excess_v1` (`01_coordinator_facts.sql:137`), wrapper `BASE_OVERFLOW_NONZERO` |
| I4 | Per cohort, on every prefix, `Σ C_c ≤ I_c` (target and retained) | `credit_capacity_v1` via the wrapper's `source_prefixes_nonnegative` |
| I5 | Every liability-account line traces to one component part or one consumption event, with exact lines | `assert_financial_materialization_provenance`, `consumer_event_data_v1` |
| I6 | Every cash refund passes the dated cash guard and its book floor | `cp7_guard.check_cash`, `initial_refund_book_plan_v1` |

Today the product enforces these only for **one cohort per invoice and U = 0 on any invoice with a cohort**. Each slice
below removes one restriction and proves the identities for the new shape, instead of skipping them.

## 2. Verifiers that must change (exact proof each needs)

| # | Verifier (frozen source) | Today | Change | Proof required |
|---|---|---|---|---|
| V1 | `build_initial_return_for_draft_v1`, `02_initial_projection.sql:314-318` | refuses when the invoice has any cohort, an incoming APPLY, a note revision or a return correction | B: admit existing cohorts. C: admit incoming APPLY. Note/return corrections stay refused until D/E | Before the quote: `reconcile_v1(initial_ordinal_input_v1(sale))` has `arithmetic_supported` true and no family with an effect (I1 before). The quoted K is the wrapper's target for family n+1, computed with `prior = base ∪ families 1..n` |
| V2 | `assert_source_admission`, `04_register_and_materialize.sql:49-66` | `assert_zero_excess_v1(p.before_events)`; refuses an incoming APPLY or another cohort on the root | Replace zero excess with "before events = base ∪ all prior family events (exact set), base zero-excess, every prior family reconciled". Keep `other.id<>p.cohort_id` for the **same** cohort | Exact-set equality of before events with a fresh collector under the FG lock. `F(before) = Σ prior I` on all corners. The ordinal is `max+1` and its predecessor link is fixed |
| V3 | `assert_current_source_plan_profile`, `05_factual_profile.sql:136-200`, and its consumer copy `_consumer_root_source_profile_v1` (`consumer/composition.py:118-126`) | `n<>1` → `CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED`; `U<>0` → `CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED`; APPLY target → `CP7_CREDIT_CURRENT_SOURCE_ROUTE_UNIMPLEMENTED` | Loop over cohorts in ordinal order and repeat today's single-cohort proof per cohort (plan set, preserved source snapshot, kernel equality, part vectors, consumer data). Then add the invoice-level sums | Per cohort: actual component vector = wrapper target components for **that family** (I1); capacity per cohort (I4). Per invoice: `Σ I = F_total` (I2); `U = Σ` incoming APPLY minus undone, with each event proven by `consumer_event_data_v1` |
| V4 | `native_source_enter` (overlay `native-empty/04_exact_overlays.sql:586-591`) and `assert_simple_native_base_v1` (`05_factual_profile.sql:42-48`) | any cohort or incoming APPLY → `..._REQUIRES_BOUND_RECONCILIATION`; note/return/payment correction → `..._ADAPTER_UNIMPLEMENTED` | A: route PAYMENT / PAYMENT_REVERSE on an APPLY target **without** cohorts to a new admission. D/E: route corrections to the compound operations | A: after-state base (P + U + this payment) has zero excess on all corners (I3). Status recomputed from `effective = P + U − I` exactly as `consumer/08_owning_command.sql:289` does |
| V5 | `source_request_enter_v1` (`reconciliation/03_source_requests.sql:150-167`) and `source_adjustment_fresh_v1` (`05_source_adjustments.sql:65-117`) | needs a simple family; any consumer → `CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO`; positive or new-cohort adjustment → `CP7_CREDIT_SOURCE_RECONCILIATION_REVIEW_REQUIRED` | D/E only, and only per the owner's answers in section 8. The loop over families already exists; the consumer and positive-adjustment refusals remain until the compound operation exists | Every affected family's new I equals its new target (I1). Every cohort keeps I4 **after** the reduction; if not, refuse and list the consumers to undo |
| V6 | consumer UNDO of an APPLY (consumer command) | admitted (the target has no cohort today) | C: refuse the undo when it would change the target of any family on the target invoice | Recompute the target invoice's wrapper without that U. Any family with an effect → refuse, naming the target return (compound undo is a later decision) |
| V7 | `payment_correction` transform (`transform.py:53,171`) | refuses an invoice with incoming APPLY | A+: same admission as V4 for the corrected payment | Same as V4, applied to the replacement payment |
| V8 | OW-08a report (`cp7_report_credit.adjustment_v1` → `erp._cp7_current_credit_adjustment`) | an unprovable profile becomes null and is counted as `CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN` | none directly; it follows V3 | Report case: the multi-cohort invoice gives a proven `U−I` and zero critical rows |
| V9 | `cp7_credit_followups` detail classifier and `src/lib/creditRefusalMessages.ts` | names PRIOR_CREDIT_RETURN, CREDIT_APPLIED_TO_INVOICE and others | Each slice removes the reasons it now admits and keeps strict parsing. The "fitur lanjutan belum ada" text applies only to what is still refused | DOM and parser tests per remaining reason. An unknown shape still shows the code (D18d) |

None of these changes may become a fallback. Wherever a proof cannot be completed, the existing refusal stays, with the
named reason.

## 3. Slices

### A. Paying the remaining balance on a credit-paid invoice (smallest; useful on its own)

- **Scope:** an ordinary PAYMENT or PAYMENT_REVERSE (not an advance or opening payment) on an invoice that received APPLY
  and has **no cohort of its own**. Example: invoice 500, credit 80 used, payment 420 accepted, invoice becomes PAID.
  Payment 421 or 500 is refused.
- **Changes:** V4 (enter and complete hooks), status recompute, V9.
- **Why it is safe:** no recognition is created. The invoice only gains or loses funding, and I3 decides admission.
- **Still refused, with a named reason:** payment correction on such an invoice (V7, slice A+), and any payment on an
  invoice that has its own cohort. The latter would be overpayment, because a cohort exists only when funding is above net.

### B. Second and later returns on a paid invoice

- **Scope:** return n+1 on an invoice whose prior families are all reconciled. Prior cohorts may already have consumers
  (APPLY, REFUND or undo), because consumption does not change targets. Settlement is the same per-return choice as
  today: cash refund or customer credit, with an eligible liability account.
- **Changes:** V1, V2, V3 (U still 0), V8, V9. Client: the quote states "retur ke-n" and shows the per-family credit.
  The customer credit workspace already selects a cohort explicitly (`cohort_id` in the consumer payload), so no
  allocation rule is needed.
- **Still refused:** the invoice received APPLY (C); note or return corrections (D/E); a source reversal on a
  multi-family invoice whose cohorts have consumers (V5, unchanged).

### C. Return on a credit-paid invoice, and the undo dependency

- **Scope:** a return on an APPLY target. Incoming U already enters its base events
  (`consumer/composition.py:104-108`).
- **Changes:** V1/V2 drop the APPLY clause. V3 replaces the `U<>0` refusal with the I2 proof including U. V6 refuses an
  undo of the incoming APPLY when that undo would change a family target on the target invoice.

### D. Edit retur on a credit invoice

- **Scope:** the return correction (reverse plus replacement) becomes one owning operation, composed with the source
  reconciliation. The replacement keeps the root family ordinal and cohort.
- **Decreases:** allowed when the reduced I still covers that cohort's consumption on every prefix (I4). Otherwise
  refuse and list the consumers to undo.
- **Increases:** depend on owner question Q1.

### E. Benerin nota on credit invoices

- **Scope:** the note correction today replays returns before payments (`NEXT_CONTRACT_GAPS.md`), which conflicts with
  the family graph. The compound operation must carry every family and cohort to the replacement note with the same
  ordinals, preserve root book floors, and handle incoming APPLY per owner question Q3.
- Positive adjustments follow Q1. Shortfalls follow Q2.

## 4. Cases per slice (Native unless noted; each with first-failure evidence kept)

**A:**
- pay exact remaining: PAID, AR 0, `E = P + U`, journal lines exact
- pay one cent over: refused, no effect
- payment dated before the APPLY that would overfund on an earlier corner: refused (two-axis check)
- reverse that payment: PARTIAL_PAID again
- undo the APPLY after the payment: status and E consistent
- payment correction still refused with a named reason
- race: two payments that each fit alone but not together: one wins, the other is refused with no effect
- report (V8) proven
- DOM: the payment screen shows the remaining amount after credit

**B:**
- second return as CREDIT, then as REFUND, each with the exact K from the wrapper; `Σ I = F` on all corners
- third return
- second return after cohort 1 was partly applied or refunded
- second return when family 1 was EMPTY (already supported; must stay unchanged)
- refusal when a prior family is unreconciled (a crafted drift through the retained source-mutation path, not by fixture)
- refused cash refund with no effect (dated guard)
- report proven
- race: two concurrent second returns, one family each and ordinals unique, or the stale review is refused
- race: second return vs undo of cohort 1's APPLY

**C:**
- return on target: K includes U
- undo of the APPLY refused with the target return named
- undo allowed when the target return produced no credit
- race: target return vs source undo

**D/E:** the counterexamples already written in `SIGNED_RECOGNITION_DESIGN.md` ("Bantahan"; two-family attribution;
root book floor) become required cases, plus increase, decrease and shortfall per the owner's answers and a race per
compound operation.

## 5. Oracles that must not be loosened

- `P11_RETURN_PAID_REFUSAL`: a payload without a settlement choice stays refused.
- Single-family results stay byte-identical: OW04 Native44/63/87, initial settlement, consumer Native8/Race, payment
  Native26, the OW-04b Native9/Race3 cases, and `OW04B_FIRST_RETURN_QUOTES_UNCHANGED`.
- `CP7_CREDIT_HISTORICAL_BASE_OVERFUNDING` / `BASE_OVERFLOW_NONZERO`, `FAMILY_NET_PREFIX_POSITIVE`,
  `ORDINAL_RECONCILIATION_CORNER_MISMATCH` / `CURRENT_MISMATCH`, and every capacity-prefix refusal.
- `CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO` and `CP7_CREDIT_SOURCE_RECONCILIATION_REVIEW_REQUIRED` stay until D/E
  replace them with the compound operation the owner chose.
- The dated cash guard and refund book floors (I6).
- **Race oracle that changes meaning:** `scripts/ow04-qualification/cp7_ow04_race_cases.py:93` expects
  `CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED` for the second of two concurrent first returns. After B, that is no
  longer the reason, but the worker must still be refused with no effect. The B stage must bind the quote to the
  before-profile and family ordinal. Its own race must then assert: one return, one cohort, worker refused with a
  stale-quote/review code, full private state equal to the holder's. The old suite stays unedited for its own
  composition.
- `OW04B_PAYMENT_ON_CREDIT_PAID_INVOICE_NAMES_REASON` stays valid for the followups composition. The A stage replaces
  it with the positive and over-payment pair above.

## 6. Size estimate (writer hours / Native CI runs)

These come from OW-04 history: most Native stages needed 2–4 runs before passing, and compound source operations took more.

| Slice | Hours | Native CI runs | Browser run |
|---|---|---|---|
| A | 6–10 | 2–3 | 1 |
| A+ (payment correction) | 4–6 | 1–2 | 0–1 |
| B | 16–24 | 3–5 | 1–2 |
| C | 12–20 | 3–4 | 1 |
| D | 24–36 | 4–6 | 1–2 |
| E | 36–56 | 5–8 | 2 |

The total is about 100–150 hours and 18–28 Native runs. A and B do not depend on any owner answer.

## 7. Delivery rules for every slice

- One stage folder per slice, composed over the latest qualified stage with counted exact substitutions. Each anchor
  occurs once and predecessor markers are checked. New helpers live in a private schema owned by `postgres`.
- Nothing in `scripts/cp7-src/**` or the hashed bundle is edited, and `source_manifest()` must pass.
- The status file says the slice is complete only after its CI run passes with the required case IDs, and the owner
  doc says in plain words what now works and what is still refused.

## 8. Questions for the owner (needed before D and E; A–C need none)

- **Q1.** Edit retur raises the value of a return that became customer credit. Should the extra (A) go automatically
  into the same customer credit, shown on screen before saving, or (B) require choosing again between cash refund and
  credit?
- **Q2.** A correction (Edit retur or Benerin nota) lowers a credit that has already been used or refunded. Should the
  system (A) refuse and list the uses to undo first, or (B) allow it and record the shortfall as money the customer owes
  (receivable)? Recommendation: A.
- **Q3.** Benerin nota on an invoice partly paid with customer credit. Should the credit use (A) move automatically to
  the replacement note, or (B) be cancelled first (the balance goes back to the customer) and re-applied by hand?
- **Optional.** When a customer pays more than the remaining balance, should the excess become customer credit
  automatically? (Yes/No. Recommendation: No, refuse as today.)
