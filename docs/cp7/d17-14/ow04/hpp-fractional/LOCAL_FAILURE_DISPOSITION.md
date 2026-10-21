# Local projection qualification: first failure and added guards

The first synthetic PGlite run is preserved in LOCAL_PROJECTION_FIRST_RUN.json
and its stderr companion. It stopped before the first case completed:
`inconsistent types deduced for parameter $4`.

Classification: fixture parameter typing. The same placeholder was inferred
as integer by the basis column and numeric by a division. The fixture now
casts it to integer explicitly in both positions. No product formula, literal
expected vector, permission, or financial/date oracle was changed for this
repair. LOCAL_PROJECTION_SECOND_RUN.json records22 PASS after that change.

The follow-up LOCAL_PROJECTION_DRAFT_CACHE_GUARDS.json additionally attaches an
actual synthetic own-DRAFT return item to a selected lot: it must not change
the before-support hash. It also alters only the synthetic PO saved FG/COGS
split while keeping actual ledger and target equal: projection must refuse.
All22 scopes passed. A later grouping-source recheck is separately recorded
after removing redundant repeated PO group discovery.

These databases contain synthetic rows and lightweight relation definitions;
they are not the real ERP writer fixture or proof of authentication, scheduling,
race behavior, browser behavior or production readiness. The reports bind the
exact expected, projection and book-source SHA256 values, including dirty-work
source identity when execution predates the candidate commit.
