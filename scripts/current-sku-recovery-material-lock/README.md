# Managed SKU recovery: exact valuation material lock

Prepared successor of public e8f878f2ecaaf24368a0ce1a3393bc29c0b886f6.
The only existing product change is one reversible hunk in recovery.sql.
All frozen Source43 bytes and evidence, eight Native captures, five private
tables, and all original 23 callbacks stay unchanged. The private function
count remains nineteen; only recovery_preflight_v1 gains the row lock.

Native ACC_DEC03 accepts both MOVING_AVERAGE and NONE. Native locks the
material row early only for MOVING_AVERAGE. Under NONE, an earlier transaction
holding SELECT FOR UPDATE has ROW SHARE, compatible with the preflight's
SHARE ROW EXCLUSIVE table lock. The later Native FK or material update could
therefore wait after document/audit creation, while the other transaction's
update waits for that table lock. This successor locks only the valuation
material row derived from the return lot already locked by Native BCLOT.
NOWAIT refusal happens before the first Native document. The existing fresh
authority and period checks after the prelocks remain byte-for-byte intact.
Native MOVING_AVERAGE may still wait before the preflight; this is not a
claim that the entire command never waits.

The source gate verifies the public parent, all old 43 pins, the exact single
SQL hunk, every other tracked parent path, and the closed new namespace.
This prepared gate does not replace the full Native27 caller's generated
artifact/untracked-source admission. No frozen Source43 reader is edited.

Local tests execute the exact captured BC/service and unchanged BE/HPP bodies
using the retained explicit Auth/material/journal doubles in PGlite. An exact
private derivation adds only a local policy-table double and four NONE
controls to the frozen 45 controls: under/equal posting and exact replay,
the same over-budget Native refusal with every local row/sequence/session
unchanged, and authority withdrawal after the BCLOT wait double.
These are **Native financial 0, real two-session contention 0**. Real NONE
FOR UPDATE holder plus separate FG holder attempts are still required in
the single new BUSY callback of the prepared total 27 actual cases. All
refusal/replay snapshots require every sequence unchanged; successful sequence
increments are restored only by the complete outer backup, never by savepoint
rollback or reseeding.

Writer freeze: `python scripts/current-sku-recovery-material-lock/bind.py --writer-freeze`.
Source tests: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s scripts/current-sku-recovery-material-lock -p 'test_*.py' -v`.
Local SQL: set F04_PGLITE_MODULE to the existing pinned local PGlite module,
SKU_RECOVERY_LOCAL_RECEIPT to an explicit private JSON path, then run
`node scripts/current-sku-recovery-material-lock/local.mjs`.
No DB server, remote operation, production adoption, or actual qualification
is performed by these commands.

The current source-proof reader explicitly blocks psycopg.connect and the
synchronous/asynchronous Connection.connect entrypoints before retained
module imports, in addition to socket/HTTP/non-Git command controls. Its
three deliberate entrypoint self-controls are reported separately from
actual source-read attempts. Original descriptors are checked restored on
success and on a deliberate late local error. This closes the helper-only
proof gap found after the first preserved 24e4f9815 source snapshot; it does
not change the product SQL or add financial qualification credit.
