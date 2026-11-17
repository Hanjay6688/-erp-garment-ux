import assert from 'node:assert/strict'

const finance = 'erp_cp7_get_finance_analysis_v1'
const sales = 'erp_cp7_save_sale_v1'
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
      assert.equal(reply.status(), 200, 'P20_CASH_GRANTED_HTTP')
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
    assert.equal(full.status(), 200, 'P20_REPORT_GRANTED_HTTP')
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
    assert.equal(comparisonReply.status(), 200, 'P20_REPORT_FALLBACK_HTTP')
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
    assert.equal(freshReply.status(), 200, 'P20_FRESH_REPORT_COMPARISON_HTTP')
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

async function saveSale(page, action, control) {
  const response = read(page, sales, body => body.p_action === action)
  await control.click()
  const reply = await response
  assert.equal(reply.status(), 200, 'P20_SALE_' + action + '_HTTP')
  return { body: await reply.json(), request: reply.request().postDataJSON() }
}

async function postSale(ui) {
  const f = JSON.parse(process.env.P20_GLOBAL_SALE_FIXTURE)
  const actor = await ui.login('OWNER', { label: 'p20-sale' })
  const page = actor.page, ws = page.locator('.csales')
  const form = ws.getByRole('form', {name:'Draft invoice'}), detail = ws.getByRole('complementary', {name:'Rincian invoice'})
  const cashless = sum => ui.sql("select count(*) from erp.journal_entries where source_type='SALE' and source_id=" + literal(sum) + "::uuid")
  const positions = () => f.members.map(member => JSON.parse(ui.sql(
    'select json_build_array(physical_qty,reserved_qty,available_qty) from cp7_fg.positions(\'\',true) where lot_id='
      + literal(member.lot) + '::uuid and product_id=' + literal(member.product) + '::uuid and location_id='
      + literal(f.location) + "::uuid and quality_grade='GRADE_A'")))
  try {
    await open(page, 'Penjualan', 'Penjualan & Invoice')
    await button(ws, 'Buat invoice').click()
    await field(form, 'Nomor draft invoice').fill(f.tag)
    const wib = new Date(Date.parse(f.sale_at) + 7 * 3600000).toISOString().slice(0,16)
    await field(form, 'Waktu draft invoice WIB').fill(wib)
    await field(form, 'Cari pelanggan draft').fill(f.tag)
    await button(form, 'Cari pelanggan draft').click()
    const customers = form.getByRole('region', {name:'Pilih pelanggan invoice'}).locator('.cproc-receipt')
    await ui.expect(customers).toHaveCount(1)
    await customers.click()
    for (const series of [0,2]) {
      await field(form, 'Cari barang draft').fill(f.members[series].sku)
      await button(form, 'Cari barang draft').click()
      const option = form.getByRole('region', {name:'Pilih barang invoice'}).locator('.cproc-receipt')
      await ui.expect(option).toHaveCount(1)
      await option.click()
      await ui.expect(form.locator('.cproc-series')).toHaveCount(series === 0 ? 1 : 2)
    }
    const first = form.locator('.cproc-series').filter({ has: page.getByRole('heading', {name:/SKU P20-X · Y · Merek Z/}) })
    const second = form.locator('.cproc-series').filter({ has: page.getByRole('heading', {name:/SKU P20-X · Merek Y · Z/}) })
    const quantities = form.locator('input[aria-label^="Jumlah invoice "]')
    await ui.expect(quantities).toHaveCount(4)
    await ui.expect(first.locator('input[aria-label^="Jumlah invoice "]')).toHaveCount(2)
    await ui.expect(second.locator('input[aria-label^="Jumlah invoice "]')).toHaveCount(2)
    await quantities.nth(0).fill('8')
    await quantities.nth(2).fill('4')
    await first.getByRole('button', {name:/^Bagi rata ke 2 ukuran/}).click()
    await ui.expect(quantities.nth(0)).toHaveValue('6')
    await ui.expect(quantities.nth(2)).toHaveValue('4')
    await second.getByRole('button', {name:/^Bagi rata ke 2 ukuran/}).click()
    for (const [index, price] of ['20','20','30','30'].entries()) {
      await ui.expect(quantities.nth(index)).toHaveValue('6')
      await field(form, 'Harga invoice '+(index+1)).fill(price)
    }
    const reviewDraft = async () => {
      await field(form, 'Alasan simpan invoice').fill('P20 sumber dan nilai transaksi diperiksa')
      await field(form, 'Draft invoice sudah diperiksa').check()
    }
    await reviewDraft()
    const create = await saveSale(page, 'CREATE', button(form, 'Simpan draft invoice'))
    const sale = create.body.sale_id
    assert.match(sale, /^[a-f0-9-]{36}$/, 'P20_SALE_ID_MISSING')
    await ui.expect(detail).toContainText('24 PCS masih dipesan')
    const createdStock = positions()
    assert.deepEqual(createdStock, [[20,6,14],[20,6,14],[20,6,14],[20,6,14]], 'P20_SALE_CREATE_STOCK')
    assert.equal(cashless(sale), '0', 'P20_SALE_CREATE_JOURNAL')
    await button(detail, 'Edit draft invoice').click()
    const editedLine = form.locator('article').filter({hasText:f.members[0].sku}).locator('input[aria-label^="Jumlah invoice "]')
    await ui.expect(editedLine).toHaveValue('6')
    await editedLine.fill('7')
    await reviewDraft()
    assert.equal((await saveSale(page, 'EDIT', button(form, 'Simpan draft invoice'))).body.sale_id, sale)
    await ui.expect(detail).toContainText('25 PCS masih dipesan')
    const editedStock = positions()
    assert.deepEqual(editedStock, [[20,7,13],[20,6,14],[20,6,14],[20,6,14]], 'P20_SALE_EDIT_STOCK')
    assert.equal(cashless(sale), '0', 'P20_SALE_EDIT_JOURNAL')
    await field(detail, 'Catatan tindakan invoice').fill('P20 posting atas empat baris yang telah diperiksa')
    await field(detail, 'Invoice sudah diperiksa').check()
    const post = await saveSale(page, 'POST', button(detail, 'Sahkan invoice'))
    assert.equal(post.body.status, 'POSTED', 'P20_SALE_POST_TERMINAL')
    await ui.expect(detail).toContainText('Sisa pembayaran Rp620')
    const postedStock = positions()
    assert.deepEqual(postedStock, [[13,0,13],[14,0,14],[14,0,14],[14,0,14]], 'P20_SALE_POST_STOCK')
    const saleId = literal(sale) + '::uuid'
    const hpp = JSON.parse(ui.sql('select json_build_array(sum(a.qty_pcs),sum(a.total_hpp),min(a.unit_hpp_snapshot),' +
      'max(a.unit_hpp_snapshot),count(*)) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=' + saleId))
    assert.deepEqual(hpp, [25,250,10,10,4], 'P20_SALE_NATIVE_HPP')
    const actual = JSON.parse(ui.sql('select json_object_agg(mapping_key,amount) from (select a.mapping_key,sum(l.debit-l.credit) amount ' +
      'from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id ' +
      'join erp.accounting_account_mappings a on a.account_id=l.account_id ' +
      "where j.source_type='SALE' and j.source_id=" + saleId + ' group by a.mapping_key) result'))
    const journal = {AR_CUSTOMER:620, SALES_REVENUE:-620, FG_INVENTORY:-250, COGS:250}
    assert.deepEqual(actual, journal, 'P20_SALE_NATIVE_GL')
    assert.equal(cashless(sale), '1', 'P20_SALE_GL_COUNT')
    const replay = await actor.rpc(sales, post.request)
    assert.equal(replay.status, 200, 'P20_SALE_EXACT_UUID_HTTP')
    assert.deepEqual(replay.body, post.body, 'P20_SALE_EXACT_UUID_RESPONSE')
    assert.deepEqual(positions(), postedStock, 'P20_SALE_REPLAY_STOCK_CHANGE')
    assert.equal(cashless(sale), '1', 'P20_SALE_REPLAY_GL_CHANGE')
    return {status:'PASS',sale_id:sale,series_counts:[2,2],full_lifecycle:['CREATE','EDIT','POST'],
      stock:{created:createdStock,edited:editedStock,posted:postedStock},sale_hpp:250,journal,replay:true}
  } finally {
    await actor.context.close()
  }
}

export async function cases(ui, today) {
  return [['P20_AUTH_CASH_01_02', () => cashAccess(ui,today)], ['P20_SALE_SERIES_BROWSER', () => postSale(ui)]]
}
