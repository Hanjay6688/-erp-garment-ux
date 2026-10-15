import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {
  parsePoFinishList, parsePoFinishWorkspace, poFinishBlockerText, poFinishPayload, poFinishReasonText, poFinishStatusText,
  validatePoFinishOutcome, type PoFinishList, type PoFinishWorkspace,
} from './poFinishContract'
import type { ProductionEnvelope } from './productionRecovery'
import './po-finish.css'

// Server amounts are exact decimal strings ("1234567.50"); show them as Rupiah without going through a float.
export function rupiahText(value: string) {
  const negative = value.startsWith('-'), [whole, cents = '00'] = value.replace('-', '').split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${negative ? '-' : ''}Rp${grouped}${cents === '00' ? '' : ',' + cents}`
}
const statusLabels: Record<string, string> = { CUTTING: 'Potong', SEWING: 'Jahit', LAUNDRY: 'Laundry', QC: 'QC', FINISHED: 'Selesai', ON_HOLD: 'Ditahan' }

// D14-14 gap G2: like the UX demo HPP checklist ("Produksi sudah selesai · PO berstatus FINISHED"), the Owner/Admin
// finishes a Production Order here; the server finishes it through the Native writer, which rebuilds its HPP, moves the
// value to finished goods and closes what is left in WIP. Nothing changes until the reviewed PO is saved.
export default function PoFinishPanel({ onCommitted }: { onCommitted: () => Promise<unknown> }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi selesai PO belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('PO_FINISH')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['finance.hpp.view', 'finance.hpp.manage'].every(p => hasPermission(identity, p))
  const serial = useRef(0), committed = useRef(false)
  const [query, setQuery] = useState(''), [list, setList] = useState<PoFinishList | null>(null)
  const [data, setData] = useState<PoFinishWorkspace | null>(null), [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false)
  useEffect(() => { ++serial.current; setList(null); setData(null); setSelected(''); setReason(''); setReviewed(false); setError('') }, [recovery.scope, allowed])
  useEffect(() => () => { ++serial.current }, [])
  const search = useCallback(async (offset: number, q: string) => {
    const n = ++serial.current
    setError(''); setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_list_po_finish_v1', { p_query: q.trim(), p_offset: offset })
      if (n !== serial.current) return false
      if (reply.error) throw reply.error
      setList(parsePoFinishList(reply.data, q, offset)); return true
    } catch (e) { if (n === serial.current) setError(normalizeClientError(e).message); return false }
    finally { if (n === serial.current) setBusy(false) }
  }, [client])
  const load = useCallback(async (poId: string) => {
    const ticket = beginRead(), n = ++serial.current
    setData(null); setReviewed(false); setError(''); setSelected(poId)
    if (!allowed) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_po_finish_v1', { p_po: poId })
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parsePoFinishWorkspace(reply.data, poId)); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_finish_po_v1', { p_payload: e.payload, p_request: e.id }),
    validate: validatePoFinishOutcome,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const r = validatePoFinishOutcome(value, e); committed.current = true
      setData(null); setReason(''); setReviewed(false)
      const per = r.hpp.perPcs === null ? 'belum ada' : `${rupiahText(r.hpp.perPcs)}/pcs`
      const left = r.hpp.pendingReasons.length ? ` Masih perlu: ${r.hpp.pendingReasons.map(poFinishReasonText).join('; ')}.` : ''
      setDone(`${r.poNumber}: PO selesai pada ${r.finishedOn}. HPP final ${per} untuk ${r.hpp.qtyBasisPcs} pcs (total ${rupiahText(r.hpp.total)}). `
        + `Sisa WIP ${rupiahText(r.residualClosed)} dibebankan ke biaya lain-lain.${left}`)
    },
    reload: async () => {
      if (committed.current) { committed.current = false; setSelected(''); await onCommitted(); if (list) void search(list.offset, list.query); return true }
      return selected ? load(selected) : false
    },
  }
  const current = data !== null && data.poId === selected && !recovery.workspaceStale
  const locked = !allowed || recovery.writerLocked || busy || !current
  const canFinish = current && data.eligible && reason.trim().length >= 5 && reviewed && !locked
  if (!allowed && !recovery.pending && !done) return null
  return <section className="panel cproc pofin" aria-label="Selesaikan PO">
    <h2>Selesaikan PO · HPP final</h2>
    <p>PO yang barangnya sudah kembali dari laundry, lewat QC, dan tidak punya BS terbuka bisa diselesaikan di sini. Saat itu HPP-nya menjadi final.</p>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="" reconcileLabel="Periksa hasil selesai PO"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed ? <form className="pofin-search" onSubmit={e => { e.preventDefault(); setDone(''); void search(0, query) }}>
      <label>Cari nomor PO<input aria-label="Cari nomor PO" value={query} maxLength={80} onChange={e => setQuery(e.target.value)}/></label>
      <button type="submit" disabled={busy || recovery.busy}>Cari PO</button>
    </form> : null}
    {busy ? <p role="status">Memeriksa PO…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {list ? <div className="pofin-list">
      {list.rows.length === 0 ? <p>Tidak ada PO yang cocok.</p> : null}
      {list.rows.map(r => <button type="button" key={r.id} aria-label={`Pilih PO ${r.number}`} aria-pressed={selected === r.id} disabled={busy || recovery.busy}
        onClick={() => { setDone(''); void load(r.id) }}>
        <strong>{r.number}</strong><span>{statusLabels[r.status] ?? r.status} · barang jadi {r.fgPcs} pcs{r.contractorName ? ` · ${r.contractorName}` : ''}</span>
      </button>)}
      <div className="pofin-pages">
        <button type="button" disabled={busy || list.offset === 0} onClick={() => void search(Math.max(0, list.offset - 20), list.query)}>PO sebelumnya</button>
        <span>{list.total} PO</span>
        <button type="button" disabled={busy || list.nextOffset === null} onClick={() => { if (list.nextOffset !== null) void search(list.nextOffset, list.query) }}>PO berikutnya</button>
      </div>
    </div> : null}
    {current ? <section className="pofin-detail" aria-label={`Selesai PO ${data.poNumber}`}>
      <h3>{data.poNumber}</h3>
      <dl className="pofin-facts">
        <div><dt>Status</dt><dd>{statusLabels[data.poStatus] ?? data.poStatus}</dd></div>
        <div><dt>Mandor</dt><dd>{data.contractorName ?? '—'}</dd></div>
        <div><dt>Barang jadi</dt><dd>{data.fgPcs} pcs ({data.fgLots} lot)</dd></div>
        <div><dt>Laundry</dt><dd>dikirim {data.laundrySentPcs} · kembali {data.laundryReturnedPcs} · klaim selesai {data.laundryClaimedPcs} pcs</dd></div>
        <div><dt>QC</dt><dd>{data.qcAccountedPcs} dari {data.laundryGoodPcs} pcs GOOD laundry</dd></div>
        <div><dt>BS terbuka</dt><dd>{data.openBsCases} kasus</dd></div>
        <div><dt>Saldo WIP PO</dt><dd>{rupiahText(data.wipBalance)}</dd></div>
        <div><dt>HPP sekarang</dt><dd>{data.hpp.perPcs === null ? '—' : `${rupiahText(data.hpp.perPcs)}/pcs`} · {poFinishStatusText(data.hpp.displayStatus)}</dd></div>
      </dl>
      {data.hpp.pendingReasons.length ? <p>Catatan kelengkapan HPP: {data.hpp.pendingReasons.map(poFinishReasonText).join('; ')}.</p> : null}
      {data.blockers.length ? <div role="alert"><p>Belum bisa diselesaikan:</p><ul>{data.blockers.map(b => <li key={b.kind}>{poFinishBlockerText(b)}</li>)}</ul></div> : null}
      {data.eligible ? <>
        <p className="pofin-warning">Tanggal selesai: {data.finishDate} (hari ini, WIB). HPP dihitung ulang dari biaya yang sudah tercatat, nilainya masuk ke barang jadi, dan sisa nilai WIP yang tidak masuk barang jadi dibebankan sebagai biaya lain-lain. PO yang sudah selesai tidak bisa dibuka lagi dari aplikasi.</p>
        <label>Catatan<input aria-label={`Catatan selesai PO ${data.poNumber}`} value={reason} maxLength={1000} disabled={locked} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
        <label className="cproc-check"><input type="checkbox" aria-label={`PO ${data.poNumber} sudah diperiksa`} checked={reviewed}
          disabled={locked || reason.trim().length < 5} onChange={e => setReviewed(e.target.checked)}/>Barang, laundry, QC, dan BS PO ini sudah saya periksa.</label>
        <button type="button" className="primary-btn" disabled={!canFinish} onClick={() => { if (canFinish) void run('FINISH_PO', poFinishPayload(data, reason), null, handlers) }}>Selesaikan PO dan kunci HPP final</button>
      </> : null}
    </section> : null}
  </section>
}
