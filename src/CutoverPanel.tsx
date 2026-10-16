import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { cutoverPayload, parseCutoverWorkspace, validateCutoverOutcome, type CutoverWorkspace } from './cutoverContract'
import type { ProductionEnvelope } from './productionRecovery'

// Owner D15-5 (FABLE-011): "Gunakan tanggal cutover resmi yang saya sahkan dalam WIB, bukan tanggal pertama login atau uji
// coba. Pengamannya wajib di server." The owner sets the date here; the server refuses every operational transaction dated
// before it and keeps the opening-balance and correction paths. This panel only shows and sets it.
const longDate = (iso: string) => new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(iso + 'T00:00:00Z'))
const stamp = (iso: string) => new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Jakarta' }).format(new Date(iso))

export default function CutoverPanel() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi tanggal mulai pakai aplikasi belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('CUTOVER')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const serial = useRef(0)
  const [data, setData] = useState<CutoverWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [date, setDate] = useState(''), [reason, setReason] = useState(''), [checked, setChecked] = useState(false)

  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current
    setBusy(true); setError('')
    try {
      const reply = await client.rpc('erp_cp7_get_cutover_v1')
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parseCutoverWorkspace(reply.data)); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [beginRead, client, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load, recovery.scope])
  useEffect(() => () => { ++serial.current }, [])

  const handlers: ProductionMutationHandlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_set_cutover_v1', { p_payload: e.payload, p_request: e.id }),
    validate: (value: unknown, e: ProductionEnvelope) => { validateCutoverOutcome(value, e) },
    retire: (value: unknown, e: ProductionEnvelope) => {
      const r = validateCutoverOutcome(value, e)
      setDone(`Tersimpan: tanggal mulai pakai aplikasi ${longDate(r.cutoverDate)}. Transaksi operasional bertanggal sebelumnya ditolak server.`)
      setDate(''); setReason(''); setChecked(false)
    },
    reload: load,
  }
  const fresh = data !== null && !recovery.workspaceStale
  const writable = fresh && data.canSet && !recovery.writerLocked && !busy
  const problem = !/^\d{4}-\d{2}-\d{2}$/.test(date) ? 'Pilih tanggal.'
    : data?.current?.cutoverDate === date ? 'Tanggal itu sudah berlaku.'
    : data?.latestAllowed && date > data.latestAllowed ? `Paling lambat ${longDate(data.latestAllowed)}: sudah ada data pada tanggal itu.`
    : reason.trim().length < 5 ? 'Tulis alasan (minimal 5 huruf).' : ''
  const canSubmit = writable && problem === '' && checked
  const submit = () => {
    if (!canSubmit || !data) return
    setDone('')
    void run('SET', cutoverPayload(data.version, date, reason), null, handlers)
  }

  return <section className="panel initial-import-advances cutover-panel" aria-label="Tanggal mulai pakai aplikasi">
    <h2>Tanggal mulai pakai aplikasi (cutover)</h2>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="" reconcileLabel="Periksa hasil simpan tanggal mulai pakai"/> : null}
    {done ? <p role="status" className="cutover-done">{done}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {data ? <>
      <p className="cutover-current">{data.current
        ? <>Berlaku: <strong>{longDate(data.current.cutoverDate)}</strong> (disahkan {data.current.setBy}, {stamp(data.current.setAt)}). Transaksi operasional baru tidak boleh bertanggal sebelum tanggal ini.</>
        : <>Belum disahkan. Selama belum ada tanggal resmi, server belum membatasi tanggal transaksi.</>}</p>
      <p className="initial-import-help">Data sebelum tanggal ini masuk lewat Impor Saldo Awal dengan tanggal cutover yang sama. Invoice terlambat atas penerimaan saldo awal, pelunasan sesudah tanggal ini, dan koreksi dokumen lama tetap lewat jalurnya masing-masing.</p>
      {data.latestAllowed ? <p className="initial-import-help">Paling lambat {longDate(data.latestAllowed)}
        {data.earliestOperational && data.earliestOperational.date === data.latestAllowed ? ': sudah ada transaksi operasional pada tanggal itu.' : ''}
        {data.earliestImport && data.earliestImport.date === data.latestAllowed ? `: impor saldo awal ${data.earliestImport.batchCode} memakai tanggal itu.` : ''}</p> : null}
      {data.canSet ? <div className="cutover-form">
        <label>Tanggal mulai (WIB)<input type="date" aria-label="Tanggal mulai pakai aplikasi (WIB)" value={date} max={data.latestAllowed ?? undefined} disabled={!writable}
          onChange={e => { setDate(e.target.value); setChecked(false) }}/></label>
        <label>Alasan<input aria-label="Alasan tanggal mulai pakai aplikasi" value={reason} maxLength={1000} disabled={!writable} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
        <label className="cmd-check"><input type="checkbox" aria-label="Tanggal mulai pakai aplikasi sudah diperiksa" checked={checked} disabled={!writable || problem !== ''}
          onChange={e => setChecked(e.target.checked)}/>Tanggal dan alasannya sudah saya periksa.</label>
        {date && problem ? <p className="cmd-problems">{problem}</p> : null}
        <button type="button" className="primary" disabled={!canSubmit} onClick={submit}>Sahkan tanggal mulai pakai</button>
      </div> : <p className="initial-import-help">Hanya owner yang bisa mengesahkan tanggal ini.</p>}
      {data.history.length ? <details><summary>Riwayat ({data.history.length})</summary><ul>{data.history.map(h => <li key={h.version}>
        {longDate(h.cutoverDate)}{h.previousDate ? ` (sebelumnya ${longDate(h.previousDate)})` : ''} · {h.setBy} · {stamp(h.setAt)} · "{h.reason}"</li>)}</ul></details> : null}
    </> : busy ? <p>Memuat…</p> : null}
  </section>
}
