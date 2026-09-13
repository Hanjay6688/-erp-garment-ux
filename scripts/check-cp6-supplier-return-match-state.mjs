import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const read = path => readFileSync(path, 'utf8')
const hash = source => createHash('sha256').update(source).digest('hex')
const name = '20260912051922_erp_v2_6_20p_cp6_supplier_return_match_state'
const migration = read(`supabase/migrations/${name}.sql`)
const rollback = read(`supabase/rollbacks/${name}.rollback.sql`)
const oracle = read('supabase/tests/cp6_supplier_return_match_state.sql')

assert.equal(hash(migration), '109a991d12643ff1c056fd984cea3b3a26bc9fe9d9d716f62c84c4bcb053c138')
assert.equal(hash(rollback), '02f269e031dc6a930c29452742ae13caf81a6c537d999e13d972731b3597290f')
assert.equal(hash(oracle), 'f239ec81369aa4ec204a5ec6aff36eef2edb5ee30c3834960ea8f21fa18b95b3')
for (const token of [
  'P_REQUIRES_EXACT_O_WITHOUT_P_RESIDUE',
  'P_PREEXISTING_RETURN_MATCH_STATE_REVIEW_REQUIRED',
  'perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id)',
  'V2620P_SUPPLIER_RETURN_MATCH_STATE',
  "r.check_name like 'V2620N_%'", "r.check_name like 'V2620O_%'",
  "r.check_name like 'V2620P_%'",
  '17a07e10665756088f2faa0570c055efae4513abf1c5985afacf86bf8467e056',
  '541ce87729dd47bffd536847e71271c1e0b968d199e2fe24fd671a025cee027a',
  '2c546026b1325e265c62828c13f2eea63aaff302c9a359d5f49c18d5fb7a492e',
]) assert.ok(migration.includes(token), token)
for (const token of [
  '(select count(*) from jsonb_object_keys(v_expected))<>66',
  'P_POST_USE_ROLLBACK_REFUSED', 'P_TRUSTED_PREDECESSOR_PIN_MISMATCH',
  '109a991d12643ff1c056fd984cea3b3a26bc9fe9d9d716f62c84c4bcb053c138',
  'b805e85e1c01136cfa299f697ec57d7746b4c1d88c36b3a27cb81f9c0faa2b80',
]) assert.ok(rollback.includes(token), token)

const caseBlock = oracle.slice(
  oracle.indexOf("if p_case='ONE_DOCUMENT_CLOSES_REMAINING_GRNI'"),
  oracle.indexOf("else raise exception 'P_UNKNOWN_CASE"),
)
assert.equal((caseBlock.match(/(?:if|elsif) p_case='[^']+' then/g) ?? []).length, 9)
for (const token of [
  'ONE_DOCUMENT_CLOSES_REMAINING_GRNI', 'TWO_DOCUMENTS_CLOSE_REMAINING_GRNI',
  'RETURN_REVERSE_RESTORE', 'MATCH_STATE_DETECTOR',
  'O_ALLOCATION_DETECTOR_SCOPE', 'KNOWN_O_BUG_REPRODUCED',
]) assert.ok(oracle.includes(token), token)

const runtime = read('scripts/cp6_v2620p_runtime.py')
const oRuntime = read('scripts/cp6_v2620o_runtime.py')
const mRuntime = read('scripts/cp6_v2620m_runtime.py')
const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
for (const token of ['P_SOURCE_PLATFORM_MISMATCH', 'verify_extra_objects',
  'P_CENT_FACT_SECURITY_MISMATCH']) assert.ok(runtime.includes(token), token)
assert.ok(oRuntime.includes('cp6_v2620p_runtime'))
assert.ok(oRuntime.includes('pre_p_installed_sha256'))
assert.ok(mRuntime.includes('non-overlapping successor edge'))
assert.ok(mRuntime.includes("predecessor_snapshot(cur, 'M', validation_successor)"))
for (const token of ["'P': {", "'P': [", "target_name in {'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U'}"])
  assert.ok(maintenance.includes(token), token)

const guards = read('scripts/cp6_v2620p_rollback_guards.py')
for (const token of ['coherent_capsule_and_checksum', 'helper_definition',
  'fact_trigger', 'verify_extra_preflight_guards', 'datallowconn',
  "target_name='P'", 'matrix.legacy.drop_clone()']) assert.ok(guards.includes(token), token)

const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of [
  'Apply v2.6.20o cumulative supplier return document allocation',
  'Reproduce independent O supplier return match and report scope',
  'Apply v2.6.20p supplier return match state and report scope',
  'Run post-CP6 real Auth',
  'Prove native O supplier return document allocation',
  'Prove native P supplier return match state',
  'Qualify exact F G H I J K L M N O P Q R S T and U rollback',
  'Prove trusted P capsule', 'Prove trusted O capsule',
]) {
  const position = workflow.indexOf(token)
  assert.ok(position > previous, token)
  previous = position
}
for (const token of [
  "len(schedules['cases'])==320", "'expected':80,'observed':80",
  "setup_unit['completed_case_count']==setup_unit['expected_case_count']==151",
  "p['runtime']['verified_m_functions']==p_before['runtime']['verified_m_functions']==15",
  "sum(c['upgrade_guard']['invalid_history_refused'] for c in p_before['cases'].values())==3",
  'CP6_V2620P_SUPPLIER_RETURN_MATCH_STATE_REGRESSION.json',
  'CP6_V2620P_ROLLBACK_GUARDS.json',
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620U',
  'CP6_M_RACE_SOURCE_GENERATION: U',
  "'format':'CP6_V2620U_RUNTIME_PROOF_V1'",
  'name: cp6-r1-v2620u-full-schema-auth-browser-proof',
]) assert.ok(workflow.includes(token), token)

for (const path of [
  'docs/cp6-p-supplier-return-match-state.md',
  'scripts/check-cp6-supplier-return-match-state.mjs',
  'scripts/cp6_v2620p_runtime.py',
  'scripts/cp6_v2620p_supplier_return_match_state_regression.py',
  'scripts/cp6_v2620p_rollback_guards.py',
  `supabase/migrations/${name}.sql`,
  `supabase/rollbacks/${name}.rollback.sql`,
  'supabase/tests/cp6_supplier_return_match_state.sql',
]) assert.ok(workflow.includes(`            '${path}',`), `source inventory: ${path}`)

console.log(JSON.stringify({
  status: 'PASS', classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 3, boundary_tables: 66,
  native_cases: 9, known_o_failures: 5, controls: 4,
  maintenance_schedules: 320, writer_body_entries: 80,
  production_go: false,
}))
