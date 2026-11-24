import {useState} from 'react'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import type {AttendanceRead,AttendanceWorker,RosterAction} from './attendanceContract'
import type {Json} from './types/database.preconnect'
export default function RosterEditor({action,source,worker,disabled,cancel,submit}:{action:RosterAction;source:AttendanceRead;worker:AttendanceWorker|null;disabled:boolean;cancel:()=>void;submit:(document:Json)=>void}){
 const create=action==='CREATE_WORKER',rateOnly=action==='SET_RATE',today=cp6WibDateTimeInput().slice(0,10)
 const [name,setName]=useState(worker?.name??''),[job,setJob]=useState(worker?.job_description??''),[code,setCode]=useState(''),[scheme,setScheme]=useState(worker?.pay_scheme??'DAILY'),[joined,setJoined]=useState(worker?.joined_at??source.date_from??today),[active,setActive]=useState(worker?.active_now??true),[left,setLeft]=useState(worker?.left_at??today),[restart,setRestart]=useState(today),[rate,setRate]=useState(''),[effective,setEffective]=useState(create?source.date_from??today:today),[notes,setNotes]=useState(worker?.notes??''),[reason,setReason]=useState('')
 const exactRate=rate.trim().replace(',','.'),thousandsLike=/^[1-9][0-9]{0,2}[.,][0-9]{3}$/.test(rate.trim()),validRate=!thousandsLike&&/^(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?$/.test(exactRate),reactivating=!create&&worker?.active_now===false&&active
 const valid=reason.trim().length>=5&&(rateOnly?validRate&&effective:!!name.trim()&&!!job.trim()&&!!joined&&(!create||validRate&&!!effective&&effective<=joined)&&(active||!!left&&left>=joined&&left<=today)&&(!reactivating||!!restart&&restart<=today&&(!worker?.left_at||restart>worker.left_at)))
 const save=()=>{
  if(!valid||disabled)return
  const document:Json=rateOnly?{worker_id:worker!.id,daily_rate:exactRate,effective_from:effective,reason:reason.trim()}:{contractor_id:source.contractor!.id,worker_name:name.trim(),job_description:job.trim(),pay_scheme:scheme,joined_at:joined,is_active:active,left_at:active?null:left,notes:notes.trim()||null,reason:reason.trim(),...(create?{worker_code:code.trim()||null,initial_daily_rate:exactRate,rate_effective_from:effective}:{worker_id:worker!.id,...(reactivating?{reactivated_at:restart}:{})})}
  submit(document)
 }
 return <section className="panel catt-editor" aria-label="Form pekerja dan tarif"><header><div className="eyebrow">{source.contractor?.name}</div><h2>{create?'Tambah pekerja':rateOnly?'Tarif harian baru':'Ubah data pekerja'}</h2>{worker?<p>{worker.name}</p>:null}</header><form onSubmit={e=>{e.preventDefault();save()}}><fieldset disabled={disabled}>
  {!rateOnly?<div className="catt-fields">
   <label>Nama pekerja<input aria-label="Nama pekerja" value={name} maxLength={200} onChange={e=>setName(e.target.value)}/></label>
   <label>Pekerjaan<input aria-label="Pekerjaan pekerja" value={job} maxLength={200} onChange={e=>setJob(e.target.value)}/></label>
   {create?<label>Kode pekerja · opsional<input aria-label="Kode pekerja" value={code} maxLength={80} onChange={e=>setCode(e.target.value)}/></label>:null}
   <label>Skema upah<select aria-label="Skema upah pekerja" value={scheme} onChange={e=>setScheme(e.target.value)}><option value="DAILY">Harian</option><option value="PIECE">Borongan</option><option value="HYBRID">Harian & borongan</option><option value="NONE">Tanpa upah</option></select></label>
   <label>Tanggal pertama bekerja<input aria-label="Tanggal mulai pekerja" type="date" value={joined} disabled={!create} onChange={e=>{setJoined(e.target.value);setEffective(e.target.value)}}/></label>
   <label>Status sekarang<select aria-label="Status pekerja" value={active?'ACTIVE':'INACTIVE'} onChange={e=>setActive(e.target.value==='ACTIVE')}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Berhenti</option></select></label>
   {!active?<label>Tanggal terakhir bekerja<input aria-label="Tanggal berhenti pekerja" type="date" min={joined} max={today} value={left} onChange={e=>setLeft(e.target.value)}/></label>:null}
   {reactivating?<label>Tanggal bekerja kembali<input aria-label="Tanggal kembali pekerja" type="date" max={today} value={restart} onChange={e=>setRestart(e.target.value)}/></label>:null}
  </div>:null}
  {create||rateOnly?<div className="catt-fields"><label>{create?'Tarif harian awal · Rp':'Tarif harian baru · Rp'}<input aria-label="Tarif harian pekerja" inputMode="decimal" value={rate} placeholder="Contoh: 75000" onChange={e=>setRate(e.target.value)}/></label><label>Berlaku mulai tanggal<input aria-label="Tarif berlaku mulai" type="date" max={create?joined:undefined} value={effective} onChange={e=>setEffective(e.target.value)}/></label></div>:null}
  {rate&&thousandsLike?<p role="alert">Tarif {rate.trim()} akan terbaca sebagai desimal, bukan ribuan. Tulis tanpa titik atau koma, misalnya {rate.trim().replace(/[.,]/,'')}.</p>:rate&&!validRate?<p role="alert">Isi tarif dengan angka tanpa pemisah ribuan. Desimal boleh memakai koma atau titik, paling banyak enam angka.</p>:null}
  {!rateOnly?<label>Catatan · opsional<textarea aria-label="Catatan pekerja" value={notes} maxLength={2000} onChange={e=>setNotes(e.target.value)}/></label>:null}
  <label>Alasan perubahan<textarea aria-label="Alasan perubahan pekerja" value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)}/></label>
  <div className="catt-review">{create||rateOnly?<p>{validRate?<><strong>Rp{formatReceiptDecimal(exactRate)} / hari</strong> · mulai {effective||'pilih tanggal'}</>:'Isi tarif awal secara sengaja, termasuk jika nilainya nol.'}</p>:<p>{active?reactivating?`Bekerja kembali mulai ${restart}.`:'Data pekerja aktif akan diperbarui.':`Berhenti setelah ${left}.`}</p>}<p>Riwayat tarif dan masa kerja sebelumnya tetap tercatat.</p></div>
  <div className="catt-tools"><button className="primary-btn" disabled={!valid}>{rateOnly?'Simpan tarif':'Simpan pekerja'}</button><button type="button" onClick={cancel}>Batal mengubah</button></div>
 </fieldset></form></section>
}
