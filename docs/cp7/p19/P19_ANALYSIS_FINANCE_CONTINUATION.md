# P19 analysis and finance continuation — 6 October 2026

Product base: `ab4d8fa5a1ba640dc2fe03167aa2cabb92337cd5`, tree `262eae67469b28d62caa456660a1e94f2b299046`. This is the guarded canonical fast-forward of all 21 Claude commits plus the Build UX retired-form oracle correction. All 63 configured combined workflows started on that exact head. Build UX run `37417072250`, job `112117924453`, passes 1546 application tests, security, build, CP4.5/Pre-CP5/CP5/CP6 browser executions and the Cloudflare **dry-run** package check. Exact available browser Originals and the shared CP4.5 reporter overwrite limitation are retained in `../evidence/build-ux/qualified-ab4/RECEIPT.json`.

## Candidate implementation

- `cp7_analysis_native.build_operational`: ordered result chunks accumulate in SQL `jsonb[]` arrays and flatten once. Recommendations, material rows, metrics, actions, models, sources, assumptions and warnings preserve their existing order and complete contents. Each target's timeline starts empty before the unchanged timeline aggregation; the complete per-target chunk is retained, then all targets flatten once. The established timeline predecessor comparison remains intact.
- Products, current stock and available history are indexed once by exact key. Duplicate rows stay in each index; a visited ambiguous key still refuses with SQLSTATE `21000`. An unrelated duplicate is not promoted into a false failure. No first/last-row selection replaces the scalar lookup.
- Material SQL NULL still propagates to the complete material result. JSON null, exact decimal strings, source references, assumptions, STOPPED/PAUSED handling, missing-policy review and global allocation membership remain unchanged.
- `cp7_finance.workspace` and `cp7_finance.analysis` declare function-scoped `SET jit=off`. No CP6 definition or global/server setting changes. Report operands, all-book provenance hash and both capture/serve financial reads remain unchanged. Current financial authority and after-wait freshness are not removed.

The candidate is on a separate writer work branch. These changes are not promoted to canonical until their affected Native regressions and exact comparisons pass. All existing case budgets remain required. No full P19 acceptance is claimed.

## Equivalence and performance evidence

`f05-assembly.test.ts` compares complete old/new JSON text on 72 deterministic varied inputs, SQL-NULL material controls, exact duplicate-key refusals and an unused-duplicate control. A deliberate extra field must fail the same comparator. This is an explicitly isolated kernel test with precomputed source stand-ins; it is not a Native Auth or business lifecycle proof.

Local PGlite/WASM benchmark with the complete output comparator:

| Targets | Previous assembly | Candidate assembly | Exact full-body comparison |
|---|---|---|---|
| 100 | 216 ms | 115 ms | Identical |
| 400 | 1,915 ms | 467 ms | Identical |
| 1,200 | 15,120 ms | 1,495 ms | Identical, 7,436,505 UTF-8 bytes |

These timings are local, synthetic and specific to assembly. They do not measure the whole Native source/capture operation. CI runs the same benchmark with native PostgreSQL at 300/1,200/5,000 targets and retains the version, complete comparison, source/file hashes and unchanged ledger canary.

The existing frozen-analysis Native case additionally compares the complete current compiler with the exact pre-P19 Git definition, using the actual saved Native facts/query/actor/run UUID. It requires byte equality with the saved Original, detects a deliberate added-field control and rolls back the temporary definition. No new case credit is counted. Native finance cases similarly compare whole previous/current reports with JIT explicitly enabled for the caller and verify that success and validation failure restore the caller setting. Their actual CP6 readers remain unchanged.

## Remaining capacity and lifecycle work

The 8 MB limit is present on both the complete analysis parser and reminder conditions. Merely raising a reminder-only threshold does not prove larger complete flows. Source limits remain unchanged in this performance candidate. A complete pagination solution must bind every page to the same immutable Original and source hash, retain global totals/budgets, reject duplicate or missing pages, check current rights and freshness, and expose no partially loaded action state.

The all-book signature intentionally still scans all financial provenance: a post and its inverse must invalidate an old Original even when aggregate balances return to the same amount. Representative whole-capture, multi-user, recovery and complete capacity qualification remain required. Full P18, independent P20 and installed P21 remain open; production authorization is false.
