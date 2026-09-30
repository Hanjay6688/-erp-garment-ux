import{expect,it}from 'vitest'
import{installmentCents,parseInstallmentRead,parseInstallmentOutcome,validInstallmentAmount}from './payrollInstallmentContract'
import{installmentRead,installmentPayment,payrollId,paymentId,cashId}from '../tests/fixtures/payrollInstallments'
it('keeps exact cents and source versions above JavaScript safe integer range',()=>{
 const r=installmentRead('0.00',[],'9007199254740993.01');expect(parseInstallmentRead(r,payrollId).document.approved_net).toBe('9007199254740993.01');expect(installmentCents('9007199254740993.01')).toBe(900719925474099301n);expect(validInstallmentAmount('9007199254740993.01','9007199254740993.01')).toBe(true);expect(validInstallmentAmount('9007199254740993.02','9007199254740993.01')).toBe(false)
})
it('requires native paid600/remaining400 and rejects client-like numeric or invented totals',()=>{
 const r=installmentRead('600.00',[installmentPayment()]);expect(parseInstallmentRead(r,payrollId).document.remaining_amount).toBe('400.00')
 for(const patch of[{remaining_amount:'399.99'},{paid_amount:600},{approved_net:1000},{paid_amount:'1000.01'},{native_status:'PAID'},{payment_state:'READY'},{managed:false},{row_version:'9223372036854775808'}])expect(()=>parseInstallmentRead({...r,document:{...r.document,...patch}},payrollId)).toThrow()
})
it('retains original and linked inverse dates and does not count reversed cash as paid',()=>{
 const r=installmentRead('0.00',[installmentPayment('600.00',true)]);expect(parseInstallmentRead(r,payrollId).payments.rows[0].reversal_accounting_date).toBe('2020-01-03');expect(r.document.remaining_amount).toBe('1000.00')
 for(const patch of[{reversal_journal_id:null},{status:'POSTED'},{reversal_journal_id:r.payments.rows[0].journal_id},{payment_date:'2020-02-30'},{economic_date:'2020-01-03'}])expect(()=>parseInstallmentRead({...r,payments:{...r.payments,rows:[{...r.payments.rows[0],...patch}]}},payrollId)).toThrow()
})
it('full totals stay native on both25+5 pages rather than becoming page subtotals',()=>{
 const all=Array.from({length:30},(_,i)=>({...installmentPayment('1.23'),id:`${String(i+1).padStart(8,'0')}-3333-4333-8333-333333333333`,journal_id:`${String(i+1).padStart(8,'0')}-4444-4444-8444-444444444444`})),r=installmentRead('36.90',all);r.document.remaining_amount='963.10'
 for(const offset of[0,25]){const p={...r,payments:{rows:all.slice(offset,offset+25),total:'30',offset,limit:25,next_offset:offset===0?25:null}};expect(parseInstallmentRead(p,payrollId).document.remaining_amount).toBe('963.10')}
 expect(()=>parseInstallmentRead({...r,payments:{...r.payments,rows:all.slice(0,25),next_offset:null}},payrollId)).toThrow()
})
it('refuses duplicate source IDs, ineligible cash, missing private-source facts and another selected payroll',()=>{
 const r=installmentRead();expect(()=>parseInstallmentRead(r,cashId)).toThrow();expect(()=>parseInstallmentRead({...r,cash_accounts:{...r.cash_accounts,rows:[{...r.cash_accounts.rows[0],eligible:false}]}},payrollId)).toThrow();expect(()=>parseInstallmentRead({...r,document:{...r.document,remaining_amount:null}},payrollId)).toThrow();const p=installmentRead('600.00',[installmentPayment(),installmentPayment()]);p.payments.total='2';expect(()=>parseInstallmentRead(p,payrollId)).toThrow()
})
it('a reversed payroll has explicit inactive balance rather than unpaid approved net',()=>{
 const r=installmentRead('0.00',[installmentPayment('600.00',true)]);r.document.native_status='REVERSED';r.document.payment_state='REVERSED';r.document.remaining_amount=null;expect(parseInstallmentRead(r,payrollId).document.remaining_amount).toBeNull();expect(()=>parseInstallmentRead({...r,document:{...r.document,remaining_amount:'1000.00'}},payrollId)).toThrow()
})
it('accepts an exact committed intent independent of JSON key order and rejects changed UUID/payload/version/action',()=>{
 const d={payroll_id:payrollId,review_token:'a'.repeat(32),amount:'600.00',payment_date:'2020-01-02',cash_account_id:cashId,cash_review_token:'b'.repeat(32),change_reason:'Source reviewed'},p={document:d,expected_version:'9007199254740993'},r={contract_version:'cp7.payroll-installment-outcome.v1',kind:'COMMITTED_OUTCOME',action:'PAY',request_id:paymentId,request_payload:Object.fromEntries(Object.entries(d).reverse()),expected_version:p.expected_version,payroll_id:payrollId,payment_id:paymentId,native_status:'APPROVED',payment_state:'PARTIAL',row_version:'9007199254740994',review_token:'c'.repeat(32)}
 expect(parseInstallmentOutcome(r,paymentId,'PAY',p).payment_id).toBe(paymentId)
 for(const patch of[{request_id:cashId},{payroll_id:cashId},{expected_version:'9007199254740992'},{request_payload:{...d,amount:'400.00'}},{native_status:'REVERSED'},{payment_state:'UNPAID'}])expect(()=>parseInstallmentOutcome({...r,...patch},paymentId,'PAY',p)).toThrow()
 expect(()=>parseInstallmentOutcome(r,paymentId,'REVERSE_PAYMENT',p)).toThrow()
})
it('refuses non-canonical cash amounts including zero, negative, float syntax, excess precision and overpayment',()=>{for(const amount of['0','-1','01','1e2','NaN','Infinity','1.001','1000.01','9999999999999999999.99'])expect(validInstallmentAmount(amount,'1000.00')).toBe(false)})
