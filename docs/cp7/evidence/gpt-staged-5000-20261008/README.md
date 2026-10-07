# Writer integration evidence: staged 5,000 targets

Checkpoint source: `7927b42cf80dc44dd8af19d7f9138e2469e1efc4`;
last qualified product base: `013ea062e69e3fb4a9d12431be8b74650bfc41c4`.
All WIP patches from the checkpoint were applied together in their documented
order. No hosted database, deployment, main or integration branch is changed.
`production_go=false`; `independent_acceptance=false`.

## Local validation (not Native/Auth/HTTP/browser proof)

Runtime: explicitly selected PGlite with pgcrypto, labelled
`PGLITE_WASM_LOCAL_NOT_NATIVE_AUTH_PROOF`. Native PostgreSQL is not available
in this workspace. Native and full application evidence must come from CI.

| Evidence | Result | Exact scope |
|---|---|---|
| `17-frontend.log` | 1,469 passed, 145 files | All `src` Vitest tests; includes ordinary and staged routes |
| `18-reopen-pause.log` | 11 passed | Staged panel DOM, same UUID pause/resume and completed reopening without recompute |
| `06-hash-contract.log` | 8 passed | Page identity including zero pages and malformed identity rejection |
| `08-parity-first.log` | 1 passed, 3 unselected | Selected 162-capture product analysis/Original parity corpus; remaining tests must run Native |
| `11-real-scenario.log` | 3 passed | Full real scenario chain parity, caps and deliberately incorrect units |
| `12-product-pages.log` | 2 passed | Product page reassembly under three byte budgets; page/access contract before extra security cases |
| `19-page-security.log` | 2 passed, 1 unselected | Current multibyte/hash/access/immutable/source checks and oversize-target refusal |
| `26-progress-api.log` | 3 passed | UUID cross-path refusal; six public boundaries; access revoke; immutable/purge; real progress contract at each unit; 5,001-target first-unit refusal |

Final typecheck, Python compilation, JS syntax and source/access/CSS catalogs
passed. Catalog: 277 runtime files, 216 RPC boundaries, 111 permissions and
48 routes. No frontend test claims browser performance.

## First failed attempts retained

Logs 01–16 retain fixture/contract/DOM setup failures and their diagnosis.
`15-reopen-pause.log.gz` is the exact losslessly compressed original DOM log
(large repeated render dumps); decompression restores it byte for byte.
Logs 20–21 show why using a limited API stand-in over a real scenario was an
invalid fixture (missing `remain_eta` privileges); the regression now calls
the real private kernel in the disposable runtime. Native/Auth uses the
closed full-bundle CI suite, not that stand-in.

`22-progress-old-failure.log` is the actual old-product regression: NET_PAIRS
reported 2 completed targets although it had processed position ranges.
The repaired status counts only target-range units. Logs 23–25 retain
subsequent test construction mistakes (zero-root generator, camelCase
parsed field, and a stand-in that bypasses real HIST_PREP bounds). The final
real-chain regression in log 26 passes without loosening the bound.

## Required CI evidence

- Product kernel suites plus independent Native sessions, lock/retry tests,
  benchmark vectors 1,000×30, 5,000×30 and 5,000×100, all target rows covered.
- Native/Auth/HTTP/browser `p19-staged12` and the full application scale
  ladder at 100/300/1,000/5,000; all generated pages actually read.
- Measured time from trusted next-page click to verified rendered page plus
  two paint frames; same measurement when reopening a completed result.
  Owner steering 8 Oct 02:09 WIB makes 3,000 ms a goal, not a mandatory gate;
  optimise as far as possible. Actual times and goal results remain visible.
- Background computation wall time, capture time and acknowledgement are
  separate measurements. None is substituted for usable result loading.
- The four previously path-filtered ERP workflows run on this head too;
  one-head qualification remains pending until their actual results exist.

## First Native CI head: cb98b0f8

All results below belong to `cb98b0f816d0a63e9d023a81140603558e9a423b`,
not to the subsequent repaired candidate. This head is **not qualified**.
`cb98b0f8-ci-snapshot.json` binds the 15 workflow observations to that source.

- Shell: all 1,659 tests in 189 files passed on Native PostgreSQL; security,
  build and browser checks passed. Exact log: `33-native-shell.log.gz`.
- Product staged kernel: 14/14 tests across five files passed, including
  independent sessions and locks. Generated-capture benchmarks completed
  without a retry; they are kernel measurements, not Auth/HTTP capacity proof.
  Exact log/report: `32-native-product-kernel.log.gz` and
  `cb98b0f8-staged-kernel-original.zip` (artifact 11507163454).
- Existing analysis transport: 15/15 cases passed with Native/Auth/HTTP and
  desktop/mobile browser evidence. Exact log and complete root JSON reports:
  `27-native-transport.log.gz`, `cb98b0f8-p19-transport-originals.zip`
  (artifact 11506605084).
- Build UX, planning, P18, finance and correction workflows passed. Payroll
  review and attendance jobs passed; roster and P08 attention were still
  running at the recorded snapshot. No all-green claim is made.

| Generated-capture kernel vector | Background wall time | Slowest unit server time | Full target keys | Pages |
|---|---:|---:|---:|---:|
| 1,000 × 30 days | 24,951 ms | 1,804.5 ms | 1,000 | 8 |
| 5,000 × 30 days | 134,464 ms | 2,021.1 ms | 5,000 | 37 |
| 5,000 × 100 days | 148,808 ms | 2,100.6 ms | 5,000 | 37 |

The 1,000-target result is byte-identical to the single chain. At 5,000 the
single chain refuses its existing grid bound; it is not promoted into a
5,000-target oracle. History, baseline, netting and distinct target coverage
all equal 5,000. Per-call 8 s and all product bounds remain unchanged.

### First CI failures and their repairs

The unmodified first reports and screenshots are retained in the ZIP files
below; `.log.gz` files decompress to their exact original text. ZIP SHA-256s
and GitHub artifact IDs are in `cb98b0f8-artifacts.json`.

| First failure | Cause and repair | Retained evidence |
|---|---|---|
| Staged identity | The reader checks access epoch before run lookup. Separate tests now require ACCESS_CHANGED for an invalid epoch and RUN_UNAVAILABLE for an unknown run with the valid epoch; guard unchanged. | `28-native-staged-first-failure.log.gz`, staged Originals/full ZIPs |
| Staged bounds and scale ladder | Reassembly SQL lacked a closing parenthesis. It also needed global prefix/page items/global suffix order. The exact Python SQL is now run against product pages and compared to the independent single Original, including a suffix example. | scale/staged first-failure ZIPs; local `29-scale-reassembly.log` |
| Lock/retry race | Locking every stage table blocked function argument compilation before the handler. Locking output INSERT inside the handler tests real retries and asserts no partial unit was saved. | staged first-failure ZIPs |
| Desktop reload | The old browser driver could issue a step before navigation. Pause it before the reload boundary; first new call must GET the same UUID, with no replacement request. | staged full ZIP browser report/screenshot |
| Mobile copy oracle | Product says “belum tersedia untuk analisis bertahap.” The test now matches that exact existing copy and still requires the downstream names. | staged full ZIP browser report/screenshot |
| Both JavaScript CodeQL jobs | `cp7_p19_result_storage.mjs` used a predictable shared temporary directory and permissive file modes. Use an atomically created private directory and exclusive mode-0600 file. No rule is waived. | `30-codeql-first-failure.log.gz`, `34-cp6-codeql-first-failure.log.gz`, CodeQL SARIF ZIP |

Before final reassembly failed, the 5,000-target one-day browser case rendered
26 pages in 60,045.6 ms and visited every page. This is an **incomplete first
attempt**, not accepted capacity or load proof. The later candidate must
complete all frozen-contract/coverage checks and separately record page and
completed-open load times. The raw failure is retained, never overwritten.

### Subsequent product optimisation

PAGES and PAGE_INDEX now execute before loading the full reference and earlier
scenario/netting/allocation results they never read. Their exact page-building
bodies are unchanged. Existing parity/access/multibyte tests and the exact
evidence reassembly SQL pass locally (`36-pages-early-dispatch.log`, one
selected test, two unselected); the full Native corpus and benchmarks must
prove the subsequent head. Its complete CI kernel measurements are below;
these are not application loading measurements or a controlled speedup claim.

P20/P21 packaging, integration merge and auditor acceptance remain pending.
Open owner policy values remain open; no invented yield/retention/driver or
downstream staged feature policy is included. No hosted database, main or
deployment is changed by this work.

## Repaired candidate: 43d26996 (qualification in progress)

Source: `43d26996d767f47bb21d86e988b92c9dcf994703`. The four T3 CodeQL
languages and both Shell CodeQL jobs passed with zero findings. The
Native/Auth/HTTP/browser staged suite passed **12/12** (5 Native, 3 races,
2 HTTP, 2 browser); ordinary transport passed **15/15** again.
Receipts and lossless root reports are in `43d26996-staged12-retained/` and
`43d26996-transport15-retained/`. They bind exact source/run/artifact hashes
and require complete case counts, package gates and restored boundaries.

Completed-open measurements in the small staged browser fixture were
152.4 ms desktop and 102.7 ms mobile, trusted click to verified first page
plus two paint frames, with no request/step/recompute. These are **not** the
5,000-target measurements. The product kernel passed 14 tests and all three
benchmark vectors. Complete Originals: `43d26996-staged-kernel-original.zip`;
exact log: `38-native-staged-kernel-optimised.log.gz`.

| Generated-capture kernel vector | Background wall time | Slowest server unit | Retries |
|---|---:|---:|---:|
| 1,000 × 30 days | 23,258 ms | 1,688.4 ms | 0 |
| 5,000 × 30 days | 123,245 ms | 1,786.1 ms | 0 |
| 5,000 × 100 days | 135,670 ms | 1,825.3 ms | 0 |

Both 5,000 vectors cover all 5,000 distinct targets and generate 37 pages;
the 1,000 vector remains byte-identical to the single chain. The observation
receipt preserves both heads in `43d26996-kernel-observations.json`.

### Scale evidence failures on this head

The full application scale job is **INCOMPLETE**, not qualified. Its exact
root reports and failed gates are retained in
`43d26996-scale5-first-failure-retained/`; exact job log:
`37-native-scale-evidence-first-failure.log.gz`.

1. Python wrongly treated `STAGED_UNIT_STOPPED_8S` as a structural refusal
   requirement, even when the real result completed with all coverage,
   frozen-contract and transport checks true. Timeouts are possible stopping
   conditions, not mandatory refusals. The regression exercises this retained
   Native point and still rejects structural-cap, missing-evidence, corrupt
   result and result-saved-after-refusal counterexamples. Originals unchanged.
2. At 1,000 targets, Playwright's default inspector evicted a response body.
   An unhandled promise ended the browser process before harness cleanup;
   `primary_unchanged=false` and 25 remaining Auth users are preserved as failed
   gates. A passive, separately bounded CDP session now reads each **original**
   request's body, without RPC replay. Evidence errors are caught and raised
   inside the case so cleanup runs. Diagnostic buffers do not raise product
   page/document/call bounds. CORS preflights are excluded from RPC evidence.

At 100/300 targets the first attempt measured staged completion and reopening,
but this failed overall run is not promoted to accepted capacity evidence.
The corrected full application ladder and all ERP suites require a subsequent
same-source run. Local recorder/verdict/frontend checks passed 1,476 tests
(`39-recorder-frontend-regression.log.gz`); these are not Native browser proof.

P21 rehearsal run 37677705173 also passed. Its runtime USE witness says
`HELD_OPEN_THEN_ROLLED_BACK`; do not promote the old script docstring's
“committed” description into proof. Rehearsal is not installed acceptance.
