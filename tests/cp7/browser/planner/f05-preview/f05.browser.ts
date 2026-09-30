import { test, expect, type Page } from '@playwright/test'

const url = '/tests/cp7/browser/planner/f05-preview/index.html'
async function menu(page: Page, name: string) { await page.getByRole('navigation', { name: 'Menu F05' }).getByRole('button', { name: new RegExp(name) }).click() }
async function fixture(page: Page, mode = 'FRAMEWORK') {
  await page.getByRole('combobox', { name: /^Data contoh/ }).selectOption(mode)
  await expect(page.getByText('Memuat snapshot contoh…', { exact: true })).toHaveCount(0)
}
test.beforeEach(async ({ page }) => { await page.goto(url) })
test('four menus handle empty, partial, stale, error and denied without fabricating a result', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'Cangkang siap menerima data' })).toBeVisible()
  for (const name of ['Panel produksi', 'Business Report', 'Reminder', 'Tanya AI']) {
    await menu(page, name); await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    for (const mode of ['PARTIAL', 'ERROR', 'EMPTY']) {
      await fixture(page, mode); await expect(page.locator('[data-fact-state]')).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Terapkan rencana', exact: true })).toHaveCount(0)
    }
    await fixture(page, 'STALE'); await expect(page.getByText('Contoh data berubah:', { exact: false }).first()).toBeVisible()
  }
  await page.getByLabel('Hak akses contoh').selectOption('DENIED')
  await expect(page.getByRole('heading', { name: 'Akses ditolak', exact: true })).toBeVisible()
  await expect(page.locator('textarea')).toHaveCount(0)
  await expect(page.getByText('fixture-O02-run1', { exact: true })).toHaveCount(0)
})
test('SKU details show physical size, reasons, WIP basis and unknown materials; draft survives panel and navigation', async ({ page }) => {
  await fixture(page)
  await page.getByLabel('Jumlah draft Buat').fill('17'); await page.getByLabel('Catatan draft').fill('Jangan timpa draft')
  await page.getByRole('button', { name: 'Buka panel bersama', exact: true }).click()
  await page.getByRole('button', { name: 'Tutup panel bersama', exact: true }).click()
  await page.getByRole('button', { name: 'Lihat alasan & sumber', exact: true }).click()
  const detail = page.getByRole('article', { name: 'Rincian SKU' })
  await expect(detail).toContainText('ukuran 30'); await expect(detail).toContainText('basis ASSUMED')
  await expect(detail).toContainText('MATERIAL_REMAINING_UNKNOWN')
  await expect(detail.getByRole('button', { name: 'Terapkan rencana', exact: true })).toBeDisabled()
  await page.getByLabel('Cari SKU / ukuran').fill('missing'); await expect(page.getByRole('heading', { name: 'Tidak ada SKU yang cocok' })).toBeVisible()
  await menu(page, 'Business Report'); await menu(page, 'Panel produksi')
  await expect(page.getByLabel('Jumlah draft Buat')).toHaveValue('17'); await expect(page.getByLabel('Catatan draft')).toHaveValue('Jangan timpa draft')
})
test('report archives remain immutable, revisions are separate and unsupported periods are withheld', async ({ page }) => {
  await fixture(page); await menu(page, 'Business Report')
  await page.getByRole('button', { name: 'Buat arsip contoh', exact: true }).click()
  const old = await page.getByLabel('Isi arsip contoh').inputValue()
  await page.getByRole('button', { name: 'Siapkan revisi terpisah', exact: true }).click()
  await page.getByRole('button', { name: 'Buat revisi contoh', exact: true }).click()
  await expect(page.getByRole('button', { name: 'local-report-2 · revisi local-report-1', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'local-report-1', exact: true }).click(); await expect(page.getByLabel('Isi arsip contoh')).toHaveValue(old)
  const downloaded = page.waitForEvent('download'); await page.getByRole('button', { name: 'Ekspor arsip ini', exact: true }).click()
  await expect((await downloaded).suggestedFilename()).toBe('local-report-1-CONTOH.txt')
  await fixture(page, 'STALE'); await expect(page.getByLabel('Isi arsip contoh')).toHaveValue(old)
  await expect(page.getByRole('button', { name: 'Buat arsip contoh', exact: true })).toBeDisabled()
  await page.getByLabel('Jenis periode').selectOption('weekly'); await page.getByRole('button', { name: 'Terapkan periode', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Laporan periode ditahan' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Buat arsip contoh', exact: true })).toHaveCount(0)
})
test('ACK and snooze keep source condition; queue deduplicates and never sends', async ({ page }) => {
  await fixture(page); await menu(page, 'Reminder')
  const episode = page.locator('article').filter({ has: page.locator('[data-condition="unknown-Utang"]') })
  await episode.getByRole('button', { name: 'Tandai dibaca', exact: true }).click()
  await expect(episode.locator('[data-attention]')).toHaveText('ACK'); await expect(episode.locator('[data-condition]')).toHaveText('UNKNOWN')
  await episode.getByRole('button', { name: 'Tunda perhatian', exact: true }).click()
  await expect(episode.locator('[data-attention]')).toHaveText('SNOOZED'); await expect(episode.locator('[data-condition]')).toHaveText('UNKNOWN')
  await episode.getByRole('button', { name: 'Antrekan simulasi', exact: true }).click(); await episode.getByRole('button', { name: 'Antrekan simulasi', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Antrean simulasi (1)', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Aktifkan pengiriman WA', exact: true })).toBeDisabled()
  await page.getByLabel('Judul reminder').fill('Periksa aksesori contoh'); await page.getByLabel('Jadwal manual · Asia/Jakarta').fill('2026-10-01T08:00')
  await page.getByRole('button', { name: 'Simpan reminder contoh', exact: true }).click(); await page.getByRole('button', { name: 'Selesai manual', exact: true }).click()
  await expect(page.getByText('2026-10-01T08:00 · Asia/Jakarta · DONE', { exact: true })).toBeVisible()
})
test('copy denial and popup blocking show manual fallback; scope restrictions purge sensitive payloads', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async () => { throw new Error('denied') } } })
    window.open = () => null
  })
  await page.reload(); await fixture(page); await menu(page, 'Tanya AI')
  await page.getByRole('button', { name: 'Salin prompt', exact: true }).click(); await expect(page.getByText('Salin otomatis gagal.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Buka ChatGPT', exact: true }).click(); await expect(page.getByText('Tab diblokir.', { exact: false })).toBeVisible()
  await expect(page.getByLabel('Prompt berizin')).toHaveValue(/Sumber bersama tidak boleh dipakai berulang/)
  await page.getByLabel('Hak akses contoh').selectOption('OPERATIONS')
  await expect(page.getByLabel('Prompt berizin')).not.toHaveValue(/GROSS_MARGIN/)
  await page.getByLabel('Hak akses contoh').selectOption('DENIED'); await expect(page.locator('textarea')).toHaveCount(0)
})
test('clipboard promise success path confirms completion and opens a payload-free safe tab', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (text: string) => { (window as Window & { copied?: string }).copied = text } } })
  })
  await page.reload(); await fixture(page); await menu(page, 'Tanya AI')
  await page.getByRole('button', { name: 'Salin prompt', exact: true }).click(); await expect(page.getByText('Prompt berhasil disalin.', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => (window as Window & { copied?: string }).copied)).toBe(await page.getByLabel('Prompt berizin').inputValue())
  await page.evaluate(() => {
    const fake = { opener: window, location: { href: 'about:blank' } }
    window.open = () => { (window as Window & { opened?: typeof fake }).opened = fake; return fake as unknown as Window }
  })
  await page.getByRole('button', { name: 'Buka ChatGPT', exact: true }).click()
  expect(await page.evaluate(() => { const popup = (window as Window & { opened?: { opener: unknown; location: { href: string } } }).opened; return { opener: popup?.opener, href: popup?.location.href } })).toEqual({ opener: null, href: 'https://chatgpt.com/' })
})
test('all four views render without console errors, horizontal overflow or ERP/external requests', async ({ page }, testInfo) => {
  const errors: string[] = []; const external: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:4195/')) external.push(request.url()) })
  await page.reload(); await fixture(page)
  for (const name of ['Panel produksi', 'Business Report', 'Reminder', 'Tanya AI']) {
    await menu(page, name); await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const screenshot = testInfo.outputPath(`${name.replaceAll(' ', '-')}.png`)
    await page.screenshot({ path: screenshot, fullPage: true }); await testInfo.attach(name, { path: screenshot, contentType: 'image/png' })
  }
  expect(errors).toEqual([]); expect(external).toEqual([])
  await expect(page.locator('vite-error-overlay')).toHaveCount(0)
})
