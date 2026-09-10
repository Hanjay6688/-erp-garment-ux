import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

const read = path => readFileSync(path, 'utf8')
const sha = value => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1
const requireTokens = (source, label, tokens) => {
  for (const token of tokens) assert.ok(source.includes(token), `${label} missing: ${token}`)
}

const migrationPath = 'supabase/migrations/20260910061516_erp_v2_6_20h_cp6_expanded_audit_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260910061516_erp_v2_6_20h_cp6_expanded_audit_closure.rollback.sql'
const maintenancePath = 'scripts/cp6_preuse_rollback_maintenance.py'
const regressionPath = 'scripts/cp6_v2620h_adversarial_regression.py'
const matrixPath = 'scripts/cp6_v2620h_maintenance_rollback_matrix.py'
const guardPath = 'scripts/cp6_v2620h_rollback_guards.py'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const migration = read(migrationPath)
const rollback = read(rollbackPath)
const maintenance = read(maintenancePath)
const regression = read(regressionPath)
const matrix = read(matrixPath)
const guard = read(guardPath)
const workflow = read(workflowPath)

const expected = {
  migration: ['e16dbb655164595be273c03582d35c9ac33593136bd418fdd87156e592f292b8', 19733],
  rollback: ['0d0318e3848344c3642f1796a205d25bcf1cc2d2091ce28d1fc9cf6d186ecbe5', 6876],
  maintenance: ['84f18953a34db299aa1bac412a9ca47099da2dcad5e87eb17f038bfaf3413c98', 34642],
  regression: ['2e56d61d85f35ad62334286ba8c7f42e03c0ab08b2ae6a86cb47972fd61b7633', 24233],
  matrix: ['d70799ceda37a4a2e872cd67e8e6265251582fb594b091f9962ab0e9c5022dd1', 31073],
  guard: ['621f51b187138750646f38c7464a959713ba3c78bcbcd5031ac9841a288aca68', 6649],
}
for (const [name, source] of Object.entries({ migration, rollback, maintenance, regression, matrix, guard })) {
  assert.equal(Buffer.byteLength(source), expected[name][1], `${name} byte drift`)
  assert.equal(sha(source), expected[name][0], `${name} SHA drift`)
}
assert.equal(sha(migration.slice(0, -1)), 'bcac43cd1cca5214f8678cd058caf6ff19ce90bdebd1c31f47675c0efd79a36f')

// F and G audited source/rollback bytes are immutable; H is forward-only.
assert.equal(sha(read('supabase/migrations/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql')), '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c')
assert.equal(sha(read('supabase/rollbacks/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.rollback.sql')), '83819e093d1489af70431704c59e2cb50a0149e1adc8520d5b9536510572a23d')
assert.equal(sha(read('supabase/migrations/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.sql')), '645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726')
assert.equal(sha(read('supabase/rollbacks/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.rollback.sql')), '8946f4ca8b75850cb284cee669b609e7e938b6020f4e9fa7a270e9794b2becd8')

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain terminal LF`)
  assert.match(sql, /^begin;$/mi)
  assert.match(sql, /commit;\s*$/i)
  const quotes = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quotes.set(match[0], (quotes.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual([...quotes].filter(([, count]) => count % 2), [], `${path} unbalanced dollar quote`)
}

requireTokens(migration, 'H exact predecessor/capsule', [
  'VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.',
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20g'", "version='v2.6.20h'",
  'create table erp.cp6_v2620h_rollback_capsule(',
  '(select count(*) from erp.cp6_v2620h_rollback_capsule)<>6',
  'installed_definition_sha256', 'boundary_snapshot',
])
for (const digest of [
  '83214f0812d151b5d03cb8669f48fb5c72b4480d0c609df84d244559f3e4d988',
  '33219c5509a43470f87d3b0fe4af472bec3f87b4808bbdba7d2eed69ea88354d',
  '217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0',
  '68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce',
  '436a77b32c953e92fc8e43f953335392c4137b61bf632780d26b9b942d94e8b0',
  'fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962',
]) assert.equal(occurrences(migration, digest), 1, `Predecessor digest must be pinned once: ${digest}`)

requireTokens(migration, 'R02/R03 business closure', [
  "v_amount:=round(p.amount,2)::numeric(20,2)",
  'if v_paid+v_amount>v_total then',
  "case when v_paid=v_total then 'PAID' else 'PARTIAL_PAID' end",
  "if v_paid>v_net_total then",
  'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH',
  'rv.physical_at is distinct from rh.physical_at',
  'V2620H_CUSTOMER_AR_STATUS_MISMATCH',
  'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH',
  'round(ar.gl_amount,2) is distinct from round(ar.subledger_amount,2)',
  'round(gl_amount,2) is distinct from round(subledger_amount,2)',
])
// The three predecessor tolerance expressions are deliberately present once
// as guarded dynamic-patch anchors.  Pin those exact occurrences instead of
// banning every line that also mentions the literal 0.01 in an error message.
assert.equal(occurrences(migration, 'v_paid+p.amount>v_total+0.01'), 0)
assert.equal(occurrences(migration, 'v_paid>v_net_total+0.01'), 1)
assert.equal(occurrences(migration, 'v_paid>=v_net_total-0.01'), 1)
assert.equal(occurrences(migration, 'v_paid>=v_total-0.01'), 1)
assert.doesNotMatch(migration, /\b(?:delete from|truncate|drop table)\b/i)

requireTokens(rollback, 'H pre-use refusal and exact G restore', [
  'Execute only through scripts/cp6_preuse_rollback_maintenance.py',
  'v2.6.20h rollback refused: exact platform ledger identity is ambiguous',
  'v2.6.20h rollback refused: post-install business history exists',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20h object/capsule/ACL',
  'drop table erp.cp6_v2620h_rollback_capsule;',
  "delete from erp.schema_migrations where version='v2.6.20h';",
  'v2.6.20h rollback postcondition failed',
  expected.migration[0], 'bcac43cd1cca5214f8678cd058caf6ff19ce90bdebd1c31f47675c0efd79a36f',
])
assert.doesNotMatch(rollback, /delete from erp\.(?:fg_|sales_|sale_|journal_|hpp_|wip_|laundry_)/i)

requireTokens(maintenance, 'closed-admission maintenance executor', [
  "alter database {} with allow_connections false",
  'pg_terminate_backend', 'DRAIN_TIMEOUT: old client invocations remain',
  "report['rollback_started'] = True", "report['rollback_committed'] = True",
  'Exact predecessor function/ACL mismatch',
  "report['admission_still_closed']",
  'Reviewed rollback checksum mismatch',
  '# Fail closed: do not reopen admission here.',
  'CP6_ROLLBACK_TARGET_PGURL',
  'CP6_ADMISSION_CONTROL_PGURL',
  'CP6_MAINTENANCE_CONFIRM_DATABASE',
])
assert.ok(!maintenance.includes("os.environ.get('CP6_MAINTENANCE_PGURL'"))
assert.ok(maintenance.indexOf("allow_connections false") < maintenance.indexOf("report['rollback_started'] = True"))
assert.ok(maintenance.indexOf("report['rollback_started'] = True") < maintenance.indexOf("alter database {} with allow_connections true"))

requireTokens(regression, 'native R02/R03 regression', [
  'R02_WIP_RETURN_CLOCK', 'R03_UNDERPAID_FINAL_CENT_AND_INVERSES',
  'R03_PAID_RETURN_ATOMIC_REFUSAL', 'R03_OVERPAYMENT_ATOMIC_REFUSAL',
  'R03_STATUS_AND_PER_CUSTOMER_DETECTORS',
  "Decimal('99.99')", "Decimal('.01')", "Decimal('100')",
  "Decimal('60')", "Decimal('40')", 'lawful_return_lifecycle',
  "'2026-09-01T12:00:00Z'", "fault_report_status': blocked_status",
  "set local session_replication_role='replica'",
  "global_issue != 0", "conn.rollback()",
])

requireTokens(matrix, 'complete native maintenance matrix', [
  "'F':", "'G':", "'H':", "'I':", "'J':",
  "OPERATIONS = ('SALE', 'RETURN', 'CONVERSION', 'REPORT', 'FK_SYNC')",
  "MODES = ('WRITER_FIRST', 'ADMISSION_FIRST', 'WRITER_ABORT', 'DRAIN_TIMEOUT')",
  "'expected_case_count': 100", "report['cases'].append(case)",
  "report['failed_case_count']", 'missing_helper_error_absent',
  'database_admission_closed_before_ddl', 'failure_kept_admission_closed',
  'blocked_inside_backend', 'inflight_inside_backend_before_admission_close',
  "writer_at_close['wait_event_type'] != 'Lock'", "status') != 'READY'",
  'Unsafe maintenance phase order', 'case_context.json',
  "if mode == 'ADMISSION_FIRST'", "if mode == 'DRAIN_TIMEOUT'",
  "ADMISSION_CONTROL = os.environ.get('CP6_ADMISSION_CONTROL_PGURL', '')",
  "'user': 'cp6_maintenance_admission'",
  'Refusing non-allowlisted admission-control authority',
  'savepoint cp6_writer_body_warmup',
  "writer['warmup_body_completed'] = True",
  "'compilation of PL/pgSQL function' in diagnostic_context",
  'writer_first_body_entry == 25', 'compilation_only_contexts == 0',
])
assert.doesNotMatch(matrix, /raise AssertionError\('Native expanded rollback schedule failed'\)/)
requireTokens(guard, 'H guards and maintenance restore', [
  "target_name='H'", 'CP6_V2620H_ROLLBACK_GUARDS.json',
  'V2620H_MAIN_MAINTENANCE_ROLLBACK.json',
  "'platform_bytes'", "'successor'", "'definition_drift'", "'acl_drift'", "'boundary_drift'",
])

const order = [
  'Apply v2.6.20g independent N01-N03 closure',
  'Apply v2.6.20h expanded R01-R03 closure',
  'Apply v2.6.20i H2 audit closure',
  'Apply v2.6.20j immutable payment facts',
  'Run post-CP6 real Auth JWT HTTP permissions',
  'Prove native G N01-N03',
  'Prove native H R02-R03',
  'Prove native I H2 payment lineage',
  'Qualify exact F G H I and J rollback under closed admission',
  'Prove trusted J capsule and maintenance-only exact J restore to I',
  'Prove trusted F G H I capsules and maintenance-only exact I restore to H',
  'Prove H guards and maintenance-only exact six-function restore to G',
  'Prove G guards and exact seven-function pre-use restore to F',
  'Prove v2.6.20f guards and exact pre-use rollback before v2.6.20e',
]
let prior = -1
for (const token of order) {
  const position = workflow.indexOf(token)
  assert.ok(position > prior, `Workflow order missing/wrong: ${token}`)
  prior = position
}
requireTokens(workflow, 'exact-H proof wiring', [
  'python scripts/cp6_v2620h_adversarial_regression.py',
  'python scripts/cp6_v2620h_maintenance_rollback_matrix.py',
  'python scripts/cp6_v2620h_rollback_guards.py',
  'python scripts/cp6_preuse_rollback_maintenance.py',
  'H_MAINTENANCE_ROLLBACK/manifest.json', "= '100'",
  'V2620H_ROLLBACK_SHA256.txt',
  "('F','RETURN','WRITER_FIRST')",
  'CP6_V2620J_RUNTIME_PROOF_V1',
  'cp6-r1-v2620j-full-schema-auth-browser-proof',
  'runtime=v2.6.20e+v2.6.20f+v2.6.20g+v2.6.20h+v2.6.20i+v2.6.20j',
  'CP6_ROLLBACK_TARGET_PGURL: postgresql://postgres:postgres@127.0.0.1:54322/postgres',
  'Provision isolated rollback admission-control authority',
  'create role cp6_maintenance_admission',
  'CP6_ADMISSION_CONTROL_PGURL=%s',
  'CP6_ADMISSION_CONTROL_PREFLIGHT.json',
  'credential_persisted_in_proof',
  'echo "::add-mask::$maintenance_password"',
  expected.migration[0],
])
assert.ok(!workflow.includes('bash scripts/run_cp6_v2620f_live_rollback_races.sh'))
assert.ok(read('scripts/cp6_auth_permission_e2e.mjs').includes('AFTER_V2620J'))
assert.ok(read('package.json').includes('node scripts/check-cp6-expanded-audit-closure.mjs'))

console.log(JSON.stringify({
  status: 'PASS',
  boundary: 'CP6_V2620H_R01_R03_EXPANDED_AUDIT_CLOSURE',
  migration_sha256: expected.migration[0],
  rollback_sha256: expected.rollback[0],
  maintenance_matrix_schedules: 100,
  production_go: false,
}))
