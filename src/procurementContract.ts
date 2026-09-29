import type { Json } from './types/database.preconnect'

export type ProcurementOption = { id: string; code: string; name: string; material_type?: string; unit_code?: string }
export type OptionKind = 'MATERIAL' | 'SUPPLIER' | 'LOCATION'
export type ProcurementOptions = { contract_version: 'cp7.procurement-options.v1'; kind: OptionKind; rows: ProcurementOption[]; total: string; offset: number; limit: number; next_offset: number | null }
type ReceiptFinance = { supplier_invoice_number: string | null; due_date: string | null; payment_status: string; receipt_value: string; basis: 'RECEIPT_PRICE_NOT_CURRENT_PAYABLE' }
export type ReceiptRow = { id: string; purchase_number: string; supplier_id: string | null; supplier_name: string | null; location_id: string | null; location_name: string | null; physical_at: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; row_version: string; notes: string | null; line_count: number; finance?: ReceiptFinance }
export type ReceiptItem = { id: string; material_id: string; material_sku: string; material_name: string; material_type: string; unit_code: string; qty: string; purchase_qty_entered: string | null; purchase_uom_code: string | null; purchase_uom_factor: string | null; lot_number: string | null; notes: string | null; rolls: { id: string; roll_number: string; receipt_qty: string; notes: string | null }[]; finance?: { unit_price: string; line_total: string; price_state: 'ESTIMATED' | 'FINAL'; price_source: string; invoice_match_state: string; benchmark_price_version_id: string | null } }
export type ReceiptDetail = ReceiptRow & { items: ReceiptItem[]; stock_effect: 'NOT_POSTED' | 'POSTED_RECEIPT' | 'REVERSED_RECEIPT'; quantity_basis: 'RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND' }
export type ProcurementWorkspace = { contract_version: 'cp7.procurement-workspace.v1'; kind: 'LIVE_WORKSPACE'; read_at: string; capabilities: { create: boolean; post: boolean; view_value: boolean }; page: { rows: ReceiptRow[]; total: string; offset: number; limit: number; next_offset: number | null }; detail: ReceiptDetail | null }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const decimal = /^(0|[1-9][0-9]{0,23})(\.[0-9]{1,6})?$/
const integer = /^(0|[1-9][0-9]{0,18})$/
const version = /^[1-9][0-9]{0,18}$/
const isString = (v: unknown): v is string => typeof v === 'string'
const nullableText = (v: unknown) => v === null || isString(v)
const isId = (v: unknown): v is string => isString(v) && uuid.test(v)
const nullableId = (v: unknown) => v === null || isId(v)
const exact = (v: unknown) => isString(v) && decimal.test(v)
const isWhole = (v: unknown): v is string => isString(v) && integer.test(v)
const instant = (v: unknown) => isString(v) && Number.isFinite(Date.parse(v))
const fail = (): never => { throw new Error('Data penerimaan tidak lengkap atau tidak cocok dengan hak akses. Muat ulang sebelum melanjutkan.') }
export function procurementObject(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v)) return fail(); return v as Record<string, unknown> }
function closed(v: unknown, required: string[], optional: string[] = []) {
  const r = procurementObject(v)
  if (required.some(k => !(k in r)) || Object.keys(r).some(k => !required.includes(k) && !optional.includes(k))) fail()
  return r
}
function page(v: Record<string, unknown>, rows: unknown[]) {
  if (!isWhole(v.total) || !Number.isSafeInteger(v.offset) || Number(v.offset) < 0 || !Number.isSafeInteger(v.limit) || Number(v.limit) < 1 || Number(v.limit) > 100 || rows.length > Number(v.limit)) fail()
  const end = BigInt(Number(v.offset)) + BigInt(rows.length), total = BigInt(v.total as string)
  if (rows.length > 0 && end > total || v.next_offset !== null && (!Number.isSafeInteger(v.next_offset) || v.next_offset !== Number(v.offset) + rows.length || end >= total || !rows.length)) fail()
  if (end < total && v.next_offset === null) fail()
}
const rowFields = ['id','purchase_number','supplier_id','supplier_name','location_id','location_name','physical_at','status','row_version','notes','line_count']
function row(v: unknown, allowValue: boolean, detail = false) {
  const r = closed(v, [...rowFields, ...(detail ? ['items','stock_effect','quantity_basis'] : [])], allowValue ? ['finance'] : [])
  if (!isId(r.id) || !isString(r.purchase_number) || !nullableId(r.supplier_id) || !nullableId(r.location_id) || !nullableText(r.supplier_name) || !nullableText(r.location_name) || !nullableText(r.notes) || !instant(r.physical_at) || !['DRAFT','POSTED','REVERSED'].includes(String(r.status)) || !isString(r.row_version) || !version.test(r.row_version) || !Number.isSafeInteger(r.line_count) || Number(r.line_count) < 0) fail()
  if (allowValue) {
    const f = closed(r.finance, ['supplier_invoice_number','due_date','payment_status','receipt_value','basis'])
    if (!nullableText(f.supplier_invoice_number) || !nullableText(f.due_date) || !isString(f.payment_status) || !exact(f.receipt_value) || f.basis !== 'RECEIPT_PRICE_NOT_CURRENT_PAYABLE') fail()
  }
  return r
}
export function parseProcurementWorkspace(v: unknown, allowValue: boolean): ProcurementWorkspace {
  const w = closed(v,['contract_version','kind','read_at','capabilities','page','detail'])
  const c = closed(w.capabilities,['create','post','view_value'])
  if (w.contract_version !== 'cp7.procurement-workspace.v1' || w.kind !== 'LIVE_WORKSPACE' || !instant(w.read_at) || Object.values(c).some(v => typeof v !== 'boolean') || c.view_value !== allowValue) fail()
  const p = closed(w.page,['rows','total','offset','limit','next_offset']); if (!Array.isArray(p.rows)) return fail()
  page(p,p.rows); const ids = p.rows.map(r => row(r,allowValue).id); if (new Set(ids).size !== ids.length) fail()
  if (w.detail !== null) {
    const d = row(w.detail,allowValue,true)
    if (!Array.isArray(d.items) || d.items.length !== d.line_count || d.items.length > 100 || d.quantity_basis !== 'RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND' || d.stock_effect !== ({ DRAFT:'NOT_POSTED',POSTED:'POSTED_RECEIPT',REVERSED:'REVERSED_RECEIPT' } as Record<string,string>)[String(d.status)]) return fail()
    const itemIds = new Set(), rollIds = new Set()
    for (const value of d.items) {
      const i = closed(value,['id','material_id','material_sku','material_name','material_type','unit_code','qty','purchase_qty_entered','purchase_uom_code','purchase_uom_factor','lot_number','notes','rolls'],allowValue ? ['finance'] : [])
      if (!isId(i.id) || itemIds.has(i.id) || !isId(i.material_id) || ![i.material_sku,i.material_name,i.material_type,i.unit_code].every(isString) || !exact(i.qty) || !nullableText(i.lot_number) || !nullableText(i.notes) || !Array.isArray(i.rolls)) return fail()
      itemIds.add(i.id)
      if (!nullableText(i.purchase_uom_code) || i.purchase_qty_entered !== null && !exact(i.purchase_qty_entered) || i.purchase_uom_factor !== null && !exact(i.purchase_uom_factor)) fail()
      for (const value of i.rolls) {
        const r = closed(value,['id','roll_number','receipt_qty','notes'])
        if (!isId(r.id) || rollIds.has(r.id) || !isString(r.roll_number) || !exact(r.receipt_qty) || !nullableText(r.notes)) fail()
        rollIds.add(r.id)
      }
      if (allowValue) {
        const f = closed(i.finance,['unit_price','line_total','price_state','price_source','invoice_match_state','benchmark_price_version_id'])
        if (!exact(f.unit_price) || !exact(f.line_total) || !['ESTIMATED','FINAL'].includes(String(f.price_state)) || !isString(f.price_source) || !isString(f.invoice_match_state) || !nullableId(f.benchmark_price_version_id)) fail()
      }
    }
    if (rollIds.size > 2000) fail()
  }
  return w as unknown as ProcurementWorkspace
}
export function parseProcurementOptions(v: unknown, kind: OptionKind): ProcurementOptions {
  const p = closed(v,['contract_version','kind','rows','total','offset','limit','next_offset'])
  if (p.contract_version !== 'cp7.procurement-options.v1' || p.kind !== kind || !Array.isArray(p.rows)) return fail()
  page(p,p.rows); const ids = new Set()
  for (const value of p.rows) {
    const r = closed(value,['id','code','name',...(kind === 'MATERIAL' ? ['material_type','unit_code'] : [])])
    if (!isId(r.id) || ids.has(r.id) || !isString(r.code) || !isString(r.name) || kind === 'MATERIAL' && (!isString(r.material_type) || !isString(r.unit_code))) fail()
    ids.add(r.id)
  }
  return p as unknown as ProcurementOptions
}
export function parseProcurementOutcome(v: unknown, request: string, action: string, document: Json) {
  const r = closed(v,['contract_version','kind','action','request_id','purchase_id','status','row_version']), p = procurementObject(document)
  if (r.contract_version !== 'cp7.procurement-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== action || r.request_id !== request || !isId(r.purchase_id) || !isString(r.row_version) || !version.test(r.row_version) || r.status !== (action === 'SAVE_DRAFT' ? 'DRAFT' : 'POSTED') || action === 'POST' && r.purchase_id !== p.purchase_id || action === 'SAVE_DRAFT' && p.id && r.purchase_id !== p.id) fail()
  return r as { purchase_id: string; row_version: string; status: 'DRAFT' | 'POSTED' }
}
export function receiptDecimal(raw: string, positive = false) {
  const v = raw.trim().replace(',', '.')
  return /^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$/.test(v) && (!positive || /[1-9]/.test(v)) ? v : null
}
export function formatReceiptDecimal(v: string) {
  const [whole, fraction = ''] = v.split('.')
  const f = fraction.replace(/0+$/, '')
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (f ? ',' + f : '')
}
export function receiptEditableInBaseUnits(d: ReceiptDetail) {
  return d.items.every(i => i.finance && ['BENCHMARK','MANUAL_ESTIMATE','SUPPLIER_QUOTE','SUPPLIER_INVOICE'].includes(i.finance.price_source)
    && (i.purchase_uom_code === null || i.purchase_uom_code === i.unit_code)
    && (i.purchase_uom_factor === null || /^1(?:\.0+)?$/.test(i.purchase_uom_factor)))
}
