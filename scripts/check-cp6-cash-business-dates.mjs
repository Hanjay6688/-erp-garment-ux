import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'

const read = p => readFileSync(p, 'utf8')
const hash = s => createHash('sha256').update(s).digest('hex')
const migrationPath = 'supabase/migrations/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.sql'
const rollbackPath = 'supabase/rollbacks/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.rollback.sql'
const migration = read(migrationPath), rollback = read(rollbackPath)
assert.equal(hash(migration), 'ac67472cc35a0a8f9e26e29887055711e3b836491c2f3b11354068844d04bffa')
assert.equal(Buffer.byteLength(migration), 32021)
assert.equal(hash(rollback), '7af2d56c8df366cb117e90edc970c012c736bc31ba4d53c9110d127953d63520')
assert.equal(Buffer.byteLength(rollback), 13892)
const frozen = execFileSync('git', ['diff', '--diff-filter=MDRTCUXB', '--name-only',
  'fa3f76c74b169d4869721a203650be60cd866160', '--', 'supabase/migrations', 'supabase/rollbacks'], { encoding: 'utf8' }).trim()
assert.equal(frozen, '', 'All admitted X business SQL and historical rollbacks must remain byte-identical')
for (const identity of ['post_opening_subledger_settlement(uuid)', 'post_vendor_payment(uuid)',
  'post_sales_payment(uuid)', 'run_v267_financial_truth_checks()',
  '_v268_financial_report_checks_pre_scope()', 'run_v268_financial_report_checks()']) {
  assert.ok(migration.includes(`erp.${identity}`), identity)
  assert.ok(rollback.includes(`erp.${identity}`), identity)
}
for (const token of ['Y_REQUIRES_EXACT_X_WITHOUT_Y_RESIDUE', 'Y_TRUSTED_X_CAPSULE_MISMATCH',
  'Y_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH', 'Y_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH',
  'Y_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED', 'Y_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED',
  'erp._cp3_business_date(p.payment_date)', 'erp._cp3_business_date(s.physical_at)',
  'erp._cp3_business_date(current_timestamp)', 'f.replaces_payment_id is null',
  'revoke all on erp.cp6_v2620y_rollback_capsule from public,anon,authenticated,service_role;',
  'jsonb_object_keys(v_snapshot))<>210']) assert.ok(migration.includes(token), token)
for (const token of ['Y_POST_USE_ROLLBACK_REFUSED', 'Y_TRUSTED_PREDECESSOR_PIN_MISMATCH',
  'Y_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH', 'jsonb_object_keys(v_expected))<>210',
  'select relation.relname from pg_class relation']) assert.ok(rollback.includes(token), token)
const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
for (const token of [hash(rollback), "'Y': {", "'capsule_count': 6", 'from cp6_v2620y_runtime import verify_extra_objects']) assert.ok(maintenance.includes(token), token)
const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of ['Reproduce all sixteen independent X cash-date failures before Y',
  'Qualify Y atomic admission refusal', 'Apply v2.6.20y canonical cash dates',
  'Prove Y canonical cash dates', 'Prove X internal-role denial',
  'Run post-CP6 real Auth', 'four hundred native schedules',
  'Prove trusted Y capsule before exact Y restore to X', 'Prove trusted X capsule before exact X restore to W']) {
  const at = workflow.indexOf(token)
  assert.ok(at > previous, token)
  previous = at
}
for (const token of ["len(schedules['cases'])==400", "'expected':100,'observed':100",
  "len(y_after['cases'])==45", "len(y_install['cases'])==10", "y_before['qualified_counterexamples']==16",
  "y_before['controls_passed']==19", "y_after['controls_passed']==45", 'CP6_V2620Y_RUNTIME_MANIFEST.json',
  'Y_COMPLETE_X_TABLE_BOUNDARY_RESTORE_MISMATCH', "y_restore['complete_function_count']==533",
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620Y']) assert.ok(workflow.includes(token), token)
for (const path of [migrationPath, rollbackPath, 'scripts/cp6_v2620y_runtime.py',
  'scripts/cp6_v2620y_cash_business_date_regression.py', 'scripts/cp6_v2620y_install_qualification.py',
  'scripts/cp6_v2620y_rollback_guards.py', 'scripts/check-cp6-cash-business-dates.mjs',
  'docs/cp6-y-cash-business-dates.md']) assert.ok(workflow.includes(`            '${path}',`), path)
console.log(JSON.stringify({ status: 'PASS', classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 6, boundary_tables: 210, before_cases: 35, after_cases: 45,
  admission_refusals: 10, maintenance_schedules: 400, writer_body_entries: 100, production_go: false }))
