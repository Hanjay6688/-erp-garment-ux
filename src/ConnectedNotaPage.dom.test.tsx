// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedNotaPage from './ConnectedNotaPage'
import {parseNotaWorkspace,parseNotaOutcome} from './notaContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',origin='22222222-2222-4222-8222-222222222222',noteId='33333333-3333-4333-8333-333333333333',at='2026-09-29T03:00:00.000000Z'
const card={card_key:`FG_REPAIR:${origin}:${id}`,source_type:'FG_REPAIR',origin_id:origin,origin_number:'BB-001',contractor_id:id,contractor_name:'Mandor Test',contractor_active:true,po_id:null,po_number:null,cutting_group_id:null,group_number:null,bs_case_id:origin,eligible_at:at,line_count:'1',source_token:'a'.repeat(32),basis:'NATIVE_REMAINING_COMPONENT_ENTITLEMENT',lines:[{source_type:'FG_REPAIR',source_id:id,component_id:id,component_code:'JAHIT',component_name:'Jahit utama',source_qty:'2',eligible_qty:'2',allocated_qty:'0',remaining_qty:'2',held_qty:'0',eligible_at:at,eligibility_reason:'FG_UNSOURCED_REPAIR_POSTED'}]}
const page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
const workspace=(section:string,rows:unknown[],financial=false)=>({contract_version:'cp7.nota-workspace.v1',section,read_at:at,financial_captured:financial,can_post:true,page:page(rows)})
function noteFixture(){return {id:noteId,note_number:'NFG-001',contractor_id:id,contractor_name:'Mandor Test',note_date:'2026-09-29',period_start:'2026-09-29',period_end:'2026-09-29',notes:'',status:'DRAFT',row_version:'9007199254740993',target_payroll_id:null,target_version:null,posted_payroll_id:null,payroll_number:null,payroll_status:null,posted_at:null,void_reason:null,created_at:at,updated_at:at,cards:[card]}}
let root:Root,container:HTMLDivElement,saved:ReturnType<typeof noteFixture>|null
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});saved=null;localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('production.fg_handoff.view','production.fg_handoff.post');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedNotaPage/>));await flush()}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(x=>x.textContent===label);if(!b)throw Error(label);await act(async()=>b.click());await flush()}
// OW-09: the reader echoes the whole saved-note list it applied (section NOTES, when the request carries one).
type Q=Record<string,unknown>
const listed=<T extends {page:object}>(w:T,q:Q)=>{if('order' in q)Object.assign(w.page,{list:{q:q.q,status:q.status,order:q.order}});return w}
function server(){client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
 if(name==='erp_cp7_save_nota_v1'){saved=noteFixture();return {error:null,data:{contract_version:'cp7.nota-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:args.p_request,note_id:noteId,status:'DRAFT',row_version:saved.row_version,payroll_id:null}}}
 return {error:null,data:args.p_section==='SOURCES'?workspace('SOURCES',[{...card,claimed_by_note:saved?noteId:null}]):listed(workspace(String(args.p_section),args.p_section==='NOTES'&&saved?[saved]:[]),args.p_query as Q)}
})}
const notes=Array.from({length:31},(_,i)=>({...noteFixture(),id:`44444444-4444-4444-8444-${String(i).padStart(12,'0')}`,note_number:`NFG-${i+1}`,status:(['DRAFT','POSTED','VOID'] as const)[i%3],posted_payroll_id:i%3===1?id:null,posted_at:i%3===1?at:null}))
function reader(q:Q){
 const all=notes.filter(n=>(!q.status||n.status===q.status)&&(!q.q||[n.note_number,n.contractor_name,n.notes].join(' ').toLowerCase().includes(String(q.q).toLowerCase())))
 if(q.order!=='SOURCE')all.sort((a,b)=>(q.order==='LABEL_DESC'?-1:1)*a.note_number.localeCompare(b.note_number,'id',{numeric:true}))
 const off=Number(q.offset),w=workspace('NOTES',all.slice(off,off+25));Object.assign(w.page,{total:String(all.length),offset:off,next_offset:off+25<all.length?off+25:null,list:{q:q.q,status:q.status,order:q.order}});return w
}
describe('native Nota boundary',()=>{
 it('searches, filters and orders every saved note through the reader and restarts at the first page',async()=>{
  client.rpc.mockImplementation(async(_name:string,args:{p_section:string;p_query:Q})=>({error:null,data:args.p_section==='NOTES'?reader(args.p_query):workspace(args.p_section,[])}));await mount()
  const last=()=>client.rpc.mock.calls.filter(([,a])=>a.p_section==='NOTES').at(-1)![1].p_query as Q,numbers=()=>[...container.querySelectorAll('.cnota-note-row small')].map(e=>e.textContent!.split(' · ')[1])
  expect(last()).toMatchObject({q:'',offset:0,limit:25,status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25);expect(container.textContent).toContain('31 nota cocok dengan pencarian dan filter');expect(container.textContent).toContain('Total 31 nota')
  expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain');expect(container.textContent).not.toContain('pada halaman')
  await click('nota berikutnya');expect(last().offset).toBe(25);expect(numbers()).toHaveLength(6)
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan nota mandor"]')!;s.value='LABEL_DESC';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,order:'LABEL_DESC'});expect(numbers()).toEqual(reader(last()).page.rows.map(n=>(n as {note_number:string}).note_number));expect(numbers()[0]).toBe('NFG-31')
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Status nota tersimpan"]')!;s.value='POSTED';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,status:'POSTED',order:'LABEL_DESC'});expect(numbers()).toHaveLength(10);expect(container.textContent).toContain('Total 10 nota')
  await click('Browse semua');expect(last()).toMatchObject({offset:0,q:'',status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25)
  expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_nota_v1')).toBe(false)
  for(const [,a] of client.rpc.mock.calls.filter(([,a])=>a.p_section!=='NOTES'||(a.p_query as Q).id))expect(Object.keys(a.p_query as Q)).not.toContain('order')
 })
 it('refuses a saved-note list that is not the list the page asked for',()=>{
  const list={q:'',status:'VOID' as const,order:'LABEL_ASC' as const},good=reader({...list,offset:0});expect(parseNotaWorkspace(good,'NOTES',list).page.total).toBe('10')
  const variants:((w:ReturnType<typeof reader>)=>void)[]=[w=>{delete (w.page as {list?:unknown}).list},w=>{(w.page as unknown as {list:Q}).list.status='DRAFT'},w=>{(w.page as unknown as {list:Q}).list.order='SOURCE'},w=>{(w.page as unknown as {list:Q}).list.extra=null},w=>{(w.page.rows[0] as {status:string}).status='DRAFT'}]
  for(const change of variants){const w=structuredClone(good);change(w);expect(()=>parseNotaWorkspace(w,'NOTES',list)).toThrow()}
  expect(()=>parseNotaWorkspace(good,'NOTES')).toThrow();expect(()=>parseNotaWorkspace(workspace('SOURCES',[]),'SOURCES' as 'NOTES',list)).toThrow()
 })
 it('accepts the existing CP3 component UUID while refusing malformed IDs',()=>{const component='a4000000-0000-0000-0000-000000000001',c={...card,claimed_by_note:null,lines:[{...card.lines[0],component_id:component}]};expect(parseNotaWorkspace(workspace('SOURCES',[c]),'SOURCES').page.rows[0].lines[0].component_id).toBe(component);expect(()=>parseNotaWorkspace(workspace('SOURCES',[{...c,lines:[{...c.lines[0],component_id:component+'x'}]}]),'SOURCES')).toThrow()})
 it('rejects money in operational nested cards and an inconsistent financial source total',()=>{const w=workspace('SOURCES',[{...card,claimed_by_note:null}]);expect(parseNotaWorkspace(w,'SOURCES').page.rows[0].remaining_amount).toBeUndefined();expect(()=>parseNotaWorkspace(workspace('SOURCES',[{...card,claimed_by_note:null,remaining_amount:'4000'}]),'SOURCES')).toThrow();expect(()=>parseNotaWorkspace(workspace('SOURCES',[{...card,claimed_by_note:null,remaining_amount:'3000',lines:[{...card.lines[0],rate:'2000',amount:'4000'}]}],true),'SOURCES')).toThrow()})
 it('adds a complete card and saves only source identity/token, then requires explicit post review',async()=>{server();await mount();await click('Tambahkan ke nota');expect(container.textContent).toContain('Bikin Bagus');expect(container.textContent).not.toContain('Rp');await click('Simpan draft nota');const call=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_nota_v1')![1];expect(call.p_payload.cards).toEqual([{card_key:card.card_key,source_token:card.source_token}]);expect(call.p_expected).toBeNull();expect(call.p_payload).not.toHaveProperty('amount');const post=[...container.querySelectorAll('button')].find(x=>x.textContent==='Posting ke payroll')!;expect(post.disabled).toBe(true);expect(container.textContent).toContain('Pembayaran dilakukan terpisah.')})
 it('keeps a large row version as exact text and clears rendered source facts after failed refresh',async()=>{server();saved=noteFixture();await mount();await click('Mandor Test2026-09-29 · NFG-001Draft');expect(parseNotaWorkspace(workspace('NOTES',[saved]),'NOTES').page.rows[0].row_version).toBe('9007199254740993');client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Access revoked'}});await click('Muat ulang nota');expect(container.querySelectorAll('.cnota-source')).toHaveLength(0);expect(container.querySelectorAll('.cnota-selected article')).toHaveLength(0);expect(container.textContent).not.toContain('Mandor Test')})
 it('refuses mismatched successful outcome document, action, and UUID',()=>{const p={document:{id:noteId},expected_version:'1'},r={contract_version:'cp7.nota-outcome.v1',kind:'COMMITTED_OUTCOME',action:'SAVE',request_id:id,note_id:origin,status:'DRAFT',row_version:'2',payroll_id:null};expect(()=>parseNotaOutcome(r,id,'SAVE',p)).toThrow();expect(()=>parseNotaOutcome({...r,note_id:noteId},origin,'SAVE',p)).toThrow();expect(()=>parseNotaOutcome({...r,note_id:noteId},id,'POST',p)).toThrow()})
})
