import {financeReportFixture} from './financeReport'
import type {AnalysisDates,CashEntryList} from '../../src/financeAnalysisContract'
const cents=(v:string)=>{const [a,b='']=v.replace(/^-/,'').split('.');return BigInt(a+b.padEnd(2,'0'))*(v.startsWith('-')?-1n:1n)}
const text=(c:bigint)=>`${c<0n?'-':''}${(c<0n?-c:c)/100n}.${String((c<0n?-c:c)%100n).padStart(2,'0')}`
/** OW-09: an unfiltered whole-period list echo; the sums equal the period debit and credit. */
export function withEntryList<T extends {cash:{debit:string;credit:string;entries:object}}>(r:T,query:Partial<CashEntryList>):T{
 if(!('entry_q' in query||'entry_status' in query||'entry_order' in query))return r
 Object.assign(r.cash.entries,{list:{q:query.entry_q??'',status:query.entry_status??null,order:query.entry_order??'SOURCE'},sums:{debit:r.cash.debit,credit:r.cash.credit,net:text(cents(r.cash.debit)-cents(r.cash.credit))}})
 return r
}
export function financeAnalysisFixture(dates:AnalysisDates&Partial<CashEntryList>,offset=0){
 const current=financeReportFixture(dates).snapshot,baseline=financeReportFixture({from:dates.compare_from,to:dates.compare_to,as_of:dates.compare_to}).snapshot
 Object.assign(current.performance,{sales_revenue_gl:'1200.00',cogs_gl:'912.00',gross_profit:'288.00',net_profit:'288.00',gross_margin_pct:'24.0000'})
 Object.assign(baseline.performance,{sales_revenue_gl:'1000.00',cogs_gl:'730.00',gross_profit:'270.00',net_profit:'270.00',gross_margin_pct:'27.0000'})
 const ids=['11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222','33333333-3333-4333-8333-333333333333']
 const rows=ids.map((id,i)=>({id,journal_number:'JRN-'+i,source_type:['TRANSFER','SALES_PAYMENT','SUPPLIER_PAYMENT'][i],source_id:null,reversal_of_id:null,status:'POSTED',economic_date:dates.from,transaction_date:dates.from,posting_at:dates.from+'T03:00:00Z',debit:['1000.00','300.00','0.00'][i],credit:['1000.00','0.00','200.00'][i],net:['0.00','300.00','-200.00'][i]}))
 return withEntryList({contract_version:'cp7.finance-analysis.v1',captured_at:'2026-09-29T03:00:00Z',knowledge_basis:'CURRENT_RECORDED_KNOWLEDGE',historical_knowledge:'NOT_RECONSTRUCTED',dates:{from:dates.from,to:dates.to,as_of:dates.as_of,compare_from:dates.compare_from,compare_to:dates.compare_to},comparison:{basis:'NATIVE_OWNER_REPORT_OPERANDS',formula_version:'GROWTH_POSITIVE_BASE_AND_GROSS_MARGIN_PP_V2',rounding_scale:4,current,baseline,revenue_growth_pct:'20.0000' as string|null,gross_margin_change_pp:'-3.0000' as string|null},cash:{basis:'GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA',account_scope:'DISTINCT_COA_INCLUDING_INACTIVE_CASH_ACCOUNTS_AND_CASH_MAPPING',opening:'1000.00',closing:'1100.00',debit:'1300.00',credit:'1200.00',net_change:'100.00',ledger_net:'100.00',source_difference:'0.00',reconciled:true,entries:{rows:offset===0?rows:[],total:'3',offset,limit:25,next_offset:null}}},dates)
}
