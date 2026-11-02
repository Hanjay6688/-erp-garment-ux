# Global envelope — closed preparation

This implements the private lock primitive, without an installer, profile seed,
owning D1/E/source hooks, public RPC, grants, Native execution or acceptance.
The parent and runtime gates remain closed. The four prepared graph-inspection
helpers stay in their existing separate schema; their exact private function
count and source/ACL checks are preserved.

The future installer must seal an actual accepted final parent, its Root receipt,
all current catalog-table identities/owners/RLS/raw NULL-versus-array ACLs, at least
the 38 reviewed financial/HPP relations plus four permission tables, and exact
Native authority. The profiles table starts empty and is immutable after insert.
The final source/writer/trigger/FK/permission census may require more relations;
the hard minimum of 42 is not a proof of complete runtime coverage.

The helper freezes pg_class/pg_namespace before enumerating the exact catalog
universe, takes SHARE NOWAIT on every catalog table, EXCLUSIVE NOWAIT on reviewed
input relations, refuses any other granted permanent transaction-ID ExclusiveLock
(including prepared pid=NULL entries), locks all Native-visited nonPO/nonvoided
lots in Native ID order, then rechecks exact Native authority. Existing caller
request/CAS/pocket TRY/FG/FGBOOK order remains the caller's responsibility.

The mechanism is backed by actual retained relation-lock primitives and catalog
primitives (four retained plus three fresh). It is not yet an ERP lock profile.
No function infers quiescence from an empty snapshot xip sublist.

Remaining: actual final-parent profile and complete source/call/trigger/FK/RLS
review; operation/backend/transaction/actor/request binding; fresh D1/E review
and permission/period/source checks; the exact three guard and eight owning
function adaptations; full outside before/after proof before receipts close;
actual persisted SKU then D1/E positive/inverse/dirty/stale/permission races;
full package, backup/restore and independent acceptance. Native costing, global
propagation, transfer, date, FIFO and posted-history guards are not replaced.
