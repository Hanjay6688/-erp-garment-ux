import { expect, test, type Page, type Route } from '@playwright/test'

const uatOrigin = 'https://siimvrusnzxexizpyoib.supabase.co'
const localOrigin = 'http://127.0.0.1:4175'
const userId = 'c8b00000-0000-4000-8000-000000000001'
const laundrySendConfirmation = 'Saya sudah mencocokkan vendor, batch, ukuran, jumlah, warna, dan waktu dengan serah-terima fisik.'
const laundryReceiptConfirmation = 'Saya sudah menghitung fisik per ukuran; Good dan BS benar, sisanya memang belum kembali.'
const qcConfirmation = 'Saya sudah mencocokkan hasil QC fisik, ukuran, Merek/Nomor SKU/Model, jumlah Good/BS, lokasi, dan waktu.'

const ids = {
  batch: 'c8b10000-0000-4000-8000-000000000001',
  pickup: 'c8b10000-0000-4000-8000-000000000002',
  group: 'c8b10000-0000-4000-8000-000000000003',
  pattern: 'c8b10000-0000-4000-8000-000000000004',
  po: 'c8b10000-0000-4000-8000-000000000005',
  model: 'c8b10000-0000-4000-8000-000000000006',
  contractor: 'c8b10000-0000-4000-8000-000000000007',
  sizeS: 'c8b10000-0000-4000-8000-000000000008',
  sizeM: 'c8b10000-0000-4000-8000-000000000009',
  vendor: 'c8b20000-0000-4000-8000-000000000001',
  process: 'c8b20000-0000-4000-8000-000000000002',
  rate: 'c8b20000-0000-4000-8000-000000000003',
  location: 'c8b20000-0000-4000-8000-000000000004',
  brand: 'c8b20000-0000-4000-8000-000000000005',
  productS: 'c8b20000-0000-4000-8000-000000000006',
  productM: 'c8b20000-0000-4000-8000-000000000007',
  wrongProduct: 'c8b20000-0000-4000-8000-000000000008',
  wrongModel: 'c8b20000-0000-4000-8000-000000000009',
  delivery: 'c8b30000-0000-4000-8000-000000000001',
  deliveryLine: 'c8b30000-0000-4000-8000-000000000002',
  deliverySizeS: 'c8b30000-0000-4000-8000-000000000003',
  receipt: 'c8b30000-0000-4000-8000-000000000004',
  receiptLine: 'c8b30000-0000-4000-8000-000000000005',
  receiptSizeS: 'c8b30000-0000-4000-8000-000000000006',
}

type ContractOptions = {
  loseFirstActionResponse?: boolean
  failFirstPostCommitWorkspace?: boolean
  permissions?: string[]
  state?: ContractState
}
type ContractState = { actionAttempts: number; committed: boolean; failNextWorkspace: boolean }
type ContractCalls = {
  workspace: Record<string, unknown>[]
  actions: Record<string, unknown>[]
  unexpected: string[]
}

function json(route: Route, value: unknown, status = 200) {
  return route.fulfill({
    status,
    body: JSON.stringify(value),
    headers: {
      'content-type': 'application/json',
      'access-control-allow-origin': localOrigin,
      'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'authorization,apikey,content-type,x-client-info,x-supabase-api-version',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
    },
  })
}

function fakeJwt() {
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url')
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: userId, aud: 'authenticated', role: 'authenticated', exp: 4_102_444_800 })}.cp6-local-contract-signature`
}

function authUser() {
  return {
    id: userId, aud: 'authenticated', role: 'authenticated',
    email: 'cp6-owner@example.test', email_confirmed_at: '2026-09-04T00:00:00Z',
    phone: '', confirmed_at: '2026-09-04T00:00:00Z', last_sign_in_at: '2026-09-04T00:00:00Z',
    app_metadata: { provider: 'email', providers: ['email'] }, user_metadata: {}, identities: [],
    created_at: '2026-09-04T00:00:00Z', updated_at: '2026-09-04T00:00:00Z',
  }
}

function accessBundle(permissions?: string[]) {
  const restricted = permissions !== undefined
  return {
    allowed: true,
    profile: {
      id: 'c8b00000-0000-4000-8000-000000000002', auth_user_id: userId,
      full_name: 'CP6 Owner', role_id: 'c8b00000-0000-4000-8000-000000000003',
      role_code: restricted ? 'LAUNDRY_VIEW' : 'OWNER', role_name: restricted ? 'Laundry · Lihat Saja' : 'Owner',
      is_active: true, row_version: 1, role_row_version: 1,
    },
    permissions: permissions ?? [
      'dashboard.view', 'production.laundry.view', 'production.laundry.create',
      'production.laundry.post', 'production.laundry.reverse', 'production.final_sku.view',
      'production.final_sku.post', 'production.final_sku.reverse', 'production.fg_handoff.view',
    ],
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
}

function lookups() {
  return {
    vendors: [{ id: ids.vendor, code: 'L-01', name: 'Laundry Nyata' }],
    wash_processes: [{ id: ids.process, code: 'BIO', name: 'Bio Wash' }],
    rate_versions: [{
      id: ids.rate, vendor_id: ids.vendor, wash_process_id: ids.process, rate_per_pcs: 700,
      effective_from: '2026-01-01T00:00:00Z', effective_to: null,
    }],
    fg_locations: [{ id: ids.location, code: 'FG-01', name: 'Gudang FG Utama' }],
    products: [
      { id: ids.productS, sku: '73001', name: 'Vivo Small', model_id: ids.model, model_code: 'VIVO', model_name: 'Vivo Pants', brand_id: ids.brand, brand_code: 'VIVO', brand_name: 'Vivo', size_id: ids.sizeS, size_code: 'S', color: 'NAVY', effective_from: '2026-01-01T00:00:00Z', effective_to: null },
      { id: ids.productM, sku: '73001', name: 'Vivo Medium', model_id: ids.model, model_code: 'VIVO', model_name: 'Vivo Pants', brand_id: ids.brand, brand_code: 'VIVO', brand_name: 'Vivo', size_id: ids.sizeM, size_code: 'M', color: 'NAVY', effective_from: '2026-01-01T00:00:00Z', effective_to: null },
      { id: ids.wrongProduct, sku: 'WRONG-S', name: 'Wrong Model Small', model_id: ids.wrongModel, model_code: 'WRONG', model_name: 'Wrong Model', brand_id: ids.brand, brand_code: 'VIVO', brand_name: 'Vivo', size_id: ids.sizeS, size_code: 'S', color: 'NAVY', effective_from: '2026-01-01T00:00:00Z', effective_to: null },
    ],
  }
}

function baseWorkspace(scope: 'LAUNDRY' | 'QC') {
  return {
    contract_version: 'CP6_V2620', scope, generated_at: '2026-09-04T08:00:00Z',
    lookups: lookups(),
    readiness: {
      laundry_writer_ready: true, qc_writer_ready: true,
      no_fixture_fallback: true, failed_wash_with_charge_supported: false,
    },
    ready_batches: [], deliveries: [], qc_queue: [], qc_history: [],
    legacy_unlinked: { delivery_count: 0, receipt_count: 0 },
  }
}

function laundryWorkspace(committed = false) {
  return {
    ...baseWorkspace('LAUNDRY'),
    ready_batches: committed ? [] : [{
      distribution_batch_id: ids.batch, batch_no: 1, pickup_id: ids.pickup,
      cutting_group_id: ids.group, cutting_group_row_version: 7, group_number: 'POT-CP6-001',
      pattern_id: ids.pattern, pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular',
      po_id: ids.po, po_number: 'PO-CP6-001', po_status: 'SEWING',
      model_code: 'VIVO-REG', model_name: 'Vivo Regular', contractor_id: ids.contractor,
      contractor_code: 'M-01', contractor_name: 'Mandor A', picked_up_at: '2026-09-04T07:00:00Z',
      group_unsent_ready_qty_pcs: 10,
      sizes: [
        { size_id: ids.sizeS, size_code: 'S', sort_order: 1, allocated_qty_pcs: 6, sent_qty_pcs: 0, available_qty_pcs: 6 },
        { size_id: ids.sizeM, size_code: 'M', sort_order: 2, allocated_qty_pcs: 4, sent_qty_pcs: 0, available_qty_pcs: 4 },
      ],
    }],
    deliveries: [{
      delivery_id: ids.delivery, delivery_number: 'LDR-CP6-001', row_version: 3, status: 'PARTIAL_RETURN',
      physical_at: '2026-09-04T07:10:00Z', target_dyeing_color: 'NAVY', special_instruction: null,
      po_id: ids.po, po_number: 'PO-CP6-001', model_id: ids.model, cutting_group_id: ids.group,
      group_number: 'POT-CP6-001', cutting_group_row_version: 7, model_code: 'VIVO-REG',
      model_name: 'Vivo Regular', contractor_name: 'Mandor A', vendor_id: ids.vendor,
      vendor_code: 'L-01', vendor_name: 'Laundry Nyata', wash_process_id: ids.process,
      process_code: 'BIO', process_name: 'Bio Wash', delivery_line_id: ids.deliveryLine,
      qty_sent_pcs: 6, estimated_rate_snapshot: 700, estimated_cost: 4200,
      distribution_batch_id: ids.batch, batch_no: 1, returned_qty_pcs: 2,
      physical_outstanding_qty_pcs: 4, active_claim_qty_pcs: 0, reversible: false,
      sizes: [{
        delivery_batch_size_line_id: ids.deliverySizeS, size_id: ids.sizeS, size_code: 'S', sort_order: 1,
        qty_sent_pcs: 6, good_returned_qty_pcs: 2, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 4,
      }], receipts: [],
    }],
  }
}

function qcWorkspace(committed = false) {
  return {
    ...baseWorkspace('QC'),
    qc_queue: committed ? [] : [{
      source_batch_size_line_id: ids.receiptSizeS, receipt_line_id: ids.receiptLine,
      receipt_id: ids.receipt, receipt_number: 'LRC-CP6-001', receipt_physical_at: '2026-09-04T07:30:00Z',
      distribution_batch_id: ids.batch, batch_no: 1, delivery_line_id: ids.deliveryLine,
      delivery_id: ids.delivery, delivery_number: 'LDR-CP6-001', vendor_name: 'Laundry Nyata',
      cutting_group_id: ids.group, group_number: 'POT-CP6-001', cutting_group_row_version: 9,
      po_id: ids.po, po_number: 'PO-CP6-001', model_id: ids.model, model_code: 'VIVO-REG',
      model_name: 'Vivo Regular', size_id: ids.sizeS, size_code: 'S', size_sort: 1,
      qty_good_received: 5, qc_accounted_qty_pcs: 0, available_for_qc_qty_pcs: 5,
      completion_status: 'READY_FOR_QC', remaining_qc_qty_pcs: 5,
    }],
  }
}

async function installContract(page: Page, options: ContractOptions = {}): Promise<ContractCalls> {
  const calls: ContractCalls = { workspace: [], actions: [], unexpected: [] }
  const state = options.state ?? { actionAttempts: 0, committed: false, failNextWorkspace: false }
  await page.route(`${uatOrigin}/**`, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: {
        'access-control-allow-origin': localOrigin, 'access-control-allow-credentials': 'true',
        'access-control-allow-headers': 'authorization,apikey,content-type,x-client-info,x-supabase-api-version',
        'access-control-allow-methods': 'GET,POST,OPTIONS',
      } })
      return
    }
    if (url.pathname === '/auth/v1/token' && request.method() === 'POST') {
      await json(route, { access_token: fakeJwt(), token_type: 'bearer', expires_in: 3600, expires_at: 4_102_444_800, refresh_token: 'cp6-local-refresh-token', user: authUser() })
      return
    }
    if (url.pathname === '/auth/v1/user' && request.method() === 'GET') {
      await json(route, authUser())
      return
    }
    const rpcName = url.pathname.startsWith('/rest/v1/rpc/') ? url.pathname.split('/').at(-1) : null
    const payload = request.postDataJSON() as Record<string, unknown> | null
    if (rpcName === 'erp_get_my_access_v1') {
      await json(route, accessBundle(options.permissions))
      return
    }
    if (rpcName === 'erp_get_laundry_qc_workspace_v1') {
      calls.workspace.push(payload ?? {})
      if (state.failNextWorkspace) {
        state.failNextWorkspace = false
        await json(route, { message: 'authoritative refetch failed' }, 503)
        return
      }
      const scope = payload?.p_scope === 'QC' ? 'QC' : 'LAUNDRY'
      await json(route, scope === 'QC' ? qcWorkspace(state.committed) : laundryWorkspace(state.committed))
      return
    }
    if (rpcName === 'erp_save_laundry_qc_action_v1') {
      calls.actions.push(payload ?? {})
      state.actionAttempts += 1
      await new Promise((resolve) => globalThis.setTimeout(resolve, 120))
      if (options.loseFirstActionResponse && state.actionAttempts === 1) {
        state.committed = true
        await route.abort('connectionreset')
        return
      }
      state.committed = true
      if (options.failFirstPostCommitWorkspace && state.actionAttempts === 1) state.failNextWorkspace = true
      await json(route, {
        contract_version: 'CP6_V2620', action: payload?.p_action, committed: true,
        client_request_id: payload?.p_client_request_id,
      })
      return
    }
    calls.unexpected.push(`${request.method()} ${url.pathname}`)
    await json(route, { message: 'Unexpected CP6 local contract request' }, 404)
  })
  return calls
}

async function signIn(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email akun ERP').fill('cp6-owner@example.test')
  await page.getByLabel('Kata sandi').fill('local-contract-password')
  await page.getByRole('button', { name: 'Masuk', exact: true }).click()
  await expect(page.locator('.top-title strong')).toBeVisible()
}

async function openPage(page: Page, projectName: string, label: string, heading: string) {
  if (projectName === 'mobile-chromium') await page.getByRole('button', { name: 'Buka menu' }).click()
  const target = page.getByRole('button', { name: `• ${label}`, exact: true })
  if (!(await target.isVisible())) await page.getByRole('button', { name: /^Produksi/ }).click()
  await target.click()
  await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
}

function watchErrors(page: Page) {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  return () => {
    expect(consoleErrors).toEqual([])
    expect(pageErrors).toEqual([])
  }
}

async function prepareValidLaundrySend(page: Page, reason: string) {
  await page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE').selectOption(ids.batch)
  await page.getByRole('button', { name: 'Isi dari sisa siap' }).click()
  await page.getByLabel('VENDOR LAUNDRY').selectOption(ids.vendor)
  await page.getByLabel('PROSES CUCI TARGET').selectOption(ids.process)
  await page.getByLabel('WARNA TARGET').fill('NAVY')
  await page.getByLabel('WAKTU FISIK KELUAR').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN / BUKTI SERAH TERIMA').fill(reason)
  await page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true }).check()
  await expect(page.getByRole('button', { name: /Post pengiriman atomic/ })).toBeEnabled()
}

test('CP6 Laundry send starts at zero and posts one exact batch-size mutation', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')

  await expect(page.getByText('CP6 · DATA RESMI LAUNDRY', { exact: true })).toBeVisible()
  await page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE').selectOption(ids.batch)
  await expect(page.getByLabel('Qty kirim size S')).toHaveValue('0')
  await expect(page.getByLabel('Qty kirim size M')).toHaveValue('0')
  await page.getByLabel('Qty kirim size S').fill('7x')
  await expect(page.getByLabel('Qty kirim size S')).toHaveValue('7x')
  await expect(page.getByText(/Input mentah tetap ditampilkan/)).toBeVisible()
  await page.getByLabel('Qty kirim size S').fill('7')
  await expect(page.getByLabel('Qty kirim size S')).toHaveValue('7')
  await expect(page.getByText(/Angka tidak diubah diam-diam/)).toBeVisible()
  await page.getByRole('button', { name: 'Isi dari sisa siap' }).click()
  await expect(page.getByLabel('Qty kirim size S')).toHaveValue('6')
  await expect(page.getByLabel('Qty kirim size M')).toHaveValue('4')
  await page.getByLabel('VENDOR LAUNDRY').selectOption(ids.vendor)
  await page.getByLabel('PROSES CUCI TARGET').selectOption(ids.process)
  await page.getByLabel('WARNA TARGET').fill('NAVY')
  await page.getByLabel('ALASAN / BUKTI SERAH TERIMA').fill('Surat jalan fisik sudah dicocokkan')
  await page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true }).check()
  const post = page.getByRole('button', { name: /Post pengiriman atomic/ })
  await expect(post).toBeDisabled()
  await page.getByLabel('WAKTU FISIK KELUAR').fill('2026-09-04T08:00')
  await expect(post).toBeEnabled()
  await post.evaluate((button: HTMLButtonElement) => { button.click(); button.click() })
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'POST_DELIVERY', p_expected_version: 7,
    p_payload: {
      distribution_batch_id: ids.batch, vendor_id: ids.vendor, wash_process_id: ids.process,
      target_dyeing_color: 'NAVY', physical_at: '2026-09-04T01:00:00.000Z',
      lines: [{ size_id: ids.sizeS, qty_sent_pcs: 6 }, { size_id: ids.sizeM, qty_sent_pcs: 4 }],
    },
  })
  expect(calls.actions[0].p_client_request_id).toMatch(/^[0-9a-f-]{36}$/)
  expect(calls.unexpected).toEqual([])
  assertNoErrors()
})

test('CP6 Laundry view-only role sees server facts but every mutation control starts locked', async ({ page }) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page, { permissions: ['production.laundry.view'] })
  await signIn(page)

  await expect(page.getByRole('heading', { name: 'Laundry', exact: true })).toBeVisible()
  await expect(page.getByText('Mode lihat saja untuk pengiriman Laundry.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toBeDisabled()
  await expect(page.getByRole('button', { name: /Post pengiriman atomic/ })).toBeDisabled()
  expect(calls.actions).toEqual([])
  assertNoErrors()
})

test('CP6 two live tabs serialize one global envelope and send at most one operator intent', async ({ page, context }, testInfo) => {
  const state: ContractState = { actionAttempts: 0, committed: false, failNextWorkspace: false }
  const firstCalls = await installContract(page, { state })
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')

  const secondPage = await context.newPage()
  const secondCalls = await installContract(secondPage, { state })
  await secondPage.goto('/')
  await expect(secondPage.locator('.top-title strong')).toBeVisible()
  await openPage(secondPage, testInfo.project.name, 'Laundry', 'Laundry')

  await Promise.all([
    prepareValidLaundrySend(page, 'Tab pertama mencatat serah terima yang sama'),
    prepareValidLaundrySend(secondPage, 'Tab kedua mencoba serah terima yang sama'),
  ])
  await Promise.all([
    page.getByRole('button', { name: /Post pengiriman atomic/ }).evaluate((button: HTMLButtonElement) => button.click()),
    secondPage.getByRole('button', { name: /Post pengiriman atomic/ }).evaluate((button: HTMLButtonElement) => button.click()),
  ])

  await expect.poll(() => firstCalls.actions.length + secondCalls.actions.length).toBe(1)
  await page.waitForTimeout(300)
  expect(firstCalls.actions.length + secondCalls.actions.length).toBe(1)
  expect([...firstCalls.unexpected, ...secondCalls.unexpected]).toEqual([])
  await secondPage.close()
})

test('CP6 Laundry receipt records only Good and BS while Stuck stays derived', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByRole('button', { name: 'Terima kembali', exact: true }).click()
  await page.getByLabel('SURAT KIRIM AKTIF').selectOption(ids.delivery)
  await expect(page.getByText('Belum kembali 4', { exact: true })).toBeVisible()
  await expect(page.getByText('OTHER', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel(/Stuck/i)).toHaveCount(0)
  await page.getByLabel('PROSES AKTUAL').selectOption(ids.process)
  await page.getByLabel('WAKTU FISIK KEMBALI').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN / BUKTI PENERIMAAN').fill('Hitung fisik vendor dan QC cocok')
  await page.getByLabel('Good kembali size S').fill('3')
  await page.getByLabel('BS Laundry size S').fill('1')
  const product = page.getByLabel('SKU BS size S')
  await expect(product.locator('option')).toHaveCount(2)
  await expect(product.locator(`option[value="${ids.wrongProduct}"]`)).toHaveCount(0)
  await expect(product.locator(`option[value="${ids.productS}"]`))
    .toHaveText('Vivo · 73001 · Vivo Pants · NAVY')
  await product.selectOption(ids.productS)
  await expect(page.getByText('Belum kembali 0', { exact: true })).toBeVisible()
  await page.getByRole('checkbox', { name: laundryReceiptConfirmation, exact: true }).check()
  await page.getByRole('button', { name: /Post penerimaan atomic/ }).click()
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'POST_RECEIPT', p_expected_version: 3,
    p_payload: { delivery_id: ids.delivery, physical_at: '2026-09-04T01:00:00.000Z', lines: [{
      delivery_batch_size_line_id: ids.deliverySizeS,
      qty_good_received: 3, qty_bs_laundry: 1, bs_product_id: ids.productS,
    }] },
  })
  expect(JSON.stringify(calls.actions[0])).not.toContain('OTHER')
  expect(JSON.stringify(calls.actions[0])).not.toContain('qty_stuck')
  assertNoErrors()
})

test('CP6 committed send form stays retired after failed then successful refetch', async ({ page }, testInfo) => {
  const calls = await installContract(page, { failFirstPostCommitWorkspace: true })
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE').selectOption(ids.batch)
  await page.getByRole('button', { name: 'Isi dari sisa siap' }).click()
  await page.getByLabel('VENDOR LAUNDRY').selectOption(ids.vendor)
  await page.getByLabel('PROSES CUCI TARGET').selectOption(ids.process)
  await page.getByLabel('WARNA TARGET').fill('NAVY')
  await page.getByLabel('WAKTU FISIK KELUAR').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN / BUKTI SERAH TERIMA').fill('Bukti fisik committed sekali')
  await page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true }).check()
  await page.getByRole('button', { name: /Post pengiriman atomic/ }).click()
  await expect(page.getByText(/Transaksi sudah committed, tetapi refetch gagal/i)).toBeVisible()
  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toHaveValue('')
  await page.getByRole('button', { name: 'Refetch', exact: true }).click()
  await expect(page.getByText('Belum ada pengiriman CP6')).toHaveCount(0)
  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE').locator('option')).toHaveCount(1)
  await expect(page.getByRole('button', { name: /Post pengiriman atomic/ })).toBeDisabled()
  await expect.poll(() => calls.actions.length).toBe(1)
})

test('CP6 lost response reconciles the exact persisted UUID and payload', async ({ page }, testInfo) => {
  const calls = await installContract(page, { loseFirstActionResponse: true })
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE').selectOption(ids.batch)
  await page.getByRole('button', { name: 'Isi dari sisa siap' }).click()
  await page.getByLabel('VENDOR LAUNDRY').selectOption(ids.vendor)
  await page.getByLabel('PROSES CUCI TARGET').selectOption(ids.process)
  await page.getByLabel('WARNA TARGET').fill('NAVY')
  await page.getByLabel('WAKTU FISIK KELUAR').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN / BUKTI SERAH TERIMA').fill('Respons hilang harus reconcile')
  await page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true }).check()
  await page.getByRole('button', { name: /Post pengiriman atomic/ }).click()
  await expect(page.getByRole('button', { name: /Reconcile UUID lama/ })).toBeVisible()
  await page.getByRole('button', { name: /Reconcile UUID lama/ }).click()
  await expect.poll(() => calls.actions.length).toBe(2)
  expect(calls.actions[1]).toEqual(calls.actions[0])
  await expect(page.getByRole('button', { name: /Reconcile UUID lama/ })).toHaveCount(0)
})

test('CP6 QC binds exact receipt batch-size and lets server own stock and HPP', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'QC & Final SKU', 'QC & Final SKU')
  await page.getByLabel('POTONGAN DENGAN GOOD LAUNDRY SIAP QC').selectOption(ids.group)
  await expect(page.getByLabel('Good final size S')).toHaveValue('0')
  await expect(page.getByLabel('BS QC size S')).toHaveValue('0')
  await page.getByRole('button', { name: 'Isi semua sebagai Good' }).click()
  const product = page.getByLabel('Final SKU size S')
  await expect(product.locator('option')).toHaveCount(1)
  await page.getByLabel('WAKTU FISIK QC').fill('2026-09-04T08:00')
  await expect(product.locator('option')).toHaveCount(2)
  await expect(product.locator(`option[value="${ids.productM}"]`)).toHaveCount(0)
  await expect(product.locator(`option[value="${ids.wrongProduct}"]`)).toHaveCount(0)
  await expect(product.locator(`option[value="${ids.productS}"]`))
    .toHaveText('Vivo · 73001 · Vivo Pants · NAVY')
  await product.selectOption(ids.productS)
  await page.getByLabel('LOKASI FG TUJUAN').selectOption(ids.location)
  await page.getByLabel('ALASAN / BUKTI HASIL QC').fill('QC fisik dan label SKU cocok')
  await page.getByRole('checkbox', { name: qcConfirmation, exact: true }).check()
  const post = page.getByRole('button', { name: /Post QC \+ Final SKU atomic/ })
  await post.evaluate((button: HTMLButtonElement) => { button.click(); button.click() })
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'POST_FINAL_SKU', p_expected_version: 9,
    p_payload: {
      cutting_group_id: ids.group, destination_location_id: ids.location,
      physical_at: '2026-09-04T01:00:00.000Z', good_qty_pcs: 5, completion_mode: 'ALL_READY',
      lines: [{
        final_product_id: ids.productS, qty_good_pcs: 5, qty_bs_pcs: 0,
        source_laundry_receipt_line_id: ids.receiptLine,
        source_laundry_receipt_batch_size_line_id: ids.receiptSizeS,
      }],
    },
  })
  expect(JSON.stringify(calls.actions[0])).not.toContain('hpp')
  expect(JSON.stringify(calls.actions[0])).not.toContain('amount')
  assertNoErrors()
})

test('CP6 blocks the legacy browser Nota writer in connected UAT', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Susun Nota FG', 'Susun Nota FG')
  await expect(page.getByText('WRITER DIBLOKIR', { exact: true })).toBeVisible()
  await expect(page.getByText(/Nota FG belum aman untuk disimpan/)).toBeVisible()
  await expect(page.getByText(/Tidak ada data yang dihapus atau diposting/)).toBeVisible()
  await expect(page.getByRole('button', { name: /Post|Simpan|Bayar/ })).toHaveCount(0)
  expect(calls.actions).toEqual([])
  assertNoErrors()
})
