# Astra r5 — audit plan frozen before execution

Candidate 17fa25075ba77f0853c3c16f504288ace03eec35; tree 65f778479093d869a3354c0b9f19b4d9a541d98a.
Audit branch audit/astra-cp1-7-r5-17fa2507-20261019. Writer observed 2766a9092f51f240267b9cbe1201d49a836fb490 (docs-only since candidate).
Basis r4 663f6faefcbb9c70f0f99bbc7e78164e03521329, prior Astra report lock 40238e36.
Rules: AUDIT_PANDUAN_PRO_MAX.md SHA256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639; decisions through D17-2.

## Execution order and scope
1. Independently execute unchanged candidate CP17 package, all 345 predeclared cases: 165 Native,39 race,27 HTTP,57 browser,57 Enteng-build browser. Exact manifest retained in CP17_PREDECLARED.json. Oracle origin WRITER / inherited r4 auditor cases, not new independent oracle.
2. Independently execute P19 scale (5), transport (11), report v2 (20). Pin exact candidate; reconcile ID sets and multiplicity using original manifests and raw output.
3. Freeze and execute Astra's own new cases for the changed roots, covering FG_REPAIR healthy book/wrong contractor/missing source/reversed; reader equality on nonempty/empty inputs, mapping changes/core guard, repeated/set calls, exact install/restore and drift refusal; retain positive and negative outcomes and exact role.
4. Retain applicable r4 proofs as historical, explicitly not newly rerun. Inspect changed scripts and impacted source families; distinguish code invariance from runtime.
5. Report remaining latency and production limitations, not an Enteng installation or production approval.

## Evidence and environment
Workflow source remains on audit branch and checks out frozen candidate independently, never copies product files from auditor branch.
No changes to main/writer/hosted/deployment. Synthetic disposable Supabase PG17.6.1.165, CLI2.116.0, Python3.12, psycopg3.2.10, Node22, locked npm dependencies.
CI starts via GitHub API commit/ref update to the audit workflow push trigger (same audit workflow convention as prior locked Astra r4). No commit on writer.
One first attempt; max one rerun only before any case. New tool qualification preserves prior failure and explanation.
Each claim gets origin; PASS requires per-case result + exact IDs + cleanup, not job colour.
No same-round peer reports/branches/runs/artifacts/comments read before own report lock. Read only prior locked r4 and writer handoff.
Production_go=false; feature_complete=false; overall audit_complete=false pending final gates.
