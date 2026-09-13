# CP6 W — paid scrap canonical business date

Status at authoring: V independently FAIL P2; W writer verification pending.
`production_go:false`. Independent final W audit and new-path HTTP/UI remain pending.
No main, UAT, legacy, production, deployment, merge, or CP7 authorization is implied.

First W native162 (run34773703073, job103767815801, commit
`b64ee3b4c12f185c2febd5fe53b0cd7e35e26d50`) failed at historical-evidence
recovery step9, before database startup or W business tests. The recovery helper
incorrectly selected the current W workflow's semantic binder for frozen V159
payloads, requiring nonexistent W reports. The correction pins the already
verified V160 binder by commit, tree and SHA256, preserving every historical
semantic assertion and continuing to reproduce the original159 string-comparison
failure. W still uses its own complete current binder at the final proof gate.
Both failed162 artifacts and its log are retained; no migration bytes change.

Native163 (run34779482518, job103783740872, commit
`8d0b2da606110983d0e944926d831a973d703bcd`) passed historical recovery,
then failed step66 during all four BEFORE_W upgrade probes. An unparenthesized
SQL CASE expression inside the predecessor-check PL/pgSQL IF condition caused
`syntax error at end of input`. W was never installed. All four probes restored
the full boundary, the unseeded runtime and schema USAGE. The forward correction
parenthesizes that CASE expression and updates its migration/rollback digest
pins; it does not change any installed function body, owner or ACL. Local
pglast8.4 reproduced the original parser failure and accepted all seven
migration/rollback PL/pgSQL blocks after correction. This is parser evidence,
not native runtime success. The original failed163 ZIP and log are retained:
artifact10325270090, 2,436,063 bytes, SHA256
`e4f162d2320976f9f38b0935173872b6545f5b22ada044c996a31b18c1982d4f`.
Published V and earlier SQL remain byte-identical; failed W commits remain in
history. W writer and independent verdicts remain pending until their gates pass.

## Immutable independent finding

V business source: `7be634e663a61545b909cf0367d12461ae7aa798`;
tree `a29235ba5386cc905cb4fb9ee784e16db4a5ce7a`.
Test-only audit commit `bf0075826177b43034f3fa73594d5f0525a03b1c`;
tree `d8d79734bd81c8fd3d817d4ce460ae8aebf69063`.

Native independent run161 `34771815011`, job `103762657743`, step67 FAIL
on PostgreSQL17.6. The frozen attack source is
`scripts/cp6_v2620v_scrap_adversarial.py` (SHA256
`8e1e2ceee9cdf71fb7d0c670d2097fafa4185b4548e786a8b2370aad611c67c5`).
This failed run must not be relabeled PASS or confused with writer native160.

Legal AVAILABLE scrap batch1kg, DRAFT sale0.5kg, cash0.03, physical timestamp
`2026-09-03T00:30:00+07:00`; actual session and current user `authenticated`,
ERP role OWNER. `erp.post_scrap_sale(uuid)` casts `s.physical_at::date`.

| Caller zone | Economic/journal date | Sep2 cash delta | Report |
| --- | --- | --- | --- |
| UTC | Sep2, wrong | +0.03, expected0 | READY, false |
| America/New_York | Sep2, wrong | +0.03, expected0 | READY, false |
| Asia/Jakarta | Sep3 | 0 | READY, lawful |
| Asia/Tokyo | Sep3 | 0 | READY, lawful |

Two qualified counterexamples, two lawful controls, zero oracle failures.
Draft inert, total cents conserved, caller timezone preserved; complete boundary
533 functions and 210 tables restored. Not a total-money-loss or stock/HPP claim.
Authenticated SQL proof is not HTTP/UI reachability proof.

Independent artifact10322770123, 2,453,379 bytes, SHA256
`bc44b878844b6f7f31a87510d54cc9fe14f16e703bbbfe50c1584624844e25d5`.
Preserve alongside the V native160 and earlier failure evidence.

## Forward-only correction

CLI-created migration `20260913173840_erp_v2_6_20w_cp6_scrap_business_date.sql`.
Only three existing functions are replaced. Owners and ACLs are unchanged.

| Function | Correction |
| --- | --- |
| `erp.post_scrap_sale(uuid)` | Derive date through private Jakarta `_cp3_business_date(s.physical_at)`; no session timezone mutation. |
| `erp.run_v267_financial_truth_checks()` | CRITICAL `V2620W_SCRAP_BUSINESS_DATE` for mismatched POSTED/REVERSED original SCRAP_SALE economic dates. |
| `erp._v268_financial_report_checks_pre_scope()` | Propagate W detector into report confidence. |

The detector compares economic date, not posting date: closed-period posting may
lawfully move to the current posting period. Existing historical misdates cause
atomic migration refusal; W does not rewrite posted journals or conceal history.

W verifies exact V source/platform, all seven inherited U capsule records, all
three V capsule records, installed definitions, owner/ACL, and inherited T
helper/fact security. Private W capsule contains exactly three originals.
Admission locks and post-use snapshot cover80 tables, adding V capsule,
scrap_batches and scrap_sales to the V77 boundary. Rollback requires closed
database admission, old-session drainage, exact installed pins and no successor.
W-to-V restoration checks all533 functions, definitions, owners and ACLs, not
only the three replaced functions. Historical migrations and rollbacks stay frozen.

## Required native predicates, not results claimed by this document

- Paired BEFORE_W four cases: two V bugs, two controls; same four AFTER_W PASS.
- Wrong-history upgrade refusal2, lawful-history upgrade acceptance2, exact
  catalog/table restoration after every probe.
- AFTER_W expanded21: microsecond midnight boundaries3; current time in zones
  behind/ahead2; one cent; future refusal; non-owner refusal; inert draft delete;
  posted update/delete refusal; post replay refusal; blank reversal refusal;
  reversal replay; zero amount; weight over-capacity; full-weight reversal;
  posted/reversed predecessor-corruption detector2; closed period; ACL contract.
- Three real natural row-lock schedules: post/reverse, duplicate post, first
  writer abort. Distinct backend PIDs, actual blocked query and blocking PID,
  no manual prelock, no retry; correct dates, exact cents and linked inverse.
- W direct rollback guards7 plus inherited helper/security preflight guards9;
  coherent capsule forgery rejected before admission changes; exact W-to-V.
- Full historical regression, Auth95, browser26, 360 closed-admission schedules
  (18 targets x5 operations x4 orderings),90 proven backend body entries.
- Rollback setup units188 and endpoint negative controls remain mandatory.
- Full rollback ladder, no W platform/application/capsule residue, zero disposable
  clone databases, physical stack cleanup, exact source/evidence binding.

The workflow expresses W residual fields in a separate concatenated
`jsonb_build_object`, respecting PostgreSQL's100-argument limit without removing
earlier checks. Lossless packaging retains the complete raw payload inventory.

## Owner constraints

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.

Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
Posted history is immutable; corrections must preserve linked lineage.
CP6 closure precedes CP7 rev3 WIP-first, CP7.5, CP7C, then CP8. CP9 obsolete.
