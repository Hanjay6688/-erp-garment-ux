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

Same harness and seeding, CI run 39159625311 at `27f04d72` against run 39157467151 at `e482ccdd` (before). The second
runner was faster: the capture without figures, which makes no guard calls, took 0.66 s server time against 1.03 s. The
like-for-like measure is the guard's own time per call at an equal call count: **121 us before, 22 us after (32,150
calls at 100 targets in both)**.

| Click to result rendered (browser, 3 history windows) | Before | After |
|---|---|---|
| 100 targets, without figures | 1.55-2.01 s | 1.03-1.35 s |
| 100 targets, with figures | 5.58-7.53 s | **2.30-2.60 s** |
| 300 targets, without figures | 5.57-7.43 s | 3.83-5.04 s |
| 300 targets, with figures | 3 of 3 stopped at 8 s | 2 of 3 complete (10.6-11.5 s, result over 8 MB so read as segments), 1 stopped at 8 s (100 days) |

| One direct capture, server (diagnostic) | Before | After |
|---|---|---|
| 100 targets, without figures | 1.03 s | 0.66 s |
| 100 targets, with figures | 6.32 s (guard 3.9 s own) | 2.17 s (guard 0.71 s own) |
| 300 targets, without figures | 3.08 s | 2.01 s |
| 300 targets, with figures | stopped at 8 s | 6.64 s (guard 98,200 calls, 2.19 s own) |

SQL ladder (same run, every point an accepted verdict): the direct capture with figures at 100 targets 2.05-2.61 s
(before 6.14-6.63 s); at 300 targets it now completes in 6.36-7.60 s (before refused at 8 s in all three windows); the
background job with figures at 300 targets completes in 4.37-5.64 s plus 2.13-2.24 s for manifest and segments (before
refused at 8 s). Log kept: `scratchpad/p19diag/run2.json` (writer).

With figures, the work grows with the books, not with the targets alone: the owner report checks every journal line (at
300 targets 1,530 lines and about 49,000 guard calls per report read, against 521 lines and 16,000 at 100) and is read
twice per direct capture.

## Qualification run (candidate 663f6fae)

CI run 39173212515, job p19-scale5 (job 117810437470), against the r3 qualification at `b53b5acd` (run 39035969434, job
117405683384, before R4-05). Same harness and seeding; each run gets whatever runner GitHub assigns. The r4 qualification
runner was slower: the paths the guard change barely touches took longer than in r3 (capture without figures, which
makes no guard calls, and the staged pages at 100 targets: 1.61-1.93 s against 0.94-1.13 s).

| Click to result rendered (browser, 3 history windows) | r3 qualification `b53b5acd` | r4 qualification `663f6fae` |
|---|---|---|
| 100 targets, without figures | 0.98-1.37 s | 1.78-2.19 s |
| 100 targets, with figures | 4.16-4.62 s | 4.57-5.92 s |
| 300 targets, without figures | 3.70-4.50 s | 6.23-8.14 s |
| 300 targets, with figures | 3 of 3 stopped at 8 s | 3 of 3 stopped at 8 s |

With figures over without figures at 100 targets: r3 4.2-4.6 times, r4 2.5-2.7 times. Diagnostic in the same run: with
figures at 100 targets 4.56 s server; `erp.require_internal()` 32,150 calls, 1.64 s own (51 us per call), while
`erp.current_app_role()` took 16 us per call on this runner (12 us in run 39157467151, 7 us in run 39159625311). Guard
time per call over `current_app_role()` time per call: 9.9 before, 3.3 and 3.1 after. SQL ladder at 300 targets with
figures: the direct capture stopped at 8 s in all three windows; the background job completed for 1 and 30 days
(7.3 s and 7.9 s plus 3.7 s for manifest and segments) and stopped at 8 s for 100 days (it completed in all three in
r3 on the faster runner). Every scale case PASS (an honest stop at 8 s is an accepted verdict). Log kept:
`scratchpad/p19diag/run_q663.json` (writer).

## Still open

- 3 s is not reliably met with figures at 100 targets: 2.30-2.60 s in run 39159625311, 4.57-5.92 s on the slower
  qualification runner. Without figures 100 targets stays under 3 s on both runners (1.03-1.35 s, 1.78-2.19 s). It is
  not met at 300 targets (without figures 3.8-8.1 s: compiler about 2-3 s server time and a 12.5 MB result; with
  figures 10.6-11.5 s or the 8 s stop). The background job and the staged analysis remain the owner-named exceptions
  for heavy scopes (`P19_PLANNING_ANALYSIS_BACKGROUND_20261007`, `P19_PLANNING_ANALYSIS_STAGED_20261007`); with figures
  at 300 targets the background job completed in all three windows in run 39159625311 and for 1 and 30 days on the
  slower qualification runner, where the direct capture stopped at 8 s in all three. The staged analysis completed
  everywhere.
- The owner report itself (Native, CP6) checks every journal line and is read twice per direct capture with figures;
  its cost grows with the books, so the direct capture with figures will slow down as the books grow.
- `owner_latency_acceptance: false`, `production_go: false`.
