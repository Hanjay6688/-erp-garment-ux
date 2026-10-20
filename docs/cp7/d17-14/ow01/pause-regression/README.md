# Synthetic actual-SQL pause regression

This proposal is outside the product checkout. It executes the selected source's actual settings/outbox tables, settings CAS and append-only guards, alert opening/refresh/queue guards, repeat queue, `waiting_eligible`, and sender pause/selection SQL in PGlite. SQL fragments are extracted with closed anchors and their hashes are reported. Owner access and Vault presence are explicit stubs. Accepted/UNKNOWN rows are synthetic delivery-state fixtures.

This is **not** Native, real Auth/ACL, concurrency, pg_net, provider receipt or WhatsApp evidence. The sender's expensive source checks and actual dispatch are not run; selected `ok`/`failed` inputs are named synthetic arguments. A passing selection does not prove the source was rechecked or a message sent.

Run from the repo with a resolvable package or set `PGLITE_MODULE` to the installed package's ESM entry point:

```bash
PGLITE_MODULE=/absolute/path/to/@electric-sql/pglite/dist/index.js node /absolute/path/to/pause/pause-regression.mjs --source scripts/cp7-src/alerts/alerts.sql --output /absolute/path/to/pause/candidate-result.json
```

The executable runner exports the exact old source from Git, snapshots the current candidate, executes both with the same harness, and writes a fresh result directory (an existing directory is refused):

```bash
PGLITE_MODULE=/absolute/path/to/@electric-sql/pglite/dist/index.js node /absolute/path/to/pause/run-proof.mjs --repo /absolute/path/to/repo --out /absolute/path/to/new-result-directory
```

The baseline invocation uses an exact `git show 6efdcd78:scripts/cp7-src/alerts/alerts.sql` export and `--first-retention-only`. It must fail the first retention assertion because the actual old update makes the accessory row DISABLED. Keep the first result unchanged. The candidate must pass all cases with its own source/function/fragment hashes. No expected is changed to make the old source green.

Retained development results: `first-harness-setup-failure.json` records the initial JavaScript identifier collision before SQL; `first-baseline-result.json` records the causal old-source failure; `first-candidate-result.json` preserves the missing-harness-dependency `ts_key` error after three passing cases. The real `ts_key` helper was then extracted without changing expected results; `candidate-second-result.json` passes all six cases on the same candidate snapshot. These harness failures are not Native or product defects.
