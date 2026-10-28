# B — OW10 first failure exclusive create — 28 October 2026

Base: `1dd83782dcaa4500bace7bf392a76f58be0271c3`.
A compared: `d24b7128cddbc79312a6058b17b56da047775c75`; target script is byte-identical to B base before this patch.
Branch: `astra-b/ow10-first-failure-exclusive-20261028`.

The first failure is now created with `wx`. Only `EEXIST` means another first record already exists; other errors escape. Existing evidence is not replaced. A's proposed inline fix is preserved semantically in a six-line shared helper so the exact production writer can be tested with real filesystem operations and independent child processes without starting SQL. Statistical calculations, expected values, SQL, and historical evidence declarations are unchanged. This is a successor declaration, not retroactive qualification of old evidence.

Four Node tests passed locally: complete new file, existing binary evidence unchanged, two writers released together with exactly one winner and complete winning bytes, and real ENOENT propagated. Duration 450.5959 ms. Syntax and diff checks passed. The actual statistical runner passed all five cases, the independent 80-digit oracle, and 22-group real local installer/catalog apply/rollback/reapply plus post-use refusal. It uses PGlite 0.5.11 and controlled ERP/history/identity; it is not Native/Auth/full-chain proof.

Preserved setup failures: the first isolated working directory omitted `docs/evidence/cp6-ao-predecessor-input.json`; the second omitted `src/initialImportCatalog.json`. Neither reached the statistical cases. The third run supplied the unchanged repository inputs and passed. All three logs remain beside this note. No timeout or assertion was relaxed. Historical first-failure bytes remain unchanged.

JavaScript CodeQL security-extended is requested by the dedicated branch workflow; the actual result will be recorded in a separate receipt. It scans JavaScript/TypeScript with the repository's pinned action, no suppression, checks nonempty SARIF plus successful invocation and zero results, and retains TAP/SARIF even on failure. Do not claim CodeQL PASS until its Original is inspected.

Apply selectively: the two production MJS files together, with the test alongside. The branch-only workflow is B's qualification harness; A chooses its integration workflow. Recompare A's current target before applying. Never merge the entire old B branch. A remains integrator; this writer check is not independent acceptance. Formal 5/16, production_go=false, independent_acceptance=false; CP7C has not started.

## Completed CI receipt

Actual source `4fcc1adc2b219304c73e2de6dc6df2b7810106d9`, tree `5a6a4a02fdbdd772840e4d8243d3934c00cff100`: run40648709228/job122683491213 attempt1 SUCCESS. Original artifact12799290246 has four passing filesystem tests (93.71136 ms; real concurrent writers 38.243846 ms) and complete JavaScript SARIF with 103 queries including `js/file-system-race`, zero findings and successful execution. The complete job lasted259 seconds; no artificial delay or timeout increase. The actual query-execution line is also retained in the compressed complete job log. See CI_RECEIPT.json for byte hashes.

`B_FIRST_FAILURE_EXCLUSIVE.patch` contains only the three MJS source/test changes. Apply from the repository root after matching the target preimage, e.g. `git apply --check` before selective application. CodeQL workflow and this evidence folder remain qualification material. A has not yet integrated this patch; the main browser/backend acceptance remains separate.
