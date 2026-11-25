import { billGross } from './laundryCredits'
import { isLaundryInvoice, laundryContractKey, type LaundryContractRef, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import { dayOk } from './warehouseDay'
import type { StockSourceLink } from './receiptRollCorrection'

export type LaundryInvoiceDraft = {
  id: string
  vendor: string
  number: string
  day: string
  contracts: LaundryContractRef[]
}

export function laundryPayablesPath(vendor?:string,invoice?:string) {
  const options=new URLSearchParams({bagian:'laundry'})
  if(vendor)options.set('vendor',vendor)
  if(invoice)options.set('invoice',invoice)
  return '/keuangan/hutang-supplier/?'+options
}

export function laundryContractsPath(vendor?:string,contract?:string) {
  const options=new URLSearchParams({tab:'tagihan'})
  if(vendor)options.set('vendor',vendor)
  if(contract)options.set('cari',contract)
  return '/produksi/laundry/?'+options
}

export const laundryDocuments=(rows:LaundryDelivery[])=>rows.flatMap(delivery=>
  (delivery.finalBills??[]).map(bill=>({delivery,bill})))

export const laundryContracts=(rows:LaundryDelivery[],vendor?:string)=>laundryDocuments(rows)
  .filter(({delivery,bill})=>bill.kind==='CONTRABON'&&!bill.reversal&&(!vendor||delivery.vendor===vendor))
  .map(({delivery,bill})=>({delivery,bill,ref:{delivery:delivery.id,number:bill.number}}))

export function invoiceForLaundryContract(rows:LaundryDelivery[],ref:LaundryContractRef,except?:string) {
  return laundryDocuments(rows).find(({bill})=>bill.kind==='INVOICE'&&!bill.reversal&&bill.invoiceId!==except
    &&bill.contracts?.some(item=>laundryContractKey(item)===laundryContractKey(ref)))
}

export function reverseLaundryContract(rows:LaundryDelivery[],ref:LaundryContractRef,reason:string) {
  const source=laundryContracts(rows).find(row=>laundryContractKey(row.ref)===laundryContractKey(ref))
  if(!source||reason.trim().length<4||invoiceForLaundryContract(rows,ref))throw Error('Periksa kontrabon dan lepaskan dari invoice terlebih dahulu.')
  const reversal={reason:reason.trim(),at:new Date().toISOString()}
  return rows.map(row=>row===source.delivery?{
    ...row,finalBills:row.finalBills?.map(bill=>bill===source.bill?{...bill,reversal}:bill),
  }:row)
}

export function quoteLaundryInvoice(rows:LaundryDelivery[],draft:LaundryInvoiceDraft,status:'DRAFT'|'POSTED') {
  const number=draft.number.trim()
  const docs=laundryDocuments(rows)
  const existing=docs.find(({bill})=>bill.invoiceId===draft.id)
  if(existing&&(existing.delivery.vendor!==draft.vendor||existing.bill.status!=='DRAFT'||existing.bill.reversal))throw Error('Periksa status invoice dan vendor asal.')
  if(!rows.some(row=>row.vendor===draft.vendor)||!number||!dayOk(draft.day)||status==='POSTED'&&!draft.contracts.length)
    throw Error('Isi nomor invoice, tanggal, dan pilih minimal satu kontrabon untuk posting.')
  if(docs.some(({delivery,bill})=>delivery.vendor===draft.vendor&&isLaundryInvoice(bill)&&bill.invoiceId!==draft.id
    &&bill.number.toLocaleLowerCase()===number.toLocaleLowerCase()))throw Error('Nomor invoice sudah dipakai oleh laundry ini.')
  const keys=draft.contracts.map(laundryContractKey)
  if(new Set(keys).size!==keys.length)throw Error('Masukkan setiap kontrabon satu kali.')
  const sources=laundryContracts(rows,draft.vendor)
  const parts=draft.contracts.flatMap(ref=>{
    const source=sources.find(row=>laundryContractKey(row.ref)===laundryContractKey(ref))
    if(!source||draft.day<source.bill.day||invoiceForLaundryContract(rows,ref,draft.id))
      throw Error('Periksa tanggal invoice dan kontrabon yang masih tersedia untuk laundry ini.')
    const bill=source.bill
    return (bill.parts??[{delivery:source.delivery.id,qty:bill.qty,process:bill.process,rate:bill.rate}]).map(part=>({
      ...part,id:JSON.stringify([ref.delivery,ref.number,part.delivery]),contract:ref.number,
    }))
  })
  const invoice:LaundryFinalBill={kind:'INVOICE',invoiceId:draft.id,status,number,day:draft.day,process:'Invoice Laundry',
    contracts:draft.contracts,parts,qty:parts.reduce((sum,part)=>sum+part.qty,0),rate:0}
  if(!Number.isSafeInteger(invoice.qty)||!Number.isSafeInteger(billGross(invoice)))throw Error('Periksa total invoice.')
  return invoice
}

export function laundryInvoiceBlockers(rows:LaundryDelivery[],delivery:LaundryDelivery,bill:LaundryFinalBill):StockSourceLink[] {
  const href=laundryPayablesPath(delivery.vendor,bill.number)+'#pembayaran-invoice'
  return [
    ...(bill.payments??[]).filter(row=>!row.reversal).map(row=>({label:'Pembayaran · '+row.reference,href})),
    ...(bill.credits??[]).filter(row=>!row.reversed).map(row=>({label:'Potongan kredit · '+row.reason,href})),
    ...(bill.vendorUses??[]).filter(row=>!row.reversal).map(row=>({label:'Penyelesaian piutang · '+row.reason,href})),
    ...laundryDocuments(rows).filter(source=>source.bill.vendorUses?.some(use=>!use.reversal&&use.target?.delivery===delivery.id&&use.target.bill===bill.number))
      .map(source=>({label:'Piutang dari '+source.bill.number,href:laundryPayablesPath(delivery.vendor,source.bill.number)+'#pembayaran-invoice'})),
  ]
}

export function reverseLaundryInvoice(rows:LaundryDelivery[],deliveryId:string,number:string,reason:string) {
  const delivery=rows.find(row=>row.id===deliveryId)
  const bill=delivery?.finalBills?.find(row=>row.number===number&&isLaundryInvoice(row)&&!row.reversal)
  if(!delivery||!bill||reason.trim().length<4||laundryInvoiceBlockers(rows,delivery,bill).length)throw Error('Selesaikan pembayaran atau kredit yang masih terhubung.')
  const reversal={reason:reason.trim(),at:new Date().toISOString()}
  return rows.map(row=>row!==delivery?row:{...row,finalBills:row.finalBills?.map(doc=>doc===bill?{...doc,reversal}:doc)})
}

export function saveLaundryInvoice(rows:LaundryDelivery[],draft:LaundryInvoiceDraft,status:'DRAFT'|'POSTED') {
  const invoice=quoteLaundryInvoice(rows,draft,status)
  const anchor=draft.contracts[0]?.delivery??rows.find(row=>row.vendor===draft.vendor)!.id
  return rows.map(row=>{
    const bills=(row.finalBills??[]).filter(bill=>bill.invoiceId!==draft.id)
    if(row.id===anchor)return {...row,finalBills:[...bills,invoice]}
    return bills.length===row.finalBills?.length||!row.finalBills?row:{...row,finalBills:bills}
  })
}
