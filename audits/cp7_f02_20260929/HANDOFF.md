# CP7 F02 — independent audit handoff

**Decision: HOLD F02. F02-01 is one current WIP defect demonstrated through two ordinary reversal paths. F02-02 is a separately disclosed and independently reproduced matching-to-allocation integration gate. `production_go=false`.**

Frozen product: `17e85404c9c5f088875099d7875be6342ca6b266`. Documentation checkpoint: `5dd3b781ceef161afe59739d9e74a72e049d6a30`. Combined P02/P03/P04 bundle SHA256: `b50edbb4f45c6e1282a3744096c5a74fbc2487a1442211307ac9d1ab45eb76cc`.

Latest writer head checked at completion: `e21f0b94c3d25a787b83470a28b557aa7a88326a`. Its identity/WIP sources and bundle builders are unchanged from the frozen F02 candidate. This finding has therefore not been superseded by a later source fix. Later F03 functionality has not been independently qualified in this audit.

This audit read the writer handoff and is **not blind**. Peer PR34 was supplied only after the original 74-case audit/report, and is recorded as a subsequent cross-check. The auditor independently wrote the oracle and 20 new cases, reran 54 existing writer cases, and separately checked historical writer evidence. Reused fixture builders and the isolated install/restore harness are disclosed. No product file, writer branch, hosted/UAT database or production database was changed.

## F02-01 — valid reversal with BS makes current WIP falsely conflict

**Severity: major functional; blocks acceptance of the delivered P04 source adapter.** The reader fails closed: this evidence does not show money/journal corruption, extra inventory, or an unsafe allocation being accepted. The demonstrated failure is loss of a usable current WIP result after a valid business correction.

### Reproduction A: reverse QC containing BS

Case: `AUD_F02_QC_BS_REVERSAL`.

1. Use the existing actual cut → pickup → sewing fixture with 100 PCS across two sizes (60/40).
2. Send 40 PCS of the selected size to laundry; receive 30 GOOD. Post QC for 15 GOOD + 5 BS using ordinary `POST_FINAL_SKU`.
3. Capture current WIP. The accepted baseline is input 100 = WIP 80 + FG 15 + BS 5.
4. Read the QC header's current `row_version`; invoke ordinary `REVERSE_FINAL_SKU` with that version and a reason. The command succeeds. The associated BS case is retained with status `CANCELLED`.
5. Capture again through both `erp_cp7_capture_cutting_wip_v1` and `erp_cp7_capture_production_wip_v1`.

Expected through both facades: `COMPLETE`, input/WIP/FG/BS/withheld/exited = **`[100,100,0,0,0,0]`**.

Observed through both facades: **`CONFLICT / BS_SOURCE_LINEAGE_MISMATCH`**. The combined facade identifies component `CUTTING`.

The old archive remains identical and becomes `ARCHIVED_STALE`. The fresh reader does not change the business boundary.

### Reproduction B: reverse a laundry receipt containing BS

Case: `AUD_F02_LAUNDRY_BS_REVERSAL`.

1. Start from the same actual 100 PCS origin, send 40 and receive 30 GOOD, without QC.
2. Receive the remaining 10 as 5 GOOD + 5 BS through ordinary `POST_RECEIPT`.
3. Current production result correctly reports **`[100,95,0,5,0,0]`**.
4. Read the new receipt header's current `row_version`; invoke ordinary `REVERSE_RECEIPT` for that receipt.
5. Capture the same production scope again.

Expected: **`[100,100,0,0,0,0]`**. Observed: **`CONFLICT / BS_SOURCE_LINEAGE_MISMATCH`, component `CUTTING`**. The earlier archive becomes stale.

### Controls that passed

- Ordinary QC with 12 GOOD and no BS, followed by its reversal and then receipt reversal: **100 WIP**, no false conflict.
- Rework of four from the original five BS: in progress `[100,84,15,1,0,0]`; completed one GOOD/three BS `[100,80,16,4,0,0]`; ordinary completion reversal restores **`[100,80,15,5,0,0]`**.
- Existing writer rework, rewash/redispatch, opening output reversal and unsourced-BS recovery reversal tests pass.

### Source seam and requested correction

- `scripts/cp7-src/wip/source.sql`, BS CTE: captures retained BS rows, including cancelled history.
- `scripts/cp7-src/wip/normalize.sql`, receipt/QC loops: constructs physical nodes for posted sources only.
- The subsequent BS loop processes all captured cases and requires their old source node to exist. A valid reversed source therefore looks like an active orphan.

Make the active physical projection agree with accepted reversal semantics, while retaining provenance/dependency information for archive staleness. Keep actual orphan active BS and inconsistent active lineage fail-closed. Do not delete history, relax the negative-prefix guard, weaken authorization, or turn a conflict into a zero balance.

Retest the two counterexamples and both controls first. Also cover a new valid QC/receipt after the old reversal, with old cancelled and new active BS coexisting, and a mixed selected scope containing the corrected origin. Preserve genuine orphan/lineage-conflict rejection, immutable archives, 2000-row completeness, auth/replay and no business-write guarantees. A product fix is still required; the auditor made none.

## F02-02 / X06 — matching result is not bound to allocation

**Origin: user-supplied peer finding in [draft PR34](https://github.com/Hanjay6688/-erp-garment-ux/pull/34), followed by a new independent reproduction. This is not claimed as the auditor's original discovery. Classification: OPEN integration acceptance gate, not a proven live transaction or authorization bypass.**

The peer's [run 36525980112](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36525980112) tests the same frozen F02 product. Its raw report is `PROBED_WITH_FINDING`: the green workflow means the reproduction assertions completed and recovery gates passed. It does **not** mean the incompatible edge was rejected. Its identity/membership and mixed-origin/replay results are valid limited checks, not evidence closing all F01 or F02. The artifact ZIP digest and raw results were checked and retained separately.

Independent supplement: [run 36528326077](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36528326077), audit commit `9f2ff86af5c5eefaca637df8e7210ee7c79dd20b`, case `AUD_F02_X06_MATCH_BINDING_REPRO`. This executes the unchanged, hash-pinned bootstrap/graph/matching/yield SQL on disposable PostgreSQL 17.6. It is **private-kernel-only**, not another full ERP/Auth/HTTP installation. Previous full-package private ACL/REST denial and recovery evidence are preserved.

Independent input: one source of **17 PCS, XS, explicit yield 2/3 → 11 projected GOOD**. Source color is required FACT RED. Target key and size stay fixed; target reference changes from revision1/RED to revision2/BLUE.

| Check | Observed |
|---|---|
| RED → RED, use actual matcher result | `CANDIDATE_MATCH`; allocation `FEASIBLE` — positive control passes |
| RED → BLUE | Matcher returns `INCOMPATIBLE / COLOR_MISMATCH` |
| Submit edge honestly labeled `INCOMPATIBLE` | Allocator rejects `CP7_WIP_INELIGIBLE_ALLOCATION` |
| Same positive edge, substitute `CANDIDATE_MATCH` | Allocator returns **`FEASIBLE`**, no violations |
| Required color proof missing | Matcher returns `NEEDS_CHECK / COLOR_NEEDS_PROOF` |
| Substitute `CONFIRMED_TARGET` without that proof | Allocator returns **`FEASIBLE`**, no violations |

The target revision/constraint changes do not enter `check_allocations`; it receives only the supplied target key and match label. This proves the missing binding, not an existing live stale-preview transaction. Exact capacity/yield checks still operate correctly on properly matched edges.

**Scope adjudication:** owner registry X06 belongs to P04 and says incompatible positive edges must be rejected. Writer explicitly leaves authoritative target/policy/source joins to P06/P07. Therefore record X06 **OPEN** across that seam; do not promote the current label-enum check to full X06 acceptance. It may be implemented as a server-side composed evaluator in the later join, but the acceptance obligation must remain visible until independently qualified. The private helper's caller-controlled intermediate input alone is not an operational exploit. F02-01 already independently blocks the delivered WIP adapter.

**Writer action:** bind each edge to server-computed matching from the same source, target, constraint and policy/identity versions as allocation. Recompute or verify authoritative results at the composed boundary; a caller-supplied string is insufficient. Keep keys/versions and source capture coherent. Retest genuine compatible edges, FACT mismatch with a forged positive label, missing required proof, and target/constraint changes after preview. When the planner route exists, add real Auth/HTTP proof that callers cannot bypass that boundary. No code change was made by this audit.

The original 74 full-package cases remain **72 PASS + two F02-01 counterexamples**. This adds **one supplemental kernel case with an X06 counterexample**, reported separately because its provenance and runtime scope differ. See `X06_ORACLE.md`, `x06_probe.py`, `X06_CROSSCHECK.json` and the supplemental raw report.

## Results by evidence origin

| Origin | Execution | Final unique result |
|---|---|---:|
| New auditor cases | 14 native + 4 real two-session + 2 Auth/HTTP | **18 PASS, 2 COUNTEREXAMPLE** |
| Writer cases rerun by auditor | 44 native + 7 two-session + 3 Auth/HTTP | **54 PASS** |
| Historical writer evidence cross-check | P03 15 + P04 39; excluded repeated smoke | Receipts, raw reports, run SHAs and all 36 source-hash entries match |
| Auditor application gates | Same frozen product | 638 unit/DOM PASS; security and build PASS; 48 original framework files verified |

Original full-package database/race/HTTP total: **74 cases = 72 PASS + 2 COUNTEREXAMPLE**. Those two original counterexamples are F02-01, not two unrelated bugs. The supplemental X06 case above is separate. Historical checks and repeat executions are not added to the unique count.

New auditor coverage includes exact integer/rational yield up to 30 digits, shared input/edge limits, malformed PCS rejection, calendar gaps/exact deadline boundaries, explicit policy cycles, all-or-nothing bulk with invalid late rows, revisions above JavaScript's safe integer, 50/51 scope and 2000/2001 source bounds, false opening-control conflict rejection, privileged-role boundaries, current authorization after real request-lock waits, atomic opposite-order policy bulk, and private REST/other-actor denial.

P03 has no remaining blocker found within this bounded audit. P04's normal forward paths and private kernels pass, but its delivered reversal adapter remains blocked by F02-01.

## Runs, original failures and recovery gates

- [Initial auditor run 36526434075](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36526434075), commit `e1c9e72b0ddd6fad26ffc0e21473184c73c75c2f`: **69 PASS, 5 INCOMPLETE**. Five incomplete results were auditor fixture/setup issues, not product findings.
- [Targeted auditor run 36527127588](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36527127588), commit `81bcafbc43e8f65b1dafe008565b2fe1f24e061b`: only those five cases, **3 PASS, 2 COUNTEREXAMPLE**. The 69 prior passes were preserved.
- `PROBE_ADJUDICATION.md` explains the version-helper correction, valid synthetic source-volume setup and isolated HTTP fixture. Expectations and product guards were not relaxed. Initial raw failures remain available.
- Both runs install the accepted **30/30 CP6 package files** before the CP7 bundle. Both preserve the primary disposable baseline, restore the CP6 business/public boundary after removing CP7, pass the security-advisor gate and complete backup/restore with identical data and equivalent engine answers. The documented pg_cron restore exception is retained in the raw recovery report.
- All race copies are removed. Auth users/sessions return to the initial counts; HTTP containers/databases are removed. The target job is red because the product counterexamples remain, not because setup or cleanup remains incomplete.

Historical source links: [P03 run](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36509688817), [P04 run](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36515586854), [writer application run](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36515590677). Their actual ZIP bytes match the recorded SHA256 and preserved reports. See `CROSSCHECK.json` and `REVIEW_NOTES.md`.

## Scope preserved and still open elsewhere

Accepted CP6 and F01 findings are not reopened by this CP7 adapter defect. UI and P02 snapshot source are unchanged from accepted F01; no new independent F02 browser claim is made. Writer's six shell browser passes are historical cross-check only and do not qualify connected P03/P04 screens.

Full policy/source/target planning joins remain P06–P08. Connected sell/return R10 remains CP7/P11. Price-later failed wash remains F03/P13. Full P18 lifecycle, P19 scale, P20/P21 release and production authorization remain separate gates. FG in this adapter means production disposition, not sale/conversion-adjusted on-hand. These limits are not additional discovered bugs.

Evidence: `FINAL_CASES.json` holds final per-case provenance; `INITIAL_CASES.json` preserves original adjudication; `CANDIDATE.json`, `PROBE_PINS.json` and `EVIDENCE_MANIFEST.json` bind the candidates, probes and raw compressed reports. The checked-in workflow runs only the five targeted cases by default (`F02_TARGETED=1`); full mode runs the complete suite with the corrected HTTP isolation. No report-only commit triggers another run.
