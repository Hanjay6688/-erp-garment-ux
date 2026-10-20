import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { isUnansweredFailure } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import { REASON_MAX, REORDER_PAGE, REORDER_QUERY_MAX, formatReorderUpTo2, formatReorderWhole, parseFgReorderRefresh, servicePercent, type ReorderFilter,
  type ServiceLevel } from './fgReorderContract'
import {
  materialBasisText, materialChanged, materialDraftOf, materialErrorText, materialFormulaLines, materialPayload, materialProblem, materialQty, materialStatus,
  materialReorderVisible, materialWriteErrorText, parseMaterialSaveResult, parseMaterialWorkspace, type MaterialDraft, type MaterialQuery, type MaterialRow, type MaterialType,
  type MaterialWorkspace,
} from './materialReorderContract'
import './procurement-connected.css'
import './fg-reorder.css'

// SS-2 (fabric) and SS-3 (accessories), owner D17-9: "Titik pesan ulang" of every active fabric or accessory, one component on
// Gudang › Bahan & Roll and Master Data › Kain & Benchmark (FABRIC), Gudang › Aksesori and Master Data › Aksesori & Harga
// Mandor (ACCESSORY). It reads erp_cp7_get_material_reorder_v1 with the server's own permissions (it shows nothing to an
// account the server would refuse), "Hitung sekarang" refreshes, and Owner/Admin (can_manage from the server) set the lama
// kirim of a material and, for an accessory, its manual number. As on Ringkasan Barang Jadi: every read is sequenced so the
// latest question wins, and a write keeps one request id per attempt in memory (an unanswered attempt is sent again with it).
type Note = { tone: 'ok' | 'bad'; text: string }
type Pending = { id: string; fingerprint: string }
type Editing = MaterialDraft & { materialId: string }
const words: Record<MaterialType, { label: string; noun: string; manualFilter: string; alert: string }> = {
  FABRIC: { label: 'Titik pesan ulang kain', noun: 'kain', manualFilter: 'Pakai minimum', alert: 'Stok kain menipis' },
  ACCESSORY: { label: 'Titik pesan ulang aksesori', noun: 'aksesori', manualFilter: 'Angka manual', alert: 'Stok aksesori menipis' },
}

export default function MaterialReorderPanel({ materialType }: { materialType: MaterialType }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !materialReorderVisible(materialType, identity.permissions)) return null
  return <Panel materialType={materialType} key={`${materialType}:${runtime.projectRef}:${identity.profile.id}:${identity.permissions.join('|')}`}/>
}

function Panel({ materialType }: { materialType: MaterialType }) {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi bahan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), say = words[materialType], fabric = materialType === 'FABRIC'
  const serial = useRef(0), requested = useRef<MaterialQuery>({ material_type: materialType, q: '', filter: 'ALL', offset: 0, limit: REORDER_PAGE })
  const [data, setData] = useState<MaterialWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [filter, setFilter] = useState<ReorderFilter>('ALL'), [search, setSearch] = useState('')
  const [writing, setWriting] = useState<string | null>(null), [notes, setNotes] = useState<Record<string, Note>>({})
  const [editing, setEditing] = useState<Editing | null>(null)
  const pending = useRef(new Map<string, Pending>())

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
      setData(parseMaterialWorkspace(reply.data, query))
    } catch (e) {
      if (n === serial.current) { setData(null); setError(materialErrorText(e, materialType)) }
    } finally { if (n === serial.current) setBusy(false) }
  }, [client, materialType])
  useEffect(() => { void load() }, [load])
  useEffect(() => () => { ++serial.current }, [])

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

  const save = async (r: MaterialRow) => {
    if (locked || !editing || editing.materialId !== r.materialId || materialProblem(materialType, editing) || !materialChanged(materialType, r, editing)) return
    const payload = materialPayload(r, materialType, editing), fingerprint = JSON.stringify(payload)
    const held = pending.current.get(r.materialId), request = held && held.fingerprint === fingerprint ? held.id : crypto.randomUUID()
    pending.current.set(r.materialId, { id: request, fingerprint })
    setWriting(r.materialId); note(r.materialId, null)
    try {
      const reply = await client.rpc('erp_cp7_save_material_reorder_v1', { p_payload: payload, p_request: request })
      if (reply.error) throw reply.error
      const saved = parseMaterialSaveResult(reply.data, payload, materialType)
      pending.current.delete(r.materialId)
      const parts = [payload.lead_days === null ? 'lama kirim kosong' : `lama kirim ${formatReorderUpTo2(payload.lead_days)} hari`]
      if (!fabric) parts.push(payload.manual_point === null ? 'tanpa angka manual (pakai rumus)'
        : `angka manual ${materialQty(payload.manual_point, r.unitCode)}${Number(payload.manual_point) === 0 ? ' (tidak pernah diingatkan)' : ''}`)
      note(r.materialId, { tone: 'ok', text: `Tersimpan (revisi ${formatReorderWhole(saved.revision)}): ${parts.join(', ')}.`
        + (saved.replay ? ' Permintaan ini ternyata sudah tersimpan sebelumnya.' : '') })
      setEditing(null); setWriting(null); await load()
    } catch (e) {
      if (!isUnansweredFailure(e)) pending.current.delete(r.materialId)
      note(r.materialId, { tone: 'bad', text: materialWriteErrorText(e, materialType, 'SAVE') })
    } finally { setWriting(null) }
  }
  const noteView = (scope: string) => {
    const n = notes[scope]
    return n ? <p className={`cfr-note ${n.tone}`} role={n.tone === 'bad' ? 'alert' : 'status'}>{n.text}</p> : null
  }

  const run = data?.run ?? null, windowDays = run?.windowDays ?? data?.settings.windowDays ?? 30
  const level = run?.serviceLevel ?? data?.settings.serviceLevel ?? '0.95', counts = data?.counts, page = data?.page
  const filterLabel: Record<ReorderFilter, string> = { ALL: 'Semua', AT_OR_BELOW: 'Menipis', MANUAL: say.manualFilter, NOT_ENOUGH_DATA: 'Belum cukup data' }
  const countOf: Record<ReorderFilter, number | undefined> = { ALL: counts?.items, AT_OR_BELOW: counts?.atOrBelow, MANUAL: counts?.manual, NOT_ENOUGH_DATA: counts?.notEnoughData }

  return <section className="cproc cfr" aria-label={say.label}><div className="panel cfr-panel">
    <header className="cfr-head">
      <div>
        <div className="eyebrow">{fabric ? 'KAIN' : 'AKSESORI'} · PENGINGAT STOK</div>
        <h2>{say.label} (safety stock)</h2>
        <p>Titik pesan ulang = rata-rata pakai per hari × lama kirim + cadangan. Dihitung dari pemakaian yang sudah diposting {formatReorderWhole(windowDays)} hari
          terakhir (hari tanpa stok tidak dihitung) dengan tingkat layanan {servicePercent(level)}%, dalam satuan bahannya.</p>
        <p>{fabric ? 'Pemakaian kain = dikeluarkan untuk potong dikurangi sisa yang kembali, pemakaian pabrik, dan bahan ke mandor. Kain yang sudah dipesan '
          + '(PO terbuka) ikut dihitung. Kain yang punya angka minimum di Master Data › Kain & Benchmark memakai minimum itu.'
          : 'Pemakaian aksesori = nota mandor dan pemakaian pabrik. Stok di pos servis, area periksa dan area rusak tidak dihitung sebagai stok.'}
          {' '}Lama kirim (hari) dari supplier diisi per {say.noun} oleh Owner atau Admin, karena ERP belum mencatatnya. Kalau sisa{fabric ? ' ditambah yang dipesan' : ''} sudah
          sama atau di bawah titik ini, muncul pengingat "{say.alert}" di Reminder › Pengingat sistem, diteruskan ke WhatsApp Bos bila Sambungan WhatsApp menyala.
          Tingkat layanan dan jumlah hari diatur di Gudang › Ringkasan Barang Jadi.</p>
        {data ? <p className="cfr-run">{run ? <>Dihitung {formatCp6WibDateTime(run.computedAt)} (pemakaian {formatWaDay(run.windowFrom)} sampai {formatWaDay(run.windowThrough)}).</>
          : <>Belum pernah dihitung. Server menghitungnya tiap menit sesudah pengingat WhatsApp diatur (Owner menyimpan pengaturan di Reminder › Sambungan
            WhatsApp satu kali), atau tekan "Hitung sekarang".</>}</p> : null}
      </div>
      <div className="cfr-actions">
        <button type="button" className="primary-btn" disabled={locked} onClick={() => { void refresh() }}>Hitung sekarang</button>
        <button type="button" aria-label={`Muat ulang ${say.label.toLowerCase()}`} disabled={writing !== null} onClick={reload}>Muat ulang</button>
      </div>
    </header>
    {noteView('REFRESH')}
    {error ? <p className="cfr-note bad" role="alert">{error}</p> : null}
    <div className="cfr-filters" role="group" aria-label={`Saring ${say.label.toLowerCase()}`}>
      {(Object.keys(filterLabel) as ReorderFilter[]).map(f => { const n = countOf[f]; return <button type="button" key={f} aria-pressed={filter === f}
        className={filter === f ? 'active' : ''} disabled={writing !== null} onClick={() => { setFilter(f); ask({ filter: f, offset: 0 }) }}>
        {filterLabel[f]}{n === undefined ? '' : ` (${formatReorderWhole(n)})`}</button> })}
    </div>
    <form className="cfr-search" onSubmit={e => { e.preventDefault(); ask({ q: search.trim(), offset: 0 }) }}>
      <label>Cari SKU atau nama {say.noun}<input aria-label={`Cari ${say.noun} untuk titik pesan ulang`} maxLength={REORDER_QUERY_MAX} value={search}
        onChange={e => setSearch(e.target.value)}/></label>
      <button type="submit" disabled={writing !== null}>Cari</button>
      <button type="button" disabled={writing !== null || (search === '' && requested.current.q === '')}
        onClick={() => { setSearch(''); ask({ q: '', offset: 0 }) }}>Kosongkan pencarian</button>
    </form>
    {busy ? <p role="status">Memuat {say.label.toLowerCase()}…</p> : null}
    {data && page ? <>
      {!page.rows.length ? <p className="cfr-none">Tidak ada {say.noun} yang cocok.</p> : null}
      <div className="cfr-list">{page.rows.map(r => <Row key={r.materialId} r={r} type={materialType} windowDays={windowDays} level={level} canManage={data.canManage}
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
  const unit = r.unitCode ? ` ${r.unitCode}` : ''
  const problem = draft ? materialProblem(type, draft) : '', changed = draft ? materialChanged(type, r, draft) : false
  return <article className="cfr-row" aria-label={`Titik pesan ulang ${r.name} (SKU ${r.sku})`} data-material-id={r.materialId}>
    <header><div><h3>{r.name}</h3><small>SKU {r.sku}</small></div><span className={`cfr-chip ${status.tone}`}>{status.label}</span></header>
    <dl>
      <div><dt>Sisa</dt><dd data-cmr="free">{q(r.freeQty)}</dd></div>
      {fabric ? <div><dt>Dipesan</dt><dd data-cmr="ordered">{q(r.onOrderQty)}</dd></div> : null}
      <div><dt>Pakai/hari</dt><dd data-cmr="daily">{r.dailyMean === null ? 'belum ada' : `${formatReorderUpTo2(r.dailyMean)}${unit}`}</dd></div>
      <div><dt>Lama kirim (hari)</dt><dd data-cmr="lead">{r.leadDays === null ? 'belum diisi' : formatReorderUpTo2(r.leadDays)}</dd></div>
      <div><dt>Titik pesan ulang</dt><dd data-cmr="point">{r.point === null ? 'belum ada' : q(r.point)}</dd></div>
      <div><dt>Dasar</dt><dd data-cmr="basis">{materialBasisText(r, windowDays)}</dd></div>
    </dl>
    <details className="cfr-formula"><summary>Rincian rumus</summary><ul>{materialFormulaLines(r, windowDays, level).map(line => <li key={line}>{line}</li>)}</ul></details>
    {note}
    {canManage && !draft ? <button type="button" disabled={locked} onClick={onOpen}>{fabric ? 'Atur lama kirim' : 'Atur lama kirim & angka manual'}</button> : null}
    {canManage && draft ? <form className="cfr-manual" onSubmit={e => { e.preventDefault(); onSave() }}>
      <fieldset disabled={locked}><legend>{fabric ? 'Lama kirim' : 'Lama kirim dan angka manual'}</legend>
        <label>Lama kirim (hari)<input inputMode="decimal" aria-label="Lama kirim (hari)" maxLength={6} value={draft.lead} onChange={e => onDraft({ lead: e.target.value })}/>
          <small>Berapa hari dari pesan ke supplier sampai {fabric ? 'kain' : 'aksesori'} diterima. Kosong = rumus tidak dihitung.</small></label>
        {fabric ? <p className="cfr-source">Angka minimum diatur di Master Data › Kain & Benchmark.</p>
          : <label>Angka manual{r.unitCode ? ` (${r.unitCode})` : ''}<input inputMode="decimal" aria-label="Angka manual" maxLength={18} value={draft.manual}
            onChange={e => onDraft({ manual: e.target.value })}/><small>0 = tidak pernah diingatkan, kosong = pakai rumus.</small></label>}
        <label>Alasan<input aria-label="Alasan perubahan bahan" maxLength={REASON_MAX} value={draft.reason} onChange={e => onDraft({ reason: e.target.value })}/></label>
        {!changed ? <p className="cfr-none">Belum ada yang diubah.</p> : problem ? <p className="cfr-problem">{problem}</p> : null}
        <div className="cfr-actions">
          <button type="submit" className="primary-btn" disabled={locked || problem !== '' || !changed}>{writing ? 'Menyimpan…' : 'Simpan'}</button>
          <button type="button" disabled={writing} onClick={onClose}>Batal</button>
        </div>
      </fieldset>
    </form> : null}
  </article>
}
