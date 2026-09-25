import { useState } from 'react'
import type { Json } from './types/database.preconnect'
import type { InitialImportBB } from './initialImportBB'
import type { InitialImportBC } from './initialImportBC'

// BB (ALL open cutover states): continuations of a posted import. Every action goes through the import RPC with the
// batch's revision; the server re-checks dates, capacity and state. Nothing here computes a balance.
type Manage = (action: string, payload: Record<string, Json>) => void
type CashAccount = { id: string; name: string }
const money = (value: string) => `Rp ${value.replace('.', ',')}`
const amountText = (value: string) => value.trim().replace(',', '.')
const positive = (value: string) => /^[0-9]+([.,][0-9]{1,2})?$/.test(value.trim()) && /[1-9]/.test(value)
const zeroOrPositive = (value: string) => /^[0-9]+([.,][0-9]{1,2})?$/.test(value.trim())
const quantityText = (value: string) => /^[0-9]+([.,][0-9]{1,6})?$/.test(value.trim())
const dateOk = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value)
const DRAFT_PAYROLL = ['DRAFT', 'CALCULATED', 'REVIEW']
const CREDIT_KIND: Record<string, string> = { CUSTOMER_RECEIVABLE:'CUSTOMER_ALLOWANCE', SUPPLIER_PAYABLE:'SUPPLIER_ALLOWANCE', VENDOR_PAYABLE:'VENDOR_ALLOWANCE' }
const BALANCE_LABEL: Record<string, string> = { CUSTOMER_RECEIVABLE:'Piutang pelanggan', SUPPLIER_PAYABLE:'Hutang supplier', VENDOR_PAYABLE:'Hutang laundry',
  CONTRACTOR_PAYABLE:'Hutang mandor', CONTRACTOR_RECEIVABLE:'Piutang mandor' }

export function OpeningBalancesPanel({ bb, cashAccounts, locked, manage }: { bb: InitialImportBB; cashAccounts: CashAccount[]; locked: boolean; manage: Manage }) {
  const [selectedId, setSelectedId] = useState(''), [operation, setOperation] = useState('SETTLE'), [amount, setAmount] = useState('')
  const [date, setDate] = useState(''), [cashId, setCashId] = useState(''), [note, setNote] = useState(''), [payrollId, setPayrollId] = useState(''), [reason, setReason] = useState('')
  const selected = bb.opening_balances.find(b => b.balance_id === selectedId) ?? bb.opening_balances[0]
  if (!selected) return null
  const operations = ['SETTLE', ...(CREDIT_KIND[selected.balance_type] ? ['CREDIT'] : []), ...(selected.balance_type === 'CONTRACTOR_PAYABLE' ? ['ALLOCATE_PAYROLL'] : [])]
  const labels: Record<string, string> = { SETTLE:selected.balance_type.endsWith('RECEIVABLE') ? 'Terima pembayaran' : 'Bayar', CREDIT:'Catat nota potongan', ALLOCATE_PAYROLL:'Bayar lewat payroll' }
  const op = operations.includes(operation) ? operation : 'SETTLE'
  const payrolls = bb.opening_payable_payrolls.filter(p => p.contractor_id === selected.party_id), payroll = payrolls.find(p => p.id === payrollId)
  const valid = reason.trim() && (op === 'ALLOCATE_PAYROLL' ? Boolean(payroll) && zeroOrPositive(amount)
    : positive(amount) && dateOk(date) && (op !== 'SETTLE' || Boolean(cashAccounts.find(c => c.id === cashId))) && (op !== 'CREDIT' || note.trim()))
  const send = (payload: Record<string, Json>) => manage('OPENING_SETTLEMENT', { balance_id:selected.balance_id, reason:reason.trim(), ...payload })
  return <section className="panel initial-import-advances" aria-label="Saldo awal dokumen">
    <h2>Pelunasan saldo awal</h2>
    <p>Pelunasan dan nota potongan hanya boleh sejak tanggal saldo awal dan tanggal dokumennya, tidak di masa depan, dan tidak melebihi sisa pada tanggal itu maupun sesudahnya. Pembayaran sebelum saldo awal tidak membentuk kas baru.</p>
    <label>Dokumen<select aria-label="Dokumen saldo awal" disabled={locked} value={selected.balance_id} onChange={e => { setSelectedId(e.target.value); setOperation('SETTLE'); setAmount(''); setPayrollId('') }}>{bb.opening_balances.map(b => <option key={b.balance_id} value={b.balance_id}>{BALANCE_LABEL[b.balance_type] ?? b.balance_type} · {b.party_name} · {b.document_number || 'tanpa nomor'}</option>)}</select></label>
    <div className="initial-import-table"><table><thead><tr><th>Nominal asal</th><th>Dibayar sebelum saldo awal</th><th>Saldo awal</th><th>Dilunasi sesudahnya</th><th>Dijanjikan ke payroll</th><th>Sisa</th><th>Tersedia</th></tr></thead><tbody><tr>{[selected.original_amount, selected.settled_before_cutover, selected.opening_amount, selected.settled_amount, selected.reserved_amount, selected.remaining_amount, selected.available_amount].map((v, i) => <td key={i}>{money(v)}</td>)}</tr></tbody></table></div>
    <div className="initial-import-toolbar">
      <label>Tindakan<select aria-label="Tindakan saldo awal" disabled={locked} value={op} onChange={e => { setOperation(e.target.value); setAmount('') }}>{operations.map(v => <option key={v} value={v}>{labels[v]}</option>)}</select></label>
      {op === 'SETTLE' && <label>Rekening kas/bank<select aria-label="Rekening pelunasan" disabled={locked} value={cashId} onChange={e => setCashId(e.target.value)}><option value="">Pilih rekening</option>{cashAccounts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
      {op === 'CREDIT' && <label>Nomor nota potongan<input aria-label="Nomor nota potongan" disabled={locked} value={note} onChange={e => setNote(e.target.value)}/></label>}
      {op === 'ALLOCATE_PAYROLL' && <label>Payroll draft<select aria-label="Payroll saldo awal" disabled={locked} value={payroll?.id ?? ''} onChange={e => { setPayrollId(e.target.value); setAmount(selected.payroll_lines.find(l => l.payroll_id === e.target.value)?.amount ?? '') }}><option value="">Pilih payroll mandor ini</option>{payrolls.map(p => <option key={p.id} value={p.id}>{p.payroll_number} · s.d. {p.period_end}</option>)}</select></label>}
      <label>Nominal<input aria-label="Nominal saldo awal" inputMode="decimal" disabled={locked} value={amount} onChange={e => setAmount(e.target.value)}/></label>
      {op !== 'ALLOCATE_PAYROLL' && <label>Tanggal<input aria-label="Tanggal pelunasan saldo awal" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>}
      <label>Alasan / catatan<input aria-label="Alasan pelunasan saldo awal" disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !valid} onClick={() => send(op === 'ALLOCATE_PAYROLL' && payroll
        ? { operation:op, payroll_id:payroll.id, expected_payroll_version:payroll.row_version, amount:amountText(amount) }
        : { operation:op, amount:amountText(amount), effective_date:date, ...(op === 'SETTLE' ? { cash_account_id:cashId } : { credit_kind:CREDIT_KIND[selected.balance_type], credit_note_number:note.trim() }) })}>{labels[op]}</button>
    </div>
    {op === 'ALLOCATE_PAYROLL' && !payrolls.length && <p>Belum ada payroll draft untuk mandor ini.</p>}
    {selected.settlements.length > 0 && <ul>{selected.settlements.map(s => <li key={s.id}>{s.number} · {s.date} · {money(s.amount)} · {s.method === 'CREDIT' ? `Nota ${s.credit_note_number}` : s.method === 'ADVANCE' ? 'Uang muka' : 'Kas/bank'} · {s.status === 'REVERSED' ? 'Dibatalkan' : s.status === 'POSTED' ? 'Dibukukan' : 'Draft'}{s.status === 'POSTED' && s.reversible && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE', settlement_id:s.id })}>Batalkan {s.number}</button>}</li>)}</ul>}
    {selected.payroll_lines.length > 0 && <ul>{selected.payroll_lines.map(l => <li key={l.payroll_id}>{l.payroll_number} · {money(l.amount)} · {l.status}{DRAFT_PAYROLL.includes(l.status) && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'ALLOCATE_PAYROLL', payroll_id:l.payroll_id, expected_payroll_version:l.row_version, amount:'0' })}>Lepas dari {l.payroll_number}</button>}</li>)}</ul>}
  </section>
}

export function CustomerCreditsPanel({ bb, cashAccounts, locked, manage }: { bb: InitialImportBB; cashAccounts: CashAccount[]; locked: boolean; manage: Manage }) {
  const [selectedId, setSelectedId] = useState(''), [operation, setOperation] = useState('APPLY_OPENING_AR'), [amount, setAmount] = useState('')
  const [date, setDate] = useState(''), [targetId, setTargetId] = useState(''), [cashId, setCashId] = useState(''), [reason, setReason] = useState('')
  const selected = bb.customer_credits.find(c => c.credit_id === selectedId) ?? bb.customer_credits[0]
  if (!selected) return null
  const target = selected.open_receivables.find(r => r.balance_id === targetId), cash = cashAccounts.find(c => c.id === cashId)
  const valid = positive(amount) && dateOk(date) && reason.trim() && (operation === 'REFUND' ? Boolean(cash) : Boolean(target))
  const send = (payload: Record<string, Json>) => manage('CUSTOMER_CREDIT', { credit_id:selected.credit_id, reason:reason.trim(), ...payload })
  const labels: Record<string, string> = { APPLY_OPENING_AR:'Potong piutang lama', REFUND:'Kembalikan uang', REVERSAL:'Pembatalan' }
  return <section className="panel initial-import-advances" aria-label="Kredit pelanggan saldo awal">
    <h2>Kredit pelanggan</h2>
    <p>Kredit dari saldo awal atau dari retur dipakai untuk memotong piutang lama pelanggan yang sama atau dikembalikan tunai. Pembatalan mengembalikan sisa kredit.</p>
    <label>Kredit<select aria-label="Kredit pelanggan" disabled={locked} value={selected.credit_id} onChange={e => { setSelectedId(e.target.value); setTargetId(''); setAmount('') }}>{bb.customer_credits.map(c => <option key={c.credit_id} value={c.credit_id}>{c.customer_name} · {c.document_number}</option>)}</select></label>
    <p>Kredit {money(selected.amount)} · Terpakai {money(selected.used_amount)} · Sisa {money(selected.remaining_amount)}{selected.voided ? ' · Dibatalkan' : ''}</p>
    <div className="initial-import-toolbar">
      <label>Tindakan<select aria-label="Tindakan kredit pelanggan" disabled={locked} value={operation} onChange={e => setOperation(e.target.value)}>{['APPLY_OPENING_AR', 'REFUND'].map(v => <option key={v} value={v}>{labels[v]}</option>)}</select></label>
      {operation === 'APPLY_OPENING_AR' ? <label>Piutang lama<select aria-label="Piutang untuk kredit" disabled={locked} value={target?.balance_id ?? ''} onChange={e => setTargetId(e.target.value)}><option value="">Pilih piutang pelanggan ini</option>{selected.open_receivables.map(r => <option key={r.balance_id} value={r.balance_id}>{r.document_number} · sisa {money(r.remaining_amount)}</option>)}</select></label>
        : <label>Rekening<select aria-label="Rekening pengembalian kredit" disabled={locked} value={cash?.id ?? ''} onChange={e => setCashId(e.target.value)}><option value="">Pilih rekening</option>{cashAccounts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
      <label>Nominal<input aria-label="Nominal kredit" inputMode="decimal" disabled={locked} value={amount} onChange={e => setAmount(e.target.value)}/></label>
      <label>Tanggal<input aria-label="Tanggal kredit" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>
      <label>Alasan / catatan<input aria-label="Alasan kredit" disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !valid} onClick={() => send({ operation, amount:amountText(amount), effective_date:date, ...(operation === 'REFUND' ? { cash_account_id:cashId } : { balance_id:targetId }) })}>{labels[operation]}</button>
    </div>
    {selected.events.length > 0 && <ul>{selected.events.map(e => <li key={e.id}>{labels[e.kind]} · {e.date} · {money(e.amount)} · {e.reason}{e.reversed ? ' · Dibatalkan' : e.kind !== 'REVERSAL' && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE_EVENT', event_id:e.id })}>Batalkan {labels[e.kind].toLowerCase()} {e.date}</button>}</li>)}</ul>}
  </section>
}

export function ReturnRightsPanel({ bb, locked, manage }: { bb: InitialImportBB; locked: boolean; manage: Manage }) {
  const [selectedId, setSelectedId] = useState(''), [qty, setQty] = useState(''), [locationId, setLocationId] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('')
  const selected = bb.sale_return_rights.find(r => r.id === selectedId) ?? bb.sale_return_rights[0]
  if (!selected) return null
  const open = selected.qty_pcs - selected.received_pcs
  const valid = /^[1-9][0-9]*$/.test(qty) && Number(qty) <= open && bb.fg_locations.some(l => l.id === locationId) && dateOk(date) && reason.trim()
  const send = (payload: Record<string, Json>) => manage('OPENING_RETURN', { right_id:selected.id, reason:reason.trim(), ...payload })
  return <section className="panel initial-import-advances" aria-label="Retur penjualan lama">
    <h2>Retur penjualan lama yang belum diterima</h2>
    <p>Barang retur masuk gudang barang jadi sebagai lot retur dengan biaya dari file; nilai kreditnya mengurangi piutang invoice lama atau menjadi kredit pelanggan bila invoice sudah lunas sebelum saldo awal.</p>
    <label>Hak retur<select aria-label="Hak retur" disabled={locked} value={selected.id} onChange={e => { setSelectedId(e.target.value); setQty('') }}>{bb.sale_return_rights.map(r => <option key={r.id} value={r.id}>{r.return_number} · {r.customer_code} · invoice {r.invoice_document_number}</option>)}</select></label>
    <p>{selected.product_sku} · {selected.qty_pcs} pcs · sudah diterima {selected.received_pcs} pcs · harga kredit {money(selected.credit_unit_price)} · invoice {selected.invoice_state === 'OPEN' ? 'masih terbuka' : 'lunas sebelum saldo awal'}</p>
    {open > 0 && <div className="initial-import-toolbar">
      <label>Diterima (pcs)<input aria-label="Jumlah retur diterima" inputMode="numeric" disabled={locked} value={qty} onChange={e => setQty(e.target.value)}/></label>
      <label>Gudang<select aria-label="Gudang retur" disabled={locked} value={locationId} onChange={e => setLocationId(e.target.value)}><option value="">Pilih gudang barang jadi</option>{bb.fg_locations.map(l => <option key={l.id} value={l.id}>{l.code} · {l.name}</option>)}</select></label>
      <label>Tanggal terima<input aria-label="Tanggal retur diterima" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>
      <label>Catatan pemeriksaan<input aria-label="Catatan retur" disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !valid} onClick={() => send({ operation:'RECEIVE', qty, location_id:locationId, effective_date:date })}>Terima retur</button>
    </div>}
    {selected.receipts.length > 0 && <ul>{selected.receipts.map(x => <li key={x.id}>{x.date} · {x.qty_pcs} pcs · {x.status === 'POSTED' ? 'Diterima' : 'Dibatalkan'}{x.status === 'POSTED' && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE_RECEIPT', receipt_id:x.id })}>Batalkan penerimaan {x.date}</button>}</li>)}</ul>}
  </section>
}

export function PurchaseCommitmentsPanel({ bb, locked, manage }: { bb: InitialImportBB; locked: boolean; manage: Manage }) {
  const [selectedId, setSelectedId] = useState(''), [lineId, setLineId] = useState(''), [qty, setQty] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('')
  const selected = bb.purchase_commitments.find(c => c.id === selectedId) ?? bb.purchase_commitments[0]
  if (!selected) return null
  const line = selected.lines.find(l => l.id === lineId)
  const openDraft = selected.drafts.some(d => d.status === 'DRAFT')
  const send = (payload: Record<string, Json>) => manage('PURCHASE_COMMITMENT', { commitment_id:selected.id, reason:reason.trim(), ...payload })
  return <section className="panel initial-import-advances" aria-label="PO pembelian terbuka">
    <h2>PO pembelian yang masih terbuka</h2>
    <p>Sisa PO dibuat sebagai draft penerimaan native. Terima barang melalui halaman pembelian bahan; batalkan sisa yang tidak akan datang di sini.</p>
    <label>PO<select aria-label="PO pembelian terbuka" disabled={locked} value={selected.id} onChange={e => { setSelectedId(e.target.value); setLineId('') }}>{bb.purchase_commitments.map(c => <option key={c.id} value={c.id}>{c.po_number} · {c.supplier_name}</option>)}</select></label>
    <div className="initial-import-table"><table><thead><tr><th>Baris</th><th>Bahan</th><th>Dipesan</th><th>Sisa</th><th>Harga</th></tr></thead><tbody>{selected.lines.map(l => <tr key={l.id}><td>{l.line_number}</td><td>{l.material_sku}</td><td>{l.ordered_qty}</td><td>{l.remaining_qty}</td><td>{l.unit_price}</td></tr>)}</tbody></table></div>
    {selected.drafts.length > 0 && <p>Penerimaan: {selected.drafts.map(d => `${d.purchase_number} (${d.status})`).join(', ')}</p>}
    <div className="initial-import-toolbar">
      <label>Baris<select aria-label="Baris PO dibatalkan" disabled={locked} value={line?.id ?? ''} onChange={e => setLineId(e.target.value)}><option value="">Pilih baris</option>{selected.lines.map(l => <option key={l.id} value={l.id}>{l.line_number} · {l.material_sku} · sisa {l.remaining_qty}</option>)}</select></label>
      <label>Batalkan jumlah<input aria-label="Jumlah PO dibatalkan" inputMode="decimal" disabled={locked} value={qty} onChange={e => setQty(e.target.value)}/></label>
      <label>Tanggal<input aria-label="Tanggal pembatalan PO" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>
      <label>Alasan<input aria-label="Alasan PO" disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !line || !quantityText(qty) || !/[1-9]/.test(qty) || !dateOk(date) || !reason.trim()} onClick={() => { if (line) send({ operation:'CANCEL', line_id:line.id, qty:qty.trim().replace(',', '.'), effective_date:date }) }}>Batalkan sisa</button>
      <button type="button" disabled={locked || openDraft || !reason.trim() || !selected.lines.some(l => /[1-9]/.test(l.remaining_qty))} onClick={() => send({ operation:'REOPEN_REMAINDER' })}>Buat draft penerimaan untuk sisa</button>
    </div>
    {openDraft && <p>Draft penerimaan untuk sisa PO masih terbuka; posting draft itu sebelum membuat draft baru. Sisa yang tidak akan datang tetap bisa dibatalkan.</p>}
  </section>
}

export function PayrollEntitlementsPanel({ bb, locked, manage }: { bb: InitialImportBB; locked: boolean; manage: Manage }) {
  const [selectedId, setSelectedId] = useState(''), [payrollId, setPayrollId] = useState(''), [qty, setQty] = useState('')
  const carried = bb.payroll_entitlements.filter(e => /[1-9]/.test(e.carry_qty))
  const selected = carried.find(e => e.id === selectedId) ?? carried[0]
  const payrolls = selected ? bb.entitlement_payrolls.filter(p => p.contractor_id === selected.contractor_id) : [], payroll = payrolls.find(p => p.id === payrollId)
  const kinds: Record<string, string> = { SEWING_WORK:'Upah jahit', ATTENDANCE:'Absensi', ACCESSORY_REIMBURSEMENT:'Reimburse aksesori' }
  const send = (payload: Record<string, Json>) => manage('PAYROLL_ENTITLEMENT', payload)
  return <section className="panel initial-import-advances" aria-label="Hak upah sebelum saldo awal">
    <h2>Hak upah sebelum saldo awal</h2>
    <p>Nominalnya dibayar lewat dokumen hutang mandor di Pelunasan saldo awal. Komponen yang dibawa (carry) dibayar lewat payroll setelah pekerjaannya selesai, tidak melebihi jumlah carry.</p>
    <div className="initial-import-table"><table><thead><tr><th>Jenis</th><th>Mandor</th><th>Dokumen</th><th>Nominal</th><th>Tarif</th><th>Carry</th><th>Sisa carry</th></tr></thead><tbody>{bb.payroll_entitlements.map(e => <tr key={e.id}><td>{kinds[e.kind]}</td><td>{e.contractor_name}</td><td>{e.document_number}/{e.line_number}</td><td>{money(e.amount)}</td><td>{money(e.rate)}</td><td>{e.carry_qty}</td><td>{e.carry_remaining}</td></tr>)}</tbody></table></div>
    {selected && <div className="initial-import-toolbar">
      <label>Carry<select aria-label="Hak upah carry" disabled={locked} value={selected.id} onChange={e => { setSelectedId(e.target.value); setPayrollId('') }}>{carried.map(e => <option key={e.id} value={e.id}>{e.contractor_name} · {e.document_number}/{e.line_number}</option>)}</select></label>
      <label>Payroll draft<select aria-label="Payroll carry" disabled={locked} value={payroll?.id ?? ''} onChange={e => { setPayrollId(e.target.value); setQty(selected.carry_lines.find(l => l.payroll_id === e.target.value)?.qty ?? '') }}><option value="">Pilih payroll mandor ini</option>{payrolls.map(p => <option key={p.id} value={p.id}>{p.payroll_number} · s.d. {p.period_end}</option>)}</select></label>
      <label>Jumlah carry<input aria-label="Jumlah carry" inputMode="decimal" disabled={locked} value={qty} onChange={e => setQty(e.target.value)}/></label>
      <button type="button" disabled={locked || !payroll || !quantityText(qty)} onClick={() => { if (payroll) send({ operation:'ALLOCATE_CARRY', entitlement_id:selected.id, payroll_id:payroll.id, qty:qty.trim().replace(',', '.'), expected_payroll_version:payroll.row_version }) }}>Simpan carry ke payroll</button>
    </div>}
    {selected && selected.carry_lines.length > 0 && <ul>{selected.carry_lines.map(l => <li key={l.payroll_id}>{l.payroll_number} · {l.qty} · {money(l.amount)} · {l.status}{DRAFT_PAYROLL.includes(l.status) && <button type="button" disabled={locked} onClick={() => send({ operation:'ALLOCATE_CARRY', entitlement_id:selected.id, payroll_id:l.payroll_id, qty:'0', expected_payroll_version:l.row_version })}>Lepas carry dari {l.payroll_number}</button>}</li>)}</ul>}
  </section>
}

export function OpenSalesDraftsPanel({ bb }: { bb: InitialImportBB }) {
  if (!bb.open_sales_drafts.length) return null
  const status = { DRAFT: 'Draf (reservasi aktif)', POSTED: 'Sudah diposting', CANCELLED: 'Dibatalkan' } as const
  return <section className="panel initial-import-advances" aria-label="Draf penjualan terbuka saldo awal">
    <h2>Draf penjualan yang masih terbuka saat saldo awal</h2>
    <p>Setiap draf menjadi draf penjualan native dengan nomor aslinya dan mereservasi stok sekali. Ubah tanggal invoice ke tanggal nyata, edit, batalkan, atau posting melalui halaman Penjualan; tanggal sebelum saldo awal dan pergantian pelanggan ditolak.</p>
    <div className="initial-import-table"><table><thead><tr><th>Draf</th><th>Pelanggan</th><th>Tanggal draf lama</th><th>Tanggal invoice</th><th>Baris</th><th>Direservasi</th><th>Status</th></tr></thead><tbody>{bb.open_sales_drafts.map(d => <tr key={d.sale_id}><td>{d.draft_number}</td><td>{d.customer_code} · {d.customer_name}</td><td>{d.draft_date}</td><td>{d.sale_date}</td><td>{d.lines.map(l => `${l.product_sku} ${l.qty_pcs} pcs @ ${l.unit_price}`).join('; ')}</td><td>{d.reserved_qty_pcs} pcs</td><td>{status[d.status]}</td></tr>)}</tbody></table></div>
  </section>
}

export function OpeningReworksPanel({ bb }: { bb: InitialImportBB }) {
  if (!bb.opening_reworks.length) return null
  return <section className="panel initial-import-advances" aria-label="Rework terbuka saldo awal">
    <h2>Rework yang masih di luar saat saldo awal</h2>
    <p>Setiap rework menjadi order rework native untuk sisa pcs-nya. Selesaikan, catat hasil baik/BS, atau batalkan melalui halaman BS/Rework; upah komponen dihitung saat rework selesai.</p>
    <div className="initial-import-table"><table><thead><tr><th>Rework</th><th>BS</th><th>Tujuan</th><th>Dikirim (asal)</th><th>Kembali sebelum saldo awal</th><th>Sisa di rework</th><th>Status</th></tr></thead><tbody>{bb.opening_reworks.map(r => <tr key={r.id}><td>{r.legacy_rework_number} → {r.rework_number}</td><td>{r.bs_number}</td><td>{r.destination_type === 'CONTRACTOR' ? 'Mandor' : 'Laundry'} {r.holder_name}</td><td>{r.qty_sent_original} pcs · {r.legacy_sent_date}</td><td>{r.qty_returned_before_cutover} pcs</td><td>{r.qty_open} pcs</td><td>{r.status}{r.qty_good_returned + r.qty_bs_returned > 0 ? ` · baik ${r.qty_good_returned}, BS ${r.qty_bs_returned}` : ''}</td></tr>)}</tbody></table></div>
  </section>
}

const pcs = (value: string) => value.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '').replace('.', ',')
const CUSTODY_LABEL: Record<string, string> = { QUARANTINE_VALUED:'Area pemeriksaan (bernilai di buku)', PENDING_VALUE:'Titipan belum dinilai',
  UNRETURNED:'Belum kembali', CUSTOMER_GARMENT:'Titipan pelanggan' }

/** BC (ALL-C02/C03): read only here; returns, inspection, credit and valuation are recorded on Gudang · Aksesori. */
export function OpeningAccessoriesPanel({ bc }: { bc: InitialImportBC }) {
  return <section className="panel initial-import-advances" aria-label="Aksesori saldo awal">
    <h2>Aksesori saldo awal</h2>
    <p>Baris nota mandor lama dan aksesori yang bukan stok siap pakai. Penerimaan kembali, pemeriksaan, kredit retur, dan penilaian dicatat di Gudang · Aksesori; jumlah dan nominal asal di sini tidak berubah.</p>
    {bc.accessory_note_lines.length > 0 && <div className="initial-import-table"><table><thead><tr><th>Nota lama</th><th>Baris</th><th>Aksesori</th><th>Jumlah</th><th>Nominal asal</th><th>Sudah kembali</th><th>Sisa piutang dokumen</th></tr></thead>
      <tbody>{bc.accessory_note_lines.map(n => <tr key={n.line_id}><td>{n.document_number}</td><td>{n.line_number}</td><td>{n.material_sku}</td><td>{pcs(n.qty)}</td>
        <td>{money(n.line_amount)}</td><td>{pcs(n.returned)}</td><td>{money(n.remaining_receivable)}</td></tr>)}</tbody></table></div>}
    {bc.accessory_custody.length > 0 && <div className="initial-import-table"><table><thead><tr><th>Kode opname</th><th>Jenis</th><th>Aksesori / pelanggan</th><th>Jumlah</th><th>Menunggu periksa</th><th>Layak</th><th>Rusak</th><th>Status nilai</th></tr></thead>
      <tbody>{bc.accessory_custody.map(c => <tr key={c.kind + c.key}><td>{c.key}</td><td>{CUSTODY_LABEL[c.kind]}</td><td>{c.material_sku || c.customer_code}{c.holder ? ` · ${c.holder}` : ''}</td>
        <td>{pcs(c.qty)}</td><td>{c.waiting === null ? '—' : pcs(c.waiting)}</td><td>{c.usable === null ? '—' : pcs(c.usable)}</td><td>{c.damaged === null ? '—' : pcs(c.damaged)}</td><td>{c.value_status}</td></tr>)}</tbody></table></div>}
  </section>
}
