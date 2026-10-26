import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './vendor/src/auth/AuthProvider'
import {getUatSupabaseClient} from './client'
import {normalizeClientError} from './vendor/src/lib/clientError'
import NativeAnalysisFinancePanel from './vendor/src/NativeAnalysisFinancePanel'
import NativeFrozenQuantityPanel from './vendor/scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel'
import type {FrozenQuantitySession} from './vendor/scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity'
import {readFrozenAnalysisRequest} from './vendor/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import type {NativeDemandQuery} from './vendor/src/nativeDemandHistory'
import type {StagedAnalysis} from './vendor/src/nativeAnalysisPages'
import type {StagedJob} from './vendor/src/nativeStagedJob'
import {createProgressReader,type Observation} from './reader'
import CombinedProgress from './CombinedProgress'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
type Source={job:StagedJob;staged:StagedAnalysis|null}
type FinanceProps={session:FrozenQuantitySession;source:Source;onAccessLost:(message:string)=>void}
const fingerprint=({actor,scope,request:r}:FrozenQuantitySession)=>JSON.stringify([actor,scope,r.actor,r.id,r.method,r.q.from_date,r.q.through_date,r.q.group_mode,r.finance??null])
function FinanceSource({session,source,onAccessLost}:FinanceProps){
 const{runtime,identity}=useAuth()
 const client=useMemo(()=>runtime.mode==='DISPOSABLE_TEST'?getUatSupabaseClient(runtime):null,[runtime])
 const allowed=identity.status==='AUTHORIZED'&&['OWNER','ADMIN'].includes(identity.profile.role)&&identity.permissions.includes('finance.reports.view')
 const[reader,setReader]=useState<ReturnType<typeof createProgressReader>|null>(null)
 const[observation,setObservation]=useState<Observation>({value:null,error:null}),[loading,setLoading]=useState(false)
 const binding=fingerprint(session),reference=source.job.reference,sourceKey=JSON.stringify([reference.sourceHash,reference.capturedAt])
 const{id,finance,q:{from_date,through_date,group_mode}}=session.request
 const request=useMemo(()=>({id,q:{from_date,through_date,group_mode},...(finance?{finance}:{})}),[id,from_date,through_date,group_mode,finance])
 const generation=useRef(0)
 useEffect(()=>{
  if(!client)return
  const n=++generation.current
  const current=()=>{
   const held=readFrozenAnalysisRequest(session.actor,session.scope)
   return generation.current===n&&!held.error&&held.pending!==null&&held.pending!==undefined
    &&fingerprint({...session,request:held.pending})===binding
  }
  const next=createProgressReader(client,request,reference,current)
  const stop=next.subscribe(value=>{
   if(generation.current!==n)return
   setObservation(value)
   if(value.error){const failure=normalizeClientError(value.error);if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED')onAccessLost(failure.message)}
  })
  setReader(next)
  return()=>{++generation.current;stop();next.dispose()}
  // The durable request and source identity define the reader, not each unit.
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[binding,client,onAccessLost,sourceKey])
 useEffect(()=>{
  if(!reader)return
  let retired=false,timer:ReturnType<typeof setTimeout>|null=null
  const read=async()=>{
   setLoading(true)
   try{
    await reader.read()
    if(!retired&&source.job.state==='RUNNING')timer=setTimeout(()=>{void read()},5000)
   }catch{/* The shared observation shows the error. Automatic reads stop. */}
   finally{if(!retired)setLoading(false)}
  }
  void read()
  return()=>{retired=true;if(timer!==null)clearTimeout(timer)}
 },[reader,source.job.state,allowed])
 const get=useCallback(async(id:string)=>{
  if(!reader)throw Error('Pembaca kemajuan belum siap.')
  return reader.status(id)
 },[reader])
 const refresh=async()=>{if(!reader||loading)return;const n=generation.current;setLoading(true);try{await reader.read()}catch{/* Same observation. */}finally{if(n===generation.current)setLoading(false)}}
 return <>
  {observation.value?<CombinedProgress value={observation.value}/>:loading?<p role="status">Memeriksa kemajuan pekerjaan tersimpan…</p>:null}
  {observation.error?<p role="alert">{normalizeClientError(observation.error).message} Status terbaru belum dapat dipastikan.</p>:null}
  <button type="button" disabled={!reader||loading} onClick={()=>void refresh()}>Periksa kemajuan pekerjaan yang sama</button>
  {reader&&source.staged?<NativeAnalysisFinancePanel request={request} runId={source.staged.set.runId} reference={source.staged.set.reference} allowed={allowed} get={get}/>:null}
 </>
}
const renderFinance=(session:FrozenQuantitySession,source:Source,onAccessLost:(message:string)=>void)=><FinanceSource key={session.request.id} session={session} source={source} onAccessLost={onAccessLost}/>

export default function CurrentProgressFinancePanel(props:Props){
 const{runtime,identity}=useAuth(),[includeFinance,setIncludeFinance]=useState(false)
 const allowed=identity.status==='AUTHORIZED'&&['OWNER','ADMIN'].includes(identity.profile.role)&&identity.permissions.includes('finance.reports.view')
 if(runtime.mode!=='DISPOSABLE_TEST')return null
 return <section aria-label="Analisis produksi dan laporan resmi">
  {allowed?<label><input type="checkbox" checked={includeFinance} onChange={e=>setIncludeFinance(e.target.checked)}/>Sertakan angka keuangan dari laporan resmi</label>:null}
  <p>Pilihan ini berlaku untuk perhitungan baru. Pekerjaan tersimpan tetap memakai pilihan dan sumber asalnya.</p>
  <NativeFrozenQuantityPanel {...props} financeMode={allowed&&includeFinance?'STAGED':undefined} renderFinance={renderFinance}/>
 </section>
}
