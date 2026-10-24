# Retained CP6 transactions in two real sessions

36 distinct schedules: AF4 + AG4 + AH8 + AI8 + independent-AI12. The four
AF schedules also occur in the historical AG suite and the eight AH schedules
in AI; they are executed once per boundary and never counted twice.
Before CP7 and on complete current A/B: 72 actual schedules, 0 new business cases.

Each case uses a fresh physical database copy. The retained copy-authority
helper proves every one of the 22 catalog groups, including actual database
owner/ACL, before fixture setup. Only the fixed local copy endpoint is rebound
for the unchanged original session helpers. Original lock waits, commit/abort,
error texts, quantities and money assertions stay. Original CONTROL_PASS results
are preserved whole and admitted only when that exact original status occurs.
Original fixture clocks and opening periods stay family-specific. The source
installation is never used for committed fixtures; copies/session leaks and
source CP6 restore are checked. This is writer Native SQL evidence with explicit
test-only schema USAGE, not Auth/browser, original pre-AE bug reproduction,
maintenance guards, independent audit acceptance or production readiness.

First run1273950b remains INCOMPLETE: AF4PASS and32INCOMPLETE on each boundary.
The next fixture prepares only existing seed prerequisites before each original
schedule, using the same Native helper as AI135. It retains the complete
original exception and preparation even when a schedule fails; the old generic
runner's3000-character truncation no longer discards the cause. No original
lock, money, status or refusal assertion is changed or waived.
