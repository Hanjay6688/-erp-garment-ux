# Full Native stock reference — work in progress

The bounded-input reader can calculate correct history without collecting
202,000 raw stock rows into JSON. A production reference must also notice a
changed row even if daily availability/free-stock totals happen to stay equal.

This additive private reader derives the exact typed stock projection and both
visibility clocks from frozen Native `planning/history-source.sql`. It hashes
every visible canonical JSONB row, ordered by its Native UUID, then frames those
fixed-width row hashes with a version/domain and row count. No raw prefix, row
sampling, floating arithmetic, old-status override or business write is used.

One private function, zero public facades/tables/old replacements. Four Native
controls are declared: private catalog; exact parity against actual Native raw
facts; full dense2000/202000 digest three times below8s; real Native late-recorded
stock whose physical date is earlier than the read cutoff. Runtime qualification
is still pending. This digest is not yet bound into staged-job fingerprints,
source freshness, work scheduling or the actual checked SAVE2000 writer.
