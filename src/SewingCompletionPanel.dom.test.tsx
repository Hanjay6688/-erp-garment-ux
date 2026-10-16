// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SewingCompletionPanel from './SewingCompletionPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const mandor = '44444444-4444-4444-8444-444444444444', event = '55555555-5555-4555-8555-555555555555', work = '66666666-6666-4666-8666-666666666666'
const onCommitted = vi.fn(async (_message: string) => {})
const recorded = (extra: Record<string, unknown> = {}) => ({ id: event, number: 'SEW-1', qty_pcs: 4, physical_at: '2026-10-14T03:00:00+00:00', row_version: 1,
  reason: 'Setoran pagi', work_completion_id: work, work_status: 'POSTED', reversed: false, wage_amount: 12, in_payroll: false, in_active_pool: false,
  cancel_blocker: null, sku: null, ...extra })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.sewing-completion-workspace.v1', group_id: group, group_version: '7',
  number: 'CUT-SEW', po_id: po, po_number: 'PO-9', po_status: 'SEWING', contractor_id: mandor, contractor_name: 'Mandor Satu',
  picked_up_at: '2026-10-13T02:00:00+00:00', effective_pcs: 10, sewn_pcs: 0, max_qty: 10, ready_unsent_pcs: 0, laundry_draft_pcs: 0,
  rates_committed: true, components: [{ code: 'JAHIT', name: 'Jahit', rate: 2, posted_qty: 0 }, { code: 'OBRAS', name: 'Obras', rate: 1, posted_qty: 0 }], rate_preview: [], rate_timeline: [],
  events: [], can_cancel: true, review_token: 'e'.repeat(32), eligible: true, blockers: [], business_DML: false, wave: null, ...extra })
// Sol R2-10: a wave Potongan, sizes S and M on SKU A (10 cut) and L on SKU B (4 cut); Jahit is paid 10 on A and 30 on B from the
// SKU version starting 13 Oct 17:00 UTC, Obras keeps the base 1; before that nothing is complete.
const skuA = '99999999-9999-4999-8999-999999999991', skuB = '99999999-9999-4999-8999-999999999992'
const r = (jahit: number) => [{ code: 'JAHIT', name: 'Jahit', rate: jahit }, { code: 'OBRAS', name: 'Obras', rate: 1 }]
const waveWorkspace = (extra: Record<string, unknown> = {}) => workspace({ rates_committed: false, components: [], effective_pcs: 14, max_qty: 14,
  wave: { rates_committed: false,
    skus: [{ sku_id: skuA, sku: 'A-01', color: 'Biru', sizes: ['S', 'M'], capacity: 10, max_qty: 10, posted_qty: 0, rates: [] },
      { sku_id: skuB, sku: 'B-01', color: 'Biru', sizes: ['L'], capacity: 4, max_qty: 4, posted_qty: 0, rates: [] }],
    timeline: [{ from: '2026-10-12T17:00:00+00:00', to: '2026-10-13T17:00:00+00:00', complete: false, skus: [{ sku_id: skuA, rates: [] }, { sku_id: skuB, rates: [] }] },
      { from: '2026-10-13T17:00:00+00:00', to: null, complete: true, skus: [{ sku_id: skuA, rates: r(10) }, { sku_id: skuB, rates: r(30) }] }] }, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'production.wip.view', 'production.wip.post', 'production.wip.reverse'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<SewingCompletionPanel groupId={group} groupNumber="CUT-SEW" groupVersion={7} parentReady onCommitted={onCommitted}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
function input(label: string) { const el = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}`); return el }
async function type(label: string, value: string) {
  const el = input(label)
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
describe('selesai jahit di WIP & Sewing (D14-14)', () => {
  it('reads nothing until asked, then shows the Mandor, the remaining pieces and the wage per piece', async () => {
    client.rpc.mockResolvedValue({ data: workspace(), error: null })
    await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Catat selesai jahit')
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_sewing_completion_v1', { p_group: group })
    expect(container.textContent).toContain('Mandor Satu')
    expect(container.textContent).toContain('0 / 10 pcs')
    expect(container.textContent).toContain('Jahit Rp2 + Obras Rp1 = Rp3')
  })
  it('records exactly the reviewed pieces, time and note, and says the wage and the laundry-ready pieces', async () => {
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_sewing_completion_v1') return { data: workspace(), error: null }
      sent.push(args)
      return { data: { contract_version: 'cp7.sewing-completion-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RECORD', request_id: args.p_request,
        group_id: group, po_id: po, number: 'CUT-SEW', result: { work_completion_id: work, sewing_event_id: event, qty_pcs: 4, wage_amount: 12,
          components: 2, sewn_pcs: 4, ready_unsent_pcs: 4, max_qty: 6 } }, error: null }
    })
    await mount(); await click('Catat selesai jahit')
    expect(button('Simpan selesai jahit').disabled).toBe(true)
    await type('Jumlah selesai dijahit CUT-SEW', '11')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Selesai jahit CUT-SEW sudah diperiksa"]')!.disabled).toBe(true)
    await type('Jumlah selesai dijahit CUT-SEW', '4')
    await type('Waktu selesai jahit CUT-SEW', '2026-10-14T10:00')
    await type('Catatan selesai jahit CUT-SEW', 'Setoran pagi')
    expect(container.textContent).toContain('4 pcs × Rp3 = Rp12')
    await act(async () => input('Selesai jahit CUT-SEW sudah diperiksa').click())
    await click('Simpan selesai jahit')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_expected: '7', p_payload: { action: 'RECORD', group_id: group, qty_pcs: '4', physical_at: '2026-10-14T03:00:00.000Z',
      review_token: 'e'.repeat(32), change_reason: 'Setoran pagi' } })
    expect(container.textContent).toContain('CUT-SEW: 4 pcs tercatat selesai dijahit. Upah mandor Rp12 masuk hutang mandor; 4 pcs siap dikirim ke laundry.')
    expect(onCommitted).toHaveBeenCalledWith('CUT-SEW: 4 pcs tercatat selesai dijahit. Upah mandor Rp12 masuk hutang mandor; 4 pcs siap dikirim ke laundry.')
  })
  it('before the first record shows the wage from the rates valid at the sewing time entered (owner D15-3)', async () => {
    // Jahit 1500 from 13 Oct, 1700 from 15 Oct (WIB); Obras keeps its BOM default 500. Today's rate must not be shown for the 14th.
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_sewing_completion_v1') return { data: workspace({ rates_committed: false, components: [],
        rate_preview: [{ code: 'JAHIT', name: 'Jahit', rate: 1700 }, { code: 'OBRAS', name: 'Obras', rate: 500 }],
        rate_timeline: [
          { from: '2026-10-12T17:00:00+00:00', to: '2026-10-14T17:00:00+00:00', complete: true, rates: [{ code: 'JAHIT', name: 'Jahit', rate: 1500 }, { code: 'OBRAS', name: 'Obras', rate: 500 }] },
          { from: '2026-10-14T17:00:00+00:00', to: null, complete: true, rates: [{ code: 'JAHIT', name: 'Jahit', rate: 1700 }, { code: 'OBRAS', name: 'Obras', rate: 500 }] }] }), error: null }
      sent.push(args); return { data: null, error: { message: 'stop here' } }
    })
    await mount(); await click('Catat selesai jahit')
    await type('Waktu selesai jahit CUT-SEW', '2026-10-14T10:00')
    expect(container.textContent).toContain('Upah mandor per pcs pada waktu jahit yang diisi (tarif yang berlaku saat itu; dikunci untuk PO ini saat pertama kali disimpan): Jahit Rp1.500 + Obras Rp500 = Rp2.000.')
    await type('Jumlah selesai dijahit CUT-SEW', '10')
    expect(container.textContent).toContain('Upah yang akan dicatat: 10 pcs × Rp2.000 = Rp20.000.')
    await type('Waktu selesai jahit CUT-SEW', '2026-10-15T08:00')
    expect(container.textContent).toContain('Upah yang akan dicatat: 10 pcs × Rp2.200 = Rp22.000.')
    // Before the first rate applies: no wage shown and nothing can be saved.
    await type('Waktu selesai jahit CUT-SEW', '2026-10-12T08:00')
    expect(container.textContent).toContain('Belum ada tarif lengkap untuk mandor ini pada waktu jahit itu.')
    expect(container.textContent).not.toContain('Upah yang akan dicatat')
    await type('Catatan selesai jahit CUT-SEW', 'Setoran pagi')
    expect(input('Selesai jahit CUT-SEW sudah diperiksa').disabled).toBe(true)
    expect(button('Simpan selesai jahit').disabled).toBe(true)
    expect(sent).toEqual([])
  })
  it('refuses a rate timeline with a gap or an empty complete segment', async () => {
    const seg = (from: string, to: string | null, rates = [{ code: 'JAHIT', name: 'Jahit', rate: 3 }]) => ({ from, to, complete: rates.length > 0, rates })
    client.rpc.mockResolvedValue({ data: workspace({ rates_committed: false, components: [], rate_timeline: [
      seg('2026-10-12T17:00:00+00:00', '2026-10-13T17:00:00+00:00'), seg('2026-10-13T18:00:00+00:00', null)] }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
  it('refuses a preview next to committed rates', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ rate_preview: [{ code: 'JAHIT', name: 'Jahit', rate: 3 }] }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
  it('names why nothing can be recorded and keeps the form closed', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ eligible: false, max_qty: 0, rates_committed: false, components: [],
      blockers: [{ kind: 'NO_WORK_RATE', id: po, label: 'PO-9' }] }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('Tarif kerja (BOM kerja) untuk model PO ini belum ada')
    expect(container.textContent).toContain('Isi komponen kerja model dan tarif mandornya di Master Data → Mandor → Tarif upah mandor.')
    expect(container.querySelector('[aria-label="Jumlah selesai dijahit CUT-SEW"]')).toBeNull()
  })
  it('cancels only a record still at the Mandor and says why another cannot be cancelled', async () => {
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_sewing_completion_v1') return { data: workspace({ sewn_pcs: 7, max_qty: 3, ready_unsent_pcs: 4, events: [recorded(),
        recorded({ id: '77777777-7777-4777-8777-777777777777', qty_pcs: 3, cancel_blocker: 'SENT_OR_DRAFTED_TO_LAUNDRY' })] }), error: null }
      sent.push(args)
      return { data: { contract_version: 'cp7.sewing-completion-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REVERSE', request_id: args.p_request,
        group_id: group, po_id: po, number: 'CUT-SEW', result: { work_completion_id: work, sewing_event_id: event, qty_pcs: 4, status: 'CANCELLED',
          sewn_pcs: 3, ready_unsent_pcs: 0, max_qty: 7 } }, error: null }
    })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('Sebagian potongan ini sudah dikirim atau didraf ke laundry.')
    await click('Batalkan 4 pcs')
    await type('Alasan batal selesai jahit CUT-SEW', 'Salah hitung setoran')
    await click('Batalkan catatan selesai jahit')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_expected: '7', p_payload: { action: 'REVERSE', group_id: group, event_id: event, review_token: 'e'.repeat(32), change_reason: 'Salah hitung setoran' } })
    expect(container.textContent).toContain('CUT-SEW: catatan 4 pcs selesai jahit dibatalkan beserta upahnya.')
  })
  it('a wave Potongan takes the pieces per SKU at that SKU rate of the sewing time, in one request (Sol R2-10)', async () => {
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_sewing_completion_v1') return { data: waveWorkspace(), error: null }
      sent.push(args)
      const lines = (args.p_payload as { lines: { sku_id: string; qty_pcs: string }[] }).lines
      return { data: { contract_version: 'cp7.sewing-completion-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RECORD_WAVE', request_id: args.p_request,
        group_id: group, po_id: po, number: 'CUT-SEW', result: { qty_pcs: 7, wage_amount: 117, sewn_pcs: 7, ready_unsent_pcs: 7, max_qty: 7,
          lines: lines.map((l, i) => ({ sku_id: l.sku_id, sku: i ? 'B-01' : 'A-01', work_completion_id: work, sewing_event_id: event, qty_pcs: Number(l.qty_pcs),
            wage_amount: i ? 62 : 55, components: 2 })) } }, error: null }
    })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('Potongan ini memakai tarif mandor per SKU (wave).')
    expect(container.textContent).toContain('SKU A-01 · Biru · ukuran S, M')
    expect(container.querySelector('[aria-label="Jumlah selesai dijahit CUT-SEW"]')).toBeNull()
    // Before the SKU rates apply nothing can be saved; at the sewing time the rates of each SKU are shown.
    await type('Waktu selesai jahit CUT-SEW', '2026-10-13T10:00')
    expect(container.textContent).toContain('Belum ada tarif lengkap untuk setiap SKU pada waktu jahit itu.')
    await type('Waktu selesai jahit CUT-SEW', '2026-10-14T10:00')
    expect(container.textContent).toContain('Upah per pcs: Jahit Rp10 + Obras Rp1 = Rp11')
    expect(container.textContent).toContain('Upah per pcs: Jahit Rp30 + Obras Rp1 = Rp31')
    await type('Jumlah selesai dijahit CUT-SEW SKU A-01', '11')
    await type('Catatan selesai jahit CUT-SEW', 'Setoran pagi')
    expect(input('Selesai jahit CUT-SEW sudah diperiksa').disabled).toBe(true)
    await type('Jumlah selesai dijahit CUT-SEW SKU A-01', '5'); await type('Jumlah selesai dijahit CUT-SEW SKU B-01', '2')
    expect(container.textContent).toContain('Upah yang akan dicatat: SKU A-01 5 pcs × Rp11 + SKU B-01 2 pcs × Rp31 = Rp117.')
    await act(async () => input('Selesai jahit CUT-SEW sudah diperiksa').click())
    await click('Simpan selesai jahit')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_expected: '7', p_payload: { action: 'RECORD_WAVE', group_id: group, physical_at: '2026-10-14T03:00:00.000Z',
      lines: [{ sku_id: skuA, qty_pcs: '5' }, { sku_id: skuB, qty_pcs: '2' }], review_token: 'e'.repeat(32), change_reason: 'Setoran pagi' } })
    expect(onCommitted).toHaveBeenCalledWith('CUT-SEW: 7 pcs tercatat selesai dijahit (SKU A-01 5 pcs, SKU B-01 2 pcs). Upah mandor Rp117 masuk hutang mandor; 7 pcs siap dikirim ke laundry.')
  })
  it('does not accept a wave answer whose lines or totals differ from what was sent', async () => {
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_sewing_completion_v1') return { data: waveWorkspace(), error: null }
      return { data: { contract_version: 'cp7.sewing-completion-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RECORD_WAVE', request_id: args.p_request,
        group_id: group, po_id: po, number: 'CUT-SEW', result: { qty_pcs: 5, wage_amount: 56, sewn_pcs: 5, ready_unsent_pcs: 5, max_qty: 9,
          lines: [{ sku_id: skuA, sku: 'A-01', work_completion_id: work, sewing_event_id: event, qty_pcs: 5, wage_amount: 55, components: 2 }] } }, error: null }
    })
    await mount(); await click('Catat selesai jahit')
    await type('Waktu selesai jahit CUT-SEW', '2026-10-14T10:00'); await type('Jumlah selesai dijahit CUT-SEW SKU A-01', '5')
    await type('Catatan selesai jahit CUT-SEW', 'Setoran pagi'); await act(async () => input('Selesai jahit CUT-SEW sudah diperiksa').click())
    await click('Simpan selesai jahit')
    // Not accepted as committed: the request stays pending for the recovery check with the same UUID and payload.
    expect(onCommitted).not.toHaveBeenCalled()
    expect(container.textContent).toContain('Respons sukses tidak membawa UUID/action yang cocok dengan kontrak transaksi. UUID/payload lama tetap disimpan untuk Reconcile transaksi.')
  })
  it('refuses a wave Potongan that also carries base rates', async () => {
    client.rpc.mockResolvedValue({ data: waveWorkspace({ components: [{ code: 'JAHIT', name: 'Jahit', rate: 2, posted_qty: 0 }] }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
  it('refuses a workspace for another Potongan', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ group_id: '88888888-8888-4888-8888-888888888888' }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
})
