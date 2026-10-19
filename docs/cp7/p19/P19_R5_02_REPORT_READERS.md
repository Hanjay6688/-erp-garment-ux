# P19 R5-02: direct analysis with financial figures (owner D17-2)

Owner D17-2 (19 Oct 2026): the auditors went first; the next writer task is the direct analysis with financial figures,
target 3 s. In the r4 retests the capture with figures at 100 targets took 4.25-4.66 s (Sol), 4.6 s SQL / 5.6 s browser
(Fable), 4.65 s (Astra), and 4.57-5.92 s in the browser on the r4 qualification runner (`P19_R4_05_DIRECT_LATENCY.md`).
Nothing below raises a limit, samples, cuts or caches a source; the 8 s statement limit, the 8,000,000-byte single body
bound, the delivery re-check of `serve` and every exact check stay as they were.

## Diagnosis (function counters, r4 qualification run 39173212515, 100 targets, with figures)

4.56 s server time. `erp.account_id(text)` 30,974 calls, 2.48 s with its guard (`erp.require_internal()` 32,150 calls,
`erp.current_app_role()` 32,170 calls). The owner report and the period readiness it carries run the Native check readers
(`run_v268`, `run_v267`, the HPP books, the opening and pocket checks); these compare every journal line with
`erp.account_id('<KEY>')` written inline in the filter, so the lookup and its guard ran once per row, and the report is
read twice per capture.

## Change (`scripts/cp7_report_accounts_bundle.py`, CP17 R5-02)

In eleven STABLE readers every literal `erp.account_id('<KEY>')` became `(select erp.account_id('<KEY>'))`: an
uncorrelated init plan that PostgreSQL evaluates once per query, when first needed. Same mapping row, same guard, same
numbers; writers untouched; calls with a non-literal key unchanged.

Found while testing locally (writer PG16, synthetic reader): the planner also evaluates an inline STABLE call with
constant arguments while it estimates, so the old text refuses a key that has no mapping even when no row reaches the
filter, while an init plan refuses only when a row needs the value. All 17 keys the readers use are core mappings
(`erp.expected_mapping_account_type`), which `erp.guard_accounting_mapping_semantics()` refuses to delete or rename, so the
install refuses unless every key is mapped; after that the two texts cannot be told apart. Locally: 66,008 calls -> 12,
same rows; the SQL rewrite equals the Python rewrite and the unwrap restores the original text.

Proof in CI: `CP17_R5_02_REPORT_READERS_SAME_ANSWER` runs each installed reader and the same reader without the change
side by side on the CP17 books (every product, PO, pocket period, opening settlement, sale journal/PO pair, three report
windows) and requires the same rows or the same refusal. Its first run (3b9817ae, CI 39209921715) passed with three
readers compared on no input, because the CP17 books hold no opening credit, pocket period or sale journal; the case now
builds those rows inside its rolled-back savepoint through the BB/BE probe paths (an opening import with three allowances
and a customer credit applied, a production import with its historical pocket period posted, a sale of an opening finished
good and its return) and fails when any reader never answers or one of those three never returns a value (best practice
E25i). `CP17_R5_02_REPORT_READERS_REVIEWED` refuses a reader with one more call, an unlisted key or already rewritten
text, the install refuses a changed reader, and a core mapping cannot be deleted. Install and uninstall go through the F03
originals like every other declared Native delta.

## Result (capture diagnosis run 39207392615 at 7ca9554e)

The runner is comparable to the r4 qualification runner: the capture without figures, which this change does not touch,
took 1.25 s server time against 1.16 s.

| Measure, 100 targets with figures | r4 qualification (before) | r5 (after) |
|---|---|---|
| One direct capture, server | 4.56 s | 2.28 s |
| `erp.require_internal()` calls | 32,150 | 3,652 |
| `erp.account_id(text)` calls | 30,974 | 2,476 |
| Click to result rendered (browser, 1/30/100 days) | 4.57-5.92 s | 2.87-3.32 s |
| SQL ladder, direct capture | 4.54-4.99 s | 2.40-2.91 s |

The 2,476 remaining lookups are four per call of the per-product HPP book (`compute_non_po_product_hpp_book_v2620f`, 588
calls): each call is its own query, so each evaluates its four init plans once.

300 targets with figures: the browser now completes for 1 and 30 days (10.3-10.8 s, result over 8 MB read as segments;
before, stopped at 8 s in all three windows) and is still stopped at 8 s for 100 days; the background job with figures
completes in all three windows (5.1-7.9 s plus manifest and segments).

## Still open

- 3 s with figures at 100 targets is close but not reliably met on this runner (2.87-3.32 s in the browser); not marked met.
- 300 targets stays above 3 s with and without figures; the background job and the staged analysis remain the owner-named
  exceptions for heavy scopes (`P19_PLANNING_ANALYSIS_BACKGROUND_20261007`, `P19_PLANNING_ANALYSIS_STAGED_20261007`).
- Considered and not done: caching the check readers between the three runs per report read (the readers would answer
  from one snapshot instead of three; a semantic change), and skipping the delivery re-check of `serve` (weakens the
  "unchanged at delivery" answer; see `P19_R4_05_DIRECT_LATENCY.md`).
- `owner_latency_acceptance: false`, `production_go: false`.
