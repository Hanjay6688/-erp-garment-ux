import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1
const requireTokens = (source, label, tokens) => {
  for (const token of tokens) {
    assert.ok(source.includes(token), `${label} missing: ${token}`)
  }
}

const migrationPath =
  'supabase/migrations/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql'
const rollbackPath =
  'supabase/rollbacks/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.rollback.sql'
const regressionPath = 'scripts/cp6_v2620f_final_runtime_regression.py'
const rollbackRacePath = 'scripts/run_cp6_v2620f_live_rollback_races.sh'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const authPath = 'scripts/cp6_auth_permission_e2e.mjs'
const packagePath = 'package.json'

const migration = read(migrationPath)
const rollback = read(rollbackPath)
const regression = read(regressionPath)
const rollbackRace = read(rollbackRacePath)
const workflow = read(workflowPath)
const auth = read(authPath)
const packageSource = read(packagePath)

const migrationBytes = 64730
const rollbackBytes = 10780
const regressionBytes = 18075
const rollbackRaceBytes = 5564
const migrationFileSha =
  '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c'
const migrationLedgerSha =
  '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae'
const rollbackFileSha =
  '83819e093d1489af70431704c59e2cb50a0149e1adc8520d5b9536510572a23d'
const regressionFileSha =
  '4656b11baaa1b14808d9fc5dbefeb262be58027bcc11bf64307df311a46e1c49'
const rollbackRaceFileSha =
  '41a612d39862c9254f6f555028e46f8e8acb242869d9c75e6efb5336c8e71006'

assert.equal(Buffer.byteLength(migration), migrationBytes)
assert.equal(Buffer.byteLength(rollback), rollbackBytes)
assert.equal(Buffer.byteLength(regression), regressionBytes)
assert.equal(Buffer.byteLength(rollbackRace), rollbackRaceBytes)
assert.equal(sha256(migration), migrationFileSha)
assert.equal(sha256(Buffer.from(migration).subarray(0, -1)), migrationLedgerSha)
assert.equal(sha256(rollback), rollbackFileSha)
assert.equal(sha256(regression), regressionFileSha)
assert.equal(sha256(rollbackRace), rollbackRaceFileSha)
assert.equal(occurrences(rollback, migrationFileSha), 4)
assert.equal(occurrences(rollback, migrationLedgerSha), 4)
assert.ok(occurrences(workflow, migrationFileSha) >= 1)
assert.ok(occurrences(workflow, migrationLedgerSha) >= 1)
assert.ok(occurrences(workflow, rollbackFileSha) >= 1)

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain its terminal LF`)
  const quoteCounts = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quoteCounts.set(match[0], (quoteCounts.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual(
    [...quoteCounts].filter(([, count]) => count % 2),
    [],
    `${path} has unbalanced dollar quotes`,
  )
  assert.match(sql, /^begin;$/mi, `${path} must open one transaction`)
  assert.match(sql, /\bcommit;\s*$/i, `${path} must commit at EOF`)
}

assert.deepEqual(
  readdirSync(resolve(root, 'supabase/migrations'))
    .filter((name) => name.startsWith('20260909174713_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/rollbacks'))
    .filter((name) => name.startsWith('20260909174713_')),
  [rollbackPath.split('/').at(-1)],
)
assert.doesNotMatch(
  migration,
  /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i,
)
assert.equal(
  occurrences(migration, 'delete from erp.product_conversion_allocations where conversion_id=h.id;'),
  1,
  'Only the inherited DRAFT-conversion allocation reset may delete a runtime row',
)
assert.equal(occurrences(migration.toLowerCase(), 'delete from '), 1)

requireTokens(migration, 'exact E boundary and rollback capsule', [
  'VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.',
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20e'", "version='v2.6.20f'",
  '8afd32e941cca025be6d68b70e1a483d98984d697b7d1da0e3d6722c423ecfdc',
  '7937cde99aa9d77e5e3d987a803fd9c11f9a4aedc61e16fdd8307849c4fe3ad2',
  'create table erp.cp6_v2620f_rollback_capsule(',
  '(select count(*) from erp.cp6_v2620f_rollback_capsule)<>8',
  'installed_definition_sha256',
])
for (const predecessorSha of [
  '77b5b531d484bcb4c1532e529e8b5269f1afab438ca16d0b1dc7f0f143efc53e',
  '15d8d2a4fceafe70105aa1a4f97dc08ce67571001c965dbc50f0c39310e37296',
  'c80f9ff4a047c7232a3bb224cccdfd9e947d38ffe8ef46b9ef9457fa43fb0e4d',
  '96e5eec137b2eee4b16dd3df6aad69c084935521dfa851bf106ef0bab2239ca4',
  'd83e9f58406528fd3777b348cf71fc7521de853c6c31c1ed668f7f3e46c2d755',
  'ec522f0eeabac729590e45360752db6d0fa021e51716289a59be65856adb6cfd',
  '8678a986758185dd489379321f4e2525187252d0108cd7fc2930121da8324175',
  '5d06a5d87aecd59f6a069a2d2ad3663859787dfe5b9e4ecd4922e1f7b2e28c6e',
]) {
  assert.equal(
    occurrences(migration, predecessorSha),
    1,
    `Predecessor function SHA must be pinned exactly once: ${predecessorSha}`,
  )
}

requireTokens(migration, 'A01 conversion value conservation', [
  "fl.lot_origin='PRODUCTION'",
  "fl.lot_origin in('PRODUCTION','CONVERSION')",
  'select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric',
  'Root-to-leaf propagated source HPP through SKU conversion',
  "perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))",
  'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW',
  "true,'CONVERSION',r.id",
  'perform erp.propagate_conversion_hpp_for_po(v_po);',
  'perform erp.assert_po_hpp_target_book_v2620e(v_po);',
  "'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH'",
  'a.conversion_cost_allocated/nullif(a.qty_pcs,0)',
])

requireTokens(migration, 'A02 cumulative non-PO minor units', [
  'create function erp.compute_non_po_product_hpp_targets_v2620f',
  'create function erp.compute_non_po_product_hpp_book_v2620f',
  'create function erp.assert_non_po_product_hpp_target_book_v2620f',
  'create function erp.sync_non_po_product_hpp_to_gl_v2620f',
  'round(b.raw_total,2)::numeric hpp',
  'round(b.raw_total-greatest(b.owned_qty,0)*b.hpp_per_pcs,2)::numeric total_out',
  "e.source_type<>'PRODUCT_CONVERSION'",
  "'NON_PO_HPP_GL_SYNC_V2620F'",
  'check(fg_delta+cogs_delta+other_delta=0)',
  "message='NON_PO_HPP_GL_SYNC_EVENT_IS_APPEND_ONLY'",
  "'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH'",
])
assert.equal(
  occurrences(migration, 'perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);'),
  6,
  'Sale and return must install pre/post asserts and both reversals must pre-assert',
)
assert.equal(
  occurrences(migration, 'perform erp.sync_non_po_product_hpp_to_gl_v2620f('),
  3,
  'Both reversals and forward reconciliation must use the append-only synchronizer',
)

requireTokens(migration, 'A03 custody-safe financial reversal', [
  "fr.status in('POSTED','REVERSED')",
  "rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'",
  "rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'",
  'rv.qty_pcs=f.qty_attempted_pcs',
  "src.source_type='LAUNDRY_DELIVERY_LINE'",
  'rv.physical_at<=dd.physical_at',
  'redispatch custody receipt anchors are not exact',
])
assert.equal(
  occurrences(migration, "v_anchor:=$anchor$join erp.laundry_receipts fr on fr.id=f.receipt_id and fr.status='POSTED'$anchor$;"),
  1,
)

requireTokens(migration, 'private install and forward reconciliation', [
  'alter table erp.non_po_hpp_gl_sync_events_v2620f enable row level security;',
  'from public,anon,authenticated,service_role;',
  'where has_function_privilege(r.role_name,f.identity,\'EXECUTE\')',
  'Forward-only reconciliation of cumulative non-PO minor-unit targets',
  'ERP v2.6.20f targeted reconciliation still has % issue(s)',
  "'v2.6.20f',",
])

requireTokens(rollback, 'reviewed F rollback', [
  'v2.6.20f rollback refused: platform ledger identity is ambiguous',
  'v2.6.20f rollback refused: a successor migration is already installed',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20f installed object/capsule drift',
  'v2.6.20f rollback refused: post-install reconciliation or business history exists',
  'lock table erp.app_users in access exclusive mode;',
  'lock table erp.idempotency_requests in share row exclusive mode;',
  'lock table erp.products, erp.journal_entries in access exclusive mode;',
  'select * from erp.cp6_v2620f_rollback_capsule order by object_identity',
  "execute format('alter function %s owner to %I'",
  "execute format('grant execute on function %s to %s%s'",
  'drop table erp.non_po_hpp_gl_sync_events_v2620f;',
  'drop table erp.cp6_v2620f_rollback_capsule;',
  "delete from erp.schema_migrations where version='v2.6.20f';",
  'v2.6.20f rollback postcondition failed',
])
assert.doesNotMatch(
  rollback,
  /delete\s+from\s+erp\.(?:journal_|fg_|hpp_|sales_|sale_|product_|laundry_|wip_)/i,
  'Rollback must refuse post-use instead of deleting business history',
)

requireTokens(regression, 'native A01-A03 regression', [
  "'boundary': 'CP6_V2620F_A01_A03_FINAL_RUNTIME_NATIVE_POSTGRESQL'",
  "'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_REGRESSION_AFTER_E_AND_F'",
  "'runtime_versions': ['v2.6.20e', 'v2.6.20f']",
  'def case_a01(', 'def case_a02(', 'def case_a03(',
  "base.fresh(cur, 'a')", "base.fresh(cur, 'b')",
  "return_product_id = base.create_product(cur, 'F-A02-RETURNS')",
  'return_opening_id = create_opening(cur, return_product_id)',
  "Decimal('60'), Decimal('40'), Decimal('0')",
  "Decimal('0.11'), Decimal('0'), Decimal('0.11'), Decimal('0')",
  "'sale_reversal_order': [4, 0, 8, 2, 6, 1, 9, 3, 7, 5]",
  "'return_reversal_order': [5, 1, 9, 3, 7, 0, 8, 2, 6, 4]",
  "'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL', 'LAUNDRY', 'SEWING', 10, True",
  "cur.execute(f'rollback to savepoint {savepoint}')",
  "'production_go': False",
])
assert.doesNotMatch(
  regression,
  /base\.fresh\(cur,\s*'[0-9a-f]{2,}'\)/i,
  'Native fixture tags must keep generated UUID prefixes exactly eight characters',
)

requireTokens(rollbackRace, 'actual F rollback races', [
  'prepare_clone V2620F_WRITER_FIRST_BOUNDARY',
  'prepare_clone V2620F_ROLLBACK_FIRST_BOUNDARY',
  "CP6_ROLLBACK_TARGET_VERSION='v2.6.20f'",
  "CP6_ROLLBACK_PREDECESSOR_VERSION='v2.6.20e'",
  "CP6_ROLLBACK_TARGET_REG_IDENTITY='erp.non_po_hpp_gl_sync_events_v2620f'",
  "CP6_ROLLBACK_GATE_RELATION='erp.wip_stage_events'",
  "assert writer['actual_facade']=='public.erp_save_laundry_qc_action_v1'",
  "assert writer['rollback_refused_post_use'] is True",
  "assert rollback['writer_blocked_by_exact_rollback_pid'] is True",
  "assert rollback['pre_use_rollback_committed'] is True",
  "assert rollback['writer_committed_under_restored_predecessor']=='v2.6.20e'",
  'V2620F_LIVE_ROLLBACK_CLONE_CLEANUP.txt',
])
assert.match(
  rollback,
  /erp\.laundry_failed_wash_batch_size_lines,\s*erp\.wip_stage_events\s*in share row exclusive mode;/,
  'Rollback race gate must remain the final table after every earlier business lock',
)

const orderedWorkflowTokens = [
  'Apply v2.6.20e C01-C06 counterexample closure before final-runtime tests',
  'Apply v2.6.20f A01-A04 final-runtime reliability closure once and reject replay',
  'Run post-CP6 real Auth JWT HTTP permissions and residue-zero E2E',
  'Run CP6 physical lineage, finance, stock, HPP, idempotency, and reversal acceptance',
  'Run thirty-four native CP6 races plus three abort qualifications, temporal, paging, and scale proofs',
  'Re-run affected CP5, Cutting, partial-FG, HPP, and accounting behavior under CP6',
  'Confirm every broad regression ran on the installed E through R runtime',
  'Re-prove native C01-C06 business closure under final E plus F runtime',
  'Prove native A01-A03 closure under the exact final E plus F runtime',
  'Qualify exact F G H I J K L M N O P Q and R rollback under closed admission across two hundred sixty native schedules',
  'Prove v2.6.20f guards and exact pre-use rollback before v2.6.20e',
  'Prove v2.6.20e pre-use rollback before the v2.6.20d ladder',
]
let priorIndex = -1
for (const token of orderedWorkflowTokens) {
  const index = workflow.indexOf(token)
  assert.ok(index > priorIndex, `Workflow runtime order is wrong or missing: ${token}`)
  priorIndex = index
}
assert.equal(occurrences(workflow, orderedWorkflowTokens[0]), 1)
assert.equal(occurrences(workflow, orderedWorkflowTokens[1]), 1)

requireTokens(workflow, 'A04 exact final-runtime proof', [
  'python -m py_compile scripts/cp6_v2620f_final_runtime_regression.py',
  'bash -n scripts/run_cp6_v2620f_live_rollback_races.sh',
  'python scripts/cp6_v2620f_final_runtime_regression.py',
  'V2620F_A01_A03_NATIVE.log',
  'V2620F_FINAL_RUNTIME_COVERAGE.txt',
  'runtime=v2.6.20e+v2.6.20f',
  'native_races=34',
  'V2620F_INSTALLED_FUNCTION_SHA256.txt',
  'V2620H_MAINTENANCE_ROLLBACK_MATRIX.log',
  'H_MAINTENANCE_ROLLBACK/manifest.json',
  "'format':'CP6_V2620N_RUNTIME_PROOF_V1'",
  "'actual_business_facade_rollback_race_orders':6",
  "'v2620f_rollback_race_orders':20",
  "'v2620f_counterexamples_a01_a03':3",
  "'v2620f_auth_acceptance_races_and_cp5_after_final_runtime':True",
  "'v2620f_installed_function_hashes_bound':True",
  "proof/'CP6_V2620R_RUNTIME_MANIFEST.json'",
  'name: cp6-r1-v2620r-full-schema-auth-browser-proof',
  "'uat_v2620e_v2620f_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'production_go':False",
])
requireTokens(workflow, 'F source and residue binding', [
  `'${migrationPath}'`, `'${rollbackPath}'`, `'${regressionPath}'`,
  `'${rollbackRacePath}'`, "'scripts/check-cp6-final-runtime-reliability.mjs'",
  "to_regclass('erp.cp6_v2620f_rollback_capsule') is null",
  "to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is null",
  "to_regprocedure('erp.compute_non_po_product_hpp_targets_v2620f(uuid)') is null",
  "where name='erp_v2_6_20f_cp6_final_runtime_reliability'",
])

requireTokens(auth, 'Auth proof target', [
  "target: 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620R'",
  'production_go: false',
])
requireTokens(packageSource, 'static gate wiring', [
  'node scripts/check-cp6-final-runtime-reliability.mjs',
  '"check:cp6:final-runtime"',
])

console.log(JSON.stringify({
  status: 'PASS',
  boundary: 'CP6_V2620F_A01_A04_FINAL_RUNTIME_RELIABILITY',
  migration_sha256: migrationFileSha,
  migration_ledger_sha256: migrationLedgerSha,
  rollback_sha256: rollbackFileSha,
  regression_sha256: regressionFileSha,
  rollback_race_sha256: rollbackRaceFileSha,
  production_go: false,
}))
