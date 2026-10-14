// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CuttingFabricReturnPanel from './CuttingFabricReturnPanel'
import { parsePickupQueue } from './cuttingPersistence'
import { readProductionRecovery } from './productionRecovery'
import { pickupFixture, recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const rollA = '33333333-3333-4333-8333-333333333333', rollB = '44444444-4444-4444-8444-444444444444'
const scope = 'disposable:actor-1', onCommitted = vi.fn(async () => {})
const source = () => ({ ...parsePickupQueue(pickupFixture()).rows[0], cutting_group_id: group, po_id: po, group_number: 'CUT-RET', row_version: 4 })
const roll = (id: string, number: string, left: string) => ({ cutting_group_roll_id: id, roll_id: id.replace(/^3|^4/, '5'), roll_number: number,
  material_sku: 'KAIN-01', material_name: 'Katun', unit_code: 'M', qty_issued: '10.000000', qty_consumed: '7.500000', qty_reported_remaining: left, unit_cost: '10000.000000' })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.cutting-return-workspace.v1', group_id: group, po_id: po, number: 'CUT-RET',
  row_version: '4', review_token: 'b'.repeat(32), cut_at: '2026-01-02T01:00:00+00:00', open_from: '2026-01-01',
  warehouse: { id: '66666666-6666-4666-8666-666666666666', code: 'GB1', name: 'Gudang Bahan' },
  rolls: [roll(rollA, 'R-001', '2.500000'), roll(rollB, 'R-002', '0.000000')], eligible: true, blockers: [], business_DML: false, ...extra })
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
async function mount() { await act(async () => root.render(<CuttingFabricReturnPanel source={source()} parentReady onCommitted={onCommitted}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function type(label: string, value: string) {
  const input = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })) })
}
function server() {
  const requests: Array<Record<string, unknown>> = []
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_cutting_return_v1') return { data: workspace(), error: null }
    if (name !== 'erp_cp7_return_cutting_fabric_v1') throw new Error('Unexpected RPC ' + name)
    requests.push(structuredClone(args))
    const p = args.p_payload as Record<string, unknown>
    return { data: { contract_version: 'cp7.cutting-return-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RETURN_FABRIC', request_id: args.p_request,
      group_id: group, po_id: po, number: 'CUT-RET', row_version: '5', returned_at: p.returned_at, value: '12500.00', recost_queued: false,
      rolls: (p.rolls as Array<Record<string, unknown>>).map(r => ({ cutting_group_roll_id: r.cutting_group_roll_id, roll_id: rollA, qty_returned: r.qty_returned, unit_cost: '10000.000000', value: '12500.00' })) }, error: null }
  })
  return requests
}
describe('fabric back to the warehouse (owner D14-4)', () => {
  it('refuses more than the remainder recorded at cutting, then sends one exact reviewed return', async () => {
    const requests = server(); await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Catat kain kembali ke gudang')
    expect(container.textContent).toContain('Gudang Bahan')
    await type('Kain kembali roll R-001', '2.6')
    expect(container.textContent).toContain('Roll R-001: kain kembali 2.6 melebihi sisa yang dicatat saat potong (2.5).')
    expect(button('Simpan kain kembali ke gudang').disabled).toBe(true)
    await type('Kain kembali roll R-001', '1.25')
    expect(container.textContent).toContain('Rp12.500,00')
    await type('Alasan kain kembali', 'Sisa kain dikembalikan ke gudang')
    await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Jumlah kain kembali sudah diperiksa"]')!.click())
    await click('Simpan kain kembali ke gudang')
    expect(requests).toHaveLength(1)
    expect(requests[0]).toMatchObject({ p_expected: '4', p_payload: { group_id: group, po_id: po, review_token: 'b'.repeat(32), change_reason: 'Sisa kain dikembalikan ke gudang',
      rolls: [{ cutting_group_roll_id: rollA, qty_returned: '1.25' }] } })
    expect(Object.keys(requests[0].p_payload as object).sort()).toEqual(['change_reason', 'group_id', 'po_id', 'returned_at', 'review_token', 'rolls'])
    expect(container.textContent).toContain('CUT-RET: kain kembali ke gudang sudah tercatat')
    expect(container.textContent).toContain('nilai Rp12.500,00. Biaya PO berkurang sebesar itu.')
    expect(onCommitted).toHaveBeenCalledOnce(); expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it('shows why a group cannot take a return and never opens the writer', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ eligible: false, blockers: [{ kind: 'ALREADY_RETURNED', id: group, label: 'CUT-RET' }] }), error: null })
    await mount(); await click('Catat kain kembali ke gudang')
    expect(container.textContent).toContain('Kain sisa CUT-RET sudah pernah dikembalikan ke gudang (hanya sekali per potongan).')
    expect(button('Simpan kain kembali ke gudang').disabled).toBe(true)
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_cp7_get_cutting_return_v1')).toBe(true)
  })
  it('rejects a workspace for another group instead of showing it', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ po_id: group }), error: null })
    await mount(); await click('Catat kain kembali ke gudang')
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('tidak cocok')
    expect(container.querySelector('[aria-label="Kain kembali roll R-001"]')).toBeNull()
  })
})
