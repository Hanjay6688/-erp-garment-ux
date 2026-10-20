# Narrow paired-date source review

Classification: independent source review of an uninstalled proposal, not a
Native execution result. No active repository files were changed. Literal
ordinal expectations were locked separately in `EXPECTED.json` before peer
exchange or ordinal-model execution.

Reviewed proposal snapshots:

| File | SHA-256 |
| --- | --- |
| `ow04-proposals/ledger/02_uuid_poster.proposal.sql` | `942f24cd55227593c352c6d01759d1cef18409309615af9d24145fbe057bdb69` |
| `ow04-proposals/ledger/03_native_copy_transform.py` | `ce09f3b09f26f311b3d413e54414487ca2b0668317f858fdc9da59d413a69238` |

## What the source establishes

`erp.post_journal` in Native release `20ac_cp6_temporal_surface_closure.sql`
canonicalizes every debit/credit to stored exact cents, refuses negative or
non-finite line values, checks balanced positive journal totals and source
uniqueness, obtains `accounting_period_control FOR SHARE`, resolves the input
economic date through the current accounting-period resolver, stores the actual
economic/book pair, inserts unchanged journal lines, and updates daily balances
on that actual book date. It does not itself bind a child journal's book date to
the original SALE or return-family book date.

The prospective private transform changes only admission before
`require_internal`, the book-date assignment, and the truthful shifted-date
audit context/reason. `PAIRED_TRANSFORM_BODY.diff` makes those source deltas
reviewable. The static check passed and rejected duplicated exact anchors. It
does not substitute for capturing and approving `pg_get_functiondef`, `prosrc`,
owner, ACL, security configuration, and the composed current predecessor.

The prospective UUID poster binds the part/component/source IDs, actor, request,
transaction/backend context, economic date, book date, and Native-cent line hash.
It recomputes source/component admission before posting and again at the date
assignment after Native's period lock. Component journals preserve the exact
recomputed kernel pair and are checked against the actual inserted journal pair.
This correctly avoids shifting an early component to the latest book date of
every supporting payment.

## Return/root-floor gap in the reviewed proposal

`post_return_journal` and the RETURN branch of `bound_book_date` currently use
`max(current lawful resolver(return economic date), linked active SALE book)`.
They do not yet bind immutable SALE-root and return-family-root book floors.
There is also no prospective inverse/restatement posting branch in the reviewed
file. The draft explicitly refuses unfinished ADJUSTMENT admission rather than
silently authorizing it.

For a qualified correction lineage with SALE-root pair `17/20`, corrected
active SALE pair `17/17`, return-family-root pair `19/22`, and lawful resolver
result `19`, a new family replacement on economic day19 must have book day22
under the accepted root-floor constraint. The reviewed leaf-only expression
returns19. This is a concrete expression-level counter, not evidence that a
completed Native OW04 implementation accepted the request.

The floor must come from the exact immutable root journals and proven Native
correction/replay membership, including reversed original rows. Inferring roots
from date/UUID sorting or selecting only the active leaf is insufficient. A new
return's physical/economic date still comes from its explicitly reviewed Native
source. This review does not impose the old return's physical date on a
legitimate corrected physical input.

## Inverse and restatement gap is broader than ordinary undo

Native `20ap.reverse_journal` is a protected-source wrapper around
`_cp3_r4_reverse_journal_internal`. `20ap.reverse_sales_payment` validates immutable
original/inverse facts and explicitly tests inverse economic/posting chronology.
Those wrappers alone do not establish the private primitive's complete book
date behavior. A full local capture of that private body was not available in
the reviewed repository sources; its exact approved body/hash must be checked
before implementation claims are made.

The actual CP7 source provides a separate concrete hazard regardless of that
unknown primitive body. Both `cp7_note.restate_reversal` in
`scripts/cp7-src/sales/correction.sql` and
`cp7_sales_return_correction.restate_reversal` in
`scripts/cp7-src/sales/return-correction.sql` post two source-owned journals
through ordinary `erp.post_journal`: a neutralizer at the Native inverse's
economic date and an effective inverse at the original economic date. After a
period reopen, the effective inverse can therefore receive a newly earlier book
date than its own original journal.

Example: an original family RETURN is `-100@19/22`. Its Native inverse and exact
neutralizer cancel at a later pair. An effective `+100@19/19` after reopen becomes
visible before the original's book22, making that family's cumulative NET
positive at a joint prefix. With sale1000/funding1000 and an earlier return200,
the otherwise aggregate-valid target for this family becomes `-100` at20/20.
Ordinary inverse chronology alone cannot close this hole.

All real original, inverse, neutralizer, and effective/restatement contributions
must therefore be source-bound. Ordinary inverses cannot precede their original
on either axis. Correction neutralizers must derive their economic date and
book floor from the actual Native inverse pair; effective inverses derive those
from the original source pair. Both also honor the lawful current period floor,
and their actual inserted pairs remain separate immutable source events.
Replacement RETURN/SALE postings also retain their proven
logical root book floors. Recheck the actual pair after posting. Current period
changes require replan/refusal; they never authorize rewriting old source dates.

## Required source invariants

The arithmetic admission checks remain necessary independently of the poster:
`F(noReturns)=0` at every joint prefix; every logical family's cumulative NET is
nonpositive at every joint prefix; before/after aggregate NET and FUNDING are
nonnegative; cohort targets and all signed retained recognition reconcile; and
every cohort's real consumption/inverse history remains supported at all
affected later joint prefixes. Hashes prove identity only when the collector
bound them to the complete authoritative source under its owning locks.

The ordinal literal fixtures include both the valid later payment400 case and
the noncausal inverse counter. Their expected values do not rely on the proposed
poster having already implemented these constraints.

## Subsequent source qualification and proposal repair

The baseline fixture
`supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz` contains the
full private reverse body. It locks the original POSTED journal, flips its exact
lines, calls `erp.post_journal('JOURNAL_REVERSAL', original_uuid, CURRENT_DATE,
...)`, marks the original REVERSED, and binds `reversal_of_id` on the inverse.
The exact first `$function$` pair was extracted to
`BASELINE_PRIVATE_REVERSE.source.txt`; the body is on one line in the fixture.

Declared migration `20u` changes that one CURRENT_DATE to canonical business
date of `current_timestamp`; `20ab` changes the one clock to
`statement_timestamp()`. Those clock rewrites do not add an original book-date
floor. `20ac` pins the accepted current function-definition digest
`2996d1c16396768097306556b5916ba93996d2ff451f3c5e7cd35deea7a3ac6f`
and postgres-only ACL. This is a qualified source-chain trace; it is not a
claim that the extracted/reconstructed fixture text equals current
`pg_get_functiondef`. `PRIVATE_REVERSE_SOURCE_RECEIPT.json` keeps those hashes
and evidence scopes separate. A current capture remains required.

After the leaf-only counter, the ledger reviewer changed the RETURN hook and
post-period-lock recheck to require
`cp7_credit.return_causal_book_floor(return_uuid)` with a non-null result at least
the active SALE's actual book date. Both use `max(lawful, authoritative causal
floor)`. The legacy no-context bypass was also replaced by an owner-context
refusal, so an empty recognition target cannot bypass ordinary family admission.
The authoritative floor helper is explicitly unresolved and unimplemented in
the proposal. Thus the leaf-only expression is withdrawn from the revised
poster, while real lineage/root-floor proof remains a whole-feature integration
requirement. The rechecked proposal digest is in the source receipt.
