import {masterBook,noteStock} from './accessoryPricing'
import type {ConversionKit,ConversionReturn,Session} from './planner/model'
import {dayOk} from './warehouseDay'

export type ConversionAccessoryDraft = {
  used:{code:string;qty:string}[]
  expected:{code:string;qty:string;holder:string}[]
}
export const emptyAccessories:ConversionAccessoryDraft = {used:[],expected:[]}
export const accessoryPcs = (value:string) => /^\d{1,9}$/.test(value.trim()) ? Number(value.trim()) : NaN

export function checkConversionAccessories(session:Session,draft?:ConversionAccessoryDraft):ConversionKit|undefined {
  if(!draft||!draft.used.length&&!draft.expected.length)return undefined
  const available=masterBook().items.filter(item=>item.active&&item.stockUom.toLowerCase()==='pcs')
  if(new Set(draft.used.map(row=>row.code)).size!==draft.used.length||new Set(draft.expected.map(row=>row.code)).size!==draft.expected.length) {
    throw Error('Gabungkan jumlah aksesori yang sama dalam satu baris.')
  }
  const used=draft.used.map(row=>{
    const item=available.find(item=>item.code===row.code),qty=accessoryPcs(row.qty)
    if(!item||!(qty>0)||qty>noteStock(item.code,item.stock,undefined,session))throw Error('Periksa stok dan jumlah aksesori yang dipakai.')
    return {code:item.code,name:item.name,qty,rate:item.movingAverage}
  })
  const expected=draft.expected.map(row=>{
    const item=available.find(item=>item.code===row.code),qty=accessoryPcs(row.qty)
    if(!item||!(qty>0)||!row.holder.trim())throw Error('Isi aksesori, jumlah pcs, dan pemegang bongkaran.')
    return {code:item.code,name:item.name,qty,holder:row.holder.trim()}
  })
  return {used,expected}
}

export const kitCost = (kit:ConversionKit) => kit.used.reduce((sum,row)=>sum+Math.round(row.qty*row.rate*100),0)/100
export function receivedConversionAccessories(session:Session,conversion:string,code:string) {
  return (session.conversionReturns??[]).filter(row=>row.conversion===conversion&&row.code===code&&!row.reversed)
    .reduce((sum,row)=>({good:sum.good+row.good,damaged:sum.damaged+row.damaged}),{good:0,damaged:0})
}

export function receiveConversionAccessories(session:Session,row:ConversionReturn):Session {
  const ledger=session.conversionReturns??[]
  const duplicate=ledger.find(event=>event.id===row.id)
  if(duplicate){if(JSON.stringify(duplicate)!==JSON.stringify(row))throw Error('Penerimaan sudah tercatat.');return session}
  const doc=session.stockEvents?.find(event=>event.id===row.conversion)
  const expected=doc?.kit?.expected.find(line=>line.code===row.code)
  const received=receivedConversionAccessories(session,row.conversion,row.code)
  const total=row.good+row.damaged
  if(!doc||!expected||session.stockEvents?.some(event=>event.reverses===doc.id)||
    !dayOk(row.day)||row.day<(doc.date??'')||!row.reason.trim()||!Number.isSafeInteger(row.good)||!Number.isSafeInteger(row.damaged)
    ||row.good<0||row.damaged<0||total<=0||total>expected.qty-received.good-received.damaged) {
    throw Error('Periksa tanggal, jumlah yang masih ditunggu, dan hasil pemeriksaan aksesori.')
  }
  return {...session,conversionReturns:[...ledger,row]}
}

export function reverseConversionAccessories(session:Session,id:string,reason:string):Session {
  const event=session.conversionReturns?.find(row=>row.id===id)
  const item=masterBook().items.find(row=>row.code===event?.code)
  if(!event||event.reversed||!reason.trim())throw Error('Isi alasan pembalikan penerimaan.')
  if(event.good>0&&(!item||noteStock(item.code,item.stock,undefined,session)<event.good))throw Error('Stok layak pakai yang sudah diterima tidak cukup untuk dibalik.')
  return {...session,conversionReturns:session.conversionReturns?.map(row=>row===event?{...row,reversed:reason.trim()}:row)}
}
