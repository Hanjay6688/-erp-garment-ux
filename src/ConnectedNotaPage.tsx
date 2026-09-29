import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {notaObject,parseNotaWorkspace,parseNotaOutcome,type NotaCard,type NotaDocument,type NotaPayroll,type NotaWorkspace} from './notaContract'
import type {Json} from './types/database.preconnect'
import './procurement-connected.css'
import './nota-connected.css'
type Form={id:string|null;version:string|null;contractor:string;contractorName:string;date:string;start:string;end:string;target:string|null;notes:string;cards:NotaCard[]}
const statusLabel={DRAFT:'Draft',POSTED:'Masuk payroll',VOID:'Draft dibatalkan'}
const kindLabel=(c:NotaCard)=>c.source_type==='PRODUCTION'?'Reguler':c.source_type==='REWORK'?'Bikin Bagus · rework':'Bikin Bagus · temuan BS'
const errorText=(e:unknown)=>{const text=normalizeClientError(e).message;return text.includes('CP7_NOTA_SOURCE_CHANGED')?'Hak kerja sumber berubah. Muat ulang dan pilih kembali kartu sebelum menyimpan.':text.includes('CP7_NOTA_PAYROLL_TARGET_CHANGED')?'Payroll tujuan sudah berubah. Muat ulang dan periksa kembali draft.':text.includes('CP7_NOTA_CARD_IN_OTHER_DRAFT')?'Kartu sudah berada di draft nota lain. Buka draft tersebut atau pilih sumber lain.':text.includes('Payroll period overlaps')?'Periode ini sudah mempunyai payroll aktif. Pilih payroll yang ada untuk menggabungkan nota.':text}
export default function ConnectedNotaPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('production.fg_handoff.view'))return <section className="panel" role="alert">Hak melihat Nota FG diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi nota belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.payroll.view')
 const mutation=useProductionMutation('FG_NOTA'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [sources,setSources]=useState<NotaWorkspace<NotaCard>|null>(null),[docs,setDocs]=useState<NotaWorkspace<NotaDocument>|null>(null),[detail,setDetail]=useState<NotaDocument|null>(null)
 const [form,setForm]=useState<Form|null>(null),[dirty,setDirty]=useState(false),[review,setReview]=useState(false),[reason,setReason]=useState('Komponen dan tujuan payroll sudah diperiksa')
 const [search,setSearch]=useState(''),[docSearch,setDocSearch]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState(''),[drop,setDrop]=useState(false)
 const request=useRef({q:'',offset:0,docQ:'',docOffset:0,selected:null as string|null,refreshEdit:false}),sequence=useRef(0),drag=useRef<NotaCard|null>(null)
 const fromNote=(n:NotaDocument):Form=>({id:n.id,version:n.row_version,contractor:n.contractor_id,contractorName:n.contractor_name,date:n.note_date,start:n.period_start,end:n.period_end,target:n.target_payroll_id,notes:n.notes,cards:n.cards})
 const load=useCallback(async()=>{
  const q={...request.current},s=++sequence.current,ticket=beginRead();setLoading(true);setSources(null);setDocs(null);setDetail(null);setReview(false);setError('');drag.current=null
  try{
   const results=await Promise.allSettled([
    client.rpc('erp_cp7_get_nota_workspace_v1',{p_section:'SOURCES',p_query:{q:q.q,offset:q.offset,limit:25}}),
    client.rpc('erp_cp7_get_nota_workspace_v1',{p_section:'NOTES',p_query:{q:q.docQ,offset:q.docOffset,limit:25}}),
    ...(q.selected?[client.rpc('erp_cp7_get_nota_workspace_v1',{p_section:'NOTES',p_query:{id:q.selected}})]:[]),
   ])
   if(s!==sequence.current||!isReadCurrent(ticket))return false
   const responses=results.map(r=>{if(r.status!=='fulfilled')throw r.reason;if(r.value.error)throw r.value.error;return r.value.data})
   const st=parseNotaWorkspace(responses[0],'SOURCES'),ds=parseNotaWorkspace(responses[1],'NOTES'),dt=q.selected?parseNotaWorkspace(responses[2],'NOTES'):null
   if(st.financial_captured!==finance||ds.financial_captured!==finance||st.can_post!==ds.can_post||st.page.offset!==q.offset||ds.page.offset!==q.docOffset||dt&&(dt.financial_captured!==finance||dt.can_post!==st.can_post||dt.page.rows.length!==1||dt.page.rows[0].id!==q.selected))throw Error('Akses, dokumen, atau halaman berubah. Muat ulang nota.')
   const selected=dt?.page.rows[0]??null;setSources(st);setDocs(ds);setDetail(selected)
   if(q.refreshEdit){setForm(selected?.status==='DRAFT'?fromNote(selected):null);setDirty(false);request.current.refreshEdit=false}
   return finishRead(ticket)
  }catch(e){if(s===sequence.current&&isReadCurrent(ticket)){setError(errorText(e));setForm(null);setDirty(false)}return false}
  finally{if(s===sequence.current)setLoading(false)}
 },[client,finance,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const handlers:ProductionMutationHandlers={
  send:e=>{const p=notaObject(e.payload);return client.rpc('erp_cp7_save_nota_v1',{p_action:e.action,p_payload:p.document as Json,p_request:e.id,p_expected:p.expected_version as string|null})},
  validate:(v,e)=>{parseNotaOutcome(v,e.id,e.action,e.payload)},
  retire:(v,e)=>{const r=parseNotaOutcome(v,e.id,e.action,e.payload);request.current.selected=r.note_id;request.current.refreshEdit=true;setForm(null);setSources(null);setDocs(null);setDetail(null);setDirty(false);setReview(false)},reload:load,
 }
 const locked=loading||mutation.writerLocked,canWrite=sources?.can_post===true&&docs?.can_post===true
 const stale=Boolean(form?.id&&(!detail||detail.id!==form.id||detail.row_version!==form.version||detail.status!=='DRAFT'))
 const write=(action:string,document:Json,version:string|null)=>run(action,{document,expected_version:version},null,handlers)
 const add=(c:NotaCard)=>{
  if(locked||!canWrite||c.claimed_by_note&&c.claimed_by_note!==form?.id||form?.cards.some(x=>x.card_key===c.card_key))return
  if(form&&form.contractor!==c.contractor_id){setError('Satu nota untuk satu mandor. Simpan draft ini atau mulai nota baru untuk mandor tersebut.');return}
  const today=cp6WibDateTimeInput().slice(0,10)
  if(!form){request.current.selected=null;setDetail(null)}
  setForm(v=>v?{...v,cards:[...v.cards,c]}:{id:null,version:null,contractor:c.contractor_id,contractorName:c.contractor_name,date:today,start:today,end:today,target:null,notes:'',cards:[c]});setDirty(true);setReview(false);setError('')
 }
 const edit=(change:Partial<Form>)=>{setForm(v=>v?{...v,...change}:null);setDirty(true);setReview(false)}
 const open=(n:NotaDocument)=>{request.current.selected=n.id;request.current.refreshEdit=true;setForm(null);void load()}
 const reset=()=>{request.current.selected=null;setForm(null);setDetail(null);setDirty(false);setReview(false);setError('')}
 const save=()=>{if(!form||locked||stale||!form.cards.length||!form.date||!form.start||!form.end||form.start>form.end)return;void write('SAVE',{id:form.id,contractor_id:form.contractor,note_date:form.date,period_start:form.start,period_end:form.end,target_payroll_id:form.target,notes:form.notes,cards:form.cards.map(c=>({card_key:c.card_key,source_token:c.source_token}))},form.version)}
 const payrollRead=useCallback(async(contractor:string,q:string,offset:number)=>{
  const r=await client.rpc('erp_cp7_get_nota_workspace_v1',{p_section:'PAYROLLS',p_query:{contractor_id:contractor,q,offset,limit:25}});if(r.error)throw r.error;const w=parseNotaWorkspace(r.data,'PAYROLLS');if(w.financial_captured!==finance||w.page.offset!==offset||w.page.rows.some(p=>p.contractor_id!==contractor))throw Error('Pilihan payroll berubah. Muat ulang.');return w
 },[client,finance])
 return <section className="cproc cnota"><header className="panel cproc-heading"><div><div className="eyebrow">PRODUKSI · NOTA MANDOR</div><h1>Susun Nota FG</h1><p>Gabungkan kartu Reguler dan Bikin Bagus untuk mandor yang sama. Setelah diperiksa, kirim nota ke payroll.</p></div><button disabled={loading||mutation.busy} onClick={()=>{request.current.refreshEdit=true;void load()}}>Muat ulang nota</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>{error?<p className="panel" role="alert">{error}</p>:null}
  <div className="cnota-columns"><section className="cnota-sources"><header><div><h2>Kartu pekerjaan</h2><p>Sisa komponen yang berhak dibayar. Pekerjaan sudah tersimpan; tidak perlu mengulang finishing.</p></div></header>
   <div className="panel cnota-search"><label>Cari mandor, PO, atau sumber<input aria-label="Cari kartu nota" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)}/></label><button disabled={loading||mutation.busy} onClick={()=>{request.current.q=search.trim();request.current.offset=0;void load()}}>Cari kartu</button></div>
   {loading?<p role="status">Memuat sumber nota…</p>:null}
   {sources?.page.rows.map(c=><article className="panel cnota-source" key={c.card_key} data-card-key={c.card_key} draggable={canWrite&&!locked&&!c.claimed_by_note}
    onDragStart={e=>{if(locked||!canWrite||c.claimed_by_note){e.preventDefault();return}drag.current=c;e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('text/plain',c.card_key)}} onDragEnd={()=>{drag.current=null;setDrop(false)}}>
    <SourceCard card={c}/><footer><span className="cnota-grip" aria-hidden="true">⠿</span>{c.claimed_by_note?<span>Kartu berada di draft tersimpan.</span>:null}<button disabled={locked||!canWrite||Boolean(c.claimed_by_note)||Boolean(form?.cards.some(x=>x.card_key===c.card_key))} onClick={()=>add(c)}>{form?.cards.some(x=>x.card_key===c.card_key)?'Sudah dipilih':'Tambahkan ke nota'}</button></footer>
   </article>)}
   {sources&&!sources.page.rows.length?<p className="panel">Tidak ada sisa pekerjaan yang cocok.</p>:null}
   {sources?<Pager label="kartu" page={sources.page} disabled={loading||mutation.busy} change={offset=>{request.current.offset=offset;void load()}}/>:null}
  </section><section className={`panel cnota-composer${drop?' cnota-drop':''}`} aria-label="Susunan nota" onDragOver={e=>{if(drag.current&&canWrite&&!locked){e.preventDefault();e.dataTransfer.dropEffect='copy';setDrop(true)}}} onDragLeave={()=>setDrop(false)} onDrop={e=>{e.preventDefault();const c=drag.current;drag.current=null;setDrop(false);if(c)add(c)}}>
   <header><div><div className="eyebrow">SUSUN NOTA</div><h2>{form?form.contractorName:detail?.contractor_name??'Pilih kartu pekerjaan'}</h2></div><button disabled={locked} onClick={reset}>Nota baru</button></header>
   {!form&&!detail?<p className="cnota-drop-hint">Tarik kartu ke sini, atau gunakan tombol Tambahkan ke nota.</p>:null}
   {form?<><p>{form.id?'Draft tersimpan':'Nota baru'} · {form.cards.length} kartu</p><fieldset disabled={locked||!canWrite||stale}><div className="cproc-grid"><label>Tanggal nota · WIB<input aria-label="Tanggal nota WIB" type="date" value={form.date} onChange={e=>edit({date:e.target.value})}/></label><label>Awal periode<input aria-label="Awal periode nota" type="date" value={form.start} disabled={Boolean(form.target)} onChange={e=>edit({start:e.target.value})}/></label><label>Akhir periode<input aria-label="Akhir periode nota" type="date" value={form.end} disabled={Boolean(form.target)} onChange={e=>edit({end:e.target.value})}/></label></div>
    <PayrollPicker key={form.contractor} contractor={form.contractor} target={form.target} read={payrollRead} disabled={locked||!canWrite||stale} choose={p=>edit(p?{target:p.id,start:p.period_start,end:p.period_end}:{target:null})}/>
    <label>Catatan nota<textarea aria-label="Catatan nota" value={form.notes} maxLength={2000} onChange={e=>edit({notes:e.target.value})}/></label>
    <div className="cnota-selected">{form.cards.map(c=><article key={c.card_key}><SourceCard card={c}/><button onClick={()=>edit({cards:form.cards.filter(x=>x.card_key!==c.card_key)})}>Lepaskan kartu</button></article>)}</div>
    <button className="primary-btn" disabled={!form.cards.length||!dirty||!form.date||!form.start||!form.end||form.start>form.end} onClick={save}>Simpan draft nota</button>
   </fieldset>{stale?<p role="alert">Draft berubah. Muat ulang nota untuk meninjau versi terbaru.</p>:null}</>:null}
   {detail?<section className="cnota-review"><h3>{statusLabel[detail.status]}</h3><p className="cnota-reference">{detail.note_number}</p>{detail.amount!==undefined?<strong className="cnota-total">Rp{numberText(detail.amount)}</strong>:null}
    {detail.status!=='DRAFT'?detail.cards.map(c=><article key={c.card_key}><SourceCard card={c}/></article>):null}
    {detail.payroll_status==='REVERSED'?<p>Payroll dibatalkan. Riwayat nota tetap tersimpan; hak kerja yang dilepas dapat disusun kembali.</p>:detail.status==='POSTED'?<p>Sudah masuk payroll {detail.payroll_number}. Persetujuan dan pembayaran mengikuti status payroll.</p>:null}
    {detail.status==='DRAFT'?<><p>Posting memasukkan komponen di nota ini ke payroll. Pembayaran dilakukan terpisah.</p><label>Alasan tindakan<textarea aria-label="Alasan tindakan nota" maxLength={1000} value={reason} disabled={locked} onChange={e=>{setReason(e.target.value);setReview(false)}}/></label><label className="cnota-check"><input type="checkbox" aria-label="Nota sudah diperiksa" checked={review} disabled={locked||dirty||stale} onChange={e=>setReview(e.target.checked)}/>Saya sudah memeriksa kartu, mandor, dan periode payroll.</label>
     <div className="cnota-actions"><button className="primary-btn" disabled={locked||!canWrite||dirty||stale||!review||reason.trim().length<5} onClick={()=>void write('POST',{id:detail.id,change_reason:reason.trim()},detail.row_version)}>Posting ke payroll</button><button disabled={locked||!canWrite||dirty||stale||!review||reason.trim().length<5} onClick={()=>void write('VOID',{id:detail.id,change_reason:reason.trim()},detail.row_version)}>Batalkan draft</button></div>{dirty?<small>Simpan perubahan draft sebelum melanjutkan.</small>:null}</>:null}
   </section>:null}
  </section></div>
  <section className="panel cnota-history"><h2>Nota tersimpan</h2><div className="cnota-search"><label>Cari nota atau mandor<input aria-label="Cari nota tersimpan" value={docSearch} maxLength={120} onChange={e=>setDocSearch(e.target.value)}/></label><button disabled={loading||mutation.busy} onClick={()=>{request.current.docQ=docSearch.trim();request.current.docOffset=0;void load()}}>Cari nota</button></div>{docs?.page.rows.map(n=><button key={n.id} className="cnota-note-row" disabled={loading||mutation.busy} onClick={()=>open(n)}><span><strong>{n.contractor_name}</strong><small>{n.note_date} · {n.note_number}</small></span><span>{statusLabel[n.status]}{n.amount!==undefined?<strong>Rp{numberText(n.amount)}</strong>:null}</span></button>)}{docs&&!docs.page.rows.length?<p>Belum ada nota yang cocok.</p>:null}{docs?<Pager label="nota" page={docs.page} disabled={loading||mutation.busy} change={offset=>{request.current.docOffset=offset;void load()}}/>:null}</section>
 </section>
}
function SourceCard({card:c}:{card:NotaCard}){
 return <><div className={`cnota-kind ${c.source_type==='PRODUCTION'?'cnota-regular':'cnota-repair'}`}>{kindLabel(c)}</div><h3>{c.contractor_name}</h3><p className="cnota-reference">{c.po_number?`${c.po_number} · `:''}{c.group_number??c.origin_number}</p><small>{formatCp6WibDateTime(c.eligible_at)}</small><div className="cnota-components">{c.lines.map(l=><div key={`${l.source_id}:${l.component_id}`}><span><strong>{l.component_name}</strong><small>{numberText(l.remaining_qty)} PCS tersisa · {numberText(l.allocated_qty)} PCS sudah dialokasikan</small>{l.eligibility_reason==='COMPONENT_PAYABLE_LAUNDRY_OUTSTANDING'?<small>Laundry masih berjalan; hak komponen sudah tercatat.</small>:null}</span>{l.rate!==undefined&&l.amount!==undefined?<span>Rp{numberText(l.rate)} / PCS<strong>Rp{numberText(l.amount)}</strong></span>:null}</div>)}</div>{c.remaining_amount!==undefined?<p className="cnota-card-total">Jumlah kartu <strong>Rp{numberText(c.remaining_amount)}</strong></p>:null}</>
}
function Pager({label,page,disabled,change}:{label:string;page:{total:string;offset:number;next_offset:number|null};disabled:boolean;change:(n:number)=>void}){
 return <div className="cproc-pagination"><span>Total {page.total} {label}</span><button disabled={disabled||!page.offset} onClick={()=>change(Math.max(0,page.offset-25))}>{label} sebelumnya</button><button disabled={disabled||page.next_offset===null} onClick={()=>change(page.next_offset??0)}>{label} berikutnya</button></div>
}
function PayrollPicker({contractor,target,read,choose,disabled}:{contractor:string;target:string|null;read:(contractor:string,q:string,offset:number)=>Promise<NotaWorkspace<NotaPayroll>>;choose:(p:NotaPayroll|null)=>void;disabled:boolean}){
 const [q,setQ]=useState(''),[data,setData]=useState<NotaWorkspace<NotaPayroll>|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),seq=useRef(0),requested=useRef('')
 useEffect(()=>()=>{++seq.current},[])
 const load=async(offset:number)=>{const n=++seq.current;setBusy(true);setData(null);setError('');try{const w=await read(contractor,requested.current,offset);if(n===seq.current)setData(w)}catch(e){if(n===seq.current)setError(errorText(e))}finally{if(n===seq.current)setBusy(false)}}
 return <details className="cnota-payroll"><summary>{target?'Gabung payroll yang dipilih':'Buat payroll untuk periode nota ini'}</summary><p>Jika mandor sudah mempunyai payroll aktif pada periode ini, pilih payroll tersebut untuk menggabungkan nota.</p><label>Cari payroll mandor<input aria-label="Cari payroll mandor" value={q} disabled={disabled||busy} onChange={e=>setQ(e.target.value)}/></label><div className="cnota-actions"><button disabled={disabled||busy} onClick={()=>{requested.current=q.trim();void load(0)}}>Cari payroll aktif</button><button disabled={disabled} onClick={()=>choose(null)}>Buat payroll baru</button></div>{error?<p role="alert">{error}</p>:null}{data?.page.rows.map(p=><button className="cnota-payroll-option" key={p.id} disabled={disabled||busy} onClick={()=>choose(p)}>{p.period_start} sampai {p.period_end} · {p.payroll_number}{p.id===target?' · Dipilih':''}</button>)}{data?<Pager label="payroll" page={data.page} disabled={disabled||busy} change={offset=>void load(offset)}/>:null}</details>
}
