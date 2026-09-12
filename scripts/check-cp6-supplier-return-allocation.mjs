import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const read = path => readFileSync(path, 'utf8')
const hash = source => createHash('sha256').update(source).digest('hex')
const name = '20260911165255_erp_v2_6_20o_cp6_supplier_return_document_allocation'
const migration = read(`supabase/migrations/${name}.sql`)
const rollback = read(`supabase/rollbacks/${name}.rollback.sql`)
const oracle = read('supabase/tests/cp6_supplier_return_document_allocation.sql')

assert.equal(hash(migration), '9399b7b8d397165d76e0a87dfcb2bf5efeae82f7930bd8ce3449a004c7ed734b')
assert.equal(hash(rollback), 'a26c3d9869337d874daef0292081a150f543b6f754b899f214ba45cf57c46003')
assert.equal(hash(oracle), '70df272720dfef16ba6544ca718516d5de00e0306402939ed1d452ce44aa489c')
for (const token of [
  'O_REQUIRES_EXACT_N_WITHOUT_O_RESIDUE',
  'O_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED',
  'v_document_ap_qty', 'running_capacity', 'f.recorded_at',
  'V2620O_SUPPLIER_RETURN_ALLOCATION',
  'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
  'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
]) assert.ok(migration.includes(token), token)
for (const token of [
  '(select count(*) from jsonb_object_keys(v_expected))<>65',
  'O_POST_USE_ROLLBACK_REFUSED', 'O_TRUSTED_PREDECESSOR_PIN_MISMATCH',
  '9399b7b8d397165d76e0a87dfcb2bf5efeae82f7930bd8ce3449a004c7ed734b',
  '72653dc66bd04ebecef31aa860c211e06a7289aea2124e8a0d446efcf60d3b8d',
]) assert.ok(rollback.includes(token), token)

const caseBlock = oracle.slice(
  oracle.indexOf("if p_case='NO_INVOICE_TWO_ROLL_FULL'"),
  oracle.indexOf("else\n    raise exception 'O_UNKNOWN_ORACLE_CASE"),
)
assert.equal((caseBlock.match(/(?:if|elsif) p_case='[^']+' then/g) ?? []).length, 18)
for (const token of [
  'LOW_CREDIT_SILENT_MISPOST', 'LOW_CREDIT_PAYMENT_CAPACITY',
  'LATE_INVOICE_LAUNDER', 'FRACTIONAL_QUANTITY',
  'KNOWN_N_BUG_REPRODUCED', 'N_LATE_INVOICE_LAUNDER_NOT_REPRODUCED',
  'O_LATE_INVOICE_CAPACITY_NOT_ATOMIC',
]) assert.ok(oracle.includes(token), token)

const runtime = read('scripts/cp6_v2620o_runtime.py')
const nRuntime = read('scripts/cp6_v2620n_runtime.py')
const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
for (const token of ['O_SOURCE_PLATFORM_MISMATCH', 'verify_extra_objects',
  'O_CENT_FACT_SECURITY_MISMATCH']) assert.ok(runtime.includes(token), token)
assert.ok(nRuntime.includes('cp6_v2620o_runtime'))
assert.ok(nRuntime.includes('pre_o_installed_sha256'))
for (const token of ["'O': {", "'O': [", "target_name in {'N', 'O', 'P', 'Q', 'R'}"])
  assert.ok(maintenance.includes(token), token)

const guards = read('scripts/cp6_v2620o_rollback_guards.py')
for (const token of ['coherent_capsule_and_checksum', 'helper_definition',
  'fact_trigger', 'verify_extra_preflight_guards', 'datallowconn',
  "target_name='O'", 'matrix.legacy.drop_clone()']) assert.ok(guards.includes(token), token)

const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of [
  'Apply v2.6.20n cumulative supplier cent',
  'Reproduce independent N supplier return document allocation',
  'Apply v2.6.20o cumulative supplier return document allocation',
  'Run post-CP6 real Auth',
  'Prove native N supplier cumulative cents',
  'Prove native O supplier return document allocation',
  'Qualify exact F G H I J K L M N O P Q and R rollback',
  'Prove trusted O capsule', 'Prove trusted N capsule',
]) {
  const position = workflow.indexOf(token)
  assert.ok(position > previous, token)
  previous = position
}
for (const token of [
  "len(schedules['cases'])==260", "'expected':65,'observed':65",
  "setup_unit['completed_case_count']==setup_unit['expected_case_count']==103",
  'CP6_V2620O_SUPPLIER_RETURN_REGRESSION.json',
  'CP6_V2620O_ROLLBACK_GUARDS.json',
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620R',
  'CP6_M_RACE_SOURCE_GENERATION: R',
]) assert.ok(workflow.includes(token), token)

for (const path of [
  'docs/cp6-o-supplier-return-document-allocation.md',
  'scripts/check-cp6-supplier-return-allocation.mjs',
  'scripts/cp6_v2620o_runtime.py',
  'scripts/cp6_v2620o_supplier_return_regression.py',
  'scripts/cp6_v2620o_rollback_guards.py',
  `supabase/migrations/${name}.sql`,
  `supabase/rollbacks/${name}.rollback.sql`,
  'supabase/tests/cp6_supplier_return_document_allocation.sql',
]) assert.ok(workflow.includes(`            '${path}',`), `source inventory: ${path}`)

console.log(JSON.stringify({
  status: 'PASS',
  classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 2, boundary_tables: 65,
  native_cases: 18, known_n_failures: 11, controls: 7,
  production_go: false,
}))
