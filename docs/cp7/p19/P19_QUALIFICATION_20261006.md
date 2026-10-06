# P19 measured continuation — 6 October 2026

The complete assembler comparison is writer-qualified at source `67a23c11edf10573328f4d8cdc185c258fbf2f8a`, tree `3b9667cec3814e3265026d263aae1bd43696eed7`. Shell run37421165675 passes all1547 application tests, six fixture browser cases, security/build and both successful Original CodeQL scans with zero findings. Complete unaltered root reports are retained in `../evidence/p19/assembly-qualified-67` and `../evidence/p19/codeql-qualified-67`.

| Isolated targets | Previous assembler | New assembler | Complete output |
|---|---|---|---|
|300|875.158ms|244.750ms|1,869,020 UTF8 bytes, identical|
|1200|11,485.340ms|1,113.524ms|7,436,505 UTF8 bytes, identical|
|5000|227,436.191ms|13,152.527ms|30,970,077 UTF8 bytes, identical|

This executes PostgreSQL16.15 with explicitly precomputed-source stand-ins. The largest ratio is0.05782952547. The full-text comparator, added-field negative control, source hashes and unchanged ledger canary all pass. It measures the assembler alone. The5000-target body exceeds the current8MB boundaries and the13.15s isolated execution exceeds the existing8s Native HTTP deadline. No full application5000 capture or production SLA follows.

The old compiler required227.4s at5000. Earlier disposable comparison deadlines of60s and180s failed and remain INCOMPLETE Originals. The qualified600s allowance applies only to this comparator process. Ordinary kernel defaults, Native ERP/HTTP timeouts and product caps remain unchanged.

All first3e5 Native setup failures are retained as well: every P08 component, all three P18 components and finance12 in `../evidence/p19/first-native-3e`, plus the separately retained finance/analysis24 first failure. Each complete Original reports observed_case_count=0, cp6_restored=true and advisor_gate=false; the package writer_runtime gate is false. Their common exact error is the predecessor metadata assertion encountering the new `jit=off` setting on workspace. The successor declares that setting precisely rather than bypassing metadata verification. No first failure is relabelled or awarded Native case credit.

## Actual Native equivalence at290d30de

Product SQL is unchanged from3e5ba257 through290d30de and67a23c11. Their tool-only differences retain separate source receipts; no old run is retargeted to a later Git head.

At290d30de, Native finance12 and finance/analysis24 pass all declared cases. The whole workspace report and analysis report match the exact predecessor, under the same SQL clock with caller JIT enabled. Function-scoped `jit=off` restores that caller setting after success and validation failure. The metadata verifier requires exactly the existing search_path, TimeZone and new function-local JIT settings for only the two changed functions, preserving owner, invoker/definer, volatility, grants and public-wrapper checks. No global/server setting or CP6 reader changes.

The actual frozen-analysis Native case compares the current compiler, exact ab4 Git compiler and saved immutable Original on actual Native facts/query/actor/run UUID: all116,545 UTF8 bytes match, SHA256 `4677907b499eca47320c7f97be67228fb1761ca11923e968f3495980835707c8`. An added-field control is detected, the definition is restored and the saved Original remains unchanged. These witnesses add zero cases to the established budgets.

Complete Original exports qualify fabric-physical21, fabric13, analysis152, plan39, attention284, fabric-rule11, rule-lifecycle16 and p18-e01-9 at290d30de. Their all-group case IDs/counts, package/install/backup/restore/advisor/real-Auth/console/cleanup gates are checked. Attention284 finishes successfully in run37420039535/job112127132399:179 Native,40 races,29 actual Auth HTTP and36 browser executions. All17 complete Original roots are retained and verified in `../evidence/p19/native-qualified-290/attention284`, including the unchanged179/40/29/36 IDs and all gates. Its three source-admission controls have zero exit-case credit.

Receipts are in `../evidence/p19/native-qualified-290`, `../evidence/p19/finance12-qualified-290` and `../evidence/p19/finance-qualified-290`. Full parent archives remain pinned by the GitHub artifact metadata. For small complete-JSON exports, the downloaded export ZIP/hash/CRC and every Original UTF8 byte are verified; the large full parent ZIP was not downloaded and is not claimed locally CRC-verified.

## Remaining exits

`P19_COMPLETE_SOURCE_CAPACITY.md` records the complete-source transport contract and every current cap. Its implementation, representative whole-capture/finance performance, multi-user throughput and recovery remain open. The isolated compiler result does not close them. The first lifecycle teardown deadlock remains preserved and its underlying cause remains open, although the same-source rerun succeeds. The new finalizer writes an honest INCOMPLETE Original on restoration exceptions without retrying or weakening a gate.

Full P18 journeys, independent P20 and installed P21 remain open. This is writer qualification only: full_P19_acceptance=false, independent_acceptance=false, installed_P21_acceptance=false, production_go=false.
