// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CutoverPanel from './CutoverPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { normalizeClientError } from './lib/clientError'

// Owner D15-5 (FABLE-011): the owner sets the official cutover date; the server refuses older operational transactions.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const ws = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.cutover-workspace.v1', today: '2026-10-16', can_set: true, version: 0,
  current: null, history: [], earliest_operational: { date: '2026-09-01', kind: 'JOURNAL', source_type: 'MISC_FINANCE' },
  earliest_import: { date: '2026-09-10', batch_code: 'SALDO-AWAL' }, latest_allowed: '2026-09-01', business_DML: false, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); auth.current = recoveryIdentity
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: n, mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
function field(label: string) { const el = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}: ${container.textContent}`); return el }
function button(name: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name); if (!b) throw new Error(`Missing ${name}`); return b }
async function type(label: string, value: string) {
  const el = field(label)
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
async function check(label: string) { await act(async () => field(label).click()); await settle() }
const saves = () => client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_set_cutover_v1')

describe('tanggal mulai pakai aplikasi (D15-5)', () => {
  it('names the latest allowed day, holds a later one on screen, and saves the allowed day with the reviewed version', async () => {
    let saved = false
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_cutover_v1') return { data: saved ? ws({ version: 1, current: { version: 1, cutover_date: '2026-09-01', previous_date: null, reason: 'Mulai pakai aplikasi', set_at: '2026-10-16T03:00:00+00:00', set_by: 'Owner' },
        history: [{ version: 1, cutover_date: '2026-09-01', previous_date: null, reason: 'Mulai pakai aplikasi', set_at: '2026-10-16T03:00:00+00:00', set_by: 'Owner' }] }) : ws(), error: null }
      if (name === 'erp_cp7_set_cutover_v1') { saved = true
        return { data: { contract_version: 'cp7.cutover-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'SET', request_id: args.p_request, version: 1, cutover_date: '2026-09-01', previous_date: null }, error: null } }
      throw new Error(name)
    })
    await act(async () => root.render(<CutoverPanel/>)); await settle()
    expect(container.textContent).toContain('Belum disahkan')
    expect(container.textContent).toContain('Paling lambat 1 September 2026: sudah ada transaksi operasional pada tanggal itu.')
    await type('Tanggal mulai pakai aplikasi (WIB)', '2026-09-02'); await type('Alasan tanggal mulai pakai aplikasi', 'Mulai pakai aplikasi')
    expect(container.querySelector('.cmd-problems')?.textContent).toContain('Paling lambat 1 September 2026')
    expect(field('Tanggal mulai pakai aplikasi sudah diperiksa').disabled).toBe(true)
    expect(button('Sahkan tanggal mulai pakai').disabled).toBe(true)
    await type('Tanggal mulai pakai aplikasi (WIB)', '2026-09-01'); await check('Tanggal mulai pakai aplikasi sudah diperiksa')
    await act(async () => button('Sahkan tanggal mulai pakai').click()); await settle()
    expect(saves()).toHaveLength(1)
    expect(saves()[0][1].p_payload).toEqual({ action: 'SET', expected_version: 0, cutover_date: '2026-09-01', reason: 'Mulai pakai aplikasi' })
    expect(container.textContent).toContain('Tersimpan: tanggal mulai pakai aplikasi 1 September 2026.')
    expect(container.textContent).toContain('Berlaku: 1 September 2026')
  })

  it('is read-only for an admin, and refuses a workspace whose latest day does not match its own facts', async () => {
    client.rpc.mockResolvedValueOnce({ data: ws({ can_set: false }), error: null })
    await act(async () => root.render(<CutoverPanel/>)); await settle()
    expect(container.textContent).toContain('Hanya owner yang bisa mengesahkan tanggal ini.')
    expect(container.querySelector('input[aria-label="Tanggal mulai pakai aplikasi (WIB)"]')).toBeNull()
    await act(async () => root.unmount()); root = createRoot(container)
    client.rpc.mockResolvedValueOnce({ data: ws({ latest_allowed: '2026-09-05' }), error: null })
    await act(async () => root.render(<CutoverPanel/>)); await settle()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('tidak cocok (batas)')
  })

  it('shows the server sentence of a refused posting without its code', () => {
    const e = normalizeClientError({ code: 'P0001', message: 'CP7_CUTOVER_BEFORE: Transaksi bertanggal 2026-08-31 jatuh sebelum tanggal mulai pakai aplikasi 2026-09-01 (cutover resmi). Data sebelum tanggal itu masuk lewat Impor Saldo Awal; dokumen lama dibetulkan lewat jalur koreksinya.' })
    expect(e.message).toBe('Transaksi bertanggal 2026-08-31 jatuh sebelum tanggal mulai pakai aplikasi 2026-09-01 (cutover resmi). Data sebelum tanggal itu masuk lewat Impor Saldo Awal; dokumen lama dibetulkan lewat jalur koreksinya.')
    expect(normalizeClientError({ code: 'P0001', message: 'CP7_CUTOVER_STALE' }).message).toBe('Tanggal mulai pakai aplikasi baru saja diubah di layar lain. Muat ulang lalu periksa lagi.')
  })
})
