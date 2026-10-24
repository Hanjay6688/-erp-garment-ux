import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { isUnansweredFailure } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import TargetDemandDetails from './TargetDemandDetails'
import {
  MANUAL_POINT_MAX, REASON_MAX, REORDER_PAGE, REORDER_QUERY_MAX, WINDOW_MAX, WINDOW_MIN, fgReorderErrorText, fgReorderWriteErrorText, formatReorderQty,
  formatReorderWhole, manualPayload, manualProblem, parseFgReorderManualResult, parseFgReorderRefresh, parseFgReorderSettingsResult, parseFgReorderWorkspace,
  reorderChip, reorderFormulaLines, reorderReasonText, reorderSourceText, reorderWipNote, reorderWipText, serviceLevels, servicePercent, settingsChanged,
  settingsDraftOf, settingsPayload, settingsProblem, type ReorderFilter, type ReorderQuery, type ReorderRow, type ReorderWorkspace, type ServiceLevel,
  type SettingsDraft,
} from './fgReorderContract'
import './procurement-connected.css'
import './fg-reorder.css'

// SS-1 (owner D17-8, D17-9): the reorder point of every finished good on Ringkasan Barang Jadi. One read facade
// (erp_cp7_get_fg_reorder_v1, permission warehouse.fg.view), "Hitung sekarang" (refresh), and for Owner/Admin only
// (can_manage from the server) a manual point per item and the formula settings. Every read carries a sequence number so a
// late answer never replaces a newer one. A write keeps one request id per attempt in memory: an unanswered attempt is sent
// again with the same id (the server answers it once), anything else starts a new one. Nothing is kept in the browser.
type Note = { tone: 'ok' | 'bad'; text: string }
type Pending = { id: string; fingerprint: string }
type ManualDraft = { rootId: string; qty: string; reason: string }
type Base = { revision: number; draft: SettingsDraft }
const filterLabel: Record<ReorderFilter, string> = { ALL: 'Semua', AT_OR_BELOW: 'Di bawah titik pesan ulang', MANUAL: 'Angka manual', NOT_ENOUGH_DATA: 'Belum cukup data' }
const levelHint: Record<ServiceLevel, string> = { '0.90': 'cadangan paling sedikit', '0.95': 'bawaan', '0.99': 'cadangan paling banyak' }
const rowLabel = (r: ReorderRow) => `${r.productName}${r.sizeCode ? ` ${r.sizeCode}` : ''}`
const sameDraft = (a: SettingsDraft, b: SettingsDraft) => a.serviceLevel === b.serviceLevel && a.windowDays.trim() === b.windowDays.trim() && a.reason.trim() === b.reason.trim()

export default function FgReorderPanel() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi barang jadi belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const serial = useRef(0), requested = useRef<ReorderQuery>({ q: '', filter: 'ALL', offset: 0, limit: REORDER_PAGE })
  const [data, setData] = useState<ReorderWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [filter, setFilter] = useState<ReorderFilter>('ALL'), [search, setSearch] = useState('')
  const [writing, setWriting] = useState<string | null>(null), [notes, setNotes] = useState<Record<string, Note>>({})
  const [manual, setManual] = useState<ManualDraft | null>(null)
  const [draft, setDraftState] = useState<SettingsDraft | null>(null), [base, setBaseState] = useState<Base | null>(null)
  const draftRef = useRef<SettingsDraft | null>(null), baseRef = useRef<Base | null>(null)
  const pendingManual = useRef(new Map<string, Pending>()), pendingSettings = useRef<Pending | null>(null)

  const note = (scope: string, value: Note | null) => setNotes(current => {
    const next = { ...current }
    if (value) next[scope] = value; else delete next[scope]
    return next
  })
  // reset: the settings form goes back to what the server holds; otherwise only an untouched form follows the server, so a
  // reload never drops what the owner is typing, and a form kept over a newer revision is refused as stale by the server.
  const load = useCallback(async (reset = false) => {
    const query = { ...requested.current }, n = ++serial.current
    setBusy(true); setError(''); setData(null)
    try {
      const reply = await client.rpc('erp_cp7_get_fg_reorder_v1', { p_query: query })
      if (n !== serial.current) return
      if (reply.error) throw reply.error
      const parsed = parseFgReorderWorkspace(reply.data, query), fresh = settingsDraftOf(parsed.settings)
      if (reset || !draftRef.current || !baseRef.current || sameDraft(draftRef.current, baseRef.current.draft)) {
        draftRef.current = fresh; setDraftState(fresh)
        baseRef.current = { revision: parsed.settings.revision, draft: fresh }; setBaseState(baseRef.current)
      }
      setData(parsed)
    } catch (e) {
      if (n === serial.current) { setData(null); setError(fgReorderErrorText(e)) }
    } finally { if (n === serial.current) setBusy(false) }
  }, [client])
  useEffect(() => { void load(true) }, [load])
  useEffect(() => () => { ++serial.current }, [])

  const locked = busy || writing !== null || !data
  // A newer question may start while a read is under way (filter, search): the sequence number keeps only its answer.
  const ask = (next: Partial<ReorderQuery>) => { requested.current = { ...requested.current, ...next }; void load() }
  const reload = () => { setNotes({}); void load() }

  const refresh = async () => {
    if (locked) return
    setWriting('REFRESH'); note('REFRESH', null)
    try {
      const reply = await client.rpc('erp_cp7_refresh_fg_reorder_v1')
      if (reply.error) throw reply.error
      const r = parseFgReorderRefresh(reply.data)
      note('REFRESH', { tone: 'ok', text: `Selesai dihitung ${formatCp6WibDateTime(r.computedAt)}: ${formatReorderWhole(r.items)} barang jadi, `
        + `${formatReorderWhole(r.atOrBelow)} perlu produksi.` })
      setWriting(null); await load()
    } catch (e) { note('REFRESH', { tone: 'bad', text: fgReorderWriteErrorText(e, 'REFRESH') }) } finally { setWriting(null) }
  }

  const saveManual = async (r: ReorderRow, clear: boolean) => {
    if (locked || !manual || manual.rootId !== r.rootId || manualProblem(clear ? null : manual.qty, manual.reason)) return
    const payload = manualPayload(r, clear ? null : manual.qty, manual.reason), fingerprint = JSON.stringify(payload)
    const held = pendingManual.current.get(r.rootId), request = held && held.fingerprint === fingerprint ? held.id : crypto.randomUUID()
    pendingManual.current.set(r.rootId, { id: request, fingerprint })
    setWriting(r.rootId); note(r.rootId, null)
    try {
      const reply = await client.rpc('erp_cp7_save_fg_reorder_manual_v1', { p_payload: payload, p_request: request })
      if (reply.error) throw reply.error
      const saved = parseFgReorderManualResult(reply.data, payload)
      pendingManual.current.delete(r.rootId)
      const again = saved.replay ? ' Permintaan ini ternyata sudah tersimpan sebelumnya.' : ''
      note(r.rootId, { tone: 'ok', text: saved.reorderPointPcs === null ? `Angka manual dihapus; titik pesan ulang kembali memakai rumus.${again}`
        : `Angka manual tersimpan: ${formatReorderWhole(saved.reorderPointPcs)} pcs${saved.reorderPointPcs === 0 ? ' (peringatan barang ini dimatikan)' : ''}.${again}` })
      setManual(null); setWriting(null); await load()
    } catch (e) {
      if (!isUnansweredFailure(e)) pendingManual.current.delete(r.rootId)
      note(r.rootId, { tone: 'bad', text: fgReorderWriteErrorText(e, 'MANUAL') })
    } finally { setWriting(null) }
  }

  const saveSettings = async () => {
    if (locked || !draft || !base || settingsProblem(draft) || !settingsChanged(draft, base.draft)) return
    const payload = settingsPayload(draft, base.revision), fingerprint = JSON.stringify(payload), held = pendingSettings.current
    const request = held && held.fingerprint === fingerprint ? held.id : crypto.randomUUID()
    pendingSettings.current = { id: request, fingerprint }
    setWriting('SETTINGS'); note('SETTINGS', null)
    try {
      const reply = await client.rpc('erp_cp7_save_stock_formula_settings_v1', { p_payload: payload, p_request: request })
      if (reply.error) throw reply.error
      const saved = parseFgReorderSettingsResult(reply.data, payload)
      pendingSettings.current = null
      note('SETTINGS', { tone: 'ok', text: `Pengaturan rumus tersimpan (revisi ${formatReorderWhole(saved.settings.revision)}); titik pesan ulang dihitung ulang.`
        + (saved.replay ? ' Permintaan ini ternyata sudah tersimpan sebelumnya.' : '') })
      setWriting(null); await load(true)
    } catch (e) {
      if (!isUnansweredFailure(e)) pendingSettings.current = null
      note('SETTINGS', { tone: 'bad', text: fgReorderWriteErrorText(e, 'SETTINGS') })
    } finally { setWriting(null) }
  }
  const setDraft = (next: Partial<SettingsDraft>) => {
    if (!draftRef.current) return
    draftRef.current = { ...draftRef.current, ...next }; setDraftState(draftRef.current); note('SETTINGS', null)
  }
  const noteView = (scope: string) => {
    const n = notes[scope]
    return n ? <p className={`cfr-note ${n.tone}`} role={n.tone === 'bad' ? 'alert' : 'status'}>{n.text}</p> : null
  }

  const run = data?.run ?? null, windowDays = run?.windowDays ?? data?.settings.windowDays ?? 30
  const native = data?.contractVersion === 'cp7.fg-reorder.v2'
  const level = run?.serviceLevel ?? data?.settings.serviceLevel ?? '0.95'
  const counts = data?.counts, page = data?.page
  const countOf: Record<ReorderFilter, number | undefined> = { ALL: counts?.items, AT_OR_BELOW: counts?.atOrBelow, MANUAL: counts?.manual, NOT_ENOUGH_DATA: counts?.notEnoughData }

  return <section className="cproc cfr" aria-label="Titik pesan ulang"><div className="panel cfr-panel">
    <header className="cfr-head">
      <div>
        <div className="eyebrow">GUDANG · BARANG JADI · PENGINGAT STOK</div>
        <h2>Titik pesan ulang (safety stock)</h2>
        {native ? <p>Titik pesan ulang menentukan kapan perlu produksi. Target jumlah produksi dihitung terpisah oleh mesin rencana yang sama, mengikuti profil produk atau pengaturan umum di bawah.
          Stok bebas dan perkiraan barang baik yang tiba tepat waktu dibandingkan dengan titik pesan ulang. Kandidat produksi ditampilkan sebagai kemungkinan tambahan dan perlu dikonfirmasi.
          Pengingat stok diteruskan ke WhatsApp Bos bila Sambungan WhatsApp menyala.</p> : <p>Titik pesan ulang = rata-rata jual per hari × lama produksi + cadangan. Dihitung dari penjualan yang sudah diposting {formatReorderWhole(windowDays)} hari
          terakhir (hari stok kosong tidak dihitung) dengan tingkat layanan {servicePercent(level)}%. Ini aturan umum; pilihan cadangan dan tingkat layanan khusus produk mengikuti profil perencanaan. Kalau stok bebas ditambah yang sedang diproduksi sudah sama atau
          di bawah angka ini, muncul pengingat "Stok barang jadi menipis" di Reminder › Pengingat sistem, dan diteruskan ke WhatsApp Bos bila Sambungan WhatsApp menyala.</p>}
        {data ? <p className="cfr-run">{run ? <>Dihitung {formatCp6WibDateTime(run.computedAt)} (penjualan {formatWaDay(run.windowFrom)} sampai {formatWaDay(run.windowThrough)}).</>
          : <>Belum pernah dihitung. Server menghitungnya tiap menit sesudah pengingat WhatsApp diatur (Owner menyimpan pengaturan di Reminder › Sambungan WhatsApp
            satu kali), atau tekan "Hitung sekarang".</>}</p> : null}
        {run && data && run.settingsRevision !== data.settings.revision ? <p className="cfr-run">Pengaturan rumus terbaru (revisi {formatReorderWhole(data.settings.revision)}) dipakai mulai
          hitungan berikutnya.</p> : null}
      </div>
      <div className="cfr-actions">
        <button type="button" className="primary-btn" disabled={locked} onClick={() => { void refresh() }}>Hitung sekarang</button>
        <button type="button" aria-label="Muat ulang titik pesan ulang" disabled={writing !== null} onClick={reload}>Muat ulang</button>
      </div>
    </header>
    {noteView('REFRESH')}
    {error ? <p className="cfr-note bad" role="alert">{error}</p> : null}
    <div className="cfr-filters" role="group" aria-label="Saring titik pesan ulang">
      {(Object.keys(filterLabel) as ReorderFilter[]).map(f => { const n = countOf[f]; return <button type="button" key={f} aria-pressed={filter === f}
        className={filter === f ? 'active' : ''} disabled={writing !== null} onClick={() => { setFilter(f); ask({ filter: f, offset: 0 }) }}>
        {filterLabel[f]}{n === undefined ? '' : ` (${formatReorderWhole(n)})`}</button> })}
    </div>
    <form className="cfr-search" onSubmit={e => { e.preventDefault(); ask({ q: search.trim(), offset: 0 }) }}>
      <label>Cari SKU atau nama barang<input aria-label="Cari barang untuk titik pesan ulang" maxLength={REORDER_QUERY_MAX} value={search} onChange={e => setSearch(e.target.value)}/></label>
      <button type="submit" disabled={writing !== null}>Cari</button>
      <button type="button" disabled={writing !== null || (search === '' && requested.current.q === '')}
        onClick={() => { setSearch(''); ask({ q: '', offset: 0 }) }}>Kosongkan pencarian</button>
    </form>
    {busy ? <p role="status">Memuat titik pesan ulang…</p> : null}
    {data && page ? <>
      {!page.rows.length ? <p className="cfr-none">Tidak ada barang jadi yang cocok.</p> : null}
      <div className="cfr-list">{page.rows.map(r => <Row key={r.targetKey} r={r} windowDays={windowDays} level={level} canManage={data.canManage} locked={locked}
        writing={writing === r.rootId} draft={manual?.rootId === r.rootId ? manual : null} note={noteView(r.rootId)}
        onOpen={() => { setManual({ rootId: r.rootId, qty: String(r.manualPoint ?? r.formulaPoint ?? ''), reason: '' }); note(r.rootId, null) }}
        onClose={() => setManual(null)} onDraft={next => setManual(current => current && current.rootId === r.rootId ? { ...current, ...next } : current)}
        onSave={clear => { void saveManual(r, clear) }}/>)}</div>
      <div className="cproc-pagination"><span>{formatReorderWhole(page.rows.length)} barang · total {page.total}</span>
        <button type="button" disabled={locked || !page.offset} onClick={() => ask({ offset: Math.max(0, page.offset - REORDER_PAGE) })}>Barang sebelumnya</button>
        <button type="button" disabled={locked || page.nextOffset === null} onClick={() => ask({ offset: page.nextOffset ?? 0 })}>Barang berikutnya</button></div>
      {data.canManage && draft && base ? <Settings data={data} draft={draft} base={base} locked={locked} note={noteView('SETTINGS')} onDraft={setDraft}
        onSave={() => { void saveSettings() }}/> : null}
    </> : null}
  </div></section>
}

function Row({ r, windowDays, level, canManage, locked, writing, draft, note, onOpen, onClose, onDraft, onSave }: {
  r: ReorderRow; windowDays: number; level: ServiceLevel; canManage: boolean; locked: boolean; writing: boolean; draft: ManualDraft | null
  note: ReactNode; onOpen: () => void; onClose: () => void; onDraft: (next: Partial<ManualDraft>) => void; onSave: (clear: boolean) => void
}) {
  const chip = reorderChip(r, windowDays), why = reorderReasonText(r), source = reorderSourceText(r), wipNote = reorderWipNote(r)
  const problem = draft ? manualProblem(draft.qty, draft.reason) : '', clearProblem = draft ? manualProblem(null, draft.reason) : ''
  return <article className="cfr-row" aria-label={`Titik pesan ulang ${rowLabel(r)} (SKU ${r.sku})`} data-target-key={r.targetKey}>
    <header><div><h3>{rowLabel(r)}</h3><small>SKU {r.sku}</small></div><span className={`cfr-chip ${chip.tone}`}>{chip.label}</span></header>
    <dl>
      <div><dt>Stok bebas</dt><dd data-cfr="free">{formatReorderQty(r.freePcs)} pcs</dd></div>
      <div><dt>{r.projection ? 'Perkiraan tepat waktu' : 'Sedang diproduksi'}</dt><dd data-cfr="wip">{reorderWipText(r)}</dd>{r.wipReadAt ? <small>{r.projection ? 'analisis' : 'dibaca'} {formatCp6WibDateTime(r.wipReadAt)}</small> : null}</div>
      <div><dt>Titik pesan ulang</dt><dd data-cfr="point">{r.point === null ? 'belum ada' : `${formatReorderWhole(r.point)} pcs`}</dd></div>
    </dl>
    {why ? <p className="cfr-why">{why}</p> : null}
    {wipNote ? <p className="cfr-why">{wipNote}</p> : null}
    {source ? <p className="cfr-source">{source}</p> : null}
    {r.projection ? <Projection r={r}/> : null}
    <details className="cfr-formula"><summary>Rincian rumus</summary><ul>{reorderFormulaLines(r, windowDays, level).map(line => <li key={line}>{line}</li>)}</ul></details>
    {note}
    {canManage && !draft ? <button type="button" disabled={locked} onClick={onOpen}>Atur angka manual</button> : null}
    {canManage && draft ? <form className="cfr-manual" onSubmit={e => { e.preventDefault(); onSave(false) }}>
      <fieldset disabled={locked}><legend>Angka manual</legend>
        <p>Angka manual menggantikan titik pesan ulang untuk barang ini sampai dihapus.{r.projection ? ' Target jumlah produksi tetap mengikuti rencana.' : ''} Isi 0 bila barang ini tidak perlu diingatkan.</p>
        <label>Titik pesan ulang manual (pcs)<input type="number" inputMode="numeric" min={0} max={MANUAL_POINT_MAX} step={1} aria-label="Titik pesan ulang manual (pcs)"
          value={draft.qty} onChange={e => onDraft({ qty: e.target.value })}/></label>
        <label>Alasan<input aria-label="Alasan angka manual" maxLength={REASON_MAX} value={draft.reason} onChange={e => onDraft({ reason: e.target.value })}/></label>
        {problem ? <p className="cfr-problem">{problem}</p> : null}
        <div className="cfr-actions">
          <button type="submit" className="primary-btn" disabled={locked || problem !== ''}>{writing ? 'Menyimpan…' : 'Simpan angka manual'}</button>
          {r.manualPoint !== null ? <button type="button" disabled={locked || clearProblem !== ''} onClick={() => onSave(true)}>Hapus angka manual</button> : null}
          <button type="button" disabled={writing} onClick={onClose}>Batal</button>
        </div>
      </fieldset>
    </form> : null}
  </article>
}

function Projection({ r }: { r: ReorderRow }) {
  const p = r.projection
  if (!p) return null
  const qty = (v: string | null) => v === null ? 'belum diketahui' : `${formatReorderQty(v)} pcs`
  return <div className="cfr-source">
    {p.targetDemand ? <TargetDemandDetails value={p.targetDemand}/> : null}
    <p>Aturan dari {p.thresholdSource === 'PLANNING_PROFILE' ? 'profil perencanaan produk' : p.thresholdSource === 'PROFILE_UNAVAILABLE'
      ? 'profil produk yang perlu ditinjau ulang' : 'riwayat stok tersedia dan pengaturan umum'}.
      {' '}Stok diperiksa {formatCp6WibDateTime(p.stockCheckedAt)}; aturan diperiksa {formatCp6WibDateTime(p.thresholdCheckedAt)}.</p>
    {p.leadDeadline ? <p>Perkiraan tepat waktu dihitung sampai {formatCp6WibDateTime(p.leadDeadline)}. Target rencana sampai {formatCp6WibDateTime(p.targetDeadline ?? p.leadDeadline)}.</p> : null}
    <p>Target rencana: {qty(p.targetPcs)}. Tambahan produksi dari stok dan suplai terarah: {qty(p.productionBasePcs)}.</p>
    {p.candidatePcs !== null ? <p>Kandidat tambahan: {qty(p.candidatePcs)}; tambahan produksi bila kandidat dipakai: {qty(p.productionConditionalPcs)}.
      {' '}Kandidat perlu dikonfirmasi; peringatan tetap mengikuti stok dan suplai terarah.</p> : null}
    {p.manualState === 'STALE_IDENTITY' && p.manualReference?.point !== null ? <p>Referensi angka manual sebelumnya: {qty(p.manualReference?.point ?? null)}. Angka ini belum aktif untuk versi barang sekarang.</p> : null}
  </div>
}

function Settings({ data, draft, base, locked, note, onDraft, onSave }: {
  data: ReorderWorkspace; draft: SettingsDraft; base: Base; locked: boolean; note: ReactNode; onDraft: (next: Partial<SettingsDraft>) => void; onSave: () => void
}) {
  const s = data.settings, changed = settingsChanged(draft, base.draft), problem = changed ? settingsProblem(draft) : ''
  return <section className="cfr-settings" aria-label="Pengaturan rumus titik pesan ulang">
    <h3>Pengaturan rumus (Owner dan Admin)</h3>
    <p>Berlaku untuk semua barang jadi. {s.revision === 0 ? 'Belum pernah diubah: memakai bawaan 95% dan 30 hari.'
      : `Revisi ${formatReorderWhole(s.revision)}, disimpan ${formatCp6WibDateTime(s.savedAt ?? '')}${s.reason ? `: ${s.reason}` : ''}.`}</p>
    <p>Tingkat layanan = seberapa sering stok diharapkan masih cukup sampai produksi berikutnya selesai. Makin tinggi, makin besar cadangannya.</p>
    {s.revision !== base.revision ? <p className="cfr-note bad" role="note">Pengaturan di server sudah berubah (revisi {formatReorderWhole(s.revision)}). Tekan "Muat ulang"
      untuk melihatnya; isian di bawah yang belum disimpan akan diganti.</p> : null}
    <form onSubmit={e => { e.preventDefault(); onSave() }}><fieldset disabled={locked}><legend className="cproc-sr">Pengaturan rumus</legend>
      <div className="cfr-grid">
        <label>Tingkat layanan<select aria-label="Tingkat layanan" value={draft.serviceLevel} onChange={e => onDraft({ serviceLevel: e.target.value as ServiceLevel })}>
          {serviceLevels.map(l => <option key={l} value={l}>{servicePercent(l)}% ({levelHint[l]})</option>)}</select></label>
        <label>Jumlah hari penjualan yang dibaca<input type="number" inputMode="numeric" min={WINDOW_MIN} max={WINDOW_MAX} step={1} aria-label="Jumlah hari penjualan"
          value={draft.windowDays} onChange={e => onDraft({ windowDays: e.target.value })}/></label>
        <label className="cfr-wide">Alasan perubahan<input aria-label="Alasan perubahan pengaturan rumus" maxLength={REASON_MAX} value={draft.reason}
          onChange={e => onDraft({ reason: e.target.value })}/></label>
      </div>
      {problem ? <p className="cfr-problem">{problem}</p> : !changed ? <p className="cfr-none">Belum ada yang diubah.</p> : null}
      <div className="cfr-actions"><button type="submit" className="primary-btn" disabled={locked || !changed || problem !== ''}>Simpan pengaturan rumus</button></div>
    </fieldset></form>
    {note}
  </section>
}
