import { expect, test, type Page } from '@playwright/test'

const patterns = {
  lucy: 'b4500000-0000-0000-0000-000000000042',
  zodiak: 'b4500000-0000-0000-0000-000000000039',
}

async function openNavigation(page: Page, projectName: string, section: string, item: string) {
  if (projectName === 'mobile-chromium') await page.getByRole('button', { name: 'Buka menu' }).click()
  const target = page.getByRole('button', { name: `• ${item}`, exact: true })
  if (!(await target.isVisible())) await page.getByRole('button', { name: new RegExp(`^${section}`) }).click()
  await target.click()
}

test('pre-CP5 Pola filters preserve one identity through pickup, WIP, Laundry, and QC', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await page.goto('/')

  await openNavigation(page, testInfo.project.name, 'Produksi', 'Bagi Potongan')
  await page.getByLabel('Filter Pola Bagi Potongan').selectOption(patterns.lucy)
  await expect(page.locator('.wip-queue-card')).toHaveCount(1)
  await expect(page.locator('.wip-queue-pattern')).toContainText('LCY-REG · R1 · Kulot Lucy Regular')
  await expect(page.locator('.simulation-pattern-filter')).toContainText('DATA SIMULASI')

  await openNavigation(page, testInfo.project.name, 'Produksi', 'WIP & Sewing')
  await page.getByLabel('Filter Pola WIP').selectOption(patterns.lucy)
  await expect(page.locator('.sewing-parent-card')).toHaveCount(1)
  await expect(page.locator('.sewing-parent-pattern')).toContainText('LCY-REG · R1 · Kulot Lucy Regular')

  await openNavigation(page, testInfo.project.name, 'Produksi', 'Laundry')
  await page.getByLabel('Filter Pola Laundry').selectOption(patterns.zodiak)
  await expect(page.locator('.laundry-parent-card')).toHaveCount(1)
  await expect(page.locator('.laundry-pattern-snapshot').first()).toContainText('ZDK-JUMBO · R3 · Zodiak Jumbo')
  await page.getByRole('button', { name: /Terima kembali/ }).click()
  await expect(page.locator('.laundry-return-card')).toHaveCount(1)
  await expect(page.locator('.laundry-pattern-filter')).toContainText('DATA SIMULASI')

  await openNavigation(page, testInfo.project.name, 'Produksi', 'QC & Final SKU')
  await page.getByLabel('Filter Pola QC').selectOption(patterns.zodiak)
  await expect(page.locator('.qc-browser-list > button')).toHaveCount(1)
  await expect(page.locator('.qc-browser-pattern')).toContainText('ZDK-JUMBO · R3')
  await expect(page.getByText('POLA · DATA SIMULASI', { exact: true })).toBeVisible()

  await testInfo.attach('cutting-bridge-pattern-filter-boundary', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS',
      viewport: testInfo.project.name,
      pickup_filter: 'SIMULATION_ONLY',
      wip_filter: 'SIMULATION_ONLY',
      laundry_filter: 'SIMULATION_ONLY',
      qc_filter: 'SIMULATION_ONLY',
      uat_pickup_and_wip_filter: 'SERVER_SIDE_PATTERN_ID',
      production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
})
