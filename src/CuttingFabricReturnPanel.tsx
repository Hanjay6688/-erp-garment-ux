import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import {
  cuttingReturnPayload, cuttingReturnProblems, micro, parseCuttingReturn, returnValueCents, rupiah, validateCuttingReturn,
  type CuttingReturnSource, type CuttingReturnWorkspace,
} from './cuttingReturnContract'
import type { PickupQueueRow } from './cuttingPersistence'
import type { ProductionEnvelope } from './productionRecovery'

const blockerText: Record<CuttingReturnWorkspace['blockers'][number]['kind'], (label: string) => string> = {
  NOT_POSTED: label => `${label} belum diposting, jadi belum ada bahan yang keluar dari gudang.`,
  ALREADY_RETURNED: label => `Kain sisa ${label} sudah pernah dikembalikan ke gudang (hanya sekali per potongan).`,
  RETURN_FACTS_PRESENT: label => `${label} sudah punya catatan kain kembali dari jalur lama; periksa dulu sebelum mencatat lagi.`,
  WAREHOUSE: label => `Gudang asal ${label} tidak aktif atau bukan gudang bahan.`,
  NOTHING_LEFT: label => `${label} tidak punya sisa kain yang dicatat saat potong.`,
}

// SG-02 (owner D14-4): "Ada langkah 'kain kembali ke gudang': roll yang sama masuk stok lagi beserta nilainya, biaya PO
// berkurang sebesar itu."
export default function CuttingFabricReturnPanel({ source, parentReady, onCommitted }: {
  source: PickupQueueRow | null; parentReady: boolean; onCommitted: () => Promise<void>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi kain kembali ke gudang belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('CUTTING_RETURN')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['production.distribution.view', 'production.cutting.view', 'production.cutting.edit_draft', 'production.cutting.post'].every(p => hasPermission(identity, p))
  const target = useMemo<CuttingReturnSource | null>(() => source ? {
    groupId: source.cutting_group_id, poId: source.po_id, number: source.group_number, rowVersion: source.row_version,
  } : null, [source])
  const bound = target ? `${target.groupId}:${target.poId}:${target.rowVersion}:${recovery.scope}` : ''
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef(false)
  const [open, setOpen] = useState(false), [data, setData] = useState<CuttingReturnWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [qty, setQty] = useState<Record<string, string>>({}), [returnedAt, setReturnedAt] = useState(() => cp6WibDateTimeInput())
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [done, setDone] = useState('')
  useEffect(() => { ++serial.current; committed.current = false; setData(null); setQty({}); setReason(''); setReviewed(false); setOpen(false); setError(''); setBusy(false) }, [bound, allowed])
  useEffect(() => { setDone('') }, [recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed || !target) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_cutting_return_v1', { p_group: target.groupId })
      if (n !== serial.current || live.current !== capture || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parseCuttingReturn(reply.data, target)); setReturnedAt(cp6WibDateTimeInput()); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, isReadCurrent, target])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_return_cutting_fabric_v1', { p_payload: e.payload, p_request: e.id, p_expected: String(e.expectedVersion) }),
    validate: validateCuttingReturn,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validateCuttingReturn(value, e); committed.current = true
      setData(null); setQty({}); setReviewed(false); setReason('')
      setDone(`${result.number}: kain kembali ke gudang sudah tercatat (${formatCp6WibDateTime(result.returnedAt)}), nilai ${rupiah(micro(result.value)! / 10_000n)}. Biaya PO berkurang sebesar itu.${result.recostQueued ? ' Barang jadi PO ini sudah ada, jadi HPP-nya masuk antrean hitung ulang HPP.' : ''}`)
    },
    reload: async () => {
      if (committed.current) { setOpen(false); await onCommitted(); return true }
      return load()
    },
  }
  const entries = useMemo(() => (data?.rolls ?? []).map(r => ({ cuttingGroupRollId: r.cuttingGroupRollId, qty: qty[r.cuttingGroupRollId] ?? '' })), [data, qty])
  const iso = cp6WibPhysicalTimeToIso(returnedAt)
  const problems = data ? cuttingReturnProblems(data, entries) : []
  if (data && !iso) problems.push('Isi tanggal dan jam kain kembali (WIB).')
  else if (data && iso && new Date(iso).getTime() < new Date(data.cutAt).getTime()) problems.push(`Kain tidak bisa kembali sebelum dipotong (${formatCp6WibDateTime(data.cutAt)}).`)
  else if (data && iso && cp6WibDateTimeInput(iso).slice(0, 10) < data.openFrom) problems.push(`Tanggal kain kembali ada di periode yang sudah ditutup. Pilih tanggal mulai ${data.openFrom}.`)
  const totalCents = data ? data.rolls.reduce((sum, r) => {
    const q = qty[r.cuttingGroupRollId] ?? '', m = micro(q)
    return m === null || m <= 0n ? sum : sum + returnValueCents(q, r.unitCost)
  }, 0n) : 0n
  const current = data && target && data.groupId === target.groupId && data.rowVersion === target.rowVersion && !recovery.workspaceStale
  const disabled = !allowed || !parentReady || recovery.writerLocked || busy || !current || !data?.eligible
  if (!open && !recovery.pending && !done && !(allowed && target)) return null
  return <section className="panel cproc-review cp7-cutting-return" aria-label="Kain kembali ke gudang">
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cpick-message error" reconcileLabel="Periksa hasil kain kembali ke gudang"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed && target && !open ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Catat kain kembali ke gudang</button> : null}
    {open ? <>
      <header><h2>Kain kembali ke gudang · {target?.number}</h2><button type="button" disabled={recovery.busy || busy} onClick={() => { ++serial.current; setData(null); setOpen(false); setReviewed(false) }}>Tutup kain kembali</button></header>
      <p>Sisa kain dari roll yang sama masuk stok lagi{data?.warehouse ? ` di ${data.warehouse.code} · ${data.warehouse.name}` : ''} beserta nilainya (harga saat dipotong). Biaya PO berkurang sebesar nilai itu. Ini hanya bisa dicatat sekali untuk satu potongan, jadi periksa angkanya.</p>
      {busy ? <p role="status">Memeriksa potongan dan sisa kain…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current && data.blockers.length ? <div role="alert"><p>Kain kembali belum bisa dicatat:</p><ul>{data.blockers.map(b => <li key={b.kind}>{blockerText[b.kind](b.label)}</li>)}</ul></div> : null}
      {current ? <div className="cpick-table-wrap"><table aria-label="Roll kain kembali"><thead><tr><th>Roll</th><th>Bahan</th><th>Sisa dicatat saat potong</th><th>Kain kembali</th><th>Nilai</th></tr></thead><tbody>{data.rolls.map(r => {
        const value = qty[r.cuttingGroupRollId] ?? '', m = micro(value)
        return <tr key={r.cuttingGroupRollId}><th>{r.rollNumber}</th><td>{r.materialSku}{r.materialName ? ` · ${r.materialName}` : ''}</td><td>{r.qtyReportedRemaining} {r.unitCode ?? ''}</td>
          <td><input aria-label={`Kain kembali roll ${r.rollNumber}`} inputMode="decimal" value={value} disabled={disabled} onChange={e => { const v = e.target.value; setQty(c => ({ ...c, [r.cuttingGroupRollId]: v })); setReviewed(false) }}/></td>
          <td>{m !== null && m > 0n ? rupiah(returnValueCents(value, r.unitCost)) : '—'}</td></tr>
      })}</tbody><tfoot><tr><th colSpan={4}>Biaya PO berkurang</th><th>{rupiah(totalCents)}</th></tr></tfoot></table></div> : null}
      <label>Tanggal & jam kain kembali (WIB)<input type="datetime-local" aria-label="Tanggal dan jam kain kembali" value={returnedAt} disabled={disabled} onChange={e => { setReturnedAt(e.target.value); setReviewed(false) }}/></label>
      <label>Alasan / catatan kain kembali<input aria-label="Alasan kain kembali" value={reason} maxLength={1000} disabled={disabled} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
      {current && data.eligible && problems.length ? <ul role="alert">{problems.map(p => <li key={p}>{p}</li>)}</ul> : null}
      <label className="cproc-check"><input type="checkbox" aria-label="Jumlah kain kembali sudah diperiksa" checked={reviewed} disabled={disabled || problems.length > 0} onChange={e => setReviewed(e.target.checked)}/>Jumlah, tanggal, dan nilai kain kembali sudah saya periksa.</label>
      <button type="button" disabled={disabled || problems.length > 0 || !reviewed || reason.trim().length < 5} onClick={() => { if (data && iso && !disabled) void run('RETURN_FABRIC', cuttingReturnPayload(data, entries, iso, reason), data.rowVersion, handlers) }}>Simpan kain kembali ke gudang</button>
    </> : null}
  </section>
}
