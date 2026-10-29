// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './ConnectedAccessoryStandardReportPage'
import type { AccessoryReportQuery } from './accessoryStandardReport'
import { asrId, asrParts, asrWorkspace } from '../tests/fixtures/accessoryStandardReport'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
type Row = Record<string, unknown>
function identity(perms = ['finance.contractor_accessory.view', 'finance.hpp.view'], role = 'OWNER') {
  return { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, role, rowVersion: 1, roleRowVersion: 1 }, permissions: perms } }
}
function query(a: Row): AccessoryReportQuery { return { period_start: a.p_start as string, period_end: a.p_end as string, contractor_id: a.p_contractor as string | null,
  po_id: a.p_po as string | null, q: a.p_query as string, offset: a.p_offset as number, limit: a.p_limit as number } }
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-10-16T06:00:00Z'))
  auth.current = identity(); client.rpc.mockReset()
  client.rpc.mockImplementation(async (_name: string, a: Row) => ({ data: asrWorkspace(query(a)), error: null }))
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount(refresh = 0) { await act(async () => root.render(<Page refresh={refresh}/>)); await settle() }
function button(text: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === text); if (!b) throw new Error('Missing '+text); return b }
async function click(text: string) { await act(async () => button(text).click()); await settle() }
async function type(label: string, value: string) {
  const el = container.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${label}"]`)!
  const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) }); await settle()
}
const result = () => container.querySelector('[aria-label="Hasil laporan aksesori"]')

describe('S05 standalone read UI', () => {
  it('requires one mandor, states both WIB cohorts and shows exact source trace and zero reimbursement', async () => {
    await mount(); expect(result()).toBeNull(); expect(container.textContent).toContain('Pilih satu mandor')
    await click('Mandor Satu')
    expect(container.textContent).toContain('Kedua tanggal mengikuti WIB')
    expect(container.textContent).toContain('7 PCS'); expect(container.textContent).toContain('5 PCS'); expect(container.textContent).toContain('2 PCS')
    expect(container.textContent).toContain('Rp22,75'); expect(container.textContent).toContain('Rp7,5'); expect(container.textContent).toContain('Nol, tidak memerlukan hak penggantian')
    expect(container.textContent).toContain('Kancing biru 18'); expect(container.textContent).toContain(asrId(24)); expect(container.textContent).toContain('9007199254740993')
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_cp7_get_accessory_standard_report_v1')).toBe(true)
    expect(container.querySelector('button[type="submit"]')?.textContent).toBe('Muat laporan')
  })
  it('passes a single selected PO to both cohorts and excludes issues without PO there', async () => {
    await mount(); await click('Mandor Satu'); expect(container.textContent).toContain('1 detail pengambilan belum terhubung')
    await type('PO laporan aksesori', asrId(3))
    expect(client.rpc.mock.calls.at(-1)?.[1]).toMatchObject({ p_contractor: asrId(1), p_po: asrId(3) })
    expect(container.textContent).toContain('−5 PCS'); expect(container.textContent).not.toContain('AMBIL-7')
  })
  it('retires figures immediately when dates change, rejects impossible/oversize dates and refreshes the active filter', async () => {
    await mount(); await click('Mandor Satu'); expect(result()).not.toBeNull()
    await type('Mulai periode aksesori', '2026-10-17'); expect(result()).toBeNull(); expect(button('Muat laporan').disabled).toBe(true)
    const count = client.rpc.mock.calls.length; await mount(1); expect(client.rpc.mock.calls).toHaveLength(count)
    await type('Mulai periode aksesori', '2026-10-16'); await mount(2)
    expect(client.rpc.mock.calls.at(-1)?.[1]).toMatchObject({ p_start: '2026-10-16', p_end: '2026-10-16' }); expect(result()).not.toBeNull()
    await type('Mulai periode aksesori', '2024-01-01'); expect(result()).toBeNull(); expect(button('Muat laporan').disabled).toBe(true)
  })
  it('discards an older pending report after a filter change and after unmount', async () => {
    await mount(); let resolve!: (x: unknown) => void
    client.rpc.mockImplementationOnce((_n: string, a: Row) => new Promise(r => { resolve = () => r({ data: asrWorkspace(query(a)), error: null }) }))
    await click('Mandor Satu'); expect(result()).toBeNull()
    await type('Cari mandor laporan', 'baru'); await act(async () => resolve(null)); await settle()
    expect(result()).toBeNull(); expect(container.textContent).not.toContain('Rp22,75')
    await act(async () => root.unmount()); root = createRoot(container); await mount(); expect(result()).toBeNull()
  })
  it('removes data on 403 and on live identity/permission changes without another business call', async () => {
    await mount(); await click('Mandor Satu'); expect(result()).not.toBeNull()
    client.rpc.mockResolvedValueOnce({ data: null, error: { code: '42501', message: 'CP7_ACCESSORY_REPORT_ACCESS_CHANGED' } })
    await click('Muat laporan'); expect(result()).toBeNull(); expect(container.textContent).toContain('Hak akses laporan sudah berubah')
    auth.current = identity(['finance.contractor_accessory.view']); const count = client.rpc.mock.calls.length; await mount()
    expect(container.textContent).toContain('Laporan ini memerlukan'); expect(result()).toBeNull(); expect(client.rpc.mock.calls).toHaveLength(count)
    auth.current = identity(['finance.contractor_accessory.view', 'finance.hpp.view'], 'STAFF'); await mount(); expect(result()).toBeNull()
  })
  it('ignores an old authorized response after the identity loses the report right', async () => {
    await mount(); let resolve!: () => void
    client.rpc.mockImplementationOnce((_n: string, a: Row) => new Promise(r => { resolve = () => r({ data: asrWorkspace(query(a)), error: null }) }))
    await click('Mandor Satu'); auth.current = identity(['finance.contractor_accessory.view']); await mount()
    await act(async () => resolve()); await settle()
    expect(result()).toBeNull(); expect(container.textContent).not.toContain('Rp22,75'); expect(container.textContent).toContain('Laporan ini memerlukan')
  })
  it('shows UNKNOWN with no numeric difference when standard or units are incomplete', async () => {
    client.rpc.mockImplementation(async (_n: string, a: Row) => {
      const value = asrWorkspace(query(a))
      if (value.report) {
        const p = asrParts(value); Object.assign(p.standard, { unit_known: false, unit: null, unit_reference: 'LUSIN' })
        Object.assign(p.row, { comparison_status: 'UNKNOWN', reasons: ['HISTORICAL_UNIT_UNKNOWN'], unit: null, delta_qty: null }); p.report.status = 'UNKNOWN'
      }
      return { data: value, error: null }
    })
    await mount(); await click('Mandor Satu'); const text = result()?.textContent
    expect(text).toContain('Perbandingan belum lengkap'); expect(text).toContain('Satuan historis belum terbukti'); expect(text).toContain('Belum diketahui'); expect(text).not.toContain('2 PCS')
  })
  it('fails closed for a partial source answer and a lost reply; repeated reads only use the read endpoint', async () => {
    await mount(); client.rpc.mockImplementationOnce(async (_n: string, a: Row) => { const value = asrWorkspace(query(a)); asrParts(value).counts.issue_items = 2; return { data: value, error: null } })
    await click('Mandor Satu'); expect(result()).toBeNull(); expect(container.textContent).toContain('Data laporan aksesori tidak lengkap')
    client.rpc.mockRejectedValueOnce(new Error('Jaringan terputus')); await click('Muat laporan'); expect(result()).toBeNull()
    await click('Muat laporan'); expect(result()).not.toBeNull(); expect(client.rpc.mock.calls.every(([n]) => n === 'erp_cp7_get_accessory_standard_report_v1')).toBe(true)
  })
})
