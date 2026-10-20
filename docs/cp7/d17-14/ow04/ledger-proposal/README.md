# OW04 immutable ledger and paired poster proposal

This directory is outside the product repository. Nothing here is installed.
Both SQL files deliberately raise before their DDL. The concrete prototype has
an INITIAL component validator and a private component-UUID-only posting entry;
it does not implement the owning return/refund/application/correction facade,
source collector, authority admission or deferred transaction closure. It
explicitly refuses ADJUSTMENT until its separately bound attribution protocol
exists. Root integrates only the complete feature.

| File | Concrete content |
| --- | --- |
| `01_immutable_facts.proposal.sql` | Append-only logical return families including empty, actual correction/replay members, financial cohorts, plans, complete source sidecars/dependencies, signed components, deterministic posting parts, actual journal links and signed consumption facts; private operation/posting scope tables |
| `02_uuid_poster.proposal.sql` | Initial plan/source/component/part validation, exact Native-cent line hashing, component UUID posting, actual RETURN journal hook with SALE book floor |
| `03_native_copy_transform.py` | Pure source transform functions for the exact private Native poster, RETURN hook and generic reverse protection; no DB calls or installer |
| `HELPER_EXPECTED.json`, `HELPER_RESULT.json`, `check_helpers.mjs` | Literal scalar expectations and isolated DDL/scalar checks |
| `STATIC_TRANSFORM_RESULT.json` | Exact-anchor transforms against accepted release sources; not an installed-function capture |
| `FIRST_STATIC_FAILURE.json`, `FIRST_HELPER_FAILURE.json` | Preserved first failures: outer-dollar-quote extraction and parenthesizing a CASE expression in PL/pgSQL |

## Financial facts and dates

For a sale, current effective paid is `P + U - I`: all actual active Native
payments, including advance-funded Native payments, plus incoming credit
applications minus **net retained signed credit
recognition**, including its linked adjustments exactly once. `I` is neither
remaining credit nor the sum of positive atoms. Refund/application changes
availability, not I. Do not both exclude an old recognition and subtract its
inverse. Current `AR = net invoice - effective paid`; reject a corrupt before
state (`AR<0`, `E<0`, `E>net`) instead of clamping it into new credit.

The independent kernel at `../kernel/kernel.sql` uses the exact six-key source
event protocol `{id,kind,amount,economic_date,transaction_date,source_sha256}`.
`NET` is signed sale/return AR and `FUNDING` is signed actual payments/incoming
applications, including original, inverse and bound restatement contributions.
Credit recognition is excluded from raw FUNDING. Every source event is visible
only where **both** dates have passed. For each joint cutoff,
`F=max(0,FUNDING-NET)`; the new-return target is the before/after difference and
components are its mixed two-axis finite differences. All retained source
events, including zero-effect and already-reversed originals, remain hashed.

The pure kernel emits exact two-decimal strings, canonical PG `jsonb::text`
vector hashes sorted by `id COLLATE "C"`, and the six component fields
`amount/economic_date/transaction_date/previous_economic_date/previous_transaction_date/corners`.
This prototype compares the FULL freshly rebuilt result and complete normalized
before/added support arrays, not only K or a selected funding row.

An initial K=0 with `+200@19/19,-200@20/20` still creates a real cohort, explicit
mode/account choice and dated recognition history. Current available/refundable
credit is zero. Only a truly empty component plan takes the ordinary return
path. Never turn the negative recognition component into a cash refund or a
Native payment reversal.

Economic dates remain actual source economic dates. A new RETURN journal's
derived book date is `max(current lawful resolver(return economic date), verified
causal source book floor)`. The latter requires actual immutable root SALE and
logical-return-family/correction lineage, including its applicable original
journal floors. A current leaf SALE alone can lose a root's later book floor
after reopen/replay. `return_causal_book_floor(uuid)` is a required unimplemented
interface; both its NULL result and a result before the actual linked SALE book
date are rejected. No convenient max of unrelated funding/reversal journals is
substituted for that source proof. Recognition retains its **exact recomputed
kernel pair**, subject to the current lawful open-period floor. A period change
invalidating any pair aborts/rebuilds the whole plan; it never independently
shifts some atoms. A blanket max of every supporting funding book day would
wrongly delay the early 100 in the split-funding case. No caller supplies a free
book date, account mapping or arbitrary journal lines to `post_component(uuid)`.

## Storage and private posting

`cent_amount` is unbounded `numeric` with finite/exact-cent checks. A bounded
`numeric(20,2)` would round `0.001` to `0.00` before a CHECK sees it. The Native
poster itself totals each journal in `numeric(20,2)`, whose largest cent value
is `999999999999999999.99`. A mixed-difference component can exceed that limit
even when return/net K fits. Its financial amount remains intact and exact.
The immutable part manifest uses largest Native-sized slices followed by the
exact remainder, preserving sign and the identical date pair. Parts sum exactly
to their component; no new product monetary cap or policy is introduced.

The posting entry accepts one component UUID, validates the entire plan and
manifest, and posts all its actual server-owned part UUIDs atomically. Native
source uniqueness is per part UUID. Every part links to its actual journal.
The owning request envelope owns committed replay; a component with any journal
history cannot be posted again, even after reversal. The reviewer binding must
cover the assigned immutable UUID manifest as well as monetary results.

Positive recognition posts Dr actual source AR / Cr selected credit liability;
negative recognition uses the exact opposite direction. The actual source AR
account and liability account snapshots are separate fields. The line helper
uses the AR account present on the actual RETURN journal; it does not look up a
new default. A scalar cohort prototype requires actual source/correction AR
provenance to remain on that same account. Reject a mixed/changed AR account
family until a source-bound per-component allocation exists; do not silently
reclassify a replay from the new current mapping into the old cohort account.

Credit uses/refunds are separate immutable positive consumption facts. Their
own inverse is a negative fact linked to exactly one real original, same cohort,
kind, amount, dimensions and permitted inverse timing. A negative arithmetic
input by itself is not authority to restore balance. The independent capacity
helper must receive complete retained signed recognition/consumption vectors
under all cohort/source locks. Require nonnegative source prefixes and enough
capacity over **all later joint cutoffs**, including current. Separate economic
and book margins can each pass while a joint rectangle is underfunded.

These SQL files do not supply a refund/application poster. Complete integration
must bind each such operation to its actual immutable event UUID, current owning
write permissions and explicit cash-out authority, current review/request,
actual customer/target ownership, real cash account/date and final dated cash
checks. The same restrictions apply inside named inverses and correction replay.
The browser receives no private schema/table/function access or raw line poster.

## Required source and authority boundary

`assert_owner_context`, `assert_return_owner_context`, `rebuild_locked_plan`,
`assert_source_admission`, `check_credit_account` and
`return_causal_book_floor` are required interfaces,
deliberately **not** implemented as permissive stubs. Existence of a context row
or a caller-set GUC never substitutes for current authority. Their implementation
must lock/recheck current permissions and complete source identity after waits,
under READ COMMITTED. Follow FG, then deterministically ordered source/header/
cohort/master rows, then period SHARE, then Native CASH advisory admission in its
journal-line AFTER INSERT guard. Include incoming-credit source/target sales and affected cohorts;
direct Native payment and prepayment paths need the same admission, not only the
public facade. Locked rebuild precedes source admission. Revalidation invoked
after period SHARE must already own its complete source lock set; it may not
discover/acquire earlier-order locks after that point. A changed lock manifest
aborts rather than attempts a new lock order. Final checks and request replay
recheck current authority too.

For a new-return INITIAL, source admission adds exactly this actual return NET event,
proves all preexisting I already reconciles the authoritative before profile,
and binds actual original/inverse/restatement facts across the full correction
root family. Do not collect only the currently active sale leaf or POSTED
payments: reversed originals can explain nonzero historical recognition. A first
financial cohort on an older registered family binds that family's complete T_i
target after the admitted mutation and explicit review; it does not allocate the
whole funding mutation's delta to that family.
Admission validates pending current-plan journals separately from retained
before history, so rechecking midway through a multi-part atomic post neither
counts unposted components as GL nor forgets already posted pending parts.

Arithmetic alone cannot mint credit from an arbitrary funding mutation. Example:
sale1000/pay1000@18, inverse−1000@20, late return200@19 gives current K0 but
`+200@19,-200@20`. Adding a new backdated payment800@18 passes the old current
payment cap yet would create raw baseline overflow800 before the return.
The source mutation must be refused, not allocate `+800@18,-800@20` into that
return cohort. Gross-before-returns overflow must remain zero at every joint
cutoff; a source contradiction is not an invitation to create a new liability.

The selected liability account follows the existing approved per-document Native
credit validation: active/postable LIABILITY/CREDIT, no cash/mapping/prepayment
collision, and reconciled tracked journal provenance. Current BB validation
knows BB lineage only; extend reconciliation to actual Native ledger sources
before sharing the account. Do not fake a migration batch/legacy return or
invent a global account default/expiry rule. Cash refund additionally requires
owning write rights plus the accepted explicit cash-out role; return create/post
permissions alone are insufficient.

Mandatory deferred closure (not implemented here) verifies exact source/support
coverage, initial cohort ownership/K, complete components/parts/journals, signed
current and both-date GL/AR/liability reconciliation, inverse provenance, final
joint capacities/cash checks, and no surviving private context/scope. No partial
ledger, RETURN/HPP/stock, refund or request receipt may commit on failure.

## Accepted attribution constraints; bound adjustment still required

The raw source kernel intentionally accepts signed compound additions; that does
not authorize attributing whole-invoice ΔF to one cohort. Root accepted an immutable
ordinal for **every logical return family**, including initially
empty returns, assigned under FG and preserved through return/note corrections:
`T_i = F(SALE+funding+families<=i) - F(SALE+funding+families<i)`.
Each target includes that family's actual signed original/inverse/restatement
events. A new appended return matches INITIAL D. Later mutations recompute all
affected targets; the posting adjustment is target components minus **all actual
retained cohort I components by exact pair**, never target minus original K or a
fresh whole-invoice delta allocated to one return.

Keep two concepts separate: immutable return-family registration needs no
account/mode; its financial cohort is created on the first nonempty recognition
effect and requires explicit mode/account then. A later payment can first expose
historical recognition for an initially empty family; the ordinary payment path
must hold for the owning settlement command when that choice is missing. Qualified
backfill must prove a unique source order or refuse; do not fabricate historical
posting order from convenient IDs/timestamps. The current concrete schema stores
separate family/member registration and one optional financial cohort per family.
Every Native posting route must register/admit its return, including empty target;
the actual RETURN journal hook therefore fails without typed owning context.
An ordinary empty-target return needs no mode/account/financial plan, but it
still receives family registration and the source SALE book floor. There is no
legacy poster fallback that bypasses those checks.

Two explicit accepted admission preconditions are necessary. Every logical family's
retained NET prefix must be nonpositive, and source corrections/restatements
must respect the original causal book floors. Otherwise a correction inverse
visible before its original book date can make an individual T_i negative even
when total NET/FUNDING and gross baseline pass. Inverses that extinguish credit
must leave all downstream consumers jointly funded, or require named dependent
undo/one atomic compound correction. A later return also depends on earlier
return-family inputs, including an earlier family's initially empty target.

The target-minus-retained-I protocol must bind the exact pure target result,
all prior signed recognition IDs/amounts/pairs/source hashes, full correction
lineage, per-pair difference components/corners and their digest. Recognition
components are not raw NET/FUNDING source events. No such new pure-kernel API is
invented here; `validate_component` explicitly refuses ADJUSTMENT rather than
pretend its INITIAL validator proves this additional contract.
Every later positive adjustment requires explicit fresh review; an original
REFUND choice never authorizes an automatic new refund on replay or adjustment.

Native correction composition also needs an explicit change. Existing note
correction replays returns **before** copied payments; recomputing paid-return
credit there yields zero and the later payment overpays the reduced note. Replay
actual funding first or use a fully bound source carry preserving original
settlement meaning, original mode/account, real source/journal pairs and named
inverse lineage. Do not replay an initial refund as fresh additional cash-out.
Ordinary undo uses its actual lawful inverse event timing; a historical correction
uses its specific source-bound restatement contract. Neither always negating the
original pairs nor always moving everything to today's economic date is safe.

## Exact Native capture and composition

All paths below are under `../../erp-d1714/` relative to this directory,
or can be opened at the absolute active repo path
`/workspace/scratch/9442228ed2dc/erp-d1714/`.

| Source | Exact anchor and implication |
| --- | --- |
| `supabase/release/cp6-t3/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql` | `erp.post_journal(text,uuid,date,text,jsonb)` 3956–4076; accepted after SHA `1f4b630c00147f88d195b3b365114eaecc60fdf3141859c384056423ae39f824`; cent canonicalization3985–4004, period SHARE4012, book resolver4056, actual entry4058, daily balances4067, shift audit4071 |
| `supabase/release/cp6-t3/20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql` | `erp.post_sales_return(uuid)` raw paid guard310–315; exactly one actual `erp.post_journal('SALES_RETURN',h.id,...)`414–417; change only that call's callee for the source SALE book-floor hook |
| `supabase/release/cp6-t3/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql` | `erp.reverse_journal(uuid,text)`5136–5167; exact early missing-source guard5148 followed by existing source protections; accepted installed SHA `9c3b04353530df3c22e601e59927321714a186cecb026f7b08ff76c0ebb7e396`; new credit source protections append there |
| Same 20ap source | `erp.post_sales_payment(uuid)` actual pair5038–5048 and immutable posting facts5050–5064; `erp.reverse_sales_payment(uuid,text)` facts/inverse5195–5224. Preserve both original and inverse facts, including allocation replacement pairs |
| `scripts/cp7-src/sales/correction.sql` | Native private-copy derivation145–179; actual snapshot247–253; inverse265–271; returns replay278–309 before payments311–325; existing restatement109–136 uses the ordinary resolver and cannot express an independently derived pair |
| `scripts/cp7-src/sales/return-correction.sql` | Private-copy derivation192–221; current Native inverse347–348/new return361–372; copied guard behavior must be composed, not missed by only patching public Native functions |
| `scripts/cp7-src/sales/payment-correction.sql` | Locks154–170, original inverse184, current restatement185–196, replacement200–203, final compound204; request replay current authority220–223 |
| `scripts/cp7-src/sales/chain-reversal.sql` | Current payment→return→sale loops156–173 need dependency-safe credit consumption/recognition/named source ordering |
| `scripts/cp7-src/finance/dated-guards.sql` | Signed original+inverse journals18–41; compound checks99–124 and cash lock132 remain effective |
| `scripts/cp6_bb_objects_financial.sql` | Per-document real account26–50; existing credit state319–331 and economic-only floor336–355; account admission357–374 must extend real provenance for Native, not fake BB lineage |

The derivation module's `Capture` is populated from its exact `CAPTURE_QUERY`:
`pg_get_functiondef`, `prosrc`, owner, sorted ACL, security-definer, volatility,
configuration. Compare it with the trusted approved predecessor manifest before
any transform. Post-journal and reverse constants are pinned above; post-return
must use the exact accepted **composed** current definition digest from the
owning CP7 phase, not a broad historic hash list and not a digest minted from
the candidate being checked.

Derive `_post_journal_bound(text,uuid,date,text,jsonb)` from that accepted Native
definition. Preserve Native language/security/config; owner is postgres, EXECUTE
only postgres. Its four exact source changes add typed admission before the
unchanged Native `require_internal`, replace only book assignment after Native's
period SHARE, and make shift audit accurately name the source-bound derived
profile with actual plan/component/part/hash context. Balancing, cent storage,
source uniqueness, AP guards, original entry/line INSERTs, accounting daily
balances and all existing cash/cutover triggers remain intact. The Native public
`post_journal` stays unchanged. No standalone caller-selected paired poster is
exposed and no role receives a context/GUC waiver around Native safeguards.

Protect recognition/apply/refund/credit-event-reverse source types in generic
`erp.reverse_journal`, and also every actual standard Native reversal descendant
through `reversal_of_id` or JOURNAL_REVERSAL source ID. A cycle-safe ancestry
predicate also protects registered component/consumption journals. Thus generic
reversal-of-reversal cannot restore balances without linked facts. Any additional
credit restatement journal must use a protected source type or immutable ledger
registration too. Their named owning undo creates verified linked facts;
generic undo cannot leave immutable credit facts claiming an unchanged balance.
The postgres-only Native internal reverse remains inaccessible to browser and
ordinary helper roles.

Compose shared effective-paid/dated source and scoped dependency guards before
both note and return-correction private copies are derived, or compose the exact
same final bodies into those copies and their source pins. Existing late F03
deltas and `cp7_note_report_bundle.py` expected-definition verifier must agree;
never weaken them to accept stale private copies. Extend the complete internal
guard context probe only with owning typed credit admission and current fine
permissions, not an unrelated module's context row.

After complete installation, verify exact generated target definition SHA,
owner/ACL/security/config against the manifest and verify the original Native
poster unchanged. Check no client/service/capture/read/write helper can execute
the private poster or mutate facts/context. Raw release-file digests in the
static receipt are intentionally distinct from `pg_get_functiondef` digests;
the static command must never be used as an authoritative installed capture.

Use `docs/cp7/d17-14/ow04/SETTLEMENT_SOURCE_MAP.md` for the complete canonical
reader/guard/detector integration register. There is no single existing shared
effective-paid helper to patch. Add one canonical source and route Native
post/inverse/status, prepayment targets, AR/report/history/reminder and integrity
detectors through it; keep `sale_net_total` as gross minus returns. In particular,
run_v253 overpay and `_v268_financial_report_checks_pre_scope` raw AR checks must
be changed with their callers; do not filter false positives out of the verifier.

## Evidence limits and required whole-feature cases

`node check_helpers.mjs` passed 26 isolated checks. A fresh in-memory catalogue
has only synthetic FK/composite types and **zero** ERP/auth functions, Native
writers, permissions or source data. It creates the two proposal DDLs after
removing their barriers in that temporary copy only; it exercises scalar exact
cents/canonical line hashes/mechanical parts, checks the UUID-only signature and
executes the ancestry predicate over eight synthetic journal rows, including
reversal-of-reversal, one-pointer lineage and an unprotected malformed cycle.
It does not call a posting, authority, source-collector or correction function.
The preserved first helper failure was a missing CASE parenthesis; it was fixed
before the passing receipt. Python static source transforms pass on all three
release definitions and reject duplicated anchors. Neither result is Native
execution, product evidence or a paid-return completion claim.

Complete integrated verification still needs the existing five dated goldens;
historical funding inverse with negative atoms and net-zero cohort; crossed
joint capacity; RETURN source SALE book floor after reopen; later return changes
and initially empty family registration; unchanged baseline/individual family
prefix refusal; mixed account provenance; late funding introducing first choice;
payment/return/note corrections and replay preserving settlements exactly once;
direct Native/prepayment/generic-reverse bypass attempts; revoke/period/source
changes while waiting; and atomic rollback of RETURN stock/HPP/journals, credit,
cash and request receipts. The existing no-settlement paid-return refusal remains
a negative control until the complete authorized route is installed.
