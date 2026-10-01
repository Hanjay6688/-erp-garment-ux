import operation from './nativeAnalysisStandin.json'
import {financeReportFixture} from './financeReport'
import {positionFields,performanceMoney,type FinanceReport} from '../../src/financeReportContract'
// Receiver-only inputs. They are never passed off as Native/Auth proof.
export function analysisFinanceFixture(blocked=false,preflight=false){
 const e=structuredClone(operation),a=e.analysis,hash='b'.repeat(64),as_of=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(a.snapshot.effective_as_of))
 const dates={from:e.query.from_date,to:e.query.through_date,as_of},report=financeReportFixture(dates,null,preflight)as unknown as FinanceReport
 report.captured_at=a.snapshot.effective_as_of
 if(blocked)Object.assign(report.snapshot.data_confidence,{status:'BLOCKED',critical_issue_count:'1',failed_checks:[{check_name:'TEST_SOURCE_COST',severity:'CRITICAL',issue_count:'1',details:'Biaya sumber belum diketahui'}],blockers:[{family:'COST',code:'UNKNOWN_COST',severity:'POLICY',scope:'AS_OF',impact_date:as_of,reference:null,reason:'Biaya sumber belum diketahui'}]})
 const refs=[{kind:'NATIVE_OWNER_FINANCIAL_REPORT',id:hash,revision:hash}],readiness=blocked?'BLOCKED':'READY'
 const fact=(value:string|null)=>value===null?{state:'UNKNOWN',unit:'IDR',reason:'SOURCE_INPUT_NOT_PROVEN',refs}:{state:'KNOWN',value,unit:'IDR',refs}
 const expected=[...performanceMoney.map(key=>({section:'performance',key,value:report.snapshot.performance[key],recorded:!['gross_profit','net_profit'].includes(key)})),...positionFields.map(key=>({section:'financial_position',key,value:report.snapshot.financial_position[key],recorded:['cash','customer_ar','supplier_final_ap','grni_estimated_liability'].includes(key)}))]
 const money=expected.map(m=>({metric_id:`NATIVE_FINANCE:${m.section}:${m.key}`,version:'accepted-owner-report-1',value:fact(!blocked||m.recorded?m.value:null),formula_ref:`${m.section==='performance'?report.snapshot.basis.performance_lifecycle_basis:'RECORDED_GL_BALANCES_AS_OF'}:${m.key}`,operands:[fact(m.value)],readiness,scope_kind:'GLOBAL',scope_key:'OWNER_FINANCIAL_REPORT',period_start:m.section==='performance'?dates.from:as_of,period_end:m.section==='performance'?dates.to:as_of,knowledge_mode:'CURRENT'}))
 Object.assign(a,{metrics:[...a.metrics,...money],financial_readiness:readiness,quality:{...a.quality,financial:blocked?'PARTIAL':'COMPLETE'},dependencies:[...a.dependencies,{domain:'native_owner_financial_report',source_hash:hash,revision:hash,fact_count:1,completeness:blocked?'PARTIAL':'COMPLETE'}]});a.snapshot.fact_count++
 return Object.assign(e,{financial_source:{contract_version:'cp7.native-analysis-finance.v1',dates,book_signature:'c'.repeat(64),source_hash:hash,report}})
}
