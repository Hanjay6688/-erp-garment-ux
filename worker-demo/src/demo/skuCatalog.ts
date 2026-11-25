import { readPlannerSession } from './planner/session'
import { productCatalog } from '../productCatalog'
import { articles, type Article, type Session, type StockChange } from './planner/model'

export const mainFg = 'Gudang FG Utama'
export const skuCatalog: Article[] = [...articles, ...productCatalog.map(p => ({
  key: p.brand+' '+p.code, sku:p.code, brand:p.brand, colour:p.color, model:p.name, sizes:p.sizes,
  opening:Object.fromEntries(p.sizes.map((size,i)=>[size,p.stocks[i]])),
}))]
export function allSkus(s:Session,activeOnly=false):Article[]{
  const items=new Map(skuCatalog.map(a=>[a.key,a]))
  for(const [key,v] of Object.entries(s.skuUpdates??{}))items.set(key,v.article)
  return [...items.values()].filter(a=>!activeOnly||s.skuUpdates?.[a.key]?.active!==false)
}
export const skuByKey=(key:string,s:Session=readPlannerSession())=>s.skuUpdates?.[key]?.article??skuCatalog.find(a=>a.key===key)
export function editSku(s:Session,oldKey:string|null,a:Article,active:boolean){
  if(oldKey!==a.key&&skuByKey(a.key,s))throw Error('Nomor SKU sudah dipakai oleh merek ini.')
  const prior=oldKey?skuByKey(oldKey,s):null
  const updates={...s.skuUpdates}
  if(prior&&prior.key!==a.key)updates[prior.key]={article:prior,active:false}
  updates[a.key]={article:{...a,opening:Object.fromEntries(a.sizes.map(x=>[x,prior?.key===a.key?prior.opening[x]??0:0]))},active}
  const next={...s,skuUpdates:updates}
  return prior&&(prior.key!==a.key||!active)?pairSku(next,prior.key,null):next
}
export const nativePosition = (a:Article) => {
  const p=productCatalog.find(p=>p.brand===a.brand&&p.code===a.sku)
  return {location:p?.location??mainFg, grade:p?.grade??'Good'}
}
export const atPosition=(c:StockChange,location:string,grade:string) =>
  (c.location??mainFg)===location&&(c.grade??'Good')===grade
export function positionDelta(s:Session,key:string,size:string,location:string,grade:string){
  const returned=(s.saleReturns??[]).filter(row=>!row.replacedBy&&row.destination===location&&row.grade===grade)
    .flatMap(row=>row.lines).reduce((n,line)=>n+(line.sku===key&&line.size===size?line.qty:0),0)
  return returned+(s.stockEvents??[]).reduce((n,e)=>n+e.changes.filter(c=>c.key===key&&c.size===size&&atPosition(c,location,grade)).reduce((v,c)=>v+c.delta,0),0)
}
export function pairOf(s:Session,key:string) {
  return s.skuPairs && Object.hasOwn(s.skuPairs,key) ? s.skuPairs[key] : skuByKey(key,s)?.pair??null
}
export function pairSku(s:Session,key:string,other:string|null):Session {
  const a=skuByKey(key,s),b=other?skuByKey(other,s):null
  if(!a||(other&&(!b||b.brand===a.brand||s.skuUpdates?.[b.key]?.active===false)))throw Error('Pilih padanan aktif dari merek lain.')
  const pairs={...s.skuPairs}
  for(const k of [key,...(other?[other]:[])]){
    const previous=pairOf(s,k)
    if(previous)pairs[previous]=null
    pairs[k]=null
  }
  if(other){pairs[key]=other;pairs[other]=key}
  return {...s,skuPairs:pairs}
}
