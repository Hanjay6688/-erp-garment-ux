# Third run (source 494da5a4, run 37715466679, job 113110806745)

Same passes as run 2 (install, pre-use rollback, identical reinstall, committed use incl. staged DONE, post-use refusal).

USED_BACKUP_RESTORE: rows identical, erp/public catalog explained, staged re-read equal; the CP7 catalog differed only in
the `tables` member: every CP7 table whose ACL is stored explicitly as exactly the owner's default privileges
(e.g. `{cp7_capture=arwdDxtm/cp7_capture}`) is restored with a NULL ACL. pg_dump omits an ACL equal to
acldefault(), and NULL means those defaults. Reproduced locally (LOCAL_PG16_DEV, not evidence): explicit
`{o=arwdDxt/o}` = acldefault -> dump/restore -> NULL. The comparison now classifies a table difference as
DEFAULT_ACL_EXPLICIT_OR_NULL only when every other field is equal and both ACLs normalize to the owner's
acldefault() read from the restored database; anything else stays UNCLASSIFIED.

HARNESS_RESTORE_AFTER_USE: restore_components = {erp_platform_auth_schema_acl: false, public members and row
hashes: true, definitions/owners/ACLs: true}. The first component is a snapshot of every ERP table's rows, the
migration ledgers, auth.users and the erp/public schema ACLs, so a committed use changes it by design. The harness
gate is now: erp/public schema ACLs exact, migration ledgers exact, every definition/owner/ACL exact, every public
member exact; ERP and auth rows written by the use are listed. Restoring a used installation's data is proved by
the pre-install backup restore (step 7).
