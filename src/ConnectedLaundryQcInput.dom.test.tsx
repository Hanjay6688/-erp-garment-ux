// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedLaundryPage from './ConnectedLaundryPage'
import ConnectedQcFinalPage from './ConnectedQcFinalPage'
import { laundryQcInputFixture } from '../tests/fixtures/laundryQcInput'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'
import type { LaundryQcScope } from './laundryQcModel'

const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn(), source: null as { key: string; document: { id: string; number: string } } | null }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
vi.mock('./TransactionSourceNavigation', () => ({ useTransactionSource: () => mock.source }))
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
function identity() {
  return { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED',
    profile: { id: id(100), authUserId: id(101), rowVersion: 1, roleRowVersion: 1, role: 'OWNER', roleName: 'Owner', isActive: true },
    permissions: ['production.laundry.view', 'production.laundry.create', 'production.laundry.post', 'production.laundry.reverse',
      'production.final_sku.view', 'production.final_sku.post', 'production.final_sku.reverse'] } }
}
function withDelivery() {
  const w = laundryQcInputFixture('LAUNDRY')
  ;(w.deliveries as unknown[]).push({ delivery_id: id(20), delivery_number: 'LDR-001', row_version: 3, status: 'SENT',
    physical_at: '2026-09-02T00:00:00Z', target_dyeing_color: 'Hitam', special_instruction: null,
    po_id: id(14), po_number: 'PO-001', model_id: id(7), cutting_group_id: id(12), group_number: 'P-001',
    cutting_group_row_version: 4, model_code: 'MOD-A', model_name: 'Model A', contractor_name: 'Mandor A',
    vendor_id: id(1), vendor_code: 'LDR-A', vendor_name: 'Laundry A', wash_process_id: id(2), process_code: 'WASH',
    process_name: 'Cuci', delivery_line_id: id(21), qty_sent_pcs: 2, estimated_rate_snapshot: 1200, estimated_cost: 2400,
    distribution_batch_id: id(10), batch_no: 1, returned_qty_pcs: 0, physical_outstanding_qty_pcs: 2,
    returned_unprocessed_qty_pcs: 0, active_claim_qty_pcs: 0, reversible: true, reversal_blocker: null,
    sizes: [{ delivery_batch_size_line_id: id(22), size_id: id(9), size_code: '31', sort_order: 1,
      qty_sent_pcs: 2, good_returned_qty_pcs: 0, bs_returned_qty_pcs: 0, outstanding_qty_pcs: 2 }], receipts: [] })
  return w
}
let root: Root, box: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.auth = identity(); mock.rpc.mockReset(); mock.source = null
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: vi.fn(async (name, _options, run) => run({ name, mode: 'exclusive' })) } })
  mock.rpc.mockImplementation((name, args) => {
    if (name === 'erp_get_laundry_qc_workspace_v1') return Promise.resolve({ data: args.p_scope === 'LAUNDRY' ? withDelivery() : laundryQcInputFixture('QC'), error: null })
    throw Error('Unexpected writer/search: ' + name)
  })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const settle = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function mount(scope: LaundryQcScope = 'LAUNDRY') { await act(async () => root.render(scope === 'LAUNDRY' ? <ConnectedLaundryPage/> : <ConnectedQcFinalPage/>)); await settle() }
const buttons = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].filter(e => e.textContent?.trim() === name)
async function click(name: string) { expect(buttons(name)).toHaveLength(1); await act(async () => buttons(name)[0].click()); await settle() }
const input = (label: string) => box.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!
const select = (label: string) => box.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`)!
async function change(e: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, value: string) {
  expect(e).not.toBeNull(); await act(async () => { const proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) }); await settle()
}
const assertReadsOnly = () => expect(mock.rpc.mock.calls.every(([name]) => name === 'erp_get_laundry_qc_workspace_v1')).toBe(true)
async function failedRefresh() {
  mock.rpc.mockResolvedValueOnce({ data: null, error: { code: '42501', message: 'current source denied' } }); await click('Muat ulang data')
  expect(box.querySelectorAll('[data-kpi-state="UNKNOWN"]')).toHaveLength(4); expect(box.querySelector('.clq-panel')).toBeNull()
}

describe('Laundry/QC own input survives current source retirement', () => {
  const qcHistory = () => {
    const w = laundryQcInputFixture('QC')
    ;(w.qc_history as unknown[]).push({ qc_inspection_id: id(70), inspection_number: 'QC-EXACT-001', status: 'POSTED',
      row_version: 2, physical_at: '2026-09-04T03:00:00Z', destination_location_id: id(5), location_name: 'FG A',
      po_id: id(14), po_number: 'PO-001', good_qty_pcs: 1, bs_qty_pcs: 0, cutting_group_count: 1,
      reversible: true, reversal_blocker: null })
    return w
  }
  it('opens the exact source QC history without writing or using another first-page inspection', async () => {
    mock.source = { key: 'actual-QC-source', document: { id: id(70), number: 'QC-EXACT-001' } }
    mock.rpc.mockResolvedValue({ data: qcHistory(), error: null }); await mount('QC')
    expect(mock.rpc).toHaveBeenCalledWith('erp_get_laundry_qc_workspace_v1', { p_scope: 'QC', p_query: 'QC-EXACT-001' })
    const row = box.querySelector(`[data-qc-inspection-id="${id(70)}"][data-source-focus="true"]`)
    expect(row?.textContent).toContain('Finalisasi asal dari buku transaksi'); expect(row?.textContent).toContain('QC-EXACT-001'); assertReadsOnly()
  })
  it('does not enable a different QC inverse when the exact source is absent or its current read is denied', async () => {
    mock.source = { key: 'missing-QC-source', document: { id: id(71), number: 'QC-EXACT-001' } }
    mock.rpc.mockResolvedValue({ data: qcHistory(), error: null }); await mount('QC')
    expect(box.textContent).toContain('Finalisasi asal belum ditemukan'); expect(input('Alasan reversal QC-EXACT-001').disabled).toBe(true)
    expect(buttons('Batalkan finalisasi')[0].disabled).toBe(true); await failedRefresh(); expect(box.querySelector('[data-qc-inspection-id]')).toBeNull(); assertReadsOnly()
  })
  it('retains only its own source QC reason across refresh and retires it on a new source selection', async () => {
    mock.source = { key: 'QC-source-A', document: { id: id(70), number: 'QC-EXACT-001' } }
    mock.rpc.mockResolvedValue({ data: qcHistory(), error: null }); await mount('QC'); await change(input('Alasan reversal QC-EXACT-001'), 'Own source QC reason')
    await failedRefresh(); await click('Muat ulang data'); expect(input('Alasan reversal QC-EXACT-001').value).toBe('Own source QC reason')
    mock.source = { ...mock.source, key: 'QC-source-B' }; await mount('QC'); expect(input('Alasan reversal QC-EXACT-001').value).toBe(''); assertReadsOnly()
  })
  it('retains raw send quantity and own time/notes across failure, revalidates changed availability, resets confirmation', async () => {
    await mount(); await change(select('BATCH DISTRIBUSI AUTHORITATIVE'), id(10)); await change(input('Qty kirim size 31'), '0005')
    await change(input('WARNA TARGET'), 'NAVY OPERATOR'); await change(input('WAKTU FISIK KELUAR'), '2026-09-04T17:00')
    await change(input('ALASAN / BUKTI SERAH TERIMA'), 'Raw own reason'); await change(box.querySelector('textarea')!, 'Own notes exact')
    await act(async () => box.querySelector<HTMLInputElement>('.clq-confirm input')!.click()); await failedRefresh()
    mock.rpc.mockImplementation(() => { const w = withDelivery(); w.ready_batches[0].sizes[0].allocated_qty_pcs = 4; w.ready_batches[0].sizes[0].available_qty_pcs = 2; w.ready_batches[0].group_unsent_ready_qty_pcs = 2; return Promise.resolve({ data: w, error: null }) })
    await click('Muat ulang data'); expect(select('BATCH DISTRIBUSI AUTHORITATIVE').value).toBe(id(10)); expect(input('Qty kirim size 31').value).toBe('0005')
    expect(input('WARNA TARGET').value).toBe('NAVY OPERATOR'); expect(input('WAKTU FISIK KELUAR').value).toBe('2026-09-04T17:00'); expect(box.querySelector('textarea')!.value).toBe('Own notes exact')
    expect(box.querySelector<HTMLInputElement>('.clq-confirm input')!.checked).toBe(false); expect(box.textContent).toContain('Qty melebihi sisa data server')
    expect(box.querySelector<HTMLButtonElement>('[aria-label="Post pengiriman atomic"]')!.disabled).toBe(true); assertReadsOnly()
  })
  it('keeps separate send/return/failed-wash own drafts when changing tabs and never carries a confirmation', async () => {
    await mount(); await change(input('WARNA TARGET'), 'SEND ONLY'); await click('Terima kembali')
    await change(input('ALASAN / BUKTI PENERIMAAN'), 'RETURN ONLY'); await click('Cuci gagal berbayar')
    await change(input('ALASAN TAGIHAN GAGAL CUCI'), 'FAILED ONLY'); await click('Kirim ke Laundry'); expect(input('WARNA TARGET').value).toBe('SEND ONLY')
    await click('Terima kembali'); expect(input('ALASAN / BUKTI PENERIMAAN').value).toBe('RETURN ONLY'); await click('Cuci gagal berbayar'); expect(input('ALASAN TAGIHAN GAGAL CUCI').value).toBe('FAILED ONLY'); assertReadsOnly()
  })
  it('retains owning inverse reason through failed/refreshed history and does not send an inverse', async () => {
    await mount(); await click('Riwayat & koreksi'); await change(input('Alasan reversal LDR-001'), 'Barang belum keluar setelah diperiksa')
    await failedRefresh(); await click('Muat ulang data'); expect(input('Alasan reversal LDR-001').value).toBe('Barang belum keluar setelah diperiksa'); assertReadsOnly()
  })
  it('retains QC raw Good/BS and selected source, then refuses a fresh source that has less available', async () => {
    await mount('QC'); await change(box.querySelector('.clq-form-grid select')!, id(12)); await change(input('Good final size 31'), '0004')
    await change(input('BS QC size 31'), '00'); await change(input('ALASAN / BUKTI HASIL QC'), 'QC raw own reason'); await failedRefresh()
    mock.rpc.mockImplementation(() => { const w = laundryQcInputFixture('QC'); w.qc_queue[0].qty_good_received = 5; w.qc_queue[0].available_for_qc_qty_pcs = 2; return Promise.resolve({ data: w, error: null }) })
    await click('Muat ulang data'); expect(input('Good final size 31').value).toBe('0004'); expect(input('BS QC size 31').value).toBe('00'); expect(input('ALASAN / BUKTI HASIL QC').value).toBe('QC raw own reason')
    expect(box.querySelector<HTMLInputElement>('.clq-confirm input')!.checked).toBe(false); expect([...box.querySelectorAll<HTMLButtonElement>('button')].find(e => e.getAttribute('aria-label') === 'Post QC + Final SKU atomic')!.disabled).toBe(true); assertReadsOnly()
  })
  it.each(['actor', 'row', 'role', 'permissions'] as const)('retires own input when current %s authority changes', async kind => {
    await mount(); await change(input('WARNA TARGET'), 'PRIOR ACTOR OWN INPUT'); const auth = structuredClone(mock.auth) as ReturnType<typeof identity>
    if (kind === 'actor') { auth.identity.profile.id = id(200); auth.identity.profile.authUserId = id(201) }
    if (kind === 'row') auth.identity.profile.rowVersion += 1
    if (kind === 'role') auth.identity.profile.roleRowVersion += 1
    if (kind === 'permissions') auth.identity.permissions = auth.identity.permissions.filter(p => p !== 'production.laundry.reverse')
    mock.auth = auth; await mount(); expect(input('WARNA TARGET').value).toBe(''); assertReadsOnly()
  })
  it('a committed delivery retires own drafts and confirmation without carrying them into another transaction', async () => {
    await mount(); await change(select('BATCH DISTRIBUSI AUTHORITATIVE'), id(10)); await change(box.querySelectorAll<HTMLSelectElement>('.clq-form-grid select')[1], id(1))
    await change(select('PROSES CUCI TARGET'), id(2)); await change(input('WARNA TARGET'), 'POSTED COLOR'); await change(input('WAKTU FISIK KELUAR'), '2026-09-04T17:00')
    await change(input('ALASAN / BUKTI SERAH TERIMA'), 'Matched physical delivery'); await change(input('Qty kirim size 31'), '2')
    await act(async () => box.querySelector<HTMLInputElement>('.clq-confirm input')!.click()); await settle()
    mock.rpc.mockImplementation((name, args) => Promise.resolve(name === 'erp_get_laundry_qc_workspace_v1' ? { data: withDelivery(), error: null } : { data: { contract_version: 'CP6_V2620', committed: true, action: args.p_action, client_request_id: args.p_client_request_id }, error: null }))
    const post = box.querySelector<HTMLButtonElement>('[aria-label="Post pengiriman atomic"]')!; expect(post.disabled).toBe(false); await act(async () => post.click()); await settle()
    expect(mock.rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(1); expect(input('WARNA TARGET').value).toBe('')
    expect(input('ALASAN / BUKTI SERAH TERIMA').value).toBe(''); expect(select('BATCH DISTRIBUSI AUTHORITATIVE').value).toBe(''); expect(box.querySelector<HTMLInputElement>('.clq-confirm input')!.checked).toBe(false)
  })
})
