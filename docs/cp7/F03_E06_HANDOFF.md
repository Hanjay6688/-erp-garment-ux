# F03 E06 — year-end physical source and three-month late invoice

Status: native execution pending. CP6 remains CLOSED_CONTRACT_SCOPE; F03 remains OPEN; production_go=false and independent_acceptance=false. This is writer qualification, not an independent audit.

## Locked oracle

Use the existing E01 ordinary production chain with its explicit source masters, changing only the material receipt to ESTIMATED:100 raw units at10, GRNI1000 and supplier AP0. Receive on30 December of a prior year; consume60 and produce60 GOOD on31 December. Existing sewing120, vendor laundry120 and contractor accessory60 give HPP900 (15 per PCS). Actual Nota/payroll is approved and unpaid. Sell20 at25 on31 December: raw40/value400, FG40/value600, COGS300, revenue500 and AR500.

The supplier invoice is dated/received31 March. At11 per raw unit, material value becomes440, FG640, COGS320 and full production HPP960. Supplier AP becomes1100 and GRNI0. The corresponding native inverse restores the previous quantities, values and all account balances. An equal-price invoice at10 changes certainty/AP/GRNI without inventing a cost increase. Request replay must have one effect.

The invoice is recorded at the real execution time. The fixture does not pretend that the system knew it in March, change the database clock or fabricate an as-known snapshot. Receipt/production physical dates, supplier document/received dates, actual known-at and native open accounting date remain distinct. The31 December close filing, its readiness/hash and closed-day financial position/performance must remain immutable; later correction stays visible in current confidence.

The invoice can recost synchronously. Pending is asserted iff a real pending queue exists, never artificially required. A separate ordinary backdated receipt creates a real pending PO queue: report/preflight must expose it and refuse close until native processing finishes. An actual two-connection period-row-lock race tests an invoice arriving while an old close review waits. Fresh review is required before filing.

## Execution boundary

- Three native cases: upward correction/UTC; equal-price correction/Los Angeles; actual pending queue/close/reopen.
- One native transaction race: invoice commit during an observed close lock wait.
- Full declared26-role combined installer, predecessor definition/owner/ACL checks, advisor gate, CP6 restoration and isolated database cleanup.
- No new browser or HTTP journey is claimed by these four cases. Existing P09/P13 access/browser controls retain their own source-bound receipts.
- No hosted database, release installation, payroll cash installment, customer refund, paid supplier-credit carry or whole-family acceptance is implied.

Sources: `scripts/cp7_f03_e06_cases.py`, `scripts/cp7_f03_e06_probe.py`, `.github/workflows/cp7-f03-e06.yml`. The E01 helper keeps FINAL as its default; only this declared fixture selects ESTIMATED. Frozen framework and product SQL are unchanged.
