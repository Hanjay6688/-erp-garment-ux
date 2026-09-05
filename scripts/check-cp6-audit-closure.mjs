import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1

const oldMigrationPath = 'supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql'
const oldRollbackPath = 'supabase/rollbacks/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.rollback.sql'
const migrationPath = 'supabase/migrations/20260905110913_erp_v2_6_20a_cp6_audit_reliability_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260905110913_erp_v2_6_20a_cp6_audit_reliability_closure.rollback.sql'
const racePath = 'scripts/cp6_laundry_qc_concurrency.py'
const seedPath = 'supabase/tests/cp6_laundry_qc_concurrency_seed.sql'
const authPath = 'scripts/cp6_auth_permission_e2e.mjs'
const scalePath = 'supabase/tests/cp6_workspace_scale_rollback.sql'
const reversalRacePath = 'scripts/cp6_reversal_concurrency_matrix.py'
const reversalSeedPath = 'supabase/tests/cp6_reversal_concurrency_seed.sql'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const modelPath = 'src/laundryQcModel.ts'
const modelTestPath = 'src/laundryQcModel.test.ts'
const laundryPagePath = 'src/ConnectedLaundryPage.tsx'
const qcPagePath = 'src/ConnectedQcFinalPage.tsx'

const oldMigration = read(oldMigrationPath)
const oldRollback = read(oldRollbackPath)
const migration = read(migrationPath)
const rollback = read(rollbackPath)
const race = read(racePath)
const seed = read(seedPath)
const auth = read(authPath)
const scale = read(scalePath)
const reversalRace = read(reversalRacePath)
const reversalSeed = read(reversalSeedPath)
const workflow = read(workflowPath)
const model = read(modelPath)
const modelTest = read(modelTestPath)
const laundryPage = read(laundryPagePath)
const qcPage = read(qcPagePath)

assert.equal(
  sha256(oldMigration),
  '52e51f56f4b8b08b7797b1a92ca9b9e26cbe611e81615c3379c728b95877ada1',
  'Recorded v2.6.20 migration bytes changed; use a forward migration only',
)
assert.equal(Buffer.byteLength(oldMigration), 251923)
assert.ok(oldMigration.endsWith('\n'))

for (const [path, sql] of [
  [migrationPath, migration], [rollbackPath, rollback], [oldRollbackPath, oldRollback],
]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain a terminal LF`)
  const quoteCounts = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quoteCounts.set(match[0], (quoteCounts.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual(
    [...quoteCounts].filter(([, count]) => count % 2 !== 0), [],
    `Unbalanced dollar quote in ${path}`,
  )
  assert.match(sql, /\bbegin;[\s\S]*\bcommit;\s*$/i, `${path} is not one explicit transaction`)
}

const migrationBytes = Buffer.from(migration, 'utf8')
const migrationFileSha = sha256(migrationBytes)
const migrationLedgerSha = sha256(migrationBytes.subarray(0, -1))
assert.equal(migrationBytes.length, 25850, 'v2.6.20a byte count changed; update all exact evidence together')
assert.equal(migrationFileSha, '03e0dcaaafecb9107d08d0c44e55b719fbaed63cd8881872423a0e9457a429cd')
assert.equal(migrationLedgerSha, '1b1b821d0a2d69a653a894c3bb407974c97bef1897d2a0f568d0264270542298')
assert.equal(occurrences(rollback, migrationFileSha), 4)
assert.equal(occurrences(rollback, migrationLedgerSha), 4)

const rollbackBusinessLockStart = rollback.indexOf('lock table\n  erp.audit_logs,')
const rollbackBusinessLockEnd = rollback.indexOf('\nin share row exclusive mode;', rollbackBusinessLockStart)
assert.ok(rollbackBusinessLockStart >= 0 && rollbackBusinessLockEnd > rollbackBusinessLockStart)
const rollbackBusinessLocks = rollback.slice(rollbackBusinessLockStart, rollbackBusinessLockEnd)
for (const relation of [
  'erp.audit_logs', 'erp.idempotency_requests', 'erp.products',
  'erp.vendor_invoices', 'erp.vendor_invoice_items',
  'erp.laundry_deliveries', 'erp.laundry_receipts',
  'erp.qc_inspections', 'erp.qc_inspection_items', 'erp.wip_stage_events',
]) assert.ok(rollbackBusinessLocks.includes(relation),
  `v2.6.20a rollback does not fence counted/writer relation ${relation}`)

const sameTimestampMigrations = readdirSync(resolve(root, 'supabase/migrations'))
  .filter((name) => name.startsWith('20260905110913_'))
const sameTimestampRollbacks = readdirSync(resolve(root, 'supabase/rollbacks'))
  .filter((name) => name.startsWith('20260905110913_'))
assert.deepEqual(sameTimestampMigrations, [migrationPath.split('/').at(-1)])
assert.deepEqual(sameTimestampRollbacks, [rollbackPath.split('/').at(-1)])

assert.doesNotMatch(migration, /\btruncate\b|\bdelete\s+from\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i,
  'Forward audit closure contains a destructive operation')
for (const token of [
  'VENI. VIDI. VICI. ERP. — I CONQUERED ERP.',
  'Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.',
  "version='v2.6.20'", "version='v2.6.20a'",
  "'b2e8ffa3e9caf72aaa101a34bded5001'",
  "'43cec1668118c4a9c30939be72cc45b5'",
  "'c03b264c3e180c5d272f310e9374021a'",
  "'25ac6c923bc0c2ff213a09b541a26b12'",
  'cp6_v2620a_rollback_capsule',
  "count(*) from erp.cp6_v2620a_rollback_capsule)<>4",
  'installed_definition_sha256',
  'idx_laundry_failed_wash_attempts_delivery_v2620a',
  'include(receipt_id,receipt_line_id,custody_outcome,qty_attempted_pcs,return_wip_event_id)',
]) assert.ok(migration.includes(token), `v2.6.20a guard/index token missing: ${token}`)

for (const token of [
  'do $patch_bounded_workspace$', 'v_collection_limit constant integer:=200',
  'v_product_limit constant integer:=500', 'limit v_collection_limit+1',
  'limit v_product_limit+1', "'collection_window',jsonb_build_object(",
  "'query_required_for_more',true", "'products_relevant_to_live_qc',v_scope='QC'",
  "and(v_scope<>'QC' or exists(",
  "'any_truncated',v_products_truncated or v_ready_truncated",
]) assert.ok(migration.includes(token), `Bounded workspace token missing: ${token}`)
assert.ok(occurrences(migration, 'limit v_collection_limit+1') >= 4,
  'Every large transactional workspace collection must be bounded')

const invoicePatchStart = migration.indexOf('do $patch_invoice_lifecycle$')
const invoicePatchEnd = migration.indexOf('$patch_invoice_lifecycle$;', invoicePatchStart + 10)
assert.ok(invoicePatchStart >= 0 && invoicePatchEnd > invoicePatchStart)
const invoicePatch = migration.slice(invoicePatchStart, invoicePatchEnd)
for (const token of [
  "pg_get_functiondef('erp.post_vendor_invoice(uuid)'::regprocedure)",
  "pg_get_functiondef('erp.reverse_vendor_invoice(uuid,text)'::regprocedure)",
  "pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0))",
  'from erp.laundry_receipts lr', 'order by lr.id', 'for update;',
  'from erp.laundry_receipt_lines lrl', 'order by lrl.id',
  'post_vendor_invoice lock anchor is not exact',
  'reverse_vendor_invoice lock anchor is not exact',
]) assert.ok(invoicePatch.includes(token), `Canonical invoice lock proof missing: ${token}`)
assert.equal(occurrences(invoicePatch, "pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0))"), 2)
assert.equal(occurrences(invoicePatch, 'from erp.laundry_receipts lr'), 2)
assert.equal(occurrences(invoicePatch, 'from erp.laundry_receipt_lines lrl'), 2)

const timelinePatchStart = migration.indexOf('do $patch_physical_timeline$')
const timelinePatchEnd = migration.indexOf('$patch_physical_timeline$;', timelinePatchStart + 10)
assert.ok(timelinePatchStart >= 0 && timelinePatchEnd > timelinePatchStart)
const timelinePatch = migration.slice(timelinePatchStart, timelinePatchEnd)
for (const token of [
  "d.status<>'DRAFT' and d.physical_at<=v_physical_at",
  'dispatched_at_prefix', 'returned_at_prefix',
  "rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'",
  "rv.physical_at<=v_physical_at",
  'Laundry redispatch time precedes sufficient linked physical return',
  'CP6 size-prefix anchor is not exact', 'CP6 group-prefix anchor is not exact',
]) assert.ok(timelinePatch.includes(token), `Physical-time prefix guard missing: ${token}`)

for (const token of [
  'v_platform_version text;', 'select m.version into strict v_platform_version',
  'where m.version>v_platform_version', "m.version>'20260904111157'",
]) {
  if (token === "m.version>'20260904111157'") {
    assert.equal(oldRollback.includes(token), false, 'Old rollback still compares against source timestamp')
  } else {
    assert.ok(oldRollback.includes(token), `Portable v2.6.20 rollback token missing: ${token}`)
  }
}

for (const token of [
  'run_invoice_reversal_vs_replacement_post', 'pg_blocking_pids',
  "'prior_status': 'ESTIMATED', 'prior_rate': 7, 'prior_cost': 70",
  'replacement reversal resurrected cancelled cost',
  'run_f02_physical_prefix_proof', 'same_rejected_uuid_attempts',
  "'laundry_at_day_2': 10", "'laundry_at_day_3': 0", "'laundry_at_day_4': 10",
  "'rejected_request_rows': 0",
]) assert.ok(race.includes(token), `Executable F01/F02 proof token missing: ${token}`)
for (const token of ['CP6-F02-PO', 'CP6 F02 physical-prefix terminal', 'Immutable F02 source']) {
  assert.ok(seed.includes(token), `F02 isolated fixture token missing: ${token}`)
}

for (const token of [
  "classification: 'LOCAL_POST_CP6_REAL_AUTH_JWT_HTTP'", 'real_password_sessions_and_bearer_jwt',
  'anonymous_unmapped_inactive_denial', 'viewer_laundry_and_qc_read_only',
  'non_admin_operator_reaches_domain_guard', 'direct_cp6_table_denial',
  'negative_mutation_transaction_residue_zero', 'auth_app_role_audit_idempotency_context_cleanup_zero',
  'confirm_high_risk: true',
  "assert.notEqual(new URL(baseUrl).hostname, 'vlxdhpkjeevubjxexnfo.supabase.co'",
  'production_go: false',
]) assert.ok(auth.includes(token), `Real post-CP6 Auth/JWT proof token missing: ${token}`)

for (const token of [
  'generated_products', 'generated_qc_history', 'jsonb_array_length(v_workspace#>',
  '{collection_window,products_truncated}', '{collection_window,qc_history_truncated}',
  'CP6-SCALE-PRODUCT-0700',
  'idx_laundry_failed_wash_attempts_delivery_v2620a', "'ROLLBACK_ONLY'",
  "'production_go',false", 'rollback;',
]) assert.ok(scale.includes(token), `Rollback-only scale proof token missing: ${token}`)

for (const token of [
  'RECEIPT_FAILED', 'REVDEL_RECEIPT', 'RECEIPT_REVDEL',
  'REVDEL_FAILED', 'FAILED_REVDEL', 'REVRECEIPT_INVOICE',
  'REVRECEIPT_QC', 'REVQC_REVRECEIPT', 'REVQC_INVOICE',
  'INVOICE_REVQC', 'REVQC_INVOICE_REV', 'INVOICE_REV_REVQC',
  'REVQC_POSTQC', 'POSTQC_REVQC',
  'CP6 reversal matrix physical terminal', "<>14",
]) assert.ok(reversalSeed.includes(token), `Reversal race seed token missing: ${token}`)

for (const token of [
  'pg_blocking_pids', 'all_blockers_observed',
  "'post_receipt_vs_failed_wash'", "'reverse_delivery_vs_post_receipt'",
  "'post_receipt_vs_reverse_delivery'", "'reverse_delivery_vs_failed_wash'",
  "'failed_wash_vs_reverse_delivery'", "'reverse_receipt_vs_vendor_invoice'",
  "'reverse_receipt_vs_final_sku'", "'reverse_qc_vs_reverse_receipt'",
  "'reverse_qc_vs_vendor_invoice'", "'vendor_invoice_vs_reverse_qc'",
  "'reverse_qc_vs_vendor_invoice_reversal'", "'vendor_invoice_reversal_vs_reverse_qc'",
  "'reverse_qc_vs_post_final_sku'", "'post_final_sku_vs_reverse_qc'",
  "'rejected_rows': 0", "'execution_context_rows': 0", "'unbalanced_journals': 0",
  "'matrix_vendor_ap': 180", "'production_go': False",
]) assert.ok(reversalRace.includes(token), `Reversal race matrix token missing: ${token}`)
assert.equal(reversalRace.includes('rl.created_at'), false,
  'Reversal matrix must order receipt lines through authoritative receipt physical time')
assert.ok(occurrences(reversalRace, 'order by r.physical_at desc,r.id desc,rl.id desc') >= 2,
  'Reversal matrix receipt-cost snapshots are not deterministically ordered')

for (const token of [
  'collection_window: Cp6CollectionWindow', 'transaction_limit !== 200',
  'product_limit !== 500', 'query_required_for_more !== true',
  'products_relevant_to_live_qc !== (scope === \'QC\')',
]) assert.ok(model.includes(token), `Frontend bounded collection parser token missing: ${token}`)
for (const token of [
  'requires explicit bounded-collection metadata and rejects silent truncation',
  'bounded.ready_batches = Array.from({ length: 200 }',
]) assert.ok(modelTest.includes(token), `Frontend bounded collection test missing: ${token}`)
assert.ok(laundryPage.includes('Hasil yang tampil bukan seluruh histori.'))
assert.ok(qcPage.includes('Merek → Nomor SKU → Model tetap berasal dari sumber QC yang cocok.'))

for (const token of [
  migrationPath, rollbackPath,
  'V2620A_MIGRATION_SHA256.txt', migrationFileSha, migrationLedgerSha,
  'invoice_reversal_vs_replacement_post', 'pg_blocking_pids_observed',
  "report['f02_physical_prefix']['status'] == 'PASS'",
  'V2620A_ROLLBACK_WRONG_NAME_REJECTION.log',
  "version='20260904232442'", 'V2620_ROLLBACK_TRUE_SUCCESSOR_REJECTION.log',
  'V2620_ROLLBACK_WRONG_NAME_REJECTION.log',
  'node scripts/cp6_auth_permission_e2e.mjs', 'CP6_AUTH_REPORT',
  "status_env=\"$(supabase status --workdir cp5-local -o env 2>/dev/null)\"",
  "grep -q '^SERVICE_ROLE_KEY=' <<<\"$status_env\"",
  scalePath, 'CP6_WORKSPACE_SCALE.json', "report['transaction']=='ROLLBACK_ONLY'",
  reversalRacePath, reversalSeedPath, 'CP6_REVERSAL_RACE_REPORT',
  "report['race_count']==14", "report['all_blockers_observed'] is True",
  'Run twenty-six CP6 races plus physical-prefix and scale proofs in an isolated clone',
  "'v2620a',exists(select 1 from erp.schema_migrations where version='v2.6.20a')",
  "'platform_v2620a',exists(select 1 from supabase_migrations.schema_migrations",
  "to_regclass('erp.cp6_v2620a_rollback_capsule') is not null",
  "to_regclass('erp.idx_laundry_failed_wash_attempts_delivery_v2620a') is not null",
]) assert.ok(workflow.includes(token), `Workflow audit-closure proof missing: ${token}`)
assert.ok(
  workflow.indexOf('Apply v2.6.20a audit reliability closure once and reject replay')
    < workflow.indexOf('Run post-CP6 real Auth JWT HTTP permissions and residue-zero E2E'),
  'Real Auth/JWT proof must execute after v2.6.20a is installed',
)

console.log(
  `CP6 audit closure passed: immutable v2.6.20 ${sha256(oldMigration).slice(0, 12)}, `
  + `forward v2.6.20a ${migrationFileSha.slice(0, 12)}, canonical invoice locks, `
  + 'physical-time prefix conservation, indexed dependency lookup, and portable exact rollback are statically owned.',
)
