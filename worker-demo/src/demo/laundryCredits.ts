import { laundryOutstanding, laundryPhysicalTime, type LaundryBillCredit, type LaundryClaim, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import { dayOk } from './warehouseDay'

export const billGross = (bill: LaundryFinalBill) => Math.round(bill.rate * bill.qty * 100)
export const billCredit = (bill: LaundryFinalBill) => (bill.credits??[]).reduce((sum, credit)=>sum+(credit.reversed ? 0 : credit.cents),0)
export const claimUse = (deliveries: LaundryDelivery[], id:string) =>
  deliveries.flatMap(row=>row.finalBills??[]).flatMap(bill=>bill.credits??[])
    .reduce((sum,credit)=>sum+(credit.claim===id&&!credit.reversed ? credit.cents : 0),0)

export const claimedPieces = (delivery: LaundryDelivery, type: LaundryClaim['type']) =>
  (delivery.claims??[]).reduce((sum,claim)=>sum+(claim.type===type&&!claim.reversed ? claim.qty : 0),0)

export const eligibleClaimPieces = (delivery: LaundryDelivery, type: LaundryClaim['type']) =>
  Math.max(0,(type==='BS' ? delivery.bs : laundryOutstanding(delivery))-claimedPieces(delivery,type))

export function validClaim(delivery: LaundryDelivery, claim: LaundryClaim) {
  return Number.isSafeInteger(claim.qty)&&claim.qty>0&&claim.qty<=eligibleClaimPieces(delivery,claim.type)
    && Number.isSafeInteger(claim.cents)&&claim.cents>0&&claim.reason.trim().length>=4
    && dayOk(claim.day)&&claim.day>=laundryPhysicalTime(delivery.sentAt).slice(0,10)
}

export function availableCredits(deliveries: LaundryDelivery[], vendor:string) {
  return deliveries.filter(delivery=>delivery.vendor===vendor).flatMap(delivery=>
    (delivery.claims??[]).filter(claim=>claim.approvedOn&&!claim.reversed).map(claim=>({
      claim, delivery, remaining:claim.cents-claimUse(deliveries,claim.id),
    }))).filter(row=>row.remaining>0)
}

export function validCredit(deliveries: LaundryDelivery[], delivery: LaundryDelivery, bill: LaundryFinalBill, credit: LaundryBillCredit) {
  const available=availableCredits(deliveries,delivery.vendor).find(row=>row.claim.id===credit.claim)
  return !!available&&Number.isSafeInteger(credit.cents)&&credit.cents>0
    && credit.cents<=Math.min(available.remaining,billGross(bill)-billCredit(bill))&&credit.reason.trim().length>=4
    && dayOk(credit.day)&&credit.day>=bill.day&&credit.day>=(available.claim.approvedOn??'')
}
