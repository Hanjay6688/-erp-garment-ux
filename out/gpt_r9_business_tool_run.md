# Independent R9 Actions run 36122470639 — frozen d1bc8ad

Run: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36122470639 ; trigger audit commit 8c80bd006b958ca0026f4fc4a57f9e85f424ed96 ; candidate tool head d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b ; product BA b6d81f93a1e244178193178aec765facfd1b5488. Label AUDITOR_SCENARIO, phase after; independent_acceptance=false, release_evidence=false, production_go=false. DB disposable clone only.

| Job ID | Intent | GitHub conclusion | Native status | Result |
|---|---|---|---|---|
| 108030928495 | W8×4, W9×2, LAU-T14×2 | SUCCESS | RUN_COMPLETE | 8/8 PASS, primary unchanged, clones removed |
| 108030928804 | W7 status out of vocabulary | FAILURE expected | INCOMPLETE | ordinary registration PASS; race and HTTP each INCOMPLETE; auth restored; primary unchanged |
| 108030928817 | W7 duplicate IDs | FAILURE expected | INCOMPLETE | ordinary control PASS; race and HTTP each refuse AUDITOR_DUPLICATE_CASE_IDS; auth restored; primary unchanged |

Exact native group outcome per case (not inferred from green/red alone):

- `G9:W8:G8:MULTI_CENT_DIRECT_UP`: PASS; oracle M3818/3820 plus A4: sum of separately posted document cents; exhausted inventory has zero value. No per-receipt tolerance authorized.
- `G9:W8:G8:MULTI_CENT_DIRECT_DOWN`: PASS; oracle M3818/3820 plus A4: sum of separately posted document cents; exhausted inventory has zero value. No per-receipt tolerance authorized.
- `G9:W8:G8:MULTI_CENT_INVOICE_UP`: PASS; oracle M3818/3820 plus A4: sum of separately posted document cents; exhausted inventory has zero value. No per-receipt tolerance authorized.
- `G9:W8:G8:MULTI_CENT_INVOICE_DOWN`: PASS; oracle M3818/3820 plus A4: sum of separately posted document cents; exhausted inventory has zero value. No per-receipt tolerance authorized.
- `G9:W9:POST_FILING_CORRECTION`: PASS; oracle C0 D01 section 3.4: filing and filed values are immutable; new economic corrections on filed dates remain marked after readiness returns; without new correction the marker stays false
- `G9:W9:NO_NEW_CORRECTION_CONTROL`: PASS; oracle C0 D01 section 3.4: filing and filed values are immutable; new economic corrections on filed dates remain marked after readiness returns; without new correction the marker stays false
- `G9:LAU_T14:SEND_RATE_AFTER_UPDATE`: PASS; oracle Master Pulih 4474: receiving later does not reprice a posted delivery at the return-day version; 10 PCS at the agreed send rate 7 remain 70
- `G9:LAU_T14:UNCHANGED_RATE_CONTROL`: PASS; oracle Master Pulih 4474: receiving later does not reprice a posted delivery at the return-day version; 10 PCS at the agreed send rate 7 remain 70
- `G9_TOOL:REGISTRATION_CONTROL`: PASS; race `G9_TOOL:RACE_UNKNOWN_STATUS`: INCOMPLETE; HTTP `G9_TOOL:HTTP_UNKNOWN_STATUS`: INCOMPLETE, all foreign status must not be silently PASS.
- `G8_TOOL:CONTROL`: PASS; race duplicate `G8_TOOL:RACE_DUP` and HTTP duplicate `G8_TOOL:HTTP_DUP`: refused `AUDITOR_DUPLICATE_CASE_IDS` before execution. GitHub runner exits red because native report INCOMPLETE as designed.

W8 four variants direct/invoice × up/down, exhausted stock 0.000000, expected zero MATERIAL_INVENTORY value and document-level cents reconciled (up WIP20.02/AP−20.02; down WIP20.00/AP−20.00). Run log per case includes full dated before/after. Historical no-BA controls four PASS already (writer claim cross-checked in prior intake); earliest BA regression cannot be cited as fault of original baseline. W9 correction after filing: changed_since_filing false→true after dated correction, same filing ID and filed values, engine READY; no-correction control remains false. LAU-T14: later rate 9 does not reprice send rate7 for 10PCS, receipt actual 7.00 and total70.00; unchanged-rate control same7.00/70.00.

All jobs record `primary_unchanged=true`, `clone_remaining=0`; each has 'Stopped supabase local development setup' in cleanup. Two negative jobs have purposeful assertion `AssertionError: INCOMPLETE` after structured report; this is tool refusal, not product failure. Artifact IDs: 10857773556 (business), 10858223420 (unknown), 10857683652 (duplicate). All results limited to tested paths and frozen writer head; no broad CP6 acceptance, HOLD/audit_complete=false/production_go=false.
