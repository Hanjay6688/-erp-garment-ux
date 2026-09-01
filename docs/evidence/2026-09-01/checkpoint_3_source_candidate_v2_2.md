# ERP Garment — Checkpoint 3 Source Candidate V2.2

**This record supersedes V2.1 for independent audit. Historical records remain provenance.**

## Identity and mutation boundary

- Writer: **Chat Sol Pro**
- Independent reviewer: **Work Sol Max**
- Exact clean base: `main` `bf3ce8e2821f120d8abd8788daf07f6da7c15459`
- Candidate branch: `cp3/hpp-attendance-sewing-terminal-candidate-v2-20260901`
- Final authoritative source gate: `.github/workflows/cp3-final-source-gate-v2.yml`
- ERP Enteng UAT: **NOT MUTATED**
- ERP-Garment legacy: **NOT MUTATED / READ-ONLY**
- Main/Auth/Storage/cron/Cloudflare: **NOT MUTATED**

## V2.2 correction after adversarial self-review

V2.1 correctly replaced QC GOOD with an immutable event ledger, but its record/correction RPC still accepted operator-supplied quantity/date/time. That was not authoritative enough.

V2.2 adds:

`supabase/migrations/20260901023300_erp_v2_6_14d_authoritative_sewing_source.sql`

The hardening:

1. Requires an existing `work_completion_line` with an existing `work_completion` header.
2. Requires a terminal header/line status: `POSTED`, `COMPLETED`, `FINAL`, or `CLOSED`.
3. Rejects reversed, cancelled, or void completion state.
4. Requires an explicit sewing/Jahit work component and rejects QC, FG, Laundry, Rework, Rewash, Susulan, and Return sources.
5. Derives production order, Mandor, quantity, business effective date, and timestamp from the terminal completion fact.
6. Creates a deterministic source payload hash and requires an exact expected hash before and after the advisory lock.
7. Removes PO, Mandor, quantity, effective date, and timestamp from the record payload contract.
8. Disables the old correction RPC that accepted arbitrary replacement quantity/date/time.
9. Adds correction V2, which requires a replacement terminal work-completion line plus its exact reviewed source hash.
10. Keeps exact reversal negation and production-order/Mandor correction lineage.

## Authoritative database candidate

Apply order in a disposable environment only after Max source GO:

1. `20260901023000_erp_v2_6_14a_attendance_hpp_policy_and_sewing_terminal.sql`
2. `20260901023100_erp_v2_6_14b_attendance_hpp_pool_intents.sql`
3. `20260901023200_erp_v2_6_14c_attendance_hpp_candidate_hardening.sql`
4. `20260901023300_erp_v2_6_14d_authoritative_sewing_source.sql`

No file above is installed in UAT. No historical migration was edited or replayed.

## Final source truth boundary

```text
SOURCE SHAPE          = FINAL WORKFLOW MUST PASS
TOP-LEVEL SQL PARSE   = FINAL WORKFLOW MUST PASS
ROLLBACK RENDERER     = FINAL WORKFLOW MUST PASS
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

The durable final workflow writes exactly one marker:

- `checkpoint_3_final_source_gate_v2_PASS.json`, or
- `checkpoint_3_final_source_gate_v2_FAIL.json`.

A PASS marker proves only source identity, explicit full-file SHA-256 manifest, Python unit tests, PostgreSQL top-level parsing, exact-byte rollback rendering, and source/private-surface checks. It is not runtime/UAT/concurrency evidence.

## Known remaining gates

Even after source PASS:

- Work Sol Max must independently audit the exact source commit and full manifest.
- Existing hosted Laundry claim integration remains `PARTIAL` until its actual route uses the typed discriminator and runtime negative tests pass.
- General-ledger post/reversal is deliberately absent; CP3 models reviewed intents only.
- PL/pgSQL semantic compile, rollback contract, data behavior, residue, and real concurrency must run against disposable/local restored schema after Max GO.
- UAT rollback-only fixture follows local acceptance.
- Persistent route/GL activation remains Checkpoint 4.

## Required next verdict

Work Sol Max returns:

```text
GO FOR CP3 LOCAL/UAT ACCEPTANCE
NO-GO FOR CP3 LOCAL/UAT ACCEPTANCE
BLOCKED
```

No UAT mutation is allowed before that verdict on exact bytes.
