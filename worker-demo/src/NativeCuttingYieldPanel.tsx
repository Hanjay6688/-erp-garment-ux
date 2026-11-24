import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseNativeCuttingYield,readCuttingYieldRequest,persistCuttingYieldRequest,clearCuttingYieldRequest,cuttingYieldRequestKey,type NativeCuttingYield} from './nativeCuttingYield'
const required=['production.cutting.view','master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
type Props={groupId:string|null;sourceKey:string;parentBusy:boolean;onAuthorityLost?:()=>void}
export default function NativeCuttingYieldPanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['OWNER','ADMIN'].includes(identity.profile.role)||!required.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({groupId,sourceKey,parentBusy,onAuthorityLost}:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi sumber potong belum siap.')
 const scope=runtime.projectRef+':'+identity.profile.id,client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0)
 const[held,setHeld]=useState(()=>readCuttingYieldRequest(scope)),[data,setData]=useState<{binding:string;groupId:string;value:NativeCuttingYield}|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const binding=JSON.stringify([groupId,sourceKey,parentBusy]),current=useRef(binding);current.current=binding
 useEffect(()=>{++seq.current;setData(null);setBusy(false);setError('');return()=>{++seq.current}},[binding])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===cuttingYieldRequestKey(scope)){++seq.current;setBusy(false);setData(null);setHeld(readCuttingYieldRequest(scope))}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const load=async(retry=false)=>{
  if(parentBusy)return;const n=++seq.current,bound=current.current;setData(null);setError('');setBusy(true)
  try{const pending=readCuttingYieldRequest(scope);if(pending.error)throw Error(pending.error);if(retry&&!pending.pending)throw Error('Permintaan tersimpan tidak ada.');if(!retry&&(!groupId||pending.pending))throw Error('Pilih potongan atau pulihkan permintaan tersimpan.')
   const request=retry?pending.pending!:{id:crypto.randomUUID(),groupId:groupId!};if(!retry)persistCuttingYieldRequest(scope,request);setHeld(readCuttingYieldRequest(scope))
   const r=await client.rpc('erp_cp7_capture_cutting_yield_v1',{p_query:{group_ids:[request.groupId]},p_request:request.id});if(n!==seq.current||bound!==current.current)return;if(r.error)throw r.error
   const value=parseNativeCuttingYield(r.data,request.groupId);if(value.requestId!==request.id)throw Error('Permintaan sumber potong tidak cocok.');clearCuttingYieldRequest(scope,request);setHeld(readCuttingYieldRequest(scope));if(groupId!==null&&request.groupId!==groupId){setError('Permintaan lama selesai. Muat sumber potongan yang sekarang dipilih.');return}setData({binding:bound,groupId:request.groupId,value})
  }catch(e){if(n===seq.current){const failure=normalizeClientError(e);setError(failure.message);if(['FORBIDDEN','AUTH_REQUIRED'].includes(failure.code))onAuthorityLost?.();setHeld(readCuttingYieldRequest(scope))}}finally{if(n===seq.current)setBusy(false)}
 }
 const check=async()=>{if(!data||parentBusy)return;const n=++seq.current,bound=current.current,run=data.value.runId,readGroup=data.groupId;setData(null);setBusy(true);setError('')
  try{const r=await client.rpc('erp_cp7_read_cutting_yield_v1',{p_run:run});if(n!==seq.current||bound!==current.current)return;if(r.error)throw r.error;const value=parseNativeCuttingYield(r.data,readGroup);if(value.runId!==run)throw Error('Arsip sumber potong tidak cocok.');setData({binding:bound,groupId:readGroup,value})}
  catch(e){if(n===seq.current){const failure=normalizeClientError(e);setError(failure.message);if(['FORBIDDEN','AUTH_REQUIRED'].includes(failure.code))onAuthorityLost?.()}}finally{if(n===seq.current)setBusy(false)}
 }
 const visible=data?.binding===binding&&!busy&&!parentBusy?data.value:null
 return <section className="ccut-card wide" aria-label="Sumber hasil potong"><header><span>HASIL POTONG · DATA ERP</span><strong>Hasil per roll</strong></header><p>Hasil tersimpan dan pemakaian bahan dibaca dari potongan asli. Pilih draft atau potongan yang baru disimpan untuk memeriksanya.</p>
  <div className="ccut-actions"><button type="button" disabled={!groupId||parentBusy||busy||Boolean(held.pending||held.error)} onClick={()=>void load()}>Muat hasil potong tersimpan</button>{held.pending?<button type="button" disabled={busy||parentBusy} onClick={()=>void load(true)}>Pulihkan pembacaan hasil potong</button>:null}{visible?<button type="button" disabled={busy||parentBusy} onClick={()=>void check()}>Periksa sumber hasil potong</button>:null}</div>
  {busy?<p role="status">Membaca sumber potong…</p>:null}{error||held.error?<p role="alert">{error||held.error}</p>:null}
  {visible?<><p>{visible.state==='UNCHANGED'?'Sumber sama dengan pembacaan ini.':'Arsip pembacaan: sumber atau mesin sudah berubah. Muat pembacaan baru sebelum menilai hasil sekarang.'}</p><p>Dibaca {formatCp6WibDateTime(visible.capturedAt)} · {visible.rows.length} slice roll.</p>{visible.rows.length===0?<p>Potongan ini belum memiliki slice roll tersimpan.</p>:visible.rows.map(row=><article key={row.sliceId}><h3>{row.materialSku} · roll {row.rollId.slice(0,8)}</h3><p>Waktu potong {formatCp6WibDateTime(row.physicalAt)} · pola {row.patternRevision??'belum terikat'}.</p>{row.actual?<><p data-cutting-actual>Terpakai {row.actual.consumed} {row.actual.unit} · hasil potong {row.actual.totalPcs} PCS.</p><details><summary>Hasil per ukuran dari sumber asli</summary><ul>{row.actual.bySize.map(y=><li key={y.yieldId}>Ukuran {y.sizeId.slice(0,8)}: {y.qtyPcs} PCS</li>)}</ul></details></>:<p>{row.reason==='NATIVE_CUTTING_NOT_POSTED'?'Potongan belum diposting. Hasil belum masuk pembanding.':'Pemakaian atau hasil potong belum lengkap.'}</p>}<p><strong>Belum dapat dinilai.</strong> Keluarga bahan, rencana campuran sebelum potong, dan rentang hasil yang teruji belum tersedia.</p><p>Lebar belum dicatat. Sisa hitungan belum membuktikan sisa fisik; BS laundry belum membuktikan penyebab saat potong.</p></article>)}<details><summary>Identitas pembacaan</summary><p>{visible.runId}</p><p>{visible.sourceHash}</p><p>Waktu diketahui berasal dari pembacaan ini; tanggal potong lama tidak menjadi bukti pengetahuan lama.</p></details></>:<p>Belum ada hasil pembacaan. Simpan dan Post potongan tetap mengikuti pemeriksaan transaksi yang biasa.</p>}
 </section>
}
