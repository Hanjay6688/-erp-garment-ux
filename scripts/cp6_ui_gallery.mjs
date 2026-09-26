// UI gallery (writer; not a test, not evidence): screenshots of the BC and BD pages for the owner's look-and-feel review,
// taken by the browser mode of the auditor runtime (cp6-auditor-scenario.yml, browser_path scripts/cp6_ui_gallery.mjs,
// phase after) against the disposable stack with BC and BD installed, real Auth and the real PostgREST. Nothing is deployed
// and nothing hosted is touched.
// Data: the BC and BD browser flows run first (their own results are reported as SETUP:*), then
// scripts/cp6_ui_gallery_fixture.py commits BD laundry data on the same copy (component prices one known / one unknown, a
// priced delivery, a posted and a draft vendor invoice; it sets LAU-DEC02/06 on this copy only so the invoice can post).
// While the Nota Ambil Aksesori page is captured, the seeded CP3 mandors with non RFC-4122 ids are deactivated on this copy
// (finding F3: the page refuses a read that contains them) and reactivated afterwards. The Laundry page's own tabs are
// captured as they are: on this copy they show "Data belum tersedia" because of the same F3 (seeded CP3 ids).
// Every gallery case returns PASS with one JPEG (base64) of the page or section; the images leave the job only in the log.
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const DESKTOP_MAX = 2200, PHONE_MAX = 2600
const sessions = {}

async function session(ui, key, role, opts) {
  if (!sessions[key]) sessions[key] = await ui.login(role, { label: 'gallery-' + key, ...opts })
  return sessions[key]
}

async function openPage(ui, p, group, item, heading) {
  const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: `• ${item}`, exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: group }).click()
  await link.click()
  await ui.expect(p.getByRole('heading', { name: heading, exact: true }).first()).toBeVisible()
}

async function settle(p) {
  await p.waitForLoadState('networkidle').catch(() => {})
  await p.waitForTimeout(700)
}

async function shot(p, note, section) {
  await settle(p)
  if (section) {
    await section.scrollIntoViewIfNeeded()
    const buf = await section.screenshot({ type: 'jpeg', quality: 50 })
    const box = await section.boundingBox()
    return { status: 'PASS', note, kind: 'section', width: Math.round(box?.width ?? 0), height: Math.round(box?.height ?? 0), jpeg_b64: buf.toString('base64') }
  }
  await p.evaluate(() => window.scrollTo(0, 0))
  const width = p.viewportSize().width, max = width < 600 ? PHONE_MAX : DESKTOP_MAX
  const full = await p.evaluate(() => document.documentElement.scrollHeight)
  const height = Math.min(full, max)
  const buf = await p.screenshot({ type: 'jpeg', quality: 50, fullPage: true, clip: { x: 0, y: 0, width, height } })
  return { status: 'PASS', note, kind: 'page', width, height, page_height: full, jpeg_b64: buf.toString('base64') }
}

const latestBatch = (ui, entity) => ui.sql(`select b.id from erp.migration_batches b where exists(select 1 from erp.migration_staging_rows r
  where r.batch_id=b.id and r.entity_type='${entity}') order by b.created_at desc limit 1`)

async function withSeedMandorsInactive(ui, fn) {
  const seeds = ui.sql("select coalesce(string_agg(id::text, ',' order by id), '') from erp.contractors where contractor_type='MANDOR' and is_active and id::text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'")
  const list = (seeds ? seeds.split(',') : []).map(i => `'${i}'`).join(',')
  if (list) ui.sql(`update erp.contractors set is_active=false where id in (${list})`)
  try { return { ...(await fn()), seed_mandors_inactive_during_capture: list ? list.split(',').length : 0 } }
  finally { if (list) ui.sql(`update erp.contractors set is_active=true where id in (${list})`) }
}

export async function cases(ui, today) {
  const bc = await import(pathToFileURL(resolve('scripts/cp6_bc_browser.mjs')).href)
  const bd = await import(pathToFileURL(resolve('scripts/cp6_bd_browser.mjs')).href)
  const setup = [...await bc.cases(ui, today), ...await bd.cases(ui, today)].map(([id, fn]) => ['SETUP:' + id, fn])
  let fx = null
  const fixture = () => {
    if (!fx) fx = JSON.parse(execFileSync('python', [resolve('scripts/cp6_ui_gallery_fixture.py')], { cwd: resolve('../writer'), env: process.env, encoding: 'utf8' }).trim().split('\n').pop())
    return fx
  }

  const accessories = (key, tab, note, before) => [`GALLERY:${key}`, async () => {
    const s = await session(ui, key.startsWith('P') ? 'owner-phone' : 'owner', 'OWNER', key.startsWith('P') ? { mobile: true } : {})
    const p = s.page
    await openPage(ui, p, 'Gudang', 'Aksesori', 'Pemakaian & Pengembalian Aksesori')
    await p.getByRole('button', { name: tab, exact: true }).click()
    if (before) await before(p)
    return shot(p, note)
  }]
  const pricing = (key, section, note, { role = 'OWNER', vendor = null } = {}) => [`GALLERY:${key}`, async () => {
    const phone = key.startsWith('P'), sessionKey = (role === 'OWNER' ? 'owner' : 'qc') + (phone ? '-phone' : '')
    const s = await session(ui, sessionKey, role, phone ? { mobile: true } : {})
    const p = s.page
    await openPage(ui, p, 'Produksi', 'Laundry', 'Laundry')
    await p.getByRole('button', { name: 'Harga & tagihan', exact: true }).click()
    await ui.expect(p.getByRole('heading', { name: 'Harga laundry dan invoice vendor', exact: true })).toBeVisible()
    await ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
    await p.getByRole('button', { name: section, exact: true }).click()
    if (vendor) {
      await p.getByLabel('Vendor harga laundry').selectOption(fixture()[vendor])
      await ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
    }
    return shot(p, note)
  }]
  const importSection = (key, entity, label, note, item) => [`GALLERY:${key}`, async () => {
    const phone = key.startsWith('P')
    const s = await session(ui, phone ? 'owner-phone' : 'owner', 'OWNER', phone ? { mobile: true } : {})
    const p = s.page
    await openPage(ui, p, 'Pengaturan & Audit', 'Impor data awal', 'Impor data awal')
    await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
    const batch = latestBatch(ui, entity)
    await p.getByLabel('Batch impor').selectOption(batch)
    if (item) {
      await p.getByLabel('Rincian produksi awal').selectOption(ui.sql(`select s.opening_item_id from erp.initial_import_production_sources s where s.batch_id='${batch}' limit 1`))
      const claims = p.getByRole('heading', { name: 'Klaim laundry', exact: true })
      await ui.expect(claims).toBeVisible()
      return shot(p, note, claims.locator('xpath=ancestor::section[1]'))
    }
    const section = p.locator(`section[aria-label="${label}"]`)
    await ui.expect(section).toBeVisible()
    return shot(p, note, section)
  }]

  const gallery = [
    ['GALLERY:FIXTURE', async () => ({ status: 'PASS', ...fixture() })],
    accessories('A01', 'Stok aksesori', 'Gudang · Aksesori, tab Stok aksesori (sesudah Cari stok)', p => p.getByRole('button', { name: 'Cari stok', exact: true }).click()),
    accessories('A02', 'Catat transaksi', 'Gudang · Aksesori, tab Catat transaksi'),
    accessories('A03', 'Barang kembali', 'Gudang · Aksesori, tab Barang kembali'),
    accessories('A04', 'Dokumen', 'Gudang · Aksesori, tab Dokumen (sesudah Cari dokumen)', p => p.getByRole('button', { name: 'Cari dokumen', exact: true }).click()),
    accessories('A05', 'Kebijakan & area', 'Gudang · Aksesori, tab Kebijakan & area'),
    ['GALLERY:N01', () => withSeedMandorsInactive(ui, async () => {
      const p = (await session(ui, 'owner', 'OWNER')).page
      await openPage(ui, p, 'Keuangan', 'Nota Ambil Aksesori', 'Nota Ambil Aksesori')
      await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
      return shot(p, 'Nota Ambil Aksesori, daftar nota')
    })],
    ['GALLERY:N02', () => withSeedMandorsInactive(ui, async () => {
      const p = (await session(ui, 'owner', 'OWNER')).page
      await openPage(ui, p, 'Keuangan', 'Nota Ambil Aksesori', 'Nota Ambil Aksesori')
      await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
      await p.getByRole('button', { name: 'Nota baru', exact: true }).click()
      return shot(p, 'Nota Ambil Aksesori, form nota baru')
    })],
    importSection('I01', 'OPENING_ACCESSORY_CUSTODY', 'Aksesori saldo awal', 'Impor data awal, panel Aksesori saldo awal (ALL-C03)'),
    ['GALLERY:L01', async () => {
      const p = (await session(ui, 'owner', 'OWNER')).page
      await openPage(ui, p, 'Produksi', 'Laundry', 'Laundry')
      return shot(p, 'Laundry, tab Kirim ke Laundry (di salinan uji tampil "Data belum tersedia" karena F3: ID seed CP3)')
    }],
    pricing('L02', 'Kebijakan owner', 'Laundry · Harga & tagihan, Kebijakan owner (LAU-DEC02/06 ditetapkan di salinan uji ini untuk invoice)'),
    pricing('L03', 'Harga vendor', 'Laundry · Harga & tagihan, Harga vendor (vendor komponen: GARMENT 5.000, SPRAY belum diketahui)', { vendor: 'vendor_components' }),
    pricing('L04', 'Kirim dengan harga', 'Laundry · Harga & tagihan, Kirim dengan harga (terkunci karena bacaan Laundry/QC gagal oleh F3)', { vendor: 'vendor_components' }),
    pricing('L05', 'Harga belum diketahui', 'Laundry · Harga & tagihan, Harga belum diketahui'),
    pricing('L06', 'Invoice vendor', 'Laundry · Harga & tagihan, Invoice vendor (satu invoice diposting, satu draf)', { vendor: 'vendor_invoice' }),
    pricing('L07', 'Laundry saldo awal', 'Laundry · Harga & tagihan, Laundry saldo awal (ALL-W05)'),
    importSection('I02', 'OPENING_LAUNDRY_UNINVOICED', 'Laundry saldo awal', 'Impor data awal, panel Laundry saldo awal (ALL-W05)'),
    importSection('I03', 'OPENING_LAUNDRY_CLAIM', null, 'Impor data awal, klaim laundry pada baris WIP saldo awal (ALL-W05)', true),
    ['GALLERY:W01', async () => {
      const p = (await session(ui, 'owner', 'OWNER')).page
      await openPage(ui, p, 'Produksi', 'WIP & Sewing', 'WIP & Sewing')
      const opening = p.locator('section[aria-label="WIP saldo awal"]')
      return (await opening.count()) ? shot(p, 'WIP & Sewing, produksi saldo awal (klaim laundry sebagai qty)', opening) : shot(p, 'WIP & Sewing')
    }],
    pricing('Q01', 'Kebijakan owner', 'Laundry · Harga & tagihan dilihat PRODUKSI_QC (tanpa nominal)', { role: 'PRODUKSI_QC' }),
    pricing('Q02', 'Invoice vendor', 'Laundry · Harga & tagihan, Invoice vendor dilihat PRODUKSI_QC (tersembunyi)', { role: 'PRODUKSI_QC', vendor: 'vendor_invoice' }),
    accessories('P01', 'Stok aksesori', 'HP · Gudang · Aksesori, Stok aksesori', p => p.getByRole('button', { name: 'Cari stok', exact: true }).click()),
    accessories('P02', 'Catat transaksi', 'HP · Gudang · Aksesori, Catat transaksi'),
    ['GALLERY:P03', () => withSeedMandorsInactive(ui, async () => {
      const p = (await session(ui, 'owner-phone', 'OWNER', { mobile: true })).page
      await openPage(ui, p, 'Keuangan', 'Nota Ambil Aksesori', 'Nota Ambil Aksesori')
      await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
      await p.getByRole('button', { name: 'Nota baru', exact: true }).click()
      return shot(p, 'HP · Nota Ambil Aksesori, form nota baru')
    })],
    pricing('P04', 'Kebijakan owner', 'HP · Laundry · Harga & tagihan, Kebijakan owner'),
    pricing('P05', 'Invoice vendor', 'HP · Laundry · Harga & tagihan, Invoice vendor', { vendor: 'vendor_invoice' }),
    pricing('P06', 'Laundry saldo awal', 'HP · Laundry · Harga & tagihan, Laundry saldo awal'),
    importSection('P07', 'OPENING_LAUNDRY_UNINVOICED', 'Laundry saldo awal', 'HP · Impor data awal, panel Laundry saldo awal'),
    ['GALLERY:CLOSE', async () => { for (const s of Object.values(sessions)) await s.context.close(); return { status: 'PASS', sessions: Object.keys(sessions) } }],
  ]
  return [...setup, ...gallery]
}
