import {useSyncExternalStore} from 'react'
import {readPlannerSession} from './planner/session'
import type {Session} from './planner/model'
export type PriceHistory={id:string;amount:number;uom?:string;effectiveFrom:string;effectiveTo?:string;note:string;reason?:string;status:'CURRENT'|'SUPERSEDED'|'CANCELLED'}
export type AccessoryMaster={id:string;code:string;name:string;category:string;stockUom:string;purchaseUom:string;conversion:number;movingAverage:number;stock:number;active:boolean;rowVersion:number}
export type AccessoryRate={category:string;sellingPrices:PriceHistory[];reimbursementPrices:PriceHistory[]}
export const contractorNames=['Afui','Epi','Selo','Afat']
export const fixtureDate='2026-11-24'
export type SpecialRate={mandor:string;category:string;start:string;amount:number|null;unit:string;id:string;reason?:string}
export type AccessoryBook={items:AccessoryMaster[];rates:AccessoryRate[];special:SpecialRate[];free:{mandor:string;categories:string[];start:string;end:string|null;version:string}[]}
export const accessorySeeds:AccessoryMaster[]=[
  {id:'acc-btn-silver',code:'ACC-BTN-017-SLV',name:'Kancing Jeans 17 mm · Silver',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:620,stock:4800,active:true,rowVersion:7},
  {id:'acc-btn-metal',code:'ACC-BTN-017-MTL',name:'Kancing Jeans 17 mm · Metal',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:690,stock:3200,active:true,rowVersion:5},
  {id:'acc-zip-14',code:'ACC-ZIP-014-BLK',name:'Sleting 14 cm · Black',category:'Sleting',stockUom:'pcs',purchaseUom:'lusin',conversion:12,movingAverage:5200,stock:2200,active:true,rowVersion:9},
  {id:'acc-label-vivo',code:'ACC-LBL-VIVO',name:'Label Woven Vivo',category:'Label',stockUom:'pcs',purchaseUom:'roll',conversion:1000,movingAverage:530,stock:8000,active:true,rowVersion:3},
  {id:'acc-label-widie',code:'ACC-LBL-WIDIE',name:'Label Woven Widie',category:'Label',stockUom:'pcs',purchaseUom:'roll',conversion:1000,movingAverage:560,stock:6000,active:true,rowVersion:1},
]
export const accessoryRateSeeds:AccessoryRate[]=[
  {category:'Kancing',sellingPrices:[{id:'owner-kancing-charge',amount:495,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-kancing-reimburse',amount:500,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Centang',sellingPrices:[{id:'owner-centang-charge',amount:200,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-centang-reimburse',amount:200,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Kulit',sellingPrices:[{id:'owner-kulit-charge',amount:1_000,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-kulit-reimburse',amount:1_000,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Sleting',sellingPrices:[{id:'owner-sleting-charge',amount:29_900,uom:'lusin',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-sleting-reimburse',amount:2_500,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Plat',sellingPrices:[{id:'owner-plat-charge',amount:500,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-plat-reimburse',amount:500,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Hang Tag',sellingPrices:[{id:'owner-hang-tag-charge',amount:7_150,uom:'lusin',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-hang-tag-reimburse',amount:600,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Lock Pin',sellingPrices:[{id:'owner-lock-pin-charge',amount:300,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi kategori besar dari Owner',status:'CURRENT'}],reimbursementPrices:[{id:'owner-lock-pin-reimburse',amount:300,uom:'pcs',effectiveFrom:'2026-09-04',note:'Referensi reimbursement Owner',status:'CURRENT'}]},
  {category:'Kain Kantong',sellingPrices:[],reimbursementPrices:[]},
  {category:'Label',sellingPrices:[],reimbursementPrices:[]},
  {category:'Kain Keras',sellingPrices:[],reimbursementPrices:[]},
]
const opening:AccessoryBook={items:accessorySeeds,rates:accessoryRateSeeds,special:[{id:'sample-afui-button',mandor:'Afui',category:'Kancing',start:'2026-11-22',amount:450,unit:'pcs'}],free:[{mandor:'Afui',categories:['Kancing'],start:'2026-11-24',end:null,version:'aturan-latihan-1'}]}
const bookKey='atelier.demo.accessory-book.v1'
let cache:{raw:string|null;book:AccessoryBook}|undefined
export function masterBook():AccessoryBook {
  const raw=sessionStorage.getItem(bookKey)
  if(cache&&cache.raw===raw)return cache.book
  const saved:AccessoryBook=raw?JSON.parse(raw):opening
  const widie=accessorySeeds.find(item=>item.code==='ACC-LBL-WIDIE')!
  const book=saved.items.some(item=>item.code===widie.code) ? saved : {...saved,items:[...saved.items,widie]}
  cache={raw,book}
  return book
}
export function updateAccessoryBook(change:(b:AccessoryBook)=>AccessoryBook){const next=change(masterBook());sessionStorage.setItem(bookKey,JSON.stringify(next));cache=undefined;window.dispatchEvent(new Event(bookKey))}
export function useAccessoryBook(){return useSyncExternalStore(cb=>{window.addEventListener(bookKey,cb);return()=>window.removeEventListener(bookKey,cb)},masterBook)}
export const normalizeMandor=(m:string)=>m.replace(/^Mandor\s+/i,'').trim()
export const amountText=(n:number)=>'Rp'+new Intl.NumberFormat('id-ID',{maximumFractionDigits:2}).format(n)
export const priceOn=(rows:PriceHistory[],date:string)=>rows.filter(x=>x.status!=='CANCELLED'&&x.effectiveFrom<=date&&(!x.effectiveTo||date<x.effectiveTo)).sort((a,b)=>b.effectiveFrom.localeCompare(a.effectiveFrom))[0]
export function specialOn(book:AccessoryBook,m:string,c:string,date:string){return book.special.filter(s=>s.mandor===normalizeMandor(m)&&s.category===c&&s.start<=date).sort((a,b)=>b.start.localeCompare(a.start))[0]}
export function validRateUnit(unit:string,item:AccessoryMaster){const u=unit.toLowerCase();return u==='pcs'?1:u==='lusin'||u==='dozen'?12:u==='gross'?144:u===item.purchaseUom.toLowerCase()?item.conversion:null}
export function saveSpecial(book:AccessoryBook,record:SpecialRate){if(!contractorNames.includes(record.mandor)||!record.category||!record.start||record.amount!==null&&(!Number.isFinite(record.amount)||record.amount<=0))throw Error('Pilih mandor, kategori dan tanggal. Harga khusus boleh kosong atau lebih dari nol.');return {...book,special:[record,...book.special]}}
export function saveRateVersion(previous:PriceHistory[],entry:PriceHistory):PriceHistory[]{const rows=[entry,...previous.filter(r=>r.effectiveFrom!==entry.effectiveFrom&&r.status!=='CANCELLED')].sort((a,b)=>b.effectiveFrom.localeCompare(a.effectiveFrom));return rows.map((r,i)=>({...r,status:i?'SUPERSEDED':'CURRENT',effectiveTo:i?rows[i-1].effectiveFrom:undefined}))}
export type PricingMode='MASTER'|'MANUAL'|'FREE'
export function issueQuote(book:AccessoryBook,item:AccessoryMaster,mandor:string,date:string,mode:PricingMode='MASTER',manual?:number|null){
  const family=book.rates.find(r=>r.category===item.category),normal=priceOn(family?.sellingPrices??[],date),reimburse=priceOn(family?.reimbursementPrices??[],date),special=specialOn(book,mandor,item.category,date)
  const hasSpecial=special?.amount!=null,amount=hasSpecial?special.amount:normal?.amount,unit=(hasSpecial?special.unit:normal?.uom)??'pcs',factor=validRateUnit(unit,item)
  const permit=book.free.find(r=>r.mandor===normalizeMandor(mandor)&&r.start<=date&&(!r.end||date<r.end)&&r.categories.includes(item.category))
  const per=mode==='FREE'?(permit?0:null):mode==='MANUAL'?(manual!=null&&manual>0&&Number.isFinite(manual)?manual:null):amount!=null&&amount>0&&factor?amount/factor:null
  const reimbFactor=reimburse&&validRateUnit(reimburse.uom??'pcs',item);const reimbursement=reimburse&&reimbFactor?reimburse.amount/reimbFactor:null
  return {per,reimbursement,hpp:item.movingAverage,normal,hasSpecial,permit,source:mode==='FREE'?permit?'Gratis Special':'Izin gratis belum berlaku':mode==='MANUAL'?'Harga eceran':hasSpecial?'Harga khusus '+normalizeMandor(mandor):normal?'Harga normal kategori':'Harga master belum diatur',version:mode==='FREE'?permit?.version:mode==='MASTER'?(hasSpecial?special.id:normal?.id):'eceran',unit,factor}
}

export const noteStorage='atelier.demo.accessory-notes.v2'
const oldCodes:Record<string,string>={'ACC-BTN-017':'ACC-BTN-017-SLV','ACC-ZIP-014':'ACC-ZIP-014-BLK','ACC-LBL-004':'ACC-LBL-VIVO'}
export const masterCode=(code:string)=>oldCodes[code]??code
export function noteStock(code:string,opening:number,docs?:{inventoryChange?:number;lines:{id:string;qty:number}[]}[],session:Session=readPlannerSession()):number {
  const ledger=docs??(JSON.parse(sessionStorage.getItem(noteStorage)??'[]') as {inventoryChange?:number;lines:{id:string;qty:number}[]}[])
  const events=session.stockEvents??[]
  const reversed=new Set(events.flatMap(event=>event.reverses?[event.reverses]:[]))
  const used=events.reduce((sum,event)=>sum+(reversed.has(event.id) ? 0 : event.kit?.used.find(line=>line.code===code)?.qty??0),0)
  const returned=(session.conversionReturns??[]).reduce((sum,row)=>sum+(!row.reversed&&row.code===code?row.good:0),0)
  const received=(session.accessoryReceipts??[]).reduce((sum,row)=>sum+(row.code===code?row.qty:0),0)
  return opening+received+returned-used+ledger.reduce((balance,d)=>balance+(d.inventoryChange??0)*d.lines.reduce((sum,l)=>sum+(masterCode(l.id)===code?l.qty:0),0),0)
}

export function usedByNote(version:string,from:string):boolean {
  const documents=JSON.parse(sessionStorage.getItem(noteStorage)??'[]') as {issuedOn:string;status:string;lines:{version?:string}[]}[]
  return documents.some(d=>d.status!=='DRAFT'&&d.issuedOn>=from&&d.lines.some(line=>line.version===version))
}
