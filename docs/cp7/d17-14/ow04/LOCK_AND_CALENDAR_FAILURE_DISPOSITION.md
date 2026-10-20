# OW04: first lock failure and fixture calendar correction

## Preserved result

Candidate `6544a2c81e6b46e44234464d775c203c85bc3d5e`, run `39476117912`, job `118812400827`: 32 declared Native cases attempted, 11 PASS and 21 INCOMPLETE. Restoration and the advisor gate passed. **None of the twelve new paid settlements passed.** Exact first-case errors and raw runtime log are retained in `CI_6544_FIRST_FAILURE.json` and `CI_6544_FIRST_RUNTIME.log.gz`.

## Product defect: locking private payment correction history

The source-family reader selects payment correction links with `FOR SHARE`. PostgreSQL requires an UPDATE privilege for this row lock; the business `postgres` role has SELECT only. Four new OPEN scenarios and nine retained controls stopped at this permission error.

Keep the exact predicate, payment UUID array, sort order and `FOR SHARE`. A fixed private SECURITY DEFINER helper executes that lock as the existing table owner, `cp7_sales_write`. Its search path is empty, its only additional caller is `postgres`, and temporary schema CREATE is revoked. No UPDATE privilege is granted to the caller; no posted history is modified. The predecessor table owner, RLS flags and full table ACL are captured before installation and must remain identical at verification. The helper's complete definition, owner and ACL join the existing exact private inventory.

## Fixture defect: impossible CLOSED/REOPENED input calendar

Eight other new scenarios stopped before settlement at an assertion about the original SALE journal's book date. Frozen v1 `native/EXPECTED.json` says D0 is today minus seven days and D3 is D0 plus three days, but also expects closed-period Native postings on D3. Accepted `erp.resolve_accounting_transaction_date(date)` resolves a closed date to `greatest(current WIB day, closed_through + 1)`: today, not four days ago.

The original file remains byte-identical (SHA256 `f6d7efdde1a409094b8c5485fb7942209175bce1d869e8c05f1a1d097b7cadde`). **Calendar V2 explicitly supersedes its input anchor only:** D3 equals the actual WIB business day, so D0 is today minus three days. All literal offsets, expected journal date-pair labels, monetary values and case IDs stay unchanged. Original posted journal bytes must still remain immutable. No stored journal date, Native resolver or financial expected value is rewritten. This is an openly declared test-input correction, not a claim that every fixture instruction is unchanged.

`native/CALENDAR_BINDING_V2.json` pins the accepted P00 resolver definition and explains the contradiction before the next run. The fixture verifies the binding hash and asserts the lawful closed-period D3 before posting. `NATIVE_INITIAL_QUALIFICATION.json` declares the override. CLOSED must still shift to D3; REOPENED must still use the earlier economic D2.

## Local evidence and counter-review

`lock-calendar-fix/RESULT.json`: ten isolated checks passed using the actual emitted lock helper and accepted Native date resolver. They retain the initial SELECT-only lock refusal, prove a real RowShareLock, preserve the old table ACL, reject history UPDATE, and exercise both calendar bindings. The PGlite caller role is renamed solely because its bootstrap `postgres` role is a superuser. This is not a full ERP Native settlement, concurrency or browser qualification.

An internal read-only source counter independently checked the exact helper predicate/order/lock and the accepted resolver hash. No access weakening or expected financial change was found. It did not execute Native or edit product files; this is writer internal review, not external audit. `SOURCE_PINS.json` binds the reviewed files and explicitly records the isolated scope.

Reproduce the isolated control from the repository root with Node and `@electric-sql/pglite` installed:

```sh
PGLITE_MODULE=/absolute/path/to/@electric-sql/pglite/dist/index.js node docs/cp7/d17-14/ow04/lock-calendar-fix/check.mjs
```

The next Native run keeps all 32 case IDs and financial assertions. Until that run succeeds, these fixes remain unqualified in the complete ERP. Even 32 PASS would leave direct Native EMPTY-family registration, corrected families, new HTTP/browser flows, race and recovery checks open. Default product installation and production remain unchanged.
