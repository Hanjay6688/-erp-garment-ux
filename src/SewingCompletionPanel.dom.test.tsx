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
const onCommitted = vi.fn(async () => {})
const recorded = (extra: Record<string, unknown> = {}) => ({ id: event, number: 'SEW-1', qty_pcs: 4, physical_at: '2026-10-14T03:00:00+00:00', row_version: 1,
  reason: 'Setoran pagi', work_completion_id: work, work_status: 'POSTED', reversed: false, wage_amount: 12, in_payroll: false, in_active_pool: false,
  cancel_blocker: null, ...extra })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.sewing-completion-workspace.v1', group_id: group, group_version: '7',
  number: 'CUT-SEW', po_id: po, po_number: 'PO-9', po_status: 'SEWING', contractor_id: mandor, contractor_name: 'Mandor Satu',
  picked_up_at: '2026-10-13T02:00:00+00:00', effective_pcs: 10, sewn_pcs: 0, max_qty: 10, ready_unsent_pcs: 0, laundry_draft_pcs: 0,
  rates_committed: true, components: [{ code: 'JAHIT', name: 'Jahit', rate: 2, posted_qty: 0 }, { code: 'OBRAS', name: 'Obras', rate: 1, posted_qty: 0 }],
  events: [], can_cancel: true, review_token: 'e'.repeat(32), eligible: true, blockers: [], business_DML: false, ...extra })
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
    expect(onCommitted).toHaveBeenCalled()
  })
  it('names why nothing can be recorded and keeps the form closed', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ eligible: false, max_qty: 0, rates_committed: false, components: [],
      blockers: [{ kind: 'NO_WORK_RATE', id: po, label: 'PO-9' }] }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('Tarif kerja (BOM kerja) untuk model PO ini belum ada')
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
  it('refuses a workspace for another Potongan', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ group_id: '88888888-8888-4888-8888-888888888888' }), error: null })
    await mount(); await click('Catat selesai jahit')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
})
