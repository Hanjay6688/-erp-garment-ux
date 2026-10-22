import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import { REASON_MAX, REORDER_PAGE, REORDER_QUERY_MAX, formatReorderQty, formatReorderUpTo2, formatReorderWhole, parseFgReorderRefresh, servicePercent,
  type ServiceLevel } from './fgReorderContract'
import {
  accessoryEstimateLines, accessoryEstimatePoint, accessoryNumbersOf, accessoryNumbersOfDraft, materialBasisText, materialChanged, materialDraftOf,
  materialErrorText, materialFilters, materialFormulaLines, materialPayload, materialProblem, materialQty, materialStatus, materialReorderVisible,
  materialWriteErrorText, parseMaterialSaveResult, parseMaterialWorkspace, type MaterialDraft, type MaterialFilter, type MaterialPayload, type MaterialQuery,
  type MaterialRow, type MaterialType, type MaterialWorkspace,
  type FabricRule,
} from './materialReorderContract'
import './procurement-connected.css'
import './fg-reorder.css'
import {clearMaterialRequest,materialAccessDenied,materialRequestDefinitelyRefused,materialRequestPrefix,persistMaterialRequest,readMaterialRequests,type MaterialRequest} from './materialReorderRequests'

// SS-2 (fabric) and SS-3 (accessories), owner D17-9, D17-10 and D17-12: one component on Gudang › Bahan & Roll and Master Data ›
// Kain & Benchmark (FABRIC: "Titik pesan ulang kain", the formula with the lama kirim of each fabric), Gudang › Aksesori and
// Master Data › Aksesori & Harga Mandor (ACCESSORY: "Batas minimum aksesori", no formula: the minimum is worked out from the
// owner's own numbers per accessory, MOQ, lama kirim dari Cina, perkiraan pemakaian per bulan and cadangan, or typed directly;
// the usage the ERP measures is shown next to the estimate for comparison only). It reads erp_cp7_get_material_reorder_v1 with
// the server's own permissions (it shows nothing to an account the server would refuse), "Hitung sekarang" refreshes, and
// Owner/Admin (can_manage from the server) set the lama kirim of a fabric or the numbers of an accessory. As on Ringkasan Barang
// Jadi: every read is sequenced so the latest question wins, and a write keeps one request id per attempt in memory (an
// unanswered attempt is sent again with it).
type Note = { tone: 'ok' | 'bad'; text: string }
type Editing = MaterialDraft & { materialId: string }
const words: Record<MaterialType, { label: string; heading: string; noun: string; search: string; row: string; manualFilter: string }> = {
  FABRIC: { label: 'Titik pesan ulang kain', heading: 'Titik pesan ulang kain (safety stock)', noun: 'kain', search: 'Cari kain untuk titik pesan ulang',
    row: 'Titik pesan ulang', manualFilter: 'Pakai minimum' },
  ACCESSORY: { label: 'Batas minimum aksesori', heading: 'Batas minimum aksesori', noun: 'aksesori', search: 'Cari aksesori untuk batas minimum',
    row: 'Batas minimum', manualFilter: 'Diketik manual' },
}

export default function MaterialReorderPanel({ materialType, readOnlySummary=false }: { materialType: MaterialType; readOnlySummary?: boolean }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !materialReorderVisible(materialType, identity.permissions)) return null
  return <Panel materialType={materialType} readOnlySummary={readOnlySummary} key={JSON.stringify([materialType,runtime.projectRef,identity.profile.id,
    identity.profile.role,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.permissions])}/>
}

function Panel({ materialType,readOnlySummary }: { materialType: MaterialType;readOnlySummary:boolean }) {
  const { runtime,identity } = useAuth()
  if (!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED') throw new Error('Sesi bahan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), say = words[materialType], fabric = materialType === 'FABRIC'
  const requestScope=runtime.projectRef+':'+identity.profile.id
  const serial = useRef(0), requested = useRef<MaterialQuery>({ material_type: materialType, q: '', filter: 'ALL', offset: 0, limit: REORDER_PAGE })
  const [data, setData] = useState<MaterialWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [filter, setFilter] = useState<MaterialFilter>('ALL'), [search, setSearch] = useState('')
  const [writing, setWriting] = useState<string | null>(null), [notes, setNotes] = useState<Record<string, Note>>({})
  const [editing, setEditing] = useState<Editing | null>(null)
  const [recovery,setRecovery]=useState(()=>readMaterialRequests(requestScope,materialType))
  const [accessDenied,setAccessDenied]=useState(false)

  const note = (scope: string, value: Note | null) => setNotes(current => {
    const next = { ...current }
    if (value) next[scope] = value; else delete next[scope]
    return next
  })
  const load = useCallback(async () => {
    const query = { ...requested.current }, n = ++serial.current
    setBusy(true); setError(''); setData(null)
    try {
      const reply = await client.rpc('erp_cp7_get_material_reorder_v1', { p_query: query })
      if (n !== serial.current) return
      if (reply.error) throw reply.error
      setData(parseMaterialWorkspace(reply.data, query));setAccessDenied(false)
    } catch (e) {
      if (n === serial.current) { setData(null);setAccessDenied(materialAccessDenied(e)); setError(materialErrorText(e, materialType)) }
    } finally { if (n === serial.current) setBusy(false) }
  }, [client, materialType])
  useEffect(() => { void load() }, [load])
  useEffect(() => () => { ++serial.current }, [])
  useEffect(()=>{
    const listen=(e:StorageEvent)=>{if(e.key===null||e.key.startsWith(materialRequestPrefix(requestScope,materialType)))setRecovery(readMaterialRequests(requestScope,materialType))}
    addEventListener('storage',listen);return()=>removeEventListener('storage',listen)
  },[requestScope,materialType])

  const locked = busy || writing !== null || !data
  // A newer question may start while a read is under way (filter, search): the sequence number keeps only its answer.
  const ask = (next: Partial<MaterialQuery>) => { requested.current = { ...requested.current, ...next }; void load() }
  const reload = () => { setNotes({}); void load() }

  const refresh = async () => {
    if (locked) return
    setWriting('REFRESH'); note('REFRESH', null)
    try {
      const reply = await client.rpc('erp_cp7_refresh_material_reorder_v1', { p_material_type: materialType })
      if (reply.error) throw reply.error
      const r = parseFgReorderRefresh(reply.data)
      note('REFRESH', { tone: 'ok', text: `Selesai dihitung ${formatCp6WibDateTime(r.computedAt)}: ${formatReorderWhole(r.materials)} kain dan aksesori, `
        + `${formatReorderWhole(r.materialsAtOrBelow)} menipis.` })
      setWriting(null); await load()
    } catch (e) { note('REFRESH', { tone: 'bad', text: materialWriteErrorText(e, materialType, 'REFRESH') }) } finally { setWriting(null) }
  }

  const send = async (request:MaterialRequest,fromEdit=false) => {
    if(readOnlySummary||busy||writing!==null||accessDenied)return
    const payload=request.payload,id=payload.material_id,n=++serial.current
    setWriting(id);note(id,null);note('RECOVERY',null)
    try{
      const reply=await client.rpc('erp_cp7_save_material_reorder_v1',{p_payload:payload,p_request:request.id})
      if(n!==serial.current)return
      if(reply.error)throw reply.error
      const saved=parseMaterialSaveResult(reply.data,payload,materialType)
      clearMaterialRequest(requestScope,materialType,request);setRecovery(readMaterialRequests(requestScope,materialType))
      const what=fabric?(payload.fabric_rule==='FORMULA'?'aturan rumus':payload.fabric_rule==='LEGACY_MINIMUM'?'minimum lama yang diperiksa':payload.lead_days===null?'lama kirim kosong':'lama kirim '+formatReorderUpTo2(payload.lead_days)+' hari')
        :accessorySavedText(payload,data?.page.rows.find(r=>r.materialId===id)?.unitCode??null)
      const result:Note={tone:'ok',text:'Tersimpan (revisi '+formatReorderWhole(saved.revision)+'): '+what+'.'+(saved.replay?' Permintaan ini ternyata sudah tersimpan sebelumnya.':'')}
      note(id,result);if(!fromEdit)note('RECOVERY',result)
      if(fromEdit)setEditing(null)
      setWriting(null);await load()
    }catch(e){
      if(n!==serial.current)return
      let failure=e
      if(materialRequestDefinitelyRefused(e)){
        try{clearMaterialRequest(requestScope,materialType,request)}catch(cleanup){failure=cleanup}
        setRecovery(readMaterialRequests(requestScope,materialType))
      }
      if(materialAccessDenied(e)){setData(null);setAccessDenied(true);setError(materialErrorText(e,materialType))}
      const result:Note={tone:'bad',text:materialWriteErrorText(failure,materialType,'SAVE')};note(id,result);if(!fromEdit)note('RECOVERY',result)
    }finally{if(n===serial.current)setWriting(null)}
  }
  const save = async (r: MaterialRow) => {
    if(locked||!editing||editing.materialId!==r.materialId||materialProblem(materialType,editing)||!materialChanged(materialType,r,editing))return
    try{
      const payload=materialPayload(r,materialType,editing),held=readMaterialRequests(requestScope,materialType)
      if(held.error)throw Error(held.error)
      const mine=held.pending.filter(x=>x.payload.material_id===r.materialId),same=mine.find(x=>JSON.stringify(x.payload)===JSON.stringify(payload))
      if(mine.length&&!same)throw Error('Masih ada penyimpanan bahan ini yang hasilnya belum jelas. Periksa penyimpanan yang sama di atas sebelum membuat perubahan lain.')
      const request=same??{id:crypto.randomUUID(),label:r.name.slice(0,400),payload}
      if(!same)persistMaterialRequest(requestScope,materialType,request)
      setRecovery(readMaterialRequests(requestScope,materialType));await send(request,true)
    }catch(e){note(r.materialId,{tone:'bad',text:materialWriteErrorText(e,materialType,'SAVE')})}
  }
  const noteView = (scope: string) => {
    const n = notes[scope]
    return n ? <p className={`cfr-note ${n.tone}`} role={n.tone === 'bad' ? 'alert' : 'status'}>{n.text}</p> : null
  }

  const run = data?.run ?? null, windowDays = run?.windowDays ?? data?.settings.windowDays ?? 30
  const level = run?.serviceLevel ?? data?.settings.serviceLevel ?? '0.95', counts = data?.counts, page = data?.page
  const filterLabel: Record<MaterialFilter, string> = { ALL: 'Semua', AT_OR_BELOW: 'Menipis', MANUAL: say.manualFilter, ESTIMATE: 'Dari hitungan',
    NOT_ENOUGH_DATA: 'Belum cukup data', NOT_SET: 'Belum diisi' }
  const countOf: Record<MaterialFilter, number | undefined> = { ALL: counts?.items, AT_OR_BELOW: counts?.atOrBelow, MANUAL: counts?.manual,
    ESTIMATE: counts?.estimate, NOT_ENOUGH_DATA: counts?.notEnoughData, NOT_SET: counts?.notSet }

  return <section className="cproc cfr" aria-label={say.label}><div className="panel cfr-panel">
    <header className="cfr-head">
      <div>
        <div className="eyebrow">{fabric ? 'KAIN' : 'AKSESORI'} · PENGINGAT STOK</div>
        <h2>{say.heading}</h2>
        {readOnlySummary ? <>
          <p>Seluruh gudang, dari perhitungan yang juga dipakai panel kain dan Pengingat sistem/WhatsApp. Pencarian gudang di atas tidak menyaring daftar kain ini.</p>
          <p>Stok fisik, pesanan yang belum diterima, dan perkiraan kebutuhan ditampilkan terpisah. Titik pesan ulang adalah ambang pengingat, bukan jumlah stok atau jumlah yang harus dibeli.</p>
          {counts?<p>{formatReorderWhole(counts.items)} kain: {formatReorderWhole(counts.formula)} memakai rumus, {formatReorderWhole(counts.manual)} memakai minimum lama;
            {' '}{formatReorderWhole(counts.notEnoughData+counts.noUsage)} belum mempunyai rumus yang cukup datanya. {formatReorderWhole(counts.atOrBelow)} perlu diperhatikan.</p>:null}
        </> : fabric ? <>
          <p>Titik pesan ulang = rata-rata pakai per hari × lama kirim + cadangan. Dihitung dari pemakaian yang sudah diposting {formatReorderWhole(windowDays)} hari
            terakhir (hari tanpa stok tidak dihitung) dengan tingkat layanan {servicePercent(level)}%, dalam satuan bahannya.</p>
          <p>Pemakaian kain = dikeluarkan untuk potong dikurangi sisa yang kembali, pemakaian pabrik, dan bahan ke mandor. Kain yang sudah dipesan (PO terbuka)
            ikut dihitung. Minimum lama dari Master Data › Kain & Benchmark tetap terlihat sebagai referensi. Pilih satu aturan per kain: minimum lama
            yang diperiksa, atau rumus. Sebelum ada pilihan baru, aturan sebelumnya tetap berlaku. Lama kirim (hari) dari supplier diisi per kain
            oleh Owner atau Admin, karena ERP belum mencatatnya. Aturan rumus membandingkan sisa ditambah yang dipesan dengan titik pesan ulang
            (sama atau di bawahnya). Minimum lama membandingkan stok fisik saja (di bawahnya). Hanya aturan aktif yang menentukan kapan muncul pengingat "Stok kain
            di bawah minimum" di Reminder › Pengingat sistem, diteruskan ke WhatsApp Bos bila Sambungan WhatsApp menyala. Tingkat layanan dan jumlah hari diatur
            di Gudang › Ringkasan Barang Jadi.</p>
        </> : <>
          <p>Aksesori memakai batas minimum, bukan rumus. Aplikasi menghitungnya dari isian per aksesori: (perkiraan pemakaian per bulan ÷ 30) × (lama kirim
            dari Cina + cadangan untuk kiriman telat), dibulatkan ke atas. Batas minimum yang diketik langsung menggantikan hitungan. Pengingat "Stok aksesori
            menipis" muncul di Reminder › Pengingat sistem kalau stok di gudang sama dengan atau di bawah batas minimum, dan diteruskan ke WhatsApp Bos bila
            Sambungan WhatsApp menyala. 0 berarti tidak pernah diingatkan; tanpa batas minimum dan tanpa isian hitungan yang lengkap, juga tidak diingatkan.</p>
          <p>Isian diisi per aksesori oleh Owner atau Admin. MOQ hanya untuk pesanan, tidak mengubah batas minimum. Pemakaian nyata per hari
            ({formatReorderWhole(windowDays)} hari terakhir, dari nota mandor dan pemakaian pabrik) hanya pembanding, tidak dipakai dalam hitungan. Stok di pos
            servis, area periksa dan area rusak tidak dihitung sebagai stok di gudang.</p>
        </>}
        {data ? <p className="cfr-run">{run ? <>Dihitung {formatCp6WibDateTime(run.computedAt)} (pemakaian {formatWaDay(run.windowFrom)} sampai {formatWaDay(run.windowThrough)}).</>
          : <>Belum pernah dihitung. Server menghitungnya tiap menit sesudah pengingat WhatsApp diatur (Owner menyimpan pengaturan di Reminder › Sambungan
            WhatsApp satu kali), atau tekan "Hitung sekarang".</>}</p> : null}
      </div>
      <div className="cfr-actions">
        {!readOnlySummary?<button type="button" className="primary-btn" disabled={locked} onClick={() => { void refresh() }}>Hitung sekarang</button>:null}
        <button type="button" aria-label={`Muat ulang ${say.label.toLowerCase()}`} disabled={writing !== null} onClick={reload}>Muat ulang</button>
      </div>
    </header>
    {noteView('REFRESH')}
    {!readOnlySummary&&(recovery.error||recovery.pending.length)?<aside className="cfr-source" aria-label="Penyimpanan bahan belum selesai">
      {recovery.error?<p role="alert">{recovery.error}</p>:null}
      {accessDenied?<p>Catatan penyimpanan tetap disimpan sampai akses akun dipulihkan.</p>:recovery.pending.map(r=><div key={r.id}>
        <p>Hasil penyimpanan {r.label} belum dipastikan. Periksa penyimpanan yang sama sebelum mengganti aturannya.</p>
        <button type="button" disabled={busy||writing!==null||Boolean(recovery.error)} onClick={()=>{void send(r)}}>Ulangi simpan bahan yang sama: {r.label}</button>
      </div>)}
    </aside>:null}
    {noteView('RECOVERY')}
    {error ? <p className="cfr-note bad" role="alert">{error}</p> : null}
    <div className="cfr-filters" role="group" aria-label={`Saring ${say.label.toLowerCase()}`}>
      {materialFilters[materialType].map(f => { const n = countOf[f]; return <button type="button" key={f} aria-pressed={filter === f}
        className={filter === f ? 'active' : ''} disabled={writing !== null} onClick={() => { setFilter(f); ask({ filter: f, offset: 0 }) }}>
        {filterLabel[f]}{n === undefined ? '' : ` (${formatReorderWhole(n)})`}</button> })}
    </div>
    <form className="cfr-search" onSubmit={e => { e.preventDefault(); ask({ q: search.trim(), offset: 0 }) }}>
      <label>Cari SKU atau nama {say.noun}<input aria-label={say.search} maxLength={REORDER_QUERY_MAX} value={search}
        onChange={e => setSearch(e.target.value)}/></label>
      <button type="submit" disabled={writing !== null}>Cari</button>
      <button type="button" disabled={writing !== null || (search === '' && requested.current.q === '')}
        onClick={() => { setSearch(''); ask({ q: '', offset: 0 }) }}>Kosongkan pencarian</button>
    </form>
    {busy ? <p role="status">Memuat {say.label.toLowerCase()}…</p> : null}
    {data && page ? <>
      {!page.rows.length ? <p className="cfr-none">Tidak ada {say.noun} yang cocok.</p> : null}
      <div className="cfr-list">{page.rows.map(r => <Row key={r.materialId} r={r} type={materialType} windowDays={windowDays} level={level} canManage={data.canManage&&!readOnlySummary}
        locked={locked} writing={writing === r.materialId} draft={editing?.materialId === r.materialId ? editing : null} note={noteView(r.materialId)}
        onOpen={() => { setEditing({ materialId: r.materialId, ...materialDraftOf(r) }); note(r.materialId, null) }} onClose={() => setEditing(null)}
        onDraft={next => setEditing(current => current && current.materialId === r.materialId ? { ...current, ...next } : current)}
        onSave={() => { void save(r) }}/>)}</div>
      <div className="cproc-pagination"><span>{formatReorderWhole(page.rows.length)} {say.noun} · total {page.total}</span>
        <button type="button" disabled={locked || !page.offset} onClick={() => ask({ offset: Math.max(0, page.offset - REORDER_PAGE) })}>Sebelumnya</button>
        <button type="button" disabled={locked || page.nextOffset === null} onClick={() => ask({ offset: page.nextOffset ?? 0 })}>Berikutnya</button></div>
    </> : null}
  </div></section>
}

function Row({ r, type, windowDays, level, canManage, locked, writing, draft, note, onOpen, onClose, onDraft, onSave }: {
  r: MaterialRow; type: MaterialType; windowDays: number; level: ServiceLevel; canManage: boolean; locked: boolean; writing: boolean; draft: Editing | null
  note: ReactNode; onOpen: () => void; onClose: () => void; onDraft: (next: Partial<MaterialDraft>) => void; onSave: () => void
}) {
  const status = materialStatus(r), fabric = type === 'FABRIC', q = (v: string) => materialQty(v, r.unitCode)
  const unit = r.unitCode ? ` ${r.unitCode}` : '', inUnit = r.unitCode ? ` (${r.unitCode})` : ''
  const minimumLabel = `Batas minimum${inUnit}`, moqLabel = `MOQ${inUnit}`, usageLabel = `Perkiraan pemakaian per bulan${inUnit}`
  const measured = r.dailyMean === null ? 'belum ada pemakaian' : `${formatReorderUpTo2(r.dailyMean)}${unit}`
  const set = (v: string | null, suffix: string) => v === null ? 'belum diisi' : `${formatReorderQty(v)}${suffix}`
  const problem = draft ? materialProblem(type, draft) : '', changed = draft ? materialChanged(type, r, draft) : false
  const actions = <div className="cfr-actions">
    <button type="submit" className="primary-btn" disabled={locked || problem !== '' || !changed}>{writing ? 'Menyimpan…' : 'Simpan'}</button>
    <button type="button" disabled={writing} onClick={onClose}>Batal</button>
  </div>
  const reason = <label>Alasan<input aria-label="Alasan perubahan bahan" maxLength={REASON_MAX} value={draft?.reason ?? ''} onChange={e => onDraft({ reason: e.target.value })}/></label>
  const check = !changed ? <p className="cfr-none">Belum ada yang diubah.</p> : problem ? <p className="cfr-problem">{problem}</p> : null
  return <article className="cfr-row" aria-label={`${words[type].row} ${r.name} (SKU ${r.sku})`} data-material-id={r.materialId}>
    <header><div><h3>{r.name}</h3><small>SKU {r.sku}</small></div><span className={`cfr-chip ${status.tone}`}>{status.label}</span></header>
    {fabric ? <dl>
      <div><dt>Stok fisik saat perhitungan</dt><dd data-cmr="free">{q(r.freeQty)}</dd></div>
      <div><dt>Pesanan belum diterima</dt><dd data-cmr="ordered">{q(r.onOrderQty)}</dd></div>
      <div><dt>Pakai/hari</dt><dd data-cmr="daily">{r.dailyMean === null ? 'belum ada' : `${formatReorderUpTo2(r.dailyMean)}${unit}`}</dd></div>
      <div><dt>Lama kirim (hari)</dt><dd data-cmr="lead">{r.leadDays === null ? 'belum diisi' : formatReorderUpTo2(r.leadDays)}</dd></div>
      <div><dt>Titik pesan ulang</dt><dd data-cmr="point">{r.point === null ? 'belum ada' : q(r.point)}</dd></div>
      <div><dt>Aturan yang aktif</dt><dd data-cmr="basis">{materialBasisText(r, windowDays)}</dd></div>
    </dl> : <dl>
      <div><dt>Stok di gudang</dt><dd data-cmr="free">{q(r.freeQty)}</dd></div>
      <div><dt>Pemakaian nyata per hari ({formatReorderWhole(windowDays)} hari terakhir)</dt><dd data-cmr="daily">{measured}</dd></div>
      <div><dt>Perkiraan pemakaian per hari (isian)</dt>
        <dd data-cmr="estimate-daily">{r.usageMonthQty === null ? 'belum diisi' : `${formatReorderUpTo2(String(Number(r.usageMonthQty) / 30))}${unit}`}</dd></div>
      <div><dt>Batas minimum</dt><dd data-cmr="point">{r.point === null ? 'belum diisi' : q(r.point)}</dd></div>
      <div><dt>Asal angka</dt><dd data-cmr="basis">{materialBasisText(r, windowDays)}</dd></div>
    </dl>}
    {fabric ? <>
      <p className="cfr-source" data-cmr="legacy">Minimum lama (referensi baca saja): {r.legacyMinimumQty===null?'belum tersedia':q(r.legacyMinimumQty)}.
        {' '}{r.fabricRule===null?'Belum ada pilihan ulang; aturan sebelumnya masih berlaku.':r.fabricRule==='FORMULA'?'Rumus dipilih; angka lama tidak mengaktifkan pengingat kedua.':'Minimum yang dipilih tetap berlaku sampai aturan disimpan lagi.'}</p>
      <details className="cfr-formula"><summary>Rincian rumus</summary><ul>{materialFormulaLines(r, windowDays, level).map(line => <li key={line}>{line}</li>)}</ul></details></>
      : <div className="cfr-source">
        <p data-cmr="inputs">Isian: MOQ {set(r.moq, unit)} · lama kirim dari Cina {set(r.leadDays, ' hari')} · pemakaian per bulan {set(r.usageMonthQty, unit)} ·
          cadangan {set(r.bufferDays, ' hari')}.</p>
        <div data-cmr="estimate">{accessoryEstimateLines(accessoryNumbersOf(r), r.unitCode).map(line => <p key={line}>{line}</p>)}</div>
      </div>}
    {note}
    {canManage && !draft ? <button type="button" disabled={locked} onClick={onOpen}>{fabric ? 'Atur lama kirim' : 'Atur batas minimum'}</button> : null}
    {canManage && draft ? <form className="cfr-manual" onSubmit={e => { e.preventDefault(); onSave() }}>
      {fabric ? <fieldset disabled={locked}><legend>Lama kirim</legend>
        <label>Lama kirim (hari)<input inputMode="decimal" aria-label="Lama kirim (hari)" maxLength={6} value={draft.lead} onChange={e => onDraft({ lead: e.target.value })}/>
          <small>Berapa hari dari pesan ke supplier sampai kain diterima. Kosong = rumus tidak dihitung.</small></label>
        <label>Aturan kain yang akan dipakai<select aria-label="Aturan kain yang akan dipakai" value={draft.fabricRule??''}
          onChange={e=>onDraft({fabricRule:e.target.value as FabricRule|''})}>
          <option value="">Pertahankan aturan yang aktif</option>
          <option value="FORMULA">Pakai rumus</option>
          <option value="LEGACY_MINIMUM" disabled={r.legacyMinimumQty===null}>Pakai minimum lama yang diperiksa</option>
        </select></label>
        <p className="cfr-source">Referensi minimum lama: {r.legacyMinimumQty===null?'belum tersedia':q(r.legacyMinimumQty)} (baca saja).
          {' '}{draft.fabricRule==='LEGACY_MINIMUM'?'Angka ini akan menjadi minimum yang dipilih. Perubahan referensi sesudahnya tidak mengubah pilihan ini.':draft.fabricRule==='FORMULA'?'Hanya rumus yang akan mengatur pengingat kain ini.':'Mengubah lama kirim mempertahankan aturan dan minimum yang sudah dipilih.'}</p>
        {reason}{check}{actions}
      </fieldset> : <fieldset disabled={locked}><legend>Batas minimum</legend>
        <label>{moqLabel}<input inputMode="decimal" aria-label={moqLabel} maxLength={18} value={draft.moq} onChange={e => onDraft({ moq: e.target.value })}/>
          <small>Jumlah pesan minimal ke supplier. Hanya untuk pesanan, tidak mengubah batas minimum. Kosong boleh.</small></label>
        <label>Lama kirim dari Cina (hari)<input inputMode="decimal" aria-label="Lama kirim dari Cina (hari)" maxLength={6} value={draft.lead}
          onChange={e => onDraft({ lead: e.target.value })}/><small>Berapa hari dari pesan sampai aksesori diterima.</small></label>
        <label>{usageLabel}<input inputMode="decimal" aria-label={usageLabel} maxLength={18} value={draft.usageMonth} onChange={e => onDraft({ usageMonth: e.target.value })}/>
          <small>Perkiraan Bos. Pemakaian nyata dari ERP: {measured} per hari ({formatReorderWhole(windowDays)} hari terakhir), hanya pembanding.</small></label>
        <label>Cadangan untuk kiriman telat (hari)<input inputMode="decimal" aria-label="Cadangan untuk kiriman telat (hari)" maxLength={6} value={draft.buffer}
          onChange={e => onDraft({ buffer: e.target.value })}/><small>Tambahan hari kalau kiriman terlambat. 0 boleh.</small></label>
        <div className="cfr-source" data-cmr="draft-estimate">{accessoryEstimateLines(accessoryNumbersOfDraft(draft), r.unitCode).map(line => <p key={line}>{line}</p>)}</div>
        <label>{minimumLabel}<input inputMode="decimal" aria-label={minimumLabel} maxLength={18} value={draft.manual} onChange={e => onDraft({ manual: e.target.value })}/>
          <small>Kalau diketik, angka ini dipakai dan menggantikan hitungan. Kosong = pakai hitungan. 0 = tidak pernah diingatkan.</small></label>
        {reason}{check}{actions}
      </fieldset>}
    </form> : null}
  </article>
}
/** What an accessory save keeps as its minimum, in plain words (the list is read again right after). */
function accessorySavedText(payload: MaterialPayload, unit: string | null): string {
  if (payload.manual_point !== null) return `batas minimum diketik ${materialQty(payload.manual_point, unit)}${Number(payload.manual_point) === 0 ? ' (tidak pernah diingatkan)' : ''}`
  const usage = payload.usage_month_qty ?? null, lead = payload.lead_days, buffer = payload.buffer_days ?? null
  return usage !== null && lead !== null && buffer !== null ? `batas minimum dari hitungan ${materialQty(accessoryEstimatePoint(usage, lead, buffer), unit)}`
    : 'batas minimum belum ada (isian hitungan belum lengkap), jadi tidak diingatkan'
}
