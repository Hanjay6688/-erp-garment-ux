// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MaterialReorderPanel from './MaterialReorderPanel'
import ConnectedMasterPage from './ConnectedMasterPage'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import { parseMaterialSaveResult, parseMaterialWorkspace, type MaterialPayload, type MaterialQuery } from './materialReorderContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { REORDER_RUN_AT, reorderRun } from '../tests/fixtures/fgReorder'
import { materialId, materialRow, materialWire, type MaterialWireRow } from '../tests/fixtures/materialReorder'

// SS-2/SS-3: Titik pesan ulang of fabric and accessories against a fake of the three public RPCs of scripts/cp7-src/
// stock-formula/materials.sql that keeps their rules (Owner/Admin to change, a fabric has no manual number, revision check,
// one answer per request id, busy refresh).
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
function recompute(r: MaterialWireRow): MaterialWireRow {
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
      if (fake.rows[i].material_type === 'FABRIC' && p.manual_point !== null) return refuse('22023', 'CP7_FORMULA_MATERIAL_INVALID')
      if (p.expected_revision !== ((fake.rows[i].setting_revision as number | null) ?? 0)) return refuse('40001', 'CP7_FORMULA_MATERIAL_STALE')
      const revision = p.expected_revision + 1, accessory = fake.rows[i].material_type === 'ACCESSORY'
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
const row = (name: string) => {
  const el = [...container.querySelectorAll<HTMLElement>('article.cfr-row')].find(a => a.getAttribute('aria-label')?.startsWith(`Titik pesan ulang ${name} (SKU `))
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
const idle = (n: number, t: 'FABRIC' | 'ACCESSORY' = 'FABRIC') => materialRow(n, t, { usage_qty: 0, counted_days: 0, use_days: 0, daily_mean: null, daily_sd: null,
  safety_qty: null, formula_point: null, point: null, basis: 'NO_USAGE', reason: 'NO_POSTED_USAGE_IN_WINDOW', state: 'NO_POINT' })
const never = (n: number) => materialRow(n, 'ACCESSORY', { lead_days: 5, manual_point: 0, manual_source: 'ACCESSORY_MANUAL', point: 0, basis: 'MANUAL', state: 'NO_POINT' })
const accessoryFormula = (n: number) => materialRow(n, 'ACCESSORY', { free_qty: 180, lead_days: 5, state: 'ABOVE', point: 63.34 })
const run45 = reorderRun({ window_from: '2026-09-05', window_through: '2026-10-19', window_days: 45 })

describe('Titik pesan ulang of fabric and accessories (SS-2/SS-3)', () => {
  it('parses the exact server shapes and refuses unknown, missing and impossible facts', () => {
    const good = materialWire([materialRow(1), minimum(2), noLead(3), fewer(4), idle(5), never(6), accessoryFormula(7)], FQ)
    const parsed = parseMaterialWorkspace(good, FQ)
    expect(parsed.page.rows.map(r => r.name)).toEqual(['Katun 1', 'Katun 2', 'Katun 3', 'Katun 4', 'Katun 5'])
    expect(parsed.page.rows[0]).toMatchObject({ freeQty: '56', onOrderQty: '0', dailyMean: '7.4667', leadDays: '6', settingRevision: 1, point: '63.34',
      formulaPoint: '63.34', basis: 'FORMULA', unitCode: 'YD', state: 'AT_OR_BELOW' })
    expect(parsed.counts).toEqual({ items: 5, atOrBelow: 2, manual: 1, formula: 1, notEnoughData: 2, noUsage: 1 })
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
    const acc = materialWire([never(6), accessoryFormula(7)], AQ)
    expect(parseMaterialWorkspace(acc, AQ).page.rows.map(r => r.manualSource)).toEqual([null, 'ACCESSORY_MANUAL'])
    expect(() => parseMaterialWorkspace({ ...acc, page: { ...acc.page, rows: [{ ...acc.page.rows[0], on_order_qty: 5 }, acc.page.rows[1]] } }, AQ)).toThrow('(bahan)')

    const payload: MaterialPayload = { material_id: materialId(1), expected_revision: 1, lead_days: '6.50', manual_point: null, reason: 'Supplier baru' }
    const evaluation = materialRow(1, 'FABRIC', { lead_days: 6.5, setting_revision: 2 })
    expect(parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC').evaluation?.leadDays).toBe('6.5')
    expect(parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2 }, payload, 'FABRIC').evaluation).toBeNull()
    expect(() => parseMaterialSaveResult({ replay: true, material_id: materialId(1), revision: 2, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 2, evaluation: { ...evaluation, lead_days: 7 } }, payload, 'FABRIC'))
      .toThrow('(hasil simpan bahan)')
    expect(() => parseMaterialSaveResult({ replay: false, material_id: materialId(1), revision: 3, evaluation }, payload, 'FABRIC')).toThrow('(hasil simpan bahan)')
  })

  it('shows each fabric with its numbers, basis and status in plain words, the window from the settings', async () => {
    server({ rows: [materialRow(1), minimum(2), noLead(3), fewer(4), idle(5), never(6)], run: run45 })
    await mount('FABRIC')
    const panel = field<HTMLElement>('Titik pesan ulang kain')
    expect(panel.querySelector('h2')?.textContent).toBe('Titik pesan ulang kain (safety stock)')
    expect(panel.textContent).toContain('Dihitung dari pemakaian yang sudah diposting 45 hari terakhir')
    expect(panel.textContent).toContain(`Dihitung ${wib(REORDER_RUN_AT)} (pemakaian ${formatWaDay('2026-09-05')} sampai ${formatWaDay('2026-10-19')}).`)
    expect(panel.textContent).toContain('"Stok kain menipis"')
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent)).toEqual(['Semua (5)', 'Menipis (2)', 'Pakai minimum (1)', 'Belum cukup data (2)'])
    const f = row('Katun 1')
    expect([chip(f), cell(f, 'free'), cell(f, 'ordered'), cell(f, 'daily'), cell(f, 'lead'), cell(f, 'point'), cell(f, 'basis')])
      .toEqual(['Menipis', '56 YD', '0 YD', '7,47 YD', '6', '63,34 YD', 'Rumus'])
    expect(f.querySelector('.cfr-formula')?.textContent).toContain('Hasil rumus: rata-rata × lama kirim + cadangan, dibulatkan ke atas = 63,34 YD.')
    const m = row('Katun 2')
    expect([chip(m), cell(m, 'point'), cell(m, 'basis')]).toEqual(['Menipis', '500 YD', 'Minimum Kain & Benchmark'])
    expect(m.textContent).toContain('pengingatnya "Stok kain di bawah minimum"')
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
    expect(item.querySelector('[aria-label="Angka manual"]')).toBeNull()
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
    expect(row('Katun 1').textContent).toContain('Jawaban server tidak sampai, jadi belum pasti pengaturan bahan ini tersimpan.')
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

  it('lets the Owner set an accessory manual number (0 = never, empty = the formula) and keeps its lead time', async () => {
    const fake = server({ rows: [never(6), accessoryFormula(7), idle(8, 'ACCESSORY')] })
    await mount('ACCESSORY')
    const panel = field<HTMLElement>('Titik pesan ulang aksesori')
    expect(panel.textContent).toContain('Stok di pos servis, area periksa dan area rusak tidak dihitung sebagai stok.')
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent)).toEqual(['Semua (3)', 'Menipis (0)', 'Angka manual (1)', 'Belum cukup data (0)'])
    const zero = row('Kancing 6')
    expect([chip(zero), cell(zero, 'point'), cell(zero, 'basis')]).toEqual(['Tanpa titik', '0 PCS', 'Angka manual 0: tidak pernah diingatkan'])
    expect(zero.querySelector('[data-cmr="ordered"]')).toBeNull()
    await click('Atur lama kirim & angka manual', zero)
    let item = row('Kancing 6')
    expect(field<HTMLInputElement>('Angka manual', item).value).toBe('0')
    expect(item.textContent).toContain('0 = tidak pernah diingatkan, kosong = pakai rumus.')
    await type('Angka manual', '', item); await type('Alasan perubahan bahan', 'Pakai rumus lagi', item)
    await click('Simpan', item)
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[0].p_payload).toEqual({ material_id: materialId(6), expected_revision: 1, lead_days: '5',
      manual_point: null, reason: 'Pakai rumus lagi' })
    item = row('Kancing 6')
    expect(item.textContent).toContain('Tersimpan (revisi 2): lama kirim 5 hari, tanpa angka manual (pakai rumus).')
    expect([cell(item, 'basis'), cell(item, 'point')]).toEqual(['Rumus', '63,34 PCS'])
    await click('Atur lama kirim & angka manual', item)
    await type('Angka manual', '0', row('Kancing 6')); await type('Alasan perubahan bahan', 'Barang tidak dipakai lagi', row('Kancing 6'))
    await click('Simpan', row('Kancing 6'))
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[1].p_payload).toMatchObject({ expected_revision: 2, lead_days: '5', manual_point: '0' })
    item = row('Kancing 6')
    expect(item.textContent).toContain('angka manual 0 PCS (tidak pernah diingatkan)')
    expect([chip(item), cell(item, 'basis')]).toEqual(['Tanpa titik', 'Angka manual 0: tidak pernah diingatkan'])
    await click('Atur lama kirim & angka manual', row('Kancing 7'))
    await type('Angka manual', '1,5', row('Kancing 7')); await type('Alasan perubahan bahan', 'Coba', row('Kancing 7'))
    await click('Simpan', row('Kancing 7'))
    expect(calls(fake, 'erp_cp7_save_material_reorder_v1')[2].p_payload).toMatchObject({ manual_point: '1.5', lead_days: '5' })
    await click('Atur lama kirim & angka manual', row('Kancing 8'))
    await type('Angka manual', '-3', row('Kancing 8'))
    expect(row('Kancing 8').textContent).toContain('Angka manual: isi 0 atau lebih')
  })

  it('shows a viewer the numbers without any edit control', async () => {
    const fake = server({ canManage: false, rows: [never(6), accessoryFormula(7)] })
    auth.current = as('GUDANG', ['warehouse.accessory.view'])
    await mount('ACCESSORY')
    expect(chip(row('Kancing 7'))).toBe('Aman')
    expect([...container.querySelectorAll('button')].some(b => b.textContent?.startsWith('Atur lama kirim'))).toBe(false)
    expect(container.querySelectorAll('input:not([aria-label="Cari aksesori untuk titik pesan ulang"])')).toHaveLength(0)
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
    expect(row('Katun 1').textContent).toContain('Lama kirim atau angka manual bahan ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
    expect(container.textContent).not.toContain('CP7_FORMULA')
    fake.corrupt = true
    await click('Muat ulang titik pesan ulang kain')
    expect(container.querySelector('[role="alert"]')?.textContent).toBe('Respons titik pesan ulang tidak cocok (titik pesan ulang).')
    expect(container.querySelector('article.cfr-row')).toBeNull()
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
    const fake = server({ rows: [materialRow(1), accessoryFormula(7)] })
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
    expect(field<HTMLElement>('Titik pesan ulang aksesori').closest('.cmd-page')).toBeNull()
    expect(row('Kancing 7').textContent).toContain('Atur lama kirim & angka manual')
    expect(calls(fake, 'erp_cp7_get_material_reorder_v1').map(a => (a.p_query as MaterialQuery).material_type)).toEqual(['FABRIC', 'ACCESSORY'])
  })
})
