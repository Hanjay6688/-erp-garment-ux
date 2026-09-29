import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {parsePayrollRead,parsePayrollOutcome,type PayrollAction,type PayrollCash,type PayrollHeader,type PayrollLine,type PayrollRead,type PayrollSection} from './payrollContract'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type {Json} from './types/database.preconnect'
import type {NotaDocument} from './notaContract'
import './procurement-connected.css'
import './payroll-connected.css'
const sections=[['WORK','Upah pekerjaan'],['ATTENDANCE','Absensi'],['REIMBURSEMENTS','Tambahan & reimbursement'],['DEDUCTIONS','Potongan & kasbon'],['NOTES','Nota asal']] as const
const statuses:Record<string,string>={DRAFT:'Draft',CALCULATED:'Sudah dihitung',REVIEW:'Dalam pemeriksaan',APPROVED:'Disetujui',PAID:'Lunas',REVERSED:'Dibatalkan'}
const money=(v:string)=>`Rp${numberText(v)}`
export default function ConnectedPayrollPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.payroll.view'))return <section className="panel" role="alert">Hak melihat payroll diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi payroll belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),[data,setData]=useState<PayrollRead|null>(null),[detail,setDetail]=useState<PayrollRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[q,setQ]=useState(''),[status,setStatus]=useState('')
 const mutation=useProductionMutation('PAYROLL'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [action,setAction]=useState<PayrollAction|null>(null)
 const seq=useRef(0),requested=useRef({q:'',status:'',offset:0,id:null as string|null,section:'WORK' as PayrollSection,detailOffset:0})
 const approve=identity.permissions.includes('finance.payroll.approve'),pay=identity.permissions.includes('finance.payroll.pay')
 const load=useCallback(async()=>{
  const f={...requested.current},s=++seq.current,ticket=beginRead();setAction(null);setBusy(true);setData(null);setDetail(null);setError('')
  try{
   const results=await Promise.allSettled([client.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:'PAYROLLS',p_query:{q:f.q,status:f.status||null,limit:25,offset:f.offset}}),...(f.id?[client.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:f.section,p_query:{id:f.id,limit:25,offset:f.detailOffset}})]:[])])
   if(s!==seq.current||!isReadCurrent(ticket))return false
   const rows=results.map(r=>{if(r.status==='rejected')throw r.reason;if(r.value.error)throw r.value.error;return r.value.data}),list=parsePayrollRead(rows[0],'PAYROLLS'),d=f.id?parsePayrollRead(rows[1],f.section):null
   if(list.page.offset!==f.offset||list.page.limit!==25||list.capabilities.approve!==approve||list.capabilities.pay!==pay||d&&(d.document?.id!==f.id||d.page.offset!==f.detailOffset||d.page.limit!==25||d.capabilities.approve!==approve||d.capabilities.pay!==pay))throw Error('Pilihan payroll atau hak akses berubah. Muat ulang payroll.')
   const inList=(list.page.rows as PayrollHeader[]).find(p=>p.id===f.id)
   if(d&&inList&&inList.review_token!==d.document?.review_token)throw Error('Payroll berubah saat dibaca. Muat ulang untuk memeriksa rincian terbaru.')
   setData(list);setDetail(d);return finishRead(ticket)
  }catch(e){if(s===seq.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}finally{if(s===seq.current)setBusy(false)}
 },[client,approve,pay,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const h=detail?.document,locked=busy||mutation.writerLocked
 const handlers:ProductionMutationHandlers={
  send:e=>{const p=e.payload as {document:Json;expected_version:string};return client.rpc('erp_cp7_save_payroll_v1',{p_action:e.action,p_payload:p.document,p_request:e.id,p_expected:p.expected_version})},
  validate:(v,e)=>{parsePayrollOutcome(v,e.id,e.action,e.payload)},
  retire:(v,e)=>{const r=parsePayrollOutcome(v,e.id,e.action,e.payload);requested.current.id=r.payroll_id;requested.current.detailOffset=0;setAction(null);setData(null);setDetail(null)},reload:load,
 }
 const write=(chosen:PayrollAction,document:Json)=>{if(!h||locked)return;const version=h.row_version;setAction(null);setData(null);setDetail(null);void run(chosen,{document,expected_version:version},null,handlers)}
 const cashRead=useCallback(async(q:string,offset:number)=>{const r=await client.rpc('erp_cp7_get_payroll_workspace_v1',{p_section:'CASH_ACCOUNTS',p_query:{q,offset,limit:25}});if(r.error)throw r.error;const w=parsePayrollRead(r.data,'CASH_ACCOUNTS');if(w.page.offset!==offset||w.page.limit!==25||w.capabilities.approve!==approve||w.capabilities.pay!==pay)throw Error('Pilihan akun atau hak pembayaran berubah. Muat ulang payroll.');return w},[client,approve,pay])
 return <section className="cproc cpay"><header className="panel cproc-heading"><div><div className="eyebrow">KEUANGAN · MANDOR</div><h1>Payroll & Kasbon</h1><p>Periksa upah, absensi, tambahan, dan potongan mandor beserta nota asalnya.</p></div><button disabled={busy||mutation.busy} onClick={()=>void load()}>Muat ulang payroll</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel" noticeText="Payroll tersimpan. Data terbaru sudah dimuat." messageText={mutation.pending&&!mutation.corruptedEnvelope?'Status transaksi payroll belum pasti. Periksa status transaksi untuk melanjutkan.':mutation.error.includes('CP7_PAYROLL_PREPARE_REQUIRED')?'Dokumen sumber atau jumlah berubah. Hitung sumber, periksa rincian terbaru, lalu setujui kembali.':mutation.error.includes('CP7_PAYROLL_REVIEW_CHANGED')?'Payroll berubah. Periksa kembali rincian yang baru dimuat.':undefined} reconcileLabel="Periksa status payroll"/>
  {error?<p className="panel" role="alert">{error}</p>:null}
  <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();requested.current={...requested.current,q:q.trim(),status,offset:0,id:null,detailOffset:0};void load()}}><label>Cari mandor atau payroll<input aria-label="Cari payroll" maxLength={120} value={q} onChange={e=>setQ(e.target.value)}/></label><label>Status payroll<select aria-label="Status payroll" value={status} onChange={e=>setStatus(e.target.value)}><option value="">Semua status</option>{Object.entries(statuses).map(([key,label])=><option value={key} key={key}>{label}</option>)}</select></label><button disabled={busy||mutation.busy}>Cari payroll</button></form>
  {busy?<p role="status">Memuat payroll…</p>:null}
  <div className="cpay-layout"><section className="panel"><h2>Daftar payroll</h2>{data?.page.rows.map(v=>{const p=v as PayrollHeader;return <button className="cproc-receipt" key={p.id} aria-pressed={h?.id===p.id} disabled={busy||mutation.busy} onClick={()=>{requested.current.id=p.id;requested.current.detailOffset=0;void load()}}><span><strong>{p.contractor_name}</strong><small>{p.period_start} sampai {p.period_end}</small><small>{p.payroll_number}</small></span><span>{statuses[p.status]}<strong className="cpay-amount">{money(p.net_payable)}</strong></span></button>})}{data&&!data.page.rows.length?<p>Tidak ada payroll yang cocok.</p>:null}{data?<Pager label="Payroll" page={data.page} busy={busy||mutation.busy} change={offset=>{requested.current.offset=offset;void load()}}/>:null}</section>
   <section className="panel cpay-detail" aria-label="Rincian payroll"><h2>{h?.contractor_name??'Pilih payroll'}</h2>{h&&detail?<><p className="cpay-reference">{h.payroll_number}</p><p>{h.period_start} sampai {h.period_end} · <strong>{statuses[h.status]}</strong></p>
    {!h.totals_match_items?<p role="alert">Total belum sesuai rincian. Payroll perlu dihitung ulang sebelum disetujui.</p>:null}
    {h.status==='REVERSED'?<p>Payroll dibatalkan. Rincian berikut adalah riwayat payroll tersebut.</p>:null}
    <dl className="cpay-totals">{([['labor_total','Upah pekerjaan'],['attendance_total','Absensi'],['reimburse_total','Tambahan'],['deduction_total','Potongan'],['manual_adjustment','Penyesuaian']] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{money(h[key])}</dd></div>)}<div className="cpay-net"><dt>{h.status==='PAID'?'Jumlah dilunasi':h.status==='REVERSED'?'Jumlah pada dokumen batal':'Bersih payroll'}</dt><dd>{money(h.net_payable)}</dd></div></dl>
    {h.status==='PAID'?<p>Pembayaran {h.payment_date} · {h.payment_cash_account_name??'Tanpa pengeluaran tunai'}{h.settled_at?` · Dicatat ${formatCp6WibDateTime(h.settled_at)}`:''}</p>:null}
    {h.notes?<p className="cpay-reference">{h.notes}</p>:null}
    <div className="cpay-actions">
     {approve&&['DRAFT','CALCULATED','REVIEW'].includes(h.status)?<><button disabled={locked} onClick={()=>write('PREPARE',{id:h.id,review_token:h.review_token,change_reason:'Perbarui perhitungan dari dokumen sumber'})}>Hitung sumber</button><button className="primary-btn" disabled={locked||!h.totals_match_items||h.status==='DRAFT'} onClick={()=>setAction('APPROVE')}>Setujui payroll</button></>:null}
     {pay&&h.status==='APPROVED'?<button className="primary-btn" disabled={locked||!h.totals_match_items} onClick={()=>setAction('PAY')}>Lunasi payroll</button>:null}
     {approve&&['DRAFT','CALCULATED','REVIEW','APPROVED'].includes(h.status)?<button disabled={locked} onClick={()=>setAction('CANCEL')}>Batalkan payroll</button>:null}
     {approve&&pay&&h.status==='PAID'?<button disabled={locked} onClick={()=>setAction('REVERSE')}>Koreksi payroll lunas</button>:null}
    </div>
    {action?<ActionForm key={`${h.id}:${h.review_token}:${action}`} action={action} payroll={h} disabled={locked} cashRead={cashRead} cancel={()=>setAction(null)} submit={document=>write(action,document)}/>:null}

    <div className="cpay-tabs" role="group" aria-label="Jenis rincian payroll">{sections.map(([key,label])=><button key={key} aria-pressed={detail.section===key} disabled={busy||mutation.busy} onClick={()=>{requested.current.section=key;requested.current.detailOffset=0;void load()}}>{label} <small>{h.counts[key.toLowerCase() as keyof PayrollHeader['counts']]}</small></button>)}</div>
    <div className="cpay-lines">{detail.page.rows.map(v=>detail.section==='NOTES'?<Note key={v.id} value={v as NotaDocument}/>:<Line key={v.id} section={detail.section} value={v as PayrollLine}/>)}{!detail.page.rows.length?<p>Belum ada rincian dalam bagian ini.</p>:null}</div><Pager label="Rincian" page={detail.page} busy={busy||mutation.busy} change={offset=>{requested.current.detailOffset=offset;void load()}}/>
   </>:<p>Pilih mandor dan periode untuk menelusuri perhitungan serta nota sumber.</p>}</section></div>
 </section>
}
function Pager({label,page,busy,change}:{label:string;page:{total:string;offset:number;next_offset:number|null};busy:boolean;change:(n:number)=>void}){return <div className="cproc-pagination"><span>Total {page.total}</span><button disabled={busy||!page.offset} onClick={()=>change(Math.max(0,page.offset-25))}>{label} sebelumnya</button><button disabled={busy||page.next_offset===null} onClick={()=>change(page.next_offset??0)}>{label} berikutnya</button></div>}
function Line({section,value:l}:{section:PayrollSection;value:PayrollLine}){
 return <article className="cpay-line"><header><strong>{section==='WORK'?l.component_name:section==='ATTENDANCE'?l.worker_name??'Pekerja · nama historis belum tercatat':section==='DEDUCTIONS'?l.type?.replaceAll('_',' '):l.description??l.source_type}</strong><strong>{money(l.amount!)}</strong></header>
  {section==='WORK'?<p>{l.source_type==='PRODUCTION'?'Reguler':'Bikin Bagus'} · {numberText(l.qty!)} PCS × {money(l.rate!)}{l.po_number?` · ${l.po_number}`:''}</p>:null}
  {section==='ATTENDANCE'?<p>{l.date??'Tanggal historis belum tercatat'} · {numberText(l.paid_fraction!)} hari × {money(l.daily_rate!)}{l.job_description?` · ${l.job_description}`:''}</p>:null}
  {l.notes?<p>{l.notes}</p>:null}<details><summary>Referensi sumber</summary>{Object.entries(l).filter(([k,v])=>k.endsWith('_id')&&v).map(([k,v])=><p className="cpay-reference" key={k}>{k.replaceAll('_',' ')} · {v}</p>)}</details></article>
}
function Note({value:n}:{value:NotaDocument}){return <article className="cpay-line"><header><strong>Nota {n.note_date}</strong><strong>{money(n.amount!)}</strong></header><p className="cpay-reference">{n.note_number}</p>{n.cards.map(c=><div key={c.card_key}><p>{c.source_type==='PRODUCTION'?'Reguler':'Bikin Bagus'} · {c.po_number??c.origin_number}</p>{c.lines.map(l=><p key={`${l.source_id}:${l.component_id}`}>{l.component_name} · {numberText(l.remaining_qty)} PCS × {money(l.rate!)} = {money(l.amount!)}</p>)}</div>)}</article>}

const actionLabels={PREPARE:'Hitung sumber',APPROVE:'Setujui payroll',PAY:'Lunasi payroll',CANCEL:'Batalkan payroll',REVERSE:'Batalkan payroll dan pembayaran'}
function ActionForm({action,payroll:h,disabled,cashRead,cancel,submit}:{action:PayrollAction;payroll:PayrollHeader;disabled:boolean;cashRead:(q:string,offset:number)=>Promise<PayrollRead>;cancel:()=>void;submit:(document:Json)=>void}){
 const [reason,setReason]=useState(''),[review,setReview]=useState(false),[date,setDate]=useState(cp6WibDateTimeInput().slice(0,10)),[cash,setCash]=useState<PayrollCash|null>(null)
 const positive=!/^0(?:\.0+)?$/.test(h.net_payable),payment=action==='PAY'
 return <section className="cpay-action" aria-label="Periksa tindakan payroll"><h3>{actionLabels[action]}</h3><p><strong>{h.contractor_name} · {money(h.net_payable)}</strong></p>
  <p>{action==='APPROVE'?'Persetujuan mencatat biaya absensi dan tambahan yang belum diakui. Periksa seluruh rincian sumber sebelum melanjutkan.':payment?positive?'Pembayaran melunasi seluruh jumlah bersih payroll ini dari akun yang dipilih.':'Seluruh upah telah diperhitungkan dalam potongan. Pelunasan ini tidak mengeluarkan uang tunai.':action==='REVERSE'?'Pembayaran dan persetujuan biaya dibalik. Payroll menjadi dibatalkan; nota asal tetap tersimpan dan hak kerja yang dilepas dapat disusun kembali.':'Payroll menjadi dibatalkan. Persetujuan biaya yang sudah tercatat dibalik; nota asal tetap tersimpan dan hak kerja yang dilepas dapat disusun kembali.'}</p>
  <fieldset disabled={disabled}>
   {payment?<label>Tanggal pembayaran · WIB<input aria-label="Tanggal pembayaran payroll" type="date" max={cp6WibDateTimeInput().slice(0,10)} value={date} onChange={e=>{setDate(e.target.value);setReview(false)}}/></label>:null}
   {payment&&positive?<CashPicker read={cashRead} selected={cash} choose={v=>{setCash(v);setReview(false)}}/>:null}
   <label>Alasan tindakan<textarea aria-label="Alasan tindakan payroll" maxLength={1000} value={reason} onChange={e=>{setReason(e.target.value);setReview(false)}}/></label>
   <label className="cpay-check"><input type="checkbox" aria-label="Rincian payroll sudah diperiksa" checked={review} onChange={e=>setReview(e.target.checked)}/>Saya sudah memeriksa rincian, jumlah, dan tindakan ini.</label>
   <div className="cpay-actions"><button className="primary-btn" disabled={!review||reason.trim().length<5||payment&&(!date||date>cp6WibDateTimeInput().slice(0,10)||positive&&!cash)} onClick={()=>submit({id:h.id,review_token:h.review_token,change_reason:reason.trim(),...(payment?{payment_date:date,cash_account_id:positive?cash?.id??null:null}:{})})}>{actionLabels[action]} sekarang</button><button onClick={cancel}>Kembali ke rincian</button></div>
  </fieldset>
 </section>
}
function CashPicker({read,selected,choose}:{read:(q:string,offset:number)=>Promise<PayrollRead>;selected:PayrollCash|null;choose:(v:PayrollCash|null)=>void}){
 const [q,setQ]=useState(''),[rows,setRows]=useState<PayrollRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),seq=useRef(0),query=useRef('')
 useEffect(()=>()=>{++seq.current},[])
 const load=async(offset:number)=>{const s=++seq.current;setBusy(true);setError('');setRows(null);choose(null);try{const r=await read(query.current,offset);if(s===seq.current)setRows(r)}catch(e){if(s===seq.current)setError(normalizeClientError(e).message)}finally{if(s===seq.current)setBusy(false)}}
 return <div className="cpay-cash"><label>Cari akun kas atau bank<input aria-label="Cari akun pembayaran payroll" value={q} maxLength={120} onChange={e=>setQ(e.target.value)}/></label><button disabled={busy} onClick={()=>{query.current=q.trim();void load(0)}}>Cari akun pembayaran</button>{error?<p role="alert">{error}</p>:null}{rows?.page.rows.map(v=>{const c=v as PayrollCash;return <button className="cpay-cash-row" aria-pressed={selected?.id===c.id} key={c.id} onClick={()=>choose(c)}>{c.code} · {c.name}{selected?.id===c.id?' · Dipilih':''}</button>})}{rows?<Pager label="Akun" page={rows.page} busy={busy} change={offset=>void load(offset)}/>:null}{selected?<p>Akun pembayaran: <strong>{selected.name}</strong></p>:<p>Pilih akun aktif untuk pembayaran.</p>}</div>
}
