import {productCatalog} from '../productCatalog'
import {saleMoves} from './saleBook'
import {initialMovements} from './stockModel'
import {atPosition,nativePosition} from './skuCatalog'
import type {Article,Session} from './planner/model'

export type FgMovement={
  id:string; ref:string; day:string; physicalTime:string; type:string; note:string
  delta:number[]; balance:number[]; sequence?:string; fromOpeningBook?:true
}
const months='jan feb mar apr mei jun jul agu sep okt nov des'.split(' ')
function seedDay(value:string){
  const [day,month,year]=value.split(' ')
  return year+'-'+String(months.indexOf(month.toLowerCase())+1).padStart(2,'0')+'-'+day.padStart(2,'0')
}
function documentTime(value:string){
  return (value.match(/(?:^|[^0-9])([0-2]\d[:.][0-5]\d)(?:$|\s)/)?.[1]??'').replace('.',':')
}
export function comparePhysical(a:{day:string;physicalTime:string},b:{day:string;physicalTime:string}){
  return a.day.localeCompare(b.day)||(a.physicalTime||'23:59').localeCompare(b.physicalTime||'23:59')
}
export function fgActivity(article:Article,s:Session,location:string,grade:string):FgMovement[]{
  const native=nativePosition(article),rows:FgMovement[]=[]
  if(native.location===location&&native.grade===grade){
    const original=productCatalog.find(p=>p.brand===article.brand&&p.code===article.sku)
    const sizeDelta=(values:number[])=>article.sizes.map(size=>values[original?.sizes.indexOf(size)??-1]??0)
    for(const m of initialMovements.filter(m=>m.brand===article.brand&&m.sku===article.sku)){
      rows.push({fromOpeningBook:true,id:m.id,ref:m.ref,day:seedDay(m.date),physicalTime:documentTime(m.date),type:m.type,note:m.note,delta:sizeDelta(m.delta),balance:[]})
    }
    for(const m of saleMoves(article.brand+'::'+article.sku)){
      rows.push({id:m.id,ref:m.ref,day:m.day,physicalTime:documentTime(m.when),type:m.type,note:m.note,delta:sizeDelta(m.delta),balance:[],sequence:m.recordedAt})
    }
  }
  for(const e of s.stockEvents??[]){
    const changes=e.changes.filter(c=>c.key===article.key&&atPosition(c,location,grade))
    if(!changes.length)continue
    rows.push({id:e.id,ref:e.id,day:e.date??'',physicalTime:e.physicalTime??'',type:e.reverses?'Pembalikan':e.action==='adjust'?'Stock Adjustment':'Ganti Merek',
      note:e.reason,delta:article.sizes.map(size=>changes.filter(c=>c.size===size).reduce((n,c)=>n+c.delta,0)),balance:[],sequence:e.recordedAt})
  }
  return rows
}
