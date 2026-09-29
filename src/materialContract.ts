import type { Json } from './types/database.preconnect'

export type MaterialPage<T> = { rows: T[]; total: string; offset: number; limit: number; next_offset: number | null }
type Capabilities = { transfer: boolean; reverse_transfer: boolean }
type Value = { state: 'KNOWN' | 'UNKNOWN'; unit_cost: string | null; value: string | null; basis: 'CURRENT_MATERIAL_MOVING_AVERAGE' }
export type MaterialBalance = { material_id: string; material_sku: string; material_name: string; unit_code: string; roll_id: string | null; roll_number: string | null; location_id: string; location_name: string; qty: string; last_movement_at: string; quality: 'KNOWN' | 'CONFLICT'; availability: 'ON_HAND' | 'EMPTY' | 'REVIEW_REQUIRED' | 'MATERIAL_INACTIVE' | 'LOCATION_INACTIVE' | 'SPECIAL_ZONE' | 'LOCATION_REVIEW'; valuation?: Value }
export type MaterialsWorkspace = { contract_version: 'cp7.material-workspace.v1'; kind: 'LIVE_FABRIC_LEDGER'; read_at: string; quantity_basis: 'POSTED_PHYSICAL_LEDGER_CURRENT_KNOWLEDGE'; financial_captured: boolean; capabilities: Capabilities; totals_by_unit: { unit_code: string; qty: string; quality: 'KNOWN' | 'CONFLICT' }[]; page: MaterialPage<MaterialBalance> }
export type MaterialMovement = { movement_id: string; physical_at: string; recorded_at: string; movement_type: string; qty_signed: string; running_qty: string; source_type: string; source_id: string | null; reversal_of_id: string | null; note: string | null; valuation?: { state: 'KNOWN' | 'UNKNOWN'; unit_cost: string | null; movement_value: string | null; basis: 'CURRENT_RESTATED_MOVEMENT_COST' } }
export type MaterialLedger = { contract_version: 'cp7.material-ledger.v1'; material_id: string; roll_id: string; location_id: string; read_at: string; financial_captured: boolean; history_basis: 'CURRENT_RESTATED_NOT_AS_KNOWN'; page: MaterialPage<MaterialMovement> }
export type TransferRow = { id: string; number: string; from_location_id: string; to_location_id: string; from_location_name: string; to_location_name: string; physical_at: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; row_version: string; notes: string | null; line_count: string }
export type TransferDetail = TransferRow & { items: { id: string; material_id: string; material_sku: string; material_name: string; unit_code: string; roll_id: string | null; roll_number: string | null; qty: string; notes: string | null }[] }
export type MaterialTransfers = { contract_version: 'cp7.material-transfers.v1'; read_at: string; capabilities: Capabilities; page: MaterialPage<TransferRow>; detail: TransferDetail | null }
export type MaterialLocation = { id: string; code: string; name: string }
const id = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string'
const nullable = (v: unknown) => v === null || text(v)
const exact = (v: unknown): v is string => text(v) && /^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,6})?$/.test(v)
const whole = (v: unknown): v is string => text(v) && /^(0|[1-9][0-9]{0,18})$/.test(v)
const revision = (v: unknown): v is string => whole(v) && v !== '0'
const instant = (v: unknown) => text(v) && Number.isFinite(Date.parse(v))
const fail = (): never => { throw new Error('Data stok atau transfer belum lengkap. Muat ulang sebelum melanjutkan.') }
export function materialObject(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v)) return fail(); return v as Record<string, unknown> }
function closed(v: unknown, keys: string[], optional: string[] = []) { const x = materialObject(v); if (keys.some(k => !(k in x)) || Object.keys(x).some(k => !keys.includes(k) && !optional.includes(k))) fail(); return x }
function page(v: unknown, check: (r: unknown) => string) {
  const p = closed(v, ['rows','total','offset','limit','next_offset'])
  if (!Array.isArray(p.rows) || !whole(p.total) || !Number.isSafeInteger(p.offset) || Number(p.offset) < 0 || !Number.isSafeInteger(p.limit) || Number(p.limit) < 1 || Number(p.limit) > 100 || p.rows.length > Number(p.limit)) return fail()
  const end = BigInt(Number(p.offset)) + BigInt(p.rows.length), total = BigInt(p.total)
  if (p.rows.length && end > total || end < total && p.next_offset === null || p.next_offset !== null && (p.next_offset !== Number(p.offset) + p.rows.length || !p.rows.length || end >= total)) fail()
  const keys = p.rows.map(check); if (new Set(keys).size !== keys.length) fail()
  return p
}
function capabilities(v: unknown) { const c = closed(v, ['transfer','reverse_transfer']); if (Object.values(c).some(x => typeof x !== 'boolean') || c.reverse_transfer && !c.transfer) fail() }
function value(v: unknown, amount: string, basis: string) {
  const f = closed(v, ['state','unit_cost',amount,'basis']); if (f.basis !== basis) fail()
  if (f.state === 'KNOWN') { if (!exact(f.unit_cost) || !exact(f[amount])) fail() }
  else if (f.state !== 'UNKNOWN' || f.unit_cost !== null || f[amount] !== null) fail()
}
export function parseMaterials(v: unknown, finance: boolean): MaterialsWorkspace {
  const w = closed(v, ['contract_version','kind','read_at','quantity_basis','financial_captured','capabilities','totals_by_unit','page'])
  if (w.contract_version !== 'cp7.material-workspace.v1' || w.kind !== 'LIVE_FABRIC_LEDGER' || w.quantity_basis !== 'POSTED_PHYSICAL_LEDGER_CURRENT_KNOWLEDGE' || w.financial_captured !== finance || !instant(w.read_at) || !Array.isArray(w.totals_by_unit)) return fail()
  capabilities(w.capabilities); const units = new Set()
  for (const v of w.totals_by_unit) { const t = closed(v, ['unit_code','qty','quality']); if (!text(t.unit_code) || units.has(t.unit_code) || !exact(t.qty) || !['KNOWN','CONFLICT'].includes(String(t.quality))) fail(); units.add(t.unit_code) }
  page(w.page, v => {
    const r = closed(v, ['material_id','material_sku','material_name','unit_code','roll_id','roll_number','location_id','location_name','qty','last_movement_at','quality','availability'], finance ? ['valuation'] : [])
    if (!id(r.material_id) || !id(r.location_id) || r.roll_id !== null && !id(r.roll_id) || !nullable(r.roll_number) || ![r.material_sku,r.material_name,r.unit_code,r.location_name].every(text) || !exact(r.qty) || !instant(r.last_movement_at) || !['KNOWN','CONFLICT'].includes(String(r.quality)) || !['ON_HAND','EMPTY','REVIEW_REQUIRED','MATERIAL_INACTIVE','LOCATION_INACTIVE','SPECIAL_ZONE','LOCATION_REVIEW'].includes(String(r.availability))) return fail()
    if (finance) value(r.valuation,'value','CURRENT_MATERIAL_MOVING_AVERAGE')
    return `${r.material_id}:${r.roll_id}:${r.location_id}`
  }); return w as unknown as MaterialsWorkspace
}
export function parseMaterialLedger(v: unknown, finance: boolean): MaterialLedger {
  const w = closed(v,['contract_version','material_id','roll_id','location_id','read_at','financial_captured','history_basis','page'])
  if (w.contract_version !== 'cp7.material-ledger.v1' || ![w.material_id,w.roll_id,w.location_id].every(id) || !instant(w.read_at) || w.financial_captured !== finance || w.history_basis !== 'CURRENT_RESTATED_NOT_AS_KNOWN') fail()
  page(w.page,v => {
    const r = closed(v,['movement_id','physical_at','recorded_at','movement_type','qty_signed','running_qty','source_type','source_id','reversal_of_id','note'],finance ? ['valuation'] : [])
    if (!id(r.movement_id) || !instant(r.physical_at) || !instant(r.recorded_at) || !text(r.movement_type) || !text(r.source_type) || r.source_id !== null && !id(r.source_id) || r.reversal_of_id !== null && !id(r.reversal_of_id) || !nullable(r.note) || !exact(r.qty_signed) || !exact(r.running_qty)) return fail()
    if (finance) value(r.valuation,'movement_value','CURRENT_RESTATED_MOVEMENT_COST')
    return r.movement_id
  }); return w as unknown as MaterialLedger
}
const transferKeys = ['id','number','from_location_id','to_location_id','from_location_name','to_location_name','physical_at','status','row_version','notes','line_count']
function transfer(v: unknown, detail = false) {
  const r = closed(v,[...transferKeys,...(detail ? ['items'] : [])])
  if (![r.id,r.from_location_id,r.to_location_id].every(id) || ![r.number,r.from_location_name,r.to_location_name].every(text) || !instant(r.physical_at) || !['DRAFT','POSTED','REVERSED'].includes(String(r.status)) || !revision(r.row_version) || !nullable(r.notes) || !whole(r.line_count)) fail()
  return r
}
export function parseMaterialTransfers(v: unknown): MaterialTransfers {
  const w = closed(v,['contract_version','read_at','capabilities','page','detail'])
  if (w.contract_version !== 'cp7.material-transfers.v1' || !instant(w.read_at)) fail(); capabilities(w.capabilities)
  page(w.page,v => String(transfer(v).id))
  if (w.detail !== null) {
    const d = transfer(w.detail,true)
    if (!Array.isArray(d.items) || d.items.length > 100 || BigInt(d.items.length) !== BigInt(String(d.line_count))) return fail()
    const seen = new Set()
    for (const v of d.items) {
      const r = closed(v,['id','material_id','material_sku','material_name','unit_code','roll_id','roll_number','qty','notes'])
      if (!id(r.id) || seen.has(r.id) || !id(r.material_id) || ![r.material_sku,r.material_name,r.unit_code].every(text) || r.roll_id !== null && !id(r.roll_id) || !nullable(r.roll_number) || !nullable(r.notes) || !exact(r.qty)) fail()
      seen.add(r.id)
    }
  }
  return w as unknown as MaterialTransfers
}
export function parseMaterialLocations(v: unknown): MaterialPage<MaterialLocation> {
  const w = closed(v,['contract_version','rows','total','offset','limit','next_offset'])
  if (w.contract_version !== 'cp7.material-locations.v1') fail()
  const {contract_version:_,...p} = w
  page(p,v=>{const r=closed(v,['id','code','name']);if(!id(r.id)||!text(r.code)||!text(r.name))return fail();return r.id})
  return p as MaterialPage<MaterialLocation>
}
export function parseMaterialOutcome(v: unknown, request: string, action: string, document: Json) {
  const r = closed(v,['contract_version','kind','action','request_id','transfer_id','status','row_version']), p = materialObject(document)
  const states: Record<string,string> = {SAVE_TRANSFER:'DRAFT',POST_TRANSFER:'POSTED',REVERSE_TRANSFER:'REVERSED'}
  if (r.contract_version !== 'cp7.material-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== action || r.request_id !== request || !id(r.transfer_id) || !revision(r.row_version) || !states[action] || r.status !== states[action] || action !== 'SAVE_TRANSFER' && r.transfer_id !== p.transfer_id || action === 'SAVE_TRANSFER' && p.id && r.transfer_id !== p.id) fail()
  return r as { transfer_id: string; row_version: string; status: 'DRAFT' | 'POSTED' | 'REVERSED' }
}
