import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'

const read = p => readFileSync(p, 'utf8')
const hash = s => createHash('sha256').update(s).digest('hex')
const migrationPath = 'supabase/migrations/20260914085912_erp_v2_6_20z_cp6_accounting_close_business_date.sql'
const rollbackPath = 'supabase/rollbacks/20260914085912_erp_v2_6_20z_cp6_accounting_close_business_date.rollback.sql'
const migration = read(migrationPath), rollback = read(rollbackPath)
assert.equal(hash(migration), '4811f4ea21b35aac10da02da96bdec34505c619d3daa0b53f64fe22205a2f4a3')
assert.equal(hash(rollback), 'c00029564f0092ebfb8afa9daeb566961af7fe2b6fe8eb800550d1b045896f2f')
const frozen = execFileSync('git', ['diff', '--diff-filter=MDRTCUXB', '--name-only',
  'bde9da786e3cde94cdb96e953310e5fac46f8574', '--', 'supabase/migrations', 'supabase/rollbacks'], { encoding: 'utf8' }).trim()
assert.equal(frozen, '', 'All admitted SQL through Y must remain byte-identical')
for (const token of ['Z_REQUIRES_EXACT_Y_WITHOUT_Z_RESIDUE', 'Z_TRUSTED_Y_PREDECESSOR_PIN_MISMATCH',
  'Z_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH', 'Z_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH',
  'Z_PREEXISTING_PERIOD_CLOSE_REVIEW_REQUIRED', 'p_closed_through>=erp._cp3_business_date(current_timestamp)',
  'jsonb_object_keys(v_snapshot))<>211', 'revoke all on erp.cp6_v2620z_rollback_capsule from public,anon,authenticated,service_role;']) assert.ok(migration.includes(token), token)
for (const token of ['Z_POST_USE_ROLLBACK_REFUSED', 'Z_TRUSTED_PREDECESSOR_PIN_MISMATCH',
  'Z_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH', 'jsonb_object_keys(v_expected))<>211']) assert.ok(rollback.includes(token), token)
const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
for (const token of [hash(rollback), "'Z': {", "'capsule_count': 1", 'from cp6_v2620z_runtime import verify_extra_objects']) assert.ok(maintenance.includes(token), token)
const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of ['Apply v2.6.20y canonical cash dates', 'Reproduce independent Y close counterexamples before installing Z',
  'Qualify Z atomic admission refusals', 'Apply Z canonical accounting-close day',
  'Prove Z closes correct business days', 'Prove Y canonical cash dates', 'Prove X internal-role denial',
  'Run post-CP6 real Auth', 'four hundred sixty native schedules', 'Prove trusted Z capsule before exact Z restore to Y',
  'Prove trusted Y capsule before exact Y restore to X']) {
  const at = workflow.indexOf(token)
  assert.ok(at > previous, token)
  previous = at
}
for (const token of ["len(schedules['cases'])==460", "'expected':115,'observed':115", "z_after['controls_passed']==20",
  "len(z_install['cases'])==10", "z_restore['restored_table_count']==213", 'CP6_V2620AB_RUNTIME_MANIFEST.json',
  'Z_COMPLETE_Y_TABLE_BOUNDARY_RESTORE_MISMATCH', "z_restore['complete_function_count']==533",
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620AB']) assert.ok(workflow.includes(token), token)
assert.ok(workflow.includes("'writer_first_backend_body_entries':schedules['writer_first_body_entry']['observed']"))
const xOracle = read('scripts/cp6_x_independent_audit.py')
for (const token of [migrationPath, rollbackPath, 'INDEPENDENT_REQUIRES_UNCHANGED_ADMITTED_Y_SQL',
  "'--diff-filter=MDRTCUXB'", "phase != 'X_AUDIT'", 'changed - allowed or modified_history']) assert.ok(xOracle.includes(token), token)
for (const path of [migrationPath, rollbackPath, 'scripts/cp6_v2620z_runtime.py', 'scripts/cp6_y_independent_audit.py',
  'scripts/cp6_v2620z_install_qualification.py', 'scripts/cp6_v2620z_rollback_guards.py',
  'scripts/check-cp6-accounting-close-business-date.mjs', 'docs/cp6-z-accounting-close-business-date.md']) assert.ok(workflow.includes(`            '${path}',`), path)
console.log(JSON.stringify({status: 'PASS', classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 1, boundary_tables: 211, before_cases: 20, after_cases: 20,
  admission_refusals: 10, maintenance_schedules: 460, writer_body_entries: 115, production_go: false}))
