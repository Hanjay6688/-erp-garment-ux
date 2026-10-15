// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CuttingFabricReturnReversalPanel from './CuttingFabricReturnReversalPanel'
import { parsePickupQueue } from './cuttingPersistence'
import { readProductionRecovery } from './productionRecovery'
import { pickupFixture, recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const rollA = '33333333-3333-4333-8333-333333333333', move = '77777777-7777-4777-8777-777777777777', later = '88888888-8888-4888-8888-888888888888'
const scope = 'disposable:actor-1', onCommitted = vi.fn(async () => {})
const source = () => ({ ...parsePickupQueue(pickupFixture()).rows[0], cutting_group_id: group, po_id: po, group_number: 'CUT-RET', row_version: 4 })
const returned = (extra: Record<string, unknown> = {}) => ({ movement_id: move, cutting_group_roll_id: rollA, roll_id: '55555555-5555-4555-8555-555555555555', roll_number: 'R-001',
  material_sku: 'KAIN-01', material_name: 'Katun', unit_code: 'M', qty_returned: '2.000000', returned_at: '2026-10-14T03:00:00+00:00', unit_cost: '10000.000000',
  qty_reported_remaining: '3.000000', available_now: '12.000000', later_uses: [], ...extra })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.cutting-return-reversal-workspace.v1', group_id: group, po_id: po, number: 'CUT-RET',
  row_version: '4', review_token: 'c'.repeat(32), cut_at: '2026-10-13T01:00:00+00:00', returned: [returned()], eligible: true, blockers: [], business_DML: false, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'production.cutting.view', 'production.distribution.view'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: LockOptions, callback: (lock: Lock | null) => Promise<unknown>) => callback({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount() { await act(async () => root.render(<CuttingFabricReturnReversalPanel source={source()} parentReady onCommitted={onCommitted}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function type(label: string, value: string) {
  const input = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })) })
}
async function check(label: string) { await act(async () => container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!.click()) }
function server(data = workspace()) {
  const requests: Array<Record<string, unknown>> = []
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_cutting_return_reversal_v1') return { data, error: null }
    if (name !== 'erp_cp7_reverse_cutting_return_v1') throw new Error('Unexpected RPC ' + name)
    requests.push(structuredClone(args))
    const p = args.p_payload as Record<string, unknown>, rolls = p.replacement_rolls as Array<Record<string, unknown>>
    return { data: { contract_version: 'cp7.cutting-return-reversal-outcome.v1', kind: 'COMMITTED_OUTCOME', action: rolls.length ? 'CORRECT_RETURN' : 'CANCEL_RETURN',
      request_id: args.p_request, group_id: group, po_id: po, number: 'CUT-RET', row_version: '6', at: '2026-10-15T02:00:00+00:00', reversed_movements: 1, reversed_journals: 1,
      replacement: rolls.length ? { rolls: rolls.map(r => ({ cutting_group_roll_id: r.cutting_group_roll_id, roll_id: rollA, qty_returned: r.qty_returned, unit_cost: '10000.000000', value: '30000.00' })), value: '30000.00' } : null,
      recost_queued: false }, error: null }
  })
  return requests
}
describe('cancel or correct a fabric return (owner D14-10)', () => {
  it('cancels the recorded return in one reviewed save and keeps nothing to correct', async () => {
    const requests = server(); await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Batal / betulkan kain kembali')
    expect(container.textContent).toContain('R-001'); expect(container.textContent).toContain('Biaya PO naik lagi'); expect(container.textContent).toContain('Rp20.000,00')
    expect(button('Batalkan kain kembali').disabled).toBe(true)
    await type('Alasan batal kain kembali', 'Salah catat kain kembali'); await check('Batal kain kembali sudah diperiksa')
    await click('Batalkan kain kembali')
    expect(requests).toHaveLength(1)
    expect(requests[0]).toMatchObject({ p_expected: '4', p_payload: { group_id: group, po_id: po, review_token: 'c'.repeat(32), change_reason: 'Salah catat kain kembali', replacement_rolls: [] } })
    expect(Object.keys(requests[0].p_payload as object).sort()).toEqual(['change_reason', 'group_id', 'po_id', 'replacement_rolls', 'review_token'])
    expect(container.textContent).toContain('CUT-RET: kain kembali dibatalkan'); expect(container.textContent).toContain('catatan aslinya tetap tersimpan')
    expect(onCommitted).toHaveBeenCalledOnce(); expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it('corrects the quantity in the same save and refuses more than the remainder', async () => {
    const requests = server(); await mount(); await click('Batal / betulkan kain kembali')
    await act(async () => [...container.querySelectorAll<HTMLInputElement>('input[type="radio"]')][1].click())
    await type('Jumlah benar roll R-001', '3.5')
    expect(container.textContent).toContain('Roll R-001: 3.5 melebihi sisa yang dicatat saat potong (3).')
    await type('Jumlah benar roll R-001', '3'); expect(container.textContent).toContain('Rp20.000,00 → Rp30.000,00')
    await type('Alasan batal kain kembali', 'Jumlah sebenarnya tiga meter'); await check('Batal kain kembali sudah diperiksa')
    await click('Simpan pembetulan kain kembali')
    expect(requests).toHaveLength(1)
    expect((requests[0].p_payload as Record<string, unknown>).replacement_rolls).toEqual([{ cutting_group_roll_id: rollA, qty_returned: '3' }])
    expect(container.textContent).toContain('CUT-RET: kain kembali dibetulkan'); expect(container.textContent).toContain('nilai baru Rp30.000,00')
  })
  it('names the later use that must be corrected first and never opens the writer', async () => {
    const use = { movement_id: later, movement_type: 'CUTTING_ISSUE', qty: '-12.000000', physical_at: '2026-10-14T05:00:00+00:00', source_type: 'CUTTING_GROUP', source_id: later, label: 'CUT-LATER' }
    server(workspace({ eligible: false, returned: [returned({ available_now: '0.000000', later_uses: [use] })],
      blockers: [{ kind: 'LATER_USE', id: rollA, label: 'R-001', qty_returned: '2.000000', available_now: '0.000000', uses: [use] }] }))
    await mount(); await click('Batal / betulkan kain kembali')
    expect(container.textContent).toContain('Kain kembali di roll R-001 (2) sudah dipakai lagi; sisa di gudang sekarang 0. Betulkan dulu: CUT-LATER (12 M')
    expect(button('Batalkan kain kembali').disabled).toBe(true)
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_cp7_get_cutting_return_reversal_v1')).toBe(true)
  })
  it('rejects a workspace for another group instead of showing it', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ po_id: group }), error: null })
    await mount(); await click('Batal / betulkan kain kembali')
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('tidak cocok')
    expect(container.textContent).not.toContain('R-001')
  })
})
