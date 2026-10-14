// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PickupReversalPanel from './PickupReversalPanel'
import { parsePickupQueue, type PickupQueueRow } from './cuttingPersistence'
import { pickupFixture, recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const pickup = '33333333-3333-4333-8333-333333333333', mandor = '44444444-4444-4444-8444-444444444444'
const onCommitted = vi.fn(async () => {})
const source = (status: 'POSTED' | 'DRAFT' = 'POSTED'): PickupQueueRow => ({ ...parsePickupQueue(pickupFixture()).rows[0], cutting_group_id: group, po_id: po, group_number: 'CUT-PICK',
  row_version: 6, pickup: { id: pickup, contractor_id: mandor, contractor_name: 'Mandor Satu', picked_up_at: '2026-10-13T02:00:00+00:00', allocation_mode: 'ROLL',
    status, notes: null, row_version: 2, batches: [] } })
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.pickup-reversal-workspace.v1', group_id: group, po_id: po, number: 'CUT-PICK',
  po_number: 'PO-7', pickup_id: pickup, pickup_version: '2', picked_up_at: '2026-10-13T02:00:00+00:00', contractor_id: mandor, contractor_name: 'Mandor Satu',
  batch_count: 1, pieces: 10, restore: { executor_name: 'Tim Potong', po_status: 'CUTTING', po_stage: 'CUTTING', clear_mandor: true, mandor_bound_by: [], other_groups_picked_up: false },
  review_token: 'e'.repeat(32), eligible: true, blockers: [], business_DML: false, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'production.distribution.view', 'production.distribution.edit_draft', 'production.distribution.post'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount(row: PickupQueueRow = source()) { await act(async () => root.render(<PickupReversalPanel source={row} parentReady onCommitted={onCommitted}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function type(label: string, value: string) {
  const input = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })) })
}
describe('batal Bagi Potongan (SG-01)', () => {
  it('appears only for a posted pickup and reads nothing until asked', async () => {
    await mount(source('DRAFT')); expect(container.textContent).toBe('')
    await mount(); expect(client.rpc).not.toHaveBeenCalled(); button('Batalkan Bagi Potongan ini')
  })
  it('reverses with the exact payload once reviewed, and says what was restored', async () => {
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_pickup_reversal_v1') return { data: workspace(), error: null }
      sent.push(args)
      return { data: { contract_version: 'cp7.pickup-reversal-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REVERSE_PICKUP', request_id: args.p_request,
        group_id: group, pickup_id: pickup, po_id: po, number: 'CUT-PICK',
        result: { pickup_status: 'REVERSED', group_status: 'CUT', po_status: 'CUTTING', po_stage: 'CUTTING', mandor_cleared: true, mandor_bound_by: [] } }, error: null }
    })
    await mount(); await click('Batalkan Bagi Potongan ini')
    expect(container.textContent).toContain('Mandor di PO dikosongkan')
    expect(button('Batalkan Bagi Potongan').disabled).toBe(true)
    await type('Alasan batal Bagi Potongan', 'Salah mandor')
    await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Pembatalan Bagi Potongan sudah diperiksa"]')!.click())
    await click('Batalkan Bagi Potongan')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_expected: '2', p_payload: { group_id: group, pickup_id: pickup, review_token: 'e'.repeat(32), change_reason: 'Salah mandor' } })
    expect(container.textContent).toContain('CUT-PICK: Bagi Potongan dibatalkan.')
    expect(onCommitted).toHaveBeenCalled()
  })
  it('names what holds the pickup and keeps the button off', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ eligible: false, blockers: [{ kind: 'WORK_COMPLETION', id: '55555555-5555-4555-8555-555555555555', status: 'DRAFT' }] }), error: null })
    await mount(); await click('Batalkan Bagi Potongan ini')
    expect(container.textContent).toContain('Sudah ada setoran jahit (termasuk yang masih draf). Status: DRAFT.')
    expect(button('Batalkan Bagi Potongan').disabled).toBe(true)
  })
  it('refuses a workspace for another pickup', async () => {
    client.rpc.mockResolvedValue({ data: workspace({ pickup_id: '66666666-6666-4666-8666-666666666666' }), error: null })
    await mount(); await click('Batalkan Bagi Potongan ini')
    expect(container.textContent).toContain('tidak cocok dengan potongan yang diperiksa')
  })
})
