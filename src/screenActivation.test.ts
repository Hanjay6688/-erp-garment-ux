import app from './App.tsx?raw'
import { describe, expect, it } from 'vitest'
import { connectedSections, isNavLabelHidden, isScreenHidden, SCREEN_ACTIVATION, screenActivation } from './screenActivation'

// Owner D15-2 (Fable FABLE-015 oracle: "di build mode Enteng, tidak ada menu yang menampilkan angka contoh tanpa label;
// setiap layar uang/absensi tersambung atau tidak tampil", checked from the routing code).
const navBlock = app.slice(app.indexOf('const nav: Record<NavSection, string[]> = {'), app.indexOf('const salesPageByLabel'))
const navLabels = [...navBlock.matchAll(/'([^']+)'/g)].map(m => m[1])
  .filter(label => label !== 'Master Data') // the one quoted section key
const adminLabels = [...(app.match(/const adminNav = \[([^\]]+)\]/)?.[1] ?? '').matchAll(/'([^']+)'/g)].map(m => m[1])
const money = ['sales-invoice', 'sales-allocation', 'sales-returns', 'sales-payments', 'sales-history', 'finance-overview', 'finance-cash', 'finance-ap',
  'finance-ar', 'finance-payroll', 'finance-journal', 'finance-reports', 'operations-attendance', 'contractor-issue', 'hpp']

describe('screen activation (owner D15-2)', () => {
  it('covers exactly the 48 menus of the sidebar', () => {
    const labels = ['Dashboard', ...navLabels, ...adminLabels]
    expect(new Set(labels).size).toBe(48)
    expect(new Set(Object.values(SCREEN_ACTIVATION).map(row => row.label))).toEqual(new Set(labels))
  })
  it('shows no sample screen in the Enteng build: every menu is connected, a boundary, a notice or hidden', () => {
    for (const page of Object.keys(SCREEN_ACTIVATION)) expect(screenActivation('UAT_AUTH_SIMULATION', page), page).not.toBe('SAMPLE')
    for (const page of money) expect(['CONNECTED', 'HIDDEN'], page).toContain(screenActivation('UAT_AUTH_SIMULATION', page))
  })
  it('hides in Enteng every screen the router connects only in the disposable test build', () => {
    const disposableOnly = new Set([
      ...[...app.matchAll(/page === '([a-z-]+)' && runtime\.mode === 'DISPOSABLE_TEST'/g)].map(m => m[1]),
      ...[...(app.match(/runtime\.mode==='DISPOSABLE_TEST'&&\(([^)]*)\)\?<ConnectedSalesPage/)?.[1] ?? '').matchAll(/page==='([a-z-]+)'/g)].map(m => m[1]),
    ])
    expect([...disposableOnly].sort()).toEqual(['finance-ar', 'finance-cash', 'finance-journal', 'finance-overview', 'finance-payroll', 'finance-reports',
      'operations-attendance', 'sales-allocation', 'sales-invoice', 'sales-payments', 'sales-returns'])
    for (const page of disposableOnly) {
      expect(isScreenHidden('UAT_AUTH_SIMULATION', page), page).toBe(true)
      expect(screenActivation('DISPOSABLE_TEST', page), page).toBe('CONNECTED')
    }
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
    expect(connectedSections('UAT_AUTH_SIMULATION')).not.toContain('Penjualan')
    expect(connectedSections('DISPOSABLE_TEST')).toContain('Penjualan')
    expect(connectedSections('DEMO_SIMULATION')).toEqual([])
  })
})
