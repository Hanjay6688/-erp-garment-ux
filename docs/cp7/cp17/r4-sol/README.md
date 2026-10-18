# Sol r3 items for the writer: validity check (r4)

Sol's locked report: `audit/sol-cp1-7-r3-b53b5acd-20261017`, seal `ff6374ad` (`audit/sol_cp17_r3/`). Sol states no new
blind product finding; it hands the writer three known open items (`FINDINGS.json` → `known_open_product_or_operating_gaps`).

| Sol item | Validity check by the writer | Disposition in r4 |
|---|---|---|
| KNOWN-POOL-PUBLIC-ENTRYPOINTS (four old public pool wrappers executable by `authenticated`; closed-period impact untested) | Valid: same root as ASTRA-R3-01, reproduced by Astra through real Auth (COUNTEREXAMPLE on b53b5acd) | Fixed by R4-01 (`scripts/cp7_public_routes_bundle.py`): the four wrappers and 21 more old public routes refuse a Data API session; Astra's two cases PASS in CP17 run 39150359349 (9cd7da11), plus a census that fails on any unreviewed public route |
| KNOWN-BACKUP-REPLACEMENT-WRITE (restore check could write into a database an administrator put in place of the attempt's own) | Valid as stated in the tool's own docstring (`scripts/cp7_nightly_backup.py`, "Operating boundary") | Prepared, not applied: owner D13-9a holds all backup work until CP7C. `CP7C_BACKUP_DISPOSABLE_SCRATCH.patch` makes the off-site tool (D13-6 restore check) run only on a scratch server of its own run: refused when it holds another database or another session before the dump, unverified when anything but the attempt appears around the restore. Writer-local check (two throwaway PostgreSQL 16 servers, local rclone folder, gpg): all 12 off-site cases PASS with the patch; the new case FAILs on the current tool (an unrelated database on the scratch server and the night still verified). To be applied and run in CI at CP7C |
| KNOWN-P19-DIRECT-LATENCY (direct capture 300 targets 6.3-8.0 s, finance 100 targets 7.4-8.0 s; owner target 3 s) | Valid as a measurement (Sol run 39146762696, 18 samples); it is the gap already declared in `docs/cp7/p19/P19_LOADING_BUDGET_20261006.md`, not a new finding | Open: needs an owner choice of timing (see the owner report) |

Audit-evidence items Sol keeps for itself (not writer work): 21 ordinary CP17 browser cases INCOMPLETE because the
group crossed WIB midnight (first result kept, harness qualification by Sol), five internal date retries kept
separately, three extra oracles not executed.
