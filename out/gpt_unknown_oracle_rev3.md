# Unknown read/recovery — diagnostic revision3

## Unknown rev2 completed; parser/recovery verification prepared

Run36102938451/job107969167045: **2INCOMPLETE**. Both initial reads were deliberately dropped once; UI rendered four0KPIs, showed connection error and kept writes locked. Real Auth control had20Laundry-outside /10QC-ready. After removing the fault, responseHTTP200/readiness true arrived, but UI still0 and generic connection error. Removing unused fixture SKU did not resolve this. Cleanup:2Authusers removed, counts restored, console0, browserDB0, clone0, primary unchanged. Full observed data in `out/gpt_unknown_run_36102938451.json`, logSHA256ccea00466d4cdc7cff91829208a6d66211001f2090099ee3799f85e4ba9a8163.

Next revision holds fixture/data/unknown oracle fixed and runs the exact candidate's pure `parseLaundryQcWorkspace` against the real response (transpilation only, sourcehash printed, no source patch). If parser accepts but refetch fails, a fresh real browser page must render the same data before classifying a product recovery failure. Otherwise preserve INCOMPLETE and capture full response/parser diagnostic. Earlier results are not relabelled. Browser SHA2563821aec1d0f0df0d32bc131c0721a32bf41344dc1116568058087d33768d72df, `audit/scenarios/unknown_round8/MANIFEST_rev3.json`; two cases only. Source notes `out/gpt_unknown_oracle_rev3.md`.

LANGKAH BERIKUTNYA: capture new run/job, read two cases and cleanup, identify parser/setup vs UI state cause. Then update existing CP6-06 and final handoff at supported scope. CP6 HOLD.


This does not replace the original M3825 oracle. Initial unavailable data must not be asserted as zero. The full healthy-control requirement is strengthened by pure-parser and fresh-browser checks. A failed control remains INCOMPLETE unless the exact same unchanged data renders in a fresh actual UI session, proving data/transport are usable. No guard is disabled or function replaced.
