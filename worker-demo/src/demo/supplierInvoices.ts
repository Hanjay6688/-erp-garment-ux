import {receiptMaterial} from './fabricArchive'
import { payables, type Payable } from '../financeData'
import { readRupiahInput } from '../moneyInput'
import { masterBook } from './accessoryPricing'
import { readPlannerSession } from './planner/session'
import { dayOk } from './warehouseDay'
import { receiptRolls, type ReceiptReversal } from './receiptRollCorrection'

export type SupplierGroup='FABRIC'|'ACCESSORY'
export type KasbonSource={id:string;number:string;day:string;supplier:string;name:string;unit:string;qty:number;rate:number;group:SupplierGroup}
type SupplierLine={source:KasbonSource;qty:number;rate:number;cents:number}
export type SupplierInvoice={id:string;number:string;day:string;supplier:string;group:SupplierGroup;status:'DRAFT'|'POSTED';lines:SupplierLine[];reversal?:ReceiptReversal}
type DraftLine={sourceId:string;qty:string;rate:string}
export type SupplierInvoiceDraft={id:string;number:string;day:string;supplier:string;group:SupplierGroup;lines:DraftLine[]}

const key='erp.demo.supplier-invoices.v1'
const opening:KasbonSource[]=[
  {id:'kain-0098',number:'BELI-KAIN-0098',day:'2026-08-26',supplier:'CV Sinar Textile',name:'Kain Lucy Navy',unit:'yd',qty:320,rate:51500,group:'FABRIC'},
  {id:'kain-0101',number:'BELI-KAIN-0101',day:'2026-08-27',supplier:'CV Sinar Textile',name:'Kain Lucy Maroon',unit:'m',qty:274,rate:59100,group:'FABRIC'},
  {id:'acc-0047',number:'BELI-ACC-0047',day:'2026-11-21',supplier:'PT Kancing Nusantara',name:'Kancing Jeans',unit:'pcs',qty:240,rate:620,group:'ACCESSORY'},
  {id:'acc-0048',number:'BELI-ACC-0048',day:'2026-11-23',supplier:'PT Kancing Nusantara',name:'Label Woven',unit:'pcs',qty:120,rate:530,group:'ACCESSORY'},
]
export const readSupplierInvoices=():SupplierInvoice[]=>JSON.parse(sessionStorage.getItem(key)??'[]')
export const writeSupplierInvoices=(rows:SupplierInvoice[])=>sessionStorage.setItem(key,JSON.stringify(rows))
export const supplierInvoiceAmount=(doc:SupplierInvoice)=>doc.lines.reduce((sum,line)=>sum+line.cents,0)/100
const scaled=(qty:number)=>Math.round(qty*1e6)
export const supplierDateLabel=(day:string)=>new Intl.DateTimeFormat('id-ID',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(day+'T12:00Z'))

export function kasbonSources():KasbonSource[] {
  const session=readPlannerSession()
  const fabric=(session.fabricReceipts??[]).filter(row=>!row.reversal).map(row=>({id:'kain:'+row.id,number:row.number,day:row.day,supplier:row.supplier,
    name:receiptMaterial(session,row),unit:row.unit,qty:receiptRolls(row).reduce((sum,roll)=>sum+roll.length,0),rate:row.rate,group:'FABRIC' as const}))
  const items=masterBook().items
  const accessory=(session.accessoryReceipts??[]).filter(row=>!row.reversal).map(row=>({id:'acc:'+row.id,number:row.number,day:row.day,supplier:row.supplier,
    name:items.find(item=>item.code===row.code)?.name??row.code,unit:'pcs',qty:row.qty,rate:row.rate,group:'ACCESSORY' as const}))
  return [...opening,...fabric,...accessory]
}

export function supplierSourceRemaining(rows:SupplierInvoice[],source:KasbonSource,except?:string) {
  const reserved=rows.filter(row=>row.id!==except&&!row.reversal).flatMap(row=>row.lines).reduce((sum,line)=>sum+(line.source.id===source.id?scaled(line.qty):0),0)
  return Math.max(0,scaled(source.qty)-reserved)/1e6
}

export function quoteSupplierInvoice(draft:SupplierInvoiceDraft,status:SupplierInvoice['status'],rows=readSupplierInvoices()):SupplierInvoice {
  const previous=rows.find(row=>row.id===draft.id)
  const number=draft.number.trim()
  const sources=kasbonSources().filter(row=>row.supplier===draft.supplier&&row.group===draft.group)
  if(previous?.status==='POSTED'||previous?.reversal||previous&&(previous.supplier!==draft.supplier||previous.group!==draft.group))throw Error('Periksa status invoice dan supplier asal.')
  const numberTaken=rows.some(row=>row.id!==draft.id&&row.number.toLowerCase()===number.toLowerCase())
    ||payables.some(row=>row.number.toLowerCase()===number.toLowerCase())||number.toLowerCase()==='inv-st-8823'
  if(!number||numberTaken||!dayOk(draft.day)||status==='POSTED'&&!draft.lines.length)throw Error('Isi nomor invoice yang unik, tanggal, dan minimal satu kasbon untuk posting.')
  if(new Set(draft.lines.map(line=>line.sourceId)).size!==draft.lines.length)throw Error('Kasbon yang sama cukup dipilih satu kali.')
  const lines=draft.lines.map(input=>{
    const source=sources.find(row=>row.id===input.sourceId)
    const qty=/^\d+(?:[.,]\d{1,6})?$/.test(input.qty.trim())?Number(input.qty.replace(',','.')):NaN
    const rate=readRupiahInput(input.rate), cents=Math.round(qty*rate*100)
    if(!source||draft.day<source.day||!Number.isSafeInteger(scaled(qty))||qty<=0||scaled(qty)>scaled(supplierSourceRemaining(rows,source,draft.id))
      ||source.unit==='pcs'&&!Number.isInteger(qty)||!Number.isSafeInteger(cents)||cents<0){
      throw Error('Periksa jumlah yang masih tersedia, harga aktual, dan tanggal kasbon terpilih.')
    }
    return {source,qty,rate,cents}
  })
  const cents=lines.reduce((sum,line)=>sum+line.cents,0)
  if(!Number.isSafeInteger(cents)||status==='POSTED'&&cents<=0)throw Error('Periksa total invoice sebelum posting.')
  return {...draft,number,status,lines}
}

export function saveSupplierInvoice(draft:SupplierInvoiceDraft,status:SupplierInvoice['status']) {
  const rows=readSupplierInvoices()
  const doc=quoteSupplierInvoice(draft,status,rows)
  const next=[doc,...rows.filter(row=>row.id!==doc.id)]
  writeSupplierInvoices(next)
  return {doc,rows:next}
}

export function invoicePayable(doc:SupplierInvoice):Payable {
  return {number:doc.number,party:doc.supplier,kind:'MATERIAL_AP',economicDate:supplierDateLabel(doc.lines.map(line=>line.source.day).sort()[0]),
    receivedDate:supplierDateLabel(doc.day),dueDate:'—',amount:supplierInvoiceAmount(doc),paid:0,status:'OPEN',costState:'ACTUAL',
    reference:doc.lines.map(line=>line.source.number).join(' · ')}
}
