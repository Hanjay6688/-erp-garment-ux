// @vitest-environment jsdom
// AI v2 panel: synthetic DOM checks; the Native and HTTP evidence is the P19 AI v2 suite.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeStagedAiPanel from './NativeStagedAiPanel'
import * as f from '../tests/fixtures/nativeStagedAi'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,copied:string[]
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();copied=[]
 Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async(t:string)=>{copied.push(t)}}})
 state.auth={runtime:{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'},identity:{status:'AUTHORIZED',profile:{id:'actor-1',authUserId:f.actor,role:'STAFF'},permissions:[]}}
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
const labels=new Map(f.keys.map((k,i)=>[k,'SKU-'+(i+1)+' · Produk '+(i+1)]))
async function render(selected:string[]=[]){await act(async()=>root.render(<NativeStagedAiPanel staged={f.staged} selected={selected} labels={labels} onClear={()=>{}} blocked={false} financeAccess={{ownerReports:false,preflight:false}}/>))}
async function click(name:string){await act(async()=>[...container.querySelectorAll('button')].find(b=>b.textContent===name)!.click());for(let i=0;i<10;i++)await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
it('copies a checked prompt from the bounded brief of the run with the selected targets; no finance without access',async()=>{
 client.rpc.mockImplementation((name:string,args:{p_targets:string[]})=>Promise.resolve(name==='erp_cp7_get_staged_ai_brief_v1'?{data:f.brief(args.p_targets),error:null}:{data:null,error:{message:'unexpected'}}))
 await render([f.keys[2]]);expect(container.textContent).toContain('1 target dipilih: SKU-3 · Produk 3.')
 expect(container.querySelector('[aria-label="Sertakan keuangan dan HPP untuk AI"]')).toBeNull()
 await click('Periksa & salin pertanyaan untuk AI')
 expect(client.rpc.mock.calls).toEqual([['erp_cp7_get_staged_ai_brief_v1',{p_run:f.run,p_targets:[f.keys[2]]}]])
 const text=(container.querySelector('[aria-label="Salinan pertanyaan dan ringkasan analisis bertahap"]') as HTMLTextAreaElement).value
 expect(copied).toEqual([text]);expect(text).toContain('bukan angka saat ini');expect(text).toContain(f.keys[2]);expect(container.textContent).not.toMatch(/terkini/i)
})
it('shows a refused brief in words and copies nothing',async()=>{
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_AI_V2_SNAPSHOT_UNAVAILABLE'}})
 await render();await click('Periksa & salin pertanyaan untuk AI')
 expect(container.querySelector('[role="alert"]')?.textContent).toBeTruthy();expect(copied).toEqual([])
 expect(container.querySelector('[aria-label="Salinan pertanyaan dan ringkasan analisis bertahap"]')).toBeNull()
})
