# CP6 AD: opening material date family

AC `1bdca3766f7c9800d68295ff5122798060b8a05d` has a qualified material
counterexample. Independent run 34963873816 produced four ordinary OWNER
postings where the material stock business day was 2026-09-11 while the opening
document and journal day were 2026-09-12. Fabric and accessory both failed in
Tokyo and Kiritimati. Sixteen other cases passed; five attendance controls were
incomplete because the harness used private functions instead of public RPCs.
The whole database and schema privileges were restored exactly. The partial
audit is retained; it is never relabeled as a complete PASS.

AD changes two functions. `post_opening_balance` uses Jakarta midnight for the
MATERIAL branch. Its shared path covers direct fabric, fabric rolls, accessory,
and migration-prepared opening items. `run_v268_financial_report_checks` adds a
material-opening timeline check consumed by the existing owner snapshot. A
posted line must have exactly one correctly linked opening movement at that
document's Jakarta day start. Existing posted discrepancies cause admission to
refuse for review; the migration does not rewrite posted history.

The family disposition records the inspected timestamp conversions and explicit
exclusions. Fifty-five cases run under both AC and AD using the same independent
oracle, including imported/prepared postings, FG manual and percentage HPP, BS
with/without a product, and attendance through the public facade. Each material
case checks stock cutoffs, cost checkpoints, exact journal cents, replay refusal,
and report confidence. Six detector controls transactionally reinstall the exact
old writer and make ordinary bad postings; the AD report must become BLOCKED.
No posted-row tampering is needed for those controls.

Only after the complete family suite and atomic controls pass does the runner
execute the 20 AD maintenance schedules. The executor preserves the AC lock fix:
function pins before admission closes; full 274-object proof after sessions
drain. AD must restore the exact 533-function, 218-table AC boundary. The older
AC -> CP4.5 ladder and 460 predecessor schedules remain source-qualified reused
evidence from Native200/AB189. They are not claimed as newly executed on AD.

The original full validation body remains byte-identical. Its routing step
recognizes the explicitly pinned AD source set and sends it to the dedicated
whole-family gate. Unknown changes fall back to the full validation path. A green
routing job records evidence reuse; the dedicated native job must independently
finish every new gate. CodeQL also runs on the new commit.

The runtime fixture uses disposable PostgreSQL 17.6, synthetic JWT SQL sessions,
and already validated import staging rows. Signed HTTP/Auth/browser evidence is
reused only for unchanged source paths. CSV parsing and new UI reachability are
not claimed by these SQL tests. The next chatbox should attack the AD delta,
material/source relation completeness, report confidence, admission poisoning,
and residual temporal input contracts before independent acceptance.

Native5 (34967943841, head 24ad7483ee594a7172e55c642f396208e5231f56)
completed all 55 successor cases, six detector controls, six admission controls,
eight rollback controls, and all 20 maintenance schedules. Its final whole-table
comparison failed after rollback. The predecessor snapshot uses Asia/Jakarta;
the failed comparison used UTC. The repaired wrapper retains both observations
and requires the entire 533-function / 218-table boundary to match under the
original observation context, with per-table diagnostics. No SQL bytes change.

The retry downloads Native5 artifact 10396157668, verifies its exact ZIP and
manifest hashes, checks all 20 cases and zero clones, and preserves all 241 matrix
payload files. Every repository path outside the explicit comparator/harness
repair list must equal Native5 before reuse is allowed. These 20 cases remain
REUSED_VERIFIED_NATIVE5; Native5 itself remains a failed run. They are not run
again or relabeled as fresh proof. The family suite and final restore comparison
run on the new candidate. The next auditor can reuse this evidence under the same
source conditions instead of repeating a completed matrix.

The authoritative verdict is the exact-run writer manifest and lossless
transfer. Until those complete, AD is a writer candidate awaiting native proof.
Even a writer PASS still requires the other chatbox's independent audit.

Only `competition/cp6-j-closure-20260911` is writable, fast-forward only.
CP6 remains active, `production_go:false`. Main, PR24/25, UAT, legacy,
production, deployment, and CP7 remain outside this work.
