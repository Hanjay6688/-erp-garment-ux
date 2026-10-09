# First failures — append only

## 37877038138, independent staged attempt1

- Product:2e605bb7; audit:ea858258.
- Error: `dict() got multiple values for keyword argument case`.
- Classification: AUDITOR_HARNESS, not a product finding.
- Cause: our result dict included `case`; the unchanged strict runner adds `case` when logging.
- First individual result was saved before the logger failed; remaining seven did not run.
- Source restoration: boundary/public/function hashes all true. Package30files, security and backup/restore gates passed.
- Fix: rename our metadata field to `audit_case_id`; no assertion/oracle/product changes.
- Preserve original run/artifacts11592801959(JSON),11593156018(raw), not overwritten.
- Corrected run must retain all first outcomes; no claim that first attempt passed.
