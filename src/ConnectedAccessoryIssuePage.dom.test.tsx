// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedAccessoryIssuePage from './ConnectedAccessoryIssuePage'
import { parseAccessoryWorkspace, previewAccessoryLine, type AccessoryChoice } from './accessoryIssue'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { persistProductionEnvelope, readProductionRecovery } from './productionRecovery'
import TransactionSourceLink, { TransactionSourceProvider } from './TransactionSourceNavigation'
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',doc='22222222-2222-4222-8222-222222222222',lineId='33333333-3333-4333-8333-333333333333'
const quote:AccessoryChoice={id,sku:'BTN',name:'Kancing silver',category:'Kancing',unit:'PCS',stock:'300.000000',master_price:'36.000000',factor:'12.000000',price_unit:'LUSIN',price_version_id:lineId}
const at='2026-09-22T10:15:00'
let root:Root,container:HTMLDivElement
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset()
  const a=structuredClone(recoveryIdentity);a.identity.permissions.push('finance.contractor_accessory.view','finance.contractor_accessory.create','finance.contractor_accessory.post','finance.contractor_accessory.reverse');auth.current=a
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}})
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})}
async function mount(){await act(async()=>root.render(<ConnectedAccessoryIssuePage/>));await flush()}
async function change(label:string,value:string){const el=container.querySelector<HTMLInputElement|HTMLSelectElement>(`[aria-label="${label}"]`)!;if(!el)throw new Error('Missing '+label)
  await act(async()=>{Object.getOwnPropertyDescriptor(el instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
function button(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent?.trim()===label);if(!b)throw new Error('Missing '+label);return b}
async function click(label:string){await act(async()=>button(label).click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_save_accessory_issue_action_v1')
function documentFixture(){return {id:doc,number:'ACC-001',contractor_id:id,location_id:id,po_id:null,physical_local:at,status:'DRAFT',row_version:'1',notes:'',total:'22.75',payroll_locked:false,
  items:[{id:lineId,material_id:id,sku:'BTN',name:'Kancing silver',unit:'PCS',qty:'7.000000',manual_price:'3.25',price:'3.250000',factor:'1.000000',price_unit:'PCS',price_version_id:null,amount:'22.750000',payroll_status:'UNALLOCATED'}]}}
type HistoryRow={id:string;number:string;contractor:string;status:string;row_version:string;date:string;total:string}
const historyRows=(numbers:string[],status=(i:number)=>i%3?'POSTED':'DRAFT')=>numbers.map((number,i)=>({id:`99999999-9999-4999-8999-${String(i+1).padStart(12,'0')}`,number,contractor:'Afui',status:status(i),row_version:'1',date:'2026-09-22',total:'1.00'}))
const reads=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_get_accessory_issue_workspace_v1').map(([,args])=>args.p_filters as Record<string,unknown>)
const shown=()=>[...container.querySelectorAll('[aria-label="Riwayat nota aksesori"] tbody tr td:first-child')].map(cell=>cell.textContent)
function server(){
  const s={document:null as ReturnType<typeof documentFixture>|null,history:null as HistoryRow[]|null,lose:false,effects:0,invalid:false,reject:false,stock:'300.000000',badReceipt:false};const cache=new Map<string,unknown>()
  const collator=new Intl.Collator('id',{numeric:true,sensitivity:'base'})
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
    if(name==='erp_get_accessory_issue_workspace_v1'){
      const f=args.p_filters as Record<string,unknown>,d=f.id?s.document:null
      const all=s.history??(s.document?[{id:doc,number:s.document.number,contractor:'Afui',status:s.document.status,row_version:s.document.row_version,date:'2026-09-22',total:s.document.total}]:[])
      // Like the stage reader: with the history keys, search, status and order apply to every note before the page is cut.
      const listed=['history_status','history_order','history_offset','history_limit'].some(k=>k in f),q=String(f.query??'').trim(),status=(f.history_status??null) as string|null
      const order=String(f.history_order??'SOURCE'),offset=Number(f.history_offset??0),limit=Number(f.history_limit??50)
      const matching=listed?all.filter(h=>(!status||h.status===status)&&(!q||`${h.number} ${h.contractor}`.toLowerCase().includes(q.toLowerCase()))):all
      const sorted=order==='SOURCE'?matching:[...matching].sort((a,b)=>(order==='LABEL_DESC'?-1:1)*collator.compare(a.number,b.number))
      const history=listed?sorted.slice(offset,offset+limit):sorted.slice(0,50)
      const w={filters:f,contractor_id:f.contractor_id??d?.contractor_id??null,location_id:f.location_id??d?.location_id??null,physical_local:typeof f.physical_at==='string'?f.physical_at.slice(0,19):d?.physical_local??at,
        contractors:[{id,name:'Afui'}],locations:[{id,name:'Gudang aksesori'}],orders:[],materials:[{...quote,stock:s.stock}],material_count:1,
        history,history_count:matching.length,document:d,
        ...(listed?{history_page:{offset,limit,next_offset:offset+history.length<matching.length?offset+history.length:null,list:{q,status,order}}}:{})}
      return {data:s.invalid?{...w,materials:[{...quote,stock:300}]}:structuredClone(w),error:null}
    }
    if(s.reject)return {data:null,error:{code:'P0001',message:'Stok sudah berubah'}}
    const p=args.p_payload as Record<string,unknown>,key=String(args.p_client_request_id),action=String(args.p_action)
    if(!cache.has(key)){
      s.effects++
      if(action==='DELETE')s.document=null
      else if(action==='REVERSE'){s.document!.status='REVERSED';s.document!.row_version='4'}
      else {
        const item=(p.items as Record<string,string>[])[0],preview=previewAccessoryLine({material_id:id,qty:item.qty,mode:item.mode as 'MANUAL'|'MASTER',manual_price:item.manual_price??''},quote)
        const cents=(preview.amount!+5000n)/10000n,total=`${cents/100n}.${String(cents%100n).padStart(2,'0')}`
        s.document={...documentFixture(),number:String(p.number),status:action==='POST'?'POSTED':'DRAFT',row_version:'3',total,items:[{...documentFixture().items[0],qty:item.qty+'.000000',manual_price:item.manual_price??null,price:(item.manual_price??'36').replace(/(\.\d+)?$/,m=>(m||'.').padEnd(7,'0')),amount:(preview.amount!/1000000n)+'.'+String(preview.amount!%1000000n).padStart(6,'0')}] as ReturnType<typeof documentFixture>['items']}
      }
      cache.set(key,{id:doc,request_id:key,action,status:action==='DELETE'?'DELETED':s.document!.status,row_version:s.document?.row_version??null})
    }
    return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:s.badReceipt?{request_id:key,status:'POSTED'}:cache.get(key),error:null}
  });return s
}
async function prepare(){await change('Nomor nota aksesori','ACC-NEW');await change('Mandor aksesori',id);await change('Gudang aksesori',id);await click('Perbarui harga dan stok');await change('Tambah aksesori',id);await change('Jumlah PCS 1','7');await change('Harga per PCS 1','3,25')}

describe('connected accessory issue',()=>{
  it('keeps the original amount on a reversed note without presenting its old collectible value as a current bill',async()=>{
    const s=server();s.document={...documentFixture(),status:'REVERSED'};Object.assign(s.document.items[0]!,{collectible:'22.75'})
    await mount();await click('Buka ACC-001')
    expect(container.textContent).toContain('Tagihan asal');expect(container.textContent).toContain('Total tagihan asal: Rp 22,75')
    expect(container.textContent).toContain('nota ini tidak lagi ditagih')
    expect(container.textContent).not.toContain('Sisa ditagih');expect(container.textContent).not.toContain('Periksa pembatalan')
    expect(writes()).toHaveLength(0)
  })
  it('opens an exact stock source outside the50-row history through the owning reader without a write or review',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED'}
    const a=structuredClone(recoveryIdentity);Object.assign(a.identity.profile,{authUserId:id});a.identity.permissions=['finance.contractor_accessory.view'];auth.current=a
    const ordinary=client.rpc.getMockImplementation()!,navigate=vi.fn()
    client.rpc.mockImplementation(async(name,args)=>{
      if(name==='erp_cp7_resolve_transaction_source_v1')return{data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:id,source:args.p_source,status:'AVAILABLE',business_DML:false,read_at:'2026-10-03T00:00:00Z',document:{domain:'ACCESSORY_ISSUE',route:'contractor-issue',id:doc,number:'ACC-001',status:'POSTED',revision:'1',focus:null}},error:null}
      const result=await ordinary(name,args)
      if(name==='erp_get_accessory_issue_workspace_v1')return{...result,data:{...result.data,history_count:51,history:Array.from({length:50},(_,i)=>({...result.data.history[0],id:`99999999-9999-4999-8999-${String(i+1).padStart(12,'0')}`,number:`LATEST-${i}`})),
        history_page:{...result.data.history_page,next_offset:50}}}
      return result
    })
    await act(async()=>root.render(<TransactionSourceProvider scope="accessory-source" onNavigate={navigate}><TransactionSourceLink sourceType="CONTRACTOR_MATERIAL_ISSUE_ITEM" sourceId={lineId}/><ConnectedAccessoryIssuePage/></TransactionSourceProvider>));await flush()
    await click('Buka transaksi asal')
    expect(navigate).toHaveBeenCalledWith('contractor-issue')
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_get_accessory_issue_workspace_v1').at(-1)?.[1]).toEqual({p_filters:{query:'',material_query:'',history_status:null,history_order:'SOURCE',history_offset:0,history_limit:50,id:doc}})
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('ACC-001 · POSTED')
    expect(container.querySelector('[aria-label="Riwayat nota aksesori"]')?.textContent).not.toContain('ACC-001')
    expect(container.querySelector('[aria-label="Konfirmasi nota"]')).toBeNull();expect(writes()).toHaveLength(0);expect(s.effects).toBe(0)
  })
  it('does not substitute another document when the exact owning source is missing from its reader',async()=>{
    const s=server();s.document=documentFixture();Object.assign((auth.current as typeof recoveryIdentity).identity.profile,{authUserId:id})
    const ordinary=client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async(name,args)=>{
      if(name==='erp_cp7_resolve_transaction_source_v1')return{data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:id,source:args.p_source,status:'AVAILABLE',business_DML:false,read_at:'2026-10-03T00:00:00Z',document:{domain:'ACCESSORY_ISSUE',route:'contractor-issue',id:doc,number:'ACC-001',status:'DRAFT',revision:'1',focus:null}},error:null}
      const r=await ordinary(name,args);return name==='erp_get_accessory_issue_workspace_v1'&&args.p_filters.id?{...r,data:{...r.data,document:{...r.data.document,id}}}:r
    })
    await act(async()=>root.render(<TransactionSourceProvider scope="accessory-source" onNavigate={()=>{}}><TransactionSourceLink sourceType="CONTRACTOR_MATERIAL_ISSUE_ITEM" sourceId={lineId}/><ConnectedAccessoryIssuePage/></TransactionSourceProvider>));await flush();await click('Buka transaksi asal')
    expect(container.textContent).toContain('Identitas nota tidak cocok.')
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('Status belum dipastikan')
    expect(button('Simpan draft').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('keeps unsent quantities and the selected note unchanged while the server orders the whole history (D17-16)',async()=>{
    const s=server();s.document={...documentFixture(),number:'ACC-10'};s.history=historyRows(['ACC-10','ACC-2','ACC-1'],()=>'DRAFT');s.history[0].id=doc
    await mount();await click('Buka ACC-10');await change('Jumlah PCS 1','9');const before=reads().length
    await change('Urutkan nota aksesori','LABEL_ASC')
    expect(reads().slice(before)).toHaveLength(1)
    expect(reads().at(-1)).toMatchObject({id:doc,history_order:'LABEL_ASC',history_status:null,history_offset:0,history_limit:50,contractor_id:id,location_id:id,material_ids:[id]})
    expect(shown()).toEqual(['ACC-1','ACC-2','ACC-10'])
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('9')
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('ACC-10')
    expect(writes()).toHaveLength(0)
  })
  it('says sort and filter cover every note and shows the count of the whole filtered history (D17-16)',async()=>{
    server();await mount()
    const tools=container.querySelector('[aria-label="Cari, browse, urutkan dan filter nota aksesori"]')!
    expect(tools.textContent).toContain('Urutkan semua hasil');expect(tools.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain; jumlah hasil mengikuti filter yang sama.')
    expect(tools.textContent).not.toContain('halaman yang sedang tampil')
    expect(container.querySelector('[aria-label="Urutkan nota aksesori"]')).not.toBeNull();expect(container.querySelector('[aria-label="Urutkan halaman nota aksesori"]')).toBeNull()
    expect(container.textContent).toContain('0 nota cocok dengan pencarian dan filter; halaman ini menampilkan 0.');expect(container.textContent).not.toContain('hanya berlaku pada daftar yang tampil')
  })
  it('browses the whole history from the first page with every list key reset and keeps unsent form edits (D17-16)',async()=>{
    server();await mount();await prepare();await change('Cari nota aksesori','ACC lama');await change('Status nota aksesori','POSTED');await change('Urutkan nota aksesori','LABEL_DESC')
    expect(reads().at(-1)).toMatchObject({history_status:'POSTED',history_order:'LABEL_DESC',history_offset:0})
    await click('Browse semua')
    const request=reads().at(-1)!
    expect(request).toMatchObject({query:'',id:null,history_status:null,history_order:'SOURCE',history_offset:0,history_limit:50});expect(request).not.toHaveProperty('limit');expect(request).not.toHaveProperty('status')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('7')
    expect(container.querySelector<HTMLSelectElement>('[aria-label="Status nota aksesori"]')!.value).toBe('ALL')
    expect(container.querySelector<HTMLSelectElement>('[aria-label="Urutkan nota aksesori"]')!.value).toBe('SOURCE')
    expect(writes()).toHaveLength(0)
  })
  it('pages through every matching note on the server; a new status or search starts again at the first page (D17-16)',async()=>{
    const s=server();s.history=historyRows(Array.from({length:120},(_,i)=>`ACC-${i+1}`));await mount()
    expect(container.textContent).toContain('120 nota cocok dengan pencarian dan filter; halaman ini menampilkan 50.');expect(button('Nota sebelumnya').disabled).toBe(true)
    await click('Nota berikutnya');expect(reads().at(-1)).toMatchObject({history_offset:50,history_limit:50});expect(shown()[0]).toBe('ACC-51')
    await click('Nota berikutnya');expect(reads().at(-1)!.history_offset).toBe(100);expect(shown()).toHaveLength(20);expect(button('Nota berikutnya').disabled).toBe(true)
    await change('Status nota aksesori','DRAFT');expect(reads().at(-1)).toMatchObject({history_status:'DRAFT',history_offset:0})
    expect(container.textContent).toContain('40 nota cocok dengan pencarian dan filter; halaman ini menampilkan 40.');expect(button('Nota berikutnya').disabled).toBe(true)
    await change('Status nota aksesori','ALL');await click('Nota berikutnya');await change('Cari nota aksesori','acc-11');await act(async()=>button('Cari nota').click());await flush()
    expect(reads().at(-1)).toMatchObject({query:'acc-11',history_status:null,history_offset:0});expect(shown()).toEqual(['ACC-11','ACC-110','ACC-111','ACC-112','ACC-113','ACC-114','ACC-115','ACC-116','ACC-117','ACC-118','ACC-119'])
    expect(writes()).toHaveLength(0)
  })
  it('refuses a history page that is not the one asked for, without showing rows (fail closed)',async()=>{
    const s=server();s.history=historyRows(['ACC-1','ACC-2']);const ordinary=client.rpc.getMockImplementation()!
    const ask={offset:0,limit:50,list:{q:'',status:null,order:'SOURCE'}} as const
    const valid=(await ordinary('erp_get_accessory_issue_workspace_v1',{p_filters:{query:'',material_query:'',history_status:null,history_order:'SOURCE',history_offset:0,history_limit:50,id:null}})).data
    expect(parseAccessoryWorkspace(valid,ask).history_page).toEqual({offset:0,limit:50,next_offset:null,list:ask.list})
    const {history_page:_,...missing}=valid,page=valid.history_page
    for(const bad of [missing,{...valid,history_page:{...page,list:{...page.list,status:'POSTED'}}},{...valid,history_page:{...page,list:{...page.list,order:'LABEL_ASC'}}},
      {...valid,history_page:{...page,list:{...page.list,q:'acc'}}},{...valid,history_page:{...page,offset:50}},{...valid,history_page:{...page,limit:25}},{...valid,history_page:{...page,next_offset:2}},
      {...valid,history_page:{...page,total:'2'}},{...valid,history_page:{...page,list:{...page.list,extra:1}}},{...valid,history_count:3}])expect(()=>parseAccessoryWorkspace(bad,ask)).toThrow()
    expect(()=>parseAccessoryWorkspace(valid)).toThrow('Daftar nota tidak cocok dengan pilihan.')
    expect(()=>parseAccessoryWorkspace({...valid,history_page:{...page,list:{...page.list,status:'POSTED'}}},{...ask,list:{...ask.list,status:'POSTED'}})).toThrow('Daftar nota tidak cocok dengan pilihan.')
    client.rpc.mockImplementation(async(name,args)=>{const r=await ordinary(name,args);return name==='erp_get_accessory_issue_workspace_v1'?{...r,data:{...r.data,history_page:{...r.data.history_page,list:{...r.data.history_page.list,order:'SOURCE'}}}}:r})
    await mount();await change('Urutkan nota aksesori','LABEL_DESC')
    expect([...container.querySelectorAll('[role="alert"]')].map(a=>a.textContent)).toContain('Daftar nota tidak cocok dengan pilihan.');expect(shown()).toEqual([]);expect(writes()).toHaveLength(0)
  })
  it('retires old totals and history on a failed refresh while preserving unsent quantity and price',async()=>{
    server();await mount();await prepare();expect(container.textContent).toContain('Rp 22,75')
    client.rpc.mockImplementation(async()=>({data:null,error:{code:'08006',message:'Read unavailable'}}))
    await click('Muat ulang')
    expect(container.textContent).not.toContain('Rp 22,75');expect(container.textContent).toContain('Total tagihan: —')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('7')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Harga per PCS 1"]')!.value).toBe('3,25')
    expect(button('Simpan draft').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('keeps preparation inert and posts the latest edited quantity and exact manual price',async()=>{
    server();await mount();await prepare();expect(writes()).toHaveLength(0)
    expect(container.textContent).toContain('Rp 22,75');await click('Simpan draft')
    expect(writes()[0][1].p_action).toBe('SAVE_DRAFT');await change('Jumlah PCS 1','8');await click('Periksa pengesahan');expect(writes()).toHaveLength(1)
    await click('Sahkan nota');const p=writes()[1][1].p_payload
    expect(p.id).toBe(doc);expect(p.expected_version).toBe('3');expect(p.items).toEqual([{material_id:id,qty:'8',mode:'MANUAL',manual_price:'3.25'}]);expect(p.physical_at).toBe(at+'+07:00')
    expect(container.textContent).toContain('POSTED');expect(container.querySelector('[aria-label="Jumlah PCS 1"]')).toBeNull()
  })
  it('clears review when quantity changes and refuses fractional pcs without clamping',async()=>{
    server();await mount();await prepare();await click('Periksa pengesahan');await change('Jumlah PCS 1','7.5')
    expect(container.querySelector('[aria-label="Konfirmasi nota"]')).toBeNull();expect(button('Simpan draft').disabled).toBe(true)
    expect((container.querySelector('[aria-label="Jumlah PCS 1"]') as HTMLInputElement).value).toBe('7.5');expect(writes()).toHaveLength(0)
  })
  it('uses master pricing only when exact and does not convert seven pcs into a rounded package fraction',async()=>{
    server();await mount();await prepare();await change('Dasar harga 1','MASTER');expect(button('Simpan draft').disabled).toBe(true)
    await change('Jumlah PCS 1','12');expect(container.textContent).toContain('Rp 36,00');await click('Simpan draft')
    expect(writes()[0][1].p_payload.items).toEqual([{material_id:id,qty:'12',mode:'MASTER',price_version_id:lineId,factor:'12.000000'}])
  })
  it('does not require a nonzero manual price and treats empty price as incomplete',async()=>{
    server();await mount();await prepare();await change('Harga per PCS 1','');expect(button('Simpan draft').disabled).toBe(true)
    await change('Harga per PCS 1','0');expect(button('Simpan draft').disabled).toBe(false);await click('Simpan draft');expect(writes()[0][1].p_payload.items[0].manual_price).toBe('0')
  })
  it('requires a fresh quote after mandor, location or physical time changes',async()=>{
    server();await mount();await prepare();await change('Waktu ambil aksesori','2026-09-21T10:15:00')
    expect(button('Simpan draft').disabled).toBe(true);await click('Perbarui harga dan stok');expect(button('Simpan draft').disabled).toBe(false)
    await click('Simpan draft');expect(writes()[0][1].p_payload.physical_at).toBe('2026-09-21T10:15:00+07:00')
  })
  it('allows an overstock draft, blocks its posting and copies the visible balance explicitly',async()=>{
    const s=server();s.stock='7.000000';await mount();await prepare();await change('Jumlah PCS 1','8')
    expect(button('Simpan draft').disabled).toBe(false);expect(button('Periksa pengesahan').disabled).toBe(true)
    await click('Ambil sisa');expect((container.querySelector('[aria-label="Jumlah PCS 1"]') as HTMLInputElement).value).toBe('7');expect(writes()).toHaveLength(0)
  })
  it.each(['SAVE_DRAFT','POST'])('recovers a lost %s reply with the identical request after remount',async action=>{
    const s=server();await mount();await prepare();s.lose=true
    if(action==='POST'){await click('Periksa pengesahan');await click('Sahkan nota')}else await click('Simpan draft')
    const original=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE?.id).toBe(original.p_client_request_id)
    await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi')
    expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE).toBeUndefined()
  })
  it('requires reason for reversal and keeps bigint versions exact',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED',row_version:'9007199254740993'};await mount();await click('Buka ACC-001')
    expect(button('Periksa pembatalan').disabled).toBe(true);await change('Alasan pembatalan nota','Salah pengambilan');await click('Periksa pembatalan');await click('Sahkan pembatalan nota')
    expect(writes()[0][1].p_payload).toEqual({id:doc,expected_version:'9007199254740993',reason:'Salah pengambilan'})
  })
  it('locks a posted source that is already linked to payroll',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED',payroll_locked:true};await mount();await click('Buka ACC-001')
    expect(button('Periksa pembatalan').disabled).toBe(true);expect(container.textContent).toContain('payroll aktif');expect(writes()).toHaveLength(0)
  })
  it('keeps form edits and the original draft version through refresh',async()=>{
    const s=server();s.document=documentFixture();await mount();await click('Buka ACC-001');await change('Jumlah PCS 1','9');s.document.row_version='2'
    await click('Muat ulang');await click('Simpan draft');expect(writes()[0][1].p_payload.expected_version).toBe('1');expect(writes()[0][1].p_payload.items[0].qty).toBe('9')
  })
  it('keeps uncertainty on malformed mutation receipts and does not issue a fresh write',async()=>{
    const s=server();s.badReceipt=true;await mount();await prepare();await click('Simpan draft')
    expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE).toBeDefined();expect(button('Simpan draft').disabled).toBe(true)
  })
  it('shares recovery exclusion with other writing domains',async()=>{
    server();const e={action:'REGISTER',payload:{material_id:id},expectedVersion:null,id:doc,createdAt:new Date().toISOString()}
    persistProductionEnvelope('disposable:actor-1','POCKET_FABRIC',{...e,fingerprint:JSON.stringify({action:e.action,payload:e.payload,expectedVersion:null})})
    await mount();expect(button('Nota baru').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('denies reads without permission and preserves view-only access without write buttons',async()=>{
    server();const a=auth.current as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.contractor_accessory.view');await mount();expect(client.rpc).not.toHaveBeenCalled()
    a.identity.permissions=['finance.contractor_accessory.view'];await act(async()=>root.render(<ConnectedAccessoryIssuePage/>));await flush()
    expect(button('Nota baru').disabled).toBe(true);expect([...container.querySelectorAll('button')].some(b=>b.textContent==='Simpan draft')).toBe(false)
  })
  it('refuses malformed stock and inconsistent posted totals without simulated fallback',async()=>{
    const s=server();s.invalid=true;await mount();expect(container.textContent).toContain('Stok aksesori tidak valid');expect(writes()).toHaveLength(0)
    s.invalid=false;s.document=documentFixture();await click('Muat ulang');const call=client.rpc.mock.calls.find(([n])=>n==='erp_get_accessory_issue_workspace_v1')!
    const valid=(await client.rpc('erp_get_accessory_issue_workspace_v1',{...call[1],p_filters:{id:doc}})).data
    expect(parseAccessoryWorkspace(valid).document?.total).toBe('22.75');expect(()=>parseAccessoryWorkspace({...valid,document:{...valid.document,total:'22.76'}})).toThrow('Total nota')
  })
})
