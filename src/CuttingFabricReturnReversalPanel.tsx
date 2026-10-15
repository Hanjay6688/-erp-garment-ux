import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { micro, microText, returnValueCents, rupiah } from './cuttingReturnContract'
import {
  correctionProblems, parseReversal, reversalPayload, validateReversal,
  type ReversalBlocker, type ReversalSource, type ReversalWorkspace,
} from './cuttingReturnReversalContract'
import type { PickupQueueRow } from './cuttingPersistence'
import type { ProductionEnvelope } from './productionRecovery'

const qtyText = (value: string) => { const neg = value.startsWith('-'), m = micro(neg ? value.slice(1) : value); return m === null ? value : (neg ? '-' : '') + microText(m) }
function blockerText(b: ReversalBlocker, unit: (id: string) => string) {
  if (b.kind === 'NOT_RETURNED') return `${b.label} belum punya kain kembali yang bisa dibatalkan.`
  if (b.kind === 'PERIOD_CLOSED') return `Periode sampai ${b.closedThrough} sudah ditutup, jadi pembatalan hari ini belum bisa dicatat.`
  const uses = b.uses.map(u => `${u.label} (${qtyText(u.qty.replace(/^-/, ''))} ${unit(b.id)}, ${formatCp6WibDateTime(u.physicalAt)})`).join('; ')
  return `Kain kembali di roll ${b.label} (${qtyText(b.qtyReturned)}) sudah dipakai lagi; sisa di gudang sekarang ${qtyText(b.availableNow)}. Betulkan dulu: ${uses || 'pemakaian sesudahnya'}. Sesudah itu baru kain kembali bisa dibatalkan.`
}

// SG-02 cancel / correct (owner D14-10). Stock, journal and PO cost of the return are reversed together; the original
// return stays in the history. A correction records the right quantity in the same save.
export default function CuttingFabricReturnReversalPanel({ source, parentReady, onCommitted }: {
  source: PickupQueueRow | null; parentReady: boolean; onCommitted: () => Promise<void>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi batal kain kembali belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('CUTTING_RETURN_REVERSAL')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['production.distribution.view', 'production.cutting.view', 'production.cutting.edit_draft', 'production.cutting.post'].every(p => hasPermission(identity, p))
  const target = useMemo<ReversalSource | null>(() => source ? {
    groupId: source.cutting_group_id, poId: source.po_id, number: source.group_number, rowVersion: source.row_version,
  } : null, [source])
  const bound = target ? `${target.groupId}:${target.poId}:${target.rowVersion}:${recovery.scope}` : ''
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef(false)
  const [open, setOpen] = useState(false), [data, setData] = useState<ReversalWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [correcting, setCorrecting] = useState(false), [qty, setQty] = useState<Record<string, string>>({})
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [done, setDone] = useState('')
  useEffect(() => { ++serial.current; committed.current = false; setData(null); setQty({}); setCorrecting(false); setReason(''); setReviewed(false); setOpen(false); setError(''); setBusy(false) }, [bound, allowed])
  useEffect(() => { setDone('') }, [recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed || !target) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_cutting_return_reversal_v1', { p_group: target.groupId })
      if (n !== serial.current || live.current !== capture || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parseReversal(reply.data, target)); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent, target])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_reverse_cutting_return_v1', { p_payload: e.payload, p_request: e.id, p_expected: String(e.expectedVersion) }),
    validate: validateReversal,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validateReversal(value, e); committed.current = true
      setData(null); setQty({}); setReviewed(false); setReason(''); setCorrecting(false)
      const recost = result.recostQueued ? ' Barang jadi PO ini sudah ada, jadi HPP-nya masuk antrean hitung ulang HPP.' : ''
      setDone(result.action === 'CANCEL_RETURN'
        ? `${result.number}: kain kembali dibatalkan (${formatCp6WibDateTime(result.at)}). Stok kain, jurnal, dan biaya PO kembali seperti sebelum kain kembali; catatan aslinya tetap tersimpan.${recost}`
        : `${result.number}: kain kembali dibetulkan (${formatCp6WibDateTime(result.at)}), nilai baru ${rupiah(micro(result.replacementValue ?? '0')! / 10_000n)}. Catatan lama dibalik dan tetap tersimpan.${recost}`)
    },
    reload: async () => {
      if (committed.current) { setOpen(false); await onCommitted(); return true }
      return load()
    },
  }
  const entries = useMemo(() => (data?.returned ?? []).map(r => ({ cuttingGroupRollId: r.cuttingGroupRollId, qty: qty[r.cuttingGroupRollId] ?? '' })), [data, qty])
  const problems = data ? correctionProblems(data, correcting, entries) : []
  const unit = (id: string) => data?.returned.find(r => r.cuttingGroupRollId === id)?.unitCode ?? ''
  const current = data && target && data.groupId === target.groupId && data.rowVersion === target.rowVersion && !recovery.workspaceStale
  const disabled = !allowed || !parentReady || recovery.writerLocked || busy || !current || !data?.eligible
  const newCents = data && correcting ? data.returned.reduce((sum, r) => { const v = qty[r.cuttingGroupRollId] ?? '', m = micro(v); return m === null || m <= 0n ? sum : sum + returnValueCents(v, r.unitCost) }, 0n) : 0n
  const oldCents = data ? data.returned.reduce((sum, r) => sum + returnValueCents(r.qtyReturned, r.unitCost), 0n) : 0n
  if (!open && !recovery.pending && !done && !(allowed && target)) return null
  return <section className="panel cproc-review cp7-cutting-return" aria-label="Batal atau betulkan kain kembali">
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cpick-message error" reconcileLabel="Periksa hasil batal kain kembali"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed && target && !open ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Batal / betulkan kain kembali</button> : null}
    {open ? <>
      <header><h2>Batal atau betulkan kain kembali · {target?.number}</h2><button type="button" disabled={recovery.busy || busy} onClick={() => { ++serial.current; setData(null); setOpen(false); setReviewed(false) }}>Tutup batal kain kembali</button></header>
      <p>Kain kembali yang sudah tercatat dibalik: stok kain di roll itu turun lagi, jurnal persediaan dibalik, dan biaya PO naik lagi sebesar nilainya. Kain kembali tidak menyentuh hutang supplier. Catatan aslinya tetap tersimpan. Kalau jumlahnya yang salah, pilih "Betulkan jumlahnya" dan isi jumlah yang benar; keduanya tersimpan sekaligus.</p>
      {busy ? <p role="status">Memeriksa kain kembali dan pemakaian sesudahnya…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current && data.blockers.length ? <div role="alert"><p>Kain kembali belum bisa dibatalkan:</p><ul>{data.blockers.map(b => <li key={b.kind + b.id}>{blockerText(b, unit)}</li>)}</ul></div> : null}
      {current && data.returned.length ? <div className="cpick-table-wrap"><table aria-label="Kain kembali yang tercatat"><thead><tr><th>Roll</th><th>Kain kembali</th><th>Waktu</th><th>Di gudang sekarang</th>{correcting ? <th>Jumlah yang benar</th> : null}</tr></thead><tbody>{data.returned.map(r =>
        <tr key={r.cuttingGroupRollId}><th>{r.rollNumber}<br/><small>{r.materialSku}{r.materialName ? ` · ${r.materialName}` : ''}</small></th><td>{qtyText(r.qtyReturned)} {r.unitCode ?? ''}</td><td>{formatCp6WibDateTime(r.returnedAt)}</td><td>{qtyText(r.availableNow)} {r.unitCode ?? ''}</td>
          {correcting ? <td><input aria-label={`Jumlah benar roll ${r.rollNumber}`} inputMode="decimal" value={qty[r.cuttingGroupRollId] ?? ''} disabled={disabled} onChange={e => { const v = e.target.value; setQty(c => ({ ...c, [r.cuttingGroupRollId]: v })); setReviewed(false) }}/></td> : null}</tr>)}</tbody>
        <tfoot><tr><th colSpan={correcting ? 4 : 3}>{correcting ? 'Nilai lama → nilai baru' : 'Biaya PO naik lagi'}</th><th>{correcting ? `${rupiah(oldCents)} → ${rupiah(newCents)}` : rupiah(oldCents)}</th></tr></tfoot></table></div> : null}
      {current && data.eligible ? <fieldset className="cp7-choice"><legend>Yang mau dilakukan</legend>
        <label><input type="radio" name="reversal-mode" checked={!correcting} disabled={disabled} onChange={() => { setCorrecting(false); setReviewed(false) }}/>Batalkan saja</label>
        <label><input type="radio" name="reversal-mode" checked={correcting} disabled={disabled} onChange={() => { setCorrecting(true); setReviewed(false) }}/>Betulkan jumlahnya</label>
      </fieldset> : null}
      <label>Alasan batal / betulkan<input aria-label="Alasan batal kain kembali" value={reason} maxLength={1000} disabled={disabled} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
      {current && data.eligible && problems.length ? <ul role="alert">{problems.map(p => <li key={p}>{p}</li>)}</ul> : null}
      <label className="cproc-check"><input type="checkbox" aria-label="Batal kain kembali sudah diperiksa" checked={reviewed} disabled={disabled || problems.length > 0} onChange={e => setReviewed(e.target.checked)}/>Roll, jumlah, dan alasannya sudah saya periksa.</label>
      <button type="button" disabled={disabled || problems.length > 0 || !reviewed || reason.trim().length < 5} onClick={() => { if (data && !disabled) void run('REVERSE_RETURN', reversalPayload(data, correcting, entries, reason), data.rowVersion, handlers) }}>{correcting ? 'Simpan pembetulan kain kembali' : 'Batalkan kain kembali'}</button>
    </> : null}
  </section>
}
