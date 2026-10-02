# Owning-note read authority

## Confirmed defect and repair

Three source counterexamples fail before this repair: a held read ticket remains current after explicit invalidation with the same recovery signature; a shared SALES invalidation leaves the old Native invoice and financial values visible; a delayed correction-history reply can then publish facts whose parent read has been retired. The correction form must retain the operator's unsent quantities and reason while retiring those source facts.

`useProductionMutation.invalidate()` now retires every preceding read sequence and clears the accepted parent ticket. `finishRead()` stores the exact accepted ticket. The new read-only `currentReadTicket()` exposes that ticket only while the completed parent proof remains current; it neither manufactures a fresh proof from an old read nor starts a parent refetch. A delayed child reply must satisfy the same parent scope, session, recovery signature and read sequence.

`ConnectedSalesPage` renders Native invoice rows, totals and detail only while the mutation workspace is current. Correction-history success and failure are fenced by the exact accepted parent ticket as well as their existing parent/history sequences. Operator search and unsent correction fields remain available; the writer stays locked until a fresh authoritative read succeeds.

The existing Native40 mobile lost-reply/two-tab case now additionally requires the peer's old invoice rows, money and correction action to disappear and its create action to be disabled. Exact UUID/payload replay, one actual commit, zero peer writes, financial amounts, historical balances, lot/line identity and microsecond guards are unchanged. The budget remains28 DB/4 race/3 Auth-HTTP/5 browser.

## Source qualification

The three counterexamples fail against the predecessor source; the repaired application suite passes1142 tests in118 files, including the exact-parent-ticket regression. Build and the full security/ownership/access catalog checks pass. Local PostgreSQL is unavailable, so this application-only result does not claim the full PostgreSQL suite.

The source repair still requires a new complete Native40 and combined Shell, receipt32 and cutting57 qualification because the shared read hook is used by other writers. Source34d7e2e passed complete Native40 before this repair: run37047744469/job110973248260, exact Original under evidence/owning-note-correction/qualified40-34d7e2e/. That preceding run does not qualify the new UI source.

Financial SQL, Native timeouts, RPC definitions and access grants are unchanged. Claude owns posted receipt/final supplier-price/name correction; his further integration is deferred until his section is finished. No parallel receipt/year-price or receipt-sale join provider is added here.

The existing receipt32 and cutting57 workflow path filters omitted the shared mutation/recovery hook. Those two source patterns are now included, keeping all jobs, source imports, probes, assertions and case budgets unchanged. This requalifies the already-integrated receipt source; it does not import Claude's unfinished branch.

The intermittent HTTP timeout cause remains open. A successful repeat is not a cause diagnosis. CP6 HOLD; audit_complete=false; production_go=false. Complete F03/F04/F05, independent/demo and hosted acceptance remain open.
