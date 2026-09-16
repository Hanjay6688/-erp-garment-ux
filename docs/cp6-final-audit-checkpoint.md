# CP6 final audit checkpoint — execution pending

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Only competition/cp6-j-closure-20260911 may advance, fast-forward. CP7, main,
PR24/25, hosted UAT, legacy, production, merge and deployment are outside this
task. production_go:false. No business source or admitted SQL is changed.

Business candidate: 25fa4736329e5148dfdb3572bc169952cba23251.
Tree: a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d.
Incoming harness: 2735703114ab52d605aa0d6cd2aa530b074fb5e9.
Its parent d20e22a6f47b0b3259a76c2f3d657c7e89aa165e directly follows the
business candidate. Six harness/router files differ; product code is identical.

## Additional evidence planned, not results

- Rerun 142 unchanged combined business cases on AI-R2, explicitly a reused
  oracle rather than independently invented expectations.
- Sixteen independent staged supplier-invoice flows after raw receipt,
  cutting, pickup, paid work, partial Laundry/QC/FG and sale. Two quantity
  partitions, four session zones, open/closed receipt day. Check physical
  custody, WIP/FG/COGS, GRNI/AP, reports, retry, queue and exact residue.
- Recheck 23 independent native cases and 12 two-session schedules.
- Run the real existing Auth/JWT/HTTP lifecycle and role matrix on an AI
  physical clone exposing public only, without temporary erp schema USAGE.
  The old script's AFTER_V2620AB label is historical; the new workflow verifies
  all 690 AI runtime objects separately. Do not use that label as runtime identity.
- Restore AI to independently captured AH: 533 functions, 223 tables, exact
  data/owner/ACL/migration boundary; remove users, clones and containers.

Local Docker/Postgres/Supabase tools are absent. Execution uses the existing
authorized GitHub disposable-runner pattern. No account/business data is used.

## Relationship map

| Flow | Authoritative dependencies | Final proof obligation |
| --- | --- | --- |
| Purchase → receipt → invoice → AP | material purchase RPCs, stock movements, GRNI, final AP, revaluation events | Staged invoices must consume the same receipt once; payments/returns reconcile cents. |
| Roll → cutting → pickup → work | cutting group/yield, distribution batch, committed work snapshots, posted completion | Same physical ten pieces; work identity and rates cannot drift; payroll eligibility differs from cash. |
| Laundry → QC → GOOD/BS → FG | seven-action facade, batch-size receipt, failed attempts, QC allocations, FG lots | No double output; downstream reversal blockers; real-role HTTP needed. |
| FG → sales draft → post → AR → return | reservation facts, post_sale_v2, source allocation, linked refund | Availability reduces once; draft dimension changes rebuild atomically; native is not UI proof. |
| Cost correction → WIP/FG/COGS → report | cost_recalc_queue, current HPP, GL state/events, owner snapshot checks | Corrected totals propagate; past accounting-day figures stay traceable; READY must agree. |

## Application limits

The original runtime accepts only its allowlisted hosted UAT URL. Localhost
fails the target guard, while this task prohibits hosted writes. The existing
Playwright suite intercepts backend responses: contract evidence, not original
application-to-real-service proof. No URL spoofing, guard relaxation, new
runtime mode or fake transaction response is introduced here.

Laundry/QC use public facades. The original CP6 handoff explicitly blocks the
legacy Nota FG browser writer. Sales/Finance still use local state. No explicit
owner contract establishing a blanket CP7 deferral for those gaps was found.
CSV transport and complete original-UI role coverage remain BELUM TERUJI.

Historical 460 means 23 targets F..AB × 5 operations × 4 maintenance schedules,
not 460 business scenarios. The final gate does not claim to rerun that matrix.
Reproducing historic runtimes cannot repair an untested final application path.

## Resume safely

Read docs/evidence/cp6-final-audit-reconciliation.json and the latest CP6 Final
Boundary Audit run. Check the live branch before any write. Preserve partial
case JSONs; scheduled/skipped cases remain untested. Harness SHA comes from the
run and is separate from AI-R2 above. Current verdict: INCOMPLETE, not lock approval.
