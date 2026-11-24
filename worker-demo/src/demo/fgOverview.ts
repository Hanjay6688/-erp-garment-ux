import { productCatalog, type Product } from '../productCatalog'
import { articles, rangeLabel, type Session } from './planner/model'
import { stockAt } from './planner/inventory'
import { readInvoices, saleStock } from './saleBook'

export function fgProducts(session: Session): Product[] {
  const sales = readInvoices()
  return [
    ...articles.map(a => ({
      code: a.sku, range: rangeLabel(a.sizes), name: a.model, brand: a.brand, color: a.colour,
      sizes: a.sizes, stocks: a.sizes.map(s => stockAt(a,s,session)), location: 'Gudang FG Utama', grade: 'Good',
    })),
    ...productCatalog.map(p => ({...p,stocks:saleStock(p,sales)})),
  ]
}

export function piecesIn(product: Product, sizes: string[] = []) {
  return product.stocks.reduce((sum, qty, i) => sum + (!sizes.length || sizes.includes(product.sizes[i]) ? qty : 0), 0)
}
export function fgTotals(products: Product[], sizes: string[] = []) {
  return products.reduce((t,p) => {
    const qty = piecesIn(p,sizes)
    t.all += qty
    if (p.grade.toUpperCase() === 'GOOD') t.good += qty
    if (p.grade.toUpperCase() === 'BS') t.bs += qty
    return t
  }, {all:0,good:0,bs:0})
}
