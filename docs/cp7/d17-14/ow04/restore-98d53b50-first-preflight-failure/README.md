# First admin-restore candidate: preflight refusal retained

Candidate98d53b50: all three jobs stopped before starting a database. Zero
Native, HTTP, race, browser or restored-write cases executed on this candidate.
The new administrative restore file was outside the qualifier's exact original
product-dependency set. A local pre-commit check had missed an untracked new
file; the missing committed-candidate recheck is corrected in this turn.

The correction does not qualify the new admin API with old Native evidence.
It admits only that one exact declared Git blob + SHA256, explicitly labelled
SEPARATE_ADMIN_RESTORE_REQUIRES_OWN_ACTUAL_RUNTIME and native_runtime_covered=false.
All existing product dependencies, Native87 receipts, declarations and actual
case/boundary/package checks remain exact. Undeclared or changed admin source,
fake Native coverage and any second unqualified script are refused. The final
gate requires the exact same separate binding. The actual restore proof is
still required. Cleanup now handles preflight failure before CLI installation.

The three complete decoded job logs are retained with text/gzip SHA256. They
also preserve the secondary cleanup errors and skipped-command final-gate
refusal. No raw workflow artifact was produced by this preflight failure.
The b3 Native87 and b20 transport18/race8/browser5 PASS receipts remain separate.
