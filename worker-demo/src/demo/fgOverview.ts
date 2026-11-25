import {type Product} from '../productCatalog'
import {rangeLabel,type Session} from './planner/model'
import {stockAt} from './planner/conversion'
import {allSkus,nativePosition,mainFg} from './skuCatalog'

export const positionKey=(p:Product)=>[p.brand,p.code,p.location,p.grade].join('::')
export function fgProducts(s:Session):Product[]{
  return allSkus(s).flatMap(a=>{
    const positions=new Map<string,{location:string;grade:string}>()
    const add=(location:string,grade:string)=>positions.set(location+'|'+grade,{location,grade})
    const home=nativePosition(a);add(home.location,home.grade)
    for(const e of s.stockEvents??[])for(const c of e.changes)if(c.key===a.key)add(c.location??mainFg,c.grade??'Good')
    for(const row of s.saleReturns??[])if(row.lines.some(line=>line.sku===a.key))add(row.destination,row.grade)
    return [...positions.values()].map(pos=>({code:a.sku,range:rangeLabel(a.sizes),name:a.model,brand:a.brand,color:a.colour,
      sizes:a.sizes,stocks:a.sizes.map(size=>stockAt(a,size,s,pos.location,pos.grade)),...pos}))
  })
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
