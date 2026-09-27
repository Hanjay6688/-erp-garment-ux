// Independent BE browser acceptance on disposable Supabase Auth + real RPC.
import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import http from 'node:http'
import { chromium, expect } from '@playwright/test'

const origin = 'http://127.0.0.1:4176'
const api = 'http://127.0.0.1:54321'
const productApi = 'http://127.0.0.1:54328'
const out = 'be-blind-browser-results.json'
const report = { candidate: '2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b',
  production_go: false, status: 'INCOMPLETE', real_auth: true,
  mocked_product_responses: false, cases: {}, console_errors: [] }
const save = () => writeFileSync(out, JSON.stringify(report, null, 2) + '\n')
const fixture = (action, payload) => JSON.parse(execFileSync('python',
  ['scripts/cp6_be_blind_browser_fixture.py', action, JSON.stringify(payload)],
  { encoding: 'utf8', env: process.env }).trim())
const status = execFileSync('supabase', ['status', '--workdir', 'cp6-be-blind-local', '-o', 'env'],
  { encoding: 'utf8' })
const values = Object.fromEntries(status.trim().split('\n').filter(x => x.includes('='))
  .map(line => { const [key, ...parts] = line.replace(/^export /, '').split('='); return [key, parts.join('=').replace(/^['"]|['"]$/g, '')] }))
const anon = values.ANON_KEY, service = values.SERVICE_ROLE_KEY
assert.ok(anon && service && values.API_URL === api, 'BLIND_BROWSER_LOOPBACK_ONLY')
const users = []
async function auth(path, key, body, method = 'POST') {
  const response = await fetch(`${api}/auth/v1/${path}`, { method,
    headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body) })
  const text = await response.text()
  return { status: response.status, body: text ? JSON.parse(text) : {} }
}
async function owner() {
  const email = `blind-be-${randomUUID()}@example.invalid`
  const password = `A!${randomBytes(24).toString('hex')}`
  const created = await auth('admin/users', service, { email, password, email_confirm: true })
  assert.ok([200, 201].includes(created.status) && created.body.id, `AUTH_CREATE_${created.status}`)
  users.push(created.body.id)
  assert.equal(fixture('bind', { auth_id: created.body.id }).bound, true)
  return { email, password }
}
async function navigate(page, name, group = 'Gudang') {
  const menu = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  const link = page.getByRole('button', { name: '• ' + name, exact: true })
  if (!await link.isVisible()) await page.locator('.sidebar .nav-main').filter({ hasText: group }).click()
  await link.click()
}
async function login(browser, mobile = false) {
  const { email, password } = await owner()
  const context = await browser.newContext({ viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
    timezoneId: mobile ? 'Pacific/Honolulu' : 'UTC', isMobile: mobile, hasTouch: mobile })
  const page = await context.newPage()
  page.setDefaultTimeout(25000)
  page.on('pageerror', error => report.console_errors.push(error.message.slice(0, 600)))
  await page.goto(origin)
  await page.getByLabel('Email akun ERP').fill(email)
  await page.getByLabel('Kata sandi').fill(password)
  await page.getByRole('button', { name: 'Masuk', exact: true }).click()
  await expect(page.locator('.top-title strong')).toBeVisible()
  return { page, context }
}
async function conversion(browser, today, mobile) {
  const f = fixture('create', { kind: 'conversion', today })
  const { page, context } = await login(browser, mobile)
  try {
    await navigate(page, 'Ganti Merek')
    const ready = () => expect(page.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
    await ready()
    await page.getByLabel('Cari lot / SKU', { exact: true }).fill(f.sku)
    await page.getByRole('button', { name: 'Cari lot', exact: true }).click()
    await ready()
    await page.getByLabel(/^Lot dan gudang/).selectOption(f.lot + ':' + f.location)
    await page.getByLabel('Cari SKU tujuan', { exact: true }).fill(f.target_sku)
    await page.getByRole('button', { name: 'Cari tujuan', exact: true }).click()
    await ready()
    await page.getByLabel(/^SKU tujuan/).selectOption(f.target)
    await page.getByLabel('Jumlah PCS', { exact: true }).fill('6')
    await page.getByLabel('Waktu fisik · WIB', { exact: true }).fill(f.day + 'T15:00')
    await page.getByLabel('Alasan', { exact: true }).fill('Blind UI lot bersumber')
    await page.getByRole('button', { name: 'Lihat pratinjau', exact: true }).click()
    const post = page.getByRole('button', { name: 'Catat konversi fisik', exact: true })
    await expect(post).toBeEnabled()
    await post.click()
    await expect.poll(() => fixture('read', f).source_qty).toBe(4)
    const after = fixture('read', f)
    assert.equal(after.documents.length, 1)
    assert.equal(after.target_qty, 6)
    assert.equal(after.documents[0][2], f.day)
    assert.equal(after.documents[0][3], '15:00:00')
    const reverse = page.getByRole('button', { name: 'Batalkan ' + f.sku, exact: true })
    await expect(reverse).toBeVisible()
    await reverse.click()
    await page.getByLabel('Alasan pembatalan', { exact: true }).fill('Blind UI inverse lot')
    await page.getByRole('button', { name: 'Konfirmasi pembatalan', exact: true }).click()
    await expect.poll(() => fixture('read', f).source_qty).toBe(10)
    const final = fixture('read', f)
    assert.equal(final.target_qty, 0)
    assert.equal(final.documents[0][1], 'REVERSED')
    return { status: 'PASS', mobile, timezone: mobile ? 'Pacific/Honolulu' : 'UTC',
      posted: [after.source_qty, after.target_qty], inverse: [final.source_qty, final.target_qty],
      economic_day: after.documents[0][2] }
  } finally { await context.close() }
}
async function pocketCsv(browser, today) {
  const f = fixture('create', { kind: 'pocket-import', today })
  const { page, context } = await login(browser)
  const responseCodes = []
  try {
    await navigate(page, 'Impor data awal', 'Pengaturan & Audit')
    await expect(page.getByLabel('Batch impor', { exact: true })).toBeEnabled()
    await page.getByLabel('Batch impor', { exact: true }).selectOption(f.batch)
    for (const [kind, rows] of Object.entries(f.files)) {
      await page.getByRole('combobox', { name: 'Jenis data', exact: true }).selectOption(kind)
      const fields = [...new Set(rows.flatMap(x => Object.keys(x)))]
      const cell = x => '"' + String(x ?? '').replaceAll('"', '""') + '"'
      const csv = [fields.join(','), ...rows.map(row => fields.map(k => cell(row[k])).join(','))].join('\n') + '\n'
      await page.getByLabel('Pilih file CSV', { exact: true }).setInputFiles({ name: kind + '.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
      const response = page.waitForResponse(r => r.url().includes('/rpc/erp_save_initial_import_action_v1') &&
        r.request().postDataJSON()?.p_action === 'SAVE_FILE')
      await page.getByRole('button', { name: 'Simpan perubahan draft', exact: true }).click()
      responseCodes.push((await response).status())
    }
    const draft = fixture('read', f)
    assert.equal(draft.usage.length, 0)
    assert.equal(draft.sewing.length, 0)
    const submit = async (label, action) => {
      const response = page.waitForResponse(r => r.url().includes('/rpc/erp_save_initial_import_action_v1') &&
        r.request().postDataJSON()?.p_action === action)
      await page.getByRole('button', { name: label, exact: true }).click()
      responseCodes.push((await response).status())
      await expect(page.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
    }
    await submit('Periksa seluruh draft', 'VALIDATE')
    await submit('Sahkan data awal', 'FINALIZE')
    await expect.poll(() => fixture('read', f).status).toBe('POSTED')
    const posted = fixture('read', f)
    assert.deepEqual(responseCodes, Array(responseCodes.length).fill(200))
    assert.equal(posted.usage.length, 1)
    assert.equal(posted.sewing.length, 3)
    assert.equal(posted.sewing.reduce((n, row) => n + Number(row[2]), 0), 10)
    assert.equal(posted.stock_moves, f.stock_moves)
    assert.equal(posted.sewing_events, f.sewing_events)
    return { status: 'PASS', responses: responseCodes, usage: 1, sewing: 3,
      denominator: 10, no_fake_stock_or_sewing: true }
  } finally { await context.close() }
}

async function rework(browser, today, redye) {
  const f = fixture('create', { kind: redye ? 'redye' : 'rework', today })
  const { page, context } = await login(browser, redye)
  try {
    await navigate(page, 'Barang BS & Rework', 'Produksi')
    await expect(page.getByRole('button', { name: 'Refetch', exact: true })).toBeEnabled()
    await page.locator('.cbsr-tabs').getByRole('button', { name: 'Semua', exact: true }).click()
    await page.getByPlaceholder('Nomor, PO, model, Pola, pihak…').fill(f.bs_number)
    await page.locator('.cbsr-search').getByRole('button', { name: 'Cari', exact: true }).click()
    await page.locator('.cbsr-list button').filter({ hasText: f.bs_number }).click()
    await page.locator('.cbsr-route-tabs').getByRole('button', { name: redye ? 'Rewash' : 'Rework', exact: true }).click()
    const form = page.locator('.cbsr-route-form')
    await form.getByLabel('NOMOR ORDER · WAJIB', { exact: true }).fill(f.number)
    await form.getByLabel(redye ? /^VENDOR REWASH/ : /^MANDOR REWORK/).selectOption(redye ? f.vendor : f.contractor)
    await form.getByLabel('QTY DIKIRIM', { exact: true }).fill('4')
    await form.getByLabel('WAKTU FISIK · WIB', { exact: true }).fill(f.day + 'T14:00')
    await form.getByLabel(/^GUDANG FG BILA GOOD/).selectOption(f.location)
    await form.getByLabel('CATATAN / ALASAN', { exact: true }).fill('Blind UI actual BS service')
    if (!redye) await form.locator('fieldset.cbsr-checks').filter({ has: page.getByText('KOMPONEN KERJA YANG DIULANG · DASAR UPAH REWORK', { exact: true }) }).getByRole('checkbox').first().check()
    for (const box of await form.locator('.cbsr-accessories input[type=checkbox]').all()) await box.uncheck()
    await form.getByRole('checkbox', { name: 'Hasil GOOD menjadi SKU lain', exact: true }).check()
    await form.getByLabel('Cari SKU hasil', { exact: true }).fill(f.target_sku)
    await form.getByRole('button', { name: 'Cari SKU hasil', exact: true }).click()
    await expect(form.getByLabel(/^SKU hasil baru/)).toBeEnabled()
    await form.getByLabel(/^SKU hasil baru/).selectOption(f.target)
    if (redye) {
      await form.getByLabel(/^Proses celup berbayar/).selectOption(f.process)
      await form.getByLabel(/^Harga jasa/).selectOption('UNKNOWN')
    }
    await form.getByRole('button', { name: redye ? 'Buat order celup ulang' : 'Buat order rework', exact: true }).click()
    const completion = () => page.locator('.cbsr-completion-form').filter({ hasText: f.number })
    await expect(completion()).toBeVisible()
    await completion().getByLabel('GOOD KUMULATIF', { exact: true }).fill('1')
    await completion().getByLabel('BS KUMULATIF', { exact: true }).fill('0')
    await completion().getByLabel('ALASAN HASIL FISIK', { exact: true }).fill('Blind actual partial one')
    await completion().getByRole('button', { name: 'Simpan partial', exact: true }).click()
    await expect.poll(() => fixture('read', f).orders[0]?.[2]).toBe(1)
    const partial = fixture('read', f)
    assert.equal(partial.conversions.length, 0)
    assert.equal(partial.orders[0][4], null)
    await completion().getByLabel('GOOD KUMULATIF', { exact: true }).fill('2')
    await completion().getByLabel('BS KUMULATIF', { exact: true }).fill('2')
    await completion().getByLabel('WAKTU SELESAI · WIB', { exact: true }).fill(f.day + 'T16:00')
    await completion().getByLabel('ALASAN HASIL FISIK', { exact: true }).fill('Blind actual two GOOD two BS')
    await completion().getByRole('button', { name: 'Post hasil & recovery', exact: true }).click()
    await expect.poll(() => fixture('read', f).qty).toBe(2)
    const completed = fixture('read', f)
    assert.equal(completed.product, f.target)
    assert.equal(completed.conversions.length, 1)
    if (redye) {
      assert.equal(completed.rate, 'None')
      await navigate(page, 'Laundry', 'Produksi')
      await page.getByRole('button', { name: 'Harga & tagihan', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled()
      await page.getByLabel('Vendor harga laundry', { exact: true }).selectOption(f.vendor)
      await page.getByRole('button', { name: 'Invoice vendor', exact: true }).click()
      await page.getByLabel('Tarif celup ' + f.number, { exact: true }).fill('50.00')
      await page.getByLabel('Alasan pembatalan invoice', { exact: true }).fill('Blind vendor confirms original rate')
      await page.getByRole('button', { name: 'Isi tarif celup ' + f.number, exact: true }).click()
      await expect.poll(() => fixture('read', f).cost).toBe('200.00')
      const priced = fixture('read', f)
      assert.equal(priced.rate, '50.000000')
      return { status: 'PASS', mode: 'paid redye', mobile: true, partial_no_fg: true,
        good: completed.qty, bs: completed.orders[0][3], cost: priced.cost }
    }
    const done = page.locator('.cbsr-rework-complete')
    await done.getByPlaceholder('Alasan reversal Owner/Admin').fill('Blind real UI inverse')
    await done.getByRole('button', { name: 'Reverse', exact: true }).click()
    await expect.poll(() => fixture('read', f).qty).toBe(0)
    const inverse = fixture('read', f)
    assert.equal(inverse.conversions[0][1], 'REVERSED')
    return { status: 'PASS', mode: 'rework', partial_no_fg: true,
      good: completed.qty, bs: completed.orders[0][3], inverse_zero: true }
  } finally { await context.close() }
}

async function pocketBrowser(browser, today) {
  const f = fixture('create', { kind: 'pocket', today })
  const { page, context } = await login(browser, true)
  try {
    await navigate(page, 'Kain kantong')
    await expect(page.getByLabel('Awal periode kain kantong')).toBeEnabled()
    await page.getByLabel('Cari kain kantong', { exact: true }).fill(f.code)
    await page.locator('form').filter({ has: page.getByLabel('Cari kain kantong', { exact: true }) })
      .getByRole('button', { name: 'Cari', exact: true }).click()
    await expect(page.getByText('KELUAR-' + f.code + ' / 1', { exact: true })).toBeVisible()
    await page.getByLabel('Awal periode kain kantong').fill(f.period)
    await page.getByLabel('Akhir periode kain kantong').fill(f.period)
    await page.getByLabel('Alasan pembagian kain kantong').fill('Blind actual historical split')
    await page.getByRole('button', { name: 'Lihat pembagian', exact: true }).click()
    await page.getByRole('button', { name: 'Sahkan pembagian ke HPP', exact: true }).click()
    await expect.poll(() => fixture('read', f).pools.length).toBe(1)
    await page.getByRole('button', { name: 'Koreksi KELUAR-' + f.code + ' / 1', exact: true }).click()
    await page.getByLabel('Nilai sumber kain kantong').fill('15.00')
    await page.getByLabel('Tanggal koreksi kain kantong').fill(today)
    await page.getByLabel('Alasan koreksi kain kantong').fill('Blind corrected source amount')
    await page.getByRole('button', { name: 'Sahkan koreksi nilai', exact: true }).click()
    await expect.poll(() => fixture('read', f).amount).toBe('15.00')
    const after = fixture('read', f)
    const delta = name => Number(after.ledger[name]) - Number(f.before[name])
    assert.equal(delta('WIP'), 7.5)
    assert.equal(delta('FG_INVENTORY'), 4.5)
    assert.equal(delta('COGS'), 3.0)
    assert.equal(after.pools[0][2], f.cut)
    return { status: 'PASS', mobile: true, amount: after.amount,
      allocations: { WIP: 7.5, FG: 4.5, COGS: 3.0 }, economic_day: f.cut }
  } finally { await context.close() }
}

let preview, browser, proxy
try {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Jakarta',
    year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  proxy = http.createServer((req, res) => {
    const allowed = req.headers.origin === origin
    const cors = allowed ? { 'access-control-allow-origin': origin, vary: 'Origin',
      'access-control-allow-headers': 'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile',
      'access-control-allow-methods': 'GET,POST,PUT,DELETE,OPTIONS' } : {}
    if (req.method === 'OPTIONS') { res.writeHead(allowed ? 204 : 403, cors); res.end(); return }
    if (!req.url.startsWith('/auth/v1/') && !req.url.startsWith('/rest/v1/rpc/')) {
      res.writeHead(404, cors); res.end(); return
    }
    const headers = { ...req.headers }; delete headers.host; delete headers.origin
    const upstream = http.request({ hostname: '127.0.0.1', port: 54321, path: req.url,
      method: req.method, headers }, response => {
      const clean = { ...response.headers, ...cors }; delete clean['access-control-allow-credentials']
      res.writeHead(response.statusCode, clean); response.pipe(res)
    })
    upstream.on('error', () => { if (!res.headersSent) res.writeHead(502, cors); res.end() })
    req.pipe(upstream)
  })
  await new Promise((resolve, reject) => { proxy.once('error', reject); proxy.listen(54328, '127.0.0.1', resolve) })
  const safeEnv = Object.fromEntries(['PATH', 'HOME', 'CI', 'TMPDIR', 'RUNNER_TEMP', 'PLAYWRIGHT_BROWSERS_PATH']
    .filter(key => process.env[key]).map(key => [key, process.env[key]]))
  execFileSync('npm', ['run', 'build:cp6-disposable'], { env: {
    ...safeEnv, VITE_ERP_RUNTIME_MODE: 'DISPOSABLE_TEST',
    VITE_SUPABASE_URL: productApi, VITE_SUPABASE_ANON_KEY: anon }, stdio: ['ignore', 'pipe', 'pipe'] })
  preview = spawn('node_modules/.bin/vite', ['preview', '--outDir', 'cp6-ui-build',
    '--host', '127.0.0.1', '--port', '4176', '--strictPort'], { stdio: 'ignore' })
  for (let i = 0; i < 40; i++) {
    try { if ((await fetch(origin)).status === 200) break } catch { /* server booting */ }
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  assert.equal((await fetch(origin)).status, 200)
  browser = await chromium.launch()
  const cases = [
    ['CONVERSION_DESKTOP', () => conversion(browser, today, false)],
    ['CONVERSION_MOBILE', () => conversion(browser, today, true)],
    ['POCKET_MOBILE_CORRECTION', () => pocketBrowser(browser, today)],
    ['REWORK_PARTIAL_COMPLETE_INVERSE', () => rework(browser, today, false)],
    ['REDYE_UNKNOWN_FIRST_PRICE_MOBILE', () => rework(browser, today, true)],
    ['POCKET_CSV_IMPORT', () => pocketCsv(browser, today)],
  ]
  for (const [name, fn] of cases) {
    try { report.cases[name] = await fn() }
    catch (error) { report.cases[name] = { status: 'INCOMPLETE',
      error: String(error?.stack || error).slice(0, 2600) } }
    save()
    console.log(JSON.stringify({ case: name, ...report.cases[name] }))
  }
  report.status = Object.values(report.cases).every(x => x.status === 'PASS') &&
    report.console_errors.length === 0 ? 'PASS' : 'INCOMPLETE'
} catch (error) {
  report.start_failure = String(error?.stack || error).slice(0, 2600)
} finally {
  await browser?.close()
  preview?.kill()
  proxy?.close()
  for (const id of users) await auth(`admin/users/${id}`, service, undefined, 'DELETE').catch(() => {})
  save()
  console.log(JSON.stringify({ status: report.status, cases: Object.fromEntries(Object.entries(report.cases).map(([k, v]) => [k, v.status])),
    console_errors: report.console_errors, start_failure: report.start_failure }))
}
process.exit(report.status === 'PASS' ? 0 : 1)
