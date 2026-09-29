# P02 — actor facade and immutable source runs

Status: **T1 writer family PASS** at `735056db3b42cc7fc3999149b42e2cadac7b42b2`, [run 36505788525](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36505788525): **10 native + 4 concurrency + 2 real Auth/HTTP cases**. CP6 restoration and advisor gate passed. [Source-bound evidence](evidence/p02-facade/VERIFICATION.json) includes original before/after reports and exact input hashes. This development bundle is not independent acceptance, a release migration or an operator UI connection.

First run `36504059754` at `479d916`: native 5 PASS / 2 INCOMPLETE, races 2 PASS / 1 INCOMPLETE, real Auth/HTTP 2 PASS; CP6 restoration and advisor gate passed. Three incomplete cases share a FIXTURE_DEFECT: lowercase hex in a synthetic role code violates the existing uppercase role constraint. The fixture is corrected before requalification; no product rule or expected refusal is weakened.

## Contract

`erp_cp7_capture_snapshot_v1(root, request)` captures one exact physical root at the current statement cutoff. A repeated request from the same actor and root returns the same immutable run. Reusing the request for a different root refuses. A source page over 500, missing root, overlapping identity or HPP conflict refuses without persisting a partial run.

`erp_cp7_read_snapshot_v1(run, domain, cursor, limit)` serves up to 100 stored facts per page. The cursor binds run, domain and position. Source changes mark the archived run stale; they never rewrite its facts. The dependency vector hashes the captured source facts per domain. The six source domains remain explicitly bounded; this is not complete ERP/planner coverage.

The server requires an active mapped actor and current `master.product.view`, `production.wip.view`, `warehouse.stock.view`, and `sales.invoice.view` permissions. Financial facts additionally require `finance.hpp.view`. An operations run does not collect or store the cost domain; gaining finance access requires a new capture for that domain. Losing finance access redacts it from a previously financial run, including counts and hashes. Runs belong to their creator. Replay and pages recheck current access; service-role JWT and stale transaction isolation are refused.

## Persistence and principal

`cp7_private.analysis_runs` stores facts, manifest and domain hashes atomically through a single INSERT/SELECT with a STABLE source reader. Data is immutable and private. The NOLOGIN `cp7_capture` principal has SELECT on the explicit source tables, INSERT/SELECT on analysis runs and EXECUTE on named read helpers. It has no business-table DML or operational-writer grants. Public wrappers run as that principal with an empty search path.

Only current knowledge is supported. No historical AS_KNOWN reconstruction is claimed. Cutting yields remain UNBOUND_CANDIDATE; no net WIP, forecast or production action is computed. Lots with unavailable cost completeness remain UNKNOWN.

## Required native proof

- Fixed source oracle: child cutting 6+7, FG9, draft2, pending cost UNKNOWN; business boundary unchanged.
- Replay/request conflict, incomplete501 refusal with zero runs, immutable cursor and stale correction.
- Operations redaction, finance grant/revoke, disabled role, unmapped actor, service role, cross-actor refusal.
- Dedicated principal cannot write business data or execute operational commands; runs reject update/delete.
- Concurrent atomic stock/sales corrections cannot produce mixed fact pairs; duplicate requests persist one run; access revoked while waiting refuses with no persisted run.
- Real Auth/PostgREST: own run, denied cross-actor/anonymous, same-token revocation, operations financial refusal.
- Native/race/HTTP cleanup, CP6 restoration, and advisor delta must all pass. Administrative source fixtures are identified separately from normal posting acceptance.

These bounded capture boundaries are writer-verified. Next: extend source identity/lineage in P03/P04, retain explicit history/source limits, and connect consumers only after their actual source and transport contracts pass. R10/P11 remains OPEN_CP7; production_go=false.

## Confirmed cutoff regression and resolution

At `bb37cd2`, run `36505409042`, a new sale committed while a capture waited on its real request lock was absent from the run: expected quantities [2,3], observed [2]. The harness recorded INCOMPLETE; review classifies this as PRODUCT_DEFECT. `statement_timestamp()` represented the outer request start rather than capture time. The reader now materializes one `clock_timestamp()` after the lock, while retaining one STABLE source MVCC statement. The identical oracle passes in the final run. [PostgreSQL clock definitions](https://www.postgresql.org/docs/17/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT).

Complete-page profiles at 1/101/500 source rows returned 1/2/5 pages, unique facts and PCS totals 2/102/501. Measured capture times were 26.783/34.721/65.045 ms on this disposable runtime. The existing 501-row refusal passed. These are bounded profile observations, not a production latency promise.

The projection labels five operational or six financial domains accurately. Financial changes do not change the operation-only projection hash or stale label. Broader policy/calendar/report/apply dependencies are not declared implemented by this capture.
