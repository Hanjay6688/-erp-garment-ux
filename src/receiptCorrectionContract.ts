// "Benerin penerimaan": closed client contract for the owning receipt correction
// workspace and its committed outcome. Unknown fields or inconsistent lineage
// are refused instead of rendered.
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso } from './cp6BusinessTime'
const fail = (): never => { throw Error('Data pembetulan penerimaan belum cocok dengan sumber yang diperiksa. Muat ulang penerimaan.') }
const object = (v: unknown) => { if (!v || typeof v !== 'object' || Array.isArray(v)) return fail(); return v as Record<string, unknown> }
const id = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const at = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
const decimal = (v: unknown): v is string => typeof v === 'string' && /^-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?$/.test(v)
const text = (v: unknown): v is string | null => v === null || typeof v === 'string'
const day = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
function closed(v: unknown, keys: string[], optional: string[] = []) {
  const r = object(v)
  if (keys.some(k => !(k in r)) || Object.keys(r).some(k => !keys.includes(k) && !optional.includes(k))) fail()
  return r
}
// Immutable actor UUID; the display name is the current profile name, or null
// (same contract as cp7_note.workspace_with_actors).
const actor = (h: Record<string, unknown>) => id(h.actor_id) && h.actor_name_basis === 'CURRENT_PROFILE'
  && (h.actor_display_name === null || (typeof h.actor_display_name === 'string' && h.actor_display_name.trim() !== ''))
export type CorrectionRoll = { roll_id: string; roll_number: string; qty: string; cached_qty: string; status: string; used_qty: string; min_qty: string; movable: boolean; uses: { source_type: string; movement_type: string; count: number }[] }
export type CorrectionLine = { item_id: string; material_id: string; material_sku: string; material_name: string; material_type: string; unit_code: string; qty: string; unit_price: string; line_total: string; price_state: string; price_source: string; invoice_match_state: string; lot_number: string | null; notes: string | null; min_qty: string; rolls: CorrectionRoll[] }
export type CorrectionInvoiceLine = { invoice_line_id: string; purchase_item_id: string; qty_invoiced: string; unit_price: string; discount_amount: string; net_amount: string; notes: string | null }
export type CreditTarget = { purchase_id: string; purchase_number: string; physical_at: string; remaining: string }
export type CorrectionInvoice = { invoice_id: string; invoice_number: string; invoice_date: string; received_at: string; due_date: string | null; row_version: string; notes: string | null; lines: CorrectionInvoiceLine[]; other_receipts: { purchase_id: string; purchase_number: string }[] }
export type CorrectionRevision = { revision_id: string; revision: string; previous_purchase_id: string; previous_purchase_number: string; replacement_purchase_id: string; replacement_purchase_number: string; effective_at: string; recorded_at: string; reason: string; actor_id: string; actor_display_name: string | null; actor_name_basis: 'CURRENT_PROFILE'; previous_document: unknown; corrected_document: unknown }
export type ReceiptCorrectionWorkspace = {
  contract_version: 'cp7.receipt-correction-workspace.v1'; read_at: string; root_purchase_id: string; current_purchase_id: string; original_purchase_number: string
  purchase: { purchase_id: string; purchase_number: string; status: string; row_version: string; supplier_id: string; supplier_name: string | null; location_id: string; location_name: string | null; physical_at: string; payment_status: string; supplier_invoice_number: string | null; due_date: string | null; notes: string | null }
  lines: CorrectionLine[]; invoices: CorrectionInvoice[]; credit_targets: CreditTarget[]; payments: { payment_id: string; payment_number: string; payment_date: string; amount: string; status: string }[]; paid_total: string
  blockers: { code: string; count: number; documents: { type: string; number: string }[] }[]; can_correct: boolean; review_token: string; history: CorrectionRevision[]; production_go: false
}
export function parseReceiptCorrectionWorkspace(v: unknown, requested: string): ReceiptCorrectionWorkspace {
  const r = closed(v, ['contract_version', 'read_at', 'root_purchase_id', 'current_purchase_id', 'original_purchase_number', 'purchase', 'lines', 'invoices', 'credit_targets', 'payments', 'paid_total', 'blockers', 'can_correct', 'review_token', 'history', 'production_go'])
  if (r.contract_version !== 'cp7.receipt-correction-workspace.v1' || !at(r.read_at) || !id(r.root_purchase_id) || !id(r.current_purchase_id) || typeof r.original_purchase_number !== 'string'
    || !Array.isArray(r.lines) || !Array.isArray(r.invoices) || !Array.isArray(r.credit_targets) || !Array.isArray(r.payments) || !decimal(r.paid_total) || !Array.isArray(r.blockers) || typeof r.can_correct !== 'boolean' || typeof r.review_token !== 'string' || !/^[0-9a-f]{32}$/.test(r.review_token)
    || !Array.isArray(r.history) || r.production_go !== false) return fail()
  const p = closed(r.purchase, ['purchase_id', 'purchase_number', 'status', 'row_version', 'supplier_id', 'supplier_name', 'location_id', 'location_name', 'physical_at', 'payment_status', 'supplier_invoice_number', 'due_date', 'notes'])
  if (p.purchase_id !== r.current_purchase_id || typeof p.purchase_number !== 'string' || !['POSTED', 'REVERSED', 'DRAFT'].includes(p.status as string) || typeof p.row_version !== 'string' || !/^[1-9][0-9]{0,18}$/.test(p.row_version)
    || !id(p.supplier_id) || !id(p.location_id) || !at(p.physical_at) || !text(p.supplier_name) || !text(p.location_name) || !text(p.supplier_invoice_number) || !text(p.notes)) return fail()
  for (const value of r.lines) {
    const l = closed(value, ['item_id', 'material_id', 'material_sku', 'material_name', 'material_type', 'unit_code', 'qty', 'unit_price', 'line_total', 'price_state', 'price_source', 'invoice_match_state', 'lot_number', 'notes', 'min_qty', 'rolls'])
    if (!id(l.item_id) || !id(l.material_id) || typeof l.material_name !== 'string' || !decimal(l.qty) || !decimal(l.unit_price) || !decimal(l.line_total) || typeof l.invoice_match_state !== 'string' || !decimal(l.min_qty) || !Array.isArray(l.rolls)) return fail()
    for (const roll of l.rolls as unknown[]) {
      const x = closed(roll, ['roll_id', 'roll_number', 'qty', 'cached_qty', 'status', 'used_qty', 'min_qty', 'movable', 'uses'])
      if (!id(x.roll_id) || typeof x.roll_number !== 'string' || !decimal(x.qty) || !decimal(x.cached_qty) || !decimal(x.used_qty) || !decimal(x.min_qty) || typeof x.movable !== 'boolean' || !Array.isArray(x.uses)) return fail()
    }
  }
  const items = new Set((r.lines as { item_id: string }[]).map(l => l.item_id))
  for (const value of r.invoices) {
    const x = closed(value, ['invoice_id', 'invoice_number', 'invoice_date', 'received_at', 'due_date', 'row_version', 'notes', 'lines', 'other_receipts'])
    if (!id(x.invoice_id) || typeof x.invoice_number !== 'string' || !day(x.invoice_date) || !at(x.received_at) || x.due_date !== null && !day(x.due_date) || typeof x.row_version !== 'string' || !text(x.notes) || !Array.isArray(x.lines) || !x.lines.length || !Array.isArray(x.other_receipts)) return fail()
    for (const other of x.other_receipts as unknown[]) { const o = closed(other, ['purchase_id', 'purchase_number']); if (!id(o.purchase_id) || o.purchase_id === r.current_purchase_id || typeof o.purchase_number !== 'string') return fail() }
    for (const line of x.lines as unknown[]) {
      const y = closed(line, ['invoice_line_id', 'purchase_item_id', 'qty_invoiced', 'unit_price', 'discount_amount', 'net_amount', 'notes'])
      if (!id(y.invoice_line_id) || !id(y.purchase_item_id) || !items.has(y.purchase_item_id) || !decimal(y.qty_invoiced) || !decimal(y.unit_price) || !decimal(y.discount_amount) || !decimal(y.net_amount) || !text(y.notes)) return fail()
    }
  }
  for (const value of r.credit_targets) {
    const x = closed(value, ['purchase_id', 'purchase_number', 'physical_at', 'remaining'])
    if (!id(x.purchase_id) || x.purchase_id === r.current_purchase_id || typeof x.purchase_number !== 'string' || !at(x.physical_at) || !decimal(x.remaining) || Number(x.remaining) <= 0) return fail()
  }
  for (const value of r.payments) { const x = closed(value, ['payment_id', 'payment_number', 'payment_date', 'amount', 'status']); if (!id(x.payment_id) || !at(x.payment_date) || !decimal(x.amount)) return fail() }
  for (const value of r.blockers) {
    const x = closed(value, ['code', 'count', 'documents'])
    if (typeof x.code !== 'string' || typeof x.count !== 'number' || !Array.isArray(x.documents)) return fail()
    for (const d of x.documents) { const k = closed(d, ['type', 'number']); if (typeof k.type !== 'string' || typeof k.number !== 'string') return fail() }
  }
  let previous = r.root_purchase_id as string, revision = 0n; const seen = new Set<string>([previous])
  for (const value of r.history) {
    const h = closed(value, ['revision_id', 'revision', 'previous_purchase_id', 'previous_purchase_number', 'replacement_purchase_id', 'replacement_purchase_number', 'effective_at', 'recorded_at', 'reason', 'actor_id', 'actor_display_name', 'actor_name_basis', 'previous_document', 'corrected_document'])
    if (!id(h.revision_id) || h.previous_purchase_id !== previous || !id(h.replacement_purchase_id) || seen.has(h.replacement_purchase_id as string) || typeof h.revision !== 'string' || !/^[1-9][0-9]{0,18}$/.test(h.revision)
      || BigInt(h.revision) !== revision + 1n || !at(h.effective_at) || !at(h.recorded_at) || typeof h.reason !== 'string' || !actor(h)) return fail()
    previous = h.replacement_purchase_id as string; seen.add(previous); revision++
  }
  if (previous !== r.current_purchase_id || !seen.has(requested)) return fail()
  return r as unknown as ReceiptCorrectionWorkspace
}
export function parseReceiptCorrectionOutcome(v: unknown, request: string, source: string) {
  const r = closed(v, ['contract_version', 'kind', 'action', 'request_id', 'root_purchase_id', 'previous_purchase_id', 'purchase_id', 'revision_id', 'revision', 'effective_at', 'row_version'])
  if (r.contract_version !== 'cp7.receipt-correction-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'CORRECT' || r.request_id !== request || r.previous_purchase_id !== source
    || !id(r.root_purchase_id) || !id(r.purchase_id) || r.purchase_id === source || !id(r.revision_id) || typeof r.revision !== 'string' || !/^[1-9][0-9]{0,18}$/.test(r.revision) || !at(r.effective_at)
    || typeof r.row_version !== 'string') return fail()
  return r as typeof r & { purchase_id: string }
}
export type DraftRoll = { key: string; replaces: string | null; number: string; qty: string; minQty: string; locked: boolean }
export type DraftLine = { key: string; replaces: string | null; materialId: string; materialName: string; materialType: string; unitCode: string; qty: string; minQty: string; price: string; priceState: string; priceSource: string; rolls: DraftRoll[] }
export type DraftInvoiceLine = { replaces: string; itemId: string; qty: string; price: string; discount: string }
export type DraftInvoice = { replaces: string; number: string; date: string; lines: DraftInvoiceLine[]; head?: { number: string; date: string; dueDate: string } }
export type DraftCredit = { purchaseId: string; amount: string }
/** The receipt as it really was: delivery-note number (without revision suffix), WIB arrival time, warehouse, supplier. */
export type DraftHeader = { purchaseNumber: string; at: string; location: { id: string; name: string }; supplier: { id: string; name: string } }
const receiptBase = (n: string) => n.replace(/ · R\d+-[0-9a-f]{8}$/, ''), invoiceBase = (n: string) => n.replace(/ · R\d+$/, '')
export const draftHeader = (w: ReceiptCorrectionWorkspace): DraftHeader => ({ purchaseNumber: receiptBase(w.purchase.purchase_number), at: cp6WibDateTimeInput(w.purchase.physical_at),
  location: { id: w.purchase.location_id, name: w.purchase.location_name ?? '' }, supplier: { id: w.purchase.supplier_id, name: w.purchase.supplier_name ?? '' } })
// Exact money: decimals as integer micro-units, rounded to cents like the database (half away from zero).
const micros = (s: string) => { const [w, f = ''] = s.trim().replace(',', '.').split('.'); return BigInt(w || '0') * 1000000n + BigInt((f + '000000').slice(0, 6)) }
const cents = (scaled: bigint, scale: bigint) => (scaled >= 0n ? (scaled + scale / 2n) / scale : -((-scaled + scale / 2n) / scale))
const money = (c: bigint) => `${c < 0n ? '-' : ''}${(c < 0n ? -c : c) / 100n}.${String((c < 0n ? -c : c) % 100n).padStart(2, '0')}`
/** Paid amount above the corrected supplier total, in rupiah with cents ("0.00" when none). */
export function correctionExcess(w: ReceiptCorrectionWorkspace, lines: DraftLine[], invoices: DraftInvoice[]): string | null {
  let total = 0n
  for (const l of lines) {
    if (l.priceState !== 'FINAL') continue
    const qty = l.materialType === 'FABRIC' ? l.rolls.map(r => exact(r.qty, true)) : [exact(l.qty, true)], price = exact(l.price, false)
    if (price === null || qty.some(q => q === null)) return null
    for (const q of qty) total += micros(q as string) * micros(price)
  }
  for (const v of invoices) for (const l of v.lines) {
    const q = exact(l.qty, true), p = exact(l.price, false), d = exact(l.discount || '0', false)
    if (!q || p === null || d === null) return null
    total += micros(q) * micros(p) - micros(d) * 1000000n
  }
  const excess = micros(w.paid_total) / 10000n - cents(total, 10000000000n)
  return money(excess > 0n ? excess : 0n)
}
const plain = (s: string) => s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s
const exact = (s: string, positive: boolean) => { const t = s.trim().replace(',', '.'); return /^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$/.test(t) && (!positive || Number(t) > 0) ? t : null }
export function correctionDraft(w: ReceiptCorrectionWorkspace): DraftLine[] {
  return w.lines.map(l => ({ key: l.item_id, replaces: l.item_id, materialId: l.material_id, materialName: l.material_name, materialType: l.material_type, unitCode: l.unit_code, qty: plain(l.qty), minQty: l.min_qty, price: plain(l.unit_price),
    priceState: l.price_state, priceSource: l.price_source, rolls: l.rolls.map(r => ({ key: r.roll_id, replaces: r.roll_id, number: r.roll_number, qty: plain(r.qty), minQty: r.min_qty, locked: Number(r.used_qty) > 0 })) }))
}
/** Every posted supplier invoice of the receipt, line by line, as it now reads. */
export function correctionInvoices(w: ReceiptCorrectionWorkspace): DraftInvoice[] {
  return w.invoices.map(v => ({ replaces: v.invoice_id, number: v.invoice_number, date: v.invoice_date, head: { number: invoiceBase(v.invoice_number), date: v.invoice_date, dueDate: v.due_date ?? '' },
    lines: v.lines.map(l => ({ replaces: l.invoice_line_id, itemId: l.purchase_item_id, qty: plain(l.qty_invoiced), price: plain(l.unit_price), discount: plain(l.discount_amount) })) }))
}
/** The exact command payload, or the reason it cannot be sent yet. */
export function correctionPayload(w: ReceiptCorrectionWorkspace, lines: DraftLine[], reason: string, invoices: DraftInvoice[] = [], credits: DraftCredit[] = [], header?: DraftHeader): { payload: Record<string, unknown> | null; problem: string | null } {
  if (reason.trim().length < 5) return { payload: null, problem: 'Tulis alasan pembetulan (minimal 5 huruf).' }
  if (!lines.length) return { payload: null, problem: 'Penerimaan harus punya minimal satu barang.' }
  const out = []
  for (const l of lines) {
    const price = exact(l.price, false)
    if (price === null) return { payload: null, problem: `Harga ${l.materialName} belum benar.` }
    if (l.materialType === 'FABRIC') {
      if (!l.rolls.length) return { payload: null, problem: `${l.materialName} harus punya minimal satu roll.` }
      const rolls = []
      for (const r of l.rolls) {
        const qty = exact(r.qty, true)
        if (!qty || !r.number.trim()) return { payload: null, problem: `Nomor atau jumlah roll ${r.number || 'baru'} belum benar.` }
        if (r.replaces && Number(qty) < Number(r.minQty)) return { payload: null, problem: `Roll ${r.number} sudah terpakai ${r.minQty}; jumlah benar tidak boleh lebih kecil.` }
        rolls.push({ ...(r.replaces ? { replaces_roll_id: r.replaces } : {}), roll_number: r.number.trim(), qty })
      }
      const numbers = rolls.map(r => r.roll_number), twice = numbers.find((n, k) => numbers.indexOf(n) !== k)
      if (twice) return { payload: null, problem: `Nomor roll ${twice} dipakai lebih dari sekali.` }
      out.push({ ...(l.replaces ? { replaces_item_id: l.replaces } : {}), material_id: l.materialId, unit_price: price, price_state: l.priceState, price_source: l.priceSource, rolls })
    } else {
      const qty = exact(l.qty, true)
      if (!qty) return { payload: null, problem: `Jumlah ${l.materialName} belum benar.` }
      // Already left the receipt location (transfer/issue): the same material keeps at least that much.
      const source = w.lines.find(x => x.item_id === l.replaces)
      if (source && Number(source.min_qty) > 0 && (source.material_id !== l.materialId || Number(qty) < Number(source.min_qty)))
        return { payload: null, problem: `${source.material_name} sudah keluar ${plain(source.min_qty)} ${source.unit_code} dari gudang penerimaan; jumlah benar tidak boleh lebih kecil dan bahannya tidak bisa diganti.` }
      out.push({ ...(l.replaces ? { replaces_item_id: l.replaces } : {}), material_id: l.materialId, unit_price: price, price_state: l.priceState, price_source: l.priceSource, qty, rolls: [] })
    }
  }
  const removed = w.lines.flatMap(l => l.rolls).filter(r => Number(r.used_qty) > 0 && !lines.some(l => l.rolls.some(x => x.replaces === r.roll_id)))
  if (removed.length) return { payload: null, problem: `Roll ${removed.map(r => r.roll_number).join(', ')} sudah terpakai sehingga tidak bisa dihapus.` }
  if (invoices.length !== w.invoices.length) return { payload: null, problem: 'Muat ulang penerimaan: daftar invoice supplier sudah berubah.' }
  const outInvoices = [], invoiced = new Map<string, number>()
  for (const v of invoices) {
    const doc = w.invoices.find(x => x.invoice_id === v.replaces)
    if (!doc || v.lines.length !== doc.lines.length) return { payload: null, problem: 'Muat ulang penerimaan: daftar invoice supplier sudah berubah.' }
    const outLines = []
    for (const l of v.lines) {
      const line = lines.find(x => x.replaces === l.itemId), name = line?.materialName ?? 'barang'
      if (!line) return { payload: null, problem: `Barang yang ditagih di invoice ${v.number} tidak boleh dihapus dari penerimaan. Batalkan invoice itu dulu bila barangnya memang tidak ada.` }
      const qty = exact(l.qty, true), price = exact(l.price, false), discount = exact(l.discount || '0', false)
      if (!qty || price === null || discount === null) return { payload: null, problem: `Jumlah, harga final atau diskon ${name} di invoice ${v.number} belum benar.` }
      if (micros(discount) * 1000000n > micros(qty) * micros(price)) return { payload: null, problem: `Diskon ${name} di invoice ${v.number} lebih besar dari nilainya.` }
      invoiced.set(l.itemId, (invoiced.get(l.itemId) ?? 0) + Number(qty))
      outLines.push({ replaces_invoice_line_id: l.replaces, qty_invoiced: qty, unit_price: price, discount_amount: discount })
    }
    // Supplier invoice number, date and due date as typed: sent only when changed.
    const fix: Record<string, string> = {}
    if (v.head) {
      const number = v.head.number.trim(), date = v.head.date.trim(), due = v.head.dueDate.trim()
      if (number !== invoiceBase(doc.invoice_number)) { if (!number || number.length > 90) return { payload: null, problem: `Nomor invoice ${v.number} belum benar.` }; fix.invoice_number = number }
      if (date !== doc.invoice_date) { if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return { payload: null, problem: `Tanggal invoice ${v.number} belum benar.` }; fix.invoice_date = date }
      if (due !== (doc.due_date ?? '')) { if (due && !/^\d{4}-\d{2}-\d{2}$/.test(due)) return { payload: null, problem: `Jatuh tempo invoice ${v.number} belum benar.` }; fix.due_date = due }
    }
    outInvoices.push({ replaces_invoice_id: v.replaces, ...fix, lines: outLines })
  }
  for (const [item, qty] of invoiced) {
    const line = lines.find(x => x.replaces === item)!
    const received = line.materialType === 'FABRIC' ? line.rolls.reduce((s, r) => s + Number(r.qty), 0) : Number(line.qty)
    if (qty > received + 1e-9) return { payload: null, problem: `Jumlah ditagih ${line.materialName} (${qty}) lebih besar dari jumlah diterima yang benar (${received}).` }
  }
  // Paid more than the corrected total: the excess is supplier credit (retur bayangan, barang tidak pernah diterima) cut from other nota of the same supplier.
  const excess = correctionExcess(w, lines, invoices), outCredits = []
  if (excess === null) return { payload: null, problem: 'Harga atau jumlah belum benar.' }
  if (excess !== '0.00') {
    let sum = 0n
    for (const c of credits) {
      if (!c.amount.trim()) continue
      const amount = exact(c.amount, true), target = w.credit_targets.find(t => t.purchase_id === c.purchaseId)
      if (!amount || !target || micros(amount) % 10000n !== 0n) return { payload: null, problem: 'Jumlah kredit per nota belum benar (rupiah, paling banyak 2 angka di belakang koma).' }
      if (micros(amount) > micros(target.remaining)) return { payload: null, problem: `Kredit untuk ${target.purchase_number} melebihi sisa utangnya Rp${target.remaining}.` }
      sum += micros(amount); outCredits.push({ purchase_id: c.purchaseId, amount: money(micros(amount) / 10000n) })
    }
    if (!w.credit_targets.length) return { payload: null, problem: `Sudah dibayar Rp${excess} lebih dari total yang benar. Belum ada nota lain dari supplier ini yang masih punya sisa utang; simpan pembetulan setelah nota berikutnya dicatat.` }
    if (money(sum / 10000n) !== excess) return { payload: null, problem: `Kelebihan bayar Rp${excess} harus ditempel penuh ke nota lain dari supplier yang sama (sekarang Rp${money(sum / 10000n)}).` }
  }
  // Receipt (delivery-note) number as typed: sent only when changed.
  const head: Record<string, string> = {}
  if (header) {
    const number = header.purchaseNumber.trim()
    if (number !== receiptBase(w.purchase.purchase_number)) {
      if (!number || number.length > 40) return { payload: null, problem: 'Nomor surat jalan harus 1–40 huruf.' }
      head.purchase_number = number
    }
    // Arrival time, warehouse and supplier as they really were (sent only when changed).
    if (header.at !== cp6WibDateTimeInput(w.purchase.physical_at)) {
      const at = cp6WibPhysicalTimeToIso(header.at)
      if (!at) return { payload: null, problem: 'Tanggal dan jam datang belum benar.' }
      if (Date.parse(at) > Date.now()) return { payload: null, problem: 'Tanggal datang tidak boleh di masa depan.' }
      head.physical_at = at
    }
    if (header.location.id !== w.purchase.location_id) head.location_id = header.location.id
    if (header.supplier.id !== w.purchase.supplier_id) {
      if (outCredits.length) return { payload: null, problem: 'Kelebihan bayar dan ganti supplier tidak bisa sekaligus: nota tujuan kredit harus dari supplier yang benar. Simpan pembetulan supplier dulu, lalu betulkan jumlahnya.' }
      head.supplier_id = header.supplier.id
    }
  }
  return { payload: { purchase_id: w.current_purchase_id, review_token: w.review_token, change_reason: reason.trim(), lines: out, ...head, ...(outInvoices.length ? { invoices: outInvoices } : {}), ...(outCredits.length ? { credit_allocations: outCredits } : {}) }, problem: null }
}

// Material card v2: same scope/access/money projection as v1; a corrected
// receipt row shows its effective quantity with the original and its raw audit members.
export type CardMember = { movement_id: string; qty_signed: string; movement_type: string; recorded_at: string; physical_at: string; source_type: string; reversal_of_id: string | null; note: string | null }
export type CardRow = { movement_id: string; physical_at: string; recorded_at: string; movement_type: string; qty_signed: string; original_qty_signed: string; running_qty: string; correction_count: string; last_correction_recorded_at: string | null; corrections: CardMember[]; source_type: string; source_id: string | null; reversal_of_id: string | null; note: string | null; valuation?: { state: 'KNOWN' | 'UNKNOWN'; unit_cost: string | null; movement_value: string | null; basis: 'CURRENT_RESTATED_MOVEMENT_COST' } }
export type MaterialCard = { contract_version: 'cp7.material-ledger.v2'; material_id: string; roll_id: string | null; location_id: string; read_at: string; financial_captured: boolean; history_basis: 'CORRECTED_EFFECTIVE_ROWS_CURRENT_RESTATED'; page: { rows: CardRow[]; total: string; offset: number; limit: number; next_offset: number | null } }
export function parseMaterialCard(v: unknown, finance: boolean): MaterialCard {
  const w = closed(v, ['contract_version', 'material_id', 'roll_id', 'location_id', 'read_at', 'financial_captured', 'history_basis', 'page'])
  if (w.contract_version !== 'cp7.material-ledger.v2' || !id(w.material_id) || !id(w.location_id) || w.roll_id !== null && !id(w.roll_id) || !at(w.read_at) || w.financial_captured !== finance || w.history_basis !== 'CORRECTED_EFFECTIVE_ROWS_CURRENT_RESTATED') return fail()
  const p = closed(w.page, ['rows', 'total', 'offset', 'limit', 'next_offset'])
  if (!Array.isArray(p.rows) || typeof p.total !== 'string' || !/^[0-9]+$/.test(p.total) || typeof p.offset !== 'number' || typeof p.limit !== 'number' || p.next_offset !== null && typeof p.next_offset !== 'number') return fail()
  const seen = new Set<string>()
  for (const value of p.rows) {
    const r = closed(value, ['movement_id', 'physical_at', 'recorded_at', 'movement_type', 'qty_signed', 'original_qty_signed', 'running_qty', 'correction_count', 'last_correction_recorded_at', 'corrections', 'source_type', 'source_id', 'reversal_of_id', 'note'], finance ? ['valuation'] : [])
    if (!id(r.movement_id) || seen.has(r.movement_id) || !at(r.physical_at) || !at(r.recorded_at) || typeof r.movement_type !== 'string' || !decimal(r.qty_signed) || !decimal(r.original_qty_signed) || !decimal(r.running_qty)
      || typeof r.correction_count !== 'string' || !/^[0-9]+$/.test(r.correction_count) || r.last_correction_recorded_at !== null && !at(r.last_correction_recorded_at) || !Array.isArray(r.corrections)
      || (r.correction_count === '0') !== (r.corrections.length === 0) || typeof r.source_type !== 'string' || r.source_id !== null && !id(r.source_id) || !text(r.note)) return fail()
    let sum = 0
    for (const m of r.corrections as unknown[]) { const x = closed(m, ['movement_id', 'qty_signed', 'movement_type', 'recorded_at', 'physical_at', 'source_type', 'reversal_of_id', 'note']); if (!id(x.movement_id) || !decimal(x.qty_signed) || !at(x.recorded_at) || !at(x.physical_at)) return fail(); sum += Number(x.qty_signed) }
    if (r.corrections.length && Math.abs(sum - Number(r.qty_signed)) > 1e-6) return fail()
    seen.add(r.movement_id)
  }
  return w as unknown as MaterialCard
}

// "Benerin nama bahan": a typo in the name of the same material. Only the name
// changes; SKU, unit, type and every stock row keep their identity.
export type MaterialNameWorkspace = { contract_version: 'cp7.material-name-workspace.v1'; read_at: string; material_id: string; material_sku: string; material_name: string; material_type: string; unit_code: string; row_version: string
  history: { id: string; previous_name: string; corrected_name: string; previous_sku: string; corrected_sku: string; reason: string; recorded_at: string; actor_id: string; actor_display_name: string | null; actor_name_basis: 'CURRENT_PROFILE' }[]; production_go: false }
export function parseMaterialNameWorkspace(v: unknown, requested: string): MaterialNameWorkspace {
  const r = closed(v, ['contract_version', 'read_at', 'material_id', 'material_sku', 'material_name', 'material_type', 'unit_code', 'row_version', 'history', 'production_go'])
  if (r.contract_version !== 'cp7.material-name-workspace.v1' || !at(r.read_at) || r.material_id !== requested || !id(r.material_id) || typeof r.material_sku !== 'string' || typeof r.material_name !== 'string'
    || typeof r.material_type !== 'string' || typeof r.unit_code !== 'string' || typeof r.row_version !== 'string' || !/^[1-9][0-9]{0,18}$/.test(r.row_version) || !Array.isArray(r.history) || r.production_go !== false) return fail()
  for (const value of r.history) {
    const h = closed(value, ['id', 'previous_name', 'corrected_name', 'previous_sku', 'corrected_sku', 'reason', 'recorded_at', 'actor_id', 'actor_display_name', 'actor_name_basis'])
    if (!id(h.id) || typeof h.previous_name !== 'string' || typeof h.corrected_name !== 'string' || typeof h.previous_sku !== 'string' || typeof h.corrected_sku !== 'string' || typeof h.reason !== 'string' || !at(h.recorded_at) || !actor(h)) return fail()
  }
  return r as unknown as MaterialNameWorkspace
}
export function parseMaterialNameOutcome(v: unknown, request: string, material: string) {
  const r = closed(v, ['contract_version', 'kind', 'action', 'request_id', 'material_id', 'previous_name', 'material_name', 'previous_sku', 'material_sku', 'row_version'])
  if (r.contract_version !== 'cp7.material-name-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'RENAME' || r.request_id !== request || r.material_id !== material
    || typeof r.previous_name !== 'string' || typeof r.material_name !== 'string' || typeof r.previous_sku !== 'string' || typeof r.material_sku !== 'string' || typeof r.row_version !== 'string') return fail()
  return r as typeof r & { material_name: string; material_sku: string }
}
export function materialNamePayload(w: MaterialNameWorkspace, name: string, reason: string, sku: string = w.material_sku): { payload: Record<string, unknown> | null; problem: string | null } {
  const clean = name.trim().replace(/\s+/g, ' '), code = sku.trim()
  if (!clean || clean.length > 150) return { payload: null, problem: 'Tulis nama bahan yang benar (1–150 huruf).' }
  if (!code || code.length > 60) return { payload: null, problem: 'Tulis kode bahan yang benar (1–60 huruf).' }
  if (clean === w.material_name && code === w.material_sku) return { payload: null, problem: 'Nama dan kode belum berubah.' }
  if (reason.trim().length < 5) return { payload: null, problem: 'Tulis alasan pembetulan (minimal 5 huruf).' }
  return { payload: { material_id: w.material_id, material_name: clean, ...(code !== w.material_sku ? { material_sku: code } : {}), change_reason: reason.trim() }, problem: null }
}

