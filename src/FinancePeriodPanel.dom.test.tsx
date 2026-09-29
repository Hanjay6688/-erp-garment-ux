// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach,beforeEach,expect,it,vi } from 'vitest'
import FinancePeriodPanel from './FinancePeriodPanel'
import { parsePeriodControl,parsePeriodOutcome } from './periodControlContract'
import { financeReportFixture } from '../tests/fixtures/financeReport'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import type { getUatSupabaseClient } from './lib/supabase'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
const day='2020-01-02',hash='a'.repeat(32),nextHash='b'.repeat(32),filing='11111111-1111-4111-8111-111111111111'
function record(through=day,closed:string|null=null){return {contract_version:'cp7.period-control.v1',captured_at:'2026-09-29T10:00:00Z',through,review_token:closed?nextHash:hash,control:{closed_through:closed,version_token:closed?nextHash:hash},preflight:{...financeReportFixture({from:through,to:through,as_of:through},null,true).close_preflight!,through,closed_through:closed,date_allowed:true},current_filing:closed?{id:filing,closed_through:closed,filed_at:'2026-09-29T10:00:00Z'}:null}}
let root:Root,container:HTMLDivElement
const onChanged=vi.fn(async()=>true)
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();onChanged.mockClear();state.auth=structuredClone(recoveryIdentity);Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<FinancePeriodPanel client={client as unknown as ReturnType<typeof getUatSupabaseClient>} onChanged={onChanged}/>));await flush()}
const button=(name:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===name)!
function field(label:string){const l=[...container.querySelectorAll('label')].find(l=>[...l.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join('')===label);if(!l)throw Error('Missing '+label);return l.querySelector<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>('input,textarea,select')!}
async function fill(label:string,value:string){const e=field(label);await act(async()=>{const proto=e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:e instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(e,value);e.dispatchEvent(new Event(e instanceof HTMLSelectElement?'change':'input',{bubbles:true}))});await flush()}
async function click(name:string){await act(async()=>button(name).click());await flush()}
async function check(){await act(async()=>field('Saya sudah memeriksa tanggal, penghalang, dan alasan perubahan periode.').click());await flush()}
function server(){const s={closed:null as string|null,effects:0,lose:false,fail:false,blocked:false},cache=new Map<string,unknown>();client.rpc.mockImplementation(async(name,args)=>{
 if(name==='erp_cp7_get_period_control_v1'){if(s.fail)return {data:null,error:{message:'Period unavailable'}};const r=record(args.p_through,s.closed);if(s.blocked)Object.assign(r.preflight,{status:'RECALC_PENDING',blocker_count:'1',recalc_count:'1',blockers:[{family:'COST',code:'PENDING_COST',severity:'RECALC',scope:'AS_OF',impact_date:args.p_through,reference:null,reason:'Tunggu hitung biaya'}]});return {data:r,error:null}}
 if(name==='erp_cp7_save_period_control_v1'){if(!cache.has(args.p_request)){s.effects++;s.closed=args.p_payload.through;cache.set(args.p_request,{contract_version:'cp7.period-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:args.p_request,closed_through:s.closed,version_token:nextHash,filing_id:args.p_action==='CLOSE'?filing:null})}return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:cache.get(args.p_request),error:null}}
 throw Error('Unexpected '+name)
 });return s}
const writes=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_period_control_v1')
async function review(){await fill('Tanggal pemeriksaan tutup buku',day);await fill('Alasan perubahan periode','Semua sumber diperiksa');await check()}
it('requires a complete matching native readiness and period token, never accepts hidden blockers',()=>{
 expect(parsePeriodControl(record(),day).review_token).toBe(hash)
 expect(()=>parsePeriodControl(record(), '2020-01-03')).toThrow()
 const r=record();r.preflight.blocker_count='1';expect(()=>parsePeriodControl(r,day)).toThrow()
 expect(()=>parsePeriodOutcome({contract_version:'cp7.period-outcome.v1',kind:'COMMITTED_OUTCOME',action:'CLOSE',request_id:filing,closed_through:day,version_token:hash,filing_id:null},filing,'CLOSE',{through:day,review_through:day,review_token:hash,reason:'checked'})).toThrow()
})
it('closes only the explicitly reviewed date/token/reason and refreshes the native report',async()=>{
 const s=server();await mount();await review();expect(button('Tutup buku dan simpan arsip').disabled).toBe(false);await click('Tutup buku dan simpan arsip')
 expect(writes()[0][1].p_payload).toEqual({through:day,review_through:day,review_token:hash,reason:'Semua sumber diperiksa'});expect(s.effects).toBe(1);expect(onChanged).toHaveBeenCalledOnce();expect(button('Tutup buku dan simpan arsip').disabled).toBe(true)
})
it('requires another confirmation when date/reason changes and disables close for native blockers',async()=>{
 const s=server();await mount();await review();await fill('Alasan perubahan periode','Alasan berubah');expect(button('Tutup buku dan simpan arsip').disabled).toBe(true)
 s.blocked=true;await click('Periksa ulang periode');await check();expect(container.textContent).toContain('Tunggu hitung biaya');expect(button('Tutup buku dan simpan arsip').disabled).toBe(true);expect(writes()).toHaveLength(0)
})
it('replays the exact close after remount without filing twice',async()=>{
 const s=server();await mount();await review();s.lose=true;await click('Tutup buku dan simpan arsip');const sent=structuredClone(writes()[0][1]);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi')
 expect(writes()[1][1]).toEqual(sent);expect(s.effects).toBe(1);expect(onChanged).toHaveBeenCalledOnce()
})
it('retires all write actions after a failed fresh read',async()=>{
 const s=server();await mount();await review();s.fail=true;await click('Periksa ulang periode');expect(container.textContent).toContain('Period unavailable');expect(button('Tutup buku dan simpan arsip')).toBeUndefined();expect(writes()).toHaveLength(0)
})
it('opens all periods only from an explicit reopen selection and confirmation',async()=>{
 const s=server();s.closed=day;await mount();await fill('Tanggal pemeriksaan tutup buku',day)
 const select=container.querySelector('select')!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value')!.set!.call(select,'REOPEN');select.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
 await act(async()=>field('Buka seluruh periode tertutup').click());await fill('Alasan perubahan periode','Koreksi sumber tertinggal');await check();await click('Buka kembali periode')
 expect(writes()[0][1].p_action).toBe('REOPEN');expect(writes()[0][1].p_payload.through).toBeNull();expect(s.closed).toBeNull()
})
