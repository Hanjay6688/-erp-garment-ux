# Credit correction D1 candidate

Owner decisions D17-19A/B: extra return value becomes credit for the same customer; insufficient free credit requires named undo first; credit applications should follow a replacement invoice atomically. This candidate implements only the first practical D vertical. D and E remain open. It is outside the default installer and has no production or independent acceptance.

Admitted class: increased refund value on an already registered credit return, identical physical instant and every quantity/allocation/location/grade, unchanged static non-PO/non-opening HPP, original economic/book pair still lawful, no incoming credit history. The original return, family ordinal, cohort, consumers, original cash, and immutable I remain; private copies of the current Native inverse/poster perform the actual inverse and replacement. A new RETURN_CORRECTION member and positive signed ADJUSTMENT parts are added atomically. Extra value after an original REFUND stays credit. There is no second cash refund and no automatic new AR.

Every unsupported decrease, physical/date/quantity change, PO/opening/recost/conversion class, or incoming credit correction remains refused. Q2 exposes real active APPLY/REFUND identities, nominal and named undo route. Legitimately reversed consumers stay in signed history and are absent from the active list. If an earlier joint cutoff is still unsafe after a later undo, the preview identifies the historical capacity adapter requirement; it does not ask to undo an already reversed event again. Q3/E has no admitted writer yet; the retained refusal stays.

## Root-only qualification interface

- Parent: `cp7_vendor_receivable.composition`, verified on the actual complete catalog before DDL. Root combines SKU/AI separately.
- Install: `cp7_credit_correction_de.composition.install(cur)` or `install_delta(cur, actual_vendor_state)`.
- Verify: `verify(cur, state)`, exact 22 catalog groups, source and parent bindings, private RLS/ACL, declared 7 existing definitions and 5 Native/private copies.
- Preuse undo: `rollback_delta_preuse` / `rollback_preuse`. Any business-data/sequence delta refuses before inverse DDL; after use requires full backup restore.
- Cases: `cp7_credit_correction_de.cases.cases(cur, today)`. The existing Native consumer fixture import paths must be present. Importing performs no SQL.
- No existing SQL, Native money/HPP body, pure kernel, ordinal wrapper, literal oracle or date fixture was edited. No hosted/project/remote/workflow action was performed by this helper.

The 13 required actual case IDs are in `cases.IDS`: Q1 extra credit, active APPLY, original REFUND, multi-family ordinal, same UUID/replay, changed review, revoked access, Q2 APPLY/REFUND named undo, original book-floor refusal, failure inside actual Native journal insert with complete restore, two correction ordinals/history, legitimately reversed consumer, and retained E refusal. Full restored backup, financial truth reports, two-session races and real Auth/browser are separate required evidence before closing D/E. The new Native cases have not been run in this helper environment.

## Local checks and honest limits

- 18 DOM tests pass, including paid-source nominal/token, real-field closed parser, named APPLY/REFUND routes, late quote retirement, existing source/ticket/access/history behavior. Supabase/source navigation are declared UI stand-ins.
- TypeScript app check passes.
- Eight supplied-vector checks execute the unchanged SQL kernel/wrapper in PGlite 0.3.14. They prove arithmetic only. `BASE_OVERFLOW_NONZERO` stays exact.
- Ten focused D quote/reconciliation SQL checks execute with the retained collectors/kernel. They include amount-bound quote, APPLY shortfall/undo identity, stale amount token, exact plan/support sets, extra-plan refusal and a historical capacity refusal after a legitimate later undo. Authority, Native source/profile/account/HPP and consumer provenance remain declared stand-ins; no journal is posted and deferred completion is rolled back.
- All new SQL declarations/bodies compile in PGlite against declared structural Native/private column types and helper signatures. This is not Native accounting, real Auth, RLS or money-flow proof.
- Static Native dump/source-format anchor check passes, including all duplicated predecessor captures refused. It is not an installed source capture. The actual installer derives only after verifying its real current parent.
- ESLint is unavailable in the retained node_modules; the repo has no lint script. No dependency or lockfile was changed.

First failures are retained in `evidence/FIRST_FAILURES.json` (commit `3082bdba`). A later structural compile found the real restatement column is `original_return_id`; the new adapter was corrected. No old oracle was changed.
