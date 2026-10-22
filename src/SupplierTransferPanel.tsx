import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatReceiptDecimal } from './procurementContract'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { salesCashAmount } from './salesCashContract'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import { financialRecoveryBlocked, useFinancialRecoveryGate } from './useFinancialRecoveryGate'
import { useRetainedFormInput, useRetainedInput } from './useRetainedFormInput'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {
  centsText, parseSupplierTransferOutcome, parseSupplierTransferWorkspace, supplierTransferPayload, transferCents,
  type SupplierTransferPayload, type SupplierTransferQuery, type SupplierTransferWorkspace,
} from './supplierTransferContract'
import type { Json } from './types/database.preconnect'

const rupiah = (c: bigint) => `Rp${formatReceiptDecimal(centsText(c))}`
const money = (v: string) => `Rp${formatReceiptDecimal(v)}`
/** Typed input to an exact two-decimal amount, or null. */
function amountText(v: string) {
  const n = salesCashAmount(v)
  if (n === null) return null
  const [a, b = ''] = n.split('.')
  return `${a}.${b.padEnd(2, '0')}`
}
type Mode = 'NONE' | 'CREATE' | 'CORRECT' | 'REVERSE'
/** One chosen receipt; `payable` is the server amount seen when chosen (null for a preloaded correction row not yet shown). */
type Allocation = { number: string; amount: string; payable: string | null; physical_at: string | null; token: string }
type Props = {
  supplierId: string | null; currentPurchaseId: string | null; parentReady: boolean; receiptRevision: string
  focusTransferId: string | null; onReceiptUpdated: (purchaseId: string) => Promise<boolean>
}

export default function SupplierTransferPanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return null
  const key = JSON.stringify([runtime.projectRef, identity.profile.id, identity.profile.authUserId,
    identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions])
  return <SupplierTransferWorkspaceView key={key} {...props}/>
}

function SupplierTransferWorkspaceView({ supplierId, currentPurchaseId, parentReady, receiptRevision, focusTransferId, onReceiptUpdated }: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw Error('Sesi transfer supplier belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('SUPPLIER_TRANSFER'), { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const authority = JSON.stringify([runtime.projectRef, identity.profile.id, identity.profile.authUserId,
    identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions])
  const canWrite = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && ['warehouse.procurement.view', 'finance.ap.view', 'finance.ap.pay'].every(p => identity.permissions.includes(p))
  const inputs = useRetainedFormInput(authority, mutation.committedSequence)
  const pendingSupplier = (() => {
    const p = mutation.pending?.payload
    if (!p || typeof p !== 'object' || Array.isArray(p)) return null
    const d = (p as { document?: Json }).document
    return d && typeof d === 'object' && !Array.isArray(d) && typeof d.supplier_id === 'string' ? d.supplier_id : null
  })()
  const supplier = supplierId ?? pendingSupplier
  const blank = (s: string | null, transfer: string | null): SupplierTransferQuery =>
    ({ supplier_id: s ?? '', transfer_id: transfer, purchase_q: '', purchase_offset: 0, bank_q: '', bank_offset: 0, transfer_offset: 0 })
  const requested = useRef<SupplierTransferQuery>(blank(supplier, focusTransferId))
  if (requested.current.supplier_id !== (supplier ?? '')) requested.current = blank(supplier, focusTransferId)
  const [capture, setCapture] = useState<{ authority: string; ticket: ReturnType<typeof beginRead>; data: SupplierTransferWorkspace } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [mode, setMode] = useState<Mode>('NONE'), [checked, setChecked] = useState(false)
  const [purchaseSearch, setPurchaseSearch] = useState(''), [bankSearch, setBankSearch] = useState('')
  const formKey = `supplierTransfer.${supplier ?? ''}.`
  const [allocations, setAllocations] = useRetainedInput<Record<string, Allocation>>(inputs, formKey + 'allocations', {})
  const [bank, setBank] = useRetainedInput<{ id: string; name: string } | null>(inputs, formKey + 'bank', null)
  const [at, setAt] = useRetainedInput(inputs, formKey + 'at', '')
  const [reason, setReason] = useRetainedInput(inputs, formKey + 'reason', '')
  const sequence = useRef(0)
  const retire = useCallback(() => { ++sequence.current; setCapture(null); setChecked(false); setBusy(false) }, [])
  const blocked = useFinancialRecoveryGate(mutation.scope, retire)
  const load = useCallback(async () => {
    retire(); setError('')
    const q = { ...requested.current }
    if (!parentReady || !q.supplier_id || financialRecoveryBlocked(mutation.scope)) return false
    const current = ++sequence.current, ticket = beginRead(); setBusy(true)
    try {
      const r = await client.rpc('erp_cp7_get_supplier_transfer_v1', { p_query: q as unknown as Json })
      if (current !== sequence.current || !isReadCurrent(ticket) || financialRecoveryBlocked(mutation.scope)) return false
      if (r.error) throw r.error
      const next = parseSupplierTransferWorkspace(r.data, q)
      if (next.can_write !== canWrite) throw Error('Hak transfer supplier berubah. Muat ulang sesi dan transfer supplier.')
      const ready = finishRead(ticket)
      if (!isReadCurrent(ticket)) return false
      setCapture({ authority, ticket, data: next }); return ready
    } catch (e) {
      if (current === sequence.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (current === sequence.current) setBusy(false) }
  }, [client, parentReady, mutation.scope, canWrite, authority, beginRead, finishRead, isReadCurrent, retire])
  useEffect(() => {
    if (focusTransferId && requested.current.transfer_id !== focusTransferId) { requested.current = { ...requested.current, transfer_id: focusTransferId }; setMode('NONE') }
  }, [focusTransferId])
  useEffect(() => { if (parentReady) void load(); else retire(); return () => { ++sequence.current } }, [load, supplier, receiptRevision, parentReady, focusTransferId, retire])
  const data = parentReady && !blocked && capture?.authority === authority && isReadCurrent(capture.ticket)
    && capture.data.supplier.id === supplier ? capture.data : null
  const locked = busy || mutation.writerLocked, readBusy = busy || mutation.busy || blocked
  const selected = data?.selected ?? null
  const seek = (change: Partial<SupplierTransferQuery>) => { requested.current = { ...requested.current, ...change }; void load() }

  // Allocation arithmetic is exact cents; the total is always the sum of the rows.
  const rows = Object.entries(allocations)
  const parsed = rows.map(([id, a]) => {
    const exact = amountText(a.amount), cents = exact === null ? null : transferCents(exact)
    const payable = a.payable === null ? null : transferCents(a.payable)
    const valid = cents !== null && cents > 0n && (payable === null || cents <= payable)
    return { id, a, exact, cents, payable, valid }
  })
  const total = parsed.reduce((s, r) => s + (r.cents ?? 0n), 0n)
  const latestReceipt = parsed.reduce<number>((m, r) => r.a.physical_at ? Math.max(m, Date.parse(r.a.physical_at)) : m, 0)
  const physical = cp6WibPhysicalTimeToIso(at)
  const validTime = physical !== null && Date.parse(physical) <= Date.now() && Date.parse(physical) >= latestReceipt
  const staleChoice = Boolean(data && parsed.some(r => r.a.token !== data.review_token))
  const payload: SupplierTransferPayload | null = !data || !canWrite || !data.can_write ? null
    : mode === 'REVERSE' ? (selected && selected.status === 'POSTED' && reason.trim().length >= 5 && reason.trim().length <= 500
      ? { action: 'REVERSE', supplier_id: data.supplier.id, transfer_id: selected.id, review_token: data.review_token, reason: reason.trim() } : null)
    : (mode === 'CREATE' || mode === 'CORRECT') && parsed.length && parsed.every(r => r.valid) && bank && validTime
      ? supplierTransferPayload({ action: mode, supplier_id: data.supplier.id, transfer_id: selected?.id, review_token: data.review_token,
        reason, cash_account_id: bank.id, payment_date: physical! }, parsed.map(r => ({ purchase_id: r.id, amount: r.exact! })))
      : null
  const ready = Boolean(payload && checked && !locked && !readBusy)

  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_cp7_save_supplier_transfer_v1', { p_payload: (envelope.payload as { document: Json }).document, p_request: envelope.id }),
    validate: (value, envelope) => { parseSupplierTransferOutcome(value, envelope.id, (envelope.payload as { document: Json }).document) },
    retire: (value, envelope) => {
      const result = parseSupplierTransferOutcome(value, envelope.id, (envelope.payload as { document: Json }).document)
      requested.current = { ...blank(result.supplier_id, result.transfer_id) }
      setAllocations({}); setReason(''); setBank(null); setAt(''); setMode('NONE'); retire()
    },
    reload: async () => {
      if (currentPurchaseId && !await onReceiptUpdated(currentPurchaseId)) { retire(); mutation.invalidate(); return false }
      return load()
    },
  }
  const save = () => { if (!ready || !payload) return; const document = payload as unknown as Json; retire(); void run(payload.action, { document }, null, handlers) }
  const start = (next: Mode) => {
    setChecked(false); setError(''); setReason(''); setAllocations({})
    if (next === 'CORRECT' && selected) {
      setAllocations(Object.fromEntries(selected.allocations.map(a => [a.purchase_id,
        { number: a.purchase_number, amount: a.amount, payable: null, physical_at: null, token: data!.review_token }])))
      setBank({ id: selected.cash_account_id, name: selected.cash_name }); setAt(cp6WibDateTimeInput(selected.payment_date))
    }
    if (next === 'CREATE') { requested.current = { ...requested.current, transfer_id: null }; setBank(null); setAt(cp6WibDateTimeInput()) }
    setMode(next)
    if (next === 'CREATE') void load()
  }
  const choose = (r: SupplierTransferWorkspace['receipts']['rows'][number], amount: string) => {
    if (!data) return
    const payable = mode === 'CORRECT' ? r.payable_after_release : r.remaining
    setChecked(false)
    setAllocations(previous => ({ ...previous, [r.id]: { number: r.number, amount, payable, physical_at: r.physical_at, token: data.review_token } }))
  }
  const drop = (id: string) => { setChecked(false); setAllocations(previous => { const next = { ...previous }; delete next[id]; return next }) }

  return <section className="panel cproc-invoices" aria-label="Transfer supplier">
    <header className="cproc-heading"><h2>Transfer supplier · satu pembayaran untuk beberapa penerimaan</h2>
      <button disabled={readBusy} onClick={() => void load()}>Muat ulang transfer supplier</button></header>
    <ProductionRecoveryNotice recovery={mutation} className="cproc-review" onReconcile={() => reconcile(handlers)}
      noticeText="Transfer supplier sudah diperbarui. Catatan terbaru sudah dimuat."
      messageText={mutation.pending && !mutation.corruptedEnvelope ? 'Hasil transfer belum pasti. Periksa transfer yang sama sebelum mencatat tindakan lain.' : undefined}
      reconcileLabel="Periksa status transfer supplier"/>
    {error ? <p role="alert">{error}</p> : null}{busy ? <p role="status">Memuat transfer supplier…</p> : null}
    {!supplier ? <p>Pilih penerimaan supplier untuk melihat atau membuat transfer.</p> : null}
    {blocked && !mutation.pending ? <p>Angka transfer menunggu pemulihan transaksi yang belum dipastikan.</p> : null}
    {data ? <>
      <p><strong>{data.supplier.name}</strong> · data diperiksa {formatCp6WibDateTime(data.captured_at)}</p>
      {!data.can_write ? <p>Transfer supplier hanya dapat dicatat, dibatalkan, atau dikoreksi Owner/Admin dengan hak bayar utang.</p> : null}
      {data.can_write && mode === 'NONE' ? <button disabled={locked} onClick={() => start('CREATE')}>Buat transfer supplier baru</button> : null}

      <section aria-label="Daftar transfer supplier"><h3>Transfer tercatat</h3>
        {data.transfers.rows.map(t => <article className="cproc-item" key={t.id} data-supplier-transfer-id={t.id}>
          <p>{t.number} · {money(t.amount)} · {formatCp6WibDateTime(t.payment_date)} · {t.status === 'POSTED' ? 'Tercatat' : t.status === 'REVERSED' ? 'Sudah dibalik' : 'Belum disahkan'}</p>
          <button disabled={readBusy} onClick={() => { setMode('NONE'); seek({ transfer_id: t.id }) }}>Buka transfer {t.number}</button>
        </article>)}
        {!data.transfers.rows.length ? <p>Belum ada transfer untuk supplier ini.</p> : null}
        <div className="cproc-pagination"><span>Total {data.transfers.total} transfer</span>
          <button disabled={readBusy || !data.transfers.offset} onClick={() => seek({ transfer_offset: Math.max(0, data.transfers.offset - 25) })}>Transfer sebelumnya</button>
          <button disabled={readBusy || data.transfers.next_offset === null} onClick={() => seek({ transfer_offset: data.transfers.next_offset ?? 0 })}>Transfer berikutnya</button></div>
      </section>

      {selected ? <section className="cproc-review" aria-label={`Rincian transfer ${selected.number}`}>
        <h3>{selected.number} · {money(selected.amount)}</h3>
        <p>{selected.status === 'POSTED' ? 'Tercatat' : 'Sudah dibalik'} · {formatCp6WibDateTime(selected.payment_date)} · {selected.cash_name}</p>
        <p>Keterangan: {selected.note}</p>
        <p>Kas keluar satu kali: jurnal {selected.journal.number} · tanggal pembukuan {selected.journal.accounting_date}{selected.journal.period_shifted ? ' · beralih ke periode terbuka' : ''}</p>
        {selected.inverse ? <p>Pembalik {selected.inverse.number} · tanggal pembukuan {selected.inverse.accounting_date}. Catatan asli tetap disimpan.</p> : null}
        <table><thead><tr><th>Penerimaan</th><th>Dibayar dari transfer ini</th></tr></thead>
          <tbody>{selected.allocations.map(a => <tr key={a.purchase_id}><td>{a.purchase_number}</td><td>{money(a.amount)}</td></tr>)}</tbody>
          <tfoot><tr><td>Total</td><td>{money(selected.amount)}</td></tr></tfoot></table>
        {selected.previous_id ? <button disabled={readBusy} onClick={() => { setMode('NONE'); seek({ transfer_id: selected.previous_id }) }}>Buka transfer sebelum koreksi</button> : null}
        {selected.replacement_id ? <button disabled={readBusy} onClick={() => { setMode('NONE'); seek({ transfer_id: selected.replacement_id }) }}>Buka transfer pengganti</button> : null}
        {data.can_write && selected.status === 'POSTED' && mode === 'NONE' ? <>
          <button disabled={locked} onClick={() => start('CORRECT')}>Koreksi transfer {selected.number}</button>
          <button disabled={locked} onClick={() => start('REVERSE')}>Batalkan transfer {selected.number}</button></> : null}
        <p>Pembayaran per penerimaan dari transfer ini hanya bisa dibatalkan atau dikoreksi lewat transfer ini, tidak satu per satu.</p>
      </section> : null}

      {mode === 'CREATE' || mode === 'CORRECT' ? <form className="cproc-review" aria-label={mode === 'CREATE' ? 'Transfer supplier baru' : 'Koreksi transfer supplier'}
        onSubmit={e => { e.preventDefault(); save() }} onChange={() => setChecked(false)}>
        <h3>{mode === 'CREATE' ? 'Transfer baru' : `Koreksi ${selected?.number ?? ''}`}</h3>
        <p>Pilih penerimaan dan isi jumlah yang dibayar untuk masing-masing. Boleh bayar sebagian; sisa utang tetap tercatat.
          Total transfer = jumlah semua baris. Kas/bank keluar satu kali sebesar total itu.{mode === 'CORRECT' ? ' Transfer lama dibalik dan diganti; catatan lama tetap disimpan.' : ''}</p>
        <fieldset className="cproc-fieldset" disabled={locked || readBusy}>
          <label>Cari nomor penerimaan<input aria-label="Cari penerimaan untuk transfer" maxLength={120} value={purchaseSearch}
            onChange={e => setPurchaseSearch(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); seek({ purchase_q: purchaseSearch.trim(), purchase_offset: 0 }) } }}/></label>
          <button type="button" onClick={() => seek({ purchase_q: purchaseSearch.trim(), purchase_offset: 0 })}>Cari penerimaan untuk transfer</button>
          <table aria-label="Penerimaan yang masih punya utang"><thead><tr><th>Penerimaan</th><th>{mode === 'CORRECT' ? 'Bisa dibayar (termasuk alokasi lama)' : 'Sisa utang'}</th><th>Dibayar</th></tr></thead>
            <tbody>{data.receipts.rows.map(r => {
              const payable = mode === 'CORRECT' ? r.payable_after_release : r.remaining, own = allocations[r.id]
              return <tr key={r.id} data-transfer-receipt-id={r.id}><td>{r.number}<br/><small>diterima {formatCp6WibDateTime(r.physical_at)}</small></td><td>{money(payable)}</td>
                <td><input aria-label={`Dibayar untuk ${r.number}`} inputMode="decimal" value={own?.amount ?? ''}
                  onChange={e => e.target.value.trim() === '' ? drop(r.id) : choose(r, e.target.value)}/>
                  <button type="button" onClick={() => choose(r, payable)}>Bayar penuh {r.number}</button></td></tr>
            })}</tbody></table>
          {!data.receipts.rows.length ? <p>Tidak ada penerimaan dengan sisa utang sesuai pencarian.</p> : null}
          <div className="cproc-pagination"><span>Total {data.receipts.total} penerimaan</span>
            <button type="button" disabled={!data.receipts.offset} onClick={() => seek({ purchase_offset: Math.max(0, data.receipts.offset - 25) })}>Penerimaan sebelumnya</button>
            <button type="button" disabled={data.receipts.next_offset === null} onClick={() => seek({ purchase_offset: data.receipts.next_offset ?? 0 })}>Penerimaan berikutnya</button></div>

          <section aria-label="Alokasi transfer terpilih"><h4>Dibayar dari transfer ini (semua halaman)</h4>
            {parsed.map(r => <p key={r.id}>{r.a.number} · {r.exact ? money(r.exact) : 'jumlah belum benar'}
              {r.payable !== null && r.cents !== null && r.valid ? ` · sisa utang sesudah bayar ${rupiah(r.payable - r.cents)}` : ''}
              {r.payable === null ? ' · batas sisa utang diperiksa server saat disimpan' : ''}
              {!r.valid ? ' · isi jumlah positif, maksimal dua desimal, paling banyak sisa utang' : ''}
              <button type="button" onClick={() => drop(r.id)}>Hapus {r.a.number} dari transfer</button></p>)}
            {!parsed.length ? <p>Belum ada penerimaan dipilih.</p> : null}
            <p><strong>Total transfer {rupiah(total)}</strong> · {parsed.length} penerimaan</p>
            {staleChoice ? <p role="status">Data supplier berubah sejak sebagian baris dipilih. Sisa utang diperiksa ulang oleh server saat disimpan.</p> : null}
          </section>

          <label>Waktu pembayaran · WIB<input aria-label="Waktu transfer supplier WIB" type="datetime-local" value={at} onChange={e => setAt(e.target.value)}/></label>
          {at && !validTime ? <p role="alert">Waktu transfer harus sesudah semua barang terpilih diterima dan tidak di masa depan.</p> : null}
          <label>Cari kas atau rekening<input aria-label="Cari rekening transfer supplier" maxLength={120} value={bankSearch}
            onChange={e => setBankSearch(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); seek({ bank_q: bankSearch.trim(), bank_offset: 0 }) } }}/></label>
          <button type="button" onClick={() => seek({ bank_q: bankSearch.trim(), bank_offset: 0 })}>Cari rekening transfer</button>
          <section aria-label="Rekening transfer supplier">{data.cash_accounts.rows.map(b => <button type="button" key={b.id} aria-pressed={bank?.id === b.id}
            onClick={() => { setBank({ id: b.id, name: b.name }); setChecked(false) }}>{b.code} · {b.name}</button>)}
            {!data.cash_accounts.rows.length ? <p>Tidak ada rekening aktif sesuai pencarian.</p> : null}
            <div className="cproc-pagination"><span>Total {data.cash_accounts.total} rekening</span>
              <button type="button" disabled={!data.cash_accounts.offset} onClick={() => seek({ bank_offset: Math.max(0, data.cash_accounts.offset - 25) })}>Rekening transfer sebelumnya</button>
              <button type="button" disabled={data.cash_accounts.next_offset === null} onClick={() => seek({ bank_offset: data.cash_accounts.next_offset ?? 0 })}>Rekening transfer berikutnya</button></div></section>
          <p>Rekening terpilih: {bank?.name ?? 'belum dipilih'}</p>
          <label>{mode === 'CORRECT' ? 'Alasan koreksi' : 'Keterangan transfer'}<input aria-label="Keterangan transfer supplier" maxLength={500} value={reason} onChange={e => setReason(e.target.value)}/></label>
          <label><input type="checkbox" aria-label="Transfer supplier sudah diperiksa" checked={checked} onChange={e => { e.stopPropagation(); setChecked(e.target.checked) }}/>
            Penerimaan, jumlah tiap baris, total {rupiah(total)}, waktu, rekening dan keterangan sudah saya periksa.</label>
          <button disabled={!ready}>{mode === 'CREATE' ? 'Sahkan transfer supplier' : 'Sahkan koreksi transfer supplier'}</button>
        </fieldset>
        <button type="button" disabled={mutation.busy} onClick={() => { setMode('NONE'); setChecked(false) }}>Tutup formulir transfer</button>
      </form> : null}

      {mode === 'REVERSE' && selected ? <section className="cproc-review" aria-label="Batalkan transfer supplier">
        <h3>Batalkan {selected.number}</h3>
        <p>Seluruh transfer dibalik: kas/bank kembali {money(selected.amount)} dan sisa utang setiap penerimaan naik lagi sesuai alokasinya. Catatan asli tetap disimpan.</p>
        <fieldset disabled={locked || readBusy}><label>Alasan pembatalan<input aria-label="Alasan pembatalan transfer supplier" maxLength={500} value={reason}
          onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
          <label><input type="checkbox" aria-label="Pembatalan transfer supplier sudah diperiksa" checked={checked} onChange={e => setChecked(e.target.checked)}/>Transfer dan semua alokasinya sudah saya periksa.</label>
          <button disabled={!ready} onClick={save}>Balikkan transfer supplier sekarang</button></fieldset>
        <button disabled={mutation.busy} onClick={() => { setMode('NONE'); setChecked(false) }}>Tutup pembatalan transfer</button>
      </section> : null}
    </> : null}
  </section>
}
