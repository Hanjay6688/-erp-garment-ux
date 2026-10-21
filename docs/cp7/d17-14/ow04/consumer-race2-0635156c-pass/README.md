# Actual consumer SQL races: 2/2 PASS

Candidate `0635156cc06842c59d5e2eb403a956c65f54b8d4`, full tree
`f0d4e16f42f6e02087e63f1370ff6bbdc6612cb0`.
[Run 39661436474](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39661436474),
job `119435161787`, original report status **PASS**, exactly two declared real-session races.

Both workers were actually observed blocked by their holder. Same saved UUID
replayed the identical committed reply, with one request/operation/event/journal.
A different UUID using the old quote was refused with exact
`P0001 / CP7_CREDIT_CONSUMER_REVIEW_CHANGED`, with no loser orphan or effect.
Full final Native/private state equalled the holder's state. Source available
120.00 / consumption 80.00, target AR 420.00, cash 1000.00, exactly as frozen
before implementation. Fresh review used the actual updated invoice versions.
No leaked sessions; per-race copied databases removed (remaining 0). Exact
preuse consumer removal, predecessor/CP6 restoration and advisor gates passed.

These are authenticated **SQL fixtures with an explicitly declared test-only
ERP USAGE grant**, not genuine Auth/browser or load evidence. They reuse the
exact prior actual Auth14 PASS and Native18 source receipts; neither suite was
rerun or added to these two counts. No financial source changed from those
qualifications. Complete OW04, general adapters, UI/recovery/browser, current
Native87 regression and performance remain open. CP7C/production_go=false.

Artifact `12374586770`, ZIP 1,633,894 bytes, client verified SHA-256:
`113cdb7c282ab993d033bf8dd17785a1872f6e399a4ee2c70e07f0752c268402`.
Original main report 262,978 bytes, SHA-256:
`f25f75ddeee4e889b2a1164c902a0db7dd6964045c90b32b3fb34e6ec51c09bc`.
All five original JSON streams are retained unchanged in deterministic gzip
files; the extraction receipt binds every raw and compressed byte hash. No
financial original was parsed and reserialized for preservation.
