# Policy hash repair and material qualification

Candidate `310ab77` qualified the original analysis and material-source extension:
run 36936014656, job 110616344817, 152/152 PASS (106 database, 20 real races,
12 actual Auth/HTTP, 14 desktop/mobile browser). CP6 restoration, advisor,
installation, primary unchanged, backup restoration, zero console errors,
Auth cleanup and disposable-database cleanup all passed. Exact originals and
archive identity are retained in `evidence/f05-native-publication/qualified152-310ab77`.
This is a bounded qualification; the full F04/F05 acceptance is still open.

The previous 198-case attention run at `1fbd6a4` had 197 PASS and one material
HTTP UNKNOWN-value failure. Its unchanged archive is retained in
`evidence/f05-native-material/third197-http-window-1fbd6a4`.

The first installed 218-case policy run at `310ab77`, run 36936014181,
job 110616343455, observed all 218 cases: 202 PASS and 16 INCOMPLETE. Its
existing 198 predecessor cases passed. Nine policy database cases, two races,
three actual HTTP cases and two browser cases failed when the policy workspace
called `extensions.digest` without schema access. The three clock/unit input
cases and the current-permission race passed. Restoration and advisor passed;
this run is not policy qualification.

The repair computes the same SHA-256 over the same UTF-8 rows using
`pg_catalog.sha256`, already used in this accepted Native stack. No schema,
function or ERP table grants are added, and no permission or case expectation
is relaxed. The 218-case candidate must be rerun from installation through
database, real races, actual Auth/HTTP, browser and restoration.

The independent rule-source/local-sink draft remains on its topic branch and
is not composed into this repaired integration candidate. No external delivery,
hosted installation, production go or independent acceptance is claimed.
