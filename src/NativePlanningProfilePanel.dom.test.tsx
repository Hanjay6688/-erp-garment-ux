// @vitest-environment jsdom
import{act}from'react'
import{createRoot,type Root}from'react-dom/client'
import{beforeEach,afterEach,it,expect,vi,type Mock}from'vitest'
import NativePlanningProfilePanel from'./NativePlanningProfilePanel'
import{recoveryIdentity}from'../tests/fixtures/productionRecovery'
import{demandRoot,demandSize,demandRequest}from'../tests/fixtures/nativeDemandHistory'
import{profileWire,baselineWire,unifiedBaselineWire,planningConfig,planningQuery,planningId}from'../tests/fixtures/nativePlanningProfile'
import{persistPlanningRequest,planningPayload,parsePlanningProfile,readPlanningRequest}from'./nativePlanningProfile'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const product={rootId:demandRoot,sizeId:demandSize,targetKey:demandRoot+':'+demandSize,sku:'SKU-NATIVE-WIRE',productName:'Celana ukuran M',active:true,physical:'100',reserved:'24',available:'76',gross:'0',returns:'0',availableDays:0,unknownDays:1,stockoutDays:0,trainingAvailable:false}
let root:Root,container:HTMLDivElement,start:Mock<()=>void>,end:Mock<()=>void>,close:Mock<()=>void>
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});a.identity.permissions.push('master.product.view','master.product.manage','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container);start=vi.fn();end=vi.fn();close=vi.fn()})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(query=planningQuery){await act(async()=>root.render(<NativePlanningProfilePanel product={product} query={query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;await act(async()=>b.click())}
async function choose(label:string,value:string){const s=container.querySelector<HTMLSelectElement>(`[aria-label="${label}"]`)!;expect(s).toBeTruthy();await act(async()=>{s.value=value;s.dispatchEvent(new Event('change',{bubbles:true}))})}
it('saves one explicit variation buffer and recovers the same policy/UUID after response loss despite a newer profile',async()=>{
 const own=profileWire(true)as any;Object.assign(own.rows[0].config,{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,buffer_days:'2'})
 let writes=0,newer=false
 client.rpc.mockImplementation(async(name:string,args:any)=>{
  if(name==='erp_cp7_get_planning_profiles_v1'){const w=structuredClone(own);if(newer)w.rows[0].revision='2';return{data:w,error:null}}
  writes++;return writes===1?{data:null,error:Error('reply lost')}:{data:{...outcome(args.p_request),revision:'2'},error:null}
 })
 await render();await choose('Cara menghitung cadangan','STATISTICAL');await choose('Tingkat layanan target','0.95');await fill('Alasan aturan target','Pakai variasi yang diperiksa')
 expect(container.querySelector('[aria-label="Cadangan waktu (hari kalender)"]')).toBeNull();await click('Simpan aturan target')
 const sent=structuredClone(client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_planning_profile_v1')![1])
 expect(sent.p_payload.config).toMatchObject({buffer_mode:'STATISTICAL',service_level:'0.95',buffer_days:null,mean_mode:'OWN_AVAILABLE_HISTORY'})
 expect(readPlanningRequest(scope).pending?.payload.config).toEqual(sent.p_payload.config)
 newer=true;await act(async()=>root.unmount());root=createRoot(container);await render();await click('Ulangi simpan aturan yang sama')
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_planning_profile_v1')[1][1]).toEqual(sent)
 expect(readPlanningRequest(scope).pending).toBeNull();expect(container.textContent).toContain('Aturan tersimpan')
})
it('does not invent a service target and keeps a dirty statistical choice until the user adopts the newer profile',async()=>{
 const own=profileWire(true)as any;Object.assign(own.rows[0].config,{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null})
 client.rpc.mockResolvedValue({data:own,error:null});await render();await choose('Cara menghitung cadangan','STATISTICAL')
 expect(container.querySelector<HTMLSelectElement>('[aria-label="Tingkat layanan target"]')!.value).toBe('')
 await choose('Tingkat layanan target','0.95')
 const next=structuredClone(own);next.rows[0].revision='2';Object.assign(next.rows[0].config,{buffer_mode:'STATISTICAL',service_level:'0.99',buffer_days:null})
 client.rpc.mockResolvedValue({data:next,error:null});await click('Muat aturan terbaru')
 expect(container.querySelector<HTMLSelectElement>('[aria-label="Tingkat layanan target"]')!.value).toBe('0.95')
 expect(container.textContent).toContain('Isianmu masih ada');await click('Gunakan aturan terbaru')
 expect(container.querySelector<HTMLSelectElement>('[aria-label="Tingkat layanan target"]')!.value).toBe('0.99')
})
it('shows separate authoritative trigger, horizon demand and one buffer without treating target as permission to start production',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire(true):unifiedBaselineWire(args.p_request),error:null}))
 await render();await click('Hitung target dari ERP')
 const detail=container.querySelector('.native-target-breakdown')!
 expect(detail.textContent).toContain('Ambang kebutuhan selama waktu produksi30 PCS')
 expect(detail.textContent).toContain('Target sampai pemeriksaan berikutnya100 PCS')
 expect(detail.textContent).toContain('Kebutuhan selama jarak pemeriksaan70 PCS')
 expect(detail.textContent).toContain('Cadangan yang sudah masuk target0 PCS')
 expect(detail.textContent).toContain('Cadangan dihitung satu kali')
 expect(container.textContent).toContain('Jumlah yang masih perlu diproduksi belum diketahui')
})
async function fill(label:string,value:string){const e=container.querySelector<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>(`[aria-label="${label}"]`)??([...container.querySelectorAll('label')].find(x=>x.textContent?.startsWith(label))?.querySelector('select')as HTMLSelectElement);await act(async()=>{const prototype=e instanceof HTMLSelectElement?HTMLSelectElement.prototype:e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event(e instanceof HTMLSelectElement?'change':'input',{bubbles:true}))})}
function outcome(request:string){return{contract_version:'cp7.planning-profile-outcome.v1',request_id:request,root_id:demandRoot,profile_id:planningId,revision:'1',quality:'SELECTED_ASSUMPTION'}}
const scope='cp6-disposable:actor-1:'+demandRoot
it('reads native identity with blank assumptions and makes no default production recommendation',async()=>{client.rpc.mockResolvedValue({data:profileWire(false),error:null});await render();expect(container.textContent).toContain('Belum ada aturan yang diperiksa');expect((container.querySelector('[aria-label="Waktu proses pilihan (hari kalender)"]')as HTMLInputElement).value).toBe('');expect((container.querySelector('[aria-label="Minimal hari riwayat tersedia"]')as HTMLInputElement).value).toBe('');expect(container.querySelector('.native-planning-result')).toBeNull();expect(start).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1);expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_planning_profiles_v1',{p_roots:[demandRoot]}])})
it('offers a blank PCS multiple for this product/size and saves only the explicitly entered value',async()=>{
 client.rpc.mockImplementation(async(name:string,a:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire(false):outcome(a.p_request),error:null}))
 await render();const field=container.querySelector('[aria-label="Kelipatan produksi produk/ukuran ini (PCS)"]') as HTMLInputElement
 expect(field).toBeTruthy();expect(field.value).toBe('')
 await fill('Minimal hari riwayat tersedia','1');await fill('Kelipatan produksi produk/ukuran ini (PCS)','12');await fill('Alasan aturan target','Kelipatan ditinjau untuk produk/ukuran ini');await click('Simpan aturan target')
 const sent=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_planning_profile_v1')![1]
 expect(sent.p_payload.root_id).toBe(demandRoot);expect(sent.p_payload.product_version_id).toBe(profileWire(false).rows[0].product_version_id)
 expect(sent.p_payload.config.rounding_multiple).toBe('12');expect(container.textContent).toContain('Aturan tersimpan')
})
it('replays saved metadata UUID/payload after committed response loss and remount despite a newer profile read',async()=>{
 let saved=false;client.rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire(saved):null,error:name==='erp_cp7_save_planning_profile_v1'?(saved=true,Error('reply lost')):null}));await render();await fill('Dasar permintaan','SELECTED_MANUAL');await fill('Permintaan pilihan PCS per hari','10');await fill('Minimal hari riwayat tersedia','20');await fill('Waktu proses pilihan (hari kalender)','3');await fill('Jarak pemeriksaan (hari kalender)','7');await fill('Cadangan waktu (hari kalender)','0');await fill('Alasan aturan target','explicit review');await click('Simpan aturan target');const original=structuredClone(client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_planning_profile_v1')!);expect(readPlanningRequest(scope).pending?.id).toBe(original[1].p_request)
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire(true):outcome(args.p_request),error:null}));await render();await click('Ulangi simpan aturan yang sama');expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_planning_profile_v1')[1]).toEqual(original);expect(localStorage.length).toBe(0);expect(container.textContent).toContain('Aturan tersimpan')
})
it('replays an omitted legacy multiple unchanged after reopening against a newer explicit multiple',async()=>{
 const request={id:demandRequest,payload:planningPayload(parsePlanningProfile(profileWire(false),demandRoot,demandSize),planningConfig,'legacy reviewed request')}
 expect(Object.hasOwn(request.payload.config,'rounding_multiple')).toBe(false)
 persistPlanningRequest(scope,request)
 const newer=profileWire(true);Object.assign(newer.rows[0].config!,{rounding_multiple:'12'})
 client.rpc.mockImplementation(async(name:string,a:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?newer:outcome(a.p_request),error:null}))
 await render();await click('Ulangi simpan aturan yang sama')
 const sent=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_planning_profile_v1')![1]
 expect(sent).toEqual({p_payload:request.payload,p_request:request.id})
 expect(Object.hasOwn(sent.p_payload.config,'rounding_multiple')).toBe(false)
 expect(localStorage.length).toBe(0);expect(container.textContent).toContain('Aturan tersimpan')
})
it('clears an explicit multiple to null at the reviewed revision and keeps readback blank after remount',async()=>{
 let saved=false
 const selected=profileWire(true);Object.assign(selected.rows[0].config!,{rounding_multiple:'12'})
 const cleared=profileWire(true);cleared.rows[0].revision='2';Object.assign(cleared.rows[0].config!,{rounding_multiple:null})
 client.rpc.mockImplementation(async(name:string,a:{p_request:string})=>{
  if(name==='erp_cp7_get_planning_profiles_v1')return{data:saved?cleared:selected,error:null}
  saved=true;return{data:{...outcome(a.p_request),revision:'2'},error:null}
 })
 await render();expect((container.querySelector('[aria-label="Kelipatan produksi produk/ukuran ini (PCS)"]')as HTMLInputElement).value).toBe('12')
 await fill('Kelipatan produksi produk/ukuran ini (PCS)','');await fill('Alasan aturan target','Kosongkan pilihan yang belum ditetapkan');await click('Simpan aturan target')
 const sent=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_planning_profile_v1')![1]
 expect(sent.p_payload.expected_revision).toBe('1');expect(sent.p_payload.config.rounding_multiple).toBeNull()
 await click('Muat aturan terbaru');await click('Gunakan aturan terbaru')
 expect((container.querySelector('[aria-label="Kelipatan produksi produk/ukuran ini (PCS)"]')as HTMLInputElement).value).toBe('')
 await act(async()=>root.unmount());root=createRoot(container);await render()
 expect((container.querySelector('[aria-label="Kelipatan produksi produk/ukuran ini (PCS)"]')as HTMLInputElement).value).toBe('');expect(localStorage.length).toBe(0)
})
it('keeps dirty inputs bound to their reviewed revision after a fresh source revision changes',async()=>{client.rpc.mockResolvedValue({data:profileWire(),error:null});await render();await fill('Permintaan pilihan PCS per hari','15');const newer=profileWire();newer.rows[0].revision='2';newer.rows[0].config!.daily_pcs='20';client.rpc.mockResolvedValue({data:newer,error:null});await click('Muat aturan terbaru');expect((container.querySelector('[aria-label="Permintaan pilihan PCS per hari"]')as HTMLInputElement).value).toBe('15');expect(container.textContent).toContain('Isianmu masih ada');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan aturan target')!.disabled).toBe(true);await click('Gunakan aturan terbaru');expect((container.querySelector('[aria-label="Permintaan pilihan PCS per hari"]')as HTMLInputElement).value).toBe('20')})
it('recovers a lost target reply with the identical query/UUID then checks the recovered period',async()=>{
 client.rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire():null,error:name==='erp_cp7_capture_baseline_v1'?Error('reply lost'):null}));await render();await click('Hitung target dari ERP');const original=structuredClone(client.rpc.mock.calls.find(([name])=>name==='erp_cp7_capture_baseline_v1')!);await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire():baselineWire(args.p_request??original[1].p_request),error:null}));await render({...planningQuery,from_date:'2026-09-28'});await click('Ulangi permintaan target yang sama');expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_capture_baseline_v1')[1]).toEqual(original);expect(container.querySelector('.native-planning-result')?.textContent).toContain('100 PCS');await click('Periksa sumber target');expect(container.querySelector('.native-planning-result')?.textContent).toContain('100 PCS');expect(localStorage.length).toBe(0)
})
it('retires old target facts on current native access denial',async()=>{client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire():baselineWire(args.p_request),error:null}));await render();await click('Hitung target dari ERP');expect(container.querySelector('.native-planning-result')).toBeTruthy();client.rpc.mockResolvedValue({data:null,error:{status:403,message:'CP7_ACCESS_DENIED'}});await click('Periksa sumber target');expect(container.querySelector('.native-planning-result')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()})
it('does not repaint a held reply after close and releases parent refresh without erasing the UUID',async()=>{client.rpc.mockResolvedValueOnce({data:profileWire(),error:null});await render();let release:(x:unknown)=>void=()=>{};client.rpc.mockImplementation(()=>new Promise(r=>release=r));await click('Hitung target dari ERP');const request=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_capture_baseline_v1')![1].p_request;await click('Tutup aturan target');expect(close).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(2);await act(async()=>release({data:baselineWire(request),error:null}));expect(container.querySelector('.native-planning-result')).toBeNull();expect(localStorage.length).toBe(1)})
it('preserves corrupt recovery and refuses replacing it with a new request',async()=>{localStorage.setItem('erp.cp7.planning-profile-request.v1:'+scope,'broken');client.rpc.mockResolvedValue({data:profileWire(false),error:null});await render();expect(container.textContent).toContain('Permintaan simpan aturan belum bisa dibaca');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Hitung target dari ERP')!.disabled).toBe(true);expect(localStorage.getItem('erp.cp7.planning-profile-request.v1:'+scope)).toBe('broken')})
it('keeps a cached metadata request after current manage permission denial',async()=>{const request={id:demandRequest,payload:planningPayload(parsePlanningProfile(profileWire(false),demandRoot,demandSize),planningConfig,'review')};persistPlanningRequest(scope,request);client.rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_planning_profiles_v1'?profileWire(true):null,error:name==='erp_cp7_save_planning_profile_v1'?{status:403,message:'CP7_POLICY_ACCESS_DENIED'}:null}));await render();await click('Ulangi simpan aturan yang sama');expect(readPlanningRequest(scope).pending).toEqual(request);expect(container.querySelector('.native-planning-result')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()})
