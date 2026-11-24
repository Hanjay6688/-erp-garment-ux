import { isoDayText, lowercaseHex32 } from './lib/contractPatterns'
import { procurementObject } from './procurementContract'
import type { Json } from './types/database.preconnect'

export type SwitchRollReceipt = { document: Json; expected_version: string }
export type SwitchRollPayload = {
  purchase_id: string; issue_id: string; new_roll_id: string; reason: string; receipt?: SwitchRollReceipt
}
type CutIssue = {
  issue_id: string; cut_number: string; roll_number: string; material_name: string
  unit_code: string; physical_at: string; qty: string
}
type RollOption = {
  roll_id: string; roll_number: string; material_name: string; material_sku: string; unit_code: string
  received_at: string | null; purchase_number: string | null; qty_at_cut: string; qty_now: string
}
type Material = { name: string; code: string; unit: string; qty: string; average: string | null }
type OrderBook = { number: string; wip: string; fg: string; cogs: string }
type Sale = { number: string; date: string; sales: string; cogs: string | null; margin: string | null }
type Snapshot = { materials: Record<string, Material>; orders: Record<string, OrderBook>; sales: Record<string, Sale> }
export type SwitchRollImpact = {
  contract: 'cp7.switch-roll-impact.v1'; issue_id: string; cut_number: string; physical_at: string
  qty: string; unit: string; from_roll: string; from_number: string; from_material: string
  to_roll: string; to_number: string; to_material: string; effective_date: string
  closed_through: string | null; recognition_date: string; before: Snapshot; after: Snapshot
}
export type SwitchRollPreview = { impact: SwitchRollImpact; review_token: string }
export type SwitchRollOutcome = {
  impact: SwitchRollImpact; purchase_id: string; kind: 'COMMITTED_OUTCOME'; action: 'SWITCH'
  request_id: string; correction_id: string; reason: string
}
export type SwitchRollWorkspace = {
  issues: CutIssue[]; rolls: RollOption[]; next_offset: number | null
  history: (SwitchRollOutcome & { recorded_at: string })[]
}

const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v)
const strings = (v: Record<string, unknown>, keys: string[]) => keys.every(k => typeof v[k] === 'string')
const decimal = (v: unknown): v is string => typeof v === 'string' && /^-?[0-9]+(\.[0-9]+)?$/.test(v)
const maybeDecimal = (v: unknown) => v === null || decimal(v)
const timestamp = (v: unknown) => typeof v === 'string' && Number.isFinite(Date.parse(v))
const day = (v: unknown) => typeof v === 'string' && isoDayText.test(v)
function bad(): never { throw new Error('ERP mengirim data Ganti roll yang tidak lengkap. Muat ulang sebelum melanjutkan.') }

function snapshot(value: unknown) {
  const w = procurementObject(value)
  const materials = procurementObject(w.materials), orders = procurementObject(w.orders), sales = procurementObject(w.sales)
  for (const row of Object.values(materials).map(procurementObject)) {
    if (!strings(row, ['name', 'code', 'unit']) || !decimal(row.qty) || !maybeDecimal(row.average)) bad()
  }
  for (const row of Object.values(orders).map(procurementObject)) {
    if (!strings(row, ['number']) || !decimal(row.wip) || !decimal(row.fg) || !decimal(row.cogs)) bad()
  }
  for (const row of Object.values(sales).map(procurementObject)) {
    if (!strings(row, ['number']) || !day(row.date) || !decimal(row.sales) || !maybeDecimal(row.cogs) || !maybeDecimal(row.margin)) bad()
  }
  return w as unknown as Snapshot
}

function parseImpact(value: unknown, issue?: string, destination?: string): SwitchRollImpact {
  const i = procurementObject(value)
  if (i.contract !== 'cp7.switch-roll-impact.v1' || ![i.issue_id, i.from_roll, i.to_roll, i.from_material, i.to_material].every(uuid)
    || (issue && i.issue_id !== issue) || (destination && i.to_roll !== destination)
    || !strings(i, ['cut_number', 'from_number', 'to_number', 'unit']) || !decimal(i.qty) || !timestamp(i.physical_at)
    || !day(i.effective_date) || !day(i.recognition_date) || (i.closed_through !== null && !day(i.closed_through))) return bad()
  snapshot(i.before); snapshot(i.after)
  return i as unknown as SwitchRollImpact
}

export function parseSwitchRollPreview(value: unknown, payload: SwitchRollPayload): SwitchRollPreview {
  const r = procurementObject(value)
  if (typeof r.review_token !== 'string' || !lowercaseHex32.test(r.review_token)) return bad()
  return { review_token: r.review_token, impact: parseImpact(r.impact, payload.issue_id, payload.new_roll_id) }
}

export function parseSwitchRollOutcome(value: unknown, request?: string, payload?: SwitchRollPayload): SwitchRollOutcome {
  const r = procurementObject(value)
  if (r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'SWITCH' || ![r.request_id, r.correction_id, r.purchase_id].every(uuid)
    || (request && r.request_id !== request) || (payload && r.reason !== payload.reason) || typeof r.reason !== 'string') return bad()
  parseImpact(r.impact, payload?.issue_id, payload?.new_roll_id)
  return r as unknown as SwitchRollOutcome
}

export function parseSwitchRollWorkspace(value: unknown, purchase: string, issue: string | null): SwitchRollWorkspace {
  const w = procurementObject(value)
  if (w.contract !== 'cp7.switch-roll-workspace.v1' || w.purchase_id !== purchase || w.issue_id !== issue
    || !Array.isArray(w.issues) || !Array.isArray(w.rolls) || !Array.isArray(w.history)
    || (w.next_offset !== null && (typeof w.next_offset !== 'number' || !Number.isSafeInteger(w.next_offset) || w.next_offset < 25))) return bad()
  for (const row of w.issues.map(procurementObject)) {
    if (!uuid(row.issue_id) || !strings(row, ['cut_number', 'roll_number', 'material_name', 'unit_code']) || !decimal(row.qty) || !timestamp(row.physical_at)) return bad()
  }
  for (const row of w.rolls.map(procurementObject)) {
    if (!uuid(row.roll_id) || !strings(row, ['roll_number', 'material_name', 'material_sku', 'unit_code'])
      || !decimal(row.qty_at_cut) || !decimal(row.qty_now) || (row.received_at !== null && !timestamp(row.received_at))
      || (row.purchase_number !== null && typeof row.purchase_number !== 'string')) return bad()
  }
  for (const row of w.history.map(procurementObject)) {
    if (!timestamp(row.recorded_at)) return bad()
    parseSwitchRollOutcome(row)
  }
  return w as unknown as SwitchRollWorkspace
}
