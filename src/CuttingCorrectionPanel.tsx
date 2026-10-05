import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { cuttingReopenPayload, parseCuttingCorrection, validateCuttingReopen, type CuttingCorrectionSource, type CuttingCorrectionWorkspace } from './cuttingCorrectionContract'
import type { PickupQueueRow } from './cuttingPersistence'
import type { ProductionEnvelope } from './productionRecovery'

export default function CuttingCorrectionPanel({ source, parentReady, onCommitted }: {
  source: PickupQueueRow | null; parentReady: boolean; onCommitted: () => Promise<void>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi koreksi potongan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('CUTTING_CORRECTION')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER','ADMIN'].includes(identity.profile.role)
    && ['production.distribution.view','production.cutting.view','production.cutting.edit_draft','production.cutting.post'].every(p => hasPermission(identity, p))
  const target = useMemo<CuttingCorrectionSource | null>(() => source ? {
    groupId: source.cutting_group_id, poId: source.po_id, number: source.group_number, rowVersion: source.row_version,
  } : null, [source])
  const bound = target ? `${target.groupId}:${target.poId}:${target.rowVersion}:${recovery.scope}` : ''
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef<CuttingCorrectionSource | null>(null)
  const [open, setOpen] = useState(false), [data, setData] = useState<CuttingCorrectionWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [done, setDone] = useState('')
  useEffect(() => { ++serial.current; committed.current = null; setData(null); setReason(''); setReviewed(false); setOpen(false); setError(''); setBusy(false) }, [bound, allowed])
  useEffect(() => { setDone('') }, [recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed || !target) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_cutting_correction_v1', { p_group: target.groupId })
      if (n !== serial.current || live.current !== capture || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      const value = parseCuttingCorrection(reply.data, target)
      setData(value); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent, target])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_reopen_cutting_v1', { p_payload: e.payload, p_request: e.id, p_expected: String(e.expectedVersion) }),
    validate: validateCuttingReopen,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validateCuttingReopen(value, e); committed.current = result
      setData(null); setReviewed(false); setReason(''); setDone(`${result.number} sudah dibuka sebagai draft koreksi. Aliran bahan lama dibalik dan riwayatnya tetap tersimpan. Buka Buat Potongan untuk memperbaiki draft tersebut.`)
    },
    reload: async () => {
      if (committed.current) { setOpen(false); await onCommitted(); return true }
      return load()
    },
  }
  const current = data && target && data.groupId === target.groupId && data.rowVersion === target.rowVersion && !recovery.workspaceStale
  const disabled = !allowed || !parentReady || recovery.writerLocked || busy || !current || !data?.eligible
  if (!open && !recovery.pending && !done && !(allowed && target)) return null
  return <section className="panel cproc-review" aria-label="Koreksi potongan tercatat">
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cpick-message error" reconcileLabel="Periksa hasil koreksi potongan"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed && target && !open ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Periksa koreksi potongan</button> : null}
    {open ? <>
      <header><h2>Koreksi {target?.number}</h2><button type="button" disabled={recovery.busy || busy} onClick={() => { ++serial.current; setData(null); setOpen(false); setReviewed(false) }}>Tutup koreksi potongan</button></header>
      <p>Potongan yang belum dijemput dapat dibuka kembali sebagai draft. Pembalikan bahan dan jurnal mengikuti transaksi asal; roll, ukuran, waktu asal dan riwayat tetap tersimpan. Perbaikan draft lalu posting adalah tindakan berikutnya.</p>
      {busy ? <p role="status">Memeriksa potongan dan transaksi terkait…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current && data.blockers.length ? <div role="alert"><p>Koreksi ini masih terhalang:</p><ul>{data.blockers.map(b => <li key={`${b.kind}:${b.id}`}>{b.kind === 'PICKUP' ? `Pembagian ${b.label} · ${b.status === 'DRAFT' ? 'draft' : 'sudah dicatat'}` : b.kind === 'DOWNSTREAM' ? `${b.label} sudah memiliki transaksi jahit atau lanjutan.` : b.kind === 'MATERIAL_FLOW' ? `${b.label} tidak memiliki aliran bahan yang dapat dibuka lewat jalur ini.` : `${b.label} sudah dijemput atau melewati tahap potong.`}</li>)}</ul></div> : null}
      <label>Alasan koreksi potongan<input aria-label="Alasan koreksi potongan" value={reason} maxLength={1000} disabled={disabled} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
      <label className="cproc-check"><input type="checkbox" aria-label="Potongan dan pembalikan bahan sudah diperiksa" checked={reviewed} disabled={disabled} onChange={e => setReviewed(e.target.checked)}/>Potongan dan pembalikan bahan sudah saya periksa.</label>
      <button type="button" disabled={disabled || !reviewed || reason.trim().length < 5} onClick={() => { if (data && !disabled) void run('REOPEN_POSTED', cuttingReopenPayload(data, reason), data.rowVersion, handlers) }}>Buka potongan sebagai draft koreksi</button>
    </> : null}
  </section>
}
