# R9 browser revision2 — independent native run 36124300108

Run https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36124300108 ; trigger 8d153c46922d4227725734ecd051c5446f443a34 ; writer frozen head d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b. Manifest rev2 SHA256 f6e6f53121c59407df78169a5431df421b105f4de8a73d1eedd7e5e0262eccba pins every scenario and original dependency. Label AUDITOR_SCENARIO, phase after, four independent disposable DB clones, actual Auth login/browser/PostgREST.

| Job / artifact | Case | Status and independently observed effect |
|---|---|---|
| 108036762501 / 10859496906 | G8UI:RECOVERY:PATTERN_COMMIT_REPLY_LOST | PASS; first server commit confirmed; sameEnvelope=true, replayExact=true, rows after first=1 and retry=1. |
| 108036762501 / 10859496906 | G8UI:RECOVERY:ROLE_DUPLICATE_COMMIT_REPLY_LOST | PASS; first commit confirmed; sameEnvelope=true, replayExact=true, one role row after first and retry, role permission set intentionally empty. |
| 108036762474 / 10859807244 | G8UI:UNKNOWN:LAUNDRY_HEALTHY_CONTROL:rev5 | PASS; valid UUIDv4 fixture through real API/Auth/UI displays 20. |
| 108036762474 / 10859807244 | G8UI:UNKNOWN:LAUNDRY_INITIAL_READ:rev5 | PASS; failed read renders KPI `—`, note `belum diketahui · data belum termuat`, write locked; genuine HTTP200/parser refetch returns 20. |
| 108036762544 / 10858931303 | G8UI:UNKNOWN:QC_HEALTHY_CONTROL:rev6 | PASS; valid UUIDv4 fixture, real Auth/UI displays 10. |
| 108036762544 / 10858931303 | G8UI:UNKNOWN:QC_INITIAL_READ:rev6 | PASS; failed read renders KPI `—`, note `belum diketahui · data belum termuat`; genuine HTTP200/parser refetch returns 10. |
| 108036762327 / 10859326995 | G9UI:W11:PARSER_ERROR_VS_NETWORK | PASS; deliberately malformed inherited cp3 seed, actual Auth RPC 200, aborted request shows unreachable, answered 200 parser shows `ID Mandor bukan UUID valid.` |

GitHub run SUCCESS, all four jobs SUCCESS/RUN_COMPLETE, 7/7 planned cases PASS. For each job: `primary_unchanged=true`, `clone_remaining=0`, Auth counts before/after [0,0,0,0], cleanup failures [] and `Stopped supabase local development setup`. No hosted DB, legacy, product code, or production touched. Older browser rev1 run 36123487209 remains immutable: W10 INCOMPLETE selectors and W13 false COUNTEREXAMPLE due auditor wrapper. See `out/gpt_r9_browser_rev1_run.md`. Narrow targeted verification only; D06/75C6/22ALL/LAU-04 remain HOLD or UNVERIFIED; production_go=false.
