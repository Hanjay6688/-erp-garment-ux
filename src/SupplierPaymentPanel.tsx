import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatReceiptDecimal } from './procurementContract'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useTransactionSource } from './TransactionSourceNavigation'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import { financialRecoveryBlocked, useFinancialRecoveryGate } from './useFinancialRecoveryGate'
import { useRetainedFormInput, useRetainedInput } from './useRetainedFormInput'
import { parseSupplierPaymentRead, parseSupplierPaymentOutcome, type SupplierPaymentRead } from './supplierPaymentContract'
import { parseSupplierPaymentCorrectionOutcome } from './supplierPaymentCorrectionContract'
import { parseSupplierPaymentCreateOutcome } from './supplierPaymentCreateContract'
import SupplierPaymentCorrectionPanel from './SupplierPaymentCorrectionPanel'
import SupplierPaymentCreatePanel from './SupplierPaymentCreatePanel'
import { signedSupplierSourceCents } from './supplierCredit'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import RecordTools, { orderRecordPage, type RecordPageOrder } from './RecordTools'
import type { Json } from './types/database.preconnect'

const money = (value: string) => `Rp${formatReceiptDecimal(value)}`
const originalTime = (value: string) => value.length === 10 ? value : formatCp6WibDateTime(value)
function pendingPurchase(payload: Json | undefined) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const d = payload.document
  return d && typeof d === 'object' && !Array.isArray(d) && typeof d.purchase_id === 'string' ? d.purchase_id : null
}
function pendingPayment(payload: Json | undefined) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const d = payload.document
  return d && typeof d === 'object' && !Array.isArray(d) && typeof d.payment_id === 'string' ? d.payment_id : null
}
type Props = { purchaseId: string | null; parentReady: boolean; receiptRevision: string; onReceiptUpdated: (id: string) => Promise<boolean> }
type Review = { id: string; token: string; capturedAt: string; checked: boolean }
export default function SupplierPaymentPanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return null
  const key = JSON.stringify([runtime.projectRef, identity.profile.id, identity.profile.authUserId,
    identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions])
  return <SupplierPaymentWorkspace key={key} {...props}/>
}
function SupplierPaymentWorkspace({ purchaseId, parentReady, receiptRevision, onReceiptUpdated }: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw Error('Sesi pembayaran supplier belum siap.')
  const source = useTransactionSource('RECEIPT')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('SUPPLIER_PAYMENT'), { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [committedTarget, setCommittedTarget] = useState<{ purchase: string; payment: string } | null>(null)
  const selected = purchaseId ?? pendingPurchase(mutation.pending?.payload) ?? committedTarget?.purchase ?? null
  const focus = source?.document.id === selected && source.document.focus?.kind === 'SUPPLIER_PAYMENT' ? source.document.focus : null
  const recoveryPayment = pendingPayment(mutation.pending?.payload) ?? (committedTarget?.purchase === selected ? committedTarget.payment : null)
  const authority = JSON.stringify([runtime.projectRef, identity.profile.id, identity.profile.authUserId,
    identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions])
  const inputs = useRetainedFormInput(authority, mutation.committedSequence)
  const [reasons, setReasons] = useRetainedInput<Record<string, string>>(inputs, 'supplierPayment.reasons', {})
  const [query, setQuery] = useState(''), [order, setOrder] = useState<RecordPageOrder>('SOURCE')
  const [capture, setCapture] = useState<{ authority: string; ticket: ReturnType<typeof beginRead>; data: SupplierPaymentRead } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [review, setReview] = useState<Review | null>(null)
  const [correction, setCorrection] = useState<{ id: string; edit: boolean } | null>(null), [creating, setCreating] = useState(false)
  const sequence = useRef(0), requested = useRef({ id: selected, q: '', offset: focus?.page_offset ?? 0, payment: focus?.id ?? recoveryPayment })
  if (requested.current.id !== selected) requested.current = { id: selected, q: '', offset: focus?.page_offset ?? 0, payment: focus?.id ?? recoveryPayment }
  const retire = useCallback(() => { ++sequence.current; setCapture(null); setReview(null); setCorrection(null); setCreating(false); setBusy(false) }, [])
  const blocked = useFinancialRecoveryGate(mutation.scope, retire)
  const canReverse = ['OWNER', 'ADMIN'].includes(identity.profile.role) && identity.permissions.includes('finance.ap.pay')
  const load = useCallback(async () => {
    retire(); setError('')
    const f = { ...requested.current }
    if (!parentReady || !f.id || financialRecoveryBlocked(mutation.scope)) return false
    const current = ++sequence.current, ticket = beginRead(); setBusy(true)
    try {
      const r = await client.rpc('erp_cp7_get_supplier_payments_v1', { p_purchase: f.id, p_q: f.q, p_offset: f.offset, p_payment: f.payment })
      if (current !== sequence.current || !isReadCurrent(ticket) || financialRecoveryBlocked(mutation.scope)) return false
      if (r.error) throw r.error
      const next = parseSupplierPaymentRead(r.data, f.id, f.q, f.payment ? null : f.offset, f.payment)
      if (next.capabilities.reverse !== canReverse) throw Error('Hak pembatalan pembayaran berubah. Muat ulang sesi dan pembayaran.')
      if (f.payment && !next.page.rows.some(p => p.id === f.payment)) {
        throw Error('Pembayaran asal berpindah atau tidak tersedia. Buka ulang dari buku transaksi.')
      }
      const ready = finishRead(ticket)
      if (!isReadCurrent(ticket)) return false
      setCapture({ authority, ticket, data: next }); return ready
    } catch (e) {
      if (current === sequence.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (current === sequence.current) setBusy(false) }
  }, [client, parentReady, mutation.scope, canReverse, focus, authority, beginRead, finishRead, isReadCurrent, retire])
  useEffect(() => { if (parentReady) void load(); else retire(); return () => { ++sequence.current } }, [load, selected, receiptRevision, parentReady, retire])
  const data = parentReady && !blocked && capture?.authority === authority && isReadCurrent(capture.ticket)
    && capture.data.purchase.id === selected ? capture.data : null
  const locked = busy || mutation.writerLocked, readBusy = busy || mutation.busy || blocked
  const visiblePayment = data?.selected_payment_id ?? null
  const chosen = data?.page.rows.find(p => p.id === review?.id)
  const freshReview = Boolean(review && chosen && chosen.status === 'POSTED' && data?.purchase.status === 'POSTED'
    && data.Native_AP && review.token === chosen.review_token && review.capturedAt === data.captured_at)
  const reason = review ? reasons[review.id] ?? '' : ''
  const handlers: ProductionMutationHandlers = {
    send: envelope => {
      const p = envelope.payload as { document: Json }
      if (envelope.action === 'CORRECT') return client.rpc('erp_cp7_correct_supplier_payment_v1', { p_payload: p.document, p_request: envelope.id })
      if (envelope.action === 'CREATE') return client.rpc('erp_cp7_create_supplier_payment_v1', { p_payload: p.document, p_request: envelope.id })
      return client.rpc('erp_cp7_reverse_supplier_payment_v1', { p_payload: p.document, p_request: envelope.id })
    },
    validate: (value, envelope) => {
      const payload = (envelope.payload as { document: Json }).document
      if (envelope.action === 'CORRECT') parseSupplierPaymentCorrectionOutcome(value, envelope.id, payload)
      else if (envelope.action === 'CREATE') parseSupplierPaymentCreateOutcome(value, envelope.id, payload)
      else parseSupplierPaymentOutcome(value, envelope.id, payload)
    },
    retire: (value, envelope) => {
      const payload = (envelope.payload as { document: Json }).document
      const result = envelope.action === 'CORRECT' ? parseSupplierPaymentCorrectionOutcome(value, envelope.id, payload)
        : envelope.action === 'CREATE' ? parseSupplierPaymentCreateOutcome(value, envelope.id, payload) : parseSupplierPaymentOutcome(value, envelope.id, payload)
      requested.current.id = result.purchase_id; requested.current.payment = result.payment_id
      setCommittedTarget({ purchase: result.purchase_id, payment: result.payment_id }); setReasons({}); retire()
    },
    reload: async () => {
      const id = requested.current.id
      if (!id || !await onReceiptUpdated(id)) { retire(); mutation.invalidate(); return false }
      return load()
    },
  }
  const reverse = () => {
    if (!review || !data || !freshReview || locked || !canReverse || !review.checked || reason.trim().length < 5) return
    const document: Json = { purchase_id: data.purchase.id, payment_id: review.id, review_token: review.token, reason: reason.trim() }
    retire(); void run('REVERSE', { document }, null, handlers)
  }
  return <section className="panel cproc-invoices" aria-label="Pembayaran supplier">
    <header className="cproc-heading"><h2>Pembayaran supplier</h2><button disabled={busy || mutation.busy || blocked} onClick={() => void load()}>Muat ulang pembayaran supplier</button></header>
    <ProductionRecoveryNotice recovery={mutation} className="cproc-review" onReconcile={() => reconcile(handlers)}
      noticeText="Pembayaran sudah diperbarui. Catatan terbaru sudah dimuat."
      messageText={mutation.pending && !mutation.corruptedEnvelope ? 'Hasil tindakan belum pasti. Periksa pembayaran yang sama sebelum mencatat tindakan lain.' : undefined}
      reconcileLabel="Periksa status pembatalan supplier"/>
    {error ? <p role="alert">{error}</p> : null}{busy ? <p role="status">Memuat pembayaran supplier…</p> : null}
    {!selected && !mutation.pending ? <p>Pilih penerimaan untuk melihat riwayat pembayaran supplier.</p> : null}
    {blocked && !mutation.pending ? <p>Angka pembayaran menunggu pemulihan transaksi yang belum dipastikan.</p> : null}
    {selected ? <RecordTools title="pembayaran supplier" busy={readBusy} order={order} onOrder={setOrder}
      submitLabel="Cari pembayaran supplier" onSubmit={e => { e.preventDefault(); requested.current.q = query.trim(); requested.current.offset = 0; requested.current.payment = null; void load() }}
      browseLabel="Browse pembayaran supplier" onBrowse={() => { setQuery(''); requested.current.q = ''; requested.current.offset = 0; requested.current.payment = null; void load() }}
      search={<label>Nomor pembayaran<input aria-label="Cari pembayaran supplier" maxLength={120} disabled={readBusy} value={query}
        onChange={e => { setQuery(e.target.value); retire() }}/></label>}/> : null}
    {data ? <>
      <p><strong>{data.purchase.number} · {data.purchase.supplier_name}</strong></p>
      {data.Native_AP ? <dl className="cproc-grid"><div><dt>Utang final</dt><dd>{money(data.Native_AP.final_ap)}</dd></div><div><dt>Sudah dibayar</dt><dd>{money(data.Native_AP.paid)}</dd></div><div><dt>Sisa utang</dt><dd>{money(data.Native_AP.remaining)}</dd></div></dl>
        : <p>Saldo utang saat ini belum tersedia untuk penerimaan ini.</p>}
      {data.capabilities.reverse && data.purchase.status === 'POSTED' && data.Native_AP && signedSupplierSourceCents(data.Native_AP.remaining) > 0n && !creating
        ? <button disabled={locked} onClick={() => { setReview(null); setCorrection(null); setCreating(true) }}>Bayar supplier {data.purchase.number}</button> : null}
      {creating ? <SupplierPaymentCreatePanel key={JSON.stringify([data.purchase.id, data.captured_at])} source={data} locked={locked} inputs={inputs}
        currentReadTicket={mutation.currentReadTicket} isReadCurrent={isReadCurrent} onClose={() => setCreating(false)}
        onInvalid={message => { retire(); mutation.invalidate(); setError(message) }}
        onSave={document => { if (locked || !canReverse) return; retire(); void run('CREATE', { document }, null, handlers) }}/> : null}
      {orderRecordPage(data.page.rows, order, p => p.number).map(p => <article className="cproc-item" key={p.id}
        data-supplier-payment-id={p.id} data-source-focus={p.id === visiblePayment ? 'true' : undefined}>
        <h3>{p.number} · {money(p.amount)}</h3>
        {p.id === visiblePayment ? <strong>Pembayaran asal dari buku transaksi</strong> : null}
        <p>{p.status === 'POSTED' ? 'Tercatat' : p.status === 'REVERSED' ? 'Sudah dibalik' : 'Belum disahkan'} · {originalTime(p.payment_date)}</p>
        <p>{p.cash_code && p.cash_name ? `${p.cash_code} · ${p.cash_name}` : 'Nama sumber kas belum tercatat'}</p>
        {p.journal ? <p>{p.journal.number} · Tanggal pembukuan {p.journal.accounting_date}{p.journal.period_shifted ? ' · Beralih ke periode terbuka' : ''}</p> : null}
        {p.inverse ? <p>Pembalik {p.inverse.number} · Tanggal pembukuan {p.inverse.accounting_date}. Catatan dan tanggal pembayaran asli tetap disimpan.</p> : null}
        <button disabled={locked} onClick={() => { setReview(null); setCreating(false); setCorrection({ id: p.id, edit: false }) }}>Lihat perubahan pembayaran supplier {p.number}</button>
        {data.capabilities.reverse && data.purchase.status === 'POSTED' && p.status === 'POSTED'
          ? <button disabled={locked} onClick={() => { setReview(null); setCorrection({ id: p.id, edit: true }) }}>Edit pembayaran supplier {p.number}</button> : null}
        {data.capabilities.reverse && data.purchase.status === 'POSTED' && p.status === 'POSTED'
          ? <button disabled={locked} onClick={() => setReview({ id: p.id, token: p.review_token, capturedAt: data.captured_at, checked: false })}>Tinjau pembatalan {p.number}</button> : null}
      </article>)}
      {!data.page.rows.length ? <p>Belum ada pembayaran sesuai pencarian.</p> : null}
      <div className="cproc-pagination"><span>Total {data.page.total} pembayaran</span>
        <button disabled={readBusy || !data.page.offset} onClick={() => { requested.current.offset = Math.max(0, data.page.offset - 25); requested.current.payment = null; void load() }}>Pembayaran supplier sebelumnya</button>
        <button disabled={readBusy || data.page.next_offset === null} onClick={() => { requested.current.offset = data.page.next_offset ?? data.page.offset; requested.current.payment = null; void load() }}>Pembayaran supplier berikutnya</button></div>
      {correction && data.page.rows.some(p => p.id === correction.id) ? <SupplierPaymentCorrectionPanel
        key={JSON.stringify([correction.id, data.page.rows.find(p => p.id === correction.id)!.review_token])} source={data}
        payment={data.page.rows.find(p => p.id === correction.id)!} initialEdit={correction.edit} locked={locked} inputs={inputs}
        currentReadTicket={mutation.currentReadTicket} isReadCurrent={isReadCurrent} onClose={() => setCorrection(null)}
        onInvalid={message => { retire(); mutation.invalidate(); setError(message) }}
        onSave={document => { if (locked || !canReverse) return; retire(); void run('CORRECT', { document }, null, handlers) }}/>:null}
      {review && chosen ? <section className="cproc-review" aria-label="Periksa pembatalan pembayaran supplier"><h3>Periksa pembayaran yang akan dibalik</h3>
        <p>{chosen.number} · {money(chosen.amount)} · {originalTime(chosen.payment_date)}. Pembalikannya mengikuti tanggal pembukuan dari server dan menambah kembali sisa utang. Catatan asli tetap disimpan.</p>
        <fieldset disabled={locked || !freshReview}><label>Alasan pembatalan<textarea aria-label="Alasan pembatalan pembayaran supplier" maxLength={1000} value={reason}
          onChange={e => { setReasons(previous => ({ ...previous, [review.id]: e.target.value })); setReview({ ...review, checked: false }) }}/></label>
          <label><input type="checkbox" aria-label="Pembayaran supplier sudah diperiksa" checked={review.checked} onChange={e => setReview({ ...review, checked: e.target.checked })}/>Jumlah, sumber kas, tanggal, dan pembayaran ini sudah saya periksa.</label>
          <button disabled={!review.checked || reason.trim().length < 5 || !freshReview} onClick={reverse}>Balikkan pembayaran supplier sekarang</button></fieldset>
        <button disabled={mutation.busy} onClick={() => setReview(null)}>Tutup pemeriksaan pembayaran supplier</button>
      </section> : null}
    </> : null}
  </section>
}
