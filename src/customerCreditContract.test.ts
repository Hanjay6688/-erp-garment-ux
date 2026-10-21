import {describe,expect,it} from 'vitest'
import {creditAmountInput,creditCents,creditNowInput,creditPhysicalInput,creditQuery,parseCreditOutcome,parseCreditPayload,parseCreditRecovery,parseCreditReview,parseCreditWorkspace} from './customerCreditContract'
import {creditActor,creditBank,creditEvent,creditId,creditOutcome,creditPayload,creditReview,creditSale,creditSource,creditTarget,creditTargetRow,creditWorkspace} from '../tests/fixtures/customerCredit'

describe('bounded credit client contracts, not database qualification',()=>{
  it('keeps cents and versions beyond Number precision exact',()=>{
    expect(creditAmountInput('9007199254740993,01')).toBe('9007199254740993.01')
    expect(creditCents('9007199254740993.01')).toBe(900719925474099301n)
    for(const raw of ['0','-1','1e2','NaN','1.001','01.00'])expect(creditAmountInput(raw)).toBeNull()
    const p=creditPayload(),review=creditReview(p),recovery={document:{...p,quote_sha256:review.quote_sha256},review}
    expect(parseCreditOutcome(creditOutcome(creditId(60),review),creditId(60),recovery).invoice_versions[creditSale]).toBe('9007199254740994')
  })
  it('requires an explicit WIB instant and compares every microsecond',()=>{
    expect(creditPhysicalInput('')).toBeNull();expect(creditPhysicalInput('2026-02-30T10:00')).toBeNull()
    expect(creditPhysicalInput('2026-10-20T10:00:00.123456')).toBe('2026-10-20T10:00:00.123456+07:00')
    expect(creditNowInput(new Date('2026-10-20T03:04:05.678Z'))).toBe('2026-10-20T10:04:05.678')
    const p=creditPayload(),q=creditReview(p)
    expect(parseCreditReview(q,p)).toEqual(q)
    expect(()=>parseCreditReview({...q,physical_at:q.physical_at.replace('123456','123457')},p)).toThrow()
    expect(()=>parseCreditPayload({...p,physical_at:''})).toThrow()
  })
  it.each(['APPLY','REFUND','UNDO']as const)('binds %s review, exact saved envelope and committed receipt',action=>{
    const p=creditPayload(action),review=creditReview(p),recovery={document:{...p,quote_sha256:review.quote_sha256},review},request=creditId(60)
    expect(parseCreditReview(review,p,{source:creditSource(),original:creditEvent(),target:creditTargetRow})).toEqual(review)
    expect(parseCreditRecovery(recovery,`CREDIT_${action}`)).toEqual(recovery)
    const outcome=creditOutcome(request,review)
    expect(parseCreditOutcome(outcome,request,recovery)).toEqual(outcome)
    for(const change of [{request_id:creditId(61)},{amount:'1.00'},{cash_account_id:creditId(62)},{available_credit:'999.00'},
      {physical_at:'2026-10-20T03:00:00.123457Z'},{invoice_versions:{...outcome.invoice_versions,[creditSale]:'9007199254740993'}}]) {
      expect(()=>parseCreditOutcome({...outcome,...change},request,recovery)).toThrow()
    }
  })
  it('UNDO names the full positive original and never accepts a typed amount, bank or cohort',()=>{
    const p=creditPayload('UNDO'),original=creditEvent('REFUND','200.00'),q=creditReview(p,original)
    expect(parseCreditReview(q,p,{source:creditSource(),original})).toEqual(q)
    for(const change of [{amount:'80.00'},{amount:'-80.00'},{cohort_id:creditId(10)},{cash_account_id:creditBank.id},{target_sale_id:creditTarget}])expect(()=>parseCreditPayload({...p,...change})).toThrow()
    expect(()=>parseCreditReview(q,p,{source:creditSource(),original:{...original,undone_by:creditId(63)}})).toThrow()
    expect(()=>parseCreditReview({...q,selection:{...q.selection,amount:'-80.00'}},p,{source:creditSource(),original})).toThrow()
  })
  it('refuses a crossed actor, source, target customer, query, page receipt or non-boolean capability',()=>{
    const source=creditSource(),query=creditQuery('TARGETS',source),data=creditWorkspace('TARGETS')
    expect(parseCreditWorkspace(data,query,source,creditActor)).toEqual(data)
    for(const change of [{actor_scope_id:creditId(70)},{business_DML:true},{q:'other'},{source:{...data.source,row_version:'2'}},
      {capabilities:{...data.capabilities,apply:'yes'}},{page:{...data.page,rows:[{...creditTargetRow,customer_id:creditId(71)}]}}])expect(()=>parseCreditWorkspace({...data,...change},query,source,creditActor)).toThrow()
  })
  it('requires the original all-row fingerprint on subsequent pages and detects duplicates/incomplete results',()=>{
    const source=creditSource(),data=creditWorkspace('COHORTS'),query=creditQuery('COHORTS',source)
    expect(()=>creditQuery('COHORTS',source,'',25)).toThrow()
    const next=creditQuery('COHORTS',source,'',25,data.dataset_sha256)
    expect(()=>parseCreditWorkspace({...data,dataset_sha256:'d'.repeat(64),page:{...data.page,offset:25,total:'26'}},next,source,creditActor)).toThrow()
    expect(()=>parseCreditWorkspace({...data,page:{...data.page,total:'2',rows:[data.page.rows[0],data.page.rows[0]]}},query,source,creditActor)).toThrow()
    expect(()=>parseCreditWorkspace({...data,page:{...data.page,total:'2'}},query,source,creditActor)).toThrow()
  })
})
