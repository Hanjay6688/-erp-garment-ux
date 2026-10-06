// @vitest-environment jsdom
// RPC stand-ins exercise the real parent/child recovery hooks. Native acceptance is separate.
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedLaundryPage from './ConnectedLaundryPage'
import { LAU_POLICY_KEYS } from './laundryBd'
import { readProductionRecovery } from './productionRecovery'
import { laundryQcInputFixture } from '../tests/fixtures/laundryQcInput'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'

const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const scope = `${recoveryRuntime.projectRef}:${id(100)}`
const prices = () => ({
  pagination: { as_of: '2026-10-06T00:00:00Z', invoice_next: null, receipt_next: null },
  money_visible: true, can_manage_master: true, can_set_price: true, is_owner: true,
  policies: LAU_POLICY_KEYS.map(key => ({ key, status: 'PENDING_POLICY_VALUE', value: null,
    version: '1', set_at: '2026-10-06T07:00:00', reason: 'Synthetic pending policy' })),
  vendors: [{ id: id(1), code: 'LDR-A', name: 'Laundry A', pricing_mode: 'COMPONENTS', pricing_unit: 'PCS',
    minimum_charge: null, terms_version: '1', bd_priced: true }],
  processes: [{ id: id(2), code: 'WASH', name: 'Cuci' }],
  components: [{ id: id(30), vendor_id: id(1), code: 'SPRAY', name: 'Spray', is_active: true,
    current: { status: 'UNKNOWN', rate: null, from: '2026-10-06T07:00:00', reason: 'Synthetic unknown price', version_id: id(31) } }],
  packages: [], process_rates: [], scoped_rates: [], priced_deliveries: [], opening_uninvoiced: [],
  invoices: [], billable_receipts: [], accounts: [], payables: null, pending_cost: { goods: [], sales: [] },
})
const ok = (data: unknown) => ({ data, error: null })
const parentResult = () => ok(laundryQcInputFixture('LAUNDRY'))
const accepted = (args: { p_action: string; p_client_request_id: string }) => ok({
  action: args.p_action, request_id: args.p_client_request_id, status: 'SAVED', rate_id: id(32),
})
let root: Root, box: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.rpc.mockReset()
  mock.auth = { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED',
    profile: { id: id(100), authUserId: id(101), rowVersion: 1, roleRowVersion: 1, role: 'OWNER', roleName: 'Owner', isActive: true },
    permissions: ['production.laundry.view', 'production.laundry.create', 'production.laundry.post', 'production.laundry.reverse', 'master.partners.manage'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true,
    value: { request: vi.fn(async (name, _options, run) => run({ name, mode: 'exclusive' })) } })
  mock.rpc.mockImplementation((name, args) => {
    if (name === 'erp_get_laundry_qc_workspace_v1') return Promise.resolve(parentResult())
    if (name === 'erp_get_laundry_bd_workspace_v1') return Promise.resolve(ok(prices()))
    if (name === 'erp_save_laundry_bd_action_v1') return Promise.resolve(accepted(args))
    throw Error('Unexpected RPC: ' + name)
  })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const settle = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
const button = (name: string) => {
  const matches = [...box.querySelectorAll<HTMLButtonElement>('button')].filter(e => e.textContent?.trim() === name)
  expect(matches).toHaveLength(1); return matches[0]
}
const select = (label: string) => box.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`)
async function click(name: string) { await act(async () => button(name).click()); await settle() }
async function change(label: string, value: string) {
  const e = box.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${label}"]`)!
  expect(e).not.toBeNull()
  await act(async () => { const proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value)
    e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) })
  await settle()
}
async function openMaster() {
  await import('./LaundryBdPanel')
  await act(async () => root.render(<ConnectedLaundryPage/>)); await settle(); await click('Harga & tagihan')
  await act(async () => { await vi.waitFor(() => expect(select('Vendor harga laundry')).not.toBeNull()) })
  await change('Vendor harga laundry', id(1)); await click('Kirim & rincian biaya')
  expect(select('Pilihan rincian biaya')).not.toBeNull()
  await click('Harga vendor'); await change('Alasan', 'Harga gratis disetujui untuk komponen ini')
  await change('Berlaku sejak (WIB)', '2026-10-06T07:00'); await change('Komponen harga', id(30))
  await change('Status harga komponen', 'FREE')
  expect(button('Simpan versi harga komponen').disabled).toBe(false)
}
const parentReads = () => mock.rpc.mock.calls.filter(([name]) => name === 'erp_get_laundry_qc_workspace_v1').length

describe('Laundry pricing refreshes the owning batch source after a definite result', () => {
  it('requests a new parent source only after clearing recovery, and waits for it before restoring priced send', async () => {
    await openMaster(); const before = parentReads()
    let complete!: (result: ReturnType<typeof parentResult>) => void
    const pendingParent = new Promise<ReturnType<typeof parentResult>>(resolve => { complete = resolve })
    mock.rpc.mockImplementation((name, args) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') {
        expect(readProductionRecovery(scope).pending.LAUNDRY_BD).toBeUndefined()
        return pendingParent
      }
      if (name === 'erp_get_laundry_bd_workspace_v1') return Promise.resolve(ok(prices()))
      if (name === 'erp_save_laundry_bd_action_v1') return Promise.resolve(accepted(args))
      throw Error('Unexpected RPC: ' + name)
    })
    await click('Simpan versi harga komponen'); expect(parentReads()).toBe(before + 1)
    await click('Kirim & rincian biaya'); expect(select('Pilihan rincian biaya')).toBeNull()
    expect(box.textContent).toContain('Data Laundry (batch siap kirim) belum terbaca')
    await act(async () => complete(parentResult())); await settle()
    expect(select('Pilihan rincian biaya')).not.toBeNull()
    expect(select('Pilihan rincian biaya')!.disabled).toBe(false)
    expect(mock.rpc.mock.calls.filter(([name]) => name.startsWith('erp_save_'))).toHaveLength(1)
  })

  it('does not resurrect the old batch if the new parent read is denied', async () => {
    await openMaster(); const before = parentReads()
    mock.rpc.mockImplementation((name, args) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return Promise.resolve({ data: null, error: { code: '42501', message: 'current batch permission denied' } })
      if (name === 'erp_get_laundry_bd_workspace_v1') return Promise.resolve(ok(prices()))
      if (name === 'erp_save_laundry_bd_action_v1') return Promise.resolve(accepted(args))
      throw Error('Unexpected RPC: ' + name)
    })
    await click('Simpan versi harga komponen'); expect(parentReads()).toBe(before + 1)
    await click('Kirim & rincian biaya'); expect(select('Pilihan rincian biaya')).toBeNull()
    expect(box.textContent).toContain('Akun tidak memiliki izin untuk operasi ini.')
    expect(box.querySelectorAll('[data-kpi-state="UNKNOWN"]')).toHaveLength(4)
    expect(readProductionRecovery(scope).pending.LAUNDRY_BD).toBeUndefined()
  })

  it('preserves a lost reply and exact UUID/payload until reconciliation, then refreshes the parent', async () => {
    await openMaster(); const before = parentReads(); let first = true
    mock.rpc.mockImplementation((name, args) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return Promise.resolve(parentResult())
      if (name === 'erp_get_laundry_bd_workspace_v1') return Promise.resolve(ok(prices()))
      if (name === 'erp_save_laundry_bd_action_v1') {
        if (first) { first = false; return Promise.reject(Error('reply dropped after commit')) }
        return Promise.resolve(accepted(args))
      }
      throw Error('Unexpected RPC: ' + name)
    })
    await click('Simpan versi harga komponen'); expect(parentReads()).toBe(before)
    const saved = readProductionRecovery(scope).pending.LAUNDRY_BD
    expect(saved?.action).toBe('SAVE_COMPONENT_RATE'); expect(button('Simpan versi harga komponen').disabled).toBe(true)
    await click('Kirim & rincian biaya'); expect(select('Pilihan rincian biaya')).toBeNull()
    await click('Reconcile transaksi'); expect(parentReads()).toBe(before + 1)
    const writes = mock.rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_bd_action_v1')
    expect(writes).toHaveLength(2); expect(writes[1][1]).toEqual(writes[0][1])
    expect(writes[1][1].p_client_request_id).toBe(saved!.id)
    expect(readProductionRecovery(scope).pending.LAUNDRY_BD).toBeUndefined()
    expect(select('Pilihan rincian biaya')).not.toBeNull()
    expect(select('Pilihan rincian biaya')!.disabled).toBe(false)
  })
})
