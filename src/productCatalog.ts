export type Product = {
  code: string
  range: string
  name: string
  color: string
  brand: string
  sizes: [string, string, string]
  stocks: [number, number, number]
  location: string
  grade: string
}

export const productCatalog: Product[] = [
  { code: '73001', range: '28–30', name: 'Vivo Classic', color: 'Indigo', brand: 'Vivo', sizes: ['28','29','30'], stocks: [96,84,108], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73002', range: '31–33', name: 'Vivo Regular', color: 'Washed Blue', brand: 'Vivo', sizes: ['31','32','33'], stocks: [72,60,48], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73003', range: '34–36', name: 'Vivo Relaxed', color: 'Charcoal', brand: 'Vivo', sizes: ['34','35','36'], stocks: [36,42,54], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73004', range: '28–30', name: 'Vivo Straight', color: 'Deep Black', brand: 'Vivo', sizes: ['28','29','30'], stocks: [60,72,66], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73001', range: '28–30', name: 'Widie Daily', color: 'Dark Navy', brand: 'Widie', sizes: ['28','29','30'], stocks: [84,78,90], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73002', range: '31–33', name: 'Widie Regular', color: 'Vintage Blue', brand: 'Widie', sizes: ['31','32','33'], stocks: [42,36,48], location: 'Gudang FG Cadangan', grade: 'BS' },
  { code: '73005', range: '31–33', name: 'Widie Tapered', color: 'Mid Blue', brand: 'Widie', sizes: ['31','32','33'], stocks: [48,54,42], location: 'Gudang FG Cadangan', grade: 'Good' },
  { code: '73006', range: '34–36', name: 'Widie Workwear', color: 'Stone', brand: 'Widie', sizes: ['34','35','36'], stocks: [24,30,36], location: 'Gudang FG Cadangan', grade: 'BS' },
]
