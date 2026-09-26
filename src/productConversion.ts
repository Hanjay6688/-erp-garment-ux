import type { Json } from './types/database.preconnect'
import { cp6WibPhysicalTimeToIso } from './cp6BusinessTime'
export const conversionActions = ['POST', 'REVERSE', 'POST_USAGE', 'SAVE_REWORK', 'SAVE_REDYE', 'SET_REDYE_PRICE'] as const
export type ConversionAction = typeof conversionActions[number]
export type ConversionLot = { id: string; lot_number: string; product_id: string; sku: string; product_name: string; location_id: string; location_name: string; qty: number; source_revision: string; unit_hpp: string | null }
export type ConversionTarget = { id: string; sku: string; product_name: string }
export type ConversionDocument = { id: string; conversion_number: string; status: string; source_sku: string; target_sku: string; qty_pcs: number; physical_at: string; notes: string; origin_kind: string; revision: string; target_value: string | null; extra_cost: string | null; pending_returns: number }
export type ConversionWorkspace = { lots: ConversionLot[]; targets: ConversionTarget[]; documents: ConversionDocument[]; total: number; page: number; page_size: number; targets_total: number; target_page: number; documents_total: number; document_page: number }
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
export function parseConversionWorkspace(value: unknown): ConversionWorkspace {
  const o = conversionObject(value)
  const lots = rows(o.lots, x => ({ id: id(x.id), product_id: id(x.product_id), lot_number: text(x.lot_number), sku: text(x.sku), product_name: text(x.product_name), location_id: id(x.location_id), location_name: text(x.location_name), qty: count(x.qty), source_revision: text(x.source_revision), unit_hpp: amount(x.unit_hpp) }))
  if (new Set(lots.map(l => l.id + l.location_id)).size !== lots.length) throw new Error('Lot dan lokasi ganda.')
  return { lots, targets: rows(o.targets, x => ({ id: id(x.id), sku: text(x.sku), product_name: text(x.product_name) })),
    documents: rows(o.documents, x => { const status = text(x.status); if (!['POSTED', 'REVERSED'].includes(status)) throw new Error('Status konversi tidak valid.')
      return { id: id(x.id), conversion_number: text(x.conversion_number), status, source_sku: text(x.source_sku), target_sku: text(x.target_sku), qty_pcs: count(x.qty_pcs), physical_at: text(x.physical_at), notes: text(x.notes), origin_kind: text(x.origin_kind), revision: text(x.revision), target_value: amount(x.target_value), extra_cost: amount(x.extra_cost), pending_returns: count(x.pending_returns) } }),
    total: count(o.total), page: count(o.page), page_size: count(o.page_size), targets_total: count(o.targets_total), target_page: count(o.target_page), documents_total: count(o.documents_total), document_page: count(o.document_page) }
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
  if (action === 'REVERSE' && (r.conversion_id !== p.conversion_id || r.status !== 'REVERSED')) throw new Error('Pembatalan tidak cocok.')
  if (action === 'POST_USAGE') { id(r.cost_document_id); if (r.conversion_id !== p.conversion_id) throw new Error('Sumber biaya tidak cocok.') }
  if (action === 'SAVE_REWORK' || action === 'SAVE_REDYE') { id(r.rework_id); if (r.target_product_id !== p.target_product_id) throw new Error('Target rework tidak cocok.') }
  if (action === 'SET_REDYE_PRICE' && (r.service_id !== p.service_id || r.price_status !== 'KNOWN')) throw new Error('Sumber harga tidak cocok.')
}
