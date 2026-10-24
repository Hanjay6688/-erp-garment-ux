// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FgReorderPanel from './FgReorderPanel'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatWaDay } from './waContract'
import {
  parseFgReorderManualResult, parseFgReorderRefresh, parseFgReorderSettingsResult, parseFgReorderWorkspace, type ManualPayload, type ReorderQuery, type SettingsPayload,
} from './fgReorderContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { REORDER_RUN_AT, reorderId, reorderRow, reorderRun, reorderSettings, reorderWire, type ReorderWireRow } from '../tests/fixtures/fgReorder'

// SS-1 (owner D17-8, D17-9): Titik pesan ulang against a fake of the four public RPCs of scripts/cp7-src/stock-formula/
// formula.sql that keeps their rules (Owner/Admin to change, revision checks, one answer per request id, busy refresh).
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const wib = formatCp6WibDateTime
const LATER = '2026-10-20T03:05:00+00:00'
const Q: ReorderQuery = { q: '', filter: 'ALL', offset: 0, limit: 25 }

type Fake = { rows: ReorderWireRow[]; settings: ReturnType<typeof reorderSettings>; run: unknown; canManage: boolean; busy: boolean; lose: Set<string>
  calls: [string, Record<string, unknown>][]; answers: Map<string, { args: string; data: unknown }> }
const refuse = (code: string, message: string) => ({ data: null, error: { code, message, details: null, hint: null } })
const stateOf = (r: ReorderWireRow, point: number | null) => point === null || point <= 0 ? 'NO_POINT'
  : Number(r.free_pcs) + Number(r.wip_pcs ?? 0) <= point ? 'AT_OR_BELOW' : 'ABOVE'
function server(options: Partial<Fake> = {}) {
  const fake: Fake = { rows: [reorderRow(1)], settings: reorderSettings(), run: undefined, canManage: true, busy: false, lose: new Set(), calls: [], answers: new Map(), ...options }
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown> = {}) => {
    fake.calls.push([name, structuredClone(args)])
    const answer = (() => {
      if (name === 'erp_cp7_get_fg_reorder_v1') return { data: reorderWire(fake.rows, args.p_query as ReorderQuery, { settings: fake.settings, can_manage: fake.canManage,
        ...(fake.run === undefined ? {} : { run: fake.run }) }), error: null }
      if (name === 'erp_cp7_refresh_fg_reorder_v1') return fake.busy ? refuse('55P03', 'CP7_FORMULA_BUSY') : { data: { computed_at: LATER, items: fake.rows.length,
        at_or_below: fake.rows.filter(r => r.state === 'AT_OR_BELOW').length, wip_read: 0, materials: 4, materials_at_or_below: 1 }, error: null }
      if (!fake.canManage) return refuse('42501', 'CP7_FORMULA_ACCESS_DENIED')
      const key = String(args.p_request), prior = fake.answers.get(key), sent = JSON.stringify(args.p_payload)
      if (prior) return prior.args === sent ? { data: prior.data, error: null } : refuse('22023', 'CP7_FORMULA_REQUEST_REUSED')
      if (name === 'erp_cp7_save_fg_reorder_manual_v1') {
        const p = args.p_payload as ManualPayload, i = fake.rows.findIndex(r => r.root_id === p.root_id)
        if (i < 0) return refuse('22023', 'CP7_FORMULA_ITEM_UNKNOWN')
        if (p.expected_revision !== (fake.rows[i].manual_revision ?? 0)) return refuse('40001', 'CP7_FORMULA_MANUAL_STALE')
        const revision = p.expected_revision + 1, point = p.reorder_point_pcs ?? (fake.rows[i].formula_point as number | null)
        const next: ReorderWireRow = { ...fake.rows[i], manual_point: p.reorder_point_pcs, manual_revision: revision, point, state: stateOf(fake.rows[i], point),
          basis: p.reorder_point_pcs === null ? 'FORMULA' : 'MANUAL' }
        fake.rows[i] = next
        fake.answers.set(key, { args: sent, data: { replay: true, root_id: p.root_id, revision, reorder_point_pcs: p.reorder_point_pcs } })
        return { data: { replay: false, root_id: p.root_id, revision, reorder_point_pcs: p.reorder_point_pcs,
          evaluation: Object.fromEntries(Object.entries(next).filter(([k]) => k !== 'wip_read_at')) }, error: null }
      }
      if (name === 'erp_cp7_save_stock_formula_settings_v1') {
        const p = args.p_payload as SettingsPayload
        if (p.expected_revision !== fake.settings.revision) return refuse('40001', 'CP7_FORMULA_SETTINGS_STALE')
        fake.settings = { revision: p.expected_revision + 1, service_level: p.service_level, window_days: p.window_days, reason: p.reason, saved_at: LATER }
        fake.answers.set(key, { args: sent, data: { replay: true, settings: fake.settings } })
        return { data: { replay: false, settings: fake.settings }, error: null }
      }
      throw new Error(`unexpected ${name}`)
    })()
    if (fake.lose.has(name)) { fake.lose.delete(name); throw new TypeError('Failed to fetch') }
    return answer
  })
  return fake
}

let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear(); client.rpc.mockReset(); auth.current = structuredClone(recoveryIdentity)
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks() })
async function settle() { for (let i = 0; i < 3; i++) await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<FgReorderPanel/>)); await settle() }
function button(name: string, scope: ParentNode = container) {
  const b = [...scope.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name || x.getAttribute('aria-label') === name || x.textContent?.startsWith(`${name} (`))
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
async function click(name: string, scope?: ParentNode) { await act(async () => button(name, scope).click()); await settle() }
function field<T extends HTMLElement>(label: string, scope: ParentNode = container) {
  const el = scope.querySelector<T>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}: ${container.textContent}`); return el
}
async function type(label: string, value: string, scope?: ParentNode) {
  const el = field<HTMLInputElement | HTMLSelectElement>(label, scope)
  const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
const row = (label: string) => {
  const el = [...container.querySelectorAll<HTMLElement>('article.cfr-row')].find(a => a.getAttribute('aria-label')?.startsWith(`Titik pesan ulang ${label} (SKU `))
  if (!el) throw new Error(`No row ${label}: ${container.textContent}`); return el
}
const value = (r: HTMLElement, key: string) => r.querySelector(`[data-cfr="${key}"]`)?.textContent
const chip = (r: HTMLElement) => r.querySelector('.cfr-chip')?.textContent
const reads = (fake: Fake) => fake.calls.filter(c => c[0] === 'erp_cp7_get_fg_reorder_v1').map(c => c[1].p_query)
const calls = (fake: Fake, name: string) => fake.calls.filter(c => c[0] === name).map(c => c[1])

// The seven situations an item can be in, as compute() writes them.
const manualAbove = (n: number) => reorderRow(n, { manual_point: 20, manual_revision: 1, point: 20, basis: 'MANUAL', state: 'ABOVE', size_code: null,
  wip_pcs: null, wip_status: 'NOT_READ', wip_reason: 'NOT_READ_YET' })
const fewerDays = (n: number) => reorderRow(n, { counted_days: 10, sale_days: 10, sales_pcs: 30, daily_mean: 3, daily_sd: 0, safety_pcs: null, formula_point: null,
  point: null, basis: 'NOT_ENOUGH_DATA', reason: 'FEWER_THAN_14_COUNTED_DAYS', state: 'NO_POINT' })
const noLead = (n: number) => reorderRow(n, { lead_days: null, lead_basis: null, safety_pcs: null, formula_point: null, point: null, basis: 'NOT_ENOUGH_DATA',
  reason: 'NO_LEAD_TIME', state: 'NO_POINT', wip_pcs: null, wip_status: 'UNKNOWN', wip_reason: 'MODEL_WIP_GROUP_LIMIT', wip_read_at: REORDER_RUN_AT })
const noSales = (n: number) => reorderRow(n, { sales_pcs: 0, counted_days: 0, sale_days: 0, daily_mean: null, daily_sd: null, safety_pcs: null, formula_point: null,
  point: null, basis: 'NO_SALES', reason: 'NO_POSTED_SALES_IN_WINDOW', state: 'NO_POINT' })
const manualZero = (n: number) => reorderRow(n, { manual_point: 0, manual_revision: 2, point: 0, basis: 'MANUAL', state: 'NO_POINT' })
const measuredDays = (n: number) => reorderRow(n, { free_pcs: 1234.5, lead_days: 9.25, lead_basis: 'MEASURED', lead_lots: 3, lead_groups: 3, buffer_mode: 'DAYS',
  buffer_days: 3, safety_pcs: 11.7, formula_point: 48, point: 48, wip_pcs: 12, state: 'ABOVE', wip_read_at: REORDER_RUN_AT })

describe('Titik pesan ulang on Ringkasan Barang Jadi (SS-1)', () => {
  it('parses the exact server shapes and refuses unknown, missing and impossible facts', () => {
    const good = reorderWire([reorderRow(1), manualAbove(2), fewerDays(3), noLead(4), noSales(5), manualZero(6), measuredDays(7)])
    const parsed = parseFgReorderWorkspace(good, Q)
    expect(parsed.page.rows).toHaveLength(7)
    expect(parsed.page.rows[0]).toMatchObject({ freePcs: '23', salesPcs: '117', dailyMean: '3.9', dailySd: '1.9182', z: '1.6449', safetyPcs: '8.3485', point: 36,
      formulaPoint: 36, basis: 'FORMULA', wipPcs: '0', wipStatus: 'COMPLETE', state: 'AT_OR_BELOW', wipReadAt: null })
    expect(parsed.run).toMatchObject({ serviceLevel: '0.95', windowDays: 30, materials: 4, materialsAtOrBelow: 1 })
    expect(parsed.counts).toEqual({ items: 7, atOrBelow: 1, manual: 2, formula: 2, notEnoughData: 2, noSales: 1 })
    expect(parsed.canManage).toBe(true)
    const rows = good.page.rows, withRow = (i: number, change: Record<string, unknown>) => ({ ...good, page: { ...good.page, rows: rows.map((r, j) => j === i ? { ...r, ...change } : r) } })
    expect(() => parseFgReorderWorkspace({ ...good, extra: 1 }, Q)).toThrow('Respons titik pesan ulang tidak cocok (titik pesan ulang).')
    expect(() => parseFgReorderWorkspace(withRow(0, { surprise: true }), Q)).toThrow('(barang)')
    const missing = structuredClone(good); delete (missing.page.rows[0] as Record<string, unknown>).wip_read_at
    expect(() => parseFgReorderWorkspace(missing, Q)).toThrow('(barang)')
    expect(() => parseFgReorderWorkspace(withRow(0, { point: 35 }), Q)).toThrow('(titik pesan ulang)')
    expect(() => parseFgReorderWorkspace(withRow(1, { point: 21 }), Q)).toThrow('(titik pesan ulang)')
    expect(() => parseFgReorderWorkspace(withRow(2, { point: 5 }), Q)).toThrow('(titik pesan ulang)')
    expect(() => parseFgReorderWorkspace(withRow(0, { wip_pcs: null }), Q)).toThrow('(sedang diproduksi)')
    expect(() => parseFgReorderWorkspace(withRow(0, { reason: 'NO_LEAD_TIME' }), Q)).toThrow('(alasan)')
    expect(() => parseFgReorderWorkspace(withRow(0, { free_pcs: '23' }), Q)).toThrow('(barang)')
    expect(() => parseFgReorderWorkspace(withRow(0, { free_pcs: 1e21 }), Q)).toThrow('(barang)')
    expect(() => parseFgReorderWorkspace(withRow(0, { state: 'ABOVE', free_pcs: 23 }), { ...Q, filter: 'AT_OR_BELOW' })).toThrow()
    expect(() => parseFgReorderWorkspace(good, { ...Q, filter: 'MANUAL' })).toThrow('(saringan)')
    expect(() => parseFgReorderWorkspace(good, { ...Q, offset: 25 })).toThrow('(halaman)')
    const oldRun = structuredClone(good) as Record<string, unknown> & { run: Record<string, unknown> }; delete oldRun.run.materials
    expect(() => parseFgReorderWorkspace(oldRun, Q)).toThrow('(hitungan terakhir)')
    expect(() => parseFgReorderWorkspace({ ...good, run: reorderRun({ window_from: '2026-09-21' }) }, Q)).toThrow('(hitungan terakhir)')
    expect(() => parseFgReorderWorkspace({ ...good, settings: reorderSettings({ revision: 2 }) }, Q)).toThrow('(pengaturan)')
    expect(parseFgReorderWorkspace({ ...good, run: null }, Q).run).toBeNull()

    const refresh = { computed_at: LATER, items: 7, at_or_below: 1, wip_read: 2, materials: 4, materials_at_or_below: 1 }
    expect(parseFgReorderRefresh(refresh)).toEqual({ computedAt: LATER, items: 7, atOrBelow: 1, wipRead: 2, materials: 4, materialsAtOrBelow: 1 })
    const { materials_at_or_below: _drop, ...noMaterials } = refresh
    expect(_drop).toBe(1)
    expect(() => parseFgReorderRefresh(noMaterials)).toThrow('(hasil hitung)')
    expect(() => parseFgReorderRefresh({ ...refresh, extra: 1 })).toThrow('(hasil hitung)')

    const payload: ManualPayload = { root_id: reorderId(1), expected_revision: 0, reorder_point_pcs: 22, reason: 'Pesanan besar' }
    const evaluation = Object.fromEntries(Object.entries(reorderRow(1, { manual_point: 22, manual_revision: 1, point: 22, basis: 'MANUAL', state: 'ABOVE' }))
      .filter(([k]) => k !== 'wip_read_at'))
    expect(parseFgReorderManualResult({ replay: false, root_id: reorderId(1), revision: 1, reorder_point_pcs: 22, evaluation }, payload).evaluation?.state).toBe('ABOVE')
    expect(parseFgReorderManualResult({ replay: true, root_id: reorderId(1), revision: 1, reorder_point_pcs: 22 }, payload).evaluation).toBeNull()
    expect(() => parseFgReorderManualResult({ replay: true, root_id: reorderId(1), revision: 1, reorder_point_pcs: 22, evaluation }, payload)).toThrow('(hasil angka manual)')
    expect(() => parseFgReorderManualResult({ replay: false, root_id: reorderId(1), revision: 2, reorder_point_pcs: 22, evaluation }, payload)).toThrow('(hasil angka manual)')
    expect(() => parseFgReorderManualResult({ replay: false, root_id: reorderId(1), revision: 1, reorder_point_pcs: 22, evaluation: { ...evaluation, wip_read_at: null } }, payload))
      .toThrow('(barang)')

    const sp: SettingsPayload = { expected_revision: 0, service_level: '0.99', window_days: 60, reason: 'Musim lebaran' }
    const saved = reorderSettings({ revision: 1, service_level: '0.99', window_days: 60, reason: 'Musim lebaran', saved_at: LATER })
    expect(parseFgReorderSettingsResult({ replay: false, settings: saved }, sp).settings.revision).toBe(1)
    expect(parseFgReorderSettingsResult({ replay: true, settings: { ...saved, revision: 2, service_level: '0.90' } }, sp).replay).toBe(true)
    expect(() => parseFgReorderSettingsResult({ replay: false, settings: { ...saved, window_days: 30 } }, sp)).toThrow('(hasil pengaturan)')
    expect(() => parseFgReorderSettingsResult({ replay: true, settings: reorderSettings() }, sp)).toThrow('(hasil pengaturan)')
  })

  it('shows each item with its status, numbers and formula in plain words', async () => {
    server({ rows: [reorderRow(1), manualAbove(2), fewerDays(3), noLead(4), noSales(5), manualZero(6), measuredDays(7)] })
    await mount()
    const panel = field<HTMLElement>('Titik pesan ulang')
    expect(panel.querySelector('h2')?.textContent).toBe('Titik pesan ulang (safety stock)')
    expect(panel.textContent).toContain('Titik pesan ulang = rata-rata jual per hari × lama produksi + cadangan. Dihitung dari penjualan yang sudah diposting 30 hari')
    expect(panel.textContent).toContain('(hari stok kosong tidak dihitung) dengan tingkat layanan 95%.')
    expect(panel.textContent).toContain(`Dihitung ${wib(REORDER_RUN_AT)} (penjualan ${formatWaDay('2026-09-20')} sampai ${formatWaDay('2026-10-19')}).`)
    expect([...panel.querySelectorAll('.cfr-filters button')].map(b => b.textContent)).toEqual(['Semua (7)', 'Di bawah titik pesan ulang (1)', 'Angka manual (2)', 'Belum cukup data (2)'])

    const formula = row('Kemeja Linen 1 M')
    expect([chip(formula), value(formula, 'free'), value(formula, 'wip'), value(formula, 'point')]).toEqual(['Perlu produksi', '23 pcs', '0 pcs', '36 pcs'])
    expect(formula.querySelector('.cfr-chip')?.classList.contains('warn')).toBe(true)
    expect(formula.textContent).toContain('Asal angka: rumus')
    expect([...formula.querySelectorAll('.cfr-formula li')].map(li => li.textContent)).toEqual([
      'Rata-rata jual per hari: 3,90 pcs.', 'Naik-turun penjualan per hari: 1,92 pcs.', 'Hari terhitung: 30 dari 30 hari (hari jual 27); terjual 117 pcs.',
      'Lama produksi: 7 hari (dari profil perencanaan).', 'Cadangan: 1,6449 × naik-turun × √lama produksi = 8,35 pcs (tingkat layanan 95%).',
      'Hasil rumus: rata-rata × lama produksi + cadangan, dibulatkan ke atas = 36 pcs.'])
    expect(formula.querySelector('details summary')?.textContent).toBe('Rincian rumus')

    const manual = row('Kemeja Linen 2')
    expect([chip(manual), value(manual, 'wip'), value(manual, 'point')]).toEqual(['Aman', 'belum dibaca', '20 pcs'])
    expect(manual.textContent).toContain('Asal angka: angka manual (rumus: 36)')
    expect(manual.textContent).toContain('Sedang diproduksi belum dibaca: server belum sempat membacanya. Selama itu, yang dibandingkan dengan titik pesan ulang hanya stok bebas.')

    const fewer = row('Kemeja Linen 3 M')
    expect([chip(fewer), value(fewer, 'point')]).toEqual(['Belum cukup data', 'belum ada'])
    expect(fewer.textContent).toContain('Belum cukup data: baru 10 hari tercatat, perlu 14.')
    expect(fewer.textContent).not.toContain('Asal angka')
    expect(fewer.textContent).toContain('Cadangan: belum bisa dihitung.'); expect(fewer.textContent).toContain('Hasil rumus: belum ada.')

    const lead = row('Kemeja Linen 4 M')
    expect([chip(lead), value(lead, 'wip')]).toEqual(['Belum cukup data', 'belum bisa dihitung'])
    expect(lead.textContent).toContain('lama produksi belum ada, karena belum ada 3 kali produksi model ini. Isi lama produksi di profil perencanaan')
    expect(lead.textContent).toContain('atau isi angka manual.')
    expect(lead.textContent).toContain(`dibaca ${wib(REORDER_RUN_AT)}`)
    expect(lead.textContent).toContain('potongan model ini yang masih berjalan lebih dari 200')
    expect(lead.textContent).toContain('Lama produksi: belum ada.')

    const sales = row('Kemeja Linen 5 M')
    expect([chip(sales), value(sales, 'point')]).toEqual(['Belum ada penjualan 30 hari terakhir', 'belum ada'])
    expect(sales.textContent).toContain('Rata-rata jual per hari: belum ada.')
    expect(sales.textContent).toContain('Naik-turun penjualan per hari: belum ada.')

    const off = row('Kemeja Linen 6 M')
    expect([chip(off), value(off, 'point')]).toEqual(['Peringatan dimatikan (angka manual 0)', '0 pcs'])

    const measured = row('Kemeja Linen 7 M')
    expect([chip(measured), value(measured, 'free'), value(measured, 'wip'), value(measured, 'point')]).toEqual(['Aman', '1.234,5 pcs', '12 pcs', '48 pcs'])
    expect(measured.textContent).toContain('Lama produksi: 9,25 hari (diukur dari 3 lot dari 3 potongan).')
    expect(measured.textContent).toContain('Cadangan: rata-rata × 3 hari = 11,7 pcs (cadangan hari dari profil perencanaan).')
    for (const word of ['NaN', 'undefined', 'null', 'CP7_', 'NOT_ENOUGH_DATA', 'NO_LEAD_TIME']) expect(panel.textContent).not.toContain(word)
    expect(panel.textContent).toContain('7 barang · total 7')
  })

  it('says plainly when it was never calculated, and "Hitung sekarang" refreshes then reads again', async () => {
    const fake = server({ run: null })
    await mount()
    expect(container.textContent).toContain('Belum pernah dihitung. Server menghitungnya tiap menit sesudah pengingat WhatsApp diatur')
    expect(container.textContent).toContain('atau tekan "Hitung sekarang".')
    fake.run = undefined
    await click('Hitung sekarang')
    expect(calls(fake, 'erp_cp7_refresh_fg_reorder_v1')).toEqual([{}])
    expect(container.textContent).toContain(`Selesai dihitung ${wib(LATER)}: 1 barang jadi, 1 perlu produksi.`)
    expect(container.textContent).toContain(`Dihitung ${wib(REORDER_RUN_AT)}`)
    expect(reads(fake)).toHaveLength(2)
  })

  it('sends the asked filter, search and page, and keeps them while paging', async () => {
    const rows = Array.from({ length: 30 }, (_, i) => reorderRow(i + 1, i % 2 ? { free_pcs: 50, state: 'ABOVE' } : {}))
    const fake = server({ rows })
    await mount()
    expect(reads(fake)).toEqual([Q])
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(25)
    expect(container.textContent).toContain('25 barang · total 30')
    expect(button('Barang sebelumnya').disabled).toBe(true)
    await click('Barang berikutnya')
    expect(reads(fake).at(-1)).toEqual({ ...Q, offset: 25 })
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(5)
    expect(button('Barang berikutnya').disabled).toBe(true)
    await click('Barang sebelumnya')
    expect(reads(fake).at(-1)).toEqual(Q)
    await click('Di bawah titik pesan ulang')
    expect(reads(fake).at(-1)).toEqual({ ...Q, filter: 'AT_OR_BELOW' })
    expect(button('Di bawah titik pesan ulang').getAttribute('aria-pressed')).toBe('true')
    expect([...container.querySelectorAll('article.cfr-row')].every(a => a.querySelector('.cfr-chip')?.textContent === 'Perlu produksi')).toBe(true)
    await type('Cari barang untuk titik pesan ulang', '  Linen 1 ')
    await click('Cari')
    expect(reads(fake).at(-1)).toEqual({ ...Q, filter: 'AT_OR_BELOW', q: 'Linen 1' })
    expect(field<HTMLInputElement>('Cari barang untuk titik pesan ulang').maxLength).toBe(120)
    await click('Angka manual')
    expect(reads(fake).at(-1)).toEqual({ ...Q, filter: 'MANUAL', q: 'Linen 1' })
    expect(container.textContent).toContain('Tidak ada barang jadi yang cocok.')
    await click('Kosongkan pencarian')
    expect(reads(fake).at(-1)).toEqual({ ...Q, filter: 'MANUAL' })
  })

  it('lets the Owner set and remove a manual point with the exact payload; a lost reply is sent again with the same id', async () => {
    const fake = server({ rows: [reorderRow(1), reorderRow(2)], lose: new Set(['erp_cp7_save_fg_reorder_manual_v1']) })
    await mount()
    let item = row('Kemeja Linen 1 M')
    await click('Atur angka manual', item)
    item = row('Kemeja Linen 1 M')
    expect(field<HTMLInputElement>('Titik pesan ulang manual (pcs)', item).value).toBe('36')
    expect(row('Kemeja Linen 2 M').querySelector('form')).toBeNull()
    expect(item.textContent).not.toContain('Hapus angka manual')
    for (const bad of ['', '2.5', '-1', '10000001']) {
      await type('Titik pesan ulang manual (pcs)', bad, item)
      expect(item.textContent).toContain('Isi titik pesan ulang dengan angka bulat 0 sampai 10.000.000 pcs')
      expect(button('Simpan angka manual', item).disabled).toBe(true)
    }
    await type('Titik pesan ulang manual (pcs)', '22', item)
    expect(item.textContent).toContain('Tulis alasannya'); expect(button('Simpan angka manual', item).disabled).toBe(true)
    await type('Alasan angka manual', '  Pesanan besar toko A ', item)
    expect(field<HTMLInputElement>('Alasan angka manual', item).maxLength).toBe(500)
    await click('Simpan angka manual', item)
    expect(container.textContent).toContain('Jawaban server tidak sampai, jadi belum pasti angka manual tersimpan. Tekan tombol yang sama lagi tanpa mengubah isian')
    await click('Simpan angka manual', row('Kemeja Linen 1 M'))
    const saves = calls(fake, 'erp_cp7_save_fg_reorder_manual_v1')
    expect(saves).toHaveLength(2)
    expect(saves[0]).toEqual({ p_payload: { root_id: reorderId(1), expected_revision: 0, reorder_point_pcs: 22, reason: 'Pesanan besar toko A' },
      p_request: expect.stringMatching(/^[0-9a-f-]{36}$/) })
    expect(saves[1]).toEqual(saves[0])
    item = row('Kemeja Linen 1 M')
    expect(item.textContent).toContain('Angka manual tersimpan: 22 pcs. Permintaan ini ternyata sudah tersimpan sebelumnya.')
    expect([chip(item), value(item, 'point')]).toEqual(['Aman', '22 pcs'])
    expect(item.textContent).toContain('Asal angka: angka manual (rumus: 36)')
    expect(item.querySelector('form')).toBeNull()
    expect(reads(fake)).toHaveLength(2)

    await click('Atur angka manual', item)
    item = row('Kemeja Linen 1 M')
    expect(field<HTMLInputElement>('Titik pesan ulang manual (pcs)', item).value).toBe('22')
    expect(button('Hapus angka manual', item).disabled).toBe(true)
    await type('Alasan angka manual', 'Pesanan toko A batal', item)
    await click('Hapus angka manual', item)
    const removed = calls(fake, 'erp_cp7_save_fg_reorder_manual_v1')
    expect(removed).toHaveLength(3)
    expect(removed[2].p_payload).toEqual({ root_id: reorderId(1), expected_revision: 1, reorder_point_pcs: null, reason: 'Pesanan toko A batal' })
    expect(removed[2].p_request).not.toBe(saves[0].p_request)
    item = row('Kemeja Linen 1 M')
    expect(item.textContent).toContain('Angka manual dihapus; titik pesan ulang kembali memakai rumus.')
    expect([chip(item), value(item, 'point')]).toEqual(['Perlu produksi', '36 pcs'])
    expect(item.textContent).toContain('Asal angka: rumus')
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0)
  })

  it('lets the Owner change the formula settings with the expected revision', async () => {
    const fake = server()
    await mount()
    const box = () => field<HTMLElement>('Pengaturan rumus titik pesan ulang')
    expect(box().textContent).toContain('Belum pernah diubah: memakai bawaan 95% dan 30 hari.')
    expect(button('Simpan pengaturan rumus', box()).disabled).toBe(true)
    expect(box().textContent).toContain('Belum ada yang diubah.')
    await type('Tingkat layanan', '0.99', box())
    await type('Jumlah hari penjualan', '400', box())
    expect(box().textContent).toContain('Jumlah hari penjualan: isi 14 sampai 365 hari.')
    await type('Jumlah hari penjualan', '60', box())
    expect(box().textContent).toContain('Tulis alasan perubahan')
    await type('Alasan perubahan pengaturan rumus', 'Musim lebaran', box())
    await click('Simpan pengaturan rumus', box())
    expect(calls(fake, 'erp_cp7_save_stock_formula_settings_v1')).toEqual([{ p_payload: { expected_revision: 0, service_level: '0.99', window_days: 60,
      reason: 'Musim lebaran' }, p_request: expect.stringMatching(/^[0-9a-f-]{36}$/) }])
    expect(box().textContent).toContain('Pengaturan rumus tersimpan (revisi 1); titik pesan ulang dihitung ulang.')
    expect(box().textContent).toContain(`Revisi 1, disimpan ${wib(LATER)}: Musim lebaran.`)
    expect(field<HTMLSelectElement>('Tingkat layanan', box()).value).toBe('0.99')
    expect(field<HTMLInputElement>('Alasan perubahan pengaturan rumus', box()).value).toBe('')
    // Someone else saves revision 2 meanwhile: the next save is refused in words.
    fake.settings = reorderSettings({ revision: 2, service_level: '0.90', window_days: 30, reason: 'lain', saved_at: LATER })
    await type('Jumlah hari penjualan', '45', box()); await type('Alasan perubahan pengaturan rumus', 'Coba', box())
    await click('Simpan pengaturan rumus', box())
    expect(box().textContent).toContain('Pengaturan rumus baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
    expect(calls(fake, 'erp_cp7_save_stock_formula_settings_v1')[1].p_payload).toMatchObject({ expected_revision: 1, window_days: 45 })
    expect(container.textContent).not.toContain('CP7_FORMULA')
  })

  it('retires a refused model cache and recovers with the existing explicit refresh', async () => {
    server({ canManage: false })
    await mount()
    client.rpc.mockImplementationOnce(async () => refuse('40001', 'CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED'))
    await click('Muat ulang')
    expect(container.textContent).toContain('Data atau hak akses untuk hitungan ini sudah berubah.')
    expect(container.textContent).not.toContain('CP7_MODEL_TARGET')
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(0)
    expect(button('Hitung sekarang').disabled).toBe(false)
    await click('Hitung sekarang')
    expect(container.textContent).not.toContain('Data atau hak akses untuk hitungan ini sudah berubah.')
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(1)
  })

  it('shows a viewer the numbers without any edit control', async () => {
    const fake = server({ canManage: false, rows: [reorderRow(1), manualAbove(2)] })
    auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, role: 'GUDANG' } } }
    await mount()
    expect(row('Kemeja Linen 1 M').textContent).toContain('Perlu produksi')
    expect(row('Kemeja Linen 2').textContent).toContain('Asal angka: angka manual (rumus: 36)')
    for (const name of ['Atur angka manual', 'Simpan angka manual', 'Hapus angka manual', 'Simpan pengaturan rumus'])
      expect([...container.querySelectorAll('button')].some(b => b.textContent === name)).toBe(false)
    expect(container.querySelector('[aria-label="Pengaturan rumus titik pesan ulang"]')).toBeNull()
    expect(container.querySelectorAll('input:not([aria-label="Cari barang untuk titik pesan ulang"]), select, textarea')).toHaveLength(0)
    expect(button('Hitung sekarang').disabled).toBe(false)
    expect(fake.calls.map(c => c[0])).toEqual(['erp_cp7_get_fg_reorder_v1'])
  })

  it('says a busy calculation and a stale manual point in plain words', async () => {
    const fake = server({ busy: true })
    await mount()
    await click('Hitung sekarang')
    expect(container.querySelector('[role="alert"]')?.textContent).toBe('Server sedang menghitung titik pesan ulang (hitungan otomatis tiap menit, atau tombol "Hitung sekarang" dari layar lain). Coba lagi sekitar satu menit lagi.')
    expect(container.textContent).not.toContain('CP7_FORMULA_BUSY')
    expect(reads(fake)).toHaveLength(1)
    fake.rows[0] = { ...fake.rows[0], manual_revision: 3, manual_point: null }
    await click('Atur angka manual', row('Kemeja Linen 1 M'))
    await type('Alasan angka manual', 'Cek', row('Kemeja Linen 1 M'))
    await click('Simpan angka manual', row('Kemeja Linen 1 M'))
    expect(row('Kemeja Linen 1 M').textContent).toContain('Angka manual barang ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang"')
    expect(calls(fake, 'erp_cp7_save_fg_reorder_manual_v1')[0].p_payload).toMatchObject({ expected_revision: 0 })
    // A definite refusal starts a new request next time.
    await click('Simpan angka manual', row('Kemeja Linen 1 M'))
    const [a, b] = calls(fake, 'erp_cp7_save_fg_reorder_manual_v1')
    expect(b.p_request).not.toBe(a.p_request)
  })

  it('never lets a late answer replace a newer one', async () => {
    let release: (x: unknown) => void = () => {}
    const fake = server({ rows: [reorderRow(1), manualAbove(2)] })
    const answer = client.rpc.getMockImplementation()!
    client.rpc.mockImplementationOnce((name: string, args: Record<string, unknown>) => { fake.calls.push([name, structuredClone(args)]); return new Promise(r => { release = r }) })
    await mount()
    expect(container.textContent).toContain('Memuat titik pesan ulang')
    client.rpc.mockImplementation(answer)
    await click('Angka manual')
    expect(reads(fake).map(q => (q as ReorderQuery).filter)).toEqual(['ALL', 'MANUAL'])
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(1)
    await act(async () => release({ data: reorderWire(fake.rows, Q), error: null })); await settle()
    expect(container.querySelectorAll('article.cfr-row')).toHaveLength(1)
    expect(row('Kemeja Linen 2').textContent).toContain('Aman')
    expect(button('Angka manual').getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelector('[role="alert"]')).toBeNull()
  })
})
