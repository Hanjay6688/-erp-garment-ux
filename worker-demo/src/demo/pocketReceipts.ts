import {dayOk} from './warehouseDay'
import {pocketScale, readPocketBook, readPocketNumber} from './pocketUsage'
import {readPocketMaterials} from './pocketMaterials'
import {readRupiahInput} from '../moneyInput'
import { pocketAllocationPath, pocketIssuePath, receiptDocumentPath, receiptRolls, reviewRollReceiptCorrection, type ReceiptReversal, type RollReceiptCorrection, type StockSourceLink } from './receiptRollCorrection'
export type PocketUnit='yd'|'m'
export type PocketRoll={id:string;name:string;length:number;rate:number;unit:PocketUnit;date:string;location:string;receipt:string;sequence?:number;materialId?:string;factory?:string;supplier?:string;finalBill?:string;physicalCode?:string}
type RollInput={number:string;qty:string}
export type ReceiptDraft={request:string;number:string;supplier:string;location:string;material:string;day:string;unit:PocketUnit;rate:string;reason:string;notes:string;rolls:RollInput[]}
type PocketBill = { number: string; day: string; rate: number }
export type PocketReceipt={request:string;number:string;supplier:string;day:string;reason:string;notes:string|null;rolls:PocketRoll[];bill?:PocketBill;reversal?:ReceiptReversal;corrections?:RollReceiptCorrection[];billReversals?:(PocketBill&ReceiptReversal)[]}
const key='erp.demo.pocket.receipts.v1'
export const seedRolls:PocketRoll[]=[
  {id:'KT-001',name:'Kain kantong putih',length:100,rate:9000,unit:'yd',date:'2026-11-20',location:'Gudang Bahan',receipt:'SJ-KT-001'},
  {id:'KT-002',name:'Kain kantong hitam',length:60,rate:10500,unit:'yd',date:'2026-11-20',location:'Gudang Bahan',receipt:'SJ-KT-001'},
]
export const readReceipts=():PocketReceipt[]=>JSON.parse(sessionStorage.getItem(key)??'[]')
export const pocketRolls=()=>[...seedRolls,...readReceipts().filter(r=>!r.reversal).flatMap(r=>
  receiptRolls(r).map(roll=>r.bill?{...roll,rate:r.bill.rate,finalBill:r.bill.number}:roll))]
export const receiptPath='/gudang/pembelian-penerimaan/?jenis=kantong'
export const pocketRollLabel = (roll: PocketRoll) => roll.physicalCode ?? (roll.sequence ? 'Roll ' + String(roll.sequence).padStart(2, '0') : roll.id)
export function pocketBenchmark(d:Pick<ReceiptDraft,'material'|'unit'>){
  return readPocketMaterials().find(item => item.id === d.material)?.benchmarks?.[d.unit] ?? null
}
export function recordPocketBill(receiptNumber: string, input: PocketBill) {
  const rows = readReceipts()
  const receipt = rows.find(row => row.number === receiptNumber)
  const number = input.number.trim()
  if (!receipt || receipt.reversal || !number || !dayOk(input.day) || input.day < receipt.day) {
    throw Error('Isi nomor tagihan dan tanggal yang sama atau sesudah penerimaan.')
  }
  if (!Number.isFinite(input.rate) || input.rate < 0 || !Number.isSafeInteger(receiptRolls(receipt).reduce((sum, roll) => sum + Math.round(roll.length * input.rate * 100), 0))) {
    throw Error('Periksa harga final per satuan.')
  }
  const bill = { ...input, number }
  if (receipt.bill) {
    if (receipt.bill.number === bill.number && receipt.bill.day === bill.day && receipt.bill.rate === bill.rate) return receipt.bill
    throw Error('Surat jalan ini sudah memiliki tagihan final.')
  }
  sessionStorage.setItem(key, JSON.stringify(rows.map(row => row === receipt ? { ...row, bill } : row)))
  return bill
}
export function prepareReceipt(d:ReceiptDraft):PocketReceipt{
  const clean=(v:string)=>v.trim()
  const material=readPocketMaterials().find(item=>item.id===d.material)
  if(!clean(d.number))throw Error('Isi nomor surat jalan.')
  if(!dayOk(d.day))throw Error('Isi tanggal barang datang yang sah.')
  if(!clean(d.supplier)||!clean(d.location)||!material)throw Error('Pilih supplier, gudang, dan nama kain kantong dari master.')
  if(!clean(d.reason))throw Error('Isi alasan penerimaan.')
  const rate=clean(d.rate)?readRupiahInput(d.rate):pocketBenchmark(d)
  if(rate===null)throw Error('Harga master belum diatur untuk bahan dan satuan ini. Isi harga sementara.')
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
    return {id,name:material.name,length:qty,rate,unit:d.unit,date:d.day,location:clean(d.location),receipt:clean(d.number),...(!number&&{sequence}),
      materialId:material.id,factory:material.factory||undefined,supplier:clean(d.supplier)}
  })
  if(!rolls.length)throw Error('Isi minimal satu roll.')
  const total = rolls.reduce((sum, roll) => sum + Math.round(roll.length * roll.rate * 100), 0)
  if (!Number.isSafeInteger(total)) throw Error('Total biaya melebihi batas yang bisa dicatat.')
  return {request:d.request,number:clean(d.number),supplier:clean(d.supplier),day:d.day,reason:clean(d.reason),notes:clean(d.notes)||null,rolls}
}
export function reviewPocketReceipt(d:ReceiptDraft){
  const doc=prepareReceipt(d),rows=readReceipts(),same=rows.find(r=>r.request===doc.request)
  if(same){
    const comparable = ({ bill: _bill, corrections: _corrections, billReversals: _reversals, ...receipt }: PocketReceipt) => JSON.stringify({ ...receipt, rolls: receipt.rolls.map(({name,materialId,factory: _factory,supplier: _supplier,...roll}) => ({...roll, material: materialId??name})) })
    if(comparable(doc)!==comparable(same))throw Error('Permintaan sudah digunakan.')
    return same
  }
  const used=[...seedRolls,...rows.flatMap(receiptRolls)]
  if(used.some(r=>r.receipt.toLowerCase()===doc.number.toLowerCase()))throw Error('Nomor surat jalan sudah tercatat.')
  const duplicate=doc.rolls.find(r=>used.some(old=>[old.id,old.physicalCode].some(code=>code?.toLowerCase()===r.id.toLowerCase())))
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
  if(receiptIssues(r).length)throw Error('Roll sudah dipakai. Balikkan dokumen pemakaian terlebih dahulu.')
  if(r.bill)throw Error('Balikkan tagihan final terlebih dahulu.')
  sessionStorage.setItem(key,JSON.stringify(rows.map(x=>x===r?{...r,reversal:{at:new Date().toISOString(),reason:why.trim()}}:x)))
}

function receiptIssues(receipt:PocketReceipt) {
  return readPocketBook().issues.filter(issue=>!issue.reversal&&receipt.rolls.some(roll=>roll.id===issue.roll))
}

export function pocketReceiptBlockers(receipt:PocketReceipt):StockSourceLink[] {
  return [
    ...(receipt.bill?[{label:'Tagihan final '+receipt.bill.number,href:receiptDocumentPath(receipt.number,'kantong')}]:[]),
    ...receiptIssues(receipt).map(issue=>({label:'Pemakaian '+issue.id,href:pocketIssuePath(issue.id)})),
  ]
}

export function pocketBillBlockers(receipt:PocketReceipt):StockSourceLink[] {
  const uses=new Set(receiptIssues(receipt).map(issue=>issue.id))
  return readPocketBook().allocations.filter(row=>!row.reversal&&row.sources.some(id=>uses.has(id)))
    .map(row=>({label:'Pembagian biaya '+row.id,href:pocketAllocationPath(row.id)}))
}

export function reversePocketBill(number:string,reason:string) {
  const rows=readReceipts(),receipt=rows.find(row=>row.number===number)
  if(!receipt?.bill||receipt.reversal||reason.trim().length<4||pocketBillBlockers(receipt).length)
    throw Error('Periksa tagihan dan pembagian biaya terkait.')
  const history={...receipt.bill,reason:reason.trim(),at:new Date().toISOString()}
  sessionStorage.setItem(key,JSON.stringify(rows.map(row=>row===receipt?{...row,bill:undefined,billReversals:[...(row.billReversals??[]),history]}:row)))
}

export function correctPocketReceiptRoll(number:string,id:string,input:{id:string;code:string;length:number;reason:string;at:string}) {
  const rows=readReceipts(),receipt=rows.find(row=>row.number===number&&!row.reversal)
  const roll=receipt&&receiptRolls(receipt).find(row=>row.id===id)
  if(!receipt||!roll)throw Error('Pilih roll dari penerimaan aktif.')
  if(receipt.bill&&roll.length!==input.length)throw Error('Balikkan tagihan final '+receipt.bill.number+' sebelum mengoreksi panjang.')
  const used=receiptIssues(receipt).filter(issue=>issue.roll===id).reduce((sum,issue)=>sum+issue.qty,0)/pocketScale
  const correction=reviewRollReceiptCorrection(roll,input,[...seedRolls,...rows.flatMap(receiptRolls)],used)
  if(!Number.isSafeInteger(Math.round(correction.length*roll.rate*100)))throw Error('Nilai roll melebihi batas.')
  sessionStorage.setItem(key,JSON.stringify(rows.map(row=>row===receipt?{...row,corrections:[...(row.corrections??[]),correction]}:row)))
}
