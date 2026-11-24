import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import type {AuthorizedAccess} from './auth/authPolicy'
import {hasPermission} from './auth/accessCatalog'
import {isConnectedRuntime,type ConnectedRuntimeConfig} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {hppPoolPeriodText} from './hppPoolContract'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import {readProductionRecovery} from './productionRecovery'
import {
 attendanceChoiceActions,attendanceChoiceDay,attendanceChoiceError,attendanceChoicePayload,attendanceChoiceReadQuery,attendanceChoiceReason,attendanceChoiceRpc,attendanceChoiceRupiah,attendanceChoiceSavePayload,
 parseAttendanceChoiceOutcome,parseAttendanceChoicePreview,parseAttendanceChoiceWorkspace,
 type AttendanceChoice,type AttendanceChoiceAction,type AttendanceChoicePayload,type AttendanceChoicePreview,type AttendanceChoiceWorkspace,
} from './attendancePeriodChoiceContract'
import './attendance-period-choice.css'

export type AttendancePeriodChoicePanelProps={onCommitted:()=>Promise<unknown>;refresh?:number;blocked?:boolean;initialPeriod?:{start:string;end:string};onInvalid?:(message:string)=>void}
const labels:Record<AttendanceChoiceAction,string>={CHOOSE:'Tentukan pilihan',CORRECT:'Betulkan pilihan',REVERSE:'Batalkan pilihan',ALLOCATE:'Alokasikan ke hasil jahit',CANCEL_ALLOCATION:'Batalkan alokasi ke hasil jahit'}
const choiceText=(choice:AttendanceChoice)=>choice==='CARRY'?'Diteruskan ke periode jahit berikutnya':'Beban periode ini'
const permittedError=(error:unknown)=>{const e=error as {code?:unknown;status?:unknown;message?:unknown}|null;return e?.code==='42501'||e?.status===401||e?.status===403||typeof e?.message==='string'&&/CP7_S03_(OWNER_REQUIRED|ACCESS_CHANGED|USER_INACTIVE)/.test(e.message)}

// Root owns mounting after actual backend qualification. This file is UI only.
export default function AttendancePeriodChoicePanel(props:AttendancePeriodChoicePanelProps){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return null
 if(identity.profile.role!=='OWNER'||!identity.profile.isActive||!hasPermission(identity,'finance.hpp.view'))return <section className="panel attendance-choice" aria-label="Pilihan biaya absensi per periode"><p>Halaman ini memerlukan Owner aktif dengan hak melihat HPP.</p></section>
 return <ConnectedChoicePanel key={runtime.projectRef+':'+identity.profile.id} {...props} runtime={runtime} identity={identity}/>
}
function ConnectedChoicePanel({runtime,identity,onCommitted,refresh=0,blocked=false,initialPeriod,onInvalid}:AttendancePeriodChoicePanelProps&{runtime:ConnectedRuntimeConfig;identity:AuthorizedAccess}){
 const rpc=useMemo(()=>attendanceChoiceRpc(getUatSupabaseClient(runtime)),[runtime])
 const recovery=useProductionMutation('ATTENDANCE_PERIOD_CHOICE')
 const {beginRead,finishRead,isReadCurrent,currentReadTicket,invalidate,run,reconcile}=recovery
 const mayManage=hasPermission(identity,'finance.hpp.manage')
 const authority=JSON.stringify([identity.profile.id,identity.profile.authUserId,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.profile.role,identity.profile.isActive,identity.permissions])
 const [start,setStart]=useState(initialPeriod?.start??''),[end,setEnd]=useState(initialPeriod?.end??'')
 const [action,setAction]=useState<AttendanceChoiceAction|''>(''),[selected,setSelected]=useState<AttendanceChoice|''>(''),[outputStart,setOutputStart]=useState(''),[outputEnd,setOutputEnd]=useState(''),[reason,setReason]=useState('')
 const [data,setData]=useState<AttendanceChoiceWorkspace|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[done,setDone]=useState(''),[permissionFault,setPermissionFault]=useState(false)
 const [otherOutcome,setOtherOutcome]=useState<{context:string;period_start:string;period_end:string;action:AttendanceChoiceAction;request_id:string}|null>(null)
 const [reviewed,setReviewed]=useState(false),[previewBusy,setPreviewBusy]=useState(false)
 type Quote={value:AttendanceChoicePreview;signature:string;serial:number;ticket:NonNullable<ReturnType<typeof currentReadTicket>>}
 const [quote,setQuote]=useState<Quote|null>(null)
 const query=useRef({period_start:start,period_end:end,offset:0,limit:25}),readSerial=useRef(0),previewSerial=useRef(0),submitting=useRef(false),mounted=useRef(false)
 const context=JSON.stringify([authority,blocked,refresh,start,end]),contextRef=useRef(context);contextRef.current=context
 const visiblePeriod=useRef({start,end});visiblePeriod.current={start,end}
 const committedRef=useRef(onCommitted);committedRef.current=onCommitted
 const invalidRef=useRef(onInvalid);invalidRef.current=onInvalid
 const retireQuote=useCallback(()=>{++previewSerial.current;setQuote(null);setReviewed(false);setPreviewBusy(false)},[])
 const retirePermission=useCallback((failure:unknown)=>{if(permittedError(failure)){retireQuote();setData(null);setPermissionFault(true);invalidate();invalidRef.current?.(attendanceChoiceError(failure))}},[invalidate,retireQuote])
 const load=useCallback(async()=>{
  const q={...query.current},capture=contextRef.current,n=++readSerial.current
  retireQuote();setData(null);setError('');setOtherOutcome(null)
  if(blocked||!attendanceChoiceDay(q.period_start)||!attendanceChoiceDay(q.period_end)||q.period_end<q.period_start)return false
  try{attendanceChoiceReadQuery(q)}catch{setError('Periksa periode asal: akhir tidak boleh sebelum mulai dan jaraknya paling banyak 366 hari.');return false}
  const ticket=beginRead();setLoading(true)
  try{
   const r=await rpc.workspace(q)
   if(n!==readSerial.current||capture!==contextRef.current||!isReadCurrent(ticket))return false
   if(r.error)throw r.error
   const w=parseAttendanceChoiceWorkspace(r.data,q),fresh=finishRead(ticket)
   setData(w);setPermissionFault(false);return fresh
  }catch(failure){if(n===readSerial.current&&capture===contextRef.current&&isReadCurrent(ticket)){retirePermission(failure);setError(attendanceChoiceError(failure))}return false}
  finally{if(n===readSerial.current)setLoading(false)}
 },[rpc,blocked,authority,refresh,beginRead,finishRead,isReadCurrent,retirePermission,retireQuote])
 const latestLoad=useRef(load);latestLoad.current=load
 useEffect(()=>{mounted.current=true;setDone('');void load();return()=>{mounted.current=false;++readSerial.current;++previewSerial.current}},[load])
 const available=data?attendanceChoiceActions(data):[]
 let payload:AttendanceChoicePayload|null=null
 try{if(action)payload=attendanceChoicePayload(action,{period_start:start,period_end:end,choice:action==='CHOOSE'||action==='CORRECT'?selected||null:null,output_start:action==='ALLOCATE'?outputStart:null,output_end:action==='ALLOCATE'?outputEnd:null,reason:attendanceChoiceReason(reason)})}catch{payload=null}
 const signature=JSON.stringify([context,action,payload,data?.source_binding,data?.current_choice,data?.current_allocation,data?.closed_through])
 const signatureRef=useRef(signature);signatureRef.current=signature
 const intent=JSON.stringify([context,action,payload]),intentRef=useRef(intent);intentRef.current=intent
 const sourceCurrent=!!data&&!blocked&&!permissionFault&&!recovery.workspaceStale&&data.period_start===start&&data.period_end===end
 const canManage=mayManage&&data?.can_manage===true
 const locked=recovery.busy||recovery.writerLocked||loading||blocked||permissionFault
 const canPreview=sourceCurrent&&canManage&&!locked&&!previewBusy&&!!action&&available.includes(action)&&payload!==null
 const currentQuote=quote&&quote.signature===signature&&quote.serial===previewSerial.current&&isReadCurrent(quote.ticket)&&sourceCurrent?quote.value:null
 const canSave=!!currentQuote&&reviewed&&canPreview
 async function preview(){
  if(!canPreview||!action||!payload||!data)return
  const ticket=currentReadTicket();if(!ticket)return
  const capture=signature,inputCapture=intent,n=++previewSerial.current,p=payload,a=action,w=data
  setQuote(null);setReviewed(false);setPreviewBusy(true);setError('');setDone('')
  try{const r=await rpc.preview(a,p);if(n!==previewSerial.current||capture!==signatureRef.current||!isReadCurrent(ticket))return;if(r.error)throw r.error
   const value=parseAttendanceChoicePreview(r.data,a,p,w);setQuote({value,signature:capture,serial:n,ticket})
  }catch(failure){if(n===previewSerial.current&&capture===signatureRef.current&&isReadCurrent(ticket)){const words=attendanceChoiceError(failure);retireQuote();retirePermission(failure);setError(words)
   if(!permittedError(failure)){await latestLoad.current();if(mounted.current&&intentRef.current===inputCapture)setError(words)}}}
  finally{if(n===previewSerial.current)setPreviewBusy(false)}
 }
 function handlers(capture:string,formCapture?:string):ProductionMutationHandlers{let refused:string|null=null,confirmed=false,confirmedVisible=false;return {
  send:async e=>{const r=await rpc.save(e);if(r.error){refused=attendanceChoiceError(r.error);if(mounted.current&&contextRef.current===capture){retirePermission(r.error);setError(refused)}const x=r.error as {code?:unknown;status?:unknown};return {data:r.data,error:{...x,message:refused}}}return r},
  validate:(v,e)=>{parseAttendanceChoiceOutcome(v,e)},
  retire:(v,e)=>{parseAttendanceChoiceOutcome(v,e);confirmed=true
   const p=attendanceChoiceSavePayload(e.action as AttendanceChoiceAction,e.payload),stored=readProductionRecovery(recovery.scope),pending=stored.pending.ATTENDANCE_PERIOD_CHOICE
   if(!mounted.current||contextRef.current!==capture||stored.corrupted||pending?.id!==e.id||pending.fingerprint!==e.fingerprint||formCapture!==undefined&&signatureRef.current!==formCapture)return
   if(p.period_start!==visiblePeriod.current.start||p.period_end!==visiblePeriod.current.end){setOtherOutcome({context:capture,period_start:p.period_start,period_end:p.period_end,action:e.action as AttendanceChoiceAction,request_id:e.id});return}
   confirmedVisible=true;retireQuote();setData(null);setAction('');setSelected('');setReason('');setDone('Pilihan biaya absensi sudah tercatat. Periode dan riwayat dimuat ulang.')},
  reload:async()=>{if(confirmed&&!confirmedVisible)return false;const current=await latestLoad.current();if(refused&&mounted.current&&contextRef.current===capture)setError(refused);if(confirmedVisible&&mounted.current&&contextRef.current===capture)await committedRef.current();return current},
 }}
 async function save(){if(!canSave||!action||!payload||!currentQuote||submitting.current)return;submitting.current=true;setReviewed(false)
  try{await run(action,{...payload,review_token:currentQuote.review_token},null,handlers(contextRef.current,signatureRef.current))}finally{submitting.current=false}
 }
 function fieldChange(change:()=>void,periodChange=false){retireQuote();setDone('');setError('');change();if(periodChange){setData(null);++readSerial.current;setLoading(false);query.current.offset=0;invalidate()}}
 const inputLocked=recovery.busy||!!recovery.pending||recovery.corruptedEnvelope||blocked
 let pendingIntent:{payload:ReturnType<typeof attendanceChoiceSavePayload>;action:AttendanceChoiceAction;request_id:string}|null=null
 if(recovery.pending)try{if(recovery.pending.expectedVersion!==null)throw Error('Invalid choice version');pendingIntent={payload:attendanceChoiceSavePayload(recovery.pending.action as AttendanceChoiceAction,recovery.pending.payload),action:recovery.pending.action as AttendanceChoiceAction,request_id:recovery.pending.id}}catch{pendingIntent=null}
 const recoveredOther=otherOutcome?.context===context?otherOutcome:null
 const notice=recovery.pending?pendingIntent?'Jawaban penyimpanan sebelumnya belum pasti. Periksa hasil permintaan yang sama; jangan membuat transaksi baru.':'Catatan permintaan terdahulu belum dapat diverifikasi. Penyimpanan diblokir; minta bantuan admin tanpa menghapus catatan lama.':recovery.corruptedEnvelope?'Catatan pemulihan di perangkat ini tidak dapat dibaca. Penyimpanan diblokir; minta bantuan admin tanpa menghapus catatan lama.':recovery.externalMutationBlocked?'Masih ada transaksi lain yang belum selesai. Selesaikan pada halamannya, lalu muat ulang periode.':recoveredOther?'Muat ulang periode yang sedang dibuka sebelum melanjutkan.':recovery.error&&!error&&(recovery.writerLocked||recovery.workspaceStale)?done?'Pilihan sudah tercatat, tetapi periode belum berhasil dimuat ulang. Muat ulang periode; jangan simpan ulang.':'Penyimpanan atau pemuatan ulang belum berhasil dipastikan. Muat ulang periode sebelum melakukan tindakan baru.':''
 return <section className="panel attendance-choice" aria-label="Pilihan biaya absensi per periode">
  <h2>Pilihan biaya absensi per periode</h2>
  <p>Untuk biaya absensi mandor biasa yang sudah disetujui saat periode asal belum memiliki hasil jahit. Owner memilih menunggu periode jahit berikutnya atau mencatatnya sebagai beban periode ini. Pembayaran gaji tidak menambah biaya absensi baru.</p>
  {blocked?<p role="alert">Halaman induk belum siap. Muat ulang sumber sebelum melanjutkan.</p>:null}
  {notice?<p role="alert">{notice}{recovery.pending&&!recovery.corruptedEnvelope?<button type="button" disabled={!pendingIntent||recovery.busy||!mayManage||data?.can_manage===false||blocked||permissionFault} onClick={()=>void reconcile(handlers(contextRef.current))}>Periksa hasil penyimpanan</button>:null}</p>:null}
  {pendingIntent?<section className="attendance-choice-review" aria-label="Permintaan biaya absensi tertunda"><h3>Permintaan yang belum dipastikan</h3><p>{labels[pendingIntent.action]} · periode asal {hppPoolPeriodText(pendingIntent.payload.period_start,pendingIntent.payload.period_end)}.</p>{pendingIntent.payload.output_start&&pendingIntent.payload.output_end?<p>Periode hasil jahit tujuan: {hppPoolPeriodText(pendingIntent.payload.output_start,pendingIntent.payload.output_end)}.</p>:null}<p>Alasan permintaan: {pendingIntent.payload.reason}</p><p>Identitas permintaan: {pendingIntent.request_id}</p><p>Bagian ini menunjukkan permintaan terdahulu yang tersimpan. Hasilnya diperiksa memakai isian dan identitas permintaan yang sama.</p></section>:null}
  {recoveredOther?<section className="attendance-choice-review" aria-label="Hasil permintaan periode terdahulu"><p role="status">Hasil {labels[recoveredOther.action].toLowerCase()} untuk periode asal {hppPoolPeriodText(recoveredOther.period_start,recoveredOther.period_end)} sudah dipastikan.</p><p>Identitas permintaan: {recoveredOther.request_id}</p><p>Periode yang sedang dibuka tetap mengikuti tanggal pilihan Anda. Muat ulang periode tersebut untuk melihat keadaan terbarunya.</p></section>:null}
  {done?<p role="status">{done}</p>:null}{error?<p role="alert">{error}</p>:null}{loading?<p role="status">Memuat periode dan riwayat biaya absensi…</p>:null}
  <form className="attendance-choice-period" onSubmit={e=>{e.preventDefault();query.current.offset=0;void load()}}>
   <label>Mulai periode asal<input type="date" aria-label="Mulai periode asal" value={start} disabled={inputLocked} onChange={e=>fieldChange(()=>{query.current.period_start=e.target.value;setStart(e.target.value)},true)}/></label>
   <label>Akhir periode asal<input type="date" aria-label="Akhir periode asal" value={end} disabled={inputLocked} onChange={e=>fieldChange(()=>{query.current.period_end=e.target.value;setEnd(e.target.value)},true)}/></label>
   <button type="submit" disabled={loading||recovery.busy||blocked}>Muat ulang periode</button>
  </form>
  {data?<>
   <h3>Periode asal {hppPoolPeriodText(data.period_start,data.period_end)}</h3>
   {data.source_problem?<p role="alert">Sumber belum dapat digunakan: {attendanceChoiceError({code:'P0001',message:data.source_problem})}</p>:null}
   <dl className="attendance-choice-facts"><div><dt>Biaya absensi sumber</dt><dd>{data.amount_cents===null?'Belum diketahui':attendanceChoiceRupiah(data.amount_cents)}</dd></div><div><dt>Hasil jahit periode asal</dt><dd>{data.original_period_sewing_qty===null?'Belum diketahui':BigInt(data.original_period_sewing_qty).toLocaleString('id-ID')+' pcs'}</dd></div><div><dt>Pembukuan ditutup sampai</dt><dd>{data.closed_through??'Belum ada periode tertutup'}</dd></div></dl>
   {data.current_choice?<article><h3>Pilihan yang berlaku: {choiceText(data.current_choice.choice)}</h3><p>{data.current_choice.reason}</p>{data.current_choice.journal_id?<p>Jurnal pilihan: {data.current_choice.journal_id}</p>:data.current_allocation?<p>Biaya sudah dialokasikan ke hasil jahit periode tujuan.</p>:<p>Biaya masih menunggu. Belum ada jurnal alokasi ke hasil jahit.</p>}{data.current_allocation?<p>Dialokasikan ke periode {hppPoolPeriodText(data.current_allocation.output_start,data.current_allocation.output_end)} · pool {data.current_allocation.pool_id}</p>:null}</article>:<p>Belum ada pilihan untuk periode asal ini.</p>}
   {!canManage?<p>Data dapat dilihat. Menyimpan pilihan memerlukan hak mengelola HPP.</p>:null}
   {canManage&&sourceCurrent&&available.length===0&&data.source_problem===null?<p role="status">{data.amount_cents==='0'?'Belum ada biaya absensi yang memenuhi syarat pada periode ini.':data.current_choice===null&&data.original_period_sewing_qty!=='0'?'Periode asal sudah memiliki hasil jahit. Periksa pool HPP periode asal.':'Tindakan belum tersedia karena periode terkait sudah ditutup. Periksa periode asal dan tujuan melalui alur Tutup Buku.'}</p>:null}
   {canManage?<div className="attendance-choice-form">
    <label>Tindakan<select aria-label="Tindakan pilihan biaya" value={action} disabled={inputLocked||loading||!sourceCurrent} onChange={e=>fieldChange(()=>{setAction(e.target.value as AttendanceChoiceAction|'');setSelected('')})}><option value="">Pilih tindakan</option>{available.map(a=><option key={a} value={a}>{labels[a]}</option>)}</select></label>
    {action==='CHOOSE'||action==='CORRECT'?<label>Pilihan biaya<select aria-label="Pilihan biaya absensi" value={selected} disabled={inputLocked} onChange={e=>fieldChange(()=>setSelected(e.target.value as AttendanceChoice|''))}><option value="">Pilih perlakuan biaya</option><option value="CARRY">Menunggu periode jahit berikutnya</option><option value="EXPENSE">Beban periode ini</option></select></label>:null}
    {action==='ALLOCATE'?<><label>Mulai periode hasil jahit<input aria-label="Mulai periode hasil jahit" type="date" value={outputStart} disabled={inputLocked} onChange={e=>fieldChange(()=>setOutputStart(e.target.value))}/></label><label>Akhir periode hasil jahit<input aria-label="Akhir periode hasil jahit" type="date" value={outputEnd} disabled={inputLocked} onChange={e=>fieldChange(()=>setOutputEnd(e.target.value))}/></label></>:null}
    <label>Alasan (5–1000 karakter)<textarea aria-label="Alasan pilihan biaya absensi" value={reason} maxLength={2000} disabled={inputLocked} onChange={e=>fieldChange(()=>setReason(e.target.value))}/></label>
    <button type="button" disabled={!canPreview} onClick={()=>void preview()}>Periksa perubahan biaya</button>{previewBusy?<p role="status">Memeriksa sumber, tanggal, dan pilihan biaya…</p>:null}
    {currentQuote?<section className="attendance-choice-review" aria-label="Tinjauan perubahan biaya"><h3>{labels[currentQuote.action]} · {attendanceChoiceRupiah(currentQuote.amount_cents)}</h3><p>Periode asal: {hppPoolPeriodText(currentQuote.payload.period_start,currentQuote.payload.period_end)} · {currentQuote.source_count} sumber biaya.</p>{currentQuote.payload.choice?<p>Pilihan: {choiceText(currentQuote.payload.choice)}</p>:null}{currentQuote.payload.output_start&&currentQuote.payload.output_end?<p>Periode hasil jahit tujuan: {hppPoolPeriodText(currentQuote.payload.output_start,currentQuote.payload.output_end)} · {currentQuote.denominator_qty} pcs.</p>:null}
     <p>Tanggal ekonomi: {currentQuote.economic_date??'Tidak membuat jurnal baru'} · tanggal buku: {currentQuote.book_date??'Tidak membuat jurnal baru'}.</p>
     {currentQuote.inverse_economic_date?<p>Tanggal ekonomi pembalik: {currentQuote.inverse_economic_date} · tanggal buku pembalik: {currentQuote.inverse_book_date}.</p>:null}
     {currentQuote.expense_account?<p>Rekening beban: {currentQuote.expense_account.code} · {currentQuote.expense_account.name} · {currentQuote.expense_account.id}.</p>:null}
     <p>Alasan: {currentQuote.payload.reason}</p><p>Pratinjau belum mencatat transaksi. Pembatalan dan koreksi tetap menyimpan riwayat sebelumnya.</p>
    </section>:null}
    <label><input type="checkbox" aria-label="Pilihan biaya sudah diperiksa" checked={reviewed} disabled={!currentQuote||locked} onChange={e=>setReviewed(e.target.checked)}/>Nominal, pilihan, periode asal dan tujuan, tanggal buku, rekening, dan alasan sudah diperiksa.</label>
    <button type="button" className="primary-btn" disabled={!canSave} onClick={()=>void save()}>Simpan pilihan biaya</button>
   </div>:null}
   <section aria-label="Riwayat pilihan biaya"><h3>Riwayat pilihan biaya</h3>{data.history.length===0?<p>Belum ada catatan pada halaman riwayat ini.</p>:null}<ol className="attendance-choice-history">{data.history.map(h=><li key={h.event_id}><strong>{labels[h.event]}</strong><p>{formatCp6WibDateTime(h.recorded_at)} · pelaku {h.actor}</p><p>{h.reason}</p>{h.event==='CHOOSE'?<p>{choiceText(h.choice)} · {attendanceChoiceRupiah(h.amount_cents)}{h.correction_of?' · membetulkan pilihan '+h.correction_of:''}</p>:null}{h.event==='ALLOCATE'?<p>Hasil jahit {hppPoolPeriodText(h.output_start,h.output_end)} · pool {h.pool_id}</p>:null}{'journal_id'in h&&h.journal_id?<p>Jurnal {h.journal_id}</p>:null}<p>Catatan {h.event_id} · pilihan {h.decision_id}</p></li>)}</ol><p>{data.history_total} catatan riwayat</p><div className="attendance-choice-buttons"><button type="button" disabled={loading||recovery.busy||blocked||data.offset===0} onClick={()=>{query.current.offset=Math.max(0,data.offset-data.limit);void load()}}>Riwayat sebelumnya</button><button type="button" disabled={loading||recovery.busy||blocked||data.next_offset===null||data.next_offset>100000} onClick={()=>{if(data.next_offset!==null){query.current.offset=data.next_offset;void load()}}}>Riwayat berikutnya</button></div></section>
  </>:null}
 </section>
}
