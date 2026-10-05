import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibPhysicalTimeToIso,formatCp6WibDateTime} from './cp6BusinessTime'
import {assertSameAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import {productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import {parseFabricWorkspace,parseFabricConfig,checkFabricOutcome,fabricSaveDefinitelyUncommitted,readFabricRequest,persistFabricRequest,clearFabricRequest,fabricRequestKey,type FabricRequest,type FabricWorkspace} from './nativeFabricRecipe'

type Props={context:NativeAnalysis|null;generation:number;blocked:boolean;access:AnalysisFinanceAccess;onReadStart:()=>number;isReadCurrent:(n:number)=>boolean;onReadEnd:(n:number)=>void;onAnalysis:(a:NativeAnalysis,n:number)=>void;requireClear:()=>void}
type Form={target:string;query:string;material:string;pattern:string;rate:string;from:string;to:string;reason:string}
const empty:Form={target:'',query:'',material:'',pattern:'',rate:'',from:'',to:'',reason:''}
export default function NativeFabricRecipePanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'].every(p=>identity.permissions.includes(p)))return null
 return <Recipes {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} project={runtime.projectRef} profile={identity.profile.id} actor={identity.profile.authUserId} canWrite={identity.permissions.includes('master.product.manage')}/>
}
function Recipes(props:Props&{project:string;profile:string;actor:string;canWrite:boolean}){
 const{runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi resep kain belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope=`analysis:${props.project}:${props.profile}`,productionScope=`erp:${props.project}:${props.profile}`
 const mounted=useRef(true),active=useRef<number|null>(null)
 const[form,setForm]=useState<Form>(empty),[reviewed,setReviewed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const[facts,setFacts]=useState<{generation:number;data:FabricWorkspace|null}>({generation:-1,data:null}),[recovery,setRecovery]=useState(()=>readFabricRequest(scope))
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===fabricRequestKey(scope)){setRecovery(readFabricRequest(scope));setFacts({generation:-1,data:null});setReviewed(false)}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const current=(n:number)=>mounted.current&&props.isReadCurrent(n),data=facts.generation===props.generation?facts.data:null,blocked=props.blocked||busy||Boolean(recovery.pending||recovery.error)
 const edit=(changes:Partial<Form>)=>{setForm(f=>({...f,...changes}));setReviewed(false);setMessage('')}
 const perform=async(operation:(n:number)=>Promise<void>)=>{if(active.current!==null)return;const n=props.onReadStart();active.current=n;setBusy(true);setFacts({generation:-1,data:null});setReviewed(false);setError('');setMessage('');try{await operation(n)}catch(e){if(current(n))setError(normalizeClientError(e).message)}finally{if(mounted.current){setBusy(false);setRecovery(readFabricRequest(scope))}if(active.current===n)active.current=null;props.onReadEnd(n)}}
 const load=(materialOffset=0,patternOffset=0)=>{const original=props.context,target=form.target;void perform(async n=>{
  props.requireClear();const held=readFabricRequest(scope);if(held.error||held.pending)throw Error(held.error??'Pastikan permintaan resep kain yang sama dahulu.')
  if(!original||!target)throw Error('Pilih produk dari analisis ERP yang masih sesuai sumber.')
  const response=await client.rpc('erp_cp7_get_fabric_recipe_v1',{p_query:{run_id:original.runId,target_key:target,material_query:form.query,material_offset:String(materialOffset),pattern_offset:String(patternOffset),limit:'50'}})
  if(!current(n))return;if(response.error)throw response.error
  const parsed=parseFabricWorkspace(response.data,original.query,props.actor,target,props.access);assertSameAnalysis(original,parsed.analysis)
  if(parsed.page.material_offset!==materialOffset||parsed.page.pattern_offset!==patternOffset||parsed.page.limit!==50)throw Error('Halaman pilihan bahan berubah; baca ulang.')
  setFacts({generation:n,data:parsed});setForm(f=>({...f,material:'',pattern:''}));props.onAnalysis(parsed.analysis,n)
 })}
 const send=(request:FabricRequest,retry=false)=>void perform(async n=>{
  props.requireClear();if(!props.canWrite)throw Error('Hak mengelola produk diperlukan untuk review resep kain.')
  const manager=productionLockManager();if(!manager)throw Error('Simpan resep kain membutuhkan pengunci tab. Data masih dapat dibaca.')
  await manager.request(productionLockName(productionScope),{mode:'exclusive',ifAvailable:true},async lock=>{
   if(!lock)throw Error('Ada transaksi ERP di tab lain. Tunggu selesai.');if(!current(n))return
   const shared=readProductionRecovery(productionScope);if(shared.corrupted||hasProductionPending(shared))throw Error('Pastikan hasil transaksi ERP yang tertunda terlebih dahulu.')
   const held=readFabricRequest(scope)
   if(retry){if(held.error||!held.pending||JSON.stringify(held.pending)!==JSON.stringify(request))throw Error(held.error??'Permintaan resep kain tersimpan berubah.')}
   else persistFabricRequest(scope,request)
   setRecovery(readFabricRequest(scope));const response=await client.rpc('erp_cp7_save_fabric_recipe_v1',{p_payload:request.payload,p_request:request.id})
   if(!current(n))return;if(response.error){
    if(fabricSaveDefinitelyUncommitted(response.error)){
     clearFabricRequest(scope,request.id);setRecovery(readFabricRequest(scope))
     const reason=response.error.code==='40001'?'Versi resep atau sumber analisis berubah.':response.error.message==='CP7_FABRIC_BACKDATE_LIMIT'?'Tanggal mulai resep kain melebihi batas mundur satu tahun.':response.error.message==='CP7_FABRIC_ORIGINAL_ACCESS_CHANGED'?'Izin analisis berubah sejak diambil.':'Data bahan, pola, satuan, atau isian review belum sesuai sumber.'
     throw Error(reason+' Ambil analisis ERP terbaru lalu review kembali.')
    }
    if(response.error.message==='CP7_FABRIC_REQUEST_CHANGED')throw Error('Permintaan tersimpan berbeda dari catatan server. Pastikan hasil permintaan ini sebelum membuat yang baru.')
    throw response.error
   }
   checkFabricOutcome(response.data,request,props.actor);clearFabricRequest(scope,request.id);setRecovery(readFabricRequest(scope))
   setMessage('Review resep kain tersimpan. Ambil analisis ERP terbaru untuk memakai versi yang berlaku.');setForm(f=>({...f,rate:'',reason:''}))
  })
 })
 const save=()=>{try{
  if(blocked||!reviewed||!data||!props.context||data.targetKey!==form.target)throw Error('Baca pilihan bahan dan review semua isian terlebih dahulu.')
  assertSameAnalysis(data.analysis,props.context)
  const material=data.materials.find(m=>m.id===form.material),pattern=data.patterns.find(p=>p.id===form.pattern)
  if(!material||form.pattern&&!pattern||!form.reason.trim())throw Error('Pilih bahan yang sudah dibaca dan tulis alasan review.')
  const config=parseFabricConfig({basis:'SELECTED_ASSUMPTIONS',effective_from:cp6WibPhysicalTimeToIso(form.from),effective_to:form.to?cp6WibPhysicalTimeToIso(form.to):null,material_id:material.id,material_hash:material.source_hash,unit:material.unit,qty_per_good_pcs:form.rate,pattern_id:pattern?.id??null,pattern_hash:pattern?.source_hash??null})
  send({id:crypto.randomUUID(),payload:{run_id:data.analysis.runId,target_key:form.target,source_hash:data.analysis.analysis.snapshot.source_hash,expected_revision:data.revision,config,reason:form.reason.trim()}})
 }catch(e){setError(normalizeClientError(e).message)}}
 const targetOptions=props.context?.analysis.recommendations.filter(r=>r.target.kind==='PRODUCT')??[]
 return <section aria-label="Review pemakaian kain"><h3>Review pemakaian kain</h3>
  <p>Pilih bahan ERP dan isi pemakaian per PCS untuk produk dan ukuran yang direview. Angka ini merupakan asumsi rencana, bukan pemasangan, alokasi bahan, atau hasil potong aktual.</p>
  {busy?<p role="status">Memeriksa sumber dan izin resep kain…</p>:null}{error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {recovery.pending?<div role="status"><p>Hasil penyimpanan resep kain belum dipastikan. Permintaan yang sama dipertahankan.</p><button disabled={busy} onClick={()=>send(recovery.pending!,true)}>Ulangi resep kain yang sama</button></div>:null}
  <fieldset disabled={blocked}><label>Produk dan ukuran resep kain<select aria-label="Produk dan ukuran resep kain" value={form.target} onChange={e=>{edit({target:e.target.value,material:'',pattern:''});setFacts({generation:-1,data:null})}}><option value="">Pilih produk dan ukuran</option>{targetOptions.map(r=><option key={r.target.key} value={r.target.key}>{props.context?.labels.find(l=>l.key===r.target.key)?.sku??r.target.key}</option>)}</select></label>
   <label>Cari bahan kain ERP<input aria-label="Cari bahan kain ERP" value={form.query} maxLength={200} onChange={e=>{edit({query:e.target.value,material:''});setFacts({generation:-1,data:null})}}/></label>
   <button disabled={!form.target||!props.context||props.context.state!=='UNCHANGED'} onClick={()=>load()}>Baca bahan dan versi resep kain</button>
  </fieldset>
  {data?<><p>{data.materials.length} dari {data.page.material_total} bahan sesuai pencarian · halaman mulai {data.page.material_offset+1}. {data.patterns.length} dari {data.page.pattern_total} pola aktif.</p>
   <div className="native-analysis-actions"><button disabled={blocked||data.page.material_offset===0} onClick={()=>load(Math.max(0,data.page.material_offset-50),data.page.pattern_offset)}>Bahan sebelumnya</button><button disabled={blocked||BigInt(data.page.material_offset+data.materials.length)>=BigInt(data.page.material_total)} onClick={()=>load(data.page.material_offset+50,data.page.pattern_offset)}>Bahan berikutnya</button><button disabled={blocked||data.page.pattern_offset===0} onClick={()=>load(data.page.material_offset,Math.max(0,data.page.pattern_offset-50))}>Pola sebelumnya</button><button disabled={blocked||BigInt(data.page.pattern_offset+data.patterns.length)>=BigInt(data.page.pattern_total)} onClick={()=>load(data.page.material_offset,data.page.pattern_offset+50)}>Pola berikutnya</button></div>
   <fieldset disabled={blocked||!props.canWrite}>
    <label>Bahan kain yang direview<select aria-label="Bahan kain yang direview" value={form.material} onChange={e=>edit({material:e.target.value,rate:''})}><option value="">Pilih bahan kain</option>{data.materials.map(m=><option key={m.id} value={m.id}>{m.sku} · {m.name} · {m.unit}</option>)}</select></label>
    <label>Pola resep kain (opsional)<select aria-label="Pola resep kain" value={form.pattern} onChange={e=>edit({pattern:e.target.value})}><option value="">Pola belum dipilih</option>{data.patterns.map(p=><option key={p.id} value={p.id}>{p.code} · {p.name} · {p.revision}</option>)}</select></label>
    <label>Pemakaian kain per PCS<input aria-label="Pemakaian kain per PCS" inputMode="decimal" value={form.rate} maxLength={19} onChange={e=>edit({rate:e.target.value})}/></label><p>Satuan: {data.materials.find(m=>m.id===form.material)?.unit??'pilih bahan terlebih dahulu'} per PCS. Tidak ada angka bawaan.</p>
    <label>Mulai berlaku resep kain (WIB)<input aria-label="Mulai berlaku resep kain WIB" type="datetime-local" step="1" value={form.from} onChange={e=>edit({from:e.target.value})}/></label>
    <p>Tanggal mulai boleh dimundurkan paling lama satu tahun.</p>
    <label>Akhir berlaku resep kain (WIB, opsional)<input aria-label="Akhir berlaku resep kain WIB" type="datetime-local" step="1" value={form.to} onChange={e=>edit({to:e.target.value})}/></label>
    <label>Alasan review resep kain<textarea aria-label="Alasan review resep kain" value={form.reason} maxLength={1000} onChange={e=>edit({reason:e.target.value})}/></label>
    <label><input aria-label="Konfirmasi review resep kain" type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa produk, ukuran, bahan, satuan, pemakaian dan tanggal berlaku.</label>
    <button disabled={!reviewed||!form.material||!form.rate||!form.from||!form.reason.trim()} onClick={save}>Simpan review resep kain</button>
   </fieldset>{!props.canWrite?<p>Hak mengelola produk diperlukan untuk menyimpan review.</p>:null}
   <details><summary>Versi resep kain</summary><p>{data.page.recipe_total} versi tersimpan; menampilkan paling banyak 50 versi terakhir. Analisis lama mempertahankan input aslinya.</p>{data.recipes.map(r=><article key={r.id}><p>Versi {r.revision} · pemakaian {r.config.qty_per_good_pcs} {r.config.unit} per PCS · mulai {formatCp6WibDateTime(r.config.effective_from)}{r.config.effective_to?` · berakhir ${formatCp6WibDateTime(r.config.effective_to)}`:''}.</p><p>{r.reason}</p></article>)}</details>
  </>:null}
 </section>
}
