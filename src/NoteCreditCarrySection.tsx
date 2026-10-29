import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal} from './procurementContract'
import {parseNoteCorrectionWorkspace} from './noteCorrectionContract'
import {noteCreditCarryReview,type NoteCreditCarryBasis,type NoteCreditCarryReview} from './noteCreditCarryContract'
import type {SalesRead} from './salesReadContract'
import type {useProductionMutation} from './useProductionMutation'
type Recovery=ReturnType<typeof useProductionMutation>
export type NoteCarryState={kind:'PENDING'|'NONE'|'REQUIRED'|'REVIEWED';fingerprint?:string;review?:NoteCreditCarryReview;isCurrent:()=>boolean}
type Source=NonNullable<SalesRead['detail']>
export default function NoteCreditCarrySection({source,newNet,priceOnly,fingerprint,locked,stale,readFence,onChange,onInvalid}:{source:Source;newNet:string|null;priceOnly:boolean;fingerprint:string;locked:boolean;stale:boolean;readFence?:Pick<Recovery,'currentReadTicket'|'isReadCurrent'>;onChange:(state:NoteCarryState)=>void;onInvalid?:(message:string)=>void}){
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw Error('Sesi pemindahan kredit nota belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),sequence=useRef(0),parent=useRef(''),ticket=useRef<ReturnType<Recovery['currentReadTicket']>>(null)
 const sourceKey=JSON.stringify([source.id,source.row_version,source.review_token]);parent.current=sourceKey
 const [basis,setBasis]=useState<NoteCreditCarryBasis|null>(null),[loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[reload,setReload]=useState(0),[reviewed,setReviewed]=useState('')
 const currentReadTicket=readFence?.currentReadTicket,isReadCurrent=readFence?.isReadCurrent
 const current=()=>!!ticket.current&&!!isReadCurrent?.(ticket.current)
 useEffect(()=>{
  const n=++sequence.current,key=sourceKey,t=currentReadTicket?.()??null;ticket.current=null;setLoaded(false);setBasis(null);setError('');setReviewed('');onChange({kind:'PENDING',isCurrent:()=>false})
  if(!t||!isReadCurrent?.(t)){setBusy(false);setError('Muat ulang invoice sebelum memeriksa pemakaian kredit nota.');return}
  setBusy(true)
  void(async()=>{try{const r=await client.rpc('erp_cp7_get_note_correction_v2',{p_sale:source.id})
   if(n!==sequence.current||parent.current!==key||!isReadCurrent(t))return;if(r.error)throw r.error
   const w=parseNoteCorrectionWorkspace(r.data,source.id),d=w.current.detail
   if(d?.id!==source.id||d.row_version!==source.row_version||d.review_token!==source.review_token)throw Error('Nota berubah. Muat ulang invoice sebelum melanjutkan.')
   if(!isReadCurrent(t)||parent.current!==key)return;ticket.current=t;setBasis(w.credit_carry??null);setLoaded(true)
  }catch(e){if(n===sequence.current&&parent.current===key&&isReadCurrent(t)){const message=normalizeClientError(e).message;setError(message);onInvalid?.(message)}}finally{if(n===sequence.current)setBusy(false)}})()
  return()=>{++sequence.current;ticket.current=null}
 },[client,source.id,source.row_version,source.review_token,sourceKey,currentReadTicket,isReadCurrent,onChange,onInvalid,reload])
 const factsCurrent=current(),plan=basis&&newNet!==null?noteCreditCarryReview(basis,newNet):null,planKey=JSON.stringify([sourceKey,fingerprint,newNet,priceOnly,basis?.basis_sha256])
 const reviewedCurrent=!!plan&&reviewed===planKey&&factsCurrent&&!locked&&!stale
 useEffect(()=>{
  if(!loaded||!factsCurrent){onChange({kind:'PENDING',isCurrent:()=>false});return}
  const t=ticket.current,key=sourceKey,n=sequence.current,isCurrent=()=>!!t&&!!isReadCurrent?.(t)&&parent.current===key&&sequence.current===n
  if(!basis){onChange({kind:'NONE',isCurrent});return}
  onChange(reviewedCurrent?{kind:'REVIEWED',fingerprint,review:plan!,isCurrent}:{kind:'REQUIRED',isCurrent})
 },[loaded,factsCurrent,basis,reviewedCurrent,fingerprint,planKey,onChange,isReadCurrent,sourceKey])
 if(loaded&&!basis&&factsCurrent)return null
 return <section aria-label="Kredit pada nota pengganti">
  {busy?<p role="status">Memeriksa pemakaian kredit pada nota…</p>:null}{error?<p role="alert">{error}</p>:null}
  {!factsCurrent&&loaded?<p role="alert">Invoice sudah dimuat ulang. Periksa lagi pemakaian kredit nota.</p>:null}
  <button type="button" disabled={locked||stale||busy} onClick={()=>setReload(n=>n+1)}>Muat ulang pemakaian kredit nota</button>
  {basis?<><p>Kredit pelanggan yang sudah dipakai otomatis mengikuti nota pengganti: Rp{formatReceiptDecimal(basis.transfer_amount)}.</p>
   {newNet!==null&&plan?<p>Sisa piutang nota pengganti: Rp{formatReceiptDecimal(plan.remaining_amount)}.</p>:null}
   {!priceOnly?<p role="alert">Pemindahan kredit ini memerlukan jumlah, barang, gudang, dan waktu invoice yang sama.</p>:null}
   {basis.issues.length?<p role="alert">Riwayat nota ini masih memerlukan alur pembetulan tambahan. Pemakaian kredit tetap tersimpan.</p>:null}
   {priceOnly&&!basis.issues.length&&newNet!==null&&!plan?<p role="alert">Nilai nota pengganti belum mencukupi pemakaian kredit pada seluruh riwayatnya. Minimum Rp{formatReceiptDecimal(basis.minimum_replacement_net)}.</p>:null}
   <button type="button" disabled={locked||stale||!factsCurrent||!plan||!priceOnly} onClick={()=>setReviewed(planKey)}>Pemindahan kredit dan sisa sudah diperiksa</button>
   {reviewedCurrent?<p role="status">Nominal kredit dan sisa piutang sudah diperiksa.</p>:null}
  </>:null}
 </section>
}
