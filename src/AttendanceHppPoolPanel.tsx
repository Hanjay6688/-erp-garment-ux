import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission, SENSITIVE_ACTION_PERMISSION } from './auth/accessCatalog'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {
  hppPoolActionPayload, hppPoolBlockerText, hppPoolCreatePayload, hppPoolDay, hppPoolPcs, hppPoolPeriodText, hppPoolRefusalText, hppPoolRupiah,
  hppPoolStatusText, parseHppPoolOutcome, parseHppPoolWorkspace, type HppPool, type HppPoolOutcome, type HppPoolQuery, type HppPoolWorkspace,
} from './hppPoolContract'
import type { ProductionEnvelope } from './productionRecovery'
import './hpp-pool.css'

// R3-04 (Sol KNOWN-R2-POOL-UI, Astra ASTRA-C17-07; owner D16-1 "selesain biar gausa sembunyiin"): the attendance HPP pool
// on the connected "HPP & Rekalkulasi" page. Pratinjau shows the Native numbers of one exact payroll period or the reason it
// cannot be made; "Buat draf pool", "Aktifkan" and "Batalkan" go through scripts/cp7-src/hpp-pool/pool.sql to the Native
// writers, each with a reason, a review and one request UUID per attempt kept by the shared recovery envelope. A cancelled
// pool offers "Buat pool pengganti" (the Native correction_of_pool_id). Only Owner/Admin see the pool; the actions also need
// the HPP "Rekalkulasi" right, as the server checks again. Owner rule D18b: the page reloads its other writers after a pool
// commit (onCommitted) and passes `refresh` up by one after theirs, so this list is read again too.
type Form = { kind: 'CREATE' } | { kind: 'ACTIVATE' | 'CANCEL'; poolId: string } | null
const LIMIT = 20
const statusClass: Record<HppPool['status'], string> = { DRAFT: 'hpool-draft', ACTIVE: 'hpool-active', CANCELLED: 'hpool-cancelled', VOIDED: 'hpool-voided' }
const validDay = (v: string) => /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v) && new Date(v + 'T00:00:00Z').toISOString().slice(0, 10) === v

function errorText(e: unknown) {
  const message = e && typeof e === 'object' ? (e as { message?: unknown }).message : undefined
  return hppPoolRefusalText(message) ?? normalizeClientError(e).message
}
function outcomeText(o: HppPoolOutcome) {
  const period = hppPoolPeriodText(o.periodStart, o.periodEnd)
  if (o.action === 'CREATE') return `Draf pool ${o.poolNumber} dibuat untuk periode ${period}${o.correctionOf ? ' sebagai pengganti pool yang dibatalkan' : ''}. Periksa angkanya, lalu aktifkan bila sudah benar.`
  if (o.action === 'ACTIVATE') return `Pool ${o.poolNumber} aktif. Jurnal biaya absensi ke PO sudah dibuat dan HPP PO terkait dihitung ulang.`
  if (o.status === 'VOIDED') return `Draf pool ${o.poolNumber} dihapus. Tidak ada jurnal yang dibuat.`
  return `Pool ${o.poolNumber} dibatalkan. Jurnal pembalik sudah dibuat dan HPP PO terkait dihitung ulang tanpa pool ini. Bila sumbernya perlu dibetulkan, betulkan dulu, lalu buat pool pengganti.`
}
function step(label: string, at: string | null, by: string | null, why: string | null, journal?: string | null) {
  if (!at) return null
  return <li>{label} {formatCp6WibDateTime(at)} oleh {by ?? 'pengguna tidak tercatat'}{why ? `: ${why}` : ''}{journal ? ` · jurnal ${journal}` : ''}</li>
}

export default function AttendanceHppPoolPanel({ onCommitted, refresh = 0 }: { onCommitted: () => Promise<unknown>; refresh?: number }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi pool HPP absensi belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('HPP_POOL')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role) && hasPermission(identity, 'finance.hpp.view')
  const mayManage = allowed && hasPermission(identity, SENSITIVE_ACTION_PERMISSION.recalculateHpp)
  const query = useRef<HppPoolQuery>({ offset: 0, limit: LIMIT, periodStart: null, periodEnd: null }), serial = useRef(0)
  const [data, setData] = useState<HppPoolWorkspace | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [done, setDone] = useState(''), [start, setStart] = useState(''), [end, setEnd] = useState(''), [correctionOf, setCorrectionOf] = useState<string | null>(null)
  const [form, setForm] = useState<Form>(null), [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false)
  const closeForm = () => { setForm(null); setReason(''); setReviewed(false) }
  const load = useCallback(async () => {
    const q = { ...query.current }, ticket = beginRead(), n = ++serial.current
    setData(null); setError(''); setReviewed(false)
    if (!allowed) return false
    setLoading(true)
    try {
      const r = await client.rpc('erp_cp7_get_hpp_pools_v1', { p_offset: q.offset, p_limit: q.limit, p_period_start: q.periodStart, p_period_end: q.periodEnd })
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (r.error) throw r.error
      const w = parseHppPoolWorkspace(r.data, q)
      // A current read may show facts while an earlier command is still being reconciled; the writer stays locked then.
      const fresh = finishRead(ticket)
      setData(w); return fresh
    } catch (e) { if (n === serial.current && isReadCurrent(ticket)) setError(errorText(e)); return false }
    finally { if (n === serial.current) setLoading(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { ++serial.current } }, [load])
  // Another writer on this page committed: its change may move what a pool shows (HPP of a PO), so read again.
  const latestLoad = useRef(load); latestLoad.current = load
  useEffect(() => { if (refresh > 0) { setDone(''); setForm(null); setReason(''); setReviewed(false); void latestLoad.current() } }, [refresh])
  const handlers: ProductionMutationHandlers = {
    send: async (e: ProductionEnvelope) => {
      const r = await client.rpc('erp_cp7_save_hpp_pool_v1', { p_action: e.action, p_payload: e.payload, p_request: e.id })
      if (!r.error) return r
      // Keep the PostgreSQL code (it tells the recovery whether the refusal is definite); only the words become plain.
      const x = r.error as { message?: unknown; code?: unknown; details?: unknown; hint?: unknown }
      return { data: r.data, error: { code: x.code, details: x.details, hint: x.hint, message: hppPoolRefusalText(x.message) ?? x.message } }
    },
    validate: (value, e) => { parseHppPoolOutcome(value, e) },
    retire: (value, e) => {
      const o = parseHppPoolOutcome(value, e)
      setDone(outcomeText(o)); closeForm(); setData(null)
      if (o.action === 'CREATE') setCorrectionOf(null)
    },
    reload: async () => { const mine = await load(); await onCommitted(); return mine },
  }
  if (!allowed) return null
  const preview = data?.preview ?? null
  const previewCurrent = preview !== null && preview.periodStart === start && preview.periodEnd === end
  const canWrite = mayManage && data?.canManage === true
  const locked = recovery.writerLocked || loading || recovery.busy
  const correctionPool = correctionOf ? data?.pools.find(p => p.id === correctionOf) ?? preview?.cancelledPools.find(c => c.id === correctionOf) ?? null : null
  const why = reason.trim(), reasonOk = why.length >= 5 && why.length <= 1000
  const showPreview = (from: string, to: string, replace: string | null) => {
    setDone(''); closeForm(); setStart(from); setEnd(to); setCorrectionOf(replace)
    query.current = { ...query.current, periodStart: from, periodEnd: to }
    if (replace) setForm({ kind: 'CREATE' })
    void load()
  }
  const submitPeriod = () => {
    if (!validDay(start) || !validDay(end) || end < start) { setError('Isi tanggal mulai dan akhir periode; akhir tidak boleh sebelum mulai.'); return }
    showPreview(start, end, null)
  }
  let createPayload: ReturnType<typeof hppPoolCreatePayload> | null = null
  if (previewCurrent && preview.canCreate && canWrite && reviewed && reasonOk && form?.kind === 'CREATE' && !locked) {
    try { createPayload = hppPoolCreatePayload(preview, why, correctionOf) } catch { createPayload = null }
  }
  const poolForm = (p: HppPool, kind: 'ACTIVATE' | 'CANCEL') => {
    const verb = kind === 'ACTIVATE' ? 'aktifkan' : 'batalkan', ok = canWrite && reviewed && reasonOk && !locked && p.actions.includes(kind)
    const effect = kind === 'ACTIVATE'
      ? `Mengaktifkan membuat jurnal biaya absensi ${hppPoolRupiah(p.numeratorAmount)} ke ${p.poCount} PO dan menghitung ulang HPP PO itu. Tanggal jurnalnya akhir periode, ${hppPoolDay(p.periodEnd)}.`
      : p.status === 'DRAFT' ? 'Draf ini akan dihapus. Belum ada jurnal, jadi tidak ada yang dibalik.'
        : `Membatalkan membuat jurnal pembalik ${hppPoolRupiah(p.numeratorAmount)} dan menghitung ulang HPP PO terkait tanpa pool ini. Sesudahnya sumber bisa dibetulkan dan pool pengganti dibuat.`
    return <section className="hpool-form" aria-label={`Form ${verb} pool ${p.poolNumber}`}>
      <p className="hpool-warning">{effect}</p>
      <label>Alasan<textarea aria-label={`Alasan ${verb} pool ${p.poolNumber}`} value={reason} maxLength={1000} disabled={locked}
        onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
      <label className="cproc-check"><input type="checkbox" aria-label={`${kind === 'ACTIVATE' ? 'Aktifkan' : 'Batalkan'} pool ${p.poolNumber} sudah diperiksa`}
        checked={reviewed} disabled={locked || !reasonOk} onChange={e => setReviewed(e.target.checked)}/>Angka, periode, dan alasan pool ini sudah saya periksa.</label>
      <div className="hpool-buttons">
        <button type="button" className="primary-btn" disabled={!ok}
          onClick={() => { if (ok) void run(kind, hppPoolActionPayload(p, kind, why), null, handlers) }}>Simpan: {verb} pool</button>
        <button type="button" disabled={recovery.busy} onClick={closeForm}>Tutup</button>
      </div>
    </section>
  }
  return <section className="panel cproc hpool" aria-label="Pool HPP absensi">
    <h2>Pool HPP absensi</h2>
    <p>Biaya absensi mandor biasa dari gaji yang sudah disetujui dibagi ke PO menurut jumlah potong yang selesai dijahit pada periode gaji yang sama. Pool aktif masuk ke HPP PO; pool yang dibatalkan dibalik jurnalnya, lalu bisa dibuat pool pengganti.</p>
    <ProductionRecoveryNotice recovery={recovery} className="" onReconcile={() => reconcile(handlers)} reconcileLabel="Periksa hasil pool"/>
    {done ? <p role="status">{done}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {loading ? <p role="status">Memuat pool HPP absensi…</p> : null}
    {data ? <>
      <p>{data.closedThrough ? `Pembukuan ditutup sampai ${hppPoolDay(data.closedThrough)}. Pool yang periodenya berakhir pada atau sebelum tanggal itu tidak bisa dibuat, diaktifkan, atau dibatalkan.` : 'Belum ada periode pembukuan yang ditutup.'}</p>
      {!canWrite ? <p>Anda bisa melihat pool. Membuat, mengaktifkan, dan membatalkan pool perlu hak HPP "Rekalkulasi".</p> : null}
    </> : null}
    <form className="hpool-period" onSubmit={e => { e.preventDefault(); submitPeriod() }}>
      <label>Mulai periode pool<input type="date" aria-label="Mulai periode pool" value={start} disabled={recovery.busy}
        onChange={e => { setStart(e.target.value); setCorrectionOf(null); closeForm() }}/></label>
      <label>Akhir periode pool<input type="date" aria-label="Akhir periode pool" value={end} disabled={recovery.busy}
        onChange={e => { setEnd(e.target.value); setCorrectionOf(null); closeForm() }}/></label>
      <button type="submit" disabled={loading || recovery.busy}>Pratinjau</button>
      <button type="button" disabled={loading || recovery.busy} onClick={() => { setDone(''); void load() }}>Muat ulang daftar pool</button>
    </form>
    {data && data.periods.length ? <section className="hpool-periods" aria-label="Periode gaji absensi">
      <h3>Periode gaji absensi yang sudah disetujui</h3>
      <div>{data.periods.map(p => <button type="button" key={p.periodStart + p.periodEnd} aria-label={`Pratinjau periode ${hppPoolPeriodText(p.periodStart, p.periodEnd)}`}
        disabled={loading || recovery.busy} onClick={() => showPreview(p.periodStart, p.periodEnd, null)}>
        <strong>{hppPoolPeriodText(p.periodStart, p.periodEnd)}</strong>
        <span>{p.payrollCount} gaji · {p.pool ? `pool ${hppPoolStatusText[p.pool.status].toLowerCase()} ${p.pool.poolNumber}` : 'belum ada pool'}</span>
      </button>)}</div>
    </section> : null}
    {preview ? <section className="hpool-preview" aria-label="Pratinjau pool">
      <h3>Pratinjau periode {hppPoolPeriodText(preview.periodStart, preview.periodEnd)}</h3>
      {!previewCurrent ? <p>Tanggal di atas sudah diubah. Tekan Pratinjau untuk melihat periode yang dipilih.</p> : null}
      {preview.status === 'BLOCKED' && preview.blocker ? <p className="hpool-blocker">Belum bisa dibuat: {hppPoolBlockerText(preview.blocker)}</p> : null}
      {preview.status === 'READY' ? <>
        <dl className="hpool-facts">
          <div><dt>Biaya absensi</dt><dd>{hppPoolRupiah(preview.numeratorAmount ?? '0.00')}</dd></div>
          <div><dt>Potong selesai dijahit</dt><dd>{hppPoolPcs(preview.denominatorQty ?? 0)}</dd></div>
          <div><dt>Biaya per pcs</dt><dd>{hppPoolRupiah(preview.unitCost ?? '0.00')}</dd></div>
          <div><dt>Gaji sumber</dt><dd>{preview.sourceCount} gaji</dd></div>
          <div><dt>PO tujuan</dt><dd>{preview.poCount} PO</dd></div>
        </dl>
        {preview.pos.length ? <ul className="hpool-lines">{preview.pos.map(x => <li key={x.poId}>{x.poNumber ?? 'PO tanpa nomor'}: {hppPoolPcs(x.sewingQty)}</li>)}</ul> : null}
        {preview.poCount !== null && preview.poCount > preview.pos.length ? <p>Menampilkan {preview.pos.length} dari {preview.poCount} PO.</p> : null}
      </> : null}
      {preview.periodClosed ? <p className="hpool-blocker">Pembukuan periode ini sudah ditutup{data?.closedThrough ? ` sampai ${hppPoolDay(data.closedThrough)}` : ''}, jadi pool untuk periode ini tidak bisa dibuat. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan → Laporan &amp; Tutup Buku → tab Tutup Buku.</p> : null}
      {preview.existingPool ? <p>Periode ini sudah punya pool {hppPoolStatusText[preview.existingPool.status].toLowerCase()}: {preview.existingPool.poolNumber}. Aktifkan atau batalkan pool itu di daftar di bawah.</p> : null}
      {preview.status === 'READY' && preview.canCreate && previewCurrent ? <p>Siap dibuat sebagai draf. Draf belum mengubah jurnal maupun HPP.</p> : null}
      {previewCurrent && preview.canCreate && canWrite ? form?.kind === 'CREATE'
        ? <section className="hpool-form" aria-label="Buat draf pool">
          {correctionPool ? <p className="hpool-warning">Pool ini akan mengganti pool {correctionPool.poolNumber} yang sudah dibatalkan.</p> : null}
          <label>Alasan<textarea aria-label="Alasan buat draf pool" value={reason} maxLength={1000} disabled={locked}
            onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
          <label className="cproc-check"><input type="checkbox" aria-label="Draf pool sudah diperiksa" checked={reviewed} disabled={locked || !reasonOk}
            onChange={e => setReviewed(e.target.checked)}/>Periode, biaya absensi, jumlah potong, dan alasan sudah saya periksa.</label>
          <div className="hpool-buttons">
            <button type="button" className="primary-btn" disabled={!createPayload}
              onClick={() => { if (createPayload) void run('CREATE', createPayload, null, handlers) }}>{correctionOf ? 'Buat draf pool pengganti' : 'Buat draf pool'}</button>
            <button type="button" disabled={recovery.busy} onClick={() => { closeForm(); setCorrectionOf(null) }}>Tutup</button>
          </div>
        </section>
        : <button type="button" className="primary-btn" disabled={locked} onClick={() => { setDone(''); setForm({ kind: 'CREATE' }) }}>Buat draf pool</button> : null}
    </section> : null}
    {data ? <section className="hpool-list" aria-label="Daftar pool HPP absensi">
      <h3>Daftar pool</h3>
      {data.pools.length === 0 ? <p>Belum ada pool HPP absensi.</p> : null}
      {data.pools.map(p => <article key={p.id} className="hpool-item" aria-label={`Pool ${p.poolNumber}`}>
        <header><strong>{p.poolNumber}</strong><span className={`hpool-status ${statusClass[p.status]}`}>{hppPoolStatusText[p.status]}</span></header>
        <p>Periode {hppPoolPeriodText(p.periodStart, p.periodEnd)} · biaya absensi {hppPoolRupiah(p.numeratorAmount)} · {hppPoolPcs(p.denominatorQty)} selesai dijahit
          {p.unitCost ? ` · ${hppPoolRupiah(p.unitCost)} per pcs` : ''} · {p.sourceCount} gaji sumber</p>
        {p.allocations.length ? <ul className="hpool-lines">{p.allocations.map(a => <li key={a.poId}>{a.poNumber ?? 'PO tanpa nomor'}: {hppPoolPcs(a.sewingQty)} → {hppPoolRupiah(a.amount)}</li>)}</ul> : null}
        {p.poCount > p.allocations.length ? <p>Menampilkan {p.allocations.length} dari {p.poCount} PO.</p> : null}
        <ul className="hpool-history">
          {step('Dibuat', p.createdAt, p.createdBy, p.reason)}
          {step('Diaktifkan', p.activatedAt, p.activatedBy, p.activationReason, p.journalNumber)}
          {step(p.status === 'VOIDED' ? 'Draf dihapus' : 'Dibatalkan', p.cancelledAt, p.cancelledBy, p.cancellationReason, p.reversalJournalNumber)}
        </ul>
        {p.correctionOf ? <p>Mengganti pool {p.correctionOf.poolNumber} yang dibatalkan.</p> : null}
        {p.replacedBy.length ? <p>Diganti oleh {p.replacedBy.map(x => `pool ${x.poolNumber} (${hppPoolStatusText[x.status]})`).join(', ')}.</p> : null}
        {p.stale ? <p className="hpool-blocker">Data gaji absensi, aturan HPP mandor, atau setoran jahit periode ini berubah sejak draf dibuat, jadi draf ini tidak bisa diaktifkan. Batalkan draf ini lalu buat draf baru.</p> : null}
        {p.periodClosed && p.status !== 'VOIDED' ? <p className="hpool-blocker">Pembukuan periode pool ini sudah ditutup, jadi pool ini tidak bisa diaktifkan atau dibatalkan. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan → Laporan &amp; Tutup Buku → tab Tutup Buku.</p> : null}
        {canWrite && p.actions.length ? <div className="hpool-buttons">
          {p.actions.includes('ACTIVATE') ? <button type="button" aria-label={`Aktifkan pool ${p.poolNumber}`} disabled={locked}
            onClick={() => { setDone(''); setReason(''); setReviewed(false); setForm({ kind: 'ACTIVATE', poolId: p.id }) }}>Aktifkan</button> : null}
          {p.actions.includes('CANCEL') ? <button type="button" aria-label={`Batalkan pool ${p.poolNumber}`} disabled={locked}
            onClick={() => { setDone(''); setReason(''); setReviewed(false); setForm({ kind: 'CANCEL', poolId: p.id }) }}>Batalkan</button> : null}
          {p.actions.includes('REPLACE') ? <button type="button" aria-label={`Buat pool pengganti untuk ${p.poolNumber}`} disabled={locked}
            onClick={() => showPreview(p.periodStart, p.periodEnd, p.id)}>Buat pool pengganti</button> : null}
        </div> : null}
        {form && form.kind !== 'CREATE' && form.poolId === p.id && canWrite ? poolForm(p, form.kind) : null}
      </article>)}
      <div className="hpool-buttons">
        <button type="button" disabled={loading || data.offset === 0} onClick={() => { query.current = { ...query.current, offset: Math.max(0, data.offset - LIMIT) }; closeForm(); void load() }}>Pool sebelumnya</button>
        <span>{data.total} pool</span>
        <button type="button" disabled={loading || data.nextOffset === null} onClick={() => { query.current = { ...query.current, offset: data.nextOffset ?? 0 }; closeForm(); void load() }}>Pool berikutnya</button>
      </div>
    </section> : null}
  </section>
}
