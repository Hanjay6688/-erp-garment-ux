// BB (ALL open cutover states): the continuations of a posted import that the workspace sends next to the batch.
// A server with BB sends every collection below; a server without BB sends none of them. One without the others is an
// incomplete read and is refused, never shown as "nothing open".

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak lengkap.`)
  return value as Record<string, unknown>
}
function list(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value
}
function id(value: unknown, label: string): string {
  if (typeof value !== 'string' || !uuid.test(value)) throw new Error(`${label}: identitas tidak valid.`)
  return value
}
function text(value: unknown, label: string, nullable = false): string {
  if (nullable && (value === null || value === undefined)) return ''
  if (typeof value !== 'string') throw new Error(`${label} tidak valid.`)
  return value
}
function money(value: unknown, label: string, signed = false): string {
  if (typeof value !== 'string' || !(signed ? /^-?\d{1,18}\.\d{2}$/ : /^\d{1,18}\.\d{2}$/).test(value)) throw new Error(`${label}: nominal tidak valid.`)
  return value
}
function quantity(value: unknown, label: string): string {
  if (typeof value !== 'string' || !/^\d{1,18}(\.\d{1,6})?$/.test(value)) throw new Error(`${label}: jumlah tidak valid.`)
  return value
}
function day(value: unknown, label: string, nullable = false): string {
  if (nullable && value === null) return ''
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error(`${label}: tanggal tidak valid.`)
  return value
}
function count(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error(`${label}: jumlah tidak valid.`)
  return value
}
function version(value: unknown, label: string): string {
  if (typeof value !== 'string' || !/^[1-9]\d{0,18}$/.test(value)) throw new Error(`${label}: versi tidak valid.`)
  return value
}
function oneOf<T extends string>(value: unknown, allowed: readonly T[], label: string): T {
  if (!allowed.includes(value as T)) throw new Error(`${label} tidak dikenal.`)
  return value as T
}

export type BbSettlement = { id: string; number: string; date: string; amount: string; status: 'DRAFT' | 'POSTED' | 'REVERSED';
  method: 'CASH' | 'CREDIT' | 'ADVANCE'; credit_kind: string; credit_note_number: string; reversible: boolean }
export type BbPayrollLine = { payroll_id: string; payroll_number: string; status: string; row_version: string; amount: string }
export type BbOpeningBalance = { balance_id: string; balance_type: string; party_type: string; party_id: string; party_code: string; party_name: string;
  document_number: string; document_date: string; due_date: string; cutover_date: string; original_amount: string; settled_before_cutover: string;
  opening_amount: string; settled_amount: string; reserved_amount: string; remaining_amount: string; available_amount: string;
  settlements: BbSettlement[]; payroll_lines: BbPayrollLine[] }
export type BbPayroll = { id: string; payroll_number: string; contractor_id: string; period_end: string; row_version: string }
export type BbCreditEvent = { id: string; kind: 'REFUND' | 'APPLY_OPENING_AR' | 'REVERSAL'; amount: string; date: string; reason: string; reversed: boolean }
export type BbCustomerCredit = { credit_id: string; origin: string; customer_id: string; customer_code: string; customer_name: string;
  document_number: string; amount: string; used_amount: string; remaining_amount: string; voided: boolean;
  open_receivables: { balance_id: string; document_number: string; remaining_amount: string }[]; events: BbCreditEvent[] }
export type BbReturnRight = { id: string; return_number: string; customer_code: string; invoice_document_number: string;
  invoice_state: 'OPEN' | 'SETTLED_BEFORE_CUTOVER'; product_sku: string; qty_pcs: number; received_pcs: number; credit_unit_price: string;
  receipts: { id: string; qty_pcs: number; date: string; status: string }[] }
export type BbLocation = { id: string; code: string; name: string }
export type BbCommitmentLine = { id: string; line_number: string; material_sku: string; ordered_qty: string; remaining_qty: string; unit_price: string }
export type BbCommitment = { id: string; po_number: string; supplier_name: string; lines: BbCommitmentLine[];
  drafts: { purchase_id: string; purchase_number: string; status: string }[] }
export type BbEntitlement = { id: string; kind: 'SEWING_WORK' | 'ATTENDANCE' | 'ACCESSORY_REIMBURSEMENT'; contractor_id: string; contractor_name: string;
  document_number: string; line_number: string; amount: string; rate: string; carry_qty: string; carry_remaining: string;
  carry_lines: { payroll_id: string; payroll_number: string; status: string; row_version: string; qty: string; amount: string }[] }
export type BbRework = { id: string; rework_order_id: string; rework_number: string; legacy_rework_number: string; legacy_sent_date: string;
  bs_number: string; destination_type: 'CONTRACTOR' | 'LAUNDRY'; holder_name: string; qty_sent_original: number;
  qty_returned_before_cutover: number; qty_open: number; status: string; qty_good_returned: number; qty_bs_returned: number }
export type BbSalesDraft = { sale_id: string; draft_number: string; draft_date: string; customer_code: string; customer_name: string;
  status: 'DRAFT' | 'POSTED' | 'CANCELLED'; sale_date: string; reserved_qty_pcs: number;
  lines: { line_number: string; product_sku: string; qty_pcs: number; unit_price: string }[] }
export type InitialImportBB = { opening_balances: BbOpeningBalance[]; opening_payable_payrolls: BbPayroll[]; legacy_documents: number;
  customer_credits: BbCustomerCredit[]; sale_return_rights: BbReturnRight[]; fg_locations: BbLocation[]; purchase_commitments: BbCommitment[];
  payroll_entitlements: BbEntitlement[]; entitlement_payrolls: BbPayroll[]; opening_reworks: BbRework[]; open_sales_drafts: BbSalesDraft[] }

const KEYS = ['opening_balances', 'opening_payable_payrolls', 'legacy_documents', 'customer_credits', 'sale_return_rights', 'fg_locations',
  'purchase_commitments', 'payroll_entitlements', 'entitlement_payrolls', 'opening_reworks', 'open_sales_drafts'] as const

function payroll(value: unknown): BbPayroll {
  const p = object(value, 'Payroll')
  return { id:id(p.id, 'Payroll'), payroll_number:text(p.payroll_number, 'Nomor payroll'), contractor_id:id(p.contractor_id, 'Mandor payroll'),
    period_end:day(p.period_end, 'Periode payroll'), row_version:version(p.row_version, 'Payroll') }
}

export function parseInitialImportBB(batch: Record<string, unknown>): InitialImportBB | null {
  const present = KEYS.filter(key => batch[key] !== undefined)
  if (!present.length) return null
  if (present.length !== KEYS.length) throw new Error('Lanjutan saldo awal tidak terbaca lengkap.')
  const opening_balances = list(batch.opening_balances, 'Saldo awal dokumen').map((value): BbOpeningBalance => {
    const b = object(value, 'Saldo awal dokumen')
    const settlements = list(b.settlements, 'Pelunasan saldo awal').map((item): BbSettlement => {
      const s = object(item, 'Pelunasan')
      if (typeof s.reversible !== 'boolean') throw new Error('Pelunasan tidak valid.')
      return { id:id(s.id, 'Pelunasan'), number:text(s.number, 'Nomor pelunasan'), date:day(s.date, 'Tanggal pelunasan'), amount:money(s.amount, 'Pelunasan'),
        status:oneOf(s.status, ['DRAFT', 'POSTED', 'REVERSED'] as const, 'Status pelunasan'), method:oneOf(s.method, ['CASH', 'CREDIT', 'ADVANCE'] as const, 'Cara pelunasan'),
        credit_kind:text(s.credit_kind, 'Jenis kredit', true), credit_note_number:text(s.credit_note_number, 'Nomor nota', true), reversible:s.reversible }
    })
    const payroll_lines = list(b.payroll_lines, 'Payroll saldo awal').map((item): BbPayrollLine => {
      const p = object(item, 'Payroll saldo awal')
      return { payroll_id:id(p.payroll_id, 'Payroll'), payroll_number:text(p.payroll_number, 'Nomor payroll'), status:text(p.status, 'Status payroll'),
        row_version:version(p.row_version, 'Payroll'), amount:money(p.amount, 'Payroll saldo awal') }
    })
    return { balance_id:id(b.balance_id, 'Saldo awal'), balance_type:text(b.balance_type, 'Jenis saldo'), party_type:text(b.party_type, 'Jenis pihak'),
      party_id:id(b.party_id, 'Pihak'), party_code:text(b.party_code, 'Kode pihak'), party_name:text(b.party_name, 'Nama pihak'),
      document_number:text(b.document_number, 'Nomor dokumen', true), document_date:day(b.document_date, 'Tanggal dokumen', true), due_date:day(b.due_date, 'Jatuh tempo', true),
      cutover_date:day(b.cutover_date, 'Tanggal saldo awal'), original_amount:money(b.original_amount, 'Nominal asal'),
      settled_before_cutover:money(b.settled_before_cutover, 'Dibayar sebelum saldo awal'), opening_amount:money(b.opening_amount, 'Saldo awal'),
      settled_amount:money(b.settled_amount, 'Dilunasi'), reserved_amount:money(b.reserved_amount, 'Dijanjikan payroll'),
      remaining_amount:money(b.remaining_amount, 'Sisa'), available_amount:money(b.available_amount, 'Tersedia'), settlements, payroll_lines }
  })
  const customer_credits = list(batch.customer_credits, 'Kredit pelanggan').map((value): BbCustomerCredit => {
    const c = object(value, 'Kredit pelanggan')
    if (typeof c.voided !== 'boolean') throw new Error('Kredit pelanggan tidak valid.')
    return { credit_id:id(c.credit_id, 'Kredit pelanggan'), origin:text(c.origin, 'Asal kredit'), customer_id:id(c.customer_id, 'Pelanggan'),
      customer_code:text(c.customer_code, 'Kode pelanggan'), customer_name:text(c.customer_name, 'Nama pelanggan'), document_number:text(c.document_number, 'Nomor kredit'),
      amount:money(c.amount, 'Kredit'), used_amount:money(c.used_amount, 'Kredit terpakai'), remaining_amount:money(c.remaining_amount, 'Sisa kredit'), voided:c.voided,
      open_receivables:list(c.open_receivables, 'Piutang terbuka').map(item => { const r = object(item, 'Piutang terbuka')
        return { balance_id:id(r.balance_id, 'Piutang'), document_number:text(r.document_number, 'Nomor piutang'), remaining_amount:money(r.remaining_amount, 'Sisa piutang') } }),
      events:list(c.events, 'Riwayat kredit').map((item): BbCreditEvent => { const e = object(item, 'Riwayat kredit')
        if (typeof e.reversed !== 'boolean') throw new Error('Riwayat kredit tidak valid.')
        return { id:id(e.id, 'Riwayat kredit'), kind:oneOf(e.kind, ['REFUND', 'APPLY_OPENING_AR', 'REVERSAL'] as const, 'Jenis riwayat kredit'),
          amount:money(e.amount, 'Riwayat kredit'), date:day(e.date, 'Tanggal kredit'), reason:text(e.reason, 'Alasan kredit'), reversed:e.reversed } }) }
  })
  const sale_return_rights = list(batch.sale_return_rights, 'Hak retur').map((value): BbReturnRight => {
    const r = object(value, 'Hak retur')
    return { id:id(r.id, 'Hak retur'), return_number:text(r.return_number, 'Nomor retur'), customer_code:text(r.customer_code, 'Kode pelanggan'),
      invoice_document_number:text(r.invoice_document_number, 'Nomor invoice'), invoice_state:oneOf(r.invoice_state, ['OPEN', 'SETTLED_BEFORE_CUTOVER'] as const, 'Status invoice'),
      product_sku:text(r.product_sku, 'Produk retur'), qty_pcs:count(r.qty_pcs, 'Retur'), received_pcs:count(r.received_pcs, 'Retur diterima'),
      credit_unit_price:money(r.credit_unit_price, 'Harga kredit'),
      receipts:list(r.receipts, 'Penerimaan retur').map(item => { const x = object(item, 'Penerimaan retur')
        return { id:id(x.id, 'Penerimaan retur'), qty_pcs:count(x.qty_pcs, 'Penerimaan retur'), date:day(x.date, 'Tanggal retur'), status:text(x.status, 'Status retur') } }) }
  })
  const fg_locations = list(batch.fg_locations, 'Gudang barang jadi').map((value): BbLocation => {
    const l = object(value, 'Gudang')
    return { id:id(l.id, 'Gudang'), code:text(l.code, 'Kode gudang'), name:text(l.name, 'Nama gudang') }
  })
  const purchase_commitments = list(batch.purchase_commitments, 'PO pembelian terbuka').map((value): BbCommitment => {
    const c = object(value, 'PO pembelian')
    return { id:id(c.id, 'PO pembelian'), po_number:text(c.po_number, 'Nomor PO'), supplier_name:text(c.supplier_name, 'Supplier'),
      lines:list(c.lines, 'Baris PO').map(item => { const l = object(item, 'Baris PO')
        return { id:id(l.id, 'Baris PO'), line_number:text(l.line_number, 'Nomor baris'), material_sku:text(l.material_sku, 'Bahan'),
          ordered_qty:quantity(l.ordered_qty, 'Dipesan'), remaining_qty:quantity(l.remaining_qty, 'Sisa PO'), unit_price:quantity(l.unit_price, 'Harga') } }),
      drafts:list(c.drafts ?? [], 'Draft penerimaan').map(item => { const d = object(item, 'Draft penerimaan')
        return { purchase_id:id(d.purchase_id, 'Draft penerimaan'), purchase_number:text(d.purchase_number, 'Nomor penerimaan'), status:text(d.status, 'Status penerimaan') } }) }
  })
  const payroll_entitlements = list(batch.payroll_entitlements, 'Hak upah').map((value): BbEntitlement => {
    const e = object(value, 'Hak upah')
    return { id:id(e.id, 'Hak upah'), kind:oneOf(e.kind, ['SEWING_WORK', 'ATTENDANCE', 'ACCESSORY_REIMBURSEMENT'] as const, 'Jenis hak upah'),
      contractor_id:id(e.contractor_id, 'Mandor'), contractor_name:text(e.contractor_name, 'Nama mandor'), document_number:text(e.document_number, 'Dokumen hak upah'),
      line_number:text(e.line_number, 'Baris hak upah'), amount:money(e.amount, 'Hak upah'), rate:money(e.rate, 'Tarif'),
      carry_qty:quantity(e.carry_qty, 'Carry'), carry_remaining:quantity(e.carry_remaining, 'Sisa carry'),
      carry_lines:list(e.carry_lines, 'Payroll carry').map(item => { const l = object(item, 'Payroll carry')
        return { payroll_id:id(l.payroll_id, 'Payroll'), payroll_number:text(l.payroll_number, 'Nomor payroll'), status:text(l.status, 'Status payroll'),
          row_version:version(l.row_version, 'Payroll'), qty:quantity(l.qty, 'Carry payroll'), amount:money(l.amount, 'Carry payroll') } }) }
  })
  const opening_reworks = list(batch.opening_reworks, 'Rework terbuka').map((value): BbRework => {
    const r = object(value, 'Rework terbuka')
    return { id:id(r.id, 'Rework terbuka'), rework_order_id:id(r.rework_order_id, 'Order rework'), rework_number:text(r.rework_number, 'Nomor rework'),
      legacy_rework_number:text(r.legacy_rework_number, 'Nomor rework asal'), legacy_sent_date:day(r.legacy_sent_date, 'Tanggal kirim'),
      bs_number:text(r.bs_number, 'Nomor BS'), destination_type:oneOf(r.destination_type, ['CONTRACTOR', 'LAUNDRY'] as const, 'Tujuan rework'),
      holder_name:text(r.holder_name, 'Pemegang rework'), qty_sent_original:count(r.qty_sent_original, 'Dikirim'),
      qty_returned_before_cutover:count(r.qty_returned_before_cutover, 'Kembali sebelum saldo awal'), qty_open:count(r.qty_open, 'Sisa rework'),
      status:text(r.status, 'Status rework'), qty_good_returned:count(r.qty_good_returned, 'Kembali baik'), qty_bs_returned:count(r.qty_bs_returned, 'Kembali BS') }
  })
  const open_sales_drafts = list(batch.open_sales_drafts, 'Draf penjualan terbuka').map((value): BbSalesDraft => {
    const d = object(value, 'Draf penjualan terbuka')
    return { sale_id:id(d.sale_id, 'Draf penjualan'), draft_number:text(d.draft_number, 'Nomor draf'), draft_date:day(d.draft_date, 'Tanggal draf lama'),
      customer_code:text(d.customer_code, 'Kode pelanggan'), customer_name:text(d.customer_name, 'Nama pelanggan'),
      status:oneOf(d.status, ['DRAFT', 'POSTED', 'CANCELLED'] as const, 'Status draf penjualan'), sale_date:day(d.sale_date, 'Tanggal invoice draf'),
      reserved_qty_pcs:count(d.reserved_qty_pcs, 'Pcs direservasi'),
      lines:list(d.lines, 'Baris draf').map(item => { const l = object(item, 'Baris draf')
        return { line_number:text(l.line_number, 'Baris draf'), product_sku:text(l.product_sku, 'Kode produk'), qty_pcs:count(l.qty_pcs, 'Pcs draf'),
          unit_price:money(l.unit_price, 'Harga draf') } }) }
  })
  return { opening_balances, opening_payable_payrolls:list(batch.opening_payable_payrolls, 'Payroll mandor').map(payroll),
    legacy_documents:list(batch.legacy_documents, 'Dokumen lama').length, customer_credits, sale_return_rights, fg_locations, purchase_commitments,
    payroll_entitlements, entitlement_payrolls:list(batch.entitlement_payrolls, 'Payroll hak upah').map(payroll), opening_reworks, open_sales_drafts }
}
