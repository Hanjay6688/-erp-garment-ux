import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'

const read = path => readFileSync(path, 'utf8')
const sha = value => createHash('sha256').update(value).digest('hex')
const requireTokens = (source, label, tokens) => {
  for (const token of tokens) {
    assert.ok(source.includes(token), `${label} missing: ${token}`)
  }
}

const migrationPath =
  'supabase/migrations/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.sql'
const rollbackPath =
  'supabase/rollbacks/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.rollback.sql'
const maintenancePath = 'scripts/cp6_preuse_rollback_maintenance.py'
const maintenanceUnitPath = 'scripts/cp6_preuse_rollback_maintenance_unit.py'
const regressionPath = 'scripts/cp6_v2620j_payment_fact_regression.py'
const guardsPath = 'scripts/cp6_v2620j_rollback_guards.py'
const matrixPath = 'scripts/cp6_v2620h_maintenance_rollback_matrix.py'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'

const migration = read(migrationPath)
const rollback = read(rollbackPath)
const maintenance = read(maintenancePath)
const maintenanceUnit = read(maintenanceUnitPath)
const regression = read(regressionPath)
const guards = read(guardsPath)
const matrix = read(matrixPath)
const workflow = read(workflowPath)
const setupUnit = read('scripts/cp6_rollback_setup_unit.py')

assert.equal(Buffer.byteLength(migration), 34695)
assert.equal(sha(migration), '663cb98b2c432ce8518f922dcd7ecbaeb61d07bfb929ac49111a00ded29cad74')
assert.equal(sha(migration.slice(0, -1)), '8c3f3e0d56ea825f19f99a1c48db25c6ae916a6fc4896031560143da10ee67f1')
assert.equal(Buffer.byteLength(rollback), 10473)
assert.equal(sha(rollback), 'b0def9ada0670e9cdfd9c33ee4c507b8be628fed17027651d4df4b3038264f6d')
assert.deepEqual(
  readdirSync('supabase/migrations').filter(name => name.startsWith('20260910170556_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync('supabase/rollbacks').filter(name => name.startsWith('20260910170556_')),
  [rollbackPath.split('/').at(-1)],
)

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain terminal LF`)
  assert.match(sql, /^begin;$/mi)
  assert.match(sql, /commit;\s*$/i)
  const quotes = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quotes.set(match[0], (quotes.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual([...quotes].filter(([, count]) => count % 2), [], `${path} dollar quote drift`)
}

assert.equal(
  sha(read('supabase/migrations/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.sql')),
  '01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683',
)
assert.equal(
  sha(read('supabase/rollbacks/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.rollback.sql')),
  '7719d329e7e0e4d4293466b9e425c9ef0b4a46a757545ad3d1bb6acbd2c535f2',
)

requireTokens(migration, 'J forward-only payment facts', [
  'VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.',
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20i'", "version='v2.6.20j'",
  'create table erp.sales_payment_posting_facts(',
  'create table erp.sales_payment_reversal_facts(',
  'create unique index uq_sales_payments_one_replacement',
  'POSTED_PAYMENT_FACT_APPEND_ONLY: use linked reversal/replacement',
  'POSTED_PAYMENT_IDENTITY_IMMUTABLE: reverse and post one linked replacement',
  "if p.payment_date::date>current_date then",
  'Replacement requires one fully reversed posted payment',
  'Allocation replacement must preserve customer, amount, cash account and original payment clock while changing invoice',
  'Payment reversal chronology cannot precede original posting',
  "'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL'",
  "f.payment_snapshot is distinct from to_jsonb(p)-'status'",
  'f.lineage_sha256 is distinct from encode(extensions.digest',
  'rf.reversal_economic_date<f.journal_economic_date',
  'rf.reversal_posting_at<f.journal_posting_at',
  'foreach v_table in array array[',
  "'sales_payment_posting_facts','sales_payment_reversal_facts'",
])
for (const digest of [
  '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df',
  '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6',
  'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1',
  '5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a',
  '00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6',
  '3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f',
]) {
  assert.ok(migration.includes(digest) || rollback.includes(digest), `J trust pin missing: ${digest}`)
}
assert.doesNotMatch(migration, /\b(?:delete from|truncate|drop table)\b/i)

requireTokens(rollback, 'J exact pre-use restore', [
  'Execute only through scripts/cp6_preuse_rollback_maintenance.py',
  'v2.6.20j rollback refused: exact platform ledger identity is ambiguous',
  'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20j',
  '(select count(*) from jsonb_object_keys(v_expected))<>29',
  'v2.6.20j rollback refused: post-install business history exists',
  'drop table erp.sales_payment_reversal_facts;',
  'drop table erp.sales_payment_posting_facts;',
  'alter table erp.sales_payments drop column replaces_payment_id;',
  "delete from erp.schema_migrations where version='v2.6.20j';",
  'v2.6.20j rollback postcondition failed',
  '663cb98b2c432ce8518f922dcd7ecbaeb61d07bfb929ac49111a00ded29cad74',
  '8c3f3e0d56ea825f19f99a1c48db25c6ae916a6fc4896031560143da10ee67f1',
])
assert.doesNotMatch(rollback, /delete from erp\.(?:fg_|sales_|sale_|journal_|hpp_|wip_|laundry_)/i)

requireTokens(maintenance, 'J trusted maintenance endpoint', [
  "'J': {", "'marker': 'v2.6.20j'", "'capsule_count': 3",
  "'rollback_sha256': 'b0def9ada0670e9cdfd9c33ee4c507b8be628fed17027651d4df4b3038264f6d'",
  'def _reject_ambiguous_conninfo(value: str, label: str) -> None:',
  "value.startswith('postgresql://')", "if '?' in value or '#' in value:",
  'Refusing ambiguous {label} conninfo query/fragment parameters',
  "allowed_conninfo = {'dbname', 'host', 'password', 'port', 'user'}",
  "_phase(report_path, report, 'ENDPOINT_VERIFIED'",
  "_phase(report_path, report, 'CAPSULE_VERIFIED'",
  "_phase(report_path, report, 'ADMISSION_CLOSED'",
])
assert.ok(maintenance.indexOf("_reject_ambiguous_conninfo(target_pgurl") < maintenance.indexOf('conninfo_to_dict(target_pgurl)'))
assert.ok(maintenance.indexOf("'ENDPOINT_VERIFIED'") < maintenance.indexOf("'CAPSULE_VERIFIED'"))
assert.ok(maintenance.indexOf("'CAPSULE_VERIFIED'") < maintenance.indexOf("'ADMISSION_CLOSED'"))

requireTokens(maintenanceUnit, '31-case fail-closed endpoint oracle', [
  "'expected_case_count': 31", "case('exact_disposable_clone', accepted=True)",
  "'duplicate_target_host_same'", "'duplicate_target_host_overrides_wrong'",
  "'duplicate_target_port'", "'duplicate_target_user'",
  "'duplicate_target_database'", "'duplicate_target_password'",
  "'duplicate_control_host'", "'conninfo_duplicate_host'",
  "except maintenance.MaintenanceRollbackError as exc:",
  "else:", "raise AssertionError(f'{name}: endpoint unexpectedly accepted')",
  "raise AssertionError('Permissive validator negative control unexpectedly passed')",
  "'suite_failed_closed': True",
])

requireTokens(regression, 'native J business and detector proof', [
  'I01_INVOICE_IDENTITY_GUARD_AND_DETECTOR',
  'I02_AUTHORITATIVE_INVERSE_DATES',
  'LINKED_ALLOCATION_REPLACEMENT',
  'APPEND_ONLY_FACT_AND_FULL_SNAPSHOT_GUARDS',
  'FUTURE_PAYMENT_FAIL_CLOSED',
  'privileged_direct_invoice_swap', 'replica_invoice_swap',
  'inverse_one_day_before_original', 'inverse_one_day_after_fact',
  'second_replacement_for_same_payment', 'payment_snapshot_after_trigger_bypass',
  'replacement_before_original_reversal', 'replacement_wrong_customer',
  'replacement_same_invoice', 'replacement_amount_drift', 'replacement_original_clock_drift',
  'duplicate_reversal_no_new_facts', 'net_cash_and_receivable_conserved',
  'stock_fg_value_cogs_unchanged',
  "if actual != (0, 'READY'):", "report != 'BLOCKED'",
  "set local session_replication_role='replica'", 'conn.rollback()',
])
requireTokens(guards, 'J trusted rollback guards', [
  "matrix.prepare('J', 'REPORT'", 'coherent_capsule_fault',
  'TRUSTED_PREDECESSOR_PIN_MISMATCH',
  "'post_install_boundary_history'", "'coherent_capsule_and_checksum'",
  "target_name='J'", "'error_code': 'V2620J_ROLLBACK_GUARD_FAILED'",
  "'restored_function_count': len(actual)",
  'for name in DIRECT_J_GUARD_NAMES',
  "'admission_reopened_after_success': True",
])
requireTokens(matrix, '200 native schedules and body-entry proof', [
  'def setup_rollback_plan(target: str, source_generation: str)',
  'verify_setup_source(source_generation)',
  'for generation in rollback_plan:',
  "'J': ('20260910170556'", "'expected_case_count': 280",
  "'expected': 70", 'writer_first_body_entry == 70',
  'savepoint cp6_writer_body_warmup', 'rollback to savepoint cp6_writer_body_warmup',
  "'compilation of PL/pgSQL function' in diagnostic_context",
  "'PL/pgSQL function' not in diagnostic_context",
])
assert.ok(read('scripts/cp6_v2620i_rollback_guards.py').includes("source_generation='I'"))
assert.ok(!guards.includes("'functions': actual"))
requireTokens(setupUnit, 'generation setup failure regressions', [
  'MOCKED_FIXTURE_ORCHESTRATION_NOT_NATIVE_DATABASE_PROOF',
  "'expected_case_count': 118", 'unconditional_j_negative_control_rejected',
  'permissive_source_negative_control_rejected', 'STRUCTURAL_RESTORE_SUMMARY', 'STRUCTURAL_CAPSULE_SUMMARY',
])

const order = [
  'Apply v2.6.20i H2 audit closure before every final-runtime proof',
  'Apply v2.6.20j immutable payment facts before every final-runtime proof',
  'Run post-CP6 real Auth JWT HTTP permissions',
  'Prove native I H2 payment lineage',
  'Prove native J immutable payment allocation',
  'Qualify exact F G H I J K L M N O P Q R and S rollback under closed admission across two hundred eighty native schedules',
  'Prove trusted J capsule and maintenance-only exact J restore to I',
  'Prove trusted F G H I capsules and maintenance-only exact I restore to H',
]
let prior = -1
for (const token of order) {
  const position = workflow.indexOf(token)
  assert.ok(position > prior, `J workflow order missing/wrong: ${token}`)
  prior = position
}
requireTokens(workflow, 'exact-J artifact contract', [
  'python scripts/cp6_rollback_setup_unit.py', 'CP6_ROLLBACK_SETUP_UNIT.json',
  "setup_unit['completed_case_count']==setup_unit['expected_case_count']==118",
  'CP6_PREUSE_ROLLBACK_MAINTENANCE_UNIT.json', "= '31'",
  'permissive_validator_negative_control.suite_failed_closed',
  'V2620J_MIGRATION_SHA256.txt', 'V2620J_ROLLBACK_SHA256.txt',
  'V2620J_NATIVE_REGRESSION.log', 'CP6_V2620J_PAYMENT_FACT_REGRESSION.json',
  'CP6_V2620J_ROLLBACK_GUARDS.json', 'V2620J_MAIN_MAINTENANCE_ROLLBACK.json',
  "('F','G','H','I','J','K','L','M','N','O','P','Q','R','S')", "len(schedules['cases'])==280",
  "'writer_first_backend_body_entries':70",
  "'writer_first_compilation_only_contexts':0",
  "'format':'CP6_V2620N_RUNTIME_PROOF_V1'",
  "proof/'CP6_V2620S_RUNTIME_MANIFEST.json'",
  'name: cp6-r1-v2620s-full-schema-auth-browser-proof',
  'runtime=v2.6.20e+v2.6.20f+v2.6.20g+v2.6.20h+v2.6.20i+v2.6.20j',
  "'uat_v2620j_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'production_go':False",
])
assert.ok(read('scripts/cp6_auth_permission_e2e.mjs').includes('AFTER_V2620S'))
assert.ok(read('package.json').includes('node scripts/check-cp6-payment-fact-closure.mjs'))

console.log(JSON.stringify({
  status: 'PASS',
  boundary: 'CP6_V2620J_PAYMENT_FACT_CLOSURE',
  migration_sha256: sha(migration),
  rollback_sha256: sha(rollback),
  maintenance_endpoint_cases: 31,
  maintenance_matrix_schedules: 280,
  writer_first_backend_body_entries: 70,
  production_go: false,
}))
