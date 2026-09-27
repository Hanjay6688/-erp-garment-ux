// Writer verification on actual Auth + browser + BD/BE database. No independent closure.
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
// The runtime copies this entrypoint to RUNNER_TEMP; cwd is the checked-out auditor repository.
const [{ cases: originalBd }, { cases: completion }, { cases: originalBe }] = await Promise.all(
  ['cp6_bd_browser.mjs', 'cp6_bd_completion_browser.mjs', 'cp6_be_browser.mjs'].map(name => import(pathToFileURL(resolve('scripts', name)).href)))
const fixture = (operation, payload) => JSON.parse(execFileSync('python', ['../auditor/scripts/cp6_bd_revision_fixture.py', operation, JSON.stringify(payload)],
  { cwd: '../writer', encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }).trim())
async function openPricing(ui, user, vendor) {
  const p = user.page, menu = p.getByRole('button', { name: 'Buka menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: '• Laundry', exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Produksi' }).click()
  await link.click(); await p.getByRole('button', { name: 'Harga & tagihan', exact: true }).click()
  const ready = () => ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
  await ready(); await p.getByLabel('Vendor harga laundry', { exact: true }).selectOption(vendor); await ready()
  return { p, ready }
}
async function priced(ui, today, kind, mobile, freeStatus = null) {
  const f = fixture('create', { kind, today }), owner = await ui.login('OWNER', { label: 'bd-revision-' + kind + '-' + mobile, mobile })
  const replies = []
  owner.page.on('response', async r => { if (r.url().includes('/rpc/erp_save_laundry_bd_action_v1')) {
    try { replies.push({ request: r.request().postDataJSON(), status: r.status(), body: await r.json() }) } catch {}
  } })
  try {
    const { p, ready } = await openPricing(ui, owner, f.vendor)
    if (freeStatus) {
      await p.getByRole('button', { name: 'Harga vendor', exact: true }).click()
      await p.getByLabel('Alasan', { exact: true }).fill('Owner documented browser ' + freeStatus)
      await p.getByLabel('Berlaku sejak (WIB)', { exact: true }).fill(f.day + 'T10:00')
      await p.getByLabel('Komponen harga', { exact: true }).selectOption(f.wash)
      await p.getByLabel('Status harga komponen', { exact: true }).selectOption(freeStatus)
      await p.getByRole('button', { name: 'Simpan versi harga komponen', exact: true }).click()
      await ui.expect.poll(() => fixture('read', f).components.find(c => c.id === f.wash)?.current.status, { timeout: 20000 }).toBe(freeStatus)
      await ready()
    }
    await p.getByRole('button', { name: 'Kirim dengan harga', exact: true }).click()
    await p.getByLabel('Batch kirim berharga', { exact: true }).selectOption(f.batch)
    await p.getByLabel('Proses kirim berharga', { exact: true }).selectOption(f.process)
    await p.getByLabel('Warna kirim berharga', { exact: true }).fill('REV-NAVY')
    await p.getByLabel('Waktu kirim berharga', { exact: true }).fill(f.day + 'T11:00')
    await p.getByLabel('Bukti serah terima', { exact: true }).fill('Browser audited explicit service recipient')
    for (const s of f.sizes) await p.getByLabel('Qty kirim berharga ' + s.code, { exact: true }).fill(String(s.qty))
    if (kind === 'package') {
      await p.getByLabel('Paket kirim berharga', { exact: true }).selectOption(f.package)
      await ui.expect(p.getByLabel('Cakupan REV_WASH ' + f.sizes[0].code, { exact: true })).toHaveCount(0)
      await p.getByLabel('Cakupan REV_FINISH ' + f.sizes[1].code, { exact: true }).fill('7')
      await p.getByLabel(/Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah/).check()
      await ui.expect(p.getByRole('button', { name: 'Catat kiriman berharga', exact: true })).toBeDisabled()
      await p.getByLabel('Cakupan REV_FINISH ' + f.sizes[1].code, { exact: true }).fill('5')
      await p.getByLabel(/Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah/).check()
      await ui.expect(p.getByRole('button', { name: 'Catat kiriman berharga', exact: true })).toBeDisabled()
      await p.getByLabel('Alasan tambahan REV_FINISH', { exact: true }).fill('Only five second-size pieces need finishing')
    } else {
      for (const s of f.sizes) await p.getByLabel('Cakupan REV_WASH ' + s.code, { exact: true }).fill(String(s.qty))
    }
    await p.getByLabel(/Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah/).check()
    await p.getByRole('button', { name: 'Catat kiriman berharga', exact: true }).click()
    await ui.expect.poll(() => fixture('read', f).deliveries.length, { timeout: 20000 }).toBe(1); await ready()
    const d = fixture('read', f).deliveries[0], request = replies.find(x => x.request.p_action === 'POST_PRICED_DELIVERY')
    const checks = { complete: d.total_complete, qty: d.qty_sent === 13, response: request?.status === 200 && String(request.body.estimated_cost) === (freeStatus ? '0' : '59568.72'),
      amount: d.total_known === (freeStatus ? '0.00' : '59568.72'), one_delivery: fixture('read', f).deliveries.length === 1,
      coverage: kind === 'package' ? d.charges.find(c => c.kind === 'EXTRA')?.coverage.length === 1
        && d.charges.find(c => c.kind === 'EXTRA').coverage[0].size_id === f.sizes[1].id && d.charges.find(c => c.kind === 'EXTRA').coverage[0].qty === 5
        : d.charges[0].rate_status === freeStatus && d.charges[0].price_reason === 'Owner documented browser ' + freeStatus }
    return { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, mobile, kind, freeStatus, delivery: d, replies }
  } catch (e) { throw new Error(String(e) + '; alerts=' + JSON.stringify(await owner.page.getByRole('alert').allTextContents()) + '; replies=' + JSON.stringify(replies)) }
  finally { await owner.context.close() }
}
async function pages(ui, today) {
  const f = fixture('create', { kind: 'pages', today }), owner = await ui.login('OWNER', { label: 'bd-pages-mobile', mobile: true })
  try {
    const { p, ready } = await openPricing(ui, owner, f.vendor)
    await p.getByRole('button', { name: 'Invoice vendor', exact: true }).click()
    await ui.expect(p.getByText('50 invoice dimuat', { exact: true })).toBeVisible()
    await ui.expect(p.getByText('200 penerimaan dimuat', { exact: true })).toBeVisible()
    await p.getByRole('button', { name: /^Ubah draf INV-/ }).first().click()
    const number = 'BROWSER-PAGING-' + f.vendor.slice(0, 8)
    await p.getByLabel('Nomor invoice vendor', { exact: true }).fill(number)
    await p.getByLabel('Total invoice', { exact: true }).fill('17.31')
    await p.getByLabel('Nominal baris 1', { exact: true }).fill('17.31')
    await p.getByRole('button', { name: 'Muat invoice berikutnya', exact: true }).click(); await ready()
    await ui.expect(p.getByText('55 invoice dimuat', { exact: true })).toBeVisible()
    await p.getByRole('button', { name: 'Muat penerimaan berikutnya', exact: true }).click(); await ready()
    await ui.expect(p.getByText('201 penerimaan dimuat', { exact: true })).toBeVisible()
    await ui.expect(p.getByLabel('Nomor invoice vendor', { exact: true })).toHaveValue(number)
    await ui.expect(p.getByLabel('Total invoice', { exact: true })).toHaveValue('17.31')
    await ui.expect(p.getByLabel('Nominal baris 1', { exact: true })).toHaveValue('17.31')
    const options = await p.getByLabel('Sumber baris 1', { exact: true }).locator('option').evaluateAll(xs => xs.map(x => x.value).filter(x => x.startsWith('r:')))
    await p.getByLabel('Sumber baris 1', { exact: true }).selectOption(options.at(-1))
    await p.getByRole('button', { name: 'Simpan draf invoice', exact: true }).click()
    await ui.expect.poll(() => fixture('read', f).all_invoices.some(i => i[1] === number), { timeout: 20000 }).toBe(true)
    const checks = { sources_reachable_once: options.length === 201 && new Set(options).size === 201,
      unchanged_invoice_count: fixture('read', f).all_invoices.length === 55, form_preserved_and_saved: true }
    return { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, mobile: true, invoice_count: 55, source_count: options.length }
  } finally { await owner.context.close() }
}
export async function cases(ui, today) {
  return [...await originalBd(ui, today), ...await completion(ui, today),
    ...(await originalBe(ui, today)).filter(([id]) => id === 'BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE'),
    ['BD_REV_BROWSER:PACKAGE_EXTRA_SIZE_DESKTOP', () => priced(ui, today, 'package', false)],
    ['BD_REV_BROWSER:PACKAGE_EXTRA_SIZE_MOBILE', () => priced(ui, today, 'package', true)],
    ['BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP', () => priced(ui, today, 'free', false, 'FREE')],
    ['BD_REV_BROWSER:WAIVED_MASTER_THEN_PHYSICAL_MOBILE', () => priced(ui, today, 'free', true, 'WAIVED')],
    ['BD_REV_BROWSER:PAGING_PRESERVES_EDIT_MOBILE', () => pages(ui, today)]]
}
