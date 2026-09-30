import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {readNativeDemandRequest,persistNativeDemandRequest,clearNativeDemandRequest,nativeDemandRequestKey,type NativeDemandQuery} from './nativeDemandHistory'
import {parseNativeSupply,parseScheduleWorkspace,parseNativeNetting,schedulePayload,checkScheduleOutcome,readScheduleRequest,persistScheduleRequest,clearScheduleRequest,scheduleRequestKey,instantToWibInput,wibInputToInstant,type NativeSupply,type ScheduleWorkspace,type ScheduleConfig,type ScheduleRequest,type NativeNetting} from './nativeProductionPlanning'
import './native-production-planning.css'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
type WorkInput={key:string;target:string;qty:string;numerator:string;denominator:string;steps:{stage:string;minutes:string}[]}
type WindowInput={key:string;start:string;end:string;load:string;originalStart:string|null;originalEnd:string|null}
type Form={centre:string;through:string;originalThrough:string|null;unit:string;windows:WindowInput[];work:WorkInput[];reason:string}
const permissions=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
const stageNames:Record<string,string>={CUT_UNASSIGNED:'Belum dijahit',SEWING_ACTIVE:'Sedang dijahit',SEWING_UNRESOLVED:'Jahit perlu pemeriksaan',LAUNDRY_OUTSTANDING:'Laundry',AWAIT_QC:'Menunggu QC',SEWING:'Jahit',LAUNDRY:'Laundry',QC:'QC',REWORK:'Perbaikan',REWASH:'Cuci ulang'}
function blankWindow():WindowInput{return{key:crypto.randomUUID(),start:'',end:'',load:'',originalStart:null,originalEnd:null}}
function formFrom(w:ScheduleWorkspace):Form{
 const c=w.planState==='SELECTED_ASSUMPTIONS'&&w.state==='UNCHANGED'?w.config:null
 return{centre:c?.work_centre_key??'',through:c?instantToWibInput(c.through_at):'',originalThrough:c?.through_at??null,unit:c?.unit_minutes??'',reason:'',
  windows:c?c.windows.map(x=>({key:x.key,start:instantToWibInput(x.starts_at),end:instantToWibInput(x.ends_at),load:x.other_load_minutes??'',originalStart:x.starts_at,originalEnd:x.ends_at})):[blankWindow()],
  work:w.requirements.map(r=>{const p=c?.positions.find(p=>p.position_key===r.key);return{key:r.key,target:p?.target_key??'',qty:p?.eligible_input_pcs??r.remaining,numerator:p?.yield_numerator??'',denominator:p?.yield_denominator??'',steps:r.route.map(stage=>({stage,minutes:p?.remaining_steps.find(s=>s.stage===stage)?.remaining_minutes??''}))}})}
}
function configFrom(f:Form):ScheduleConfig{return{basis:'SELECTED_ASSUMPTIONS',resource_scope:'SINGLE_HOMOGENEOUS_SELECTED_CENTRE',work_centre_key:f.centre,through_at:wibInputToInstant(f.through,f.originalThrough),unit_minutes:f.unit===''?null:f.unit,
 windows:f.windows.map(w=>({key:w.key,starts_at:wibInputToInstant(w.start,w.originalStart),ends_at:wibInputToInstant(w.end,w.originalEnd),other_load_minutes:w.load===''?null:w.load})),
 positions:f.work.map(p=>({position_key:p.key,target_key:p.target===''?null:p.target,eligible_input_pcs:p.qty,yield_numerator:p.numerator===''?null:p.numerator,yield_denominator:p.denominator===''?null:p.denominator,remaining_steps:p.steps.map(s=>({stage:s.stage,remaining_minutes:s.minutes===''?null:s.minutes}))}))}}
export default function NativeProductionPlanningPanel(props:Props){const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!permissions.every(p=>identity.permissions.includes(p)))return null;return<Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>}
function Workspace({query,onSourceReadStart,onSourceReadEnd,onClose}:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi jadwal belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope=runtime.projectRef+':'+identity.profile.id,supplyScope='supply:'+scope,netScope='netting:'+scope,seq=useRef(0),active=useRef(false),formBound=useRef(false)
 const[supply,setSupply]=useState<NativeSupply|null>(null),[workspace,setWorkspace]=useState<ScheduleWorkspace|null>(null),[base,setBase]=useState<ScheduleWorkspace|null>(null),[form,setForm]=useState<Form|null>(null),[net,setNet]=useState<NativeNetting|null>(null)
 const[supplyRecovery,setSupplyRecovery]=useState(()=>readNativeDemandRequest(supplyScope)),[netRecovery,setNetRecovery]=useState(()=>readNativeDemandRequest(netScope)),[saveRecovery,setSaveRecovery]=useState(()=>readScheduleRequest(scope))
 const[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[search,setSearch]=useState('')
 const canSave=identity.permissions.includes('master.product.manage')
 const adopt=useCallback((w:ScheduleWorkspace)=>{setBase(w);setForm(formFrom(w));setMessage('')},[])
 const begin=()=>{const n=++seq.current;active.current=true;setBusy(true);setSupply(null);setWorkspace(null);setNet(null);setError('');setMessage('');onSourceReadStart();return n}
 const end=(n:number)=>{if(n===seq.current){active.current=false;setBusy(false);onSourceReadEnd()}}
 useEffect(()=>()=>{++seq.current;if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||[nativeDemandRequestKey(supplyScope),nativeDemandRequestKey(netScope),scheduleRequestKey(scope)].includes(e.key)){++seq.current;active.current=false;setBusy(false);setSupply(null);setWorkspace(null);setNet(null);setSupplyRecovery(readNativeDemandRequest(supplyScope));setNetRecovery(readNativeDemandRequest(netScope));setSaveRecovery(readScheduleRequest(scope));onSourceReadStart();onSourceReadEnd()}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope,supplyScope,netScope,onSourceReadStart,onSourceReadEnd])
 const loadSupply=async(retry=false)=>{
  const n=begin()
  try{const held=readNativeDemandRequest(supplyScope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan stok proses tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan stok proses yang sama terlebih dahulu.')
   const request=retry?held.pending!:{id:crypto.randomUUID(),q:query};if(!retry)persistNativeDemandRequest(supplyScope,request);setSupplyRecovery(readNativeDemandRequest(supplyScope))
   const r=await client.rpc('erp_cp7_capture_production_supply_v1',{p_query:request.q,p_request:request.id});if(n!==seq.current)return;if(r.error)throw r.error;const s=parseNativeSupply(r.data,request.q);if(s.requestId!==request.id)throw Error('Permintaan stok proses server berubah.')
   clearNativeDemandRequest(supplyScope,request.id);setSupplyRecovery(readNativeDemandRequest(supplyScope))
   const reply=await client.rpc('erp_cp7_get_production_schedule_v1',{p_run:s.runId});if(n!==seq.current)return;if(reply.error)throw reply.error;const w=parseScheduleWorkspace(reply.data,s)
   setSupply({...s,state:w.state});setWorkspace(w);if(!formBound.current){formBound.current=true;adopt(w)}
  }catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const checkSupply=async()=>{
  if(!supply)return;const previous=supply,n=begin()
  try{const r=await client.rpc('erp_cp7_read_production_supply_v1',{p_run:previous.runId});if(n!==seq.current)return;if(r.error)throw r.error;const s=parseNativeSupply(r.data,previous.baseline.query);if(s.runId!==previous.runId||s.sourceHash!==previous.sourceHash)throw Error('Arsip stok proses server berubah.')
   const reply=await client.rpc('erp_cp7_get_production_schedule_v1',{p_run:s.runId});if(n!==seq.current)return;if(reply.error)throw reply.error;const w=parseScheduleWorkspace(reply.data,s);setSupply({...s,state:w.state});setWorkspace(w)
  }catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const save=async(retry=false)=>{
  if(!canSave)return;const n=begin()
  try{const held=readScheduleRequest(scope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan jadwal tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan jadwal yang sama terlebih dahulu.')
   const request:ScheduleRequest=retry?held.pending!:{id:crypto.randomUUID(),payload:schedulePayload(base!,configFrom(form!),form!.reason)};if(!retry)persistScheduleRequest(scope,request);setSaveRecovery(readScheduleRequest(scope))
   const r=await client.rpc('erp_cp7_save_production_schedule_v1',{p_payload:request.payload,p_request:request.id});if(n!==seq.current)return;if(r.error)throw r.error;checkScheduleOutcome(r.data,request);clearScheduleRequest(scope,request.id);setSaveRecovery(readScheduleRequest(scope));setMessage('Jadwal tersimpan. Ambil sumber terbaru untuk memeriksa versi jadwal dan menghitung kekurangan.')
  }catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const calculate=async(retry=false)=>{
  const n=begin()
  try{const held=readNativeDemandRequest(netScope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan kekurangan tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan kekurangan yang sama terlebih dahulu.')
   const request=retry?held.pending!:{id:crypto.randomUUID(),q:query};if(!retry)persistNativeDemandRequest(netScope,request);setNetRecovery(readNativeDemandRequest(netScope))
   const r=await client.rpc('erp_cp7_capture_netting_v1',{p_query:request.q,p_request:request.id});if(n!==seq.current)return;if(r.error)throw r.error;const result=parseNativeNetting(r.data,request.q);if(result.requestId!==request.id)throw Error('Permintaan kekurangan server berubah.');clearNativeDemandRequest(netScope,request.id);setNetRecovery(readNativeDemandRequest(netScope));setNet(result)
  }catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const checkNet=async()=>{
  if(!net)return;const previous=net,n=begin()
  try{const r=await client.rpc('erp_cp7_read_netting_v1',{p_run:previous.runId});if(n!==seq.current)return;if(r.error)throw r.error;const result=parseNativeNetting(r.data,previous.query);if(result.runId!==previous.runId||result.sourceHash!==previous.sourceHash)throw Error('Arsip kekurangan server berubah.');setNet(result)}catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const close=()=>{++seq.current;if(active.current){active.current=false;onSourceReadEnd()}onClose()}
 const pending=Boolean(supplyRecovery.pending||supplyRecovery.error||netRecovery.pending||netRecovery.error||saveRecovery.pending||saveRecovery.error)
 const stale=Boolean(workspace&&base&&(workspace.state!=='UNCHANGED'||workspace.sourceHash!==base.sourceHash||workspace.revision!==base.revision))
 const edit=(change:Partial<Form>)=>setForm(f=>f?{...f,...change}:f)
 const editWork=(key:string,change:Partial<WorkInput>)=>setForm(f=>f?{...f,work:f.work.map(p=>p.key===key?{...p,...change}:p)}:f)
 const editWindow=(key:string,change:Partial<WindowInput>)=>setForm(f=>f?{...f,windows:f.windows.map(w=>w.key===key?{...w,...change}:w)}:f)
 const qty=(value:string|null)=>value===null?'Belum diketahui':numberText(value)+' PCS'
 const rows=net?.rows.filter(r=>`${r.sku} ${r.productName}`.toLowerCase().includes(search.toLowerCase()))??[]
 return<section className="native-production panel" aria-label="Jadwal dan kekurangan produksi"><header><div><div className="eyebrow">PERENCANAAN SELURUH PRODUK</div><h2>Jadwal & kekurangan produksi</h2><p>Stok proses dibaca sekaligus untuk seluruh produk. Pekerjaan pelanggan ikut memakai waktu kerja.</p></div><button onClick={close}>Tutup jadwal produksi</button></header>
  <div className="native-production-actions"><button disabled={busy||pending} onClick={()=>void loadSupply()}>Ambil stok proses terbaru</button>{supply?<button disabled={busy||pending} onClick={()=>void checkSupply()}>Periksa sumber stok proses</button>:null}<button disabled={busy||pending||Boolean(message)} onClick={()=>void calculate()}>Hitung kekurangan seluruh produk</button></div>
  {busy?<p role="status">Memeriksa stok proses, jadwal, dan sumber ERP…</p>:null}{error||supplyRecovery.error||netRecovery.error||saveRecovery.error?<p role="alert">{error||supplyRecovery.error||netRecovery.error||saveRecovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {supplyRecovery.pending?<div role="status"><p>Hasil ambil stok proses belum dipastikan.</p><button disabled={busy} onClick={()=>void loadSupply(true)}>Ulangi stok proses yang sama</button></div>:null}{netRecovery.pending?<div role="status"><p>Hasil hitung kekurangan belum dipastikan.</p><button disabled={busy} onClick={()=>void calculate(true)}>Ulangi kekurangan yang sama</button></div>:null}{saveRecovery.pending?<div role="status"><p>Hasil simpan jadwal belum dipastikan.</p><button disabled={busy||!canSave} onClick={()=>void save(true)}>Ulangi simpan jadwal yang sama</button></div>:null}
  {workspace?<p className={workspace.state==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>{workspace.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip lama: ambil stok proses terbaru.'} Diambil {formatCp6WibDateTime(workspace.capturedAt)} · jadwal versi {workspace.revision}.</p>:null}
  {stale?<p role="alert">Sumber atau versi jadwal berubah. Isianmu masih ada. Ambil sumber terbaru, lalu gunakan sumber terbaru sebelum menyimpan.</p>:null}
  {workspace&&base&&(stale||Boolean(message)||workspace.revision!==base.revision)?<button disabled={busy||pending||workspace.state!=='UNCHANGED'} onClick={()=>adopt(workspace)}>Gunakan sumber jadwal terbaru</button>:null}
  {supply&&!supply.complete?<p role="alert">Jumlah stok proses belum dapat dicocokkan. Jadwal belum bisa disimpan.</p>:null}
  {form&&base?<form onSubmit={e=>{e.preventDefault();void save()}}><fieldset disabled={busy||pending||!canSave}><legend>Waktu kerja dan perkiraan hasil yang diperiksa</legend><p>Kosong berarti belum diketahui. Isi 0 hanya jika memang sudah diperiksa tidak ada beban lain. Waktu sisa mencakup seluruh pekerjaan pada antrean ini.</p>
   <div className="native-production-fields"><label>Tempat kerja pilihan<input aria-label="Tempat kerja pilihan" value={form.centre} onChange={e=>edit({centre:e.target.value})} required/></label><label>Batas jadwal (WIB)<input aria-label="Batas jadwal WIB" type="datetime-local" step="1" value={form.through} onChange={e=>edit({through:e.target.value})} required/></label><label>Waktu untuk 1 PCS baru (menit)<input aria-label="Waktu satu PCS baru" inputMode="decimal" placeholder="Belum diketahui" value={form.unit} onChange={e=>edit({unit:e.target.value})}/></label></div>
   {form.windows.map((w,i)=><div key={w.key} className="native-production-window"><h3>Waktu kerja {i+1}</h3><label>Mulai (WIB)<input aria-label={`Mulai kerja ${i+1} WIB`} type="datetime-local" step="1" value={w.start} onChange={e=>editWindow(w.key,{start:e.target.value})} required/></label><label>Selesai (WIB)<input aria-label={`Selesai kerja ${i+1} WIB`} type="datetime-local" step="1" value={w.end} onChange={e=>editWindow(w.key,{end:e.target.value})} required/></label><label>Beban pekerjaan lain (menit)<input aria-label={`Beban lain ${i+1}`} inputMode="decimal" placeholder="Belum diketahui" value={w.load} onChange={e=>editWindow(w.key,{load:e.target.value})}/></label><button type="button" onClick={()=>edit({windows:form.windows.filter(x=>x.key!==w.key)})}>Hapus waktu kerja {i+1}</button></div>)}<button type="button" disabled={form.windows.length>=1000} onClick={()=>edit({windows:[...form.windows,blankWindow()]})}>Tambah waktu kerja</button>
   <p>{base.requirements.length} posisi kerja tercatat. Urutan antrean ini adalah skenario; perhitungan memakai seluruh posisi yang dibaca.</p>
   {base.requirements.map(r=>{const input=form.work.find(x=>x.key===r.key)!;return<article className="native-production-work" key={r.key}><h3>{stageNames[r.stage]??r.stage} · {r.ownership==='CUSTOMER'?'Milik pelanggan':'Milik perusahaan'}</h3><p>{numberText(r.remaining)} PCS tersisa · <small>{r.key}</small></p><label>Jumlah yang diperiksa<input aria-label={`Jumlah ${r.key}`} inputMode="numeric" value={input.qty} onChange={e=>editWork(r.key,{qty:e.target.value})}/></label>
    {r.eligible?<><label>Tujuan yang diperiksa<select aria-label={`Tujuan ${r.key}`} value={input.target} onChange={e=>editWork(r.key,{target:e.target.value})}><option value="">Belum dipilih</option>{r.targets.map(t=><option key={t.key} value={t.key}>{t.sku} · {t.name}</option>)}</select></label><p>Tujuan pilihan tidak mengubah identitas fisik barang. Kecocokan tetap diperiksa dari sumber ERP.</p><label>Perkiraan jumlah bagus<input aria-label={`Bagus ${r.key}`} inputMode="numeric" placeholder="Belum diketahui" value={input.numerator} onChange={e=>editWork(r.key,{numerator:e.target.value})}/></label><label>Dari jumlah acuan<input aria-label={`Acuan ${r.key}`} inputMode="numeric" placeholder="Belum diketahui" value={input.denominator} onChange={e=>editWork(r.key,{denominator:e.target.value})}/></label></>:<p>Pekerjaan pelanggan memakai waktu kerja dan tidak menambah stok perusahaan.</p>}
    {input.steps.map((s,i)=><label key={s.stage}>{stageNames[s.stage]??s.stage}: waktu sisa seluruh pekerjaan (menit)<input aria-label={`${s.stage} menit ${r.key}`} inputMode="numeric" placeholder="Belum diketahui" value={s.minutes} onChange={e=>editWork(r.key,{steps:input.steps.map((x,j)=>j===i?{...x,minutes:e.target.value}:x)})}/></label>)}</article>})}
   <label>Alasan pemeriksaan jadwal<textarea aria-label="Alasan jadwal" maxLength={1000} value={form.reason} onChange={e=>edit({reason:e.target.value})} required/></label><button disabled={!workspace||stale||!supply?.complete||Boolean(message)}>Simpan jadwal yang diperiksa</button></fieldset></form>:null}
  {!canSave?<p>Hak mengubah aturan produk diperlukan untuk menyimpan jadwal.</p>:null}
  {net?<article className="native-production-result"><p className={net.state==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>{net.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip lama: hitung kekurangan baru.'} Diambil {formatCp6WibDateTime(net.capturedAt)}.</p><p>Kapasitas untuk produksi baru setelah pekerjaan tercatat: <strong>{qty(net.capacity)}</strong>. Waktu kerja dan hasil bagus memakai asumsi yang dipilih.</p><p>Bahan dan jumlah produksi baru belum dipastikan. Jumlah kosong tetap belum diketahui.</p><button disabled={busy||pending} onClick={()=>void checkNet()}>Periksa sumber kekurangan</button><label>Cari produk<input aria-label="Cari hasil kekurangan" value={search} onChange={e=>setSearch(e.target.value)}/></label><p>{rows.length} dari {net.rows.length} produk. Pencarian hanya mengubah tampilan hasil.</p>
   <div className="responsive-table"><table><thead><tr><th scope="col">Produk</th><th scope="col">Target</th><th scope="col">Tersedia</th><th scope="col">Kurang sebelum stok proses</th><th scope="col">Perkiraan bagus tepat waktu</th><th scope="col">Kurang setelah stok proses terikat</th><th scope="col">Kurang setelah pembagian global</th><th scope="col">Kekurangan pertama</th></tr></thead><tbody>{rows.map(r=><tr key={r.key}><td><strong>{r.sku}</strong><small>{r.productName}</small></td><td data-label="Target">{qty(r.target)}</td><td data-label="Tersedia">{qty(r.available)}</td><td data-label="Kurang sebelum stok proses">{qty(r.rawGap)}</td><td data-label="Perkiraan bagus tepat waktu">{qty(r.directed)}</td><td data-label="Kurang setelah stok proses terikat">{qty(r.baseGap)}</td><td data-label="Kurang setelah pembagian global">{qty(r.conditionalGap)}</td><td data-label="Kekurangan pertama">{r.firstGapAt?formatCp6WibDateTime(r.firstGapAt):r.timelineState==='UNKNOWN'?'Belum diketahui':'Tidak ada dalam skenario'}</td></tr>)}</tbody></table></div>
   <p>Perkiraan yang datang setelah batas kebutuhan tidak mengurangi kekurangan sebelumnya. Barang dalam proses tidak dianggap stok jadi.</p></article>:null}
 </section>
}
