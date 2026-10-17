import type { RuntimeConfig } from './config/runtime'

// Owner D15-2 (Fable FABLE-015, Astra ASTRA-C17-03, Sol KNOWN-UI-MODE): one table says how every menu renders in each
// mode. In the Enteng build (real data) a menu that has no connected screen yet is HIDDEN: it is not in the sidebar and
// its direct route shows a boundary screen without any figure. It appears as soon as its screen is connected (the row
// here becomes CONNECTED), so nothing has to be switched on twice. The demo build keeps its sample screens, and the
// disposable test build keeps today's routing (connected where wired, sample otherwise).
// Owner D16-1 ("selesain biar gausa sembunyiin", Fable oracle 1): a hidden menu is finished, not kept hidden; the Enteng
// build renders the same connected component as the disposable test build. Owner D16-5: "Tutup Periode" is no longer a
// menu of its own; it is the "Tutup Buku" tab of "Laporan & Tutup Buku" (src/App.tsx redirects the old route).
export type ScreenActivation = 'CONNECTED' | 'SAMPLE' | 'BOUNDARY' | 'NOTICE' | 'HIDDEN'
type Mode = RuntimeConfig['mode']
type Row = { label: string; section: string; enteng: ScreenActivation; test: ScreenActivation }

export const SCREEN_ACTIVATION: Readonly<Record<string, Row>> = Object.freeze({
  dashboard: { label: 'Dashboard', section: 'Dashboard', enteng: 'NOTICE', test: 'NOTICE' },
  'cutting-roll': { label: 'Buat Potongan', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  'mandor-wip': { label: 'Bagi Potongan', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sewing-wip': { label: 'WIP & Sewing', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  laundry: { label: 'Laundry', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  qc: { label: 'QC & Final SKU', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  'fg-handoff': { label: 'Susun Nota FG', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  'bs-rework': { label: 'Barang BS & Rework', section: 'Produksi', enteng: 'CONNECTED', test: 'CONNECTED' },
  'warehouse-dashboard': { label: 'Ringkasan Gudang', section: 'Gudang', enteng: 'HIDDEN', test: 'SAMPLE' },
  procurement: { label: 'Pembelian & Penerimaan', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'materials-rolls': { label: 'Bahan & Roll', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'pocket-fabric': { label: 'Kain kantong', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  accessories: { label: 'Aksesori', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'fg-summary': { label: 'Ringkasan Barang Jadi', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'movements-vivo': { label: 'Mutasi Barang Jadi · Vivo', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'movements-widie': { label: 'Mutasi Barang Jadi · Widie', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'stock-card': { label: 'Kartu Stok FG', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'stock-adjustment': { label: 'Stock Adjustment', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'brand-conversion': { label: 'Ganti Merek', section: 'Gudang', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sales-invoice': { label: 'Penjualan & Invoice', section: 'Penjualan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sales-allocation': { label: 'Semua Invoice', section: 'Penjualan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sales-returns': { label: 'Retur Penjualan', section: 'Penjualan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sales-payments': { label: 'Pembayaran Pelanggan', section: 'Penjualan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'sales-history': { label: 'Riwayat Pelanggan', section: 'Penjualan', enteng: 'HIDDEN', test: 'SAMPLE' },
  'finance-overview': { label: 'Ringkasan Keuangan', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-cash': { label: 'Kas & Bank', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-ap': { label: 'Hutang Supplier & Vendor', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-ar': { label: 'Piutang Pelanggan', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-payroll': { label: 'Payroll & Kasbon', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'operations-attendance': { label: 'Absensi & Rate Harian', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'contractor-issue': { label: 'Nota Ambil Aksesori', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  hpp: { label: 'HPP & Rekalkulasi', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-journal': { label: 'Jurnal & Transaksi Lain', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'finance-reports': { label: 'Laporan & Tutup Buku', section: 'Keuangan', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-fabric': { label: 'Kain & Benchmark', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-accessory': { label: 'Aksesori & Harga Mandor', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-products': { label: 'Produk & SKU', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-customers': { label: 'Pelanggan', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-partners': { label: 'Supplier & Vendor', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-workforce': { label: 'Mandor', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-locations': { label: 'Gudang & Lokasi', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'master-pattern': { label: 'Pola', section: 'Master Data', enteng: 'CONNECTED', test: 'CONNECTED' },
  'admin-reminders': { label: 'Reminder', section: 'Pengaturan & Audit', enteng: 'CONNECTED', test: 'CONNECTED' },
  'admin-access': { label: 'Pengguna & Hak Akses', section: 'Pengaturan & Audit', enteng: 'CONNECTED', test: 'CONNECTED' },
  'admin-settings': { label: 'Pengaturan ERP', section: 'Pengaturan & Audit', enteng: 'CONNECTED', test: 'CONNECTED' },
  'admin-import': { label: 'Impor data awal', section: 'Pengaturan & Audit', enteng: 'CONNECTED', test: 'CONNECTED' },
  'admin-audit': { label: 'Audit Trail', section: 'Pengaturan & Audit', enteng: 'CONNECTED', test: 'CONNECTED' },
})

const PAGE_BY_LABEL: Readonly<Record<string, string>> = Object.freeze(Object.fromEntries(Object.entries(SCREEN_ACTIVATION).map(([page, row]) => [row.label, page])))

export function screenActivation(mode: Mode, page: string): ScreenActivation {
  const row = SCREEN_ACTIVATION[page]
  if (mode === 'DEMO_SIMULATION') return 'SAMPLE'
  if (!row) return mode === 'UAT_AUTH_SIMULATION' ? 'HIDDEN' : 'SAMPLE'
  return mode === 'UAT_AUTH_SIMULATION' ? row.enteng : row.test
}
export function isScreenHidden(mode: Mode, page: string) { return screenActivation(mode, page) === 'HIDDEN' }
export function isNavLabelHidden(mode: Mode, label: string) {
  const page = PAGE_BY_LABEL[label]
  return page === undefined ? mode === 'UAT_AUTH_SIMULATION' : isScreenHidden(mode, page)
}
// Menu sections that hold at least one connected screen in this mode, for the dashboard notice.
export function connectedSections(mode: Mode) {
  return [...new Set(Object.keys(SCREEN_ACTIVATION).filter(page => screenActivation(mode, page) === 'CONNECTED').map(page => SCREEN_ACTIVATION[page].section))]
}
