import { laundryOutstanding, laundryOutstandingSizes, laundryPhysicalTime, type LaundryBillCredit, type LaundryClaim, type LaundryClaimResolution, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import { dayOk } from './warehouseDay'

export const billGross = (bill: LaundryFinalBill) => bill.parts
  ?bill.parts.reduce((sum,line)=>sum+Math.round(line.rate*line.qty*100),0):Math.round(bill.rate * bill.qty * 100)
export const billCredit = (bill: LaundryFinalBill) => (bill.credits??[]).reduce((sum, credit)=>sum+(credit.reversed ? 0 : credit.cents),0)
export const billPaid = (bill: LaundryFinalBill) => (bill.payments??[]).reduce((sum,row)=>sum+row.cents,0)
export const vendorCreditApplied = (deliveries: LaundryDelivery[], deliveryId:string, billNumber:string) => deliveries
  .flatMap(row=>row.finalBills??[]).flatMap(bill=>bill.vendorUses??[])
  .reduce((sum,use)=>sum+(use.target?.delivery===deliveryId&&use.target.bill===billNumber?use.cents:0),0)
export const billRemaining = (rows:LaundryDelivery[], delivery:LaundryDelivery, bill:LaundryFinalBill) =>
  Math.max(0,billGross(bill)-billCredit(bill)-vendorCreditApplied(rows,delivery.id,bill.number)-billPaid(bill))
export const vendorReceivable = (rows:LaundryDelivery[], delivery:LaundryDelivery, bill:LaundryFinalBill) =>
  Math.max(0,billPaid(bill)-Math.max(0,billGross(bill)-billCredit(bill)-vendorCreditApplied(rows,delivery.id,bill.number)))
export const vendorBalance = (rows:LaundryDelivery[],delivery:LaundryDelivery,bill:LaundryFinalBill) =>
  vendorReceivable(rows,delivery,bill)-(bill.vendorUses??[]).reduce((sum,use)=>sum+use.cents,0)
export const claimUse = (deliveries: LaundryDelivery[], id:string) =>
  deliveries.flatMap(row=>row.finalBills??[]).flatMap(bill=>bill.credits??[])
    .reduce((sum,credit)=>sum+(credit.claim===id&&!credit.reversed ? credit.cents : 0),0)

export const claimedPieces = (delivery: LaundryDelivery, type: LaundryClaim['type']) =>
  (delivery.claims??[]).reduce((sum,claim)=>sum+(claim.type===type&&!claim.reversed&&(type==='BS'||!claim.resolution) ? claim.qty : 0),0)
export const claimedOutsidePieces = (delivery:LaundryDelivery) => claimedPieces(delivery,'STUCK')+claimedPieces(delivery,'MISSING')

export const eligibleClaimPieces = (delivery: LaundryDelivery, type: LaundryClaim['type']) =>
  Math.max(0,type==='BS' ? delivery.bs-claimedPieces(delivery,type) : laundryOutstanding(delivery)-claimedOutsidePieces(delivery))

export function validClaim(delivery: LaundryDelivery, claim: LaundryClaim) {
  return Number.isSafeInteger(claim.qty)&&claim.qty>0&&claim.qty<=eligibleClaimPieces(delivery,claim.type)
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

export function validCredit(deliveries: LaundryDelivery[], delivery: LaundryDelivery, bill: LaundryFinalBill, credit: LaundryBillCredit) {
  const available=availableCredits(deliveries,delivery.vendor).find(row=>row.claim.id===credit.claim)
  return !!available&&Number.isSafeInteger(credit.cents)&&credit.cents>0
    && credit.cents<=Math.min(available.remaining,billRemaining(deliveries,delivery,bill))&&credit.reason.trim().length>=4
    && dayOk(credit.day)&&credit.day>=bill.day&&credit.day>=(bill.corrections?.at(-1)?.day??'')
    && credit.day>=(available.claim.resolution?.day??available.claim.approvedOn??'')
}

export function applyLaundryCredit(rows:LaundryDelivery[],deliveryId:string,billNumber:string,credit:LaundryBillCredit) {
  const delivery=rows.find(row=>row.id===deliveryId)
  const bill=delivery?.finalBills?.find(row=>row.number===billNumber)
  if(!delivery||!bill||bill.credits?.some(row=>row.id===credit.id)||!validCredit(rows,delivery,bill,credit))return rows
  return rows.map(row=>row===delivery?{...row,finalBills:row.finalBills?.map(entry=>entry===bill?{...entry,credits:[...(entry.credits??[]),credit]}:entry)}:row)
}
