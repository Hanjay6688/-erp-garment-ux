// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PoFinishPanel, { rupiahText } from './PoFinishPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const po = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333'
const onCommitted = vi.fn(async () => {})
const list = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.po-finish-list.v1', query: 'PO-9', offset: 0, limit: 20, total: 2, next_offset: null,
  rows: [{ id: po, number: 'PO-9', status: 'SEWING', contractor_name: 'Mandor Satu', fg_pcs: 10 }, { id: other, number: 'PO-90', status: 'FINISHED', contractor_name: null, fg_pcs: 4 }],
  business_DML: false, ...extra })
const hpp = (extra: Record<string, unknown> = {}) => ({ display_status: 'SEMENTARA', engine_cost_state: 'ACTUAL', total: '1200.00', qty_basis_pcs: 10, per_pcs: '120.00',
  pending_reasons: ['PRODUKSI_BELUM_FINISHED'], latest_hpp_at: '2026-10-14T03:00:00+00:00', ...extra })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.po-finish-workspace.v1', po_id: po, po_number: 'PO-9', po_status: 'SEWING',
  stage: 'QC', contractor_name: 'Mandor Satu', fg_pcs: 10, fg_lots: 1, laundry_sent_pcs: 10, laundry_returned_pcs: 10, laundry_claimed_pcs: 0,
  laundry_good_pcs: 10, qc_accounted_pcs: 10, open_bs_cases: 0, recost_open: 0, wip_balance: '35.50', hpp: hpp(), finish_date: '2026-10-15',
  review_token: 'f'.repeat(32), eligible: true, blockers: [], business_DML: false, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'finance.hpp.view', 'finance.hpp.manage'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<PoFinishPanel onCommitted={onCommitted}/>)); await settle() }
function button(name: string) {
  const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === name || b.getAttribute('aria-label') === name)
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
async function click(name: string) { await act(async () => button(name).click()); await settle() }
function input(label: string) { const el = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}`); return el }
async function type(label: string, value: string) {
  const el = input(label)
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
async function pick(ws: Record<string, unknown>, finish?: (args: Record<string, unknown>) => unknown) {
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_list_po_finish_v1') return { data: list(), error: null }
    if (name === 'erp_cp7_get_po_finish_v1') return { data: ws, error: null }
    return { data: finish?.(args), error: null }
  })
  await mount(); await type('Cari nomor PO', 'PO-9'); await click('Cari PO'); await click('Pilih PO PO-9')
}
describe('selesai PO dan HPP final di HPP & Rekalkulasi (D14-14)', () => {
  it('reads nothing until asked, then lists the POs and shows what the Native finish checks', async () => {
    client.rpc.mockResolvedValue({ data: list(), error: null })
    await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await pick(workspace())
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_list_po_finish_v1', { p_query: 'PO-9', p_offset: 0 })
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_po_finish_v1', { p_po: po })
    expect(container.textContent).toContain('dikirim 10 · kembali 10 · klaim selesai 0 pcs')
    expect(container.textContent).toContain('Rp35,50')
    expect(container.textContent).toContain('Rp120/pcs · Sementara (PO belum selesai)')
    expect(container.textContent).toContain('Tanggal selesai: 2026-10-15 (hari ini, WIB)')
    expect(button('Selesaikan PO dan kunci HPP final').disabled).toBe(true)
  })
  it('finishes exactly the reviewed PO and says the final HPP and the WIP closed', async () => {
    const sent: Array<Record<string, unknown>> = []
    await pick(workspace(), args => {
      sent.push(args)
      return { contract_version: 'cp7.po-finish-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'FINISH', request_id: args.p_request, po_id: po, po_number: 'PO-9',
        result: { status: 'FINISHED', fg_pcs: 10, hpp: hpp({ display_status: 'BELUM_LENGKAP', pending_reasons: ['RECOST_BELUM_SELESAI'], per_pcs: '123.55', total: '1235.50' }),
          residual_closed: '0.00', wip_after: '0.00', finished_on: '2026-10-15', recost_open: 1 } }
    })
    await type('Catatan selesai PO PO-9', 'Semua barang sudah QC')
    await act(async () => input('PO PO-9 sudah diperiksa').click())
    await click('Selesaikan PO dan kunci HPP final')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_payload: { action: 'FINISH', po_id: po, review_token: 'f'.repeat(32), change_reason: 'Semua barang sudah QC' } })
    expect(container.textContent).toContain('PO-9: PO selesai pada 2026-10-15. HPP final Rp123,55/pcs untuk 10 pcs (total Rp1.235,50). Sisa WIP Rp0 dibebankan ke biaya lain-lain. Masih perlu: hitung ulang HPP PO ini masih antre atau gagal')
    expect(onCommitted).toHaveBeenCalled()
  })
  it('names why the PO cannot be finished and keeps the form closed', async () => {
    await pick(workspace({ eligible: false, laundry_returned_pcs: 8, blockers: [{ kind: 'LAUNDRY_OUTSTANDING', qty: 2 }, { kind: 'OPEN_BS', qty: 1 }] }))
    expect(container.textContent).toContain('2 pcs masih di laundry')
    expect(container.textContent).toContain('1 kasus BS/rework masih terbuka.')
    expect(container.querySelector('[aria-label="Catatan selesai PO PO-9"]')).toBeNull()
  })
  it('refuses a workspace for another PO or an eligible finished PO', async () => {
    await pick(workspace({ po_id: other }))
    expect(container.textContent).toContain('tidak cocok dengan PO yang diperiksa')
    await act(async () => root.unmount()); root = createRoot(container)
    await pick(workspace({ po_status: 'FINISHED' }))
    expect(container.textContent).toContain('tidak cocok dengan PO yang diperiksa')
  })
  it('shows exact Rupiah from the server strings', () => {
    expect(rupiahText('9007199254740993.01')).toBe('Rp9.007.199.254.740.993,01')
    expect(rupiahText('-12.00')).toBe('-Rp12')
    expect(rupiahText('0.00')).toBe('Rp0')
  })
})
