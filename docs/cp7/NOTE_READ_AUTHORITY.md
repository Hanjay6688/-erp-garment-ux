# Owning-note read authority

The separate E01 successor reveals a fresh-read gap while a pending command exists: a valid newly authorized invoice is still hidden. The shared hook now separates source-read readiness from write readiness while retaining exact parent tickets, unchanged pending UUID/payload and all write locks. Local24 controls and full1143 application tests/build/security pass; complete new Native qualification is required. See PENDING_SOURCE_READ.md. Earlier note40 success below belongs to source15aca456 before this shared-hook correction.

## Confirmed defect and repair

Three source counterexamples fail before this repair: a held read ticket remains current after explicit invalidation with the same recovery signature; a shared SALES invalidation leaves the old Native invoice and financial values visible; a delayed correction-history reply can then publish facts whose parent read has been retired. The correction form must retain the operator's unsent quantities and reason while retiring those source facts.

`useProductionMutation.invalidate()` now retires every preceding read sequence and clears the accepted parent ticket. `finishRead()` stores the exact accepted ticket. The new read-only `currentReadTicket()` exposes that ticket only while the completed parent proof remains current; it neither manufactures a fresh proof from an old read nor starts a parent refetch. A delayed child reply must satisfy the same parent scope, session, recovery signature and read sequence.

`ConnectedSalesPage` renders Native invoice rows, totals and detail only while the mutation workspace is current. Correction-history success and failure are fenced by the exact accepted parent ticket as well as their existing parent/history sequences. Operator search and unsent correction fields remain available; the writer stays locked until a fresh authoritative read succeeds.

The existing Native40 mobile lost-reply/two-tab case now additionally requires the peer's old invoice rows, money and correction action to disappear and its create action to be disabled. Exact UUID/payload replay, one actual commit, zero peer writes, financial amounts, historical balances, lot/line identity and microsecond guards are unchanged. The budget remains28 DB/4 race/3 Auth-HTTP/5 browser.

## Source qualification

Actual guard source15aca456/tree57338a9d now qualifies complete Native40 at37061659616/job111019496644 with the strengthened mobile peer source-retirement oracle, exact UUID/payload and one-commit recovery. All28 DB/4 race/3 Auth-HTTP/5 browser and every package/restoration/primary/backup/advisor/runtime/Auth0→0 gate pass; console errors are zero. Full Native Shell1278, integrated receipt32 and cutting57 also qualify that source. Exact note Original: evidence/owning-note-correction/qualified40-15aca45/. This qualifies the repaired product paths; the separate corrected E01 four-journey scenario remains under actual qualification.

The separate E01 four-journey regression at15aca456 retains3/4 because its historical mobile peer assertion requires a return button that the source-retirement repair correctly removes. Its corrected oracle now explicitly checks absent old invoice/money/actions, disabled create, current recovery and zero peer writes before a fresh read, while preserving exact pending UUID/payload and every committed financial value. No product change or case-budget reduction accompanies it; a complete new Native4 remains required. See E01_READ_AUTHORITY_SCENARIO.md and the retained failure Original.

The three counterexamples fail against the predecessor source; the repaired application suite passes1142 tests in118 files, including the exact-parent-ticket regression. Build and the full security/ownership/access catalog checks pass. Local PostgreSQL is unavailable, so this application-only result does not claim the full PostgreSQL suite.

Source34d7e2e passed complete Native40 before this repair: run37047744469/job110973248260, exact Original under evidence/owning-note-correction/qualified40-34d7e2e/. That preceding run does not qualify the new UI source; the exact15aca456 qualifications above provide the repaired product's source-bound proof.

Financial SQL, Native timeouts, RPC definitions and access grants are unchanged. Claude owns posted receipt/final supplier-price/name correction; his further integration is deferred until his section is finished. No parallel receipt/year-price or receipt-sale join provider is added here.

The existing receipt32 and cutting57 workflow path filters omitted the shared mutation/recovery hook. Those two source patterns are now included, keeping all jobs, source imports, probes, assertions and case budgets unchanged. This requalifies the already-integrated receipt source; it does not import Claude's unfinished branch.

The intermittent HTTP timeout cause remains open. A successful repeat is not a cause diagnosis. CP6 HOLD; audit_complete=false; production_go=false. Complete F03/F04/F05, independent/demo and hosted acceptance remain open.
