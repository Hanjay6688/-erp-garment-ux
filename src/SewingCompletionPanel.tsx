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
  parseSewingWorkspace, sewingBlockerText, sewingCancelPayload, sewingCancelText, sewingRecordPayload, validateSewingOutcome,
  type SewingEvent, type SewingWorkspace,
} from './sewingCompletionContract'
import type { ProductionEnvelope } from './productionRecovery'

const rupiah = (value: number) => `Rp${value.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`

// D14-14 gap G1: like the UX demo card ("SELESAI DIJAHIT __ / N pcs"), a picked-up Potongan records the pieces its Mandor
// finished sewing. The server posts the piece-work wage (WORK_COMPLETION) and the SELESAI_DIJAHIT that Laundry counts as
// ready to send, in one step. A record can be cancelled while its pieces are still at the Mandor and its wage is unpaid.
export default function SewingCompletionPanel({ groupId, groupNumber, groupVersion, parentReady, onCommitted }: {
  groupId: string; groupNumber: string; groupVersion: number; parentReady: boolean; onCommitted: (message: string) => Promise<unknown>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi selesai jahit belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('SEWING_COMPLETION')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['production.wip.view', 'production.wip.post'].every(p => hasPermission(identity, p))
  const bound = `${groupId}:${groupVersion}:${recovery.scope}`
  const live = useRef(bound); live.current = bound
  const serial = useRef(0), committed = useRef(false), outcome = useRef('')
  const [open, setOpen] = useState(false), [data, setData] = useState<SewingWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [qty, setQty] = useState(''), [at, setAt] = useState(() => cp6WibDateTimeInput()), [reason, setReason] = useState('')
  const [reviewed, setReviewed] = useState(false), [cancelId, setCancelId] = useState(''), [cancelReason, setCancelReason] = useState('')
  const reset = () => { setData(null); setQty(''); setReason(''); setReviewed(false); setCancelId(''); setCancelReason('') }
  useEffect(() => { ++serial.current; committed.current = false; reset(); setOpen(false); setError(''); setBusy(false) }, [bound, allowed])
  useEffect(() => { setDone('') }, [recovery.scope, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions.join('|')])
  useEffect(() => () => { ++serial.current }, [])
  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, capture = live.current
    setData(null); setReviewed(false); setError('')
    if (!allowed) return false
    setBusy(true)
    try {
      const reply = await client.rpc('erp_cp7_get_sewing_completion_v1', { p_group: groupId })
      if (n !== serial.current || live.current !== capture || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      const parsed = parseSewingWorkspace(reply.data, groupId)
      setData(parsed); setAt(cp6WibDateTimeInput()); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [allowed, beginRead, client, finishRead, groupId, isReadCurrent])
  const handlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_save_sewing_completion_v1', { p_payload: e.payload, p_request: e.id, p_expected: String(e.expectedVersion) }),
    validate: validateSewingOutcome,
    retire: (value: unknown, e: ProductionEnvelope) => {
      const result = validateSewingOutcome(value, e); committed.current = true
      reset()
      outcome.current = result.action === 'RECORD'
        ? `${result.number}: ${result.qtyPcs} pcs tercatat selesai dijahit. Upah mandor ${rupiah(result.wageAmount ?? 0)} masuk hutang mandor; ${result.readyUnsentPcs} pcs siap dikirim ke laundry.`
        : `${result.number}: catatan ${result.qtyPcs} pcs selesai jahit dibatalkan beserta upahnya.`
      setDone(outcome.current)
    },
    reload: async () => {
      // The page keeps the outcome: its reload replaces this card.
      if (committed.current) { setOpen(false); await onCommitted(outcome.current); return true }
      return load()
    },
  }
  const current = data !== null && data.groupId === groupId && !recovery.workspaceStale
  const locked = !allowed || !parentReady || recovery.writerLocked || busy || !current
  const physicalIso = cp6WibPhysicalTimeToIso(at)
  const qtyValid = current && /^[1-9][0-9]{0,6}$/.test(qty) && Number(qty) <= data.maxQty
  const rates = current ? (data.ratesCommitted ? data.components : data.ratePreview) : []
  const rateSum = rates.reduce((sum, c) => sum + c.rate, 0)
  const canRecord = current && data.eligible && qtyValid && physicalIso !== null && reason.trim().length >= 5 && reviewed && !locked
  const activeEvents = current ? data.events.filter(e => !e.reversed) : []
  const cancelTarget: SewingEvent | undefined = activeEvents.find(e => e.id === cancelId)
  if (!allowed && !recovery.pending && !done) return null
  return <section className="cwip-sewing" aria-label={`Selesai jahit ${groupNumber}`}>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="cwip-error" reconcileLabel="Periksa hasil selesai jahit"/> : null}
    {done ? <p role="status">{done}</p> : null}
    {allowed && !open ? <button type="button" disabled={!parentReady || recovery.busy || Boolean(recovery.pending)} onClick={() => { setOpen(true); setDone(''); void load() }}>Catat selesai jahit</button> : null}
    {open ? <>
      <header><h3>Selesai jahit · {groupNumber}</h3><button type="button" disabled={recovery.busy || busy} onClick={() => { ++serial.current; reset(); setOpen(false) }}>Tutup selesai jahit</button></header>
      {busy ? <p role="status">Memeriksa potongan dan tarif mandor…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {current ? <dl className="cwip-sewing-facts">
        <div><dt>Mandor</dt><dd>{data.contractorName ?? '—'}</dd></div>
        <div><dt>Diambil</dt><dd>{data.pickedUpAt ? formatCp6WibDateTime(data.pickedUpAt) : '—'}</dd></div>
        <div><dt>Selesai dijahit</dt><dd>{data.sewnPcs} / {data.effectivePcs} pcs</dd></div>
        <div><dt>Bisa dicatat</dt><dd>{data.maxQty} pcs</dd></div>
      </dl> : null}
      {current && data.blockers.length ? <div role="alert"><p>Belum bisa dicatat:</p><ul>{data.blockers.map((b, i) => <li key={`${b.kind}:${b.id ?? i}`}>{sewingBlockerText(b)}</li>)}</ul></div> : null}
      {current && data.eligible ? <>
        <p>{data.ratesCommitted
          ? `Upah mandor per pcs: ${rates.map(c => `${c.name} ${rupiah(c.rate)}`).join(' + ')} = ${rupiah(rateSum)}.`
          : `Perkiraan upah mandor per pcs (tarif yang berlaku sekarang; dikunci dari BOM kerja saat pertama kali disimpan): ${rates.map(c => `${c.name} ${rupiah(c.rate)}`).join(' + ')} = ${rupiah(rateSum)}.`}</p>
        <label className="cwip-sewing-qty"><span>SELESAI DIJAHIT</span><span><input aria-label={`Jumlah selesai dijahit ${groupNumber}`} inputMode="numeric" value={qty} disabled={locked}
          onFocus={e => e.currentTarget.select()} onChange={e => { setQty(e.target.value.replace(/[^0-9]/g, '')); setReviewed(false) }}/><b>/ {data.maxQty} pcs</b></span></label>
        <label>Waktu selesai jahit (WIB)<input type="datetime-local" aria-label={`Waktu selesai jahit ${groupNumber}`} value={at} disabled={locked} onChange={e => { setAt(e.target.value); setReviewed(false) }}/></label>
        <label>Catatan<input aria-label={`Catatan selesai jahit ${groupNumber}`} value={reason} maxLength={1000} disabled={locked} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
        {qtyValid ? <p>{data.ratesCommitted ? 'Upah yang akan dicatat' : 'Perkiraan upah yang akan dicatat'}: {qty} pcs × {rupiah(rateSum)} = {rupiah(Number(qty) * rateSum)}.</p> : null}
        <label className="cproc-check"><input type="checkbox" aria-label={`Selesai jahit ${groupNumber} sudah diperiksa`} checked={reviewed}
          disabled={locked || !qtyValid || physicalIso === null || reason.trim().length < 5} onChange={e => setReviewed(e.target.checked)}/>Jumlah, waktu, dan mandor sudah saya periksa.</label>
        <button type="button" disabled={!canRecord} onClick={() => { if (canRecord) void run('RECORD_SEWING', sewingRecordPayload(data, qty, physicalIso, reason), Number(data.groupVersion), handlers) }}>Simpan selesai jahit</button>
      </> : null}
      {current && activeEvents.length ? <section aria-label={`Riwayat selesai jahit ${groupNumber}`}>
        <h4>Sudah tercatat</h4>
        <ul>{activeEvents.map(e => <li key={e.id}>
          <span>{formatCp6WibDateTime(e.physicalAt)} · {e.qtyPcs} pcs · upah {rupiah(e.wageAmount)}</span>
          {e.cancelBlocker ? <small>{sewingCancelText(e.cancelBlocker)}</small>
            : data.canCancel ? <button type="button" disabled={locked} onClick={() => { setCancelId(e.id); setCancelReason('') }}>Batalkan {e.qtyPcs} pcs</button> : null}
        </li>)}</ul>
        {cancelTarget && !cancelTarget.cancelBlocker ? <div>
          <label>Alasan batal<input aria-label={`Alasan batal selesai jahit ${groupNumber}`} value={cancelReason} maxLength={1000} disabled={locked} onChange={e => setCancelReason(e.target.value)}/></label>
          <button type="button" disabled={locked || cancelReason.trim().length < 5} onClick={() => { if (!locked) void run('CANCEL_SEWING', sewingCancelPayload(data, cancelTarget, cancelReason), Number(data.groupVersion), handlers) }}>Batalkan catatan selesai jahit</button>
        </div> : null}
      </section> : null}
    </> : null}
  </section>
}
