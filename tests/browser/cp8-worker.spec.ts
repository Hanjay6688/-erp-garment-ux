import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import JSZip from 'jszip'

async function openGroup(page: Page, name: string) {
  const menu = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  await page.locator('aside.sidebar').getByRole('button', { name: new RegExp('^' + name) }).click()
}
async function pageFits(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true)
}

for (const width of [320, 390, 768, 1440]) {
  test(`Gladi Worker pada ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const crashes: string[] = []
    page.on('pageerror', error => crashes.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('heading',{ name:'Veni. Vidi. Vici. ERP' })).toBeVisible()
    await expect(page.locator('.kpi-grid')).toContainText('Rp284,6 jt')
    await expect(page.locator('html')).toHaveClass(/ux-rapih/)
    await expect(page.locator('.topbar')).toHaveCSS('border-bottom-color','rgb(47, 59, 90)')
    await pageFits(page)
    await page.getByRole('button',{name:'Input penjualan'}).click()
    await page.getByRole('button',{name:'Review invoice'}).click()
    await expect(page.getByRole('dialog')).toContainText('72 pcs')
    await page.getByRole('button',{name:'Simpan Draft + reserve'}).click()
    await expect(page.getByText(/Draft tersimpan\. Mutasi RESERVE INVOICE/)).toContainText('−72 pcs')
    await openGroup(page,'Keuangan')
    await page.getByRole('button',{name:/• Kas & Bank/}).click()
    await expect(page.locator('.biz-table.cash > article').first()).toBeVisible()
    await pageFits(page)
    await openGroup(page,'Pengaturan & Audit')
    await page.getByRole('button',{name:/• Impor data awal/}).click()
    await page.getByRole('button',{name:'Coba data contoh'}).click()
    await expect(page.getByRole('status')).toContainText('9 baris dalam 5 tab')
    await pageFits(page)
    const saved = page.waitForEvent('download')
    await page.getByRole('button',{name:'Unduh paket CSV'}).click()
    const download = await saved
    const zip = await JSZip.loadAsync(await readFile((await download.path())!))
    expect(Object.keys(zip.files).filter(f => f.endsWith('.csv'))).toHaveLength(5)
    expect(await zip.file('CUSTOMER.csv')!.async('string')).toContain('00017')
    await openGroup(page,'Analisis & Planner')
    await page.getByRole('link',{name:'Business Report'}).click()
    await expect(page.getByRole('table')).toContainText('Kebutuhan dasar')
    await expect(page.getByRole('table')).toContainText('18 PCS')
    await page.reload()
    await expect(page.getByRole('table')).toContainText('18 PCS')
    await pageFits(page)
    await page.getByRole('button',{name:'Prioritas produksi'}).click()
    await expect(page.getByRole('heading',{name:'Tindakan yang perlu ditinjau'})).toBeVisible()
    await page.getByRole('button',{name:'Lihat detail'}).first().click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button',{name:'Tutup detail'}).click()
    expect(crashes).toEqual([])
  })
}
