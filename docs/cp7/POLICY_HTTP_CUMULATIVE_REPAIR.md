# Shared policy HTTP fixture repair

Source aaee5a0 retained every one of the 218 required cases. Native139,
actual races29 and browser30 passed. HTTP18/20 passed. Run36940540624,
job110630750558, observed216 PASS and two INCOMPLETE; restoration,
advisor, unchanged primary, backup and cleanup all passed.

The HTTP runtime keeps prior case commits in the same disposable database.
The current-authority fixture attempted expected_revision0 after its predecessor
had already created the shared global production policy. The absent-intent
fixture assumed the shared policy list was empty. These are fixture mistakes:
policy versions are shared across current authorized actors and must survive.

The authority fixture now explicitly reads the current public workspace and
uses its actual latest revision for CAS. The absent-intent fixture pins and
compares the complete existing shared list, and still requires NOT_COMMITTED
with no late write. Product SQL, policy permissions, UUID fencing, thresholds
and the fixed218 budget are unchanged. Complete rerun is required.

Exact Original reports, archive digest and source identity are retained in
`evidence/f05-native-policy/second216-http-cumulative-aaee5a0`.
No full F04/F05 acceptance, independent acceptance or production go is claimed.
