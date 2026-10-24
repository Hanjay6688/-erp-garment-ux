// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedCuttingPage from './ConnectedCuttingPage'
import { cuttingSelectorFixture, recoveryIdentity, recoveryPatterns } from '../tests/fixtures/productionRecovery'
import {persistProductionEnvelope,readProductionRecovery} from './productionRecovery'

// Owner D15-6 (SOL-R1-002): Buat Potongan makes its PO when the cutting is posted; a draft makes nothing.
const authState = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => authState.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))

const model = '7a000000-0000-4000-8000-000000000001', small = '7b000000-0000-4000-8000-000000000001', large = '7b000000-0000-4000-8000-000000000002'
const draftId = '7c000000-0000-4000-8000-000000000001', po = '7d000000-0000-4000-8000-000000000001', group = '7e000000-0000-4000-8000-000000000001'
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); authState.current = recoveryIdentity
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: n, mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
function button(label: string, within: ParentNode = container) {
  const found = [...within.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.includes(label) || b.getAttribute('aria-label') === label)
  if (!found) throw new Error(`Button ${label} absent: ${within.textContent?.slice(-800)}`)
  return found
}
async function click(label: string, within: ParentNode = container) { await act(async () => button(label, within).click()); await settle() }
async function until(check: () => boolean) { for (let i = 0; i < 40 && !check(); i++) await act(async () => { await new Promise(r => setTimeout(r, 25)) }); expect(check()).toBe(true) }
async function setValue(el: HTMLInputElement | HTMLSelectElement, raw: string) {
  await act(async () => {
    const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, raw)
    el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true }))
  }); await settle()
}
const autoWorkspace = (extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.cutting-auto-po-workspace.v1', today: '2026-10-16', can_draft: true, can_post: true,
  models: { total: 1, offset: 0, query: '', rows: [{ id: model, code: 'MDL-AUTO', name: 'Model Otomatis', sizes: [{ id: small, code: '31' }, { id: large, code: '32' }] }] },
  drafts: [], selected_draft: null, business_DML: false, ...extra })
function server(answer: (args: Record<string, unknown>) => unknown) {
  const sent: Record<string, unknown>[] = []
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_list_patterns_v1') return { data: recoveryPatterns, error: null }
    if (name === 'erp_get_cutting_workspace_v2') return { data: cuttingSelectorFixture(args), error: null }
    if (name === 'erp_cp7_get_cutting_auto_po_v1') return { data: autoWorkspace(), error: null }
    if (name === 'erp_cp7_save_cutting_auto_po_v1') { sent.push(args); return { data: answer(args), error: null } }
    if (name.startsWith('erp_cp7_get_')) return { data: null, error: { message: 'not used here' } }
    throw new Error('Unexpected RPC ' + name)
  })
  return sent
}
async function fillCutting() {
  await act(async () => root.render(<ConnectedCuttingPage/>)); await settle()
  expect(container.querySelector<HTMLInputElement>('fieldset.ccut-po-mode input[type="radio"]')!.checked).toBe(true)
  expect(container.textContent).toContain('Nomor PO dibuat otomatis saat potongan disahkan')
  await setValue(container.querySelector<HTMLSelectElement>('select[aria-label="Model potongan"]')!, model)
  expect([...container.querySelectorAll('.ccut-size-list button')].map(b => b.textContent)).toEqual(['31', '32'])
  await until(() => Boolean(container.querySelector('[aria-label="Pola aktif"] button')))
  await click('REG · R1', container.querySelector('[aria-label="Pola aktif"]')!)
  await click('R-1', container.querySelector('.ccut-roll-catalog')!)
  await setValue(container.querySelector<HTMLInputElement>('input[aria-label="R-1 terpakai"]')!, '18')
  await setValue(container.querySelector<HTMLInputElement>('input[aria-label="R-1 Size 31"]')!, '5')
  await setValue(container.querySelector<HTMLInputElement>('input[aria-label="R-1 Size 32"]')!, '4')
}

it('keeps the suggestion recovery entry readable while a staged checked SAVE locks all production writers',async()=>{
 const auth=structuredClone(recoveryIdentity)
 Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST'})
 auth.identity.permissions.push('master.product.view','warehouse.stock.view','sales.invoice.view','production.cutting.view')
 authState.current=auth
 const content={action:'SAVE_DRAFT',payload:{cutting_save_contract:'cp7.cutting-checked-save.v1'},expectedVersion:null}
 const pending={...content,fingerprint:JSON.stringify(content),id:'4a000000-0000-4000-8000-000000000001',createdAt:'2026-10-24T00:00:00Z'}
 persistProductionEnvelope('disposable:actor-1','PLAN_APPLY_STAGED',pending)
 server(()=>{throw Error('No production write is permitted while the earlier result is uncertain')})
 await act(async()=>root.render(<ConnectedCuttingPage/>));await settle()
 const from=container.querySelector<HTMLInputElement>('[aria-label="Penjualan mulai untuk saran potong"]')!
 const through=container.querySelector<HTMLInputElement>('[aria-label="Penjualan sampai untuk saran potong"]')!
 expect(from.disabled).toBe(false);expect(through.disabled).toBe(false)
 await setValue(from,'2026-09-01');await setValue(through,'2026-09-30')
 expect(button('Buka saran potong').disabled).toBe(false)
 expect(button('Sahkan & buat PO').disabled).toBe(true)
 expect(readProductionRecovery('disposable:actor-1').pending.PLAN_APPLY_STAGED).toEqual(pending)
 expect(client.rpc.mock.calls.some(([name])=>name.startsWith('erp_save_')||name.startsWith('erp_cp7_save_'))).toBe(false)
})

describe('Buat Potongan with the PO made automatically (owner D15-6)', () => {
  it('posts the cutting and creates its PO in one request, then names the new PO', async () => {
    const sent = server(args => ({ contract_version: 'cp7.cutting-auto-po-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'POST', request_id: args.p_request,
      draft_id: null, po_id: po, po_number: 'PO-261016-001', cutting_group_id: group, group_number: 'POT-261016-AB12CD34', total_pieces: 9, material_issue_posted: true }))
    await fillCutting()
    expect(button('Sahkan & buat PO').disabled).toBe(false)
    await click('Sahkan & buat PO')
    expect(sent).toHaveLength(1)
    const body = sent[0].p_payload as Record<string, unknown>
    expect(body).toMatchObject({ action: 'POST', draft_id: null, expected_version: null, model_id: model, change_reason: 'Posting Potongan dengan PO otomatis dari workspace connected' })
    expect(body).not.toHaveProperty('po_id')
    expect(body.cutting).toMatchObject({ pattern_id: 'pattern-1', source_location_id: 'loc-1', notes: null,
      size_slots: [{ slot_no: 1, size_id: small, drawing_no: 1 }, { slot_no: 2, size_id: large, drawing_no: 1 }],
      rolls: [{ roll_id: 'roll-1', qty_issued: 20, qty_consumed: 18, qty_reported_remaining: 2, yields: [{ slot_no: 1, qty_pcs: 5 }, { slot_no: 2, qty_pcs: 4 }] }] })
    expect(Object.keys(body.cutting as object).sort()).toEqual(['cut_at', 'notes', 'pattern_id', 'rolls', 'size_slots', 'source_location_id'])
    expect(client.rpc.mock.calls.some(([name]) => name === 'erp_save_cutting_group_before_sewing_v2')).toBe(false)
    expect(container.textContent).toContain('PO-261016-001 dibuat otomatis; POT-261016-AB12CD34 terposting (9 pcs).')
  })

  it('keeps a draft without making a PO, and refuses an answer for another request', async () => {
    let wrong = false
    const sent = server(args => wrong ? { contract_version: 'cp7.cutting-auto-po-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'SAVE_DRAFT', request_id: draftId, draft_id: draftId, row_version: 1 }
      : { contract_version: 'cp7.cutting-auto-po-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'SAVE_DRAFT', request_id: args.p_request, draft_id: draftId, row_version: 1 })
    await fillCutting()
    await click('Simpan draft')
    expect(sent).toHaveLength(1)
    expect(sent[0].p_payload).toMatchObject({ action: 'SAVE_DRAFT', draft_id: null, expected_version: null, model_id: model })
    expect(sent[0].p_payload).not.toHaveProperty('change_reason')
    expect(container.textContent).toContain('Draf PO otomatis tersimpan. Belum ada PO, stok, atau jurnal yang berubah.')
    wrong = true
    await fillCutting()
    await click('Simpan draft')
    expect(sent).toHaveLength(2)
    expect(container.textContent).toContain('Respons sukses tidak membawa UUID/action yang cocok dengan kontrak transaksi.')
    expect(button('Simpan draft').disabled).toBe(true)
    expect(container.textContent).not.toContain('PO-26')
  })

  it('cannot post without a model, and the existing-PO mode still posts through the Native writer only', async () => {
    server(() => null)
    await act(async () => root.render(<ConnectedCuttingPage/>)); await settle()
    expect(button('Sahkan & buat PO').disabled).toBe(true)
    await act(async () => container.querySelectorAll<HTMLInputElement>('fieldset.ccut-po-mode input[type="radio"]')[1].click()); await settle()
    expect(container.textContent).not.toContain('Sahkan & buat PO')
    expect(button('Post ke WIP Potongan')).toBeTruthy()
    expect(container.querySelector('select[aria-label="Model potongan"]')).toBeNull()
  })
})
