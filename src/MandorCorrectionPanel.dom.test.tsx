// @vitest-environment jsdom
import { act, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MandorCorrectionPanel from './MandorCorrectionPanel'
import { TransactionSourceProvider } from './TransactionSourceNavigation'
import { parseMandorCorrection } from './mandorCorrectionContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const old = '33333333-3333-4333-8333-333333333333', target = '44444444-4444-4444-8444-444444444444'
const pickup = '55555555-5555-4555-8555-555555555555', next = '66666666-6666-4666-8666-666666666666'
const onCommitted = vi.fn(async () => {})
const workspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.mandor-correction-workspace.v1',
  po_id: po, po_number: 'PO-9', contractor_id: old, contractors: [{ id: old, name: 'Mandor Lama' }, { id: target, name: 'Mandor Benar' }],
  group_count: 2, pickup_count: 1, blockers: [], eligible: true, review_token: 'e'.repeat(32), closed_through: null,
  after_step: 'Catat ulang hasil jahit dengan waktu fisik asli dan pilihan tarif; baru susun ulang nota.', business_DML: false,
  after_steps: [{ menu: 'Produksi › WIP & Sewing', step: 'Catat ulang hasil jahit untuk mandor yang benar.' },
    { menu: 'Produksi › Laundry', step: 'Bila laundry dibatalkan, kirim dan terima lagi.' },
    { menu: 'Keuangan › Payroll & Kasbon', step: 'Susun lagi nota/gaji untuk mandor yang benar.' }],
  history: [], ...extra })
const blocker = (extra: Record<string, unknown>) => ({ menu: null, source: null, ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...new Set([...recoveryIdentity.identity.permissions,
    'production.distribution.view', 'production.distribution.create', 'production.distribution.edit_draft', 'production.distribution.post',
    'production.wip.view', 'production.wip.post', 'production.wip.reverse'])] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: unknown, cb: (l: unknown) => Promise<unknown>) => cb({}) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function mount(groupId = group, version = 7) { await act(async () => root.render(<MandorCorrectionPanel groupId={groupId} groupVersion={version} parentReady onCommitted={onCommitted}/>)); await settle() }
function button(label: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === label); if (!b) throw new Error('Missing button '+label); return b }
async function click(label: string) { await act(async () => button(label).click()); await settle() }
function input(label: string) { return container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)! }
async function fill() {
  const select = container.querySelector<HTMLSelectElement>('[aria-label="Mandor yang benar"]')!
  await act(async () => { select.value = target; select.dispatchEvent(new Event('change', { bubbles: true })) })
  await act(async () => {
    const reason = input('Alasan koreksi mandor')
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(reason, 'Salah mandor diketahui sesudah jahit')
    reason.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await act(async () => input('Koreksi seluruh PO sudah diperiksa').click())
}
function serve(w = workspace(), post?: (args: Record<string, unknown>) => unknown) {
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_sewing_completion_v1') return { data: { contract_version: 'cp7.sewing-completion-workspace.v1', group_id: group, po_id: po }, error: null }
    if (name === 'erp_cp7_get_mandor_correction_v1') return { data: w, error: null }
    return post ? post(args) : { data: null, error: { code: 'P0001', message: 'Unexpected writer' } }
  })
}
function result(args: Record<string, unknown>, extra: Record<string, unknown> = {}) {
  return { data: { contract_version: 'cp7.mandor-correction-result.v1', po_id: po, po_number: 'PO-9',
    old_contractor_id: old, contractor_id: target, request_id: args.p_request, status: 'PICKUPS_REPLACED',
    sewing_repost_required: true, wage_history_reassigned: false, replacements: [{ group_id: group,
      old_pickup_id: pickup, new_pickup_id: next, picked_up_at: '2026-10-21T02:00:00Z', allocated_pieces: 10 }], ...extra }, error: null }
}
describe('koreksi mandor sesudah jahit', () => {
  it('does no read until opened and shows the PO-wide scope and real inverse guidance', async () => {
    serve(workspace({ eligible: false, blockers: [blocker({ order: 20, kind: 'PAYROLL', id: pickup, number: 'NOTA-9', step: 'Balik pembayaran dan nota melalui Nota/Gaji.' })] }))
    await mount(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Koreksi mandor sesudah jahit')
    expect(container.textContent).toContain('seluruh PO'); expect(container.textContent).toContain('NOTA-9')
    expect(container.textContent).toContain('Balik pembayaran dan nota')
    expect(button('Ganti pembagian ke mandor yang benar').disabled).toBe(true)
  })
  it('binds the reviewed target and UUID and keeps the required sewing/nota next step after refresh', async () => {
    serve(workspace(), result)
    await mount(); await click('Koreksi mandor sesudah jahit'); await fill(); await click('Ganti pembagian ke mandor yang benar')
    const call = client.rpc.mock.calls.find(c => c[0] === 'erp_cp7_correct_mandor_v1')!
    expect(call[1]).toMatchObject({ p_payload: { po_id: po, contractor_id: target, review_token: 'e'.repeat(32), change_reason: 'Salah mandor diketahui sesudah jahit' } })
    expect(onCommitted).toHaveBeenCalledTimes(1); await mount(group, 9)
    expect(container.textContent).toContain('Catat ulang hasil jahit')
    expect(container.textContent).toContain('Riwayat upah dan nota lama tetap tersimpan')
  })
  it('explains that existing FG use must be undone before a finished PO can reopen', async () => {
    serve(workspace({ eligible: false, blockers: [
      blocker({ order: 10, kind: 'PO_STATE', id: po, number: 'PO-9', status: 'FINISHED', step: 'Buka kembali PO selesai.' }),
      blocker({ order: 40, kind: 'FG_LOT', id: next, number: 'LOT-9', step: 'Balik pemakaian barang jadi lalu QC asalnya.' }),
    ] }))
    await mount(); await click('Koreksi mandor sesudah jahit')
    expect(container.textContent).toContain('melalui dokumen pemakaiannya sebelum membuka kembali PO')
    expect(button('Ganti pembagian ke mandor yang benar').disabled).toBe(true)
  })
  it('refuses a response bound to another PO without claiming success', async () => {
    serve(workspace(), args => result(args, { po_id: target }))
    await mount(); await click('Koreksi mandor sesudah jahit'); await fill(); await click('Ganti pembagian ke mandor yang benar')
    expect(onCommitted).not.toHaveBeenCalled(); expect(container.textContent).not.toContain('pembagian diganti ke mandor yang benar')
  })
  it('hands the next sewing step to the page before the loading refresh unmounts the panel', async () => {
    serve(workspace(), result)
    function Page() {
      const [version, setVersion] = useState(0), [notice, setNotice] = useState('')
      return <><p role="status" aria-label="Hasil koreksi PO">{notice}</p><MandorCorrectionPanel key={version} groupId={group} groupVersion={7} parentReady
        onCommitted={async message => { setNotice(message); setVersion(v => v + 1) }}/></>
    }
    await act(async () => root.render(<Page/>)); await settle()
    await click('Koreksi mandor sesudah jahit'); await fill(); await click('Ganti pembagian ke mandor yang benar')
    expect(container.querySelector('[aria-label="Hasil koreksi PO"]')?.textContent).toContain('Catat ulang hasil jahit')
    expect(container.querySelector('[aria-label="Hasil koreksi PO"]')?.textContent).toContain('Riwayat upah dan nota lama tetap tersimpan')
    expect(button('Koreksi mandor sesudah jahit')).toBeTruthy()
  })
  it('cancels the confirmation as soon as the target changes', async () => {
    serve(); await mount(); await click('Koreksi mandor sesudah jahit'); await fill()
    expect(button('Ganti pembagian ke mandor yang benar').disabled).toBe(false)
    const select = container.querySelector<HTMLSelectElement>('[aria-label="Mandor yang benar"]')!
    await act(async () => { select.value = ''; select.dispatchEvent(new Event('change', { bubbles: true })) })
    expect(input('Koreksi seluruh PO sudah diperiksa').checked).toBe(false)
    expect(button('Ganti pembagian ke mandor yang benar').disabled).toBe(true)
  })
  it('drops a late source response after the selected group changes', async () => {
    let resolve!: (v: unknown) => void
    client.rpc.mockReturnValue(new Promise(r => { resolve = r }))
    await mount(); await click('Koreksi mandor sesudah jahit'); await mount(target)
    await act(async () => resolve({ data: { contract_version: 'cp7.sewing-completion-workspace.v1', group_id: group, po_id: po }, error: null }))
    expect(client.rpc).toHaveBeenCalledTimes(1); expect(container.textContent).not.toContain('PO-9')
  })
  it('shows a stale-review refusal as an actionable message and clears the old facts', async () => {
    let stale = false
    serve(workspace(), () => { stale = true; return { data: null, error: { code: 'P0001', message: 'CP7_MANDOR_CORRECTION_STALE_REVIEW' } } })
    const original = client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => stale && name === 'erp_cp7_get_mandor_correction_v1'
      ? { data: workspace({ eligible: false, blockers: [blocker({ order: 20, kind: 'WORK', id: pickup, step: 'Balik hasil kerja yang baru muncul.' })] }), error: null }
      : original(name, args))
    await mount(); await click('Koreksi mandor sesudah jahit'); await fill(); await click('Ganti pembagian ke mandor yang benar')
    expect(onCommitted).not.toHaveBeenCalled(); expect(container.textContent).toContain('Dokumen PO atau data mandor berubah')
    expect(container.textContent).toContain('Balik hasil kerja yang baru muncul')
    expect(button('Ganti pembagian ke mandor yang benar').disabled).toBe(true)
  })

  it('names the real menu, opens the blocking document through the source reader, and lists every redo step', async () => {
    const actor = '77777777-7777-4777-8777-777777777777', current = auth.current as typeof recoveryIdentity
    auth.current = { ...current, identity: { ...current.identity, profile: { ...current.identity.profile, authUserId: actor } } }
    serve(workspace({ eligible: false, blockers: [blocker({ order: 20, kind: 'PAYROLL', id: pickup, number: 'NOTA-9', status: 'APPROVED',
      step: 'Batalkan nota/gaji ini di Keuangan › Payroll & Kasbon (tombol Batalkan payroll).', menu: 'Keuangan › Payroll & Kasbon',
      source: { source_type: 'PAYROLL_PAYMENT', source_id: pickup } })] }), args => ({ data: { contract_version: 'cp7.transaction-source.v1',
      actor_scope_id: actor, source: args.p_source, status: 'AVAILABLE', document: { domain: 'PAYROLL', route: 'finance-payroll', id: pickup,
      number: 'NOTA-9', status: 'APPROVED', revision: '3', focus: null }, read_at: '2026-10-23T03:00:00Z', business_DML: false }, error: null }))
    const navigate = vi.fn()
    await act(async () => root.render(<TransactionSourceProvider scope="AUTH:1" onNavigate={navigate}><MandorCorrectionPanel groupId={group} groupVersion={7} parentReady onCommitted={onCommitted}/></TransactionSourceProvider>))
    await settle(); await click('Koreksi mandor sesudah jahit')
    expect(container.textContent).toContain('Keuangan › Payroll & Kasbon'); expect(container.textContent).not.toContain('Nota/Gaji')
    await click('Buka NOTA-9')
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_resolve_transaction_source_v1', { p_source: { source_type: 'PAYROLL_PAYMENT', source_id: pickup } })
    expect(navigate).toHaveBeenCalledExactlyOnceWith('finance-payroll')
    const steps = container.querySelector('[aria-label="Langkah sesudah koreksi mandor"]')!
    expect([...steps.querySelectorAll('li strong')].map(x => x.textContent)).toEqual(['Produksi › WIP & Sewing', 'Produksi › Laundry', 'Keuangan › Payroll & Kasbon'])
  })
  it('shows who corrected the Mandor, when, from whom to whom and why, newest first', async () => {
    serve(workspace({ history: [
      { generation_no: 8, recorded_at: '2026-10-22T03:15:00Z', actor_name: 'Bu Owner', old_contractor_id: target, old_contractor_name: 'Mandor Benar',
        new_contractor_id: old, new_contractor_name: 'Mandor Lama', reason: 'Dikembalikan setelah cek nota', pickup_count: 2 },
      { generation_no: 5, recorded_at: '2026-10-21T03:15:00Z', actor_name: null, old_contractor_id: old, old_contractor_name: 'Mandor Lama',
        new_contractor_id: target, new_contractor_name: 'Mandor Benar', reason: 'Salah mandor sesudah jahit', pickup_count: 2 }] }))
    await mount(); await click('Koreksi mandor sesudah jahit')
    const rows = [...container.querySelectorAll('[aria-label="Riwayat koreksi mandor PO ini"] li')].map(x => x.textContent ?? '')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toContain('Mandor Benar → Mandor Lama'); expect(rows[0]).toContain('Bu Owner'); expect(rows[0]).toContain('Dikembalikan setelah cek nota')
    expect(rows[0]).toContain('WIB'); expect(rows[1]).toContain('akun yang sudah tidak terdaftar')
  })
  it('says plainly when the PO was never corrected and puts the redo menus in the outcome', async () => {
    serve(workspace(), result)
    await mount(); await click('Koreksi mandor sesudah jahit')
    expect(container.textContent).toContain('PO ini belum pernah dikoreksi mandornya.')
    await fill(); await click('Ganti pembagian ke mandor yang benar')
    expect(container.textContent).toContain('Produksi › WIP & Sewing'); expect(container.textContent).toContain('Produksi › Laundry; Keuangan › Payroll & Kasbon')
    expect(container.textContent).not.toContain('WIP & Jahit')
  })
  it.each([
    ['a blocker without menu/source', workspace({ eligible: false, blockers: [{ order: 1, kind: 'QC', id: pickup, step: 'Batalkan finalisasi QC ini.' }] })],
    ['a menu outside the sidebar form', workspace({ eligible: false, blockers: [blocker({ order: 1, kind: 'QC', id: pickup, step: 'x', menu: 'layar QC' })] })],
    ['a source with extra keys', workspace({ eligible: false, blockers: [blocker({ order: 1, kind: 'QC', id: pickup, step: 'x', source: { source_type: 'QC_INSPECTION', source_id: pickup, x: 1 } })] })],
    ['missing after steps', workspace({ after_steps: [] })],
    ['history out of order', workspace({ history: [1, 2].map(n => ({ generation_no: n, recorded_at: '2026-10-21T03:15:00Z', actor_name: null,
      old_contractor_id: old, old_contractor_name: 'A', new_contractor_id: target, new_contractor_name: 'B', reason: 'alasan', pickup_count: 1 })) })],
  ])('refuses %s', (_label, value) => { expect(() => parseMandorCorrection(value, po)).toThrow() })
})
