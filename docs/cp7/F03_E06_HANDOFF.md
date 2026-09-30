# F03 E06 — year-end physical source and three-month late invoice

Status: native execution pending. CP6 remains CLOSED_CONTRACT_SCOPE; F03 remains OPEN; production_go=false and independent_acceptance=false. This is writer qualification, not an independent audit.

## Locked oracle

Use the existing E01 ordinary production chain with its explicit source masters, changing only the material receipt to ESTIMATED:100 raw units at10, GRNI1000 and supplier AP0. Receive on30 December of a prior year; consume60 and produce60 GOOD on31 December. Existing sewing120, vendor laundry120 and contractor accessory60 give HPP900 (15 per PCS). Actual Nota/payroll is approved and unpaid. Sell20 at25 on31 December: raw40/value400, FG40/value600, COGS300, revenue500 and AR500.

The main supplier document has a30 December economic date and is received31 March, as in the accepted AA/AW late-invoice contract. A separate control uses a31 March economic/document date and31 March receipt date. At11 per raw unit, material value becomes440, FG640, COGS320 and full production HPP960. Supplier AP becomes1100 and GRNI0. The corresponding native inverse restores the previous quantities, values and all account balances. An equal-price invoice at10 changes certainty/AP/GRNI without inventing a cost increase. Request replay must have one effect.

The invoice is recorded at the real execution time. The fixture does not pretend that the system knew it in March, change the database clock or fabricate an as-known snapshot. Receipt/production physical dates, supplier document/received dates, actual known-at and native open accounting date remain distinct. The31 December close filing, its readiness/hash and closed-day financial position/performance must remain immutable; a correction whose economic date reaches December stays visible in current confidence. The accepted C0 D01 3.4/BA W9 marker is not a generic “any later invoice” flag: the March-economic-date control leaves the December marker false while preserving the archive.

The invoice can recost synchronously. Pending is asserted iff a real pending queue exists, never artificially required. A separate ordinary backdated receipt creates a real pending PO queue: report/preflight must expose it and refuse close until native processing finishes. An actual two-connection period-row-lock race tests an invoice arriving while an old close review waits. Fresh review is required before filing.

## Execution boundary

- Four native cases: December-economic upward correction/UTC; equal-price correction/Los Angeles; March-economic control; actual pending queue/close/reopen.
- One native transaction race: invoice commit during an observed close lock wait.
- Full declared26-role combined installer, predecessor definition/owner/ACL checks, advisor gate, CP6 restoration and isolated database cleanup.
- No new browser or HTTP journey is claimed by these five cases. Existing P09/P13 access/browser controls retain their own source-bound receipts.
- No hosted database, release installation, payroll cash installment, customer refund, paid supplier-credit carry or whole-family acceptance is implied.

Sources: `scripts/cp7_f03_e06_cases.py`, `scripts/cp7_f03_e06_probe.py`, `.github/workflows/cp7-f03-e06.yml`. The E01 helper keeps FINAL as its default; only this declared fixture selects ESTIMATED. Frozen framework and product SQL are unchanged.


## First result and oracle correction

Source`d6a48e17d456f1e559878e89bda7a2fd4ed9494b`, run36659785503/job109711764341:2 PASS,2 INCOMPLETE,0 NOT_RUN. [Original receipt](evidence/f03-e06/FIRST_RECEIPT.json) and compressed report retain every result. CP6 restoration/advisor/backup restore and isolated cleanup pass; the overall writer gate remains false.

Actual pending-close and the real invoice-versus-close lock race pass. Both invoice cases stopped at an incorrect marker assertion: the fixture supplied a March economic/document date while demanding the December correction marker. The recovered C0 D01 3.4/BA W9 contract marks an economic correction at/before the report cutoff booked after the filing; the original test had not selected that case. This is not established product damage. The rerun explicitly separates a December-dated invoice received in March from a March-dated control. Amount, quantity, replay, archive and inverse oracles remain unchanged. Product SQL and native date policy are unchanged. Subsequent assertions not reached in the first run are not claimed proven.


Economic-date rerun:source`77c5373b93ddc682dc97d1bc58300dba5fdd189d`, run36660344730/job109713487513:4 PASS/1 INCOMPLETE. [Receipt](evidence/f03-e06/ECONOMIC_DATE_RECEIPT.json). Both December-economic invoice cases now fully pass: exact price11/HPP960/FG640/COGS320 and zero-delta10/HPP900/FG600/COGS300, timestamps, one-effect replay, invoice inverse, unchanged source facts and immutable filing. Pending-close and the real close race also pass.

The added March-economic control reaches its correct values and marker but its accounting-date assertion still incorrectly reused the closed-December case's current-day expectation. Native AY/AZ date rules preserve31 March when that economic period is open; only a closed economic date redirects recognition to the current open business day. The corrected assertion fixes these two explicit expected dates before rerun and retains the same monetary oracle. No product code/date policy changes. The E06 workflow now omits npm/Chromium installation because this declared qualifier has only native/race cases; database installation, source/ACL checks, restore and cleanup gates are retained.
