import type { StockChange } from './planner/model'

export const invoiceKey = 'erp.owner.invoice-register.v2'
export const returnDestinations = ['Gudang FG Utama', 'Gudang FG Cadangan', 'Area QC Retur']
export const returnGrades = ['Good', 'Grade B', 'Hold QC'] as const
export type ReturnGrade = typeof returnGrades[number]
export type ReturnLine = { key:string; sku:string; size:string; lot:string; qty:number; amount:number }
export type SaleReturn = {
  number:string; invoice:string; at:string; recordedAt:string; reason:string; destination:string; grade:ReturnGrade
  lines:ReturnLine[]; amount:number; ar:number; excess:number; settlement:''|'CREDIT'|'REFUND'; account?:string
  replaces?:string; replacedBy?:string
}

export function readSaleReturns():SaleReturn[] {
  const raw = typeof sessionStorage === 'undefined' ? null : sessionStorage.getItem(invoiceKey)
  return raw ? JSON.parse(raw).returnDocs ?? [] : []
}

function returnChanges(doc:SaleReturn,sign:number):StockChange[] {
  return doc.lines.map(line=>({key:line.sku,size:line.size,location:doc.destination,grade:doc.grade,delta:sign*line.qty}))
}

export function saleReturnActivity(returns:SaleReturn[]) {
  return returns.flatMap(doc=>{
    const change = { id:doc.number, day:doc.at.slice(0,10), time:doc.at.slice(11), note:doc.reason,
      recordedAt:doc.recordedAt, type:'Retur penjualan', changes:returnChanges(doc,1) }
    const replacement = returns.find(row=>row.number===doc.replacedBy)
    return replacement ? [change,{...change,id:doc.number+'-BALIK',note:replacement.reason,
      recordedAt:replacement.recordedAt,type:'Pembalikan retur',changes:returnChanges(doc,-1)}] : [change]
  })
}
