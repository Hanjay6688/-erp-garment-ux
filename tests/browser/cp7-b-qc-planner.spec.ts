import { expect, test, type Page } from '@playwright/test'
import {
  autoRpc, button, fillPartialQc, initial, navigate, openAnalysisPanel, openCurrentInitial, openManualAnalysis, openWarehouse,
  prepareReport, profileRpc, qcRpc, region, report, reportRpc, selectSecondTarget,
} from '../../scripts/cp7-b-qc-planner/operator.mjs'
import { capture, mockApp, signIn, verifyTransport } from './support/cp7-b-loopback-fixture'
import { plannerFixture, plannerJobId, qcCase, qcReportFixture, qcReportTitles, query, rights, second } from './support/cp7-b-qc-planner-fixture'

const staged = (page: Page) => region(page, 'Hasil analisis bertahap')
const archive = (page: Page) => report(page).getByRole('article', { name: 'Isi laporan bertahap' })
const summary = (page: Page) => archive(page).getByLabel('Ringkasan laporan bertahap')
const section = (page: Page) => archive(page).getByLabel('Bagian laporan bertahap', { exact: true })

async function expectWip(page: Page, remaining: number) {
  await navigate(page, 'Produksi', 'WIP & Sewing')
  const row = page.locator('.cwip-list > article').filter({ hasText: qcCase.poNumber })
  await expect(row).toHaveCount(1)
  await expect(row.locator('.cwip-facts > span').filter({ hasText: 'FINAL SKU TERSISA' }).locator('strong')).toHaveText(remaining + ' pcs')
}

async function expectReport(page: Page, revision: 1 | 2) {
  const title = qcReportTitles[revision - 1]
  await expect(archive(page).getByRole('heading', { name: title + ' · versi ' + revision, exact: true })).toBeVisible()
  await expect(archive(page)).toContainText('Keuangan dan HPP dari laporan keuangan ERP untuk tanggal itu.')
  await expect(archive(page)).toContainText('tanggal laporan ' + query.through_date)
  await expect(summary(page)).toContainText('LAPORAN PERIODE · ' + query.from_date + ' s.d. ' + query.through_date)
  await expect(summary(page)).toContainText(revision === 1 ? 'Nilai barang dalam proses: 288.00 IDR' : 'Nilai barang dalam proses: 180.00 IDR')
  await expect(summary(page)).toContainText(revision === 1 ? 'Nilai persediaan barang jadi: 0.00 IDR' : 'Nilai persediaan barang jadi: 108.00 IDR')
  await expect(summary(page)).toContainText('HPP penjualan tercatat: 0.00 IDR')
  await expect(summary(page)).toContainText('siap Belum diketahui')
  await button(archive(page), 'Buka bagian laporan').click()
  await expect(section(page)).toContainText(qcCase.sku + ' ·')
  await expect(section(page)).toContainText('size ' + qcCase.sizeCode)
  await expect(section(page)).toContainText('stok fisik saat analisis 0 PCS')
  await expect(section(page)).toContainText('stok fisik aktual ' + (revision === 1 ? '0' : '3') + ' PCS')
}

test('QC 3 dari 8, saldo WIP dan lot FG, laporan INCLUDED, arsip lama dan kegagalan AI', async ({ page, context }, info) => {
  const fixture = qcReportFixture()
  const mock = await mockApp(context, { role: 'OWNER', rights, actor: fixture.actor, resolve: fixture.resolve })
  await signIn(page)

  await expectWip(page, 8)
  await openManualAnalysis(page, query)
  await expect(page.getByText('Tidak ada stok yang cocok.', { exact: true })).toBeVisible()
  await expect(region(page, 'Kesegaran data')).toHaveAttribute('data-freshness-state', 'NO_RECORDED_CHANGE')
  const runId = await staged(page).getAttribute('data-run-id')
  const identityHash = await staged(page).getAttribute('data-identity-hash')
  expect(runId).toBeTruthy()
  expect(identityHash).toMatch(/^[a-f0-9]{64}$/)
  await (await prepareReport(report(page), qcReportTitles[0])).click()
  await expectReport(page, 1)
  const before = {
    id: await archive(page).getAttribute('data-report-id'),
    summary: await summary(page).textContent(),
    section: await section(page).textContent(),
    hash: fixture.documents[0].doc.report_hash,
  }
  await capture(page, info, 'laporan-sebelum-qc')

  const post = await fillPartialQc(page, qcCase, expect)
  await post.evaluate((el: HTMLButtonElement) => { el.click(); el.click() })
  await expect.poll(() => fixture.effects.qc).toBe(1)
  await expect(post).toBeDisabled()
  await expectWip(page, 5)
  await openAnalysisPanel(page, query)
  const stock = page.locator('.cfg-position').filter({ has: page.getByRole('heading', { name: qcCase.sku, exact: true }) })
  await expect(stock).toHaveCount(1)
  await expect(stock.locator('.cfg-size')).toHaveText(qcCase.sizeCode)
  await expect(stock).toContainText(qcCase.locationName + ' · GRADE A · ' + qcCase.lotNumber)
  await expect(stock.getByRole('definition').first()).toHaveText('3')
  await expect(stock).toContainText(/Nilai fisik Rp108(?:,00)? · HPP Rp36(?:,00)? \/ PCS/)
  expect(5 + Number(await stock.getByRole('definition').first().textContent())).toBe(8)
  await button(stock, 'Lihat mutasi ' + qcCase.sku + ' · ' + qcCase.sizeCode).click()
  const movement = page.locator('[data-fg-movement-id="' + qcCase.movement + '"]')
  await expect(movement).toContainText('Hasil QC')
  await expect(movement.getByRole('definition').first()).toHaveText('3')
  await capture(page, info, 'lot-dan-mutasi-fg')

  await expect(staged(page)).toHaveAttribute('data-run-id', runId!)
  await expect(staged(page)).toHaveAttribute('data-identity-hash', identityHash!)
  await expect(region(page, 'Kesegaran data')).toHaveAttribute('data-freshness-state', 'CHANGES_RECORDED')
  await button(staged(page), 'Cek sumber').click()
  await expect(region(page, 'Kesegaran data')).toHaveAttribute('data-freshness-state', 'STALE_VERIFIED')
  await button(report(page), 'Muat laporan bertahap tersimpan').click()
  await report(page).getByRole('button', { name: /^Buka laporan bertahap/ }).filter({ hasText: qcReportTitles[0] }).click()
  await button(archive(page), 'Buat revisi dari laporan ini').click()
  await (await prepareReport(report(page), qcReportTitles[1], { revision: true })).click()
  await expectReport(page, 2)
  expect(fixture.documents[1].doc.report_hash).not.toBe(before.hash)
  await capture(page, info, 'laporan-sesudah-qc')

  await button(report(page), 'Muat laporan bertahap tersimpan').click()
  await report(page).getByRole('button', { name: /^Buka laporan bertahap/ }).filter({ hasText: qcReportTitles[0] }).click()
  await expectReport(page, 1)
  await expect(archive(page)).toHaveAttribute('data-report-id', before.id!)
  await expect(archive(page)).toContainText('Versi lama; revisi berikutnya sudah tersedia.')
  expect(await summary(page).textContent()).toBe(before.summary)
  expect(await section(page).textContent()).toBe(before.section)
  expect(fixture.documents[0].doc.report_hash).toBe(before.hash)

  const ai = region(page, 'Tanya AI dari analisis bertahap')
  await ai.getByLabel('Pertanyaan untuk AI dari analisis bertahap').fill('Apa yang berubah setelah QC?')
  await button(ai, 'Periksa & salin pertanyaan untuk AI').click()
  await expect(ai.getByRole('alert')).toBeVisible()
  await expect(ai.getByRole('link', { name: /Buka ChatGPT/ })).toHaveCount(0)
  await expect(archive(page)).toHaveAttribute('data-report-id', before.id!)
  expect(await summary(page).textContent()).toBe(before.summary)
  await capture(page, info, 'arsip-lama-saat-ai-gagal')

  fixture.refuseNextPublication()
  await (await prepareReport(report(page), 'Publikasi harus ditolak')).click()
  await expect(report(page).getByRole('alert')).toContainText('Analisis bertahap di layar tidak sama dengan yang tersimpan di server.')
  await expect(archive(page)).toHaveCount(0)
  expect(fixture.effects).toEqual({ analysis: 1, qc: 1, publications: 2, refused: 1 })
  const posts = mock.calls.filter(c => c.name === qcRpc)
  expect(posts).toHaveLength(1)
  expect(posts[0].args.p_client_request_id).toMatch(/^[a-f0-9-]{36}$/)
  expect(mock.calls.filter(c => c.name === reportRpc)).toHaveLength(3)
  await verifyTransport(mock, info, [/503/, /400/])
})

test('Planner menyimpan SKU kedua, membaca satu job setelah tutup, dan menyembunyikan hasil saat izin dicabut', async ({ page, context }, info) => {
  const fixture = await plannerFixture()
  const mock = await mockApp(context, { role: info.project.name === 'desktop' ? 'OWNER' : 'ADMIN', rights, actor: fixture.run.actor, resolve: fixture.resolve })
  await signIn(page)
  await openWarehouse(page)
  await expect(button(initial(page), 'Lengkapi target B-PLAN-001')).toBeVisible()
  await expect(button(initial(page), 'Lengkapi target ' + second.sku)).toBeVisible()
  await (await selectSecondTarget(page, second.sku, expect)).click()
  await expect(initial(page)).toContainText('Server sedang memproses; halaman boleh ditutup.')
  await expect(initial(page)).toContainText('unit 12 dari 55')
  await openCurrentInitial(page, false)
  const statusCalls = () => mock.calls.filter(c => c.name === 'erp_cp7_get_staged_analysis_v1').map(c => c.args.p_request)
  await expect.poll(statusCalls).toContain(plannerJobId)
  await capture(page, info, 'planner-job-berjalan')
  await page.close()
  fixture.finish()

  const reopened = await context.newPage()
  await reopened.goto('/')
  await openWarehouse(reopened)
  await expect(initial(reopened)).toContainText('Analisis awal sudah selesai.')
  await expect(initial(reopened)).toContainText('Periode ' + fixture.run.query.from_date + ' sampai ' + fixture.run.query.through_date)
  await openCurrentInitial(reopened, true)
  await expect(staged(reopened)).toHaveAttribute('data-run-id', fixture.run.runId)
  await expect(staged(reopened)).toHaveAttribute('data-identity-hash', fixture.run.identityHash)
  const row = staged(reopened).locator('[data-analysis-target="' + second.rootId + ':' + second.sizeId + '"]')
  await expect(row).toContainText(second.sku)
  await expect(row.locator('[data-label="Stok fisik"]')).toHaveText('17 PCS')
  await expect(row.locator('[data-label="Target"]')).toHaveText('120 PCS · asumsi')
  await expect(row.locator('[data-label="Produksi baru layak"]')).toHaveText('Belum diketahui')
  await expect(staged(reopened).getByRole('row').filter({ hasText: 'B-PLAN-001' }).locator('[data-label="Target"]')).toHaveText('Belum diketahui')
  await capture(reopened, info, 'planner-hasil-yang-sama')

  fixture.revoke()
  await button(initial(reopened), 'Periksa kesiapan lagi').click()
  await expect(initial(reopened).getByRole('alert')).toBeVisible()
  await expect(staged(reopened)).toHaveCount(0)
  await expect(button(initial(reopened), 'Buka hasil analisis awal')).toHaveCount(0)
  await capture(reopened, info, 'planner-izin-dicabut')
  expect(fixture.effects).toEqual({ profiles: 1, jobs: 1 })
  expect(mock.calls.filter(c => c.name === profileRpc)).toHaveLength(1)
  expect(mock.calls.filter(c => c.name === autoRpc && c.args.p_query.initial_auto === 'ENSURE')).toHaveLength(1)
  expect(statusCalls().length).toBeGreaterThanOrEqual(2)
  expect(new Set(statusCalls())).toEqual(new Set([plannerJobId]))
  await verifyTransport(mock, info, [/403/])
})
