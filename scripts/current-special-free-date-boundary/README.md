# Special FREE date boundary

The existing pickup helper compares an inclusive DATE policy range directly to
a timestamp. That makes eligibility depend on the SQL session timezone and
can exclude the first hours or the final day of a valid policy.

This prepared change compares the physical timestamp's Asia/Jakarta DATE to
the inclusive policy dates. The exact actual function and all metadata agree
between the qualified SKU090b capture and current F42 S03 capture. One counted
predicate replacement preserves every other byte and all function privileges.
No category or rate is configured, no existing posted record is rewritten,
and no requirement to match accessory pickup to a PO or FG is introduced.

This engineering correction does not decide which policy governs GOOD when
Special/FREE eligibility changes between pickup and production. The owner has
not answered that question. The HPP-positive, reimbursement-zero GOOD/accrual/
recost/inverse path remains open. This code has not been installed on the
active combined candidate.

Generate `PREPARED.sql` with `python -B derive.py --emit PREPARED.sql` from this
directory. Run `test_dates.mjs` with `PGLITE_MODULE` pointing to the separately
installed `@electric-sql/pglite@0.3.14/dist/index.js`; an optional first argument
is the JSON evidence destination. These isolated PostgreSQL controls use only
artificial local fixtures and earn zero ERP Native/Auth/browser case credit.
