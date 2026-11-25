export const cuttingForms = {
  'cutting-roll': { name: 'Buat Potongan', path: '/produksi/buat-potongan/' },
  'mandor-wip': { name: 'Bagi Potongan', path: '/produksi/bagi-potongan/' },
} as const

export const productionForms = {
  ...cuttingForms,
  'fg-summary':{name:'Ringkasan Barang Jadi',path:'/gudang/barang-jadi/'},
  'stock-card':{name:'Kartu stok FG',path:'/gudang/kartu-stok-fg/'},

  procurement:{name:'Pembelian & Penerimaan',path:'/gudang/pembelian-penerimaan/'},
  'materials-rolls':{name:'Bahan & Roll',path:'/gudang/bahan-roll/'},
  accessories:{name:'Aksesori',path:'/gudang/aksesori/'},
  'pocket-fabric':{name:'Kain kantong',path:'/gudang/kain-kantong/'},
  'finance-payroll':{name:'Payroll & Kasbon',path:'/keuangan/payroll-kasbon/'},
  'fg-handoff':{name:'Susun Nota FG',path:'/produksi/susun-nota-fg/'},
  'sales-allocation':{name:'Semua Invoice',path:'/penjualan/semua-invoice/'},
  'sales-invoice':{name:'Penjualan & Invoice',path:'/penjualan/invoice/'},
  'sales-history':{name:'Riwayat Pelanggan',path:'/penjualan/riwayat/'},

  'master-partners':{name:'Supplier & Vendor',path:'/master/supplier-vendor/'},
  'master-fabric':{name:'Kain & Benchmark',path:'/master/kain-benchmark/'},
  'master-accessory':{name:'Master Aksesori',path:'/master/aksesori/'},
  'contractor-issue':{name:'Nota Ambil Mandor',path:'/keuangan/nota-ambil-mandor/'},
  'brand-conversion':{name:'Ganti Merek',path:'/gudang/ganti-merek/'},
  'stock-adjustment':{name:'Stock Adjustment',path:'/gudang/stock-adjustment/'},
  'master-products':{name:'Master SKU',path:'/master/produk-sku/'},
  'sewing-wip': {name:'Jahit',path:'/produksi/jahit/'},
  laundry: {name:'Laundry',path:'/produksi/laundry/'},
  qc: {name:'QC',path:'/produksi/qc/'},
  'admin-reminders':{name:'Reminder',path:'/pengaturan/pengingat/'},
} as const
export function cuttingFormAt(pathname: string) {
  const path = pathname.replace(/\/+$/, '') + '/'
  return (Object.keys(productionForms) as Array<keyof typeof productionForms>)
    .find(page => productionForms[page].path === path)
}
