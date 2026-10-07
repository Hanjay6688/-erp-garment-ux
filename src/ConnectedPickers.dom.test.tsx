// @vitest-environment jsdom
// Searchable pickers on the backend-mode (Connected) pages: what a person picks
// in the popdown is exactly what the RPC receives, and every old rule (default
// choice, locks and their reasons, resets, empty states) still holds.

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedBsResolutionPage from './ConnectedBsResolutionPage'
import ConnectedCuttingPage from './ConnectedCuttingPage'
import ConnectedPickupPage from './ConnectedPickupPage'
import ConnectedWipStatusPage from './ConnectedWipStatusPage'
import {
  choosePickerOption, openPicker, pickerOptionLabels, pickerPanel, pickerTrigger, pickerValue, pressInPicker, typeInPicker,
} from './components/browsePickerDom.test.support'

const authState = vi.hoisted(() => ({ current: null as unknown }))
const mockedClient = vi.hoisted(() => ({ current: null as unknown }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => authState.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mockedClient.current }))

const runtime = {
  mode: 'UAT_AUTH_SIMULATION', authMode: 'UAT_SUPABASE', businessDataMode: 'PARTIAL_CONNECTED',
  businessRpcEnabled: true, accessControlMode: 'CONNECTED', patternMode: 'CONNECTED',
  cuttingMode: 'CONNECTED', distributionMode: 'CONNECTED', wipStatusMode: 'CONNECTED', bsResolutionMode: 'CONNECTED',
  projectRef: 'siimvrusnzxexizpyoib', supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_picker_dom_fixture',
} as const

function identity(permissions: string[]) {
  return {
    runtime,
    identity: {
      status: 'AUTHORIZED',
      profile: { id: 'app-user-1', authUserId: 'auth-user-1', fullName: 'Owner', roleId: 'role-1', role: 'OWNER', roleName: 'OWNER', isActive: true, rowVersion: 1, roleRowVersion: 1 },
      permissions,
      externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
    },
    signingOut: false, signOutError: null, signIn: vi.fn(), signOut: vi.fn(), retryIdentity: vi.fn(),
  }
}

const patterns = [
  { id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular', sort_order: 1, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 1 },
  { id: 'pattern-2', code: 'SLIM', revision: 'R1', name: 'Slim', sort_order: 2, is_active: true, row_version: 1, updated_at: '2026-09-03T07:00:00Z', updated_by: null, usage_count: 0 },
]

function setControlValue(control: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string) {
  const prototype = control instanceof HTMLSelectElement ? HTMLSelectElement.prototype
    : control instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(control, value)
  control.dispatchEvent(new Event(control instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true }))
}
const settle = async (delay = 0) => { await act(async () => { await new Promise((resolve) => globalThis.setTimeout(resolve, delay)) }) }
const buttonWith = (text: string, scope: ParentNode = document) => [...scope.querySelectorAll<HTMLButtonElement>('button')]
  .find((button) => button.textContent?.includes(text))!
const rpcArgs = (rpc: ReturnType<typeof vi.fn>, name: string) => rpc.mock.calls.filter(([called]) => called === name).map(([, args]) => args as Record<string, unknown>)

let container: HTMLDivElement
let root: Root
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  globalThis.localStorage.clear()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  globalThis.localStorage.clear()
  vi.restoreAllMocks()
})

// ── CP5 BS Resolution ──────────────────────────────────────────────────────
const bomItem = { id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', base_uom_code: 'PCS', qty_per_good_fg_base: 2, reimbursement_rate: 100, reimbursement_uom_code: 'PCS', default_selected: true, default_selection_basis: 'UNPAID_BASELINE', default_reason: 'PRE_FG_UNPAID_BASELINE', already_entitled_good_qty_pcs: 0, already_cash_settled_good_qty_pcs: 0, remaining_unentitled_good_qty_pcs: 10 }
function bsRow(id: string, extra: Record<string, unknown>) {
  return {
    case_key: `BS:${id}`, kind: 'BS', id, number: id.toUpperCase(), status: 'OPEN', row_version: 4,
    qty_pcs: 10, resolved_qty: 0, active_rework_qty: 0, available_qty: 10, opened_at: '2026-09-03T08:00:00Z',
    po_id: 'po-1', po_number: 'PO-1', model_name: 'Model A', cutting_group_id: 'group-1', group_number: 'POT-1',
    patterns: [{ id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular' }],
    product_id: 'product-1', sku: 'SKU-1', product_name: 'Produk 1', responsible_contractor_id: 'contractor-1',
    contractor_name: 'Mandor A', responsible_vendor_id: null, vendor_name: null, detected_stage: 'QC', cause_source: 'SEWING',
    untracked_type: null, claim_type: null, compensation_amount: 0, laundry_delivery_id: null, laundry_receipt_line_id: null,
    legacy_reference: null, notes: null, next_action: 'START_REWORK_OR_DISPOSITION', is_closed: false,
    accessory_bom: { state: 'AVAILABLE', bom_version_id: 'bom-1', default_policy: 'SERVER_ENTITLEMENT_V2619B', available_qty_pcs: 10, items: [bomItem] },
    components: [{ id: 'component-1', work_component_id: 'work-1', code: 'JAHIT', name: 'Jahit', category: 'LABOR', completed_before_bs_qty: 0, lifetime_newly_completed_qty: 0, lifetime_paid_qty: 0, remaining_new_work_qty_pcs: 10, default_selected: true, default_selection_basis: 'UNPAID_COMPONENT_ENTITLEMENT', notes: null }],
    resolutions: [], rework_orders: [], hold_events: [], ...extra,
  }
}
function bsWorkspace(rows = [bsRow('bs-1', {})]) {
  return {
    filter: 'ACTIVE', kind: 'ALL', pattern_id: null, query: null, limit: 50, offset: 0, total: rows.length,
    lookups: {
      contractors: [{ id: 'contractor-1', code: 'M-01', name: 'Mandor A' }, { id: 'contractor-2', code: 'M-02', name: 'Mandor B' }],
      vendors: [{ id: 'vendor-1', code: 'L-01', name: 'Laundry A' }, { id: 'vendor-2', code: 'L-02', name: 'Laundry B' }],
      fg_locations: [{ id: 'location-1', code: 'FG-01', name: 'Gudang FG' }],
      work_components: [{ id: 'work-1', code: 'JAHIT', name: 'Jahit' }],
      products: [{ id: 'product-1', sku: 'SKU-1', name: 'Produk 1' }, { id: 'product-2', sku: 'SKU-2', name: 'Produk Dua' }],
      laundry_sources: [
        { id: 'delivery-1', number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T08:00:00Z', qty_sent_pcs: 10, qty_claimable_pcs: 7 },
        { id: 'delivery-2', number: 'LDR-2', vendor_id: 'vendor-2', vendor_name: 'Laundry B', po_number: 'PO-2', physical_at: '2026-09-03T08:30:00Z', qty_sent_pcs: 8, qty_claimable_pcs: 5 },
        { id: 'delivery-3', number: 'LDR-3', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-3', physical_at: '2026-09-03T09:00:00Z', qty_sent_pcs: 4, qty_claimable_pcs: 0 },
      ],
      laundry_receipt_sources: [
        { id: 'receipt-line-1', receipt_id: 'receipt-1', number: 'LRC-1', delivery_id: 'delivery-1', delivery_number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T09:00:00Z', qty_bs_laundry: 3, qty_claimable_pcs: 2 },
        { id: 'receipt-line-2', receipt_id: 'receipt-2', number: 'LRC-2', delivery_id: 'delivery-2', delivery_number: 'LDR-2', vendor_id: 'vendor-2', vendor_name: 'Laundry B', po_number: 'PO-2', physical_at: '2026-09-03T10:00:00Z', qty_bs_laundry: 4, qty_claimable_pcs: 4 },
      ],
      settled_claims: [
        { id: 'claim-1', number: 'CLM-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', delivery_id: 'delivery-1', receipt_line_id: null, qty_claimed: 4, compensation_amount: 120000, available_qty: 4, available_amount: 120000 },
        { id: 'claim-2', number: 'CLM-2', vendor_id: 'vendor-2', vendor_name: 'Laundry B', delivery_id: 'delivery-2', receipt_line_id: null, qty_claimed: 2, compensation_amount: 50000, available_qty: 2, available_amount: 50000 },
      ],
    },
    rows,
  }
}
const bsPermissions = ['production.bs_rework.view', 'production.bs_rework.create', 'production.bs_rework.post', 'production.bs_rework.reverse', 'master.pattern.view']
function bsClient(rows?: ReturnType<typeof bsRow>[]) {
  const rpc = vi.fn(async (name: string, args?: Record<string, unknown>) => {
    if (name === 'erp_list_patterns_v1') {
      const query = String(args?.p_query ?? '').toLowerCase()
      return { data: patterns.filter((row) => !query || `${row.code} ${row.revision} ${row.name}`.toLowerCase().includes(query)), error: null }
    }
    if (name === 'erp_get_bs_resolution_workspace_v1') return { data: bsWorkspace(rows), error: null }
    if (name === 'erp_save_bs_resolution_action_v1') return { data: { ok: true }, error: null }
    throw new Error(`Unexpected RPC ${name}`)
  })
  mockedClient.current = { rpc }
  authState.current = identity(bsPermissions)
  return rpc
}
async function renderBs() {
  await act(async () => { root.render(<ConnectedBsResolutionPage/>) })
  await settle(220)
}
const lastAction = (rpc: ReturnType<typeof vi.fn>) => rpcArgs(rpc, 'erp_save_bs_resolution_action_v1').at(-1)

describe('CP5 BS Resolution pickers', () => {
  it('legacy BS product: search → pick sends that product; "Belum dapat diidentifikasi" stays the default and sends none', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { buttonWith('BS legacy').click() })
    const modal = document.querySelector<HTMLElement>('.cbsr-modal-layer')!
    const product = pickerTrigger('PRODUK · OPSIONAL', modal)
    expect(pickerValue(product)).toBe('Belum dapat diidentifikasi')

    await openPicker(product)
    await typeInPicker('dua')
    expect(pickerOptionLabels()).toEqual(['Belum dapat diidentifikasi', 'SKU-2'])
    await pressInPicker('Enter')
    expect(pickerValue(product)).toBe('SKU-2')

    const inputs = modal.querySelectorAll<HTMLInputElement>('input')
    await act(async () => {
      setControlValue(inputs[1]!, 'Nota lama 12')
      setControlValue(inputs[2]!, '3')
      setControlValue(inputs[4]!, 'Ditemukan saat opname')
    })
    await act(async () => { buttonWith('Simpan kasus authoritative', modal).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'CREATE_MANUAL_BS', p_payload: { product_id: 'product-2', qty_pcs: 3, legacy_reference: 'Nota lama 12' } })
  })

  it('legacy BS product: picking "Belum dapat diidentifikasi" back clears the product', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { buttonWith('BS legacy').click() })
    const modal = document.querySelector<HTMLElement>('.cbsr-modal-layer')!
    const product = pickerTrigger('PRODUK · OPSIONAL', modal)
    await choosePickerOption(product, 'SKU-1', 'sku-1')
    await choosePickerOption(product, 'Belum dapat diidentifikasi', 'sku')
    const inputs = modal.querySelectorAll<HTMLInputElement>('input')
    await act(async () => {
      setControlValue(inputs[1]!, 'Buku BS lama')
      setControlValue(inputs[2]!, '2')
      setControlValue(inputs[4]!, 'Tanpa label SKU')
    })
    await act(async () => { buttonWith('Simpan kasus authoritative', modal).click() })
    await settle()
    expect(lastAction(rpc)?.p_action).toBe('CREATE_MANUAL_BS')
    expect((lastAction(rpc)?.p_payload as Record<string, unknown>).product_id).toBeUndefined()
  })

  it('Laundry claim source: default and grouping as before; search → pick sends that surat kirim; DAMAGE picks a receipt line', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { buttonWith('Claim Laundry').click() })
    const modal = document.querySelector<HTMLElement>('.cbsr-modal-layer')!
    const source = pickerTrigger('SURAT KIRIM', modal)
    // old rule: the first surat kirim that still has claimable pcs is preselected; LDR-3 (0 pcs) is not offered
    expect(pickerValue(source)).toBe('LDR-1')
    await openPicker(source)
    expect(pickerOptionLabels()).toEqual(['LDR-1', 'LDR-2'])
    expect([...pickerPanel()!.querySelectorAll('.browse-picker-group-name')].map((node) => node.textContent)).toEqual(['Laundry A', 'Laundry B'])
    await pressInPicker('Escape')

    const [number, quantity] = [...modal.querySelectorAll<HTMLInputElement>('input')]
    await act(async () => { setControlValue(quantity!, '6') })
    await choosePickerOption(source, 'LDR-2', 'laundry b')
    // old rule: changing the source clears the quantity (max follows the new source)
    expect(quantity!.value).toBe('')
    await act(async () => {
      setControlValue(number!, 'CLM-9')
      setControlValue(quantity!, '9')
      setControlValue(modal.querySelector('textarea')!, 'Lima pcs tertahan di Laundry B')
    })
    expect(quantity!.value).toBe('5')
    await act(async () => { buttonWith('Simpan claim', modal).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'SAVE_CLAIM', p_payload: { delivery_id: 'delivery-2', vendor_id: 'vendor-2', receipt_line_id: null, qty_claimed: 5, claim_type: 'STUCK' } })
  })

  it('Laundry claim DAMAGE: the picker switches to receipt lines and sends the picked line', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { buttonWith('Claim Laundry').click() })
    const modal = document.querySelector<HTMLElement>('.cbsr-modal-layer')!
    await act(async () => { setControlValue(modal.querySelector('select')!, 'DAMAGE') })
    const source = pickerTrigger('BARIS PENERIMAAN BS', modal)
    expect(pickerValue(source)).toBe('LRC-1')
    await choosePickerOption(source, 'LRC-2', 'LRC-2')
    const [number, quantity] = [...modal.querySelectorAll<HTMLInputElement>('input')]
    await act(async () => {
      setControlValue(number!, 'CLM-D')
      setControlValue(quantity!, '4')
      setControlValue(modal.querySelector('textarea')!, 'Rusak saat dicuci')
    })
    await act(async () => { buttonWith('Simpan claim', modal).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'SAVE_CLAIM', p_payload: { receipt_line_id: 'receipt-line-2', delivery_id: 'delivery-2', vendor_id: 'vendor-2', claim_type: 'DAMAGE' } })
  })

  it('classification: Mandor picked with the keyboard; Escape keeps the current one', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { container.querySelector<HTMLElement>('.cbsr-fold summary')!.click() })
    const fold = container.querySelector<HTMLElement>('.cbsr-fold-body')!
    const mandor = pickerTrigger('MANDOR TANGGUNG JAWAB', fold)
    expect(pickerValue(mandor)).toBe('Mandor A')
    await openPicker(mandor)
    await pressInPicker('ArrowDown')
    await pressInPicker('Escape')
    expect(pickerValue(mandor)).toBe('Mandor A')
    await openPicker(mandor)
    await typeInPicker('M-02')
    await pressInPicker('Enter')
    expect(pickerValue(mandor)).toBe('Mandor B')
    await act(async () => { setControlValue(fold.querySelector<HTMLInputElement>('input[placeholder="Dasar hasil pemeriksaan fisik"]')!, 'Cek fisik ulang') })
    await act(async () => { buttonWith('Simpan klasifikasi', fold).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'CLASSIFY_BS', p_payload: { cause_source: 'SEWING', responsible_contractor_id: 'contractor-2', responsible_vendor_id: null } })
  })

  it('classification: Laundry responsible picked from the vendor list', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { container.querySelector<HTMLElement>('.cbsr-fold summary')!.click() })
    const fold = container.querySelector<HTMLElement>('.cbsr-fold-body')!
    await act(async () => { setControlValue(fold.querySelector('select')!, 'LAUNDRY') })
    const vendor = pickerTrigger('VENDOR TANGGUNG JAWAB', fold)
    expect(pickerValue(vendor)).toBe('Pilih Laundry…')
    // old rule: no Laundry chosen → cannot save
    await act(async () => { setControlValue(fold.querySelector<HTMLInputElement>('input[placeholder="Dasar hasil pemeriksaan fisik"]')!, 'Noda dari pencucian') })
    expect(buttonWith('Simpan klasifikasi', fold).disabled).toBe(true)
    await choosePickerOption(vendor, 'Laundry B', 'L-02')
    await act(async () => { buttonWith('Simpan klasifikasi', fold).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'CLASSIFY_BS', p_payload: { cause_source: 'LAUNDRY', responsible_contractor_id: null, responsible_vendor_id: 'vendor-2' } })
  })

  it('rewash: the Laundry vendor picked is the order vendor; nothing is preselected', async () => {
    const rpc = bsClient()
    await renderBs()
    await act(async () => { buttonWith('Rewash', container.querySelector('.cbsr-route-tabs')!).click() })
    const form = container.querySelector<HTMLElement>('.cbsr-route-form')!
    const vendor = pickerTrigger('VENDOR REWASH', form)
    expect(pickerValue(vendor)).toBe('Pilih…')
    await choosePickerOption(vendor, 'Laundry A', 'laundry a')
    await act(async () => {
      setControlValue(form.querySelector<HTMLInputElement>('input[placeholder="RWL-BS-1"]')!, 'RWL-1')
      setControlValue(form.querySelector('textarea')!, 'Cuci ulang noda')
    })
    await act(async () => { buttonWith('Buat order rewash', form).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'SAVE_REWORK', p_payload: { destination_type: 'LAUNDRY', vendor_id: 'vendor-1', contractor_id: null } })
  })

  it('compensation: only settled claims of the responsible Laundry are offered; the picked claim is the source', async () => {
    const rpc = bsClient([bsRow('bs-2', { cause_source: 'LAUNDRY', responsible_contractor_id: null, contractor_name: null, responsible_vendor_id: 'vendor-1', vendor_name: 'Laundry A', detected_stage: 'LAUNDRY' })])
    await renderBs()
    await act(async () => { buttonWith('Kompensasi', container.querySelector('.cbsr-route-tabs')!).click() })
    const form = container.querySelector<HTMLElement>('.cbsr-route-form')!
    const claim = pickerTrigger('CLAIM SETTLED · SALDO TERSEDIA', form)
    expect(pickerValue(claim)).toBe('Pilih claim…')
    await openPicker(claim)
    expect(pickerOptionLabels()).toEqual(['CLM-1'])
    expect(pickerPanel()!.textContent).toContain('4 pcs / Rp120.000')
    await pressInPicker('Enter')
    const inputs = form.querySelectorAll<HTMLInputElement>('input[inputmode="numeric"]')
    await act(async () => {
      setControlValue(inputs[0]!, '3')
      setControlValue(inputs[1]!, '90000')
      setControlValue(form.querySelector('textarea')!, 'Kompensasi dari claim')
    })
    await act(async () => { buttonWith('Post disposition', form).click() })
    await settle()
    expect(lastAction(rpc)).toMatchObject({ p_action: 'DISPOSE_BS', p_payload: { resolution_type: 'CASH_COMPENSATION', source_laundry_claim_id: 'claim-1', qty_pcs: 3, compensation_amount: 90000 } })
  })

  it('compensation: the empty state still explains what to do when no claim has a balance', async () => {
    bsClient([bsRow('bs-3', { cause_source: 'SEWING' })])
    await renderBs()
    await act(async () => { buttonWith('Kompensasi', container.querySelector('.cbsr-route-tabs')!).click() })
    const form = container.querySelector<HTMLElement>('.cbsr-route-form')!
    expect(form.textContent).toContain('Klasifikasikan vendor penanggung jawab dan settle claim')
    await openPicker(pickerTrigger('CLAIM SETTLED · SALDO TERSEDIA', form))
    expect(pickerPanel()!.textContent).toContain('Belum ada claim settled bersaldo')
  })

  it('Pola filter: typing searches Master Pola on the server; the picked Pola reloads the workspace', async () => {
    const rpc = bsClient()
    await renderBs()
    const filter = pickerTrigger('FILTER POLA CP5', container)
    expect(pickerValue(filter)).toBe('Semua Pola')
    await openPicker(filter)
    await typeInPicker('slim')
    await settle(220)
    expect(rpcArgs(rpc, 'erp_list_patterns_v1').at(-1)).toMatchObject({ p_query: 'slim', p_status: 'ALL' })
    expect(pickerOptionLabels()).toEqual(['Semua Pola', 'SLIM · R1'])
    await pressInPicker('Enter')
    await settle()
    expect(rpcArgs(rpc, 'erp_get_bs_resolution_workspace_v1').at(-1)).toMatchObject({ p_pattern_id: 'pattern-2' })
    // picking the same Pola again is not a new filter (a native select fired nothing either)
    const loads = rpcArgs(rpc, 'erp_get_bs_resolution_workspace_v1').length
    await settle(220)
    await choosePickerOption(pickerTrigger('FILTER POLA CP5', container), 'SLIM · R1')
    await settle()
    expect(rpcArgs(rpc, 'erp_get_bs_resolution_workspace_v1')).toHaveLength(loads)
  })
})

// ── Cutting (Buat Potongan) ────────────────────────────────────────────────
const cuttingOrders = [
  { id: 'po-1', po_number: 'PO-001', model_id: 'model-1', model_code: 'M1', model_name: 'Kulot', status: 'RELEASED', current_stage: 'CUTTING', contractor_id: null, contractor_name: null },
  { id: 'po-2', po_number: 'PO-002', model_id: 'model-2', model_code: 'M2', model_name: 'Jumbo', status: 'RELEASED', current_stage: 'CUTTING', contractor_id: 'mandor-2', contractor_name: 'Mandor B' },
]
function cuttingWorkspace(args: Record<string, unknown>, drafts: unknown[] = []) {
  return {
    location_id: args.p_location_id ?? null, roll_query: null, limit: 100, offset: 0, roll_total: args.p_location_id ? 1 : 0,
    orders: cuttingOrders,
    sizes: [
      { id: 'size-s', code: 'S', sort_order: 1, model_ids: ['model-1'] },
      { id: 'size-30', code: '30', sort_order: 2, model_ids: ['model-2'] },
      { id: 'size-31', code: '31', sort_order: 3, model_ids: ['model-2'] },
    ],
    locations: [{ id: 'loc-1', code: 'GB-01', name: 'Gudang Bahan' }],
    contractors: [],
    drafts,
    rolls: args.p_location_id ? [{ id: 'roll-1', roll_number: 'R-1', material_id: 'mat-1', material_sku: 'DNM', material_name: 'Denim', unit_code: 'YD', supplier_id: null, supplier_code: null, supplier_name: null, original_qty: 50, available_qty: 50, status: 'AVAILABLE', received_at: null }] : [],
  }
}
const cuttingDraft = {
  cutting_group_id: 'group-1', group_number: 'POT-1', row_version: 3, po_id: 'po-2', po_number: 'PO-002', model_code: 'M2', model_name: 'Jumbo',
  cut_at: '2026-09-03T08:00:00Z', source_location_id: 'loc-1', notes: null, pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R2', pattern_name: 'Regular', pattern_is_active: true,
  editable: true, size_slots: [{ slot_no: 1, size_id: 'size-30', size_code: '30', drawing_no: 1, label_override: null }], rolls: [],
}

describe('Connected Buat Potongan PO picker', () => {
  it('keeps the first PO preloaded, picks another by search, and saves that PO with its model sizes', async () => {
    const rpc = vi.fn(async (name: string, args?: Record<string, unknown>) => {
      if (name === 'erp_get_cutting_workspace_v1') return { data: cuttingWorkspace(args ?? {}), error: null }
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_save_cutting_group_before_sewing_v2') return { data: null, error: { message: 'stop after capture' } }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity(['production.cutting.view', 'production.cutting.create', 'production.cutting.edit_draft', 'production.cutting.post'])
    await act(async () => { root.render(<ConnectedCuttingPage/>) })
    await settle(220)
    const po = pickerTrigger('Production Order', container)
    expect(pickerValue(po)).toBe('PO-001')
    expect(po.disabled).toBe(false)

    await openPicker(po)
    expect([...pickerPanel()!.querySelectorAll('.browse-picker-group-name')].map((node) => node.textContent)).toEqual(['M1 · Kulot', 'M2 · Jumbo'])
    await typeInPicker('jumbo')
    expect(pickerOptionLabels()).toEqual(['PO-002'])
    await pressInPicker('Enter')
    expect(pickerValue(po)).toBe('PO-002')
    expect([...container.querySelectorAll('.ccut-size-list button')].map((button) => button.textContent)).toEqual(['30', '31'])

    await act(async () => { [...container.querySelectorAll<HTMLButtonElement>('.cutting-pattern-results button')][0]!.click() })
    await act(async () => { container.querySelector<HTMLButtonElement>('.ccut-roll-catalog button')!.click() })
    const [consumed, firstYield] = [...container.querySelectorAll<HTMLInputElement>('.ccut-table-wrap input')]
    await act(async () => { setControlValue(consumed!, '9'); setControlValue(firstYield!, '6') })
    const saveDraft = buttonWith('Simpan draft', container.querySelector('.ccut-actions')!)
    expect(saveDraft.disabled).toBe(false)
    await act(async () => { saveDraft.click() })
    await settle()
    expect(rpcArgs(rpc, 'erp_save_cutting_group_before_sewing_v2').at(-1)).toMatchObject({
      p_payload: { action: 'SAVE_DRAFT', po_id: 'po-2', size_slots: [{ slot_no: 1, size_id: 'size-30' }, { slot_no: 2, size_id: 'size-31' }] },
    })
  })

  it('locks the PO, with the reason, once a saved draft is resumed', async () => {
    const rpc = vi.fn(async (name: string, args?: Record<string, unknown>) => {
      if (name === 'erp_get_cutting_workspace_v1') return { data: cuttingWorkspace(args ?? {}, [cuttingDraft]), error: null }
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity(['production.cutting.view', 'production.cutting.create', 'production.cutting.edit_draft'])
    await act(async () => { root.render(<ConnectedCuttingPage/>) })
    await settle(220)
    await act(async () => { buttonWith('POT-1', container.querySelector('.ccut-drafts')!).click() })
    const po = pickerTrigger('Production Order', container)
    expect(pickerValue(po)).toBe('PO-002')
    expect(po.disabled).toBe(true)
    expect(container.querySelector('.ccut-picker-field > small')?.textContent).toBe('PO dikunci pada draft yang sudah tersimpan.')
    await act(async () => { po.click() })
    expect(pickerPanel()).toBeNull()
  })
})

// ── Pickup (Bagi Potongan) ─────────────────────────────────────────────────
const yieldRow = { yield_id: 'yield-1', size_slot_id: 'slot-1', slot_no: 1, size_id: 'size-30', size_code: '30', drawing_no: 1, label: null, qty_pcs: 6 }
function pickupRow(id: string, extra: Record<string, unknown> = {}) {
  return {
    cutting_group_id: id, group_number: id.toUpperCase(), row_version: 2, po_id: 'po-1', po_number: 'PO-001', model_code: 'M1', model_name: 'Kulot',
    assigned_contractor_id: null, assigned_contractor_name: null, cut_at: '2026-09-03T08:00:00Z', status: 'POSTED', picked_up_at: null, executor_name: null,
    source_location_id: 'loc-1', source_location_code: 'GB-01', pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R2', pattern_name: 'Regular',
    total_qty_issued: 10, total_pieces: 6, pickup_eligible: true, pickup: null,
    rolls: [{ cutting_group_roll_id: `${id}-roll`, roll_id: 'roll-1', roll_number: 'R-1', material_id: 'mat-1', material_sku: 'DNM', material_name: 'Denim', unit_code: 'YD', supplier_name: null, original_qty: 50, qty_issued: 10, qty_consumed: 9, qty_reported_remaining: 1, yields: [yieldRow] }],
    ...extra,
  }
}
const pickupContractors = [{ id: 'mandor-1', code: 'M-01', name: 'Mandor A' }, { id: 'mandor-2', code: 'M-02', name: 'Mandor B' }, { id: 'mandor-3', code: 'M-03', name: 'Mandor C' }]
function pickupClient(rows: ReturnType<typeof pickupRow>[]) {
  const rpc = vi.fn(async (name: string) => {
    if (name === 'erp_get_cutting_pickup_queue_v1') return { data: { filter: 'WAITING', pattern_id: null, query: null, limit: 100, offset: 0, total: rows.length, contractors: pickupContractors, rows }, error: null }
    if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
    if (name === 'erp_save_cutting_pickup_v1') return { data: null, error: { message: 'stop after capture' } }
    throw new Error(`Unexpected RPC ${name}`)
  })
  mockedClient.current = { rpc }
  authState.current = identity(['production.distribution.view', 'production.distribution.create', 'production.distribution.edit_draft', 'production.distribution.post'])
  return rpc
}

describe('Connected Bagi Potongan Mandor picker', () => {
  it('keeps the first active Mandor preselected as before; the picked Mandor is the pickup contractor', async () => {
    const rpc = pickupClient([pickupRow('pot-1')])
    await act(async () => { root.render(<ConnectedPickupPage/>) })
    await settle(220)
    const mandor = pickerTrigger('Mandor', container.querySelector('.cpick-setup')!)
    expect(pickerValue(mandor)).toBe('Mandor A')
    await choosePickerOption(mandor, 'Mandor C', 'm-03')
    await act(async () => { buttonWith('Simpan draft', container).click() })
    await settle()
    expect(rpcArgs(rpc, 'erp_save_cutting_pickup_v1').at(-1)).toMatchObject({ p_payload: { action: 'SAVE_DRAFT', cutting_group_id: 'pot-1', contractor_id: 'mandor-3' } })
  })

  it('a Mandor locked by the Production Order stays locked, with its reason', async () => {
    pickupClient([pickupRow('pot-2', { assigned_contractor_id: 'mandor-2', assigned_contractor_name: 'Mandor B' })])
    await act(async () => { root.render(<ConnectedPickupPage/>) })
    await settle(220)
    const mandor = pickerTrigger('Mandor', container.querySelector('.cpick-setup')!)
    expect(pickerValue(mandor)).toBe('Mandor B')
    expect(mandor.disabled).toBe(true)
    expect(container.querySelector('.cpick-mandor > small')?.textContent).toBe('Mandor dikunci mengikuti penugasan Production Order.')
  })

  it('an inactive Mandor on the PO is shown as TIDAK AKTIF, cannot be picked, and blocks saving with the alert', async () => {
    pickupClient([pickupRow('pot-3', { assigned_contractor_id: 'mandor-9', assigned_contractor_name: 'Mandor Lama' })])
    await act(async () => { root.render(<ConnectedPickupPage/>) })
    await settle(220)
    const mandor = pickerTrigger('Mandor', container.querySelector('.cpick-setup')!)
    expect(pickerValue(mandor)).toBe('Mandor Lama')
    expect(mandor.querySelector('.browse-picker-meta')?.textContent).toBe('TIDAK AKTIF')
    expect(container.querySelector('.cpick-mandor > small[role="alert"]')?.textContent).toContain('Mandor yang dikunci di Production Order sudah tidak aktif')
    expect(buttonWith('Simpan draft', container).disabled).toBe(true)
  })
})

// ── WIP & Sewing status ────────────────────────────────────────────────────
describe('Connected WIP Pola filter', () => {
  it('the picked Pola reloads WIP with that pattern id; "Semua Pola" clears it', async () => {
    const rpc = vi.fn(async (name: string, args?: Record<string, unknown>) => {
      if (name === 'erp_list_patterns_v1') return { data: patterns, error: null }
      if (name === 'erp_get_wip_control_v1') return { data: { filter: 'ACTIVE', sort: 'PATTERN', pattern_id: args?.p_pattern_id ?? null, rows: [] }, error: null }
      throw new Error(`Unexpected RPC ${name}`)
    })
    mockedClient.current = { rpc }
    authState.current = identity(['production.wip.view'])
    await act(async () => { root.render(<ConnectedWipStatusPage/>) })
    await settle(220)
    const filter = pickerTrigger('FILTER POLA', container)
    expect(filter.closest('.connected-pattern-filter')?.classList.contains('tone-light')).toBe(true)
    await choosePickerOption(filter, 'REG · R2')
    await settle()
    expect(rpcArgs(rpc, 'erp_get_wip_control_v1').at(-1)).toMatchObject({ p_pattern_id: 'pattern-1' })
    await choosePickerOption(filter, 'Semua Pola')
    await settle()
    expect(rpcArgs(rpc, 'erp_get_wip_control_v1').at(-1)).toMatchObject({ p_pattern_id: null })
  })
})
