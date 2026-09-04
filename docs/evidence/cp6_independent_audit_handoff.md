# CP6 v2.6.20 independent audit handoff

Audit this candidate independently from the business context and your own logic
first; only after that blind pass, use the explicit checklist below to reconcile
anything you may have missed. Do not accept this handoff, CI color, or the
writer's conclusions as authority.

This handoff freezes the CP6 candidate that connects authoritative Laundry
dispatch and return, paid failed-wash attempts, QC, and exact-size Final SKU/FG
to the same physical, WIP, stock, HPP, journal, payable/accrual, and reporting
facts. It is evidence for review. It does not authorize merge, production
deployment, a real-user invitation, or any mutation of the legacy ERP.
`production_go` is `false`.

## Exact identity

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#24`, open, draft, unmerged
- Branch: `cp6/laundry-qc-fg-authoritative-r1-20260904`
- Live base/main: `6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`
- Base tree: `6d90546ecd7e55e16a9e6062599ee09b2e9b505d`
- Runtime/code HEAD: `9509bee8525ff9ba8e422eae7c9665ed76c506c4`
- Runtime parent: `ae488ee2bd96706c3ec7f4b1b23f00977e0ba8e1`
- Runtime tree: `cb299396eac081a300a8062950089ba5dad8ba24`
- Evidence successor: resolve from PR immediately before review. Its first
  parent must be the runtime/code HEAD above and its diff must contain only
  `docs/evidence/cp6_v2620_uat_acceptance.json`,
  `docs/evidence/cp6_r1_source_hashes.json`, and this handoff.

Reject the handoff if HEAD, base, parent, tree, migration bytes, UAT identity,
or the evidence-only commit shape differs. A later runtime change invalidates
all recorded PASS results.

## Owner truth that controls the design

**Reliable Data adalah Dewa. Keuangan—including reports—stock, and HPP are
Raja.** A business action succeeds only if its physical custody, stock, cost,
HPP, journal, payable/accrual, report inputs, and immutable lineage tell the
same story in one transaction. Partial success, silent overwrite, selective
history deletion, double counting, and untraceable formula repair are blocking
failures.

Human product identity is ordered **Brand → SKU number → Model → Color →
Size**. The same numeric SKU may legitimately exist under different brands and
may then represent different models. Pattern is not a SKU attribute. A later
question such as “which Pattern did this SKU use last year?” must be derived
through immutable FG/QC/Laundry/cutting lineage.

## Delivered business boundary

| Boundary | Authoritative rule |
| --- | --- |
| Laundry dispatch | One posted contractor distribution source is conserved by exact cutting batch and size. The browser cannot invent readiness or quantity. |
| Laundry return | Good and Laundry-BS are bound to exact delivery batch/size capacity. Good is the only QC capacity; Laundry-BS is terminal and product-bound at physical receipt. |
| Paid failed wash | A real failed service may cost money without creating Good, BS, QC, or FG. `RETRY_AT_VENDOR` keeps custody at Laundry. `RETURN_UNPROCESSED` returns the exact whole physical quantity and appends Laundry → Sewing custody. |
| Retry and second charge | A later genuine wash is a new physical/service leg. Both real attempts stay in history and may each be charged; neither may duplicate stock or output. |
| QC | QC consumes only authoritative Laundry Good from its exact receipt batch/size source. Posted corrections are reversal-only. |
| Final SKU / FG | Good is classified to an exact brand-scoped product/size only at the terminal boundary. Server code owns FG stock, HPP, reimbursement, journal, and completion; browser formulas are ignored. |
| Late/replacement invoice | Physical receipt cost may begin as an estimate. Posting, reversing, or replacing the vendor invoice shares the canonical locks and atomically reconciles WIP, accrued liability, AP, FG HPP, and reports without new physical output. |
| Reversal | Delivery/receipt/QC reversal is blocked by active downstream use. An accepted reversal appends exactly one inverse WIP/stock/finance event linked to its origin; history is never updated away. |

All seven CP6 mutation actions use a closed server allowlist, UUID idempotency,
canonical payload hashing, expected row version, canonical source-row locks,
and a transaction-local internal execution context. Identical replay returns
the original result; the same key with different input fails closed. Competing
writers serialize, and the loser must leave no business, idempotency, or
execution-context residue.

## Connected UX contract

- Laundry and QC display Brand → SKU number → Model and exact batch/size
  lineage; they do not store or guess Pattern on SKU.
- Physical dispatch, receipt, and QC times begin blank. The operator confirms
  them explicitly and the payload is serialized in WIB (`Asia/Jakarta`,
  `+07:00`) independent of the device timezone.
- Backend readiness, row version, capacity, and reversal blockers control
  every mutation. Operator acknowledgement expires after authoritative
  refetch.
- The mutation envelope is persisted before send. A lost response reuses the
  exact UUID, payload, expected version, target identity, UAT project, and app
  user. It cannot be replaced with a new operation.
- Once the server confirms a create, the committed form is retired before
  refetch. If refetch fails, the page becomes stale and all writers remain
  frozen; recovery cannot resurrect the committed form.
- Cross-tab locking permits at most one live intent. View-only roles can read
  facts but mutation controls start locked. The legacy Nota FG browser writer
  stays blocked.

## Exact runtime CI

Exact runtime HEAD `9509bee8525ff9ba8e422eae7c9665ed76c506c4`
passed the Build UX job and the complete CP6 disposable full-schema job.

| Check | Run / job | Artifact / SHA-256 |
| --- | --- | --- |
| Build, security, unit, Chromium | `33928921418` / `101203330653` | dist `9957874743` / `14a7d3a13c592731284aa0a2e2002a881f24d2a967ab158a9aae140769979c3f`; browser `9957873747` / `e7cd81252883f076bbfbb99523279dd94073b6159ab9568a389d514d612e3ee9` |
| CP6 full-schema/Auth/browser/race/rollback | `33928918805` / `101203322910` | `9957936799` / `04caf9d3f8ebfa2ede07e974b9f84b3fcda2f9c9c31e8e17c5e50575018c0942` |

Verified output:

- Unit: 29 files / 201 tests.
- Chromium: 2 CP4.5 + 2 pre-CP5 + 12 CP5 + 24 CP6. The 24 CP6 cases
  are 12 scenarios on desktop and mobile, not 24 distinct business flows.
- Source ownership: 94 runtime files / 21 RPC boundaries / orphan and direct
  table access zero.
- Backend ownership: 89 effective / 66 CP5 source-byte-bound / unowned zero.
- Access ownership: 111 permissions / 46 navigation entries / 46 routes /
  20 sensitive actions / 21 RPC boundaries.
- CSS ownership: 36 stylesheets.
- The downloaded full-schema ZIP was 2,354,296 bytes, contained 132 entries,
  passed ZIP integrity, and independently hashed to the exact artifact digest.
  GitHub reports expiry at `2026-10-04T23:22:46Z`.

## Disposable authoritative proof

The full-schema job rebuilt the frozen predecessor, replayed CP4.5 through
CP5, applied v2.6.20 once, rejected replay, and exercised real PostgreSQL—not
browser formulas.

Representative finance/physical assertions include:

- failed-wash WIP path `180 → 180 → 190 → 180 → 90 → 0`;
- paid retry cost `90` and paid full-return cost `90` without FG/HPP output;
- unbilled accrual before reversal `70`;
- late-invoice HPP `94` and replacement-invoice HPP `88`;
- two paid failed-wash attempts retained as history;
- failed-wash physical net and final cost residue both zero after reversal;
- original and replacement history preserved;
- final PO ledger net zero after the complete reversal sequence;
- browser formula used: false.

Eleven real two-connection race families covered accrual, dispatch, receipt,
failed-wash, invoice, Final-SKU, and reversal conflicts. Final race invariants
were one active delivery of 10, one active receipt/Good of 10, one posted QC of
10, FG stock 10, current HPP 70, WIP net zero, FG debit 70, accrued credit 70,
AP zero, unbalanced journals zero, execution-context residue zero, 15/15 facade
idempotency rows/IDs, 6/6 nested Final-SKU rows/IDs, and zero unexpected winner
or loser rows.

Rollback was tested against relevant post-use, successor migration, new
product history, wrong name, tampered statement bytes, both connector-shaped
and full-file ledger byte forms, and an in-flight writer. The concurrency proof
recorded a rollback wait of 1.02 seconds and made its decision only after the
writer committed. The full rollback ladder restored CP4.5 and ended with all
v2.6.18–v2.6.20 application markers absent and schema/business/auth residue
zero.

## Recorded UAT state

UAT project `siimvrusnzxexizpyoib` received exactly one authorized mutation:
the official connector applied the complete 251,923-byte v2.6.20 migration.
It did not receive a seed, password user, or business transaction.

- Source and platform ledger are byte-identical:
  `52e51f56f4b8b08b7797b1a92ca9b9e26cbe611e81615c3379c728b95877ada1`.
- v2.6.18, v2.6.18a, v2.6.19, v2.6.19a, v2.6.19b, v2.6.19c, and
  v2.6.20 each exist exactly once in both applicable ledgers.
- Rollback capsule 13 and ACL capsule 13; stored-text checksum mismatch zero;
  installed-runtime checksum mismatch zero.
- Three public facades are owned by `postgres`, `SECURITY DEFINER`, empty
  search path, denied to PUBLIC/anon, and granted only to authenticated and
  service role. Their SHA-256 values are recorded in
  `cp6_v2620_uat_acceptance.json`.
- Eleven private functions and seven private tables were checked; execute/data
  leaks are zero. All private tables have RLS with no client policy. Six
  expected CP6 indexes are valid and ready.
- Of 180 ERP tables, 156 are empty. The 24 nonempty tables are only frozen
  configuration, access catalog, ledger, rollback/ACL capsule, release control,
  and the 36 pre-existing audit rows. Transactional business facts are zero.
- Auth users, app users, CP6 execution context, locks, active non-self sessions,
  long/idle transactions, and `http`/`pg_net` extensions are zero.
- Audit stayed 36; latest row remains `2026-09-02T19:09:40.299186Z`.

Advisor scan has no ERROR. Security reports the expected authenticated
`SECURITY DEFINER` warning for the three intended public facades and RLS-without-
policy INFO for the seven private deny-by-default tables. Live owner, ACL,
empty search path, internal permission checks, and private-table denial close
that generic warning.

Performance advisor has no WARN/ERROR. It reports nine unindexed-FK INFO items
on new history tables and five unused-index INFO items in the empty UAT. These
do not prove a data-integrity fault or production performance. They are
recorded as an explicit scale-review item; an independent reviewer should
decide whether any needs an index before later production cutover rather than
assuming INFO means either safe or broken.

## Legacy isolation

Legacy project `vlxdhpkjeevubjxexnfo` was rechecked read-only after UAT apply:

- 272 platform migrations, latest `20260829204756`;
- 38 application migrations, latest `v2.6.9a`;
- CP5/CP6 ledger rows and CP6 objects zero;
- auth/app users, locks, active sessions, long/idle transactions, and network
  extensions zero;
- audit remains two rows, latest `2026-08-28T09:59:41.219804Z`;
- historical rework/claim function MD5 values remain exactly
  `d4f297f43858bb3c819c9cacec2972ab`,
  `c59e0fc2f14934d3947ce5cc7f3c78bb`, and
  `3ce81f61adc7d56c5bd9d048dafda180`.

There is no evidence of CP6 contamination or any legacy mutation.

## Independent audit: blind pass first

Before using the checklist below, derive the intended Laundry → QC → Final SKU
flow yourself from the owner rules, exact source, database constraints, lock
order, journals, stock movements, HPP propagation, and reports. Search for any
way that a normal or malicious writer, retry, reversal, delayed invoice,
concurrent transaction, stale tab, or product-identity ambiguity can make two
authoritative subsystems disagree. Report every P0/P1/P2 finding even if it is
not anticipated here.

## Independent audit: checklist reconciliation

1. Resolve PR #24, base, exact head/parent/tree, draft/open/unmerged state, and
   `production_go:false`. Verify the evidence successor is one direct,
   evidence-only child of runtime HEAD `9509bee…`; recompute every Git blob.
2. Reconstruct product identity independently. Prove Brand scopes SKU number,
   two brands may share a number/model distinction safely, exact product/size
   owns stock and HPP, and Pattern is derived only from immutable production
   lineage.
3. For dispatch, ordinary return, Laundry-BS, paid failed wash, retry at
   vendor, full unprocessed return, QC, and Final-SKU, prove source quantity
   conservation and the absence of duplicate physical output.
4. Trace every journal, WIP event, accrual/AP transition, FG movement, HPP
   revision, entitlement, and report input. Recompute late/replacement invoice
   and reversal outcomes; reject any browser-owned formula.
5. Attempt identical replay, same-key/different-payload conflict, stale row
   version, cross-tab conflict, response loss, reload, committed-response plus
   failed refetch, and recovery. Require one durable operator intent and no
   resurrected committed form.
6. Re-run all eleven race families in both relevant commit orders. Check
   canonical lock order, winner/loser residue, nested idempotency, execution
   context, unbalanced journals, stock, HPP, and finance totals.
7. Reverse delivery, receipt, paid failed-wash cost, QC, Final-SKU, and vendor
   invoice in legal and illegal downstream states. Require exactly one linked
   inverse per origin, preserved history, and atomic rejection when blocked.
8. Tamper migration name, statement bytes, capsule definition, owner/ACL,
   successor state, post-use history, and product identity. Serialize rollback
   against a real in-flight writer, then run the complete ladder and prove
   exact restoration plus zero residue.
9. Re-run unit, build, client-secret scan, ownership/access/CSS checks,
   Auth/JWT HTTP proof, Chromium desktop/mobile, full-schema acceptance, and
   artifact digest verification from the exact evidence HEAD.
10. Recheck UAT and legacy read-only. Stop on ledger/function drift, business
    residue, audit growth, unexpected user, lock/session, extension, legacy
    object, or any advisor issue whose actual exploit/performance impact is
    blocking.

## Limits and next gate

Browser tests prove the state machine with mocked UAT responses; hosted UAT
proves exact migration identity, live definitions, ACL/RLS, and hygiene. Real
business transactions were exercised only in the exact-schema disposable
proof. CP6 therefore remains a draft audit candidate, not production-ready.

CP7 is the first checkpoint where the owner should run one complete dummy flow
through authoritative stock, HPP, journals, and financial reports. The formal
owner UX verdict is recommended after CP7.5 rebaseline/restore proof. Dummy
cleanup means tearing down or restoring the entire disposable environment and
then proving users, documents, stock, HPP, journals, report inputs, audit
fixtures, idempotency, locks, and sessions are all zero. It never means
selectively deleting posted history, and production/legacy are never cleanup
targets.

Independent verdict: pending. Merge authorization: pending independent PASS.
