// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PayrollKasbonPanel from './PayrollKasbonPanel'
import { kasbonCents } from './payrollKasbonContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const contractor = '11111111-1111-4111-8111-111111111111', payroll = '22222222-2222-4222-8222-222222222222'
const bank = '33333333-3333-4333-8333-333333333333', kas = '44444444-4444-4444-8444-444444444444'
const onChanged = vi.fn(async () => true)
const advance = (extra: Record<string, unknown> = {}) => ({ id: kas, number: 'KB-20261014-ABC123', contractor_id: contractor, advance_date: '2026-10-13', amount: '2500.00',
  status: 'GIVEN', reason: 'Kasbon anak sakit', cash_account_id: bank, recovered: '0.00', reserved: '0.00', free: '2500.00', allocations: [], ...extra })
const workspace = (advances: unknown[] = []) => ({ contract_version: 'cp7.kasbon-workspace.v1', contractor: { id: contractor, code: 'M01', name: 'Mandor Satu' },
  advances, payroll_drafts: [{ id: payroll, payroll_number: 'PR-1', status: 'CALCULATED', row_version: '3', period_start: '2026-10-01', period_end: '2026-10-15',
    earnings: '6000.00', deduction_total: '0.00', net_payable: '6000.00' }],
  cash_accounts: [{ id: bank, code: 'BC1', name: 'Bank satu', review_token: 'c'.repeat(32), eligible: true }], open_from: '2026-10-01', today: '2026-10-14',
  review_token: 'd'.repeat(32), can_write: true, business_DML: false })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onChanged.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'finance.payroll.view', 'finance.payroll.pay'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<PayrollKasbonPanel contractorId={contractor} payrollId={payroll} parentReady onChanged={onChanged}/>)); await settle(); expect(client.rpc).not.toHaveBeenCalled(); await click('Lihat kasbon mandor ini') }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === text); if (!b) throw new Error(`Missing ${text}: ${container.textContent}`); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function type(label: string, value: string, tag: 'input' | 'select' = 'input') {
  const el = container.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${label}"]`)!
  const proto = tag === 'input' ? HTMLInputElement.prototype : HTMLSelectElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event(tag === 'input' ? 'input' : 'change', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
describe('kasbon tunai (owner D14-6)', () => {
  it('gives a kasbon with an exact payload, refusing a future date first', async () => {
    const sent: Array<Record<string, unknown>> = []
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_kasbon_v1') return { data: workspace(), error: null }
      sent.push(args)
      return { data: { contract_version: 'cp7.kasbon-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'GIVE', request_id: args.p_request, contractor_id: contractor, advance: advance(), payroll: null }, error: null }
    })
    await mount(); expect(container.textContent).toContain('Mandor ini belum punya kasbon.')
    await click('Beri kasbon')
    await type('Nominal kasbon', '2500'); await type('Tanggal kasbon', '2026-10-15'); await type('Rekening kasbon', bank, 'select'); await type('Alasan kasbon', 'Kasbon anak sakit')
    expect(container.textContent).toContain('Tanggal kasbon tidak boleh di masa depan.')
    expect(button('Simpan kasbon').disabled).toBe(true)
    await type('Tanggal kasbon', '2026-10-13')
    await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Kasbon sudah diperiksa"]')!.click())
    await click('Simpan kasbon')
    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ p_action: 'GIVE', p_expected: 'd'.repeat(32), p_payload: { contractor_id: contractor, cash_account_id: bank, cash_review_token: 'c'.repeat(32),
      advance_date: '2026-10-13', amount: '2500.00', reason: 'Kasbon anak sakit' } })
    expect(container.textContent).toContain('Kasbon KB-20261014-ABC123 Rp2.500,00 tercatat.')
    expect(onChanged).toHaveBeenCalled()
  })
  it('keeps the saved message and the open panel while the payroll page reloads, and closes for another mandor', async () => {
    const other = '77777777-7777-4777-8777-777777777777'
    const render = (id: string | null, ready = true) => act(async () => root.render(<PayrollKasbonPanel contractorId={id} payrollId={id ? payroll : null} parentReady={ready} onChanged={onChanged}/>))
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => name === 'erp_cp7_get_kasbon_v1' ? { data: workspace(), error: null }
      : { data: { contract_version: 'cp7.kasbon-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'GIVE', request_id: args.p_request, contractor_id: contractor, advance: advance(), payroll: null }, error: null })
    await mount(); await click('Beri kasbon')
    await type('Nominal kasbon', '2500'); await type('Rekening kasbon', bank, 'select'); await type('Alasan kasbon', 'Kasbon anak sakit')
    await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Kasbon sudah diperiksa"]')!.click())
    await click('Simpan kasbon'); await settle()
    expect(onChanged).toHaveBeenCalled()
    // What onChanged does on the payroll page: its detail is emptied while it reloads (no contractor, parent not
    // ready), then the same payroll comes back.
    await render(null, false); await settle(); await render(contractor); await settle()
    expect(container.textContent).toContain('Kasbon KB-20261014-ABC123 Rp2.500,00 tercatat.')
    button('Muat ulang kasbon'); expect(container.textContent).toContain('Beri kasbon')
    await render(other); await settle()
    expect(container.textContent).not.toContain('tercatat'); button('Lihat kasbon mandor ini')
  })
  it('shows a refused kasbon as the server said when the payroll page re-reads during the refresh (no false refresh failure)', async () => {
    // CI 39020856920 (R3 guards case): the payroll page's reload made this panel start a newer read while the refresh read
    // was in flight; the superseded read was reported as "Refetch authoritative gagal; writer tetap terkunci".
    const refusal = 'Saldo BC1 menjadi minus -2500.00 pada tanggal buku 2026-10-13 atau sesudahnya (laporan kas harian).'
    let reads = 0
    client.rpc.mockImplementation(async (name: string) => {
      if (name === 'erp_cp7_get_kasbon_v1') { reads++; await new Promise(r => setTimeout(r, 5)); return { data: workspace(), error: null } }
      return { data: null, error: { code: 'P0001', message: refusal } }
    })
    const render = (ready: boolean) => root.render(<PayrollKasbonPanel contractorId={contractor} payrollId={payroll} parentReady={ready} onChanged={onChanged}/>)
    // What the payroll page does on onChanged: not ready while it reloads, ready again right after its read resolves.
    onChanged.mockImplementation(async () => { render(false); setTimeout(() => render(true), 0); return true })
    const wait = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)) })
    await mount(); await wait(20); await click('Beri kasbon')
    await type('Nominal kasbon', '2500'); await type('Rekening kasbon', bank, 'select'); await type('Alasan kasbon', 'Kasbon anak sakit')
    await act(async () => container.querySelector<HTMLInputElement>('[aria-label="Kasbon sudah diperiksa"]')!.click())
    await click('Simpan kasbon'); await wait(40)
    expect(onChanged).toHaveBeenCalled(); expect(reads).toBeGreaterThanOrEqual(3)
    const alert = [...container.querySelectorAll('[role="alert"]')].map(a => a.textContent).find(x => x?.includes('laporan kas harian'))
    expect(alert).toContain(refusal); expect(alert).not.toContain('Refetch authoritative gagal')
    expect(container.textContent).toContain('Beri kasbon')
  })
  it('prefills the deduction with what the kasbon and the payroll can take, and hides cancel once used', async () => {
    client.rpc.mockResolvedValue({ data: workspace([advance(), advance({ id: '55555555-5555-4555-8555-555555555555', number: 'KB-2', reserved: '100.00', free: '2400.00',
      allocations: [{ deduction_id: '66666666-6666-4666-8666-666666666666', payroll_id: payroll, payroll_number: 'PR-1', payroll_status: 'CALCULATED', amount: '100.00' }] })]), error: null })
    await mount()
    const labels = [...container.querySelectorAll('button')].map(b => b.textContent)
    expect(labels).toContain('Batalkan kasbon KB-20261014-ABC123'); expect(labels).not.toContain('Batalkan kasbon KB-2')
    await act(async () => [...container.querySelectorAll<HTMLButtonElement>('button')].filter(b => b.textContent === 'Potong dari payroll PR-1')[0].click()); await settle()
    expect(container.querySelector<HTMLInputElement>('[aria-label="Nominal kasbon"]')!.value).toBe('2500.00')
    await type('Nominal kasbon', '2500.01'); expect(container.textContent).toContain('Potongan melebihi sisa kasbon (Rp2.500,00).')
  })
  it('reads amounts as exact cents', () => {
    expect(kasbonCents('2500')).toBe(250000n); expect(kasbonCents('12,5')).toBe(1250n); expect(kasbonCents('1.234')).toBeNull(); expect(kasbonCents('-1')).toBeNull()
  })
})
