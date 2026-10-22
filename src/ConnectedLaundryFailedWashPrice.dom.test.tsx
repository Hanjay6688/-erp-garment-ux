// @vitest-environment jsdom
// OW-08b (LAU-DEC04): a paid failed wash recorded while the vendor price is unknown, and its price set later on Harga & tagihan.
// RPC stand-ins exercise the real forms and recovery hooks; the server rules themselves are proven by the Native11 cases.
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedLaundryPage from './ConnectedLaundryPage'
import { LAU_POLICY_KEYS } from './laundryBd'
import { laundryQcInputFixture } from '../tests/fixtures/laundryQcInput'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'

const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const receipt = (over: Record<string, unknown>) => ({ id: id(60), number: 'LFW-001', status: 'POSTED', row_version: 1, physical_at: '2026-09-04T03:00:00Z',
  actual_cost: null, actual_rate: null, cost_status: 'PENDING', event_kind: 'FAILED_WASH_ATTEMPT', failed_wash_attempt_id: id(61),
  custody_outcome: 'RETRY_AT_VENDOR', attempted_qty_pcs: 2, process_name: 'Bleach', reversible: true, reversal_blocker: null, ...over })
// The fixture vendor has a rate for WASH only; BLEACH has none, so only BLEACH may be recorded with an unknown price.
function laundry(receipts: unknown[] = []) {
  const w = laundryQcInputFixture('LAUNDRY')
  w.lookups.wash_processes.push({ id: id(40), code: 'BLEACH', name: 'Bleach' })
  ;(w.deliveries as unknown[]).push({ delivery_id: id(20), delivery_number: 'LDR-001', row_version: 3, status: 'SENT',
    physical_at: '2026-09-02T00:00:00Z', target_dyeing_color: 'Hitam', special_instruction: null,
    po_id: id(14), po_number: 'PO-001', model_id: id(7), cutting_group_id: id(12), group_number: 'P-001',
    cutting_group_row_version: 4, model_code: 'MOD-A', model_name: 'Model A', contractor_name: 'Mandor A',
    vendor_id: id(1), vendor_code: 'LDR-A', vendor_name: 'Laundry A', wash_process_id: id(2), process_code: 'WASH',
    process_name: 'Cuci', delivery_line_id: id(21), qty_sent_pcs: 2, estimated_rate_snapshot: 1200, estimated_cost: 2400,
    distribution_batch_id: id(10), batch_no: 1, returned_qty_pcs: 0, physical_outstanding_qty_pcs: 2,
    returned_unprocessed_qty_pcs: 0, active_claim_qty_pcs: 0, reversible: true, reversal_blocker: null,
    sizes: [{ delivery_batch_size_line_id: id(22), size_id: id(9), size_code: '31', sort_order: 1,
      qty_sent_pcs: 2, good_returned_qty_pcs: 0, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 2 }], receipts })
  return w
}
const waitingRow = { attempt_id: id(61), receipt_id: id(60), receipt_number: 'LFW-001', attempt_status: 'POSTED', delivery_number: 'LDR-001', po_number: 'PO-001',
  vendor_id: id(1), vendor_code: 'LDR-A', process_name: 'Bleach', custody_outcome: 'RETRY_AT_VENDOR', qty: 2, physical_local: '2026-09-04T10:00:00',
  recorded_reason: 'Vendor menagih attempt, nota belum datang', recorded_by: 'Admin', recorded_local: '2026-09-04T10:05:00', price_status: 'UNKNOWN',
  rate: null, amount: null, price_reason: null, priced_by: null, priced_local: null }
const pricedRow = { ...waitingRow, attempt_id: id(63), receipt_id: id(62), receipt_number: 'LFW-000', price_status: 'KNOWN', rate: '1500.00', amount: '3000.00',
  price_reason: 'Nota vendor datang', priced_by: 'Owner', priced_local: '2026-09-05T09:00:00' }
const prices = (over: Record<string, unknown> = {}) => ({
  pagination: { as_of: '2026-10-06T00:00:00Z', invoice_next: null, receipt_next: null },
  money_visible: true, can_manage_master: true, can_set_price: true, is_owner: true,
  policies: LAU_POLICY_KEYS.map(key => ({ key, status: 'PENDING_POLICY_VALUE', value: null, version: '1', set_at: '2026-10-06T07:00:00', reason: 'Synthetic pending policy' })),
  vendors: [{ id: id(1), code: 'LDR-A', name: 'Laundry A', pricing_mode: 'RATE', pricing_unit: 'PCS', minimum_charge: null, terms_version: '1', bd_priced: false }],
  processes: [{ id: id(2), code: 'WASH', name: 'Cuci' }], components: [], packages: [], process_rates: [], scoped_rates: [], priced_deliveries: [],
  opening_uninvoiced: [], invoices: [], billable_receipts: null, accounts: [], payables: null, pending_cost: { goods: [], sales: [] },
  failed_wash_prices: [waitingRow, pricedRow], ...over })
const ok = (data: unknown) => ({ data, error: null })
let root: Root, box: HTMLDivElement, qc: ReturnType<typeof laundry>, bd: ReturnType<typeof prices>
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.rpc.mockReset(); qc = laundry(); bd = prices()
  mock.auth = { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED',
    profile: { id: id(100), authUserId: id(101), rowVersion: 1, roleRowVersion: 1, role: 'OWNER', roleName: 'Owner', isActive: true },
    permissions: ['production.laundry.view', 'production.laundry.create', 'production.laundry.post', 'production.laundry.reverse'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: vi.fn(async (name, _options, run) => run({ name, mode: 'exclusive' })) } })
  mock.rpc.mockImplementation((name, args) => {
    if (name === 'erp_get_laundry_qc_workspace_v1') return Promise.resolve(ok(qc))
    if (name === 'erp_get_laundry_bd_workspace_v1') return Promise.resolve(ok(bd))
    if (name === 'erp_save_laundry_qc_action_v1') return Promise.resolve(ok({ contract_version: 'CP6_V2620', committed: true, action: args.p_action, client_request_id: args.p_client_request_id }))
    if (name === 'erp_save_laundry_bd_action_v1') return Promise.resolve(ok({ action: args.p_action, request_id: args.p_client_request_id, status: 'SAVED' }))
    throw Error('Unexpected RPC: ' + name)
  })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const settle = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
const buttons = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].filter(e => e.textContent?.trim() === name)
async function click(name: string) { expect(buttons(name)).toHaveLength(1); await act(async () => buttons(name)[0].click()); await settle() }
const field = (label: string) => box.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${label}"]`)
async function change(label: string, value: string) {
  const e = field(label)!; expect(e).not.toBeNull()
  await act(async () => { const proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) })
  await settle()
}
async function tick(e: HTMLInputElement) { await act(async () => e.click()); await settle() }
const post = () => box.querySelector<HTMLButtonElement>('[aria-label="Post jasa gagal cuci atomic"]')!
const writes = (name: string) => mock.rpc.mock.calls.filter(([n]) => n === name)
async function failedWash(process: number) {
  await act(async () => root.render(<ConnectedLaundryPage/>)); await settle(); await click('Cuci gagal berbayar')
  await change('SURAT KIRIM GAGAL CUCI', id(20)); await change('PROSES GAGAL CUCI', id(process)); await change('POSISI FISIK GAGAL CUCI', 'RETRY_AT_VENDOR')
  await change('WAKTU GAGAL CUCI', '2026-09-04T10:00'); await change('Qty gagal cuci size 31', '2'); await change('ALASAN TAGIHAN GAGAL CUCI', 'Vendor menagih attempt, nota belum datang')
}
const confirm = () => [...box.querySelectorAll<HTMLInputElement>('.clq-confirm input')].find(e => e.getAttribute('aria-label') === null)!

describe('OW-08b failed wash with an unknown vendor price', () => {
  it('offers "tarif vendor belum diketahui" only without an effective rate, says the cost is not zero and HPP not final, and sends price_status UNKNOWN', async () => {
    await failedWash(40)
    const unknown = field('Tarif vendor belum diketahui') as HTMLInputElement
    expect(unknown).not.toBeNull(); expect(unknown.checked).toBe(false)
    expect(box.textContent).toContain('Biayanya belum dihitung (bukan nol), HPP PO ini belum final')
    expect(box.textContent).toContain('Laundry › Harga & tagihan › Harga belum diketahui')
    await tick(confirm()); expect(post().disabled).toBe(true)
    await tick(unknown); expect(box.textContent).toContain('tarif vendor belum diketahui · biaya belum dihitung, bukan nol · HPP belum final')
    await tick(confirm()); expect(post().disabled).toBe(false)
    await act(async () => post().click()); await settle()
    const sent = writes('erp_save_laundry_qc_action_v1')
    expect(sent).toHaveLength(1); expect(sent[0][1].p_action).toBe('POST_FAILED_WASH')
    expect(sent[0][1].p_payload).toMatchObject({ delivery_id: id(20), wash_process_id: id(40), custody_outcome: 'RETRY_AT_VENDOR', price_status: 'UNKNOWN',
      lines: [{ delivery_batch_size_line_id: id(22), qty_attempted_pcs: 2 }] })
  })
  it('keeps the known-rate attempt exactly as before: no unknown option and no price_status key', async () => {
    await failedWash(2)
    expect(field('Tarif vendor belum diketahui')).toBeNull(); expect(box.textContent).toContain('Rp1.200/pcs · biaya Rp2.400')
    await tick(confirm()); expect(post().disabled).toBe(false)
    await act(async () => post().click()); await settle()
    const sent = writes('erp_save_laundry_qc_action_v1')
    expect(sent).toHaveLength(1); expect(Object.keys(sent[0][1].p_payload).sort()).toEqual(['custody_outcome', 'delivery_id', 'lines', 'physical_at', 'reason', 'wash_process_id'])
  })
  it('never offers the unknown option when two rates are effective at once: that read is refused whole', async () => {
    qc.lookups.rate_versions.push({ id: id(41), vendor_id: id(1), wash_process_id: id(2), rate_per_pcs: 1300, effective_from: '2026-08-01T00:00:00Z', effective_to: null })
    await act(async () => root.render(<ConnectedLaundryPage/>)); await settle()
    expect(box.textContent).toContain('Versi rate Laundry bertumpuk pada Vendor/proses yang sama.')
    expect(field('SURAT KIRIM GAGAL CUCI')).toBeNull(); expect(field('Tarif vendor belum diketahui')).toBeNull()
    expect(writes('erp_save_laundry_qc_action_v1')).toHaveLength(0)
  })
  it('shows an unknown-price attempt in the history as not counted yet, never as zero', async () => {
    qc = laundry([receipt({})])
    await act(async () => root.render(<ConnectedLaundryPage/>)); await settle(); await click('Riwayat & koreksi')
    const row = box.querySelector(`[data-laundry-receipt-id="${id(60)}"]`)!
    expect(row.textContent).toContain('tarif vendor belum diketahui · biaya belum dihitung, bukan nol')
    expect(row.textContent).toContain('HPP PO belum final; isi harganya di Harga & tagihan › Harga belum diketahui.')
    expect(row.textContent).not.toContain('Rp0')
  })
})

describe('OW-08b Harga & tagihan › Harga belum diketahui', () => {
  async function open() {
    await import('./LaundryBdPanel')
    await act(async () => root.render(<ConnectedLaundryPage/>)); await settle(); await click('Harga & tagihan')
    await act(async () => { await vi.waitFor(() => expect(field('Vendor harga laundry')).not.toBeNull()) }); await click('Harga belum diketahui')
  }
  it('lists the waiting attempt first and the priced one with its reason, and sets the price once with a reason', async () => {
    await open()
    const rows = [...box.querySelectorAll('[aria-label="Daftar cuci gagal harga belum diketahui"] tbody tr')].map(r => r.textContent)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toContain('LFW-001'); expect(rows[0]).toContain('Belum diketahui · biaya belum dihitung · HPP belum final')
    expect(rows[1]).toContain('Diketahui · Rp 1.500,00/PCS · biaya Rp 3.000,00 · Nota vendor datang · Owner')
    expect(buttons('Isi harga cuci gagal LFW-000')).toHaveLength(0)
    const set = buttons('Isi harga cuci gagal LFW-001')[0]; expect(set.disabled).toBe(true)
    await change('Harga per PCS cuci gagal LFW-001', '0'); await change('Alasan harga cuci gagal', 'Nota vendor datang 5 Okt')
    expect(set.disabled).toBe(true)
    await change('Harga per PCS cuci gagal LFW-001', '1500'); expect(set.disabled).toBe(false)
    await click('Isi harga cuci gagal LFW-001')
    const sent = writes('erp_save_laundry_bd_action_v1')
    expect(sent).toHaveLength(1); expect(sent[0][1].p_action).toBe('SET_FAILED_WASH_PRICE')
    expect(sent[0][1].p_payload).toEqual({ failed_wash_attempt_id: id(61), rate_status: 'KNOWN', rate_per_pcs: '1500.00', reason: 'Nota vendor datang 5 Okt' })
  })
  it('sends FREE or WAIVED as zero with its reason', async () => {
    await open()
    await change('Status harga cuci gagal LFW-001', 'WAIVED'); expect(field('Harga per PCS cuci gagal LFW-001')).toBeNull()
    await change('Alasan harga cuci gagal', 'Vendor tidak menagih attempt ini'); await click('Isi harga cuci gagal LFW-001')
    expect(writes('erp_save_laundry_bd_action_v1')[0][1].p_payload).toEqual({ failed_wash_attempt_id: id(61), rate_status: 'WAIVED', rate_per_pcs: '0.00', reason: 'Vendor tidak menagih attempt ini' })
  })
  it('shows the waiting attempt to a reader who may not set prices, without a button', async () => {
    bd = prices({ can_set_price: false, is_owner: false }); await open()
    expect(box.textContent).toContain('Harga cuci gagal hanya dapat diisi owner/admin yang berhak mengelola HPP.')
    expect(buttons('Isi harga cuci gagal LFW-001')).toHaveLength(0); expect(field('Alasan harga cuci gagal')).toBeNull()
  })
  it('marks a reversed attempt as not priced and without cost', async () => {
    bd = prices({ failed_wash_prices: [{ ...waitingRow, attempt_status: 'REVERSED' }] }); await open()
    expect(box.textContent).toContain('LFW-001 · 2026-09-04 10:00:00 · dibatalkan')
    expect(box.textContent).toContain('Tidak diisi; cuci gagal sudah dibatalkan tanpa biaya')
    expect(buttons('Isi harga cuci gagal LFW-001')).toHaveLength(0)
  })
})
