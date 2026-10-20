# Eight real Auth/HTTP settlement qualifications

Expected cases and boundaries are declared in EXPECTED.json before runtime.
Run only in the disposable CP6 runtime prepared by
`.github/workflows/cp7-ow04-http.yml`:

```sh
python ../auditor/scripts/ow04-qualification/transport_probe.py
```

The entry accepts no arguments or authority overrides. Its normal repo root
is derived from this tracked path; for source-only imports from elsewhere set
ERP_REPO explicitly. Before opening a DB connection it requires the exact
Native44-qualified core/probe/dependencies bound by QUALIFIED_CORE.json.
The current HTTP candidate and its actual case/entry/declaration hashes are
recorded separately from the reused Native candidate/run/job.

The harness creates real Auth users, uses actual password-grant tokens and
PostgREST, and tests real COMMIT followed by fresh-connection money, original
payment, journal/date-pair, stock and HPP assertions. Replays/refusals require
the complete private table inventory and exact full rows to stay unchanged.
No request issues a test-minted token or replaces a Native authority guard.
Administrative stock/sale/payment/period/master fixtures are labelled and
confined to the copied database; normal writers post their source documents.

PASS requires all eight exact IDs, real Auth cleanup, copied-database removal,
CP6 restoration and advisor gate. Preserve the first complete job log and
CP7_OW04_HTTP.json even on failure. Source preflight and counter records live
in `docs/cp7/d17-14/ow04/http-check/`; they are not HTTP runtime results.
This does not prove browser interactions, concurrency, interrupted-response
recovery, corrected/cohort/APPLY completion or production readiness.

Six separately declared public-SQL races now follow this group in the same
disposable workflow, using RACE_EXPECTED.json and race_probe.py. They reuse
the unchanged qualified backend, not this HTTP group's results:

```sh
python ../auditor/scripts/ow04-qualification/race_probe.py
```

Each race gets a fresh copied database. The test requires observed exact
holder-to-worker blocking and checks the full ledger and unchanged financial,
date, stock and HPP oracles. The termination case only kills its own known
holder PID after proving the exact disposable race database; it tests server
rollback of an uncommitted transaction. Real Auth belongs to the first group;
SQL fixture claims do not establish Auth, browser or lost-committed-reply proof.
