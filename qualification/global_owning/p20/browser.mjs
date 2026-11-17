import assert from 'node:assert/strict'

const finance = 'erp_cp7_get_finance_analysis_v1'
const literal = value => "'" + String(value).replaceAll("'", "''") + "'"
const priorDay = date => new Date(Date.parse(date + 'T00:00:00Z') - 86400000).toISOString().slice(0,10)
const button = (target, name) => target.getByRole('button', { name, exact: true })
const field = (target, label) => target.getByLabel(label, { exact: true })
const read = (page, rpc, match) => page.waitForResponse(response =>
  response.url().endsWith('/rpc/' + rpc) && match(response.request().postDataJSON() ?? {}))

async function open(page, group, label) {
  const menu = button(page, 'Buka menu')
  if (await menu.isVisible()) await menu.click()
  const link = button(page, '• ' + label)
  if (!await link.isVisible()) await page.locator('.sidebar .nav-main').filter({ hasText: group }).click()
  await link.click()
}

function comparison(body) {
  assert.ok(!Object.hasOwn(body, 'cash'), 'P20_CASH_PAYLOAD_LEAK')
  for (const period of ['current', 'baseline']) {
    assert.deepEqual(Object.keys(body.comparison[period]).sort(),
      ['basis', 'data_confidence', 'performance'], 'P20_COMPARISON_FIELD_SCOPE')
  }
}

async function expectHttp(reply, wanted, label) {
  if (reply.status() === wanted) return
  const payload = await reply.json().catch(() => ({}))
  const state = /^(?:[A-Z0-9]{5}|PGRST[0-9]{3})$/.test(payload.code ?? '') ? payload.code : 'UNKNOWN'
  const reason = /^(?:CP[67]_|GLOBAL_)[A-Z0-9_]{3,85}$/.test(payload.message ?? '') ? payload.message
    : /^permission denied for (?:schema|function|table) [a-z_][a-z0-9_]{1,65}$/.test(payload.message ?? '')
      ? payload.message.toUpperCase().replaceAll(' ', '_') : 'UNAVAILABLE'
  throw new Error(label + '_' + reply.status() + '_' + state + '_' + reason)
}
async function denied(reply) {
  assert.equal(reply.status, 403, 'P20_CASH_REVOCATION_HTTP_STATUS')
  assert.equal(reply.body?.code, '42501', 'P20_CASH_REVOCATION_SQLSTATE')
  assert.equal(reply.body?.message, 'CP7_FINANCE_CASH_ACCESS_DENIED', 'P20_CASH_REVOCATION_MESSAGE')
}

async function viewReport(ui, page, day, withCash) {
  await open(page, 'Keuangan', 'Laporan & Tutup Buku')
  for (const label of ['Periode laporan dari', 'Periode laporan sampai', 'Posisi laporan pada']) {
    await field(page, label).fill(day)
  }
  await button(page, 'Tampilkan laporan').click()
  const panel = page.locator('.cfinance-analysis')
  await ui.expect(panel).toBeVisible()
  await button(panel, withCash ? 'Buka perbandingan & arus kas' : 'Buka perbandingan').click()
  return panel
}

async function cashAccess(ui, today) {
  const day = priorDay(today)
  const activeCash = await ui.login('ADMIN', { label: 'p20-cash' })
  const activeReport = await ui.login('ADMIN', { label: 'p20-report' })
  const cashPage = activeCash.page
  const reportPage = activeReport.page
  const cash = cashPage.getByRole('main', { name: 'Kas dan bank dari jurnal', exact: true })
  const cashDetails = page => page.getByRole('region', { name: 'Arus kas menurut jurnal', exact: true })
  const submitCash = button(cash, 'Tampilkan kas')
  const grantFilter = "role_id = (select role_id from erp.app_users where auth_user_id=" +
    literal(activeReport.user.id) + "::uuid and role='ADMIN') and permission_key='finance.cash.view'"
  let grant = ''
  let fresh
  const cashRows = []
  const stableCash = []
  let query
  try {
    await open(cashPage, 'Keuangan', 'Kas & Bank')
    await field(cash, 'Periode kas dari').fill(day)
    await field(cash, 'Periode kas sampai').fill(day)
    await field(cash, 'Cari jurnal kas').fill('P20-PAGE-RECEIPT')
    for (const [offset, trigger, count] of [[0, submitCash, 25],
      [25, button(cash, 'Jurnal berikutnya'), 10]]) {
      const response = read(cashPage, finance, body => body.p_query?.offset === offset
        && body.p_query?.entry_q === 'P20-PAGE-RECEIPT')
      await trigger.click()
      const reply = await response
      await expectHttp(reply, 200, 'P20_CASH_GRANTED_HTTP')
      query = reply.request().postDataJSON().p_query
      const body = await reply.json()
      assert.equal(body.cash.entries.total, '35', 'P20_CASH_EXPECTED_FILTERED_COUNT')
      assert.equal(body.cash.entries.rows.length, count, 'P20_CASH_EXPECTED_PAGE_COUNT')
      assert.ok(body.cash.reconciled, 'P20_CASH_EXPECTED_RECONCILIATION')
      cashRows.push(...body.cash.entries.rows.map(row => row.id))
      stableCash.push(body.cash)
      await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(count)
    }
    assert.equal(new Set(cashRows).size, 35, 'P20_CASH_DUPLICATED_PAGE_ENTRIES')
    const panel = await viewReport(ui, reportPage, day, true)
    const check = button(panel, 'Periksa perbandingan & kas')
    const withCash = read(reportPage, finance, body => body.p_query?.comparison_only !== true)
    await check.click()
    const full = await withCash
    await expectHttp(full, 200, 'P20_REPORT_GRANTED_HTTP')
    assert.ok((await full.json()).cash, 'P20_REPORT_GRANTED_CASH_REQUIRED')
    await ui.expect(cashDetails(reportPage)).toBeVisible()

    grant = ui.sql("with removed as (delete from erp.app_role_permissions where " + grantFilter
      + " returning role_id,permission_key,granted_by,granted_at) select row_to_json(removed) from removed")
    assert.ok(grant, 'P20_CASH_INITIAL_ADMIN_GRANT_REQUIRED')
    const oldCash = read(cashPage, finance, body => body.p_query?.offset === 25)
    await submitCash.click()
    const oldReply = await oldCash
    await denied({ status: oldReply.status(), body: await oldReply.json() })
    await ui.expect(cash.getByRole('alert')).toBeVisible()
    await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(0)
    assert.ok(!(await cash.innerText()).includes('Rp'), 'P20_CASH_OLD_MONEY_VISIBLE')

    const oldReport = read(reportPage, finance, body => body.p_query?.comparison_only !== true)
    const fallback = read(reportPage, finance, body => body.p_query?.comparison_only === true)
    await check.click()
    const reportReply = await oldReport
    await denied({ status: reportReply.status(), body: await reportReply.json() })
    const comparisonReply = await fallback
    await expectHttp(comparisonReply, 200, 'P20_REPORT_FALLBACK_HTTP')
    comparison(await comparisonReply.json())
    await ui.expect(cashDetails(reportPage)).toHaveCount(0)
    await ui.expect(panel.getByRole('region', { name: 'Kinerja periode ini' })).toBeVisible()

    fresh = await ui.login('ADMIN', { label: 'p20-fresh' })
    assert.equal(fresh.user.id, activeReport.user.id, 'P20_FRESH_LOGIN_SUBJECT_CHANGED')
    assert.notEqual(fresh.sessionId, activeReport.sessionId, 'P20_FRESH_LOGIN_REUSED_ISSUER_SESSION')
    assert.ok(fresh.sessionId && activeReport.sessionId && activeCash.sessionId, 'P20_ISSUER_SESSION_MISSING')
    const freshPanel = await viewReport(ui, fresh.page, day, false)
    await ui.expect(button(fresh.page, '• Kas & Bank')).toHaveCount(0)
    const liveComparison = read(fresh.page, finance, body => body.p_query?.comparison_only === true)
    await button(freshPanel, 'Periksa perbandingan').click()
    const freshReply = await liveComparison
    await expectHttp(freshReply, 200, 'P20_FRESH_REPORT_COMPARISON_HTTP')
    comparison(await freshReply.json())
    await ui.expect(cashDetails(fresh.page)).toHaveCount(0)
    for (const actor of [activeCash, activeReport, fresh]) {
      const profile = await actor.rpc('erp_get_my_access_v1', {})
      assert.equal(profile.status, 200, 'P20_CASH_REAL_PROFILE_HTTP')
      assert.ok(profile.body.permissions.includes('finance.reports.view'), 'P20_REPORT_GRANT_LOST')
      assert.ok(!profile.body.permissions.includes('finance.cash.view'), 'P20_CASH_REVOKED_GRANT_STILL_PRESENT')
      for (const offset of [0,25]) await denied(await actor.rpc(finance, { p_query: {...query, offset} }))
    }
  } finally {
    try {
      if (grant) {
        const row = "json_populate_record(null::erp.app_role_permissions," + literal(grant) + "::json)"
        ui.sql("insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at) " +
          "select role_id,permission_key,granted_by,granted_at from " + row)
      }
    } finally {
      await Promise.all([activeCash.context.close(), activeReport.context.close(), fresh?.context.close()])
    }
  }
  assert.equal(ui.sql("select row_to_json(p) from (select role_id,permission_key,granted_by,granted_at " +
    "from erp.app_role_permissions where " + grantFilter + ") p"), grant, 'P20_CASH_GRANT_RESTORE_MISMATCH')
  // The UI session is closed only after the exact row has been restored.
  // rpc() uses its same signed token from the real browser sign-in.
  for (const [index, offset] of [0,25].entries()) {
    const restored = await activeCash.rpc(finance, { p_query: {...query, offset} })
    assert.equal(restored.status, 200, 'P20_CASH_RESTORED_GRANT_HTTP')
    assert.deepEqual(restored.body.cash, stableCash[index], 'P20_CASH_RESTORED_PAGE_CHANGED')
  }
  return { status: 'PASS', cash_pages: [25,10], old_cash: 403, old_report: [403,200],
    fresh_report: 200, fresh_cash: 403, stale_data_retired: true, exact_grant_restored: true,
    separate_issuer_sessions: true }
}

export async function cases(ui, today) {
  return [['P20_AUTH_CASH_01_02', () => cashAccess(ui,today)]]
}
