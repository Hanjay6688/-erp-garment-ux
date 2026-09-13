import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const read = path => readFileSync(path, 'utf8')
const hash = source => createHash('sha256').update(source).digest('hex')
const name = '20260911124328_erp_v2_6_20n_cp6_supplier_cent_lifecycle'
const migration = read(`supabase/migrations/${name}.sql`)
const rollback = read(`supabase/rollbacks/${name}.rollback.sql`)
assert.equal(hash(migration), '4b351432f4ddd8781f42c3c194b78fc575257e3a5fd60753e310c9928590b21e')
assert.equal(hash(rollback), '29f52100d28779112638bd7bc95b0ffb7dd5ec17c83dc140e79b2f18e2fe3dda')
assert.equal((migration.match(/CREATE OR REPLACE FUNCTION erp\./g) ?? []).length, 7)
assert.equal((migration.match(/create function erp\._cp6_/g) ?? []).length, 3)
for (const token of ['N_PREDECESSOR_M_CAPSULE_MISMATCH', 'N_PREEXISTING_SUPPLIER_REVIEW_REQUIRED',
  'supplier_cent_posting_facts', 'CENT_INVERSE:',
  'V2620N_SUPPLIER_CENT_FACT_LEDGER', 'N_INHERITED_FACT_GUARD_MISMATCH']) {
  assert.ok(migration.includes(token), token)
}
for (const token of ['(select count(*) from jsonb_object_keys(v_expected))<>64',
  'N_POST_USE_ROLLBACK_REFUSED', 'N_EXTRA_FUNCTION_OWNER_ACL_MISMATCH',
  'N_CENT_FACT_SECURITY_MISMATCH', 'N_INHERITED_FACT_GUARD_MISMATCH']) {
  assert.ok(rollback.includes(token), token)
}
const runtime = read('scripts/cp6_v2620n_runtime.py')
const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
assert.ok(runtime.includes('N_SOURCE_PLATFORM_MISMATCH'))
assert.ok(runtime.includes('INHERITED_FACT_GUARD'))
assert.ok(maintenance.includes('verify_extra_objects(extra_cur)'))
assert.ok(read('scripts/cp6_v2620m_runtime.py').includes('cp6_v2620n_runtime'))
const guards = read('scripts/cp6_v2620n_rollback_guards.py')
for (const token of ['helper_definition', 'helper_acl', 'fact_trigger', 'fact_grant',
  'inherited_fact_guard', 'verify_extra_preflight_guards', 'datallowconn', 'matrix.legacy.drop_clone()']) {
  assert.ok(guards.includes(token), token)
}
const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of ['Apply v2.6.20m exact supplier', 'Reproduce independent M supplier cent',
  'Apply v2.6.20n cumulative supplier cent', 'Run post-CP6 real Auth',
  'Prove native M exact supplier', 'Prove native N supplier cumulative cents',
  'Qualify exact F G H I J K L M N O P Q R S T and U rollback', 'Prove trusted N capsule', 'Prove trusted M capsule']) {
  const position = workflow.indexOf(token)
  assert.ok(position > previous, token); previous = position
}
for (const token of ["len(n_before['cases'])==5", "len(n['cases'])==15",
  "len(ng['guards'])==12", "len(ng['extra_object_preflight_guards'])==5",
  "len(schedules['cases'])==320", "'expected':80,'observed':80",
  'CP6_V2620U_RUNTIME_MANIFEST.json', 'cp6-r1-v2620u-full-schema-auth-browser-proof']) {
  assert.ok(workflow.includes(token), token)
}
const install = workflow.slice(workflow.indexOf('- name: Install validation runtime'), workflow.indexOf('- name:', workflow.indexOf('- name: Install validation runtime') + 8))
assert.ok(install.includes(`test "$(jq '.completed_case_count' cp6-proof/CP6_ROLLBACK_SETUP_UNIT.json)" = '151'`))
assert.ok(workflow.includes('CP6_M_RACE_SOURCE_GENERATION: U'))
assert.ok(workflow.includes("mr['source_generation']=='U'"))
const auth = read('scripts/cp6_auth_permission_e2e.mjs')
assert.ok(auth.includes('PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620U'))
assert.ok(workflow.includes("report['target']=='PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620U'"))
for (const path of [`supabase/migrations/${name}.sql`, `supabase/rollbacks/${name}.rollback.sql`,
  'supabase/tests/cp6_supplier_cent_lifecycle.sql', 'scripts/cp6_v2620n_runtime.py',
  'scripts/cp6_v2620n_supplier_cent_regression.py', 'scripts/cp6_v2620n_rollback_guards.py',
  'scripts/check-cp6-supplier-cent-lifecycle.mjs']) {
  assert.ok(workflow.includes(`            '${path}',`), `source inventory: ${path}`)
}
console.log(JSON.stringify({ status: 'PASS', classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 7, private_helpers: 3, boundary_tables: 64, production_go: false }))
