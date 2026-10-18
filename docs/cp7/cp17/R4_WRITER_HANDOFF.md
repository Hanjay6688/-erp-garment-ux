# r4 writer handoff (living checkpoint)

Same mechanism as `R3_WRITER_HANDOFF.md` (owner 17 Okt: commit one piece at a time; when close to the limit, the nearest
checkpoint is forwarded to writer Sol). Updated with every r4 commit on `claude/r4-fixes-20261018`; the last commit that
touches this file is the checkpoint to continue from.

## Rules that stay in force

- Owner reports: plain everyday Indonesian, first sentence says what is done and what is not (CLAUDE.md).
- Follow `docs/ERP_BEST_PRACTICES.md` and its checklist; new general audit lessons go there with their finding IDs.
- Never mutate: main, Cloudflare deployment, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
  (`vlxdhpkjeevubjxexnfo`, read-only), production. `production_go:false`; D13-9a (the writer does not touch hosted or Drive).
- Do not loosen old oracles/guards to get green; keep failed logs and wrong fixtures. Do not reopen approved decisions.
- No production dump in the repo, public artifacts or logs. No paid services. No messages to other people. No PR.

## Mandate (r4)

Owner 18 Okt, after Fable and Astra locked their r3 reports and before Sol's: "mulai aja ntar nyusul, tar tinggal lu cek
temuannya valid apa engga". So: fix the r3 findings now; when Sol's report arrives, check each Sol finding for validity
(reproduce or refute with evidence) and fold the valid ones into r4; then qualify on one commit and prepare the retest
package for Fable/Astra/Sol.

Basis: candidate r3 `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`; r4 branches from `claude/new-session-deapao` at
`64339905` (r3 plus docs only).

## r3 audit results (locked reports)

| Auditor | Branch / lock | Verdict |
|---|---|---|
| Fable | `audit/fable-cp1-7-r3-b53b5acd-20261017`, lock `2033fdfc` (`audit/fable_cp17_r3/`) | D16-1 oracles 1-5 closed, FABLE-016 and FABLE-018 closed, no new finding; FABLE-012 still deferred (D14-9) |
| Astra | `audit/astra-cp1-7-r3-b53b5acd-20261018`, lock `741ffdf3` (`audit/astra_cp17_r3/`) | HOLD: 2 S1, 2 S2 (below) |
| Sol | `audit/sol-cp1-7-r3-b53b5acd-20261017` | no report yet (branch at the candidate, no commit) |

| Finding | Severity | Validity check by the writer | r4 item |
|---|---|---|---|
| ASTRA-R3-01 public CP4 pool wrappers skip the CP7 closed-period and manage-permission refusal | S1 | Valid by source: `supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql:470-544` only calls `erp.require_owner_admin()` then the Native writer, granted to `authenticated`; the CP7 app does not call them (`src/` uses `erp_cp7_save_hpp_pool_v1`). Family sweep of other public writers running | R4-01 |
| ASTRA-R2-01 remainder: reopen still blocked after a positive FG adjustment and its inverse | S1 | Valid by source: `po-reopen.sql` counted every negative movement as use minus its own reversals, so the -2 REVERSAL of a +2 inflow was a use. Fixed (committed), CP17 cases added | R4-02 |
| ASTRA-R3-02 Audit Trail paging skips a lower id committed after the first page, no "newer" flag | S2 | (pending) | R4-03 |
| ASTRA-R3-03 connected WIP numbers pale on white cards | S2 | (pending) | R4-04 |

## Not done yet (in this order)

1. R4-01..R4-04: validate each finding (source + local reproduction where possible), fix, CP17 cases with the auditor's
   own oracle and numbers, declaration, local checks, one commit each.
2. Sol's report: validity check per finding, fold valid ones in.
3. Qualify one commit, receipt, package `docs/cp7/audit-candidate/cp1-7-r4-<date>/`, boxes, owner report.

## How to check locally

As in `R3_WRITER_HANDOFF.md` ("How to check locally").

## Checkpoint log

| Commit subject | State after it |
|---|---|
| fix(r4): PO reopen ignores the inverse of an inflow (R4-02) | `po-reopen.sql` skips a negative movement that reverses a positive one; `scripts/cp7_r4_cases.py` (Astra's case as written + 2 controls + 1 race) wired into `cp7_cp17_fix_cases.py`; declaration 325 (156/35/24/55/55); workflow paths include `scripts/cp7_r4_*`. Local: compile + clash check of po-reopen.sql, py_compile, declaration equal. Not yet run in CI |
