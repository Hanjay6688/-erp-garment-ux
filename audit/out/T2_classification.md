# T2 frozen / HOLD case classification (auditor, blind phase 1)

Source of evidence: my own T2 rerun on head 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc, run 36037873682 (INDEPENDENT_NATIVE_RERUN), jobs 107762384861 (ar), 107762384959 (temporal), 107762385235 (regression). Statuses read per case from the JSON lines, not from job colour. Job colour was green for all three jobs; the regression job's own verdict line is `T2_REGRESSION_VERDICT status=DISPOSITION_REQUIRED`.

Classes (blind pack): COVERED_BY_OWNER_DECISION+PROVEN / DECISION_EXISTS_EVIDENCE_MISSING / DECISION_MISSING. "Owner decision" counts only when written in the three contract files. Writer-quoted decisions of 24 Sep that appear only in scripts (`cp6_t2_regression.py:42-52`, `APPROVED_DECISION`, the `T2_APPROVED_ORACLE_B` decision strings in the run log) are UNVERIFIED_OWNER_DECISION until the owner confirms them. No frozen case is relabelled PASS here.

## Counts observed (regression job)
| group | statuses |
|---|---|
| BUSINESS | PASS 179, CONTROL_PASS 39, DATE_POLICY_REVIEW_REQUIRED 12 |
| IMPORTS | PASS 31 |
| VALUES | PASS 65 |
| NEW_CASES (AS 34) | PASS 25, COUNTEREXAMPLE 8, INCOMPLETE 1 |
| T2_APPROVED_ORACLE (harness re-scoring of the same 8) | MATCH 8 |
| T2_CALENDAR_POLICY (harness re-scoring of the 12 HOLD) | COUNTEREXAMPLE 12 |
| AO_TRIAL | PASS 8, INCOMPLETE 4 |
| APPROVED_ORACLE_B (harness) | PASS 5 |
| T2_IDENTITY | BUSINESS/IMPORTS/VALUES moved []; NEW_CASES moved 9 (8 PASS→COUNTEREXAMPLE, 1 PASS→INCOMPLETE); holds 12 identical |

ar job: AR_SEQUENTIAL PASS 146, AR_CONCURRENCY PASS 28. temporal job: AT 16 PASS + 4 races PASS, AU 15 PASS + 6 races PASS.

## 1. The 12 calendar date cases (BUSINESS, status DATE_POLICY_REVIEW_REQUIRED; harness T2_CALENDAR_POLICY = COUNTEREXAMPLE)
Ids: CALENDAR:{1_MONTHS,2_MONTHS,3_MONTHS,JAN31,FEB28,MAY31}:{UTC,Pacific/Kiritimati}:False.
Observed (my run): each shows `material_event_date` mismatch: the WIP revaluation event is dated on the cutting day (e.g. 2026-08-25, 2026-07-25, 2026-03-01, 2026-02-01, 2026-06-01) where the frozen oracle expects the invoice date.
Contract: ERP-DEC01 is DECIDED: "koreksi biaya/invoice pada periode yang masih terbuka mengikuti tanggal invoice. Ini harus konsisten pada nilai persediaan, jurnal, barang dalam proses, barang jadi, harga pokok penjualan, laporan menurut tanggal, dan indikator kesiapan data" (Master 1057-1062, Perubahan 999-1004). The same layer says the 12 date cases "masih perlu perbaikan serta bukti" and "Keputusan owner bukan hasil tes" (Master 1082-1086). R3.5: "12 HOLD tetap sampai kebijakan dan bukti lengkap" (Master 1406).
Classification: **DECISION_EXISTS_EVIDENCE_MISSING**. The contract decision exists (invoice date). The only evidence on 9add57e contradicts it (cut-day dating of the WIP leg). The harness's `calendar_decision` string ("Owner 24 Sep: 12 kalender HOLD - tanggal perpindahan nilai ke WIP mengikuti hari potong; status tetap HOLD") is not in the contract → UNVERIFIED_OWNER_DECISION. Status stays HOLD either way.

## 2. The 8 AS date cases (NEW_CASES COUNTEREXAMPLE; harness T2_APPROVED_ORACLE = MATCH)
Ids: DATE:False:{Asia/Jakarta,UTC,Etc/GMT+12,Pacific/Kiritimati}:True:{20,20.003}.
Observed: invoice date 2026-09-22; revaluation events, PO HPP events and the PO_HPP_GL_SYNC / MATERIAL_COST_REVALUATION journals dated 2026-09-23 (the cut/goods/sale day); the supplier-invoice journal stays 2026-09-22. The frozen oracle (recorded reference PASS at AU) expects 2026-09-22 for all of them, consistent with ERP-DEC01. T2_IDENTITY lists all 8 as moved PASS→COUNTEREXAMPLE.
Contract: ERP-DEC01 (invoice date) as above. Nothing in the three files adopts "HPP PO mengikuti hari barang jadi/penjualan" or "revaluasi bahan ke WIP ikut hari potong" (grep for "Ikut prinsip WIP", "delapan kasus", "hari potong" in the contract: 0 hits).
Classification: **DECISION_MISSING** for the behaviour the candidate implements; under the contract's own decision the observed result is a COUNTEREXAMPLE, so these cannot count as passing. The harness MATCH is a writer verdict against a writer-quoted decision (`cp6_t2_regression.py:42-52`) → UNVERIFIED_OWNER_DECISION; it does not resolve the disposition.

## 3. ADJUSTMENT_DATE:False (NEW_CASES INCOMPLETE)
Observed: Python assertion error inside the frozen oracle (`[(2026-09-23, 2026-09-23, 2026-09-23, {...: 20.01, ...: -20.01})]`), i.e. the oracle's expectation about the adjustment date no longer holds and the case did not complete. Harness APPROVED_ORACLE_B re-scores it MATCH under "Owner 24 Sep: ADJUSTMENT_DATE tidak disahkan otomatis; telusuri pembaca effective_date..." (writer-quoted).
Contract: no decision on the material-adjustment revaluation date beyond ERP-DEC01 (invoice date for cost corrections) and the AQ/AP rule that adjustments follow the physical date of the adjustment (Master 4304-4316 is about migration; the adjustment-date rule itself is not stated for this case).
Classification: **DECISION_MISSING**; per Master 4324 ("Tool error/setup error/missing data = INCOMPLETE, bukan BUG_PROVEN atau PASS") it stays INCOMPLETE.

## 4. AO_TRIAL INVOICE:{UTC,Pacific/Kiritimati}:{False,True} (4 INCOMPLETE)
Observed: oracle assertion errors: open-period cases show MATERIAL_COST_REVALUATION and PO_HPP_GL_SYNC journals on 2026-07-25 while the invoice journal is 2026-07-24 (invoice date); closed-period cases show a WIP revaluation event on 2026-09-25 (recognition day). The AO trial oracle expected invoice-date behaviour. Harness APPROVED_ORACLE_B re-scores all four MATCH under "Owner 24 Sep: AO periode terbuka - tanggal koreksi WIP/FG mengikuti hari barangnya berpindah tahap ..." / "AO periode tertutup - tanggal posting mengikuti hari pengakuan" (writer-quoted).
Contract: ERP-DEC01 for the open period (invoice date); for the closed period "Aturan periode tertutup tetap memakai penyesuaian terkendali yang sudah ada" (Master 1061). The closed-period recognition-day posting is consistent with the contract's closed-period rule only if "penyesuaian terkendali yang sudah ada" means recognition-day posting with the economic date kept; the open-period behaviour contradicts ERP-DEC01 as written.
Classification: open-period pair **DECISION_MISSING** (behaviour follows an unverified 24 Sep decision); closed-period pair **DECISION_EXISTS_EVIDENCE_MISSING** (contract rule exists, the trial oracle did not complete, so no proof).

## 5. What is COVERED_BY_OWNER_DECISION+PROVEN in T2 as run
- The 179 BUSINESS PASS, 39 CONTROL_PASS, 31 IMPORTS, 65 VALUES, 25 NEW_CASES PASS, AR 174, AT/AU 31 + races: these reproduce the AU reference per id (moved []). They are covered by the contract's standing rules and reproduced on 9add57e. Caveat: they ran with the harness fixture completion CP6_T2_FIXTURE=PAYROLL_APPROVED (each case's own uncovered attendance/work put into an APPROVED, unpaid payroll before readiness reads) and CP6_T2_SEED=QUIETED. Both are harness-side changes justified by writer-quoted 24 Sep owner policy (`cp6_t2_regression.py:24-40`), not by the contract. The contract's own rule is that setup differences must be declared (Master 4322-4324). So: PROVEN for the business assertions themselves; the readiness-dependent subset is proven only under the harness's payroll completion, which is UNVERIFIED_OWNER_DECISION.

## 6. Disposition summary
| bucket | count | class |
|---|---|---|
| 12 calendar HOLD | 12 | DECISION_EXISTS_EVIDENCE_MISSING (evidence contradicts ERP-DEC01; harness rule unverified) |
| 8 AS DATE COUNTEREXAMPLE | 8 | DECISION_MISSING (candidate follows a rule absent from the contract) |
| ADJUSTMENT_DATE INCOMPLETE | 1 | DECISION_MISSING; stays INCOMPLETE |
| AO trial INCOMPLETE (open period) | 2 | DECISION_MISSING |
| AO trial INCOMPLETE (closed period) | 2 | DECISION_EXISTS_EVIDENCE_MISSING |
| everything else | 174+31+31+65+230+25 (+races) | COVERED+PROVEN with the fixture-completion caveat |

T2 verdict as a gate (contract R1.6 no. 6, Master 1769: "Jangan menghapus assertion atau mengganti expected HOLD menjadi PASS"): the regression is reproduced and identical per id; it is NOT green. 25 case-results (12+8+1+4) depend on an owner decision that is not in the contract. The gate cannot be ACCEPTED on the contract alone; it is HOLD pending the owner's written confirmation of the 24 Sep dating decisions (or a contract update), after which the 12+8+4 would need re-oracling and rerun, not relabelling.
