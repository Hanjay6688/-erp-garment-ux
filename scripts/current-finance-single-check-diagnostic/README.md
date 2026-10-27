# Prepared single-check experiment — Writer A

PREPARED, NOT EXECUTED. Exact parent evidence is accepted; first diagnostic execution is admitted. No speed improvement,
financial acceptance, timeout change, product adoption or factory completion
is claimed. The first parent953b87c0 is INCOMPLETE; successor0bccf142/run40519853334
passed13 Native cases and1actual cron. This diagnostic has not run yet.

The existing accepted d05c568c diagnostic (artifact12684969367, Original
SHA256 c9c9d9898126e205bbbf424e1106587c69e8e1517aecc6ac02bb938392ab9efb)
measured the readonly candidate at14001.089ms for1200SKU x3sizes. Its profile
still shows two run_v268_financial_report_checks calls,13861.547911ms total:
one from readiness/blockers and one for warning rows. These are OLD measured
values, not progress from this preparation. Factory diagnostics already used
a30000ms per-statement limit; this experiment keeps that exact limit and8000ms
for both small fixtures. Production limits and schedules stay unchanged.

single_check.py derives the exact current BF blockers plus OW07 and unknown
wash extensions. It changes only the checker row source in a new private
sibling, passes the resulting rows through an unchanged readiness calculation,
and shares them with the warning query inside the existing date-only report
helper. All counts, details (TEXT), warning exclusions, dates, permissions,
UNKNOWN values, WIP/HPP rules and Native close/preflight commands are retained.
Two internal helper functions cannot be called by browser, finance-reader or
worker roles; callers never supply a cached check result. Nothing survives
beyond the statement. The existing helper keeps its owner, ACL and settings.

The paired harness derives from the accepted diagnostic with explicit changes
in ORIGIN.json. Its baseline is the composed CURRENT READONLY reader (two
checker calls), not the older three-call writer-backed reader. It compares
all report fields except report.captured_at and exact source-family counts,
requires one actual checker call, records table write attempts and timings,
and rolls back the complete catalog/data/sequence delta after every measure.
The Native small, PRICE_PERCENT and1200x3factory fixtures are retained. No
minimum speedup is assumed. If timing worsens or any figure differs, keep the
first result and investigate. The complete outer baseline restore is required.
