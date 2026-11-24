import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal, procurementObject } from './procurementContract'
import { parseSwitchRollOutcome, parseSwitchRollPreview, parseSwitchRollWorkspace, type SwitchRollImpact,
  type SwitchRollPayload, type SwitchRollPreview, type SwitchRollReceipt, type SwitchRollWorkspace } from './switchRollContract'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import type { Json } from './types/database.preconnect'

type Props = {
  purchaseId: string | null
  receiptRevision?: string | null
  receiptDraft?: SwitchRollReceipt | null
  onReceiptUpdated: (purchaseId: string) => Promise<boolean>
}
const required = ['production.cutting.view', 'production.cutting.post', 'finance.hpp.view', 'sales.invoice.view']
const amount = (value: string | null) => value === null ? 'Belum diketahui' : `Rp${formatReceiptDecimal(value)}`
const date = (value: string) => value.split('-').reverse().join('/')

export default function SwitchRollPanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !required.every(p => identity.permissions.includes(p))) return null
  return <SwitchRollWorkspacePanel key={`${runtime.projectRef}:${identity.profile.id}:${identity.permissions.join('|')}`} {...props}/>
}

function Impact({ impact }: { impact: SwitchRollImpact }) {
  const { before, after } = impact
  const changedOrders = Object.entries(after.orders).filter(([id, row]) => JSON.stringify(before.orders[id]) !== JSON.stringify(row))
  const changedSales = Object.entries(after.sales).filter(([id, row]) => before.sales[id]?.cogs !== row.cogs || row.cogs === null)
  return <div className="cproc-review" aria-label="Dampak Ganti roll">
    <h4>{impact.from_number} → {impact.to_number}</h4>
    <p>{impact.cut_number} · {formatReceiptDecimal(impact.qty)} {impact.unit} · potong {formatCp6WibDateTime(impact.physical_at)}</p>
    {impact.closed_through && impact.effective_date <= impact.closed_through
      ? <p role="status">Periode ditutup sampai {date(impact.closed_through)}. Tanggal ekonomi {date(impact.effective_date)}. Jurnal koreksi diakui pada {date(impact.recognition_date)}.</p> : null}
    <h4>Saldo bahan</h4>
    <ul>{Object.entries(after.materials).map(([id, row]) => <li key={id}>{row.code} · {row.name}: {formatReceiptDecimal(before.materials[id].qty)} → <strong>{formatReceiptDecimal(row.qty)} {row.unit}</strong>
      <br/><small>Biaya rata-rata per {row.unit} {amount(before.materials[id].average)} → {amount(row.average)}</small></li>)}</ul>
    {changedOrders.length ? <><h4>Nilai di buku per PO</h4><ul>{changedOrders.map(([id, row]) => <li key={id}><strong>{row.number}</strong><br/>
      WIP {amount(before.orders[id].wip)} → {amount(row.wip)}<br/>
      Barang jadi {amount(before.orders[id].fg)} → {amount(row.fg)}<br/>
      HPP terjual {amount(before.orders[id].cogs)} → {amount(row.cogs)}</li>)}</ul></> : null}
    {changedSales.length ? <><h4>Nota penjualan terdampak</h4><ul>{changedSales.map(([id, row]) => <li key={id}><strong>{row.number}</strong> · {date(row.date)}<br/>
      Penjualan bersih {amount(row.sales)}<br/>HPP {amount(before.sales[id].cogs)} → {amount(row.cogs)}<br/>
      Laba kotor {amount(before.sales[id].margin)} → {amount(row.margin)}</li>)}</ul></> : <p>HPP nota penjualan tidak berubah.</p>}
  </div>
}

function SwitchRollWorkspacePanel({ purchaseId, receiptRevision, receiptDraft, onReceiptUpdated }: Props) {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi Ganti roll belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('SWITCH_ROLL')
  const { beginRead, isReadCurrent, finishRead, invalidate } = mutation
  const requested = useRef(purchaseId)
  const committed = useRef<string | null>(null)
  const [open, setOpen] = useState(false)
  const [workspace, setWorkspace] = useState<SwitchRollWorkspace | null>(null)
  const [issue, setIssue] = useState('')
  const [destination, setDestination] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [reason, setReason] = useState('')
  const [includeReceipt, setIncludeReceipt] = useState(false)
  const [review, setReview] = useState<{ key: string; result: SwitchRollPreview } | null>(null)
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async (selected: string | null = null, term = '', page = 0) => {
    const purchase = requested.current
    if (!purchase) return false
    const ticket = beginRead()
    setReview(null); setError(''); setLoading(true)
    try {
      const result = await client.rpc('erp_cp7_get_switch_roll_v1', { p_purchase: purchase, p_issue: selected, p_query: term, p_offset: page })
      if (!isReadCurrent(ticket)) return false
      if (result.error) throw result.error
      setWorkspace(parseSwitchRollWorkspace(result.data, purchase, selected)); setOffset(page)
      return finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket)) { setWorkspace(null); setError(normalizeClientError(failure).message) }
      return false
    } finally { if (isReadCurrent(ticket)) setLoading(false) }
  }, [client, beginRead, isReadCurrent, finishRead])

  useEffect(() => {
    requested.current = purchaseId
    if (!open && !committed.current) return
    if (committed.current && committed.current !== purchaseId) return
    setDestination(''); setIssue(''); setChecking(false); setWorkspace(null)
    void load()
  }, [purchaseId, receiptRevision, open, load])

  const payload: SwitchRollPayload | null = purchaseId && issue && destination && reason.trim().length >= 5 && (!includeReceipt || receiptDraft)
    ? { purchase_id: purchaseId, issue_id: issue, new_roll_id: destination, reason: reason.trim(),
      ...(includeReceipt && receiptDraft ? { receipt: receiptDraft } : {}) } : null
  const payloadKey = payload ? JSON.stringify(payload) : null
  const reviewed = payloadKey && review?.key === payloadKey && !mutation.workspaceStale ? review.result : null
  const preview = async () => {
    if (!payload || !payloadKey || mutation.writerLocked || loading || checking) return
    const ticket = beginRead()
    setReview(null); setError(''); setChecking(true)
    try {
      const result = await client.rpc('erp_cp7_preview_switch_roll_v1', { p_payload: payload })
      if (!isReadCurrent(ticket)) return
      if (result.error) throw result.error
      const value = parseSwitchRollPreview(result.data, payload)
      if (finishRead(ticket)) setReview({ key: payloadKey, result: value })
    } catch (failure) {
      if (isReadCurrent(ticket)) {
        const problem = normalizeClientError(failure)
        if (problem.code === 'AUTH_REQUIRED' || problem.code === 'FORBIDDEN') setWorkspace(null)
        else finishRead(ticket)
        setError(problem.message)
      }
    } finally { setChecking(false) }
  }

  const handlers: ProductionMutationHandlers = {
    send: async envelope => {
      const p = procurementObject(envelope.payload)
      return client.rpc('erp_cp7_switch_roll_v1', { p_payload: p.document as Json, p_request: envelope.id, p_review: p.review as string })
    },
    validate: (value, envelope) => { parseSwitchRollOutcome(value, envelope.id, procurementObject(envelope.payload).document as SwitchRollPayload) },
    retire: (value, envelope) => {
      committed.current = parseSwitchRollOutcome(value, envelope.id).purchase_id
      setIssue(''); setDestination(''); setReason(''); setIncludeReceipt(false); setReview(null); setWorkspace(null); setOpen(true)
    },
    reload: async () => {
      const purchase = committed.current
      if (!purchase || !await onReceiptUpdated(purchase)) { invalidate(); return false }
      requested.current = purchase
      committed.current = null
      return load()
    },
  }

  if (!purchaseId && !mutation.pending && !mutation.error) return null
  const data = mutation.workspaceStale && !checking ? null : workspace
  const choice = data?.issues.find(x => x.issue_id === issue)
  const blocked = loading || checking || mutation.busy || Boolean(mutation.pending) || mutation.externalMutationBlocked
  return <section className="cproc-line" aria-label="Ganti roll sumber pemakaian">
    <h3>Ganti roll sumber pemakaian</h3>
    {purchaseId ? <button type="button" disabled={mutation.busy} onClick={() => setOpen(v => !v)}>{open ? 'Tutup Ganti roll' : 'Buka Ganti roll'}</button> : null}
    {(mutation.pending || mutation.notice || mutation.error) ? <ProductionRecoveryNotice recovery={mutation}
      noticeText="Koreksi roll sudah tercatat." onReconcile={() => mutation.reconcile(handlers)} className="cproc-review"/> : null}
    {!open || !purchaseId ? null : <>
      {loading ? <p role="status">Memuat pemakaian dan saldo roll…</p> : null}
      {checking ? <p role="status">Menghitung dampak ke stok, HPP, dan nota…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {!loading && !checking && !data ? <button type="button" disabled={blocked} onClick={() => { setIssue(''); setDestination(''); void load() }}>Muat ulang Ganti roll</button> : null}
      {data && !data.issues.length ? <p>Belum ada pemakaian potong aktif dari penerimaan ini.</p> : null}
      {data?.issues.length ? <fieldset disabled={blocked}>
        <label>Pemakaian yang salah<select value={issue} onChange={e => {
          const value = e.target.value
          setIssue(value); setDestination(''); setQuery(''); void load(value || null)
        }}><option value="">Pilih potongan dan roll</option>{data.issues.map(x => <option key={x.issue_id} value={x.issue_id}>{x.cut_number} · {x.roll_number} · {x.material_name} · {formatReceiptDecimal(x.qty)} {x.unit_code}</option>)}</select></label>
        {choice ? <>
          <p>{choice.roll_number} · {formatReceiptDecimal(choice.qty)} {choice.unit_code} · {formatCp6WibDateTime(choice.physical_at)}</p>
          <div className="cproc-inline"><label>Cari roll yang benar<input value={query} maxLength={120} onChange={e => setQuery(e.target.value)}/></label>
            <button type="button" onClick={() => { setDestination(''); void load(issue, query) }}>Cari roll</button></div>
          <label>Roll yang benar<select value={destination} onChange={e => { setDestination(e.target.value); setReview(null) }}>
            <option value="">Pilih roll yang dipakai secara fisik</option>{data.rolls.map(r => <option key={r.roll_id} value={r.roll_id}>
              {r.roll_number} · {r.material_sku} {r.material_name} · {r.purchase_number ?? 'Saldo awal'} · {formatReceiptDecimal(r.qty_at_cut)} {r.unit_code} saat potong
            </option>)}</select></label>
          {!data.rolls.length ? <p>Roll yang memenuhi saldo saat potong tidak ditemukan.</p> : null}
          {(offset > 0 || data.next_offset !== null) ? <div className="cproc-inline">
            <button type="button" disabled={!offset} onClick={() => { setDestination(''); void load(issue, query, offset - 25) }}>Roll sebelumnya</button>
            <button type="button" disabled={data.next_offset === null} onClick={() => { setDestination(''); void load(issue, query, data.next_offset ?? 0) }}>Roll berikutnya</button>
          </div> : null}
          {receiptDraft || includeReceipt ? <label className="cproc-check"><input type="checkbox" checked={includeReceipt} onChange={e => { setIncludeReceipt(e.target.checked); setReview(null) }}/>Simpan juga revisi penerimaan di atas</label> : null}
          {includeReceipt && !receiptDraft ? <p role="status">Lengkapi dulu revisi penerimaan di atas.</p> : null}
          <label>Alasan ganti roll<input value={reason} maxLength={500} onChange={e => { setReason(e.target.value); setReview(null) }}/></label>
          <button type="button" disabled={!payload || mutation.writerLocked} onClick={() => void preview()}>Tinjau dampak Ganti roll</button>
          {reviewed && payload ? <><Impact impact={reviewed.impact}/><button className="primary-btn" type="button" disabled={mutation.writerLocked} onClick={() => {
            setReview(null); setError('')
            void mutation.run('SWITCH', { document: payload, review: reviewed.review_token }, null, handlers)
          }}>Simpan Ganti roll</button></> : null}
        </> : null}
      </fieldset> : null}
      {data?.history.length ? <details><summary>Riwayat Ganti roll ({data.history.length})</summary><ul>{data.history.map(row => <li key={row.correction_id}>
        {formatCp6WibDateTime(row.recorded_at)} · {row.reason}<Impact impact={row.impact}/></li>)}</ul></details> : null}
    </>}
  </section>
}
