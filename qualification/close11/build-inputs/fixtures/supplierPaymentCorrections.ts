// Synthetic component/parser data only; Native23 has its own actual fixtures.
import {supplierPaymentFixture,supplierPaymentReadFixture}from'./supplierPayments'
import type {SupplierPaymentCorrectionRead,SupplierPaymentCorrectionLink}from'../../src/supplierPaymentCorrectionContract'
import type {Json}from'../../src/types/database.preconnect'
export const replacementId='b2000000-0000-4000-8000-000000000027'
export function supplierCorrectionFixture():SupplierPaymentCorrectionRead{
 const source=supplierPaymentReadFixture(),payment=supplierPaymentFixture()
 return{contract_version:'cp7.supplier-payment-correction-workspace.v1',captured_at:source.captured_at,purchase_id:source.purchase.id,Native_AP:source.Native_AP,document:payment,can_correct:true,eligible:true,previous:null,next:null,cash_accounts:{rows:[{id:payment.cash_account_id!,code:payment.cash_code!,name:payment.cash_name!,kind:'BANK'}],total:'1',offset:0,limit:25,next_offset:null}}
}
export function supplierCorrectionLink(request:string,reason:string):SupplierPaymentCorrectionLink{
 const p=supplierPaymentFixture(),source=supplierPaymentReadFixture()
 return{original_id:p.id,replacement_id:replacementId,purchase_id:source.purchase.id,actor_scope_id:'a1000000-0000-4000-8000-000000000099',request_id:request,reason,recorded_at:source.captured_at,time_restatement:null}
}
export function supplierCorrectionOutcome(request:string,payload:Json){
 const p=payload as {purchase_id:string;payment_id:string;change_reason:string}
 return{contract_version:'cp7.supplier-payment-correction.v1',kind:'COMMITTED_OUTCOME',action:'CORRECT',request_id:request,request_payload:payload,purchase_id:p.purchase_id,original_payment_id:p.payment_id,payment_id:replacementId,original_status:'REVERSED',status:'POSTED',link:supplierCorrectionLink(request,p.change_reason)}
}
