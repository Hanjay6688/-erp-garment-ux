# First transport execution on Native63-qualified core

HTTP/race run39566460885/job119109810264 and browser run39566460814/
job119109809061 tested8a683ef21d2236d438c9a534f355c181a17fea2a, reusing
the exact successful e9287cf3 Native63 core. Neither complete workflow passed.

The real Auth/HTTP subgroup passed14/14 and its package/restore/advisor gates.
The unchanged retained races passed6/6. Both new source races stopped inside
the holder's post-write assertion before running the contender. Their sealed
snapshots use Native's `_raw` exact-decimal parser; the fresh snapshot used
psycopg's default JSON decoder, so strings such as `10.000000` were compared
with floats. The passed HTTP record independently retains equal before/actual/
final HPP snapshots. The correction reads the fresh snapshot through the same
existing exact parser. All eight full-snapshot equality predicates stay
byte-for-byte unchanged, along with every frozen financial/stock/date oracle.
Local actual-expression controls reproduce the original false difference and
still reject changed HPP amounts, extra versions and all seven other fields.

All four browser cases stopped before fixture preparation: browser_fixture
referenced the new merged HTTP case-registration module as if it exposed the
old initial-settlement helpers. It now explicitly selects initial_http; actual
import reproduces the old failure and resolves both retained helpers afterward
with zero database calls. CI now imports that fixture before rebuilding the DB.

Full original reports, host report, package gates and artifact identities are
preserved here. Native63 remains valid: only qualification files changed.
New real races/browser and the complete workflow gates must run again; local
controls do not supply those results. OW04 remains open, production_go=false.
