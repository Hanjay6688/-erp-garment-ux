# Selected-return customer refusal correction

The retained current contract6 run d69dc2d3 rejected a mismatched-customer draft
without any row/sequence effects, but emitted CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED
instead of OW04_SOURCE_CUSTOMER_MISMATCH. Its valid next-return control was not
reached. Both this failure and the earlier sibling-draft poisoning failure remain
immutable prerequisites. No test body or expected result changes.

The opt-in full-current wrapper installs the proven target predecessor, verifies
its real full22 catalog, and applies one exact callback-body delta. Active-sale
status retains its original guard. The selected draft's customer comparison
uses IS DISTINCT FROM and the retained dedicated error. It changes no grants,
function attributes, row, sequence, policy or default installation. Unrelated
DRAFT returns remain non-authoritative under the previous isolated-draft fix.

Before any inverse DDL the full used-data guard must match. Rollback restores
the one original function, verifies the predecessor, and removes that predecessor
with exact full22/ALLrows/ALLsequences checks. The six unchanged baseline/current
cases run with full backup restoration between phases and after current use.
Local preflight proves only exact structural replacement on the real used backup;
Native execution, production and independent acceptance are not inferred.
