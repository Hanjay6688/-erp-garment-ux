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
test('yield analyzer compares exact mixes with optional width and withholds unsupported all-30', async ({ page }, testInfo) => {
  await fixture(page)
  const card = page.getByRole('complementary', { name: 'Analyzer hasil potong' })
  await expect(card.getByLabel('Lebar efektif (cm) · opsional')).toHaveValue('')
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-range]')).toContainText('80–120 PCS')
  await expect(card.getByText('Basis: tanpa lebar.', { exact: false })).toBeVisible()
  await card.getByRole('combobox', { name: /^Kombinasi ukuran contoh/ }).selectOption('unique')
  await expect(card.locator('[data-yield-range]')).toHaveCount(0)
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-range]')).toContainText('74–114 PCS')
  await card.getByRole('combobox', { name: /^Kombinasi ukuran contoh/ }).selectOption('all30')
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-range]')).toHaveCount(0)
  await card.getByRole('combobox', { name: /^Kombinasi ukuran contoh/ }).selectOption('small')
  await card.getByLabel('Lebar efektif (cm) · opsional').fill('150')
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-range]')).toContainText('90–110 PCS')
  await card.getByLabel('Lebar efektif (cm) · opsional').clear()
  await expect(card.locator('[data-yield-range]')).toHaveCount(0)
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-range]')).toContainText('80–120 PCS')
  await card.getByText('Kenapa & apa yang perlu dicek?', { exact: true }).click()
  const screenshot = testInfo.outputPath('analyzer-width-optional.png'); await card.screenshot({ path: screenshot }); await testInfo.attach('Analyzer tanpa lebar', { path: screenshot, contentType: 'image/png' })
})
test('yield analyzer separates a short measured roll, a narrow batch and unexplained low yield', async ({ page }) => {
  await fixture(page)
  const card = page.getByRole('complementary', { name: 'Analyzer hasil potong' })
  const select = card.getByRole('combobox', { name: /^Kondisi analyzer contoh/ })
  await select.selectOption('SHORT_ROLL'); await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await card.getByText('Kenapa & apa yang perlu dicek?', { exact: true }).click(); await expect(card).toContainText('Penyebab selisih panjang belum diketahui')
  await select.selectOption('NARROW_BATCH'); await card.getByLabel('Lebar efektif (cm) · opsional').fill('140')
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await card.getByText('Kenapa & apa yang perlu dicek?', { exact: true }).click(); await expect(card).toContainText('Lebar batch yang diisi 140 cm')
  await select.selectOption('LOW'); await card.getByLabel('Lebar efektif (cm) · opsional').clear()
  await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
  await expect(card.locator('[data-yield-status]')).toContainText('Abnormal rendah')
  await card.getByText('Kenapa & apa yang perlu dicek?', { exact: true }).click(); await expect(card).toContainText('Lebar belum tercatat')
  for (const mode of ['INSUFFICIENT', 'INCOMPLETE', 'UNSEEN_COMBINATION', 'ERROR']) {
    await select.selectOption(mode); await card.getByRole('button', { name: 'Muat contoh analyzer', exact: true }).click()
    await expect(card.locator('[data-yield-range]')).toHaveCount(0)
  }
  await page.getByLabel('Hak akses contoh').selectOption('DENIED'); await expect(card).toHaveCount(0)
})
