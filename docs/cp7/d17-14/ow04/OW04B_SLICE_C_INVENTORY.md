# OW-04b slice C (return on an invoice paid with credit): exact change inventory, not built yet

**Untuk Bos:** tahap C belum dibuat. Tahap C membuka retur pada invoice yang pernah dibayar memakai saldo kredit
pelanggan. Pemeriksaan sumber menunjukkan pekerjaannya lebih kecil dari tahap B, karena dua hal penting sudah ada di
sistem:
- Pembatalan pemakaian saldo yang menjadi dasar retur seperti itu sudah ditolak.
- Saldo kredit yang dipakai sudah dihitung sebagai pembayaran invoice.

Yang perlu diubah ada sembilan titik, kebanyakan "ikut menghitung saldo kredit yang dipakai". Sampai tahap C selesai, retur
seperti itu tetap ditolak dengan alasan yang jelas.

Basis: `OW04B_MULTI_COHORT_DESIGN.md` slice C and the slice B stage (`scripts/cp7_credit_multi/`, Native6+Race1 run
started at b005aafe). File references are to the frozen sources under `scripts/cp7_customer_credit/`, to
`followups.sql`, or to the slice B replacement text, as stated. E25j2 applies: nothing frozen is edited. The anchor
counts below were checked against those texts on 23 Oct 2026.

## Stage placement

A new stage over `cp7_credit_multi` (slice B), so the chain stays linear: followups → A → B → C. Several anchors are
slice B replacement strings, so C must capture B's installed text. Pre-use removal restores the B definitions exactly,
then calls B's removal.

## What already exists (no change needed, but proven by cases)

- **Incoming credit counts as funding.** The consumer composition adds `consumer_incoming_funding_v1(sale)` to
  `initial_base_events_v1` (`consumer/composition.py:104-108`). Every kernel, wrapper and zero-excess call on the
  target therefore already includes U, on both date axes.
- **The undo dependency is already refused.** `consumer/07_locked_projection.sql:277-283` handles an APPLY or UNDO into
  a target invoice:
  - it rebuilds the target's ordinal input with the new consumption added as FUNDING;
  - it refuses `CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED` when any target family would then need an
    adjustment.
  So once the target has a credit-bearing return, undoing the credit it depends on is refused before any write. A new
  APPLY that would raise the target's excess is refused the same way. Nothing in C changes this.
- **The current readers include U.** `current_effective_paid` (P + U − I) and the composed Native payment poster
  (slice A) already do. The consumer edit already lets an EMPTY receiving family carry U (`if(p_actual->>'I')::numeric<>0`).
- **Slice B's multi-family arithmetic** (`assert_prior_families_reconciled_v1`, family-prefix collectors, the profile
  loop) applies unchanged.

## Assumptions that must change (9, plus C8 kept on purpose)

| # | Where (installed text) | Exact anchor (count 1) | Change | Proof |
|---|---|---|---|---|
| C1 | Quote family check (`02_initial_projection.sql:316`) | `  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=(p_legacy->>'sale_id')::uuid)` | Drop it. Note revision and return correction stay | Side by side: same refusal and detail for the reasons that remain |
| C2 | Quote checks and totals (slice B text B3, B4, B5a/b) | `paid-cp7_credit_multi.prior_recognized_v1(h.id)>net`, `…-issued>after_net`, `'credit_applied','0.00'` | Add U (new private `incoming_applied_v1(sale)` = Σ APPLY-kind amounts into the invoice, undos included as negative; exactly what `fixture.profiles` reads). Totals show `credit_applied` = U, `effective_paid` = P + U − prior − issued | With U = 0 every value is slice B's |
| C3 | Native return guard, reviewed branch (slice B text B6) | `  v:=p_raw_paid-cp7_credit_multi.prior_recognized_v1(w.source_sale_id)-` | v = P + U − prior − K, so Native's status and its `v_paid>v_net_total` refusal see the effective paid | Status after the return equals today's reader status |
| C3b | Native return guard, ORDINARY branch (`native-empty/04_exact_overlays.sql`) | `  if p_raw_paid>p_net_after then return p_raw_paid;end if;` … `  v:=p_raw_paid;` | **Decision during implementation, not business:** an ordinary return (no settlement choice) on a credit-paid invoice must compare and return P + U. Otherwise Native sets PARTIAL_PAID when P + U = net. P11 (overpaid without choice) must stay a refusal: `p_raw_paid+U>p_net_after` returns the Native exception path unchanged | Side by side: P11 identical when U = 0 |
| C4 | Native return completion (slice B text B8) | ` result:=(w.projection->>'raw_paid')::numeric-cp7_credit_multi.prior_recognized_v1(w.source_sale_id,w.family_ordinal)-full_k;` | Add U | `result` = P + U − Σ I |
| C5 | Registration admission (`04_register_and_materialize.sql:60`) | `  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=w.source_sale_id)` | Drop it. B2/B7 already prove the before-vector, which contains U | Same as B7 |
| C6 | Profile loop (slice B text B9d) | `or(p_actual->>'U')::numeric<>0 then` | Becomes `<>incoming_applied_v1(p_sale)`. Each incoming event is already proven by the root wrapper (`consumer_event_data_v1` over upstream roots). B9e's whole-excess check already includes U, through the events | One/two families with U: accepted; wrong U refuses `CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED` |
| C7 | Followups reason list (`initial_family_reasons_v1`; once inside that function, twice in `followups.sql` because `source_mutation_reasons_v1` keeps it) | ` if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then\n  reasons:=reasons\|\|jsonb_build_array('CREDIT_APPLIED_TO_INVOICE');end if;\n` | Remove it from the return reasons only. Edit retur, Benerin nota and payment reasons keep it | Side by side |
| C8 | Native-empty direct route (`native-empty/02_native_empty_callbacks.sql:38-39`) | `…event_kind='APPLY'and target_sale_id=p_sale)then\n  raise exception 'CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED'` | **Keep** (direct Native writer route only, `native_empty_is_direct_v1`). CP7 returns go through the coordinator. Listed so it is not loosened by accident | Identical |
| C9 | Screen (`src/lib/creditRefusalMessages.ts`) | — | Name `CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED` ("pemakaian saldo ini tidak bisa dibatalkan atau ditambah karena retur pada invoice tujuan bergantung padanya; batalkan dulu retur itu…"). Stop showing "pernah dibayar memakai saldo kredit" as a reason for returns | Unit and DOM tests |

Still refused after C, with named reasons:
- payment correction on such an invoice (`payment_correction/transform.py:53,171`, `04_completion.sql:9`);
- source reversal of its payments or returns (`consumer/11_source_history.sql:14`, `CP7_CREDIT_SOURCE_INCOMING_HISTORY_ADAPTER_REQUIRED`);
- Edit retur and Benerin nota (D/E);
- slice A payment on an invoice that has its own return family (slice A admission returns false; it would be an overpayment anyway).

## Steps

1. `incoming_applied_v1` in a new private schema. Local check: equals the fixture's U sum, 0 without APPLY, negative undo
   included.
2. Counted substitutions C1–C7 and C9's server part over slice B, side by side in a local check. With U = 0 every
   change is the slice B value; C3b is checked against P11.
3. Native cases, the race, the screen text, pins, a probe pinned to the slice B Native6+Race1 original (once it passes),
   and the workflow.

## Cases (Native, on the consumer pair: target 500 with 80 credit applied)

| Case | Setup | Expected |
|---|---|---|
| `RETURN_ON_CREDIT_PAID_INVOICE_NO_CREDIT` | target not fully paid (P 0, U 80), return 50 | K = 0, no choice needed. After: E 80, AR 370, PARTIAL_PAID; no cohort |
| `RETURN_ON_CREDIT_PAID_INVOICE_CREDIT` | slice A pays 420 first (P 420, U 80), return 100 as CREDIT | K = 100. After: I 100, E 400, AR 0, PAID; the source invoice's credit is unchanged |
| `…_REFUND` | same, as REFUND | Cash −100 on the dated guard |
| `UNDO_REFUSED_WHEN_RETURN_DEPENDS` | after the CREDIT case, UNDO the 80 APPLY | Refused `CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED`, no effect (the oracle that already exists) |
| `UNDO_ALLOWED_WHEN_RETURN_EMPTY` | after the K = 0 case, UNDO | Accepted. E 0, AR 450; the target's EMPTY family stays empty |
| `SECOND_RETURN_ON_CREDIT_PAID_INVOICE` | slice B on the target | Family 2 target with U included |
| `PROTECTED_REFUSALS_IDENTICAL` | payment correction, Edit retur, Benerin nota on the target; source payment reversal; P11 return without choice | Same code, message and detail side by side. P11 is identical when U = 0 |

**Race** (read the settle and consumer paths for the first-hit code before writing the oracle):
- **Return on the target vs UNDO of its credit.** Both serialize on the FG lock.
  - Return first: the UNDO is refused, either by the dependency check above or by the consumer's stale review.
  - UNDO first: the return is refused `CP7_SALES_REVIEW_CHANGED`. The UNDO rewrites the header status, and the review token hashes the header.
  - Either way, no partial state.

## Oracles that must not be loosened

- `CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED`, `CP7_CREDIT_CONSUMER_FINAL_JOINT_CAPACITY_NEGATIVE`, and every
  consumer capacity and target-correction refusal.
- P11 (a return without a settlement choice on an overpaid invoice) stays refused.
- `CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED` on the direct route.
- The incoming-history adapter refusal on source reversals.
- All slice A, B, followups and OW04 cases and races, unchanged. With U = 0 every C substitution must give slice B's
  value (local side-by-side).

## Size

About 10–16 writer hours and 2–4 Native CI runs, plus one browser run for the new screen text. That is smaller than B,
because the funding vector, the dependency refusal and the multi-family proofs already exist. The main risks are:
- C3b (an ordinary return with U), which needs a careful side-by-side against P11;
- the race's first-hit codes.
