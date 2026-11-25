import { isPostedLaundryInvoice, laundryOutstanding, laundryOutstandingSizes, laundryPhysicalTime, type LaundryBillCredit, type LaundryClaim, type LaundryClaimResolution, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import { dayOk } from './warehouseDay'

export const billGross = (bill: LaundryFinalBill) => bill.parts
  ?bill.parts.reduce((sum,line)=>sum+Math.round(line.rate*line.qty*100),0):Math.round(bill.rate * bill.qty * 100)
export const billCredit = (bill: LaundryFinalBill) => (bill.credits??[]).reduce((sum, credit)=>sum+(credit.reversed ? 0 : credit.cents),0)
export const billPaid = (bill: LaundryFinalBill) => (bill.payments??[]).reduce((sum,row)=>sum+(row.reversal?0:row.cents),0)
export const vendorCreditApplied = (deliveries: LaundryDelivery[], deliveryId:string, billNumber:string) => deliveries
  .flatMap(row=>row.finalBills??[]).flatMap(bill=>bill.vendorUses??[])
  .reduce((sum,use)=>sum+(!use.reversal&&use.target?.delivery===deliveryId&&use.target.bill===billNumber?use.cents:0),0)
export const billRemaining = (rows:LaundryDelivery[], delivery:LaundryDelivery, bill:LaundryFinalBill) =>
  Math.max(0,billGross(bill)-billCredit(bill)-vendorCreditApplied(rows,delivery.id,bill.number)-billPaid(bill))
export const vendorReceivable = (rows:LaundryDelivery[], delivery:LaundryDelivery, bill:LaundryFinalBill) =>
  Math.max(0,billPaid(bill)-Math.max(0,billGross(bill)-billCredit(bill)-vendorCreditApplied(rows,delivery.id,bill.number)))
export const vendorBalance = (rows:LaundryDelivery[],delivery:LaundryDelivery,bill:LaundryFinalBill) =>
  vendorReceivable(rows,delivery,bill)-(bill.vendorUses??[]).reduce((sum,use)=>sum+(use.reversal?0:use.cents),0)
export const claimUse = (deliveries: LaundryDelivery[], id:string) =>
  deliveries.flatMap(row=>row.finalBills??[]).flatMap(bill=>bill.credits??[])
    .reduce((sum,credit)=>sum+(credit.claim===id&&!credit.reversed ? credit.cents : 0),0)

export const claimedOutsidePieces = (delivery:LaundryDelivery) =>
  (delivery.claims??[]).reduce((sum,claim)=>sum+(claim.type!=='BS'&&!claim.reversed&&!claim.resolution?claim.qty:0),0)

export const eligibleOutsideClaims = (delivery:LaundryDelivery) =>
  Math.max(0,laundryOutstanding(delivery)-claimedOutsidePieces(delivery))

export function validClaim(delivery: LaundryDelivery, claim: LaundryClaim) {
  return Number.isSafeInteger(claim.qty)&&claim.qty>0&&(claim.type==='BS'||claim.qty<=eligibleOutsideClaims(delivery))
    && Number.isSafeInteger(claim.cents)&&claim.cents>=(claim.type==='BS'?1:0)&&claim.reason.trim().length>=4
    && dayOk(claim.day)&&claim.day>=laundryPhysicalTime(delivery.sentAt).slice(0,10)
}

export function validClaimResolution(delivery:LaundryDelivery,claim:LaundryClaim,resolution:LaundryClaimResolution) {
  if(!claim.approvedOn||claim.reversed||claim.resolution||!dayOk(resolution.day)||resolution.day<claim.day||resolution.day<claim.approvedOn||resolution.reason.trim().length<4)return false
  if(resolution.kind==='CREDIT'&&claim.cents<=0)return false
  if(claim.type==='BS')return resolution.kind==='CREDIT'&&resolution.sizes.length===0
  const outside=laundryOutstandingSizes(delivery)
  return outside.length===resolution.sizes.length&&resolution.sizes.every((qty,index)=>Number.isSafeInteger(qty)&&qty>=0&&qty<=outside[index])
    &&resolution.sizes.reduce((sum,qty)=>sum+qty,0)===claim.qty
}

export function availableCredits(deliveries: LaundryDelivery[], vendor:string) {
  return deliveries.filter(delivery=>delivery.vendor===vendor).flatMap(delivery=>
    (delivery.claims??[]).filter(claim=>claim.approvedOn&&!claim.reversed&&(claim.resolution?claim.resolution.kind==='CREDIT':!claim.needsResolution)).map(claim=>({
      claim, delivery, remaining:claim.cents-claimUse(deliveries,claim.id),
    }))).filter(row=>row.remaining>0)
}

export function applyLaundryCredits(rows:LaundryDelivery[],deliveryId:string,billNumber:string,credits:LaundryBillCredit[]) {
  const delivery=rows.find(row=>row.id===deliveryId)
  const bill=delivery?.finalBills?.find(row=>row.number===billNumber&&isPostedLaundryInvoice(row))
  if(!delivery||!bill||!credits.length)throw Error('Pilih kredit dan invoice yang siap dibayar.')
  const total=credits.reduce((sum,credit)=>sum+credit.cents,0)
  const sources=new Map(availableCredits(rows,delivery.vendor).map(row=>[row.claim.id,row]))
  const existing=bill.credits??[]
  if(credits.every(credit=>existing.some(row=>row.id===credit.id&&JSON.stringify(row)===JSON.stringify(credit))))return rows
  if(new Set(credits.map(credit=>credit.claim)).size!==credits.length||new Set(credits.map(credit=>credit.id)).size!==credits.length
    ||!Number.isSafeInteger(total)||total>billRemaining(rows,delivery,bill)||credits.some(credit=>{
      const source=sources.get(credit.claim)
      return !source||existing.some(row=>row.id===credit.id)||!Number.isSafeInteger(credit.cents)||credit.cents<=0
        ||credit.cents>source.remaining||credit.reason.trim().length<4||!dayOk(credit.day)
        ||credit.day<bill.day||credit.day<(bill.corrections?.at(-1)?.day??'')
        ||credit.day<(source.claim.resolution?.day??source.claim.approvedOn??'')
    }))throw Error('Periksa tanggal, bukti potongan, saldo kredit, dan sisa invoice.')
  return rows.map(row=>row===delivery?{...row,finalBills:row.finalBills?.map(entry=>entry===bill?{...entry,credits:[...existing,...credits]}:entry)}:row)
}
