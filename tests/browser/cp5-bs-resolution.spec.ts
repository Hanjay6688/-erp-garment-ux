import { expect, test, type Page, type Route } from '@playwright/test'

const uatOrigin = 'https://siimvrusnzxexizpyoib.supabase.co'
const localOrigin = 'http://127.0.0.1:4174'
const userId = 'c6b00000-0000-4000-8000-000000000001'

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
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: userId, aud: 'authenticated', role: 'authenticated', exp: 4_102_444_800 })}.cp5-local-contract-signature`
}

function authUser() {
  return {
    id: userId, aud: 'authenticated', role: 'authenticated',
    email: 'cp5-owner@example.test', email_confirmed_at: '2026-09-03T00:00:00Z',
    phone: '', confirmed_at: '2026-09-03T00:00:00Z',
    last_sign_in_at: '2026-09-03T00:00:00Z',
    app_metadata: { provider: 'email', providers: ['email'] }, user_metadata: {},
    identities: [], created_at: '2026-09-03T00:00:00Z', updated_at: '2026-09-03T00:00:00Z',
  }
}

function accessBundle(viewOnly: boolean) {
  return {
    allowed: true,
    profile: {
      id: 'c6b00000-0000-4000-8000-000000000002', auth_user_id: userId,
      full_name: viewOnly ? 'CP5 Viewer' : 'CP5 Owner',
      role_id: 'c6b00000-0000-4000-8000-000000000003',
      role_code: viewOnly ? 'PRODUKSI_QC' : 'OWNER', role_name: viewOnly ? 'Produksi QC' : 'Owner',
      is_active: true, row_version: 1, role_row_version: 1,
    },
    permissions: viewOnly
      ? ['dashboard.view', 'production.bs_rework.view', 'master.pattern.view']
      : [
        'dashboard.view', 'production.bs_rework.view', 'production.bs_rework.create',
        'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view',
      ],
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
}

const patternRows = [
  { id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular', sort_order: 1, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 1 },
  { id: 'pattern-2', code: 'SLIM', revision: 'R1', name: 'Slim', sort_order: 2, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 0 },
]

function workspace(patternId: string | null, includeRow = true, partialOrder = false) {
  const result = {
    filter: 'ACTIVE', kind: 'ALL', pattern_id: patternId, query: null,
    limit: 50, offset: 0, total: includeRow ? 1 : 0,
    lookups: {
      contractors: [{ id: 'contractor-1', code: 'M-01', name: 'Mandor A' }],
      vendors: [{ id: 'vendor-1', code: 'L-01', name: 'Laundry A' }],
      fg_locations: [{ id: 'location-1', code: 'FG-01', name: 'Gudang FG' }],
      work_components: [{ id: 'work-1', code: 'JAHIT', name: 'Jahit' }],
      products: [{ id: 'product-1', sku: 'SKU-1', name: 'Produk 1' }],
      laundry_sources: [{ id: 'delivery-1', number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T08:00:00Z', qty_sent_pcs: 10, qty_claimable_pcs: 7 }],
      laundry_receipt_sources: [{ id: 'receipt-line-1', receipt_id: 'receipt-1', number: 'LRC-1', delivery_id: 'delivery-1', delivery_number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T09:00:00Z', qty_bs_laundry: 3, qty_claimable_pcs: 2 }],
      settled_claims: [],
    },
    rows: includeRow ? [{
      case_key: 'BS:case-1', kind: 'BS', id: 'case-1', number: 'BS-1', status: 'OPEN', row_version: 4,
      qty_pcs: 10, resolved_qty: 0, active_rework_qty: 0, available_qty: 10, opened_at: '2026-09-03T08:00:00Z',
      po_id: 'po-1', po_number: 'PO-1', model_name: 'Model A', cutting_group_id: 'group-1', group_number: 'POT-1',
      patterns: [{ id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular' }],
      product_id: 'product-1', sku: 'SKU-1', product_name: 'Produk 1', responsible_contractor_id: 'contractor-1',
      contractor_name: 'Mandor A', responsible_vendor_id: null, vendor_name: null, detected_stage: 'QC', cause_source: 'SEWING',
      untracked_type: null, claim_type: null, compensation_amount: 0, laundry_delivery_id: null, laundry_receipt_line_id: null,
      legacy_reference: null, notes: 'Perlu recovery', next_action: 'START_REWORK_OR_DISPOSITION', is_closed: false,
      accessory_bom: { state: 'AVAILABLE', bom_version_id: 'bom-1', default_policy: 'SERVER_ENTITLEMENT_V2619B', available_qty_pcs: 10, items: [
        { id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', base_uom_code: 'PCS', qty_per_good_fg_base: 2, reimbursement_rate: 100, reimbursement_uom_code: 'PCS', default_selected: true, default_selection_basis: 'UNPAID_BASELINE', default_reason: 'PRE_FG_UNPAID_BASELINE', already_entitled_good_qty_pcs: 0, already_cash_settled_good_qty_pcs: 0, remaining_unentitled_good_qty_pcs: 10 },
        { id: 'bom-item-2', category_id: 'category-2', code: 'LABEL', name: 'Label', base_uom_code: 'PCS', qty_per_good_fg_base: 1, reimbursement_rate: 50, reimbursement_uom_code: 'PCS', default_selected: true, default_selection_basis: 'UNPAID_BASELINE', default_reason: 'PRE_FG_UNPAID_BASELINE', already_entitled_good_qty_pcs: 2, already_cash_settled_good_qty_pcs: 0, remaining_unentitled_good_qty_pcs: 8 },
      ] },
      components: [{ id: 'component-1', work_component_id: 'work-1', code: 'JAHIT', name: 'Jahit', category: 'LABOR', completed_before_bs_qty: 0, lifetime_newly_completed_qty: 0, lifetime_paid_qty: 0, remaining_new_work_qty_pcs: 10, default_selected: true, default_selection_basis: 'UNPAID_COMPONENT_ENTITLEMENT', notes: null }],
      resolutions: [], rework_orders: [] as Array<Record<string, unknown>>, hold_events: [],
    }] : [],
  }
  if (partialOrder && result.rows[0]) {
    const row = result.rows[0]
    row.status = 'IN_REWORK'
    row.active_rework_qty = 4
    row.available_qty = 6
    row.accessory_bom.available_qty_pcs = 6
    row.accessory_bom.items.forEach((item) => { item.remaining_unentitled_good_qty_pcs = 6 })
    row.rework_orders = [{
      id: 'rework-1', rework_number: 'RW-PARTIAL-1', destination_type: 'CONTRACTOR',
      contractor_id: 'contractor-1', contractor_name: 'Mandor A', vendor_id: null, vendor_name: null,
      qty_sent: 4, qty_good_returned: 1, qty_bs_returned: 1,
      physical_sent_at: '2026-09-03T10:00:00Z', completed_at: null, status: 'PARTIAL', cost_posted: false,
      return_fg_location_id: 'location-1', return_fg_location_name: 'Gudang FG', good_fg_lot_id: null,
      row_version: 2, notes: null, components: [],
      accessory_decision: {
        state: 'SELECTED', bom_version_id: 'bom-1', reimbursement_contractor_id: 'contractor-1',
        selected_item_count: 1, selection_sha256: 'b'.repeat(64), basis_at: '2026-09-03T10:00:00Z',
        selected_items: [{
          id: 'choice-1', bom_item_id: 'bom-item-1', category_id: 'category-1',
          code: 'KANCING', name: 'Kancing', qty_per_good_fg_base: 2,
          reimbursement_unit_rate_base: 100, selection_basis: 'UNPAID_BASELINE',
        }],
      },
    }]
  }
  return result
}

async function installLocalUatContract(
  page: Page, viewOnly = false, partialOrder = false, loseFirstActionResponse = false,
): Promise<ContractCalls> {
  const calls: ContractCalls = { workspace: [], actions: [], unexpected: [] }
  let actionAttempts = 0
  await page.route(`${uatOrigin}/**`, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.method() === 'OPTIONS') {
      await route.fulfill({
        status: 204,
        headers: {
          'access-control-allow-origin': localOrigin,
          'access-control-allow-credentials': 'true',
          'access-control-allow-headers': 'authorization,apikey,content-type,x-client-info,x-supabase-api-version',
          'access-control-allow-methods': 'GET,POST,OPTIONS',
        },
      })
      return
    }
    if (url.pathname === '/auth/v1/token' && request.method() === 'POST') {
      const user = authUser()
      await json(route, {
        access_token: fakeJwt(), token_type: 'bearer', expires_in: 3600,
        expires_at: 4_102_444_800, refresh_token: 'cp5-local-refresh-token', user,
      })
      return
    }
    if (url.pathname === '/auth/v1/user' && request.method() === 'GET') {
      await json(route, authUser())
      return
    }
    const rpcName = url.pathname.startsWith('/rest/v1/rpc/') ? url.pathname.split('/').at(-1) : null
    const payload = request.postDataJSON() as Record<string, unknown> | null
    if (rpcName === 'erp_get_my_access_v1') {
      await json(route, accessBundle(viewOnly))
      return
    }
    if (rpcName === 'erp_list_patterns_v1') {
      await json(route, patternRows)
      return
    }
    if (rpcName === 'erp_get_bs_resolution_workspace_v1') {
      const args = payload ?? {}
      calls.workspace.push(args)
      await json(route, workspace(
        (args.p_pattern_id as string | null) ?? null,
        args.p_pattern_id !== 'pattern-2',
        partialOrder,
      ))
      return
    }
    if (rpcName === 'erp_save_bs_resolution_action_v1') {
      calls.actions.push(payload ?? {})
      actionAttempts += 1
      await new Promise((resolve) => globalThis.setTimeout(resolve, 120))
      if (loseFirstActionResponse && actionAttempts === 1) {
        await route.abort('connectionreset')
        return
      }
      await json(route, { request_id: payload?.p_client_request_id, action: payload?.p_action, result: { status: 'ON_HOLD', row_version: 5 } })
      return
    }
    calls.unexpected.push(`${request.method()} ${url.pathname}`)
    await json(route, { message: 'Unexpected local CP5 contract request' }, 404)
  })
  return calls
}

async function signIn(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email akun ERP').fill('cp5-owner@example.test')
  await page.getByLabel('Kata sandi').fill('local-contract-password')
  await page.getByRole('button', { name: 'Masuk', exact: true }).click()
  await expect(page.locator('.top-title strong')).toBeVisible()
}

async function openBsResolution(page: Page, projectName: string) {
  if (projectName === 'mobile-chromium') await page.getByRole('button', { name: 'Buka menu' }).click()
  const target = page.getByRole('button', { name: '• Barang BS & Rework', exact: true })
  if (!(await target.isVisible())) await page.getByRole('button', { name: /^Produksi/ }).click()
  await target.click()
  await expect(page.getByRole('heading', { name: 'Barang BS & Rework' })).toBeVisible()
}

test('CP5 local mocked-UAT contract keeps server-side Pattern truth and one mutation', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  const calls = await installLocalUatContract(page)

  await signIn(page)
  await openBsResolution(page, testInfo.project.name)
  await expect(page.getByText('UAT BACKEND CONNECTED', { exact: true })).toBeVisible()
  await expect(page.getByText('REG · R2 · Regular', { exact: true }).first()).toBeVisible()

  await page.getByLabel('FILTER POLA CP5').selectOption('pattern-2')
  await expect(page.getByText('Tidak ada kasus pada filter ini')).toBeVisible()
  await expect(page.getByText('Tidak ada detail')).toBeVisible()
  await expect(page.getByText('BS-1', { exact: true })).toHaveCount(0)
  expect(calls.workspace.filter((args) => args.p_pattern_id === 'pattern-2')).toHaveLength(1)

  await page.getByLabel('FILTER POLA CP5').selectOption('pattern-1')
  await expect(page.locator('.cbsr-detail').getByRole('heading', { name: 'BS-1', exact: true })).toBeVisible()
  const accessoryChoice = page.getByRole('group', { name: /AKSESORI YANG BENAR-BENAR DIPASANG/ })
  await expect(accessoryChoice.getByText('KANCING · Kancing')).toBeVisible()
  const labelChoice = accessoryChoice.getByRole('checkbox', { name: /LABEL · Label/ })
  await expect(labelChoice).toBeChecked()
  await labelChoice.uncheck()
  await expect(labelChoice).not.toBeChecked()
  await labelChoice.check()
  await expect(labelChoice).toBeChecked()
  await page.locator('.cbsr-route-tabs').getByRole('button', { name: 'Hold', exact: true }).click()
  await page.locator('.cbsr-route-form textarea').fill('Menunggu bukti fisik Laundry')
  const saveHold = page.getByRole('button', { name: /Simpan HOLD/ })
  await expect(saveHold).toBeEnabled()
  await saveHold.evaluate((button: HTMLButtonElement) => { button.click(); button.click() })
  await expect.poll(() => calls.actions.length).toBe(1)
  await expect(page.getByText(/HOLD BS tersimpan/)).toBeVisible()
  expect(calls.actions[0]).toMatchObject({
    p_action: 'HOLD_BS', p_expected_version: 4,
    p_payload: { bs_case_id: 'case-1', change_reason: 'Menunggu bukti fisik Laundry' },
  })

  await testInfo.attach('cp5-local-mocked-uat-contract', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS', proof_class: 'LOCAL_MOCKED_UAT_CONTRACT',
      target_host: 'siimvrusnzxexizpyoib.supabase.co', hosted_uat: false,
      server_side_pattern_filter: true, same_frame_mutation_count: calls.actions.length,
      direct_table_access: false, production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
  expect(calls.unexpected).toEqual([])
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
})

test('CP5 lost commit response survives reload and reconciles the exact persisted request', async ({ page }, testInfo) => {
  const calls = await installLocalUatContract(page, false, false, true)
  await signIn(page)
  await openBsResolution(page, testInfo.project.name)

  await page.locator('.cbsr-route-tabs').getByRole('button', { name: 'Hold', exact: true }).click()
  await page.locator('.cbsr-route-form textarea').fill('Menunggu bukti fisik Laundry')
  const saveHold = page.getByRole('button', { name: /Simpan HOLD/ })
  await saveHold.click()
  await expect(page.getByText(/Hasil transaksi belum diketahui/).first()).toBeVisible()
  await expect(saveHold).toBeDisabled()
  await expect(page.getByRole('button', { name: /Claim Laundry/ })).toBeDisabled()
  expect(calls.actions).toHaveLength(1)

  await page.reload()
  await expect(page.locator('.top-title strong')).toBeVisible()
  await openBsResolution(page, testInfo.project.name)
  await expect(page.getByText(/Hasil transaksi belum diketahui/).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /Claim Laundry/ })).toBeDisabled()

  await page.getByRole('button', { name: 'Refetch', exact: true }).click()
  await expect(page.getByText(/Hasil transaksi belum diketahui/).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /Claim Laundry/ })).toBeDisabled()

  await page.getByRole('button', { name: /Reconcile transaksi/ }).click()
  await expect(page.getByText(/sudah direconcile dengan UUID lama/)).toBeVisible()
  await expect(page.getByRole('button', { name: /Claim Laundry/ })).toBeEnabled()
  expect(calls.actions).toHaveLength(2)
  expect(calls.actions[1]).toEqual(calls.actions[0])

  await testInfo.attach('cp5-lost-response-reconciliation', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS', proof_class: 'LOCAL_MOCKED_UAT_CONTRACT',
      simulated_server_commit_count: 1, transport_attempt_count: calls.actions.length,
      same_idempotency_uuid: calls.actions[0]?.p_client_request_id === calls.actions[1]?.p_client_request_id,
      exact_payload_replay: true, persisted_across_reload: true,
      hosted_uat: false, production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
  expect(calls.unexpected).toEqual([])
})

test('CP5 local mocked-UAT contract saves cumulative partial return without posting completion', async ({ page }, testInfo) => {
  const calls = await installLocalUatContract(page, false, true)
  await signIn(page)
  await openBsResolution(page, testInfo.project.name)

  await expect(page.getByText('RW-PARTIAL-1', { exact: true }).first()).toBeVisible()
  await page.getByLabel('GOOD KUMULATIF').fill('2')
  await page.getByLabel('BS KUMULATIF').fill('1')
  await page.getByLabel('ALASAN HASIL FISIK').fill('Tiga barang sudah kembali fisik')
  const savePartial = page.getByRole('button', { name: /Simpan partial/ })
  await expect(savePartial).toBeEnabled()
  await savePartial.click()
  await expect.poll(() => calls.actions.length).toBe(1)
  expect(calls.actions[0]).toMatchObject({
    p_action: 'SAVE_REWORK', p_expected_version: 2,
    p_payload: {
      id: 'rework-1', action: 'SAVE', qty_good_returned: 2,
      qty_bs_returned: 1, return_fg_location_id: 'location-1',
    },
  })
  expect(calls.actions[0]?.p_action).not.toBe('COMPLETE_REWORK')
  expect(calls.unexpected).toEqual([])

  await testInfo.attach('cp5-partial-return-contract', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS', proof_class: 'LOCAL_MOCKED_UAT_CONTRACT',
      action: 'SAVE_REWORK', completion_posted: false,
      hosted_uat: false, production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
})

test('CP5 local mocked-UAT contract keeps view-only identity non-executable', async ({ page }, testInfo) => {
  const calls = await installLocalUatContract(page, true)
  await signIn(page)
  await openBsResolution(page, testInfo.project.name)

  await expect(page.getByRole('button', { name: /Claim Laundry/ })).toBeDisabled()
  await expect(page.getByRole('button', { name: /BS legacy/ })).toBeDisabled()
  await page.locator('.cbsr-route-tabs').getByRole('button', { name: 'Hold', exact: true }).click()
  await expect(page.getByRole('button', { name: /Simpan HOLD/ })).toBeDisabled()
  expect(calls.actions).toEqual([])
  expect(calls.unexpected).toEqual([])

  await testInfo.attach('cp5-view-only-contract', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS', proof_class: 'LOCAL_MOCKED_UAT_CONTRACT',
      view_only_mutation_count: 0, hosted_uat: false, production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
})
