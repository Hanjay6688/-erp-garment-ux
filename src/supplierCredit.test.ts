import { describe, expect, it } from 'vitest'
import { creditAmount, creditCents, parseSupplierCredit } from './supplierCredit'
const fixture=()=>({supplier_id:'s',page:1,total:1,can_manage:true,suppliers:[{id:'s',code:'S',name:'Supplier'}],
 purchases:[{id:'p',number:'P',date:'2026-09-28',final_ap:'88.00',paid:'8.00',remaining:'80.00',credit_delta:'-12.00',payment_status:'PARTIAL'}],
 credits:[{return_id:'r',return_number:'R',supplier_id:'s',source_purchase_id:'origin',purchase_number:'O',credit:'20.00',original_purchase_credit:'8.00',version:'1',allocations:[{purchase_id:'p',amount:'12.00'}],events:[]}]})
describe('Supplier credit money and document balances',()=>{
 it('keeps cents exact beyond the JavaScript safe integer range',()=>{const text='99999999999999.99';expect(creditAmount(creditCents(text)!)).toBe(text);expect(creditCents('0.015')).toBeNull();expect(creditCents('-1')).toBeNull();expect(creditCents('NaN')).toBeNull()})
 it('accepts partial allocation while preserving the original purchase credit',()=>{expect(parseSupplierCredit(fixture()).credits[0].original_purchase_credit).toBe('8.00')})
 it('refuses doubled use of one credit and inconsistent AP',()=>{const duplicate=fixture();duplicate.credits[0].allocations.push({purchase_id:'p',amount:'12.00'});expect(()=>parseSupplierCredit(duplicate)).toThrow();const wrong=fixture();wrong.purchases[0].remaining='88.00';expect(()=>parseSupplierCredit(wrong)).toThrow();const over=fixture();over.credits[0].original_purchase_credit='20.00';expect(()=>parseSupplierCredit(over)).toThrow()})
})
