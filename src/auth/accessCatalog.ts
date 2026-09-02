export type PermissionKey = string

export type AccessBundle = {
  permissions: readonly PermissionKey[]
}

export const NAV_PERMISSION_BY_LABEL: Readonly<Record<string, PermissionKey>> = Object.freeze({
  Dashboard: 'dashboard.view',
  'Buat Potongan': 'production.cutting.view',
  'Bagi Potongan': 'production.distribution.view',
  'WIP & Sewing': 'production.wip.view',
  Laundry: 'production.laundry.view',
  'QC & Final SKU': 'production.final_sku.view',
  'Susun Nota FG': 'production.fg_handoff.view',
  'Barang BS & Rework': 'production.bs_rework.view',
  'Ringkasan Gudang': 'warehouse.dashboard.view',
  'Pembelian & Penerimaan': 'warehouse.procurement.view',
  'Bahan & Roll': 'warehouse.material.view',
  Aksesori: 'warehouse.accessory.view',
  'Ringkasan Barang Jadi': 'warehouse.fg.view',
  'Mutasi Barang Jadi · Vivo': 'warehouse.movement.view',
  'Mutasi Barang Jadi · Widie': 'warehouse.movement.view',
  'Kartu Stok FG': 'warehouse.stock.view',
  'Stock Adjustment': 'warehouse.stock.adjust',
  'Ganti Merek': 'warehouse.brand_conversion.view',
  'Penjualan & Invoice': 'sales.invoice.view',
  'Semua Invoice': 'sales.invoice.view',
  'Retur Penjualan': 'sales.return.view',
  'Pembayaran Pelanggan': 'sales.payment.view',
  'Riwayat Pelanggan': 'sales.history.view',
  'Ringkasan Keuangan': 'finance.dashboard.view',
  'Kas & Bank': 'finance.cash.view',
  'Hutang Supplier & Vendor': 'finance.ap.view',
  'Piutang Pelanggan': 'finance.ar.view',
  'Payroll & Kasbon': 'finance.payroll.view',
  'Absensi & Rate Harian': 'finance.attendance.view',
  'Nota Ambil Aksesori': 'finance.contractor_accessory.view',
  'HPP & Rekalkulasi': 'finance.hpp.view',
  'Jurnal & Transaksi Lain': 'finance.journal.view',
  'Laporan & Tutup Buku': 'finance.reports.view',
  'Kain & Benchmark': 'master.fabric.view',
  'Aksesori & Harga Mandor': 'master.accessory.view',
  'Produk & SKU': 'master.product.view',
  Pelanggan: 'master.customer.view',
  'Supplier & Vendor': 'master.partner.view',
  Mandor: 'master.workforce.view',
  'Gudang & Lokasi': 'master.location.view',
  Pola: 'master.pattern.view',
  Reminder: 'settings.reminder.view',
  'Pengguna & Hak Akses': 'settings.access.view',
  'Pengaturan ERP': 'settings.erp.view',
  'Tutup Periode': 'finance.period_close.manage',
  'Audit Trail': 'settings.audit.view',
})

export const PAGE_PERMISSION_BY_ID: Readonly<Record<string, PermissionKey>> = Object.freeze({
  dashboard: 'dashboard.view',
  'cutting-roll': 'production.cutting.view',
  'mandor-wip': 'production.distribution.view',
  'sewing-wip': 'production.wip.view',
  laundry: 'production.laundry.view',
  qc: 'production.final_sku.view',
  'fg-handoff': 'production.fg_handoff.view',
  'bs-rework': 'production.bs_rework.view',
  'warehouse-dashboard': 'warehouse.dashboard.view',
  procurement: 'warehouse.procurement.view',
  'materials-rolls': 'warehouse.material.view',
  accessories: 'warehouse.accessory.view',
  'fg-summary': 'warehouse.fg.view',
  'movements-vivo': 'warehouse.movement.view',
  'movements-widie': 'warehouse.movement.view',
  'stock-card': 'warehouse.stock.view',
  'stock-adjustment': 'warehouse.stock.adjust',
  'brand-conversion': 'warehouse.brand_conversion.view',
  'sales-invoice': 'sales.invoice.view',
  'sales-allocation': 'sales.invoice.view',
  'sales-returns': 'sales.return.view',
  'sales-payments': 'sales.payment.view',
  'sales-history': 'sales.history.view',
  'finance-overview': 'finance.dashboard.view',
  'finance-cash': 'finance.cash.view',
  'finance-ap': 'finance.ap.view',
  'finance-ar': 'finance.ar.view',
  'finance-payroll': 'finance.payroll.view',
  'operations-attendance': 'finance.attendance.view',
  'contractor-issue': 'finance.contractor_accessory.view',
  hpp: 'finance.hpp.view',
  'finance-journal': 'finance.journal.view',
  'finance-reports': 'finance.reports.view',
  'master-fabric': 'master.fabric.view',
  'master-accessory': 'master.accessory.view',
  'master-products': 'master.product.view',
  'master-customers': 'master.customer.view',
  'master-partners': 'master.partner.view',
  'master-workforce': 'master.workforce.view',
  'master-locations': 'master.location.view',
  'master-pattern': 'master.pattern.view',
  'admin-reminders': 'settings.reminder.view',
  'admin-access': 'settings.access.view',
  'admin-settings': 'settings.erp.view',
  'admin-period-close': 'finance.period_close.manage',
  'admin-audit': 'settings.audit.view',
})

export const SENSITIVE_ACTION_PERMISSION = Object.freeze({
  saveRole: 'settings.access.manage',
  assignUserRole: 'settings.access.manage',
  savePattern: 'master.pattern.manage',
  quickCreatePattern: 'master.pattern.manage',
  adjustWip: 'production.wip.adjust',
  reverseWip: 'production.wip.reverse',
  postSewing: 'production.wip.post',
  postLaundry: 'production.laundry.post',
  reverseLaundry: 'production.laundry.reverse',
  postFinalSku: 'production.final_sku.post',
  stockAdjustment: 'warehouse.stock.adjust',
  postInvoice: 'sales.invoice.post',
  reverseInvoice: 'sales.invoice.reverse',
  approvePayroll: 'finance.payroll.approve',
  payPayroll: 'finance.payroll.pay',
  editMasterPrice: 'master.price.edit_draft',
  exportAudit: 'settings.audit.export',
})

export function hasPermission(bundle: AccessBundle | null | undefined, permission: PermissionKey) {
  return bundle?.permissions.includes(permission) ?? false
}

export function isPageAllowed(bundle: AccessBundle | null | undefined, pageId: string) {
  const permission = PAGE_PERMISSION_BY_ID[pageId]
  return permission ? hasPermission(bundle, permission) : false
}

export function isNavLabelAllowed(bundle: AccessBundle | null | undefined, label: string) {
  const permission = NAV_PERMISSION_BY_LABEL[label]
  return permission ? hasPermission(bundle, permission) : false
}
