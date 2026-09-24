# Adversarial verification: CP6-09 / F1-12

## Claim

A second import batch (FINALIZE) that re-declares the same opening stock item
(same `material_sku`+`location_code`, or `product_sku`+`location`, same or
earlier cutover) is POSTED again, doubling opening stock/value. The AR
cross-route overlap guard's predicate
`(h.migration_batch_id is null)<>(oh.migration_batch_id is null)` only fires
when exactly one side is a legacy header (`migration_batch_id is null`) and
the other is an import header — so import-vs-import is never compared. Also
holds under real two-session concurrency.

## Refutation attempts

### A. CODE lens

1. **Predicate confirmed as described.** Read
   `cand/supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql:372`:
   `and ((h.migration_batch_id is null)<>(oh.migration_batch_id is null))`
   inside the `AR_OPENING_ROUTE_OVERLAP` check (raised at line 402). This is a
   boolean XOR: true only when one header is legacy (`migration_batch_id
   null`) and the other is import-sourced (`migration_batch_id` not null).
   Two import headers both have non-null `migration_batch_id` → XOR is always
   false → the whole overlap subquery excludes that row → **no exception**,
   confirming the mechanism claimed.

2. **No compensating unique index / document-identity registry for opening
   MATERIAL/FINISHED_GOODS.** Grepped
   `20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql` for
   `unique`: found `initial_import_receipt_identity`
   (supplier_id+receipt_number), `initial_import_financial_document_key`,
   `initial_import_prepayment_document` (party+document_number) — i.e. the
   codebase *does* have the "document identity" pattern for other import
   types (receipts, financial docs, prepayments) — but there is no analogous
   unique key on `opening_balance_items` for MATERIAL (material_id,
   location_id) or FINISHED_GOODS (product_id, location_id, grade). This
   supports that the gap is a real asymmetry in the codebase, not merely
   theoretical.

3. **"Different roll/lot" defense checked and fails for this scenario.** The
   overlap-suppressing SQL predicate for MATERIAL already carries roll
   identity (`i.roll_id is null or o.roll_id is null or i.roll_id=o.roll_id`)
   and FABRIC materials are further protected earlier in the same function
   (`AE_OPENING_ROLL_ALREADY_POSTED`, roll status/qty checks, lines ~340-354).
   But the probe (`cand/scripts/cp6_opening_overlap_probe.py:42-46`) and the
   `open_2.py`/`xaudit_5.py` scenarios use `material_type='OTHER'`
   (non-fabric, roll-less), so there is *no* lot/roll identity to distinguish
   the two batches — the only identity is `material_id`+`location_id`, and
   `open_2.py`'s `second_batch()` (line 36-43) reuses the *same* `tag` string
   as both `material_sku` and `location_code` from the first import — it does
   **not** re-upload MATERIAL/LOCATION master rows, so FINALIZE resolves the
   *same* `material_id`/`location_id` rows in the DB. This is not a fixture
   artifact representing a "different roll/lot" — it is literally the same
   row by every identity dimension the schema tracks. Same reasoning applies
   to FG (doc `cp6-ar-opening-overlap.md:55` states FG identity is
   product+warehouse+grade only — no per-unit lot key at the opening layer).

4. **Ledger delta is genuinely attributable to the second batch, not
   vacuous.** `open_2.py`'s `cross_batch()` computes `delta(before,after)`
   from full `ledger()` snapshots taken immediately before/after the single
   `second_batch()` call — a real dict diff, not a placeholder. Evidence:
   `OPEN2:MATERIAL_SECOND_BATCH_SAME_CUTOVER` → `ledger_delta_second:
   {"MATERIAL_INVENTORY": "15.75"}`, `posted_items_before: {items:1,
   qty:7.000000, posted_headers:1}` → `posted_items_after: {items:2,
   qty:14.000000, posted_headers:2}`. Same for
   `MATERIAL_SECOND_BATCH_EARLIER_CUTOVER` (cutover -2d) and
   `FG_SECOND_BATCH_SAME_CUTOVER` (`FG_INVENTORY +15.75`). Note:
   `open_1.py`'s `import_twice()` case has a **vacuous** check
   (`ledger_unchanged_by_second=before==after or (err is None and second is
   not None)` — the `or` clause is trivially true because the *first* probe
   call inside that test always succeeds) — this one sub-case's
   "ledger_unchanged" flag is not meaningful evidence either way, but it does
   not undermine `open_2.py`'s non-vacuous deltas, which are the load-bearing
   evidence.

5. **Concurrency race confirmed independently.** `xaudit_5.py`
   `r1_import_overlap` (real `tools.two_sessions`, holder commits then
   worker proceeds) → `auditor_xaudit5_36065517737.json`,
   `XA5:R1_TWO_SESSIONS_SECOND_IMPORT_BATCH_SAME_ITEM`: `contention.kind =
   BLOCKED, holder_blocks_worker = true`, worker still returns `status:
   POSTED`, `posted_items_for_location: 3, posted_qty: "21.000000"` (3×7).
   `checks.no_further_posted_beyond_first = false`. This independently
   confirms the defect is not merely a sequential-savepoint testing artifact
   — it reproduces under real transactional concurrency with the advisory
   lock (`FG_HPP_SALES_V2620C`) held/released exactly as the AR doc describes
   (`cp6-ar-opening-overlap.md:64-67`).

6. **Selective, not systemic, absence of guarding — rules out "test used the
   wrong RPC".** Same-batch FINALIZE replay (re-FINALIZE the identical
   `batch_id`) **is** correctly refused: `OPEN2:MATERIAL_SAME_BATCH_FINALIZE_REPLAY`
   → `PASS`, refusal message `"Impor yang sudah disahkan tidak dapat diedit
   atau disahkan ulang dengan permintaan baru"`. This shows the system has a
   working idempotency/replay guard at the *header* level, and the counter-
   example specifically targets the *new-batch-id, same-item* path that
   guard does not cover — exactly the mechanism the finding describes, not a
   confusion between "replay" and "duplicate".

**A-lens verdict: refutation FAILED.** The code inspection reproduces the
exact predicate/line cited, confirms no alternate guard (unique index,
document identity) exists for non-roll MATERIAL/FG opening items, and the
scenario fixtures are not distinguishable "different physical stock" by any
dimension the schema tracks.

### B. CONTRACT lens

1. Master doc line 138 (`pack/kontrak/ERP_V3_2_Master_Pulih_20260923.md:138`):
   "*Berikutnya: buktikan perlindungan tumpang tindih saldo awal pada semua
   jalur lama*" — literally "prove opening-balance overlap protection across
   all **old/legacy** routes" (finding's paraphrase drops "lama"/legacy,
   slightly broadening the quote — a minor citation looseness, not
   materially misleading since the AR guard *was* scoped to legacy-vs-import
   and that scope is exactly what line 138 asked for and got).

2. Master doc line 1043: "*... identitas dokumen lintas batch dan tumpang
   tindih saldo awal vs dokumen operasional masih perlu kontrak/tes*" —
   explicitly says cross-batch document identity **"still needs
   contract/tests"** — i.e. the master itself discloses this as an **open,
   unresolved item**, not a broken passed acceptance criterion.

3. **Smoking-gun scope admission in the candidate's own docs**:
   `cand/docs/cp6-ar-opening-overlap.md:59-62`: "*The inherited import
   registry still governs separate source documents and lots. **AR does not
   claim to detect duplicate legacy-only records or every duplicate import
   source across batches.** A different warehouse, roll, product/size,
   party, or non-overlapping production position must remain admissible.*"
   This is an explicit, written statement by the AR author that import-vs-
   import duplicate detection is **out of scope** for this migration and
   was never claimed as fixed. Combined with `cp6-ar-opening-overlap.md:101-103`:
   "*CP6 remains HOLD. `production_go: false` ... Independent acceptance
   ... remain pending.*"

4. Control-total oracle (lines ~44-46, confirmed by `grep`): "*Impor harus
   membukukan isi draft terakhir, mencocokkan rincian dengan total kontrol,
   dan tidak membukukan total kontrol sebagai transaksi*" — this governs the
   *within-batch* control-total match, not cross-batch dedup; it is not
   directly violated by this finding (that's really the separate
   `CONTROL_TOTAL_MISMATCH_AND_NOT_POSTED` case, which PASSed in evidence).
   The finding cites it as supporting context for "control totals exist as a
   quality bar," which is fair but not itself violated here.

5. Line 10, confirmed verbatim: "*Keuangan—termasuk laporan—stok, dan HPP
   adalah raja*" ("Finance—including reports—stock and HPP are king") is a
   general business-priority statement, legitimately invoked as the
   materiality justification (doubled stock/value is exactly the kind of
   defect this principle prioritizes), not a specific technical requirement
   that was tested pass/fail.

**B-lens verdict: partial refutation of framing, not of substance.** The
contract does **not** establish this as a violated, already-passed
acceptance gate — the candidate's own documentation explicitly discloses
import-vs-import dedup as unimplemented/out-of-scope and keeps `CP6 HOLD` /
`production_go: false` pending exactly this kind of gap. So this is more
accurately a **confirmed, reproducible manifestation of a known, disclosed,
still-open gap that blocks go-live**, not a silent regression against a
signed-off requirement. The finding's own oracle citation (M:1043 "masih
perlu kontrak/tes") already reflects this nuance honestly — it does not
claim the contract was violated outright, only that protection is
incomplete and the concrete impact (doubling) is now quantified.

## Residual doubts

- `open_1.py`'s `OPEN:IMPORT_SAME_MATERIAL_TWICE` case has a vacuous
  `ledger_unchanged_by_second` check (OR-bug); not used as load-bearing
  evidence here since `open_2.py` supplies non-vacuous deltas.
- The `xaudit_5.py` R1 race shows `posted_items_for_location: 3` rather than
  the "1→2" cardinality quoted in the finding for the sequential cases; this
  is explained by that scenario's own `r1_import_overlap` calling
  `ovp.imported` once (baseline) before the two racing sessions each add one
  more (3 total), not a discrepancy in the underlying defect — still >1
  POSTED header for the same material+location, confirming `checks.
  no_further_posted_beyond_first = false`.
- Whether this specific counterexample was already known to the CP6 team
  (very likely, given `cp6-ar-opening-overlap.md`'s explicit disclosure) is
  relevant to *priority/urgency* framing but not to *whether the defect is
  real*.
- Did not independently re-execute SQL against a live DB (read-only
  verification per task constraints); relied on static code reading plus the
  three supplied JSON evidence artifacts, which are internally consistent
  (matching qty/amount/header-count arithmetic) and cross-corroborate each
  other (sequential same-cutover, sequential earlier-cutover, real
  concurrency) across three independent scenario scripts.

## Verdict: CONFIRMED

One-paragraph justification: Static reading of
`20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql:372` confirms the XOR
predicate exactly as cited, and shows no other guard (unique index, roll/lot
identity, document registry) exists for non-roll MATERIAL or FINISHED_GOODS
opening items that could distinguish a genuine second physical source from an
accidental re-import of the same material_sku+location_code; the three
evidence files (`auditor_open2_36045629594.json` sequential same/earlier
cutover, `auditor_xaudit5_36065517737.json` real two-session race) give
non-vacuous, mutually consistent proof — posted headers 1→2, qty 7→14, ledger
delta exactly +15.75 on MATERIAL_INVENTORY/FG_INVENTORY — while the adjacent
same-batch replay guard is shown working correctly, isolating the gap
precisely to new-batch/same-item. The contract lens tempers the framing
(the candidate's own `docs/cp6-ar-opening-overlap.md` explicitly discloses
that import-vs-import dedup is out of scope for AR and keeps
`production_go: false`/CP6 HOLD pending this exact class of gap), so this is
best read as a confirmed, quantified, high-materiality instance of an
already-flagged open risk rather than a surprise regression against a passed
gate — but the underlying technical claim of double-posting/double-value is
fully verified and not an artifact of the test fixtures or scenario tooling.

**Recommended priority: P1** (blocking for `production_go=true`/CP6 exit from
HOLD). Rationale: it directly doubles a core financial/stock quantity
("stok, HPP adalah raja" — Master line 10) with zero refusal signal to the
operator, reproduces under real concurrent sessions (not just sequential
misuse), and is trivially triggerable by an operator re-running or
re-uploading an import file. It should gate CP6 exit from HOLD even though
it is already a known/disclosed gap and no live production system is
currently exposed.
