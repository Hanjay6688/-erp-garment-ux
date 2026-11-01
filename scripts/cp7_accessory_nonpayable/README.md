# D17-20: GOOD-date nonpayable accessory basis

The owner selected `Tanggal GOOD (Recommended)` on 1 November 2026. The exact
question, answer and limits are published as D17-20 at Root commit
`1b4d7033d9cfb78dbb0eff3637a806d67e237daf`. This replaces the earlier unanswered
date question. Configured FREE components are not reimbursed; their inventory
HPP remains recognized. Pickup-to-PO/FG matching is not required.

This first source component implements the dated policy foundation only:

- An append-only category timeline refers to exact existing ERP_DEC02 event
  identities and values. The owner supplies the effective date explicitly;
  event `set_at` is not treated as an economic effective date.
- Physical GOOD time becomes a business date in Asia/Jakarta. The resolver
  uses the inclusive dated contractor Special policy and the dated category
  policy, returning their identities for the future immutable cost basis.
- Unknown, pending, overlapping or unregistered policies refuse. An explicit
  empty category list is known zero. Ordinary contractors retain reimbursement.
- Registration has a stale timeline token, request identity, exact replay and
  changed-intent refusal. Locks cover the actual BC source row and private
  timeline; authority is checked again after waits.
- No browser role receives schema, table or function access. No real category
  values, rates or historical effective dates are seeded.

`policy.sql` has no installer or public RPC yet. Do not execute it on the live
candidate, hosted project or production. The isolated PostgreSQL controls use
small labelled model tables and guard stubs, not an ERP installation.

Still required before this feature can be accepted:

1. Freeze the resolved basis with each new Native GOOD cost snapshot; preserve
   the original BOM reimbursement rate while setting only eligible components
   to nonpayable. Guard later dated policy changes against active posted uses.
2. Derive the initial accrual narrowly from the exact predecessor. Preserve the
   H>0/R0 refusal unless every relevant component has the lawful frozen basis;
   preserve explicit contractor identity and accounting conservation.
3. Handle recost including zero/zero and zero-cent starts, and linked QC inverse.
4. Install on the actually accepted final parent, add the ordinary settings/UI
   route, and prove actual Native, permissions, two-tab and browser behavior.

Local command (the separately pinned test dependency is not a repo dependency):

```sh
PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js \
  node scripts/cp7_accessory_nonpayable/test_policy.mjs /absolute/result.json
```

No actual Native/Auth/browser acceptance is claimed by these model checks.
`production_go=false`, `independent_acceptance=false`.
