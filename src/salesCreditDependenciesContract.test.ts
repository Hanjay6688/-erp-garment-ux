import {describe,expect,it} from 'vitest'
import {parseSalesCreditDependencies,type CreditDependencySource,type SalesCreditDependencies} from './salesCreditDependenciesContract'

const id = (n: number) => `11111111-1111-4111-8111-${String(n).padStart(12,'0')}`
const source: CreditDependencySource = {id:id(1),number:'INV-1',status:'PAID',row_version:'9007199254740993',review_token:'a'.repeat(32)}
const actor = id(2)
const reply = (): SalesCreditDependencies => ({
  contract_version:'cp7.sales-credit-dependencies.v1',actor_scope_id:actor,read_at:'2026-10-21T09:00:00Z',read_only:true,business_DML:false,
  source:{sale_id:source.id,number:source.number,status:source.status,row_version:source.row_version,review_token:source.review_token!},
  dependency_sha256:'b'.repeat(64),page:{offset:0,limit:25,total:'1',next_offset:null},
  dependencies:[{event_id:id(3),kind:'REFUND',amount:'100.01',economic_date:'2026-10-20',book_date:'2026-10-21',
    source_sale_id:source.id,source_sale_number:'INV-1',source_return_id:id(4),source_return_number:'RET-1',target_sale:null,journal_id:id(5)}],
})

describe('authoritative credit dependency display',()=>{
  it('preserves exact cents, both dates and the actual source document',()=>{
    const r=reply();r.dependencies[0].amount='90071992547409931234567890.01'
    expect(parseSalesCreditDependencies(r,source,actor)).toEqual(r)
  })
  it('requires a complete authoritative empty result, never treats missing data as no blockers',()=>{
    const r=reply();r.dependencies=[];r.page.total='0'
    expect(parseSalesCreditDependencies(r,source,actor).dependencies).toEqual([])
    for(const bad of [null,{}, {...r,dependencies:null},{...r,page:{...r.page,total:null}}, {...r,read_only:false}, {...r,business_DML:true}])
      expect(()=>parseSalesCreditDependencies(bad,source,actor)).toThrow()
  })
  it('retires a response for another actor or parent revision, status, review or identity',()=>{
    for(const key of ['sale_id','number','status','row_version','review_token'] as const){
      const r=reply();r.source[key]='changed';expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
    }
    expect(()=>parseSalesCreditDependencies(reply(),source,id(99))).toThrow()
  })
  it('refuses missing rows, duplicate events and fake end-of-list',()=>{
    const r=reply();r.page.total='2';expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
    r.dependencies.push({...r.dependencies[0]});expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
    r.dependencies[1].event_id=id(6);r.page.next_offset=25;expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
  })
  it('validates a full page and its next offset, including exact totals beyond JS integer precision',()=>{
    const r=reply();r.dependencies=Array.from({length:25},(_,i)=>({...r.dependencies[0],event_id:id(i+10)}))
    r.page.total='9007199254740993';r.page.next_offset=25
    expect(parseSalesCreditDependencies(r,source,actor).page.total).toBe('9007199254740993')
    expect(()=>parseSalesCreditDependencies(r,source,actor,25)).toThrow()
    r.page.next_offset=null;expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
  })
  it('refuses impossible money/dates and an APPLY without the actual target invoice',()=>{
    for(const amount of ['0.00','-1.00','1.001','1e3','NaN']){const r=reply();r.dependencies[0].amount=amount;expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()}
    for(const dates of [['2026-02-30','2026-03-01'],['2026-10-21','2026-10-20']]){const r=reply();[r.dependencies[0].economic_date,r.dependencies[0].book_date]=dates;expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()}
    const r=reply();r.dependencies[0].kind='APPLY';expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
    r.dependencies[0].target_sale={id:id(7),number:'INV-TARGET'};expect(parseSalesCreditDependencies(r,source,actor).dependencies[0].target_sale?.number).toBe('INV-TARGET')
    r.dependencies[0].kind='REFUND';expect(()=>parseSalesCreditDependencies(r,source,actor)).toThrow()
  })
})
