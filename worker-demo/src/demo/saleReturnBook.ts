import { cashAccounts } from '../financeData'
import { readInvoices, sourceLines, writeSaleReturn, type DemoInvoice } from './saleBook'
import { readSaleReturns, returnDestinations, returnGrades, type SaleReturn } from './saleReturnJournal'
import { dayOk } from './warehouseDay'
import { readPlannerSession } from './planner/session'
import { stockAt } from './planner/conversion'
import { skuByKey } from './skuCatalog'
import { comparePhysical, fgActivity } from './fgTimeline'

export type ReturnDraft = Pick<SaleReturn,'at'|'reason'|'destination'|'grade'|'settlement'|'account'> & {
  quantities:Record<string,string>
}

export const canReturnInvoice=(doc:DemoInvoice)=>!doc.buyerKind&&['POSTED','PAID'].includes(doc.status)

export function returnAllocations(invoice:DemoInvoice,returns:SaleReturn[],except?:string) {
  const related=returns.filter(row=>row.invoice===invoice.number)
  const recorded=related.filter(row=>!row.replacedBy&&row.number!==except).flatMap(row=>row.lines)
  const originalValue=invoice.returns-related.reduce((sum,row)=>sum+(row.replacedBy?0:row.amount),0)
  const knownOpeningReturn=invoice.number==='INV-JUAL-0241'&&originalValue===180000
  return sourceLines(invoice).flatMap(line=>line.product.sizes.flatMap((size,index)=>{
    const sold=line.quantities[index]??0
    if(!sold)return []
    const sku=line.product.brand+' '+line.product.code
    const key=line.key+'|'+size
    const openingQty=knownOpeningReturn&&sku==='Vivo 73001'&&size==='29'?2:0
    const returned=openingQty+recorded.reduce((sum,row)=>sum+(row.key===key?row.qty:0),0)
    const lot=openingQty?'FG-73001-0822':`SIM-${invoice.number.slice(-4)}-${line.product.code}-${size}`
    return [{key,sku,size,lot,sold,returned,eligible:originalValue>0&&!knownOpeningReturn?0:Math.max(0,sold-returned),price:line.priceDozen/12}]
  }))
}

export function returnQuote(invoice:DemoInvoice,returns:SaleReturn[],draft:ReturnDraft,original?:SaleReturn) {
  const allocations=returnAllocations(invoice,returns,original?.number)
  const lines=allocations.flatMap(row=>{
    const qty=Number(draft.quantities[row.key]||0)
    return qty>0?[{key:row.key,sku:row.sku,size:row.size,lot:row.lot,qty,amount:Math.round(qty*row.price*100)/100}]:[]
  })
  const valid=Object.entries(draft.quantities).every(([key,value])=>!value||/^\d{1,9}$/.test(value)&&Number(value)<=(allocations.find(row=>row.key===key)?.eligible??0))
  const amount=Math.round(lines.reduce((sum,row)=>sum+row.amount,0)*100)/100
  const outstanding=Math.max(0,Math.round((invoice.gross-invoice.returns-invoice.paid+(original?.amount??0))*100)/100)
  const ar=Math.min(amount,outstanding)
  return {lines,valid,qty:lines.reduce((sum,row)=>sum+row.qty,0),amount,ar,excess:Math.round((amount-ar)*100)/100,outstanding}
}

export function postSaleReturn(invoiceId:string,draft:ReturnDraft,replaces?:string) {
  const returns=readSaleReturns()
  const invoice=readInvoices().find(row=>row.number===invoiceId)
  if(!invoice||!canReturnInvoice(invoice))throw Error('Invoice asal sudah berubah.')
  const original=returns.find(row=>row.number===replaces&&row.invoice===invoiceId&&!row.replacedBy)
  if(replaces&&!original)throw Error('Retur asal sudah dikoreksi.')
  if(original&&returns.some(row=>row.invoice===invoiceId&&!row.replacedBy&&row.recordedAt>original.recordedAt)){
    throw Error('Buka retur terbaru pada invoice ini sebelum mengoreksi retur lebih awal.')
  }
  const {lines,qty,valid,amount,ar,excess}=returnQuote(invoice,returns,draft,original)
  const at=draft.at, day=at.slice(0,10)
  if(!valid||!qty||!Number.isSafeInteger(Math.round(amount*100))||!dayOk(day)||!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$/.test(at)
    ||at<`${invoice.dateKey}T${invoice.time}`||draft.reason.trim().length<4||!returnGrades.includes(draft.grade)
    ||!returnDestinations.includes(draft.destination)||draft.grade==='Hold QC'&&draft.destination!=='Area QC Retur'
    ||draft.grade!=='Hold QC'&&draft.destination==='Area QC Retur')throw Error('Periksa jumlah per ukuran, grade, lokasi, tanggal fisik, dan alasan retur.')
  if(excess>0&&(!draft.settlement||draft.settlement==='REFUND'&&!cashAccounts.some(account=>account.name===draft.account)))throw Error('Pilih penyelesaian sisa kredit atau rekening refund.')
  if(original){
    const session=readPlannerSession()
    const start={day:original.at.slice(0,10),physicalTime:original.at.slice(11)}
    const replacementAt={day,physicalTime:at.slice(11)}
    for(const line of original.lines){
      const article=skuByKey(line.sku,session)
      if(!article)throw Error('SKU sumber retur sudah berubah.')
      const index=article.sizes.indexOf(line.size)
      const replacement=(draft.destination===original.destination&&draft.grade===original.grade?lines.find(row=>row.key===line.key)?.qty:0)??0
      const activity=fgActivity(article,session,original.destination,original.grade)
      const current=stockAt(article,line.size,session,original.destination,original.grade)
      const points=[start,replacementAt,...activity].filter(point=>comparePhysical(point,start)>=0)
      if(index<0||points.some(point=>{
        const balance=activity.reduce((sum,row)=>comparePhysical(row,point)>0?sum-row.delta[index]:sum,current)
        return balance-line.qty+(comparePhysical(point,replacementAt)>=0?replacement:0)<0
      }))throw Error('Stok hasil retur sudah digunakan. Periksa mutasi lanjutan sebelum mengoreksi.')
    }
  }
  const result:SaleReturn={...draft,number:'RET-'+day.replaceAll('-','').slice(2)+'-'+crypto.randomUUID().slice(0,6).toUpperCase(),
    invoice:invoice.number,reason:draft.reason.trim(),recordedAt:new Date().toISOString(),lines,amount,ar,excess,
    settlement:excess>0?draft.settlement:'',account:excess>0&&draft.settlement==='REFUND'?draft.account:undefined,replaces:original?.number}
  writeSaleReturn(result)
  return result
}
