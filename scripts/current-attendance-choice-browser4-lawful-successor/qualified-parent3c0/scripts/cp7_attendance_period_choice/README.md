# S03 — owner choice for attendance with no sewing output

Owner decision D17-19C is in `docs/cp7/OWNER_DECISIONS_20261008.md`.
This isolated stage starts at A0b4e5ead. Its runtime parent is
`cp7_vendor_receivable.composition`, byte-equal to the qualified vendor41c
Combined11 source (Native7+races3+realAuthHTTP1). Existing frozen SQL, App, shared menus and installers stay
unchanged. Formal acceptance5/16 and production_go=false remain unchanged.

Native14c `_build_attendance_hpp_manifest_v1` binds payroll sources and normal
Mandor sewing to the same exact period. Native CREATE refuses positive cost
with zero sewing; Native VALIDATE also refuses destinations outside that
period. Payroll APPROVED recognizes WIP/payable once. PAID is settlement.
Afui/special contractors and contractors without required attendance are
excluded by the original Native policy snapshots.

The additive lifecycle uses insert-only choices, exact source debit links,
choice reversals, carried-pool metadata, allocation reversals and request
answers. An OWNER with current HPP view/manage rights chooses CARRY or EXPENSE
for one exact source period after a fresh review and explicit reason.

* CARRY retains the same WIP without inventing output. Later ALLOCATE selects
  a separate, strictly later exact output period. Its sources remain the
  original Native source manifest; its destinations come from the separate
  Native later-period manifest. No range is widened. A private counted clone
  of Native CREATE/VALIDATE retains every source/cent/allocation check, while
  normal pools keep their original path. Native ACTIVATE/CANCEL, HPP rebuild,
  descendant propagation, GL sync and finished-PO residual closure still own
  costing. The carried pool header is the source period, so a normal pool for
  the later period may coexist without taking the old payroll sources twice.
  Its allocation journal date is explicitly the later output period end.
* EXPENSE posts Native DrOTHER_EXPENSE/Cr original unassigned WIP, linked per
  exact original payroll debit. It does not recognize payroll again, change
  a payroll payment or create a receivable. A legitimate owning reversal
  restores that same WIP. A replacement appends its correction link.

An active carried pool must be cancelled through Native before changing its
choice. Payroll cancellation/new approval and policy changes that would
invalidate held sources are guarded; APPROVED→PAID remains settlement and
does not change the source binding. Generic journal reversal cannot detach
an expense from its owning choice. No GUC bypass or broad inverse flag exists.
All current permissions are checked after waits and before replay or DML.
Period, global finance/FG, contractor policy and original source locks remain.

Unresolved zero-output cost becomes a POLICY blocker under D17-19C. The old
OW07 Native7 Original remains historical INFO/nonblocking evidence and is not
relabelled. An explicit current CARRY waiting decision explains the WIP and
permits closing; EXPENSE explains its linked reclassification. Both economics
and books must never remove WIP before the original accrual is recognized.
Closed expense/allocation periods must be reopened legitimately for corrections.

Backend and wire v1 are implemented, with no actual Native/Auth/browser/CI
execution. Public wire shape stays exactly at7e91ec5e6 in `WIRE_CONTRACT.md`.
Root separately owns the standalone panel, source/type registration, recovery
integration, mounting and actual qualification. This namespace adds no roles.

Twelve installed Native function bodies and one existing private payroll
settlement facade keep their frozen financial/access hooks. Two existing private
HPP readers receive counted return decorators: fifteen captured originals total.
Two private Native CREATE/VALIDATE clones preserve their
source/cents/ownership/HPP checks.
Thirty-six new functions include three authenticated public RPCs. Every new
catalogue identity is declared explicitly, with no blanket schema prefix
allowance. Actual current15 definitions, owners/metadata, immutable captured
originals and clone derivation are checked against the actual22 catalogue;
preuse restores every old catalogue/data/sequence value exactly. After use,
the guard refuses before inverse DDL and requires the full backup boundary.
The Native source builder, journal arithmetic and HPP engines stay unchanged.

Actual baseline9a0 failed before any business callback: replacing the existing
postgres-owned payroll facade still required CREATE on its cp7_payroll schema,
owned by cp7_payroll_read. The two HPP readers have the same schema pattern.
`installer_ddl.py` now inventories only these two known schemas, actual owner,
raw nspacl, preexisting USAGE/CREATE, current/session actor and SET authority.
Actor stays postgres; SET ROLE authority is session-user based, as in the
qualified OW05 envelope. Needed CREATE alone is granted by the existing schema
owner and revoked before exposing state; install and preuse undo share the exact
context. No new role, membership, USAGE, persistent grant or default privilege.
Existing CREATE is preserved, including raw NULL no-op profiles; a NULL profile
requiring a grant refuses instead of normalization. A usable-transaction error
cleans/verifies; an aborted SQL transaction is restored by the owning outer
atomic rollback. Actual9a0 role rows were not retained, so source-derived owner
facts and local literal non-SU postgres/SU-session controls remain distinct from
an actual installed profile. The next qualification repeats the whole14-case
successor/all5 envelope; failed9a0 is never a prerequisite PASS.

Reader compatibility is additive in `readers.sql`; `choice.sql`, all thirteen
earlier financial/access derivations and both Native clones remain byte-exact
atf265. Immutable allocation.pool_id gives a carried pool permanent ownership
metadata and removes legacy CANCEL/REPLACE, including after inverse/correction/
decision reversal. Separate exact-source `period_hold` metadata blocks ordinary
replacement/create while a CARRY or EXPENSE decision holds that same period.
No broad overlap or output-P2 hold is added; ordinary P2 pools remain unchanged.
Native header/period_closed stay sourceP1 while owned metadata shows real outputP2
and its closed flag. One current Native composite/ownership/inverse snapshot
refuses stale data with READ_CHANGED. The existing BLOCKED contract has no
figures/token/can_create; READY is never weakened. Three new helpers are private
SECURITY INVOKER under the existing postgres-definer HPP reader authority, with
no new roles, persistent grants, RPCs or financial guards. See `READER_WIRE_CONTRACT.md`.

Carry's live identity binds only actual eligible destination facts and quantity
from P2; its full initial P2 manifest remains immutable provenance. P2 payroll
and normal P2 pools with disjoint sources can coexist. Previously excluded P2
output becoming eligible is fenced after policy insert, before its Native audit
allocation, by exact fresh carry binding. Future policy metadata that is not in
the Native destination binding remains lawful; held source effective_to is in
the source binding and cannot be truncated. Direct Native carried-pool cancel
requires exact actor/backend/transaction/pool/UUID/reason/version context; only
the owning command closes both Native and private inverse metadata. Late new
output in an active carry destination is fenced under Native date lock order.

The original source accrual/items/policy bind cost, not payment state. E05
individual cash corrections/reopen remain settlement. Whole E05 source inverse
is refused at its first exact linked cash journal when its command context says
REVERSE_PAYROLL, before it can reach the later original payroll source guard.
Expense journal generic inverse remains protected by its immutable decision.
All source, restoration, expense and allocation movements stay nonnegative per
original debit at every economic and book cutoff. No generic dated reversal,
range widening or session bypass was introduced.

Local controls use exact retained/source-derived Native routine bodies over
declared isolated table/Auth/calendar/HPP dependencies. They are zero actual
Native/Auth/browser credit. SET_POLICY now includes exact current HPP01 source
transformation; initial earlier reports used the P00-only local template, and
their provenance/failures remain unchanged. Owning install always captures and
verifies current definitions; it never installs this local ABI as Native proof.
See `evidence/LOCAL_CHECK_RECEIPT.json` for final commands/counts/source hashes.

The audited APPROVE control uses the
retained Native recalculate, unconditional row-version bump and payroll audit
trigger definitions; access/context/token/document and nonwork eligibility
remain explicit local doubles. The first run correctly refused a second
CALCULATED payroll held by a choice, but audit sequence10→12 proved the claim
guard was too late. That unmodified21PASS/1FAIL report and exact census diff
remain in evidence. The repair captures the existing private settlement facade
as the thirteenth original. Public APPROVE keeps payroll row→raw-contractor
advisory→shared period order, then repeats current settlement access and checks
the claim before child locks or rebuild. Direct Native APPROVE keeps its original
OWNER/ADMIN authority, takes payroll row→period, repeats that authority and
checks the claim before recalculate. Original later guards remain. Other
settlement actions follow their original paths; wire7e91 stays unchanged.

Failure-first history is retained: seven initial nullable-contract failures;
cash-column/chronology fixture corrections; stale expense-account preview;
SQL alias ambiguity; missing local identity preparation and timestamptz catalog
canonical alias; inverse event-ID and excluded-P2 policy defects; one overly
restrictive destination-policy expectation corrected from exact Native ABI;
missing declared generic-inverse dependencies; first Native cash inverse under
modeled E05 whole-source context. A later isolated runtime failure under shared
CPU is retained alongside unchanged targeted diagnosis and full-suite results;
its cause was not established.
No assertion was removed to fabricate a Native PASS, no historical Original was
relabelled, and no test is skipped in the complete final local suite.

An injected late HPP dependency failure rolls every modeled business row back.
The exact one Native CREATE audit sequence allocation remains visible because
PostgreSQL sequences are not transactional. That control claims exact row
atomicity plus that named allocation, not absolute full no-DML. Every guard
refusal before writes compares the full model business rows and all sequences.

Eleven meaningful full-parent Native callbacks are prepared separately in
`scripts/current-attendance-period-choice-qualification`. Retained vendor41c
Combined11 means Native7+races3+realAuth1. Their historical package/restoration
proof is a prerequisite; it gives zero new S03 credit. Actual Native/real Auth,
permission waits/races, descendant conversions, full browser journeys and all
backup/package/advisor gates remain required. Unproven paths remain guarded
with explicit reasons. Local results never confer independent acceptance,
CP7 closure or production go. The explicit UTC17:00/WIB-midnight fact pair is
not covered: local caller-timezone invariance and lawful actual-day fixture
timestamps do not qualify that boundary.

The reader successor adds three PREPARED Native cases in
`scripts/current-attendance-period-choice-readers-qualification`. Fresh unchanged
financial11 plus reader3 means14 business cases; function captures15 is a
different count. The source13 baseline's eventual qualification does not accept
this new reader source. Reader first-failure controls are preserved: old23PASS/
5readerFAIL after declaring a missing local name-table dependency, then the
first new-reader full28 run27PASS/1 local reinstall omission. A selected
DateStyle diagnostic retained its finally-masked aborted-transaction failure;
the new date comparison now uses Native canonical dates, not caller DateStyle.
All complete-suite assertions remain; selected diagnostics are not full-suite
or Native evidence. Final commands/counts live in the current local receipt.
