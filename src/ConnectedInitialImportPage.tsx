import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, FileUp, RefreshCw } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { initialImportCatalog, initialImportTemplate, readInitialImportFile, type InitialImportEntity, type InitialImportRow } from './initialImport'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { Json } from './types/database.preconnect'
import './initial-import.css'
import { parseInitialProductionSources, type InitialProductionSource } from './initialProduction'
import { parseInitialImportBB, type InitialImportBB } from './initialImportBB'
import { CustomerCreditsPanel, OpenSalesDraftsPanel, OpeningBalancesPanel, OpeningReworksPanel, PayrollEntitlementsPanel, PurchaseCommitmentsPanel, ReturnRightsPanel } from './InitialImportContinuations'

type Row = InitialImportRow & { id: string; entity: InitialImportEntity; validation_status: string; errors: string[]; applied: boolean }
type AdvanceAllocation = { payroll_id: string; payroll_number: string; status: string; row_version: string; amount: string }
type CashAdvance = { balance_id: string; contractor_id: string; contractor_name: string; document_number: string;
  original_amount: string; settled_before_cutover: string; opening_amount: string; settled_amount: string;
  remaining_amount: string; reserved_amount: string; available_amount: string; allocations: AdvanceAllocation[] }
type AdvancePayroll = { id: string; contractor_id: string; payroll_number: string; row_version: string }
type Prepayment = { id: string; party_type: 'SUPPLIER' | 'CUSTOMER' | 'VENDOR'; party_id: string; party_name: string; document_number: string;
  original_amount: string; settled_before_cutover: string; opening_amount: string; applied_amount: string; refunded_amount: string; remaining_amount: string;
  targets: { id: string; number: string; party_id: string; party_type: string; remaining_amount: string; target_date: string }[];
  payments: { id: string; number: string; status: string; amount: string }[];
  events: { id: string; kind: string; delta: string; date: string; reason: string; reversed: boolean }[] }
type CashAccount = { id: string; name: string }
type Batch = { id: string; code: string; status: string; cutover_at: string; revision: string; rows: Row[]; cash_advances: CashAdvance[]; advance_payrolls: AdvancePayroll[]; prepayments: Prepayment[]; prepayment_cash_accounts: CashAccount[]; production_sources: InitialProductionSource[]; bb: InitialImportBB | null }
type Workspace = { batch: Batch | null; recent: { id: string; batch_code: string; status: string }[] }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons impor tidak lengkap.')
  return value as Record<string, unknown>
}
const moneyText = (value: unknown): value is string => typeof value === 'string' && /^\d{1,18}\.\d{2}$/.test(value)
const versionText = (value: unknown): value is string => typeof value === 'string' && /^[1-9]\d{0,18}$/.test(value)
const dateText = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
function prepayment(value: unknown): Prepayment {
  const p = object(value)
  if (typeof p.id !== 'string' || !uuid.test(p.id) || typeof p.party_id !== 'string' || !uuid.test(p.party_id)
    || !['SUPPLIER', 'CUSTOMER', 'VENDOR'].includes(String(p.party_type)) || typeof p.party_name !== 'string' || typeof p.document_number !== 'string'
    || !['original_amount', 'settled_before_cutover', 'opening_amount', 'applied_amount', 'refunded_amount', 'remaining_amount'].every(k => moneyText(p[k]))
    || !Array.isArray(p.targets) || !Array.isArray(p.payments) || !Array.isArray(p.events)) throw new Error('Saldo uang muka tidak lengkap atau perlu diperiksa.')
  for (const item of p.targets) {
    const t = object(item)
    if (typeof t.id !== 'string' || !uuid.test(t.id) || typeof t.number !== 'string' || t.party_id !== p.party_id || t.party_type !== p.party_type
      || !moneyText(t.remaining_amount) || !dateText(t.target_date)) throw new Error('Tagihan uang muka tidak cocok dengan pihaknya.')
  }
  for (const item of p.payments) {
    const t = object(item)
    if (typeof t.id !== 'string' || !uuid.test(t.id) || typeof t.number !== 'string' || !['DRAFT', 'POSTED', 'REVERSED'].includes(String(t.status)) || !moneyText(t.amount)) throw new Error('Pemakaian uang muka tidak valid.')
  }
  for (const item of p.events) {
    const t = object(item)
    if (typeof t.id !== 'string' || !uuid.test(t.id) || !['CORRECTION', 'REFUND', 'REVERSAL'].includes(String(t.kind)) || typeof t.delta !== 'string'
      || !/^-?\d{1,18}\.\d{2}$/.test(t.delta) || !dateText(t.date) || typeof t.reason !== 'string' || typeof t.reversed !== 'boolean') throw new Error('Riwayat uang muka tidak valid.')
  }
  return p as Prepayment
}
function cashAdvance(value: unknown): CashAdvance {
  const a = object(value)
  if (typeof a.balance_id !== 'string' || !uuid.test(a.balance_id) || typeof a.contractor_id !== 'string' || !uuid.test(a.contractor_id)
    || typeof a.contractor_name !== 'string' || typeof a.document_number !== 'string' || !Array.isArray(a.allocations)
    || !['original_amount', 'settled_before_cutover', 'opening_amount', 'settled_amount', 'remaining_amount', 'reserved_amount', 'available_amount'].every(k => moneyText(a[k]))) throw new Error('Saldo kasbon tidak lengkap atau perlu diperiksa.')
  const allocations = a.allocations.map((value): AdvanceAllocation => {
    const d = object(value)
    if (typeof d.payroll_id !== 'string' || !uuid.test(d.payroll_id) || typeof d.payroll_number !== 'string'
      || typeof d.status !== 'string' || !['DRAFT','CALCULATED','REVIEW','APPROVED','PAID'].includes(d.status)
      || !versionText(d.row_version) || !moneyText(d.amount)) throw new Error('Alokasi kasbon tidak valid.')
    return { payroll_id:d.payroll_id, payroll_number:d.payroll_number, status:d.status, row_version:d.row_version, amount:d.amount }
  })
  return { ...a, allocations } as CashAdvance
}
export function parseInitialImportWorkspace(value: unknown): Workspace {
  const raw = object(value)
  if (!Array.isArray(raw.recent)) throw new Error('Daftar impor tidak lengkap.')
  const recent = raw.recent.map((entry) => {
    const r = object(entry)
    if (typeof r.id !== 'string' || !uuid.test(r.id) || typeof r.batch_code !== 'string' || typeof r.status !== 'string') throw new Error('Identitas impor tidak valid.')
    return { id: r.id, batch_code: r.batch_code, status: r.status }
  })
  if (raw.batch === null) return { batch: null, recent }
  const b = object(raw.batch)
  if (typeof b.id !== 'string' || !uuid.test(b.id) || typeof b.code !== 'string' || typeof b.status !== 'string'
    || typeof b.cutover_at !== 'string' || !Number.isFinite(Date.parse(b.cutover_at))
    || typeof b.revision !== 'string' || !/^[0-9a-f]{64}$/.test(b.revision) || !Array.isArray(b.rows)) throw new Error('Isi batch impor tidak lengkap.')
  const rows = b.rows.map((entry): Row => {
    const r = object(entry), payload = object(r.payload)
    if (typeof r.id !== 'string' || !uuid.test(r.id) || typeof r.entity !== 'string' || !(r.entity in initialImportCatalog)
      || !Number.isSafeInteger(r.source_row_no) || Number(r.source_row_no) < 1 || typeof r.validation_status !== 'string'
      || !Array.isArray(r.errors) || !r.errors.every((e) => typeof e === 'string') || typeof r.applied !== 'boolean'
      || Object.values(payload).some((v) => v !== null && typeof v !== 'string' && typeof v !== 'boolean' && (typeof v !== 'number' || !Number.isFinite(v)))) throw new Error('Rincian baris impor tidak valid.')
    return { id: r.id, entity: r.entity as InitialImportEntity, source_row_no: Number(r.source_row_no),
      payload: Object.fromEntries(Object.entries(payload).map(([key, v]) => [key, v === null ? '' : String(v)])),
      validation_status: r.validation_status, errors: r.errors as string[], applied: r.applied }
  })
  // Every collection is required: a missing key is an incomplete read, never "no balances".
  const list = (value: unknown, label: string): unknown[] => {
    if (value === undefined) throw new Error(`${label} tidak terbaca lengkap.`)
    if (!Array.isArray(value)) throw new Error(`${label} tidak valid.`)
    return value
  }
  const cash_advances = list(b.cash_advances, 'Daftar kasbon').map(cashAdvance)
  const advance_payrolls = list(b.advance_payrolls, 'Pilihan payroll kasbon').map((value): AdvancePayroll => {
    const p = object(value)
    if (typeof p.id !== 'string' || !uuid.test(p.id) || typeof p.contractor_id !== 'string' || !uuid.test(p.contractor_id)
      || typeof p.payroll_number !== 'string' || !versionText(p.row_version)) throw new Error('Pilihan payroll kasbon tidak valid.')
    return { id:p.id, contractor_id:p.contractor_id, payroll_number:p.payroll_number, row_version:p.row_version }
  })
  const prepayments = list(b.prepayments, 'Daftar uang muka').map(prepayment)
  const prepayment_cash_accounts = list(b.prepayment_cash_accounts, 'Rekening pengembalian uang muka').map((value): CashAccount => {
    const c = object(value)
    if (typeof c.id !== 'string' || !uuid.test(c.id) || typeof c.name !== 'string') throw new Error('Rekening pengembalian uang muka tidak valid.')
    return { id:c.id, name:c.name }
  })
  return { recent, batch: { id:b.id, code:b.code, status:b.status, cutover_at:b.cutover_at, revision:b.revision, rows, cash_advances, advance_payrolls, prepayments, prepayment_cash_accounts, production_sources:parseInitialProductionSources(b.production_sources, true), bb:parseInitialImportBB(b) } }
}

function ProductionBalances({ batch, locked, manage }: { batch: Batch; locked: boolean; manage: (payload: Record<string, Json>) => void }) {
  const [selectedId, setSelectedId] = useState(''), [qty, setQty] = useState(''), [sku, setSku] = useState(''), [brand, setBrand] = useState('')
  const [location, setLocation] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('')
  const [mode, setMode] = useState<'COMPLETE' | 'SPLIT_BS'>('COMPLETE'), [mandor, setMandor] = useState('')
  const selected = batch.production_sources.find(s => s.opening_item_id === selectedId) ?? batch.production_sources[0]
  if (!selected) return null
  const state = selected.bb, waiting = state?.current_stage === 'CUTTING'
  const activeOutputs = selected.outputs.some(o => !o.reversed), activeSplits = state?.splits.some(s => !s.reversed) ?? false
  const valid = selected.balance_type === 'WIP' && !waiting && /^[1-9][0-9]*$/.test(qty) && Number(qty) <= selected.remaining_qty_pcs && sku.trim() && (mode === 'SPLIT_BS' || location.trim()) && date && reason.trim()
  const send = (payload: Record<string, Json>) => manage({ opening_item_id:selected.opening_item_id, expected_remaining:String(selected.remaining_qty_pcs), reason:reason.trim(), ...payload })
  return <section className="panel initial-import-advances" aria-label="Saldo fisik produksi awal">
    <h2>Saldo fisik produksi awal</h2><p>Jumlah dan biaya pada tanggal saldo awal tetap tersimpan. Catat hasil setelah barang selesai dan sudah diperiksa; upah atau tagihan baru dicatat melalui transaksi produksinya.</p>
    <label>Rincian produksi<select aria-label="Rincian produksi awal" value={selected.opening_item_id} disabled={locked} onChange={e => { setSelectedId(e.target.value); setQty(''); setSku(''); setBrand('') }}>{batch.production_sources.map(s => <option key={s.opening_item_id} value={s.opening_item_id}>{s.po_number} · {s.balance_type} {s.stage} · {s.size_code} · {s.source_key}</option>)}</select></label>
    <p>{waiting ? `Menunggu pickup di lokasi ${state?.location_code ?? ''}` : (selected.stage === 'LAUNDRY' ? selected.vendor_name : selected.contractor_name ?? selected.vendor_name) ?? 'Pemegang mengikuti rincian saldo'} · Awal {selected.qty_pcs} pcs · Sisa {selected.remaining_qty_pcs} pcs{state && state.split_qty_pcs > 0 ? ` · Dipisah BS ${state.split_qty_pcs} pcs` : ''}{state && state.current_stage !== selected.stage ? ` · Tahap sekarang ${state.current_stage}` : ''}</p>
    <p>Nilai asal Rp {selected.original_amount?.replace('.', ',')} · Nilai asal setelah koreksi Rp {selected.current_amount?.replace('.', ',')}</p>
    {state?.pickup && <p>Di-pickup {state.pickup.contractor_name} pada {state.pickup.date}{!activeOutputs && !activeSplits && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE_PICKUP' })}>Batalkan pickup</button>}</p>}
    {selected.balance_type === 'BS' ? <p>Lanjutkan pemeriksaan, rework, atau pengeluaran melalui halaman BS/Rework.</p> : waiting ? <>
      <p>Potongan ini belum diambil mandor. Catat pickup dahulu; hasil, pisah BS, dan upah baru bisa dicatat sejak tanggal pickup.</p>
      <div className="initial-import-toolbar"><label>Kode mandor<input aria-label="Mandor pickup" value={mandor} disabled={locked} onChange={e => setMandor(e.target.value)}/></label><label>Tanggal pickup<input aria-label="Tanggal pickup" type="date" value={date} disabled={locked} onChange={e => setDate(e.target.value)}/></label><label>Catatan<input aria-label="Catatan pickup" value={reason} disabled={locked} onChange={e => setReason(e.target.value)}/></label><button type="button" disabled={locked || !mandor.trim() || !date || !reason.trim()} onClick={() => send({ operation:'PICKUP', contractor_code:mandor.trim(), date })}>Catat pickup</button></div>
    </> : <>
      {state && <label>Catat<select aria-label="Jenis catatan WIP awal" value={mode} disabled={locked} onChange={e => setMode(e.target.value as 'COMPLETE' | 'SPLIT_BS')}><option value="COMPLETE">Hasil baik ke barang jadi</option><option value="SPLIT_BS">Pisahkan sebagai BS</option></select></label>}
      <div className="initial-import-toolbar"><label>{mode === 'SPLIT_BS' ? 'BS (pcs)' : 'Hasil baik (pcs)'}<input aria-label="Hasil WIP baik" inputMode="numeric" value={qty} disabled={locked} onChange={e => setQty(e.target.value)}/></label><label>Kode produk jadi<input aria-label="Produk hasil WIP" value={sku} disabled={locked} onChange={e => setSku(e.target.value)}/></label><label>Kode merek produk<input aria-label="Merek hasil WIP" value={brand} disabled={locked} onChange={e => setBrand(e.target.value)}/></label>{mode === 'COMPLETE' && <label>Kode gudang barang jadi<input aria-label="Gudang hasil WIP" value={location} disabled={locked} onChange={e => setLocation(e.target.value)}/></label>}<label>Tanggal hasil<input aria-label="Tanggal hasil WIP" type="date" value={date} disabled={locked} onChange={e => setDate(e.target.value)}/></label><label>Catatan pemeriksaan<input aria-label="Catatan hasil WIP" value={reason} disabled={locked} onChange={e => setReason(e.target.value)}/></label><button type="button" disabled={locked || !valid} onClick={() => send({ operation:mode, qty_pcs:qty, product_sku:sku.trim(), ...(brand.trim() ? { brand_code:brand.trim() } : {}), ...(mode === 'COMPLETE' ? { location_code:location.trim() } : {}), date })}>{mode === 'SPLIT_BS' ? 'Pisahkan sebagai BS' : 'Sahkan hasil WIP awal'}</button></div>
      <p>Isi kode merek bila SKU yang sama digunakan oleh beberapa merek.</p>
      {mode === 'SPLIT_BS' && <p>Pcs BS menjadi kasus BS dengan nilai per pcs dari saldo awal; lanjutkan rework atau pengeluarannya di halaman BS/Rework.</p>}
      {selected.outputs.length > 0 && <ul>{selected.outputs.map(o => <li key={o.id}>{o.date} · {o.qty_pcs} pcs · {o.reversed ? 'Dibatalkan' : 'Sudah masuk barang jadi'}{!o.reversed && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE', output_id:o.id })}>Batalkan hasil {o.date}</button>}</li>)}</ul>}
      {state && state.splits.length > 0 && <ul>{state.splits.map(s => <li key={s.id}>{s.date} · BS {s.bs_number} · {s.qty_pcs} pcs · {s.reversed ? 'Dibatalkan' : s.bs_status}{!s.reversed && s.bs_status === 'OPEN' && s.resolved_qty_pcs === 0 && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({ operation:'REVERSE_SPLIT', split_id:s.id })}>Batalkan pisah BS {s.date}</button>}</li>)}</ul>}
    </>}
  </section>
}

function CashAdvanceBalances({ batch, locked, allocate }: { batch: Batch; locked: boolean; allocate: (payload: Record<string, Json>) => void }) {
  const [selectedId, setSelectedId] = useState(''), [payrollId, setPayrollId] = useState(''), [amount, setAmount] = useState('')
  const selected = batch.cash_advances.find(a => a.balance_id === selectedId) ?? batch.cash_advances[0]
  const payrolls = batch.advance_payrolls.filter(p => p.contractor_id === selected?.contractor_id)
  const payroll = payrolls.find(p => p.id === payrollId)
  const money = (value: string) => `Rp ${value.replace('.', ',')}`
  if (!selected) return null
  return <section className="panel initial-import-advances" aria-label="Kasbon tunai saldo awal">
    <h2>Kasbon tunai saldo awal</h2>
    <p>Alokasi draft menyisihkan saldo untuk payroll yang dipilih. Pelunasan terjadi saat payroll dibayar; sisa kasbon tetap bisa dibawa ke periode berikutnya.</p>
    <label>Dokumen kasbon<select aria-label="Dokumen kasbon" disabled={locked} value={selected.balance_id} onChange={e => { setSelectedId(e.target.value); setPayrollId(''); setAmount('') }}>{batch.cash_advances.map(a => <option key={a.balance_id} value={a.balance_id}>{a.contractor_name} · {a.document_number}</option>)}</select></label>
    <div className="initial-import-table"><table><thead><tr><th>Nominal asal</th><th>Dibayar sebelum saldo awal</th><th>Saldo awal saat ini</th><th>Dilunasi setelah saldo awal</th><th>Sisa kasbon</th><th>Dialokasikan ke payroll</th><th>Belum dialokasikan</th></tr></thead><tbody><tr>{[selected.original_amount, selected.settled_before_cutover, selected.opening_amount, selected.settled_amount, selected.remaining_amount, selected.reserved_amount, selected.available_amount].map((v,i) => <td key={i}>{money(v)}</td>)}</tr></tbody></table></div>
    {selected.allocations.length > 0 && <ul>{selected.allocations.map(a => <li key={a.payroll_id}>{a.payroll_number} · {money(a.amount)} · {a.status}{['DRAFT','CALCULATED','REVIEW'].includes(a.status) && <button type="button" disabled={locked} onClick={() => allocate({ balance_id:selected.balance_id, payroll_id:a.payroll_id, expected_payroll_version:a.row_version, amount:'0' })}>Lepas alokasi {a.payroll_number}</button>}</li>)}</ul>}
    <div className="initial-import-toolbar"><label>Payroll draft<select aria-label="Payroll untuk kasbon" disabled={locked} value={payroll?.id ?? ''} onChange={e => { setPayrollId(e.target.value); setAmount(selected.allocations.find(a => a.payroll_id === e.target.value)?.amount ?? '') }}><option value="">Pilih payroll mandor ini</option>{payrolls.map(p => <option key={p.id} value={p.id}>{p.payroll_number}</option>)}</select></label><label>Nominal alokasi<input aria-label="Nominal alokasi kasbon" inputMode="decimal" value={amount} disabled={locked} onChange={e => setAmount(e.target.value)}/></label><button type="button" disabled={locked || !payroll || !/^[0-9]+([.,][0-9]{1,2})?$/.test(amount) || !/[1-9]/.test(amount)} onClick={() => { if (payroll) allocate({ balance_id:selected.balance_id, payroll_id:payroll.id, expected_payroll_version:payroll.row_version, amount }) }}>Simpan alokasi kasbon</button></div>
    {!payrolls.length && <p>Belum ada payroll draft untuk mandor ini.</p>}
  </section>
}

function PrepaymentBalances({ batch, locked, manage }: { batch: Batch; locked: boolean; manage: (payload: Record<string, Json>) => void }) {
  const [selectedId, setSelectedId] = useState(''), [targetId, setTargetId] = useState(''), [cashId, setCashId] = useState('')
  const [operation, setOperation] = useState('APPLY'), [amount, setAmount] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('')
  const selected = batch.prepayments.find(a => a.id === selectedId) ?? batch.prepayments[0]
  const target = selected?.targets.find(t => t.id === targetId), cash = batch.prepayment_cash_accounts.find(c => c.id === cashId)
  const labels: Record<string, string> = { APPLY:'Pakai untuk tagihan', REFUND:'Catat pengembalian uang', CORRECT:'Koreksi saldo awal', CORRECTION:'Koreksi saldo awal', REVERSAL:'Pembatalan' }
  const money = (value: string) => `Rp ${value.replace('.', ',')}`
  const valid = /^[0-9]+([.,][0-9]{1,2})?$/.test(amount) && (operation === 'CORRECT' || /[1-9]/.test(amount)) && dateText(date) && reason.trim().length > 0
    && (operation !== 'APPLY' || Boolean(target)) && (operation !== 'REFUND' || Boolean(cash))
  if (!selected) return null
  const send = (payload: Record<string, Json>) => manage({ advance_id:selected.id, reason:reason.trim(), ...payload })
  return <section className="panel initial-import-advances" aria-label="Uang muka saldo awal">
    <h2>Uang muka saldo awal</h2>
    <p>Pakai sisa uang muka untuk mengurangi tagihan pihak yang sama. Uang kas bergerak saat pengembalian. Koreksi dan pembatalan tetap tercatat dalam riwayat.</p>
    <label>Dokumen uang muka<select aria-label="Dokumen uang muka" disabled={locked} value={selected.id} onChange={e => { setSelectedId(e.target.value); setTargetId(''); setAmount('') }}>{batch.prepayments.map(p => <option key={p.id} value={p.id}>{p.party_name} · {p.document_number}</option>)}</select></label>
    <div className="initial-import-table"><table><thead><tr><th>Nominal asal</th><th>Terpakai/kembali sebelum saldo awal</th><th>Saldo awal saat ini</th><th>Dipakai untuk tagihan</th><th>Dikembalikan</th><th>Sisa uang muka</th></tr></thead><tbody><tr>{[selected.original_amount,selected.settled_before_cutover,selected.opening_amount,selected.applied_amount,selected.refunded_amount,selected.remaining_amount].map((v,i) => <td key={i}>{money(v)}</td>)}</tr></tbody></table></div>
    <div className="initial-import-toolbar">
      <label>Tindakan<select aria-label="Tindakan uang muka" disabled={locked} value={operation} onChange={e => { setOperation(e.target.value); setAmount('') }}>{['APPLY','REFUND','CORRECT'].map(v => <option key={v} value={v}>{labels[v]}</option>)}</select></label>
      {operation === 'APPLY' && <label>Tagihan<select aria-label="Tagihan untuk uang muka" disabled={locked} value={target?.id ?? ''} onChange={e => setTargetId(e.target.value)}><option value="">Pilih tagihan pihak ini</option>{selected.targets.map(t => <option key={t.id} value={t.id}>{t.number} · sisa {money(t.remaining_amount)}</option>)}</select></label>}
      {operation === 'REFUND' && <label>Rekening pengembalian<select aria-label="Rekening pengembalian uang muka" disabled={locked} value={cash?.id ?? ''} onChange={e => setCashId(e.target.value)}><option value="">Pilih rekening kas/bank</option>{batch.prepayment_cash_accounts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
      <label>{operation === 'CORRECT' ? 'Saldo awal pengganti' : 'Nominal'}<input aria-label="Nominal uang muka" inputMode="decimal" disabled={locked} value={amount} onChange={e => setAmount(e.target.value)}/></label>
      <label>Tanggal kejadian<input aria-label="Tanggal uang muka" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>
      <label>Alasan / catatan<input aria-label="Alasan uang muka" disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !valid} onClick={() => send({ operation, amount, effective_date:date, ...(operation === 'APPLY' && target ? { target_id:target.id } : {}), ...(operation === 'REFUND' && cash ? { cash_account_id:cash.id } : {}) })}>{labels[operation]}</button>
    </div>
    {operation === 'APPLY' && !selected.targets.length && <p>Belum ada tagihan dengan sisa pembayaran untuk pihak ini.</p>}
    {selected.payments.length > 0 && <ul>{selected.payments.map(p => <li key={p.id}>{p.number} · {money(p.amount)} · {p.status === 'REVERSED' ? 'Dibatalkan' : p.status === 'POSTED' ? 'Sudah dipakai' : 'Draft'}{p.status === 'POSTED' && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({operation:'REVERSE_PAYMENT',payment_id:p.id})}>Batalkan pemakaian {p.number}</button>}</li>)}</ul>}
    {selected.events.length > 0 && <ul>{selected.events.map(e => <li key={e.id}>{labels[e.kind]} · {e.date} · {money(e.delta)} · {e.reason}{e.reversed ? ' · Dibatalkan' : e.kind !== 'REVERSAL' && <button type="button" disabled={locked || !reason.trim()} onClick={() => send({operation:'REVERSE_EVENT',event_id:e.id})}>Batalkan perubahan {e.date}</button>}</li>)}</ul>}
  </section>
}

// CP6-04: every editable batch is listed (the server no longer cuts open drafts); a long list gets a search box.
const BATCH_SEARCH_FROM = 20

export default function ConnectedInitialImportPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel initial-import"><h1>Impor data awal</h1><p>Masuk ke ERP yang tersambung untuk mengunggah dan memeriksa data awal.</p></section>
  if (!['OWNER', 'ADMIN'].includes(identity.profile.role)) return <section className="panel initial-import" role="alert"><h1>Impor data awal</h1><p>Halaman ini tersedia untuk owner dan admin.</p></section>
  return <ImportWorkspace key={`${runtime.projectRef}:${identity.profile.id}`} />
}

function ImportWorkspace() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('INITIAL_IMPORT')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [entity, setEntity] = useState<InitialImportEntity>('MATERIAL')
  const [editor, setEditor] = useState<InitialImportRow[] | null>(null)
  const [filename, setFilename] = useState('Perbaikan di aplikasi')
  const [code, setCode] = useState('')
  const [batchQuery, setBatchQuery] = useState('')
  const [date, setDate] = useState('')
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [reading, setReading] = useState(false)
  const batchId = useRef<string | null>(null)
  const editorRevision = useRef<string | null>(null)
  const readFileSequence = useRef(0)
  const loadSequence = useRef(0)
  const batch = workspace?.batch ?? null
  const spec = initialImportCatalog[entity]
  const fields = Object.entries(spec.fields)
  const storedRows = batch?.rows.filter((row) => row.entity === entity) ?? []
  const shownRows = editor ?? storedRows
  const locked = mutation.writerLocked || loading || reading
  const posted = batch?.status === 'POSTED'

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current
    const ticket = beginRead(), requested = batchId.current
    setLoading(true); setError('')
    try {
      const { data, error: failure } = await client.rpc('erp_get_initial_import_workspace_v1', { p_batch_id: requested })
      if (!isReadCurrent(ticket) || requested !== batchId.current) return false
      if (failure) throw failure
      const parsed = parseInitialImportWorkspace(data)
      if ((parsed.batch?.id ?? null) !== requested) throw new Error('Respons tidak sesuai batch yang dipilih.')
      setWorkspace(parsed)
      return finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket)) setError(normalizeClientError(failure).message)
      return false
    } finally { if (sequence === loadSequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { readFileSequence.current++ } }, [load])

  const handlers: ProductionMutationHandlers = {
    send: (envelope) => client.rpc('erp_save_initial_import_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (data, envelope) => {
      const result = object(data), payload = object(envelope.payload)
      if (result.request_id !== envelope.id || result.action !== envelope.action || typeof result.batch_id !== 'string'
        || !uuid.test(result.batch_id) || typeof result.status !== 'string'
        || (envelope.action !== 'CREATE' && result.batch_id !== payload.batch_id)) throw new Error('Respons transaksi tidak cocok.')
    },
    retire: (data) => { batchId.current = object(data).batch_id as string; setEditor(null); setPage(0); readFileSequence.current++ },
    reload: load,
  }
  const act = (action: string, extra: Record<string, Json> = {}) => {
    setError('')
    return run(action, { batch_id: batch?.id ?? null, expected_revision: action === 'SAVE_FILE' ? editorRevision.current : batch?.revision ?? null, ...extra }, null, handlers)
  }
  const upload = async (file: File | undefined) => {
    if (!file || locked || posted) return
    const sequence = ++readFileSequence.current, selected = entity, selectedBatch = batch?.id
    setReading(true); setError('')
    try {
      const rows = await readInitialImportFile(file, selected)
      if (sequence !== readFileSequence.current || selected !== entity || selectedBatch !== batchId.current) return
      editorRevision.current = batch?.revision ?? null; setEditor(rows); setFilename(file.name); setPage(0)
    } catch (failure) { if (sequence === readFileSequence.current) setError(normalizeClientError(failure).message) }
    finally { if (sequence === readFileSequence.current) setReading(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([initialImportTemplate(entity)], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `Impor_${entity}.csv`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const errors = batch?.rows.filter((row) => row.errors.length) ?? []
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">PENGATURAN ERP</div><h1>Impor data awal</h1><p>Unggah tabel dari Excel, periksa isinya, lalu sahkan setelah semuanya cocok.</p></div><button type="button" disabled={mutation.busy || reading || Boolean(editor)} onClick={() => void load()}><RefreshCw size={16}/> Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <div className="panel initial-import-toolbar">
      {(workspace?.recent.length ?? 0) > BATCH_SEARCH_FROM && <label>Cari batch<input type="search" aria-label="Cari batch impor" value={batchQuery} disabled={locked || Boolean(editor)} onChange={(event) => setBatchQuery(event.target.value)} placeholder="Kode atau status batch"/></label>}
      <label>Batch impor<select aria-label="Batch impor" disabled={locked || Boolean(editor)} value={batch?.id ?? ''} onChange={(event) => { batchId.current = event.target.value || null; setPage(0); void load() }}><option value="">Buat batch baru</option>{workspace?.recent.filter((item) => item.id === batch?.id || (workspace.recent.length ?? 0) <= BATCH_SEARCH_FROM || !batchQuery.trim() || `${item.batch_code} ${item.status}`.toLowerCase().includes(batchQuery.trim().toLowerCase())).map((item) => <option key={item.id} value={item.id}>{item.batch_code} · {item.status}</option>)}</select></label>
      {!batch && <><label>Kode batch<input value={code} disabled={locked} maxLength={60} onChange={(event) => setCode(event.target.value)} placeholder="SALDO-AWAL-2026"/></label><label>Tanggal saldo awal<input type="date" value={date} disabled={locked} onChange={(event) => setDate(event.target.value)}/></label><button type="button" disabled={locked || !date || !code.trim()} onClick={() => void act('CREATE', { batch_code: code.trim(), cutover_date: date })}>Buat draft</button></>}
      {batch && <div><strong>{batch.code}</strong><p>{new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeZone: 'Asia/Jakarta' }).format(new Date(batch.cutover_at))} · {posted ? 'Sudah disahkan' : 'Draft'} · {batch.rows.length} baris</p></div>}
    </div>
    {batch && <>
      {posted && batch.cash_advances.length > 0 && <CashAdvanceBalances key={batch.id} batch={batch} locked={locked} allocate={payload => { void act('ALLOCATE_CASH_ADVANCE', payload) }}/>} 
      {posted && batch.prepayments.length > 0 && <PrepaymentBalances key={batch.id} batch={batch} locked={locked} manage={payload => { void act('PREPAYMENT', payload) }}/>} 
      {posted && batch.production_sources.length > 0 && <ProductionBalances key={batch.id} batch={batch} locked={locked} manage={payload => { void act('WIP_OUTPUT', payload) }}/>}
      {posted && batch.bb && <>
        <OpeningBalancesPanel key={`oss-${batch.id}`} bb={batch.bb} cashAccounts={batch.prepayment_cash_accounts} locked={locked} manage={(action, payload) => { void act(action, payload) }}/>
        <CustomerCreditsPanel key={`credit-${batch.id}`} bb={batch.bb} cashAccounts={batch.prepayment_cash_accounts} locked={locked} manage={(action, payload) => { void act(action, payload) }}/>
        <ReturnRightsPanel key={`return-${batch.id}`} bb={batch.bb} locked={locked} manage={(action, payload) => { void act(action, payload) }}/>
        <PurchaseCommitmentsPanel key={`po-${batch.id}`} bb={batch.bb} locked={locked} manage={(action, payload) => { void act(action, payload) }}/>
        {batch.bb.payroll_entitlements.length > 0 && <PayrollEntitlementsPanel key={`y02-${batch.id}`} bb={batch.bb} locked={locked} manage={(action, payload) => { void act(action, payload) }}/>}
        <OpeningReworksPanel bb={batch.bb}/>
        <OpenSalesDraftsPanel bb={batch.bb}/>
        {batch.bb.legacy_documents > 0 && <p className="initial-import-help">{batch.bb.legacy_documents} dokumen lama yang sudah lunas tercatat sebagai riwayat; tidak ada saldo atau kas baru darinya.</p>}
      </>}
      <div className="panel initial-import-toolbar"><label>Jenis data<select disabled={locked || Boolean(editor)} value={entity} onChange={(event) => { setEntity(event.target.value as InitialImportEntity); setPage(0); readFileSequence.current++ }}>{Object.entries(initialImportCatalog).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}</select></label><button type="button" onClick={download}><Download size={16}/> Unduh template</button>{!posted && <label className="initial-import-upload"><FileUp size={16}/> Pilih file CSV<input aria-label="Pilih file CSV" type="file" accept=".csv,.tsv,text/csv" disabled={locked || Boolean(editor)} onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ''; void upload(file) }}/></label>}</div>
      <p className="initial-import-help">Simpan dari Excel sebagai <strong>CSV UTF-8</strong>. Angka tanpa pemisah ribuan; desimal boleh memakai titik atau koma. Kolom aktif/absensi: true atau false. Satuan memakai kode ERP. Maksimal 5 MB dan 5.000 baris per batch. Hubungkan setiap rincian saldo ke kode total pembanding. Total pembanding hanya diperiksa dan tidak dibukukan.</p>
      {entity === 'UNINVOICED_RECEIPT' && <p className="initial-import-help">Isi seluruh jumlah penerimaan yang belum ditagih. Hubungkan bagian yang masih berupa bahan ke kode rincian stok asal; rincikan bagian yang sudah terpakai pada Asal biaya sebelum cutover. Jumlah keduanya harus sama dengan jumlah penerimaan. Gunakan total pembanding GRNI_MATERIAL; nilai dibulatkan dua desimal per dokumen penerimaan. Tanggal invoice berikutnya harus sejak tanggal saldo awal. Asal biaya merupakan bagian dari nilai WIP/BS/FG yang diimpor dan tidak menambah nilai saldo lagi.</p>}
      {entity === 'OPENING_BALANCE_ITEM' && <p className="initial-import-help">Untuk kasbon tunai mandor, isi jenis saldo CONTRACTOR_RECEIVABLE dan jenis sumber CONTRACTOR_CASH_ADVANCE. Wajib isi nomor dan tanggal dokumen, nominal awal, serta pembayaran sebelum saldo awal; nominal tersisa harus sama dengan selisihnya. Pembayaran lama tidak membentuk arus kas baru. Saldo lainnya memakai jenis sumber BALANCE atau dibiarkan kosong.</p>}
      {entity === 'OPENING_COST_ORIGIN' && <p className="initial-import-help">Hubungkan supplier, nomor penerimaan, dan nomor barisnya ke kode rincian WIP/BS/FG. Jumlah adalah satuan bahan asal, bukan jumlah pakaian. Nilai bahan yang terurai tidak boleh melebihi nilai saldo tujuan.</p>}
      {entity === 'OPENING_BALANCE_ITEM' && <p className="initial-import-help">Saldo fisik WIP/BS perlu kode sumber, OPEN_PO dalam batch yang sama, ukuran, pcs bulat, nilai biaya, serta tahap CUTTING, SEWING, atau LAUNDRY (BS juga boleh QC). Isi mandor untuk SEWING atau vendor untuk LAUNDRY; potongan yang menunggu pickup (CUTTING) diisi lokasi potong tanpa mandor. Isi apakah biaya aksesoris sudah termasuk: true atau false. Pisahkan ringkasan WIP tanpa rincian fisik dari batch ini.</p>}
      {entity === 'OPENING_ADVANCE' && <p className="initial-import-help">Isi jenis pihak SUPPLIER, CUSTOMER, atau VENDOR dan nomor bukti uang muka. Sisa harus sama dengan nominal asal dikurangi pemakaian atau pengembalian sebelumnya. Gunakan akun khusus uang muka: aset untuk supplier/laundry dan kewajiban untuk pelanggan. Jenis total pembanding mengikuti pihak: SUPPLIER_ADVANCE, CUSTOMER_ADVANCE, atau VENDOR_ADVANCE.</p>}
      {entity === 'OPENING_REWORK' && <p className="initial-import-help">Isi rework yang masih di mandor atau laundry saat saldo awal. Kode rincian BS asal menunjuk baris BS ber-PO di batch ini; tujuan dan pemegang harus sama dengan pemegang BS itu. Sisa di rework harus sama dengan jumlah dikirim dikurangi yang sudah kembali. Rework ke mandor memerlukan komponen dengan tarif mandor yang berlaku, dan produk BS memerlukan BOM aksesori (BOM kosong pun dicatat).</p>}
      {entity === 'OPENING_REWORK_COMPONENT' && <p className="initial-import-help">Satu baris per komponen kerja rework: pcs yang komponennya sudah selesai sebelum BS (tidak dibayar lagi), pcs yang akan dikerjakan, dan tarif per pcs yang harus sama dengan tarif mandor yang berlaku.</p>}
      {editor && editorRevision.current !== batch.revision && <p role="alert" className="initial-import-message">Draft di server sudah berubah. Perubahan di layar ini belum disimpan; batalkan perubahan lokal lalu periksa isi terbaru sebelum mengunggah ulang.</p>}
      {editor && <div className="initial-import-message" role="status"><span>{filename} · {editor.length} baris belum disimpan. Penyimpanan mengganti seluruh bagian “{spec.label}” dalam draft ini.</span><button type="button" disabled={locked || editorRevision.current !== batch.revision} onClick={() => void act('SAVE_FILE', { entity, filename, rows: editor as unknown as Json })}>Simpan perubahan draft</button><button type="button" disabled={mutation.busy || reading} onClick={() => { setEditor(null); setPage(0) }}>Batalkan perubahan</button></div>}
      <div className="panel initial-import-table"><table><thead><tr><th>Baris file</th>{fields.map(([key, label]) => <th key={key}>{label}{(spec.required as readonly string[]).includes(key) ? ' *' : ''}</th>)}{!editor && <th>Pemeriksaan</th>}</tr></thead><tbody>{shownRows.slice(page * 50, (page + 1) * 50).map((row, index) => <tr key={row.source_row_no}><th>{row.source_row_no}</th>{fields.map(([key, label]) => <td key={key}>{posted ? row.payload[key] ?? '—' : <input aria-label={`${label}, baris ${row.source_row_no}`} value={row.payload[key] ?? ''} disabled={locked} onChange={(event) => { const value = event.target.value; if (!editor) editorRevision.current = batch.revision; setEditor((current) => (current ?? storedRows).map((old, i) => i === page * 50 + index ? { source_row_no: old.source_row_no, payload: { ...old.payload, [key]: value } } : { source_row_no: old.source_row_no, payload: { ...old.payload } })); setFilename('Perbaikan di aplikasi') }}/>}</td>)}{!editor && <td>{(row as Row).errors?.join(' · ') || ((row as Row).validation_status === 'VALID' ? 'Valid' : 'Belum diperiksa')}</td>}</tr>)}</tbody></table>{shownRows.length === 0 && <p>Belum ada data {spec.label.toLowerCase()}. Unduh template lalu pilih file yang sudah diisi.</p>}</div>
      {shownRows.length > 50 && <nav className="initial-import-pagination" aria-label="Halaman rincian"><button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>Sebelumnya</button><span>{page + 1} / {Math.ceil(shownRows.length / 50)}</span><button type="button" disabled={(page + 1) * 50 >= shownRows.length} onClick={() => setPage(page + 1)}>Berikutnya</button></nav>}
      {errors.length > 0 && <div className="panel initial-import-errors" role="alert"><strong>{errors.length} baris perlu diperbaiki</strong><ul>{errors.slice(0,30).map((row) => <li key={row.id}>{initialImportCatalog[row.entity].label}, baris {row.source_row_no}: {row.errors.join(' · ')}</li>)}</ul>{errors.length > 30 && <p>Pilih jenis data untuk melihat seluruh kesalahan di tabel.</p>}</div>}
      {!posted && <footer className="panel initial-import-toolbar"><p>Draft tetap bisa diperbaiki. Pengesahan memeriksa ulang data terakhir dan membukukan seluruh batch sekaligus.</p><button type="button" disabled={locked || Boolean(editor) || !batch.rows.length} onClick={() => void act('VALIDATE')}>Periksa seluruh draft</button><button type="button" className="primary" disabled={locked || Boolean(editor) || !batch.rows.length || batch.status !== 'READY' || errors.length > 0} onClick={() => void act('FINALIZE')}>Sahkan data awal</button></footer>}
    </>}
  </section>
}
