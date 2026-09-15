# Owner rule: finish the whole affected family, then run the acceptance gate

Owner instruction, 2026-09-15: when one root cause can affect multiple ERP
features, enumerate and inspect every affected path and consolidate the fixes.
Do not spend hours rerunning the historical matrix after each isolated P2.

Keep evidence-first, one active writer, idempotency, fail-closed behavior,
immutable posted history, and the money/report/stock/HPP priorities intact.

For each wave:

1. Pin the candidate, tree, parent, branch, and incoming artifact hashes.
2. Map the root cause to producers, consumers, triggers, reports, defaults,
   imports, public facades, linked corrections, and rollback obligations.
3. Record each path as affected, excluded with a source/type reason, or still
   unproven. A token search or an old CLOSED label is insufficient.
4. Design independent expected outcomes and negative controls. Collect every
   case even after a qualified failure; distinguish fixture errors from bugs.
5. Consolidate product fixes and their tests, detectors, source pins, docs,
   installation and rollback wiring. Keep admitted SQL immutable.
6. Run the final native gate once the changes stabilize. Rerun a historical
   matrix only when source/runtime drift, an invalid checksum, changed
   concurrency behavior, or a counterexample invalidates that evidence.
7. Report REUSED_EVIDENCE, RECONCILED, RERUN_REQUIRED, or DRIFT per evidence
   group. Reusing source-bound evidence never grants independent acceptance.

The writer hands off to the other chatbox for an independent review of the
repair plus residual attacks. A qualified material defect transfers the writer
role to that auditor. Do not self-certify the successor's independent PASS.

Audit-only commits may reuse AC Native200 only while the entire original
business/runtime source stays byte-identical to AC. The full workflow's routing
guard also checks that its original validation body is unchanged. Any product,
legacy harness, unknown-path, or original validation-body mismatch takes the full native path.
The focused independent runner checks out the original AC commit separately;
it reports the audit harness commit and candidate commit independently.

Only competition/cp6-j-closure-20260911 is writable, fast-forward only. Main,
PR24/25, hosted UAT/legacy/production, deployment, and CP7 are outside this wave.
production_go remains false.
