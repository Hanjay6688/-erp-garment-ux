# ERP Garment — Checkpoint 3 Source Candidate V2

**Mode:** OWNER-GRADE COMPETITION MODE  
**Writer:** Chat Sol Pro  
**Independent reviewer:** Work Sol Max  
**Base:** clean `main` `bf3ce8e2821f120d8abd8788daf07f6da7c15459`  
**Candidate branch:** `cp3/hpp-attendance-sewing-terminal-candidate-v2-20260901`  
**ERP Enteng UAT:** **NOT MUTATED**  
**ERP-Garment legacy:** **NOT MUTATED / READ-ONLY**  
**Cloudflare/main/Auth/Storage/cron:** **NOT MUTATED**

## Verdict boundary

This package is a **source candidate for independent delta audit**. It is not a completed Checkpoint 3 and is not permission to apply SQL.

| Layer | Status |
|---|---|
| SOURCE | Candidate reconstructed; automated source gate required |
| SQL top-level parse | Automated source gate required |
| Database compile/runtime | NOT EXECUTED |
| Real concurrency | Harness implemented; NOT EXECUTED |
| UAT | NOT APPLIED |
| LIVE | Unchanged demo simulation |
| BACKEND-CONNECTED | NO |
| GL posted | NO — intentionally absent |
| PRODUCTION GO | NO |

The one-time workflow artifact records the exact candidate commit, tree, file SHA-256 values, renderer metadata, and parser/source checks. A green source gate must not be relabeled as database runtime or UAT PASS.

## Superseded branch warning

The earlier branch:

`cp3/hpp-attendance-sewing-terminal-reconstruction-20260901`

is **SUPERSEDED**. It contained a placeholder and then an unreviewed monolithic reconstruction attempt. It must not be reviewed as the candidate, merged, applied, or deployed. A warning file is persisted on that branch.

Only the V2 branch in this document is eligible for Max delta review.

## Binding business contract

- Numerator: posted attendance payroll amount for normal Mandor in the exact pool period.
- Eligible Mandor: explicit `MANDOR` + `attendance_required=true` + explicit `is_special=false`.
- `Special` is independent from attendance requirement and is never inferred from `Afui` or any name.
- Denominator: immutable authoritative `SELESAI_DIJAHIT` event in the same period.
- QC GOOD, FG, Laundry, Rework GOOD, Rewash, Susulan GOOD, and other downstream destinations are forbidden denominator sources.
- Rework GOOD cannot enter the denominator a second time.
- Positive numerator with zero sewing output remains `UNASSIGNED`; no silent allocation, divide-by-zero, or QC fallback.

## Candidate files

### Database source

1. `supabase/migrations/20260901023000_erp_v2_6_14a_attendance_hpp_policy_and_sewing_terminal.sql`
   - strict JSON contract;
   - typed operation discriminator;
   - effective-dated explicit contractor HPP policy;
   - immutable `SELESAI_DIJAHIT` event ledger;
   - owning record/correct/reverse RPCs;
   - private, service-role-only surface;
   - no public facade or hook.

2. `supabase/migrations/20260901023100_erp_v2_6_14b_attendance_hpp_pool_intents.sql`
   - exact payroll and original journal-line lineage;
   - numerator tied to payroll attendance snapshots;
   - denominator tied only to active sewing events;
   - deterministic largest-remainder cent allocation per original debit line;
   - one terminal credit intent per original debit line;
   - set-based bounded pool validation;
   - ACTIVE/UNASSIGNED cancellation without manual pre-reversal;
   - READY/REVERSED intent lifecycle;
   - no `post_journal()` call and no enabled route.

### Acceptance and tooling

3. `supabase/tests/attendance_hpp_cp3_source_contract.sql`
   - rollback-only SQL contract test;
   - missing/null/type/extra/nested JSON corpus;
   - mixed claim operation rejection;
   - timezone deterministic epoch/hash assertion;
   - private ACL/no-public-facade assertion;
   - stale QC/FG denominator token assertion;
   - source-line terminal-credit uniqueness;
   - no deferred validator;
   - no GL posting.

4. `scripts/cp3_render_reviewed_rollback.py`
   - exact input SHA-256 guard;
   - strict UTF-8;
   - lexical handling for comments, quoted text, nested block comments, and dollar bodies;
   - exactly one first-statement `BEGIN;` and one terminal `COMMIT;`;
   - no existing top-level rollback;
   - exact terminal replacement `COMMIT` → `ROLLBACK`;
   - output digest and metadata.

5. `scripts/test_cp3_render_reviewed_rollback.py`
   - adversarial renderer corpus: wrong digest, duplicate/missing commit, trailing SQL, comments/strings/dollar bodies, malformed lexical states, existing rollback, transaction shape, BOM, and non-ASCII offsets.

6. `supabase/tests/attendance_hpp_cp3_concurrency.py`
   - actual two-connection/thread barrier harness;
   - same key/same payload;
   - same key/different payload;
   - cancel-versus-finalize race;
   - stale version;
   - local-host-only and disposable-database guards.

7. `supabase/tests/attendance_hpp_cp3_concurrency.fixture.example.json`
   - explicit fixture input contract; no fabricated IDs or credentials.

8. `scripts/cp3_source_candidate_checks.py`
   - fail-closed source/provenance checks;
   - emits SHA-256 manifest;
   - truth boundary stays source-only.

9. `.github/workflows/cp3-source-candidate.yml`
   - source identity;
   - Python compile/unit tests;
   - fail-closed source checks;
   - PostgreSQL top-level parser;
   - exact-byte rollback rendering;
   - secret/public-surface scan;
   - non-secret evidence artifact only;
   - no deployment or database call.

## Max defect crosswalk

| Max finding | Candidate disposition | Claim level |
|---|---|---|
| CP3-P0-01 QC GOOD denominator | Replaced by explicit immutable `SELESAI_DIJAHIT` ledger and pool query | SOURCE FIX CANDIDATE |
| CP3-P1-01 Special policy missing | Effective-dated `is_special` independent from attendance | SOURCE FIX CANDIDATE |
| CP3-P1-02 authoritative bytes missing | Clean branch from exact main, committed files, automated hashes | PROVENANCE CANDIDATE |
| CP3-P1-03 terminal credit collapsed | One credit intent per original journal-line source | SOURCE FIX CANDIDATE |
| CP3-P1-04 no active cancel | Atomic ACTIVE/UNASSIGNED cancel RPC | SOURCE FIX CANDIDATE |
| CP3-P1-05 fixture bypassed owning flow | Owning policy and sewing record/correct/reverse RPCs | SOURCE FIX CANDIDATE |
| CP3-P1-06 renderer missing | Digest/count/terminal-transaction renderer + adversarial tests | SOURCE FIX CANDIDATE |
| CP3-P1-07 JSON assertions incomplete | Required-key, null/type, extra and nested checks | SOURCE FIX CANDIDATE |
| CP3-P1-08 claim isolation | Closed typed manifest helper rejects transfer/carry/movement | PARTIAL — existing claim route integration still requires Max review/runtime test |
| CP3-P1-09 validator complexity unknown | Explicit set-based one-pool validator; no deferred validator | SOURCE FIX CANDIDATE; benchmark pending |
| CP3-P1-10 concurrency untested | Real two-session harness implemented | NOT EXECUTED |

## Deliberate containment

The candidate intentionally does **not**:

- apply any migration to UAT;
- create a browser/public facade;
- grant `authenticated` access;
- create a hook, queue, scheduler, or cron;
- connect the frontend;
- post general-ledger entries;
- deploy Cloudflare;
- modify existing immutable migrations;
- touch ERP-Garment legacy;
- claim SQL compile, behavior, concurrency, or residue PASS.

The general-ledger posting adapter is deferred because Max must first validate source identity, original debit-line cardinality, denominator semantics, cancel lifecycle, and acceptance design. `READY` means a reviewed intent only.

## Required independent delta review before UAT

Work Sol Max must review the exact candidate commit and automated SHA-256 artifact, then classify every CP3 P0/P1 as:

- SOURCE CLOSED;
- PARTIAL;
- FAIL;
- BLOCKED;
- RUNTIME TEST REQUIRED.

No persistent UAT mutation is allowed until Max gives **GO FOR CP3 LOCAL/UAT ACCEPTANCE** on exact bytes. After that gate, the next work is disposable/local SQL compile + rollback contract + real concurrency, then UAT rollback-only fixture. Persistent route activation remains Checkpoint 4.

## Takeover state

```text
SOURCE              = CANDIDATE UNDER AUDIT
UAT                 = UNCHANGED / NOT APPLIED
LIVE                = UNCHANGED DEMO
BACKEND-CONNECTED   = NO
AUTH E2E            = NOT EXECUTED
PRODUCTION GO       = NO
ERP-GARMENT LEGACY  = NOT MUTATED
TAKEOVER_READY      = YES FOR READ-ONLY MAX DELTA REVIEW
```
