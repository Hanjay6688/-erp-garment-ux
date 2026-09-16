# CP6 — original UI on a disposable target

Owner approved adding the dedicated disposable UI target after the final-audit
checkpoint reported the UI target-guard gap. This is a frontend writer successor,
not an independent acceptance of its own changes. CP7 is not implemented.
`production_go:false`.

Backend candidate remains AI-R2 `25fa4736329e5148dfdb3572bc169952cba23251`, tree
`a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d`. Starting competition head is
`9f884fbb27bdb92d6ee63f60333e007dc36f3f1c`, tree
`b4cf1e5d6c8aff531470af01dcdb4d146b4fca7f`. Source pins and the CI artifact identify
the separate frontend/harness candidate. No SQL migration or function changes.

The build mode `cp6-disposable-test` only accepts page origin
`http://127.0.0.1:4176`, API origin `http://127.0.0.1:54328`, and a local anon key.
Normal build/deploy rejects this runtime. Its output is a separate temporary
directory removed after testing. A transparent loopback proxy forwards Auth to
the local Auth service and RPCs to the disposable clone's original public API.
No business API responses are mocked. Schema permissions are not expanded.

Planned evidence: original login, anonymous/unmapped/inactive/viewer restrictions;
granular operator on desktop and owner on mobile; ten physical pieces at rate 7,
partial receipt of eight, two QC postings of five and three, parent reversal
blocked by posted children, linked reversal back to zero balances, double submit,
and a paid failed-wash commit whose HTTP response is deliberately lost before
reconciliation with the original UUID. The lost-response control tests transport
recovery; it is not evidence that an ordinary ERP transaction is inconsistent.
Each completed case is persisted before the next one. Unfinished cases stay
INCOMPLETE. Financial arithmetic is independent of the writer's PASS list.

Cleanup closes browser, preview and proxy; deletes temporary Auth users/sessions;
retains posted business history until the whole disposable clone is removed;
then runs the unchanged AI-to-AH restoration comparison and container cleanup.
Credentials, tokens, traces, browser storage, and database dumps are not artifacts.

Scope correction from the restored owner master context
`ERP_GARMENT_MASTER_CONTEXT_2026-09-15_AD.md` (Library version 1, lines 1960–2004):
CP6 is Laundry → QC → exact-size Final SKU/FG. Remaining Sales/invoice,
payroll/Nota, HPP/Finance/reporting connections and full dummy flow through journals
and reports are explicitly CP7 acceptance. The older blanket UI-gap statement
must be read with that contract. This does not remove CP6's backend accounting,
stock, HPP, correction or report-consistency obligations.

Opening/import rules in section 21 require preview, per-row errors, totals
reconciliation, idempotency, manifest and rollback/recovery. Import obligations
need separate source-to-path inventory; this document does not silently relabel
unproven import work as CP7 or N/A.

Run 35123732959 stopped during the source guard, before browser installation or
database startup: adding local output paths to the frozen predecessor `.gitignore`
was rejected. The predecessor file is restored byte-for-byte; the source guard is
unchanged. All 226 unit cases passed before that failure. No UI/business execution
is claimed for that run. Its cleanup-only artifact is 10457879554 (288 bytes),
GitHub-reported SHA-256 `c1abb38719dee9f087cf1a208ffd55620a978780b56c90964f52b0ceca72ebdc`.

Current execution status: PENDING_CI. The earlier native/HTTP audit and historical
460-case reconciliation remain in `docs/cp6-final-audit-checkpoint.md` and
`docs/evidence/cp6-final-audit-reconciliation.json`. No new PASS is claimed here.
