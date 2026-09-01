# CP3 R3 Patch Boundary

**Status:** SOURCE-ONLY PATCH CANDIDATE UNDER FULL-SCHEMA VALIDATION
**Do not merge, apply to UAT, grant, hook, connect, or deploy.**

- Parent frozen review head: `d3755e709e7bc1d959a18a359173ff2cdb9bb5be`
- Parent validated source commit: `aa1bf9d9938d543b4add1c944e7f84d4370038ae`
- Patch branch: `cp3/hpp-attendance-sewing-terminal-r3-20260901`
- Writer: Chat Sol Pro
- Reviewer after proof: Work Sol Max
- ERP Enteng UAT mutation: none
- ERP-Garment legacy mutation: none
- Auth/Cloudflare/`main` mutation: none

R3 targets the independent-review findings and one fail-closed lifecycle defect found during writer self-review:

1. attendance cost recognition at payroll `APPROVED`;
2. payment as settlement-only for already-recognized payroll cost;
3. exact ERP Enteng audit-action vocabulary;
4. fixed `Asia/Jakarta` business dates and canonical `YYYY-MM-DD` input/output;
5. strict nested JSON types;
6. shared source/pool race locking;
7. source-first and activation-first real two-connection races;
8. stale DRAFT pool disposal through `VOIDED`, so a stale preview cannot block a period forever;
9. full restored-schema behavior, accounting, rollback, ACL, benchmark, and residue proof.

The patch is forward-only migration `v2.6.14c` after reviewed source candidates `v2.6.14a` and `v2.6.14b`. No previous migration is edited or replayed in UAT.

This marker is interim. It must be replaced by a frozen machine-readable manifest after the full-schema workflow is green and temporary workflows are retired.
