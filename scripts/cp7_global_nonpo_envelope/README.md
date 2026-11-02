## Fixed platform catalog fence preparation

Actual Supabase PostgreSQL17 refused the old all-catalog SHARE barrier under the ordinary postgres owner with SQLSTATE42501. The old successful catalog primitive models used a superuser creator. Their lock semantics remain valid; they do not establish installation authority for the product owner.

`platform_catalog_fence.sql` prepares one zero-argument private function owned by the existing platform supabase_admin. It may enumerate and SHARE NOWAIT lock only pg_catalog tables, returning relation identity/ACL metadata. Its only non-owner invoker is postgres. It creates no role and grants no catalog DML/MAINTAIN, browser or service access. Bootstrap must use declared trusted maintenance authority in an explicit transaction. `catalog_bridge.derive()` routes one exact block of the unchanged old lock source through this helper; ordinary postgres regains control with transaction locks retained. The existing relation barrier, XID review, Native lot order, authority comparison and eight owning adapters are unchanged.

The source gate remains closed. Actual17 helper capability/ACL/inverse checks, a lawful bootstrap/outer-cleanup transition, final-parent profile adoption, complete current input/rights/writer/phantom closure and actual Native coexistence/all5 remain required. No old scope21/review13, catalog7 or relation9 controls were rerun for this source preparation.

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

`work_scope.sql` additionally prepares backend/transaction/actor/request binding
from the three real Native work tables. D1/E require the exact reviewed global
basis; generic SOURCE binds a fresh owned basis without claiming UI review.
After the NOWAIT barrier, live Native access and work identity are rechecked.
Completion requires the same owner/request/payload/version and Native completion
phase, then exact outside identity and full fact equality. It changes no Native
phase itself. Immutable private completion rows reject update/delete/truncate.

Twenty-one new PostgreSQL/WASM18.6 model controls passed after one initial SQL
CASE-parentheses compile fix (zero cases had run). Exact73 column types come
from the accepted DE30 original. Native owners, constraints, Auth/rights, barrier
and inspector are explicitly modeled; none of the old actual lock controls or
census was rerun. The four standalone graph helpers are separate, and the eight
counted owning adapters and final-parent adoption remain uninstalled.

The mechanism is backed by actual retained relation-lock primitives and catalog
primitives (four retained plus three fresh). It is not yet an ERP lock profile.
No function infers quiescence from an empty snapshot xip sublist.

`review.sql` adds two private helpers. One actual sealed profile and exact
Native authority are required; a dirty observation remains a refusal. The new
private basis joins the existing D1/E review hash without adding public fields.
`native_hooks.py` derives all eight owning functions through eighteen exact
reversible routes over actual accepted DE30 definitions and all19 attributes.
Barriers precede fresh reads, scope binding follows the actual Native work row,
and completion precedes the original immutable receipt/work cleanup. Native
propagation/transfer/global sync/FIFO/HPP/stock/journal engines are unchanged.

Thirteen new controls passed on their first execution. Both original and derived
eight functions compile against nine actual Native row-type maps in the model;
every other pg_proc field, OID and raw ACL stays exact there. Actual business
functions do not execute. The unchanged actual E public projection omits the
new private global field. The prior21 scope controls were not rerun.

Remaining: actual final-parent profile and complete source/call/trigger/FK/RLS
review; actual Native integration of operation/backend/transaction/actor/request binding; fresh D1/E review
and permission/period/source checks; actual installation and validation of the three guard/eight owning
function adaptations; full outside before/after proof before receipts close;
actual persisted SKU then D1/E positive/inverse/dirty/stale/permission races;
full package, backup/restore and independent acceptance. Native costing, global
propagation, transfer, date, FIFO and posted-history guards are not replaced.
