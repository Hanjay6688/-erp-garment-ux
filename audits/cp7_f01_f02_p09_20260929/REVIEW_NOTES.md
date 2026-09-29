# Review provenance and scope

- Request: independently retest writer F02 repairs, search additional F01/F02 seams, and include P09. No product edit, hosted write, merge or deployment.
- Product frozen at `ee8699829bc53799e5f840bb5490059e456fa81a` using documentation checkpoint `e3ddcec94c4db2b6fe299cdadc82f50d57781bfc`. Latest observed `f41e6eb1dd7fc44d8cd60a1b02ff3998e14f499a` adds P10 FG modules and App routing; those are excluded. Reviewed F01/F02/P09 SQL modules are unchanged between checkpoint and observed head.
- Writer handoffs read before retest: F02_FIX_HANDOFF; P09 procurement/count/combined-invoice handoffs. This is explicitly disclosed retesting, not blind discovery.
- Prior independent F02 probe copied byte-for-byte (SHA256 `43ac48d8ec4dffdffa94722348a503a345771094d1f33219c72a4d70431c29d1`). Five relevant original case bodies selected without changing expectations. No obsolete label-only allocation test is counted as a valid positive control against the new matching protocol.
- New matching tests call SQL directly. They do not use writer `bind_compatible_fixture` to silently supply compatibility data. Red/blue, unknown proof, stale version and snapshot, duplicate/missing facts, capacity and yield controls are explicit.
- New P09 public-writer cases use independent arithmetic: 1×22,000,000; 7×13+11×17=278; physical counts 10/10→8/7. Master builders are shared setup. Stock, invoices and journals under test are created through public commands. F01 snapshot fixtures retain disclosed administrative source setup; they prove reader isolation, not physical posting.
- P09 harness is reused for installation, function/ACL boundary, original-function restoration, disposable Auth/race/browser copies, and reporting. Adapter wraps case factories only. Product SQL and frontend source are unchanged.
- Cross-check raw writer ZIPs matches published hashes exactly: F02 `c32513351a3e2c4fc4b571701295ddb239c0a4c635f77e0da83d1c6d3a54a3d8`; P09 `57d3345387f1b954f72c99094abefe30f3d7ba5138fb252511a286107df2324b`. Raw reports match source bundle hashes and published raw JSON hashes. Both package gates show primary unchanged, successful backup/restore, security gate true and Auth users 0 before/after.
- Writer F02: 53 PASS + one smoke (run36558701316). Writer P09:121 PASS + three smokes, including18 browser cases (run36558701532). This is cross-check evidence, separate from auditor execution.
- Writer app runs36558707443 and36558701502 succeeded. Inspected shell log109374038242:690 unit/DOM tests in65files; source/access/recovery/backend ownership, build/secret scans and6shell browser cases pass. CodeQL jobs succeeded. This is writer app evidence, not an additional independent frontend acceptance.

## Boundaries that must not disappear from the handoff

- P04 owns X06. Private matcher recomputation can close the reproduced label-forgery defect if independent tests pass. Authoritative server-composed facts, current versions and the future public P06/P07 planner path still need composed Auth/HTTP proof. Do not describe a pure private JSON function as proving a live client cannot forge facts.
- P09 implemented increments are receipt, UOM, material/transfer/count, supplier invoice/return and receipt inverse. Full P09/F03 remains open: material issue workflows, multi-input/zero-history count UI, mixed-receipt and paid-source supplier-return work, full exit matrices and later family/release gates. A passing multi-input native command does not prove its UI exists.
- Previous safe F01/F02 evidence is preserved, not relabeled as newly rerun. CP6 remains closed at its accepted contract scope. `production_go=false` remains unchanged.

## Executed outcome

Run36563251161 at auditor commit`b345d4e4fb50e0142d9e741acccf926863bb5617` passed on its first execution:16 independent cases,146 writer cases rerun and3smokes. No failed fixture, narrowed expectation or corrective rerun occurred. Source hashes match the pinned writer candidate. All restoration/security gates pass;18browser cases have0console errors and Auth users/case databases cleaned up. Representative count-desktop and combined-invoice-mobile screenshots inspected from this run.

The closed findings are F02-01 and the reproduced private matching-label bypass F02-02. No additional counterexample was found in the tested scope. Neither a full P09/F03 closure nor public planner/X06 integration acceptance is claimed. See HANDOFF.md for exact closure boundaries.
