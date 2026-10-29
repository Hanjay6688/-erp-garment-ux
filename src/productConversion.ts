import type { Json } from './types/database.preconnect'
import { cp6WibPhysicalTimeToIso } from './cp6BusinessTime'
export const conversionActions = ['POST', 'REVERSE', 'POST_USAGE', 'SAVE_REWORK', 'SAVE_REDYE', 'SET_REDYE_PRICE'] as const
export type ConversionAction = typeof conversionActions[number]
const exactQuantity = (v: unknown): string => { if (typeof v !== 'string' || !/^\d{1,12}\.\d{6}$/.test(v)) throw new Error('Jumlah bongkaran tidak valid.'); return v }
export type ConversionLot = { id: string; lot_number: string; product_id: string; sku: string; product_name: string; location_id: string; location_name: string; qty: number; source_revision: string; unit_hpp: string | null }
export type ConversionStock = { available: number; reserved: number; physical: number }
export type ConversionSource = { product_id: string; sku: string; product_name: string; brand_name: string; size: string; location_id: string; location_name: string; stock: ConversionStock }
export type ConversionTarget = { id: string; sku: string; product_name: string; brand_name?: string; size?: string; recommended?: boolean }
export type ConversionSelection = { source_product_id: string; target_product_id: string | null; location_id: string; source_stock: ConversionStock; target_stock: ConversionStock | null }
export type AutoConversionPreview = { source_product_id: string; target_product_id: string; location_id: string; location_name: string; source_sku: string; target_sku: string; physical_at: string; qty_pcs: number; source_revision: string; source_stock: ConversionStock; target_stock: ConversionStock; source_after: ConversionStock; target_after: ConversionStock; cost: { source_value?: string }; allocations: { source_lot_id: string; qty_pcs: number; source_revision: string; source_value: string | null; lot_number: string }[] }
export type ConversionDocument = { id: string; conversion_number: string; status: string; source_sku: string; target_sku: string; qty_pcs: number; physical_at: string; notes: string; origin_kind: string; revision: string; target_value: string | null; extra_cost: string | null; pending_returns: number; value_state: 'PROVISIONAL_RECOVERY' | 'SOURCED_TO_DATE'; returns: { id: string; material: string; holder: string; expected: string; received: string; unreturned: string; awaiting_value: string }[]; group_id?: string; group_qty_pcs?: number; group_part_count?: number; group_line_no?: number }
export type ConversionWorkspace = { lots: ConversionLot[]; targets: ConversionTarget[]; documents: ConversionDocument[]; total: number; page: number; page_size: number; targets_total: number; target_page: number; documents_total: number; document_page: number; contract_version?: string; sources?: ConversionSource[]; sources_total?: number; selection?: ConversionSelection }
export function conversionObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Data konversi tidak lengkap.')
  return value as Record<string, unknown>
}
const text = (v: unknown): string => { if (typeof v !== 'string' || !v.trim()) throw new Error('Teks konversi tidak lengkap.'); return v }
const id = (v: unknown): string => { const s = text(v); if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(s)) throw new Error('ID konversi tidak valid.'); return s }
const count = (v: unknown): number => { if (typeof v !== 'number' || !Number.isSafeInteger(v) || v < 0) throw new Error('Jumlah konversi tidak valid.'); return v }
const amount = (v: unknown): string | null => { if (v === null) return null; const s = text(v); if (!/^-?\d+(\.\d+)?$/.test(s)) throw new Error('Nilai konversi tidak valid.'); return s }
function rows<T>(v: unknown, parse: (o: Record<string, unknown>) => T): T[] {
  if (!Array.isArray(v)) throw new Error('Daftar konversi tidak lengkap.')
  const parsed = v.map(x => parse(conversionObject(x))); const ids = parsed.map(x => (x as { id: string }).id)
  // Stock can span locations, so its composite uniqueness is checked below.
  if (new Set(ids).size !== ids.length && v.some(x => !conversionObject(x).location_id)) throw new Error('ID dokumen ganda.')
  return parsed
}
export function parseConversionStock(value: unknown): ConversionStock {
  const s = conversionObject(value), stock = { available: count(s.available), reserved: count(s.reserved), physical: count(s.physical) }
  if (stock.available + stock.reserved !== stock.physical) throw new Error('Stok fisik dan reservasi tidak cocok.')
  return stock
}
export function parseConversionWorkspace(value: unknown): ConversionWorkspace {
  const o = conversionObject(value)
  const lots = rows(o.lots, x => ({ id: id(x.id), product_id: id(x.product_id), lot_number: text(x.lot_number), sku: text(x.sku), product_name: text(x.product_name), location_id: id(x.location_id), location_name: text(x.location_name), qty: count(x.qty), source_revision: text(x.source_revision), unit_hpp: amount(x.unit_hpp) }))
  if (new Set(lots.map(l => l.id + l.location_id)).size !== lots.length) throw new Error('Lot dan lokasi ganda.')
  const workspace: ConversionWorkspace = { lots, targets: rows(o.targets, x => ({ id: id(x.id), sku: text(x.sku), product_name: text(x.product_name), ...(x.recommended === undefined ? {} : { recommended: typeof x.recommended === 'boolean' ? x.recommended : (() => { throw new Error('Rekomendasi SKU tidak valid.') })(), brand_name: text(x.brand_name), size: text(x.size) }) })),
    documents: rows(o.documents, x => { const status = text(x.status); if (!['POSTED', 'REVERSED'].includes(status)) throw new Error('Status konversi tidak valid.')
      return { id: id(x.id), conversion_number: text(x.conversion_number), status, source_sku: text(x.source_sku), target_sku: text(x.target_sku), qty_pcs: count(x.qty_pcs), physical_at: text(x.physical_at), notes: text(x.notes), origin_kind: text(x.origin_kind), revision: text(x.revision), target_value: amount(x.target_value), extra_cost: amount(x.extra_cost), pending_returns: count(x.pending_returns), value_state: x.value_state === 'PROVISIONAL_RECOVERY' || x.value_state === 'SOURCED_TO_DATE' ? x.value_state : (() => { throw new Error('Status nilai konversi tidak lengkap.') })(),
        returns: rows(x.returns, r => { return { id:id(r.id),material:text(r.material),holder:text(r.holder),expected:exactQuantity(r.expected),received:exactQuantity(r.received),unreturned:exactQuantity(r.unreturned),awaiting_value:exactQuantity(r.awaiting_value) } }),
        ...(x.group_id === undefined ? {} : { group_id: id(x.group_id), group_qty_pcs: count(x.group_qty_pcs), group_part_count: count(x.group_part_count), group_line_no: count(x.group_line_no) }) } }),
    total: count(o.total), page: count(o.page), page_size: count(o.page_size), targets_total: count(o.targets_total), target_page: count(o.target_page), documents_total: count(o.documents_total), document_page: count(o.document_page) }
  if (o.contract_version !== undefined) {
    if (o.contract_version !== 'cp7.sku-conversion.v1' || !Array.isArray(o.sources)) throw new Error('Pembaca stok konversi belum sesuai.')
    workspace.contract_version = o.contract_version
    workspace.sources = o.sources.map(value => { const s = conversionObject(value); return { product_id: id(s.product_id), sku: text(s.sku), product_name: text(s.product_name), brand_name: text(s.brand_name), size: text(s.size), location_id: id(s.location_id), location_name: text(s.location_name), stock: parseConversionStock(s.stock) } })
    if (new Set(workspace.sources.map(s => `${s.product_id}:${s.location_id}`)).size !== workspace.sources.length) throw new Error('Stok SKU dan lokasi ganda.')
    workspace.sources_total = count(o.sources_total)
    if (o.selection !== undefined) { const s = conversionObject(o.selection); workspace.selection = { source_product_id: id(s.source_product_id), location_id: id(s.location_id), target_product_id: s.target_product_id === null ? null : id(s.target_product_id), source_stock: parseConversionStock(s.source_stock), target_stock: s.target_stock === null ? null : parseConversionStock(s.target_stock) } }
  }
  return workspace
}
export function autoConversionPayload(source: ConversionSource | undefined, target: string, quantity: string, at: string, reason: string): Record<string, Json> {
  const time = cp6WibPhysicalTimeToIso(at)
  if (!source || !target || source.product_id === target || !/^[1-9]\d{0,8}$/.test(quantity) || Number(quantity) > source.stock.available || !time || !reason.trim()) throw new Error('Lengkapi SKU asal dan tujuan berbeda, jumlah sesuai stok tersedia, waktu WIB dan alasan.')
  return { source_product_id: source.product_id, target_product_id: target, location_id: source.location_id, qty_pcs: Number(quantity), physical_at: time, reason: reason.trim() }
}
export function parseAutoConversionPreview(value: unknown, payload: Record<string, Json>): AutoConversionPreview {
  const p = conversionObject(value)
  if (p.source_product_id !== payload.source_product_id || p.target_product_id !== payload.target_product_id || p.location_id !== payload.location_id || p.qty_pcs !== payload.qty_pcs || !Number.isFinite(Date.parse(text(p.physical_at))) || Date.parse(text(p.physical_at)) !== Date.parse(String(payload.physical_at))) throw new Error('Pratinjau SKU/lokasi/jumlah tidak cocok.')
  const sourceStock = parseConversionStock(p.source_stock), targetStock = parseConversionStock(p.target_stock), sourceAfter = parseConversionStock(p.source_after), targetAfter = parseConversionStock(p.target_after), quantity = count(p.qty_pcs)
  if (sourceStock.available - quantity !== sourceAfter.available || sourceStock.physical - quantity !== sourceAfter.physical || sourceStock.reserved !== sourceAfter.reserved
    || targetStock.available + quantity !== targetAfter.available || targetStock.physical + quantity !== targetAfter.physical || targetStock.reserved !== targetAfter.reserved) throw new Error('Pratinjau mutasi dan reservasi tidak seimbang.')
  const allocations = rows(p.allocations, a => ({ id: id(a.source_lot_id), source_lot_id: id(a.source_lot_id), qty_pcs: count(a.qty_pcs), source_revision: text(a.source_revision), source_value: amount(a.source_value), lot_number: text(a.lot_number) }))
  if (!allocations.length || allocations.some(a => a.qty_pcs < 1) || allocations.reduce((n, a) => n + a.qty_pcs, 0) !== quantity) throw new Error('Alokasi sumber tidak sama dengan jumlah konversi.')
  const cost = conversionObject(p.cost); if (cost.source_value !== undefined) amount(cost.source_value)
  return { source_product_id: id(p.source_product_id), target_product_id: id(p.target_product_id), location_id: id(p.location_id), location_name: text(p.location_name), source_sku: text(p.source_sku), target_sku: text(p.target_sku), physical_at: text(p.physical_at), qty_pcs: quantity, source_revision: text(p.source_revision), source_stock: sourceStock, target_stock: targetStock, source_after: sourceAfter, target_after: targetAfter, allocations, cost: cost as { source_value?: string } }
}
export function conversionPayload(lot: ConversionLot | undefined, target: string, quantity: string, at: string, reason: string): Record<string, Json> {
  const time = cp6WibPhysicalTimeToIso(at)
  if (!lot || !target || !/^[1-9]\d{0,8}$/.test(quantity) || Number(quantity) > lot.qty || !time || !reason.trim()) throw new Error('Lengkapi lot, SKU tujuan, jumlah sesuai stok, waktu WIB dan alasan.')
  return { source_lot_id: lot.id, target_product_id: target, location_id: lot.location_id, qty_pcs: Number(quantity), physical_at: time, reason: reason.trim(), expected_version: lot.source_revision }
}
export function validateConversionResult(value: unknown, action: string, request: string, payload: Json) {
  const r = conversionObject(value), p = conversionObject(payload)
  if (r.request_id !== request || r.action !== action) throw new Error('Respons konversi tidak cocok; pulihkan request yang sama.')
  if (action === 'POST' && (r.conversion_id !== request || r.status !== 'POSTED')) throw new Error('Identitas konversi tidak cocok.')
  if (action === 'POST') id(r.destination_lot_id)
  if (action === 'POST' && p.source_product_id !== undefined) {
    if (r.source_product_id !== p.source_product_id || r.target_product_id !== p.target_product_id || r.location_id !== p.location_id || r.qty_pcs !== p.qty_pcs
      || !Array.isArray(r.conversion_ids) || !Array.isArray(r.destination_lot_ids) || !r.conversion_ids.length || r.conversion_ids[0] !== request || r.conversion_ids.length !== r.destination_lot_ids.length) throw new Error('Alokasi hasil konversi tidak cocok.')
    for (const value of [...r.conversion_ids, ...r.destination_lot_ids]) id(value)
    if (new Set(r.conversion_ids).size !== r.conversion_ids.length || new Set(r.destination_lot_ids).size !== r.destination_lot_ids.length) throw new Error('Alokasi hasil konversi ganda.')
  }
  if (action === 'REVERSE' && (r.conversion_id !== p.conversion_id || r.status !== 'REVERSED')) throw new Error('Pembatalan tidak cocok.')
  if (action === 'POST_USAGE') { id(r.cost_document_id); if (r.conversion_id !== p.conversion_id) throw new Error('Sumber biaya tidak cocok.') }
  if (action === 'SAVE_REWORK' || action === 'SAVE_REDYE') { id(r.rework_id); if (r.target_product_id !== p.target_product_id) throw new Error('Target rework tidak cocok.') }
  if (action === 'SET_REDYE_PRICE' && (r.service_id !== p.service_id || r.price_status !== 'KNOWN')) throw new Error('Sumber harga tidak cocok.')
}
