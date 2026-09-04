import assert from 'node:assert/strict'
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
const race = read(racePath)
const workflow = read(workflowPath)
const mainWorkflow = read(mainWorkflowPath)
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

const migrationBytes = Buffer.from(migration, 'utf8')
assert.equal(migrationBytes.at(-1), 10, 'CP6 migration must have one final LF excluded from platform statements')
const migrationFileSha = sha256(migrationBytes)
const ledgerSha = sha256(migrationBytes.subarray(0, -1))
assert.equal(occurrences(rollback, ledgerSha), 3,
  'CP6 rollback must bind both platform guards and its exact delete to current statement bytes')
assert.match(workflow, new RegExp(`test "\\$\\(wc -c < "\\$migration_source"\\)" = '${migrationBytes.length}'`),
  'CP6 workflow byte count is stale')
assert.ok(workflow.includes(`${migrationFileSha}  ${migrationPath}`), 'CP6 workflow file SHA-256 is stale')
assert.ok(workflow.includes(`= '${ledgerSha}'`), 'CP6 workflow platform-ledger digest is stale')

const backendActionBlock = migration.match(/if v_action not in\(\s*([\s\S]*?)\s*\) then/)
assert.ok(backendActionBlock, 'CP6 backend action allowlist not found')
const expectedActions = [
  'POST_DELIVERY', 'POST_RECEIPT', 'REVERSE_DELIVERY',
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
  'CP6 POST_RECEIPT payload', 'CP6 POST_FINAL_SKU payload',
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
  'sync_po_hpp_to_gl', 'desired_laundry_accrual', 'post_journal', 'reverse_journal',
  "or (old.status='POSTED' and new.status='REVERSED')",
]) assert.ok(migration.includes(token), `CP6 authoritative boundary token missing: ${token}`)
assert.ok(acceptance.includes('CP6 false ALL READY must fail atomically'),
  'Acceptance does not reject a false ALL_READY declaration')
assert.ok(acceptance.includes('CP6 false PARTIAL must fail atomically'),
  'Acceptance does not reject a false PARTIAL_SELECTION declaration')
assert.ok(acceptance.includes('completion-mode rejection left QC, FG, BS, finance, or idempotency residue'),
  'Acceptance does not prove false completion labels roll back every derived fact')
assert.equal(occurrences(migration, "pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0))"), 6,
  'All six CP6 mutations must share the same Potongan serialization fence')

for (const [signature, digest] of [
  ['erp.desired_laundry_accrual(uuid)', '4ded5af2c9c604357d18c783b00dcdb9'],
  ['erp.post_journal(text,uuid,date,text,jsonb)', 'dbf6138ccc575950fc6aed789863af8c'],
  ['erp.reverse_journal(uuid,text)', '6ee9da4164624f08381415b01630f323'],
]) {
  assert.ok(migration.includes(`'${signature}'::regprocedure`), `CP6 omits finance dependency ${signature}`)
  assert.ok(migration.includes(`'${digest}'`), `CP6 finance dependency digest drifted for ${signature}`)
}

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
]) assert.ok(qcPage.includes(token), `QC reversal UX guard missing: ${token}`)
for (const token of [
  'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.',
  'FG hasil QC masih dipakai transaksi downstream aktif.',
  "toBeDisabled()",
]) assert.ok(browser.includes(token), `Browser reversal-affordance proof missing: ${token}`)
for (const token of [
  'WRITER DIBLOKIR', 'Formula Nota FG lama belum menjadi kontrak backend',
  'Tidak ada data yang dihapus atau diposting.',
]) {
  assert.ok(fgBoundary.includes(token), `Connected Nota FG safety boundary missing: ${token}`)
  assert.ok(browser.includes(token), `Browser Nota FG safety proof missing: ${token}`)
}

for (const token of [
  'platform ledger statement digest is ambiguous',
  'a successor migration is already installed',
  'post-install CP6 physical/financial/stock/HPP/idempotency/audit history exists',
  'exact rollback capsule is missing', 'installed object/capsule drift',
  'rollback failed exact ACL restoration', 'rollback left CP6 schema residue',
]) assert.ok(rollback.includes(token), `CP6 rollback refusal/restoration proof missing: ${token}`)

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
  'controlled reversal lost history or left active stock/accrual',
  'CP6_AUTHORITATIVE_ACCEPTANCE_PASS', 'CP6_AUTHORITATIVE_RESIDUE_ZERO',
]) assert.ok(acceptance.includes(token), `CP6 acceptance proof missing: ${token}`)

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
  'committedRefreshRequired', 'retireCommittedForm()',
  'Reconcile wajib memakai UUID/payload yang sama',
]) assert.ok(hook.includes(token), `CP6 UI reliability lifecycle missing: ${token}`)
for (const token of [
  'reconciles an ambiguous response with the exact same UUID, payload, and version',
  'retires a committed form and keeps it dead after refetch failure then recovery',
  'locks the writer synchronously when a refetch starts before React can rerender',
  'fails closed when a persisted envelope is corrupt',
]) assert.ok(hookTest.includes(token), `CP6 hook lifecycle proof missing: ${token}`)

assert.equal(occurrences(laundryPage, "const [physicalAt, setPhysicalAt] = useState('')"), 2,
  'Laundry physical timestamps must start blank for dispatch and receipt')
assert.equal(occurrences(qcPage, "const [physicalAt, setPhysicalAt] = useState('')"), 1,
  'QC physical timestamp must start blank')
assert.equal(laundryPage.includes('localNow'), false, 'Laundry UI infers physical time from page/browser clock')
assert.equal(qcPage.includes('localNow'), false, 'QC UI infers physical time from page/browser clock')
assert.equal(occurrences(laundryPage, 'useEffect(() => setConfirmed(false), [workspace])'), 2,
  'Laundry acknowledgement must expire after every authoritative refetch')
assert.equal(occurrences(qcPage, 'useEffect(() => setConfirmed(false), [workspace])'), 1,
  'QC acknowledgement must expire after every authoritative refetch')
for (const token of ['WAKTU FISIK KELUAR', 'WAKTU FISIK KEMBALI']) {
  assert.ok(laundryPage.includes(token), `Laundry UI physical-time input missing: ${token}`)
}
assert.ok(qcPage.includes('WAKTU FISIK QC'), 'QC UI physical-time input missing')
assert.ok(laundryPage.includes('MEREK → NOMOR SKU → MODEL'), 'Laundry identity order drifted')
assert.ok(qcPage.includes('MEREK → NOMOR SKU → MODEL'), 'QC identity order drifted')
for (const token of [
  'Hak kerja · {roleName}', 'Mode lihat saja untuk {action}.',
  'Form dikunci; data tetap bisa dilihat.',
]) assert.ok(permissionNotice.includes(token), `CP6 permission UX invariant missing: ${token}`)
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
assert.equal(occurrences(browser, "physical_at: '2026-09-04T01:00:00.000Z'"), 3,
  'Browser contract must prove all three 08:00 WIB inputs serialize to exact UTC instants')
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
]) assert.ok(modelTest.includes(token), `CP6 parser test coverage missing: ${token}`)

const raceKeys = [...race.matchAll(/report\['races'\]\['([^']+)'\]\s*=/g)].map((match) => match[1])
assert.deepEqual(raceKeys, [
  'post_delivery', 'post_receipt', 'vendor_invoice_vs_reverse_receipt',
  'vendor_invoice_vs_final_sku', 'vendor_invoice_reversal_vs_final_sku',
  'final_sku_vs_vendor_invoice', 'final_sku_vs_vendor_invoice_reversal',
  'post_final_sku', 'final_sku_vs_reverse_receipt',
], 'CP6 concurrency proof must retain exactly nine named races')
for (const token of [
  "'receipt_cost_status': 'ESTIMATED'", "'laundry_accrual': 70",
  "'wip_net': 0", "'fg_net': 70", "'vendor_ap_net': 0",
  "'unbalanced_journals': 0", "'loser_idempotency_rows': 0",
  "'receipt_actual_cost': 90", "'current_hpp_total': 90",
  "'vendor_ap_net': -90", "'winner_idempotency_rows': 19",
  "'voided_hpp_history_lots': 5", "l.lot_origin='PRODUCTION'",
  'real serialization wait', 'invoice finalization owns the receipt lock',
  'invoice cost/AP commits before a waiting Final-SKU reads HPP',
  'invoice reversal restores estimate before waiting Final-SKU HPP',
  'Hold Final-SKU uncommitted, then prove invoice lifecycle recosts it',
]) assert.ok(race.includes(token), `CP6 concurrency invariant missing: ${token}`)

for (const token of [
  'npm run check:cp6', 'python -m py_compile scripts/cp6_laundry_qc_concurrency.py',
  'test:browser:cp6', 'V2620_MIGRATION_SHA256.txt',
  'CP6_AUTHORITATIVE_ACCEPTANCE_PASS', 'CP6_AUTHORITATIVE_RESIDUE_ZERO',
  'vendor_invoice_vs_reverse_receipt', 'vendor_invoice_vs_final_sku',
  'vendor_invoice_reversal_vs_final_sku',
  'final_sku_vs_vendor_invoice', 'final_sku_vs_vendor_invoice_reversal',
  'final_sku_vs_reverse_receipt',
  'V2620_ROLLBACK_TAMPERED_STATEMENT_REJECTION.log',
  'V2620_PREEXISTING_PRODUCT_AMBIGUITY_REJECTION.log',
  'V2620_ROLLBACK_POST_USE_REJECTION.log', 'FINAL_RECONCILIATION.json',
  "'production_go',false", 'rm -rf supabase/.temp',
]) assert.ok(workflow.includes(token), `CP6 full-schema workflow missing: ${token}`)
assert.match(browserConfig, /testMatch: 'cp6-laundry-qc\.spec\.ts'/)
assert.match(browserConfig, /ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1'/)
assert.match(packageJson, /"check:cp6": "node scripts\/check-cp6-boundary\.mjs"/)
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

for (const token of [
  'Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.',
  'Laporan keuangan termasuk di dalam wilayah Keuangan',
  'Physical time', 'timestamps start blank',
  'Brand -> SKU number -> Model', 'two different brands may',
  'effective period are immutable',
  'an immutable cutting/production snapshot',
  'The legacy ERP project is read-only',
]) assert.ok(rules.includes(token), `Binding ERP reliability rule missing: ${token}`)

console.log(`CP6 boundary passed: migration ${migrationBytes.length} bytes / ${migrationFileSha.slice(0, 12)}, ledger ${ledgerSha.slice(0, 12)}; six closed actions, exact batch-size conservation, Brand-scoped SKU identity, explicit physical time, durable idempotency, append-only reversal, finance/stock/HPP reconciliation, nine serialized races, and digest-bound rollback are owned.`)
