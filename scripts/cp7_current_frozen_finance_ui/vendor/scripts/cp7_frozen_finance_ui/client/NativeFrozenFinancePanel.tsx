import {useCallback,useMemo,useState} from 'react'
import {useAuth} from '../../../src/auth/AuthProvider'
import {getUatSupabaseClient} from '../../../src/lib/supabase'
import {normalizeClientError} from '../../../src/lib/clientError'
import NativeAnalysisFinancePanel,{AnalysisFinanceSummary} from '../../../src/NativeAnalysisFinancePanel'
import type {NativeDemandQuery} from '../../../src/nativeDemandHistory'
import type {StagedAnalysis} from '../../../src/nativeAnalysisPages'
import type {StagedJob} from '../../../src/nativeStagedJob'
import NativeFrozenQuantityPanel from '../../cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel'
import {frozenQuantityStagedRequest,readFrozenQuantityFinanceStatus,type FrozenQuantitySession} from '../../cp7_frozen_quantity_ui/client/nativeFrozenQuantity'
import './frozen-finance.css'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
type Source={job:StagedJob;staged:StagedAnalysis|null}
type SourceProps={session:FrozenQuantitySession;source:Source;onAccessLost:(message:string)=>void}
function FinanceSource({session,source,onAccessLost}:SourceProps){
 const{runtime,identity}=useAuth()
 const client=useMemo(()=>runtime.mode==='DISPOSABLE_TEST'?getUatSupabaseClient(runtime):null,[runtime])
 const allowed=identity.status==='AUTHORIZED'&&['OWNER','ADMIN'].includes(identity.profile.role)&&identity.permissions.includes('finance.reports.view')
 const staged=source.staged
 const request=useMemo(()=>frozenQuantityStagedRequest(session.request),[session.request])
 const get=useCallback(async(id:string)=>{
  if(id!==session.request.id||!client||!staged)throw Error('Acuan laporan keuangan berubah.')
  try{return await readFrozenQuantityFinanceStatus(client,session,staged)}catch(error){
   const failure=normalizeClientError(error)
   if(failure.code==='AUTH_REQUIRED'||failure.code==='FORBIDDEN')onAccessLost(failure.message)
   throw error
  }
 },[client,onAccessLost,session,staged])
 if(!staged)return source.job.financeCapture?<section aria-label="Kemajuan laporan resmi"><AnalysisFinanceSummary data={source.job.financeCapture} allowed={allowed} progressOnly/></section>:null
 return <NativeAnalysisFinancePanel request={request} runId={staged.set.runId} reference={staged.set.reference} allowed={allowed} get={get}/>
}
const renderFinance=(session:FrozenQuantitySession,source:Source,onAccessLost:(message:string)=>void)=><FinanceSource key={session.request.id} session={session} source={source} onAccessLost={onAccessLost}/>

// Explicit disposable host. A owns default adoption and the complete composition.
export default function NativeFrozenFinancePanel(props:Props){
 const{runtime,identity}=useAuth(),[includeFinance,setIncludeFinance]=useState(false)
 const allowed=identity.status==='AUTHORIZED'&&['OWNER','ADMIN'].includes(identity.profile.role)&&identity.permissions.includes('finance.reports.view')
 if(runtime.mode!=='DISPOSABLE_TEST')return null
 return <section className="frozen-finance-panel" aria-label="Analisis produksi dan laporan resmi">
  {allowed?<label className="frozen-finance-choice"><input type="checkbox" checked={includeFinance} onChange={e=>setIncludeFinance(e.target.checked)}/>Sertakan angka keuangan dari laporan resmi</label>:null}
  <p>Pilihan ini berlaku untuk perhitungan baru. Perhitungan tersimpan tetap memakai pilihan asalnya. Gunakan Hitung kebutuhan terbaru untuk mengganti pilihan.</p>
  <NativeFrozenQuantityPanel {...props} financeMode={allowed&&includeFinance?'STAGED':undefined} renderFinance={renderFinance}/>
 </section>
}
