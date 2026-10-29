// @vitest-environment jsdom
import { act, useEffect, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedSkuHppPage from './ConnectedSkuHppPage'
import type { AttendanceHppPoolPanelProps } from './AttendanceHppPoolPanel'
import type { AttendancePeriodChoicePanelProps } from './AttendancePeriodChoicePanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'

// Wiring-only child doubles; real pool/choice contracts, recovery and async handlers have separate directed DOM controls.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
const observed = vi.hoisted(() => ({ pool: null as AttendanceHppPoolPanelProps | null, choice: null as AttendancePeriodChoicePanelProps | null,
  mounts: { recost: 0, finish: 0, choice: 0 }, next: 0 }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
vi.mock('./RecostQueuePanel', () => ({ default: ({ onChanged }: { onChanged: () => Promise<unknown> }) => {
  useEffect(() => { observed.mounts.recost++ }, [])
  return <button onClick={() => void onChanged()}>Recost commit double</button>
} }))
vi.mock('./PoFinishPanel', () => ({ default: ({ onCommitted }: { onCommitted: () => Promise<unknown> }) => {
  useEffect(() => { observed.mounts.finish++ }, [])
  return <button onClick={() => void onCommitted()}>PO commit double</button>
} }))
vi.mock('./AttendanceHppPoolPanel', () => ({ default: (props: AttendanceHppPoolPanelProps) => {
  observed.pool = props
  return <section aria-label="Pool mount double"><span>{props.refresh}</span><button onClick={() => props.onOpenAttendanceChoice?.({ start: '2026-10-01', end: '2026-10-07' })}>Source P1 route double</button><button onClick={() => void props.onCommitted()}>Pool commit double</button></section>
} }))
vi.mock('./AttendancePeriodChoicePanel', () => ({ default: (props: AttendancePeriodChoicePanelProps) => {
  observed.choice = props
  const [instance] = useState(() => ++observed.next)
  useEffect(() => { observed.mounts.choice++ }, [])
  return <section aria-label="Choice mount double" data-instance={instance}><span>{props.refresh}</span><button onClick={() => void props.onCommitted()}>Choice commit double</button></section>
} }))

let root: Root, container: HTMLDivElement
function identity(role = 'OWNER', permissions = ['finance.hpp.view', 'finance.hpp.manage'], id = recoveryIdentity.identity.profile.id) {
  return { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, role, id, isActive: true }, permissions } }
}
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); auth.current = identity(); client.rpc.mockReset()
  observed.pool = null; observed.choice = null; observed.mounts = { recost: 0, finish: 0, choice: 0 }; observed.next = 0
  client.rpc.mockResolvedValue({ data: { contract_version: 'deliberately unavailable SKU double' }, error: null })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); vi.restoreAllMocks() })
async function flush() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount() { await act(async () => root.render(<ConnectedSkuHppPage/>)); await flush() }
async function click(label: string) { const button = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === label)!; await act(async () => button.click()); await flush() }
const instance = () => container.querySelector('[aria-label="Choice mount double"]')?.getAttribute('data-instance')

describe('S03 mount wiring only, zero Native/Auth/browser credit', () => {
  it('mounts the Owner reader without requiring manage rights and never creates another app route', async () => {
    auth.current = identity('OWNER', ['finance.hpp.view']); await mount()
    expect(observed.choice).not.toBeNull(); expect(observed.choice?.initialPeriod).toBeUndefined(); expect(observed.pool?.onOpenAttendanceChoice).toBeTypeOf('function')
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_get_sku_hpp_v1')).toBe(true)
  })
  it.each(['ADMIN', 'STAFF', 'KEUANGAN'])('does not mount or provide the S03 route for %s', async role => {
    auth.current = identity(role); await mount(); expect(container.querySelector('[aria-label="Choice mount double"]')).toBeNull(); expect(observed.pool?.onOpenAttendanceChoice).toBeUndefined()
  })
  it('opens only authoritative P1 and remounts a fresh choice context on every explicit route', async () => {
    await mount(); const old = instance(); await click('Source P1 route double')
    expect(observed.choice?.initialPeriod).toEqual({ start: '2026-10-01', end: '2026-10-07' }); expect(instance()).not.toBe(old)
    const again = instance(); await click('Source P1 route double'); expect(instance()).not.toBe(again)
    expect(Object.keys(observed.choice?.initialPeriod ?? {}).sort()).toEqual(['end', 'start']); expect(observed.mounts.choice).toBe(3)
  })
  it('refreshes both attendance readers after another HPP writer commits', async () => {
    await mount(); await click('Recost commit double'); expect(observed.pool?.refresh).toBe(1); expect(observed.choice?.refresh).toBe(1)
    await click('PO commit double'); expect(observed.pool?.refresh).toBe(2); expect(observed.choice?.refresh).toBe(2)
  })
  it('refreshes the pool and other HPP writers after a choice commit without changing its own context', async () => {
    await mount(); await click('Source P1 route double'); const before = instance(), reads = client.rpc.mock.calls.length
    await click('Choice commit double'); expect(instance()).toBe(before); expect(observed.choice?.refresh).toBe(0); expect(observed.pool?.refresh).toBe(1)
    expect(observed.mounts.recost).toBe(2); expect(observed.mounts.finish).toBe(2); expect(client.rpc.mock.calls.length).toBe(reads + 1)
  })
  it('refreshes choice after a pool commit without adding the pool own commit to its refresh', async () => {
    await mount(); const before = instance(); await click('Pool commit double')
    expect(instance()).toBe(before); expect(observed.choice?.refresh).toBe(1); expect(observed.pool?.refresh).toBe(0); expect(observed.mounts.recost).toBe(2); expect(observed.mounts.finish).toBe(2)
  })
  it('retires source selection on actor/permission context change without deleting persisted recovery', async () => {
    await mount(); await click('Source P1 route double'); const before = instance()
    localStorage.setItem('erp-production-preserved-test-record', 'unchanged pending envelope double')
    auth.current = identity('OWNER', ['finance.hpp.view'], 'ffffffff-ffff-ffff-ffff-ffffffffffff'); await mount()
    expect(instance()).not.toBe(before); expect(observed.choice?.initialPeriod).toBeUndefined(); expect(localStorage.getItem('erp-production-preserved-test-record')).toBe('unchanged pending envelope double')
  })
})
