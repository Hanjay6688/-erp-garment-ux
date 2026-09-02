import { expect, test, type Page } from '@playwright/test'

async function openNavigation(page: Page, projectName: string, section: string, item: string) {
  if (projectName === 'mobile-chromium') await page.getByRole('button', { name: 'Buka menu' }).click()
  await page.getByRole('button', { name: new RegExp(`^${section}`) }).click()
  await page.getByRole('button', { name: new RegExp(`${item}$`) }).click()
}

test('CP4.5 Master Pola grows from operational need with fail-closed Potongan selection', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await page.goto('/')
  await expect(page.locator('.top-title strong')).toHaveText('Dashboard')

  await openNavigation(page, testInfo.project.name, 'Produksi', 'Buat Potongan')
  await expect(page.getByRole('heading', { name: 'Buat Potongan' })).toBeVisible()
  await expect(page.getByText('POLA · WAJIB', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /Simpan Potongan ke WIP/ })).toBeDisabled()

  await page.getByRole('option').first().click()
  await expect(page.getByRole('button', { name: /Simpan Potongan ke WIP/ })).toBeEnabled()
  await expect(page.getByText(/MASTER POLA SIMULATION/)).toBeVisible()

  await page.getByRole('button', { name: 'Ganti Pola' }).click()
  await expect(page.getByRole('button', { name: /Simpan Potongan ke WIP/ })).toBeDisabled()
  await page.getByRole('button', { name: /Tambah Pola Baru/ }).click()
  await page.getByLabel('Kode', { exact: true }).fill('AUTO')
  await page.getByLabel('Revisi', { exact: true }).fill('R3')
  await page.getByLabel('Nama', { exact: true }).fill('Pola Auto Pilih')
  await page.getByRole('button', { name: 'Buat & pilih' }).click()
  await expect(page.locator('.cutting-pattern-picker > header').getByText('AUTO · R3', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /Simpan Potongan ke WIP/ })).toBeEnabled()
  await testInfo.attach(`cutting-${testInfo.project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await openNavigation(page, testInfo.project.name, 'Master Data', 'Pola')
  await expect(page.getByRole('heading', { name: 'Pola', exact: true })).toBeVisible()
  await expect(page.getByPlaceholder('Cari kode, revisi, atau nama Pola…')).toBeVisible()
  await expect(page.getByText(/Potongan baru wajib memakai pattern_id/)).toBeVisible()
  await page.getByRole('button', { name: 'Nonaktif', exact: true }).click()
  await page.getByPlaceholder('Cari kode, revisi, atau nama Pola…').fill('OLD R1')
  await expect(page.getByText('OLD · R1', { exact: true })).toBeVisible()
  await testInfo.attach(`pattern-${testInfo.project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await openNavigation(page, testInfo.project.name, 'Pengaturan & Audit', 'Pengguna & Hak Akses')
  await expect(page.getByRole('heading', { name: 'Pengguna & Hak Akses' })).toBeVisible()
  await expect(page.getByText('DATA SIMULASI', { exact: true })).toBeVisible()
  await expect(page.getByText(/request server berikutnya/)).toBeVisible()

  await testInfo.attach(`access-${testInfo.project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
  await testInfo.attach('cp45-boundary', {
    body: Buffer.from(JSON.stringify({
      status: 'PASS',
      viewport: testInfo.project.name,
      master_pattern_source: 'erp_save_pattern_v1',
      cutting_pattern_required: true,
      production_go: false,
    }, null, 2)),
    contentType: 'application/json',
  })
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
})
