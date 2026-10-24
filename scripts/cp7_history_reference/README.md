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
stock whose physical date is earlier than the read cutoff. Native4 qualified this reader at8909b7c/run40024688908:4/4 PASS,40 source
hashes,11 pre-use22 inverses, unchanged legacy10, restore/advisor and all5
package gates exact. Dense202001 visible rows were hashed in2206.968/2213.959/
2190.252ms, each below8s. The late-recorded Native stock control passed without
rewriting a clock or date. See `docs/cp7/d17-14/ow13c/8909b7c-reference4-pass.json`. This digest is not yet bound into staged-job fingerprints,
source freshness, work scheduling or the actual checked SAVE2000 writer.
