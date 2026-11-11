# SKU runner shutdown: diagnosis and prepared checkpoint

Run 42941789501 / job 130265082676 / attempt 1 used candidate
`6aebc5888d164203ba7934b322b3edaf67ee36bd`. It stopped at 09:47 WIB on
11 November 2026. Steps 1–75 succeeded, step 76 was cancelled, cleanup and
canonical upload were skipped, and the artifact list remains empty.

The retained log reports a runner shutdown, supervisor SIGTERM, worker exit
-9, empty process group and process tree, and `deadline_reached=false`.
It does not establish why GitHub shut down the runner. No SKU scenario
completed. Database restoration and explicit cleanup are unverified.
The failed run remains incomplete; nothing here converts it into a pass.

## Prepared change

`checkpoint.py` saves immutable diagnostic receipts containing the candidate
identity and three exact admission reports before the disposable database is
started. The archive has a separate name from the canonical qualification
archive. Credentials and arbitrary environment variables are not copied.
The helper refuses the wrong head, dirty tracked source, missing or oversized
receipts, symlink paths, credential fields and attempts to overwrite evidence.

Its optional phase context writes and fsyncs STARTED before a call, preserves
the original exception on failure, and never calls an incomplete phase complete.
This context is prepared for future explicitly reviewed subphase wiring; it
is not wired into the current parent installer by this change. Local surviving
files do not survive loss of a GitHub VM unless previously uploaded. No helper
can promise a final upload after the hosting machine has disappeared.

`derive_workflow.py` produces review text with two additional steps after
browser/source prerequisites and before database setup. Removing those two
steps gives the original workflow exactly as parsed: all 81 existing steps,
permissions, branch gate, concurrency, budgets, recovery and final canonical
upload are unchanged. This is an 83-step draft, not an activated workflow.

Current owning `workflow.py --check` and SOURCE manifest must refuse this draft.
Integration must update the owning derivation/template/manifest together and
rerun exact source controls before any qualification. Do not bypass that guard
or run this draft directly. This branch introduces no active workflow.

## Validation and scope

Run `python3 -m unittest -v test_checkpoint.py test_workflow.py` in this directory.
Controls include an actual child process killed by SIGKILL; only STARTED survives,
no completion or recovery credit. Original receipt bytes can be recovered exactly
and their hashes verified. Wrong candidate/source, secret data and symlink cases
are refused. Old workflow semantics and distinct canonical/diagnostic artifacts
are checked, and a changed source or weakened recovery is refused.

No ERP, financial, Auth or database scenario is credited by these controls.
No hosted DB, production, main or Writer B change is included.

`MANDOR_LONG_LABEL_REVIEW.patch` is the earlier isolated Payroll CSS fix,
preserved here for integration. Its exact and long-name fixtures passed four
screen widths in the previous audit. It is not applied to product code here;
the earlier accepted Mandor evidence remains tied to its original source.

## Remaining boundaries

- The original shutdown run has no canonical artifact or observed cleanup.
  Its resources were local to a GitHub-hosted runner, but that fact is not a
  passing restore test. Preserve this distinction when deciding a successor.
- Rebind the checkpoint draft and CSS separately to the actual reviewed source.
- Identify actual parent-install subphase entry points before adding phase
  instrumentation; do not infer from the last broad log phase which installer
  function was active.
- Global still requires actual SKU25+2, all five gates, full restoration,
  worker completion, original archive and actual full25 catalogue. Prior Global
  branch auto-review denial remains; this review branch does not bypass it.
- Formal CP7 remains 5/16; independent acceptance and production_go remain false.

Source of the original diagnosis and CSS tests: audit archive
`CP7_ERP_AUDIT_REGRESI_20261111.zip`, SHA-256
`c6970712d0470d2fda00b7ae7df0e0e9791d8cbef6045726788a2f8eb989c7bc`.
