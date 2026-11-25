import { cashAccounts } from '../financeData'
import { billCredit, billGross, billRemaining, vendorBalance, vendorCreditApplied } from './laundryCredits'
import type { LaundryBillCorrection, LaundryBillPayment, LaundryDelivery, LaundryFinalBill, LaundryVendorUse } from './laundryModel'
import { dayOk } from './warehouseDay'

export type Settlement = {kind:'PAY';record:LaundryBillPayment}|{kind:'CORRECT';record:LaundryBillCorrection}|{kind:'USE';record:LaundryVendorUse}

export function laundryBillAtRate(bill:LaundryFinalBill,rate:number,part?:string):LaundryFinalBill {
  return bill.parts?{...bill,parts:bill.parts.map(line=>line.delivery===part?{...line,rate}:line)}:{...bill,rate}
}

export function settleLaundry(rows:LaundryDelivery[],deliveryId:string,billNumber:string,action:Settlement) {
  const delivery=rows.find(row=>row.id===deliveryId)
  const bill=delivery?.finalBills?.find(row=>row.number===billNumber)
  if(!delivery||!bill)throw Error('Kontrabon asal tidak ditemukan.')
  const record=action.record
  const duplicate=[...(bill.payments??[]),...(bill.corrections??[]),...(bill.vendorUses??[])].find(row=>row.id===record.id)
  if(duplicate){if(JSON.stringify(duplicate)!==JSON.stringify(record))throw Error('Nomor tindakan sudah tercatat.');return rows}
  const latestCorrection=bill.corrections?.at(-1)
  if(!dayOk(record.day)||record.day<bill.day||record.day<(latestCorrection?.day??''))throw Error('Periksa tanggal kontrabon dan tindakan terakhir.')
  const accountExists=(name:string|undefined)=>cashAccounts.some(row=>row.name===name)
  const remaining=billRemaining(rows,delivery,bill)
  let next:LaundryFinalBill

  if(action.kind==='PAY'){
    const payment=action.record
    if(!Number.isSafeInteger(payment.cents)||payment.cents<=0||payment.cents>remaining||!accountExists(payment.account)||payment.reference.trim().length<3){
      throw Error('Periksa nominal sisa, rekening, dan bukti pembayaran.')
    }
    next={...bill,payments:[...(bill.payments??[]),payment]}
  } else if(action.kind==='CORRECT'){
    const correction=action.record
    const oldRate=bill.parts?bill.parts.find(line=>line.delivery===correction.part)?.rate:bill.rate
    const adjusted=laundryBillAtRate(bill,correction.rate,correction.part)
    const newGross=billGross(adjusted)
    if(oldRate===undefined||!Number.isSafeInteger(newGross)||correction.rate<0||correction.rate===oldRate||correction.previousRate!==oldRate||correction.reason.trim().length<4){
      throw Error('Isi tarif pengganti yang berbeda dan alasan koreksi.')
    }
    if(bill.payments?.some(row=>row.day>correction.day)||bill.vendorUses?.some(row=>row.day>correction.day))throw Error('Tanggal koreksi harus sesudah pembayaran dan pemakaian kredit terkait.')
    if(newGross<billCredit(bill)+vendorCreditApplied(rows,delivery.id,bill.number))throw Error('Nilai koreksi lebih kecil dari kredit yang sudah ditempel.')
    next={...adjusted,corrections:[...(bill.corrections??[]),correction]}
    if(vendorBalance(rows,delivery,next)<0)throw Error('Sebagian piutang vendor sudah diselesaikan. Periksa penyelesaian sebelum menaikkan tarif.')
  } else {
    const use=action.record
    const target=use.target?rows.find(row=>row.id===use.target?.delivery):undefined
    const targetBill=target?.finalBills?.find(row=>row.number===use.target?.bill)
    const balance=vendorBalance(rows,delivery,bill)
    if(!latestCorrection||!Number.isSafeInteger(use.cents)||use.cents<=0||use.cents>balance||use.reason.trim().length<4){
      throw Error('Isi nominal yang masih tersedia dan referensi penyelesaian.')
    }
    if(use.target){
      if(!target||!targetBill||targetBill===bill||target.vendor!==delivery.vendor||use.cents>billRemaining(rows,target,targetBill)
        ||use.day<targetBill.day||use.day<(targetBill.corrections?.at(-1)?.day??''))throw Error('Pilih tagihan terbuka vendor yang sama dan periksa batas potongan.')
    } else if(!accountExists(use.account))throw Error('Pilih rekening penerimaan pengembalian vendor.')
    next={...bill,vendorUses:[...(bill.vendorUses??[]),use]}
  }
  return rows.map(row=>row===delivery?{...row,finalBills:row.finalBills?.map(item=>item===bill?next:item)}:row)
}
