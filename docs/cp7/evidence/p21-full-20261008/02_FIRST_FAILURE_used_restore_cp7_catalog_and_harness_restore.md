# Second run: first failures kept (source cfc96da2, run 37714806457, job 113108746232)

Passed: PREINSTALL_BACKUP (10.6 MB dump, 407 tables), INSTALL_1 (1,776 functions, 129 CP7 tables, 38 CP7 roles),
PREUSE_ROLLBACK (restored exactly), REINSTALL (identical catalog 4f05e71b…), USE committed (supplier payment
d6f3b589…, remaining 900.00; staged job 51469e0b… DONE in 21 units, 3 targets, 1 page, identity_hash dd16e712…),
POSTUSE_ROLLBACK refused (CP7 rows since install incl. cp7_analysis_stage.jobs 1 / pages 1 and
cp7_supplier_payment_create.requests 1). Advisor gate passed.

Failed:
1. USED_BACKUP_RESTORE = DIFFERENCES_RECORDED although pg_restore had only the 19 known pg_cron lines, the erp/public
   catalog differences were all classified (29 constraints, 6 views, 1 index: VARCHAR_IN_LIST_REPARSE; pg_cron
   extension), every table's rows were identical and the staged result re-read on the restored database was equal
   (identity_hash, page, reassembled Original). Only the CP7 catalog comparison (exact md5 of every definition,
   tables, policies, roles) differed; the probe did not record which members.
2. HARNESS_RESTORE_AFTER_USE: the exact restore proof failed after the committed use; the summary line did not print
   which component.

Change: the CP7 catalog comparison now records every differing member and classifies a definition or policy that a
dump round trip re-parses (the same G-01 varchar IN-list form the erp/public comparison already accepts) as
SAME_MEANING; anything else stays UNCLASSIFIED and fails. The harness restore after a committed use reports the exact
proof and gates on the catalog (schema ACLs, every definition/owner/ACL, every public member); public tables holding
rows of the committed use are listed, since a used installation is restored from backup (step 7), not by the harness.
