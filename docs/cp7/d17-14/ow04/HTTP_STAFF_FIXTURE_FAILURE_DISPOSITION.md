# Two actual HTTP8 fixture failures, unchanged product/expected

f3437108, run39492199058/job118867983298:7PASS/1INCOMPLETE.
2f6c28ec, run39494596197/job118876226645:7PASS/1INCOMPLETE;
the six race cases were skipped after the HTTP step failed, not passed.
Both complete first logs and receipts remain in CI_F343_HTTP_FIRST_* and
CI_2F6C_HTTP_FIRST_*. CP6 restoration and advisor gates were true in both.

Both runs passed actual CREDIT and REFUND commits, fresh-connection exact
money/journal/date/stock/HPP assertions, unchanged original payments,
committed replay and five negative cases. The STAFF case stopped before
STAFF Auth login/refund calls, so neither run proves the non-owner distinction.

The writer initially interpreted a lookup filtered by is_active as an absent
STAFF master. That diagnosis was wrong. The next run proves the existing
STAFF is inactive; migration20260902104937 seeds that Legacy STAFF inactive.
The first correction only created absent rows and deliberately refused an
inactive existing row, producing the second fixture error.

The final administrative setup explicitly activates this STAFF only on the
disposable HTTP copy, records prior_active/created/activated, and preserves
its actual STAFF identity and system/protection flags. It copies the actual
OWNER fine-permission keys, asserts all six required keys, uses unchanged
real Auth user creation/password-grant login, and requires the same user's
CREDIT quote to succeed before both REFUND calls fail with the exact unchanged
Native400/P0001 owner/admin message. No Native authority helper, guard,
public facade, product master or frozen monetary/date golden changes.
The eight IDs and EXPECTED.json remain byte-identical to f3437108.

The workflow now collects the two independent copied-runtime groups even
if one inner test fails, after verifying CP6 restoration, primary unchanged
and real Auth cleanup before preserving HTTP proofs and making a fresh AB
clone. continue-on-error never permits overall PASS: the final gate requires
both actual GitHub step outcomes to be success (not the masked conclusion),
both preserved/current package reports' five original gates all true, and
all inner exact8/6 IDs/counts/candidate/core/restore/advisor/cleanup checks.
The counter's two false-green reproductions and previous gate/workflow are
preserved in race-check; the final source recheck and24 synthetic gate controls
reject those counterexamples. Those controls are not runtime/Auth/Native proof.

Fresh actual qualification on6f318261, run39497414236/job118885938105,
passed all eight real Auth HTTP cases and all six actual SQL race/recovery
cases. The actual STAFF fixture records prior_active:false and explicit
activation:true; the same user's CREDIT quote succeeds before both exact
Native refund refusals. Both actual GitHub step outcomes are success and both
outer package reports pass all five gates. CP6 restoration, advisors and Auth
cleanup pass. CI_6F31_HTTP_RACE14_PASS.json and the complete compressed log
preserve the new result, separately from both original seven-case results.
Native44 is reused with the exact backend/probe binding, not rerun here.
No browser, whole-server crash, lost successful HTTP response or production
readiness is inferred. OW04 remains open; production_go:false.
