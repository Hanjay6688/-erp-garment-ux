import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {normalizeClientError} from './lib/clientError'
import {attendanceMarks,parseAttendancePreview,validPaidFraction,type AttendanceEntry,type AttendancePreview,type EntryCell,type EntryMode} from './attendanceEntryContract'
import type {AttendancePeriod} from './attendanceContract'
import type {useProductionMutation} from './useProductionMutation'
import type {Json} from './types/database.preconnect'
export type AttendanceSelection={mode:EntryMode;contractor:string;from:string;to:string;period:AttendancePeriod|null}
type MarkedCell=EntryCell&{mark:string;fraction:string;note:string}
const defaultFraction=(mark:string)=>mark==='HALF_DAY'?'0.5000':['ABSENT','OFF'].includes(mark)?'0.0000':'1.0000'
export default function AttendanceEntryEditor({selection,recovery,read,preview,cancel,commit}:{selection:AttendanceSelection;recovery:ReturnType<typeof useProductionMutation>;read:(query:Json)=>Promise<AttendanceEntry>;preview:(payload:Json,version:string|null)=>Promise<unknown>;cancel:()=>void;commit:(action:'SAVE'|'POST'|'REVERSE',payload:Json,version:string|null)=>void}){
 const {mode,contractor,from,to,period}=selection,edit=['CREATE','EDIT','CORRECT'].includes(mode),correction=mode==='CORRECT'
 const {beginRead,finishRead,isReadCurrent,invalidate}=recovery
 const [sheet,setSheet]=useState<AttendanceEntry|null>(null),[cells,setCells]=useState<MarkedCell[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[page,setPage]=useState(0),[bulk,setBulk]=useState(''),[number,setNumber]=useState(mode==='CREATE'?'':`${period?.number??''}${correction?'-K':''}`),[payDate,setPayDate]=useState(period?.pay_date??cp6WibDateTimeInput().slice(0,10)),[reason,setReason]=useState(''),[notes,setNotes]=useState(period?.notes??''),[estimate,setEstimate]=useState<{value:AttendancePreview;fingerprint:string}|null>(null),[reviewed,setReviewed]=useState(false)
 const seq=useRef(0)
 const load=useCallback(async()=>{
  const ticket=beginRead(),turn=++seq.current;setBusy(true);setError('');setSheet(null);setCells([]);setEstimate(null);setReviewed(false)
  try{
   let head:AttendanceEntry|null=null,offset=0,all:EntryCell[]=[]
   for(;;){
    const result=await read({contractor_id:contractor,date_from:from,date_to:to,period_id:period?.id??null,offset,limit:100})
    if(turn!==seq.current||!isReadCurrent(ticket))return
    if(result.contractor.id!==contractor||result.date_from!==from||result.date_to!==to||result.period?.id!==(period?.id)||result.page.offset!==offset||result.page.limit!==100||head&&(result.source_token!==head.source_token||result.page.total!==head.page.total||JSON.stringify(result.period)!==JSON.stringify(head.period)))throw Error('Periode atau sumber absensi berubah saat dimuat. Muat ulang seluruh periode.')
    head??=result;all=all.concat(result.page.rows)
    if(result.page.next_offset===null)break
    if(result.page.next_offset<=offset)throw Error('Halaman absensi tidak lengkap.');offset=result.page.next_offset
   }
   if(!head||BigInt(all.length)!==BigInt(head.page.total)||new Set(all.map(c=>c.id)).size!==all.length)throw Error('Catatan absensi belum lengkap. Muat ulang seluruh periode.')
   const status=head.period?.status
   if(mode==='CREATE'&&status||['EDIT','POST'].includes(mode)&&status!=='DRAFT'||['CORRECT','REVERSE'].includes(mode)&&status!=='POSTED')throw Error('Status periode berubah. Kembali ke daftar untuk memeriksa sumber terbaru.')
   if(head.period&&period&&head.period.row_version!==period.row_version)throw Error('Versi periode berubah. Kembali ke daftar untuk memeriksa sumber terbaru.')
   setSheet(head);setCells(all.map(c=>({...c,mark:c.record?.mark??'',fraction:c.record?.paid_fraction??'',note:c.record?.notes??''})));setPage(0);finishRead(ticket)
  }catch(e){if(turn===seq.current)setError(normalizeClientError(e).message)}finally{if(turn===seq.current)setBusy(false)}
 },[beginRead,finishRead,isReadCurrent,read,contractor,from,to,period,mode])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const missing=cells.filter(c=>c.required&&!c.mark).length,invalid=cells.some(c=>c.mark&&(!c.eligible||c.daily_rate===null||!validPaidFraction(c.mark,c.fraction))),incompleteCorrection=correction&&cells.some(c=>c.record&&!c.mark),consumed=sheet?.period?.consuming_payroll_count!=='0'&&sheet?.period?.consuming_payroll_count!==undefined
 const version=mode==='CREATE'||correction?null:sheet?.period?.row_version??null
 const body=useMemo<Json>(()=>({contractor_id:contractor,period_number:number.trim(),period_start:from,period_end:to,pay_date:payDate,reason:reason.trim(),notes:notes.trim()||null,...(mode==='EDIT'?{period_id:period!.id}:{}),...(correction?{correction_of_period_id:period!.id}:{}),attendance:cells.filter(c=>c.mark).map(c=>({worker_id:c.worker_id,attendance_date:c.date,status:c.mark,paid_fraction:c.fraction,notes:c.note.trim()||null,...(correction?{supersedes_attendance_record_id:c.record?.id??null}:mode==='EDIT'&&period?.correction_of_id?{supersedes_attendance_record_id:c.record?.supersedes_id??null}:{})})),...(mode==='EDIT'&&period?.correction_of_id?{correction_of_period_id:period.correction_of_id}:{})}),[contractor,number,from,to,payDate,reason,notes,mode,period,correction,cells])
 const payload:Json={contractor_id:contractor,date_from:from,date_to:to,source_token:sheet?.source_token??'',document:body},fingerprint=JSON.stringify(payload)
 const valid=!!sheet&&reason.trim().length>=5&&!!number.trim()&&!!payDate&&!invalid&&!incompleteCorrection&&!(correction&&consumed)
 const locked=busy||recovery.writerLocked,changed=()=>{setEstimate(null);setReviewed(false)}
 const update=(id:string,patch:Partial<MarkedCell>)=>{changed();setCells(old=>old.map(c=>c.id===id?{...c,...patch}:c))}
 const check=async()=>{
  if(!valid||locked)return;const turn=++seq.current;setBusy(true);setError('');setEstimate(null)
  try{const r=parseAttendancePreview(await preview(payload,version),payload);if(turn===seq.current)setEstimate({value:r,fingerprint})}catch(e){if(turn===seq.current){setError(normalizeClientError(e).message);setSheet(null);setCells([]);invalidate()}}finally{if(turn===seq.current)setBusy(false)}
 }
 const action=mode==='POST'?'POST':mode==='REVERSE'?'REVERSE':'SAVE',canCommit=edit?valid&&estimate?.fingerprint===fingerprint:!!sheet&&reason.trim().length>=5&&reviewed&&(mode!=='POST'||!missing&&!invalid)&&(mode!=='REVERSE'||!consumed)
 const commitNow=()=>{if(locked||!canCommit)return;const p:Json=edit?payload:{contractor_id:contractor,date_from:from,date_to:to,source_token:sheet!.source_token,document:{period_id:period!.id,reason:reason.trim()}};commit(action,p,version)}
 return <section className="panel catt-editor catt-entry" aria-label="Pencatatan absensi"><header><div className="eyebrow">{sheet?.contractor.name??'ABSENSI'}</div><h2>{({CREATE:'Periode absensi baru',EDIT:'Ubah draft absensi',CORRECT:'Koreksi absensi',POST:'Catat absensi',REVERSE:'Batalkan absensi'} as Record<EntryMode,string>)[mode]}</h2><p>{from} sampai {to}</p></header>
  {error?<p role="alert">{error}</p>:null}{busy?<p role="status">Memuat dan memeriksa seluruh catatan…</p>:null}
  <div className="catt-tools"><button disabled={busy||recovery.busy} onClick={()=>void load()}>Muat ulang periode</button><button disabled={busy||recovery.busy} onClick={cancel}>Kembali ke daftar periode</button></div>
  {sheet?<><fieldset disabled={locked}>
   {edit?<div className="catt-fields"><label>Nomor periode<input aria-label="Nomor periode absensi" value={number} maxLength={120} onChange={e=>{setNumber(e.target.value);changed()}}/></label><label>Tanggal gajian<input aria-label="Tanggal gajian absensi" type="date" value={payDate} onChange={e=>{setPayDate(e.target.value);changed()}}/></label></div>:<p><strong>{sheet.period?.number}</strong> · tanggal gajian {sheet.period?.pay_date}</p>}
   {consumed?<p role="alert">Periode dipakai oleh {sheet.period?.consuming_payroll_count} payroll aktif. Balik payroll terkait sebelum mengoreksi atau membatalkan absensi.</p>:null}
   <p>{cells.length} sel pekerja/tanggal dimuat lengkap. {missing} sel wajib belum dicatat. Sel kosong tidak dianggap tidak hadir atau libur.</p>
   {edit?<div className="catt-bulk"><label>Isi sel kosong pada halaman ini<select aria-label="Tanda massal absensi" value={bulk} onChange={e=>setBulk(e.target.value)}><option value="">Pilih tanda</option>{Object.entries(attendanceMarks).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><button disabled={!bulk} onClick={()=>{changed();const ids=new Set(cells.slice(page*20,(page+1)*20).filter(c=>c.eligible&&!c.mark&&(!correction||c.record)).map(c=>c.id));setCells(old=>old.map(c=>ids.has(c.id)?{...c,mark:bulk,fraction:defaultFraction(bulk)}:c))}}>Terapkan ke sel kosong halaman ini</button></div>:null}
   <div className="catt-matrix">{cells.slice(page*20,(page+1)*20).map(c=><article className="catt-cell" key={c.id} data-cell-id={c.id}><header><strong>{c.worker_name}</strong><span>{c.date}{c.required?' · Wajib':''}</span><small>{c.daily_rate===null?'Tarif belum tersedia':`Rp${numberText(c.daily_rate)} / hari`}</small>{!c.eligible?<small>Di luar masa kerja. Kosongkan catatan draft yang tidak berlaku.</small>:null}</header>
    {edit?<><label>Tanda kehadiran<select aria-label={`Kehadiran ${c.worker_name} ${c.date}`} value={c.mark} onChange={e=>update(c.id,{mark:e.target.value,fraction:e.target.value?defaultFraction(e.target.value):''})}><option value="">Belum dicatat</option>{Object.entries(attendanceMarks).map(([key,label])=><option key={key} value={key} disabled={!c.eligible||correction&&!c.record}>{label}</option>)}</select></label><label>Bagian hari dibayar<input aria-label={`Bagian hari ${c.worker_name} ${c.date}`} inputMode="decimal" value={c.fraction} disabled={!c.mark||['ABSENT','OFF'].includes(c.mark)} onChange={e=>update(c.id,{fraction:e.target.value.replace(',','.')})}/></label><label className="catt-cell-note">Catatan<input aria-label={`Catatan ${c.worker_name} ${c.date}`} value={c.note} maxLength={1000} onChange={e=>update(c.id,{note:e.target.value})}/></label></>:<div><strong>{c.mark?attendanceMarks[c.mark as keyof typeof attendanceMarks]:'Belum dicatat'}</strong>{c.mark?<p>{numberText(c.fraction)} hari dibayar</p>:null}{c.note?<p>{c.note}</p>:null}</div>}
   </article>)}</div>
   <div className="cproc-pagination"><span>Halaman {page+1} dari {Math.max(1,Math.ceil(cells.length/20))}</span><button disabled={!page} onClick={()=>setPage(page-1)}>Sel sebelumnya</button><button disabled={(page+1)*20>=cells.length} onClick={()=>setPage(page+1)}>Sel berikutnya</button></div>
   {invalid?<p role="alert">Periksa masa kerja, ketersediaan tarif, dan bagian hari dibayar. Setengah hari paling banyak 0,5.</p>:null}{incompleteCorrection?<p role="alert">Koreksi harus mengganti seluruh catatan asal secara jelas.</p>:null}
   {edit?<label>Catatan periode · opsional<textarea aria-label="Catatan periode absensi" value={notes} maxLength={2000} onChange={e=>{setNotes(e.target.value);changed()}}/></label>:null}
   <label>Alasan tindakan<textarea aria-label="Alasan tindakan absensi" value={reason} maxLength={1000} onChange={e=>{setReason(e.target.value);changed()}}/></label>
   {edit?<><button disabled={!valid} onClick={()=>void check()}>Pratinjau hitungan absensi</button>{estimate?.fingerprint===fingerprint?<div className="catt-review" role="status"><strong>Nilai absensi Rp{numberText(estimate.value.estimated_amount)}</strong><p>{estimate.value.line_count} catatan · {numberText(estimate.value.paid_day_equivalent)} hari dibayar × tarif harian di data pekerja.</p><p>Ini bukan upah payroll: payroll menghitung upah sesuai cara bayar pekerja (harian, borongan, atau campuran). Draft ini belum mengakui biaya payroll atau membayar gaji.</p></div>:null}</>:<><p>{mode==='POST'?'Posting menyediakan catatan absensi untuk perhitungan payroll. Pengakuan biaya dan pembayaran tetap melalui payroll.':'Pembatalan menyimpan riwayat absensi. Jika ini dokumen koreksi, catatan asal akan dipulihkan.'}</p><label className="catt-check"><input aria-label="Absensi sudah diperiksa" type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa catatan dan tindakan ini.</label></>}
   <button className="primary-btn" disabled={!canCommit} onClick={commitNow}>{action==='SAVE'?'Simpan draft absensi':action==='POST'?'Posting absensi sekarang':'Batalkan absensi sekarang'}</button>
  </fieldset></>:null}
 </section>
}
