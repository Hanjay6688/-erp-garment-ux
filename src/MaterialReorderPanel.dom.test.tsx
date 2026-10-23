// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MaterialReorderPanel from './MaterialReorderPanel'
import WarehouseFabricReorderSummary from './WarehouseFabricReorderSummary'
import ConnectedMasterPage from './ConnectedMasterPage'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import {
  accessoryEstimatePoint, materialPayload, materialProblem, materialWriteErrorText, moqDays, parseMaterialSaveResult, parseMaterialWorkspace, type MaterialDraft,
  type MaterialPayload, type MaterialQuery,
} from './materialReorderContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { REORDER_RUN_AT, reorderRun } from '../tests/fixtures/fgReorder'
import { materialId, materialRow, materialWire, type MaterialWireRow } from '../tests/fixtures/materialReorder'

// SS-2/SS-3 and owner D17-10/D17-12: Titik pesan ulang of fabric and Batas minimum of accessories against a fake of the three
// public RPCs of scripts/cp7-src/stock-formula/materials.sql that keeps their rules (Owner/Admin to change, a fabric has no
// manual number and none of the accessory numbers, an accessory no formula but a minimum typed or worked out from the owner's
// MOQ, lama kirim, monthly use and buffer, revision check, one answer per request id, busy refresh).
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const wib = formatCp6WibDateTime
const LATER = '2026-10-20T03:05:00+00:00'
const FQ: MaterialQuery = { material_type: 'FABRIC', q: '', filter: 'ALL', offset: 0, limit: 25 }
const AQ: MaterialQuery = { ...FQ, material_type: 'ACCESSORY' }
const PERMS = ['warehouse.material.view', 'master.fabric.view', 'warehouse.accessory.view']

type Fake = { rows: MaterialWireRow[]; canManage: boolean; busy: boolean; run: unknown; lose: Set<string>; calls: [string, Record<string, unknown>][]
  answers: Map<string, { args: string; data: unknown }>; corrupt: boolean }
const refuse = (code: string, message: string) => ({ data: null, error: { code, message, details: null, hint: null } })
const num = (v: string | null | undefined) => v === undefined || v === null ? null : Number(v)
// The server's estimate on the test's numbers (chosen so that this floating-point form is exact).
const serverEstimate = (usage: number, lead: number, buffer: number) => Math.ceil(usage / 30 * (lead + buffer) * 100) / 100
// compute_materials(): a fabric on its minimum or the formula; an accessory (D17-10/D17-12) on its typed minimum or else the
// estimate from its three numbers, at or under it when the stock in the warehouse is not above it.
function recompute(r: MaterialWireRow): MaterialWireRow {
  if (r.material_type === 'ACCESSORY') {
    const manual = r.manual_point as number | null, usage = r.usage_month_qty as number | null, lead = r.lead_days as number | null
    const buffer = r.buffer_days as number | null, estimate = usage !== null && lead !== null && buffer !== null ? serverEstimate(usage, lead, buffer) : null
    const point = manual ?? estimate
    return { ...r, basis: manual !== null ? 'MANUAL' : estimate !== null ? 'ESTIMATE' : 'NOT_SET', reason: point === null ? 'NO_MINIMUM_OR_ESTIMATE' : null, point,
      estimate_point: estimate, safety_qty: null, formula_point: null,
      state: point === null || point <= 0 ? 'NO_POINT' : Number(r.free_qty) <= point ? 'AT_OR_BELOW' : 'ABOVE' }
  }
  const manual = r.manual_point as number | null, lead = r.lead_days as number | null, usage = Number(r.usage_qty), counted = r.counted_days as number
  const formula = manual === null && usage > 0 && counted >= 14 && lead !== null
  const point = manual !== null ? manual : formula ? (r.formula_point as number | null) ?? 63.34 : null
  const basis = manual !== null ? 'MANUAL' : usage <= 0 ? 'NO_USAGE' : counted < 14 || lead === null ? 'NOT_ENOUGH_DATA' : 'FORMULA'
  const reason = basis === 'NO_USAGE' ? 'NO_POSTED_USAGE_IN_WINDOW' : basis === 'NOT_ENOUGH_DATA' ? (counted < 14 ? 'FEWER_THAN_14_COUNTED_DAYS' : 'NO_LEAD_TIME') : null
  const safety = lead !== null && usage > 0 && counted >= 14 ? (r.safety_qty as number | null) ?? 18.5521 : null
  return { ...r, basis, reason, point, safety_qty: safety, formula_point: safety === null ? null : (r.formula_point as number | null) ?? 63.34,
    state: point === null || point <= 0 ? 'NO_POINT' : Number(r.free_qty) + Number(r.on_order_qty) <= point ? 'AT_OR_BELOW' : 'ABOVE' }
}
function server(options: Partial<Fake> = {}) {
  const fake: Fake = { rows: [materialRow(1)], canManage: true, busy: false, run: undefined, lose: new Set(), calls: [], answers: new Map(), corrupt: false, ...options }
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown> = {}) => {
    fake.calls.push([name, structuredClone(args)])
    const answer = (() => {
      if (name === 'erp_cp7_get_material_reorder_v1') {
        const data = materialWire(fake.rows, args.p_query as MaterialQuery, { can_manage: fake.canManage, ...(fake.run === undefined ? {} : { run: fake.run }) })
        if (fake.corrupt) Object.assign(data.page.rows[0] as object, { point: 0, state: 'AT_OR_BELOW' })
        return { data, error: null }
      }
      if (name === 'erp_cp7_refresh_material_reorder_v1') return fake.busy ? refuse('55P03', 'CP7_FORMULA_BUSY') : { data: { computed_at: LATER, items: 3,
        at_or_below: 1, wip_read: 0, materials: fake.rows.length, materials_at_or_below: fake.rows.filter(r => r.state === 'AT_OR_BELOW').length }, error: null }
      if (name !== 'erp_cp7_save_material_reorder_v1') throw new Error(`unexpected ${name}`)
      const p = args.p_payload as MaterialPayload, key = String(args.p_request), sent = JSON.stringify(p), prior = fake.answers.get(key)
      if (prior) return prior.args === sent ? { data: prior.data, error: null } : refuse('22023', 'CP7_FORMULA_REQUEST_REUSED')
      if (!fake.canManage) return refuse('42501', 'CP7_FORMULA_ACCESS_DENIED')
      const i = fake.rows.findIndex(r => r.material_id === p.material_id)
      if (i < 0) return refuse('22023', 'CP7_FORMULA_ITEM_UNKNOWN')
      const accessory = fake.rows[i].material_type === 'ACCESSORY'
      // save_material: a fabric has no manual number and none of the accessory numbers (D17-12).
      if (!accessory && (p.manual_point !== null || [p.moq, p.usage_month_qty, p.buffer_days].some(v => v !== undefined && v !== null)))
        return refuse('22023', 'CP7_FORMULA_MATERIAL_INVALID')
      if (p.expected_revision !== ((fake.rows[i].setting_revision as number | null) ?? 0)) return refuse('40001', 'CP7_FORMULA_MATERIAL_STALE')
      const revision = p.expected_revision + 1
      const next = recompute({ ...fake.rows[i], setting_revision: revision, lead_days: p.lead_days === null ? null : Number(p.lead_days),
        ...(accessory ? { manual_point: p.manual_point === null ? null : Number(p.manual_point), manual_source: p.manual_point === null ? null : 'ACCESSORY_MANUAL',
          moq: num(p.moq), usage_month_qty: num(p.usage_month_qty), buffer_days: num(p.buffer_days) } : {}) })
      fake.rows[i] = next
      fake.answers.set(key, { args: sent, data: { replay: true, material_id: p.material_id, revision } })
      return { data: { replay: false, material_id: p.material_id, revision, evaluation: next }, error: null }
    })()
    if (fake.lose.has(name)) { fake.lose.delete(name); throw new TypeError('Failed to fetch') }
    return answer
  })
  return fake
}

let root: Root, container: HTMLDivElement
const as = (role: string, permissions: string[]) => ({ ...recoveryIdentity, identity: { ...recoveryIdentity.identity,
  profile: { ...recoveryIdentity.identity.profile, role }, permissions: [...recoveryIdentity.identity.permissions, ...permissions] } })
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear(); client.rpc.mockReset(); auth.current = as('OWNER', PERMS)
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks() })
async function settle() { for (let i = 0; i < 3; i++) await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount(type: 'FABRIC' | 'ACCESSORY' = 'FABRIC') { await act(async () => root.render(<MaterialReorderPanel materialType={type}/>)); await settle() }
function button(name: string, scope: ParentNode = container) {
  const b = [...scope.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name || x.getAttribute('aria-label') === name || x.textContent?.startsWith(`${name} (`))
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
async function click(name: string, scope?: ParentNode) { await act(async () => button(name, scope).click()); await settle() }
function field<T extends HTMLElement>(label: string, scope: ParentNode = container) {
  const el = scope.querySelector<T>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}: ${container.textContent}`); return el
}
async function type(label: string, value: string, scope?: ParentNode) {
  const el = field<HTMLInputElement>(label, scope)
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })) })
}
// A fabric row is "Titik pesan ulang <name>", an accessory row "Batas minimum <name>" (D17-10).
const row = (name: string) => {
  const el = [...container.querySelectorAll<HTMLElement>('article.cfr-row')].find(a => [`Titik pesan ulang ${name} (SKU `, `Batas minimum ${name} (SKU `]
    .some(prefix => a.getAttribute('aria-label')?.startsWith(prefix)))
  if (!el) throw new Error(`No row ${name}: ${container.textContent}`); return el
}
const cell = (r: HTMLElement, key: string) => r.querySelector(`[data-cmr="${key}"]`)?.textContent
const chip = (r: HTMLElement) => r.querySelector('.cfr-chip')?.textContent

describe('OW14a warehouse fabric calculation',()=>{
 async function expand(){
  await act(async()=>{const details=container.querySelector('details')!;details.open=true;details.dispatchEvent(new Event('toggle'))});await settle()
 }
 it('opens the existing fabric reader on demand and separates physical stock, incoming orders and the active threshold',async()=>{
  const fake=server()
  await act(async()=>root.render(<WarehouseFabricReorderSummary/>));await settle()
  expect(fake.calls).toEqual([])
  await expand()
  expect(fake.calls).toEqual([['erp_cp7_get_material_reorder_v1',{p_query:FQ}]])
  const fabric=row('Katun 1')
  expect(cell(fabric,'free')).toBe('56 YD');expect(cell(fabric,'ordered')).toBe('0 YD');expect(cell(fabric,'point')).toBe('63,34 YD')
  expect(fabric.textContent).toContain('Stok fisik saat perhitungan');expect(fabric.textContent).toContain('Pesanan belum diterima')
  expect(container.textContent).toContain('Pencarian gudang di atas tidak menyaring daftar kain ini')
  expect(container.textContent).toContain('ambang pengingat, bukan jumlah stok atau jumlah yang harus dibeli')
  expect([...container.querySelectorAll('button')].some(b=>/Hitung sekarang|Ubah|Simpan/.test(b.textContent??''))).toBe(false)
  expect(container.textContent).toContain(formatCp6WibDateTime(REORDER_RUN_AT))
 })
 it('retires the expanded facts when current access disappears and refuses to retain stale stock on a denied read',async()=>{
  server();await act(async()=>root.render(<WarehouseFabricReorderSummary/>));await expand()
  expect(row('Katun 1')).toBeTruthy()
  auth.current=as('OWNER',[])
  // The base recovery fixture has no fabric permissions: removal is immediate,
  // before another response can disclose the former facts.
  await act(async()=>root.render(<WarehouseFabricReorderSummary/>));await settle()
  expect(container.querySelectorAll('.cfr-row')).toHaveLength(0)
  auth.current=as('OWNER',PERMS);client.rpc.mockResolvedValue(refuse('42501','CP7_FORMULA_MATERIAL_SOURCE_DENIED'))
  await act(async()=>root.render(<WarehouseFabricReorderSummary/>));await settle()
  expect(container.querySelector('[role="alert"]')).toBeTruthy();expect(container.querySelectorAll('.cfr-row')).toHaveLength(0)
 })
})
const calls = (fake: Fake, name: string) => fake.calls.filter(c => c[0] === name).map(c => c[1])

// The situations a material can be in, as compute_materials() writes them.
const minimum = (n: number) => materialRow(n, 'FABRIC', { free_qty: 300, manual_point: 500, manual_source: 'FABRIC_MINIMUM', point: 500, basis: 'MANUAL',
  formula_point: 55.1 })
const noLead = (n: number) => materialRow(n, 'FABRIC', { lead_days: null, setting_revision: null, safety_qty: null, formula_point: null, point: null,
  basis: 'NOT_ENOUGH_DATA', reason: 'NO_LEAD_TIME', state: 'NO_POINT' })
const fewer = (n: number) => materialRow(n, 'FABRIC', { counted_days: 9, use_days: 3, usage_qty: 30, daily_mean: 3.3333, safety_qty: null, formula_point: null,
  point: null, basis: 'NOT_ENOUGH_DATA', reason: 'FEWER_THAN_14_COUNTED_DAYS', state: 'NO_POINT' })
const idle = (n: number) => materialRow(n, 'FABRIC', { usage_qty: 0, counted_days: 0, use_days: 0, daily_mean: null, daily_sd: null,
  safety_qty: null, formula_point: null, point: null, basis: 'NO_USAGE', reason: 'NO_POSTED_USAGE_IN_WINDOW', state: 'NO_POINT' })
// Accessories (D17-10/D17-12): a typed minimum (MANUAL), the estimate from the owner's numbers (ESTIMATE), or neither (NOT_SET);
// never a formula.
const accessoryMinimum = (n: number, point: number, free = 180, extra: Record<string, unknown> = {}) => materialRow(n, 'ACCESSORY', { free_qty: free,
  setting_revision: 1, manual_point: point, manual_source: 'ACCESSORY_MANUAL', point, basis: 'MANUAL', reason: null,
  state: point <= 0 ? 'NO_POINT' : free <= point ? 'AT_OR_BELOW' : 'ABOVE', ...extra })
const never = (n: number) => accessoryMinimum(n, 0)
const notSet = (n: number, extra: Record<string, unknown> = {}) => materialRow(n, 'ACCESSORY', extra)
/** 300 a month, 20 days from China and 5 days of buffer: (300 / 30) x 25 = 250, MOQ 5.000 (500 days). */
const estimated = (n: number, free = 180, usage = 300, lead = 20, buffer = 5, moq: number | null = 5000) => {
  const point = serverEstimate(usage, lead, buffer)
  return materialRow(n, 'ACCESSORY', { free_qty: free, setting_revision: 1, lead_days: lead, usage_month_qty: usage, buffer_days: buffer, moq, estimate_point: point,
    point, basis: 'ESTIMATE', reason: null, state: free <= point ? 'AT_OR_BELOW' : 'ABOVE' })
}
const draftOf = (d: Partial<MaterialDraft>): MaterialDraft => ({ lead: '', manual: '', moq: '', usageMonth: '', buffer: '', reason: 'Isian', ...d })
const run45 = reorderRun({ window_from: '2026-09-05', window_through: '2026-10-19', window_days: 45 })

describe('Titik pesan ulang of fabric and Batas minimum of accessories (SS-2/SS-3, D17-10, D17-12)', () => {
  it('parses the exact server shapes and refuses unknown, missing and impossible facts', () => {
    const good = materialWire([materialRow(1), minimum(2), noLead(3), fewer(4), idle(5), never(6), accessoryMinimum(7, 150)], FQ)
    const parsed = parseMaterialWorkspace(good, FQ)
    expect(parsed.page.rows.map(r => r.name)).toEqual(['Katun 1', 'Katun 2', 'Katun 3', 'Katun 4', 'Katun 5'])
    expect(parsed.page.rows[0]).toMatchObject({ freeQty: '56', onOrderQty: '0', dailyMean: '7.4667', leadDays: '6', settingRevision: 1, point: '63.34',
      formulaPoint: '63.34', basis: 'FORMULA', unitCode: 'YD', state: 'AT_OR_BELOW' })
    expect(parsed.counts).toEqual({ items: 5, atOrBelow: 2, manual: 1, formula: 1, estimate: 0, notEnoughData: 2, noUsage: 1, notSet: 0 })
    expect(parsed.run).toMatchObject({ materials: 7, materialsAtOrBelow: 2 })
    const rows = good.page.rows, withRow = (i: number, change: Record<string, unknown>) => ({ ...good, page: { ...good.page, rows: rows.map((r, j) => j === i ? { ...r, ...change } : r) } })
    expect(() => parseMaterialWorkspace({ ...good, extra: 1 }, FQ)).toThrow('Respons titik pesan ulang tidak cocok (titik pesan ulang bahan).')
    expect(() => parseMaterialWorkspace(good, AQ)).toThrow('(jenis bahan)')
    expect(() => parseMaterialWorkspace({ ...good, contract_version: 'cp7.fg-reorder.v1' }, FQ)).toThrow('(kontrak)')
    expect(() => parseMaterialWorkspace(withRow(0, { surprise: 1 }), FQ)).toThrow('(bahan)')
    const missing = structuredClone(good); delete (missing.page.rows[0] as Record<string, unknown>).manual_source
    expect(() => parseMaterialWorkspace(missing, FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(withRow(0, { point: 63 }), FQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(withRow(1, { manual_source: null }), FQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(withRow(1, { manual_source: 'ACCESSORY_MANUAL' }), FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(withRow(2, { lead_days: 6 }), FQ)).toThrow('(lama kirim)')
    expect(() => parseMaterialWorkspace(withRow(2, { point: 10 }), FQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(withRow(0, { point: 0, formula_point: 0 }), FQ)).toThrow('(status)')
    expect(() => parseMaterialWorkspace(withRow(0, { material_type: 'ACCESSORY' }), FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(withRow(0, { free_qty: '56' }), FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace({ ...good, counts: { ...good.counts, no_usage: 0 } }, FQ)).toThrow('(jumlah)')
    expect(() => parseMaterialWorkspace(good, { ...FQ, filter: 'MANUAL' })).toThrow('(saringan)')
    // D17-10/D17-12: NOT_SET and ESTIMATE are an accessory's only; their counts are always there and 0 for fabric, and a fabric
    // never carries the accessory numbers.
    expect(() => parseMaterialWorkspace(withRow(2, { basis: 'NOT_SET', reason: 'NO_MINIMUM_OR_ESTIMATE' }), FQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(withRow(0, { basis: 'ESTIMATE', estimate_point: 63.34 }), FQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(withRow(2, { reason: 'NO_MINIMUM_OR_ESTIMATE' }), FQ)).toThrow('(bahan)')
    for (const change of [{ moq: 5000 }, { usage_month_qty: 300 }, { buffer_days: 5 }, { estimate_point: 63.34 }])
      expect(() => parseMaterialWorkspace(withRow(0, change), FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace({ ...good, counts: { ...good.counts, items: 6, not_set: 1 } }, FQ)).toThrow('(jumlah)')
    expect(() => parseMaterialWorkspace({ ...good, counts: { ...good.counts, items: 6, estimate: 1 } }, FQ)).toThrow('(jumlah)')
    for (const key of ['not_set', 'estimate']) {
      const without: Record<string, unknown> = { ...good.counts }; delete without[key]
      expect(() => parseMaterialWorkspace({ ...good, counts: without }, FQ)).toThrow('(jumlah)')
    }

    // Accessories: MANUAL (typed), ESTIMATE (from the owner's numbers, worked out again here) or NOT_SET; never a formula or
    // cadangan; at or under exactly when stock <= minimum.
    const acc = materialWire([never(6), accessoryMinimum(7, 150), notSet(8), accessoryMinimum(9, 180), estimated(10), notSet(11, { usage_month_qty: 300, moq: 5000 }),
      accessoryMinimum(12, 100, 180, { usage_month_qty: 300, lead_days: 20, buffer_days: 5, estimate_point: 250 })], AQ)
    const accessories = parseMaterialWorkspace(acc, AQ)
    expect(accessories.page.rows.map(r => [r.name, r.basis, r.reason, r.point, r.estimatePoint, r.state, r.manualSource])).toEqual([
      ['Kancing 10', 'ESTIMATE', null, '250', '250', 'AT_OR_BELOW', null], ['Kancing 9', 'MANUAL', null, '180', null, 'AT_OR_BELOW', 'ACCESSORY_MANUAL'],
      ['Kancing 12', 'MANUAL', null, '100', '250', 'ABOVE', 'ACCESSORY_MANUAL'], ['Kancing 7', 'MANUAL', null, '150', null, 'ABOVE', 'ACCESSORY_MANUAL'],
      ['Kancing 11', 'NOT_SET', 'NO_MINIMUM_OR_ESTIMATE', null, null, 'NO_POINT', null], ['Kancing 6', 'MANUAL', null, '0', null, 'NO_POINT', 'ACCESSORY_MANUAL'],
      ['Kancing 8', 'NOT_SET', 'NO_MINIMUM_OR_ESTIMATE', null, null, 'NO_POINT', null]])
    expect(accessories.counts).toEqual({ items: 7, atOrBelow: 2, manual: 4, formula: 0, estimate: 1, notEnoughData: 0, noUsage: 0, notSet: 2 })
    expect(accessories.page.rows[0]).toMatchObject({ moq: '5000', usageMonthQty: '300', leadDays: '20', bufferDays: '5', dailyMean: '7.4667', usageQty: '224',
      formulaPoint: null, safetyQty: null })
    const accBy = (name: string, change: Record<string, unknown>) => ({ ...acc, page: { ...acc.page, rows: acc.page.rows.map(r => r.name === name ? { ...r, ...change } : r) } })
    expect(() => parseMaterialWorkspace(accBy('Kancing 6', { on_order_qty: 5 }), AQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { basis: 'FORMULA', reason: null, lead_days: 5, safety_qty: 18.5521, formula_point: 63.34, point: 63.34,
      state: 'AT_OR_BELOW' }), AQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { basis: 'NOT_ENOUGH_DATA', reason: 'NO_LEAD_TIME' }), AQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { basis: 'NO_USAGE', reason: 'NO_POSTED_USAGE_IN_WINDOW' }), AQ)).toThrow('(dasar angka)')
    // D17-12: a lama kirim is the accessory's own setting now, on any basis.
    expect(parseMaterialWorkspace(accBy('Kancing 7', { lead_days: 5 }), AQ).page.rows.find(r => r.name === 'Kancing 7')?.leadDays).toBe('5')
    expect(() => parseMaterialWorkspace(accBy('Kancing 7', { formula_point: 63.34 }), AQ)).toThrow('(batas minimum)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 7', { safety_qty: 18.5521 }), AQ)).toThrow('(batas minimum)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { reason: null }), AQ)).toThrow('(alasan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { reason: 'NO_MANUAL_MINIMUM' }), AQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 8', { point: 10, state: 'ABOVE' }), AQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 7', { state: 'AT_OR_BELOW' }), AQ)).toThrow('(status)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 9', { state: 'ABOVE' }), AQ)).toThrow('(status)')
    expect(parseMaterialWorkspace(accBy('Kancing 7', { free_qty: 150.0001 }), AQ).page.rows.find(r => r.name === 'Kancing 7')?.state).toBe('ABOVE')
    expect(() => parseMaterialWorkspace(accBy('Kancing 7', { free_qty: 149.9999 }), AQ)).toThrow('(status)')
    // The estimate: there exactly with its three numbers, equal to the owner's rule worked out here, and the point when no
    // minimum is typed.
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { buffer_days: null }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { lead_days: null }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { estimate_point: 251, point: 251 }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { point: 251 }), AQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { moq: 0 }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 10', { usage_month_qty: 0, estimate_point: 0, point: 0, state: 'NO_POINT' }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 11', { estimate_point: 250 }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 11', { lead_days: 20, buffer_days: 5 }), AQ)).toThrow('(hitungan)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 11', { lead_days: 20, buffer_days: 5, estimate_point: 250 }), AQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(accBy('Kancing 12', { estimate_point: 251 }), AQ)).toThrow('(hitungan)')
    // 500 a month with 14 + 7 days is exactly 350; a server that rounds 500 / 30 up first would answer 350,01 and is refused.
    const exact = materialWire([estimated(13, 180, 500, 14, 7)], AQ)
    expect(parseMaterialWorkspace(exact, AQ).page.rows[0]).toMatchObject({ point: '350', estimatePoint: '350' })
    expect(() => parseMaterialWorkspace({ ...exact, page: { ...exact.page, rows: [{ ...exact.page.rows[0], point: 350.01, estimate_point: 350.01 }] } }, AQ))
      .toThrow('(hitungan)')
    expect([['300', '20', '5'], ['1000', '21', '7'], ['1000', '21', '0'], ['500', '14', '7'], ['200', '10', '5'], ['0.5', '1', '0'], ['12.3456', '7.25', '0.5']]
      .map(([u, l, b]) => accessoryEstimatePoint(u, l, b))).toEqual(['250', '933.34', '700', '350', '100', '0.02', '3.19'])
    expect([moqDays('5000', '300'), moqDays('1000', '70'), moqDays('0.5', '30')]).toEqual(['500', '428', '0'])
    expect(() => parseMaterialWorkspace({ ...acc, counts: { ...acc.counts, items: 8, formula: 1 } }, AQ)).toThrow('(jumlah)')
    expect(() => parseMaterialWorkspace(acc, { ...AQ, filter: 'NOT_SET' })).toThrow('(saringan)')
    expect(() => parseMaterialWorkspace(acc, { ...AQ, filter: 'ESTIMATE' })).toThrow('(saringan)')
    for (const [filter, names] of [['NOT_SET', ['Kancing 11', 'Kancing 8']], ['ESTIMATE', ['Kancing 10']]] as const)
      expect(parseMaterialWorkspace(materialWire(acc.page.rows as MaterialWireRow[], { ...AQ, filter }), { ...AQ, filter }).page.rows.map(r => r.name)).toEqual(names)

    const payload: MaterialPayload = { material_id: materialId(1), expected_revision: 1, lead_days: '6.50', manual_point: null, reason: 'Supplier baru' }
    const evaluation = materialRow(1, 'FABRIC', { lead_days: 6.5, setting_revision: 2 })
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC').evaluation?.leadDays).toBe('6.5')
    expect(parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2 }, payload, 'FABRIC').evaluation).toBeNull()
    expect(() => parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation: { ...evaluation, lead_days: 7 } }, payload, 'FABRIC'))
      .toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 3, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
    const saveEstimate: MaterialPayload = { material_id: materialId(10), expected_revision: 1, lead_days: '20', manual_point: null, moq: '5000', usage_month_qty: '300',
      buffer_days: '5', reason: 'MOQ 5.000 pcs' }
    const estimateSaved = { ...estimated(10), setting_revision: 2 }
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(10), revision: 2, evaluation: estimateSaved }, saveEstimate, 'ACCESSORY').evaluation)
      .toMatchObject({ basis: 'ESTIMATE', point: '250', moq: '5000', usageMonthQty: '300', bufferDays: '5', leadDays: '20' })
    for (const change of [{ buffer_days: 6, estimate_point: 260, point: 260 }, { moq: 4000 }, { lead_days: 21, estimate_point: 260, point: 260 }])
      expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(10), revision: 2, evaluation: { ...estimateSaved, ...change } }, saveEstimate, 'ACCESSORY'))
        .toThrow('(hasil simpan bahan)')
    const saveMinimum: MaterialPayload = { ...saveEstimate, material_id: materialId(7), lead_days: null, manual_point: '150', moq: null, usage_month_qty: null,
      buffer_days: null }
    const minimumSaved = { ...accessoryMinimum(7, 150), setting_revision: 2 }
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(7), revision: 2, evaluation: minimumSaved }, saveMinimum, 'ACCESSORY').evaluation)
      .toMatchObject({ basis: 'MANUAL', manualPoint: '150', leadDays: null })
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(7), revision: 2, evaluation: { ...minimumSaved, manual_point: 151, point: 151 } },
      saveMinimum, 'ACCESSORY')).toThrow('(hasil simpan bahan)')
    // The form: an accessory always sends all five numbers (null when empty); a fabric only its lama kirim.
    const accessoryRow = accessories.page.rows.find(r => r.name === 'Kancing 7')!
    expect(materialPayload(accessoryRow, 'ACCESSORY', draftOf({ lead: '20', moq: '5000', usageMonth: '7,5', buffer: '0', reason: ' MOQ ' }))).toEqual({
      material_id: materialId(7), expected_revision: 1, lead_days: '20', manual_point: null, moq: '5000', usage_month_qty: '7.5', buffer_days: '0', reason: 'MOQ' })
    expect(materialPayload(accessoryRow, 'ACCESSORY', draftOf({ manual: '200' }))).toEqual({ material_id: materialId(7), expected_revision: 1, lead_days: null,
      manual_point: '200', moq: null, usage_month_qty: null, buffer_days: null, reason: 'Isian' })
    expect(Object.keys(materialPayload(parsed.page.rows[0], 'FABRIC', draftOf({ lead: '7', manual: '99' }))).sort())
      .toEqual(['expected_revision', 'lead_days', 'manual_point', 'material_id', 'reason'])
    expect(materialPayload(parsed.page.rows[0], 'FABRIC', draftOf({ lead: '7', manual: '99' }))).toMatchObject({ lead_days: '7', manual_point: null })
    expect(materialProblem('FABRIC', draftOf({ lead: '7', moq: '100' }))).toBe('Kain tidak memakai isian hitungan aksesori. Muat ulang halaman.')
    expect([draftOf({ lead: '0' }), draftOf({ moq: '0' }), draftOf({ usageMonth: '0,0000' }), draftOf({ buffer: '366' }), draftOf({ buffer: '1.234' }),
      draftOf({ manual: '-1' }), draftOf({ reason: ' ' })].map(d => materialProblem('ACCESSORY', d))).toEqual([
      'Lama kirim dari Cina: isi lebih dari 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.',
      'MOQ: isi lebih dari 0 (boleh 4 angka di belakang koma), atau kosongkan.',
      'Perkiraan pemakaian per bulan: isi lebih dari 0 (boleh 4 angka di belakang koma), atau kosongkan.',
      'Cadangan untuk kiriman telat: isi 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.',
      'Cadangan untuk kiriman telat: isi 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.',
      'Batas minimum: isi 0 atau lebih (boleh 4 angka di belakang koma), atau kosongkan untuk memakai hitungan.',
      'Tulis alasannya (1 sampai 500 huruf), misalnya "pesan minimal 5.000 pcs, kirim dari Cina 20 hari".'])
    expect(() => materialPayload(accessoryRow, 'ACCESSORY', draftOf({ buffer: '366' }))).toThrow('(isian bahan)')
    expect(materialWriteErrorText({ message: 'CP7_FORMULA_MATERIAL_INVALID' }, 'ACCESSORY', 'SAVE')).toBe('Isian belum sesuai: lama kirim dari Cina lebih dari 0 '
      + 'sampai 365 hari, MOQ dan pemakaian per bulan lebih dari 0, cadangan 0 sampai 365 hari, batas minimum 0 atau lebih (semuanya boleh kosong), dan alasan 1 '
      + 'sampai 500 huruf.')
  })

  it('shows each fabric with its numbers, basis and status in plain words, the window from the settings', async () => {
    server({ rows: [materialRow(1), minimum(2), noLead(3), fewer(4), idle(5), never(6)], run: run45 })
    await mount('FABRIC')
    const panel = field<HTMLElement>('Titik pesan ulang kain')
    expect(panel.querySelector('h2')?.textContent).toBe('Titik pesan ulang kain (safety stock)')
    expect(panel.textContent).toContain('Dihitung dari pemakaian yang sudah diposting 45 hari terakhir')
    expect(panel.textContent).toContain(`Dihitung ${wib(REORDER_RUN_AT)} (pemakaian ${formatWaDay('2026-09-05')} sampai ${formatWaDay('2026-10-19')}).`)
    // D17-10: one reminder title for fabric.
    expect(panel.textContent).toContain('muncul pengingat "Stok kain di bawah minimum" di Reminder › Pengingat sistem')
    expect(panel.textContent).not.toContain('Stok kain menipis')
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent)).toEqual(['Semua (5)', 'Menipis (2)', 'Pakai minimum (1)', 'Belum cukup data (2)'])
    const f = row('Katun 1')
    expect([chip(f), cell(f, 'free'), cell(f, 'ordered'), cell(f, 'daily'), cell(f, 'lead'), cell(f, 'point'), cell(f, 'basis')])
      .toEqual(['Menipis', '56 YD', '0 YD', '7,47 YD', '6', '63,34 YD', 'Rumus'])
    expect(f.querySelector('.cfr-formula')?.textContent).toContain('Hasil rumus: rata-rata × lama kirim + cadangan, dibulatkan ke atas = 63,34 YD.')
    const m = row('Katun 2')
    expect([chip(m), cell(m, 'point'), cell(m, 'basis')]).toEqual(['Menipis', '500 YD', 'Minimum Kain & Benchmark'])
    expect(m.textContent).toContain('Kain ini memakai angka minimum dari Master Data › Kain & Benchmark (500 YD), bukan hasil rumus: pengingat "Stok kain di bawah minimum" '
      + 'muncul bila stok di bawah angka itu.')
    expect([chip(row('Katun 3')), cell(row('Katun 3'), 'basis'), cell(row('Katun 3'), 'lead'), cell(row('Katun 3'), 'point')])
      .toEqual(['Tanpa titik', 'Belum cukup data: lama kirim belum diisi', 'belum diisi', 'belum ada'])
    expect(cell(row('Katun 4'), 'basis')).toBe('Belum cukup data: kurang dari 14 hari tercatat (baru 9 hari)')
    expect([cell(row('Katun 5'), 'basis'), cell(row('Katun 5'), 'daily')]).toEqual(['Belum ada pemakaian 45 hari terakhir', 'belum ada'])
    expect(container.textContent).not.toContain('Kancing')
    for (const word of ['NaN', 'undefined', 'null', 'CP7_', 'NOT_ENOUGH_DATA', 'FABRIC_MINIMUM']) expect(panel.textContent).not.toContain(word)
  })

  it('lets the Owner set a fabric lead time (no manual number for fabric); a lost reply is sent again with the same id', async () => {
    const fake = server({ rows: [materialRow(1), noLead(3)], lose: new Set(['erp_cp7_save_material_reorder_v1']) })
    await mount('FABRIC')
    await click('Atur lama kirim', row('Katun 1'))
    let item = row('Katun 1')
    expect(field<HTMLInputElement>('Lama kirim (hari)', item).value).toBe('6')
    expect(item.querySelector('[aria-label="Angka manual"]')).toBeNull(); expect(item.querySelector('[aria-label^="Batas minimum"]')).toBeNull()
    expect(item.textContent).toContain('Referensi minimum lama: belum tersedia (baca saja).')
    expect(field<HTMLSelectElement>('Aturan kain yang akan dipakai',item).value).toBe('')
    expect(field<HTMLSelectElement>('Aturan kain yang akan dipakai',item).querySelector('option[value="LEGACY_MINIMUM"]')?.hasAttribute('disabled')).toBe(true)
    expect(item.textContent).toContain('Belum ada yang diubah.')
    for (const bad of ['0', '366', '6.555', 'enam']) {
      await type('Lama kirim (hari)', bad, item)
      expect(item.textContent).toContain('Lama kirim: isi lebih dari 0 sampai 365 hari')
      expect(button('Simpan', item).disabled).toBe(true)
    }
    await type('Lama kirim (hari)', '6,5', item)
    expect(item.textContent).toContain('Tulis alasannya'); expect(button('Simpan', item).disabled).toBe(true)
    await type('Alasan perubahan bahan', '  Supplier baru ', item)
    await click('Simpan', item)
    expect(row('Katun 1').textContent).toContain('Jawaban server tidak sampai, jadi belum pasti lama kirim kain ini tersimpan.')
    await click('Simpan', row('Katun 1'))
    const saves = calls(fake, 'erp_cp7_save_material_reorder_v1')
    expect(saves).toHaveLength(2)
    expect(saves[0]).toEqual({ p_payload: { material_id: materialId(1), expected_revision: 1, lead_days: '6.5', manual_point: null, reason: 'Supplier baru' },
      p_request: expect.stringMatching(/^[0-9a-f-]{36}$/) })
    expect(saves[1]).toEqual(saves[0])
    item = row('Katun 1')
    expect(item.textContent).toContain('Tersimpan (revisi 2): lama kirim 6,5 hari. Permintaan ini ternyata sudah tersimpan sebelumnya.')
    expect(cell(item, 'lead')).toBe('6,5')
    // A fabric without lead time: filled in, it is on the formula.
    await click('Atur lama kirim', row('Katun 3'))
    await type('Lama kirim (hari)', '6', row('Katun 3')); await type('Alasan perubahan bahan', 'Lama kirim dari supplier', row('Katun 3'))
    await click('Simpan', row('Katun 3'))
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[2].p_payload).toEqual({ material_id: materialId(3), expected_revision: 0, lead_days: '6',
      manual_point: null, reason: 'Lama kirim dari supplier' })
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[2].p_request).not.toBe(saves[0].p_request)
    expect([cell(row('Katun 3'), 'basis'), chip(row('Katun 3'))]).toEqual(['Rumus', 'Menipis'])
  })

  it('works an accessory minimum out from the owner\u2019s numbers, lets a typed minimum win, and shows the ERP usage for comparison (D17-12)', async () => {
    const fake = server({ rows: [never(6), accessoryMinimum(7, 150), notSet(8, { usage_month_qty: 300 }), notSet(9, { usage_qty: 0, counted_days: 0, use_days: 0,
      daily_mean: null, daily_sd: null }), estimated(10)] })
    await mount('ACCESSORY')
    const panel = field<HTMLElement>('Batas minimum aksesori')
    expect(panel.querySelector('h2')?.textContent).toBe('Batas minimum aksesori')
    expect(panel.textContent).toContain('Aksesori memakai batas minimum, bukan rumus. Aplikasi menghitungnya dari isian per aksesori: (perkiraan pemakaian per bulan '
      + '÷ 30) × (lama kirim dari Cina + cadangan untuk kiriman telat), dibulatkan ke atas. Batas minimum yang diketik langsung menggantikan hitungan.')
    expect(panel.textContent).toContain('Pengingat "Stok aksesori menipis" muncul di Reminder › Pengingat sistem kalau stok di gudang sama dengan atau di bawah batas minimum')
    expect(panel.textContent).toContain('MOQ hanya untuk pesanan, tidak mengubah batas minimum. Pemakaian nyata per hari (30 hari terakhir, dari nota mandor dan '
      + 'pemakaian pabrik) hanya pembanding, tidak dipakai dalam hitungan.')
    for (const word of ['ingkat layanan', 'Titik pesan ulang', 'titik pesan ulang', 'safety stock', 'Rincian rumus', 'Angka manual', 'NOT_SET', 'ESTIMATE', 'null',
      'undefined', 'NaN']) expect(panel.textContent).not.toContain(word)
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent))
      .toEqual(['Semua (5)', 'Menipis (1)', 'Diketik manual (2)', 'Dari hitungan (1)', 'Belum diisi (2)'])
    const lines = (r: HTMLElement) => [...r.querySelectorAll('[data-cmr="estimate"] p')].map(x => x.textContent)
    const est = row('Kancing 10')
    expect([chip(est), cell(est, 'free'), cell(est, 'daily'), cell(est, 'estimate-daily'), cell(est, 'point'), cell(est, 'basis')])
      .toEqual(['Menipis', '180 PCS', '7,47 PCS', '10 PCS', '250 PCS', 'Dari isian hitungan'])
    expect([...est.querySelectorAll('dt')].map(d => d.textContent)).toEqual(['Stok di gudang', 'Pemakaian nyata per hari (30 hari terakhir)',
      'Perkiraan pemakaian per hari (isian)', 'Batas minimum', 'Asal angka'])
    expect(cell(est, 'inputs')).toBe('Isian: MOQ 5.000 PCS · lama kirim dari Cina 20 hari · pemakaian per bulan 300 PCS · cadangan 5 hari.')
    expect(lines(est)).toEqual(['Batas minimum hitungan: (pemakaian per bulan ÷ 30) × (lama kirim + cadangan) = (300 ÷ 30) × (20 + 5) = 250 PCS.',
      'MOQ cukup untuk sekitar 500 hari (menurut perkiraan pemakaian per bulan).'])
    expect([est.querySelector('[data-cmr="ordered"]'), est.querySelector('[data-cmr="lead"]'), est.querySelector('.cfr-formula')]).toEqual([null, null, null])
    expect([cell(row('Kancing 7'), 'basis'), chip(row('Kancing 7'))]).toEqual(['Diketik manual', 'Aman'])
    expect(lines(row('Kancing 7'))).toEqual(['Batas minimum hitungan belum bisa dihitung: perkiraan pemakaian per bulan, lama kirim dari Cina dan cadangan untuk '
      + 'kiriman telat belum diisi.', 'Batas minimum yang diketik (150 PCS) dipakai, bukan hitungan.'])
    expect([chip(row('Kancing 8')), cell(row('Kancing 8'), 'point'), cell(row('Kancing 8'), 'basis'), cell(row('Kancing 8'), 'estimate-daily')])
      .toEqual(['Tidak diingatkan', 'belum diisi', 'Belum diisi', '10 PCS'])
    expect(lines(row('Kancing 8'))).toEqual(['Batas minimum hitungan belum bisa dihitung: lama kirim dari Cina dan cadangan untuk kiriman telat belum diisi.'])
    expect([cell(row('Kancing 9'), 'daily'), cell(row('Kancing 9'), 'estimate-daily')]).toEqual(['belum ada pemakaian', 'belum diisi'])
    expect(cell(row('Kancing 6'), 'basis')).toBe('Diketik manual 0: tidak pernah diingatkan')

    // The owner fills the three numbers and the MOQ of Kancing 8: the minimum is worked out while typing, then saved.
    await click('Atur batas minimum', row('Kancing 8'))
    let item = row('Kancing 8')
    const draftLines = () => [...row('Kancing 8').querySelectorAll('[data-cmr="draft-estimate"] p')].map(x => x.textContent)
    expect(item.querySelector('fieldset legend')?.textContent).toBe('Batas minimum')
    expect(['MOQ (PCS)', 'Lama kirim dari Cina (hari)', 'Perkiraan pemakaian per bulan (PCS)', 'Cadangan untuk kiriman telat (hari)', 'Batas minimum (PCS)']
      .map(label => field<HTMLInputElement>(label, item).value)).toEqual(['', '', '300', '', ''])
    expect(item.textContent).toContain('Pemakaian nyata dari ERP: 7,47 PCS per hari (30 hari terakhir), hanya pembanding.')
    expect(item.textContent).toContain('Kalau diketik, angka ini dipakai dan menggantikan hitungan. Kosong = pakai hitungan. 0 = tidak pernah diingatkan.')
    expect(item.textContent).toContain('Belum ada yang diubah.')
    expect(draftLines()).toEqual(['Batas minimum hitungan belum bisa dihitung: lama kirim dari Cina dan cadangan untuk kiriman telat belum diisi.'])
    for (const [label, bad, good, words] of [['Lama kirim dari Cina (hari)', '0', '20', 'Lama kirim dari Cina: isi lebih dari 0'],
      ['Cadangan untuk kiriman telat (hari)', '366', '5', 'Cadangan untuk kiriman telat: isi 0 sampai 365 hari'],
      ['Perkiraan pemakaian per bulan (PCS)', '0', '300', 'Perkiraan pemakaian per bulan: isi lebih dari 0'], ['MOQ (PCS)', '0', '5000', 'MOQ: isi lebih dari 0']]) {
      await type(label, bad, item)
      expect(row('Kancing 8').textContent).toContain(words); expect(button('Simpan', row('Kancing 8')).disabled).toBe(true)
      await type(label, good, row('Kancing 8'))
    }
    expect(draftLines()).toEqual(['Batas minimum hitungan: (pemakaian per bulan ÷ 30) × (lama kirim + cadangan) = (300 ÷ 30) × (20 + 5) = 250 PCS.',
      'MOQ cukup untuk sekitar 500 hari (menurut perkiraan pemakaian per bulan).'])
    await type('Cadangan untuk kiriman telat (hari)', '5,555', row('Kancing 8'))
    expect(draftLines()).toEqual(['Batas minimum hitungan belum bisa dihitung: periksa isian yang belum sesuai.',
      'MOQ cukup untuk sekitar 500 hari (menurut perkiraan pemakaian per bulan).'])
    await type('Cadangan untuk kiriman telat (hari)', '5', row('Kancing 8'))
    await type('Alasan perubahan bahan', 'MOQ dan lama kirim dari Cina', row('Kancing 8'))
    await click('Simpan', row('Kancing 8'))
    const saves = () => calls(fake, 'erp_cp7_save_material_reorder_v1').map(c => c.p_payload as MaterialPayload)
    expect(saves()[0]).toEqual({ material_id: materialId(8), expected_revision: 0, lead_days: '20', manual_point: null, moq: '5000', usage_month_qty: '300',
      buffer_days: '5', reason: 'MOQ dan lama kirim dari Cina' })
    item = row('Kancing 8')
    expect(item.textContent).toContain('Tersimpan (revisi 1): batas minimum dari hitungan 250 PCS.')
    expect([chip(item), cell(item, 'point'), cell(item, 'basis')]).toEqual(['Menipis', '250 PCS', 'Dari isian hitungan'])
    expect(cell(item, 'inputs')).toBe('Isian: MOQ 5.000 PCS · lama kirim dari Cina 20 hari · pemakaian per bulan 300 PCS · cadangan 5 hari.')
    // A typed minimum wins over the hitungan; the numbers stay.
    await click('Atur batas minimum', item)
    await type('Batas minimum (PCS)', '40', row('Kancing 8'))
    expect(draftLines()).toContain('Batas minimum yang diketik (40 PCS) dipakai, bukan hitungan.')
    await type('Alasan perubahan bahan', 'Sementara pakai angka sendiri', row('Kancing 8'))
    await click('Simpan', row('Kancing 8'))
    expect(saves()[1]).toEqual({ material_id: materialId(8), expected_revision: 1, lead_days: '20', manual_point: '40', moq: '5000', usage_month_qty: '300',
      buffer_days: '5', reason: 'Sementara pakai angka sendiri' })
    item = row('Kancing 8')
    expect(item.textContent).toContain('Tersimpan (revisi 2): batas minimum diketik 40 PCS.')
    expect([chip(item), cell(item, 'point'), cell(item, 'basis')]).toEqual(['Aman', '40 PCS', 'Diketik manual'])
    expect(lines(item)).toContain('Batas minimum yang diketik (40 PCS) dipakai, bukan hitungan.')
    // Emptied: no typed minimum and no numbers, so no reminder.
    await click('Atur batas minimum', row('Kancing 6'))
    expect(field<HTMLInputElement>('Batas minimum (PCS)', row('Kancing 6')).value).toBe('0')
    await type('Batas minimum (PCS)', '', row('Kancing 6')); await type('Alasan perubahan bahan', 'Belum tahu MOQ', row('Kancing 6'))
    await click('Simpan', row('Kancing 6'))
    expect(saves()[2]).toEqual({ material_id: materialId(6), expected_revision: 1, lead_days: null, manual_point: null, moq: null, usage_month_qty: null,
      buffer_days: null, reason: 'Belum tahu MOQ' })
    item = row('Kancing 6')
    expect(item.textContent).toContain('Tersimpan (revisi 2): batas minimum belum ada (isian hitungan belum lengkap), jadi tidak diingatkan.')
    expect([chip(item), cell(item, 'point'), cell(item, 'basis')]).toEqual(['Tidak diingatkan', 'belum diisi', 'Belum diisi'])
    // Every accessory save carries all five numbers; "Dari hitungan" asks the server for ESTIMATE.
    for (const payload of saves()) expect(Object.keys(payload).sort()).toEqual(['buffer_days', 'expected_revision', 'lead_days', 'manual_point', 'material_id',
      'moq', 'reason', 'usage_month_qty'])
    await click('Dari hitungan')
    expect((calls(fake, 'erp_cp7_get_material_reorder_v1').at(-1)?.p_query as MaterialQuery).filter).toBe('ESTIMATE')
    expect([...container.querySelectorAll('article.cfr-row')].map(a => a.querySelector('h3')?.textContent)).toEqual(['Kancing 10'])
  })

  it('shows a viewer the numbers without any edit control', async () => {
    const fake = server({ canManage: false, rows: [never(6), accessoryMinimum(7, 150), estimated(10)] })
    auth.current = as('GUDANG', ['warehouse.accessory.view'])
    await mount('ACCESSORY')
    expect(chip(row('Kancing 7'))).toBe('Aman')
    // The owner's numbers and the hitungan are shown to everyone who may read the screen.
    expect(cell(row('Kancing 10'), 'inputs')).toBe('Isian: MOQ 5.000 PCS · lama kirim dari Cina 20 hari · pemakaian per bulan 300 PCS · cadangan 5 hari.')
    expect(row('Kancing 10').textContent).toContain('= (300 ÷ 30) × (20 + 5) = 250 PCS.')
    expect([...container.querySelectorAll('button')].some(b => b.textContent?.startsWith('Atur'))).toBe(false)
    expect(container.querySelectorAll('input:not([aria-label="Cari aksesori untuk batas minimum"])')).toHaveLength(0)
    expect(button('Hitung sekarang').disabled).toBe(false)
    expect(fake.calls.map(c => c[0])).toEqual(['erp_cp7_get_material_reorder_v1'])
    expect(fake.calls[0][1]).toEqual({ p_query: AQ })
  })

  it('shows nothing and calls nothing without the screens’ read permissions', async () => {
    const fake = server()
    auth.current = as('GUDANG', ['warehouse.material.view'])
    await mount('FABRIC')
    expect(container.innerHTML).toBe(''); expect(fake.calls).toHaveLength(0)
    auth.current = as('GUDANG', ['warehouse.material.view', 'master.fabric.view'])
    await mount('ACCESSORY')
    expect(container.innerHTML).toBe(''); expect(fake.calls).toHaveLength(0)
  })

  it('says a busy calculation, a stale lead time and a mismatching answer in plain words, never as zero', async () => {
    const fake = server({ busy: true })
    await mount('FABRIC')
    await click('Hitung sekarang')
    expect(container.querySelector('[role="alert"]')?.textContent).toBe('Titik pesan ulang sedang dihitung oleh server. Coba lagi sebentar (sekitar satu menit).')
    fake.busy = false
    await click('Hitung sekarang')
    expect(calls(fake, 'erp_cp7_refresh_material_reorder_v1')).toEqual([{ p_material_type: 'FABRIC' }, { p_material_type: 'FABRIC' }])
    expect(container.textContent).toContain(`Selesai dihitung ${wib(LATER)}: 1 kain dan aksesori, 1 menipis.`)
    fake.rows[0] = { ...fake.rows[0], setting_revision: 4 }
    await click('Atur lama kirim', row('Katun 1'))
    await type('Lama kirim (hari)', '7', row('Katun 1')); await type('Alasan perubahan bahan', 'Cek', row('Katun 1'))
    await click('Simpan', row('Katun 1'))
    expect(row('Katun 1').textContent).toContain('Lama kirim kain ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
    expect(container.textContent).not.toContain('CP7_FORMULA')
    fake.corrupt = true
    await click('Muat ulang titik pesan ulang kain')
    expect(container.querySelector('[role="alert"]')?.textContent).toBe('Respons titik pesan ulang tidak cocok (titik pesan ulang).')
    expect(container.querySelector('article.cfr-row')).toBeNull()
  })

  it('says a stale accessory minimum in its own words', async () => {
    const fake = server({ rows: [accessoryMinimum(7, 150)] })
    await mount('ACCESSORY')
    fake.rows[0] = { ...fake.rows[0], setting_revision: 3 }
    await click('Atur batas minimum', row('Kancing 7'))
    await type('Batas minimum (PCS)', '200', row('Kancing 7')); await type('Alasan perubahan bahan', 'MOQ', row('Kancing 7'))
    await click('Simpan', row('Kancing 7'))
    expect(row('Kancing 7').textContent).toContain('Isian batas minimum aksesori ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
    expect(container.textContent).not.toContain('CP7_FORMULA')
  })

  it('never lets a late answer replace a newer one', async () => {
    let release: (x: unknown) => void = () => {}
    const fake = server({ rows: [materialRow(1), minimum(2)] })
    const answer = client.rpc.getMockImplementation()!
    client.rpc.mockImplementationOnce((name: string, args: Record<string, unknown>) => { fake.calls.push([name, structuredClone(args)]); return new Promise(r => { release = r }) })
    await mount('FABRIC')
    client.rpc.mockImplementation(answer)
    await click('Pakai minimum')
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(1)
    await act(async () => release({ data: materialWire(fake.rows, FQ), error: null })); await settle()
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(1)
    expect(cell(row('Katun 2'), 'basis')).toBe('Minimum Kain & Benchmark')
    expect(container.querySelector('[role="alert"]')).toBeNull()
  })

  it('is on Master Data › Kain & Benchmark and Aksesori & Harga Mandor too, outside the light master screen', async () => {
    const fake = server({ rows: [materialRow(1), accessoryMinimum(7, 150)] })
    const answer = client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => name.startsWith('erp_cp7_') && name.includes('material_reorder')
      ? answer(name, args) : { data: null, error: { message: 'not in this test' } })
    auth.current = as('OWNER', [...PERMS, 'master.fabric.view', 'master.accessory.view'])
    await act(async () => root.render(<ConnectedMasterPage view="master-fabric"/>)); await settle()
    const fabricPanel = field<HTMLElement>('Titik pesan ulang kain')
    expect(fabricPanel.closest('.cmd-page')).toBeNull()
    expect(row('Katun 1').textContent).toContain('Atur lama kirim')
    await act(async () => root.render(<ConnectedMasterPage view="master-accessory"/>)); await settle()
    expect(container.querySelector('[aria-label="Titik pesan ulang kain"]')).toBeNull()
    expect(field<HTMLElement>('Batas minimum aksesori').closest('.cmd-page')).toBeNull()
    expect(row('Kancing 7').textContent).toContain('Atur batas minimum')
    expect(calls(fake, 'erp_cp7_get_material_reorder_v1').map(a => (a.p_query as MaterialQuery).material_type)).toEqual(['FABRIC', 'ACCESSORY'])
  })
})
