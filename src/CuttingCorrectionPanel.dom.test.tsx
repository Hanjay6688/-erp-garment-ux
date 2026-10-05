// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CuttingCorrectionPanel from './CuttingCorrectionPanel'
import { parsePickupQueue } from './cuttingPersistence'
import { productionKey, readProductionRecovery } from './productionRecovery'
import { pickupFixture, recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const scope = 'disposable:actor-1', onCommitted = vi.fn(async () => {})
const source = () => ({ ...parsePickupQueue(pickupFixture()).rows[0], cutting_group_id: group, po_id: po, group_number: 'CUT-EXACT', row_version: 4 })
const workspace = () => ({ contract_version: 'cp7.cutting-reopen-workspace.v1', group_id: group, po_id: po, number: 'CUT-EXACT', row_version: '4', review_token: 'a'.repeat(32), eligible: true, blockers: [], business_DML: false })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'production.cutting.view','production.distribution.view'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: LockOptions, callback: (lock: Lock | null) => Promise<unknown>) => callback({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount(row: ReturnType<typeof source> | null = source()) { await act(async () => root.render(<CuttingCorrectionPanel source={row} parentReady={Boolean(row)} onCommitted={onCommitted}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function review() {
  const input = container.querySelector<HTMLInputElement>('[aria-label="Alasan koreksi potongan"]')!
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, 'Potongan dan bahan asal sudah diperiksa'); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })) })
  await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Potongan dan pembalikan bahan sudah diperiksa"]')!.click())
}
function server(options: { loseReply?: boolean; wrongReceipt?: boolean } = {}) {
  const receipts = new Map<string, unknown>(), requests: unknown[] = []
  let effects = 0
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_cutting_correction_v1') return { data: workspace(), error: null }
    if (name !== 'erp_cp7_reopen_cutting_v1') throw new Error('Unexpected RPC '+name)
    requests.push(structuredClone(args))
    const id = String(args.p_request)
    if (!receipts.has(id)) { ++effects; receipts.set(id, { contract_version: 'cp7.cutting-reopen-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REOPEN_POSTED', request_id: id,
      group_id: group, po_id: po, number: 'CUT-EXACT', status: 'DRAFT_FOR_CORRECTION', row_version: '5',
      Native_response: { cutting_group_id: group, status: 'CUT', row_version: 5, reversed_movement_count: 1, reversed_journal_count: 1, presewing_reversible: true } })
      if (options.loseReply) throw new Error('Committed reply deliberately lost')
    }
    const r = receipts.get(id) as Record<string, unknown>
    return { data: options.wrongReceipt ? { ...r, request_id: po } : r, error: null }
  })
  return { requests, get effects() { return effects } }
}
describe('posted cutting owning review and recovery', () => {
  it('opens only by explicit request and sends one exact reviewed command', async () => {
    const s = server(); await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Periksa koreksi potongan'); expect(button('Buka potongan sebagai draft koreksi').disabled).toBe(true)
    await review(); await click('Buka potongan sebagai draft koreksi')
    expect(s.effects).toBe(1); expect(s.requests).toHaveLength(1)
    expect(s.requests[0]).toMatchObject({ p_expected: '4', p_payload: { group_id: group, po_id: po, review_token: 'a'.repeat(32) } })
    expect(onCommitted).toHaveBeenCalledOnce(); expect(container.textContent).toContain('CUT-EXACT sudah dibuka sebagai draft koreksi')
    expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it('retires the source on wrong actual parent instead of opening a writer', async () => {
    client.rpc.mockResolvedValue({ data: { ...workspace(), po_id: group }, error: null })
    await mount(); await click('Periksa koreksi potongan')
    expect(button('Buka potongan sebagai draft koreksi').disabled).toBe(true); expect(container.querySelector('[role="alert"]')).not.toBeNull()
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_cp7_get_cutting_correction_v1')).toBe(true)
  })
  it('cannot revive held old metadata after target or current authority changes', async () => {
    let resolve!: (value: unknown) => void
    client.rpc.mockImplementation(() => new Promise(r => { resolve = r }))
    await mount(); await act(async () => button('Periksa koreksi potongan').click())
    await mount({ ...source(), cutting_group_id: po, po_id: group, group_number: 'OTHER', row_version: 9 })
    await act(async () => resolve({ data: workspace(), error: null })); await settle()
    expect(container.textContent).not.toContain('Koreksi CUT-EXACT'); expect(container.querySelector('[aria-label="Alasan koreksi potongan"]')).toBeNull()
    await act(async () => button('Periksa koreksi potongan').click())
    const current = auth.current as typeof recoveryIdentity
    auth.current = { ...current, identity: { ...current.identity, permissions: current.identity.permissions.filter(p => p !== 'production.cutting.post') } }
    await mount(); await act(async () => resolve({ data: workspace(), error: null })); await settle()
    expect(container.textContent).not.toContain('Koreksi CUT-EXACT'); expect(container.querySelector('[aria-label="Alasan koreksi potongan"]')).toBeNull()
  })
  it('reconciles lost COMMIT after reload without a posted queue target', async () => {
    const s = server({ loseReply: true }); await mount(); await click('Periksa koreksi potongan'); await review(); await click('Buka potongan sebagai draft koreksi')
    const first = structuredClone(s.requests[0]), raw = localStorage.getItem(productionKey(scope, 'CUTTING_CORRECTION'))
    expect(raw).not.toBeNull(); expect(readProductionRecovery(scope).pending.CUTTING_CORRECTION).not.toBeUndefined()
    await act(async () => root.unmount()); root = createRoot(container); await mount(null)
    await click('Periksa hasil koreksi potongan')
    expect(s.requests[1]).toEqual(first); expect(s.effects).toBe(1); expect(onCommitted).toHaveBeenCalledOnce()
    expect(localStorage.getItem(productionKey(scope, 'CUTTING_CORRECTION'))).toBeNull()
    expect(container.textContent).toContain('CUT-EXACT sudah dibuka sebagai draft koreksi')
  })
  it('keeps an uncertain receipt and fences every other writer', async () => {
    const s = server({ wrongReceipt: true }); await mount(); await click('Periksa koreksi potongan'); await review(); await click('Buka potongan sebagai draft koreksi')
    const raw = localStorage.getItem(productionKey(scope, 'CUTTING_CORRECTION'))
    expect(raw).not.toBeNull(); expect(onCommitted).not.toHaveBeenCalled(); expect(button('Buka potongan sebagai draft koreksi').disabled).toBe(true)
    client.rpc.mockResolvedValue({ data: null, error: { code: '42501', message: 'Current permission revoked' } })
    await click('Periksa hasil koreksi potongan')
    expect(localStorage.getItem(productionKey(scope, 'CUTTING_CORRECTION'))).toBe(raw); expect(s.effects).toBe(1)
  })
})
