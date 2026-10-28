# OW08b vendor receivable successor — prepared, NOT Native qualified

Owner29 October confirms BOTH next-invoice application and cash/bank refund. Base A70ed847e includes accepted B delivery; B is not a pending dependency for this scope.

The optional provider adds seven counted BD function changes and twelve private helpers in one private schema. Three append-only source/refund/reversal registers link existing invoices, applications and Native journals; they are not a second ledger. No new public RPC, Native journal engine, HPP formula, stock engine or scheduler.

A downward correction with an explicit dedicated ASSET/DEBIT account enters AR; existing BD credit first settles the origin, and can then settle another invoice/opening payable or receive a bank refund. The old covered-payable path remains when no AR account is selected. Refund uses consume the same source credit; the existing request envelope checks current permissions before replay. Native inverses retain original receipts. Every AR line must trace to a source/application/refund/Native inverse, and economic/book-date balances must remain nonnegative. Account IDs are selected from eligible existing masters, never invented.

UI adds dedicated account selection, cash/bank receipt, linked reversal and strict versioned response parsing. Existing production recovery now recognizes both new actions and retains the same UUID/payload on lost response. Older backends do not expose the feature.

Local checks use explicit PGlite Native test doubles and real retained BD application/request code, plus unit/DOM recovery tests. They are NOT actual Auth, Native installation, concurrent-session, Drive, delivery or production proof. First local failures are retained: test path/parameter typing/missing unused CASE dependencies, then the missing production-recovery action whitelist (fixed), and a test's wrong pending-envelope lookup (fixed).

Actual qualifier reuses the aligned full installer, source admission, all22 catalogs, streamed whole-data guard, baseline dump/role/advisor/package restores. Seven Native cases and a committed used-inverse witness are prepared under scripts/current-vendor-receivable-qualification. Runtime outcome is separate and must be inspected before integration. No default registration or production approval.

Still required for final closure: actual Native/restore result, concurrent application/refund and access-revocation proof, actual UI/visual journeys for the changed money flow, source-consistent final installer and independent acceptance. Frozen backend3194/B browser evidence retains its original source/coverage and does not automatically qualify this delta.


## Successor after the first Native attempt (29 October)

First attempt f30ffc8d / run40741343738 / job123003448565 is
FAILURE/INCOMPLETE: six Native cases PASS, one assertion after refund reversal
incomplete. Baseline full22/data/sequences/roles/CP6/advisors and four package
gates PASS; writer_runtime failed. Do not relabel it as qualified.

The new observer serializes complete payment rows under UTC and restores the
previous timezone in finally (E25z). The retained refusal helper selects UTC;
raw to_jsonb(timestamptz) differs across WIB/UTC even for unchanged rows, as
reproduced locally. All original money, history, date and refusal expectations
are retained; the inverse assertions now retain actual observed states.
Native execution must still establish the final result. Product SQL, the
seven derived business functions and frontend source are byte-identical to f30.
The exact first incomplete Original is admitted before DB work, and all seven
cases run afresh because each uses the corrected observer. No fresh race,
Auth/browser, independent acceptance or production GO is claimed.
