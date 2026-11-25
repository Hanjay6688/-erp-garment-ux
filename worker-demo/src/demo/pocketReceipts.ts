import {dayOk} from './warehouseDay'
import {pocketScale, readPocketBook, readPocketNumber} from './pocketUsage'
export type PocketUnit='yd'|'m'
export type PocketRoll={id:string;name:string;length:number;rate:number;unit:PocketUnit;date:string;location:string;receipt:string;sequence?:number}
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
export const pocketRollLabel = (roll: PocketRoll) => roll.sequence ? 'Roll ' + String(roll.sequence).padStart(2, '0') : roll.id
export function pocketBenchmark(d:Pick<ReceiptDraft,'supplier'|'material'|'unit'|'day'>){
  if(d.supplier!=='Sinaran')return null
  return seedRolls.find(r=>r.name===d.material&&r.unit===d.unit&&r.date<=d.day)?.rate??null
}
export function prepareReceipt(d:ReceiptDraft):PocketReceipt{
  const clean=(v:string)=>v.trim()
  if(!clean(d.number))throw Error('Isi nomor surat jalan.')
  if(!dayOk(d.day))throw Error('Isi tanggal barang datang yang sah.')
  if(!clean(d.supplier)||!clean(d.location)||!clean(d.material))throw Error('Pilih supplier, gudang, dan nama kain kantong.')
  if(!clean(d.reason))throw Error('Isi alasan penerimaan.')
  const rate=clean(d.rate)?readPocketNumber(d.rate):pocketBenchmark(d)
  if(rate===null)throw Error('Harga master belum diatur untuk supplier, bahan dan satuan ini. Isi harga sementara.')
  if(!['yd','m'].includes(d.unit)||!Number.isFinite(rate)||rate<0||!Number.isSafeInteger(Math.round(rate*100)))throw Error('Periksa satuan dan harga per satuan.')
  const seen=new Set<string>()
  const rolls=d.rolls.flatMap((r,index)=>{
    const number = clean(r.number)
    if (!number && !clean(r.qty)) return []
    const sequence = index + 1
    const id = number || clean(d.number) + '-' + String(sequence).padStart(2, '0')
    const qty = readPocketNumber(r.qty)
    if (!(qty > 0) || !Number.isSafeInteger(Math.round(qty * pocketScale)) || !Number.isSafeInteger(Math.round(qty * rate * 100))) {
      throw Error('Isi panjang yang lebih dari nol di roll ' + sequence + '.')
    }
    if(seen.has(id.toLowerCase()))throw Error('Nomor roll '+id+' ditulis lebih dari sekali di surat jalan.')
    seen.add(id.toLowerCase())
    return {id,name:clean(d.material),length:qty,rate,unit:d.unit,date:d.day,location:clean(d.location),receipt:clean(d.number),...(!number&&{sequence})}
  })
  if(!rolls.length)throw Error('Isi minimal satu roll.')
  return {request:d.request,number:clean(d.number),supplier:clean(d.supplier),day:d.day,reason:clean(d.reason),notes:clean(d.notes)||null,rolls}
}
export function reviewPocketReceipt(d:ReceiptDraft){
  const doc=prepareReceipt(d),rows=readReceipts(),same=rows.find(r=>r.request===doc.request)
  if(same){if(JSON.stringify(doc)!==JSON.stringify(same))throw Error('Permintaan sudah digunakan.');return same}
  const used=[...seedRolls,...rows.flatMap(r=>r.rolls)]
  if(used.some(r=>r.receipt.toLowerCase()===doc.number.toLowerCase()))throw Error('Nomor surat jalan sudah tercatat.')
  const duplicate=doc.rolls.find(r=>used.some(old=>old.id.toLowerCase()===r.id.toLowerCase()))
  if(duplicate)throw Error('Nomor roll '+duplicate.id+' sudah tercatat.')
  return doc
}
export function receivePocket(d:ReceiptDraft){
  const doc=reviewPocketReceipt(d),rows=readReceipts()
  if(!rows.some(r=>r.request===doc.request))sessionStorage.setItem(key,JSON.stringify([doc,...rows]))
  return doc
}
export function reverseReceipt(number:string,why:string){
  const rows=readReceipts(),r=rows.find(x=>x.number===number)
  if(!r||r.reversal||!why.trim())throw Error('Pilih penerimaan aktif dan isi alasan pembalikan.')
  const book=readPocketBook()
  if(r.rolls.some(roll=>book.issues.some(i=>i.roll===roll.id&&!i.reversal)))throw Error('Roll sudah dipakai. Balikkan pemakaian terkait lebih dulu.')
  sessionStorage.setItem(key,JSON.stringify(rows.map(x=>x===r?{...r,reversal:{at:new Date().toISOString(),reason:why.trim()}}:x)))
}
