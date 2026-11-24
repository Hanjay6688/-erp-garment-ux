import { productCatalog } from '../productCatalog'
import type { Product } from '../productCatalog'
import type { QtyTuple } from './productionModel'

export type Movement = {
  id: string
  sku: string
  brand: string
  customer: string | null
  date: string
  ref: string
  type: string
  note: string
  delta: QtyTuple
  balance: QtyTuple
}

export const productKey = (product: Pick<Product, 'brand' | 'code'>) => `${product.brand}::${product.code}`

export const movementProductKey = (movement: Pick<Movement, 'brand' | 'sku'>) => `${movement.brand}::${movement.sku}`

export const productBrands = Array.from(new Set(productCatalog.map((product) => product.brand)))

export const productSizes = Array.from(new Set(productCatalog.flatMap((product) => product.sizes)))

export const stockLocations = Array.from(new Set(productCatalog.map((product) => product.location)))

export const stockGrades = Array.from(new Set(productCatalog.map((product) => product.grade)))

export const initialMovements: Movement[] = [
  { id: 'MV-1052', sku: '73001', brand: 'Vivo', customer: 'Nusantara Fashion', date: '27 Agu 2026 · 13:44', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-8,-8,-8], balance: [96,84,108] },
  { id: 'MV-1051', sku: '73001', brand: 'Widie', customer: 'Maju Jaya', date: '27 Agu 2026 · 12:30', ref: 'INV-260827-018', type: 'Penjualan', note: 'Maju Jaya', delta: [-6,-6,-6], balance: [84,78,90] },
  { id: 'MV-1050', sku: '73002', brand: 'Vivo', customer: null, date: '27 Agu 2026 · 10:22', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031', delta: [24,24,24], balance: [72,60,48] },
  { id: 'MV-1049', sku: '73002', brand: 'Widie', customer: null, date: '27 Agu 2026 · 09:55', ref: 'FG-260827-005', type: 'QC → FG', note: 'PO-260812-028', delta: [12,12,12], balance: [42,36,48] },
  { id: 'MV-1048', sku: '73001', brand: 'Vivo', customer: 'Sumber Denim', date: '26 Agu 2026 · 17:06', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', delta: [-12,-8,-4], balance: [104,92,116] },
  { id: 'MV-1047', sku: '73001', brand: 'Widie', customer: null, date: '26 Agu 2026 · 15:40', ref: 'ADJ-260826-006', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', delta: [0,-1,0], balance: [90,84,96] },
  { id: 'MV-1046', sku: '73002', brand: 'Vivo', customer: 'Nusantara Fashion', date: '26 Agu 2026 · 14:25', ref: 'INV-260826-023', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-6,-6,-6], balance: [48,36,24] },
  { id: 'MV-1045', sku: '73002', brand: 'Widie', customer: 'Sumber Denim', date: '26 Agu 2026 · 11:18', ref: 'INV-260826-020', type: 'Penjualan', note: 'Sumber Denim', delta: [-4,-4,-4], balance: [30,24,36] },
]

export const chronologicalMovements = [...initialMovements].reverse()
