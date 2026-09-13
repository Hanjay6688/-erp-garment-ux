import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'

const read = path => readFileSync(path, 'utf8')
const hash = source => createHash('sha256').update(source).digest('hex')
const pinned = {
  'supabase/migrations/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.sql':
    '972b5189a065e078590c0742f67722684eb14a1d0df21f5fb1ebd42bf7f3bbaa',
  'supabase/rollbacks/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.rollback.sql':
    'e69035e7402c1d04ee3771145ad19bf3e83d6f303076dabdb8e05b1b251dcd76',
  'supabase/tests/cp6_canonical_business_date.sql':
    '84ff9b521fc40ca435b445c5db84cb617c02d6c3973ef432fd7b025c2ad45967',
  'supabase/tests/cp6_u_expanded_dates.sql':
    'ce4a81878509533cedf0b9ca6a8c04175871f6c8e25226cc08334250dd0388e9',
}
for (const [path, sha256] of Object.entries(pinned)) {
  assert.equal(hash(read(path)), sha256, path)
}

const migration = read(Object.keys(pinned)[0])
const rollback = read(Object.keys(pinned)[1])
const oracle = read(Object.keys(pinned)[2])
for (const token of [
  'U_REQUIRES_EXACT_T_WITHOUT_U_RESIDUE',
  'U_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED',
  'U_TRUSTED_T_FUNCTION_OWNER_ACL_MISMATCH',
  'U_INHERITED_T_SECURITY_MISMATCH',
  'U_JOURNAL_REVERSAL_DAY_ANCHOR',
  'U_MATERIAL_ADJUSTMENT_DAY_ANCHOR',
  'U_OWNER_DEFAULT_AS_OF_ANCHOR',
  'U_OWNER_WIP_CUTOFF_ANCHOR',
  'U_MATERIAL_RECEIPT_DAY_ANCHOR', 'U_MATERIAL_GRNI_DAY_ANCHOR',
  'V2620U_MATERIAL_RECEIPT_BUSINESS_DATE',
  'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE',
  'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE',
  "or r.check_name like 'V2620T_%' or r.check_name like 'V2620U_%'",
  'erp._cp3_business_date(current_timestamp)',
]) assert.ok(migration.includes(token), token)
for (const sha256 of [
  '2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c',
  'b32962d12adde0ca4ae659f2dd83a02a0a3111c3a9060d845ed2e82025696201',
  '0afb94d932b1c7488c1a787de7f734133c1674e0a43100d366c6f3f129ffb9bb',
  'f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce',
  '3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775',
]) assert.ok(migration.includes(sha256), sha256)
for (const token of [
  'jsonb_object_keys(v_expected))<>74',
  'U_POST_USE_ROLLBACK_REFUSED',
  'U_TRUSTED_PREDECESSOR_PIN_MISMATCH',
  'U_ROLLBACK_POSTCONDITION_FAILED',
  'drop table erp.cp6_v2620u_rollback_capsule;',
]) assert.ok(rollback.includes(token), token)

for (const name of [
  'MATERIAL_ORIGINAL_UTC', 'MATERIAL_REVERSAL_REAL_ZONE',
  'OWNER_WIP_CUTOFF', 'OWNER_DEFAULT_AS_OF', 'MATERIAL_ORIGINAL_JAKARTA',
]) assert.ok(oracle.includes(name), name)
const runner = read('scripts/cp6_v2620u_canonical_business_date_regression.py')
for (const token of [
  "phase not in ('BEFORE_U', 'AFTER_U')", "fixed = phase == 'AFTER_U'",
  "'hypothetical_function_hashes'", "'installed_function_hashes'",
  'POSTGRES_CREATE_AND_PG_GET_FUNCTIONDEF_ROUNDTRIP',
  'U_ROUNDTRIP_CHANGED_OWNER_ACL', 'U_UPGRADE_HISTORY_LEFT_RESIDUE',
  'EXPANDED_CASES', 'DETECTOR_REVERSAL_DATE', 'FROZEN_DEFAULT_PRIVILEGE',
  "'verified_u_functions'", 'AUTH_SCHEMA_SOURCE',
  "grant usage on schema public, erp to authenticated;",
]) assert.ok(runner.includes(token), token)

const maintenance = read('scripts/cp6_preuse_rollback_maintenance.py')
for (const token of [
  "'U': {", "'capsule_count': 7", "'predecessor': 'v2.6.20t'",
  "from cp6_v2620u_runtime import verify_extra_objects",
]) assert.ok(maintenance.includes(token), token)
for (const generation of ['m', 'n', 'o', 'p', 'q', 'r', 's', 't']) {
  assert.ok(read(`scripts/cp6_v2620${generation}_runtime.py`).includes(
    'pre_u_installed_sha256'
  ), generation)
}
for (const path of [
  'scripts/cp6_v2620g_independent_regression.py',
  'scripts/cp6_v2620h_adversarial_regression.py',
  'scripts/cp6_v2620i_h2_audit_regression.py',
  'scripts/cp6_v2620j_payment_fact_regression.py',
]) assert.ok(read(path).includes(
  "(['v2.6.20u'] if any('pre_u_installed_sha256' in x for x in m_successor.values()) else [])"
), path)
assert.ok(read('scripts/cp6_v2620t_runtime.py').includes(
  "u_runtime.predecessor_snapshot(cur, 'T', successor)"
))
const matrix = read('scripts/cp6_v2620h_maintenance_rollback_matrix.py')
for (const token of [
  "'U': ('20260913070000'", "'expected_case_count': 320",
  "source_generation: str = 'U'",
]) assert.ok(matrix.includes(token), token)
const setup = read('scripts/cp6_rollback_setup_unit.py')
for (const token of ["'T', 'U'", 'assert len(cases) == 151', "'expected_case_count': 151"]) {
  assert.ok(setup.includes(token), token)
}

const workflow = read('.github/workflows/cp6-full-schema-validation.yml')
let previous = -1
for (const token of [
  'Reproduce independent T canonical business-date counterexamples before U',
  'Apply v2.6.20u canonical material, reversal and owner-report business dates',
  'Prove native U canonical material, reversal and owner-report business dates',
  'Run post-CP6 real Auth',
  'Qualify exact F G H I J K L M N O P Q R S T and U rollback',
  'Prove trusted U capsule before exact U restore to T',
  'Prove trusted T capsule',
]) {
  const at = workflow.indexOf(token)
  assert.ok(at > previous, token)
  previous = at
}
for (const token of [
  "len(schedules['cases'])==320", "'expected':80,'observed':80",
  "setup_unit['completed_case_count']==setup_unit['expected_case_count']==151",
  'CP6_V2620U_RUNTIME_MANIFEST.json',
  'CP6_V2620U_CANONICAL_BUSINESS_DATE_REGRESSION.json',
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620U',
  'CP6_M_RACE_SOURCE_GENERATION: U',
  'U_COMPLETE_T_CATALOG_RESTORE_MISMATCH',
  "to_regclass('erp.cp6_v2620u_rollback_capsule') is null",
]) assert.ok(workflow.includes(token), token)
for (const path of [
  ...Object.keys(pinned), 'docs/cp6-u-canonical-business-date.md',
  'scripts/check-cp6-canonical-business-date.mjs',
  'scripts/cp6_v2620u_runtime.py',
  'scripts/cp6_v2620u_install_diagnostic.py',
  'scripts/cp6_v2620u_canonical_business_date_regression.py',
  'scripts/cp6_v2620u_rollback_guards.py',
]) assert.ok(workflow.includes(`            '${path}',`), path)

console.log(JSON.stringify({
  status: 'PASS', classification: 'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions: 7, boundary_tables: 74, native_cases: 5, expanded_native_cases: 20,
  known_t_paths: 4, controls: 1, maintenance_schedules: 320,
  writer_body_entries: 80, rollback_setup_units: 151, production_go: false,
}))
