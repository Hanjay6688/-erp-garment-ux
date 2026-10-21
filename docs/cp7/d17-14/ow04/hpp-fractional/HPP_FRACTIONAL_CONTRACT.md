# OW04 cumulative HPP: writer contract and qualification scope

Owner's authorized OW04 work continues after each checkpoint. This change is
internal writer work, not independent acceptance or permission to deploy.

The old initial-return predictor accepted only per-piece cent costs and
assumed an equal FG debit / COGS credit. Actual Native returns calculate
cumulative FG, COGS and OTHER targets. Their marginal can contain a rounding
cent in either OTHER direction, even when the selected unit cost is cents.

- PO: round the pooled raw production/conversion source value, pooled owned
  value and pooled net-sold value at the Native BE boundaries.
- Non-PO: retain conversion-adjusted raw source value, round each lot at those
  boundaries, then sum the product. Aggregate all requested quantities per lot
  before calculating the hypothetical after-state.
- Reconcile the before target with the actual ledger. PO additionally retains
  the existing saved-state refusal, including source output quantity. A stale
  saved state is not silently repaired by accepting the return.
- Emit the full signed vector after target minus before ledger. Preserve
  product/PO/customer dimensions, OTHER_EXPENSE debits and OTHER_INCOME credits.
  Existing actual Native journal-line/date comparisons remain authoritative.
- Public quote v1 keeps its shape. `hpp_amount` means the sum of positive
  debit-side HPP entries within each group, then the sum across groups before
  netting. It is not FG value, unit HPP or a valuation authority. This keeps
  HPP-only journals visible when FG itself has zero delta.
- A zero refund and zero full HPP vector with a positive actual six-decimal
  frozen unit snapshot still refuses with
  `CP7_CREDIT_POSITIVE_HPP_ZERO_VECTOR_UNPROVEN`. Its complete historical
  absence proof remains a separate open boundary. Do not manufacture a journal,
  zero a positive snapshot, or reject a nonzero financial return for this
  particular absence-proof reason.

The private PO readers reproduce Native20d historical allocation and the final
Native20ap/e book, including inverses, untagged history, BS-value exclusion and
residual close. Their four server-resolved account UUIDs remove guarded lookup
calls without creating Native admission. An install guard checks actual
predecessor bodies and metadata; private ownership/ACL inventory remains exact.

Source protection includes whole-PO sibling lot/HPP locks, post-wait lock-set
rereads, raw versions and before/after targets, saved state, and full supporting
stock/allocation/return/conversion/cost/journal identity hashes. Hash support
before and after the separate READ COMMITTED calculation statements; refuse a
change. Exclude only transient return DRAFTs from the historical return support.
Bind the HPP mapping/account facts used for the book and reread them after the
existing globally ordered account locks, before taking period SHARE.

`EXPECTED_LITERAL.json` is the independently declared arithmetic matrix.
`local_projection_recheck.mjs` executes22 scopes on synthetic PGlite relations;
it does not qualify Native writers, privileges, dates, races or the browser.
Native fractional expectations and actual writer fixtures are separately
declared before CI. Keep all old44 expected cases byte-identical. A fresh
Native pass and exact new-core binding are required before HTTP/browser reuse
or new execution can qualify this changed candidate.

OW04 remains OPEN: corrected/consumed families and other explicitly unsupported
routes are not made complete by this arithmetic extension. The former browser
and HTTP receipts remain evidence of their old exact candidates. No speed,
feature-complete, audit-complete or production-go claim follows from local
arithmetic or a reviewer's agreement.
