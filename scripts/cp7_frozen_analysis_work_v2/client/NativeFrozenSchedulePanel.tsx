import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from '../../../src/auth/AuthProvider'
import {getUatSupabaseClient} from '../../../src/lib/supabase'
import {normalizeClientError} from '../../../src/lib/clientError'
import {formatCp6WibDateTime} from '../../../src/cp6BusinessTime'
import type {NativeDemandQuery} from '../../../src/nativeDemandHistory'
import {parseStagedJob} from '../../../src/nativeStagedJob'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,readFrozenAnalysisRequest,persistFrozenAnalysisRequest,requestFrozenAnalysis,clearFrozenAnalysisRequest,type FrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {readFrozenScheduleWorkspace,prepareFrozenScheduleRequest,frozenScheduleRequestKey,readFrozenScheduleRequest,persistFrozenScheduleRequest,saveFrozenSchedule,clearFrozenScheduleRequest,type FrozenWorkContext,type FrozenScheduleWorkspace} from './nativeFrozenWork'
import FrozenScheduleForm,{formFrom,configFrom,type Form} from './FrozenScheduleForm'
import '../../../src/native-production-planning.css'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
type Source={context:FrozenWorkContext;workspace:FrozenScheduleWorkspace}
const permissions=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']

// Explicit entry only. The default application graph does not import this
// prepared panel. Runtime/identity gates match the existing planning panel.
export default function NativeFrozenSchedulePanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!permissions.every(p=>identity.permissions.includes(p)))return null
 return<Workspace {...props} key={JSON.stringify([runtime.projectRef,identity.profile.authUserId,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.permissions,props.query])}/>
}
function Workspace({query,onSourceReadStart,onSourceReadEnd,onClose}:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi jadwal belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),actor=identity.profile.authUserId
 const scope='work-schedule:'+runtime.projectRef,canSave=identity.permissions.includes('master.product.manage')
 const sequence=useRef(0),active=useRef(false)
 const[source,setSource]=useState<Source|null>(null),[base,setBase]=useState<Source|null>(null),[form,setForm]=useState<Form|null>(null)
 const[readHeld,setReadHeld]=useState(()=>readFrozenAnalysisRequest(actor,scope)),[saveHeld,setSaveHeld]=useState(()=>readFrozenScheduleRequest(scope,actor))
 const[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const refreshRecovery=()=>{setReadHeld(readFrozenAnalysisRequest(actor,scope));setSaveHeld(readFrozenScheduleRequest(scope,actor))}
 const begin=()=>{const n=++sequence.current;active.current=true;setBusy(true);setError('');setMessage('');onSourceReadStart();return n}
 const end=(n:number)=>{if(n===sequence.current){active.current=false;setBusy(false);onSourceReadEnd()}}
 const retire=()=>{++sequence.current;if(active.current){active.current=false;onSourceReadEnd()}}
 useEffect(()=>()=>{++sequence.current;if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 useEffect(()=>{
  const listener=(event:StorageEvent)=>{
   if(event.key!==null&&event.key!==frozenAnalysisRequestKey(actor,scope)&&event.key!==frozenScheduleRequestKey(scope,actor))return
   ++sequence.current;if(active.current){active.current=false;onSourceReadEnd()}
   setBusy(false);setSource(null);setReadHeld(readFrozenAnalysisRequest(actor,scope));setSaveHeld(readFrozenScheduleRequest(scope,actor));setMessage('');setError('Catatan jadwal berubah di tab lain. Periksa permintaan tersimpan dan sumber terbaru.')
  }
  addEventListener('storage',listener);return()=>removeEventListener('storage',listener)
 },[actor,scope,onSourceReadEnd])
 const adopt=(value:Source)=>{setBase(value);setForm(formFrom(value.workspace));setMessage('')}
 const report=(e:unknown)=>{
  const normalized=normalizeClientError(e);setError(normalized.message)
  if(normalized.code==='FORBIDDEN'||normalized.code==='AUTH_REQUIRED'){setSource(null);setBase(null);setForm(null)}
 }
 const load=async(retry=false)=>{
  if(active.current)return;const n=begin();setSource(null)
  try{
   const held=readFrozenAnalysisRequest(actor,scope),saved=readFrozenScheduleRequest(scope,actor)
   if(!retry&&(saved.error||saved.pending))throw Error(saved.error||'Pastikan hasil simpan jadwal tersimpan sebelum mengambil sumber baru.')
   if(held.error)throw Error(held.error)
   if(retry&&!held.pending||!retry&&held.pending)throw Error('Periksa permintaan stok proses tersimpan yang sama terlebih dahulu.')
   const request:FrozenAnalysisRequest=retry?held.pending!:{id:crypto.randomUUID(),actor,q:structuredClone(query),method:FROZEN_ANALYSIS_REQUEST}
   if(!retry)await persistFrozenAnalysisRequest(actor,scope,request)
   if(n!==sequence.current)return;refreshRecovery()
   const reply=await requestFrozenAnalysis(client,actor,scope)
   if(n!==sequence.current)return;if(reply.error)throw reply.error
   const job=parseStagedJob(reply.data,request.id,{id:request.id,q:request.q})
   const context:FrozenWorkContext={requestId:request.id,reference:job.reference,runId:job.runId,method:'FROZEN_V2'}
   const workspace=await readFrozenScheduleWorkspace(client,context)
   if(n!==sequence.current)return
   await clearFrozenAnalysisRequest(actor,scope,request)
   if(n!==sequence.current)return
   const next={context:{...context,runId:workspace.sourceRun},workspace};setSource(next);if(base===null)adopt(next);refreshRecovery()
  }catch(e){if(n===sequence.current){refreshRecovery();report(e)}}finally{end(n)}
 }
 const check=async()=>{
  if(active.current||!source)return;const previous=source,n=begin();setSource(null)
  try{const workspace=await readFrozenScheduleWorkspace(client,previous.context);if(n===sequence.current)setSource({...previous,workspace})}
  catch(e){if(n===sequence.current)report(e)}finally{end(n)}
 }
 const save=async(retry=false)=>{
  if(active.current||!canSave)return;const n=begin()
  try{
   const held=readFrozenScheduleRequest(scope,actor),reading=readFrozenAnalysisRequest(actor,scope)
   if(held.error||!retry&&(reading.error||reading.pending))throw Error(held.error||reading.error||'Selesaikan pembacaan stok proses yang tersimpan.')
   if(retry&&!held.pending||!retry&&held.pending)throw Error('Periksa permintaan simpan jadwal yang sama terlebih dahulu.')
   if(!retry&&(!base||!form||!source||source.workspace.state!=='UNCHANGED'||source.workspace.staged.productionState!=='COMPLETE'||source.workspace.sourceRun!==base.workspace.sourceRun||source.workspace.sourceHash!==base.workspace.sourceHash||source.workspace.revision!==base.workspace.revision||source.workspace.staged.analysisHash!==base.workspace.staged.analysisHash))throw Error('Sumber atau versi jadwal berubah. Gunakan sumber terbaru sebelum menyimpan.')
   const request=retry?held.pending!:prepareFrozenScheduleRequest(base!.workspace,base!.context,actor,configFrom(form!),form!.reason,crypto.randomUUID())
   if(!retry)await persistFrozenScheduleRequest(scope,request)
   if(n!==sequence.current)return;refreshRecovery()
   await saveFrozenSchedule(client,scope,actor)
   if(n!==sequence.current)return
   await clearFrozenScheduleRequest(scope,request)
   if(n!==sequence.current)return
   refreshRecovery();setSource(null);setMessage('Jadwal tersimpan. Ambil sumber terbaru untuk memeriksa versi jadwal.');setError('')
  }catch(e){if(n===sequence.current){refreshRecovery();report(e)}}finally{end(n)}
 }
 const pending=Boolean(readHeld.pending||readHeld.error||saveHeld.pending||saveHeld.error)
 const stale=Boolean(source&&base&&(source.workspace.state!=='UNCHANGED'||source.workspace.sourceRun!==base.workspace.sourceRun||source.workspace.sourceHash!==base.workspace.sourceHash||source.workspace.revision!==base.workspace.revision||source.workspace.staged.analysisHash!==base.workspace.staged.analysisHash))
 const canSubmit=Boolean(canSave&&!busy&&!pending&&source&&base&&!stale&&source.workspace.staged.productionState==='COMPLETE'&&!message)
 return<section className="native-production panel" aria-label="Jadwal produksi"><header><div><div className="eyebrow">PERENCANAAN SELURUH PRODUK</div><h2>Jadwal produksi</h2><p>Periksa waktu kerja dan perkiraan hasil. Pekerjaan pelanggan ikut memakai waktu kerja.</p></div><button onClick={()=>{retire();onClose()}}>Tutup jadwal produksi</button></header>
  <div className="native-production-actions"><button disabled={busy||pending} onClick={()=>void load()}>Ambil stok proses terbaru</button>{source?<button disabled={busy||pending} onClick={()=>void check()}>Periksa sumber stok proses</button>:null}</div>
  {busy?<p role="status">Memeriksa stok proses dan jadwal…</p>:null}
  {error||readHeld.error||saveHeld.error?<p role="alert">{error||readHeld.error||saveHeld.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {readHeld.pending?<div role="status"><p>Hasil ambil stok proses belum dipastikan.</p><button disabled={busy} onClick={()=>void load(true)}>Ulangi pembacaan stok proses</button></div>:null}
  {saveHeld.pending?<div role="status"><p>Hasil simpan jadwal belum dipastikan. Permintaan asal tetap disimpan.</p><button disabled={busy||!canSave} onClick={()=>void save(true)}>Ulangi simpan jadwal yang sama</button></div>:null}
  {source?<><p className={source.workspace.state==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>{source.workspace.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip lama: ambil stok proses terbaru.'} Diambil {formatCp6WibDateTime(source.workspace.capturedAt)} · jadwal versi {source.workspace.revision}.</p>
   <p role="status">{source.workspace.staged.inputCoverage==='PENDING'?'Riwayat stok sedang disiapkan; perhitungan kebutuhan belum selesai. ':source.workspace.staged.analysisState==='DONE'?'Perhitungan kebutuhan telah selesai. ':'Riwayat stok telah dibaca; perhitungan kebutuhan belum selesai. '}{source.workspace.staged.analysisState==='FAILED'?'Perhitungan kebutuhan terhenti. ':''}Jadwal memakai pekerjaan fisik yang tercatat dan asumsi yang diperiksa.</p>
   {source.workspace.staged.productionState==='UNKNOWN'?<p role="alert">Jumlah stok proses belum dapat dicocokkan. Jadwal belum bisa disimpan.</p>:null}</>:null}
  {stale?<p role="alert">Sumber atau versi jadwal berubah. Isianmu masih ada. Gunakan sumber terbaru sebelum menyimpan.</p>:null}
  {source&&base&&stale?<button disabled={busy||pending||source.workspace.state!=='UNCHANGED'} onClick={()=>adopt(source)}>Gunakan sumber jadwal terbaru</button>:null}
  {base&&form?<FrozenScheduleForm base={base.workspace} form={form} disabled={busy||pending||!canSave} canSubmit={canSubmit} update={change=>setForm(f=>f?change(f):f)} onSubmit={()=>void save()}/>:null}
  {!canSave?<p>Hak mengubah aturan produk diperlukan untuk menyimpan jadwal.</p>:null}
 </section>
}
