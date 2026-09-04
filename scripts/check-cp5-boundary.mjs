import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const normalizeSql = (value) => value.replace(/\s+/g, ' ').trim()

const cuttingMigrationPath = 'supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql'
const cuttingRollbackPath = 'supabase/rollbacks/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.rollback.sql'
const correctionMigrationPath = 'supabase/migrations/20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.sql'
const correctionRollbackPath = 'supabase/rollbacks/20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.rollback.sql'
const cuttingTestPath = 'supabase/tests/cutting_bridge_persistence_pickup_wip_rollback.sql'
const cp5MigrationPath = 'supabase/migrations/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql'
const cp5RollbackPath = 'supabase/rollbacks/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.rollback.sql'
const cp5TestPath = 'supabase/tests/cp5_bs_resolution_recovery_rollback.sql'
const lineageMigrationPath = 'supabase/migrations/20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.sql'
const lineageRollbackPath = 'supabase/rollbacks/20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.rollback.sql'
const lineageTestPath = 'supabase/tests/cp5_rework_accessory_lineage_rollback.sql'
const reliabilityMigrationPath = 'supabase/migrations/20260904012525_erp_v2_6_19b_cp5_reliability_closure.sql'
const reliabilityRollbackPath = 'supabase/rollbacks/20260904012525_erp_v2_6_19b_cp5_reliability_closure.rollback.sql'
const atomicReversalMigrationPath = 'supabase/migrations/20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.sql'
const atomicReversalRollbackPath = 'supabase/rollbacks/20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.rollback.sql'

const cuttingMigration = read(cuttingMigrationPath)
const cuttingRollback = read(cuttingRollbackPath)
const correctionMigration = read(correctionMigrationPath)
const correctionRollback = read(correctionRollbackPath)
const cuttingTest = read(cuttingTestPath)
const cp5Migration = read(cp5MigrationPath)
const cp5Rollback = read(cp5RollbackPath)
const cp5Test = read(cp5TestPath)
const lineageMigration = read(lineageMigrationPath)
const lineageRollback = read(lineageRollbackPath)
const lineageTest = read(lineageTestPath)
const reliabilityMigration = read(reliabilityMigrationPath)
const reliabilityRollback = read(reliabilityRollbackPath)
const atomicReversalMigration = read(atomicReversalMigrationPath)
const atomicReversalRollback = read(atomicReversalRollbackPath)

function onlyVersion(directory, version, expected) {
  const matches = readdirSync(resolve(root, directory))
    .filter((name) => name.startsWith(`${version}_`))
  assert.deepEqual(matches, [expected], `Migration ledger version ${version} is duplicated or misnamed in ${directory}`)
}

onlyVersion('supabase/migrations', '20260903022604', cuttingMigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260903022604', cuttingRollbackPath.split('/').at(-1))
onlyVersion('supabase/migrations', '20260903070931', correctionMigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260903070931', correctionRollbackPath.split('/').at(-1))
onlyVersion('supabase/migrations', '20260903070932', cp5MigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260903070932', cp5RollbackPath.split('/').at(-1))
onlyVersion('supabase/migrations', '20260903151034', lineageMigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260903151034', lineageRollbackPath.split('/').at(-1))
onlyVersion('supabase/migrations', '20260904012525', reliabilityMigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260904012525', reliabilityRollbackPath.split('/').at(-1))
onlyVersion('supabase/migrations', '20260904061346', atomicReversalMigrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', '20260904061346', atomicReversalRollbackPath.split('/').at(-1))

for (const [path, sql] of [
  [cuttingMigrationPath, cuttingMigration], [cuttingRollbackPath, cuttingRollback],
  [correctionMigrationPath, correctionMigration], [correctionRollbackPath, correctionRollback],
  [cuttingTestPath, cuttingTest], [cp5MigrationPath, cp5Migration],
  [cp5RollbackPath, cp5Rollback], [cp5TestPath, cp5Test],
  [lineageMigrationPath, lineageMigration], [lineageRollbackPath, lineageRollback],
  [lineageTestPath, lineageTest],
  [reliabilityMigrationPath, reliabilityMigration], [reliabilityRollbackPath, reliabilityRollback],
  [atomicReversalMigrationPath, atomicReversalMigration], [atomicReversalRollbackPath, atomicReversalRollback],
]) {
  const tags = [...sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)].map((match) => match[0])
  const counts = new Map()
  tags.forEach((tag) => counts.set(tag, (counts.get(tag) ?? 0) + 1))
  assert.deepEqual([...counts].filter(([, count]) => count % 2 !== 0), [], `Unbalanced dollar quote in ${path}`)
  assert.match(sql, /\bbegin;/i, `${path} is not transactional`)
  assert.match(sql, /\b(?:commit|rollback);\s*$/i, `${path} has no explicit transaction close`)
}

function assertLedgerIdentity(rollback, migration, version, name, placeholder, ledgerSource = migration) {
  const migrationHash = sha256(ledgerSource)
  assert.doesNotMatch(rollback, new RegExp(placeholder), `${name} rollback hash was not rendered`)
  assert.equal((rollback.match(new RegExp(migrationHash, 'g')) ?? []).length, 3, `${name} rollback does not bind match, conflict, and DELETE predicates to exact migration bytes`)
  const guard = rollback.match(/select count\(\*\) into v_match_count\s+from supabase_migrations\.schema_migrations m\s+where\s*([\s\S]*?);\s+select count\(\*\) into v_conflict_count/i)
  const deletion = rollback.match(/delete from supabase_migrations\.schema_migrations m\s+where\s*([\s\S]*?);\s+drop table/i)
  assert.ok(guard, `${name} guarded platform-ledger predicate is missing`)
  assert.ok(deletion, `${name} platform-ledger DELETE predicate is missing`)
  assert.equal(normalizeSql(deletion[1]), normalizeSql(guard[1]), `${name} DELETE predicate diverges from its guard`)
  assert.match(normalizeSql(guard[1]), new RegExp(`m\\.name='${name}'.*${migrationHash}`))
  assert.doesNotMatch(normalizeSql(guard[1]), /m\.version=/, `${name} exact-version path can bypass statement digest`)
  assert.match(normalizeSql(rollback), new RegExp(`m\\.version='${version}' or m\\.name='${name}'`), `${name} conflict detector omits reviewed version/name`)
  return migrationHash
}

const cuttingHash = assertLedgerIdentity(
  cuttingRollback, cuttingMigration, '20260903022604',
  'erp_v2_6_18_cutting_persistence_pickup_wip', '__CUTTING_BRIDGE_MIGRATION_SHA256__',
)
const correctionHash = assertLedgerIdentity(
  correctionRollback, correctionMigration, '20260903070931',
  'erp_v2_6_18a_cutting_bridge_reconciliation', '__CUTTING_BRIDGE_RECONCILIATION_MIGRATION_SHA256__',
)
const cp5Hash = assertLedgerIdentity(
  cp5Rollback, cp5Migration, '20260903070932',
  'erp_v2_6_19_cp5_bs_resolution_recovery', '__BS_RESOLUTION_MIGRATION_SHA256__',
)
const lineageHash = assertLedgerIdentity(
  lineageRollback, lineageMigration, '20260903151034',
  'erp_v2_6_19a_cp5_rework_accessory_lineage', '__REWORK_ACCESSORY_LINEAGE_MIGRATION_SHA256__',
)
assert.ok(reliabilityMigration.endsWith('\n'), 'v2.6.19b source must retain one canonical file newline')
const reliabilityHash = assertLedgerIdentity(
  reliabilityRollback, reliabilityMigration, '20260904012525',
  'erp_v2_6_19b_cp5_reliability_closure', '__CP5_RELIABILITY_CLOSURE_MIGRATION_SHA256__',
  reliabilityMigration.slice(0, -1),
)
assert.ok(atomicReversalMigration.endsWith('\n'), 'v2.6.19c source must retain one canonical file newline')
const atomicReversalHash = assertLedgerIdentity(
  atomicReversalRollback, atomicReversalMigration, '20260904061346',
  'erp_v2_6_19c_cp5_atomic_reversal_reconciliation', '__CP5_ATOMIC_REVERSAL_MIGRATION_SHA256__',
  atomicReversalMigration.slice(0, -1),
)

assert.equal(Buffer.byteLength(cuttingMigration), 80392, 'Recorded UAT v2.6.18 byte length drift')
assert.equal(cuttingHash, '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f', 'Recorded UAT v2.6.18 source drift')
assert.match(cuttingMigration, /count\(\*\) from erp\.cutting_bridge_v2618_rollback_capsule where object_kind='FUNCTION'\)<>8/)
assert.match(cuttingMigration, /count\(\*\) from erp\.cutting_bridge_v2618_rollback_capsule where object_kind='RELATION'\)<>9/)
assert.match(cuttingMigration, /create index idx_material_stock_location_roll/)
assert.match(cuttingMigration, /'model_ids',coalesce/)
assert.match(cuttingMigration, /PO_ALREADY_ASSIGNED_TO_DIFFERENT_MANDOR/)
assert.match(cuttingMigration, /delete from erp\.cutting_distribution_allocations a/)
assert.match(cuttingMigration, /regexp_replace\([\s\S]{0,300}require_internal/i, 'Recorded v2.6.18 vulnerability is not represented exactly')
assert.doesNotMatch(cuttingMigration, /cutting_bridge_execution_context/, 'Recorded v2.6.18 must not be silently rewritten with the forward correction')
assert.match(cuttingRollback, /rollback CP5\/v2\.6\.19 and v2\.6\.18a first/)
assert.match(cuttingRollback, /idx_material_stock_location_roll/)
assert.doesNotMatch(cuttingRollback, /exists\(select 1 from erp\.cutting_bridge_execution_context\)/, 'Recorded v2.6.18 rollback must not query an intentionally absent correction table')

for (const token of [
  'cutting_bridge_v2618a_rollback_capsule', 'cutting_bridge_execution_context',
  'production.cutting.post', 'backend_pid=pg_backend_pid()', 'transaction_id=txid_current()',
  'actor_key=erp._idempotency_actor_key()', 'erp.has_permission(c.permission_key)',
  'Cutting Bridge execution context was lost before completion', 'production.distribution.view',
  'production.bs_rework.view', 'v_restored<>5',
]) assert.match(correctionMigration, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `Cutting reconciliation token missing: ${token}`)
assert.doesNotMatch(correctionMigration, /regexp_replace\([\s\S]{0,300}require_internal/i, 'Reconciliation must restore, not strip, canonical require_internal guards')
assert.match(correctionMigration, /and lower\(p\.prosrc\) not like '%require_internal%'/)
assert.match(correctionMigration, /alter table erp\.cutting_bridge_execution_context enable row level security/)
assert.match(correctionMigration, /alter table erp\.cutting_bridge_v2618_rollback_capsule enable row level security/)
assert.match(correctionMigration, /count\(\*\) from erp\.cutting_bridge_v2618a_rollback_capsule\)<>8/)
assert.match(correctionMigration, /drop index erp\.idx_material_stock_location_roll;[\s\S]*create index idx_material_stock_roll_location/)
assert.match(correctionMigration, /requires the unused recorded v2\.6\.18 boundary/)
assert.match(correctionRollback, /rollback CP5\/v2\.6\.19 first/)
assert.match(correctionRollback, /restores the exact recorded v2\.6\.18 runtime/)
assert.match(correctionRollback, /drop table erp\.cutting_bridge_execution_context/)
assert.match(correctionRollback, /disable row level security/)
assert.match(cuttingTest, /PRODUKSI_QC/)
assert.match(cuttingTest, /CBR_DIST_VIEW/)
assert.doesNotMatch(cuttingTest, /CBR_DISTRIBUTION_VIEW/, 'Cutting acceptance synthetic legacy role exceeds app_users.role varchar(20)')
assert.match(cuttingTest, /not like '%require_internal%'/)
assert.match(cuttingTest, /version='v2\.6\.18a'/)
assert.match(cuttingTest, /public\.erp_record_sewing_terminal_v1/, 'Cutting acceptance bypasses the authenticated sewing-terminal facade')
assert.doesNotMatch(cuttingTest, /insert\s+into\s+erp\.sewing_terminal_events/i, 'Cutting acceptance must not forge an authoritative sewing terminal event')

for (const token of [
  'bs_resolution_execution_context', 'cutting_bridge_execution_context',
  'bs_case_hold_events', 'ON_HOLD', 'transaction_id=txid_current()',
  'actor_key=erp._idempotency_actor_key()', 'erp.has_permission(c.permission_key)',
  'laundry_receipt_sources', 'settled_claims', "d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')",
  "c.claim_type='DAMAGE'", "c.status='SETTLED'", 'p_pattern_id',
  "untracked_type=case when v_cause='UNKNOWN' then untracked_type else null end",
]) assert.ok(cp5Migration.includes(token), `CP5 boundary token missing: ${token}`)
assert.doesNotMatch(cp5Migration, /d\.status\s*=\s*'POSTED'/, 'Laundry delivery lookup uses an impossible POSTED status')
assert.match(cp5Migration, /coalesce\(c\.delivery_id,claim_receipt\.delivery_id\) delivery_id/, 'Settled receipt claim must derive its delivery lineage')
for (const table of ['bs_resolution_v2619_rollback_capsule', 'bs_case_hold_events', 'bs_resolution_execution_context']) {
  assert.match(cp5Migration, new RegExp(`alter table erp\\.${table} enable row level security`))
}
assert.match(cp5Migration, /count\(\*\) from erp\.bs_resolution_v2619_rollback_capsule where object_kind='FUNCTION'\)<>20/)
assert.match(cp5Migration, /count\(\*\) from erp\.bs_resolution_v2619_rollback_capsule where object_kind='RELATION'\)<>10/)
assert.match(cp5Migration, /version='v2\.6\.18a'/)
assert.match(cp5Migration, /delete from erp\.bs_resolution_execution_context[\s\S]*CP5 execution context was lost before completion/)
assert.match(cp5Rollback, /v_internal_def not like '%cutting_bridge_execution_context%'/)
assert.match(cp5Rollback, /v_internal_def like '%bs_resolution_execution_context%'/)

assert.equal(Buffer.byteLength(lineageMigration), 55354, 'Recorded UAT v2.6.19a byte length drift')
assert.equal(lineageHash, '204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f', 'Recorded UAT v2.6.19a source drift')
for (const token of [
  'rework_accessory_decisions', 'rework_accessory_selection_lines',
  'accessory_bom_item_ids must be an explicit array',
  'Cumulative rework return quantities cannot decrease',
  'Final cumulative rework quantities cannot decrease',
  'Link the lot before snapshotting', 'idx_bs_case_hold_events_actor',
  'ux_rework_orders_good_fg_lot_v2619a', "'v2.6.19a'",
]) assert.ok(lineageMigration.includes(token), `v2.6.19a lineage boundary token missing: ${token}`)
for (const token of [
  'intentionally pre-use only', 'exact six-function capsule',
  'post-install business/audit/idempotency history exists',
  "md5(pg_get_functiondef(\n       'erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure",
  'f4f238d3b029c63d8d4c7753e3b661a1',
]) assert.ok(lineageRollback.includes(token), `v2.6.19a rollback proof token missing: ${token}`)
for (const token of [
  'Only Button was newly installed; Label remained unchecked',
  'Partial return posted FG/accounting or lost cumulative custody',
  'Selected Button reimbursement did not accrue to the authoritative Mandor',
  'Selected accessory accrual did not post exact WIP/variance/payable amounts',
  'Explicit empty accessory choice fell back to the full BOM',
  'REWASH did not pay only Label to the PO Mandor with zero vendor work fee',
  'Reversal did not unwind money/stock while preserving immutable selection',
  'Accessory selection history accepted an in-place rewrite',
]) assert.ok(lineageTest.includes(token), `v2.6.19a acceptance proof missing: ${token}`)

assert.equal(Buffer.byteLength(reliabilityMigration), 42021, 'v2.6.19b source byte length drift')
assert.equal(sha256(reliabilityMigration), 'b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d', 'v2.6.19b file source drift')
assert.equal(reliabilityHash, '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d', 'v2.6.19b connector ledger source drift')
for (const token of [
  'rollback capsule is incomplete or invalid', "check(claim_type in('MISSING','STUCK','DAMAGE'))",
  "selection_basis in('UNPAID_BASELINE','MANUAL_REPLACEMENT')",
  'Laundry claim requires a sent authoritative delivery',
  'Laundry return plus active MISSING/STUCK claims exceed sent quantity',
  'SERVER_ENTITLEMENT_V2619B', 'UNPAID_COMPONENT_ENTITLEMENT',
  'remaining_unentitled_good_qty_pcs', 'v_entitled_qty<v_case_qty',
  'for update of lr,lrl', 'matching DAMAGE claim validation',
  "new.status in('DRAFT','REVERSED')", "new.status='REVERSED'",
  "'v2.6.19b'",
]) assert.ok(reliabilityMigration.includes(token), `v2.6.19b reliability token missing: ${token}`)
for (const token of [
  'post-install business/financial/stock/HPP/audit history exists',
  'platform ledger identity is ambiguous', 'exact function/ACL/owner restoration failed',
  'rollback left reliability-closure residue',
]) assert.ok(reliabilityRollback.includes(token), `v2.6.19b rollback proof token missing: ${token}`)
assert.equal(Buffer.byteLength(atomicReversalMigration), 13808, 'v2.6.19c source byte length drift')
assert.equal(sha256(atomicReversalMigration), 'b11014081391f3d72e242813b09bb64c53e2aefe0f4eb42cc20e8089a57ef8ba', 'v2.6.19c file source drift')
assert.equal(atomicReversalHash, '70bafe4f4c690c6ef1548f712ee2035a78c9137e153c92c69fc57decba58e3cc', 'v2.6.19c connector ledger source drift')
for (const token of [
  'CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION',
  'BS_CASH_COMPENSATION_REQUIRES_ACTIVE_SETTLED_CLAIM',
  'bs_resolutions_cash_claim_contract_v2619c',
  'r.compensation_amount is distinct from 0',
  'compensation_amount is not distinct from 0',
  'for update', "'v2.6.19c'",
]) assert.ok(atomicReversalMigration.includes(token), `v2.6.19c atomic-reversal token missing: ${token}`)
for (const token of [
  'post-install claim/BS financial or audit history exists',
  'platform ledger statement digest is ambiguous',
  'rollback failed exact restoration or left invariant residue',
]) assert.ok(atomicReversalRollback.includes(token), `v2.6.19c rollback proof token missing: ${token}`)
for (const token of [
  'CP5 accepted a claim against a DRAFT delivery',
  'CP5 accepted a claim against a REVERSED delivery',
  'CP5 accepted DAMAGE against a DRAFT receipt',
  'CP5 accepted DAMAGE against a REVERSED receipt',
  'CP5 accepted unconserved Laundry claim OTHER',
  'return plus active MISSING/STUCK claims exceed sent quantity',
  'CP5 v2.6.19c claim/BS cross-ledger invariant is not installed completely',
  'CP5 reversed a settled claim while its BS CASH_COMPENSATION remained active',
]) assert.ok(cp5Test.includes(token), `v2.6.19b Laundry acceptance proof missing: ${token}`)
for (const token of [
  'SERVER_ENTITLEMENT_V2619B', 'UNPAID_BASELINE', 'MANUAL_REPLACEMENT',
  'UNPAID_COMPONENT_ENTITLEMENT', 'remaining_unentitled_good_qty_pcs',
  'Remaining physical BS did not keep exactly one unpaid baseline entitlement',
]) assert.ok(lineageTest.includes(token), `v2.6.19b accessory-default proof missing: ${token}`)

const cp5Page = read('src/ConnectedBsResolutionPage.tsx')
const cp5Model = read('src/bsResolutionModel.ts')
const cp5ModelTest = read('src/bsResolutionModel.test.ts')
const cp5DomTest = read('src/ConnectedBsResolutionPage.dom.test.tsx')
const cp5BrowserTest = read('tests/browser/cp5-bs-resolution.spec.ts')
const cp5BrowserConfig = read('playwright.cp5.config.ts')
const cp5AuthTest = read('scripts/cp5_auth_permission_e2e.mjs')
const cp5RaceTest = read('scripts/cp5_bs_resolution_concurrency.py')
const cp5Workflow = read('.github/workflows/cp5-full-schema-validation.yml')
const masterDataPage = read('src/MasterDataPages.tsx')
const materialMasterPage = read('src/MaterialMasterPages.tsx')
const reliabilityRules = read('docs/erp-reliability-invariants.md')
const packageJson = read('package.json')
const uatEnvironmentGuard = read('scripts/assert-uat-auth-env.mjs')
const uatEnvironmentGuardTest = read('scripts/test-uat-auth-assertions.mjs')
const hostedUatEvidence = JSON.parse(read('docs/evidence/cp5_hosted_uat_auth_e2e.json'))
const app = read('src/App.tsx')
const cuttingPage = read('src/ConnectedCuttingPage.tsx')
const cuttingPatternPicker = read('src/CuttingPatternPicker.tsx')
const wipPage = read('src/ConnectedWipStatusPage.tsx')
const pickupPage = read('src/ConnectedPickupPage.tsx')
const qcPage = read('src/QcFinalPage.tsx')
const runtime = read('src/config/runtime.ts')

const cp5RpcNames = [...cp5Page.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)].map((match) => match[1])
assert.deepEqual(
  [...new Set(cp5RpcNames)].sort(),
  ['erp_get_bs_resolution_workspace_v1', 'erp_save_bs_resolution_action_v1'],
  'CP5 browser boundary must use exactly the two owned public RPC facades',
)
assert.equal(cp5RpcNames.filter((name) => name === 'erp_save_bs_resolution_action_v1').length, 2,
  'CP5 UI must have exactly one initial mutation call and one exact-envelope reconcile call')
for (const token of [
  "type ClaimType = 'STUCK' | 'MISSING' | 'DAMAGE'", 'receipt_line_id:',
  'settled_claims', "action: 'CANCEL'", 'busyRef.current', 'cbsr-pagination',
  'completed_before_bs_qty', 'globalThis.crypto.randomUUID()', 'loadRequestRef.current',
  'pendingMutationStorageKey', 'writePendingMutation', 'pendingMutationRef.current',
  'Reconcile transaksi', 'AKSESORI YANG BENAR-BENAR DIPASANG',
  'accessory_bom_item_ids: accessoryIds', "action: 'SAVE', qty_good_returned: qty(good)",
  'Simpan partial', 'Vendor Rewash tidak mendapat fee kerja komponen',
  'item.default_selected', 'workspaceStale', 'refresh authoritative gagal',
  'seluruh writer terkunci sampai Refetch authoritative berhasil',
  "action === 'CREATE_MANUAL_BS' || action === 'SAVE_CLAIM'",
  'return refetched && recoveryEnvelopeCleared', 'canSubmit={effectiveCanCreate}',
  'remaining_unentitled_good_qty_pcs', 'selectedContractKey',
]) assert.ok(cp5Page.includes(token), `CP5 UI lifecycle token missing: ${token}`)
const claimFormSource = cp5Page.slice(cp5Page.indexOf('function CreateClaim'), cp5Page.indexOf('function ClassificationPanel'))
assert.doesNotMatch(claimFormSource, /OTHER/, 'CP5 claim UI still offers unconserved Laundry OTHER')
for (const token of [
  'laundry_sources', 'laundry_receipt_sources', 'settled_claims', 'qty_claimable_pcs',
  'accessory_bom', 'accessory_decision', 'selection_sha256', 'default_selected',
  'default_selection_basis', 'remaining_new_work_qty_pcs', 'selection_basis',
  'remaining_unentitled_good_qty_pcs',
]) {
  assert.ok(cp5Model.includes(token), `CP5 response parser omits ${token}`)
  assert.ok(cp5ModelTest.includes(token), `CP5 parser test omits ${token}`)
}

for (const token of [
  "{category:'Kancing',chargeUom:'pcs',reimbursementUom:'pcs',mandorCharge:495,reimbursement:500",
  "{category:'Sleting',chargeUom:'lusin',reimbursementUom:'pcs',mandorCharge:29_900,reimbursement:2_500",
  "{category:'Hang Tag',chargeUom:'lusin',reimbursementUom:'pcs',mandorCharge:7_150,reimbursement:600",
  "{category:'Lock Pin',chargeUom:'pcs',reimbursementUom:'pcs',mandorCharge:300,reimbursement:300",
  "{category:'Kain Kantong'", "{category:'Label'", "{category:'Kain Keras'",
]) assert.ok(masterDataPage.includes(token), `Owner accessory category truth missing: ${token}`)
for (const token of [
  "{category:'Kancing',sellingPrices:[{id:'owner-kancing-charge',amount:495,uom:'pcs'",
  "{category:'Centang',sellingPrices:[{id:'owner-centang-charge',amount:200,uom:'pcs'",
  "{category:'Kulit',sellingPrices:[{id:'owner-kulit-charge',amount:1_000,uom:'pcs'",
  "{category:'Sleting',sellingPrices:[{id:'owner-sleting-charge',amount:29_900,uom:'lusin'",
  "{category:'Plat',sellingPrices:[{id:'owner-plat-charge',amount:500,uom:'pcs'",
  "{category:'Hang Tag',sellingPrices:[{id:'owner-hang-tag-charge',amount:7_150,uom:'lusin'",
  "{category:'Lock Pin',sellingPrices:[{id:'owner-lock-pin-charge',amount:300,uom:'pcs'",
  "{category:'Kain Kantong',sellingPrices:[],reimbursementPrices:[]}",
  "{category:'Label',sellingPrices:[],reimbursementPrices:[]}",
  "{category:'Kain Keras',sellingPrices:[],reimbursementPrices:[]}",
  '7 kategori aktif dan 3 future',
  'tagihan dan reimbursement selalu memakai kategori besar',
]) assert.ok(materialMasterPage.includes(token), `Operational accessory master truth missing: ${token}`)
for (const forbidden of [
  "category:'Resleting'", "amount:750,uom:'pcs'", "amount:800,uom:'pcs'",
]) assert.equal(materialMasterPage.includes(forbidden), false, `Stale accessory master truth remains: ${forbidden}`)
for (const token of [
  'Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.',
  'Financial posting, stock movement, HPP propagation, entitlement, physical custody',
  'The legacy ERP project is read-only',
]) assert.ok(reliabilityRules.includes(token), `ERP supreme reliability rule missing: ${token}`)

assert.match(pickupPage, /ConnectedPatternFilter/)
assert.match(wipPage, /ConnectedPatternFilter/)
for (const [name, source] of [['Cutting', cuttingPage], ['Pickup', pickupPage], ['WIP', wipPage]]) {
  assert.match(source, /loadRequestRef\.current/, `${name} connected loader can accept a stale RPC response`)
}
assert.match(cuttingPage, /ccut-pagination/)
assert.match(cuttingPage, /setLocationId\(event\.target\.value\)[\s\S]{0,200}setSelectedRolls\(\{\}\)[\s\S]{0,100}setYields\(\{\}\)/, 'Changing warehouse must clear rolls and yields from the old warehouse')
assert.match(cuttingPatternPicker, /savingRef\.current/, 'Pattern quick-create permits same-frame double submit')
assert.match(pickupPage, /cpick-pagination/)
assert.match(pickupPage, /!selectedContractorMissing/)
assert.match(pickupPage, /Mandor yang dikunci di Production Order sudah tidak aktif/)
assert.match(pickupPage, /Mandor pada draft sudah tidak aktif/)
assert.match(app, /aria-label="Filter Pola Laundry"[\s\S]*DATA SIMULASI/)
assert.match(qcPage, /aria-label="Filter Pola QC"[\s\S]*DATA SIMULASI/)
assert.doesNotMatch(qcPage, /visible\[0\]\s*\?\?\s*seeds\[0\]/, 'QC Pattern filter must not fall back to an unrelated hidden seed')
for (const [name, source] of [['Cutting', cuttingPage], ['Pickup', pickupPage]]) {
  assert.match(source, /savingRef\.current/, `${name} mutation boundary permits same-frame double submit`)
}
assert.match(wipPage, /flaggingRef\.current/, 'WIP flag mutation boundary permits same-frame double submit')
for (const mode of ['cuttingMode', 'distributionMode', 'wipStatusMode', 'bsResolutionMode']) {
  assert.match(runtime, new RegExp(`${mode}: 'CONNECTED'`), `UAT runtime does not connect ${mode}`)
  assert.match(app, new RegExp(`runtime\\.${mode} === 'CONNECTED'`), `App routing ignores ${mode}`)
}

for (const action of [
  'CREATE_MANUAL_BS', 'CLASSIFY_BS', 'SAVE_REWORK', 'COMPLETE_REWORK',
  'DISPOSE_BS', 'HOLD_BS', 'RELEASE_HOLD', 'REVERSE_DISPOSITION',
  'REVERSE_REWORK_COMPLETION', 'SAVE_CLAIM', 'RESOLVE_CLAIM',
  'REVERSE_CLAIM_RESOLUTION',
]) {
  assert.ok(cp5Migration.includes(`'${action}'`), `CP5 dispatcher omits ${action}`)
  assert.ok(cp5Test.includes(`'${action}'`), `CP5 acceptance omits ${action}`)
}
for (const proof of [
  'CP5 active rework cancellation path failed', 'All-BS rewash leaked the legacy PARTIAL status bug',
  'settled_claims', 'CASH_COMPENSATION', 'CP5 Pattern filter',
  'CP5 execution capability leaked', 'CP5 HOLD history accepted an in-place rewrite',
  'CP5 explicit claim REJECT action failed', 'CP5 rejected DAMAGE claim did not restore receipt-line capacity',
  'CP5 DAMAGE claim exceeded receipt-line capacity', 'source_laundry_receipt_line_id=v_receipt_line',
  'laundry_receipt_bs_product_allocations', 'source_laundry_bs_allocation_id=v_receipt_allocation',
  'select row_version into v_receipt_version',
  'CP5 manual BS classification did not reconcile tracked cause and legacy audit lineage',
]) assert.ok(cp5Test.includes(proof), `CP5 acceptance proof missing: ${proof}`)

for (const token of [
  'same-frame double mutation', "p_action: 'HOLD_BS'", "p_pattern_id === 'pattern-2'",
  'Tidak ada kasus pada filter ini', 'Tidak ada detail', 'view-only access',
  'persists a lost-response envelope across reload',
  'Payload berbeda yang tidak boleh terkirim', 'sudah direconcile dengan UUID lama',
  "expect(container.querySelector('.cbsr-modal-layer')).toBeNull()",
  'retires a committed claim form permanently',
  'retires a committed manual BS form permanently',
  "p_action: 'CREATE_MANUAL_BS'",
  'defaults only server-proven unpaid items and sends exactly the checked set',
  'saves cumulative partial returns without calling the completion action',
  "accessory_bom_item_ids: ['bom-item-1']", "p_action: 'SAVE_REWORK'", "action: 'SAVE'",
  'allows an explicit real replacement without silently checking a prior entitlement',
  "expect(actionCalls).toHaveLength(1)",
]) assert.ok(cp5DomTest.includes(token), `CP5 DOM proof missing: ${token}`)
for (const token of [
  "proof_class: 'LOCAL_MOCKED_UAT_CONTRACT'", 'hosted_uat: false',
  "p_action: 'HOLD_BS'", "args.p_pattern_id !== 'pattern-2'",
  'same_frame_mutation_count', 'view_only_mutation_count: 0',
  "locator('.cbsr-detail').getByRole('heading', { name: 'BS-1', exact: true })",
  'AKSESORI YANG BENAR-BENAR DIPASANG',
  'SERVER_ENTITLEMENT_V2619B', 'remaining_unentitled_good_qty_pcs',
  'saves cumulative partial return without posting completion',
  "p_action: 'SAVE_REWORK', p_expected_version: 2", 'completion_posted: false',
  'lost commit response survives reload', 'same_idempotency_uuid',
  'persisted_across_reload: true',
  'committed claim cannot be submitted again',
  'committed manual BS cannot be submitted again',
  'mutation_count_after_recovery', "p_action: 'CREATE_MANUAL_BS'", "p_action: 'SAVE_CLAIM'",
]) assert.ok(cp5BrowserTest.includes(token), `CP5 browser contract proof missing: ${token}`)
assert.match(cp5BrowserConfig, /testMatch: 'cp5-bs-resolution\.spec\.ts'/)
assert.match(cp5BrowserConfig, /ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1'/)
assert.match(packageJson, /"test:browser:cp5": "playwright test --config playwright\.cp5\.config\.ts"/)
assert.ok(
  uatEnvironmentGuard.includes('if (!/^sb_publishable_[a-z0-9._-]{16,}$/i.test(publishableKey))'),
  'UAT release guard regressed to a case-sensitive publishable-key format check',
)
assert.ok(
  uatEnvironmentGuardTest.includes('sb_publishable_Unreviewed_MixedCase_1234567890'),
  'UAT release guard lacks a mixed-case publishable-key regression',
)
assert.equal(hostedUatEvidence.format, 'CP5_HOSTED_UAT_AUTH_E2E_V1')
assert.equal(hostedUatEvidence.status, 'PASS')
assert.equal(hostedUatEvidence.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
assert.equal(hostedUatEvidence.classified_as_ci, false)
assert.equal(hostedUatEvidence.case_count, 31)
assert.equal(hostedUatEvidence.case_passed, 31)
assert.equal(hostedUatEvidence.assertions.server_side_pattern_filter_has_true_empty_state, true)
assert.equal(hostedUatEvidence.cleanup.temporary_credentials_retained, false)
assert.equal(hostedUatEvidence.cleanup.new_audit_rows_after_cleanup, 0)
assert.equal(hostedUatEvidence.cloudflare_preview.promoted_to_canonical_worker, false)
assert.equal(hostedUatEvidence.production_go, false)

for (const token of [
  "const uatHost = 'siimvrusnzxexizpyoib.supabase.co'",
  "const legacyHost = 'vlxdhpkjeevubjxexnfo.supabase.co'",
  'manual_bs_idempotency_and_conflict', 'view_only_read_and_mutation_denial',
  'owner_stale_rejection_and_reversal', 'synthetic_identity_session_token_and_business_cleanup',
  "'audit_logs',(select count(*) from erp.audit_logs", "'access_audit',(select count(*) from erp.app_access_audit",
  "'execution_context',(select count(*) from erp.bs_resolution_execution_context)",
  "textUuidCondition('user_id', users.map((user) => user.id))",
]) assert.ok(cp5AuthTest.includes(token), `CP5 Auth/JWT proof missing: ${token}`)
for (const token of [
  'run_disposition_race()', 'run_claim_race()', 'DAMAGE conservation failed',
  'run_damage_source_claim_wins_race()', 'run_damage_source_reversal_wins_race()',
  'damage_claim_and_receipt_reversal_serialize_both_directions',
  'run_stuck_vs_return_race()', 'stuck_claim_and_physical_return_share_one_conservation_lock',
  'run_claim_cash_dependency_races()',
  'claim_reversal_and_bs_cash_compensation_serialize_both_directions',
  'real_two_connection_wait_observed', 'remaining_capacity', "'audit_logs',(select count(*) from erp.audit_logs",
  "'access_audit',(select count(*) from erp.app_access_audit", "report['residue'] = residue",
  "insert into erp.contractors", "insert into erp.product_models",
  "'contractors',(select count(*) from erp.contractors", "'models',(select count(*) from erp.product_models",
]) assert.ok(cp5RaceTest.includes(token), `CP5 concurrency proof missing: ${token}`)
assert.doesNotMatch(cp5RaceTest, /clock_timestamp\(\)/, 'CP5 race fixtures must not depend on runner wall-clock ordering')
for (const token of [
  'SOURCE_BASE_SHA: 8bfac13b91ea1be92111139e2fddcabccf9ae19a',
  'erp_enteng_cp45a_catalog_bootstrap.sql.gz',
  'READ_ONLY_PG_CATALOG_PLUS_ALLOWLISTED_CONFIGURATION',
  'CP45A_RESTORED_BOUNDARY.json',
  'rm -rf supabase/.temp',
  '20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql',
  '20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.sql',
  '20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql',
  '20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.sql',
  '20260904012525_erp_v2_6_19b_cp5_reliability_closure.sql',
  '20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.sql',
  'cp5_bs_resolution_recovery_rollback.sql', 'cp5_bs_resolution_concurrency.py',
  'cp5_rework_accessory_lineage_rollback.sql',
  'cp5_auth_permission_e2e.mjs', 'test:browser:precp5', 'test:browser:cp5',
  '20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.rollback.sql',
  '20260904012525_erp_v2_6_19b_cp5_reliability_closure.rollback.sql',
  '20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.rollback.sql',
  '20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.rollback.sql',
  '20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.rollback.sql',
  '20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.rollback.sql',
  'V2619A_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log', 'V2619_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log',
  'V2619A_ROLLBACK_POST_USE_REJECTION.log',
  'V2619B_ROLLBACK_POST_USE_REJECTION.log',
  'V2619B_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log',
  'V2619C_ROLLBACK_POST_USE_REJECTION.log',
  'V2619C_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log',
  'V2619C_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2619C_INSTALLED_INVARIANT.json',
  'V2619B_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2619A_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2619_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2618A_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2618_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2618A_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log',
  'V2618_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log', 'V2619_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  'V2619A_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  'V2619B_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  'V2618A_HOSTED_PLATFORM_LEDGER_SHAPE.json', 'V2618_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  '20260903060213', '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f',
  "set name='WRONG_MIGRATION'", "'production_go',false",
]) assert.ok(cp5Workflow.includes(token), `CP5 full-schema workflow missing: ${token}`)
for (const staleRecoveryToken of [
  'RECOVERY_RUN_ID', 'cp35-final-recovery-capsule-encrypted',
  'cp35-final-recovery-key-separate', 'recovery-transport',
]) assert.equal(cp5Workflow.includes(staleRecoveryToken), false, `CP5 workflow still depends on expiring recovery material: ${staleRecoveryToken}`)

const tempDirectory = resolve(root, 'supabase/.temp')
assert.equal(existsSync(tempDirectory) ? readdirSync(tempDirectory).length : 0, 0, 'Supabase generator cache files must not enter the candidate')
console.log(`CP5 boundary passed: recorded Cutting ${cuttingHash.slice(0, 12)}, reconciliation ${correctionHash.slice(0, 12)}, BS Resolution ${cp5Hash.slice(0, 12)}, accessory lineage ${lineageHash.slice(0, 12)}, reliability closure ${reliabilityHash.slice(0, 12)}, atomic reversal ${atomicReversalHash.slice(0, 12)}; canonical gates, 12 actions, entitlement-derived defaults, conserved Laundry claims, lost-response reconciliation, claim/BS serialization, digest-bound rollback identities, and hosted-UAT boundaries are owned.`)
