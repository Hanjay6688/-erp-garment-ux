# D17-20: GOOD-date nonpayable accessory basis

The owner selected `Tanggal GOOD (Recommended)` on 1 November 2026. The exact
question, answer and limits are published as D17-20 at Root commit
`1b4d7033d9cfb78dbb0eff3637a806d67e237daf`. This replaces the earlier unanswered
date question. Configured FREE components are not reimbursed; their inventory
HPP remains recognized. Pickup-to-PO/FG matching is not required.

This source component prepares the dated policy foundation and its counted
Native financial derivations, separately from the active qualification:

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

`basis.sql` freezes contractor, Special/category policy identities, original BOM
rate and the snapshot's fixed fields. It protects active GOOD from policy
backdating; lawful QC/rework inverse releases the active-use protection without
deleting the frozen history. `native_derivation.py` checks every original byte
before making four bounded Native changes: snapshot, initial accrual, recost,
and nonpayable rework inverse. The existing QC inverse remains unchanged.

The financial derivation preserves the positive-HPP/zero-reimbursement refusal
for unproven components. Company-funded components keep HPP in WIP against the
reimbursement variance, with no payable entitlement. Zero/sub-cent starts have
no manufactured zero journal. Their recost uses cumulative cents, retains
Native dates and revision UUIDs, and prevents a later duplicate initial accrual.

There is no installer or public RPC yet. Do not execute this source on the live
candidate, hosted project or production. The isolated PostgreSQL controls use
small labelled model tables and guard stubs, not an ERP installation.

Still required before this feature can be accepted:

1. Bind an installer and source/admission controls to the actually accepted
   final parent; preserve exact Native metadata and all22/data/sequence guards.
2. Add the ordinary owner settings/UI route for confirming effective dates and
   replay/recovery, and verify posted-use refusal messages in that route.
3. Prove the complete real inventory/HPP/sales and zero-payable flow, real
   permissions and two-tab waits, complete restoration and preuse inverse.
4. Retain the final source, advisor and restoration evidence with the exact
   accepted parent, candidate and run identities for integration review.

Local command (the separately pinned test dependency is not a repo dependency):

```sh
PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js \
  node scripts/cp7_accessory_nonpayable/test_policy.mjs /absolute/result.json
```

`LOCAL_POSTGRES_CONTROLS.json`: 44 dated-policy controls. `LOCAL_COST_CONTROLS.json`:
25 new isolated function/accounting controls, including the unchanged Native
counterexample, ordinary payable preservation, half-cent initial recognition,
cumulative recost, both inverses, and active-use release. The policy controls
were reused without rerunning. Local first failures and narrow repairs remain
in `LOCAL_COST_MODEL_FAILURES.json`; no CI ERP run was started for these models.

No actual Native/Auth/browser acceptance is claimed by these model checks.
`production_go=false`, `independent_acceptance=false`.
