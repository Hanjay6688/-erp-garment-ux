import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal as numberText, parseProcurementOptions, procurementObject, type ProcurementOption } from './procurementContract'
import { blockerLabels, correctionDraft, correctionRefusal, correctionExcess, correctionInvoices, correctionPayload, draftHeader, parseReceiptCorrectionOutcome, parseReceiptCorrectionWorkspace, type DraftCredit, type DraftHeader, type DraftInvoice, type DraftLine, type ReceiptCorrectionWorkspace } from './receiptCorrectionContract'
import type { Json } from './types/database.preconnect'

type Props = { purchaseId: string | null; receiptRevision?: string | null; onReceiptUpdated: (purchaseId: string) => Promise<boolean> }
const REQUIRED = ['warehouse.procurement.view', 'warehouse.procurement.create', 'warehouse.procurement.post', 'warehouse.procurement.reverse', 'finance.ap.view']

export default function ReceiptCorrectionPanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !['OWNER', 'ADMIN'].includes(identity.profile.role) || !REQUIRED.every(p => identity.permissions.includes(p))) return null
  return <CorrectionWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} {...props}/>
}

function MaterialChoice({ client, value, disabled, onChange }: { client: ReturnType<typeof getUatSupabaseClient>; value: { id: string; name: string }; disabled: boolean; onChange: (m: ProcurementOption) => void }) {
  const [q, setQ] = useState(''), [rows, setRows] = useState<ProcurementOption[]>([]), [error, setError] = useState('')
  const search = async () => {
    setError('')
    try { const r = await client.rpc('erp_cp7_get_procurement_options_v1', { p_kind: 'MATERIAL', p_q: q.trim(), p_offset: 0, p_limit: 25 }); if (r.error) throw r.error; setRows(parseProcurementOptions(r.data, 'MATERIAL').rows) }
    catch (e) { setError(normalizeClientError(e).message) }
  }
  return <div className="cproc-picker"><label>Bahan yang benar<select aria-label="Bahan yang benar" value={value.id} disabled={disabled} onChange={e => { const m = rows.find(r => r.id === e.target.value); if (m) onChange(m) }}>
    <option value={value.id}>{value.name}</option>{rows.filter(r => r.id !== value.id).map(r => <option key={r.id} value={r.id}>{r.code} · {r.name}{r.unit_code ? ` · ${r.unit_code}` : ''}</option>)}</select></label>
    <div className="cproc-inline"><input aria-label="Cari bahan yang benar" placeholder="Cari kode atau nama bahan" value={q} maxLength={120} disabled={disabled} onChange={e => setQ(e.target.value)}/><button type="button" disabled={disabled} onClick={() => void search()}>Cari</button></div>
    {error ? <span role="alert">{error}</span> : <small>Pilih bahan lain hanya jika barang yang datang memang bahan berbeda. Untuk salah ketik nama, ubah nama di master bahan.</small>}</div>
}

function CorrectionWorkspace({ purchaseId, receiptRevision, onReceiptUpdated }: Props) {
  const { runtime } = useAuth(); if (!isConnectedRuntime(runtime)) throw Error('Sesi pembetulan penerimaan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), mutation = useProductionMutation('RECEIPT_CORRECTION')
  const { beginRead, finishRead, isReadCurrent, run, reconcile, invalidate } = mutation
  const [data, setData] = useState<ReceiptCorrectionWorkspace | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [lines, setLines] = useState<DraftLine[] | null>(null), [invoices, setInvoices] = useState<DraftInvoice[]>([]), [credits, setCredits] = useState<DraftCredit[]>([]), [reason, setReason] = useState(''), [header, setHeader] = useState<DraftHeader | null>(null), [checked, setChecked] = useState(false), [open, setOpen] = useState(false)
  const requested = useRef(purchaseId), sequence = useRef(0)
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead(), purchase = requested.current
    setLoading(true); setError('')
    try {
      if (!purchase) { setData(null); return false }
      const r = await client.rpc('erp_cp7_get_receipt_correction_v1', { p_purchase: purchase })
      if (!isReadCurrent(ticket) || s !== sequence.current) return false
      if (r.error) throw r.error
      setData(parseReceiptCorrectionWorkspace(r.data, purchase)); return finishRead(ticket)
    } catch (e) { if (isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }; return false }
    finally { if (s === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { if (mutation.busy) return; if (requested.current !== purchaseId) { requested.current = purchaseId; setLines(null); setInvoices([]); setCredits([]); setHeader(null); setChecked(false) }; if (open) void load() }, [purchaseId, receiptRevision, open, load, mutation.busy])
  const handlers: ProductionMutationHandlers = {
    send: async envelope => { const p = procurementObject(envelope.payload); const r = await client.rpc('erp_cp7_correct_receipt_v1', { p_payload: p.document as Json, p_request: envelope.id, p_expected: p.expected_version as string }); return { data: r.data, error: r.error ? correctionRefusal(r.error) : null } },
    validate: (r, e) => { const d = procurementObject(procurementObject(e.payload).document); parseReceiptCorrectionOutcome(r, e.id, d.purchase_id as string) },
    retire: (r, e) => { const d = procurementObject(procurementObject(e.payload).document); const out = parseReceiptCorrectionOutcome(r, e.id, d.purchase_id as string); requested.current = out.purchase_id; setLines(null); setInvoices([]); setCredits([]); setHeader(null); setChecked(false); setReason(''); setData(null); setOpen(true) },
    // The page first selects the replacement receipt (after the envelope is
    // cleared), then this panel reads its own workspace for the same receipt.
    reload: async () => { if (!requested.current || !await onReceiptUpdated(requested.current)) { invalidate(); setData(null); return false }; return load() },
  }
  const locked = mutation.writerLocked || loading
  const stale = Boolean(lines && data && data.purchase.purchase_id !== requested.current)
  const built = data && lines ? correctionPayload(data, lines, reason, invoices, credits, header ?? undefined) : null
  const excess = data && lines ? correctionExcess(data, lines, invoices) : null
  const change = (key: string, fn: (l: DraftLine) => DraftLine) => setLines(ls => ls ? ls.map(l => l.key === key ? fn(l) : l) : ls)
  const changeHead = (invoice: string, field: 'number' | 'date' | 'dueDate', value: string) => { setChecked(false); setInvoices(vs => vs.map(v => v.replaces !== invoice || !v.head ? v : { ...v, head: { ...v.head, [field]: value } })) }
  const changeInvoice = (invoice: string, line: string, field: 'qty' | 'price' | 'discount', value: string) => { setChecked(false); setInvoices(vs => vs.map(v => v.replaces !== invoice ? v : { ...v, lines: v.lines.map(l => l.replaces === line ? { ...l, [field]: value } : l) })) }
  // A pending result stays reachable after reload even before a receipt is selected (the receipt list is locked meanwhile).
  if (!purchaseId && !mutation.pending && !mutation.error) return null
  return <section className="panel cproc-invoices" aria-label="Benerin penerimaan">
    <div className="cproc-heading"><div><div className="eyebrow">PEMBETULAN PENERIMAAN</div><h2>Benerin penerimaan</h2><p>Untuk salah ketik jumlah, jumlah roll, harga (termasuk harga final di invoice supplier), atau salah pilih bahan pada penerimaan yang sudah diterima — termasuk yang bahannya sudah dipotong. Dokumen lama tetap tersimpan sebagai riwayat; saldo stok, HPP, dan utang mengikuti angka yang benar sejak tanggal barang datang.</p></div>
      {purchaseId ? <button type="button" disabled={mutation.busy} onClick={() => { setOpen(o => !o); if (!open) { requested.current = purchaseId } }}>{open ? 'Tutup' : 'Buka pembetulan'}</button> : null}</div>
    <ProductionRecoveryNotice recovery={{ ...mutation, notice: mutation.notice ? 'Pembetulan penerimaan sudah tercatat.' : '' }} onReconcile={() => reconcile(handlers)} className="cproc-review"/>
    {!open || !purchaseId ? null : loading && !data ? <p role="status">Memuat penerimaan…</p> : error ? <p role="alert">{error}</p> : data ? <>
      <p><strong>{data.purchase.purchase_number}</strong> · {data.purchase.supplier_name} · {data.purchase.location_name} · barang datang {formatCp6WibDateTime(data.purchase.physical_at)}</p>
      {data.history.length ? <details open><summary>Riwayat pembetulan ({data.history.length})</summary><ul>{data.history.map(h => <li key={h.revision_id}>R{h.revision} · {h.previous_purchase_number} → {h.replacement_purchase_number} · dicatat {formatCp6WibDateTime(h.recorded_at)}{h.actor_name ? ` oleh ${h.actor_name}` : ''} · berlaku sejak {formatCp6WibDateTime(h.effective_at)} · {h.reason}</li>)}</ul></details> : null}
      {data.blockers.length ? <div role="alert"><p>Penerimaan ini belum bisa dibenerin:</p><ul>{data.blockers.map(b => <li key={b.code}>{blockerLabels[b.code] ?? b.code}</li>)}</ul></div> : null}
      {data.payments.some(p => p.status === 'POSTED') ? <p className="cproc-help">Pembayaran supplier Rp{numberText(data.paid_total)} dipindahkan ke dokumen yang benar dengan tanggal pembayaran aslinya. Kalau total yang benar lebih kecil, kelebihannya jadi kredit yang dipotong ke nota lain dari supplier yang sama.</p> : null}
      {data.invoices.length ? <p className="cproc-help">Penerimaan ini sudah punya invoice supplier ({data.invoices.map(v => v.invoice_number).join(', ')}). Invoice ikut dibetulkan: yang lama dibatalkan dan yang benar dicatat ulang dengan tanggal invoice yang sama.</p> : null}
      {data.can_correct && !lines ? <button className="primary-btn" type="button" disabled={locked} onClick={() => { setLines(correctionDraft(data)); setInvoices(correctionInvoices(data)); setHeader(draftHeader(data)); setChecked(false) }}>Benerin penerimaan</button> : null}
      {lines ? <form onSubmit={e => { e.preventDefault(); if (built?.payload && checked && !locked && !stale) void run('CORRECT', { document: built.payload as Json, expected_version: data.purchase.row_version }, null, handlers) }}>
        {stale ? <p role="alert">Penerimaan sudah berubah. Tutup formulir dan muat ulang.</p> : null}
        <fieldset disabled={locked || stale}>
          {lines.map((l, n) => <section className="cproc-line" key={l.key}>
            <h3>Barang {n + 1}: {l.materialName}</h3>
            <div className="cproc-grid"><MaterialChoice client={client} value={{ id: l.materialId, name: l.materialName }} disabled={locked} onChange={m => change(l.key, old => ({ ...old, materialId: m.id, materialName: m.name, unitCode: m.unit_code ?? old.unitCode }))}/>
              <label>{l.priceState === 'FINAL' ? 'Harga' : 'Harga perkiraan saat terima'} per {l.unitCode}<input aria-label={`Harga benar barang ${n + 1}`} inputMode="decimal" value={l.price} onChange={e => change(l.key, old => ({ ...old, price: e.target.value }))}/></label></div>
            {l.materialType === 'FABRIC' ? <div className="cproc-rolls"><h4>Roll yang benar</h4>{l.rolls.map((r, ri) => <div className="cproc-inline" key={r.key}>
              <label>Nomor roll{r.replaces && r.number.trim() !== data.lines.flatMap(x => x.rolls).find(x => x.roll_id === r.replaces)?.roll_number ? ` · tadinya ${data.lines.flatMap(x => x.rolls).find(x => x.roll_id === r.replaces)?.roll_number}` : ''}<input aria-label={`Nomor roll benar ${n + 1}.${ri + 1}`} maxLength={80} value={r.number} onChange={e => change(l.key, old => ({ ...old, rolls: old.rolls.map(x => x.key === r.key ? { ...x, number: e.target.value } : x) }))}/></label>
              <label>Jumlah ({l.unitCode}){r.locked ? ` · sudah terpakai ${numberText(r.minQty)}` : ''}<input aria-label={`Jumlah roll benar ${n + 1}.${ri + 1}`} inputMode="decimal" value={r.qty} onChange={e => change(l.key, old => ({ ...old, rolls: old.rolls.map(x => x.key === r.key ? { ...x, qty: e.target.value } : x) }))}/></label>
              <button type="button" disabled={r.locked} title={r.locked ? 'Roll ini sudah terpakai sehingga tidak bisa dihapus' : undefined} onClick={() => change(l.key, old => ({ ...old, rolls: old.rolls.filter(x => x.key !== r.key) }))}>Hapus roll {ri + 1}</button></div>)}
              <button type="button" onClick={() => change(l.key, old => ({ ...old, rolls: [...old.rolls, { key: crypto.randomUUID(), replaces: null, number: '', qty: '', minQty: '0', locked: false }] }))}>Tambah roll yang terlewat</button></div>
              : <label>Jumlah benar ({l.unitCode}){Number(l.minQty) > 0 ? ` · sudah keluar ${numberText(l.minQty)}` : ''}<input aria-label={`Jumlah benar barang ${n + 1}`} inputMode="decimal" value={l.qty} onChange={e => change(l.key, old => ({ ...old, qty: e.target.value }))}/></label>}
          </section>)}
          {invoices.length ? <section className="cproc-line" aria-label="Invoice supplier yang ikut dibetulkan"><h3>Invoice supplier</h3>
            <p className="cproc-help">Harga final dan jumlah ditagih mengikuti invoice yang benar. HPP, nilai stok, dan utang dihitung ulang sejak tanggal invoice; tidak ada selisih yang dicatat di hari ini.</p>
            {invoices.map((v, vi) => <div key={v.replaces}><h4>{v.number} · tanggal invoice {v.date.split('-').reverse().join('-')}</h4>
              {v.head ? <div className="cproc-grid">
                <label>Nomor invoice supplier<input aria-label={`Nomor invoice benar ${vi + 1}`} maxLength={90} value={v.head.number} onChange={e => changeHead(v.replaces, 'number', e.target.value)}/></label>
                <label>Tanggal invoice<input aria-label={`Tanggal invoice benar ${vi + 1}`} type="date" value={v.head.date} onChange={e => changeHead(v.replaces, 'date', e.target.value)}/></label>
                <label>Jatuh tempo<input aria-label={`Jatuh tempo invoice benar ${vi + 1}`} type="date" value={v.head.dueDate} onChange={e => changeHead(v.replaces, 'dueDate', e.target.value)}/></label></div> : null}
              {data.invoices.find(x => x.invoice_id === v.replaces)?.other_receipts.length ? <p className="cproc-help">Invoice ini juga mencakup {data.invoices.find(x => x.invoice_id === v.replaces)!.other_receipts.map(o => o.purchase_number).join(', ')}. Baris penerimaan itu ikut dicatat ulang apa adanya, dan pembayarannya dipindah utuh dengan tanggal aslinya.</p> : null}
              {v.lines.map((x, li) => <div className="cproc-inline" key={x.replaces}><span>{lines.find(l => l.replaces === x.itemId)?.materialName ?? 'Barang'}</span>
                <label>Jumlah ditagih<input aria-label={`Jumlah ditagih invoice ${vi + 1}.${li + 1}`} inputMode="decimal" value={x.qty} onChange={e => changeInvoice(v.replaces, x.replaces, 'qty', e.target.value)}/></label>
                <label>Harga final<input aria-label={`Harga final invoice ${vi + 1}.${li + 1}`} inputMode="decimal" value={x.price} onChange={e => changeInvoice(v.replaces, x.replaces, 'price', e.target.value)}/></label>
                <label>Diskon (Rp)<input aria-label={`Diskon invoice ${vi + 1}.${li + 1}`} inputMode="decimal" value={x.discount} onChange={e => changeInvoice(v.replaces, x.replaces, 'discount', e.target.value)}/></label></div>)}</div>)}
          </section> : null}
          {excess && excess !== '0.00' ? <section className="cproc-line" aria-label="Kredit kelebihan bayar"><h3>Kelebihan bayar Rp{numberText(excess)}</h3>
            <p className="cproc-help">Sudah dibayar lebih dari total yang benar. Kelebihannya jadi kredit supplier (retur bayangan: barang tidak pernah diterima) dan dipotong ke nota lain dari supplier yang sama, dengan tanggal dan kas pembayaran aslinya. Tidak ada uang yang berpindah hari ini.</p>
            {data.credit_targets.length ? data.credit_targets.map((t, ti) => <div className="cproc-inline" key={t.purchase_id}><span>{t.purchase_number} · {formatCp6WibDateTime(t.physical_at)} · sisa utang Rp{numberText(t.remaining)}</span>
              <label>Potong kredit (Rp)<input aria-label={`Kredit ke nota ${ti + 1}`} inputMode="decimal" value={credits.find(c => c.purchaseId === t.purchase_id)?.amount ?? ''}
                onChange={e => { const amount = e.target.value; setChecked(false); setCredits(cs => [...cs.filter(c => c.purchaseId !== t.purchase_id), { purchaseId: t.purchase_id, amount }]) }}/></label></div>)
              : <p role="alert">Belum ada nota lain dari supplier ini yang masih punya sisa utang. Simpan pembetulan setelah nota berikutnya dicatat.</p>}
          </section> : null}
          {header ? <section className="cproc-line" aria-label="Data surat jalan"><h3>Surat jalan</h3>
            <label>Nomor surat jalan{header.purchaseNumber.trim() !== draftHeader(data).purchaseNumber ? ` · tadinya ${draftHeader(data).purchaseNumber}` : ''}<input aria-label="Nomor surat jalan yang benar" maxLength={40} value={header.purchaseNumber} onChange={e => { const v = e.target.value; setChecked(false); setHeader({ purchaseNumber: v }) }}/></label>
          </section> : null}
          <label>Alasan pembetulan<input aria-label="Alasan pembetulan penerimaan" value={reason} maxLength={500} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
          {built?.problem ? <p role="alert">{built.problem}</p> : null}
          <label className="cproc-check"><input type="checkbox" aria-label="Pembetulan penerimaan sudah diperiksa" checked={checked} onChange={e => setChecked(e.target.checked)}/>Saya sudah mencocokkan dengan surat jalan / barang fisik. Stok, HPP, dan utang akan dihitung ulang sejak tanggal barang datang.</label>
          <div className="cproc-actions"><button className="primary-btn" disabled={!built?.payload || !checked}>Simpan pembetulan</button><button type="button" disabled={mutation.busy} onClick={() => { setLines(null); setInvoices([]); setCredits([]); setHeader(null); setChecked(false) }}>Batal</button></div>
        </fieldset></form> : null}
    </> : null}
  </section>
}
