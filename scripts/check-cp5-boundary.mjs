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

const cuttingMigration = read(cuttingMigrationPath)
const cuttingRollback = read(cuttingRollbackPath)
const correctionMigration = read(correctionMigrationPath)
const correctionRollback = read(correctionRollbackPath)
const cuttingTest = read(cuttingTestPath)
const cp5Migration = read(cp5MigrationPath)
const cp5Rollback = read(cp5RollbackPath)
const cp5Test = read(cp5TestPath)

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

for (const [path, sql] of [
  [cuttingMigrationPath, cuttingMigration], [cuttingRollbackPath, cuttingRollback],
  [correctionMigrationPath, correctionMigration], [correctionRollbackPath, correctionRollback],
  [cuttingTestPath, cuttingTest], [cp5MigrationPath, cp5Migration],
  [cp5RollbackPath, cp5Rollback], [cp5TestPath, cp5Test],
]) {
  const tags = [...sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)].map((match) => match[0])
  const counts = new Map()
  tags.forEach((tag) => counts.set(tag, (counts.get(tag) ?? 0) + 1))
  assert.deepEqual([...counts].filter(([, count]) => count % 2 !== 0), [], `Unbalanced dollar quote in ${path}`)
  assert.match(sql, /\bbegin;/i, `${path} is not transactional`)
  assert.match(sql, /\b(?:commit|rollback);\s*$/i, `${path} has no explicit transaction close`)
}

function assertLedgerIdentity(rollback, migration, version, name, placeholder) {
  const migrationHash = sha256(migration)
  assert.doesNotMatch(rollback, new RegExp(placeholder), `${name} rollback hash was not rendered`)
  assert.equal((rollback.match(new RegExp(migrationHash, 'g')) ?? []).length, 3, `${name} rollback does not bind match, conflict, and DELETE predicates to exact migration bytes`)
  const guard = rollback.match(/select count\(\*\) into v_match_count\s+from supabase_migrations\.schema_migrations m\s+where\s*([\s\S]*?);\s+select count\(\*\) into v_conflict_count/i)
  const deletion = rollback.match(/delete from supabase_migrations\.schema_migrations m\s+where\s*([\s\S]*?);\s+drop table/i)
  assert.ok(guard, `${name} guarded platform-ledger predicate is missing`)
  assert.ok(deletion, `${name} platform-ledger DELETE predicate is missing`)
  assert.equal(normalizeSql(deletion[1]), normalizeSql(guard[1]), `${name} DELETE predicate diverges from its guard`)
  assert.match(normalizeSql(guard[1]), new RegExp(`m\\.version='${version}'.*m\\.name='${name}'`))
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
assert.match(cuttingTest, /not like '%require_internal%'/)
assert.match(cuttingTest, /version='v2\.6\.18a'/)

for (const token of [
  'bs_resolution_execution_context', 'cutting_bridge_execution_context',
  'bs_case_hold_events', 'ON_HOLD', 'transaction_id=txid_current()',
  'actor_key=erp._idempotency_actor_key()', 'erp.has_permission(c.permission_key)',
  'laundry_receipt_sources', 'settled_claims', "d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')",
  "c.claim_type='DAMAGE'", "c.status='SETTLED'", 'p_pattern_id',
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

const cp5Page = read('src/ConnectedBsResolutionPage.tsx')
const cp5Model = read('src/bsResolutionModel.ts')
const cp5ModelTest = read('src/bsResolutionModel.test.ts')
const cp5DomTest = read('src/ConnectedBsResolutionPage.dom.test.tsx')
const cp5BrowserTest = read('tests/browser/cp5-bs-resolution.spec.ts')
const cp5BrowserConfig = read('playwright.cp5.config.ts')
const cp5AuthTest = read('scripts/cp5_auth_permission_e2e.mjs')
const cp5RaceTest = read('scripts/cp5_bs_resolution_concurrency.py')
const cp5Workflow = read('.github/workflows/cp5-full-schema-validation.yml')
const packageJson = read('package.json')
const app = read('src/App.tsx')
const cuttingPage = read('src/ConnectedCuttingPage.tsx')
const cuttingPatternPicker = read('src/CuttingPatternPicker.tsx')
const wipPage = read('src/ConnectedWipStatusPage.tsx')
const pickupPage = read('src/ConnectedPickupPage.tsx')
const qcPage = read('src/QcFinalPage.tsx')
const runtime = read('src/config/runtime.ts')

assert.deepEqual(
  [...cp5Page.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)].map((match) => match[1]).sort(),
  ['erp_get_bs_resolution_workspace_v1', 'erp_save_bs_resolution_action_v1'],
  'CP5 browser boundary must use exactly the two owned public RPC facades',
)
for (const token of [
  "type ClaimType = 'STUCK' | 'MISSING' | 'DAMAGE' | 'OTHER'", 'receipt_line_id:',
  'settled_claims', "action: 'CANCEL'", 'busyRef.current', 'cbsr-pagination',
  'completed_before_bs_qty', 'globalThis.crypto.randomUUID()', 'loadRequestRef.current',
  'actionRequestRef.current.fingerprint',
]) assert.ok(cp5Page.includes(token), `CP5 UI lifecycle token missing: ${token}`)
for (const token of ['laundry_sources', 'laundry_receipt_sources', 'settled_claims', 'qty_claimable_pcs']) {
  assert.ok(cp5Model.includes(token), `CP5 response parser omits ${token}`)
  assert.ok(cp5ModelTest.includes(token), `CP5 parser test omits ${token}`)
}

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
]) assert.ok(cp5Test.includes(proof), `CP5 acceptance proof missing: ${proof}`)

for (const token of [
  'same-frame double mutation', "p_action: 'HOLD_BS'", "p_pattern_id === 'pattern-2'",
  'Tidak ada kasus pada filter ini', 'Tidak ada detail', 'view-only access',
  'reuses the same idempotency key',
]) assert.ok(cp5DomTest.includes(token), `CP5 DOM proof missing: ${token}`)
for (const token of [
  "proof_class: 'LOCAL_MOCKED_UAT_CONTRACT'", 'hosted_uat: false',
  "p_action: 'HOLD_BS'", "args.p_pattern_id !== 'pattern-2'",
  'same_frame_mutation_count', 'view_only_mutation_count: 0',
]) assert.ok(cp5BrowserTest.includes(token), `CP5 browser contract proof missing: ${token}`)
assert.match(cp5BrowserConfig, /testMatch: 'cp5-bs-resolution\.spec\.ts'/)
assert.match(cp5BrowserConfig, /ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1'/)
assert.match(packageJson, /"test:browser:cp5": "playwright test --config playwright\.cp5\.config\.ts"/)

for (const token of [
  "const uatHost = 'siimvrusnzxexizpyoib.supabase.co'",
  "const legacyHost = 'vlxdhpkjeevubjxexnfo.supabase.co'",
  'manual_bs_idempotency_and_conflict', 'view_only_read_and_mutation_denial',
  'owner_stale_rejection_and_reversal', 'synthetic_identity_session_token_and_business_cleanup',
  "'audit_logs',(select count(*) from erp.audit_logs", "'access_audit',(select count(*) from erp.app_access_audit",
  "'execution_context',(select count(*) from erp.bs_resolution_execution_context)",
]) assert.ok(cp5AuthTest.includes(token), `CP5 Auth/JWT proof missing: ${token}`)
for (const token of [
  'run_disposition_race()', 'run_claim_race()', 'DAMAGE claim exceeds BS quantity',
  'real_two_connection_wait_observed', 'remaining_capacity', "'audit_logs',(select count(*) from erp.audit_logs",
  "'access_audit',(select count(*) from erp.app_access_audit", "report['residue'] = residue",
]) assert.ok(cp5RaceTest.includes(token), `CP5 concurrency proof missing: ${token}`)
for (const token of [
  'SOURCE_BASE_SHA: 8bfac13b91ea1be92111139e2fddcabccf9ae19a',
  '20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql',
  '20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.sql',
  '20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql',
  'cp5_bs_resolution_recovery_rollback.sql', 'cp5_bs_resolution_concurrency.py',
  'cp5_auth_permission_e2e.mjs', 'test:browser:precp5', 'test:browser:cp5',
  '20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.rollback.sql',
  '20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.rollback.sql',
  '20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.rollback.sql',
  'V2619_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log', 'V2618A_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log',
  'V2618_ROLLBACK_WRONG_LOCAL_NAME_REJECTION.log', 'V2619_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  'V2618A_HOSTED_PLATFORM_LEDGER_SHAPE.json', 'V2618_HOSTED_PLATFORM_LEDGER_SHAPE.json',
  '20260903060213', '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f',
  "set name='WRONG_MIGRATION'", "'production_go',false",
]) assert.ok(cp5Workflow.includes(token), `CP5 full-schema workflow missing: ${token}`)

const tempDirectory = resolve(root, 'supabase/.temp')
assert.equal(existsSync(tempDirectory) ? readdirSync(tempDirectory).length : 0, 0, 'Supabase generator cache files must not enter the candidate')
console.log(`CP5 boundary passed: recorded Cutting ${cuttingHash.slice(0, 12)}, reconciliation ${correctionHash.slice(0, 12)}, BS Resolution ${cp5Hash.slice(0, 12)}; canonical gates, 12 actions, Pattern filters, rollback identities, and partial-UAT boundaries are owned.`)
