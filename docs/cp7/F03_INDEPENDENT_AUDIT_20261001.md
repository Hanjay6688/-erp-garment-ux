# Independent F03 audit — 2026-10-01 UTC / 2 October WIB

**Verdict: INDEPENDENT_ACCEPTED_F03_CONTRACT_SCOPE.** The frozen F03 candidate
passes the declared P09–P13 audit matrix and affected integration checks. No
confirmed material product defect or required execution gap remains in this
matrix. This supersedes the earlier INCOMPLETE checkpoint; it does not grant
full CP7 acceptance or production approval. `production_go=false`.

New auditor checks: **26 local +23 native/race/Auth/browser PASS**.
Retained cross-checks executed by the auditor: **502 PASS +3 separate smokes**.
Counts describe overlapping executions, not unique requirements.
The full original receipts, hashes, artifact IDs and source pins are indexed in
[runtime/INDEX.json](evidence/f03-independent-20261001/runtime/INDEX.json).

## Candidate and independence

- Frozen product: `eb6b8682e97e94c95f89d431ab81974c54ddcbaf`.
- F03 SQL SHA256: `6df48df8bbf7113636ce504b2f1f894b43a6444f803ba71a0007c18b32f6907c`.
- Installed F03 stack: 31 private roles over the accepted disposable CP6 package.
- Audit branch: `audit/f03-independent-20261001`; product and writer branches
  are unchanged by this audit. All business fixtures and Auth users are disposable.
- This is independently designed and executed verification, **not a blind audit**.
  Writer progress and handoff were read. The auditor predeclared separate money,
  quantity, authorization and recovery expectations before running new probes.
  Writer suites are explicitly labeled retained cross-checks. No peer auditor's
  conclusion supplies the independent expected values.

The installation recipe, lawful upstream fixture builders and strict cleanup
runner are reused. Native writers create stock, entitlement and journal facts;
expected final amounts are not inserted into result tables. Reused fixture
builders do not become new independent coverage merely because they are called.

Latest writer comparison inspected: `50c4e46a9a9388d4644414a68df5d0e59f00671f`.
The product delta since the frozen candidate is in planning/actuals/report
publication and related F04/F05 types and panels. No F03 source change was found
in that comparison. This audit does not accept those newer F04/F05 changes.

## Newly authored independent checks

Local 26/26 contract checks pass: exact decimal handling including values beyond
JavaScript's safe integer, discounted invoice arithmetic, installment capacity,
quantity precision, invalid input and real calendar dates. These are not database
or connected-browser proof.

The corrected independent run [36912838566](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36912838566)
passes **23/23** at probe commit `120dfe321a47a7d65db86db14bc1222af3fbe160`:
14 native, four concurrent-session, three real Auth/REST and two connected
desktop/mobile browser journeys. Every restoration/advisor/cleanup gate passes.
The original failure is preserved rather than retroactively marked green. Business
worksheets include:

| Independent worksheet | Required result |
|---|---|
| Production 60 PCS / value 900; sell 17 ×31.17 −0.23; cash 173.29; return 3 / credit 93.42 | FG46/value690; sales436.24; COGS210; profit226.24; AR262.95; cash173.29; inverse restores60 and baseline ledger |
| Seven PCS ×37.13 −0.06 | Invoice259.85; cash123.45 leaves136.40; final136.40 settles; payment changes cash/AR without repeating revenue or stock |
| Two Grade B and one HOLD returned | Distinct physical grades; cost restored30; AR148.52; exact inverse |
| Receipt1.234567 ×17.000001 | Source value20.987640; AP20.99; one physical event |
| Receipt3 ×22,000,000.01 | AP66,000,000.03; exact replay; no integer-cent overflow |
| Approved payroll1000; installments333.33/333.33/333.34 | Same entitlement settled once; first inverse leaves333.33 outstanding; stock/HPP unchanged |
| Two payments of200.01 competing for invoice259.85 | One committed payment; AR59.84; same UUID gets identical result, different stale intent refused |
| Two payroll payments700.01 competing for1000 | One payment; remaining299.99 |
| Permission revoked while the identified cached-request worker waits | Exact42501 current-authority denial; committed state unchanged |
| Real HTTP and browser | Current deactivation refused, private schema REST refused, exact envelope survives lost committed response/reload, one payment, failed refresh retires old money |

Other independent checks cover changed UUID payloads, operational money
redaction, thirteen invoices across5/5/3 pages, FG adjustment inverse,
read-only reports, invalid dates, stale payroll intents and one-cent overpayment.
The existing paid-new-invoice return refusal is respected; it is not an invented
refund policy. The original three-piece preparatory worksheet was supplemented
by the executed seven-piece and seventeen-piece runtime worksheets; it is not
claimed as another native execution.

Initial run36911271122 has20 PASS/3 INCOMPLETE. Its receipts remain preserved.
The three incomplete results were auditor measurement errors: exact invalid-date
SQLSTATE and premature browser response-loss observation. The correction keeps
all business amounts, authority and recovery assertions. See
[probe errata](F03_INDEPENDENT_PROBE_ERRATA_20261001.md).

## Retained cross-checks executed by this auditor

These counts describe executions, not unique requirements or newly authored
oracles. The native and browser journeys overlap intentionally.

| Group | Declared executions | Auditor run |
|---|---:|---|
| P09 procurement/material/invoice/return |132 +3 separate smokes|36910147400|
| P10 FG/adjustments/ledger/book |34|36910147400|
| P11 sale/reservation/payment/return |64|36910147400|
| P12 source/attendance/Nota/payroll |90|36910147400|
| P13 finance/period/comparison/recost |50|36910147400|
| Cash/readers/journal/misc/installments |61|36910147400|
| Paid-target supplier credit |5|36910147400|
| Customer custody and lawful old-sale/imported refund |10|36910147400|
| Production, late cost/year-end, rework/range/redye, FREE/WAIVED, capacity and supplier authority |32 native/HTTP/race|36911723469|
| Connected production/sale/report, redye, service issue and complete source capacity |8 browser|36915203087; initial36911723469 incomplete|
| Literal O06 reservation and O07 size gap |2 on composed planner stack|36911723469|
| Multi-receipt supplier returns and combined ledger/private contexts |14|36913310583|

Source pins: retained eight buckets at `b38d1cd2ed9b8e28dda425fa1c2df390f594adfd`;
extended economic/planner at `7a7d4c7147dd088df18e6998706dc89d3ca241ab`;
browser recheck at `cc64cb11caac0fd57a6dccbaa8afca5a96697a90`; additional at
`da077c69bf40c358d8302296dafee1dfac482eed`. Each workflow verifies the frozen
product diff before executing. The planner seam uses its explicitly composed
planner stack, not the F03-only bundle. Its SHA256 is
`ee509f7b3b2d6815d6810dd488cc17dca62312ad9b9b8e295917001a5b110e25`.
The first extended workflow remains red because three browser hosts could not
bind their loopback port; its economic32 and planner2 jobs passed separately.
The separate browser rerun36915203087 passes8/8 with the unchanged cases,
actual Auth/HTTP, both viewports and complete restoration. Its port preflight
confirms the isolated listeners were available; no unrelated process was killed.
The original INCOMPLETE receipt is preserved separately.

The writer's original qualified eight reports and run36861170597 were separately
inspected and match their reported counts/source bundle. Their historic test
results are not relabeled as auditor executions. Earlier cured counterexamples
remain historical unless reproduced on this candidate.

## Restoration and evidence limits

Runtime receipts must show complete case groups, unchanged predecessor function
definitions/owners/declared ACL boundaries, restored CP6 state, no leaked test
sessions or Auth users, dropped disposable HTTP/browser/race databases, unchanged
primary temporary database, and acceptable advisor delta. The package backup
drill reports `RESTORED_SAME_MEANING`. Its 19 declared missing-pg_cron/schema-cron
restore diagnostics are an existing disposable-clone limitation, not zero-error
cron restoration; unexplained errors must remain zero.

All final receipts satisfy those requirements. Sixteen selected real screenshots
were visually inspected, including both new auditor recovery journeys and
retired financial facts after access loss. The exact inspection list and hashes
are in [VISUAL_REVIEW.json](evidence/f03-independent-20261001/visual/VISUAL_REVIEW.json).
Two original independent screenshots are retained in that directory. Other
captures remain in the linked workflow artifacts; no claim of exhaustive visual
inspection is made.

Some retained cost-provider rows contain the historical literal label
`EXPLICIT_F03_26_ROLES`. The enclosing installer and before/after runtime checks
verify the actual 31-role stack and exact current bundle. Preserve the raw label
and use the enclosing source metadata; do not rewrite old evidence.

Official local build including ownership/access/CSS gates and the client secret
scan passes. The retained local suite has1156 PASS and one F04 PostgreSQL setup
failure in this root-only environment. It was not skipped or called a product
failure. Native F03 evidence comes from the disposable CI receipts.

This audit does not claim hosted production execution, all final CP7 lifecycle/
scale/resilience scenarios, release cutover or owner production approval.
The demo-design comparison, iPad-specific visual acceptance and final P18–P21
remain their explicit CP7 gates. Current captured desktop/mobile interactions
are tested; they do not establish every possible viewport or every input.

`production_go=false` throughout.

## Findings and writer disposition

- **Independently authored tests:** no confirmed product defect. Money/quantity
  worksheets, exact inverses, current authority, concurrent capacity and
  connected recovery all pass their predeclared expectations.
- **Retained cross-checks:** no current product defect reproduced. This includes
  lawful FREE/WAIVED, late costs, historical SKU/source versions, supplier credit,
  customer custody/refund, partial payroll and exact-size planner boundaries.
- **Audit apparatus:** initial invalid-date and timing assertions plus the
  occupied browser listener were corrected or isolated and successfully rerun.
  Original failures remain visible and create no product-repair ticket.

No product patch is requested. The unified [writer handoff](F03_INDEPENDENT_WRITER_HANDOFF_20261001.md)
records the acceptance source and the final CP7 gates that remain outside this
F03 decision. Changes to affected transaction, permission, date, lock or costing
paths require a targeted new audit; unrelated documentation changes do not.
