// Normal App menu and real Auth/PostgREST. Native preparation is not UI creation.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {equalCensus, observeConsole, requireConsoleEvidence, readable} from '../current-sku-pair-browser-qualification/evidence.mjs'
import {observeResponseWaits} from './response_waits.mjs'

export const IDS = ['S05_SKU_NORMAL_APP_DESKTOP_SOURCE_AND_LATE_REPLY', 'S05_SKU_NORMAL_APP_MOBILE390_UNKNOWN_ZERO_AND_CURRENT_ACCESS']
export const RPC = 'erp_cp7_get_accessory_standard_report_v1'
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const sha = raw => createHash('sha256').update(raw).digest('hex')
const input = response => response.request().postDataJSON()
const isRead = response => response.url().endsWith('/rpc/'+RPC) && response.request().method() === 'POST'
const fixture = (operation, payload) => JSON.parse(execFileSync('python', ['-B', resolve(ROOT, 'scripts/current-s03-sku-s05-composite-qualification/browser_fixture.py'), operation],
  {cwd: ROOT, input: JSON.stringify(payload), encoding: 'utf8', maxBuffer: 32*1024*1024, timeout: 120000}).trim())

export function displayed(value, rupiah = false) {
  if (value === null) return 'Belum diketahui'
  assert.match(value, /^-?\d+(\.\d+)?$/)
  let [whole, fraction = ''] = value.split('.')
  const negative = whole.startsWith('-'); whole = whole.replace('-', '').replace(/^0+(?=\d)/, '')
  fraction = fraction.replace(/0+$/, '')
  return (negative ? '−' : '')+(rupiah ? 'Rp' : '')+whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')+(fraction ? ','+fraction : '')
}

function admitted() {
  const raw = readFileSync(resolve(ROOT, 'scripts/current-s03-sku-s05-composite-qualification/SOURCE.json'))
  const pins = JSON.parse(raw); assert.deepEqual(pins.browser_case_ids, IDS)
  for (const [path, expected] of Object.entries(pins.files)) assert.equal(sha(readFileSync(resolve(ROOT, path))), expected, 'S05_BROWSER_SOURCE_CHANGED:'+path)
  const preparedRaw = readFileSync(resolve(ROOT, 'cp6-proof/t3/S05_SKU_BROWSER_FIXTURES.json'))
  assert.equal(sha(preparedRaw), process.env.S05_SKU_BROWSER_FIXTURES_SHA256)
  const prepared = JSON.parse(preparedRaw)
  assert.equal(prepared.status, 'ACTUAL_NATIVE_BROWSER_PREREQUISITES_PREPARED')
  assert.deepEqual(Object.keys(prepared.fixtures), ['variants', 'zero', 'empty', 'no_good'].sort())
  return {fixtures: prepared.fixtures, source: {source_sha256: sha(raw), actual_preparation_sha256: sha(preparedRaw), Native_fixture_case_credit: 0}}
}

async function menu(page) {
  const toggle = page.getByRole('button', {name: 'Buka menu', exact: true}), sidebar = page.locator('.sidebar')
  if (await toggle.isVisible() && !await sidebar.evaluate(e => e.classList.contains('sidebar-open'))) await toggle.click()
  const link = page.getByRole('button', {name: '• Nota Ambil Aksesori', exact: true})
  if (!await link.isVisible()) await page.locator('.sidebar .nav-main').filter({hasText: 'Keuangan'}).click()
  await link.click()
}

async function journey(ui, mobile) {
  const {fixtures, source} = admitted(), suffix = mobile ? 'MOBILE390' : 'DESKTOP'
  const user = await ui.login(mobile ? 'ADMIN' : 'OWNER', {label: 'S05-'+suffix, mobile, timezoneId: mobile ? 'America/Los_Angeles' : 'Asia/Jakarta'})
  const page = user.page, expect = ui.expect, capture = observeConsole(page), stopWaiting = observeResponseWaits(page)
  const calls = [], contrasts = [], shots = [], progress = {}, expectedNetwork = [], run = fixtures.variants.po_id.replaceAll('-', '').toUpperCase()
  let serial = 0, inactive = false, release, heldHandler, primaryError
  const routeErrors = []
  const panel = () => page.getByRole('region', {name: 'Laporan aksesori mandor', exact: true})
  const state = label => fixture('observe', {label: `S05_SKU_${suffix}_${run}_${String(++serial).padStart(2, '0')}_${label}`})
  const listener = request => { if (request.url().endsWith('/rpc/'+RPC)) calls.push(request.postDataJSON()) }
  page.on('request', listener)
  const request = async (predicate, action) => {
    const pending = page.waitForResponse(r => isRead(r) && predicate(input(r)))
    await action(); const response = await pending
    assert.equal(response.status(), 200, await response.text())
    const body = await response.json(); assert.equal(body.business_DML, false)
    return body
  }
  async function visual(label) {
    const width = await page.evaluate(() => ({viewport: innerWidth, page: document.documentElement.scrollWidth}))
    assert.equal(width.viewport, mobile ? 390 : 1440); assert.ok(width.page <= width.viewport, JSON.stringify(width))
    contrasts.push({label, width, measured: await readable(panel())})
    mkdirSync('cp6-proof/t3', {recursive: true})
    const path = `cp6-proof/t3/S05_SKU_${suffix}_${run}_${label}.png`
    await page.screenshot({path, fullPage: true}); shots.push(path)
  }
  async function open() {
    return request(() => true, () => page.getByRole('button', {name: 'Diambil vs standar GOOD', exact: true}).click())
  }
  async function reportFor(label) {
    const f = fixtures[label]
    await panel().getByLabel('Mulai periode aksesori', {exact: true}).fill(f.day)
    await panel().getByLabel('Akhir periode aksesori', {exact: true}).fill(f.day)
    const search = panel().getByLabel('Cari mandor laporan', {exact: true})
    // Several lawful fixtures can share the same contractor. Force a real
    // input change so React retires the prior contractor/PO selection.
    await search.fill(''); await search.fill(f.contractor_name)
    let workspace = await request(a => a.p_start === f.day && a.p_end === f.day && a.p_query === f.contractor_name && a.p_contractor === null,
      () => panel().getByRole('button', {name: 'Muat laporan', exact: true}).click())
    let index = workspace.contractors.rows.findIndex(row => row.id === f.contractor_id)
    while (index < 0 && workspace.contractors.next_offset !== null) {
      const next = workspace.contractors.next_offset
      workspace = await request(a => a.p_offset === next && a.p_query === f.contractor_name,
        () => panel().getByRole('button', {name: 'Mandor berikutnya', exact: true}).click())
      index = workspace.contractors.rows.findIndex(row => row.id === f.contractor_id)
    }
    assert.ok(index >= 0, 'PREPARED_CONTRACTOR_NOT_IN_ACTUAL_FILTERED_PAGES')
    const choices = panel().getByRole('region', {name: 'Pilih mandor laporan', exact: true}).locator('ul > li > button')
    await expect(choices).toHaveCount(workspace.contractors.rows.length)
    workspace = await request(a => a.p_contractor === f.contractor_id && a.p_po === null, () => choices.nth(index).click())
    assert.ok(workspace.po_options.some(po => po.id === f.po_id))
    workspace = await request(a => a.p_contractor === f.contractor_id && a.p_po === f.po_id,
      () => panel().getByLabel('PO laporan aksesori', {exact: true}).selectOption(f.po_id))
    assert.deepEqual(workspace.report, f.expected_report, 'ACTUAL_HTTP_REPORT_DIFFERS_FROM_FINAL_NATIVE_READ')
    const result = panel().getByRole('region', {name: 'Hasil laporan aksesori', exact: true})
    await expect(result).toBeVisible()
    const rows = result.locator('tbody > tr'); await expect(rows).toHaveCount(f.expected_report.rows.length)
    for (let i = 0; i < f.expected_report.rows.length; ++i) {
      const r = f.expected_report.rows[i], cells = rows.nth(i).getByRole('cell')
      await expect(rows.nth(i).getByRole('rowheader')).toContainText(r.category_name)
      const qty = x => x === null ? 'Belum diketahui' : displayed(x)+' '+(r.unit ?? '(satuan belum diketahui)')
      const values = [qty(r.actual_qty), qty(r.standard_qty), qty(r.delta_qty), displayed(r.actual_inventory_cost, true),
        displayed(r.actual_receivable, true), displayed(r.standard_hpp_cost, true), displayed(r.standard_reimbursement, true)]
      await expect(cells).toHaveText(values)
    }
    await visual(label.toUpperCase())
    progress[label] = {exact_HTTP_equals_Native: true, exact_displayed_cells: true, status: workspace.report.status}
    return workspace
  }
  try {
    await menu(page)
    await expect(page.getByRole('button', {name: 'Nota ambil aksesori', exact: true})).toHaveAttribute('aria-pressed', 'true')
    assert.equal(calls.length, 0, 'REPORT_READ_BEFORE_REPORT_TAB_SELECTED')
    await open(); const before = state('BEFORE_REPORT_READS')
    for (const label of ['variants', 'zero', 'empty', 'no_good']) await reportFor(label)
    await reportFor('variants')
    await panel().locator('summary').filter({hasText: /^Jejak sumber pengambilan/}).click()
    await panel().locator('summary').filter({hasText: /^Jejak standar GOOD/}).click()
    for (const s of fixtures.variants.expected_report.actual_sources) {
      const article = panel().getByRole('article', {name: 'Sumber pengambilan '+s.issue_number, exact: true})
      await expect(article).toContainText(s.id); await expect(article).toContainText(s.material_id)
    }
    for (const s of fixtures.variants.expected_report.standard_sources) {
      await expect(panel().getByRole('region', {name: 'Snapshot standar '+s.id, exact: true})).toContainText(s.bom_version_id)
    }
    await visual('SOURCES')
    let intercepted = false
    const held = new Promise(resolveHeld => { release = resolveHeld })
    heldHandler = async route => {
      intercepted = true; await held
      try { await route.fallback() }
      catch (error) { routeErrors.push(String(error)); await route.abort('failed').catch(() => {}) }
    }
    await page.route('**/rest/v1/rpc/'+RPC, heldHandler)
    const pending = page.waitForResponse(isRead)
    await panel().getByRole('button', {name: 'Muat laporan', exact: true}).click()
    await expect.poll(() => intercepted, {timeout: 10000}).toBe(true)
    await page.getByRole('button', {name: 'Nota ambil aksesori', exact: true}).click()
    await expect(panel()).toHaveCount(0); release()
    assert.equal((await pending).status(), 200)
    await page.unroute('**/rest/v1/rpc/'+RPC, heldHandler); heldHandler = null
    await expect(panel()).toHaveCount(0)
    await expect(page.getByRole('button', {name: 'Nota ambil aksesori', exact: true})).toHaveAttribute('aria-pressed', 'true')
    progress.late_reply = {real_request_delayed_before_forwarding: true, response_mocked: false, report_not_resurrected: true}
    equalCensus(before, state('AFTER_REPORT_READS'))
    if (mobile) {
      await open(); await reportFor('variants')
      progress.revoke = fixture('deactivate_admin', {auth_user_id: user.user.id}); inactive = true
      const deniedBefore = state('BEFORE_ACCESS_REFUSAL'), pending = page.waitForResponse(isRead)
      await panel().getByRole('button', {name: 'Muat laporan', exact: true}).click()
      const response = await pending, body = await response.json()
      assert.equal(response.status(), 403); assert.equal(body.code, '42501')
      assert.match(body.message, /CP7_ACCESSORY_REPORT_(DENIED|ACCESS_CHANGED)/)
      expectedNetwork.push({url: response.url(), text: 'Failed to load resource: the server responded with a status of 403 (Forbidden)', reason: 'ACTUAL_CURRENT_ADMIN_ACCESS_REFUSAL'})
      await expect(page.getByRole('region', {name: 'Hasil laporan aksesori', exact: true})).toHaveCount(0)
      equalCensus(deniedBefore, state('AFTER_ACCESS_REFUSAL'))
      progress.access = {current_403_with_existing_Auth_session: true, previous_figures_retired: true, full_read_refusal_no_effect: true}
    }
    assert.deepEqual(routeErrors, [], 'DELAYED_REAL_ROUTE_FAILED')
    return {status: 'PASS', role: mobile ? 'ADMIN' : 'OWNER', viewport: mobile ? 390 : 1440,
      actual_normal_App_real_Auth_public_RPC: true, source, progress, contrasts, screenshots: shots, read_requests: calls,
      console_evidence: requireConsoleEvidence(capture, expectedNetwork), all_report_reads_full22_data_ALL_sequences_unchanged: true,
      actual_Native_case_credit: 0, fixture_screen_creation_claim: false, Afui_positive_HPP_zero_reimbursement_coverage: false,
      outer_full_restore_required: true, production_go: false, independent_acceptance: false}
  } catch (error) {
    primaryError = error
    mkdirSync('cp6-proof/t3', {recursive: true})
    writeFileSync(`cp6-proof/t3/S05_SKU_${suffix}_${run}_FIRST_FAILURE.json`, JSON.stringify({error: String(error.stack || error), progress,
      calls, source, routeErrors, console_errors: capture.errors, page_errors: capture.pageErrors, expectedNetwork,
      text: await page.locator('main').innerText().catch(() => '')}, null, 2)+'\n')
    await page.screenshot({path: `cp6-proof/t3/S05_SKU_${suffix}_${run}_FIRST_FAILURE.png`, fullPage: true}).catch(() => {})
    throw error
  } finally {
    const cleanup = await cleanupSteps([
      () => release?.(),
      () => heldHandler ? page.unroute('**/rest/v1/rpc/'+RPC, heldHandler) : undefined,
      () => inactive ? fixture('reactivate_admin', {auth_user_id: user.user.id}) : undefined,
      stopWaiting, capture.stop, () => page.off('request', listener), () => user.context.close(),
    ])
    if (cleanup.length) {
      writeFileSync(`cp6-proof/t3/S05_SKU_${suffix}_${run}_CLEANUP_FAILURE.json`, JSON.stringify({primary_error: String(primaryError || ''), cleanup, routeErrors}, null, 2)+'\n')
      if (!primaryError) throw new Error('S05_BROWSER_CLEANUP_FAILED: '+cleanup.join('; '))
    }
  }
}

export async function cleanupSteps(operations) {
  const failures = []
  for (const operation of operations) {
    try { await operation() } catch (error) { failures.push(String(error)) }
  }
  return failures
}

export function cases(ui) { admitted(); return IDS.map((id, index) => [id, () => journey(ui, index === 1)]) }
