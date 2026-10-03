// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedCuttingPage from './ConnectedCuttingPage'
import ConnectedPickupPage from './ConnectedPickupPage'
import ConnectedWipStatusPage from './ConnectedWipStatusPage'
import { productionKey, readProductionRecovery } from './productionRecovery'
import { cuttingCommit, cuttingSelectorFixture, pickupCommit, pickupFixture, recoveryIdentity, recoveryPatterns, wipFixture } from '../tests/fixtures/productionRecovery'

const authState = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => authState.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))

let root: Root
let container: HTMLDivElement
const scope = 'disposable:actor-1'
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); authState.current = recoveryIdentity
  const held = new Set<string>()
  Object.defineProperty(navigator, 'locks', { configurable: true, value: {
    request: async (name: string, _options: LockOptions, callback: (lock: Lock | null) => Promise<unknown>) => {
      if (held.has(name)) return callback(null)
      held.add(name)
      try { return await callback({ name, mode: 'exclusive' } as Lock) } finally { held.delete(name) }
    },
  } })
  vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks()
})
async function settle() { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)) }) }
function button(label: string, within: ParentNode = container) {
  const found = [...within.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.includes(label))
  if (!found) throw new Error(`Button ${label} absent: ${within.textContent?.slice(-1500)}`)
  return found
}
async function click(label: string, within: ParentNode = container) { await act(async () => button(label, within).click()); await settle() }
async function fill(input: HTMLInputElement, raw: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, raw)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })
}
function server() {
  const state = { failRead: false, loseReply: false, wrongReceipt: false, replayRejection: false, committed: false, effects: 0, selectorVersion: 1, hideSelectors: false, missingDraft: false }
  const saved = new Map<string, unknown>()
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_list_patterns_v1') return { data: recoveryPatterns, error: null }
    if (name.startsWith('erp_get_')) {
      if (state.failRead && state.committed) return { data: null, error: { message: 'Refetch failed' } }
      if (name === 'erp_get_cutting_workspace_v2') {
        const data = cuttingSelectorFixture(args)
        data.drafts[0].row_version = state.selectorVersion
        data.drafts[0].notes = state.selectorVersion > 1 ? 'Current server draft' : null
        if (state.hideSelectors) { data.orders = []; data.order_page.total = 0; data.drafts = []; data.draft_page.total = 0 }
        if (state.missingDraft) { data.drafts = []; data.draft_page.total = 0; data.selected_draft = null }
        return { data, error: null }
      }
      if (name === 'erp_get_cutting_pickup_queue_v1') return { data: pickupFixture(), error: null }
    }
    const payload = args.p_payload as Record<string, unknown>
    const id = String(args.p_client_request_id)
    if (!saved.has(id)) {
      saved.set(id, name === 'erp_save_cutting_pickup_v1' ? pickupCommit(String(payload.action)) : cuttingCommit(String(payload.action)))
      state.effects += 1; state.committed = true
    } else if (state.replayRejection) return { data: null, error: { code: '42501', message: 'Role changed since original request' } }
    if (state.loseReply) return { data: null, error: { status: 503, message: 'Gateway response unavailable' } }
    return { data: state.wrongReceipt ? { ok: true } : saved.get(id), error: null }
  })
  return state
}
async function mount(kind: 'CUTTING' | 'PICKUP') {
  await act(async () => root.render(kind === 'CUTTING' ? <ConnectedCuttingPage/> : <ConnectedPickupPage/>))
  await settle()
  if (kind === 'CUTTING' && !readProductionRecovery(scope).pending.CUTTING) await click('CUT-1', container.querySelector('.ccut-drafts')!)
}
function writes() { return client.rpc.mock.calls.filter(([name]) => name.startsWith('erp_save_')) }

describe('cutting source authority covers the complete connected page', () => {
  it('a current learning403 retires parent stock, draft facts and sibling results while retaining own notes', async () => {
    const auth = structuredClone(recoveryIdentity)
    Object.assign(auth.runtime, { mode: 'DISPOSABLE_TEST' })
    Object.assign(auth.identity.profile, { authUserId: '22222222-2222-4222-8222-222222222222' })
    auth.identity.permissions.push('production.cutting.view', 'master.product.view', 'warehouse.stock.view', 'sales.invoice.view')
    authState.current = auth
    server()
    const ordinary = client.rpc.getMockImplementation()!
    client.rpc.mockImplementation((name, args) => name === 'erp_cp7_get_cutting_input_workspace_v1'
      ? Promise.resolve({ data: null, error: { code: '42501', message: 'Current actor revoked' } })
      : ordinary(name, args))
    await mount('CUTTING')
    const notes = container.querySelector<HTMLInputElement>('.ccut-fields input[placeholder="Opsional"]')!
    await fill(notes, 'CATATAN OPERATOR TETAP')
    expect(container.querySelectorAll('.ccut-roll-catalog button')).toHaveLength(1)
    expect(container.querySelector('.ccut-review')?.textContent).toContain('9 pcs')
    await click('Muat penilaian potong', container.querySelector('[aria-label="Belajar dari hasil potong"]')!)
    expect(container.querySelectorAll('.ccut-roll-catalog button')).toHaveLength(0)
    expect(container.querySelectorAll('.ccut-drafts > button')).toHaveLength(0)
    expect(container.querySelector('.ccut-review')?.textContent).not.toContain('9 pcs')
    expect(container.querySelector('.ccut-table-wrap')).toBeNull()
    expect(notes.value).toBe('CATATAN OPERATOR TETAP')
    expect(button('Post ke WIP').disabled).toBe(true)
    expect(button('Muat hasil potong tersimpan').disabled).toBe(true)
    expect(writes()).toHaveLength(0)
  })
  it('a fresh parent403 cannot be repainted by an older in-flight200 and never erases unsent notes', async () => {
    server(); await mount('CUTTING')
    const notes = container.querySelector<HTMLInputElement>('.ccut-fields input[placeholder="Opsional"]')!
    await fill(notes, 'BELUM DIKIRIM')
    const ordinary = client.rpc.getMockImplementation()!
    let resolve!:(value:unknown)=>void, oldArgs!:Record<string,unknown>, pending = false
    client.rpc.mockImplementation((name, args) => {
      if (name !== 'erp_get_cutting_workspace_v2') return ordinary(name, args)
      if (!pending) { pending = true; oldArgs = args; return new Promise(r => { resolve = r }) }
      return Promise.resolve({ data: null, error: { status: 403, code: '42501', message: 'Current actor revoked' } })
    })
    await click('Refetch'); await click('Refetch')
    await act(async () => resolve({ data: cuttingSelectorFixture(oldArgs), error: null })); await settle()
    expect(container.querySelectorAll('.ccut-roll-catalog button')).toHaveLength(0)
    expect(container.querySelector('.ccut-review')?.textContent).not.toContain('9 pcs')
    expect(container.querySelector('.ccut-table-wrap')).toBeNull()
    expect(notes.value).toBe('BELUM DIKIRIM')
    expect(button('Post ke WIP').disabled).toBe(true)
    expect(writes()).toHaveLength(0)
  })
})

describe('real Cutting/Pickup forms keep pending, committed and stale distinct', () => {
  it('orders the pickup page without selecting a different group or changing its unsent allocation', async () => {
    const data=pickupFixture()
    data.rows=['CUT-10','CUT-2','CUT-1'].map((group_number,index)=>({...data.rows[0]!,group_number,cutting_group_id:`group-${index}`}))
    data.total=3
    client.rpc.mockImplementation(async(name:string)=>name==='erp_list_patterns_v1'?{data:recoveryPatterns,error:null}:{data,error:null})
    await mount('PICKUP')
    const notes=container.querySelector<HTMLInputElement>('.cpick-notes input')!
    await fill(notes,'BELUM DIKIRIM')
    const reads=client.rpc.mock.calls.length
    await act(async()=>{
      const select=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman distribusi potongan"]')!
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value')!.set!.call(select,'LABEL_ASC')
      select.dispatchEvent(new Event('change',{bubbles:true}))
    })
    expect([...container.querySelectorAll('.cpick-queue > button strong')].map(row=>row.textContent)).toEqual(['CUT-1','CUT-2','CUT-10'])
    expect(container.querySelector('.cpick-selected h2')?.textContent).toContain('CUT-10')
    expect(notes.value).toBe('BELUM DIKIRIM');expect(client.rpc.mock.calls).toHaveLength(reads);expect(writes()).toHaveLength(0)
  })

  it('browses pickup with the complete existing100-row reader from page zero and no write', async () => {
    client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
      if(name==='erp_list_patterns_v1')return{data:recoveryPatterns,error:null}
      if(name==='erp_get_cutting_pickup_queue_v1')return{data:{...pickupFixture(),filter:args.p_filter,pattern_id:args.p_pattern_id,query:args.p_query,offset:args.p_offset},error:null}
      throw new Error(`Unexpected writer ${name}`)
    })
    await mount('PICKUP')
    await fill(container.querySelector<HTMLInputElement>('[aria-label="Cari distribusi potongan"]')!,'CUT lama')
    await click('Browse semua')
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_get_cutting_pickup_queue_v1').at(-1)?.[1]).toEqual({p_filter:'ALL',p_pattern_id:null,p_query:null,p_limit:100,p_offset:0})
    expect(container.querySelector<HTMLInputElement>('[aria-label="Cari distribusi potongan"]')!.value).toBe('')
    expect(writes()).toHaveLength(0)
  })

  it('does not reveal an old pickup after a failed reader is dismissed and keeps the search', async () => {
    server();await mount('PICKUP')
    await fill(container.querySelector<HTMLInputElement>('[aria-label="Cari distribusi potongan"]')!,'BELUM DIKIRIM')
    const ordinary=client.rpc.getMockImplementation()!
    client.rpc.mockImplementation((name,args)=>name==='erp_get_cutting_pickup_queue_v1'?Promise.resolve({data:null,error:{code:'08006',message:'Read failed'}}):ordinary(name,args))
    await click('Refetch');await click('Tutup',container.querySelector('.cpick-message.error')!)
    expect(container.querySelector('.cpick-selected')).toBeNull()
    expect(container.querySelector('.cpick-queue > header strong')?.textContent).toBe('— Potongan')
    expect(container.querySelector('.cpick-pagination > span')?.textContent).toBe('— Potongan')
    expect(button('Berikutnya').disabled).toBe(true)
    expect(container.querySelector<HTMLInputElement>('[aria-label="Cari distribusi potongan"]')!.value).toBe('BELUM DIKIRIM')
    expect(writes()).toHaveLength(0)
  })

  it('refuses an old pickup response after the new authority generation denies the reader', async () => {
    let resolve!:(value:unknown)=>void
    client.rpc.mockImplementation((name:string)=>name==='erp_list_patterns_v1'?Promise.resolve({data:recoveryPatterns,error:null}):new Promise(r=>{resolve=r}))
    await mount('PICKUP');const oldResolve=resolve
    client.rpc.mockImplementation(async(name:string)=>name==='erp_list_patterns_v1'?{data:recoveryPatterns,error:null}:{data:null,error:{code:'42501',message:'Current pickup view revoked'}})
    const next=structuredClone(recoveryIdentity);Object.assign(next.identity.profile,{roleRowVersion:2});authState.current=next
    await mount('PICKUP')
    await act(async()=>oldResolve({data:pickupFixture(),error:null}));await settle()
    expect(container.querySelector('.cpick-selected')).toBeNull()
    expect(container.querySelector('.cpick-queue > header strong')?.textContent).toBe('— Potongan')
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Akun tidak memiliki izin untuk operasi ini.');expect(writes()).toHaveLength(0)
  })

  it.each(['CUTTING', 'PICKUP'] as const)('%s retires committed form before a failed refetch and never replays it', async (kind) => {
    const state = server(); state.failRead = true
    await mount(kind)
    const label = kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup'
    const oldSave = button(label)
    expect(oldSave.disabled).toBe(false)
    await click(label)
    expect(state.effects).toBe(1)
    expect(container.textContent).toContain('Aksi sudah tersimpan, tetapi refresh authoritative gagal')
    expect(kind === 'CUTTING' ? button(label).disabled : container.querySelector('.cpick-actions')).toBe(kind === 'CUTTING' ? true : null)
    await act(async () => oldSave.click())
    expect(writes()).toHaveLength(1)
    state.failRead = false
    await click('Refetch')
    expect(container.textContent).not.toContain('refresh authoritative gagal')
    await act(async () => oldSave.click())
    expect(writes()).toHaveLength(1)
  })
  it.each(['CUTTING', 'PICKUP'] as const)('%s keeps a lost reply across unmount, payload edits and reload', async (kind) => {
    const state = server(); state.loseReply = true
    await mount(kind)
    await click(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup')
    const original = structuredClone(writes()[0][1])
    expect(readProductionRecovery(scope).pending[kind]?.id).toBe(original.p_client_request_id)
    await act(async () => root.unmount()); root = createRoot(container)
    await mount(kind)
    await click('Refetch')
    expect(writes()).toHaveLength(1)
    state.loseReply = false
    await click('Reconcile transaksi')
    expect(writes()).toHaveLength(2)
    expect(writes()[1][1]).toEqual(original)
    expect(state.effects).toBe(1)
    expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it.each(['CUTTING', 'PICKUP'] as const)('%s preserves its request when the reply has no valid commit contract', async (kind) => {
    const state = server(); state.wrongReceipt = true
    await mount(kind); await click(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup')
    expect(readProductionRecovery(scope).pending[kind]).toBeDefined()
    expect(container.textContent).toContain('UUID/payload lama tetap disimpan')
    expect(state.effects).toBe(1)
  })
  it('does not mistake a role rejection on replay for rollback of the original committed pickup', async () => {
    const state = server(); state.loseReply = true
    await mount('PICKUP'); await click('Catat pickup')
    const raw = localStorage.getItem(productionKey(scope, 'PICKUP'))
    state.loseReply = false; state.replayRejection = true
    await click('Reconcile transaksi')
    expect(localStorage.getItem(productionKey(scope, 'PICKUP'))).toBe(raw)
    expect(state.effects).toBe(1)
    expect(button('Catat pickup').disabled).toBe(true)
  })
  it('keeps DELETE on the same recovery path and validates its smaller cutting receipt', async () => {
    const state = server(); state.loseReply = true
    await mount('CUTTING'); await click('Hapus draft')
    const original = writes()[0][1]
    expect(readProductionRecovery(scope).pending.CUTTING?.action).toBe('DELETE')
    state.loseReply = false
    await click('Reconcile transaksi')
    expect(writes()[1][1]).toEqual(original)
    expect(state.effects).toBe(1)
    expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it.each(['CUTTING', 'PICKUP'] as const)('%s blocks a same-frame write when refetch starts', async (kind) => {
    server(); await mount(kind)
    const save = button(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup')
    await act(async () => { button('Refetch').click(); save.click() })
    expect(writes()).toHaveLength(0)
  })
  it.each(['CUTTING', 'PICKUP'] as const)('%s refuses all writes without Web Locks', async (kind) => {
    server(); Reflect.deleteProperty(navigator, 'locks')
    await act(async () => root.render(kind === 'CUTTING' ? <ConnectedCuttingPage/> : <ConnectedPickupPage/>)); await settle()
    expect(container.textContent).toContain('Web Locks')
    expect(writes()).toHaveLength(0)
    expect(button(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup').disabled).toBe(true)
  })
  it('rejects a missed cross-tab generation change before dispatching a stale request', async () => {
    server(); await mount('PICKUP')
    // No StorageEvent is dispatched: the per-command reread must catch this.
    localStorage.setItem('erp.production.revision.v1:'+scope, '00000000-0000-4000-8000-000000000999')
    await click('Catat pickup')
    expect(writes()).toHaveLength(0)
    expect(button('Catat pickup').disabled).toBe(true)
    await click('Refetch')
    expect(button('Catat pickup').disabled).toBe(false)
  })
  it('does not send after navigation retires a writer while it is waiting for its lock', async () => {
    server(); await mount('PICKUP')
    let enter: (() => Promise<unknown>) | undefined
    Object.defineProperty(navigator, 'locks', { configurable: true, value: {
      request: (name: string, _options: LockOptions, callback: (lock: Lock) => Promise<unknown>) => new Promise((resolve) => {
        enter = async () => { const result = await callback({ name, mode: 'exclusive' } as Lock); resolve(result); return result }
      }),
    } })
    await act(async () => { button('Catat pickup').click(); await Promise.resolve() })
    await act(async () => root.render(<p>Another page</p>))
    await act(async () => { await enter!() })
    expect(writes()).toHaveLength(0)
    expect(readProductionRecovery(scope).pending).toEqual({})
  })
  it('shows unknown totals and disables WIP writes when a previously valid read becomes malformed', async () => {
    let malformed = false
    client.rpc.mockImplementation(async (name: string) => {
      if (name === 'erp_list_patterns_v1') return { data: recoveryPatterns, error: null }
      const data = wipFixture()
      if (malformed) Object.assign(data.rows[0], { unfinished_sewing_qty_pcs: 'not-a-number' })
      return { data, error: null }
    })
    await act(async () => root.render(<ConnectedWipStatusPage/>)); await settle()
    expect(container.querySelector('.cwip-kpis')?.textContent).toContain('10 pcs')
    malformed = true; await click('Refetch')
    expect([...container.querySelectorAll('.cwip-kpis strong')].map((node) => node.textContent)).toEqual(['—','—','—'])
    expect([...container.querySelectorAll<HTMLButtonElement>('.cwip-list button')].every((control) => control.disabled)).toBe(true)
    expect(client.rpc.mock.calls.every(([name]) => name.startsWith('erp_get_') || name==='erp_list_patterns_v1')).toBe(true)
  })
  it('blocks another production domain while preserving unrelated reads' , async () => {
    const state = server(); state.loseReply = true
    await act(async () => root.render(<><ConnectedCuttingPage/><ConnectedPickupPage/></>)); await settle()
    await click('CUT-1', container.querySelector('.ccut-drafts')!)
    await click('Post ke WIP')
    expect(button('Catat pickup').disabled).toBe(true)
    expect(container.querySelector('.connected-pickup-page')?.textContent).toContain('Buat Potongan belum selesai')
    await click('Refetch', container.querySelector('.connected-pickup-page')!)
    expect(client.rpc.mock.calls.filter(([name]) => name === 'erp_get_cutting_pickup_queue_v1').length).toBeGreaterThan(1)
    expect(button('Catat pickup').disabled).toBe(true)
    expect(writes()).toHaveLength(1)
  })
  it('quarantines a legacy BS envelope on the Pickup screen without deleting its raw evidence', async () => {
    server(); localStorage.setItem(productionKey(scope, 'BS'), '{broken-json')
    await mount('PICKUP')
    expect(button('Catat pickup').disabled).toBe(true)
    expect(localStorage.getItem(productionKey(scope, 'BS'))).toBe('{broken-json')
    await click('Refetch'); expect(writes()).toHaveLength(0)
  })
})

describe('actual quantity fields preserve invalid pasted text', () => {
  it.each(['CUTTING', 'PICKUP'] as const)('%s does not turn signs, decimals, exponents or blanks into PCS', async (kind) => {
    server(); await mount(kind)
    const input = container.querySelector<HTMLInputElement>(kind === 'CUTTING' ? 'input[aria-label="R-1 Size S"]' : 'input[aria-label="R-1 S Batch 1"]')!
    for (const raw of ['-2', '1,5', '1.5', '1e3', '', '2147483648']) {
      await fill(input, raw)
      expect(input.value).toBe(raw)
      expect(input.getAttribute('aria-invalid')).toBe('true')
      expect(button('Simpan draft').disabled).toBe(true)
    }
    expect(writes()).toHaveLength(0)
    await fill(input, '9'); await click('Simpan draft')
    const payload = writes()[0][1].p_payload
    expect(kind === 'CUTTING' ? payload.rolls[0].yields[0].qty_pcs : payload.batches[0].allocations[0].qty_pcs).toBe(9)
  })
  it('keeps fractional material measures while rejecting their negative sign', async () => {
    server(); await mount('CUTTING')
    const input = container.querySelector<HTMLInputElement>('input[aria-label="R-1 terpakai"]')!
    await fill(input, '-1,5'); expect(input.value).toBe('-1,5'); expect(button('Simpan draft').disabled).toBe(true)
    await fill(input, '1,5'); expect(input.value).toBe('1,5'); await click('Simpan draft')
    expect(writes()[0][1].p_payload.rolls[0]).toMatchObject({ qty_consumed: 1.5, qty_reported_remaining: 18.5 })
  })
})


describe('cutting selector continuity and stale drafts', () => {
  it('preserves edited quantities and selected model when both pages filter out the selection', async () => {
    const state = server(); await mount('CUTTING')
    const qty = container.querySelector<HTMLInputElement>('[aria-label="R-1 Size S"]')!
    await fill(qty, '3')
    state.hideSelectors = true
    await fill(container.querySelector<HTMLInputElement>('[aria-label="Cari PO"]')!, 'No match')
    await click('Cari PO')
    expect(container.querySelector<HTMLInputElement>('[aria-label="R-1 Size S"]')!.value).toBe('3')
    expect(container.querySelector('.ccut-size-list')?.textContent).toContain('S')
    expect(container.querySelector<HTMLSelectElement>('.ccut-fields select')!.value).toBe('po-1')
    expect(button('Post ke WIP').disabled).toBe(false)
    expect(writes()).toHaveLength(0)
  })
  it('blocks a changed draft version, preserves user input, and requires explicit reload', async () => {
    const state = server(); await mount('CUTTING')
    await fill(container.querySelector<HTMLInputElement>('[aria-label="R-1 Size S"]')!, '3')
    state.selectorVersion = 2
    await click('Refetch')
    expect(container.textContent).toContain('Draft berubah di sesi lain')
    expect(button('Post ke WIP').disabled).toBe(true)
    expect(button('Hapus draft').disabled).toBe(true)
    expect(container.querySelector<HTMLInputElement>('[aria-label="R-1 Size S"]')!.value).toBe('3')
    await click('Muat draft terbaru')
    expect(container.querySelector<HTMLInputElement>('[aria-label="R-1 Size S"]')!.value).toBe('9')
    expect(button('Post ke WIP').disabled).toBe(false)
    await click('Simpan draft')
    expect(writes()).toHaveLength(1)
    expect(writes()[0][1].p_expected_version).toBe(2)
  })
  it('blocks a posted or missing draft while keeping the explicit New action available', async () => {
    const state = server(); await mount('CUTTING'); state.missingDraft = true
    await click('Refetch')
    expect(container.textContent).toContain('Draft sudah berubah tahap')
    expect(button('Post ke WIP').disabled).toBe(true)
    expect(button('Baru').disabled).toBe(false)
    await click('Baru')
    expect(container.textContent).not.toContain('Draft sudah berubah tahap')
    expect(writes()).toHaveLength(0)
  })
})

// Node's process.env.TZ sets the timezone Date uses; typed here because the app tsconfig has no Node types.
const nodeEnv = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env

describe('physical time is sent as the WIB wall clock on every device (CP6-01)', () => {
  const zones = ['Asia/Jakarta', 'Asia/Makassar', 'UTC', 'Pacific/Kiritimati']
  it.each(zones.flatMap((zone) => (['CUTTING', 'PICKUP'] as const).map((kind) => [kind, zone] as const)))('%s on a device in %s', async (kind, zone) => {
    const previous = nodeEnv.TZ
    nodeEnv.TZ = zone
    try {
      server()
      await mount(kind)
      const time = container.querySelector<HTMLInputElement>('input[type="datetime-local"]')!
      await fill(time, '2026-09-20T00:30')
      await click(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup')
      const payload = writes()[0][1].p_payload as Record<string, unknown>
      expect(payload[kind === 'CUTTING' ? 'cut_at' : 'picked_up_at']).toBe('2026-09-19T17:30:00.000Z')
    } finally {
      if (previous === undefined) delete nodeEnv.TZ
      else nodeEnv.TZ = previous
    }
  })

  it.each(['CUTTING', 'PICKUP'] as const)('%s keeps its write disabled for an empty physical time', async (kind) => {
    server()
    await mount(kind)
    const time = container.querySelector<HTMLInputElement>('input[type="datetime-local"]')!
    await fill(time, '')
    expect(button(kind === 'CUTTING' ? 'Post ke WIP' : 'Catat pickup').disabled).toBe(true)
    expect(writes()).toHaveLength(0)
  })
})
