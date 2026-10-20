# Second browser CI failure: datetime-local input precision

Candidate 6d9c58e1ae95d18225054da7b8b71c2efce39822, tree
ee7cc59dd0e4f4381a9deda7b062389bc25060a9,
run 39503792170/job 118907533136 produced 4 INCOMPLETE, 0 PASS.
All four cases reached real Auth and the return form, then Playwright rejected
the fixture's datetime-local value with seconds as Malformed value. Four real
test users and 44 loopback responses were observed; no settlement was reached.
The complete original runtime and CI_6D9C_BROWSER_SECOND_FAILURE.json retain
that result. CP6 restoration and advisors passed; writer_runtime:false made
the outer package fail, as required.

The fixture now emits the minute precision used by cp6WibDateTimeInput:
YYYY-MM-DDTHH:mm. These prospective inputs already have seconds and
microseconds equal to zero, so removing their display suffix changes no
instant. The wire UTC timestamps, frozen money/date goldens, original posted
facts, four case IDs, browser assertions and BROWSER_EXPECTED.json remain
unchanged. src/cp6BusinessTime.test.ts separately specifies that both minute
and second strings convert to their corresponding exact WIB instant.

This is a writer qualification-input repair, not evidence that the four
journeys pass. A fresh real-browser run is required. The previous SKU failure
and its complete original runtime remain retained without reclassification.
OW04 remains open and production_go:false.
