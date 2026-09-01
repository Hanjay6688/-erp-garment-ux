# ERP Garment — Checkpoint 3 Source Candidate V2.1

**This record supersedes `checkpoint_3_source_candidate_v2.md` for audit execution.**  
The older record remains provenance and is not rewritten.

## Identity and safety

- Writer: **Chat Sol Pro**
- Reviewer: **Work Sol Max**
- Clean base: `main` `bf3ce8e2821f120d8abd8788daf07f6da7c15459`
- Candidate branch: `cp3/hpp-attendance-sewing-terminal-candidate-v2-20260901`
- Superseding workflow: `.github/workflows/cp3-source-candidate-v2.yml`
- Expected artifact: `cp3-source-candidate-v2-proof`
- ERP Enteng UAT: **not mutated**
- ERP-Garment legacy: **not mutated / read-only**
- Main, Auth, Storage, cron, Cloudflare: **not mutated**

## V2.1 hardening delta

V2.1 adds:

`supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_candidate_hardening.sql`

The delta closes source-level bypasses not sufficiently defended by RPC-only validation:

1. The append-only sewing trigger independently rechecks explicit normal-Mandor policy coverage.
2. The trigger rechecks the authoritative work-completion sewing source on every RECORD/CORRECTION insert.
3. A reversal must exactly negate source PO, Mandor, completion line, date/time, policy, and quantity.
4. A correction must retain source PO, Mandor, and completion-line lineage.
5. Pool validation now rejects a sewing contractor that has no payroll source in that pool.
6. Pool validation rejects empty/invalid policy manifests.
7. Destination count must reconcile with snapshotted sewing destinations.
8. Validation remains one bounded set-based query; no deferred row-by-row validator is added.
9. No public facade, authenticated grant, hook, `post_journal`, or route activation is added.

## Authoritative candidate file set

Database candidate:

- `20260901023000_erp_v2_6_14a_attendance_hpp_policy_and_sewing_terminal.sql`
- `20260901023100_erp_v2_6_14b_attendance_hpp_pool_intents.sql`
- `20260901023200_erp_v2_6_14c_attendance_hpp_candidate_hardening.sql`

Acceptance/tooling:

- `supabase/tests/attendance_hpp_cp3_source_contract.sql`
- `supabase/tests/attendance_hpp_cp3_concurrency.py`
- `supabase/tests/attendance_hpp_cp3_concurrency.fixture.example.json`
- `scripts/cp3_render_reviewed_rollback.py`
- `scripts/test_cp3_render_reviewed_rollback.py`
- `scripts/cp3_source_candidate_checks.py`
- `scripts/cp3_source_candidate_checks_v2.py`
- `.github/workflows/cp3-source-candidate-v2.yml`

## Truth boundary after V2.1

```text
SOURCE SHAPE          = AUTOMATED GATE REQUIRED
TOP-LEVEL SQL PARSE   = AUTOMATED GATE REQUIRED
DATABASE COMPILE      = NOT EXECUTED
SQL CONTRACT RUNTIME  = NOT EXECUTED
REAL CONCURRENCY      = HARNESS PRESENT / NOT EXECUTED
UAT APPLIED           = NO
GENERAL LEDGER POSTED = NO
ROUTE ENABLED         = NO
LIVE DEPLOYED         = NO
BACKEND-CONNECTED     = NO
PRODUCTION GO         = NO
```

A green V2.1 workflow proves only exact source identity, source-shape assertions, Python tests, PostgreSQL top-level parsing, exact-byte rollback rendering, and non-secret/private surface. It does **not** prove PL/pgSQL semantic compile against the live schema, behavior, concurrency, UAT, or residue.

## Remaining independent dispositions

The following must remain open for Work Sol Max:

- Claim blocker: typed claim isolation exists, but integration with the existing hosted claim route still needs independent source/runtime disposition.
- Journal blocker: original debit-line intents are modeled, but actual GL post/reversal remains intentionally absent until source and local acceptance pass.
- Validator performance: source is bounded and set-based, but cardinality benchmark is not executed.
- Concurrency: true two-session harness exists but is not executed.
- SQL behavior: rollback-only contract exists but is not executed against a disposable restored schema.

## Next gate

Work Sol Max reviews the exact draft PR head plus `cp3-source-candidate-v2-proof` and returns one of:

- `GO FOR CP3 LOCAL/UAT ACCEPTANCE`
- `NO-GO FOR CP3 LOCAL/UAT ACCEPTANCE`
- `BLOCKED`

No UAT SQL may be applied before that independent delta verdict. Persistent route/GL activation remains Checkpoint 4.
