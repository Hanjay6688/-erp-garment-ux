import app from './App.tsx?raw'
import { describe, expect, it } from 'vitest'
import { connectedSections, isNavLabelHidden, SCREEN_ACTIVATION, screenActivation } from './screenActivation'

// Owner D15-2 (Fable FABLE-015 oracle: "di build mode Enteng, tidak ada menu yang menampilkan angka contoh tanpa label;
// setiap layar uang/absensi tersambung atau tidak tampil", checked from the routing code), superseded by owner D16-1
// ("selesain biar gausa sembunyiin"; Fable oracle 1: no hidden menu and no sample figure in the Enteng build, each menu
// uses the same connected component as the test build) and D16-5 ("Tutup Periode" is a tab of "Laporan & Tutup Buku").
const navBlock = app.slice(app.indexOf('const nav: Record<NavSection, string[]> = {'), app.indexOf('const salesPageByLabel'))
const navLabels = [...navBlock.matchAll(/'([^']+)'/g)].map(m => m[1])
  .filter(label => label !== 'Master Data') // the one quoted section key
const adminLabels = [...(app.match(/const adminNav = \[([^\]]+)\]/)?.[1] ?? '').matchAll(/'([^']+)'/g)].map(m => m[1])
const money = ['sales-invoice', 'sales-allocation', 'sales-returns', 'sales-payments', 'sales-history', 'finance-overview', 'finance-cash', 'finance-ap',
  'finance-ar', 'finance-payroll', 'finance-journal', 'finance-reports', 'operations-attendance', 'contractor-issue', 'hpp']

describe('screen activation (owner D15-2)', () => {
  it('covers exactly the 47 menus of the sidebar (48 before D16-5 merged Tutup Periode)', () => {
    const labels = ['Dashboard', ...navLabels, ...adminLabels]
    expect(new Set(labels).size).toBe(47)
    expect(labels).not.toContain('Tutup Periode')
    expect(new Set(Object.values(SCREEN_ACTIVATION).map(row => row.label))).toEqual(new Set(labels))
  })
  it('shows no sample, boundary or hidden screen in the Enteng build: every menu is connected (the dashboard is a notice)', () => {
    for (const page of Object.keys(SCREEN_ACTIVATION)) expect(screenActivation('UAT_AUTH_SIMULATION', page), page).toBe(page === 'dashboard' ? 'NOTICE' : 'CONNECTED')
    for (const page of money) expect(screenActivation('UAT_AUTH_SIMULATION', page), page).toBe('CONNECTED')
  })
  it('routes the Enteng build to the same connected component as the disposable test build', () => {
    // No route is connected only in the disposable test build any more (D16-1); before, eleven were.
    expect(app).not.toMatch(/runtime\.mode\s*===?\s*'DISPOSABLE_TEST'/)
    for (const page of Object.keys(SCREEN_ACTIVATION)) expect(screenActivation('DISPOSABLE_TEST', page), page).toBe(screenActivation('UAT_AUTH_SIMULATION', page))
  })
  it('opens the old Tutup Periode route on the Tutup Buku tab of the merged page (owner D16-5)', () => {
    expect(app).toContain("const redirectedPages: Partial<Record<Page, { page: Page; reportTab: FinanceReportTab }>> = { 'admin-period-close': { page: 'finance-reports', reportTab: 'PERIOD' } }")
    expect(app).toContain('<ConnectedFinanceReportPage tab={reportTab} onTab={setReportTab}/>')
    expect(SCREEN_ACTIVATION['admin-period-close']).toBeUndefined()
  })
  it('hides the sidebar entry together with the screen, and nothing in the demo build', () => {
    for (const row of Object.values(SCREEN_ACTIVATION)) {
      expect(isNavLabelHidden('UAT_AUTH_SIMULATION', row.label), row.label).toBe(row.enteng === 'HIDDEN')
      expect(isNavLabelHidden('DEMO_SIMULATION', row.label), row.label).toBe(false)
      expect(isNavLabelHidden('DISPOSABLE_TEST', row.label), row.label).toBe(false)
    }
    expect(isNavLabelHidden('UAT_AUTH_SIMULATION', 'Menu tak dikenal')).toBe(true)
  })
  it('lets the dashboard point only to sections with a connected screen', () => {
    expect(connectedSections('UAT_AUTH_SIMULATION')).toContain('Penjualan')
    expect(connectedSections('DISPOSABLE_TEST')).toContain('Penjualan')
    expect(connectedSections('DEMO_SIMULATION')).toEqual([])
  })
})
