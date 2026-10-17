// R3-03 (owner D16-1): Ringkasan Gudang. Closed parser for public.erp_cp7_get_warehouse_summary_v1
// (scripts/cp7-src/warehouse-summary/summary.sql). Unknown keys, a section the identity may not see, a value without
// finance.hpp.view or a page whose rows do not add up to its totals are refused, so the screen never shows such a figure.
export type WarehouseMenu = 'materials-rolls' | 'accessories' | 'fg-summary' | 'procurement' | 'stock-adjustment'
export type SummaryValuation = { value: string; unknown_count: string; basis: 'CURRENT_MATERIAL_MOVING_AVERAGE' | 'CURRENT_RESTATED_LOT_VALUE' }
export type Quality = 'KNOWN' | 'CONFLICT'
export type MaterialLine = { kind: 'FABRIC' | 'OTHER'; unit_code: string; qty: string; rolls: string; balances: string; quality: Quality }
export type MaterialPart = { lines: MaterialLine[]; valuation?: SummaryValuation }
export type AccessoryLine = { unit_code: string; qty: string; items: string; balances: string; quality: Quality }
export type AccessoryPart = { lines: AccessoryLine[]; valuation?: SummaryValuation }
export type FgGrade = { quality_grade: string; physical_qty: string }
export type FgPart = { physical_qty: string; reserved_qty: string; available_qty: string; positions: string; quality: Quality; grades: FgGrade[]; valuation?: SummaryValuation }
export type SummaryLocation = {
  location_id: string; location_code: string | null; location_name: string; location_type: string; is_active: boolean; zone_kind: string | null
  materials: MaterialPart | null; accessories: AccessoryPart | null; finished_goods: FgPart | null
}
export type LowFabric = { material_id: string; material_sku: string; material_name: string; unit_code: string; qty: string; minimum_qty: string }
export type AttentionKind = 'MATERIAL_BALANCE_REVIEW' | 'ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS' | 'ACCESSORY_NEGATIVE' | 'FG_POSITION_REVIEW'
  | 'FABRIC_BELOW_MINIMUM' | 'RECEIPT_DRAFT' | 'MATERIAL_TRANSFER_DRAFT' | 'MATERIAL_COUNT_DRAFT' | 'FG_ADJUSTMENT_DRAFT'
export type Attention = { kind: AttentionKind; menu: WarehouseMenu; count: string; rows?: LowFabric[] }
export type WarehouseSummary = {
  contract_version: 'cp7.warehouse-summary.v1'; kind: 'LIVE_WAREHOUSE_SUMMARY'; read_at: string; business_DML: false; financial_captured: boolean; q: string
  sections: { materials: boolean; accessories: boolean; finished_goods: boolean }
  totals: { materials: MaterialPart | null; accessories: AccessoryPart | null; finished_goods: FgPart | null }
  page: { rows: SummaryLocation[]; total: string; offset: number; limit: number; next_offset: number | null }
  attention: Attention[]
}
// What the identity may see, from its permissions (src/auth/accessCatalog.ts keys); the server answer must match it.
export type SummaryAccess = { materials: boolean; accessories: boolean; finished_goods: boolean; finance: boolean; procurement: boolean; stockAdjust: boolean; fabricMaster: boolean }
export function summaryAccess(permissions: readonly string[]): SummaryAccess {
  const has = (key: string) => permissions.includes(key)
  return { materials: has('warehouse.material.view'), accessories: has('warehouse.accessory.view'), finished_goods: has('warehouse.fg.view'),
    finance: has('finance.hpp.view'), procurement: has('warehouse.procurement.view'), stockAdjust: has('warehouse.stock.adjust'), fabricMaster: has('master.fabric.view') }
}
// Each check, the screen that shows it, and the keys it needs (the same rule as the server).
export const ATTENTION_RULES: Readonly<Record<AttentionKind, { menu: WarehouseMenu; allowed: (a: SummaryAccess) => boolean }>> = Object.freeze({
  MATERIAL_BALANCE_REVIEW: { menu: 'materials-rolls', allowed: a => a.materials },
  ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS: { menu: 'materials-rolls', allowed: a => a.materials },
  ACCESSORY_NEGATIVE: { menu: 'accessories', allowed: a => a.accessories },
  FG_POSITION_REVIEW: { menu: 'fg-summary', allowed: a => a.finished_goods },
  FABRIC_BELOW_MINIMUM: { menu: 'materials-rolls', allowed: a => a.materials && a.fabricMaster },
  RECEIPT_DRAFT: { menu: 'procurement', allowed: a => a.procurement },
  MATERIAL_TRANSFER_DRAFT: { menu: 'materials-rolls', allowed: a => a.materials },
  MATERIAL_COUNT_DRAFT: { menu: 'stock-adjustment', allowed: a => a.materials && a.stockAdjust },
  FG_ADJUSTMENT_DRAFT: { menu: 'stock-adjustment', allowed: a => a.finished_goods && a.stockAdjust },
})
const KINDS = Object.keys(ATTENTION_RULES) as AttentionKind[]

type Obj = Record<string, unknown>
const fail = (): never => { throw new Error('Data ringkasan gudang belum lengkap atau hak akses berubah. Muat ulang ringkasan.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const nullableText = (v: unknown) => v === null || text(v)
const exact = (v: unknown): v is string => typeof v === 'string' && /^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,6})?$/.test(v)
const whole = (v: unknown): v is string => typeof v === 'string' && /^(0|[1-9][0-9]{0,18})$/.test(v)
const instant = (v: unknown) => typeof v === 'string' && Number.isFinite(Date.parse(v))
function object(v: unknown): Obj { if (!v || typeof v !== 'object' || Array.isArray(v)) fail(); return v as Obj }
function closed(v: unknown, keys: string[], optional: string[] = []): Obj {
  const o = object(v)
  if (keys.some(k => !(k in o)) || Object.keys(o).some(k => !keys.includes(k) && !optional.includes(k))) fail()
  return o
}
function array(v: unknown): unknown[] { if (!Array.isArray(v)) fail(); return v as unknown[] }
const quality = (v: unknown) => v === 'KNOWN' || v === 'CONFLICT'

// Exact decimal arithmetic on the server's strings (6 decimals at most), never floating point.
const SCALE = 1_000_000n
export function decimalUnits(v: string): bigint {
  const negative = v.startsWith('-'), [w, f = ''] = (negative ? v.slice(1) : v).split('.')
  const units = BigInt(w) * SCALE + BigInt((f + '000000').slice(0, 6))
  return negative ? -units : units
}
export function decimalText(units: bigint): string {
  const negative = units < 0n, a = negative ? -units : units, w = a / SCALE, f = (a % SCALE).toString().padStart(6, '0').replace(/0+$/, '')
  return (negative ? '-' : '') + w.toString() + (f ? '.' + f : '')
}
// Rupiah to whole cents, half away from zero (as PostgreSQL round), for display only.
export function moneyText(v: string): string {
  const units = decimalUnits(v), step = 10_000n, a = units < 0n ? -units : units, cents = (a + step / 2n) / step * step
  return decimalText(units < 0n ? -cents : cents)
}

function valuation(v: unknown, basis: string, finance: boolean, holder: Obj) {
  if (!finance) { if ('valuation' in holder) fail(); return }
  const x = closed(v, ['value', 'unknown_count', 'basis'])
  if (!exact(x.value) || !whole(x.unknown_count) || x.basis !== basis) fail()
}
function materialPart(v: unknown, finance: boolean): MaterialPart {
  const o = closed(v, ['lines'], ['valuation']), seen = new Set<string>()
  for (const l of array(o.lines)) {
    const x = closed(l, ['kind', 'unit_code', 'qty', 'rolls', 'balances', 'quality'])
    if ((x.kind !== 'FABRIC' && x.kind !== 'OTHER') || !text(x.unit_code) || !exact(x.qty) || !whole(x.rolls) || !whole(x.balances) || !quality(x.quality)
      || x.kind === 'OTHER' && x.rolls !== '0' || BigInt(x.rolls as string) > BigInt(x.balances as string) || seen.has(`${x.kind}:${x.unit_code}`)) fail()
    seen.add(`${x.kind}:${x.unit_code}`)
  }
  valuation(o.valuation, 'CURRENT_MATERIAL_MOVING_AVERAGE', finance, o)
  return o as unknown as MaterialPart
}
function accessoryPart(v: unknown, finance: boolean): AccessoryPart {
  const o = closed(v, ['lines'], ['valuation']), seen = new Set<string>()
  for (const l of array(o.lines)) {
    const x = closed(l, ['unit_code', 'qty', 'items', 'balances', 'quality'])
    if (!text(x.unit_code) || !exact(x.qty) || !whole(x.items) || !whole(x.balances) || !quality(x.quality) || seen.has(x.unit_code)) fail()
    seen.add(x.unit_code as string)
  }
  valuation(o.valuation, 'CURRENT_MATERIAL_MOVING_AVERAGE', finance, o)
  return o as unknown as AccessoryPart
}
function fgPart(v: unknown, finance: boolean): FgPart {
  const o = closed(v, ['physical_qty', 'reserved_qty', 'available_qty', 'positions', 'quality', 'grades'], ['valuation']), seen = new Set<string>()
  if (![o.physical_qty, o.reserved_qty, o.available_qty].every(exact) || !whole(o.positions) || !quality(o.quality)) fail()
  if (decimalUnits(o.available_qty as string) + decimalUnits(o.reserved_qty as string) !== decimalUnits(o.physical_qty as string)) fail()
  let grades = 0n
  for (const g of array(o.grades)) {
    const x = closed(g, ['quality_grade', 'physical_qty'])
    if (!text(x.quality_grade) || !exact(x.physical_qty) || seen.has(x.quality_grade)) fail()
    seen.add(x.quality_grade as string); grades += decimalUnits(x.physical_qty as string)
  }
  if (grades !== decimalUnits(o.physical_qty as string)) fail()
  valuation(o.valuation, 'CURRENT_RESTATED_LOT_VALUE', finance, o)
  return o as unknown as FgPart
}
function part<T>(v: unknown, visible: boolean, parse: (v: unknown) => T): T | null {
  if (!visible) { if (v !== null) fail(); return null }
  return parse(v)
}
function sumLines<T extends { qty: string }>(rows: T[][], key: (l: T) => string) {
  const out = new Map<string, bigint>()
  for (const lines of rows) for (const l of lines) out.set(key(l), (out.get(key(l)) ?? 0n) + decimalUnits(l.qty))
  return out
}
function sameMap(a: Map<string, bigint>, b: Map<string, bigint>) {
  const keys = new Set([...a.keys(), ...b.keys()])
  return [...keys].every(k => (a.get(k) ?? 0n) === (b.get(k) ?? 0n))
}

export function parseWarehouseSummary(v: unknown, access: SummaryAccess): WarehouseSummary {
  const w = closed(v, ['contract_version', 'kind', 'read_at', 'business_DML', 'financial_captured', 'q', 'sections', 'totals', 'page', 'attention'])
  if (w.contract_version !== 'cp7.warehouse-summary.v1' || w.kind !== 'LIVE_WAREHOUSE_SUMMARY' || w.business_DML !== false || !instant(w.read_at)
    || typeof w.q !== 'string' || w.q.length > 120 || w.financial_captured !== access.finance) fail()
  const s = closed(w.sections, ['materials', 'accessories', 'finished_goods'])
  if (s.materials !== access.materials || s.accessories !== access.accessories || s.finished_goods !== access.finished_goods) fail()
  const f = access.finance
  const t = closed(w.totals, ['materials', 'accessories', 'finished_goods'])
  const totals = {
    materials: part(t.materials, access.materials, x => materialPart(x, f)),
    accessories: part(t.accessories, access.accessories, x => accessoryPart(x, f)),
    finished_goods: part(t.finished_goods, access.finished_goods, x => fgPart(x, f)),
  }
  const p = closed(w.page, ['rows', 'total', 'offset', 'limit', 'next_offset']), rows = array(p.rows)
  if (!whole(p.total) || !Number.isSafeInteger(p.offset) || (p.offset as number) < 0 || !Number.isSafeInteger(p.limit) || (p.limit as number) < 1 || (p.limit as number) > 100 || rows.length > (p.limit as number)) fail()
  const end = BigInt(p.offset as number) + BigInt(rows.length), total = BigInt(p.total as string)
  if (rows.length && end > total || end < total && p.next_offset !== Number(end) || end >= total && p.next_offset !== null || end < total && !rows.length) fail()
  const ids = new Set<string>()
  const locations = rows.map(r => {
    const x = closed(r, ['location_id', 'location_code', 'location_name', 'location_type', 'is_active', 'zone_kind', 'materials', 'accessories', 'finished_goods'])
    if (!uuid(x.location_id) || ids.has(x.location_id) || !nullableText(x.location_code) || !text(x.location_name) || !text(x.location_type) || typeof x.is_active !== 'boolean' || !nullableText(x.zone_kind)) fail()
    ids.add(x.location_id as string)
    const loc = { ...x, materials: part(x.materials, access.materials, y => materialPart(y, f)), accessories: part(x.accessories, access.accessories, y => accessoryPart(y, f)),
      finished_goods: part(x.finished_goods, access.finished_goods, y => fgPart(y, f)) } as SummaryLocation
    // A location is listed only where a visible section holds stock.
    if (!(loc.materials?.lines.length || loc.accessories?.lines.length || Number(loc.finished_goods?.positions ?? '0') > 0)) fail()
    return loc
  })
  // One answer is one reading: when the page holds every location, its rows add up to its totals exactly.
  if (p.offset === 0 && p.next_offset === null) {
    if (totals.materials && !sameMap(sumLines(locations.map(l => l.materials!.lines), l => `${l.kind}:${l.unit_code}`), sumLines([totals.materials.lines], l => `${l.kind}:${l.unit_code}`))) fail()
    if (totals.accessories && !sameMap(sumLines(locations.map(l => l.accessories!.lines), l => l.unit_code), sumLines([totals.accessories.lines], l => l.unit_code))) fail()
    if (totals.finished_goods && locations.reduce((a, l) => a + decimalUnits(l.finished_goods!.physical_qty), 0n) !== decimalUnits(totals.finished_goods.physical_qty)) fail()
  }
  const kinds = new Set<string>()
  const attention = array(w.attention).map(a => {
    const x = closed(a, ['kind', 'menu', 'count'], ['rows'])
    const kind = x.kind as AttentionKind
    if (!KINDS.includes(kind) || kinds.has(kind) || x.menu !== ATTENTION_RULES[kind].menu || !ATTENTION_RULES[kind].allowed(access) || !whole(x.count)) fail()
    kinds.add(kind)
    if (kind === 'FABRIC_BELOW_MINIMUM') {
      const list = array(x.rows)
      if (list.length > 10 || BigInt(list.length) > BigInt(x.count as string) || BigInt(x.count as string) > 0n && !list.length) fail()
      for (const r of list) {
        const y = closed(r, ['material_id', 'material_sku', 'material_name', 'unit_code', 'qty', 'minimum_qty'])
        if (!uuid(y.material_id) || ![y.material_sku, y.material_name, y.unit_code].every(text) || !exact(y.qty) || !exact(y.minimum_qty)
          || decimalUnits(y.qty as string) >= decimalUnits(y.minimum_qty as string)) fail()
      }
    } else if ('rows' in x) fail()
    return x as unknown as Attention
  })
  // Every check the identity may see is answered (with 0 when there is nothing), none other.
  if (KINDS.filter(k => ATTENTION_RULES[k].allowed(access)).some(k => !kinds.has(k))) fail()
  return { ...(w as unknown as WarehouseSummary), totals, page: { ...(p as unknown as WarehouseSummary['page']), rows: locations }, attention }
}
