// Real browser/Auth/product. Inject transport loss only, never a fabricated success.
// Oracle: M1679/M3819 exact pending envelope; M3825 unknown is not zero.
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const lit = s => "'" + String(s).replaceAll("'", "''") + "'"
async function navigate(page, label) {
  const target = page.locator('.sidebar .submenu button').filter({ hasText: label })
  if (await target.isVisible()) { await target.click(); return }
  const buttons = page.locator('.sidebar .nav-main')
  const n = await buttons.count()
  for (let i = 0; i < n; i++) {
    await buttons.nth(i).click()
    if (await target.isVisible()) { await target.click(); return }
  }
  throw new Error('NAV_TARGET_MISSING:' + label)
}
const dbRows = (ui, query) => JSON.parse(ui.sql(query))
const emptySuccess = r => r && r.status >= 200 && r.status < 300
async function interceptCommittedReply(page, fn) {
  const records = []
  const url = '**/rpc/' + fn
  await page.route(url, async route => {
    if (route.request().method() !== 'POST') { await route.continue(); return }
    const request = route.request().postDataJSON()
    const response = await route.fetch()
    const record = { request, status: response.status(), body: await response.json(), reply_discarded: records.length === 0 }
    records.push(record)
    if (record.reply_discarded) await route.abort('failed')
    else await route.fulfill({ response })
  })
  return { records, url }
}
async function patternRetry(ui) {
  const u = await ui.login('OWNER', { label: 'recovery-pattern' })
  const { page } = u
  try {
    await navigate(page, 'Pola')
    await page.getByRole('button', { name: 'Pola baru', exact: true }).click()
    const d = page.getByRole('dialog')
    const code = 'G8P_' + randomUUID().replaceAll('-', '').slice(0, 14).toUpperCase()
    await d.getByLabel('Kode stabil', { exact: true }).fill(code)
    await d.getByLabel('Nama Pola', { exact: true }).fill(code)
    await d.getByLabel('Alasan perubahan', { exact: true }).fill('GPT ambiguity test on disposable copy')
    const wire = await interceptCommittedReply(page, 'erp_save_pattern_v1')
    const save = d.getByRole('button', { name: 'Simpan Pola', exact: true })
    await save.click()
    await ui.expect.poll(() => wire.records.length).toBe(1)
    await ui.expect(page.locator('.pattern-error')).toBeVisible()
    await ui.expect(save).toBeEnabled()
    const afterFirst = dbRows(ui, `select coalesce(jsonb_agg(jsonb_build_object('id',id,'code',pattern_code,'name',pattern_name,'version',row_version)),'[]'::jsonb) from erp.production_patterns where pattern_code=${lit(code)}`)
    if (!emptySuccess(wire.records[0]) || afterFirst.length !== 1) return { status: 'INCOMPLETE', stage: 'FIRST_SAVE_MUST_COMMIT', wire: wire.records, afterFirst }
    await save.click()
    await ui.expect.poll(() => wire.records.length).toBe(2)
    const afterRetry = dbRows(ui, `select coalesce(jsonb_agg(jsonb_build_object('id',id,'code',pattern_code,'name',pattern_name,'version',row_version)),'[]'::jsonb) from erp.production_patterns where pattern_code=${lit(code)}`)
    const sameEnvelope = JSON.stringify(wire.records[0].request) === JSON.stringify(wire.records[1].request)
    const replayExact = emptySuccess(wire.records[1]) && JSON.stringify(wire.records[0].body) === JSON.stringify(wire.records[1].body)
    return { status: sameEnvelope && replayExact && afterRetry.length === 1 ? 'PASS' : 'COUNTEREXAMPLE',
      oracle: 'M1679/M3819: ambiguous commit retains exact UUID/payload and retry replays committed result once',
      transport_fault: 'server real response received by route.fetch, then browser reply discarded',
      first_commit_confirmed: true, sameEnvelope, replayExact, afterFirst, afterRetry,
      wire: wire.records, visible_error: await page.locator('.pattern-error').innerText().catch(() => ''),
      financial_duplicate_claimed: false }
  } finally { await u.context.close() }
}
async function roleRetry(ui) {
  const u = await ui.login('OWNER', { label: 'recovery-role' })
  const { page } = u
  try {
    await navigate(page, 'Pengguna & Hak Akses')
    const gudang = page.locator('.role-list article').filter({ has: page.locator('.role-title small', { hasText: /^GUDANG$/ }) })
    await gudang.getByRole('button', { name: 'Duplikat', exact: true }).click()
    const d = page.getByRole('dialog')
    const name = 'G8R-' + randomUUID()
    await d.getByLabel('Nama role', { exact: true }).fill(name)
    await d.getByLabel('Alasan perubahan', { exact: true }).fill('GPT disposable role retry, no user assigned')
    // Reduce the duplicate template to an empty permission set; no new effective access.
    for (const box of await d.locator('.permission-matrix input[type=checkbox]').all()) if (await box.isChecked()) await box.uncheck()
    const wire = await interceptCommittedReply(page, 'erp_save_role_v1')
    const save = d.getByRole('button', { name: 'Simpan role', exact: true })
    await save.click()
    await ui.expect.poll(() => wire.records.length).toBe(1)
    await ui.expect(page.locator('.access-error')).toBeVisible()
    await ui.expect(save).toBeEnabled()
    const snapshot = () => dbRows(ui, `select coalesce(jsonb_agg(jsonb_build_object('id',id,'code',role_code,'name',role_name,'version',row_version)),'[]'::jsonb) from erp.app_roles where role_name=${lit(name)}`)
    const afterFirst = snapshot()
    if (!emptySuccess(wire.records[0]) || afterFirst.length !== 1) return { status: 'INCOMPLETE', stage: 'FIRST_SAVE_MUST_COMMIT', wire: wire.records, afterFirst }
    await save.click()
    await ui.expect.poll(() => wire.records.length).toBe(2)
    const afterRetry = snapshot()
    const sameEnvelope = JSON.stringify(wire.records[0].request) === JSON.stringify(wire.records[1].request)
    const replayExact = emptySuccess(wire.records[1]) && JSON.stringify(wire.records[0].body) === JSON.stringify(wire.records[1].body)
    const assignedUsers = Number(ui.sql(`select count(*) from erp.app_users u join erp.app_roles r on r.id=u.role_id where r.role_name=${lit(name)}`))
    return { status: sameEnvelope && replayExact && afterRetry.length === 1 ? 'PASS' : 'COUNTEREXAMPLE',
      oracle: 'M1679/M3819: retry same intent preserves identity and produces one role definition, exact replay',
      transport_fault: 'server real response received by route.fetch, then browser reply discarded',
      first_commit_confirmed: true, sameEnvelope, replayExact, afterFirst, afterRetry, assignedUsers,
      wire: wire.records, permission_keys: wire.records[0].request.p_payload.permission_keys,
      privilege_escalation_claimed: false }
  } finally { await u.context.close() }
}
function fixture(scope, today) {
  const raw = execFileSync('python', [resolve(here, 'gpt_unknown_fixture_rev2.py'), scope, String(today)],
    { cwd: resolve(process.cwd(), '../writer'), encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 })
  return JSON.parse(raw.trim().split('\n').at(-1))
}
async function unknownRead(ui, today, scope) {
  const f = fixture(scope, today)
  const u = await ui.login('OWNER', { label: 'unknown-' + scope })
  const { page } = u
  try {
    const args = { p_scope: scope, p_query: null }
    const control = await u.rpc('erp_get_laundry_qc_workspace_v1', args)
    if (control.status !== 200) return { status: 'INCOMPLETE', stage: 'POSITIVE_WORKSPACE_CONTROL', response: control }
    const ws = control.body
    const expectedPositive = scope === 'LAUNDRY'
      ? ws.deliveries.reduce((s, r) => s + Number(r.physical_outstanding_qty_pcs), 0)
      : ws.qc_queue.reduce((s, r) => s + Number(r.available_for_qc_qty_pcs), 0)
    if (!(expectedPositive >= 10)) return { status: 'INCOMPLETE', stage: 'NONZERO_FIXTURE_REQUIRED', expectedPositive, fixture: f, keys: Object.keys(ws) }
    let dropped = 0
    const url = '**/rpc/erp_get_laundry_qc_workspace_v1'
    const handler = async route => {
      if (route.request().method() === 'POST' && route.request().postDataJSON().p_scope === scope) {
        dropped++; await route.abort('failed')
      } else await route.continue()
    }
    await page.route(url, handler)
    const label = scope === 'LAUNDRY' ? 'Laundry' : 'QC & Final SKU'
    await navigate(page, label)
    await ui.expect(page.locator('.clq-alert.error')).toBeVisible()
    await ui.expect(page.getByRole('button', { name: 'Muat ulang data', exact: true })).toBeEnabled()
    const cards = await page.locator('.clq-kpis article').evaluateAll(es => es.map(e => ({ label: e.querySelector('span')?.textContent, value: e.querySelector('strong')?.textContent, text: e.textContent })))
    const primary = cards[scope === 'LAUNDRY' ? 1 : 0]
    const initialError = await page.locator('.clq-alert.error').innerText()
    const bodyText = await page.locator('.connected-laundry-qc-page').innerText()
    const initialWriterLocked = bodyText.includes('Data belum tersedia; semua tombol transaksi tetap terkunci.')
    await page.unroute(url, handler)
    const responseWait = page.waitForResponse(r => r.url().endsWith('/rpc/erp_get_laundry_qc_workspace_v1') && r.request().method() === 'POST' && r.request().postDataJSON().p_scope === scope)
    await page.getByRole('button', { name: 'Muat ulang data', exact: true }).click()
    const response = await responseWait
    const target = page.locator('.clq-kpis article').nth(scope === 'LAUNDRY' ? 1 : 0).locator('strong')
    const refetchBody = await response.json()
    let renderError = null
    try { await ui.expect(target).toHaveText(String(expectedPositive)) }
    catch (e) { renderError = String(e.message).slice(0, 1500) }
    const after = await target.innerText()
    const refetchError = await page.locator('.clq-alert.error').innerText().catch(() => '')
    if (renderError) return { status: 'INCOMPLETE', stage: 'POSITIVE_REFETCH_CONTROL', scope,
      fixture: f, actual_server_qty: expectedPositive, dropped_reads: dropped,
      initial_kpis: cards, primary, initialError, initialWriterLocked,
      refetch_http_status: response.status(), refetch_error_ui: refetchError, rendered_qty: after,
      refetch_workspace_keys: Object.keys(refetchBody ?? {}),
      refetch_products: refetchBody?.lookups?.products ?? null,
      refetch_readiness: refetchBody?.readiness ?? null,
      renderError, no_product_finding_promoted_from_failed_control: true }

    const falseZero = primary?.value?.trim() === '0'
    return { status: falseZero ? 'COUNTEREXAMPLE' : 'PASS', oracle: 'M3825: failed initial read is unknown, not an authoritative zero; successful refetch restores actual nonzero value',
      scope, fixture: f, real_auth_control_status: control.status, actual_server_qty: expectedPositive,
      dropped_reads: dropped, initial_kpis: cards, primary, initialError, initialWriterLocked,
      refetch_http_status: response.status(), refetched_qty: after,
      no_mutation_bypass_claimed: true, no_financial_finality_claimed: true }
  } finally { await u.context.close() }
}

export async function cases(ui, today) {
  return [
    ['G8UI:UNKNOWN:LAUNDRY_INITIAL_READ:rev2', () => unknownRead(ui, today, 'LAUNDRY')],
    ['G8UI:UNKNOWN:QC_INITIAL_READ:rev2', () => unknownRead(ui, today, 'QC')],
  ]
}
