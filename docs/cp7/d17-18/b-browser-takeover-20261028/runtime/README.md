# B — actual Chromium instrumentation check

Base fdea191e65014a5c7b86d3ce56fb3b1d01958581. This small browser-tool test imports the existing B recorder unchanged. It does not replace or launch the ERP real-Auth runner. The earlier pinned Chromium download failed in the local workspace; its Original remains in the parent receipt. A separate CI environment with the same package-lock and Playwright version is the next diagnostic, not an unchanged retry in the failed environment.

Two actual Chromium contexts (desktop1440x1000, mobile390x844) must each prove six checks: application console.error rejected; real aborted network response matches the exact allowed text/URL; wrong URL rejected; actual loopback HTTP403 matches the exact allowed text/URL; unexpected HTTP404 rejected; and one allowance cannot hide two real errors. Listener cleanup is also required. All console observations and any setup/runtime/cleanup failure remain in the single report, written exclusively. Install logs and TAP remain in the artifact even if a step fails.

The server binds only127.0.0.1 and serves instrumentation fixtures. No ERP, Auth, database, official value, restored backend or visual acceptance credit. CONFIG remains false/null. The frozen ERP runner,113host/91B files, financial code and dependency versions are unchanged. Only this test, its branch-only CI workflow and successor evidence are new. Original parent declarations are not rewritten.

Latest checked A is7657bbee5d55277855a0ab53126438c2e9c63118; no backend is selected. After this diagnostic B still requires A's exact qualified backend and all7/restore Originals before the actual combined browser candidate can be bound. Formal5/16, production_go=false, independent_acceptance=false, CP7C not started.

The source receipt is PREPARED.json; actual CI result will be appended separately. No success is claimed before inspecting the report and artifact.
