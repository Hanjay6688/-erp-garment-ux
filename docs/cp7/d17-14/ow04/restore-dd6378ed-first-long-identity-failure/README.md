# Long internal trigger identity truncation retained

Candidate dd6378ed120052fcb3049d23513e06b290f71c43, run39613923341,
job119269748629 still refused source manifest export with
`OW04_RESTORE_DUPLICATE_CATALOG_IDENTITY: triggers`, before the used dump.
Actual CREDIT and REFUND committed and unsafe pre-use rollback was refused.
The full preinstallation CP6 state was restored exactly. Five original JSON
reports remain unchanged bytes in gzip. RECEIPT.json records independent
verification of the downloaded artifact ZIP SHA256.

The internal CASE had a text concatenation in THEN but PostgreSQL name in ELSE.
That CASE coerced the derived internal identity to name and truncated its
semantic suffix to63 bytes. The minimal correction casts ELSE tgname to text.
The owner table, full constraint name, function and trigger type are preserved;
no duplicate is ignored and no raw OID runtime check is relaxed.

The local full ERP aligned-schema control executes all22 capture queries over
880 relations and2411 triggers. Its retained previous query has1016 duplicate
identities; the corrected query has zero. This control omits215 COPY data
sections and supplies explicit auth/storage stubs. It proves metadata capture,
not business execution or Native17 backup restoration. The separate two-database
control retains different OIDs, a source-only dropped column, same FK names on
multiple children, long table/constraint names, self-reference and OLD/NEW WHEN;
changing an FK delete action is detected. Actual used-restore proof is still
required and is not replaced by these local results.
