import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
const read = p => readFileSync(p, 'utf8')
const hash = s => createHash('sha256').update(s).digest('hex')
const migrationPath = 'supabase/migrations/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.rollback.sql'
const migration = read(migrationPath), rollback = read(rollbackPath)
const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
assert.equal(Buffer.byteLength(migration), 23916)
assert.equal(hash(migration), '645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726')
assert.equal(hash(migration.slice(0, -1)), 'e9bc2d59dbd1da0facfaa01d2b955630710258e6b761e3ef114b95fc8c783724')
assert.equal(hash(rollback), '8946f4ca8b75850cb284cee669b609e7e938b6020f4e9fa7a270e9794b2becd8')
for (const sha of ['645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726', 'e9bc2d59dbd1da0facfaa01d2b955630710258e6b761e3ef114b95fc8c783724']) assert.ok(rollback.includes(sha))
for (const sql of [migration, rollback]) {
  assert.match(sql, /^begin;$/m)
  assert.match(sql, /commit;\n$/)
  assert.ok(sql.includes("lock table erp.app_users in access exclusive mode;"))
  assert.ok(sql.includes("lock table erp.idempotency_requests in share row exclusive mode;"))
  assert.ok(sql.includes("pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))"))
}
for (const token of [
  'VENI. VIDI. VICI. ERP.', 'Reliable data adalah DEWA.',
  'alter table erp.cp6_v2620g_rollback_capsule enable row level security;',
  'boundary_snapshot', 'string_agg(row_hash', 'opening_hpp_corrections',
  'v_debits:=v_debits+round(v_value,2);', 'v_credits:=v_credits+round(v_value,2);',
  'OPENING_SOURCE_CHANGE_NOT_EXACT', 'OPENING_HPP_SOURCE_V2620G',
  'perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);',
  'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH', 'source.valid_sources<>1',
  "s.contractor_id is not distinct from po.contractor_id",
  'r.qty_pcs=dl.qty_sent_pcs and r.qty_pcs=s.qty_pcs',
  'source.source_qty-inverse.inverse_qty',
  "(select count(*) from erp.cp6_v2620g_rollback_capsule)<>7",
]) assert.ok(migration.includes(token), 'G missing contract: ' + token)
assert.doesNotMatch(migration, /\b(?:delete from|truncate|drop table)\b/i)
assert.doesNotMatch(rollback, /delete from erp\.(?:fg_|sales_|sale_|journal_|hpp_|opening_|wip_)/i)
const test = read('supabase/tests/cp6_independent_n_regression.sql')
for (const name of ['g_n01_split_loss', 'g_n01_gain_lumped', 'g_n02_multiline',
  'g_n02_corrected_loss', 'g_n02_zero_minor_units', 'g_n03_source_detector',
  'g_n01_threshold_matrix', 'g_n02_reserved_reprice']) {
  assert.ok(test.includes('function pg_temp.' + name + '()'))
  assert.ok(read('scripts/cp6_v2620g_independent_regression.py').includes("'" + name + "'"))
}
assert.ok(test.includes('.0129'))
assert.ok(test.includes('source_and_inverse_qty'))
assert.ok(test.includes('post deducted reserved stock twice'))
const order = [
  'Apply v2.6.20f A01-A04', 'Apply v2.6.20g independent N01-N03',
  'Apply v2.6.20h expanded R01-R03',
  'Apply v2.6.20i H2 audit closure',
  'Apply v2.6.20j immutable payment facts',
  'Run post-CP6 real Auth', 'Run thirty-four native CP6 races',
  'Prove native G N01-N03', 'Prove native H R02-R03',
  'Prove native I H2 payment lineage',
  'Qualify exact F G H I J K L M N O P Q R S T and U rollback under closed admission',
  'Prove trusted J capsule and maintenance-only exact J restore to I',
  'Prove trusted F G H I capsules and maintenance-only exact I restore to H',
  'Prove H guards and maintenance-only exact six-function',
  'Prove G guards and exact seven-function',
]
let previous = -1
for (const token of order) {
  const position = workflow.indexOf(token)
  assert.ok(position > previous, 'Wrong installed-runtime order: ' + token)
  previous = position
}
assert.ok(workflow.includes('CP6_V2620U_RUNTIME_MANIFEST.json'))
assert.ok(workflow.includes("runtime=v2.6.20e+v2.6.20f+v2.6.20g+v2.6.20h+v2.6.20i+v2.6.20j"))
assert.ok(workflow.includes("name: cp6-r1-v2620u-full-schema-auth-browser-proof"))
assert.ok(read('scripts/cp6_auth_permission_e2e.mjs').includes('AFTER_V2620U'))
const races = read('scripts/cp6_v2620g_expanded_rollback_races.py')
for (const token of ['pg_blocking_pids', 'WRITER_FIRST', 'ROLLBACK_FIRST', 'WRITER_ABORT',
  'ROLLBACK_LOCK_TIMEOUT', 'SALE', 'RETURN', 'CONVERSION', 'REPORT', 'FK_SYNC',
  "len(report['cases']) != 40", "'manual_writer_prelock': False",
  'function_hash_observations', 'remaining_clone_databases', 'FK_SYNC did not exercise']) {
  assert.ok(races.includes(token), 'Incomplete native rollback harness: ' + token)
}
console.log('CP6 G source contracts passed: N01-N03, exact source-basis corrections, seven-function rollback capsule, and final-G native proof gates. This static check is not runtime evidence.')
