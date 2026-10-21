# First executed real Auth HTTP14 —13 PASS /1 INCOMPLETE, retained

Candidate `86e3ba320fc0cf50c48c6b590ac8453d3f6cea27`, tree
`9a7b909ddc17cef2c293b0313062f049c3c650fa`.
[Run39656545087](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39656545087),
job119418228577, workflow failure. All14 cases actually ran; original qualifier
INCOMPLETE.13 PASS/1 INCOMPLETE. Auth user counts restored, HTTP copy/container
removed, exact primary consumer/predecessor/CP6 restore and advisor gate passed.

Actual Auth/PostgREST commit+fresh-connection receipt/read/replay passed for
APPLY, REFUND, their named UNDOs and original initial-refund UNDO. Changed request,
stale review, anonymous, revoked membership, caller book-date, invented partial
UNDO, second UNDO and true STAFF cash-out restrictions passed.

The remaining case received the correct atomic-overdraw rejection message
`CP7_CREDIT_CONSUMER_INSUFFICIENT_DATED_SOURCE_CAPACITY` with P0001/HTTP400.
Its test mistakenly expected only the suffix `INSUFFICIENT_DATED_SOURCE_CAPACITY`.
The exact response assertion stopped before this case's subsequent unchanged
state assertion, so it remains INCOMPLETE and must be run again.

The original unchanged pinned product source
`consumer/04_credit_book_bound.sql` line50 already declares the full message.
Correct the test to compare that exact full message and explicitly P0001, retaining
HTTP400 and complete before/after state equality. No substring/any-error acceptance,
test removal, product SQL or money/economic/book expectation change is allowed.

Artifact12371099705 ZIP1633930bytes client SHA256
`4380b0c28f3abbd06dc198f1eed7caff0a31114da846dbbae351ada8990d0858`.
Main original report268847bytes SHA256
`a11219466ed3eac66f8304bc0d18dcdd9074f588128f315dd79c0606e25f3ecd`.
All5 original JSON streams preserved unchanged gzip with extraction receipt.
Native18 remains18/18 PASS, not rerun or relabelled by this HTTP group.
No whole OW04, browser/race, independent acceptance, production or CP7C claim.
