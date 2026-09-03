// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedBsResolutionPage from './ConnectedBsResolutionPage'

const authState = vi.hoisted(() => ({ current: null as unknown }))
const mockedClient = vi.hoisted(() => ({ current: null as unknown }))

vi.mock('./auth/AuthProvider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('./lib/supabase', () => ({
  getUatSupabaseClient: () => mockedClient.current,
}))

const runtime = {
  mode: 'UAT_AUTH_SIMULATION',
  authMode: 'UAT_SUPABASE',
  businessDataMode: 'PARTIAL_CONNECTED',
  businessRpcEnabled: true,
  accessControlMode: 'CONNECTED',
  patternMode: 'CONNECTED',
  cuttingMode: 'CONNECTED',
  distributionMode: 'CONNECTED',
  wipStatusMode: 'CONNECTED',
  bsResolutionMode: 'CONNECTED',
  projectRef: 'siimvrusnzxexizpyoib',
  supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_cp5_dom_fixture_20260903',
} as const

const patterns = [
  { id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular', sort_order: 1, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 1 },
  { id: 'pattern-2', code: 'SLIM', revision: 'R1', name: 'Slim', sort_order: 2, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 0 },
]

function workspace(patternId: string | null = null, includeRow = true) {
  return {
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
      accessory_bom: { state: 'AVAILABLE', bom_version_id: 'bom-1', items: [
        { id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', base_uom_code: 'PCS', qty_per_good_fg_base: 2, reimbursement_rate: 100, reimbursement_uom_code: 'PCS' },
        { id: 'bom-item-2', category_id: 'category-2', code: 'LABEL', name: 'Label', base_uom_code: 'PCS', qty_per_good_fg_base: 1, reimbursement_rate: 50, reimbursement_uom_code: 'PCS' },
      ] },
      components: [{ id: 'component-1', work_component_id: 'work-1', code: 'JAHIT', name: 'Jahit', category: 'LABOR', completed_before_bs_qty: 0, lifetime_newly_completed_qty: 0, lifetime_paid_qty: 0, notes: null }],
      resolutions: [], rework_orders: [] as Array<Record<string, unknown>>, hold_events: [],
    }] : [],
  }
}

function identity(permissions: string[], role = 'OWNER') {
  return {
    runtime,
    identity: {
      status: 'AUTHORIZED',
      profile: {
        id: 'app-user-1', authUserId: 'auth-user-1', fullName: 'CP5 Owner',
        roleId: 'role-1', role, roleName: role, isActive: true,
        rowVersion: 1, roleRowVersion: 1,
      },
      permissions,
      externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
    },
    signingOut: false, signOutError: null,
    signIn: vi.fn(), signOut: vi.fn(), retryIdentity: vi.fn(),
  }
}

function setControlValue(control: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string) {
  const prototype = control instanceof HTMLSelectElement
    ? HTMLSelectElement.prototype
    : control instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set
  if (!setter) throw new Error('DOM value setter is unavailable.')
  setter.call(control, value)
  control.dispatchEvent(new Event(control instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true }))
}

async function settle(delay = 0) {
  await act(async () => { await new Promise((resolve) => globalThis.setTimeout(resolve, delay)) })
}

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

async function renderPage() {
  await act(async () => { root.render(<ConnectedBsResolutionPage />) })
  await settle(220)
}

describe('CP5 connected BS Resolution DOM boundary', () => {
  it('keeps Pattern empty state authoritative and blocks a same-frame double mutation', async () => {
    let finishAction: ((value: { data: unknown; error: null }) => void) | undefined
    const actionResult = new Promise<{ data: unknown; error: null }>((resolve) => { finishAction = resolve })
    const rpc = vi.fn(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_bs_resolution_workspace_v1') {
        return { data: workspace((args.p_pattern_id as string | null) ?? null, args.p_pattern_id !== 'pattern-2'), error: null }
      }
      if (name === 'erp_save_bs_resolution_action_v1') return actionResult
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity([
      'production.bs_rework.view', 'production.bs_rework.create',
      'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view',
    ])

    await renderPage()
    expect(container.textContent).toContain('BS-1')
    expect(container.textContent).toContain('REG · R2 · Regular')

    const holdTab = [...container.querySelectorAll<HTMLButtonElement>('.cbsr-route-tabs button')]
      .find((button) => button.textContent?.trim() === 'Hold')
    expect(holdTab).toBeTruthy()
    await act(async () => { holdTab!.click() })
    const reason = container.querySelector<HTMLTextAreaElement>('.cbsr-route-form textarea')!
    await act(async () => { setControlValue(reason, 'Bukti fisik belum lengkap') })
    const saveHold = [...container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Simpan HOLD'))
    expect(saveHold?.disabled).toBe(false)

    await act(async () => {
      saveHold!.click()
      saveHold!.click()
      await Promise.resolve()
    })
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_bs_resolution_action_v1')).toHaveLength(1)
    expect(rpc.mock.calls.find(([name]) => name === 'erp_save_bs_resolution_action_v1')?.[1]).toMatchObject({
      p_action: 'HOLD_BS', p_expected_version: 4,
      p_payload: { bs_case_id: 'case-1', change_reason: 'Bukti fisik belum lengkap' },
    })
    await act(async () => { finishAction!({ data: { ok: true }, error: null }) })
    await settle()

    const patternFilter = container.querySelector<HTMLSelectElement>('select[aria-label="FILTER POLA CP5"]')!
    await act(async () => { setControlValue(patternFilter, 'pattern-2') })
    await settle()
    expect(rpc.mock.calls.filter(([name, args]) => name === 'erp_get_bs_resolution_workspace_v1' && args.p_pattern_id === 'pattern-2')).toHaveLength(1)
    expect(container.textContent).toContain('Tidak ada kasus pada filter ini')
    expect(container.textContent).toContain('Tidak ada detail')
    expect(container.textContent).not.toContain('BS-1')
  })

  it('sends only checked accessory BOM items when a rework order is created', async () => {
    const rpc = vi.fn(async (name: string, _args?: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_bs_resolution_workspace_v1') return { data: workspace(), error: null }
      if (name === 'erp_save_bs_resolution_action_v1') return { data: { ok: true }, error: null }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity([
      'production.bs_rework.view', 'production.bs_rework.create',
      'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view',
    ])

    await renderPage()
    const routeForm = container.querySelector<HTMLElement>('.cbsr-route-form')!
    const number = routeForm.querySelector<HTMLInputElement>('input[placeholder="RW-BS-1"]')!
    const party = routeForm.querySelector<HTMLSelectElement>('select')!
    const reason = routeForm.querySelector<HTMLTextAreaElement>('textarea')!
    await act(async () => {
      setControlValue(number, 'RW-BS-1-A')
      setControlValue(party, 'contractor-1')
      setControlValue(reason, 'Pasang kancing saja sesuai fisik')
      routeForm.querySelectorAll<HTMLInputElement>('.cbsr-accessories input[type="checkbox"]')[1]!.click()
    })
    const create = [...routeForm.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Buat order rework'))!
    expect(create.disabled).toBe(false)
    await act(async () => { create.click() })
    await settle()

    const call = rpc.mock.calls.find(([name]) => name === 'erp_save_bs_resolution_action_v1')
    expect(call?.[1]).toMatchObject({
      p_action: 'SAVE_REWORK', p_expected_version: null,
      p_payload: {
        accessory_bom_version_id: 'bom-1', accessory_bom_item_ids: ['bom-item-1'],
        components: [{ bs_case_component_id: 'component-1', qty_performed: 10 }],
      },
    })
  })

  it('saves cumulative partial returns without calling the completion action', async () => {
    const partial = workspace()
    const row = partial.rows[0]
    row.status = 'IN_REWORK'
    row.active_rework_qty = 4
    row.available_qty = 6
    row.rework_orders = [{
      id: 'rework-1', rework_number: 'RW-PARTIAL-1', destination_type: 'CONTRACTOR',
      contractor_id: 'contractor-1', contractor_name: 'Mandor A', vendor_id: null, vendor_name: null,
      qty_sent: 4, qty_good_returned: 1, qty_bs_returned: 1,
      physical_sent_at: '2026-09-03T10:00:00Z', completed_at: null, status: 'PARTIAL', cost_posted: false,
      return_fg_location_id: 'location-1', return_fg_location_name: 'Gudang FG', good_fg_lot_id: null,
      row_version: 2, notes: null, components: [],
      accessory_decision: { state: 'SELECTED', bom_version_id: 'bom-1', reimbursement_contractor_id: 'contractor-1', selected_item_count: 1, selection_sha256: 'b'.repeat(64), basis_at: '2026-09-03T10:00:00Z', selected_items: [
        { id: 'choice-1', bom_item_id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', qty_per_good_fg_base: 2, reimbursement_unit_rate_base: 100 },
      ] },
    }]
    const rpc = vi.fn(async (name: string, _args?: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_bs_resolution_workspace_v1') return { data: partial, error: null }
      if (name === 'erp_save_bs_resolution_action_v1') return { data: { ok: true }, error: null }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity([
      'production.bs_rework.view', 'production.bs_rework.create',
      'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view',
    ])

    await renderPage()
    const completion = container.querySelector<HTMLElement>('.cbsr-completion-form')!
    const controls = completion.querySelectorAll<HTMLInputElement>('input')
    await act(async () => {
      setControlValue(controls[0]!, '2')
      setControlValue(controls[1]!, '1')
      setControlValue(controls[3]!, 'Tiga barang sudah kembali fisik')
    })
    const savePartial = [...completion.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Simpan partial'))!
    expect(savePartial.disabled).toBe(false)
    await act(async () => { savePartial.click() })
    await settle()

    const mutationCalls = rpc.mock.calls.filter(([name]) => name === 'erp_save_bs_resolution_action_v1')
    expect(mutationCalls).toHaveLength(1)
    expect(mutationCalls[0]?.[1]).toMatchObject({
      p_action: 'SAVE_REWORK', p_expected_version: 2,
      p_payload: {
        id: 'rework-1', action: 'SAVE', qty_good_returned: 2,
        qty_bs_returned: 1, return_fg_location_id: 'location-1',
      },
    })
  })

  it('renders view-only access without executable CP5 controls', async () => {
    const rpc = vi.fn(async (name: string, _args?: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_bs_resolution_workspace_v1') return { data: workspace(), error: null }
      throw new Error(`View-only page attempted mutation RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity(['production.bs_rework.view', 'master.pattern.view'], 'PRODUKSI_QC')

    await renderPage()
    const claimButton = [...container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Claim Laundry'))
    const manualButton = [...container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('BS legacy'))
    expect(claimButton?.disabled).toBe(true)
    expect(manualButton?.disabled).toBe(true)

    const holdTab = [...container.querySelectorAll<HTMLButtonElement>('.cbsr-route-tabs button')]
      .find((button) => button.textContent?.trim() === 'Hold')
    await act(async () => { holdTab!.click() })
    expect([...container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Simpan HOLD'))?.disabled).toBe(true)
    expect(rpc.mock.calls.some(([name]) => name === 'erp_save_bs_resolution_action_v1')).toBe(false)
  })

  it('reuses the same idempotency key when an unchanged action is retried after a transport error', async () => {
    let actionAttempts = 0
    const rpc = vi.fn(async (name: string, _args?: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_bs_resolution_workspace_v1') return { data: workspace(), error: null }
      if (name === 'erp_save_bs_resolution_action_v1') {
        actionAttempts += 1
        return actionAttempts === 1
          ? { data: null, error: { message: 'Transport terputus setelah request dikirim' } }
          : { data: { ok: true }, error: null }
      }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity([
      'production.bs_rework.view', 'production.bs_rework.create',
      'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view',
    ])

    await renderPage()
    const holdTab = [...container.querySelectorAll<HTMLButtonElement>('.cbsr-route-tabs button')]
      .find((button) => button.textContent?.trim() === 'Hold')!
    await act(async () => { holdTab.click() })
    const reason = container.querySelector<HTMLTextAreaElement>('.cbsr-route-form textarea')!
    await act(async () => { setControlValue(reason, 'Bukti fisik belum lengkap') })
    const saveHold = [...container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Simpan HOLD'))!

    await act(async () => { saveHold.click() })
    await settle()
    expect(container.textContent).toContain('Layanan UAT belum dapat dihubungi')
    await act(async () => { saveHold.click() })
    await settle()

    const actionCalls = rpc.mock.calls.filter(([name]) => name === 'erp_save_bs_resolution_action_v1')
    expect(actionCalls).toHaveLength(2)
    expect(actionCalls[0]?.[1]?.p_client_request_id).toBe(actionCalls[1]?.[1]?.p_client_request_id)
  })
})
