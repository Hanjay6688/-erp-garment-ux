# Native T2 on frozen writer head — audit run 36125151913

- Run: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36125151913; audit trigger `79e887e763f1ac1a0db60a55198b5d400b6f9915`; writer/tool head `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`; release_evidence=false, production_go=false.
- Workflow `.github/workflows/gpt-cp6-round9-t2.yml` SHA256 `1834620471235a96674b33ca805f6aaf5c794d19bbbe64dea03bfbd278fc24ba`; disposable DB, no hosted writes. This reproduces writer T2, **not independent release acceptance**.
- Per-case list for **all 600 rows** in `out/gpt_r9_t2_cases.json`, preserving group, original case ID and original status; each job artifact below. The added C0 group has 25 separate new IDs and never changes frozen IDs.

| Job | Conclusion | Original results | Artifact |
|---|---|---|---|
| `108039445366` AR | SUCCESS / native WRITER_PASS | `AR_SEQUENTIAL` 146/146 PASS; `AR_CONCURRENCY` 28/28 PASS; fixture payroll 6/6, refused=[] | `10858967717` |
| `108039445443` temporal | SUCCESS / native WRITER_PASS | `AT_CASES` 16/16, `AT_CONCURRENCY` 4/4, `AU_CASES` 15/15, `AU_CONCURRENCY` 6/6 PASS | `10859687248` |
| `108039445222` regression | SUCCESS / native DISPOSITION_REQUIRED | BUSINESS 179 PASS +39 CONTROL_PASS +12 DATE_POLICY_REVIEW_REQUIRED; IMPORTS 31 PASS; VALUES 65 PASS; NEW_CASES 25 PASS +8 COUNTEREXAMPLE +1 INCOMPLETE; C0 25/25 PASS | `10859463234` |

**Identity:** `T2_IDENTITY` original BUSINESS230, IMPORTS31, VALUES65, NEW_CASES34 counts and order unchanged. Exactly **12 historical HOLD identical** (`DATE_POLICY_REVIEW_REQUIRED`), nobody left/entered HOLD. 8 old date cases and one adjustment case moved relative to an *old pre-owner reference*; their frozen outcome remains recorded verbatim; eight owner date oracle `MATCH`, five owner AO/adjustment decisions `MATCH`, calendar policy twelve `MATCH`, and new C0 group 25/25 PASS. A `MATCH` is not a retroactive PASS for a frozen case. AO trial original 8 PASS +4 INCOMPLETE. Status stays `DISPOSITION_REQUIRED`; see exact 600 case rows.

**All 21 original rows outside PASS/CONTROL_PASS, unchanged:**
- `BUSINESS/CALENDAR:1_MONTHS:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:1_MONTHS:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:2_MONTHS:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:2_MONTHS:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:3_MONTHS:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:3_MONTHS:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:JAN31:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:JAN31:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:FEB28:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:FEB28:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:MAY31:UTC:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `BUSINESS/CALENDAR:MAY31:Pacific/Kiritimati:False`: `DATE_POLICY_REVIEW_REQUIRED`.
- `NEW_CASES/DATE:False:Asia/Jakarta:True:20`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:Asia/Jakarta:True:20.003`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:UTC:True:20`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:UTC:True:20.003`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:Etc/GMT+12:True:20`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:Etc/GMT+12:True:20.003`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:Pacific/Kiritimati:True:20`: `COUNTEREXAMPLE`.
- `NEW_CASES/DATE:False:Pacific/Kiritimati:True:20.003`: `COUNTEREXAMPLE`.
- `NEW_CASES/ADJUSTMENT_DATE:False`: `INCOMPLETE`.

Job final JSON verifies `primary_unchanged=true`, `clone_remaining=0`, `production_go=false`, `independent_acceptance=false` for regression; AR/temporal `primary_unchanged=true`, clones 0 and cleanup. All three actions jobs SUCCESS. Run completion only means the script executed successfully, not that CP6 passed.

**Next:** commit/push this per-case ledger, then dispatch the single planned T3 package workflow; wait for completion before the rollback workflow. Continue CP6 HOLD; 75 C6 +22 ALL remain UNVERIFIED on new BB–BE.
