# Verification: CP6-07 (initial-import advance/prepayment, backdated refund vs. correction)

## Claim
Opening advance 67.25 (original 100, settled-before-cutover 32.75). A CORRECTION +32.75
dated later (D-2) and a REFUND 100 dated earlier (D-4, "backdated, before the correction")
are both accepted through the public import RPC action `PREPAYMENT`. Result: the dedicated
advance account reads -32.75 on the dated prefix between refund_day and correction_day, while
bank moves +100 on the refund date. Ordered control (correction-then-refund) passes. Claimed
oracle: Master lines 629-646 + 3816-3820 ("Backdate tidak boleh merusak prefix qty/value pada
timeline"). Proposed priority P1.

## Refutation attempts

### (A) CODE

Evidence file: `.../audit/runs_fable/auditor_native15_36065350201.json`, cases index
15-20 (`BCR1-ADVANCE-{SUPPLIER,CUSTOMER,VENDOR}-{ORDERED_CONTROL,DATED_CAPACITY}`).
Scenario source: `.../audit/scenarios/business_scenarios_reconstructed.py:150-234`.

1. **The guard is real and is a current-balance guard, not a bypassed one.**
   `supabase/migrations/20260922135615_..._connected_import_materials.sql:1323,1349-1350`:
   `v_state:=erp.initial_prepayment_state_v1(a.id); ... if (v_state->>'remaining_amount')::numeric+v_delta<0 then raise exception 'Perubahan melebihi sisa uang muka; batalkan pemakaian dahulu';`.
   `initial_prepayment_state_v1` (line 1059-1071) sums `delta` over **all** CORRECTION/REFUND
   events with no `effective_date` filter — a pure current/cumulative state, by design.
   Confirms lens-A premise: acceptance is a "current balance now" check, not a dated one.

2. **The refund is only accepted because the correction was already recorded — in real
   submission order, correction is always submitted before refund.** In
   `business_scenarios_reconstructed.py:157-166` the `PREPAYMENT/CORRECT` RPC call is made
   *first*, unconditionally, regardless of the `backdated` flag; the `PREPAYMENT/REFUND` call
   is made *second* (line 166-176). The only thing `backdated` changes is which
   `effective_date` string is attached to each call (`correction_day`/`refund_day` swap,
   lines 155-156). So at the moment the refund is validated, current `remaining_amount` is
   already 100.00 (67.25+32.75) regardless of scenario; `100-100=0` passes the guard cleanly.
   The guard is never literally violated at call time in either case — refuting the framing
   that a negative-capacity refund is "accepted" by a weak/missing check. What's negative is
   a *later, date-filtered reconstruction* of the ledger (`asof()` in the scenario, reading
   `erp.account_daily_balances where balance_date<=day`), not anything the guard evaluated.

3. **Is a raw refund of 100 against an as-of balance of 67.25, with no correction at all,
   refused?** Yes — by the same guard: `state.remaining_amount(67.25) + (-100) = -32.75 < 0`
   → `raise exception`. So the product does enforce non-negative *current* capacity; it does
   not (and by design does not) enforce non-negative capacity *as of every date the way a
   dated ledger read would show it* when a later-effective-dated correction is submitted
   first. This is a coherent, narrower gap than "no guard at all."

4. **Does the product's own reader ever expose the negative dated value?** No UI/report
   path found. `src/ConnectedInitialImportPage.tsx:155-170` (`PrepaymentBalances`) only
   renders `remaining_amount` (current state), never a dated/as-of balance. Repo-wide grep
   for `account_daily_balances` in `src/**/*.ts(x)` → no hits; grep for
   `neraca|trial_balance|general_ledger|financial_statement` in `src/**` → no hits. There is
   currently no trial-balance / GL-as-of-date / financial-statement feature in the product
   that would surface this negative prefix to a real user. The only place it is visible is a
   direct SQL query against `erp.account_daily_balances`, which is exactly what the audit
   scenario's own `asof()` helper does (line 114-119) — i.e. the negative value is a raw
   ledger-table artifact, not something the product currently shows anyone.

5. **Realistic actor/path?** REFUND/CORRECT on an initial-import advance are owner/admin-only
   actions per Master line 631 ("Owner/admin dapat ... mengembalikan kas, mengoreksi
   opening ... dengan alasan wajib"), so the actor is plausible. But per the case's own
   `scope` field, this is "Public native import RPC with ordinary authenticated actor; no
   HTTP/UI proof" — no browser/HTTP path was exercised, only a direct native RPC call with
   savepoints; this is consistent with the file's other native-only caveats, not a unique
   weakness of this one finding.

### (B) CONTRACT

`ERP_V3_2_Master_Pulih_20260923.md:615-660` (lines 629-646 area): describes the advance
lifecycle and states the capacity rule in **current-state** terms only: "Setelah 75,00
dipakai, koreksi/reversal yang membuat kapasitas kurang ditolak" (line 646) — matches
exactly what the code enforces (item A.1/A.3 above). No sentence in 615-660 requires that a
per-date/as-of reconstruction of the advance balance stay non-negative.

`ERP_V3_2_Master_Pulih_20260923.md:3816-3820`: "Backdate tidak boleh merusak prefix
qty/value pada timeline" is a **general, cross-domain** architecture bullet inside "3.
Invariant proyek yang tidak berubah," stated alongside stock/qty language ("prefix
qty/value"), not an advance/money-specific requirement. Applying it to prepayment capacity is
the auditor's own inference — and the scenario code says so explicitly:
`business_scenarios_reconstructed.py:180-182,187`: *"The reviewed contract specifies
capacity/invariant but no exact refusal ... Dated-capacity refusal needs an exact
contract/product oracle; arbitrary SQL refusal is not PASS"* and the JSON's own
`oracle_inference` field: *"Dated-prefix rule applied to monetary advance capacity; exact
refusal remains unspecified."* This is the audit's own admission that no exact contract
oracle mandates refusal in this scenario — materially undercutting "Claimed contract oracle"
framing as settled.

**Decisive precedent inside the same contract, for the identical issue-shape:** section
"S04 — Backdate perlu validasi saldo historis per lokasi, bukan hanya saldo terkini"
(`ERP_V3_2_Master_Pulih_20260923.md:6008-6021`) is the *stock-quantity* twin of this exact
pattern: "current sufficient, but a later-effective-dated correction submitted out of order
makes an earlier-dated historical prefix negative." The contract's own audit register
classifies this pattern as:
- **Prioritas: P2 sementara** (line 6008: "S04 ... Prioritas: P2 sementara"),
- **Bukti: STATIC_RUNTIME_TEST_REQUIRED**, status **"Hipotesis"** (lines 3857, 6008),
- explicit note that "Current negative-stock guard nyata ada" (the current-balance guard
  genuinely exists; only the historical/dated view is unguarded) — mirroring item A.1 above,
- and requires an **explicit owner policy decision** before being treated as a fail-closed
  requirement: "Backdate yang sah tidak boleh membuat source-location mempunyai saldo
  historis negatif **tanpa kebijakan yang eksplisit**" (line 6015, emphasis mine).

Additionally, the whole "as-of / historical restatement" topic is carried project-wide as an
open HOLD, not a settled MUST: AUD-B04 ("Laporan historis READY walau per-date biaya belum
konsisten... 12 observasi tanggal masih HOLD", line 3823/3866) and repeated statements that
"CP6/date acceptance tetap HOLD" (lines 5100, 6148, 6350) and "Tanggal akuntansi/restatement
open-period masih AUD-B04/keputusan proyek" (line 4216).

CP6-07's cited oracle (629-646, 3816-3820) omits this directly on-point precedent
(AUD-S04, 6008-6021) that the same document uses to prioritize and qualify this exact class
of issue. Given that the contract's own audit register treats the mechanically identical
pattern (current-balance guard present, historical/dated prefix unguarded, pending owner
policy) as P2-provisional/hypothesis for stock, there is no textual basis in the contract for
treating the money/prepayment instance as a settled P1 "must never happen" violation.

## Residual doubts
- CP6-07's evidence is a genuine native DB reproduction (concrete negative observed value,
  `exact_replay: true`, `source_immutable: true`), which is *stronger* evidence than AUD-S04's
  purely static/hypothesis-level evidence — so CP6-07 is not weaker on reproducibility, only
  on priority/oracle-exactness and on real-world exposure (no reader surfaces it today).
- It is possible a future GL/trial-balance/"as of date" report (not yet built) would inherit
  this exact misstatement risk once built on `account_daily_balances`; that is a legitimate
  forward-looking risk, consistent with how AUD-S04/AUD-B04 are already framed (design
  question to resolve before such reports are trusted), but it is not evidence of *current*
  user-facing financial misstatement.
- Whether "D-4..D-3" is meant as a continuous date range or is inferred from a single sampled
  day (`2026-09-21`, the only day the JSON shows advance=-32.75) is not fully resolvable from
  the JSON alone (only 4 discrete dates are sampled), though it is a reasonable inference from
  economic_date semantics.

## Verdict: PARTIALLY_REFUTED

The core technical observation is CONFIRMED by code inspection: `initial_prepayment_state_v1`
/ the CORRECT/REFUND guard is a non-dated, current-cumulative check (`supabase/migrations/
20260922135615_..._connected_import_materials.sql:1059-1071,1323,1349-1350`), so a
correction whose `effective_date` is later than an already-submitted refund's
`effective_date` can make a date-filtered read of `erp.account_daily_balances` (or the
audit's `asof()` helper) show a negative advance balance for the dates between them. This
matches cases `BCR1-ADVANCE-*-DATED_CAPACITY` (status `COUNTEREXAMPLE`) in
`auditor_native15_36065350201.json`.

However, the finding's characterization as a settled, contract-mandated **P1** defect is
REFUTED on two independent grounds:
1. **No exact contract oracle** — the cited lines (629-646) describe and match a
   current-capacity rule that the code correctly implements; line 3816-3820 is a general,
   non-advance-specific principle whose application here is admitted by the audit's own
   scenario code to be an inference without "an exact refusal oracle."
2. **Contract precedent for the identical issue-shape sets P2/hypothesis, not P1** — Master
   §S04 (lines 6008-6021) is the same pattern in the stock domain and is explicitly scored
   "Prioritas: P2 sementara," "Hipotesis," pending "kebijakan yang eksplisit" from the owner,
   while separately noting the current-state guard genuinely exists. The broader as-of/date
   policy question is tracked project-wide as HOLD (AUD-B04).
3. Additionally, no current product reader (`PrepaymentBalances` UI, or any GL/trial-balance
   feature) exposes the negative dated value to a real user today, so the "financial
   mis-statement in dated reports" impact used to justify P1 is not yet demonstrated in the
   live product surface — it is a latent data-layer property, same class of latency as
   AUD-S04.

**Recommended disposition:** keep as a valid finding (downgrade from "product defect" framing
to "confirmed dated-capacity gap, same class as AUD-S04"), but **re-prioritize to P2** and
cross-reference AUD-S04/AUD-B04 rather than treating it as an isolated new P1 contract
violation of 629-646/3816-3820.
