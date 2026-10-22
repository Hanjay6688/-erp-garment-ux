import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import TransactionSourceLink from './TransactionSourceNavigation'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import type { ProductionEnvelope } from './productionRecovery'
import { correctionPoFromSewing, parseMandorCorrection, mandorCorrectionPayload, validateMandorCorrection,
  type MandorCorrectionWorkspace } from './mandorCorrectionContract'

const permissions = ['production.distribution.view', 'production.distribution.create', 'production.distribution.edit_draft',
  'production.distribution.post', 'production.wip.view', 'production.wip.post', 'production.wip.reverse']
const documentNames: Record<string, string> = {
  PO_STATE: 'Status PO', PICKUP_SOURCE: 'Riwayat pembagian', PAYROLL: 'Nota/gaji', ATTENDANCE_POOL: 'Pool HPP absen',
  POCKET_POOL: 'Pembagian kain kantong', QC: 'QC', FG_LOT: 'Lot barang jadi', LAUNDRY: 'Laundry', SEWING: 'Selesai dijahit',
  WORK: 'Hasil kerja/upah', WORK_JOURNAL: 'Jurnal upah', ACCESSORY_NOTE: 'Nota aksesori', MATERIAL_ISSUE: 'Bahan mandor',
  REWORK: 'Rework', BS: 'Kasus BS', SCRAP: 'Scrap', PICKUP_DRAFT: 'Draft pembagian', GROUP_STATE: 'Status potongan', WIP_HISTORY: 'Riwayat WIP',
}
export default function MandorCorrectionPanel({ groupId, groupVersion, parentReady, onCommitted }: {
  groupId: string; groupVersion: number; parentReady: boolean; onCommitted: (message: string) => Promise<void>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi koreksi mandor belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('MANDOR_CORRECTION')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role) && permissions.every(p => hasPermission(identity, p))
  const bound = `${groupId}:${groupVersion}:${recovery.scope}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef(false), outcome = useRef(''), redo = useRef<{ poId: string; menus: string[] } | null>(null)
  const [open, setOpen] = useState(false), [data, setData] = useState<MandorCorrectionWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [target, setTarget] = useState(''), [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false)
  useEffect(() => {
    ++serial.current; committed.current = false; setData(null); setOpen(false); setBusy(false)
    setError(''); setTarget(''); setReason(''); setReviewed(false)
  }, [bound])
  useEffect(() => { setDone('') }, [groupId, recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed || !parentReady) return false
    setBusy(true)
    try {
      const po = await client.rpc('erp_cp7_get_sewing_completion_v1', { p_group: groupId })
      if (n !== serial.current || capture !== live.current || !isReadCurrent(ticket)) return false
      if (po.error) throw po.error
      const poId = correctionPoFromSewing(po.data, groupId)
      const reply = await client.rpc('erp_cp7_get_mandor_correction_v1', { p_po: poId })
      if (n !== serial.current || capture !== live.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      const parsed = parseMandorCorrection(reply.data, poId)
      redo.current = { poId, menus: parsed.afterSteps.map(s => s.menu) }
      setData(parsed); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, parentReady, beginRead, client, finishRead, groupId, isReadCurrent])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_correct_mandor_v1', { p_payload: e.payload, p_request: e.id }),
    validate: validateMandorCorrection,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validateMandorCorrection(value, e); committed.current = true
      setData(null); setReviewed(false); setTarget(''); setReason('')
      const p = e.payload as { po_id?: unknown }, seen = redo.current, menus = seen && seen.poId === p.po_id ? seen.menus : []
      outcome.current = `${result.poNumber}: ${result.pickupCount} pembagian diganti ke mandor yang benar. Catat ulang hasil jahit di Produksi › WIP & Sewing dengan waktu fisik aslinya dan pilih tarifnya, lalu buat lagi dokumen lain yang tadi dibalik${menus.length ? ` (urutannya: ${menus.join('; ')})` : ''}. Riwayat upah dan nota lama tetap tersimpan.`
      setDone(outcome.current)
    },
    reload: async () => {
      if (committed.current) { setOpen(false); await onCommitted(outcome.current); return true }
      return load()
    },
  }
  const current = data !== null && parentReady && !recovery.workspaceStale
  const disabled = !allowed || !current || !data?.eligible || busy || recovery.writerLocked
  const validTarget = data?.contractors.some(c => c.id === target && c.id !== data.contractorId) ?? false
  if (!allowed && !recovery.pending && !done) return null
  return <section className="panel cproc-review cp7-mandor-correction" aria-label="Koreksi mandor sesudah jahit">
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cwip-error" reconcileLabel="Periksa hasil koreksi mandor"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {!open && allowed ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Koreksi mandor sesudah jahit</button> : null}
    {open ? <>
      <header><h2>Koreksi mandor · seluruh PO</h2><button type="button" disabled={busy || recovery.busy} onClick={() => { ++serial.current; setData(null); setOpen(false); setReviewed(false) }}>Tutup koreksi mandor</button></header>
      <p>Dipakai ketika salah mandor baru diketahui sesudah jahit. Semua potongan dalam PO mengikuti satu mandor; upah, nota dan pembayaran lama dibalik melalui dokumen asal sebelum pembagian diganti.</p>
      {busy ? <p role="status">Memeriksa PO, upah, nota dan proses lanjutannya…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current ? <>
        <p><strong>{data.poNumber}</strong> · {data.groupCount} potongan · {data.pickupCount} pembagian sudah diposting.</p>
        <p>Mandor tercatat: {data.contractors.find(c => c.id === data.contractorId)?.name ?? 'Lihat riwayat PO'}.</p>
        {data.blockers.length ? <div role="alert"><p>Dokumen berikut masih mengunci koreksi. Balik pemakaiannya dari dokumen paling akhir, lalu periksa ulang daftar ini.</p>
          {data.blockers.some(b => b.kind === 'PO_STATE' && b.status === 'FINISHED') && data.blockers.some(b => b.kind === 'FG_LOT') ? <p>Barang jadi yang sudah dipakai harus dibalik melalui dokumen pemakaiannya sebelum membuka kembali PO. Setelah PO dibuka, balik QC dan laundry, lalu periksa lagi pengunci upahnya.</p> : null}
          <ol>{data.blockers.map(b => { const name = b.number ?? documentNames[b.kind] ?? 'Dokumen terkait'
            return <li key={`${b.kind}:${b.id}`}><strong>{name}</strong> — {b.step}
              {b.source ? <TransactionSourceLink sourceType={b.source.sourceType} sourceId={b.source.sourceId} label={`Buka ${name}`}/> : null}</li> })}</ol></div> : <p>Dokumen pengunci sudah ditutup. Riwayat lama tetap tersimpan saat pembagian pengganti dibuat.</p>}
        <button type="button" disabled={busy || recovery.busy} onClick={() => void load()}>Periksa ulang dokumen pengunci</button>
        <label>Mandor yang benar<select aria-label="Mandor yang benar" value={target} disabled={disabled} onChange={e => { setTarget(e.target.value); setReviewed(false) }}><option value="">Pilih mandor</option>{data.contractors.filter(c => c.id !== data.contractorId).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <label>Alasan koreksi mandor<input aria-label="Alasan koreksi mandor" value={reason} maxLength={1000} disabled={disabled} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
        <p>{data.afterStep}</p>
        <ol aria-label="Langkah sesudah koreksi mandor">{data.afterSteps.map(s => <li key={s.menu}><strong>{s.menu}</strong> — {s.step}</li>)}</ol>
        <label className="cproc-check"><input type="checkbox" aria-label="Koreksi seluruh PO sudah diperiksa" checked={reviewed} disabled={disabled || !validTarget || reason.trim().length < 5} onChange={e => setReviewed(e.target.checked)}/>Saya sudah memeriksa seluruh PO, mandor pengganti, dan langkah mencatat ulang jahitan.</label>
        <button type="button" disabled={disabled || !validTarget || !reviewed || reason.trim().length < 5} onClick={() => { if (data && !disabled) void run('CORRECT_MANDOR', mandorCorrectionPayload(data, target, reason), null, handlers) }}>Ganti pembagian ke mandor yang benar</button>
        <section aria-label="Riwayat koreksi mandor PO ini"><h3>Riwayat koreksi mandor PO ini</h3>
          {data.history.length ? <ol>{data.history.map(h => <li key={h.generationNo}>{formatCp6WibDateTime(h.recordedAt)} · {h.oldContractorName} → {h.newContractorName} · {h.pickupCount} pembagian diganti · oleh {h.actorName ?? 'akun yang sudah tidak terdaftar'} · alasan: {h.reason}</li>)}</ol>
            : <p>PO ini belum pernah dikoreksi mandornya.</p>}</section>
      </> : null}
    </> : null}
  </section>
}
