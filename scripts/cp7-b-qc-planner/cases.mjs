// Two focused cases for cp6_auditor_browser_host.mjs on a disposable copy.
import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import {
  autoRpc, button, fillPartialQc, initial, navigate, openAnalysisPanel, openCurrentInitial, openManualAnalysis,
  openWarehouse, prepareReport, profileRpc, qcRpc, region, report, reportRpc, selectSecondTarget,
} from './operator.mjs'

const fixtureScript = fileURLToPath(new URL('./native_fixture.py', import.meta.url))
const run = promisify(execFile)
const output = 'cp6-proof/t3/B_QC_SNAPSHOT_PLANNER'
const result = page => region(page, 'Hasil analisis bertahap')
const archive = page => report(page).getByRole('article', { name: 'Isi laporan bertahap' })
const summary = page => archive(page).getByLabel('Ringkasan laporan bertahap')
const hash = text => createHash('sha256').update(text).digest('hex')

async function native(operation, args = {}) {
  const proc = run('python', [fixtureScript, operation], { maxBuffer: 8 * 1024 * 1024 })
  proc.child.stdin.end(JSON.stringify(args))
  try {
    return JSON.parse((await proc).stdout)
  } catch (error) {
    throw Error((error.stderr || error.message).trim())
  }
}

async function rpc(user, name, args) {
  const response = await user.rpc(name, args)
  assert.equal(response.status, 200, JSON.stringify({ name, ...response }))
  return response.body
}

async function screenshot(page, name, files) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, name)
  const path = output + '/' + name + '.png'
  await page.screenshot({ path, fullPage: true, scale: 'css' })
  files.push(path)
}

async function trackedCase(ui, id, role, options, exercise) {
  await mkdir(output, { recursive: true })
  const evidence = { screenshots: [] }
  let user
  try {
    user = await ui.login(role, { label: id, ...options })
    return { status: 'PASS', actual_auth: true, real_postgrest: true, ...await exercise(user, evidence) }
  } catch (error) {
    const message = String(error.stack || error)
    const path = output + '/' + id + '_FIRST_FAILURE.json'
    await writeFile(path, JSON.stringify({ ...evidence, error: message }, null, 2) + '\n', { flag: 'wx' })
      .catch(failure => { if (failure.code !== 'EEXIST') throw failure })
    return { status: message.includes('BLOCKED:') ? 'INCOMPLETE' : 'FAIL', error: message, first_failure: path }
  } finally {
    await user?.context.close()
  }
}

async function action(page, rpcName, click, pred = () => true) {
  const received = page.waitForResponse(r => r.url().endsWith('/rpc/' + rpcName) && pred(r.request().postDataJSON()), { timeout: 30_000 })
  const [response] = await Promise.all([received, click()])
  const body = await response.json()
  assert.equal(response.status(), 200, JSON.stringify({ rpcName, body }))
  return { args: response.request().postDataJSON(), body }
}

async function showWip(ui, page, f, count) {
  await navigate(page, 'Produksi', 'WIP & Sewing')
  await page.getByLabel('Cari WIP', { exact: true }).fill(f.poNumber)
  await button(page, 'Terapkan').click()
  const group = page.locator('.cwip-list > article').filter({ hasText: f.poNumber })
  await ui.expect(group).toHaveCount(1)
  await ui.expect(group.locator('.cwip-facts > span').filter({ hasText: 'FINAL SKU TERSISA' }).locator('strong')).toHaveText(count + ' pcs')
}

async function snapshot(user, f, wip, fg) {
  const scope = { cutting_groups: [f.group], opening_items: [], unsourced_bs: [] }
  const s = await rpc(user, 'erp_cp7_capture_production_wip_v1', { p_scope: scope, p_request: randomUUID() })
  assert.equal(s.capture_complete, true)
  assert.equal(s.result.status, 'COMPLETE')
  assert.deepEqual(s.scope, scope)
  const [pool, extra] = s.result.totals
  assert.equal(extra, undefined)
  assert.equal(pool.size_id, f.size)
  assert.deepEqual([pool.input_pcs, pool.wip_pcs, pool.fg_pcs, pool.bs_pcs, pool.withheld_pcs, pool.exited_pcs],
    ['8', String(wip), String(fg), '0', '0', '0'])
  assert.deepEqual([s.result.timing.quality, s.result.timing.eta], ['UNKNOWN', null])
  return s
}

async function analysisTarget(user, runId, key) {
  const pages = await rpc(user, 'erp_cp7_read_staged_analysis_pages_v1', { p_run: runId })
  const hdr = JSON.parse(pages.header.body)
  // The harness uses a small copy. Resolve each target's exact page even
  // when other fixture roots share the analysis.
  for (const ref of pages.pages) {
    const page = await rpc(user, 'erp_cp7_read_staged_analysis_page_v1', { p_run: runId, p_index: ref.index, p_access: pages.access_epoch })
    const rec = JSON.parse(page.body).items.recommendations.find(x => x.target.key === key)
    if (rec) return { rec, index: ref.index, hdr, pages }
  }
  assert.fail('Target tidak muncul pada hasil analisis yang tersimpan: ' + key)
}

function cents(amount) {
  const m = /^(-?)(\d+)(?:\.(\d{1,2})0*)?$/.exec(String(amount))
  assert.ok(m, 'Angka rupiah tidak dapat dibandingkan tepat: ' + String(amount))
  return (m[1] ? -1n : 1n) * (BigInt(m[2]) * 100n + BigInt((m[3] ?? '').padEnd(2, '0')))
}

const metricPaths = [
  ['Nilai barang dalam proses', 'financial_position', 'wip_inventory'],
  ['Nilai persediaan barang jadi', 'financial_position', 'fg_inventory'],
  ['HPP penjualan tercatat', 'performance', 'cogs_gl'],
]

function checkPublicationAmounts(doc, official, dates) {
  return metricPaths.map(([name, area, key]) => {
    const line = doc.summary.split('\n').find(s => s.startsWith(name + ': '))
    const number = line?.slice(name.length + 2).match(/^(-?\d+(?:\.\d+)?) IDR;/)
    assert.ok(number, line ?? name)
    const amount = official[area][key]
    assert.equal(cents(number[1]), cents(amount))
    const days = area === 'performance' ? [dates.from, dates.to] : [dates.as_of, dates.as_of]
    assert.ok(line.includes('periode ' + days.join(' sampai ')), line)
    return String(amount)
  })
}

async function publication(ui, user, f, analysis, title, revision, today) {
  const { page } = user
  const post = await prepareReport(report(page), title, { revision: revision === 2 })
  const sent = await action(page, reportRpc, () => post.click())
  const { args } = sent
  assert.deepEqual([args.p_payload.kind, args.p_payload.finance, args.p_payload.run_id, args.p_payload.identity_hash],
    ['PERIOD', 'INCLUDED', analysis.pages.run_id, analysis.pages.identity_hash])
  await ui.expect(archive(page).getByRole('heading', { name: title + ' · versi ' + revision, exact: true })).toBeVisible({ timeout: 45_000 })
  const id = await archive(page).getAttribute('data-report-id')
  const doc = await rpc(user, 'erp_cp7_read_report_v2', { p_id: id })
  assert.deepEqual([doc.finance, doc.report_date, doc.period_query], ['INCLUDED', today, f.query])
  const { read, stock_book: stockBook } = await native('report-books', { actor: user.user.id, request: args.p_request, root: f.root })
  const qty = revision === 1 ? '0' : '3'
  assert.deepEqual(stockBook, { physical_fg_pcs: qty, available_fg_pcs: qty })
  assert.deepEqual(read.stock[f.root], stockBook)
  const dates = { from: f.query.from_date, to: f.query.through_date, as_of: today }
  assert.deepEqual(read.finance.dates, dates)
  assert.equal(doc.financial_source_hash, read.finance.source_hash)
  const nativeReport = await rpc(user, 'erp_cp7_get_finance_report_v1', { p_query: { ...dates, filing_id: null, offset: 0, limit: 25 } })
  const stored = read.finance.report.snapshot, official = nativeReport.snapshot
  assert.deepEqual([stored.data_confidence.status, official.data_confidence.status], ['READY', 'READY'])
  const money = checkPublicationAmounts(doc, official, dates)
  assert.deepEqual(checkPublicationAmounts(doc, stored, dates), money)

  const section = await rpc(user, 'erp_cp7_read_report_section_v2', { p_id: id, p_index: analysis.index, p_access: doc.access_epoch })
  const productLabel = analysis.hdr.product_labels.find(p => p.target_key === f.targetKey)
  assert.ok(productLabel && [f.commercialSku, f.sku].includes(productLabel.sku))
  const line = section.body.split('\n').find(line => line.includes('size ' + f.size + ' ·') && line.startsWith(productLabel.sku + ' ·'))
  assert.ok(line?.includes('stok fisik saat analisis 0 PCS;'), line ?? f.targetKey)
  assert.match(line, new RegExp('stok fisik aktual per [^;]+ ' + qty + ' PCS; stok tersedia setelah reservasi aktual ' + qty + ' PCS'))
  assert.equal(hash(section.body), section.sha256)
  assert.equal(hash(doc.summary), doc.summary_sha256)
  assert.equal(hash([doc.summary_sha256, ...doc.sections.map(s => s.sha256)].join('\n')), doc.report_hash)
  await ui.expect(summary(page)).toHaveText(doc.summary)
  await archive(page).getByLabel('Pilih bagian laporan bertahap', { exact: true }).selectOption(String(analysis.index))
  await button(archive(page), 'Buka bagian laporan').click()
  await ui.expect(archive(page).getByLabel('Bagian laporan bertahap', { exact: true })).toHaveText(section.body)
  return { doc, section, args, dates, money, stockBook }
}

const expectedMoney = [
  { WIP: '288.00', FG_INVENTORY: '0.00', COGS: '0.00' },
  { WIP: '180.00', FG_INVENTORY: '108.00', COGS: '0.00' },
]

async function qcJourney(ui, user, e, today) {
  const { page } = user
  const f = e.fixture = await native('prepare-qc', { today })
  const preflight = await rpc(user, autoRpc, { p_query: { initial_auto: 'STATUS' }, p_request: null })
  assert.equal(preflight.state, 'NOT_READY', 'BLOCKED: skenario QC memerlukan salinan kecil tanpa profil target yang siap otomatis')
  const before = e.before = await native('qc-books', { fixture: f, today })
  assert.deepEqual([before.ledger, before.progress, before.current_hpp, before.native.fg_stock], [expectedMoney[0], [8, 0, 8], [], 0])
  const wipBefore = e.wip_before = await snapshot(user, f, 8, 0)
  await showWip(ui, page, f, 8)
  await openManualAnalysis(page, f.query)
  await ui.expect(result(page)).toBeVisible({ timeout: 60_000 })
  const runId = await result(page).getAttribute('data-run-id')
  const analysis = await analysisTarget(user, runId, f.targetKey)
  assert.deepEqual(analysis.hdr.query, f.query)
  assert.deepEqual([analysis.rec.target.product_version_id, analysis.rec.target.size_id, analysis.rec.actual_fg.value], [f.product, f.size, '0'])
  const unknown = analysis.hdr.analysis_header.sources.find(s => s.eta === null && s.refs.some(ref => ref.id === f.group))
  const old = e.report_before = await publication(ui, user, f, analysis, 'Posisi sebelum QC', 1, today)
  if (unknown) assert.ok(old.doc.summary.includes(unknown.source_key + ':') && old.doc.summary.includes('; siap Belum diketahui (UNKNOWN).'))
  await screenshot(page, 'qc_report_before', e.screenshots)

  const post = await fillPartialQc(page, f, ui.expect)
  const sent = e.qc = await action(page, qcRpc, () => post.click())
  assert.equal(sent.body.committed, true)
  const after = e.after = await native('qc-books', { fixture: f, today })
  const { inspections, items, lots, movements } = after.native
  assert.deepEqual([inspections.length, items.length, lots.length, movements.length, after.native.bs_cases], [1, 1, 1, 1, 0])
  assert.deepEqual([after.ledger, after.progress, after.native.fg_stock], [expectedMoney[1], [8, 3, 5], 3])
  assert.deepEqual(after.current_hpp.map(([qty, unit, value]) => [qty, cents(unit), cents(value)]), [[3, 3600n, 10800n]])
  assert.deepEqual([items[0].inspection, items[0].product, items[0].good, items[0].bs, items[0].receipt_line],
    [inspections[0].id, f.product, 3, 0, f.receiptLine])
  assert.deepEqual([lots[0].product, lots[0].qc_item, lots[0].origin], [f.product, items[0].id, 'PRODUCTION'])
  assert.deepEqual(movements.map(m => [m.lot, m.location, m.qty, m.movement_type, m.source_type, m.source_id, m.reversal_of]),
    [[lots[0].id, f.location, 3, 'QC_GOOD', 'QC_ITEM', items[0].id, null]])
  const previousJournals = new Set(before.native.journals.map(j => j.id))
  const newJournals = after.native.journals.filter(j => !previousJournals.has(j.id))
  const hppSync = newJournals.filter(j => j.source_type === 'PO_HPP_GL_SYNC')
  assert.ok(newJournals.every(j => j.balanced) && hppSync.length > 0)
  assert.deepEqual(['WIP', 'FG_INVENTORY', 'COGS'].map(key => hppSync.reduce((n, j) => n + cents(j.nets[key] ?? 0), 0n)),
    [-10800n, 10800n, 0n])
  const replay = await rpc(user, qcRpc, sent.args)
  assert.deepEqual(replay, sent.body)
  assert.deepEqual(await native('qc-books', { fixture: f, today }), after)

  const wipAfter = e.wip_after = await snapshot(user, f, 5, 3)
  const fg = wipAfter.result.positions.find(p => p.stage === 'FG' && p.remaining_pcs === '3')
  assert.ok(fg?.refs.some(ref => ref.id === items[0].id))
  const reopened = await rpc(user, 'erp_cp7_read_production_wip_v1', { p_run: wipBefore.run_id })
  assert.deepEqual([reopened.source_state, reopened.captured_at, reopened.result], ['ARCHIVED_STALE', wipBefore.captured_at, wipBefore.result])
  await showWip(ui, page, f, 5)
  await openAnalysisPanel(page, f.query)
  await ui.expect(result(page)).toHaveAttribute('data-run-id', runId, { timeout: 30_000 })
  await page.getByLabel('Cari barang jadi', { exact: true }).fill(f.commercialSku)
  await button(page, 'Cari stok').click()
  const position = page.locator('.cfg-position').filter({ has: page.getByRole('heading', { name: f.commercialSku, exact: true }) })
  await ui.expect(position).toHaveCount(1)
  await ui.expect(position.locator('.cfg-size')).toHaveText(f.sizeCode)
  await ui.expect(position).toContainText(f.locationName)
  await ui.expect(position).toContainText(after.lot_numbers[lots[0].id])
  await ui.expect(position.getByRole('definition').first()).toHaveText('3')
  await ui.expect(position).toContainText(/Nilai fisik Rp108(?:,00)? · HPP Rp36(?:,00)? \/ PCS/)
  await button(position, 'Lihat mutasi ' + f.commercialSku + ' · ' + f.sizeCode).click()
  await ui.expect(page.locator('[data-fg-movement-id="' + movements[0].id + '"]')).toContainText('Hasil QC')
  await screenshot(page, 'qc_fg_movement', e.screenshots)

  const openPrior = async () => {
    await button(report(page), 'Muat laporan bertahap tersimpan').click()
    await report(page).getByRole('button', { name: /^Buka laporan bertahap/ }).filter({ hasText: old.doc.title }).click()
    await ui.expect(archive(page)).toHaveAttribute('data-report-id', old.doc.id)
  }
  await openPrior()
  await button(archive(page), 'Buat revisi dari laporan ini').click()
  const now = e.report_after = await publication(ui, user, f, analysis, 'Posisi sesudah QC', 2, today)
  assert.deepEqual(now.dates, old.dates)
  assert.deepEqual(now.money.map((v, index) => cents(v) - cents(old.money[index])), [-10800n, 10800n, 0n])
  assert.equal(now.doc.series_id, old.doc.series_id)
  assert.notEqual(now.doc.report_hash, old.doc.report_hash)
  await screenshot(page, 'qc_report_after', e.screenshots)
  await openPrior()
  const again = await rpc(user, 'erp_cp7_read_report_v2', { p_id: old.doc.id })
  const oldSection = await rpc(user, 'erp_cp7_read_report_section_v2', { p_id: again.id, p_index: analysis.index, p_access: again.access_epoch })
  assert.equal(again.is_latest, false)
  for (const key of ['summary', 'summary_sha256', 'report_hash', 'sections', 'data_as_of', 'actuals_read_at', 'financial_source_hash']) {
    assert.deepEqual(again[key], old.doc[key], key)
  }
  assert.deepEqual(oldSection, old.section)
  await ui.expect(summary(page)).toHaveText(old.doc.summary)
  const mismatched = await user.rpc(reportRpc, { p_request: randomUUID(), p_payload: { ...now.args.p_payload, identity_hash: '0'.repeat(64) } })
  assert.equal(mismatched.status, 400)
  assert.equal(mismatched.body.message, 'CP7_REPORT_V2_IDENTITY_CHANGED')
  const listed = await rpc(user, 'erp_cp7_list_reports_v2', { p_query: { before_id: null, limit: 25 } })
  assert.deepEqual(listed.rows.map(x => x.id).sort(), [now.doc.id, old.doc.id].sort())
  const limited = await ui.login(await native('reject-role'), { label: 'b-report-without-role' })
  try {
    const refusal = await limited.rpc('erp_cp7_read_report_v2', { p_id: old.doc.id })
    assert.equal(refusal.status, 403)
    assert.equal(refusal.body.code, '42501')
  } finally { await limited.context.close() }
  return {
    amounts_before: before.ledger, amounts_after: after.ledger, progress_pcs: [before.progress, after.progress],
    snapshot_ids: [wipBefore.run_id, wipAfter.run_id], expected_no_duplicate: true, archive_unchanged: true, archive_access_denied: true,
    eta_unknown_in_production_snapshot: true, eta_unknown_source_visible_in_report: Boolean(unknown),
    report_period: now.dates, report_hashes: [old.doc.report_hash, now.doc.report_hash], screenshots: e.screenshots,
  }
}

async function plannerJourney(ui, user, e, today) {
  let { page } = user
  const actor = user.user.id
  const state = () => native('planner-state', { actor })
  const products = e.products = await native('prepare-planner', { today })
  const f = e.preflight = await rpc(user, autoRpc, { p_query: { initial_auto: 'STATUS' }, p_request: null })
  assert.equal(f.state, 'NOT_READY', 'BLOCKED: salinan Planner sudah memiliki aturan yang dapat membuat job otomatis')
  const visible = f.readiness.candidates.filter(r => !r.profile_ready && products.some(p => p.root === r.root_id))
  assert.equal(visible.length, 2, 'BLOCKED: kedua SKU fixture belum muncul pada kandidat Planner (maksimal 20)')
  const [first, second] = visible.map(r => {
    const product = products.find(p => p.root === r.root_id)
    assert.equal(r.product_id, product.product)
    assert.ok([product.sku, product.commercialSku].includes(r.sku))
    return { ...product, visibleSku: r.sku }
  })
  assert.deepEqual(await state(), { intents: 0, jobs: 0, job: null })
  await openWarehouse(page)
  await ui.expect(button(initial(page), 'Lengkapi target ' + first.visibleSku)).toBeVisible()
  const save = await selectSecondTarget(page, second.visibleSku, ui.expect)
  const { args } = e.save = await action(page, profileRpc, () => save.click())
  assert.deepEqual([args.p_payload.root_id, args.p_payload.product_version_id], [second.root, second.product])
  const p = args.p_payload.config
  assert.deepEqual([p.daily_pcs, p.lead_days, p.review_days, p.buffer_days], ['10', '3', '7', '2'])
  const profiles = (await rpc(user, 'erp_cp7_get_planning_profiles_v1', { p_roots: [first.root, second.root] })).rows
  assert.equal(profiles.find(r => r.root_id === first.root)?.revision, '0')
  const secondProfile = profiles.find(r => r.root_id === second.root)
  assert.equal(secondProfile?.revision, '1')
  assert.deepEqual([secondProfile.config.daily_pcs, secondProfile.config.lead_days, secondProfile.config.review_days, secondProfile.config.buffer_days], ['10', '3', '7', '2'])
  await ui.expect(button(initial(page), 'Buka analisis awal yang berjalan')).toBeVisible({ timeout: 30_000 })
  const stored = e.running = await state()
  const id = stored.job.request_id
  assert.deepEqual([stored.intents, stored.jobs, stored.job.state], [1, 1, 'RUNNING'])
  await ui.expect(initial(page)).toContainText('Analisis bertahap:')
  await screenshot(page, 'planner_running', e.screenshots)
  await page.close()

  const finished = e.finished = await native('finish-planner', { actor, request: id })
  const job = finished.state.job
  assert.equal(job.state, 'DONE', JSON.stringify(job))
  assert.ok(job.units_done > stored.job.units_done)
  assert.deepEqual([job.request_id, finished.state.intents, finished.state.jobs], [id, 1, 1])
  page = await user.context.newPage()
  await page.goto(ui.origin)
  await openWarehouse(page)
  await ui.expect(initial(page)).toContainText('Periode ' + job.query.from_date + ' sampai ' + job.query.through_date)
  await openCurrentInitial(page, true)
  await ui.expect(result(page)).toHaveAttribute('data-run-id', job.run_id, { timeout: 30_000 })
  const resolved = await analysisTarget(user, job.run_id, second.targetKey)
  assert.deepEqual([resolved.pages.request_id, resolved.hdr.query], [id, job.query])
  assert.deepEqual([resolved.rec.target.product_version_id, resolved.rec.actual_fg.value, resolved.rec.target_qty.value, resolved.rec.feasible_new.state],
    [second.product, second.stock, '120', 'UNKNOWN'])
  const control = await analysisTarget(user, job.run_id, first.targetKey)
  assert.deepEqual([control.rec.actual_fg.value, control.rec.target_qty.state], [first.stock, 'UNKNOWN'])
  await result(page).getByLabel('Pilih rentang target', { exact: true }).selectOption(String(resolved.index))
  const row = result(page).locator('[data-analysis-target="' + second.targetKey + '"]')
  const labels = resolved.hdr.product_labels.filter(p => p.target_key === second.targetKey)
  assert.equal(labels.length, 1)
  assert.ok([second.sku, second.commercialSku].includes(labels[0].sku))
  await ui.expect(row).toContainText(labels[0].sku)
  await ui.expect(row.locator('[data-label="Target"]')).toHaveText('120 PCS · asumsi')
  await ui.expect(row.locator('[data-label="Produksi baru layak"]')).toHaveText('Belum diketahui')
  await screenshot(page, 'planner_reopened', e.screenshots)
  assert.deepEqual(await state(), finished.state)

  const limited = await ui.login(await native('reject-role'), { label: 'b-planner-without-role', mobile: true })
  try {
    for (const mode of ['STATUS', 'ENSURE']) {
      const refusal = await limited.rpc(autoRpc, { p_query: { initial_auto: mode }, p_request: null })
      assert.equal(refusal.status, 403)
      assert.equal(refusal.body.code, '42501')
    }
    const refusal = await limited.rpc('erp_cp7_read_staged_analysis_pages_v1', { p_run: job.run_id })
    assert.equal(refusal.status, 403)
    assert.equal(refusal.body.code, '42501')
    assert.deepEqual(await native('planner-state', { actor: limited.user.id }), { intents: 0, jobs: 0, job: null })
  } finally { await limited.context.close() }
  return {
    request: id, run: job.run_id, period: job.query, profile_revisions: ['0', '1'], target_pcs: '120',
    job_count: 1, server_units_with_page_closed: job.units_done - stored.job.units_done, unauthorized_rejected: true,
    screenshots: e.screenshots,
  }
}

export function cases(ui, today) {
  const db = new URL(process.env.AUDITOR_BROWSER_DB_URL || 'postgresql://invalid/')
  assert.ok(['postgres:', 'postgresql:'].includes(db.protocol) && ['127.0.0.1', 'localhost'].includes(db.hostname) && db.pathname === '/cp6_auditor_browser',
    'DISPOSABLE_BROWSER_COPY_ONLY')
  assert.equal((process.env.AUDITOR_UI_MODE || 'DISPOSABLE').toUpperCase(), 'DISPOSABLE')
  return [
    ['B_QC_SNAPSHOT_REPORT_OWNER', () => trackedCase(ui, 'qc', 'OWNER', {}, (user, e) => qcJourney(ui, user, e, today))],
    ['B_PLANNER_SECOND_SKU_ADMIN', () => trackedCase(ui, 'planner', 'ADMIN', { mobile: true }, (user, e) => plannerJourney(ui, user, e, today))],
  ]
}
