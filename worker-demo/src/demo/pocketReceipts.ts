import {fixtureDate} from './accessoryPricing'
export type PocketUnit='yd'|'m'
export type PocketRoll={id:string;name:string;length:number;rate:number;unit:PocketUnit;date:string;location:string;receipt:string}
type RollInput={number:string;qty:string}
export type ReceiptDraft={request:string;number:string;supplier:string;location:string;material:string;day:string;unit:PocketUnit;rate:string;reason:string;notes:string;rolls:RollInput[]}
export type PocketReceipt={request:string;number:string;supplier:string;day:string;reason:string;notes:string|null;rolls:PocketRoll[];reversal?:{reason:string;at:string}}
const key='erp.demo.pocket.receipts.v1'
export const seedRolls:PocketRoll[]=[
  {id:'KT-001',name:'Kain kantong putih',length:100,rate:9000,unit:'yd',date:'2026-11-20',location:'Gudang Bahan',receipt:'SJ-KT-001'},
  {id:'KT-002',name:'Kain kantong hitam',length:60,rate:10500,unit:'yd',date:'2026-11-20',location:'Gudang Bahan',receipt:'SJ-KT-001'},
]
export const readReceipts=():PocketReceipt[]=>JSON.parse(sessionStorage.getItem(key)??'[]')
export const pocketRolls=()=>[...seedRolls,...readReceipts().filter(r=>!r.reversal).flatMap(r=>r.rolls)]
export const receiptPath='/gudang/pembelian-penerimaan/?jenis=kantong'
export const dayOk=(day:string)=>/^\d{4}-\d{2}-\d{2}$/.test(day)&&Number.isFinite(Date.parse(day))&&new Date(day).toISOString().slice(0,10)===day&&day<=fixtureDate
export function prepareReceipt(d:ReceiptDraft):PocketReceipt{
  const clean=(v:string)=>v.trim()
  if(![d.number,d.supplier,d.location,d.material,d.reason].every(v=>clean(v))||!dayOk(d.day))throw Error('Isi surat jalan, supplier, gudang, bahan, tanggal fisik dan alasan penerimaan.')
  const parse=(v:string)=>/^\d+(?:[.,]\d{1,6})?$/.test(clean(v))?Number(clean(v).replace(',','.')):NaN
  const rate=parse(d.rate)
  if(!['yd','m'].includes(d.unit)||!Number.isFinite(rate)||rate<0||!Number.isSafeInteger(Math.round(rate*100)))throw Error('Periksa satuan dan harga per satuan.')
  const seen=new Set<string>()
  const rolls=d.rolls.filter(r=>clean(r.number)||clean(r.qty)).map(r=>{
    const id=clean(r.number),qty=parse(r.qty)
    if(!id||!(qty>0)||!Number.isSafeInteger(Math.round(qty*1e6))||!Number.isSafeInteger(Math.round(qty*rate*100)))throw Error('Setiap roll terisi perlu nomor dan panjang positif.')
    if(seen.has(id.toLowerCase()))throw Error('Nomor roll ganda di surat jalan.')
    seen.add(id.toLowerCase())
    return {id,name:clean(d.material),length:qty,rate,unit:d.unit,date:d.day,location:clean(d.location),receipt:clean(d.number)}
  })
  if(!rolls.length)throw Error('Isi minimal satu roll.')
  return {request:d.request,number:clean(d.number),supplier:clean(d.supplier),day:d.day,reason:clean(d.reason),notes:clean(d.notes)||null,rolls}
}
export function receivePocket(d:ReceiptDraft){
  const doc=prepareReceipt(d),rows=readReceipts(),same=rows.find(r=>r.request===doc.request)
  if(same){if(JSON.stringify(doc)!==JSON.stringify(same))throw Error('Permintaan sudah digunakan.');return same}
  const used=[...seedRolls,...rows.flatMap(r=>r.rolls)]
  if(used.some(r=>r.receipt.toLowerCase()===doc.number.toLowerCase()))throw Error('Nomor surat jalan sudah tercatat.')
  if(doc.rolls.some(r=>used.some(old=>old.id.toLowerCase()===r.id.toLowerCase())))throw Error('Nomor roll sudah tercatat.')
  sessionStorage.setItem(key,JSON.stringify([doc,...rows]));return doc
}
export function reverseReceipt(number:string,why:string){
  const rows=readReceipts(),r=rows.find(x=>x.number===number)
  if(!r||r.reversal||!why.trim())throw Error('Pilih penerimaan aktif dan isi alasan pembalikan.')
  const book: {issues:{roll:string;reversal?:string}[]}=JSON.parse(sessionStorage.getItem('erp.demo.pocket.period.v1')??'{"issues":[]}')
  if(r.rolls.some(roll=>book.issues.some(i=>i.roll===roll.id&&!i.reversal)))throw Error('Roll sudah dipakai. Balikkan pemakaian terkait lebih dulu.')
  sessionStorage.setItem(key,JSON.stringify(rows.map(x=>x===r?{...r,reversal:{at:new Date().toISOString(),reason:why.trim()}}:x)))
}
