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
staged receipts of eight and two, QC postings of five, three and two, parent reversal
blocked by posted children, linked reversal back to zero balances, double submit,
and a paid failed-wash commit whose HTTP response is deliberately lost before
page reload and reconciliation with the original persisted UUID. The lost-response control tests transport
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

Run 35124061446 completed the native combined 142, staged-invoice 16, work 23,
two-session 12 and Auth/HTTP 95 stages. UI stopped at unmapped-account login after
1/28 cases (anonymous login page). UI cleanup, clone disposal and AI→AH restoration
completed. The test proxy omitted Auth's `X-Supabase-Api-Version` CORS header;
this is a harness transport defect, not a qualified ERP posting bug. The header
is now passed through, browser transport failures are recorded without payloads,
and label selectors use the original accessible names. CodeQL run 35124061384
succeeded. Artifact 10459275971 is 2541090 bytes; GitHub-reported SHA-256:
`539e204978506b71c9f5c4bf31132aa80895ddb0d1a22f33147d51601789a7c0`.
The final runner expands the receipt chain to 8+2 and QC to 5+3+2 (36 planned
cases), including browser reload after the deliberately lost response.

Import inventory: `scripts/cp6_ac_independent_audit.py` inserts synthetic
`migration_staging_rows` already marked VALID, then calls
`erp.prepare_migration_opening_balance`, `erp.post_opening_balance`, and
`erp.finalize_migration_batch`. The combined native family retains direct/import
opening cases. No CSV parser, file input, or staging/finalize browser caller was
found in `src` at this candidate. This is a missing executable application path;
native staging evidence does not close CSV transport. Section 21 of the owner
master binds these rules to opening/import and cutover, without assigning a
separate CSV-upload deliverable explicitly to CP6. Preserve that scope question;
do not infer N/A or implement a new import product during this audit.

Run 35125003066 / candidate a4d45ef4742d2b8b14a92c631a6dd0db84b3accb:
the Auth version-header correction alone did not close browser transport. UI
remained 1/36, with `/auth/v1/token` reporting `net::ERR_FAILED`. The proxy also
combined lowercase upstream CORS headers with mixed-case local headers, leaving
duplicate origin values. It now replaces headers consistently and checks the
real Auth health response and preflight before opening the browser. This still
requires a successful browser rerun; it is not an ERP transaction finding.

The same run crossed Jakarta midnight (combined native stage 16:59:15–17:00:34
UTC). It completed 119 PASS and 23 FAIL: 16 explicit
`AA_INVOICE_DAY_CHANGED_REQUIRES_SEPARATE_MIDNIGHT_CASE`, three cash reversal-date
expectations, and four previously-future payment dates that became today's date.
The latter seven expectations use the phase-start date. These are unresolved
rerun/clock-context evidence, not 23 proven business defects. The frozen oracle
is unchanged. Subsequent runs record the real business date before/after and
preserve the original exit code; there is no automatic retry or changed oracle.
The 16 additional invoice cases, 23 work cases, 12 schedules, HTTP 95, exact
AI→AH restoration and cleanup completed. Artifact 10458598039: 2529732 bytes,
SHA-256 `ed3c7e15d5ef8c34167ddf3e621409e326f3baccd409d63dfa8937747693ace5`.
The downloaded bytes and ZIP CRC matched. CodeQL 35125002987 passed four languages.
