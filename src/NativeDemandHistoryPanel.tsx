import {useCallback,useEffect,useMemo,useRef,useState}from'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseNativeDemandHistory,yesterdayWib,readNativeDemandRequest,persistNativeDemandRequest,clearNativeDemandRequest,nativeDemandRequestKey,type NativeDemandHistory,type NativeDemandQuery,type NativeDemandRow} from './nativeDemandHistory'
import NativePlanningProfilePanel from './NativePlanningProfilePanel'
import NativeProductionPlanningPanel from './NativeProductionPlanningPanel'
import NativeAnalysisPanel from './NativeAnalysisPanel'
import NativeModelEvaluationPanel from './NativeModelEvaluationPanel'
import NativeHistoryYieldPolicyPanel from './NativeHistoryYieldPolicyPanel'
import './native-demand-history.css'
const required=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
type SourceReadProps={onSourceReadStart?:()=>void;onSourceReadEnd?:()=>void}
export default function NativeDemandHistoryPanel(props:SourceReadProps){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!required.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({onSourceReadStart,onSourceReadEnd}:SourceReadProps){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi perencanaan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),sequence=useRef(0)
 const scope=runtime.projectRef+':'+identity.profile.id
 const[recovery,setRecovery]=useState(()=>readNativeDemandRequest(scope))
 const[open,setOpen]=useState(Boolean(recovery.pending||recovery.error)),[from,setFrom]=useState(recovery.pending?.q.from_date??yesterdayWib()),[through,setThrough]=useState(recovery.pending?.q.through_date??yesterdayWib()),[basis,setBasis]=useState<'AS_SOLD'|'RESTATED'>(recovery.pending?.q.group_mode??'AS_SOLD')
 const[data,setData]=useState<NativeDemandHistory|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[search,setSearch]=useState('')
 const[selected,setSelected]=useState<{product:NativeDemandRow;query:NativeDemandQuery}|null>(null)
 const[workQuery,setWorkQuery]=useState<NativeDemandQuery|null>(null)
 const[analysisQuery,setAnalysisQuery]=useState<NativeDemandQuery|null>(null)
 const[modelSelection,setModelSelection]=useState<{historyRunId:string;targetKey:string}|null>(null)
 const[yieldPolicy,setYieldPolicy]=useState(false)
 const analysisReadStart=useCallback(()=>{++sequence.current;setData(null);setBusy(true);onSourceReadStart?.()},[onSourceReadStart])
 const analysisReadEnd=useCallback(()=>{setBusy(false);onSourceReadEnd?.()},[onSourceReadEnd])
 const closeAnalysis=useCallback(()=>setAnalysisQuery(null),[])
 const planningReadStart=useCallback(()=>{setData(null);onSourceReadStart?.()},[onSourceReadStart])
 const planningReadEnd=useCallback(()=>{onSourceReadEnd?.()},[onSourceReadEnd])
 const closePlanning=useCallback(()=>setSelected(null),[])
 const closeWork=useCallback(()=>setWorkQuery(null),[])
 useEffect(()=>()=>{++sequence.current},[])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===nativeDemandRequestKey(scope)){++sequence.current;setBusy(false);setData(null);setRecovery(readNativeDemandRequest(scope));onSourceReadStart?.();onSourceReadEnd?.()}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope,onSourceReadStart,onSourceReadEnd])
 const load=async(retry=false)=>{
  const n=++sequence.current;setBusy(true);setData(null);setError('');onSourceReadStart?.()
  try{
   const held=readNativeDemandRequest(scope);if(held.error)throw Error(held.error)
   if(retry&&!held.pending)throw Error('Permintaan tersimpan tidak tersedia. Periksa penyimpanan.')
   if(!retry&&held.pending)throw Error('Ulangi permintaan tersimpan terlebih dahulu.')
   const q:NativeDemandQuery={from_date:from,through_date:through,group_mode:basis}
   const request=retry?held.pending!:{q,id:crypto.randomUUID()};if(!retry)persistNativeDemandRequest(scope,request);setRecovery(readNativeDemandRequest(scope))
   const reply=await client.rpc('erp_cp7_capture_demand_history_v1',{p_query:request.q,p_request:request.id});if(n!==sequence.current)return
   if(reply.error)throw reply.error;const parsed=parseNativeDemandHistory(reply.data)
   if(parsed.requestId!==request.id||parsed.from!==request.q.from_date||parsed.through!==request.q.through_date||parsed.basis!==request.q.group_mode)throw Error('Periode atau permintaan server berubah. Muat ulang.')
   clearNativeDemandRequest(scope,request.id);setRecovery(readNativeDemandRequest(scope));setData(parsed)
  }catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{if(n===sequence.current){setBusy(false);onSourceReadEnd?.()}}
 }
 const check=async()=>{
  if(!data)return;const run=data.runId,n=++sequence.current;setData(null);setBusy(true);setError('');onSourceReadStart?.()
  try{const r=await client.rpc('erp_cp7_read_demand_history_v1',{p_run:run});if(n!==sequence.current)return;if(r.error)throw r.error
   const parsed=parseNativeDemandHistory(r.data);if(parsed.runId!==run)throw Error('Arsip server berubah.');setData(parsed)
  }catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{if(n===sequence.current){setBusy(false);onSourceReadEnd?.()}}
 }
 const clear=()=>{++sequence.current;setData(null);setSelected(null);setWorkQuery(null);setAnalysisQuery(null);setModelSelection(null);setBusy(false);setError('');if(busy)onSourceReadEnd?.()}
 const rows=data?.rows.filter(r=>`${r.sku} ${r.productName}`.toLowerCase().includes(search.toLowerCase()))??[]
 return <section className="panel native-demand" aria-label="Data permintaan ERP"><button type="button" aria-expanded={open} onClick={()=>{if(open)clear();setOpen(!open)}}>{open?'Tutup data permintaan':'Data permintaan & stok'}</button>
  {open?<><header><div className="eyebrow">PERENCANAAN · DATA ERP</div><h2>Permintaan dan stok</h2><p>Penjualan tercatat, retur, dan pesanan terbuka memakai sumber yang sama. Periode hanya mencakup hari yang sudah selesai.</p></header>
   <form onSubmit={e=>{e.preventDefault();void load()}}><label>Dari tanggal<input aria-label="Permintaan dari tanggal" type="date" value={from} max={yesterdayWib()} disabled={busy||Boolean(recovery.pending)||Boolean(recovery.error)} onChange={e=>{clear();setFrom(e.target.value)}} required/></label><label>Sampai tanggal<input aria-label="Permintaan sampai tanggal" type="date" value={through} min={from} max={yesterdayWib()} disabled={busy||Boolean(recovery.pending)||Boolean(recovery.error)} onChange={e=>{clear();setThrough(e.target.value)}} required/></label><label>Pengelompokan<select value={basis} disabled={busy||Boolean(recovery.pending)||Boolean(recovery.error)} onChange={e=>{clear();setBasis(e.target.value as typeof basis)}}><option value="AS_SOLD">SKU saat penjualan</option><option value="RESTATED">SKU saat ini</option></select></label><button disabled={busy||from>through||Boolean(recovery.pending)||Boolean(recovery.error)}>Muat data permintaan</button></form>
   <button disabled={busy||from>through||Boolean(recovery.pending)||Boolean(recovery.error)} onClick={()=>{setModelSelection(null);setSelected(null);setWorkQuery(null);setAnalysisQuery({from_date:from,through_date:through,group_mode:basis})}}>Analisis, laporan & pengingat seluruh produk</button>
   <button type="button" aria-expanded={yieldPolicy} onClick={()=>setYieldPolicy(!yieldPolicy)}>Kebijakan yield histori</button>
   {yieldPolicy?<NativeHistoryYieldPolicyPanel onClose={()=>setYieldPolicy(false)}/>:null}
   {busy?<p role="status">Memeriksa sumber ERP…</p>:null}{error||recovery.error?<div role="alert"><p>{error||recovery.error}</p></div>:null}
   {recovery.pending?<div role="status"><p>Permintaan sebelumnya belum dipastikan. Periksa permintaan yang sama sebelum membuat analisis baru.</p><button disabled={busy} onClick={()=>void load(true)}>Ulangi permintaan yang sama</button></div>:null}
   {data?<><p className={data.state==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>{data.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip lama: sumber ERP sudah berubah. Muat analisis baru.'} Diambil {formatCp6WibDateTime(data.capturedAt)}.</p><button disabled={busy} onClick={()=>void check()}>Periksa sumber arsip</button><button disabled={busy} onClick={()=>{setModelSelection(null);setSelected(null);setAnalysisQuery(null);setWorkQuery({from_date:data.from,through_date:data.through,group_mode:data.basis})}}>Jadwal & kekurangan seluruh produk</button><label>Cari pada seluruh hasil<input aria-label="Cari data permintaan" value={search} onChange={e=>setSearch(e.target.value)}/></label><p>{rows.length} dari {data.rows.length} produk. Periode {data.from} sampai {data.through}; stok tersedia adalah posisi saat data diambil.</p>
    <div className="responsive-table"><table><thead><tr><th scope="col">Produk</th><th scope="col">Penjualan tercatat</th><th scope="col">Retur</th><th scope="col">Stok fisik</th><th scope="col">Pesanan terbuka</th><th scope="col">Tersedia</th><th scope="col">Riwayat stok</th><th scope="col">Aturan</th></tr></thead><tbody>{rows.map(r=><tr key={r.targetKey}><td className="native-demand-product"><strong>{r.sku}</strong><small>{r.productName}{r.active?'':' · Tidak aktif'}</small></td><td data-label="Penjualan tercatat">{numberText(r.gross)} PCS</td><td data-label="Retur">{numberText(r.returns)} PCS</td><td data-label="Stok fisik">{numberText(r.physical)} PCS</td><td data-label="Pesanan terbuka">{numberText(r.reserved)} PCS</td><td data-label="Tersedia" className="native-demand-available">{numberText(r.available)} PCS</td><td data-label="Riwayat stok" className="native-demand-history">{r.unknownDays>0?`${r.unknownDays} hari belum diketahui`:r.stockoutDays>0?`${r.stockoutDays} hari stok habis`:`${r.availableDays} hari tersedia`}</td><td data-label="Aturan"><button disabled={busy} onClick={()=>{setModelSelection(null);setAnalysisQuery(null);setSelected({product:r,query:{from_date:data.from,through_date:data.through,group_mode:data.basis}})}}>Atur target {r.sku}</button><button disabled={busy||data.state!=='UNCHANGED'} onClick={()=>{setSelected(null);setWorkQuery(null);setAnalysisQuery(null);setModelSelection({historyRunId:data.runId,targetKey:r.targetKey})}}>Bandingkan ramalan {r.sku}</button></td></tr>)}</tbody></table></div>
    {!rows.length?<p>Hasil pencarian kosong.</p>:null}<p>Riwayat stok yang belum diketahui tidak dianggap nol. Saran jumlah produksi menunggu bukti permintaan, waktu proses, dan kapasitas yang memadai.</p>
   </>:null}
   {modelSelection?<NativeModelEvaluationPanel {...modelSelection} onSourceReadStart={planningReadStart} onSourceReadEnd={planningReadEnd} onClose={()=>setModelSelection(null)}/>:null}
   {selected?<NativePlanningProfilePanel product={selected.product} query={selected.query} onSourceReadStart={planningReadStart} onSourceReadEnd={planningReadEnd} onClose={closePlanning}/>:null}
   {analysisQuery?<NativeAnalysisPanel query={analysisQuery} onSourceReadStart={analysisReadStart} onSourceReadEnd={analysisReadEnd} onClose={closeAnalysis}/>:null}
   {workQuery?<NativeProductionPlanningPanel query={workQuery} onSourceReadStart={planningReadStart} onSourceReadEnd={planningReadEnd} onClose={closeWork}/>:null}
  </>:null}
 </section>
}
