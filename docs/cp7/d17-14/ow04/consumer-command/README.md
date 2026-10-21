# Existing OW04 credit use and named undo: preimplementation numbers

These nine literal arithmetic expectations are recorded before changing the
financial writers. They do not add Native cases, implement APPLY, or close OW04.
All amounts are exact decimal strings and are checked independently with Decimal.
The accepted ledger contract remains the authority; no expiry/default account or
new date policy is introduced. These are internal writer expectations, not an
independent auditor acceptance.

The main chain is: source credit200 → apply80 → apply120 → reject another0.01
→ undo exactly the original80 → net use120. Replay keeps one effect. Undoing
both applications permits an ordinary lawful source inverse only if the full
dated profile remains funded; a historical restatement must still fund earlier
consumption, even when it was later undone.

Before this chain can be exposed, the current explicit incoming-application,
second-consumption and provenance refusals in coordinator/05_factual_profile.sql
must become complete factual checks. Both source and target readers/status,
Native payment/inverse/prepayment guards, immutable materialization provenance,
all affected family targets, dated capacity, generic-reversal protection,
current permissions, owning UUID protocol and deferred closure are part of that
same change. Removing the present refusal alone is not implementation.

The active backup candidate and all qualified product bytes are untouched by
this documentation. Formal CP7C and operational backup qualification have not
started; the current backup test is the earlier bounded OW04 restore check.
