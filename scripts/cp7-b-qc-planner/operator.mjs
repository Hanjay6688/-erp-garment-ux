// Shared UI actions. The caller supplies an isolated authenticated browser or a loopback fixture.
export const qcRpc = 'erp_save_laundry_qc_action_v1'
export const reportRpc = 'erp_cp7_publish_report_v2'
export const profileRpc = 'erp_cp7_save_planning_profile_v1'
export const autoRpc = 'erp_cp7_request_staged_analysis_v1'
export const button = (scope, name) => scope.getByRole('button', { name, exact: true })
export const region = (scope, name) => scope.getByRole('region', { name, exact: true })
export const initial = page => region(page, 'Analisis awal otomatis')
export const analysis = page => region(page, 'Analisis ERP bersama')
export const report = page => region(page, 'Laporan analisis bertahap')

export async function navigate(page, group, label) {
  const sidebar = page.locator('.sidebar')
  const parent = sidebar.locator('.nav-main').filter({ hasText: group }).first()
  await parent.waitFor({ state: 'attached' })
  const menu = button(page, 'Buka menu')
  const link = button(sidebar, '• ' + label)
  if (await menu.isVisible() && !(await sidebar.evaluate(el => el.classList.contains('sidebar-open')))) await menu.click()
  if (!await link.isVisible()) await parent.click()
  await link.click()
}
export const openWarehouse = page => navigate(page, 'Gudang', 'Ringkasan Barang Jadi')

export async function openAnalysisPanel(page, q) {
  await openWarehouse(page)
  const history = region(page, 'Data permintaan ERP')
  await button(history, 'Data permintaan & stok').click()
  // Set the end first so changing the start never depends on an invalid range.
  await history.getByLabel('Permintaan sampai tanggal', { exact: true }).fill(q.through_date)
  await history.getByLabel('Permintaan dari tanggal', { exact: true }).fill(q.from_date)
  await history.getByRole('combobox', { name: 'Pengelompokan', exact: true }).selectOption(q.group_mode)
  await button(history, 'Analisis, laporan & pengingat seluruh produk').click()
}

export async function openManualAnalysis(page, q) {
  await openAnalysisPanel(page, q)
  await button(analysis(page), 'Analisis bertahap (hingga 5.000 target)').click()
}

export async function openCurrentInitial(page, done) {
  await button(initial(page), done ? 'Buka hasil analisis awal' : 'Buka analisis awal yang berjalan').click()
}

export async function fillPartialQc(page, f, expect) {
  await navigate(page, 'Produksi', 'QC & Final SKU')
  await expect(page.getByRole('heading', { name: 'QC & Final SKU', exact: true })).toBeVisible()
  await expect(button(page, 'Muat ulang data')).toBeEnabled()
  await page.locator('nav.clq-tabs input').fill(f.poNumber)
  const selection = page.getByRole('combobox', { name: /^POTONGAN DENGAN GOOD LAUNDRY SIAP QC/ })
  await expect(selection.locator('option[value="' + f.group + '"]')).toHaveCount(1)
  await selection.selectOption(f.group)
  await page.getByLabel('LOKASI FG TUJUAN', { exact: true }).selectOption(f.location)
  await page.getByLabel('WAKTU FISIK QC', { exact: true }).fill(f.qcLocal)
  await page.getByLabel('ALASAN / BUKTI HASIL QC', { exact: true }).fill('Periksa hasil QC tiga potong dari delapan')
  const row = page.locator('.clq-qc-editor article').filter({ hasText: 'Ukuran ' + f.sizeCode })
  await row.getByLabel('Good final size ' + f.sizeCode, { exact: true }).fill('3')
  await expect(row.getByLabel('BS QC size ' + f.sizeCode, { exact: true })).toHaveValue('0')
  await row.getByLabel('Cari Final SKU size ' + f.sizeCode, { exact: true }).fill(f.sku)
  await button(row, 'Cari SKU').click()
  const sku = row.getByRole('combobox', { name: 'Final SKU size ' + f.sizeCode, exact: true })
  await expect(sku.locator('option[value="' + f.product + '"]')).toHaveCount(1)
  await sku.selectOption(f.product)
  await expect(page.locator('.clq-impact')).toContainText('Good 3 · BS 0 · dipilih 3 dari 8 pcs terlihat')
  await expect(page.locator('.clq-impact')).toContainText('Sebagian barang siap QC dipilih.')
  const post = button(page, 'Post QC + Final SKU atomic')
  await expect(post).toBeDisabled()
  await page.getByRole('checkbox', { name: /^Saya sudah mencocokkan hasil QC fisik/ }).check()
  await expect(post).toBeEnabled()
  return post
}

export async function prepareReport(panel, title, { revision = false } = {}) {
  if (!revision) await panel.getByLabel('Jenis laporan bertahap', { exact: true }).selectOption('PERIOD')
  await panel.getByLabel('Judul laporan bertahap', { exact: true }).fill(title)
  await panel.getByLabel('Alasan laporan bertahap', { exact: true }).fill('Cocokkan periode, stok dan buku besar dari hasil QC')
  await panel.getByRole('checkbox', { name: 'Sertakan keuangan dan HPP pada laporan bertahap', exact: true }).check()
  await panel.getByRole('checkbox', { name: 'Laporan bertahap sudah ditinjau', exact: true }).check()
  return button(panel, revision ? 'Simpan revisi laporan bertahap' : 'Buat laporan dari analisis ini')
}

export async function selectSecondTarget(page, sku, expect) {
  await button(initial(page), 'Lengkapi target ' + sku).click()
  const profile = region(page, 'Aturan dan target produksi')
  await expect(profile.getByRole('heading', { name: sku, exact: true })).toBeVisible()
  await profile.getByLabel('Dasar permintaan', { exact: true }).selectOption('SELECTED_MANUAL')
  await profile.getByLabel('Permintaan pilihan PCS per hari', { exact: true }).fill('10')
  await profile.getByLabel('Minimal hari riwayat tersedia', { exact: true }).fill('14')
  await profile.getByLabel('Waktu proses pilihan (hari kalender)', { exact: true }).fill('3')
  await profile.getByLabel('Jarak pemeriksaan (hari kalender)', { exact: true }).fill('7')
  await profile.getByLabel('Cadangan waktu (hari kalender)', { exact: true }).fill('2')
  await profile.getByLabel('Alasan aturan target', { exact: true }).fill('Uji aturan SKU kedua di salinan disposable')
  return button(profile, 'Simpan aturan target')
}
