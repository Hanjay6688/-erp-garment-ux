import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

const fixture = JSON.parse(process.env.CP7_P21_FOLLOWUP_FIXTURE)
delete process.env.CP7_P21_FOLLOWUP_FIXTURE
const output = process.env.CP7_P21_FOLLOWUP_RAW
const button = (scope, name) => scope.getByRole('button', { name, exact: true })
const digest = text => createHash('sha256').update(text, 'utf8').digest('hex')
const getRoll = 'erp_cp7_get_switch_roll_v1'
const previewRoll = 'erp_cp7_preview_switch_roll_v1'
const saveRoll = 'erp_cp7_switch_roll_v1'
const source = fixture.switch_roll

// The normal FG screen may enqueue its read-only staged analysis. Track
// that request explicitly and preserve all table digests regardless.
const initialJobTables = [
  'cp7_initial_analysis.intents',
  ...['jobs', 'capture_marks', 'units', 'outputs', 'target_rows', 'pair_rows', 'pair_lists',
    'fragments', 'headers', 'pages', 'page_sets', 'plan_targets', 'plan_scope', 'plan_groups']
      .map(name => 'cp7_analysis_stage.' + name),
]

function trackInitialAnalysis(page, actor) {
  const events = []
  page.on('response', async reply => {
    if (!reply.url().endsWith('/rpc/erp_cp7_request_staged_analysis_v1') || reply.request().method() !== 'POST') return
    const mode = reply.request().postDataJSON()?.p_query?.initial_auto
    if (!['STATUS', 'ENSURE'].includes(mode)) return
    const body = await reply.json().catch(() => ({}))
    events.push({ mode, http: reply.status(), state: body.state ?? null,
      bound: body.contract_version === 'cp7.initial-analysis.v1' && body.actor === actor })
  })
  const verified = event => event.http === 200 && event.bound
  const completedRead = () => events.some(event => verified(event) &&
    ['NOT_READY','BUSY','RUNNING','DONE','FAILED','EXPIRED'].includes(event.state))
  const canEnqueue = () => events.some(event => verified(event) &&
    ['RUNNING','DONE'].includes(event.state))
  return { events, completedRead, tables: () => canEnqueue() ? initialJobTables : [] }
}
const readArgs = { p_purchase: source.source_purchase, p_issue: source.payload.issue_id, p_query: '', p_offset: 0 }

function retain(label, value) {
  writeFileSync(join(output, label + '.json'), JSON.stringify(value, null, 2) + '\n', { flag: 'wx', mode: 0o600 })
}

function observe(label) {
  return JSON.parse(execFileSync('python3', ['-B', process.env.CP7_P21_STATE_SCRIPT, label], {
    encoding: 'utf8', maxBuffer: 4 * 1024 * 1024, timeout: 45000, stdio: ['ignore', 'pipe', 'pipe'],
  }))
}

function compare(before, after, allowedTables = []) {
  function changed(left, right) {
    return [...new Set([...Object.keys(left), ...Object.keys(right)])]
      .filter(key => JSON.stringify(left[key]) !== JSON.stringify(right[key])).sort()
  }
  const tableChanges = changed(before.tables, after.tables)
  const sequenceChanges = changed(before.sequences, after.sequences)
  const unexpected = tableChanges.filter(name => !allowedTables.includes(name))
  const equalTotals = JSON.stringify(before.totals) === JSON.stringify(after.totals)
  return { observed_tables: Object.keys(before.tables).length, observed_sequences: Object.keys(before.sequences).length,
    populated_tables: Object.values(before.tables).filter(([n]) => n > 0).length,
    table_changes: tableChanges, sequence_changes: sequenceChanges, unexpected_tables: unexpected,
    totals_equal: equalTotals, operations_equal: !unexpected.length && !sequenceChanges.length && equalTotals }
}

function unchanged(label, before, allowedTables = []) {
  const result = compare(before, observe(label + '-after'), allowedTables)
  retain(label + '-comparison', result)
  assert.equal(result.operations_equal, true, 'P21_OPERATIONAL_CHANGE_' + label)
  return result
}

async function open(page, group, label) {
  await page.locator('.top-title strong').waitFor()
  const menu = button(page, 'Buka menu')
  if (await menu.isVisible()) await menu.click()
  const link = button(page, '• ' + label)
  if (!await link.isVisible()) await page.locator('.sidebar .nav-main').filter({ hasText: group }).click()
  await link.click()
}

async function clickRpc(page, name, action, timeout = 45000) {
  const [resolution] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/rpc/' + name) && response.request().method() === 'POST', { timeout }),
    action(),
  ])
  return { status: resolution.status(), body: await resolution.json() }
}

function assertDenial(reply, status, code, reason) {
  assert.equal(reply.status, status)
  assert.equal(reply.body?.code, code)
  if (reason) assert.equal(reply.body?.message, reason)
  for (const key of ['issues', 'rolls', 'impact', 'before', 'after', 'review_token', 'result', 'history']) {
    assert.ok(!(key in reply.body), 'P21_DENIAL_EXPOSES_' + key)
  }
}

async function negative(label, rpc, status, code, reason, args = readArgs, payload = source.payload, token = '0'.repeat(32), allowedTables = []) {
  const before = observe(label + '-before')
  const requests = [
    [getRoll, args],
    [previewRoll, { p_payload: payload }],
    [saveRoll, { p_payload: payload, p_request: randomUUID(), p_review: token }],
  ]
  const calls = {}
  for (const [name, params] of requests) {
    calls[name] = await rpc(name, params)
    // Persist the original response before trying to classify it.
    retain(label + '-' + name, calls[name])
  }
  const state = unchanged(label, before, allowedTables)
  for (const reply of Object.values(calls)) assertDenial(reply, status, code, reason)
  return { status, code, calls: Object.keys(calls).length, ...state }
}

async function analysisCases(ui) {
  const owner = await ui.login('OWNER', { label: 'owner', mobile: false })

  const results = {}
  const initial = trackInitialAnalysis(owner.page, owner.user.id)
  try {
    const { page, context } = owner
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: ui.origin })
    let before = observe('e22-read-report-before')
    assert.ok(Number(before.totals.cash_idr) > 0 && Number(before.totals.cogs_idr) > 0 &&
      before.totals.hpp_versions > 0 && before.totals.ledger_entries > 0, 'P21_ANALYSIS_NONEMPTY_ECONOMIC_FIXTURE_REQUIRED')
    await open(page, 'Keuangan', 'Laporan & Tutup Buku')
    for (const [name, value] of Object.entries(fixture.finance_fields)) {
      await page.getByLabel(name, { exact: true }).fill(value)
    }
    const read = await clickRpc(page, 'erp_cp7_get_finance_report_v1', () => button(page, 'Tampilkan laporan').click())
    retain('e22-finance-report-original', read)
    assert.equal(read.status, 200)
    assert.ok(read.body.snapshot?.financial_position && read.body.snapshot?.performance)
    results.read = { http: read.status, ...unchanged('e22-read-report', before) }

    before = observe('e22-initial-navigation-before')
    await open(page, 'Gudang', 'Ringkasan Barang Jadi')
    await ui.expect.poll(initial.completedRead, { timeout: 90000 }).toBe(true)
    results.initial_navigation = unchanged('e22-initial-navigation', before, initial.tables())
    retain('e22-initial-analysis-requests', initial.events)
    const history = page.getByRole('region', { name: 'Data permintaan ERP', exact: true })
    await button(history, 'Data permintaan & stok').click()
    await button(history, 'Analisis, laporan & pengingat seluruh produk').click()
    const panel = page.getByRole('region', { name: 'Analisis ERP bersama', exact: true })
    await panel.getByRole('checkbox', { name: 'Sertakan angka keuangan (menunggu buku besar)', exact: true }).check()
    before = observe('e22-compute-before')
    const original = await clickRpc(page, 'erp_cp7_capture_analysis_v1', () => button(panel, 'Ambil analisis ERP terbaru').click(), 90000)
    retain('e22-compute-original', original)
    assert.equal(original.status, 200)
    assert.equal(original.body.contract_version, 'cp7.native-analysis-run.v1')
    assert.equal(original.body.analysis.snapshot.capture_complete, true)
    assert.ok(original.body.financial_source && original.body.analysis.actions.length > 0)
    const analysisRun = original.body.run_id
    const computed = unchanged('e22-compute', before, ['cp7_analysis_native.runs', ...initial.tables()])
    assert.ok(computed.table_changes.includes('cp7_analysis_native.runs'))
    results.compute = { http: original.status, semantic_hash: original.body.analysis.semantic_hash, ...computed }

    await panel.getByRole('tab', { name: 'Laporan', exact: true }).click()
    before = observe('e22-copy-report-before')
    const visibleText = await panel.getByLabel('Isi laporan ERP', { exact: true }).textContent()
    assert.ok(Buffer.byteLength(visibleText, 'utf8') > 100)
    await button(panel, 'Periksa & salin laporan').click()
    const manual = panel.getByLabel('Salinan manual laporan ERP', { exact: true })
    await ui.expect(manual).toBeVisible()
    const content = await manual.inputValue()
    const clipboard = await page.evaluate(() => navigator.clipboard.readText())
    assert.equal(clipboard, content)
    assert.equal(content, visibleText)
    writeFileSync(join(output, 'e22-clipboard-original.txt'), clipboard, { flag: 'wx', mode: 0o600 })
    results.copy = { utf8_bytes: Buffer.byteLength(clipboard, 'utf8'), sha256: digest(clipboard), ...unchanged('e22-copy-report', before, initial.tables()) }

    await panel.getByRole('tab', { name: 'Pengingat', exact: true }).click()
    before = observe('e22-ack-before')
    const status = await clickRpc(page, 'erp_cp7_get_analysis_attention_v1', () => button(panel, 'Muat perhatian tersimpan').click())
    assert.equal(status.status, 200)
    const action = status.body.rows.find(row => row.attention.state === 'NEW' && row.business_resolved === false)
    assert.ok(action, 'P21_E22_ACTIVE_REMINDER_FIXTURE_REQUIRED')
    const beforeRow = action
    const card = panel.getByRole('article', { name: 'Perhatian ' + action.action_key, exact: true })
    const ack = await clickRpc(page, 'erp_cp7_save_analysis_attention_v1', () => button(card, 'Sudah dibaca').click())
    retain('e22-ack-original', { before: beforeRow, reply: ack })
    assert.equal(ack.status, 200)
    const afterRow = ack.body.rows.find(row => row.action_key === action.action_key)
    assert.equal(afterRow.attention.state, 'ACK')
    assert.equal(afterRow.business_resolved, false)
    assert.deepEqual(ack.body.analysis.analysis, original.body.analysis)
    await ui.expect(card).toContainText('Perhatian: Sudah dibaca')
    const stored = await owner.rpc('erp_cp7_get_analysis_attention_v1', { p_run: analysisRun })
    retain('e22-ack-persisted-read', stored)
    assert.ok(stored.status === 200 && stored.body.rows.some(row =>
      row.action_key === action.action_key && row.attention.state === 'ACK' && row.business_resolved === false))
    results.ack = { http: ack.status, persists: true, business_resolved: false,
      ...unchanged('e22-ack', before, ['cp7_reminder_native.attention', 'cp7_reminder_native.requests', ...initial.tables()]) }
  } finally { await owner.context.close() }

  const analyst = await ui.login('ADMIN', { label: 'analyst', mobile: false })
  try {
    const before = observe('e22-analyst-compute-before')
    const access = await analyst.rpc('erp_get_my_access_v1', {})
    assert.equal(access.body.profile.role_code, 'P21_ANALYSIS_ONLY')
    const calc = await analyst.rpc('erp_cp7_capture_operational_analysis_v1', { p_query: fixture.analysis_query, p_request: randomUUID() })
    retain('e22-analysis-actor-compute', calc)
    assert.ok(calc.status === 200 && calc.body.analysis.snapshot.capture_complete && calc.body.financial_source === null)
    const state = unchanged('e22-analyst-compute', before, ['cp7_analysis_native.runs', ...initial.tables()])
    const denial = await negative('e22-analysis-actor-refused', analyst.rpc, 403, '42501',
      'CP7_RECEIPT_FIX_ACCESS_DENIED', readArgs, source.payload, '0'.repeat(32), initial.tables())
    results.analyst = { login_http: analyst.loginStatus, computed_http: calc.status, no_finance_leak: true,
      writes_denied: denial, ...state }
  } finally { await analyst.context.close() }
  retain('e22-analysis-request-final-trace', initial.events)
  retain('e22-processing-summary', results)
  return { status: 'PASS', real_browser_read_compute_copy_ack: true, isolated: true, observations: results }
}

export function cases(ui) {
  return [['P21_E22_ANALYSIS_ISOLATION', () => analysisCases(ui)]]
}
