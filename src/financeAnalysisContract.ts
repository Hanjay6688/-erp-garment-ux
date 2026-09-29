import {financeDate,parseFinanceSnapshot,type FinanceDates,type FinanceReport} from './financeReportContract'
export type AnalysisDates=FinanceDates&{compare_from:string;compare_to:string}
export type CashEntry={id:string;journal_number:string;source_type:string;source_id:string|null;reversal_of_id:string|null;status:'POSTED'|'REVERSED';economic_date:string;transaction_date:string;posting_at:string;debit:string;credit:string;net:string}
export type FinanceAnalysis={contract_version:'cp7.finance-analysis.v1';captured_at:string;knowledge_basis:'CURRENT_RECORDED_KNOWLEDGE';historical_knowledge:'NOT_RECONSTRUCTED';dates:AnalysisDates;comparison:{basis:'NATIVE_OWNER_REPORT_OPERANDS';formula_version:'GROWTH_BASELINE_AND_GROSS_MARGIN_PP_V1';rounding_scale:4;current:FinanceReport['snapshot'];baseline:FinanceReport['snapshot'];revenue_growth_pct:string|null;gross_margin_change_pp:string|null};cash:{basis:'GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA';account_scope:'DISTINCT_COA_INCLUDING_INACTIVE_CASH_ACCOUNTS_AND_CASH_MAPPING';opening:string;closing:string;debit:string;credit:string;net_change:string;ledger_net:string;source_difference:string;reconciled:boolean;entries:{rows:CashEntry[];total:string;offset:number;limit:25;next_offset:number|null}}}
const fail=():never=>{throw Error('Perbandingan atau arus kas belum lengkap. Muat ulang dengan tanggal yang sama.')}
const text=(v:unknown):v is string=>typeof v==='string'
const decimal=(v:unknown,scale=2):v is string=>text(v)&&new RegExp(`^-?(0|[1-9][0-9]{0,40})(\\.[0-9]{1,${scale}})?$`).test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,20})$/.test(v)
const uuid=(v:unknown)=>text(v)&&/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(v)
const timestamp=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}T/.test(v)&&Number.isFinite(Date.parse(v))
function closed(value:unknown,keys:string[]){if(!value||typeof value!=='object'||Array.isArray(value))return fail();const r=value as Record<string,unknown>;if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
function cents(v:unknown){if(!decimal(v))return fail();const negative=v.startsWith('-'),[a,b='']=v.replace(/^-/,'').split('.');return BigInt(a+b.padEnd(2,'0'))*(negative?-1n:1n)}
export function parseFinanceAnalysis(value:unknown,dates:AnalysisDates,offset=0):FinanceAnalysis{
 const r=closed(value,['contract_version','captured_at','knowledge_basis','historical_knowledge','dates','comparison','cash'])
 if(r.contract_version!=='cp7.finance-analysis.v1'||!timestamp(r.captured_at)||r.knowledge_basis!=='CURRENT_RECORDED_KNOWLEDGE'||r.historical_knowledge!=='NOT_RECONSTRUCTED')fail()
 const d=closed(r.dates,['from','to','as_of','compare_from','compare_to']);if(Object.entries(dates).some(([k,v])=>!financeDate(v)||d[k]!==v)||dates.from>dates.to||dates.to>dates.as_of||dates.compare_from>dates.compare_to||dates.compare_to>=dates.from)fail()
 const c=closed(r.comparison,['basis','formula_version','rounding_scale','current','baseline','revenue_growth_pct','gross_margin_change_pp'])
 if(c.basis!=='NATIVE_OWNER_REPORT_OPERANDS'||c.formula_version!=='GROWTH_BASELINE_AND_GROSS_MARGIN_PP_V1'||c.rounding_scale!==4)fail()
 const current=parseFinanceSnapshot(c.current,dates),baseline=parseFinanceSnapshot(c.baseline,{from:dates.compare_from,to:dates.compare_to,as_of:dates.compare_to})
 if(![c.revenue_growth_pct,c.gross_margin_change_pp].every(x=>x===null||decimal(x,4)))fail()
 if((c.revenue_growth_pct===null)!==(cents(baseline.performance.sales_revenue_gl)===0n)||(c.gross_margin_change_pp===null)!==(cents(baseline.performance.sales_revenue_gl)===0n||cents(current.performance.sales_revenue_gl)===0n))fail()
 const cash=closed(r.cash,['basis','account_scope','opening','closing','debit','credit','net_change','ledger_net','source_difference','reconciled','entries'])
 if(cash.basis!=='GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA'||cash.account_scope!=='DISTINCT_COA_INCLUDING_INACTIVE_CASH_ACCOUNTS_AND_CASH_MAPPING'||typeof cash.reconciled!=='boolean')fail()
 for(const k of ['opening','closing','debit','credit','net_change','ledger_net','source_difference'])if(!decimal(cash[k]))fail()
 if(cents(cash.debit)<0n||cents(cash.credit)<0n||cents(cash.net_change)!==cents(cash.closing)-cents(cash.opening)||cents(cash.ledger_net)!==cents(cash.debit)-cents(cash.credit)||cents(cash.source_difference)!==cents(cash.net_change)-cents(cash.ledger_net)||cash.reconciled!==(cents(cash.source_difference)===0n))fail()
 const page=closed(cash.entries,['rows','total','offset','limit','next_offset']);if(!Array.isArray(page.rows)||page.rows.length>25||!whole(page.total)||page.offset!==offset||page.limit!==25)return fail()
 const end=BigInt(offset+page.rows.length),total=BigInt(page.total);if(page.rows.length&&end>total||end<total&&(!page.rows.length||page.next_offset!==Number(end))||end>=total&&page.next_offset!==null)fail()
 const ids=new Set();for(const value of page.rows){const e=closed(value,['id','journal_number','source_type','source_id','reversal_of_id','status','economic_date','transaction_date','posting_at','debit','credit','net']);if(!uuid(e.id)||ids.has(e.id)||!text(e.journal_number)||!text(e.source_type)||e.source_id!==null&&!uuid(e.source_id)||e.reversal_of_id!==null&&!uuid(e.reversal_of_id)||!['POSTED','REVERSED'].includes(String(e.status))||!financeDate(e.economic_date)||!financeDate(e.transaction_date)||String(e.transaction_date)<dates.from||String(e.transaction_date)>dates.to||!timestamp(e.posting_at)||cents(e.debit)<0n||cents(e.credit)<0n||cents(e.net)!==cents(e.debit)-cents(e.credit))fail();ids.add(e.id)}
 return r as unknown as FinanceAnalysis
}
