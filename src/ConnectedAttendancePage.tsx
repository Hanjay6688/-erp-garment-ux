import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseAttendanceRead,parseRosterOutcome,type RosterAction,type AttendanceContractor,type AttendanceEmployment,type AttendancePeriod,type AttendanceRate,type AttendanceRead,type AttendanceRecord,type AttendanceSection,type AttendanceWorker} from './attendanceContract'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import RosterEditor from './RosterEditor'
import AttendanceEntryEditor,{type AttendanceSelection} from './AttendanceEntryEditor'
import {parseAttendanceEntry,parseAttendanceOutcome,type EntryMode} from './attendanceEntryContract'
import type {Json} from './types/database.preconnect'
import './procurement-connected.css'
import './attendance-connected.css'
const money=(v:string)=>`Rp${numberText(v)}`
const statuses:Record<string,string>={DRAFT:'Draft',POSTED:'Tercatat',CORRECTED:'Dikoreksi',REVERSED:'Dibatalkan',LEGACY_POSTED:'Catatan lama'}
const marks:Record<string,string>={PRESENT:'Hadir',ABSENT:'Tidak hadir',HALF_DAY:'Setengah hari',SICK:'Sakit',LEAVE:'Izin / cuti',OFF:'Libur'}
export default function ConnectedAttendancePage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.attendance.view'))return <section className="panel" role="alert">Hak melihat absensi diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
import RecordTools,{orderRecordPage,type RecordPageOrder} from './RecordTools'

function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi absensi belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),today=cp6WibDateTimeInput().slice(0,10)
 const [from,setFrom]=useState(today),[to,setTo]=useState(today),[q,setQ]=useState(''),[data,setData]=useState<AttendanceRead|null>(null),[detail,setDetail]=useState<AttendanceRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const mutation=useProductionMutation('ROSTER'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [listOrder,setListOrder]=useState<RecordPageOrder>('SOURCE')
 const retireSearch=()=>{++seq.current;setData(null);setDetail(null);setBusy(false);setAction(null);setEntry(null)}
 const [action,setAction]=useState<RosterAction|null>(null),canManage=['OWNER','ADMIN'].includes(identity.profile.role),canCreate=canManage&&identity.permissions.includes('finance.attendance.create'),canEdit=canManage&&identity.permissions.includes('finance.attendance.edit_draft')
 const [entry,setEntry]=useState<AttendanceSelection|null>(null)
 const seq=useRef(0),requested=useRef({contractor:null as string|null,from:today,to:today,q:'',offset:0,section:'WORKERS' as 'WORKERS'|'PERIODS',focus:null as AttendanceWorker|AttendancePeriod|null,detailSection:'RATES' as 'RATES'|'EMPLOYMENT'|'RECORDS',detailOffset:0})
 const load=useCallback(async()=>{
  const f={...requested.current},s=++seq.current,ticket=beginRead();setAction(null);setEntry(null);setBusy(true);setData(null);setDetail(null);setError('')
  const section:AttendanceSection=f.contractor?f.section:'CONTRACTORS',base={contractor_id:f.contractor,date_from:f.from,date_to:f.to}
  const query:Json=f.contractor?{...base,q:f.q,offset:f.offset,limit:25}:{q:f.q,offset:f.offset,limit:25}
  const dQuery:Json=f.focus?f.section==='WORKERS'?{...base,worker_id:f.focus.id,offset:f.detailOffset,limit:25}:{...base,date_from:(f.focus as AttendancePeriod).period_start,date_to:(f.focus as AttendancePeriod).period_end,period_id:f.focus.id,offset:f.detailOffset,limit:25}:{}
  try{
   const results=await Promise.allSettled([client.rpc('erp_cp7_get_attendance_workspace_v1',{p_section:section,p_query:query}),...(f.focus?[client.rpc('erp_cp7_get_attendance_workspace_v1',{p_section:f.detailSection,p_query:dQuery})]:[])])
   if(s!==seq.current||!isReadCurrent(ticket))return false
   const values=results.map(r=>{if(r.status==='rejected')throw r.reason;if(r.value.error)throw r.value.error;return r.value.data}),list=parseAttendanceRead(values[0],section),d=f.focus?parseAttendanceRead(values[1],f.detailSection):null
   if(list.page.offset!==f.offset||list.page.limit!==25||f.contractor&&(list.contractor?.id!==f.contractor||list.date_from!==f.from||list.date_to!==f.to))throw Error('Pilihan mandor atau tanggal berubah. Muat ulang absensi.')
   if(d){
    const selected=list.page.rows.find(x=>x.id===f.focus?.id),parent=d.worker??d.period
    if(!selected||!parent||parent.id!==f.focus?.id||d.contractor?.id!==f.contractor||d.page.offset!==f.detailOffset||d.page.limit!==25||JSON.stringify(selected)!==JSON.stringify(parent))throw Error('Sumber absensi berubah saat dibaca. Muat ulang rincian.')
    if(f.section==='WORKERS'&&(d.date_from!==f.from||d.date_to!==f.to)||d.date_from===list.date_from&&d.date_to===list.date_to&&d.source_token!==list.source_token)throw Error('Tarif atau riwayat kerja berubah. Muat ulang absensi.')
   }
   setData(list);setDetail(d);return finishRead(ticket)
  }catch(e){if(s===seq.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}finally{if(s===seq.current)setBusy(false)}
 },[client,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const locked=busy||mutation.writerLocked
 const handlers:ProductionMutationHandlers={
  send:e=>{const p=e.payload as {document:Json;expected_version:string|null};if(e.action.endsWith('_ATTENDANCE'))return client.rpc('erp_cp7_save_attendance_v1',{p_action:e.action.replace('_ATTENDANCE',''),p_payload:p.document,p_request:e.id,p_expected:p.expected_version});return client.rpc('erp_cp7_save_roster_v1',{p_action:e.action,p_payload:p.document,p_request:e.id,p_expected:p.expected_version})},
  validate:(v,e)=>{if(e.action.endsWith('_ATTENDANCE'))parseAttendanceOutcome(v,e.id,e.action.replace('_ATTENDANCE',''),e.payload);else parseRosterOutcome(v,e.id,e.action,e.payload)},
  retire:(v,e)=>{const isAttendance=e.action.endsWith('_ATTENDANCE'),r=isAttendance?parseAttendanceOutcome(v,e.id,e.action.replace('_ATTENDANCE',''),e.payload):parseRosterOutcome(v,e.id,e.action,e.payload),p=(e.payload as {document:{date_from:string;date_to:string}}).document;requested.current={...requested.current,contractor:r.contractor_id,from:p.date_from,to:p.date_to,q:'',offset:0,section:isAttendance?'PERIODS':'WORKERS',focus:null,detailOffset:0};setFrom(p.date_from);setTo(p.date_to);setQ('');setAction(null);setEntry(null);setData(null);setDetail(null)},reload:load,
 }
 const write=(document:Json)=>{if(!action||locked||!data?.contractor||!data.source_token||action!=='CREATE_WORKER'&&!detail?.worker)return;const payload={document:{contractor_id:data.contractor.id,date_from:data.date_from,date_to:data.date_to,source_token:data.source_token,document},expected_version:action==='CREATE_WORKER'?null:detail!.worker!.row_version};setAction(null);setData(null);setDetail(null);void run(action,payload,null,handlers)}
 const entryRead=useCallback(async(query:Json)=>{const r=await client.rpc('erp_cp7_get_attendance_entry_v1',{p_query:query});if(r.error)throw r.error;return parseAttendanceEntry(r.data)},[client])
 const entryPreview=useCallback(async(payload:Json,version:string|null)=>{const r=await client.rpc('erp_cp7_preview_attendance_v1',{p_payload:payload,p_expected:version});if(r.error)throw r.error;return r.data},[client])
 const openEntry=(mode:EntryMode)=>{if(!data?.contractor||locked)return;const h=mode==='CREATE'?null:detail?.period??null;if(mode!=='CREATE'&&!h)return;setAction(null);setEntry({mode,contractor:data.contractor.id,from:h?.period_start??data.date_from!,to:h?.period_end??data.date_to!,period:h})}
 const writeEntry=(action:'SAVE'|'POST'|'REVERSE',payload:Json,version:string|null)=>{if(locked)return;setEntry(null);setData(null);setDetail(null);void run(action+'_ATTENDANCE',{document:payload,expected_version:version},null,handlers)}
 const changeSection=(section:'WORKERS'|'PERIODS')=>{requested.current={...requested.current,section,q:'',offset:0,focus:null,detailOffset:0};setQ('');void load()}
 const select=(row:AttendanceWorker|AttendancePeriod)=>{requested.current.focus=row;requested.current.detailSection=requested.current.section==='WORKERS'?'RATES':'RECORDS';requested.current.detailOffset=0;void load()}
 return <section className="cproc catt"><header className="panel cproc-heading"><div><div className="eyebrow">MANDOR · ABSENSI</div><h1>Absensi & Rate Harian</h1><p>Telusuri hari kerja, tarif pada tanggalnya, serta periode yang sudah dipakai payroll.</p></div><button disabled={busy||mutation.busy} onClick={()=>void load()}>Muat ulang absensi</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel" noticeText="Sumber absensi tersimpan. Data terbaru sudah dimuat." messageText={mutation.pending&&!mutation.corruptedEnvelope?mutation.pending.action.endsWith('_ATTENDANCE')?'Status simpan absensi belum pasti. Periksa status untuk melanjutkan.':'Status simpan pekerja belum pasti. Periksa status untuk melanjutkan.':mutation.error.includes('CP7_ROSTER_REVIEW_CHANGED')||mutation.error.includes('CP7_ROSTER_VERSION_CHANGED')?'Data pekerja atau tarif berubah. Periksa sumber terbaru sebelum menyimpan kembali.':undefined} reconcileLabel={mutation.pending?.action.endsWith('_ATTENDANCE')?'Periksa status simpan absensi':'Periksa status simpan pekerja'}/>
  {error?<p className="panel" role="alert">{error}</p>:null}
     <RecordTools title="absensi" browseLabel="Browse mandor pada tanggal terpilih" busy={busy||mutation.busy} submitDisabled={!from||!to||to<from} order={listOrder} onOrder={setListOrder} submitLabel="Tampilkan absensi"
    onSubmit={e=>{e.preventDefault();requested.current={...requested.current,from,to,q:q.trim(),offset:0,focus:null,detailOffset:0};void load()}}
    onBrowse={()=>{retireSearch();setQ('');setListOrder('SOURCE');requested.current={...requested.current,contractor:null,from,to,q:'',offset:0,focus:null,detailOffset:0};void load()}}
    search={<label>{requested.current.contractor?'Cari pekerja atau periode':'Cari mandor'}<input aria-label="Pencarian absensi" maxLength={120} value={q} onChange={e=>{retireSearch();setQ(e.target.value)}}/></label>}
    filters={<><label>Dari tanggal<input aria-label="Absensi dari tanggal" type="date" value={from} onChange={e=>{retireSearch();setFrom(e.target.value)}}/></label><label>Sampai tanggal<input aria-label="Absensi sampai tanggal" type="date" value={to} onChange={e=>{retireSearch();setTo(e.target.value)}}/></label></>}/>

  {requested.current.contractor?<div className="panel catt-tools"><button disabled={busy||mutation.busy} onClick={()=>{requested.current={...requested.current,contractor:null,q:'',offset:0,focus:null,detailOffset:0};setQ('');void load()}}>Kembali ke daftar mandor</button><div role="group" aria-label="Sumber absensi"><button disabled={busy||mutation.busy} aria-pressed={requested.current.section==='WORKERS'} onClick={()=>changeSection('WORKERS')}>Pekerja & riwayat tarif</button><button disabled={busy||mutation.busy} aria-pressed={requested.current.section==='PERIODS'} onClick={()=>changeSection('PERIODS')}>Periode absensi</button></div></div>:null}
  {data?.section==='WORKERS'&&canCreate?<div className="catt-tools"><button className="primary-btn" disabled={locked} onClick={()=>setAction('CREATE_WORKER')}>Tambah pekerja</button></div>:null}
  {data?.section==='PERIODS'&&identity.permissions.includes('finance.attendance.create')?<div className="catt-tools"><button className="primary-btn" disabled={locked} onClick={()=>openEntry('CREATE')}>Tambah periode absensi</button></div>:null}
  {entry?<AttendanceEntryEditor key={`${entry.mode}:${entry.period?.id??'new'}:${entry.from}:${entry.to}`} selection={entry} recovery={mutation} read={entryRead} preview={entryPreview} cancel={()=>void load()} commit={writeEntry}/>:null}
  {action&&data?<RosterEditor key={`${data.source_token}:${detail?.worker?.id??'new'}:${action}`} action={action} source={data} worker={action==='CREATE_WORKER'?null:detail?.worker??null} disabled={locked} cancel={()=>setAction(null)} submit={write}/>:null}
  {busy?<p role="status">Memuat sumber absensi…</p>:null}
  {data?<div className="catt-layout"><section className="panel"><h2>{data.contractor?.name??'Daftar mandor'}</h2>{data.contractor?<><p>Data {data.date_from} sampai {data.date_to}</p><p>{data.contractor.attendance_required?'Absensi wajib untuk mandor ini.':'Mandor ini tidak diwajibkan memakai absensi.'}</p></>:null}
   {data.section==='CONTRACTORS'?orderRecordPage(data.page.rows,listOrder,item=>(item as AttendanceContractor).name).map(item=>{const c=item as AttendanceContractor;return <button className="cproc-receipt" key={c.id} disabled={busy||mutation.busy} onClick={()=>{requested.current={...requested.current,contractor:c.id,q:'',offset:0,focus:null,detailOffset:0};setQ('');void load()}}><span><strong>{c.name}</strong><small>{c.active_now?'Aktif':'Nonaktif sekarang'}</small></span><span>{c.attendance_required?'Absensi wajib':'Tidak wajib'}</span></button>}):data.section==='WORKERS'?orderRecordPage(data.page.rows,listOrder,item=>(item as AttendanceWorker).name).map(item=>{const w=item as AttendanceWorker;return <button className="cproc-receipt" key={w.id} disabled={busy||mutation.busy} onClick={()=>select(w)} aria-pressed={detail?.worker?.id===w.id}><span><strong>{w.name}</strong><small>{w.job_description??'Pekerjaan belum tercatat'}</small><small>{w.active_now?'Aktif sekarang':'Nonaktif sekarang · termasuk riwayat periode ini'}</small></span><span>{w.daily_rate_at_date===null?'Tarif belum tersedia':money(w.daily_rate_at_date)}<small>Pada {w.rate_at}</small></span></button>}):orderRecordPage(data.page.rows,listOrder,item=>(item as AttendancePeriod).number).map(item=>{const h=item as AttendancePeriod;return <button className="cproc-receipt" key={h.id} disabled={busy||mutation.busy} onClick={()=>select(h)} aria-pressed={detail?.period?.id===h.id}><span><strong>{h.number}</strong><small>{h.period_start} sampai {h.period_end}</small></span><span>{statuses[h.status]}<small>{h.record_count} catatan</small></span></button>})}
   {!data.page.rows.length?<p>Tidak ada sumber yang cocok untuk pilihan ini.</p>:null}<Pager label="Sumber" read={data} busy={busy||mutation.busy} change={offset=>{requested.current.offset=offset;requested.current.focus=null;void load()}}/>
  </section><section className="panel catt-detail" aria-label="Rincian sumber absensi"><h2>{detail?.worker?.name??detail?.period?.number??'Pilih sumber absensi'}</h2>
   {detail?.worker?<><p>{detail.worker.job_description??'Pekerjaan belum tercatat'} · {detail.worker.pay_scheme}</p><p>Riwayat yang berlaku antara {detail.date_from} dan {detail.date_to}.</p>{canEdit?<div className="catt-tools"><button disabled={locked||!detail.worker.joined_at} onClick={()=>setAction('UPDATE_WORKER')}>Ubah pekerja</button><button disabled={locked} onClick={()=>setAction('SET_RATE')}>Tambah tarif harian</button></div>:null}<div className="catt-tabs" role="group" aria-label="Riwayat pekerja">{(['RATES','EMPLOYMENT'] as const).map(section=><button key={section} aria-pressed={detail.section===section} disabled={busy||mutation.busy} onClick={()=>{requested.current.detailSection=section;requested.current.detailOffset=0;void load()}}>{section==='RATES'?'Riwayat tarif':'Riwayat masa kerja'}</button>)}</div></>:null}
   {detail?.period?<><p>{detail.period.period_start} sampai {detail.period.period_end} · {statuses[detail.period.status]}</p><p>Tanggal gajian {detail.period.pay_date}</p><p>{detail.period.consuming_payroll_count!=='0'?`Dipakai oleh ${detail.period.consuming_payroll_count} payroll aktif. Balik payroll terkait sebelum memperbaiki absensi.`:'Belum dipakai oleh payroll aktif.'}</p><p>Hari yang belum dicatat tidak dianggap tidak hadir atau libur.</p><div className="catt-tools">{detail.period.status==='DRAFT'?<>{identity.permissions.includes('finance.attendance.edit_draft')&&(!detail.period.correction_of_id||canManage)?<button disabled={locked} onClick={()=>openEntry('EDIT')}>Ubah draft absensi</button>:null}{identity.permissions.includes('finance.attendance.post')&&(!detail.period.correction_of_id||canManage)?<button disabled={locked} onClick={()=>openEntry('POST')}>Posting absensi</button>:null}</>:null}{detail.period.status==='POSTED'&&canManage?<>{identity.permissions.includes('finance.attendance.create')?<button disabled={locked||detail.period.consuming_payroll_count!=='0'} onClick={()=>openEntry('CORRECT')}>Koreksi absensi</button>:null}{identity.permissions.includes('finance.attendance.reverse')?<button disabled={locked||detail.period.consuming_payroll_count!=='0'} onClick={()=>openEntry('REVERSE')}>Batalkan absensi</button>:null}</>:null}</div></>:null}
   {detail?<><div className="catt-lines">{detail.page.rows.map(item=>detail.section==='RATES'?<Rate key={item.id} row={item as AttendanceRate}/>:detail.section==='EMPLOYMENT'?<Employment key={item.id} row={item as AttendanceEmployment}/>:<Record key={item.id} row={item as AttendanceRecord}/>)}{!detail.page.rows.length?<p>Belum ada rincian pada rentang tanggal ini.</p>:null}</div><Pager label="Rincian" read={detail} busy={busy||mutation.busy} change={offset=>{requested.current.detailOffset=offset;void load()}}/></>:<p>Pilih pekerja untuk melihat tarif dan masa kerja, atau pilih periode untuk melihat catatan harian.</p>}
  </section></div>:null}
 </section>
}
function Pager({label,read,busy,change}:{label:string;read:AttendanceRead;busy:boolean;change:(offset:number)=>void}){const p=read.page;return <div className="cproc-pagination"><span>Total {p.total}</span><button disabled={busy||!p.offset} onClick={()=>change(Math.max(0,p.offset-25))}>{label} sebelumnya</button><button disabled={busy||p.next_offset===null} onClick={()=>change(p.next_offset??0)}>{label} berikutnya</button></div>}
function Rate({row:r}:{row:AttendanceRate}){return <article className="catt-line"><header><strong>{money(r.daily_rate)} / hari</strong></header><p>{r.date_from} sampai {r.date_to??'seterusnya'}</p><p>{r.reason}</p></article>}
function Employment({row:r}:{row:AttendanceEmployment}){return <article className="catt-line"><header><strong>{r.date_from} sampai {r.date_to??'masih bekerja'}</strong></header><p>Mulai: {r.start_reason}</p>{r.end_reason?<p>Berakhir: {r.end_reason}</p>:null}</article>}
function Record({row:r}:{row:AttendanceRecord}){return <article className="catt-line"><header><strong>{r.worker_name}</strong><strong>{marks[r.mark]}</strong></header><p>{r.date} · {numberText(r.paid_fraction)} hari dibayar · {statuses[r.lifecycle]}</p>{r.notes?<p>{r.notes}</p>:null}</article>}
