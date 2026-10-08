import {useMemo} from 'react'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatFact} from './cp7/workspace'
import {analysisWarningLabel} from './nativeAnalysis'
import {stagedRangeLabel,stagedNumber,type StagedAnalysis,type AnalysisPage,type StagedFullCheck,type StagedFreshness,type StagedChangeCategory} from './nativeAnalysisPages'

// A staged run (up to 5,000 targets) shown as its header plus ONE page of
// targets at a time. Every whole-run number below comes from the server's
// page set; the page only ever speaks for its own target range. The run has
// no financial figures (operational path), and the features that read a whole
// Original (reports, reminders, AI, stock detail, fabric workspace, archives)
// are stated unavailable rather than offered. A production plan is made per
// target from the snapshot (contract v2 §3) and rechecked live when applied.
// The run is a snapshot "Data per <time>" (contract v2): what changed since is
// shown beside it and the snapshot is never called current; "Cek sumber" says
// only how it compared with the data at the check's own time.
type Props={staged:StagedAnalysis;page:AnalysisPage|null;loading:number|null;blocked:boolean;sourceCheck:StagedFullCheck|null;checking:boolean
 freshness:StagedFreshness|null;freshnessLoading:boolean;freshnessError:string;onPage:(index:number)=>void;onCheckSource:()=>void;onPlan?:(targetKey:string)=>void}
const stateLabel=(s:string)=>s==='ACTIVE'?'Aktif':s==='PAUSED'?'Ditunda':s==='STOPPED'?'Dihentikan':'Status lain'
export const STAGED_CHANGE_LABELS:Record<StagedChangeCategory,string>={SALES:'Penjualan & retur',FG_STOCK:'Stok barang jadi',MATERIAL_STOCK:'Stok bahan',
 PRODUCTION:'Produksi (potong, jahit, QC, laundry, BS)',PRODUCTION_ORDERS:'PO produksi',MASTER_DATA:'Data induk (produk, SKU, pola, bahan, lokasi)',
 MATERIAL_PURCHASES:'Pembelian bahan',PLANNING_POLICIES:'Kebijakan perencanaan'}
export function stagedFreshnessText(f:StagedFreshness):string{
 const t=formatCp6WibDateTime,n=stagedNumber,asOf=`hasil ini tetap analisis per ${t(f.dataAsOf)}`
 if(f.state==='VERIFIED_SAME')return`Sama dengan data per ${t(f.sameAsOf!)} (Cek sumber). Belum ada perubahan tercatat sesudahnya.`
 if(f.state==='STALE_VERIFIED')return`Data sudah berubah (Cek sumber ${t(f.lastCheck!.checkedAt)}); ${asOf}.`
 if(f.state==='CHANGES_RECORDED')return f.lastCheck?`Cek sumber ${t(f.lastCheck.checkedAt)}: sama. Sesudah itu ada ${n(f.lastCheck.changesAfterCheck)} perubahan tercatat; ${asOf}.`:`Sudah ada ${n(f.changesTotal)} perubahan tercatat sejak data diambil; ${asOf}.`
 return'Belum ada perubahan tercatat sejak data diambil. Belum dicek penuh; tekan Cek sumber untuk memastikan.'
}
export default function NativeStagedAnalysisView({staged,page,loading,blocked,sourceCheck,checking,freshness,freshnessLoading,freshnessError,onPage,onCheckSource,onPlan}:Props){
 const m=staged.set,h=staged.header,x=h.analysisHeader,t=m.totals,n=stagedNumber
 const current=loading??page?.index??0,range=(i:number)=>stagedRangeLabel(m.pages[i].targetLo,m.pages[i].targetHi,m.targetsTotal)
 const labels=useMemo(()=>new Map(h.labels.map(l=>[l.key,`${l.sku} · ${l.name}`])),[h.labels])
 const label=(key:string)=>labels.get(key)??key
 return<section className="native-analysis-staged native-analysis-result" role="region" aria-label="Hasil analisis bertahap" data-run-id={m.runId} data-identity-hash={m.identityHash}>
  <p className="native-analysis-run">Run <span>{m.runId}</span></p>
  <p>{n(m.targetsTotal)} target dalam {n(m.pageCount)} halaman. Data per {formatCp6WibDateTime(m.reference.capturedAt)}; jadwal versi {x.scenario.version}. Angka keuangan tidak termasuk analisis bertahap.</p>
  <section aria-label="Kesegaran data" data-freshness-state={freshness?.state??''}>
   {freshness?<p className={freshness.state==='VERIFIED_SAME'?'native-demand-current':freshness.state==='NO_RECORDED_CHANGE'?undefined:'native-demand-stale'}>{stagedFreshnessText(freshness)}</p>:null}
   {freshness&&freshness.changesTotal>0?<ul aria-label="Perubahan sejak data diambil">{freshness.changes.filter(c=>c.rows>0).map(c=><li key={c.category} data-change-category={c.category}>{STAGED_CHANGE_LABELS[c.category]}: {n(c.rows)} perubahan{c.deleted?` (${n(c.deleted)} dihapus)`:''}{c.lastRecordedAt?`, terakhir ${formatCp6WibDateTime(c.lastRecordedAt)}`:''}</li>)}</ul>:null}
   {freshnessLoading?<p role="status">Membaca perubahan sejak data diambil…</p>:null}
   {freshnessError?<p>Perubahan sejak data diambil belum bisa dibaca: {freshnessError}</p>:null}
   {!freshness&&sourceCheck?<p className={sourceCheck.sourceState==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>Cek sumber {formatCp6WibDateTime(sourceCheck.checkedAt)}: {sourceCheck.sourceState==='UNCHANGED'?'sama dengan data saat itu':'data sudah berubah'}.</p>:null}
  </section>
  <div className="native-analysis-actions"><button disabled={blocked||checking} onClick={onCheckSource}>Cek sumber</button></div>
  {checking?<p>Memeriksa sumber acuan…</p>:null}
  <section aria-label="Ringkasan seluruh analisis bertahap">
   <h3>Ringkasan seluruh analisis · {n(m.targetsTotal)} target</h3>
   <p>Angka di bagian ini dihitung server dari seluruh {n(m.targetsTotal)} target, bukan dari halaman target yang sedang dibuka.</p>
   <ul>
    <li data-total="ACTIVE">Status produksi aktif: {n(t.recommendations.ACTIVE)} target</li>
    <li data-total="PAUSED">Ditunda: {n(t.recommendations.PAUSED)} target</li>
    <li data-total="STOPPED">Dihentikan: {n(t.recommendations.STOPPED)} target</li>
    {t.recommendations.OTHER?<li data-total="OTHER">Status produksi lain: {n(t.recommendations.OTHER)} target</li>:null}
    <li data-total="POLICY_UNREVIEWED">Status produksi belum diperiksa: {n(t.policyUnreviewed)} target</li>
    <li data-total="TIMELINE">Baris linimasa seluruh target: {n(t.items.timeline??0)} · kebutuhan bahan seluruh target: {n(t.items.material_needs??0)}</li>
   </ul>
   <p>Bahan dan produksi baru belum dipastikan. Keuangan dan HPP tidak tercakup pada analisis bertahap dan tidak dianggap nol. Angka belum diketahui tetap ditampilkan apa adanya.</p>
   <p>Laporan, pengingat, Tanya AI, rincian stok, ruang kerja kain dan arsip memakai seluruh hasil sekaligus, jadi belum tersedia untuk analisis bertahap. Rincian per target dibaca per halaman di bawah.</p>
   <p>Rencana Potongan dibuat per target dari halaman di bawah memakai data per {formatCp6WibDateTime(m.reference.capturedAt)}; saat draf Potongan dibuat, server memeriksa ulang stok, barang dalam proses, kebijakan dan kapasitas pada saat itu.</p>
  </section>
  {m.pageCount===0?<p>Analisis ini tidak memuat rincian per target.</p>:<section aria-label="Target per halaman">
   <h3>{range(current)}</h3>
   <nav aria-label="Halaman target analisis"><button disabled={blocked||current===0} onClick={()=>onPage(current-1)}>Halaman sebelumnya</button><span>Halaman {n(current+1)} dari {n(m.pageCount)}</span><button disabled={blocked||current>=m.pageCount-1} onClick={()=>onPage(current+1)}>Halaman berikutnya</button></nav>
   <label>Pilih rentang target<select aria-label="Pilih rentang target" value={current} disabled={blocked} onChange={e=>onPage(Number(e.target.value))}>{m.pages.map(p=><option key={p.index} value={p.index}>{range(p.index)}</option>)}</select></label>
   {loading!==null?<p role="status">Mengambil {range(loading).replace(/^Target/,'target')}…</p>:null}
   {page&&loading===null?<div aria-label={`Isi ${range(page.index)}`} data-page-index={page.index}>
    <p>Halaman ini hanya memuat {range(page.index).replace(/^Target/,'target')}: {n(page.items.recommendations.length)} rekomendasi dan {n(page.summary.policyUnreviewed)} target dengan status produksi belum diperiksa.</p>
    <div className="responsive-table"><table><thead><tr><th>Produk</th><th>Status produksi</th><th>Stok fisik</th><th>Target</th><th>Kurang setelah stok proses terikat</th><th>Kurang setelah pembagian global</th><th>Produksi baru layak</th>{onPlan?<th>Rencana</th>:null}</tr></thead>
     <tbody>{page.items.recommendations.map(r=><tr key={r.target.key} data-analysis-target={r.target.key}><td><strong>{label(r.target.key)}</strong></td><td data-label="Status produksi">{stateLabel(r.production_state)}</td><td data-label="Stok fisik">{formatFact(r.actual_fg)}</td><td data-label="Target">{formatFact(r.target_qty)}</td><td data-label="Kurang setelah stok proses terikat">{formatFact(r.q_base)}</td><td data-label="Kurang setelah pembagian global">{formatFact(r.q_conditional)}</td><td data-label="Produksi baru layak">{formatFact(r.feasible_new)}</td>{onPlan?<td data-label="Rencana"><button disabled={blocked} onClick={()=>onPlan(r.target.key)}>Rencanakan Potongan {label(r.target.key)}</button></td>:null}</tr>)}</tbody></table></div>
    {page.items.generation_warnings.length?<details><summary>Target pada halaman ini dengan status produksi belum diperiksa</summary>{page.items.generation_warnings.map(w=><p key={w}>{label(w.slice('PRODUCTION_POLICY_UNREVIEWED:'.length))} · {analysisWarningLabel(w)}</p>)}</details>:null}
   </div>:null}
  </section>}
  <details><summary>Asumsi dan batas data</summary>{x.assumptions.map(a=><p key={a.id}>{a.label} · {a.confirmed_for_operation?'Dikonfirmasi untuk operasi':'Belum dikonfirmasi untuk operasi'}.</p>)}{x.generation_warnings.map((w,i)=><p key={`${w}:${i}`}>{analysisWarningLabel(w)}</p>)}<p>Asumsi per target ada pada halaman targetnya.</p><p>Hash identitas {m.identityHash}</p><p>Hash sumber acuan {m.reference.sourceHash}; {n(m.pageCount)} halaman, masing-masing paling besar 8.000.000 byte.</p></details>
 </section>
}
