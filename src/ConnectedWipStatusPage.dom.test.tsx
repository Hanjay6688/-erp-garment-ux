// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedWipStatusPage from './ConnectedWipStatusPage'
import { recoveryIdentity, recoveryPatterns } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const opening = { opening_item_id:'11111111-1111-4111-8111-111111111111', batch_id:'22222222-2222-4222-8222-222222222222',
  source_key:'OPEN-001', po_number:'PO-OPEN-001', balance_type:'WIP', stage:'SEWING', size_code:'M', qty_pcs:8, remaining_qty_pcs:8,
  completed_qty_pcs:0, contractor_name:'Mandor', vendor_name:null, outputs:[] }
const wip = (patch: Record<string, unknown> = {}) => ({ filter:'ACTIVE', sort:'PATTERN', pattern_id:null, rows:[], opening_rows:[], ...patch })
const withoutOpening = () => { const value: Record<string, unknown> = wip(); Reflect.deleteProperty(value, 'opening_rows'); return value }
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  localStorage.clear(); client.rpc.mockReset(); auth.current = structuredClone(recoveryIdentity)
  Object.defineProperty(navigator, 'locks', { configurable:true, value:{request:async (_name: string, _options:unknown, fn:(lock:unknown)=>Promise<unknown>) => fn({})} })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function flush() { await act(async () => { await new Promise(resolve => setTimeout(resolve,0)) }) }
function serve(read: () => { data: unknown; error: unknown }) {
  client.rpc.mockImplementation(async (name: string) => {
    if (name === 'erp_list_patterns_v1') return { data:recoveryPatterns, error:null }
    if (name === 'erp_get_wip_control_v1') return read()
    throw new Error('Unexpected RPC '+name)
  })
}
async function mount(read: () => { data: unknown; error: unknown }) { serve(read); await act(async () => root.render(<ConnectedWipStatusPage/>)); await flush() }
async function refetch(read: () => { data: unknown; error: unknown }) { serve(read); await act(async () => container.querySelector<HTMLButtonElement>('.cwip-hero button')!.click()); await flush() }
const kpis = () => [...container.querySelectorAll('.cwip-kpis strong')].map(x => x.textContent)
const claimsNoWip = () => container.textContent?.includes('Tidak ada WIP aktif.') ?? false

describe('WIP totals stay unknown unless the whole response was read', () => {
  it('browses all through the existing global WIP sort and clears the search without a write', async () => {
    client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>name==='erp_list_patterns_v1'?{data:recoveryPatterns,error:null}:{data:wip({filter:args.p_filter,sort:args.p_sort,pattern_id:args.p_pattern_id}),error:null})
    await act(async()=>root.render(<ConnectedWipStatusPage/>));await flush()
    const input=container.querySelector<HTMLInputElement>('[aria-label="Cari WIP"]')!
    await act(async()=>{
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'PO LAMA')
      input.dispatchEvent(new Event('input',{bubbles:true}))
    })
    await act(async()=>[...container.querySelectorAll<HTMLButtonElement>('button')].find(b=>b.textContent==='Browse semua')!.click());await flush()
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_get_wip_control_v1').at(-1)?.[1]).toEqual({p_filter:'ALL',p_pattern_id:null,p_sort:'PATTERN',p_query:null})
    expect(input.value).toBe('')
    expect(client.rpc.mock.calls.every(([name])=>['erp_list_patterns_v1','erp_get_wip_control_v1'].includes(name))).toBe(true)
  })

  it('cannot repaint the earlier opening WIP after the current role generation is denied', async () => {
    let resolve!:(value:unknown)=>void
    client.rpc.mockImplementation((name:string)=>name==='erp_list_patterns_v1'?Promise.resolve({data:recoveryPatterns,error:null}):new Promise(r=>{resolve=r}))
    await act(async()=>root.render(<ConnectedWipStatusPage/>));await flush()
    const oldResolve=resolve
    serve(()=>({data:null,error:{code:'42501',message:'Current WIP view revoked'}}))
    const next=structuredClone(recoveryIdentity)
    Object.assign(next.identity.profile,{roleRowVersion:2});auth.current=next
    await act(async()=>root.render(<ConnectedWipStatusPage/>));await flush()
    await act(async()=>oldResolve({data:wip({opening_rows:[opening]}),error:null}));await flush()
    expect(kpis()).toEqual(['—','—','—'])
    expect(container.querySelector('[aria-label="WIP saldo awal"]')).toBeNull()
    expect([...container.querySelectorAll('[role="alert"]')].some(row=>row.textContent?.includes('Akun tidak memiliki izin untuk operasi ini.'))).toBe(true)
  })

  it('shows a real zero only for an explicit empty opening collection', async () => {
    await mount(() => ({ data:wip(), error:null }))
    expect(kpis()).toEqual(['0', '0 pcs', '0']); expect(claimsNoWip()).toBe(true)
  })
  it('counts complete opening WIP as quantity and open action', async () => {
    await mount(() => ({ data:wip({ opening_rows:[opening] }), error:null }))
    expect(kpis()).toEqual(['1', '8 pcs', '1']); expect(container.querySelector('[aria-label="WIP saldo awal"]')).not.toBe(null)
  })
  it('refuses a response without the opening collection instead of reading zero', async () => {
    await mount(() => ({ data:withoutOpening(), error:null }))
    expect(kpis()).toEqual(['—', '—', '—']); expect(container.querySelector('[role="alert"]')).not.toBe(null)
    expect(claimsNoWip()).toBe(false); expect(container.textContent).toContain('WIP belum dapat dipastikan.')
  })
  it('does not replace eight known pieces with zero when a refetch loses the opening collection', async () => {
    await mount(() => ({ data:wip({ opening_rows:[opening] }), error:null }))
    await refetch(() => ({ data:withoutOpening(), error:null }))
    expect(kpis()).toEqual(['—', '—', '—']); expect(claimsNoWip()).toBe(false)
  })
  it('does not keep earlier totals as current after a failed refetch', async () => {
    await mount(() => ({ data:wip({ opening_rows:[opening] }), error:null }))
    await refetch(() => ({ data:null, error:{ code:'08006', message:'connection lost' } }))
    expect(kpis()).toEqual(['—', '—', '—']); expect(claimsNoWip()).toBe(false)
    expect(container.querySelector('[role="alert"]')).not.toBe(null)
  })
})
