// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedSkuHppPage from './ConnectedSkuHppPage'
import type { AttendanceHppPoolPanelProps } from './AttendanceHppPoolPanel'
import type { AttendanceChoiceAction, AttendanceChoicePayload, AttendanceChoiceWorkspace } from './attendancePeriodChoiceContract'
import { readProductionRecovery, type ProductionEnvelope } from './productionRecovery'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { attendanceChoiceCurrent as current, attendanceChoiceIds as ids, attendanceChoiceOutcomeFixture as outcome,
  attendanceChoicePreviewFixture as preview, attendanceChoiceQuery as query, attendanceChoiceWorkspace as workspace } from '../tests/fixtures/attendancePeriodChoice'

// Real connected parent + real S03 UI/hook; unrelated children and all RPC responses are explicit local doubles.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
const observed = vi.hoisted(() => ({ pool: null as AttendanceHppPoolPanelProps | null }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
vi.mock('./RecostQueuePanel', () => ({ default: () => null }))
vi.mock('./PoFinishPanel', () => ({ default: () => null }))
vi.mock('./AttendanceHppPoolPanel', () => ({ default: (props: AttendanceHppPoolPanelProps) => {
  observed.pool = props
  return <section aria-label="Pool routing double">
    <button onClick={() => props.onOpenAttendanceChoice?.({ start: query.period_start, end: query.period_end })}>Open P1 double</button>
    <button onClick={() => props.onOpenAttendanceChoice?.({ start: '2026-10-08', end: '2026-10-14' })}>Open P2 double</button>
  </section>
} }))

type Row = Record<string, unknown>
let root: Root, container: HTMLDivElement, state: { periods: Map<string, AttendanceChoiceWorkspace>; lose: boolean; effects: number; receipts: Map<string, unknown> }
function owner() { return { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, id: ids.actor, authUserId: ids.actor }, permissions: ['finance.hpp.view', 'finance.hpp.manage'] } } }
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); auth.current = owner(); client.rpc.mockReset(); observed.pool = null
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, callback: (lock: unknown) => Promise<unknown>) => callback({ name: 'shared', mode: 'exclusive' }) } })
  state = { periods: new Map(), lose: false, effects: 0, receipts: new Map() }
  client.rpc.mockImplementation(async (name: string, args: Row) => {
    // A SKU report does not authorize S03; S03 must obtain its own exact-period source read.
    if (name === 'erp_get_sku_hpp_v1') return { data: null, error: { code: 'P0001', message: 'Declared unavailable SKU report double' } }
    if (name === 'erp_cp7_get_attendance_choice_v1') {
      const start = args.p_period_start as string, end = args.p_period_end as string
      const value = state.periods.get(start) ?? workspace({ period_start: start, period_end: end })
      return { data: { ...value, offset: args.p_offset, limit: args.p_limit }, error: null }
    }
    if (name === 'erp_cp7_preview_attendance_choice_v1') {
      const p = args.p_payload as AttendanceChoicePayload
      return { data: preview(state.periods.get(p.period_start) ?? workspace({ period_start: p.period_start, period_end: p.period_end }), p, args.p_action as AttendanceChoiceAction), error: null }
    }
    if (name === 'erp_cp7_save_attendance_choice_v1') {
      const p = args.p_payload as AttendanceChoicePayload, action = args.p_action as AttendanceChoiceAction, id = args.p_request as string
      if (!state.receipts.has(id)) {
        const e: ProductionEnvelope = { action, payload: args.p_payload as ProductionEnvelope['payload'], expectedVersion: null, id,
          createdAt: '2026-10-30T00:00:00Z', fingerprint: JSON.stringify({ action, payload: p, expectedVersion: null }) }
        state.effects++; state.receipts.set(id, outcome(e)); state.periods.set(p.period_start, current(p.choice ?? 'CARRY'))
      }
      return state.lose ? { data: null, error: { status: 503, message: 'Lost actual-response stand-in' } } : { data: state.receipts.get(id), error: null }
    }
    throw Error('Unexpected RPC:' + name)
  })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function flush() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount() { await act(async () => root.render(<ConnectedSkuHppPage/>)); await flush() }
const button = (text: string) => [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text)!
const field = (label: string) => container.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(`[aria-label="${label}"]`)!
async function click(element: HTMLElement) { await act(async () => element.click()); await flush() }
async function change(label: string, value: string) { await act(async () => { const element = field(label), prototype = element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(element, value); element.dispatchEvent(new Event(element instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true })) }); await flush() }
const reads = () => client.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_get_attendance_choice_v1')
const writes = () => client.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_save_attendance_choice_v1')
async function reviewed() {
  await change('Tindakan pilihan biaya', 'CHOOSE'); await change('Pilihan biaya absensi', 'CARRY'); await change('Alasan pilihan biaya absensi', 'Sumber periode sudah diperiksa Owner')
  await click(button('Periksa perubahan biaya')); await click(field('Pilihan biaya sudah diperiksa'))
}

describe('Mounted S03 with real UI/hook and explicit local RPC doubles; Native/Auth/browser zero', () => {
  it('opens fresh source P1, requires a new64 token and keeps its real context alive after parent refresh', async () => {
    await mount(); expect(reads()).toHaveLength(0); await click(button('Open P1 double'))
    expect(reads()[0][1]).toEqual({ p_period_start: query.period_start, p_period_end: query.period_end, p_offset: 0, p_limit: 25 })
    expect(field('Tindakan pilihan biaya').value).toBe(''); expect(writes()).toHaveLength(0)
    await reviewed(); await click(button('Simpan pilihan biaya'))
    expect(state.effects).toBe(1); expect(writes()).toHaveLength(1); expect((writes()[0][1] as Row).p_payload).toMatchObject({ review_token: 'b'.repeat(64) })
    expect(observed.pool?.refresh).toBe(1); expect(container.textContent).toContain('Pilihan biaya absensi sudah tercatat')
    expect(container.textContent).toContain('Pilihan yang berlaku'); expect(field('Mulai periode asal').value).toBe(query.period_start)
    expect(field('Tindakan pilihan biaya').disabled).toBe(false); expect(readProductionRecovery('disposable:' + ids.actor).pending).toEqual({})
  })
  it('keeps the persisted old-source UUID across route remount and does not refresh unrelated P2 on replay success', async () => {
    await mount(); await click(button('Open P1 double')); await reviewed(); state.lose = true; await click(button('Simpan pilihan biaya'))
    const original = structuredClone(writes()[0][1]); expect(state.effects).toBe(1); await click(button('Open P2 double'))
    expect(field('Mulai periode asal').value).toBe('2026-10-08'); expect(container.querySelector('[aria-label="Permintaan biaya absensi tertunda"]')?.textContent).toContain('1 Okt 2026 – 7 Okt 2026')
    state.lose = false; await click(button('Periksa hasil penyimpanan'))
    expect(writes()[1][1]).toEqual(original); expect(state.effects).toBe(1); expect(field('Mulai periode asal').value).toBe('2026-10-08')
    expect(container.textContent).toContain('Hasil tentukan pilihan untuk periode asal 1 Okt 2026 – 7 Okt 2026 sudah dipastikan')
    expect(container.textContent).not.toContain('Pilihan biaya absensi sudah tercatat. Periode dan riwayat dimuat ulang.')
    expect(observed.pool?.refresh).toBe(0); expect(readProductionRecovery('disposable:' + ids.actor).pending).toEqual({})
  })
})
