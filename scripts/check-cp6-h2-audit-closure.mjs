import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'

const read = path => readFileSync(path, 'utf8')
const sha = value => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1
const requireTokens = (source, label, tokens) => {
  for (const token of tokens) {
    assert.ok(source.includes(token), `${label} missing: ${token}`)
  }
}

const migrationPath =
  'supabase/migrations/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.sql'
const rollbackPath =
  'supabase/rollbacks/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.rollback.sql'
const maintenancePath = 'scripts/cp6_preuse_rollback_maintenance.py'
const maintenanceUnitPath = 'scripts/cp6_preuse_rollback_maintenance_unit.py'
const regressionPath = 'scripts/cp6_v2620i_h2_audit_regression.py'
const guardsPath = 'scripts/cp6_v2620i_rollback_guards.py'
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

assert.equal(Buffer.byteLength(migration), 16100)
assert.equal(sha(migration), '01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683')
assert.equal(sha(migration.slice(0, -1)), '60fa613e31d13f7db3efff7f1e0daee956886afe2676c61ee05661bb55211a1c')
assert.equal(Buffer.byteLength(rollback), 7577)
assert.equal(sha(rollback), '7719d329e7e0e4d4293466b9e425c9ef0b4a46a757545ad3d1bb6acbd2c535f2')
assert.deepEqual(
  readdirSync('supabase/migrations').filter(name => name.startsWith('20260910100051_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync('supabase/rollbacks').filter(name => name.startsWith('20260910100051_')),
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

requireTokens(migration, 'I exact H trust and forward-only capsule', [
  'VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.',
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20h'", "version='v2.6.20i'",
  'TRUSTED_PREDECESSOR_PIN_MISMATCH: H capsule/function',
  'create table erp.cp6_v2620i_rollback_capsule(',
  '(select count(*) from erp.cp6_v2620h_rollback_capsule)<>6',
  "'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule'",
  'installed_definition_sha256', 'owner_snapshot', 'acl_snapshot',
  'ERP v2.6.20i payment lineage reconciliation failed',
])
for (const digest of [
  '436a77b32c953e92fc8e43f953335392c4137b61bf632780d26b9b942d94e8b0',
  '4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7',
  '83214f0812d151b5d03cb8669f48fb5c72b4480d0c609df84d244559f3e4d988',
  '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df',
  '217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0',
  'd959c5e095cce32540b9f2a4310857520b4eec70c5200465f16d74cccfb45a46',
  '33219c5509a43470f87d3b0fe4af472bec3f87b4808bbdba7d2eed69ea88354d',
  '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6',
  '68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce',
  'e7155962a8aa0f0e72f16644ffdf3563d3a11658b73c5185e94d6023090ec3cb',
  'fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962',
]) {
  assert.equal(occurrences(migration, digest), 1, `H trust pin cardinality drift: ${digest}`)
}
assert.equal(occurrences(migration, '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'), 3)
assert.ok(occurrences(migration, 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1') === 0)

requireTokens(migration, 'H2-01 exact payment journal lineage', [
  "'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','CRITICAL'",
  "p.status='DRAFT' and exists(",
  "p.status in('POSTED','REVERSED')",
  "o.source_type='SALES_PAYMENT' and o.source_id=p.id",
  '(select count(*) from erp.journal_lines l where l.journal_entry_id=o.id)=2',
  '(select coalesce(sum(l.debit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount',
  '(select coalesce(sum(l.credit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount',
  "l.account_id=erp.account_id('AR_CUSTOMER')",
  "r.source_type='JOURNAL_REVERSAL' and r.source_id=o.id",
  'r.reversal_of_id=o.id',
  "where o.source_type='SALES_PAYMENT'",
  'not exists(select 1 from erp.sales_payments p where p.id=o.source_id)',
])
assert.doesNotMatch(migration, /\b(?:delete from|truncate|drop table)\b/i)

requireTokens(rollback, 'I exact pre-use restore', [
  'Execute only through scripts/cp6_preuse_rollback_maintenance.py',
  'v2.6.20i rollback refused: exact platform ledger identity is ambiguous',
  'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20i report capsule/function',
  '(select count(*) from jsonb_object_keys(c.boundary_snapshot))<>26',
  'v2.6.20i rollback refused: post-install business history exists',
  "delete from erp.schema_migrations where version='v2.6.20i';",
  'drop table erp.cp6_v2620i_rollback_capsule;',
  'v2.6.20i rollback postcondition failed',
  '01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683',
  '60fa613e31d13f7db3efff7f1e0daee956886afe2676c61ee05661bb55211a1c',
  '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f',
  'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1',
])
assert.doesNotMatch(rollback, /delete from erp\.(?:fg_|sales_|sale_|journal_|hpp_|wip_|laundry_)/i)

requireTokens(maintenance, 'independent capsule trust and endpoint allowlist', [
  "'contract': 'CP6_PREUSE_ROLLBACK_MAINTENANCE_V2'",
  "'I': {", 'TRUSTED_FUNCTIONS', 'TRUSTED_PREDECESSOR_PIN_MISMATCH',
  'def _public_failure_code(exc: Exception) -> str:',
  "'trusted_predecessor_identity_count': len(TRUSTED_FUNCTIONS[target_name])",
  "report['error_code'] = _public_failure_code(exc)",
  "allowed_conninfo = {'dbname', 'host', 'password', 'port', 'user'}",
  'connection parameters outside allowlist', 'endpoint without password',
  "'host': '127.0.0.1'", "'port': '54322'",
  "'user': 'cp6_maintenance_admission'", "'dbname': 'template1'",
  '(pg_control_system()).system_identifier::text',
  'Target/admission-control runtime cluster mismatch',
  "_phase(report_path, report, 'ENDPOINT_VERIFIED'",
  "_phase(report_path, report, 'CAPSULE_VERIFIED'",
  "_phase(report_path, report, 'ADMISSION_CLOSED'",
])
assert.ok(!maintenance.includes("'trusted_predecessor_expectations': TRUSTED_FUNCTIONS[target_name]"))
assert.ok(!maintenance.includes("report['error'] = str(exc)"))
assert.ok(maintenance.indexOf("'ENDPOINT_VERIFIED'") < maintenance.indexOf("'CAPSULE_VERIFIED'"))
assert.ok(maintenance.indexOf("'CAPSULE_VERIFIED'") < maintenance.indexOf("'ADMISSION_CLOSED'"))
requireTokens(maintenanceUnit, 'endpoint negative matrix plus J successor hardening', [
  "'expected_case_count': 31", "case('exact_disposable_clone', accepted=True)",
  "'target_application_name_override'", "'target_without_password'",
  "'non_loopback_control_hostaddr'", "'control_options_override'",
  "'control_service_override'", "'control_without_password'",
])

requireTokens(regression, 'native H2-01 and valid payment lifecycle proof', [
  'H2_01_SAME_CUSTOMER_CROSS_INVOICE_WASH',
  'VALID_PAYMENT_AND_EXACT_INVERSE', 'PAYMENT_LINEAGE_FAULT_MATRIX',
  'AUTHENTICATED_DIRECT_PAYMENT_WRITE_DENIED',
  "when %s then 49.99 when %s then 50.01",
  "(i_issues, h_customer, global_ar, report) != (2, 0, 0, 'BLOCKED')",
  'balanced_original_line_amount_drift', 'payment_journal_customer_drift',
  'orphan_sales_payment_journal', 'inverse_link_drift',
  "set local role authenticated", "conn.rollback()",
])
requireTokens(guards, 'trusted coherent-capsule fault proof', [
  "for target in ('F', 'G', 'H', 'I')", 'canonical_cost_tamper',
  'coherent_capsule_fault', 'TRUSTED_PREDECESSOR_PIN_MISMATCH',
  'def disposable_clone_confirmation(pgurl: str):',
  "if database != 'cp6_rollback':",
  'with disposable_clone_confirmation(matrix.CLONE):',
  "'error_code': 'V2620I_ROLLBACK_GUARD_FAILED'",
  "'expected_rejection_observed': True",
  "'admission_reopened_after_success': True",
  "if report.get('admission_closed') or report.get('rollback_started')",
  "target_name='I'", 'V2620I_MAIN_MAINTENANCE_ROLLBACK.json',
])
requireTokens(matrix, '200 successor-aware native schedules and body-entry proof', [
  "'I': ('20260910100051'", "'J': ('20260910170556'", "'expected_case_count': 300",
  'savepoint cp6_writer_body_warmup', 'rollback to savepoint cp6_writer_body_warmup',
  "writer['warmup_body_completed'] = True",
  "writer['warmup_effects_rolled_back'] = True",
  "'compilation of PL/pgSQL function' in diagnostic_context",
  "'PL/pgSQL function' not in diagnostic_context", "'at SQL statement' not in diagnostic_context",
  "'expected': 70", 'writer_first_body_entry == 70', 'compilation_only_contexts == 0',
])

const order = [
  'Apply v2.6.20h expanded R01-R03 closure',
  'Apply v2.6.20i H2 audit closure',
  'Apply v2.6.20j immutable payment facts',
  'Run post-CP6 real Auth JWT HTTP permissions',
  'Prove native H R02-R03',
  'Prove native I H2 payment lineage',
  'Qualify exact F G H I J K L M N O P Q R S and T rollback under closed admission across three hundred native schedules',
  'Prove trusted J capsule and maintenance-only exact J restore to I',
  'Prove trusted F G H I capsules and maintenance-only exact I restore to H',
  'Prove H guards and maintenance-only exact six-function restore to G',
]
let prior = -1
for (const token of order) {
  const position = workflow.indexOf(token)
  assert.ok(position > prior, `I workflow order missing/wrong: ${token}`)
  prior = position
}
requireTokens(workflow, 'exact-I proof retained inside exact-J artifact contract', [
  'CP6_PREUSE_ROLLBACK_MAINTENANCE_UNIT.json', "= '31'",
  'V2620I_MIGRATION_SHA256.txt', 'V2620I_ROLLBACK_SHA256.txt',
  'V2620I_NATIVE_REGRESSION.log', 'CP6_V2620I_H2_AUDIT_REGRESSION.json',
  'CP6_V2620I_ROLLBACK_GUARDS.json', 'V2620I_MAIN_MAINTENANCE_ROLLBACK.json',
  "('F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T')", "len(schedules['cases'])==300",
  "'writer_first_backend_body_entries':75",
  "'writer_first_compilation_only_contexts':0",
  "iguard['maintenance']['admission_reopened_after_success']",
  "'format':'CP6_V2620N_RUNTIME_PROOF_V1'",
  "proof/'CP6_V2620T_RUNTIME_MANIFEST.json'",
  'name: cp6-r1-v2620t-full-schema-auth-browser-proof',
  'runtime=v2.6.20e+v2.6.20f+v2.6.20g+v2.6.20h+v2.6.20i+v2.6.20j',
  "'uat_v2620i_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'production_go':False",
])
assert.ok(!workflow.includes("iguard['maintenance']['admission_reopened']"))
assert.ok(read('scripts/cp6_auth_permission_e2e.mjs').includes('AFTER_V2620T'))
assert.ok(read('package.json').includes('node scripts/check-cp6-h2-audit-closure.mjs'))

console.log(JSON.stringify({
  status: 'PASS',
  boundary: 'CP6_V2620I_H2_AUDIT_CLOSURE',
  migration_sha256: sha(migration),
  rollback_sha256: sha(rollback),
  maintenance_matrix_schedules: 300,
  writer_first_backend_body_entries: 75,
  production_go: false,
}))
