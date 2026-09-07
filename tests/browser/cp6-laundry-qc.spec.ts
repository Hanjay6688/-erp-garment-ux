import { expect, test, type Page, type Route } from '@playwright/test'

const uatOrigin = 'https://siimvrusnzxexizpyoib.supabase.co'
const localOrigin = 'http://127.0.0.1:4175'
const userId = 'c8b00000-0000-4000-8000-000000000001'
const laundrySendConfirmation = 'Saya sudah mencocokkan vendor, batch, ukuran, jumlah, warna, dan waktu dengan serah-terima fisik.'
const laundryReceiptConfirmation = 'Saya sudah menghitung fisik per ukuran; Good dan BS benar, sisanya memang belum kembali.'
const failedWashConfirmation = 'Saya sudah mencocokkan bukti tagihan, proses, jumlah per ukuran, waktu, dan posisi fisik. Tidak ada Good atau BS yang diterima dari attempt ini.'
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
  productBeyond500: 'c8b20000-0000-4000-8000-000000000010',
  delivery: 'c8b30000-0000-4000-8000-000000000001',
  deliveryLine: 'c8b30000-0000-4000-8000-000000000002',
  deliverySizeS: 'c8b30000-0000-4000-8000-000000000003',
  receipt: 'c8b30000-0000-4000-8000-000000000004',
  receiptLine: 'c8b30000-0000-4000-8000-000000000005',
  receiptSizeS: 'c8b30000-0000-4000-8000-000000000006',
  qcInspection: 'c8b30000-0000-4000-8000-000000000007',
  fullDelivery: 'c8b30000-0000-4000-8000-000000000008',
  fullDeliveryLine: 'c8b30000-0000-4000-8000-000000000009',
  fullDeliverySizeM: 'c8b30000-0000-4000-8000-000000000010',
  failedReceipt: 'c8b30000-0000-4000-8000-000000000011',
  failedAttempt: 'c8b30000-0000-4000-8000-000000000012',
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
  productSearch: Record<string, unknown>[]
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
      lineage_integrity_ok: true, lineage_issue_count: 0,
      no_fixture_fallback: true, failed_wash_with_charge_supported: true,
    },
    collection_window: {
      transaction_limit: 200, product_limit: 500, query_required_for_more: true,
      transaction_query_scope: 'SOURCE_QUEUE_AND_HISTORY',
      product_search_contract: 'CP6_PRODUCT_SEARCH_V2620B', product_query_decoupled: true,
      products_relevant_to_live_qc: scope === 'QC', products_truncated: false,
      ready_batches_truncated: false, deliveries_truncated: false,
      qc_queue_truncated: false, qc_history_truncated: false, any_truncated: false,
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
      contractor_code: 'M-01', contractor_name: 'Mandor A', picked_up_at: '2026-09-04T00:30:00Z',
      group_unsent_ready_qty_pcs: 10,
      sizes: [
        { size_id: ids.sizeS, size_code: 'S', sort_order: 1, allocated_qty_pcs: 6, sent_qty_pcs: 0, available_qty_pcs: 6 },
        { size_id: ids.sizeM, size_code: 'M', sort_order: 2, allocated_qty_pcs: 4, sent_qty_pcs: 0, available_qty_pcs: 4 },
      ],
    }],
    deliveries: [{
      delivery_id: ids.delivery, delivery_number: 'LDR-CP6-001', row_version: 3, status: 'PARTIAL_RETURN',
      physical_at: '2026-09-04T00:40:00Z', target_dyeing_color: 'NAVY', special_instruction: null,
      po_id: ids.po, po_number: 'PO-CP6-001', model_id: ids.model, cutting_group_id: ids.group,
      group_number: 'POT-CP6-001', cutting_group_row_version: 7, model_code: 'VIVO-REG',
      model_name: 'Vivo Regular', contractor_name: 'Mandor A', vendor_id: ids.vendor,
      vendor_code: 'L-01', vendor_name: 'Laundry Nyata', wash_process_id: ids.process,
      process_code: 'BIO', process_name: 'Bio Wash', delivery_line_id: ids.deliveryLine,
      qty_sent_pcs: 6, estimated_rate_snapshot: 700, estimated_cost: 4200,
      distribution_batch_id: ids.batch, batch_no: 1, returned_qty_pcs: 2,
      physical_outstanding_qty_pcs: 4, returned_unprocessed_qty_pcs: 0,
      active_claim_qty_pcs: 0, reversible: false,
      reversal_blocker: 'Masih ada barang fisik di luar Laundry.',
      sizes: [{
        delivery_batch_size_line_id: ids.deliverySizeS, size_id: ids.sizeS, size_code: 'S', sort_order: 1,
        qty_sent_pcs: 6, good_returned_qty_pcs: 2, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 4,
      }], receipts: [{
        id: ids.receipt, number: 'LRC-CP6-001', status: 'POSTED', row_version: 4,
        physical_at: '2026-09-04T00:50:00Z', actual_cost: null, actual_rate: null,
        cost_status: 'ESTIMATED', event_kind: 'PHYSICAL_RECEIPT',
        failed_wash_attempt_id: null, custody_outcome: null,
        attempted_qty_pcs: null, process_name: null, reversible: false,
        reversal_blocker: 'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.',
      }],
    }, {
      delivery_id: ids.fullDelivery, delivery_number: 'LDR-CP6-FULL', row_version: 5, status: 'SENT',
      physical_at: '2026-09-04T00:42:00Z', target_dyeing_color: 'NAVY', special_instruction: null,
      po_id: ids.po, po_number: 'PO-CP6-001', model_id: ids.model, cutting_group_id: ids.group,
      group_number: 'POT-CP6-001', cutting_group_row_version: 7, model_code: 'VIVO-REG',
      model_name: 'Vivo Regular', contractor_name: 'Mandor A', vendor_id: ids.vendor,
      vendor_code: 'L-01', vendor_name: 'Laundry Nyata', wash_process_id: ids.process,
      process_code: 'BIO', process_name: 'Bio Wash', delivery_line_id: ids.fullDeliveryLine,
      qty_sent_pcs: 4, estimated_rate_snapshot: 700, estimated_cost: 2800,
      distribution_batch_id: ids.batch, batch_no: 1, returned_qty_pcs: 0,
      physical_outstanding_qty_pcs: 4, returned_unprocessed_qty_pcs: 0,
      active_claim_qty_pcs: 0, reversible: false,
      reversal_blocker: 'Masih ada receipt aktif; reverse receipt terlebih dahulu.',
      sizes: [{
        delivery_batch_size_line_id: ids.fullDeliverySizeM, size_id: ids.sizeM, size_code: 'M', sort_order: 2,
        qty_sent_pcs: 4, good_returned_qty_pcs: 0, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 4,
      }], receipts: [{
        id: ids.failedReceipt, number: 'LFW-CP6-001', status: 'POSTED', row_version: 2,
        physical_at: '2026-09-04T00:55:00Z', actual_cost: 2800, actual_rate: 700,
        cost_status: 'ESTIMATED', event_kind: 'FAILED_WASH_ATTEMPT',
        failed_wash_attempt_id: ids.failedAttempt, custody_outcome: 'RETRY_AT_VENDOR',
        attempted_qty_pcs: 4, process_name: 'Bio Wash', reversible: true,
        reversal_blocker: null,
      }],
    }],
  }
}

function qcWorkspace(committed = false) {
  return {
    ...baseWorkspace('QC'),
    qc_queue: committed ? [] : [{
      source_batch_size_line_id: ids.receiptSizeS, receipt_line_id: ids.receiptLine,
      receipt_id: ids.receipt, receipt_number: 'LRC-CP6-001', receipt_physical_at: '2026-09-04T00:50:00Z',
      distribution_batch_id: ids.batch, batch_no: 1, delivery_line_id: ids.deliveryLine,
      delivery_id: ids.delivery, delivery_number: 'LDR-CP6-001', vendor_name: 'Laundry Nyata',
      cutting_group_id: ids.group, group_number: 'POT-CP6-001', cutting_group_row_version: 9,
      po_id: ids.po, po_number: 'PO-CP6-001', model_id: ids.model, model_code: 'VIVO-REG',
      model_name: 'Vivo Regular', size_id: ids.sizeS, size_code: 'S', size_sort: 1,
      qty_good_received: 5, qc_accounted_qty_pcs: 0, available_for_qc_qty_pcs: 5,
      completion_status: 'READY_FOR_QC', remaining_qc_qty_pcs: 5,
    }],
    qc_history: [{
      qc_inspection_id: ids.qcInspection, inspection_number: 'QC-CP6-BLOCKED', status: 'POSTED',
      row_version: 6, physical_at: '2026-09-04T01:10:00Z',
      destination_location_id: ids.location, location_name: 'Gudang FG Utama',
      po_id: ids.po, po_number: 'PO-CP6-001', good_qty_pcs: 5, bs_qty_pcs: 0,
      cutting_group_count: 1, reversible: false,
      reversal_blocker: 'FG hasil QC masih dipakai transaksi downstream aktif.',
    }],
  }
}

async function installContract(page: Page, options: ContractOptions = {}): Promise<ContractCalls> {
  const calls: ContractCalls = { workspace: [], productSearch: [], actions: [], unexpected: [] }
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
    if (rpcName === 'erp_search_final_sku_products_v1') {
      calls.productSearch.push(payload ?? {})
      await json(route, {
        contract_version: 'CP6_PRODUCT_SEARCH_V2620B',
        source_laundry_receipt_batch_size_line_id: payload?.p_source_laundry_receipt_batch_size_line_id,
        physical_at: payload?.p_physical_at,
        query: typeof payload?.p_query === 'string' ? payload.p_query.toLowerCase() : null,
        page_limit: 50,
        products: [{
          id: ids.productBeyond500, sku: '73999', name: 'Vivo Beyond 500',
          model_id: ids.model, model_code: 'VIVO', model_name: 'Vivo Pants',
          brand_id: ids.brand, brand_code: 'VIVO', brand_name: 'Vivo',
          size_id: ids.sizeS, size_code: 'S', color: 'OCEAN',
          effective_from: '2026-01-01T00:00:00Z', effective_to: null,
        }],
        has_more: false, next_cursor: null,
      })
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
  const confirmation = page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true })
  await confirmation.check()
  const post = page.getByRole('button', { name: /Post pengiriman atomic/ })
  await expect(post).toBeDisabled()
  await page.getByLabel('WAKTU FISIK KELUAR').fill('2026-09-04T08:00')
  await expect(confirmation).not.toBeChecked()
  await expect(post).toBeDisabled()
  await confirmation.check()
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
  await prepareValidLaundrySend(page, 'Tab pertama mencatat serah terima yang sama')

  const secondPage = await context.newPage()
  const secondCalls = await installContract(secondPage, { state })
  await secondPage.goto('/')
  await expect(secondPage.locator('.top-title strong')).toBeVisible()
  await openPage(secondPage, testInfo.project.name, 'Laundry', 'Laundry')

  await expect(page.getByRole('heading', { name: 'Laundry', exact: true })).toBeVisible()
  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toHaveValue(ids.batch)
  await expect(page.getByLabel('Qty kirim size S')).toHaveValue('6')
  await expect(page.getByLabel('WAKTU FISIK KELUAR')).toHaveValue('2026-09-04T08:00')
  await expect(page.getByLabel('ALASAN / BUKTI SERAH TERIMA'))
    .toHaveValue('Tab pertama mencatat serah terima yang sama')
  await expect(page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true })).toBeChecked()
  await prepareValidLaundrySend(secondPage, 'Tab kedua mencoba serah terima yang sama')
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

test('CP6 authoritative refetch expires an earlier physical acknowledgement', async ({ page }, testInfo) => {
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await prepareValidLaundrySend(page, 'Bukti fisik wajib habis saat data berubah')
  const confirmation = page.getByRole('checkbox', { name: laundrySendConfirmation, exact: true })
  const post = page.getByRole('button', { name: /Post pengiriman atomic/ })
  await expect(confirmation).toBeChecked()
  await expect(post).toBeEnabled()

  await page.getByRole('button', { name: 'Muat ulang data', exact: true }).click()
  await expect.poll(() => calls.workspace.length).toBe(2)
  await expect(confirmation).not.toBeChecked()
  await expect(post).toBeDisabled()
  expect(calls.actions).toEqual([])
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
  const product = page.getByLabel('SKU BS size S', { exact: true })
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

test('CP6 paid failed-wash retry posts cost without inventing a physical receipt', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByRole('button', { name: 'Cuci gagal berbayar', exact: true }).click()
  await page.getByLabel('SURAT KIRIM GAGAL CUCI').selectOption(ids.delivery)
  await expect(page.getByLabel('Qty gagal cuci size S')).toHaveValue('0')
  await page.getByLabel('PROSES GAGAL CUCI').selectOption(ids.process)
  await page.getByLabel('POSISI FISIK GAGAL CUCI').selectOption('RETRY_AT_VENDOR')
  await page.getByLabel('WAKTU GAGAL CUCI').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN TAGIHAN GAGAL CUCI').fill('Kimia habis setelah attempt dimulai')
  await page.getByLabel('Qty gagal cuci size S').fill('4x')
  await expect(page.getByLabel('Qty gagal cuci size S')).toHaveValue('4x')
  await expect(page.getByText(/input tidak diubah diam-diam/i)).toBeVisible()
  await page.getByLabel('Qty gagal cuci size S').fill('4')
  await page.getByRole('checkbox', { name: failedWashConfirmation, exact: true }).check()
  await page.getByRole('button', { name: /Post jasa gagal cuci atomic/ }).click()
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'POST_FAILED_WASH', p_expected_version: 3,
    p_payload: {
      delivery_id: ids.delivery, wash_process_id: ids.process,
      custody_outcome: 'RETRY_AT_VENDOR', physical_at: '2026-09-04T01:00:00.000Z',
      lines: [{ delivery_batch_size_line_id: ids.deliverySizeS, qty_attempted_pcs: 4 }],
    },
  })
  expect(JSON.stringify(calls.actions[0])).not.toContain('qty_good_received')
  expect(JSON.stringify(calls.actions[0])).not.toContain('qty_bs_laundry')
  assertNoErrors()
})

test('CP6 paid full return is exact, all-or-nothing, and retires the committed form', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByRole('button', { name: 'Cuci gagal berbayar', exact: true }).click()
  await page.getByLabel('SURAT KIRIM GAGAL CUCI').selectOption(ids.fullDelivery)
  await page.getByLabel('PROSES GAGAL CUCI').selectOption(ids.process)
  await page.getByLabel('POSISI FISIK GAGAL CUCI').selectOption('RETURN_UNPROCESSED')
  await expect(page.getByLabel('Qty gagal cuci size M')).toHaveValue('4')
  await expect(page.getByLabel('Qty gagal cuci size M')).toBeDisabled()
  await expect(page.getByText(/Seluruh fisik kembali ke Jahit/)).toBeVisible()
  await page.getByLabel('WAKTU GAGAL CUCI').fill('2026-09-04T08:00')
  await page.getByLabel('ALASAN TAGIHAN GAGAL CUCI').fill('Vendor tidak mampu lanjut dan mengembalikan semua')
  await page.getByRole('checkbox', { name: failedWashConfirmation, exact: true }).check()
  await page.getByRole('button', { name: /Post jasa gagal cuci atomic/ }).click()
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'POST_FAILED_WASH', p_expected_version: 5,
    p_payload: {
      delivery_id: ids.fullDelivery, wash_process_id: ids.process,
      custody_outcome: 'RETURN_UNPROCESSED', physical_at: '2026-09-04T01:00:00.000Z',
      lines: [{ delivery_batch_size_line_id: ids.fullDeliverySizeM, qty_attempted_pcs: 4 }],
    },
  })
  await expect(page.getByLabel('SURAT KIRIM GAGAL CUCI')).toHaveValue('')
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
  await expect(page.getByText('Cuci gagal berbayar dicatat dari tab Laundry sebagai attempt biaya terpisah;', { exact: false })).toBeVisible()
  await expect(page.getByText(/tetap ditahan sampai alur hutang vendor/i)).toHaveCount(0)
  await page.getByLabel('POTONGAN DENGAN GOOD LAUNDRY SIAP QC').selectOption(ids.group)
  await expect(page.getByLabel('Good final size S')).toHaveValue('0')
  await expect(page.getByLabel('BS QC size S')).toHaveValue('0')
  await page.getByRole('button', { name: 'Isi semua sebagai Good' }).click()
  const product = page.getByLabel('Final SKU size S', { exact: true })
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

test('CP6 QC finds an SKU beyond the initial catalog without hiding its source queue', async ({ page }, testInfo) => {
  const assertNoErrors = watchErrors(page)
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'QC & Final SKU', 'QC & Final SKU')

  const source = page.getByLabel('POTONGAN DENGAN GOOD LAUNDRY SIAP QC')
  await source.selectOption(ids.group)
  await page.getByRole('button', { name: 'Isi semua sebagai Good' }).click()
  await page.getByLabel('WAKTU FISIK QC').fill('2026-09-04T08:00')
  const product = page.getByLabel('Final SKU size S', { exact: true })
  await expect(product.locator(`option[value="${ids.productBeyond500}"]`)).toHaveCount(0)

  await page.getByLabel('Cari Final SKU size S', { exact: true }).fill('73999')
  await page.getByRole('button', { name: 'Cari SKU', exact: true }).click()
  await expect.poll(() => calls.productSearch.length).toBe(1)
  expect(calls.productSearch[0]).toMatchObject({
    p_source_laundry_receipt_batch_size_line_id: ids.receiptSizeS,
    p_physical_at: '2026-09-04T01:00:00.000Z',
    p_query: '73999', p_after_sort_key: null, p_limit: 50,
  })
  await expect(product.locator(`option[value="${ids.productBeyond500}"]`))
    .toHaveText('Vivo · 73999 · Vivo Pants · OCEAN')
  await expect(source).toHaveValue(ids.group)
  await expect(page.getByText(/antrean QC dan pilihan sumber tidak berubah/i)).toBeVisible()

  await product.selectOption(ids.productBeyond500)
  await page.getByLabel('WAKTU FISIK QC').fill('2026-09-04T08:01')
  await expect(product).toHaveValue('')
  await expect(product.locator(`option[value="${ids.productBeyond500}"]`)).toHaveCount(0)
  expect(calls.workspace).toHaveLength(1)
  expect(calls.actions).toEqual([])
  expect(calls.unexpected).toEqual([])
  assertNoErrors()
})

test('CP6 reversal buttons obey authoritative downstream blockers', async ({ page }, testInfo) => {
  const calls = await installContract(page)
  await signIn(page)
  await openPage(page, testInfo.project.name, 'Laundry', 'Laundry')
  await page.getByRole('button', { name: 'Riwayat & koreksi', exact: true }).click()
  await expect(page.getByText('Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Batalkan penerimaan', exact: true })).toBeDisabled()
  await expect(page.getByText(/Cuci gagal berbayar · fisik tetap di vendor/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Batalkan biaya attempt', exact: true })).toBeDisabled()
  await page.getByLabel('Alasan reversal LFW-CP6-001', { exact: true }).fill('Tagihan attempt salah dan harus dibalik')
  await expect(page.getByRole('button', { name: 'Batalkan biaya attempt', exact: true })).toBeEnabled()

  await openPage(page, testInfo.project.name, 'QC & Final SKU', 'QC & Final SKU')
  await page.getByRole('button', { name: 'Riwayat & koreksi', exact: true }).click()
  await expect(page.getByText('FG hasil QC masih dipakai transaksi downstream aktif.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Batalkan finalisasi', exact: true })).toBeDisabled()
  expect(calls.actions).toEqual([])
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
