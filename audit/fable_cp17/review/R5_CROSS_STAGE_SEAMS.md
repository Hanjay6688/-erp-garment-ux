# R5 — Cross-stage seams on one final code (SKN-22) — PARTIAL (in progress)

Candidate `0b7049d9`, read-only checkout `scratchpad/frozen`. Label for every claim: **SOURCE_READ**.
Conventions as R1/R3/R4: `BOOT:N` = decompressed fixture `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz` (scratchpad `fable7/fixture.sql`);
`M/<stamp>` = `supabase/migrations/…`; `AC..BF` = `supabase/release/cp6-t3/…`; `CP7/<dir>/<file>` = `scripts/cp7-src/…`.
"Final" = last `create [or replace] function` in order fixture → migrations not re-shipped → AC..BF → cp7-src, plus the in-place
`pg_get_functiondef`+`replace` patches of M/20t (`:335-341`), M/20u (`:177-183`) and M/20ab (`:255-268`). Index: `scratchpad/fable7/r5/fnidx.py` (1874 functions).

(partial — sections A–D follow)
