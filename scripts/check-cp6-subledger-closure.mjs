import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'

const read = path => readFileSync(path, 'utf8')
const hash = source => createHash('sha256').update(source).digest('hex')
const name = '20260911092622_erp_v2_6_20m_cp6_subledger_exact_cent_closure'
const migration = read(`supabase/migrations/${name}.sql`)
const rollback = read(`supabase/rollbacks/${name}.rollback.sql`)
assert.equal(hash(migration), 'c5404de584a4734fb235f5253f10fb10a1d13f01f3f993b99150a422008e2268')
assert.equal(hash(rollback), '1bf669e82c46fe3fa7e8d007800657c6f30c13445f301960aec78154c970b5ac')
assert.equal((migration.match(/CREATE OR REPLACE FUNCTION erp\./g) ?? []).length, 15)
assert.ok(rollback.includes('(select count(*) from jsonb_object_keys(v_expected))<>58'))
for (const token of ['M_PREDECESSOR_L_CAPSULE_SOURCE_PIN_MISMATCH',
  'M_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH', 'M_PREEXISTING_SUBLEDGER_REVIEW_REQUIRED',
  'opening_subledger_balances', 'round(erp.material_purchase_final_ap_total']) {
  assert.ok(migration.includes(token), token)
}
assert.doesNotMatch(rollback, /\b(?:delete from|drop table|truncate) erp\.(?:sales_|journal_|wip_|fg_|laundry_|opening_|supplier_|material_)/i)
const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const name of ['Apply v2.6.20l exact ledger', 'Reproduce independent L supplier',
  'Apply v2.6.20m exact supplier', 'Run post-CP6 real Auth', 'Prove native L exact money',
  'Prove native M exact supplier', 'Prove native M supplier payment',
  'Qualify exact F G H I J K L M N O P Q R and S rollback', 'Prove trusted M capsule', 'Prove trusted L capsule']) {
  const position = workflow.indexOf(name)
  assert.ok(position > previous, name); previous = position
}
for (const token of ['CP6_V2620N_RUNTIME_PROOF_V1', "len(m_before['cases'])==12",
  "len(m['cases'])==20", "len(mr['cases'])==3", "len(schedules['cases'])==280",
  "'expected':70,'observed':70", "'production_go':False"]) assert.ok(workflow.includes(token), token)
const runner = read('scripts/cp6_v2620m_subledger_races.py')
assert.ok(runner.includes('pg_blocking_pids(pid)'))
assert.ok(runner.includes("'select erp.post_supplier_payment(%s)'"))
assert.ok(runner.includes("'select erp.post_opening_subledger_settlement(%s)'"))
assert.ok(runner.includes('matrix.legacy.drop_clone()'))
assert.doesNotMatch(runner, /lock table|pg_advisory.*lock\(/i)
const runtime = read('scripts/cp6_v2620m_runtime.py')
for (const token of ['M_SOURCE_PLATFORM_MISMATCH', 'M_PREDECESSOR_CHAIN_MISMATCH',
  'M_HISTORICAL_CAPSULE_SOURCE_PIN_MISMATCH']) assert.ok(runtime.includes(token), token)
console.log(JSON.stringify({status:'PASS', classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  functions:15, boundary_tables:58, production_go:false}))
