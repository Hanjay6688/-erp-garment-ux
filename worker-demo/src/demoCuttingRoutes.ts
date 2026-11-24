export const cuttingForms = {
  'cutting-roll': { name: 'Buat Potongan', path: '/produksi/buat-potongan/' },
  'mandor-wip': { name: 'Bagi Potongan', path: '/produksi/bagi-potongan/' },
} as const

export const productionForms = {
  ...cuttingForms,
  'brand-conversion':{name:'Ganti Merek',path:'/gudang/ganti-merek/'},
  'stock-adjustment':{name:'Stock Adjustment',path:'/gudang/stock-adjustment/'},
  'master-products':{name:'Master SKU',path:'/master/produk-sku/'},
  'sewing-wip': {name:'Jahit',path:'/produksi/jahit/'},
  laundry: {name:'Laundry',path:'/produksi/laundry/'},
  qc: {name:'QC',path:'/produksi/qc/'},
} as const
export function cuttingFormAt(pathname: string) {
  const path = pathname.replace(/\/+$/, '') + '/'
  return (Object.keys(productionForms) as Array<keyof typeof productionForms>)
    .find(page => productionForms[page].path === path)
}
