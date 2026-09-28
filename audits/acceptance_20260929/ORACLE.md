# Independent acceptance retest — 29 September 2026

CP6 candidate: fab23e77669f899594f983b41a6301c32246958b.
CP7 candidate: fa0ed346c322b8f24924f19f3a39f4117e6a0068.
No product edits, production writes, merge or deployment.

This is a disclosed retest, not a blind audit. The original three conversion
probes and the original seven CP7 probes must remain byte-identical. The writer
fixture builders are reused; the four microsecond-boundary expectations below
are independently authored. The four writer contention schedules and populated
Grade B scenario are rerun by the auditor but retain their writer provenance.

1. All three original CP6 probes must PASS on the actual 30-file package.
2. Both source and destination identities must reject a master edit at T-1us
   and T exactly after a conversion is POSTED, also when that document was
   REVERSED. Every refusal must leave versions, document, stock, money and HPP
   grouping unchanged.
3. T+1us is a legitimate later change. It must be accepted, retain the exact
   document and its original labels at T, and make the new identity effective
   from T+1us. Replaying that exact request must not add another version.
4. A later range move must not prevent conversion reversal; stock and the
   FG/COGS/WIP balances return exactly to their pre-conversion state.
5. Conversion/master contention must serialize in both orders, with commit and
   abort. A populated Grade B return must partition quantities/values correctly.
6. Original CP7 comparison probe must pass; OWNER retains its authorized data,
   OPERATIONS and DENIED do not retain restricted comparison data, and source
   objects remain unchanged. The separate shell still uses synthetic data.

Any business failure remains FAIL. Missing fixture prerequisites remain
INCOMPLETE and are never converted into a product defect or silently skipped.
