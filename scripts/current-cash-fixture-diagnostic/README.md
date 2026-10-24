# Three original financial-readiness diagnostics

Crossflow142 recorded CASH_LINKED:1, CASH_LINKED:4 and H_R02 as INCOMPLETE in
both baseline and current. Their historical assertions omitted the actual
financial reports, so the reason is not yet established by runtime evidence.

This diagnostic calls the exact retained crossflow case factory and fixtures,
selecting only those three IDs. If an original operation raises, it preserves
its full error and traceback, then reads the same report dates/context before
the existing strict runner rolls the case back. It never completes extra work,
changes a financial expectation, relabels a failure or decides owner policy.
An SQL-aborted transaction is recorded without attempted diagnostic reads.

Baseline/current results remain whatever the original oracles report. Complete
backup recovery, bounded qualifier lock preparation, used guard, full22/data/
sequence restoration, CP6 and advisor checks remain required. This is diagnostic
evidence, no new business case, browser proof or independent acceptance.
