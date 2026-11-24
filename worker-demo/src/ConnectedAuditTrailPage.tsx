import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {hasPermission,PAGE_PERMISSION_BY_ID,SENSITIVE_ACTION_PERMISSION} from './auth/accessCatalog'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {auditCsv,parseAuditTrail,type AuditActor,type AuditQuery,type AuditRequest,type AuditRow,type AuditTrail} from './auditTrailContract'
import './procurement-connected.css'

// R3-03 (owner D16-1): Audit Trail, connected. It reads the Native audit log through erp_cp7_get_audit_trail_v1 and
// writes nothing. The first page fixes the listing (snapshot.as_of); the next and previous pages keep it, so a change saved
// while paging never moves a row between pages. A row with a lower id that commits after the first page (ASTRA-R3-02) changes
// the listing's mark (snapshot.listed): the answer says so (snapshot.changed) and paging stops until Muat ulang.
// Download CSV is offered only with settings.audit.export.
const PAGE=25
type Filters={from:string;to:string;entity_type:string;action:string;actor_id:string;q:string}
type Listing={query:AuditQuery;asOf:string|null;listed:string|null;cursors:(string|null)[];id:string|null}
const blank:Filters={from:'',to:'',entity_type:'',action:'',actor_id:'',q:''}
const toQuery=(f:Filters):AuditQuery=>({from:f.from||null,to:f.to||null,entity_type:f.entity_type||null,action:f.action||null,actor_id:f.actor_id||null,q:f.q.trim()||null})
const numbers=new Intl.NumberFormat('id-ID')
const amount=(n:bigint|number)=>numbers.format(n)
const entityNames:Record<string,string>={customers:'Pelanggan',suppliers:'Supplier',laundry_vendors:'Vendor laundry',contractors:'Mandor',locations:'Gudang & lokasi',
 materials:'Bahan',fabric_master_profiles:'Profil kain',accessory_categories:'Kategori aksesori',products:'Produk & SKU',production_orders:'PO produksi',
 cutting_pickups:'Bagi potongan',cutting_distribution_batches:'Distribusi potongan',cutting_distribution_allocations:'Pembagian potongan',
 sewing_terminal_events:'Setoran jahit',payroll_settlements:'Payroll',attendance_periods:'Periode absensi',attendance_hpp_pools:'Pool HPP absensi',
 contractor_hpp_policy_versions:'Kebijakan HPP mandor',worker_daily_rate_versions:'Rate harian pekerja',worker_employment_periods:'Masa kerja pekerja',
 misc_finance_transactions:'Transaksi lain',manual_reminders:'Reminder',sales_headers:'Penjualan',stock_policy_versions:'Kebijakan stok',bs_case_hold_events:'Barang BS'}
const actionNames:Record<string,string>={INSERT:'Dibuat',UPDATE:'Diubah',DELETE:'Dihapus',POST:'Diposting',REVERSE:'Dibatalkan',CREATE_DRAFT:'Draf dibuat',
 ACTIVATE:'Diaktifkan',CANCEL_ACTIVE:'Dibatalkan',CANCEL_UNPAID:'Dibatalkan sebelum dibayar',REVERSE_PAID:'Pembayaran dibalik'}
export const auditEntityLabel=(t:string|null)=>t===null?'Jenis data tidak tercatat':entityNames[t]??t.replace(/_/g,' ')
export const auditActionLabel=(a:string|null)=>a===null?'Aksi tidak tercatat':actionNames[a]??a.replace(/_/g,' ').toLowerCase()
export function auditTime(at:string|null){
 if(at===null)return 'Waktu tidak tercatat'
 const d=new Date(at);if(Number.isNaN(d.getTime()))return 'Waktu tidak valid'
 return `${d.toLocaleString('id-ID',{timeZone:'Asia/Jakarta',dateStyle:'medium',timeStyle:'medium',hour12:false})} WIB`
}
export const auditActor=(r:{actorId:string|null;actorName:string|null})=>r.actorName??(r.actorId===null?'Sistem (tanpa pengguna)':'Pengguna tidak dikenal')
const changedText=(r:AuditRow)=>r.changedKeyCount===0?'Tidak ada kolom yang berubah':`Kolom berubah: ${r.changedKeys.join(', ')}${r.changedKeyCount>r.changedKeys.length?` dan ${amount(r.changedKeyCount-r.changedKeys.length)} lainnya`:''}`
function readable(e:unknown){
 const raw=String((e as {message?:unknown}|null)?.message??'')
 if(raw.includes('CP7_AUDIT_DENIED'))return 'Akun ini tidak punya hak melihat jejak audit.'
 if(raw.includes('CP7_AUDIT_CURSOR_GONE'))return 'Jejak audit berubah sejak daftar ini dibuka. Tekan Muat ulang untuk membaca dari halaman pertama.'
 if(raw.includes('CP7_AUDIT_NOT_FOUND'))return 'Catatan audit itu sudah tidak ada. Tekan Muat ulang.'
 if(raw.includes('CP7_AUDIT_QUERY'))return 'Isian filter tidak bisa dipakai. Periksa tanggal dan kata pencarian.'
 if(raw.startsWith('Jawaban jejak audit'))return raw
 return 'Jejak audit belum bisa dibaca. '+normalizeClientError(e).message
}

export default function ConnectedAuditTrailPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!hasPermission(identity,PAGE_PERMISSION_BY_ID['admin-audit']))return <section className="panel" role="alert">Hak melihat jejak audit diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi audit belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0),mayExport=hasPermission(identity,SENSITIVE_ACTION_PERMISSION.exportAudit)
 const listing=useRef<Listing>({query:toQuery(blank),asOf:null,listed:null,cursors:[null],id:null})
 const [entered,setEntered]=useState<Filters>(blank),[data,setData]=useState<AuditTrail|null>(null),[options,setOptions]=useState<AuditTrail['options']|null>(null)
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[pending,setPending]=useState(false)
 const load=useCallback(async()=>{
  const ticket=++seq.current,l=listing.current
  const request:AuditRequest={...l.query,as_of:l.asOf,after:l.cursors[l.cursors.length-1]??null,listed:l.listed,id:l.id,offset:0,limit:PAGE}
  setData(null);setBusy(true);setError('')
  try{
   const r=await client.rpc('erp_cp7_get_audit_trail_v1',{p_query:request})
   if(ticket!==seq.current)return
   if(r.error)throw r.error
   const read=parseAuditTrail(r.data,request)
   if(l.asOf===null)listing.current={...l,asOf:read.asOf,listed:read.listed}
   setData(read);setOptions(read.options)
  }catch(e){if(ticket===seq.current)setError(readable(e))}finally{if(ticket===seq.current)setBusy(false)}
 },[client])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const edit=(key:keyof Filters,value:string)=>{++seq.current;setBusy(false);setData(null);setError('');setPending(true);setEntered(f=>({...f,[key]:value}))}
 const apply=(f:Filters)=>{
  if(f.from&&f.to&&f.from>f.to){++seq.current;setData(null);setError('Tanggal mulai harus sama atau sebelum tanggal akhir.');return}
  setPending(false);listing.current={query:toQuery(f),asOf:null,listed:null,cursors:[null],id:null};void load()
 }
 const page=(cursors:(string|null)[])=>{listing.current={...listing.current,cursors,id:null};void load()}
 const choose=(id:string)=>{listing.current={...listing.current,id};void load()}
 const closeDetail=()=>{listing.current={...listing.current,id:null};setData(d=>d?{...d,detail:null}:d)}
 const download=(d:AuditTrail)=>{
  const csv=auditCsv(d.page.rows,auditTime,auditActor),blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob)
  const a=document.createElement('a');a.href=url;a.download=`jejak-audit-${d.readAt.slice(0,19).replace(/[^0-9]/g,'')}.csv`;document.body.append(a);a.click();a.remove()
  setTimeout(()=>URL.revokeObjectURL(url),0)
 }
 const types=withSelected(options?.entityTypes??[],entered.entity_type),actions=withSelected(options?.actions??[],entered.action)
 const actors:AuditActor[]=[...(options?.actors??[])];if(entered.actor_id&&!actors.some(a=>a.id===entered.actor_id))actors.push({id:entered.actor_id,name:null})
 const detail=data?.detail??null,rows=data?.page.rows??[]
 const first=data?data.page.before+BigInt(data.page.offset)+1n:0n,last=data?first+BigInt(rows.length)-1n:0n
 const cursors=listing.current.cursors
 return <main className="cproc cmisc" aria-label="Jejak audit perubahan data">
  <header className="panel cproc-heading"><div><div className="eyebrow">PENGATURAN & AUDIT</div><h1>Audit Trail</h1><p>Jejak perubahan data: siapa, kapan, data apa, dan alasannya. Layar ini hanya membaca; tidak ada data yang bisa diubah dari sini.</p></div><button disabled={busy} onClick={()=>apply(entered)}>Muat ulang</button></header>
  <form className="panel cproc-grid" aria-label="Filter jejak audit" onSubmit={e=>{e.preventDefault();apply(entered)}}>
   <label>Dari tanggal (WIB)<input type="date" aria-label="Audit dari tanggal" value={entered.from} onChange={e=>edit('from',e.target.value)}/></label>
   <label>Sampai tanggal (WIB)<input type="date" aria-label="Audit sampai tanggal" value={entered.to} onChange={e=>edit('to',e.target.value)}/></label>
   <label>Jenis data<select aria-label="Jenis data audit" value={entered.entity_type} onChange={e=>edit('entity_type',e.target.value)}><option value="">Semua jenis data</option>{types.map(t=><option key={t} value={t}>{auditEntityLabel(t)}{entityNames[t]?` (${t})`:''}</option>)}</select></label>
   <label>Aksi<select aria-label="Aksi audit" value={entered.action} onChange={e=>edit('action',e.target.value)}><option value="">Semua aksi</option>{actions.map(a=><option key={a} value={a}>{auditActionLabel(a)}</option>)}</select></label>
   <label>Pengguna<select aria-label="Pengguna audit" value={entered.actor_id} onChange={e=>edit('actor_id',e.target.value)}><option value="">Semua pengguna</option>{actors.map(a=><option key={a.id} value={a.id}>{a.name??'Pengguna tidak dikenal'}</option>)}</select></label>
   <label>Cari nomor data atau alasan<input aria-label="Cari jejak audit" maxLength={120} value={entered.q} onChange={e=>edit('q',e.target.value)}/></label>
   <div className="cproc-actions"><button className="primary-btn" type="submit" disabled={busy}>Tampilkan</button><button type="button" disabled={busy} onClick={()=>{setEntered(blank);apply(blank)}}>Hapus filter</button></div>
  </form>
  {busy?<p role="status">Membaca jejak audit…</p>:null}
  {error?<p className="panel" role="alert">{error}</p>:null}
  {pending&&!busy&&!error?<p className="panel" role="note">Filter belum diterapkan. Tekan Tampilkan untuk membaca jejak audit dengan filter ini.</p>:null}
  {data?<>
   <section className="panel" aria-label="Dasar daftar audit"><p>Daftar dibaca {auditTime(data.readAt)}. Catatan yang masuk sesudah daftar ini dibuka tampil sesudah Muat ulang, supaya halaman berikutnya tidak bergeser.</p>
    {data.changed?<p role="alert">Daftar ini berubah sejak dibuka: ada catatan yang baru tersimpan di antara halaman yang sudah dibaca. Tekan Muat ulang supaya tidak ada catatan yang terlewat.</p>
     :data.newer?<p role="status">Ada catatan baru sesudah daftar ini dibuka. Tekan Muat ulang untuk melihatnya.</p>:null}</section>
   <div className="cproc-layout"><section className="panel" aria-label="Daftar jejak audit"><h2>Catatan perubahan</h2>
    {rows.length===0?<p>Tidak ada catatan audit untuk filter ini.</p>:<p>Baris {amount(first)}–{amount(last)} dari {amount(data.page.total)} catatan</p>}
    {rows.map(r=><article key={r.id}><button className="cproc-receipt" data-audit-id={r.id} aria-pressed={detail?.id===r.id} disabled={busy} onClick={()=>choose(r.id)}><span><strong>{auditActionLabel(r.action)} · {auditEntityLabel(r.entityType)}</strong><small>{auditTime(r.at)} · {auditActor(r)}</small><small>Nomor data: {r.entityId??'tidak tercatat'}</small><small>Alasan: {r.reason??'tidak dicatat'}</small><small>{changedText(r)}</small></span><small>#{r.id}</small></button></article>)}
    <div className="cproc-pagination"><button disabled={busy||data.changed||cursors.length<2} onClick={()=>page(cursors.slice(0,-1))}>Halaman sebelumnya</button><button disabled={busy||data.changed||data.page.nextAfter===null} onClick={()=>page([...cursors,data.page.nextAfter])}>Halaman berikutnya</button>
     {mayExport&&data.canExport?<button disabled={busy||rows.length===0} onClick={()=>download(data)}>Unduh CSV halaman ini</button>:<small>Unduh CSV hanya untuk pengguna dengan hak ekspor audit.</small>}</div>
   </section>
   <aside className="panel" aria-label="Rincian catatan audit">{detail?<>
    <h2>Catatan audit #{detail.id}</h2><p>{auditActionLabel(detail.action)} · {auditEntityLabel(detail.entityType)}{detail.entityType?` (tabel ${detail.entityType})`:''}</p>
    <p>Waktu: {auditTime(detail.at)}</p><p>Oleh: {auditActor(detail)}</p><p>Nomor data: {detail.entityId??'tidak tercatat'}</p><p>Alasan: {detail.reason??'tidak dicatat'}</p>
    {detail.tooLarge?<p role="note">Isi data catatan ini terlalu besar untuk ditampilkan di layar.</p>:!detail.hasBefore&&!detail.hasAfter?<p>Catatan ini tidak menyimpan isi data sebelum atau sesudah.</p>:<>
     <h3>Yang berubah</h3>{detail.fields.filter(f=>f.changed).length===0?<p>Tidak ada kolom yang berubah.</p>:null}
     {detail.fields.filter(f=>f.changed).map(f=><article className="cproc-item" key={f.key} data-audit-field={f.key}><strong>{f.key}</strong><p>Sebelum: {f.before??'—'}</p><p>Sesudah: {f.after??'—'}</p></article>)}
     {detail.fields.some(f=>!f.changed)?<details><summary>Kolom lain yang tidak berubah ({amount(detail.fields.filter(f=>!f.changed).length)})</summary>{detail.fields.filter(f=>!f.changed).map(f=><p key={f.key}>{f.key}: {f.after??'—'}</p>)}</details>:null}
     {detail.fieldsTotal>detail.fields.length?<p>Menampilkan {amount(detail.fields.length)} kolom pertama dari {amount(detail.fieldsTotal)}.</p>:null}
     {detail.rawBefore!==null?<p>Data sebelum (bukan daftar kolom): {detail.rawBefore}</p>:null}{detail.rawAfter!==null?<p>Data sesudah (bukan daftar kolom): {detail.rawAfter}</p>:null}
    </>}
    <button disabled={busy} onClick={closeDetail}>Tutup rincian</button>
   </>:<><h2>Rincian catatan audit</h2><p>Pilih satu catatan untuk melihat isi data sebelum dan sesudah perubahan.</p></>}</aside></div>
  </>:null}
 </main>
}
function withSelected(values:string[],selected:string){return selected&&!values.includes(selected)?[...values,selected]:values}
