import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1
const literals = (source) => [...source.matchAll(/'([^']+)'/g)].map((match) => match[1])

const version = '20260904111157'
const migrationName = 'erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
const migrationPath = `supabase/migrations/${version}_${migrationName}.sql`
const rollbackPath = `supabase/rollbacks/${version}_${migrationName}.rollback.sql`
const acceptancePath = 'supabase/tests/cp6_laundry_qc_fg_authoritative_rollback.sql'
const seedPath = 'supabase/tests/cp6_laundry_qc_concurrency_seed.sql'
const racePath = 'scripts/cp6_laundry_qc_concurrency.py'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const mainWorkflowPath = '.github/workflows/ci.yml'

const migration = read(migrationPath)
const rollback = read(rollbackPath)
const acceptance = read(acceptancePath)
const seed = read(seedPath)
const cp5Recovery = read('supabase/tests/cp5_bs_resolution_recovery_rollback.sql')
const race = read(racePath)
const workflow = read(workflowPath)
const mainWorkflow = read(mainWorkflowPath)
const cloneVerifier = read('scripts/verify-cp6-disposable-clone.sh')
const cloneBuilder = read('scripts/clone-cp6-disposable-database.sh')
const gitignore = read('.gitignore')
const predecessorOwnership = read('scripts/check-predecessor-backend-ownership.mjs')
const authPolicy = read('src/auth/authPolicy.ts')
const authPolicyTest = read('src/auth/AuthProvider.test.ts')
const authLifecycleTest = read('src/auth/AuthProvider.lifecycle.test.tsx')
const model = read('src/laundryQcModel.ts')
const modelTest = read('src/laundryQcModel.test.ts')
const hook = read('src/useLaundryQcWorkspace.ts')
const hookTest = read('src/useLaundryQcWorkspace.dom.test.tsx')
const businessTime = read('src/cp6BusinessTime.ts')
const businessTimeTest = read('src/cp6BusinessTime.test.ts')
const laundryPage = read('src/ConnectedLaundryPage.tsx')
const qcPage = read('src/ConnectedQcFinalPage.tsx')
const fgBoundary = read('src/ConnectedFgHandoffBoundary.tsx')
const permissionNotice = read('src/Cp6PermissionNotice.tsx')
const workspaceCss = read('src/connected-laundry-qc.css')
const masterPage = read('src/MasterDataPages.tsx')
const masterTest = read('src/MasterDataPages.dom.test.tsx')
const browser = read('tests/browser/cp6-laundry-qc.spec.ts')
const browserConfig = read('playwright.cp6.config.ts')
const rules = read('docs/erp-reliability-invariants.md')
const packageJson = read('package.json')

assert.ok(acceptance.includes('v_nested jsonb;'),
  'CP6 acceptance must declare the nested workspace fact used by failed-wash assertions')

function onlyVersion(directory, expectedName) {
  const matches = readdirSync(resolve(root, directory)).filter((name) => name.startsWith(`${version}_`))
  assert.deepEqual(matches, [expectedName], `CP6 version ${version} is duplicated or misnamed in ${directory}`)
}

onlyVersion('supabase/migrations', migrationPath.split('/').at(-1))
onlyVersion('supabase/rollbacks', rollbackPath.split('/').at(-1))

for (const [path, sql] of [
  [migrationPath, migration], [rollbackPath, rollback],
  [acceptancePath, acceptance], [seedPath, seed],
]) {
  assert.ok(sql.endsWith('\n'), `${path} must end in exactly materializable text`)
  const quoteCounts = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quoteCounts.set(match[0], (quoteCounts.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual(
    [...quoteCounts].filter(([, count]) => count % 2 !== 0), [],
    `Unbalanced dollar quote in ${path}`,
  )
  assert.match(sql, /\bbegin;/i, `${path} is not transactional`)
}
assert.match(migration, /\bcommit;\s*$/i, `${migrationPath} has no explicit transaction close`)
assert.match(rollback, /\bcommit;\s*$/i, `${rollbackPath} has no explicit transaction close`)
assert.match(seed, /\bcommit;\s*$/i, `${seedPath} has no explicit transaction close`)
assert.match(acceptance, /\brollback;[\s\S]*CP6_AUTHORITATIVE_RESIDUE_ZERO[\s\S]*$/i,
  `${acceptancePath} must roll back fixtures before an out-of-transaction residue assertion`)

assert.match(migration, /\bbegin;[\s\S]*insert into erp\.schema_migrations\(version,description\)[\s\S]*commit;\s*$/i)
assert.match(rollback, /\bbegin;[\s\S]*delete from erp\.schema_migrations where version='v2\.6\.20';[\s\S]*commit;\s*$/i)
assert.doesNotMatch(migration, /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i,
  'Forward CP6 migration contains a destructive schema/data operation')
for (const match of migration.matchAll(/\bdelete\s+from\s+erp\.([a-z0-9_]+)/gi)) {
  assert.equal(match[1], 'cp6_laundry_qc_execution_context', `Forward CP6 deletes business history from erp.${match[1]}`)
}
assert.doesNotMatch(rollback, /\btruncate\b|\bdelete\s+from\s+erp\.(?!schema_migrations\b)/i,
  'CP6 rollback deletes business history instead of refusing post-use rollback')

for (const predecessorViewSha of [
  '7897479ca27144e599b6607b60f5b9bed08bdea57171ff6ba8ec81ce46f20037',
  'efb2d15345589645f2184c3a749da42acc11bad1d4585988c3e02c5c762464e6',
  '2aa2bab69b86be921b022eaca8142a1523124c05bd639b8a641ccf572ac8ded4',
  'a823510e0e5e5f57dc124001db93ec9636e8120970281473e10fedc54089420a',
]) assert.equal(occurrences(migration, predecessorViewSha), 2,
  `CP6 must bind guard and rollback capsule to audited predecessor view ${predecessorViewSha}`)
assert.ok(migration.includes('pg_get_viewdef is not a parse/deparse fixed point'),
  'CP6 predecessor view allowlist lacks its live-UAT versus immutable-replay rationale')
assert.ok(migration.includes("v_fg_progress_def:=lower(regexp_replace("),
  'CP6 post-install guard does not normalize the installed FG progress view')
assert.ok(migration.includes(
  "'coalesce\\(lr\\.laundry_good_returned_qty_pcs,[^)]*\\)-coalesce\\(q\\.laundry_qc_accounted_qty_pcs,[^)]*\\)'",
), 'CP6 post-install guard does not require GOOD-returned minus QC-accounted readiness')
assert.ok(migration.includes(
  "'coalesce\\(lr\\.laundry_returned_qty_pcs,[^)]*\\)-coalesce\\(q\\.laundry_qc_accounted_qty_pcs,[^)]*\\)'",
), 'CP6 post-install guard does not reject total-returned minus QC-accounted readiness')
assert.doesNotMatch(migration,
  /laundry_returned_qty_pcs% - COALESCE\(q\.laundry_qc_accounted_qty_pcs/,
  'CP6 post-install guard may not use a cross-expression wildcard for readiness')
assert.equal(occurrences(migration, 'po.po_number,po.model_id,po.status,g.id'), 1,
  'Laundry workspace must group the backend PO-status reversal decision')
assert.equal(occurrences(migration, 'q.po_id,po.po_number,po.status,rev.reversal_blocker'), 1,
  'QC workspace must group the backend PO-status reversal decision')

const physicalTimeGate = migration.indexOf("if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU') then")
const closedPayloadGate = migration.indexOf("if v_action='POST_DELIVERY' then")
assert.ok(physicalTimeGate > migration.indexOf('Unsupported CP6 Laundry/QC action')
  && physicalTimeGate < closedPayloadGate,
  'CP6 physical-time domain gate must run before the generic closed-payload gate')
assert.ok(migration.includes('v_physical_at timestamptz;'),
  'CP6 must defer timestamp casting until the domain gate has validated operator input')
assert.equal(occurrences(migration, 'v_physical_at timestamptz:=v_physical_raw::timestamptz;'), 0,
  'CP6 declaration still exposes native timestamp cast errors before domain validation')
assert.ok(migration.includes('when data_exception then'),
  'CP6 must map calendar/timezone parser failures to the physical-time domain error')
assert.equal(occurrences(migration,
  'An explicit timezone-qualified physical_at is required; server time is never a transactional default'), 2,
  'CP6 must use one stable operator-facing error for missing, ambiguous, and invalid physical time')
assert.ok(acceptance.includes("'POST_DELIVERY',v_send_payload-'physical_at'"))
assert.ok(acceptance.includes('CP6 accepted a calendar-invalid physical time'))
assert.equal(acceptance.includes('CP6 POST_DELIVERY payload requires non-null key physical_at'), false,
  'Acceptance was weakened to bless a generic missing-key error for operator physical time')
assert.equal(acceptance.includes("'physical_at','2026-09-05"), false,
  'CP6 acceptance must not depend on a physical fixture time that is future at the frozen test boundary')
assert.equal(acceptance.includes("'2026-09-06','2026-09-06"), false,
  'CP6 acceptance must not report a future-dated failed-wash invoice as ordinary valid history')

const migrationBytes = Buffer.from(migration, 'utf8')
assert.equal(migrationBytes.at(-1), 10, 'CP6 migration must have one final LF excluded from platform statements')
const migrationFileSha = sha256(migrationBytes)
const ledgerSha = sha256(migrationBytes.subarray(0, -1))
assert.equal(occurrences(rollback, ledgerSha), 4,
  'CP6 rollback must bind both platform guards, actual own-version resolution, and its exact delete to no-terminal-LF statement bytes')
assert.equal(occurrences(rollback, migrationFileSha), 4,
  'CP6 rollback must bind both platform guards, actual own-version resolution, and its exact delete to full-file hosted statement bytes')
assert.match(workflow, new RegExp(`test "\\$\\(wc -c < "\\$migration_source"\\)" = '${migrationBytes.length}'`),
  'CP6 workflow byte count is stale')
assert.ok(workflow.includes(`${migrationFileSha}  ${migrationPath}`), 'CP6 workflow file SHA-256 is stale')
assert.ok(workflow.includes(`= '${ledgerSha}'`), 'CP6 workflow platform-ledger digest is stale')
assert.ok(occurrences(workflow, migrationFileSha) >= 3,
  'CP6 workflow does not prove the full-file hosted ledger shape and tamper rejection')
assert.ok(workflow.includes('\\set migration_source_b64 `python3 -c'),
  'CP6 workflow does not stream exact statement bytes into a psql-local variable')
assert.ok(!workflow.includes('-v migration_source_b64="$migration_source_b64"'),
  'CP6 workflow passes the 232 KiB statement through an argv entry and will exceed MAX_ARG_STRLEN')

function assertWorkflowShellSyntax(stepName) {
  const marker = `      - name: ${stepName}`
  const stepStart = workflow.indexOf(marker)
  assert.ok(stepStart >= 0, `CP6 workflow step is missing: ${stepName}`)
  const runMarker = '        run: |\n'
  const runStart = workflow.indexOf(runMarker, stepStart)
  assert.ok(runStart >= 0, `CP6 workflow shell body is missing: ${stepName}`)
  const bodyStart = runStart + runMarker.length
  const nextStep = workflow.indexOf('\n      - name:', bodyStart)
  const body = workflow.slice(bodyStart, nextStep < 0 ? workflow.length : nextStep)
    .split('\n')
    .map((line) => line.startsWith('          ') ? line.slice(10) : line)
    .join('\n')
  const parsed = spawnSync('bash', ['-n'], { input: body, encoding: 'utf8' })
  assert.equal(parsed.status, 0,
    `CP6 workflow shell syntax failed for ${stepName}: ${parsed.stderr}`)
}

assertWorkflowShellSyntax('Roll back v2.6.20a then prove v2.6.20 UAT-version portability and exact rollback')
assertWorkflowShellSyntax('Reject tampered statement bytes then roll back connector-shaped v2.6.19c')

const backendActionBlock = migration.match(/if v_action not in\(\s*([\s\S]*?)\s*\) then/)
assert.ok(backendActionBlock, 'CP6 backend action allowlist not found')
const expectedActions = [
  'POST_DELIVERY', 'POST_RECEIPT', 'POST_FAILED_WASH', 'REVERSE_DELIVERY',
  'REVERSE_RECEIPT', 'POST_FINAL_SKU', 'REVERSE_FINAL_SKU',
]
assert.deepEqual(literals(backendActionBlock[1]), expectedActions, 'CP6 backend action vocabulary drifted')
const modelActionBlock = model.match(/export type LaundryQcAction\s*=([\s\S]*?)\n\n/)
assert.ok(modelActionBlock, 'CP6 frontend action type not found')
assert.deepEqual(literals(modelActionBlock[1]), expectedActions, 'CP6 frontend/backend action vocabulary differs')
const hookActionBlock = hook.match(/const actions = new Set<LaundryQcAction>\(\[([\s\S]*?)\]\)/)
assert.ok(hookActionBlock, 'CP6 persisted-envelope action allowlist not found')
assert.deepEqual(literals(hookActionBlock[1]), expectedActions, 'CP6 envelope/backend action vocabulary differs')
assert.equal(expectedActions.includes('OTHER'), false, 'Free-form OTHER may not enter conserved Laundry actions')

for (const token of [
  'Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.',
  'Laporan keuangan termasuk di dalam wilayah Keuangan.',
  'lock table erp.schema_migrations', 'DRIFT_CONCURRENT_MUTATION_DETECTED',
  'erp._cp3_assert_closed_json_object', 'CP6 POST_DELIVERY payload',
  'CP6 POST_RECEIPT payload', 'CP6 POST_FAILED_WASH payload', 'CP6 POST_FINAL_SKU payload',
  'CP6 REVERSE_DELIVERY payload', 'CP6 REVERSE_RECEIPT payload',
  'CP6 REVERSE_FINAL_SKU payload', 'for update', 'pg_advisory_xact_lock',
  "'ESTIMATED'", 'PRESERVED_UNTIL_VENDOR_INVOICE',
  'trg_guard_cp6_vendor_invoice_receipt_on_post_v2620',
  'uq_cp6_wip_reversal_source_v2620', 'Append-only inverse of WIP event',
  'CP6 Laundry delivery must contain exactly one authoritative distribution batch',
  'CP6 posted Laundry delivery requires immutable distribution batch/size lineage',
  'CP6 posted Laundry receipt requires immutable delivery batch/size lineage',
  'CP6 Laundry receipt must contain exactly one authoritative delivery line',
  'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL', 'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL',
  'CP6_LAUNDRY_BS_WIP_REVERSAL', 'source_laundry_receipt_batch_size_line_id',
  "'lineage_integrity_ok',v_lineage_issue_count=0",
  "'lineage_issue_count',v_lineage_issue_count",
  'Never hide a malformed CP6',
  'completion_mode is operational/reporting state, not browser-owned',
  'conflicts with authoritative ready-for-QC remainder',
  'actual_cost_status', 'rebuild_po_hpp', 'propagate_conversion_hpp_for_po',
  'laundry_failed_wash_attempts', 'laundry_failed_wash_batch_size_lines',
  'RETURN_UNPROCESSED', 'PHYSICAL_STAYS_AT_LAUNDRY',
  'sync_po_hpp_to_gl', 'desired_laundry_accrual', 'post_journal', 'reverse_journal',
  "or (old.status='POSTED' and new.status='REVERSED')",
]) assert.ok(migration.includes(token), `CP6 authoritative boundary token missing: ${token}`)
assert.ok(acceptance.includes('CP6 false ALL READY must fail atomically'),
  'Acceptance does not reject a false ALL_READY declaration')
assert.ok(acceptance.includes('CP6 false PARTIAL must fail atomically'),
  'Acceptance does not reject a false PARTIAL_SELECTION declaration')
assert.ok(acceptance.includes('completion-mode rejection left QC, FG, BS, finance, or idempotency residue'),
  'Acceptance does not prove false completion labels roll back every derived fact')
for (const token of [
  'Return-unprocessed is deliberately all-or-nothing: every exact sent size must return before redispatch',
  'CP6 partial full return did not fail atomically without receipt, attempt, custody, or idempotency residue',
  'v_failed_partial_return_request',
]) assert.ok(acceptance.includes(token), `Partial full-return atomic rejection proof missing: ${token}`)
assert.equal(occurrences(migration, "pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0))"), 7,
  'All seven CP6 mutations must share the same Potongan serialization fence')

for (const [signature, digest] of [
  ['erp.desired_laundry_accrual(uuid)', '4ded5af2c9c604357d18c783b00dcdb9'],
  ['erp.sync_laundry_accrual(uuid,date)', '9d5afd8d5c23e81a924a87cb4ef0037d'],
  ['erp.rebuild_po_hpp(uuid,text)', 'bf5593c35375abb35c0c6d531ee375e6'],
  ['erp.post_journal(text,uuid,date,text,jsonb)', 'dbf6138ccc575950fc6aed789863af8c'],
  ['erp.reverse_journal(uuid,text)', '6ee9da4164624f08381415b01630f323'],
]) {
  assert.ok(migration.includes(`'${signature}'::regprocedure`), `CP6 omits finance dependency ${signature}`)
  assert.ok(migration.includes(`'${digest}'`), `CP6 finance dependency digest drifted for ${signature}`)
}
const finalSkuNumberWriter = 'erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)'
assert.ok(migration.includes(`'${finalSkuNumberWriter}'::regprocedure`),
  'CP6 omits the collision-safe Final-SKU document-number writer dependency')
assert.equal(occurrences(migration, "'4704db79cbcd2ad70384c6dbdfe85572'"), 2,
  'CP6 must bind the exact predecessor Final-SKU writer into dependency and rollback-capsule guards')
assert.equal(occurrences(migration, "'38d2795520b05cd70fd7bee2c69d3afa'"), 1,
  'CP6 must bind the exact installed collision-safe Final-SKU writer digest')
assert.ok(acceptance.includes("'38d2795520b05cd70fd7bee2c69d3afa'"),
  'Acceptance does not prove the collision-safe Final-SKU writer install boundary')
assert.ok(migration.includes("upper(replace(p_client_request_id::text, '-', ''))"),
  'Final-SKU document numbers must retain all UUID entropy')
assert.equal(migration.includes("upper(substr(replace(p_client_request_id::text, '-', ''), 1, 10))"), false,
  'Final-SKU document numbers still truncate UUID entropy to a collision-prone prefix')
for (const [identity, expectedOccurrences] of [
  ['v_delivery_id', 1],
  ['v_receipt_id', 2],
]) {
  assert.equal(occurrences(migration, `upper(replace(${identity}::text,'-',''))`), expectedOccurrences,
    `Every CP6 ${identity} document number must retain all UUID entropy`)
  assert.equal(migration.includes(`upper(substr(replace(${identity}::text,'-',''),1,10))`), false,
    `CP6 ${identity} document numbers still expose a 40-bit collision surface`)
}
for (const token of [
  "right((select delivery_number from erp.laundry_deliveries where id=v_delivery),32)",
  "right((select receipt_number from erp.laundry_receipts where id=v_receipt),32)",
  "where id=v_failed_retry_receipt),32)<>upper(replace(v_failed_retry_receipt::text,'-',''))",
  "where id=v_failed_return_receipt),32)<>upper(replace(v_failed_return_receipt::text,'-',''))",
]) assert.ok(acceptance.includes(token), `Runtime full-UUID document identity proof missing: ${token}`)
assert.equal(occurrences(migration, 'count(*) from erp.cp6_v2620_rollback_capsule)<>13'), 2,
  'CP6 must bind all thirteen replaced functions/views, including receipt source/cost validation, accrual serialization, HPP, and the Final-SKU number writer, into install/post guards')
assert.ok(rollback.includes('count(*) from erp.cp6_v2620_rollback_capsule)<>13'),
  'CP6 rollback does not require the exact thirteen-object restoration capsule')
assert.ok(acceptance.includes('count(*) from erp.cp6_v2620_rollback_capsule)<>13'),
  'CP6 acceptance does not require the exact thirteen-object restoration capsule')
for (const token of [
  'posted_receipt_cost', "lrl.actual_cost_status in('ESTIMATED','FINAL')",
  "lrl.actual_cost_status='ESTIMATED'", 'unbilled_actual_estimate',
  'greatest(qty_sent_pcs-costed_qty,0)*coalesce(estimated_rate_snapshot,0)',
  "pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0))",
  'first-row Laundry accrual serialization is absent',
  'one process/rate while WIP/accrued manufacturing still uses another',
  'revoke all on function erp.desired_laundry_accrual(uuid)',
]) assert.ok(migration.includes(token), `Laundry actual-rate accrual reconciliation missing: ${token}`)
for (const token of [
  "md5(pg_get_functiondef('erp.validate_laundry_receipt_line()'::regprocedure))",
  "'erp.validate_laundry_receipt_line()'::regprocedure",
  "to_regprocedure('erp.validate_laundry_receipt_line()') is null",
  'create or replace function erp.validate_laundry_receipt_line()',
  "c.action='POST_FAILED_WASH'", "c.permission_key='production.laundry.post'",
  "(c.payload->>'delivery_id')::uuid=v_receipt_delivery",
  "(c.payload->>'wash_process_id')::uuid=new.actual_wash_process_id",
  "new.actual_cost:=round(v_failed_qty*new.actual_rate_snapshot,2)",
  'select a.qty_attempted_pcs into v_existing_failed_qty',
  "new.actual_cost:=round(v_existing_failed_qty*new.actual_rate_snapshot,2)",
  'Final failed-wash invoice cost must equal immutable attempt quantity times rate',
  'Existing paid failed-wash cost must remain ESTIMATED until an exact invoice finalizes it',
  "new.actual_cost:=(new.qty_good_received+new.qty_bs_laundry)*new.actual_rate_snapshot",
  'Paid failed-wash cost requires one exact zero-output facade context',
  "not like '%v_failed_context_count%POST_FAILED_WASH%v_existing_failed_qty%'",
]) assert.ok(migration.includes(token), `Failed-wash cost formula does not preserve the physical-receipt validator boundary: ${token}`)
assert.equal(occurrences(workflow, "'receipt_cost_validator_sha256'"), 3,
  'Full-schema proof must capture, restore, and compare the predecessor Laundry receipt-cost validator')
for (const token of [
  "to_regprocedure('erp.guard_laundry_receipt_source_capacity_on_post()') is null",
  "md5(pg_get_functiondef(\n    'erp.guard_laundry_receipt_source_capacity_on_post()'::regprocedure",
  "'erp.guard_laundry_receipt_source_capacity_on_post()'::regprocedure",
  'create or replace function erp.guard_laundry_receipt_source_capacity_on_post()',
  'v_cp6_full_return_context boolean:=false',
  "c.action='POST_FAILED_WASH'", "c.payload->>'custody_outcome'='RETURN_UNPROCESSED'",
  "rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'",
  "not(v_delivery_status='REVERSED' and v_cp6_full_return_context)",
  "not like '%v_cp6_full_return_context%RETURN_UNPROCESSED%CP6_LAUNDRY_DELIVERY_WIP_REVERSAL%'",
]) assert.ok(migration.includes(token), `Full-return receipt source exception is not exact and fail-closed: ${token}`)
assert.equal(occurrences(workflow, "'receipt_source_guard_sha256'"), 3,
  'Full-schema proof must capture, restore, and compare the predecessor Laundry receipt source guard')
for (const token of [
  'Failed-wash receipt must contain exactly one canonical cost line',
  'Failed-wash service cost must not create physical Good/BS receipt facts',
  'Failed-wash canonical cost line is not an exact zero-output estimate',
  'Failed-wash attempted size total does not equal its canonical cost quantity',
  'Failed-wash attempted size facts do not belong to the exact delivery capacity',
]) assert.ok(migration.includes(token), `Failed-wash post invariant is not independently diagnosable: ${token}`)
for (const token of [
  'CP6 delivery-time target rate', 'CP6 receipt-time actual-process estimate',
  "erp.desired_laundry_accrual(v_po)<>82", 'prior_actual_rate_snapshot from erp.vendor_invoice_items',
  '<>9', 'Six physically returned pieces at final invoice rate 11',
  'Replacement invoice: six pieces at actual rate 10',
  "'late_invoice_hpp',94,'replacement_invoice_hpp',88",
  "where id=v_failed_return_receipt_line)<>'ESTIMATED'",
  'where id=v_failed_return_receipt_line)<>90',
]) assert.ok(acceptance.includes(token), `Different target/actual Laundry rate proof missing: ${token}`)

for (const token of [
  'Human identity is Brand -> SKU number -> Model',
  "'BRANDSKU:'||new.brand_id::text||':'||lower(btrim(new.sku))",
  'p.brand_id=new.brand_id', 'lower(btrim(p.sku))=lower(btrim(new.sku))',
  'Nomor SKU % untuk merek dan size ini sudah punya identitas aktif',
  'Varian size untuk merek + nomor SKU yang sama wajib memakai model dan warna yang sama',
  'PRODUCT_IDENTITY_BRAND_SKU_VARIANT_MISMATCH',
  'Identitas dan periode SKU immutable setelah row dibuat',
  "'SKUROOT:'||new.identity_root_id::text",
  'Versi SKU non-root wajib menunjuk predecessor',
  'Satu versi SKU tidak boleh memiliki lebih dari satu successor',
  'Perubahan periode SKU akan memutus rantai successor yang sudah ada',
  'PRODUCT_SUCCESSOR_BRANCH',
  'pre-existing product identity ambiguity: repair Brand + SKU + Model history before install',
]) assert.ok(migration.includes(token), `Brand-scoped SKU invariant missing: ${token}`)
assert.match(migration, /lock table erp\.schema_migrations,\s+erp\.products,\s+supabase_migrations\.schema_migrations in share row exclusive mode;/,
  'CP6 installer does not serialize its pre-existing product-identity decision')
assert.ok(acceptance.includes("v_cross_brand_same_sku,'CP6-SKU-S',v_other_model,v_second_brand"),
  'Acceptance does not prove same SKU number may use another model under another brand')
for (const token of [
  'CP6 allowed duplicate brand + SKU number + size identity',
  'CP6 allowed one brand + SKU number to drift across model/color by size',
  'CP6 product checker rejected valid Brand/SKU variants or version lineage',
  'CP6 allowed a product version with a missing identity root',
  'CP6 allowed a non-root product version without a predecessor',
  'CP6 allowed a branched product successor chain',
  'CP6 allowed a product period update to rewrite historical stock/HPP identity',
  'CP6 allowed a product identity update to rewrite historical stock/HPP meaning',
  'CP6 immutable identity guard blocked safe display-name maintenance',
  'CP6 product lookup violated Brand -> SKU -> Model identity or leaked Pattern into SKU',
  'CP6_LATE_RETURN_PROOF_ROLLBACK',
  'CP6 late-return-after-claim-reversal conservation diverged',
  'CP6 cross-Potongan/PO Final-SKU rejection failed or left finance/stock/HPP residue',
  'CP6 trusted writer bypassed the cross-Potongan/PO source trigger',
  'CP6 trusted receipt-linked QC writer bypassed exact batch/size lineage',
  'CP6 exact receipt/batch/size cap failed or left QC residue',
  'CP6 facade accepted quantity above authoritative Potongan remainder',
  'CP6 trusted delivery writer bypassed exact batch/size lineage or left residue',
  'CP6 trusted receipt writer bypassed exact batch/size lineage or left residue',
  'CP6 trusted receipt writer created a multi-line receipt or left residue',
  'CP6 reversal chain did not return to an exact, readable lineage state',
]) assert.ok(acceptance.includes(token), `Product identity acceptance proof missing: ${token}`)

for (const token of [
  'v_source_group is distinct from new.cutting_group_id',
  'v_source_po is distinct from v_qc_po',
  'Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt',
  'QC batch/size source belongs to a different Potongan/PO',
  'New receipt-linked QC facts do not',
  'CP6_LAUNDRY_SIZE_LINEAGE_REQUIRED',
  'and dl.id=rl.delivery_line_id', 'and r.delivery_id=d.id',
  'and p.cutting_group_id=dl.cutting_group_id', 'and s.id=sx.size_id',
]) assert.ok(migration.includes(token), `Cross-Potongan/PO Final-SKU lineage guard missing: ${token}`)

for (const token of [
  'rev.reversal_blocker is null as reversible',
  'rr.reversal_blocker is null',
  'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.',
  'FG hasil QC masih dipakai transaksi downstream aktif.',
  'Histori WIP surat kirim tidak utuh; reversal dikunci untuk investigasi.',
]) assert.ok(migration.includes(token), `Authoritative reversal affordance missing: ${token}`)
for (const token of [
  'CP6 QC workspace did not expose the authoritative reversal decision',
  'CP6 Laundry workspace offered a reversal that backend authority must reject',
]) assert.ok(acceptance.includes(token), `Reversal-affordance acceptance proof missing: ${token}`)
for (const token of [
  'reversible: boolean; reversal_blocker: string | null',
  'Status dan penghambat reversal penerimaan kontradiktif.',
  'Status dan penghambat reversal pengiriman kontradiktif.',
  'Status dan penghambat reversal QC kontradiktif.',
]) assert.ok(model.includes(token), `Frontend reversal contract missing: ${token}`)
for (const token of [
  '!receipt.reversible', '!canReverse',
  'receipt.reversal_blocker', 'delivery.reversal_blocker',
]) assert.ok(laundryPage.includes(token), `Laundry reversal UX guard missing: ${token}`)
for (const token of [
  '!row.reversible', '!canReverse', 'row.reversal_blocker',
  'Cuci gagal berbayar dicatat dari tab Laundry sebagai attempt biaya terpisah',
  'seluruh barang kembali ke Jahit',
]) assert.ok(qcPage.includes(token), `QC reversal UX guard missing: ${token}`)
assert.ok(!qcPage.includes('tetap ditahan sampai alur hutang vendor'),
  'QC UI still claims the authoritative paid failed-wash flow is unavailable')
for (const token of [
  'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.',
  'FG hasil QC masih dipakai transaksi downstream aktif.',
  'CP6 paid failed-wash retry posts cost without inventing a physical receipt',
  'CP6 paid full return is exact, all-or-nothing, and retires the committed form',
  "expect.poll(() => calls.actions.length).toBe(1)",
  "toBeDisabled()",
]) assert.ok(browser.includes(token), `Browser reversal-affordance proof missing: ${token}`)

for (const token of [
  'platform ledger statement digest is ambiguous',
  'a successor migration is already installed',
  'post-install CP6 physical/financial/stock/HPP/idempotency/audit history exists',
  'exact rollback capsule is missing', 'installed object/capsule drift',
  'rollback failed exact ACL restoration', 'rollback left CP6 schema residue',
]) assert.ok(rollback.includes(token), `CP6 rollback refusal/restoration proof missing: ${token}`)
for (const token of [
  "to_regclass('erp.idx_failed_wash_source_size_v2620') is not null",
  "to_regprocedure('erp.guard_cp6_failed_wash_attempt_v2620()') is not null",
  "to_regprocedure('erp.guard_cp6_failed_wash_size_v2620()') is not null",
  "to_regprocedure('erp.get_laundry_qc_workspace_v1(text,text)') is not null",
  "to_regprocedure('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)') is not null",
  "'trg_guard_cp6_vendor_invoice_receipt_on_post_v2620'",
]) assert.ok(rollback.includes(token), `CP6 rollback schema-residue guard missing: ${token}`)

for (const token of [
  'CP6 coerced a string into a physical integer quantity',
  'CP6 rounded a fractional physical return into integer pcs',
  'payload contains unexpected key qty_sent',
  'delivery posting/idempotent replay diverged',
  'receipt posting/idempotent replay diverged',
  'QC/Final-SKU posting or replay diverged',
  'client_request_id was already used with a different payload',
  'late Laundry invoice did not atomically finalize AP/accrual/HPP/FG',
  'replacement invoice did not replace financial state atomically',
  'invoice replacement/retry left financial residue or duplicated history',
  'append-only Laundry WIP reversal history is not net zero',
  'v_rare_flow_base',
  'CP6 rare-flow fixture has no linked physical delivery return',
  "replace((v_rare_flow_base+interval '1 second')::text,' ','T')",
  "replace((v_rare_flow_base+interval '4 seconds')::text,' ','T')",
  'controlled reversal lost history or left active stock/accrual',
  'paid retry did not preserve WIP/accrual/HPP/custody separation',
  'paid full return did not conserve WIP/accrual without manufacturing FG/HPP',
  'malformed failed-wash invoice did not fail without receipt, accrual, AP, HPP, FG, or journal residue',
  'did not split WIP into exact accrual/AP without manufacturing FG/HPP',
  "'failed_wash_wip_path',jsonb_build_array(180,180,190,180,90,0)",
  "'failed_wash_hpp_without_fg',0",
  'cost reversal rewrote the immutable full-return custody fact',
  'paid failed-wash reversal lost history or left cost/WIP residue',
  'CP6_AUTHORITATIVE_ACCEPTANCE_PASS', 'CP6_AUTHORITATIVE_RESIDUE_ZERO',
]) assert.ok(acceptance.includes(token), `CP6 acceptance proof missing: ${token}`)
assert.equal(occurrences(acceptance, "account_id=erp.account_id('WIP'))<>180"), 4,
  'Paid failed-wash proof must pin WIP 180 after retry, full return, malformed-invoice rollback, and invoice reversal')
assert.equal(occurrences(acceptance, "account_id=erp.account_id('WIP'))<>190"), 1,
  'Paid failed-wash invoice proof must pin WIP 190 as accrual 90 plus AP 100')
assert.equal(occurrences(acceptance, "account_id=erp.account_id('WIP'))<>90"), 1,
  'Reversing one paid attempt must leave exactly one WIP estimate of 90')
assert.equal(occurrences(acceptance,
  "account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-180"), 4,
  'Paid failed-wash proof must pin accrued manufacturing at 180 in every equivalent state')
assert.equal(occurrences(acceptance,
  "account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-90"), 2,
  'Invoice finalization and one-attempt reversal must pin accrued manufacturing at 90')

for (const token of [
  "case when to_regclass('erp.laundry_delivery_batch_size_lines') is null",
  "if to_regclass('erp.laundry_delivery_batch_size_lines') is not null then",
  'v_cp6_distribution_allocation', 'v_cp6_delivery_batch_size',
  'v_cp6_receipt_batch_size', 'v_cp6_late_receipt_batch_size',
  "set picked_up_at='2026-08-20 08:30:00+00'",
  "executor_name='CP5 CP6 Mandor',status='PICKED_UP'",
  "update erp.laundry_deliveries set status='SENT' where id=v_delivery",
  'v_response:=erp.post_laundry_receipt_v2(',
  'The CP5 behavior remains under test',
]) assert.ok(cp5Recovery.includes(token),
  `CP5-under-CP6 immutable-lineage regression proof missing: ${token}`)
assert.equal(/disable\s+trigger|session_replication_role/i.test(cp5Recovery), false,
  'CP5-under-CP6 regression must not bypass authoritative database triggers')

const rpcNames = [...hook.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)].map((match) => match[1])
assert.deepEqual([...new Set(rpcNames)].sort(), [
  'erp_get_laundry_qc_workspace_v1', 'erp_save_laundry_qc_action_v1',
], 'CP6 browser boundary must use exactly two public RPC facades')
assert.equal(rpcNames.filter((name) => name === 'erp_save_laundry_qc_action_v1').length, 1,
  'CP6 mutations must share one exact-envelope send path')
for (const token of [
  'globalThis.localStorage?.setItem', 'globalThis.localStorage?.getItem(key) === serialized',
  'globalThis.crypto.randomUUID()', 'isExactCommittedResponse',
  'candidate.fingerprint !== fingerprint', 'busyRef.current', 'workspaceStale',
  'workspaceReadyRef.current = false', '!workspaceReadyRef.current',
  'committedRefreshRequired', 'retireCommittedForm()', 'globalThis.navigator?.locks',
  "mode: 'exclusive', ifAvailable: true", "globalThis.addEventListener('storage'",
  'erp.cp6.pending-mutation.v1:', 'preserveExactPending',
  'Reconcile wajib memakai UUID/payload yang sama',
]) assert.ok(hook.includes(token), `CP6 UI reliability lifecycle missing: ${token}`)
assert.doesNotMatch(hook, /erp\.cp6\.\$\{scope\.toLowerCase\(\)\}\.pending-mutation/,
  'CP6 pending envelope is scope-local and can be overwritten across Laundry/QC tabs')
for (const token of [
  'reconciles an ambiguous response with the exact same UUID, payload, and version',
  'retires a committed form and keeps it dead after refetch failure then recovery',
  'locks the writer synchronously when a refetch starts before React can rerender',
  'fails closed when a persisted envelope is corrupt',
  'refuses a second mounted writer while the global cross-tab envelope is in flight',
  'fails closed without Web Locks and sends no mutation',
]) assert.ok(hookTest.includes(token), `CP6 hook lifecycle proof missing: ${token}`)

assert.equal(occurrences(laundryPage, "const [physicalAt, setPhysicalAt] = useState('')"), 3,
  'Laundry physical timestamps must start blank for dispatch, receipt, and failed wash')
assert.equal(occurrences(qcPage, "const [physicalAt, setPhysicalAt] = useState('')"), 1,
  'QC physical timestamp must start blank')
assert.equal(laundryPage.includes('localNow'), false, 'Laundry UI infers physical time from page/browser clock')
assert.equal(qcPage.includes('localNow'), false, 'QC UI infers physical time from page/browser clock')
assert.equal(occurrences(laundryPage, 'cp6WibPhysicalTimeToIso(physicalAt)'), 3,
  'All Laundry physical timestamps must use the fixed business-time serializer')
assert.equal(occurrences(qcPage, 'cp6WibPhysicalTimeToIso(physicalAt)'), 1,
  'QC physical timestamp must use the fixed business-time serializer')
assert.equal(occurrences(laundryPage, 'useEffect(() => setConfirmed(false), [workspace])'), 3,
  'Laundry acknowledgement must expire after every authoritative refetch')
assert.equal(occurrences(qcPage, 'useEffect(() => setConfirmed(false), [workspace])'), 1,
  'QC acknowledgement must expire after every authoritative refetch')
for (const token of ['WAKTU FISIK KELUAR', 'WAKTU FISIK KEMBALI', 'WAKTU KEJADIAN FISIK']) {
  assert.ok(laundryPage.includes(token), `Laundry UI physical-time input missing: ${token}`)
}
assert.ok(qcPage.includes('WAKTU FISIK QC'), 'QC UI physical-time input missing')
assert.ok(laundryPage.includes('MEREK → NOMOR SKU → MODEL'), 'Laundry identity order drifted')
assert.ok(qcPage.includes('MEREK → NOMOR SKU → MODEL'), 'QC identity order drifted')
for (const token of [
  'Hak kerja · {roleName}', 'Mode lihat saja untuk {action}.',
  'Form dikunci; data tetap bisa dilihat.',
]) assert.ok(permissionNotice.includes(token), `CP6 permission UX invariant missing: ${token}`)
for (const token of [
  'PAGAR KEAMANAN DATA', 'Ini bukan masalah hak akses role Anda.',
  'Nota FG belum aman untuk disimpan', 'Tidak ada data yang dihapus atau diposting.',
  'Untuk sekarang, simpan Final SKU dari halaman QC',
]) assert.ok(fgBoundary.includes(token), `CP6 blocked Nota FG operator guidance missing: ${token}`)
assert.doesNotMatch(fgBoundary, /SAFETY BOUNDARY|hard-coded|subtotal React/,
  'Blocked Nota FG explains implementation jargon instead of the operator decision')
assert.match(laundryPage, /actionLocked = writerLocked \|\| !actionAllowed/)
assert.match(qcPage, /actionLocked = writerLocked \|\| !canPost/)
const cp6FontSizes = [...workspaceCss.matchAll(/font-size:\s*([\d.]+)px/g)].map((match) => Number(match[1]))
assert.ok(cp6FontSizes.length > 0 && Math.min(...cp6FontSizes) >= 11,
  'CP6 operator UI reintroduced text smaller than 11px')
assert.match(workspaceCss, /min-height:\s*42px/)
assert.match(workspaceCss, /height:\s*44px/)
for (const token of [
  "CP6_BUSINESS_TIME_ZONE = 'Asia/Jakarta'", "CP6_BUSINESS_UTC_OFFSET = '+07:00'",
  'never the browser/device timezone',
]) assert.ok(businessTime.includes(token), `Explicit WIB conversion invariant missing: ${token}`)
for (const token of [
  "toBe('2026-09-04T01:15:00.000Z')", 'rejects impossible or ambiguous wall-clock values',
]) assert.ok(businessTimeTest.includes(token), `WIB conversion test missing: ${token}`)
assert.ok(browser.includes("getByRole('button', { name: /Post pengiriman atomic/ })"), 'CP6 browser send proof missing')
assert.ok(browser.includes('await expect(post).toBeDisabled()'), 'CP6 browser does not prove blank physical time blocks posting')
assert.equal(occurrences(browser, "physical_at: '2026-09-04T01:00:00.000Z'"), 5,
  'Browser contract must prove all five asserted 08:00 WIB inputs serialize to exact UTC instants')
assert.ok(browser.includes('calls.workspace.length).toBe(2)'), 'CP6 browser does not prove refetch expires acknowledgement')
for (const token of [
  'view-only role sees server facts but every mutation control starts locked',
  "permissions: ['production.laundry.view']",
  "getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toBeDisabled()",
  'two live tabs serialize one global envelope and send at most one operator intent',
  'firstCalls.actions.length + secondCalls.actions.length).toBe(1)',
]) assert.ok(browser.includes(token), `CP6 browser reliability/permission proof missing: ${token}`)
const firstTabPrepared = browser.indexOf("prepareValidLaundrySend(page, 'Tab pertama mencatat serah terima yang sama')")
const secondTabOpened = browser.indexOf('const secondPage = await context.newPage()')
assert.ok(firstTabPrepared > 0 && secondTabOpened > firstTabPrepared,
  'CP6 browser must prepare the first operator form before opening the second tab')
for (const token of [
  ".toHaveValue('Tab pertama mencatat serah terima yang sama')",
  "getByRole('checkbox', { name: laundrySendConfirmation, exact: true })).toBeChecked()",
]) assert.ok(browser.includes(token), `CP6 browser does not prove first-tab form preservation: ${token}`)
assert.match(authPolicy, /sameVerifiedUser && \(event === 'TOKEN_REFRESHED' \|\| event === 'SIGNED_IN'\)/,
  'Same-user cross-tab sign-in would remount and erase an in-progress operator form')
assert.ok(authPolicyTest.includes("planAuthEvent(authorized, 'SIGNED_IN', authUserId)"),
  'Auth policy unit proof omits same-user cross-tab SIGNED_IN')
assert.ok(authLifecycleTest.includes('keeps same-user forms mounted while a cross-tab sign-in is revalidated'),
  'Mounted auth lifecycle proof omits same-user form preservation')

assert.match(masterPage, /isProduct\?<>{brandField&&renderField\(brandField,true\)}<label><span>NOMOR SKU<\/span>[\s\S]*?{modelField&&renderField\(modelField\)}/,
  'Product editor is not ordered Merek -> Nomor SKU -> Model')
assert.ok(masterPage.includes('Nomor yang sama boleh dipakai merek berbeda'), 'Master copy omits brand-scoped SKU semantics')
assert.ok(masterPage.includes('pola tidak disimpan di SKU'), 'Master copy permits Pattern to be stored on SKU')
for (const token of [
  'MEREK', 'NOMOR SKU', 'MODEL', 'NAMA PRODUK / DESKRIPSI',
  "expect(fieldLabels).not.toContain('POLA')",
]) assert.ok(masterTest.includes(token), `Product-master DOM proof missing: ${token}`)

for (const token of [
  'Konservasi size batch siap Laundry tidak konsisten.',
  'duplikat pada payload authoritative.', 'kontradiktif pada payload authoritative.',
  'bukan timestamp authoritative valid.', 'Number.isSafeInteger',
  'CP6_V2620', 'no_fixture_fallback: true',
  'lineage_integrity_ok: true', 'lineage_issue_count: 0',
]) assert.ok(model.includes(token), `CP6 response parser invariant missing: ${token}`)
for (const token of [
  'rejects changed or deleted quantity conservation',
  'rejects null/string numeric coercion and malformed authoritative timestamps',
  'accepts one Brand + SKU across exact sizes and the same number under another Brand',
  'rejects ambiguous same-size identity or model/color drift inside one Brand + SKU',
  'rejects contradictory lookup metadata and Potongan versions before rendering a writer',
  'requires every reversal affordance to match the backend blocker decision',
  'fails closed when two rate versions overlap at the physical time',
  'fails closed when backend reports any CP6 lineage issue',
  'silently disables the paid-failure contract',
]) assert.ok(modelTest.includes(token), `CP6 parser test coverage missing: ${token}`)

const raceKeys = [...race.matchAll(/report\['races'\]\['([^']+)'\]\s*=/g)].map((match) => match[1])
assert.deepEqual(raceKeys, [
  'first_accrual_creation', 'post_delivery',
  'failed_wash_vs_post_receipt', 'post_receipt',
  'vendor_invoice_vs_reverse_receipt',
  'vendor_invoice_vs_final_sku', 'vendor_invoice_reversal_vs_final_sku',
  'invoice_reversal_vs_replacement_post',
  'final_sku_vs_vendor_invoice', 'final_sku_vs_vendor_invoice_reversal',
  'post_final_sku', 'final_sku_vs_reverse_receipt',
], 'CP6 concurrency proof must retain twelve named races including the audited invoice replacement schedule')

for (const token of [
  'CP6-FIRST-ACCRUAL-PO',
  "erp.desired_laundry_accrual('c8d40000-0000-4000-8000-000000000001')<>70",
  'CP6 first-row accrual race seed is not pristine',
]) assert.ok(seed.includes(token), `First-row accrual race seed missing: ${token}`)

const requestBlockStart = race.indexOf('REQUESTS = {')
const requestBlockEnd = race.indexOf('\n}\n\n', requestBlockStart)
assert.ok(requestBlockStart >= 0 && requestBlockEnd > requestBlockStart,
  'CP6 concurrency request-ID fixture block is missing')
const requestIds = [...race.slice(requestBlockStart, requestBlockEnd)
  .matchAll(/'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'/g)]
  .map((match) => match[1])
assert.ok(requestIds.length >= 2 && new Set(requestIds).size === requestIds.length,
  'CP6 concurrency proof needs distinct valid request UUIDs')
const requestPrefixCounts = new Map()
for (const requestId of requestIds) {
  const prefix = requestId.replaceAll('-', '').slice(0, 10)
  requestPrefixCounts.set(prefix, (requestPrefixCounts.get(prefix) ?? 0) + 1)
}
assert.ok([...requestPrefixCounts.values()].some((count) => count >= 2),
  'CP6 race fixtures must retain distinct UUIDs sharing the legacy ten-hex prefix collision')
for (const token of [
  'run_first_accrual_creation_race',
  "'first_accrual_invariants'", "'state_rows': 1", "'event_rows': 1",
  "'event_delta': 70", "'journal_rows': 1",
  'Second first-accrual caller did not wait for the PO_HPP fence',
  "'receipt_cost_status': 'ESTIMATED'", "'laundry_accrual': 70",
  "'wip_net': 0", "'fg_net': 70", "'vendor_ap_net': 0",
  "'unbalanced_journals': 0", "'loser_idempotency_rows': 0",
  "'receipt_actual_cost': 90", "'current_hpp_total': 90",
  "'vendor_ap_net': -90", "'winner_facade_idempotency_rows': 15",
  "'winner_facade_request_ids': 15",
  "'winner_nested_final_sku_idempotency_rows': 6",
  "'winner_nested_final_sku_request_ids': 6",
  "'unexpected_winner_idempotency_rows': 0",
  'winner_facade_expectations', 'final_sku_requests',
  "'cp6_laundry_qc_action_v1:post_final_sku'",
  "i.operation_name='post_fg_partial_completion_v2'",
  "'failed_wash_attempt_history': 1", "'failed_wash_active_receipts': 0",
  "'failed_wash_physical_lines': 0", 'POST_FAILED_WASH_VS_POST_RECEIPT',
  "'voided_hpp_history_lots': 5", "l.lot_origin='PRODUCTION'",
  'real serialization wait', 'invoice finalization owns the receipt lock',
  'invoice cost/AP commits before a waiting Final-SKU reads HPP',
  'invoice reversal restores estimate before waiting Final-SKU HPP',
  'Hold Final-SKU uncommitted, then prove invoice lifecycle recosts it',
  'The winner action itself establishes the canonical runtime lock order.',
]) assert.ok(race.includes(token), `CP6 concurrency invariant missing: ${token}`)
assert.equal(race.includes('lock_sql'), false,
  'CP6 race fixture must not pre-lock a row before the runtime advisory fence')
assert.ok(race.includes('Laundry receipt requires an active SENT/PARTIAL_RETURN delivery'),
  'Serialized duplicate receipt does not accept the authoritative terminal-status rejection')

const invoiceFixtureStart = race.indexOf('def create_vendor_invoice(')
const invoiceFixtureEnd = race.indexOf('\ndef reverse_vendor_invoice(', invoiceFixtureStart)
assert.ok(invoiceFixtureStart >= 0 && invoiceFixtureEnd > invoiceFixtureStart,
  'CP6 race fixture vendor-invoice helper is missing')
const invoiceFixture = race.slice(invoiceFixtureStart, invoiceFixtureEnd)
assert.equal(occurrences(invoiceFixture, 'cur.execute('), 2,
  'Vendor-invoice parent and item inserts must use two Psycopg-safe statements')
assert.equal(/vendor_invoices[\s\S]*;\s*insert into erp\.vendor_invoice_items/.test(invoiceFixture), false,
  'Vendor-invoice race fixture must not send multiple commands as one prepared statement')
assert.ok(race.includes('def set_operator_claims(cur):'),
  'CP6 race harness lacks a claims-only backend execution context')
assert.equal(occurrences(race, 'set_operator_claims(cur)'), 12,
  'Every internal accrual/vendor-invoice lifecycle path must retain backend privilege with operator claims')
assert.equal(
  /set_operator_context\(cur\)\s+(?:if reverse_invoice:\s+)?cur\.execute\(\s*['"]select erp\.(?:post|reverse)_vendor_invoice/.test(race),
  false,
  'Authenticated browser role must not be used to call private vendor-invoice routines',
)
const vendorApQuery = "where l.vendor_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')"
const fakePoApQuery = "where l.po_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')"
assert.equal(occurrences(race, vendorApQuery), 2,
  'Both race finance snapshots must read the vendor-scoped AP control line')
assert.equal(occurrences(race, fakePoApQuery), 0,
  'Race finance snapshots must not invent a PO dimension for a multi-PO invoice')
assert.ok(race.includes('PO, PO, PO, PO, VENDOR,'),
  'Invoice/Final-SKU snapshot does not bind the vendor AP placeholder')
assert.ok(race.includes('PO, receipt_line, PO, PO, PO, PO, VENDOR,'),
  'Final residue snapshot does not bind the vendor AP placeholder')

const postDeliveryStart = migration.lastIndexOf("if v_action='POST_DELIVERY' then")
const postReceiptStart = migration.lastIndexOf("elsif v_action='POST_RECEIPT' then")
const postDeliveryAction = migration.slice(postDeliveryStart, postReceiptStart)
assert.ok(postDeliveryAction.indexOf("pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0))")
  < postDeliveryAction.indexOf('for update of b,p'),
  'POST_DELIVERY must acquire the Potongan fence before source row locks')
assert.ok(postDeliveryAction.includes('changed while waiting for the Potongan fence; refetch before retrying'),
  'POST_DELIVERY does not fail closed when its unlocked identity lookup changes')

for (const token of [
  'npm run check:cp6', 'python -m py_compile scripts/cp6_laundry_qc_concurrency.py',
  'test:browser:cp6', 'V2620_MIGRATION_SHA256.txt',
  'CP6_AUTHORITATIVE_ACCEPTANCE_PASS', 'CP6_AUTHORITATIVE_RESIDUE_ZERO',
  'vendor_invoice_vs_reverse_receipt', 'vendor_invoice_vs_final_sku',
  'vendor_invoice_reversal_vs_final_sku',
  'final_sku_vs_vendor_invoice', 'final_sku_vs_vendor_invoice_reversal',
  'final_sku_vs_reverse_receipt', 'failed_wash_vs_post_receipt',
  'first_accrual_creation', "'event_delta': 70",
  'V2620_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2620_PREEXISTING_PRODUCT_AMBIGUITY_REJECTION.log',
  'V2620A_ROLLBACK_POST_USE_REJECTION.log', 'FINAL_RECONCILIATION.json',
  "'production_go',false", 'rm -rf supabase/.temp',
]) assert.ok(workflow.includes(token), `CP6 full-schema workflow missing: ${token}`)
for (const key of [
  'desired_laundry_accrual_sha256', 'sync_laundry_accrual_sha256',
  'rebuild_po_hpp_sha256', 'final_sku_number_writer_sha256',
]) assert.equal(occurrences(workflow, key), 3,
  `CP6 rollback proof must snapshot, resnapshot, and compare ${key}`)
for (const token of [
  "to_regclass('erp.idx_failed_wash_source_size_v2620') is not null",
  "to_regprocedure('erp.guard_cp6_failed_wash_attempt_v2620()') is not null",
  "to_regprocedure('erp.guard_cp6_failed_wash_size_v2620()') is not null",
  "to_regprocedure('erp.get_laundry_qc_workspace_v1(text,text)') is not null",
  "to_regprocedure('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)') is not null",
  "'trg_guard_cp6_vendor_invoice_receipt_on_post_v2620'",
]) assert.ok(workflow.includes(token), `CP6 rollback/final schema-residue proof missing: ${token}`)
assert.match(browserConfig, /testMatch: 'cp6-laundry-qc\.spec\.ts'/)
assert.match(browserConfig, /ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1'/)
assert.match(packageJson, /"check:cp6": "node scripts\/check-cp6-boundary\.mjs && node scripts\/check-cp6-audit-closure\.mjs"/)
assert.match(packageJson, /"test:security":[^\n]*npm run check:cp6/)
assert.match(packageJson, /"check:backend": "node scripts\/check-predecessor-backend-ownership\.mjs"/)
for (const token of [
  "cp6Predecessor = '6d4cda118f5d28d1f039cc0ecf318d0866f55c2c'",
  "['worktree', 'add', '--detach'", 'check-backend-ownership-v3.mjs',
  'Fetch full history before claiming backend ownership PASS',
]) assert.ok(predecessorOwnership.includes(token), `CP6 predecessor ownership wrapper missing: ${token}`)
assert.ok(mainWorkflow.includes('npm run test:browser:cp6'), 'Main PR CI omits the CP6 Chromium contract')
assert.ok(mainWorkflow.includes('cp6-browser-contract-proof'), 'Main PR CI omits CP6 browser artifacts')
for (const token of [
  'postgresql-client-17', "/usr/lib/postgresql/17/bin/pg_dump",
  'https://www.postgresql.org/media/keys/ACCC4CF8.asc',
  'B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8',
  'https://apt.postgresql.org/pub/repos/apt',
  'Verify PostgreSQL dump and server compatibility',
  'CP6_POSTGRES_CLIENT_SERVER_COMPATIBILITY.txt',
  'test "$client_major" = "$server_major"',
]) assert.ok(workflow.includes(token), `CP6 disposable database toolchain guard missing: ${token}`)
assert.equal(occurrences(workflow, 'scripts/clone-cp6-disposable-database.sh'), 2,
  'Both and only the CP6 preflight/race tests must use the fenced physical clone builder')
assert.equal(occurrences(workflow, 'dropdb -U supabase_admin --if-exists --force --maintenance-db=template1'), 2,
  'Both CP6 physical clones must be removed by their disposable database owner')
for (const token of [
  'CP6_MAINTENANCE_PGURL', 'CP6_DATABASE_CONTAINER: supabase_db_cp5-local',
  'cp6-proof/CP6_PREFLIGHT_CLONE_BOUNDARY',
  'cp6-proof/CP6_RACE_CLONE_BOUNDARY',
  'CP6_PREFLIGHT_CLONE_CLEANUP.txt', 'CP6_RACE_CLONE_CLEANUP.txt',
  "select count(*) from pg_database where datname='cp6_preflight'",
  "select count(*) from pg_database where datname='cp6_race'",
]) assert.ok(workflow.includes(token), `CP6 disposable clone proof missing: ${token}`)
for (const token of [
  "source_pg_cron_count", "clone_pg_cron_count", "test \"$source_pg_cron_count\" = '1'",
  "test \"$clone_pg_cron_count\" = '1'", '--schema=erp',
  '--restrict-key="$restrict_key"', 'cmp -s "$source_erp_dump" "$clone_erp_dump"',
  'erp_schema_owners_grants_sequences_rows=IDENTICAL', 'status=PASS',
]) assert.ok(cloneVerifier.includes(token), `CP6 disposable clone verifier missing: ${token}`)
for (const token of [
  'cp6_preflight|cp6_race', "supabase_db_cp5-local", "trap restore_source_connections EXIT",
  "admin_psql", "psql -U supabase_admin -d template1",
  "test \"$(admin_psql -c 'select current_user')\" = 'supabase_admin'",
  "test \"$source_pgurl\" = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'",
  "test \"$maintenance_pgurl\" = 'postgresql://postgres:postgres@127.0.0.1:54322/template1'",
  'refusing a clone URL outside the exact loopback CP6 disposable allowlist',
  'alter database postgres with allow_connections false',
  'docker restart "$database_container"', 'wait_for_admin',
  "select datallowconn from pg_database where datname='postgres'",
  'pg_terminate_backend(pid)', 'createdb -U supabase_admin', '--template=postgres',
  'alter database postgres with allow_connections true',
  'remaining_source_connections', 'scripts/verify-cp6-disposable-clone.sh',
  'clone_strategy=TEMPLATE_POSTGRES', 'database_admin=supabase_admin',
  'source_restart_under_fence=PASS',
  'source_connections_restored=PASS',
]) assert.ok(cloneBuilder.includes(token), `CP6 fenced physical clone builder missing: ${token}`)
assert.ok(cloneBuilder.indexOf("source_fenced='1'")
  < cloneBuilder.indexOf("admin_psql -c 'alter database postgres with allow_connections false'"),
  'CP6 connection-restoration trap is armed only after the source fence can already succeed')
assert.equal(sha256(gitignore), 'b3fbafd905cf6f028db98274a05811af388886e01d3209c59e098134e19b42d4',
  'CP6 changed the frozen CP5 .gitignore instead of keeping proof ownership explicit')

for (const token of [
  'Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.',
  'Laporan keuangan termasuk di dalam wilayah Keuangan',
  'Physical time', 'timestamps start blank',
  'Brand -> SKU number -> Model', 'two different brands may',
  'effective period are immutable',
  'an immutable cutting/production snapshot',
  'The legacy ERP project is read-only',
]) assert.ok(rules.includes(token), `Binding ERP reliability rule missing: ${token}`)

console.log(`CP6 boundary passed: immutable migration ${migrationBytes.length} bytes; exact ledger shapes ${ledgerSha.slice(0, 12)}/${migrationFileSha.slice(0, 12)}; seven closed actions, physical-time conservation, Brand-scoped SKU identity, durable idempotency, append-only reversal, paid failed-wash custody/cost separation, finance/stock/HPP reconciliation, twelve serialized races, and digest-bound rollback are owned.`)
