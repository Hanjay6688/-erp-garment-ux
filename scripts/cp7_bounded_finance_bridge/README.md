# OW12a — explicit bounded finance composition proposal

VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan termasuk laporan,
stok, dan HPP adalah raja.

The operational bounded request currently defers finance. This additional route
starts the same bounded job and the existing official finance capture in one
transaction, bound to the same actor, job, query and source capture date.
It adds no financial formula, table, Native business write or scheduler.

`public.erp_cp7_request_bounded_finance_analysis_v1(jsonb,uuid)` accepts exactly
`from_date`, `through_date`, `group_mode`, and explicit string `finance_mode=STAGED`.
Only `authenticated` has public execution. Its private invoker function uses
the existing current-access checks, bounded source, capacity limit, job creation
and `cp7_finance_capture.start`. Fresh access and finance permission are checked
after the request lock and after capture start. Failure rolls back all writes.

The original operational route retains its closed three-field query and creates
no finance capture. Its one declared body change refuses a UUID already used by
the STAGED route. Both routes reject cross-mode UUID reuse and changed queries.
The existing finance status/processing/sealing path remains the owner of figures;
an operational READY alone cannot establish official finance READY.

`render.py` derives both request bodies from the actual B bounded renderer and
the actual A finance bridge patcher. `verify_sources()` checks generated SQL and
manifest equality. The opt-in stage admits one existing body replacement plus
one private function and one public RPC. Installation holds composition and HPP
locks and all-table SHARE locks, verifies the actual predecessor, refuses running
analysis jobs, and proves all 22 catalog groups and all rows/sequences unchanged
except the three declared functions. Pre-use inverse checks global used data
before any DDL. Used recovery requires full backup/restore.

Local PGlite qualification executed the generated routes, actual closed-query
helpers, actual finance capture table and actual capture start: 17 checks PASS.
Access, bounded source and job/status dependencies are controlled fixtures.
Injected access changes are not actual waits/races or Supabase Auth proof.
The initial local helper failed because it assigned one control column twice;
the helper correction leaves product SQL unchanged and the failure is retained.

This isolated proposal has no default installer or UI caller. Full-current
composition, Native official figures, used recovery, real Auth/races, actual cron,
and 1200 SKU × 3 size financial parity remain to be qualified. The small local
fixture and capacity rejection provide no factory3600 success claim.
`production_go=false`; writer evidence is not independent acceptance.

Run locally from the repository root with an available PGlite module:

```sh
CP7_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node scripts/bounded-finance-local-qualification/routing.mjs /private/output.json
```
