import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import {
  boundText, parsePickupReversal, pickupBlockerText, pickupReversalPayload, validatePickupReversal,
  type PickupReversalSource, type PickupReversalWorkspace,
} from './pickupReversalContract'
import type { PickupQueueRow } from './cuttingPersistence'
import type { ProductionEnvelope } from './productionRecovery'

const stageText: Record<string, string> = { DRAFT: 'Draft', CUTTING: 'Potong', SEWING: 'Jahit', LAUNDRY: 'Laundry', QC: 'QC' }

// SG-01 (Fable FABLE-009, Astra SG-01): undo a posted Bagi Potongan before any sewing, so it can be distributed again
// (another Mandor, other batches or another time). After sewing has started it is refused and names what holds it.
export default function PickupReversalPanel({ source, parentReady, onCommitted }: {
  source: PickupQueueRow | null; parentReady: boolean; onCommitted: () => Promise<void>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi batal Bagi Potongan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('PICKUP_REVERSAL')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['production.distribution.view', 'production.distribution.edit_draft', 'production.distribution.post'].every(p => hasPermission(identity, p))
  const target = useMemo<PickupReversalSource | null>(() => source?.pickup?.status === 'POSTED' ? {
    groupId: source.cutting_group_id, poId: source.po_id, number: source.group_number, pickupId: source.pickup.id,
  } : null, [source])
  const bound = target ? `${target.groupId}:${target.pickupId}:${source?.pickup?.row_version ?? ''}:${recovery.scope}` : ''
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef(false)
  const [open, setOpen] = useState(false), [data, setData] = useState<PickupReversalWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [done, setDone] = useState('')
  useEffect(() => { ++serial.current; committed.current = false; setData(null); setReason(''); setReviewed(false); setOpen(false); setError(''); setBusy(false) }, [bound, allowed])
  useEffect(() => { setDone('') }, [recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed || !target) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_pickup_reversal_v1', { p_group: target.groupId })
      if (n !== serial.current || live.current !== capture || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parsePickupReversal(reply.data, target)); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent, target])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_reverse_pickup_v1', { p_payload: e.payload, p_request: e.id, p_expected: String(e.expectedVersion) }),
    validate: validatePickupReversal,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validatePickupReversal(value, e); committed.current = true
      setData(null); setReviewed(false); setReason('')
      setDone(`${result.number}: Bagi Potongan dibatalkan. Potongan kembali menunggu dibagi; status PO ${stageText[result.poStage] ?? result.poStage}.${result.mandorCleared ? ' Mandor di PO dikosongkan, jadi bisa dibagi ke Mandor lain.' : ''}`)
    },
    reload: async () => {
      if (committed.current) { setOpen(false); await onCommitted(); return true }
      return load()
    },
  }
  const current = data && target && data.groupId === target.groupId && data.pickupId === target.pickupId && !recovery.workspaceStale
  const disabled = !allowed || !parentReady || recovery.writerLocked || busy || !current || !data?.eligible
  if (!open && !recovery.pending && !done && !(allowed && target)) return null
  const restore = current ? data.restore : null
  return <section className="panel cproc-review cp7-pickup-reversal" aria-label="Batal Bagi Potongan">
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cpick-message error" reconcileLabel="Periksa hasil batal Bagi Potongan"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed && target && !open ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Batalkan Bagi Potongan ini</button> : null}
    {open ? <>
      <header><h2>Batal Bagi Potongan · {target?.number}</h2><button type="button" disabled={recovery.busy || busy} onClick={() => { ++serial.current; setData(null); setOpen(false); setReviewed(false) }}>Tutup batal Bagi Potongan</button></header>
      <p>Dipakai kalau Bagi Potongan salah (salah Mandor, salah bagi batch, atau salah jam) dan belum ada yang dijahit. Bahan tetap tercatat keluar dari gudang; potongan kembali menunggu dibagi, lalu bisa dibagi ulang seperti biasa. Catatan Bagi Potongan lama tetap disimpan sebagai riwayat.</p>
      {busy ? <p role="status">Memeriksa Bagi Potongan dan proses lanjutannya…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current ? <dl className="cpick-facts">
        <div><dt>Mandor</dt><dd>{data.contractorName ?? '—'}</dd></div>
        <div><dt>Diambil</dt><dd>{formatCp6WibDateTime(data.pickedUpAt)}</dd></div>
        <div><dt>Batch</dt><dd>{data.batchCount} batch · {data.pieces} pcs</dd></div>
        <div><dt>PO</dt><dd>{data.poNumber}</dd></div>
      </dl> : null}
      {current && data.blockers.length ? <div role="alert"><p>Bagi Potongan ini belum bisa dibatalkan:</p><ul>{data.blockers.map((b, i) => <li key={`${b.kind}:${b.id ?? i}`}>{pickupBlockerText(b)}</li>)}</ul></div> : null}
      {current && data.eligible && restore ? <ul aria-label="Yang dipulihkan">
        <li>Status PO menjadi {stageText[restore.poStage ?? ''] ?? restore.poStage}{restore.otherGroupsPickedUp ? ' (tetap, karena potongan lain di PO ini sudah dibagi)' : ''}.</li>
        <li>{restore.clearMandor ? 'Mandor di PO dikosongkan, jadi potongan bisa dibagi ke Mandor lain.' : `Mandor di PO tetap ${data.contractorName ?? ''} karena masih terikat ${restore.mandorBoundBy.map(b => boundText[b.kind] ?? b.kind).filter((v, i, a) => a.indexOf(v) === i).join(', ') || 'sejak sebelum Bagi Potongan ini'}.`}</li>
        <li>Pelaksana potongan kembali menjadi {restore.executorName ?? '(kosong)'}.</li>
      </ul> : null}
      <label>Alasan pembatalan<input aria-label="Alasan batal Bagi Potongan" value={reason} maxLength={1000} disabled={disabled} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
      <label className="cproc-check"><input type="checkbox" aria-label="Pembatalan Bagi Potongan sudah diperiksa" checked={reviewed} disabled={disabled || reason.trim().length < 5} onChange={e => setReviewed(e.target.checked)}/>Saya sudah memeriksa Mandor, batch, dan PO yang akan dipulihkan.</label>
      <button type="button" disabled={disabled || !reviewed || reason.trim().length < 5} onClick={() => { if (data && !disabled) void run('REVERSE_PICKUP', pickupReversalPayload(data, reason), Number(data.pickupVersion), handlers) }}>Batalkan Bagi Potongan</button>
    </> : null}
  </section>
}
