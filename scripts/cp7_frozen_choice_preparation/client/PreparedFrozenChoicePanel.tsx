import {useEffect,useRef,useState,type ComponentProps,type ReactNode} from 'react'
import NativeFrozenChoicePanel from '../../cp7_frozen_choice_ui/client/NativeFrozenChoicePanel'
import {normalizeClientError} from '../../../src/lib/clientError'
import {formatCp6WibDateTime} from '../../../src/cp6BusinessTime'
import {frozenDuration} from '../../cp7_frozen_quantity_ui/client/nativeFrozenProgress'
import {choicePreparationRPC,driveChoicePreparation,type ChoicePreparation} from './nativeFrozenChoicePreparation'

type Props=ComponentProps<typeof NativeFrozenChoicePanel>
// Explicit optional host. Existing default/qualified hosts are not rerouted.
export default function PreparedFrozenChoicePanel(props:Props){
 return <ChoicePreparationGate client={props.client} context={props.context} scope={props.scope} enabled={props.canManage} onAccessLost={props.onAccessLost}>{ready=><NativeFrozenChoicePanel {...props} candidates={ready?props.candidates:null}/>}</ChoicePreparationGate>
}
type GateProps=Pick<Props,'client'|'context'|'scope'|'onAccessLost'>&{enabled:boolean;children:(ready:boolean)=>ReactNode}
export function ChoicePreparationGate(props:GateProps){
 return <Workspace {...props} key={JSON.stringify([props.scope,props.context,props.enabled])}/>
}
function Workspace({client,context,enabled,onAccessLost,children}:GateProps){
 const seq=useRef(0),active=useRef(false)
 const[state,setState]=useState<ChoicePreparation|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[clock,setClock]=useState(Date.now())
 const report=(value:unknown)=>{
  const f=normalizeClientError(value);setError(f.message)
  if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED'){setState(null);onAccessLost(f.message)}
 }
 useEffect(()=>{
  const n=++seq.current
  if(!enabled||context.sourceMethod!=='FROZEN_V2')return
  active.current=true;setBusy(true)
  void choicePreparationRPC(client,'get',context).then(s=>{if(n===seq.current)setState(s)},e=>{
   if(n!==seq.current)return
   if(!(e&&typeof e==='object'&&'message'in e&&e.message==='CP7_CHOICE_PREPARATION_NOT_STARTED'))report(e)
  }).finally(()=>{if(n===seq.current){active.current=false;setBusy(false)}})
  return()=>{++seq.current;active.current=false}
 // The enclosing immutable identity key remounts on every context/permission change.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[client])
 const running=state?.state==='QUEUED'||state?.state==='RUNNING'
 useEffect(()=>{if(!running)return;setClock(Date.now());const t=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(t)},[running])
 const prepare=async()=>{
  if(active.current||!enabled)return
  const n=++seq.current;active.current=true;setBusy(true);setError('')
  try{await driveChoicePreparation(client,context,{current:()=>n===seq.current,status:s=>setState(s)})}
  catch(e){if(n===seq.current)report(e)}
  finally{if(n===seq.current){active.current=false;setBusy(false)}}
 }
 const ready=state?.state==='READY',failed=state?.state==='FAILED'||state?.state==='EXPIRED'
 return <>
  {enabled?<section aria-label="Persiapan pemeriksaan pilihan">
   <h5>Persiapan pemeriksaan pilihan</h5>
   <p>Siapkan data pembanding sebelum menyimpan pilihan. Pekerjaan ini memakai acuan analisis yang sama.</p>
   {state?<>
    <p role="status">{ready?'Persiapan selesai. Pilihan belum disimpan.':state.state==='FAILED'?'Persiapan gagal. Pilihan belum disimpan.':state.state==='EXPIRED'?'Acuan sudah kedaluwarsa.':state.state==='RUNNING'?'Menyiapkan data pembanding…':'Persiapan mengantre.'}</p>
    <p>{state.unitsDone} dari 1 langkah persiapan selesai. {running?`Waktu sejak diminta: ${frozenDuration((clock-Date.parse(state.createdAt))/1000)}.`:''}</p>
    <p>Acuan data: {formatCp6WibDateTime(context.reference.capturedAt)}.</p>
   </>:busy?<p role="status">Memeriksa persiapan tersimpan…</p>:null}
   {error?<p role="alert">{error}</p>:null}
   {failed?<p>{state?.failure==='CP7_CHOICE_PREPARATION_TIME_LIMIT'?'Persiapan berhenti setelah tiga percobaan pada langkah yang sama melampaui batas. Acuan lama tetap tersimpan; periksa penyebab sebelum mencoba analisis baru.':'Periksa data dan konfigurasi analisis sebelum membuat perhitungan baru.'}</p>:null}
   {!ready&&!failed?<button disabled={busy} onClick={()=>void prepare()}>{state?'Lanjutkan persiapan yang sama':'Siapkan pemeriksaan pilihan'}</button>:null}
   {running?<p>Anda boleh meninggalkan halaman. Buka analisis yang sama untuk membaca status dan melanjutkan. Kelanjutan otomatis di server belum dikonfirmasi.</p>:null}
  </section>:null}
  {children(ready)}
 </>
}
