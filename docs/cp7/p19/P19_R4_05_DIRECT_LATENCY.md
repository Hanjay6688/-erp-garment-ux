# P19 R4-05: direct analysis latency (owner D17-1)

Sol r3 handed over KNOWN-P19-DIRECT-LATENCY (run 39146762696): "Ambil analisis ERP terbaru" took 6.3-8.0 s at 300
targets, and with financial figures 7.4-8.0 s at 100 targets (two of three clicks stopped by the unchanged 8 s limit).
Owner D17-1: do it now, in r4. Nothing below raises a limit, samples, cuts or caches a source; the 8 s statement limit,
the 8,000,000-byte single body bound and every exact check stay as they were. The 3 s heavy-complete target is reported
as measured and is not marked met where it is not.

## Diagnosis (measured, not guessed)

The phase profile of the scale suite (one call per layer) put the 100-target capture with figures at about 2.1 s while
the real capture took 6.1 s, so it could not say where the time went. A labelled diagnostic was added to the scale SQL
ladder (`capture_diagnosis` in `scripts/cp7_p19_scale_cases.py`, sizes 100 and 300, rolled back, never application
latency): one direct capture per finance mode with `track_functions=all` for that call only, each function's own and
total time from the transaction's counters (deltas), and the capture with figures once more with JIT off. A dispatch-only
workflow runs the scale suite at those two sizes (`.github/workflows/claude-p19-capture-diagnosis.yml`).

CI run 39157467151 (writer branch, 100 and 300 targets):

| Call | Server time | Where it went |
|---|---|---|
| Without figures, 100 targets | 1.03 s | analysis compiler (build 0.83 s) |
| With figures, 100 targets | 6.32 s | owner report read twice (capture, then the delivery re-check of `serve`), 2.6 s each; inside it `erp.require_internal()` called 32,150 times: 3.9 s own time |
| With figures, 100 targets, JIT off | 6.09 s | the same (JIT is not the cause) |
| Without figures, 300 targets | 3.08 s | analysis compiler (build 2.30 s, netting 1.41 s) |
| With figures, 300 targets | stopped at 8 s | owner report 5.6 s for the first read alone; `erp.require_internal()` 34,733 calls, 4.2 s |

Browser (same run): without figures 100 targets 1.55-2.01 s; 300 targets 5.6-7.4 s, of which about 26.5 MB is sent: the
12.5 MB result in the capture reply (above the 8 MB single-body bound, so the panel discards it) and again as seven
segments. With figures 100 targets 5.6-7.5 s; 300 targets refused by the 8 s limit.

`erp.require_internal()` is the Native internal-role guard; the protected owner report calls it once per checked row
(`erp.account_id`). The CP7 stack had grown it to one query per private command context table (ten tables), about
100 us per call.

## Changes

1. **The guard answers the common case with one probe** (`scripts/cp7_internal_guard_bundle.py`, last delta of the F03
   stack; CP17 R4-05). Every branch before the final role test can only admit, and only through a row of this backend
   and transaction (its identity filters are repeated inside its CASE). Without such a row the answer is the final
   role test alone: a transaction without a transaction id has written none; otherwise one probe of the same ten
   tables with the same identity filters decides. With any row the unchanged dispatch runs, every check and fine refusal
   in place. `verify()` proves the dispatch shape and that the probe reads exactly its tables; CP17 Native cases call the
   old and new guard side by side for eight callers and require equal answers, and a guard whose dispatch the probe no
   longer stands for fails the review. Writer-local PG16 (stub tables): 27 callers equal; 89-103 us per call before, 29 us
   without a transaction id and 45 us with one after.
2. **The panel states its start clock at once** ("Sedang dihitung sejak jam ... WIB" was shown only after a 3 s timer;
   Sol measured it at 3003-3015 ms).

## Considered and not done

- **Skip `serve`'s re-read at the end of a capture.** It would save one full source read (with figures, the owner
  report again), but the reply would then say "UNCHANGED" as of the capture statement instead of at delivery; a commit
  that lands while the capture computes would no longer be reported at once. Kept as is.
- **Return a small envelope instead of an oversized result from the capture** (avoids sending 12.5 MB twice at 300
  targets). A contract change of `cp7.native-analysis-run.v1` across the panel, transport cases and browser checks; the
  gain (about 1-1.5 s at 300 targets) would not reach 3 s, because the compiler alone needs about 3 s there.
- **Route captures with figures to the background job.** About ten browser suites assert the direct full capture path;
  the guard fix removes the 8 s stops instead.

## Result after the change

To be filled from the CI rerun of the capture diagnosis on the writer branch (see the handoff checkpoint log).

## Still open

- 300 targets without figures stays above 3 s (compiler about 3 s server time, 12.5 MB result); the background job and
  the staged analysis remain the owner-named exceptions for heavy scopes (`P19_PLANNING_ANALYSIS_BACKGROUND_20261007`,
  `P19_PLANNING_ANALYSIS_STAGED_20261007`).
- The owner report itself (Native) is read twice per capture with figures; its own cost grows with the books.
- `owner_latency_acceptance: false`, `production_go: false`.
