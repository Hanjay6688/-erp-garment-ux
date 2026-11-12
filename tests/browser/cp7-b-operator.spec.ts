import { expect, test, type BrowserContext, type Page, type TestInfo } from '@playwright/test'
import initialReady from '../fixtures/initialAnalysisReadyActual.json'
import { profileWire } from '../fixtures/nativePlanningProfile'
import { stagedFreshnessFixture, stagedRun } from '../fixtures/nativeAnalysisPages'
import { reorderWire } from '../fixtures/fgReorder'
import { laundryQcInputFixture } from '../fixtures/laundryQcInput'

// Full disposable App, with the same form-login pattern as CP5/CP6 browser
// contract tests. Every API response is served locally from test fixtures.
const appOrigin = 'http://127.0.0.1:4176'
const apiOrigin = 'http://127.0.0.1:54328'
const at = '2026-11-12T05:00:00Z'
const appUserId = 'c6b00000-0000-4000-8000-000000000002'
const permissions = ['dashboard.view', 'warehouse.fg.view', 'warehouse.stock.view', 'production.wip.view',
  'master.product.view', 'master.product.manage', 'sales.invoice.view']
const initialRpc = 'erp_cp7_request_staged_analysis_v1'
const getJob = 'erp_cp7_get_staged_analysis_v1'
const readPages = 'erp_cp7_read_staged_analysis_pages_v1'
const readPage = 'erp_cp7_read_staged_analysis_page_v1'
type Call = { name: string; args: Record<string, any> }
type Reply = { body: unknown; status?: number }
type Role = 'OWNER' | 'ADMIN' | 'STAFF'
type Transport = { calls: Call[]; unexpected: string[]; pageErrors: string[]; consoleErrors: string[] }
const transports = new WeakMap<BrowserContext, Transport>()

async function mockApp(context: BrowserContext, config: {
  role: Role; actor?: string; rights?: string[]; resolve: (call: Call) => Reply | undefined
}) {
  const actor = config.actor ?? initialReady.actor
  const calls: Call[] = [], unexpected: string[] = [], pageErrors: string[] = [], consoleErrors: string[] = []
  const transport = { calls, unexpected, pageErrors, consoleErrors }
  transports.set(context, transport)
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url')
  const expires = Math.floor(Date.now() / 1000) + 3600
  const token = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: actor, aud: 'authenticated', role: 'authenticated', exp: expires })}.cp7-fixture-signature`
  const user = {
    id: actor, aud: 'authenticated', role: 'authenticated', email: 'operator@example.test',
    email_confirmed_at: at, created_at: at, updated_at: at, app_metadata: { provider: 'email', providers: ['email'] },
    user_metadata: {}, identities: [],
  }
  const access = {
    allowed: true,
    profile: { id: appUserId, auth_user_id: actor, full_name: `Operator fixture ${config.role}`,
      role_id: 'c6b00000-0000-4000-8000-000000000003', role_code: config.role, role_name: config.role,
      is_active: true, row_version: 1, role_row_version: 1 },
    permissions: config.rights ?? permissions,
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
  const watch = (page: Page) => {
    page.on('pageerror', error => pageErrors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  }
  context.pages().forEach(watch)
  context.on('page', watch)
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url())
    if (url.origin === appOrigin && ['GET', 'HEAD'].includes(request.method())) return route.continue()
    if (url.origin !== apiOrigin) {
      unexpected.push(`${request.method()} ${url.origin}${url.pathname}`)
      return route.abort('blockedbyclient')
    }
    const headers = { 'access-control-allow-origin': appOrigin,
      'access-control-allow-headers': request.headers()['access-control-request-headers'] ?? '*',
      'access-control-allow-methods': 'GET,POST,OPTIONS' }
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    const send = (body: unknown, status = 200) => route.fulfill({ status, headers, json: body })
    if (url.pathname === '/auth/v1/token' && request.method() === 'POST') {
      return send({ access_token: token, token_type: 'bearer', expires_in: 3600, expires_at: expires,
        refresh_token: 'cp7-local-refresh-fixture', user })
    }
    if (url.pathname === '/auth/v1/user' && request.method() === 'GET') return send(user)
    if (url.pathname.startsWith('/rest/v1/rpc/') && request.method() === 'POST') {
      const name = url.pathname.split('/').at(-1)!
      const call = { name, args: request.postDataJSON() ?? {} }
      calls.push(call)
      if (name === 'erp_get_my_access_v1') return send(access)
      const reply = config.resolve(call)
      if (reply) return send(reply.body, reply.status)
    }
    unexpected.push(`${request.method()} ${url.pathname}`)
    return send({ message: 'RPC fixture tidak dideklarasikan.' }, 404)
  })
  return transport
}

test.afterEach(async ({ context }, info) => {
  const transport = transports.get(context)
  if (transport && info.status !== 'passed') {
    await info.attach('transport-at-failure', { body: JSON.stringify(transport, null, 2), contentType: 'application/json' })
  }
})

async function signIn(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email akun ERP').fill('operator@example.test')
  await page.getByLabel('Kata sandi').fill('disposable-fixture-password')
  await page.getByRole('button', { name: 'Masuk', exact: true }).click()
  await expect(page.locator('.top-title strong')).toBeVisible()
}

async function navigate(page: Page, group: string, label: string) {
  const parent = page.locator('.sidebar .nav-main').filter({ hasText: group }).first()
  await parent.waitFor({ state: 'attached' })
  const menu = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  const link = page.getByRole('button', { name: `• ${label}`, exact: true })
  if (!await link.isVisible()) await parent.click()
  await link.click()
}

const openPlanner = (page: Page) => navigate(page, 'Gudang', 'Ringkasan Barang Jadi')
const initialPanel = (page: Page) => page.getByRole('region', { name: 'Analisis awal otomatis', exact: true })
const isMobile = (info: TestInfo) => info.project.name === 'mobile'
const plannerRole = (info: TestInfo): Role => isMobile(info) ? 'ADMIN' : 'OWNER'

async function screenshot(page: Page, info: TestInfo, name: string) {
  const size = await page.evaluate(() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth }))
  await info.attach(`${name}-width`, { body: JSON.stringify(size), contentType: 'application/json' })
  const path = info.outputPath(`${name}.png`)
  await page.screenshot({ path, fullPage: true, animations: 'disabled' })
  await info.attach(name, { path, contentType: 'image/png' })
  expect.soft(size.viewport).toBe(page.viewportSize()?.width)
  expect.soft(size.document).toBeLessThanOrEqual(page.viewportSize()!.width)
}

async function verifyTransport(mock: Awaited<ReturnType<typeof mockApp>>, info: TestInfo) {
  await info.attach('transport', { body: JSON.stringify(mock, null, 2), contentType: 'application/json' })
  expect(mock.unexpected).toEqual([])
  expect(mock.pageErrors).toEqual([])
  expect(mock.consoleErrors).toEqual([])
}

function stockRpc(call: Call): Reply | undefined {
  if (call.name === 'erp_cp7_get_fg_v1') return { body: {
    contract_version: 'cp7.fg-workspace.v1', purpose: 'SUMMARY', read_at: at, knowledge: 'CURRENT',
    quantity_basis: 'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION', financial_captured: false,
    capabilities: { card: false }, unit_code: 'PCS', totals: { physical_qty: '0', reserved_qty: '0', available_qty: '0', quality: 'KNOWN' },
    page: { rows: [], total: '0', offset: 0, limit: 25, next_offset: null },
  } }
  if (call.name === 'erp_cp7_get_fg_reorder_v1') return { body: reorderWire([]) }
  return undefined
}

test('Planner opens the actual SKU Master when there are no active products', async ({ page, context }, info) => {
  const noProducts = { ...initialReady, state: 'NOT_READY', readiness: { ...initialReady.readiness,
    ready: false, reasons: ['NO_ACTIVE_PRODUCTS'], products_total: 0, active_products: 0, eligible_targets: 0, candidates: [] } }
  const mock = await mockApp(context, { role: plannerRole(info), resolve: call => {
    if (call.name === initialRpc) return { body: noProducts }
    if (call.name === 'erp_get_sku_workspace_v1') return { body: { at, page: 1, page_size: 50,
      groups_total: 0, products_total: 0, can_edit: true, groups: [], related_groups: [], products: [], selected_products: [],
      legacy_basis: null, lookups: { accessories: [], work: [], contractors: [], vendors: [], laundry: [] } } }
    return stockRpc(call)
  } })
  await signIn(page)
  await openPlanner(page)
  await expect(initialPanel(page)).toContainText('Belum ada produk aktif.')
  await screenshot(page, info, 'planner-no-products')
  await initialPanel(page).getByRole('button', { name: 'Lengkapi produk di Data Master' }).click()
  await expect(page.getByRole('heading', { name: 'Produk & SKU', exact: true })).toBeVisible()
  await expect.poll(() => mock.calls.filter(c => c.name === 'erp_get_sku_workspace_v1').length).toBeGreaterThan(0)
  expect(mock.calls.filter(c => c.name === initialRpc).map(c => c.args)).toEqual([{ p_query: { initial_auto: 'STATUS' }, p_request: null }])
  await screenshot(page, info, 'planner-master-destination')
  await verifyTransport(mock, info)
})

test('Planner passes the selected incomplete product root to the target form', async ({ page, context }, info) => {
  const first = { ...initialReady.readiness.candidates[0], profile_ready: false }
  const second = { ...first, sku: 'TARGET-B-002', product_name: 'Celana ukuran kedua',
    root_id: '00000020-1111-4111-8111-111111111111', product_id: '00000021-1111-4111-8111-111111111111', size_id: '00000022-1111-4111-8111-111111111111' }
  const missing = { ...initialReady, state: 'NOT_READY', readiness: { ...initialReady.readiness, ready: false,
    reasons: ['PLANNING_PROFILE_INCOMPLETE'], products_total: 2, active_products: 2, eligible_targets: 0, candidates: [first, second] } }
  const mock = await mockApp(context, { role: plannerRole(info), resolve: call => {
    if (call.name === initialRpc) return { body: missing }
    if (call.name === 'erp_cp7_get_planning_profiles_v1') {
      const candidate = call.args.p_roots?.[0] === second.root_id ? second : first
      return { body: { ...profileWire(false), rows: [{ ...profileWire(false).rows[0],
        root_id: candidate.root_id, product_version_id: candidate.product_id, size_id: candidate.size_id,
        sku: candidate.sku, product_name: candidate.product_name }] } }
    }
    return stockRpc(call)
  } })
  await signIn(page)
  await openPlanner(page)
  await initialPanel(page).getByRole('button', { name: 'Lengkapi target TARGET-B-002', exact: true }).click()
  const profile = page.getByRole('region', { name: 'Aturan dan target produksi' })
  await expect(profile).toContainText('TARGET-B-002')
  await expect(profile).toContainText(second.product_name)
  await expect(profile.getByLabel('Waktu proses pilihan (hari kalender)', { exact: true })).toBeVisible()
  expect(mock.calls.filter(c => c.name === 'erp_cp7_get_planning_profiles_v1').map(c => c.args)).toEqual([{ p_roots: [second.root_id] }])
  expect(mock.calls.filter(c => c.name === initialRpc).every(c => c.args.p_query.initial_auto === 'STATUS')).toBe(true)
  await screenshot(page, info, 'planner-target-product')
  await verifyTransport(mock, info)
})

test('Planner opens running and completed results under the same server job across closing and refresh', async ({ page, context }, info) => {
  const id = '00000000-0000-4000-8000-000000000095'
  const result = await stagedRun({ targets: 1, requestId: id })
  const label = result.original.product_labels[0]
  const [rootId, sizeId] = label.target_key.split(':')
  const readiness = { ...initialReady.readiness, candidates: [{ root_id: rootId, product_id: rootId,
    size_id: sizeId, sku: label.sku, product_name: label.product_name, profile_ready: true }] }
  let state: 'READY' | 'RUNNING' | 'DONE' = 'READY'
  let created = 0
  const job = () => result.job(state === 'DONE' ? 'DONE' : 'RUNNING', state === 'DONE' ? {} : {
    targets_done_in_stage: 0, worker_active: true,
    server_runner: { active: true, last_tick_at: result.reference.captured_at },
  })
  const status = () => ({ ...initialReady, actor: result.actor, query: result.query, state, readiness,
    ...(state === 'READY' ? {} : { job_query: result.query, job_semantic_hash: initialReady.semantic_hash, job: job() }) })
  const mock = await mockApp(context, { role: plannerRole(info), actor: result.actor, resolve: call => {
    if (call.name === initialRpc) {
      if (call.args.p_request !== null) return undefined
      if (call.args.p_query?.initial_auto === 'ENSURE' && state === 'READY') { created++; state = 'RUNNING' }
      return { body: status() }
    }
    if (call.name === getJob && call.args.p_request === id) return { body: job() }
    if (call.name === readPages && call.args.p_run === result.runId) return { body: result.pageSet }
    if (call.name === readPage && call.args.p_run === result.runId && call.args.p_index === 0 && call.args.p_access === result.pageSet.access_epoch) return { body: result.page(0) }
    if (call.name === 'erp_cp7_staged_snapshot_freshness_v1' && call.args.p_run === result.runId) return { body: stagedFreshnessFixture(result) }
    return stockRpc(call)
  } })
  await signIn(page)
  await openPlanner(page)
  await expect(initialPanel(page)).toContainText('Server sedang memproses')
  await initialPanel(page).getByRole('button', { name: 'Buka analisis awal yang berjalan' }).click()
  await expect.poll(() => mock.calls.filter(c => c.name === getJob).length).toBeGreaterThan(0)
  await screenshot(page, info, 'planner-running')
  await page.close()
  // The fixture worker changes the existing job while the page is closed.
  state = 'DONE'
  const reopened = await context.newPage()
  const readResult = async () => {
    await openPlanner(reopened)
    await expect(initialPanel(reopened)).toContainText(`Periode ${result.query.from_date} sampai ${result.query.through_date}`)
    await initialPanel(reopened).getByRole('button', { name: 'Buka hasil analisis awal' }).click()
    const row = reopened.locator('[data-analysis-target]')
    await expect(row).toHaveCount(1)
    await expect(row).toContainText('TEST')
    await expect(row.locator('td[data-label="Stok fisik"]')).toHaveText('76 PCS')
    await expect(row.locator('td[data-label="Produksi baru layak"]')).toContainText(/belum diketahui|belum tersedia/i)
    await expect(reopened.getByText('Halaman 1 dari 1', { exact: true })).toBeVisible()
    return row.innerText()
  }
  await reopened.goto('/')
  const beforeRefresh = await readResult()
  await screenshot(reopened, info, 'planner-reopened-complete')
  await reopened.reload()
  expect(await readResult()).toBe(beforeRefresh)
  expect(created).toBe(1)
  expect(mock.calls.filter(c => c.name === initialRpc && c.args.p_query?.initial_auto === 'ENSURE').map(c => c.args))
    .toEqual([{ p_query: { initial_auto: 'ENSURE' }, p_request: null }])
  expect([...new Set(mock.calls.filter(c => c.name === getJob).map(c => c.args.p_request))]).toEqual([id])
  expect(mock.calls.filter(c => c.name === readPages && c.args.p_run === result.runId)).toHaveLength(2)
  await info.attach('same-job', { body: JSON.stringify({ id, run: result.runId, period: result.query, created, beforeRefresh }, null, 2), contentType: 'application/json' })
  await verifyTransport(mock, info)
})

test('Planner shows a failed job and does not start another one', async ({ page, context }, info) => {
  const id = '00000000-0000-4000-8000-000000000096'
  const run = await stagedRun({ targets: 1, requestId: id })
  const mock = await mockApp(context, { role: plannerRole(info), actor: run.actor, resolve: call => call.name === initialRpc
    ? { body: { ...initialReady, actor: run.actor, query: run.query, state: 'FAILED',
      job: run.job('FAILED', { targets_done_in_stage: 0 }), job_query: run.query, job_semantic_hash: initialReady.semantic_hash } } : stockRpc(call) })
  await signIn(page)
  await openPlanner(page)
  await expect(initialPanel(page).getByRole('alert')).toContainText('Permintaan gagal tidak diulang otomatis.')
  await expect(initialPanel(page).getByRole('button', { name: /^Buka (hasil )?analisis awal/ })).toHaveCount(0)
  await initialPanel(page).getByRole('button', { name: 'Periksa kesiapan lagi' }).click()
  await expect(initialPanel(page).getByRole('alert')).toContainText('Permintaan gagal tidak diulang otomatis.')
  expect(mock.calls.filter(c => c.name === initialRpc).every(c => c.args.p_query.initial_auto === 'STATUS')).toBe(true)
  expect(mock.calls.some(c => c.name === readPages || c.name === getJob)).toBe(false)
  await screenshot(page, info, 'planner-failed')
  await verifyTransport(mock, info)
})

test('Planner refuses automatic access outside the owner/admin permission set', async ({ page, context }, info) => {
  const role = isMobile(info) ? 'ADMIN' : 'STAFF'
  const rights = isMobile(info) ? permissions.filter(p => p !== 'sales.invoice.view') : permissions
  const mock = await mockApp(context, { role, rights, resolve: stockRpc })
  await signIn(page)
  await openPlanner(page)
  await expect(page.getByRole('heading', { name: 'Barang jadi', exact: true })).toBeVisible()
  await expect(initialPanel(page)).toHaveCount(0)
  expect(mock.calls.some(c => c.name === initialRpc)).toBe(false)
  await verifyTransport(mock, info)
})

const operatorRights = ['dashboard.view', 'production.bs_rework.view', 'production.bs_rework.create',
  'production.laundry.view', 'production.laundry.post']
const bsWorkspaceRpc = 'erp_get_bs_resolution_workspace_v1'
const classifyRpc = 'erp_save_bs_resolution_action_v1'
const vendor = { id: '00000000-0000-4000-8000-000000000001', code: 'LDR-A', name: 'Laundry A' }
const source = {
  id: '00000000-0000-4000-8000-000000000020', number: 'LDR-PARTIAL-07',
  receiptId: '00000000-0000-4000-8000-000000000018', receiptLine: '00000000-0000-4000-8000-000000000017',
  poId: '00000000-0000-4000-8000-000000000014', po: 'PO-PARTIAL-07',
  groupId: '00000000-0000-4000-8000-000000000012', group: 'P-001', batch: 7,
}

function bsWorkspace(call: Call, rows: Record<string, unknown>[]) {
  const { p_filter, p_kind, p_pattern_id, p_query, p_limit, p_offset } = call.args
  const selected = rows.filter(row => p_kind === 'ALL' || p_kind === row.kind)
  return { filter: p_filter, kind: p_kind, pattern_id: p_pattern_id, query: p_query, limit: p_limit, offset: p_offset,
    total: selected.length, rows: selected,
    lookups: { contractors: [], vendors: [vendor], fg_locations: [], work_components: [], products: [],
      laundry_sources: [{ id: source.id, number: source.number, vendor_id: vendor.id, vendor_name: vendor.name,
        po_number: source.po, physical_at: at, qty_sent_pcs: 13, qty_claimable_pcs: 5 }],
      laundry_receipt_sources: [], settled_claims: [] } }
}

const commonCase = {
  status: 'OPEN', row_version: 4, qty_pcs: 1, resolved_qty: 0, active_rework_qty: 0, available_qty: 1,
  opened_at: at, po_id: source.poId, po_number: source.po, model_name: 'Model A', cutting_group_id: source.groupId,
  group_number: source.group, patterns: [], product_id: null, sku: null, product_name: null,
  responsible_contractor_id: null, contractor_name: null, responsible_vendor_id: null, vendor_name: null,
  detected_stage: 'QC', cause_source: 'UNKNOWN', untracked_type: null, claim_type: null, compensation_amount: 0,
  laundry_delivery_id: null, laundry_receipt_line_id: null, legacy_reference: null, notes: null as string | null,
  next_action: 'START_REWORK_OR_DISPOSITION', is_closed: false, accessory_bom: null as object | null,
  components: [], resolutions: [], rework_orders: [], hold_events: [],
}

test('BS/Laundry shows readable reject causes and reloads the saved free-text note', async ({ page, context }, info) => {
  const note = 'Ada bolong di lipatan kiri dan noda setelah dicuci. Jahitan lepas dekat saku. ' +
    'Sudah dihitung ulang dengan operator dan bukti foto ditaruh bersama surat jalan pengiriman.'
  const row = { ...commonCase, id: 'case-reject-1', case_key: 'BS:case-reject-1', kind: 'BS', number: 'BS-OPERATOR-01',
    accessory_bom: { state: 'UNAVAILABLE', bom_version_id: null, default_policy: 'SERVER_ENTITLEMENT_V2619B', available_qty_pcs: 1, items: [] } }
  const mock = await mockApp(context, { role: plannerRole(info), rights: operatorRights, resolve: call => {
    if (call.name === bsWorkspaceRpc) return { body: bsWorkspace(call, [row]) }
    if (call.name === classifyRpc && call.args.p_action === 'CLASSIFY_BS' && call.args.p_expected_version === row.row_version) {
      const p = call.args.p_payload
      Object.assign(row, { cause_source: p.cause_source, notes: p.notes, responsible_vendor_id: p.responsible_vendor_id,
        vendor_name: vendor.name, row_version: row.row_version + 1 })
      return { body: { request_id: call.args.p_client_request_id, action: 'CLASSIFY_BS', result: { row_version: row.row_version } } }
    }
    return undefined
  } })
  await signIn(page)
  const openCase = async () => {
    await navigate(page, 'Produksi', 'Barang BS & Rework')
    await page.getByRole('button', { name: /BS-OPERATOR-01/ }).click()
    await expect(page.getByRole('heading', { name: 'BS-OPERATOR-01', exact: true })).toBeVisible()
    await page.getByText('Klasifikasi & tanggung jawab', { exact: true }).click()
  }
  await openCase()
  const cause = page.getByLabel('SUMBER PENYEBAB', { exact: true })
  expect.soft(await cause.locator('option').allTextContents()).toEqual(['Belum diketahui', 'Jahit', 'Laundry'])
  expect(await cause.locator('option').evaluateAll(options => options.map(o => (o as HTMLOptionElement).value)))
    .toEqual(['UNKNOWN', 'SEWING', 'LAUNDRY'])
  await screenshot(page, info, 'bs-cause-category')
  await cause.selectOption('LAUNDRY')
  await page.getByLabel('VENDOR TANGGUNG JAWAB', { exact: true }).selectOption(vendor.id)
  await page.getByLabel('CATATAN KASUS', { exact: true }).fill(note)
  await page.getByLabel('ALASAN PERUBAHAN · WAJIB', { exact: true }).fill('Pemeriksaan reject bersama operator')
  await page.getByRole('button', { name: 'Simpan klasifikasi', exact: true }).click()
  await expect(page.locator('.cbsr-case-note')).toHaveText(note)
  const actions = mock.calls.filter(c => c.name === classifyRpc)
  expect(actions).toHaveLength(1)
  expect(actions[0].args).toMatchObject({ p_action: 'CLASSIFY_BS', p_expected_version: 4,
    p_payload: { bs_case_id: row.id, cause_source: 'LAUNDRY', responsible_vendor_id: vendor.id,
      responsible_contractor_id: null, notes: note } })
  expect(actions[0].args.p_client_request_id).toMatch(/^[0-9a-f-]{36}$/)
  await page.reload()
  await openCase()
  await expect(cause).toHaveValue('LAUNDRY')
  await expect(page.getByLabel('CATATAN KASUS', { exact: true })).toHaveValue(note)
  await expect(page.locator('.cbsr-case-note')).toHaveText(note)
  expect(mock.calls.filter(c => c.name === classifyRpc)).toHaveLength(1)
  await screenshot(page, info, 'bs-note-reopened')
  if (isMobile(info)) {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 900 })
      await screenshot(page, info, `bs-note-${width}`)
    }
  }
  await verifyTransport(mock, info)
})

test('BS/Laundry identifies all sizes of a partial return and opens its damage claim', async ({ page, context }, info) => {
  const base = laundryQcInputFixture('LAUNDRY')
  const ready = base.ready_batches[0]
  const receipt = {
    id: source.receiptId, number: 'LRC-PARTIAL-07', status: 'POSTED', row_version: 1, physical_at: at,
    actual_cost: null, actual_rate: null, cost_status: 'PENDING', event_kind: 'PHYSICAL_RECEIPT',
    failed_wash_attempt_id: null, custody_outcome: null, attempted_qty_pcs: null, process_name: 'Cuci',
    reversible: false, reversal_blocker: 'Penerimaan terhubung dengan klaim kerusakan.',
  }
  const delivery = {
    delivery_id: source.id, delivery_number: source.number, row_version: 2, status: 'PARTIAL_RETURN', physical_at: at,
    target_dyeing_color: 'Hitam', special_instruction: null, po_id: source.poId, po_number: source.po,
    model_id: base.lookups.products[0].model_id, cutting_group_id: source.groupId, group_number: source.group,
    cutting_group_row_version: ready.cutting_group_row_version, model_code: 'MOD-A', model_name: 'Model A', contractor_name: 'Mandor A',
    vendor_id: vendor.id, vendor_code: vendor.code, vendor_name: vendor.name, wash_process_id: base.lookups.wash_processes[0].id,
    process_code: 'WASH', process_name: 'Cuci', delivery_line_id: '00000000-0000-4000-8000-000000000019',
    qty_sent_pcs: 13, estimated_rate_snapshot: null, estimated_cost: null,
    distribution_batch_id: ready.distribution_batch_id, batch_no: source.batch, returned_qty_pcs: 8,
    physical_outstanding_qty_pcs: 5, returned_unprocessed_qty_pcs: 0, active_claim_qty_pcs: 0,
    reversible: false, reversal_blocker: 'Sudah ada penerimaan parsial.', receipts: [receipt],
    sizes: [
      { delivery_batch_size_line_id: '00000000-0000-4000-8000-000000000061', size_id: ready.sizes[0].size_id, size_code: '31',
        sort_order: 1, qty_sent_pcs: 5, good_returned_qty_pcs: 5, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 0 },
      { delivery_batch_size_line_id: '00000000-0000-4000-8000-000000000062', size_id: '00000000-0000-4000-8000-000000000032', size_code: '32',
        sort_order: 2, qty_sent_pcs: 8, good_returned_qty_pcs: 2, bs_returned_qty_pcs: 1, outstanding_qty_pcs: 5 },
    ],
  }
  const claim = { ...commonCase, id: 'claim-partial-1', case_key: 'LAUNDRY_CLAIM:claim-partial-1', kind: 'LAUNDRY_CLAIM',
    number: 'CLM-PARTIAL-01', detected_stage: 'LAUNDRY', cause_source: 'LAUNDRY', claim_type: 'DAMAGE',
    responsible_vendor_id: vendor.id, vendor_name: vendor.name, laundry_delivery_id: source.id, laundry_receipt_line_id: source.receiptLine,
    notes: `1 PCS BS dari penerimaan ${receipt.number}, surat kirim ${source.number}. Pemeriksaan klaim masih terbuka.`,
    next_action: 'SETTLE_OR_CLOSE' }
  const mock = await mockApp(context, { role: plannerRole(info), rights: operatorRights, resolve: call => {
    if (call.name === 'erp_get_laundry_qc_workspace_v1' && call.args.p_scope === 'LAUNDRY') return { body: { ...base, deliveries: [delivery] } }
    if (call.name === bsWorkspaceRpc) return { body: bsWorkspace(call, [claim]) }
    return undefined
  } })
  await signIn(page)
  await navigate(page, 'Produksi', 'Laundry')
  await page.getByRole('button', { name: 'Terima kembali', exact: true }).click()
  await expect(page.getByText('Pilih surat kirim yang kembali', { exact: true })).toBeVisible()
  await page.getByLabel('SURAT KIRIM AKTIF', { exact: true }).selectOption(source.id)
  const selected = page.locator('.clq-return-editor')
  await expect(selected.locator('header')).toContainText(`${source.number} · ${vendor.name}`)
  await expect.soft(selected.locator('header')).toContainText(source.po, { timeout: 1000 })
  await expect(selected.locator('header')).toContainText('Batch 7')
  await expect(selected.locator('header')).toContainText('5 pcs belum kembali')
  await expect.soft(selected.locator('article').filter({ hasText: 'Ukuran 31' })).toContainText('Dikirim 5 · sudah kembali 5 · belum kembali 0', { timeout: 1000 })
  await expect(selected.locator('article').filter({ hasText: 'Ukuran 32' })).toContainText('Dikirim 8 · sudah kembali 3 · belum kembali 5')
  await expect(selected.getByLabel('Good kembali size 31')).toHaveCount(0)
  await expect(selected.getByLabel('Good kembali size 32')).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Post penerimaan atomic' })).toBeDisabled()
  await screenshot(page, info, 'laundry-partial')
  if (isMobile(info)) {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 900 })
      await screenshot(page, info, `laundry-partial-${width}`)
    }
    await page.setViewportSize({ width: 390, height: 844 })
  }
  await navigate(page, 'Produksi', 'Barang BS & Rework')
  await page.getByLabel('Jenis kasus CP5').selectOption({ label: 'Claim Laundry' })
  await page.getByRole('button', { name: /CLM-PARTIAL-01/ }).click()
  const detail = page.locator('.cbsr-detail')
  await expect(detail.getByRole('heading', { name: 'CLM-PARTIAL-01' })).toBeVisible()
  await expect(detail).toContainText(source.po)
  await expect(detail).toContainText(vendor.name)
  await expect(detail).toContainText('1 pcs ditahan oleh claim')
  await expect(detail).toContainText(`1 PCS BS dari penerimaan ${receipt.number}, surat kirim ${source.number}`)
  await expect(detail).toContainText('DAMAGE · Rp0')
  expect(mock.calls.some(c => /(^erp_save|^erp_cp7_save)/.test(c.name))).toBe(false)
  await info.attach('partial-return', { body: JSON.stringify({ delivery: source, claim: claim.number,
    quantities: delivery.sizes.map(r => ({ size: r.size_code, sent: r.qty_sent_pcs, received: r.good_returned_qty_pcs + r.bs_returned_qty_pcs, outside: r.outstanding_qty_pcs })),
    damage: claim.qty_pcs, compensation: claim.compensation_amount }, null, 2), contentType: 'application/json' })
  await screenshot(page, info, 'laundry-damage-claim')
  await verifyTransport(mock, info)
})
