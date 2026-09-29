// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import RecostQueuePanel from './RecostQueuePanel'
import {parseRecostQueue,parseRecostOutcome,type RecostQueue} from './recostContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {getUatSupabaseClient} from './lib/supabase'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
const instant='2026-09-29T10:00:00Z',id='11111111-1111-4111-8111-111111111111'
function queue(status:'PENDING'|'FAILED'|'DONE'='PENDING'):RecostQueue{return {contract_version:'cp7.recost-queue.v1',captured_at:instant,scope:'CURRENT_QUEUE_ALL_ENTITIES',batch_semantics:'AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS',counts:{pending:status==='PENDING'?'1':'0',running:'0',failed:status==='FAILED'?'1':'0',done:status==='DONE'?'1':'0',eligible:status==='PENDING'?'1':'0',exhausted:'0'},page:{rows:status==='DONE'?[]:[{id:'1',entity_type:'PO',entity_id:id,po_number:'PO-RECOST',status,reason:'Harga susulan',recalc_from:instant,queued_at:instant,attempt_count:status==='FAILED'?1:0,next_attempt_at:status==='FAILED'?'2026-09-29T10:05:00Z':null,error_message:status==='FAILED'?'Sumber belum lengkap':null,error_truncated:false,eligible:status==='PENDING'}],total:status==='DONE'?'0':'1',offset:0,limit:25,next_offset:null}}}
let root:Root,container:HTMLDivElement;const onChanged=vi.fn(async()=>true)
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();onChanged.mockClear();state.auth=structuredClone(recoveryIdentity);Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(canManage=true){await act(async()=>root.render(<RecostQueuePanel client={client as unknown as ReturnType<typeof getUatSupabaseClient>} canManage={canManage} onChanged={onChanged}/>));await flush()}
const button=(s:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===s)!
async function click(s:string){await act(async()=>button(s).click());await flush()}
async function review(){const t=container.querySelector('textarea')!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')!.set!.call(t,'Periksa biaya susulan');t.dispatchEvent(new Event('input',{bubbles:true}))});await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_process_recost_v1')
function server(){const s={status:'PENDING' as 'PENDING'|'FAILED'|'DONE',failRead:false,lose:false,effects:0,failJob:false},cache=new Map();client.rpc.mockImplementation(async(name,args)=>{
 if(name==='erp_cp7_get_recost_queue_v1')return s.failRead?{data:null,error:{message:'Antrean tidak tersedia'}}:{data:queue(s.status),error:null}
 if(name==='erp_cp7_process_recost_v1'){if(!cache.has(args.p_request)){s.effects++;s.status=s.failJob?'FAILED':'DONE';cache.set(args.p_request,{contract_version:'cp7.recost-outcome.v1',kind:'COMMITTED_OUTCOME',action:'PROCESS_ELIGIBLE',request_id:args.p_request,limit:20,completed:s.failJob?0:1,processed_at:instant,batch_semantics:'AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS',queue_after:queue(s.status)})}return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:cache.get(args.p_request),error:null}}
 throw Error('Unexpected '+name)
 });return s}
it('rejects contradictory counts, hidden sources, unsafe queue IDs and impossible retry readiness',()=>{
 expect(parseRecostQueue(queue()).page.rows).toHaveLength(1)
 const wrong=queue();wrong.counts.exhausted='1';expect(()=>parseRecostQueue(wrong)).toThrow()
 const hidden=queue();hidden.page.rows=[];expect(()=>parseRecostQueue(hidden)).toThrow()
 const retry=queue('FAILED');retry.page.rows[0].eligible=true;expect(()=>parseRecostQueue(retry)).toThrow()
 const numeric=queue();Object.assign(numeric.page.rows[0],{id:9007199254740993});expect(()=>parseRecostQueue(numeric)).toThrow()
 expect(()=>parseRecostOutcome({kind:'COMMITTED_OUTCOME',completed:21},id,{limit:20,reason:'checked'})).toThrow()
})
it('requires explicit reason and confirmation, bounds native work to20 and reloads HPP',async()=>{
 const s=server();await mount();expect(button('Proses maksimal 20 pekerjaan').disabled).toBe(true);await review();await click('Proses maksimal 20 pekerjaan')
 expect(writes()[0][1].p_payload).toEqual({limit:20,reason:'Periksa biaya susulan'});expect(s.effects).toBe(1);expect(onChanged).toHaveBeenCalledOnce();expect(container.textContent).toContain('menyelesaikan 1 pekerjaan');expect(button('Proses maksimal 20 pekerjaan').disabled).toBe(true)
})
it('keeps a failed native job explicit even when the batch RPC commits successfully',async()=>{
 const s=server();s.failJob=true;await mount();await review();await click('Proses maksimal 20 pekerjaan')
 expect(container.textContent).toContain('menyelesaikan 0 pekerjaan');expect(container.textContent).toContain('gagal 1');expect(container.textContent).toContain('Sumber belum lengkap');expect(button('Proses maksimal 20 pekerjaan').disabled).toBe(true)
})
it('recovers an identical lost response after remount without consuming another batch',async()=>{
 const s=server();await mount();await review();s.lose=true;await click('Proses maksimal 20 pekerjaan');const first=structuredClone(writes()[0][1]);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi');expect(writes()[1][1]).toEqual(first);expect(s.effects).toBe(1);expect(onChanged).toHaveBeenCalledOnce()
})
it('retires the command and source rows after a failed fresh queue read',async()=>{
 const s=server();await mount();await review();s.failRead=true;await click('Muat ulang antrean HPP');expect(container.textContent).toContain('Antrean tidak tersedia');expect(container.textContent).not.toContain('PO-RECOST');expect(button('Proses maksimal 20 pekerjaan')).toBeUndefined();expect(writes()).toHaveLength(0)
})
it('keeps current read-only HPP access without exposing a process button',async()=>{
 server();await mount(false);expect(container.textContent).toContain('PO-RECOST');expect(button('Proses maksimal 20 pekerjaan')).toBeUndefined();expect(writes()).toHaveLength(0)
})
