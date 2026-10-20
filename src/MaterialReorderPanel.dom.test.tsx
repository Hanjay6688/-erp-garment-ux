// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MaterialReorderPanel from './MaterialReorderPanel'
import ConnectedMasterPage from './ConnectedMasterPage'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import {
  materialPayload, materialProblem, materialWriteErrorText, parseMaterialSaveResult, parseMaterialWorkspace, type MaterialPayload, type MaterialQuery,
} from './materialReorderContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { REORDER_RUN_AT, reorderRun } from '../tests/fixtures/fgReorder'
import { materialId, materialRow, materialWire, type MaterialWireRow } from '../tests/fixtures/materialReorder'

// SS-2/SS-3 and owner D17-10: Titik pesan ulang of fabric and Batas minimum of accessories against a fake of the three public
// RPCs of scripts/cp7-src/stock-formula/materials.sql that keeps their rules (Owner/Admin to change, a fabric has no manual
// number, an accessory no lama kirim and no formula, revision check, one answer per request id, busy refresh).
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
// compute_materials(): a fabric on its minimum or the formula; an accessory (D17-10) on its manual minimum only, at or under it
// when the stock in the warehouse is not above it.
function recompute(r: MaterialWireRow): MaterialWireRow {
  if (r.material_type === 'ACCESSORY') {
    const point = r.manual_point as number | null
    return { ...r, basis: point === null ? 'NOT_SET' : 'MANUAL', reason: point === null ? 'NO_MANUAL_MINIMUM' : null, point, lead_days: null, safety_qty: null,
      formula_point: null, state: point === null || point <= 0 ? 'NO_POINT' : Number(r.free_qty) <= point ? 'AT_OR_BELOW' : 'ABOVE' }
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
      // save_material: a fabric has no manual number, an accessory no lama kirim (D17-10).
      if ((!accessory && p.manual_point !== null) || (accessory && p.lead_days !== null)) return refuse('22023', 'CP7_FORMULA_MATERIAL_INVALID')
      if (p.expected_revision !== ((fake.rows[i].setting_revision as number | null) ?? 0)) return refuse('40001', 'CP7_FORMULA_MATERIAL_STALE')
      const revision = p.expected_revision + 1
      const next = recompute({ ...fake.rows[i], setting_revision: revision, lead_days: p.lead_days === null ? null : Number(p.lead_days),
        ...(accessory ? { manual_point: p.manual_point === null ? null : Number(p.manual_point), manual_source: p.manual_point === null ? null : 'ACCESSORY_MANUAL' } : {}) })
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
// Accessories (D17-10): a minimum entered by hand (MANUAL) or none yet (NOT_SET); never a lama kirim or a formula.
const accessoryMinimum = (n: number, point: number, free = 180) => materialRow(n, 'ACCESSORY', { free_qty: free, setting_revision: 1, manual_point: point,
  manual_source: 'ACCESSORY_MANUAL', point, basis: 'MANUAL', reason: null, state: point <= 0 ? 'NO_POINT' : free <= point ? 'AT_OR_BELOW' : 'ABOVE' })
const never = (n: number) => accessoryMinimum(n, 0)
const notSet = (n: number, extra: Record<string, unknown> = {}) => materialRow(n, 'ACCESSORY', extra)
const run45 = reorderRun({ window_from: '2026-09-05', window_through: '2026-10-19', window_days: 45 })

describe('Titik pesan ulang of fabric and Batas minimum of accessories (SS-2/SS-3, D17-10)', () => {
  it('parses the exact server shapes and refuses unknown, missing and impossible facts', () => {
    const good = materialWire([materialRow(1), minimum(2), noLead(3), fewer(4), idle(5), never(6), accessoryMinimum(7, 150)], FQ)
    const parsed = parseMaterialWorkspace(good, FQ)
    expect(parsed.page.rows.map(r => r.name)).toEqual(['Katun 1', 'Katun 2', 'Katun 3', 'Katun 4', 'Katun 5'])
    expect(parsed.page.rows[0]).toMatchObject({ freeQty: '56', onOrderQty: '0', dailyMean: '7.4667', leadDays: '6', settingRevision: 1, point: '63.34',
      formulaPoint: '63.34', basis: 'FORMULA', unitCode: 'YD', state: 'AT_OR_BELOW' })
    expect(parsed.counts).toEqual({ items: 5, atOrBelow: 2, manual: 1, formula: 1, notEnoughData: 2, noUsage: 1, notSet: 0 })
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
    // D17-10: NOT_SET is an accessory's only; the count is always there and 0 for fabric.
    expect(() => parseMaterialWorkspace(withRow(2, { basis: 'NOT_SET', reason: 'NO_MANUAL_MINIMUM' }), FQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(withRow(2, { reason: 'NO_MANUAL_MINIMUM' }), FQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace({ ...good, counts: { ...good.counts, items: 6, not_set: 1 } }, FQ)).toThrow('(jumlah)')
    const noNotSet: Record<string, unknown> = { ...good.counts }; delete noNotSet.not_set
    expect(() => parseMaterialWorkspace({ ...good, counts: noNotSet }, FQ)).toThrow('(jumlah)')

    // Accessories: MANUAL or NOT_SET, never a lama kirim, cadangan or formula number; at or under exactly when stock <= minimum.
    const acc = materialWire([never(6), accessoryMinimum(7, 150), notSet(8), accessoryMinimum(9, 180)], AQ)
    const accessories = parseMaterialWorkspace(acc, AQ)
    expect(accessories.page.rows.map(r => [r.name, r.basis, r.reason, r.point, r.state, r.manualSource])).toEqual([
      ['Kancing 9', 'MANUAL', null, '180', 'AT_OR_BELOW', 'ACCESSORY_MANUAL'], ['Kancing 7', 'MANUAL', null, '150', 'ABOVE', 'ACCESSORY_MANUAL'],
      ['Kancing 6', 'MANUAL', null, '0', 'NO_POINT', 'ACCESSORY_MANUAL'], ['Kancing 8', 'NOT_SET', 'NO_MANUAL_MINIMUM', null, 'NO_POINT', null]])
    expect(accessories.counts).toEqual({ items: 4, atOrBelow: 1, manual: 3, formula: 0, notEnoughData: 0, noUsage: 0, notSet: 1 })
    expect(accessories.page.rows[3]).toMatchObject({ dailyMean: '7.4667', usageQty: '224', countedDays: 30, leadDays: null, formulaPoint: null, safetyQty: null })
    const accRow = (i: number, change: Record<string, unknown>) => ({ ...acc, page: { ...acc.page, rows: acc.page.rows.map((r, j) => j === i ? { ...r, ...change } : r) } })
    expect(() => parseMaterialWorkspace(accRow(0, { on_order_qty: 5 }), AQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(accRow(3, { basis: 'FORMULA', reason: null, lead_days: 5, safety_qty: 18.5521, formula_point: 63.34, point: 63.34,
      state: 'AT_OR_BELOW' }), AQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(accRow(3, { basis: 'NOT_ENOUGH_DATA', reason: 'NO_LEAD_TIME' }), AQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(accRow(3, { basis: 'NO_USAGE', reason: 'NO_POSTED_USAGE_IN_WINDOW' }), AQ)).toThrow('(dasar angka)')
    expect(() => parseMaterialWorkspace(accRow(1, { lead_days: 5 }), AQ)).toThrow('(batas minimum)')
    expect(() => parseMaterialWorkspace(accRow(1, { formula_point: 63.34 }), AQ)).toThrow('(batas minimum)')
    expect(() => parseMaterialWorkspace(accRow(1, { safety_qty: 18.5521 }), AQ)).toThrow('(batas minimum)')
    expect(() => parseMaterialWorkspace(accRow(3, { reason: null }), AQ)).toThrow('(alasan)')
    expect(() => parseMaterialWorkspace(accRow(3, { reason: 'NO_LEAD_TIME' }), AQ)).toThrow('(bahan)')
    expect(() => parseMaterialWorkspace(accRow(3, { point: 10, state: 'ABOVE' }), AQ)).toThrow('(titik pesan ulang)')
    expect(() => parseMaterialWorkspace(accRow(1, { state: 'AT_OR_BELOW' }), AQ)).toThrow('(status)')
    expect(() => parseMaterialWorkspace(accRow(0, { state: 'ABOVE' }), AQ)).toThrow('(status)')
    expect(parseMaterialWorkspace(accRow(1, { free_qty: 150.0001 }), AQ).page.rows[1].state).toBe('ABOVE')
    expect(() => parseMaterialWorkspace(accRow(1, { free_qty: 149.9999 }), AQ)).toThrow('(status)')
    expect(() => parseMaterialWorkspace({ ...acc, counts: { ...acc.counts, items: 5, formula: 1 } }, AQ)).toThrow('(jumlah)')
    expect(() => parseMaterialWorkspace(acc, { ...AQ, filter: 'NOT_SET' })).toThrow('(saringan)')
    expect(parseMaterialWorkspace(materialWire(acc.page.rows as MaterialWireRow[], { ...AQ, filter: 'NOT_SET' }), { ...AQ, filter: 'NOT_SET' }).page.rows
      .map(r => r.name)).toEqual(['Kancing 8'])

    const payload: MaterialPayload = { material_id: materialId(1), expected_revision: 1, lead_days: '6.50', manual_point: null, reason: 'Supplier baru' }
    const evaluation = materialRow(1, 'FABRIC', { lead_days: 6.5, setting_revision: 2 })
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC').evaluation?.leadDays).toBe('6.5')
    expect(parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2 }, payload, 'FABRIC').evaluation).toBeNull()
    expect(() => parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation: { ...evaluation, lead_days: 7 } }, payload, 'FABRIC'))
      .toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 3, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
    const saveMinimum: MaterialPayload = { material_id: materialId(7), expected_revision: 1, lead_days: null, manual_point: '150', reason: 'MOQ 1.000 pcs' }
    const minimumEval = accessoryMinimum(7, 150), minimumSaved = { ...minimumEval, setting_revision: 2 }
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(7), revision: 2, evaluation: minimumSaved }, saveMinimum, 'ACCESSORY').evaluation)
      .toMatchObject({ basis: 'MANUAL', manualPoint: '150', leadDays: null })
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(7), revision: 2, evaluation: { ...minimumSaved, manual_point: 151, point: 151 } },
      saveMinimum, 'ACCESSORY')).toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(7), revision: 2, evaluation: { ...minimumSaved, lead_days: 5 } },
      saveMinimum, 'ACCESSORY')).toThrow('(batas minimum)')
    // The form never sends a lama kirim for an accessory, and says why if one is ever in the draft.
    const accessoryRow = accessories.page.rows[1]
    expect(materialPayload(accessoryRow, 'ACCESSORY', { lead: '', manual: '200', reason: ' MOQ ' })).toEqual({ material_id: materialId(7), expected_revision: 1,
      lead_days: null, manual_point: '200', reason: 'MOQ' })
    expect(materialProblem('ACCESSORY', { lead: '5', manual: '200', reason: 'MOQ' })).toBe('Aksesori tidak memakai lama kirim. Muat ulang halaman lalu isi batas minimumnya saja.')
    expect(() => materialPayload(accessoryRow, 'ACCESSORY', { lead: '5', manual: '200', reason: 'MOQ' })).toThrow('(isian bahan)')
    expect(materialPayload(parsed.page.rows[0], 'FABRIC', { lead: '7', manual: '99', reason: 'x' })).toMatchObject({ lead_days: '7', manual_point: null })
    expect(materialWriteErrorText({ message: 'CP7_FORMULA_MATERIAL_INVALID' }, 'ACCESSORY', 'SAVE'))
      .toBe('Isian belum sesuai: batas minimum 0 atau lebih, atau kosong, dan alasan 1 sampai 500 huruf. Aksesori tidak memakai lama kirim.')
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
    expect(item.textContent).toContain('Angka minimum diatur di Master Data › Kain & Benchmark.')
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

  it('lets the Owner set an accessory batas minimum (0 = never, empty = not set), never a lama kirim or a formula (D17-10)', async () => {
    const fake = server({ rows: [never(6), accessoryMinimum(7, 150), notSet(8), notSet(9, { usage_qty: 0, counted_days: 0, use_days: 0, daily_mean: null,
      daily_sd: null })] })
    await mount('ACCESSORY')
    const panel = field<HTMLElement>('Batas minimum aksesori')
    expect(panel.querySelector('h2')?.textContent).toBe('Batas minimum aksesori')
    expect(panel.textContent).toContain('Aksesori memakai batas minimum yang diisi manual, bukan rumus. Pengingat "Stok aksesori menipis" muncul di Reminder › '
      + 'Pengingat sistem kalau stok di gudang sama dengan atau di bawah batas minimum')
    expect(panel.textContent).toContain('0 berarti tidak pernah diingatkan; kosong berarti belum diisi, jadi juga tidak diingatkan.')
    expect(panel.textContent).toContain('Stok di pos servis, area periksa dan area rusak tidak dihitung sebagai stok di gudang.')
    for (const word of ['ama kirim', 'adangan', 'ingkat layanan', 'Titik pesan ulang', 'titik pesan ulang', 'safety stock', 'Rincian rumus', 'Angka manual', 'NOT_SET', 'null'])
      expect(panel.textContent).not.toContain(word)
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent)).toEqual(['Semua (4)', 'Menipis (0)', 'Sudah diisi (2)', 'Belum diisi (2)'])
    const zero = row('Kancing 6')
    expect([chip(zero), cell(zero, 'free'), cell(zero, 'daily'), cell(zero, 'point'), cell(zero, 'basis')])
      .toEqual(['Tidak diingatkan', '180 PCS', '7,47 PCS', '0 PCS', 'Manual 0: tidak pernah diingatkan'])
    expect([...zero.querySelectorAll('dt')].map(d => d.textContent)).toEqual(['Stok di gudang', 'Pemakaian rata-rata per hari (30 hari terakhir)', 'Batas minimum', 'Diisi'])
    expect([zero.querySelector('[data-cmr="ordered"]'), zero.querySelector('[data-cmr="lead"]'), zero.querySelector('.cfr-formula')]).toEqual([null, null, null])
    expect([chip(row('Kancing 7')), cell(row('Kancing 7'), 'free'), cell(row('Kancing 7'), 'point'), cell(row('Kancing 7'), 'basis')])
      .toEqual(['Aman', '180 PCS', '150 PCS', 'Manual'])
    expect([chip(row('Kancing 8')), cell(row('Kancing 8'), 'point'), cell(row('Kancing 8'), 'basis')]).toEqual(['Tidak diingatkan', 'belum diisi', 'Belum diisi'])
    expect(cell(row('Kancing 9'), 'daily')).toBe('belum ada pemakaian')
    // A minimum above the stock: the accessory is at or under it.
    await click('Atur batas minimum', row('Kancing 8'))
    let item = row('Kancing 8')
    expect(item.querySelector('fieldset legend')?.textContent).toBe('Batas minimum')
    expect(field<HTMLInputElement>('Batas minimum (PCS)', item).value).toBe('')
    expect(item.querySelector('[aria-label="Lama kirim (hari)"]')).toBeNull()
    expect(item.textContent).toContain('0 = tidak pernah diingatkan, kosong = belum diisi (tidak diingatkan).')
    expect(item.textContent).toContain('Belum ada yang diubah.')
    for (const bad of ['-3', '1.23456', 'sepuluh']) {
      await type('Batas minimum (PCS)', bad, item)
      expect(item.textContent).toContain('Batas minimum: isi 0 atau lebih (boleh 4 angka di belakang koma), atau kosongkan.')
      expect(button('Simpan', item).disabled).toBe(true)
    }
    await type('Batas minimum (PCS)', '60,5', item)
    expect(item.textContent).toContain('misalnya "pesan minimal 1.000 pcs, kirim dari Cina 30 hari"')
    await type('Alasan perubahan bahan', 'MOQ dari Cina', item)
    await click('Simpan', item)
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[0].p_payload).toEqual({ material_id: materialId(8), expected_revision: 0, lead_days: null,
      manual_point: '60.5', reason: 'MOQ dari Cina' })
    item = row('Kancing 8')
    expect(item.textContent).toContain('Tersimpan (revisi 1): batas minimum 60,5 PCS.')
    expect([chip(item), cell(item, 'point'), cell(item, 'basis')]).toEqual(['Menipis', '60,5 PCS', 'Manual'])
    // Emptied: not set, never reminded.
    await click('Atur batas minimum', row('Kancing 6'))
    expect(field<HTMLInputElement>('Batas minimum (PCS)', row('Kancing 6')).value).toBe('0')
    await type('Batas minimum (PCS)', '', row('Kancing 6')); await type('Alasan perubahan bahan', 'Belum tahu MOQ', row('Kancing 6'))
    await click('Simpan', row('Kancing 6'))
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[1].p_payload).toEqual({ material_id: materialId(6), expected_revision: 1, lead_days: null,
      manual_point: null, reason: 'Belum tahu MOQ' })
    item = row('Kancing 6')
    expect(item.textContent).toContain('Tersimpan (revisi 2): batas minimum dikosongkan (tidak diingatkan).')
    expect([chip(item), cell(item, 'point'), cell(item, 'basis')]).toEqual(['Tidak diingatkan', 'belum diisi', 'Belum diisi'])
    // 0: never reminded.
    await click('Atur batas minimum', item)
    await type('Batas minimum (PCS)', '0', row('Kancing 6')); await type('Alasan perubahan bahan', 'Barang tidak dipakai lagi', row('Kancing 6'))
    await click('Simpan', row('Kancing 6'))
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[2].p_payload).toMatchObject({ expected_revision: 2, lead_days: null, manual_point: '0' })
    item = row('Kancing 6')
    expect(item.textContent).toContain('Tersimpan (revisi 3): batas minimum 0 PCS (tidak pernah diingatkan).')
    expect([chip(item), cell(item, 'basis')]).toEqual(['Tidak diingatkan', 'Manual 0: tidak pernah diingatkan'])
    // Every accessory save carries no lama kirim; filtered by "Belum diisi" the list asks the server for NOT_SET.
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1').every(c => (c.p_payload as MaterialPayload).lead_days === null)).toBe(true)
    await click('Belum diisi')
    expect((calls(fake, 'erp_cp7_get_material_reorder_v1').at(-1)?.p_query as MaterialQuery).filter).toBe('NOT_SET')
    expect([...container.querySelectorAll('article.cfr-row')].map(a => a.querySelector('h3')?.textContent)).toEqual(['Kancing 9'])
  })

  it('shows a viewer the numbers without any edit control', async () => {
    const fake = server({ canManage: false, rows: [never(6), accessoryMinimum(7, 150)] })
    auth.current = as('GUDANG', ['warehouse.accessory.view'])
    await mount('ACCESSORY')
    expect(chip(row('Kancing 7'))).toBe('Aman')
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
    expect(row('Kancing 7').textContent).toContain('Batas minimum aksesori ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
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
