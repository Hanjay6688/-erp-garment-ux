// Fable cp17c screen census (D14-13 focus 2): open every one of the 48 menus as OWNER and record what the screen
// offers, so the connected screen can be compared with the UX demo screen captured by the same function locally
// (DEMO_SIMULATION build, no backend). Recorded per menu: first heading, action buttons, tabs, table headers,
// whether the page says it is sample data (SIMULASI / DATA CONTOH / contoh), number of rupiah figures, and
// horizontal overflow. The comparison verdict (SAMA / BEDA / TIDAK ADA LAYAR TERSAMBUNG) is made by the auditor from
// these records and the routing code; this module only states a menu as INCOMPLETE when it could not be opened.
export const MENUS = [
  ['', 'Dashboard'],
  ['Produksi', 'Buat Potongan'], ['Produksi', 'Bagi Potongan'], ['Produksi', 'WIP & Sewing'], ['Produksi', 'Laundry'],
  ['Produksi', 'QC & Final SKU'], ['Produksi', 'Susun Nota FG'], ['Produksi', 'Barang BS & Rework'],
  ['Gudang', 'Ringkasan Gudang'], ['Gudang', 'Pembelian & Penerimaan'], ['Gudang', 'Bahan & Roll'], ['Gudang', 'Kain kantong'],
  ['Gudang', 'Aksesori'], ['Gudang', 'Ringkasan Barang Jadi'], ['Gudang', 'Mutasi Barang Jadi · Vivo'],
  ['Gudang', 'Mutasi Barang Jadi · Widie'], ['Gudang', 'Kartu Stok FG'], ['Gudang', 'Stock Adjustment'], ['Gudang', 'Ganti Merek'],
  ['Penjualan', 'Penjualan & Invoice'], ['Penjualan', 'Semua Invoice'], ['Penjualan', 'Retur Penjualan'],
  ['Penjualan', 'Pembayaran Pelanggan'], ['Penjualan', 'Riwayat Pelanggan'],
  ['Keuangan', 'Ringkasan Keuangan'], ['Keuangan', 'Kas & Bank'], ['Keuangan', 'Hutang Supplier & Vendor'],
  ['Keuangan', 'Piutang Pelanggan'], ['Keuangan', 'Payroll & Kasbon'], ['Keuangan', 'Absensi & Rate Harian'],
  ['Keuangan', 'Nota Ambil Aksesori'], ['Keuangan', 'HPP & Rekalkulasi'], ['Keuangan', 'Jurnal & Transaksi Lain'],
  ['Keuangan', 'Laporan & Tutup Buku'],
  ['Master Data', 'Kain & Benchmark'], ['Master Data', 'Aksesori & Harga Mandor'], ['Master Data', 'Produk & SKU'],
  ['Master Data', 'Pelanggan'], ['Master Data', 'Supplier & Vendor'], ['Master Data', 'Mandor'], ['Master Data', 'Gudang & Lokasi'],
  ['Master Data', 'Pola'],
  ['Pengaturan & Audit', 'Reminder'], ['Pengaturan & Audit', 'Pengguna & Hak Akses'], ['Pengaturan & Audit', 'Pengaturan ERP'],
  ['Pengaturan & Audit', 'Impor data awal'], ['Pengaturan & Audit', 'Tutup Periode'], ['Pengaturan & Audit', 'Audit Trail'],
]

async function open(page, group, item) {
  const burger = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await burger.isVisible().catch(() => false)) await burger.click()
  if (!group) { await page.locator('.sidebar .nav-main').filter({ hasText: item }).first().click(); return }
  const link = page.getByRole('button', { name: `• ${item}`, exact: true })
  if (!await link.isVisible().catch(() => false)) await page.locator('.sidebar .nav-main').filter({ hasText: group }).first().click()
  await link.click({ timeout: 15000 })
}

const uniq = (xs) => Array.from(new Set(xs.map((x) => x.replace(/\s+/g, ' ').trim()).filter((x) => x && x.length <= 80)))

export async function capture(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(1200)
  return page.evaluate(() => {
    const root = document.querySelector('.page-wrap') || document.body
    const vis = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' }
    const txt = (sel) => Array.from(root.querySelectorAll(sel)).filter(vis).map((e) => (e.innerText || e.getAttribute('aria-label') || '').trim())
    const text = root.innerText || ''
    return {
      heading: (txt('h1')[0] || txt('h2')[0] || '').slice(0, 120),
      headings: txt('h1, h2, h3').slice(0, 30),
      buttons: txt('button').slice(0, 120),
      tabs: txt('[role=tab], .tabs button, .segmented button').slice(0, 40),
      table_headers: txt('th').slice(0, 80),
      inputs: Array.from(root.querySelectorAll('input, select, textarea')).filter(vis).length,
      sample_label: /SIMULASI|DATA CONTOH|data contoh|UX SIMULASI/i.test(text),
      notice_only: text.length < 600,
      rupiah_figures: (text.match(/Rp\s?[\d.,]+/g) || []).length,
      text_chars: text.length,
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      topbar: (document.querySelector('.topbar')?.innerText || '').slice(0, 160),
    }
  })
}

export async function census(page, menus = MENUS) {
  const out = {}
  for (const [group, item] of menus) {
    try { await open(page, group, item); const c = await capture(page); out[item] = { opened: true, ...c } }
    catch (e) { out[item] = { opened: false, error: String(e).slice(0, 300) } }
  }
  return out
}

export function cases(ui, today) {
  const sections = ['', 'Produksi', 'Gudang', 'Penjualan', 'Keuangan', 'Master Data', 'Pengaturan & Audit']
  return sections.map((s) => [`FABLE_SCREENS:${s || 'Dashboard'}`, async () => {
    const user = await ui.login('OWNER', { label: 'fable-screens-' + (s || 'dash').replace(/\W+/g, '').toLowerCase() })
    try {
      await user.page.locator('.sidebar .nav-main').first().waitFor({ state: 'attached', timeout: 60000 })
      const menus = await census(user.page, MENUS.filter(([g]) => g === s))
      const notOpened = Object.entries(menus).filter(([, v]) => !v.opened).map(([k]) => k)
      return { status: notOpened.length ? 'INCOMPLETE' : 'PASS', not_opened: notOpened, menus }
    } finally { await user.context.close() }
  }])
}
