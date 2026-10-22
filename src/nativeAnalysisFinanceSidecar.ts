import type {NativeDemandQuery} from './nativeDemandHistory'
import {parseStagedReference,stagedInstant,type StagedReference} from './nativeAnalysisPages'

export type AnalysisFinanceState='RUNNING'|'READY'|'FAILED'|'ACCESS_REVOKED'
export type AnalysisFinanceReadiness='READY'|'LIMITED'|'BLOCKED'
export type AnalysisFinanceFact={state:'KNOWN';value:string}|{state:'UNKNOWN';reason:string}
export type AnalysisFinanceMetric={id:string;value:AnalysisFinanceFact;periodStart:string;periodEnd:string}
export type AnalysisFinanceCapture={id:string;unitsDone:number;unitsTotal:number|null;reportReadAt:string|null;readiness:AnalysisFinanceReadiness|null;failureCode:string|null}
export type AnalysisFinanceResult={captureId:string;sourceHash:string;dates:{from:string;to:string;asOf:string};reportReadAt:string;readiness:AnalysisFinanceReadiness;metrics:AnalysisFinanceMetric[];warnings:string[]}
export type AnalysisFinance={requestId:string;jobId:string;query:NativeDemandQuery;reference:StagedReference;state:AnalysisFinanceState;capture:AnalysisFinanceCapture|null;result:AnalysisFinanceResult|null}
function fail():never{throw Error('Status keuangan analisis belum sesuai sumber laporan resmi.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const keys=(o:Record<string,unknown>,ks:readonly string[])=>{if(Object.keys(o).length!==ks.length||ks.some(k=>!Object.hasOwn(o,k)))fail()}
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const count=(v:unknown)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:fail()
const day=(v:unknown)=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return fail();const d=new Date(v+'T00:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===v?v:fail()}
const readiness=(v:unknown):AnalysisFinanceReadiness=>v==='READY'||v==='LIMITED'||v==='BLOCKED'?v:fail()
const query=(v:unknown):NativeDemandQuery=>{const q=obj(v);keys(q,['from_date','through_date','group_mode']);const from=day(q.from_date),to=day(q.through_date)
 if(from>to||q.group_mode!=='AS_SOLD'&&q.group_mode!=='RESTATED')fail();return{from_date:from,through_date:to,group_mode:q.group_mode}}
const sameQuery=(a:NativeDemandQuery,b:NativeDemandQuery)=>a.from_date===b.from_date&&a.through_date===b.through_date&&a.group_mode===b.group_mode
const sameReference=(a:StagedReference,b:StagedReference)=>a.sourceHash===b.sourceHash&&Date.parse(a.capturedAt)===Date.parse(b.capturedAt)
const wibDay=(v:string)=>{const p=new Map(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(v)).map(x=>[x.type,x.value]));return`${p.get('year')}-${p.get('month')}-${p.get('day')}`}
function datesOf(v:unknown,q:NativeDemandQuery,at:string){const d=obj(v);keys(d,['from','to','as_of']);const from=day(d.from),to=day(d.to),asOf=day(d.as_of)
 if(from!==q.from_date||to!==q.through_date||asOf!==wibDay(at)||to>asOf)fail();return{from,to,asOf}}
function fact(v:unknown,source:string):AnalysisFinanceFact{const f=obj(v)
 keys(f,f.state==='KNOWN'?['state','value','unit','refs']:['state','unit','reason','refs'])
 if(f.unit!=='IDR'||!Array.isArray(f.refs)||f.refs.length!==1)fail()
 const r=obj(f.refs[0]);keys(r,['kind','id','revision']);if(r.kind!=='NATIVE_OWNER_FINANCIAL_REPORT'||r.id!==source||r.revision!==source)fail()
 if(f.state==='KNOWN')return{state:'KNOWN',value:typeof f.value==='string'&&/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$/.test(f.value)?f.value:fail()}
 if(f.state!=='UNKNOWN'||f.reason!=='SOURCE_INPUT_NOT_PROVEN')fail();return{state:'UNKNOWN',reason:f.reason}}
function parseResult(v:unknown,c:AnalysisFinanceCapture,q:NativeDemandQuery,at:string):AnalysisFinanceResult{
 const r=obj(v);keys(r,['contract_version','capture_id','source_hash','dates','report_read_at','readiness','metrics','dependencies','warnings'])
 if(r.contract_version!=='cp7.analysis-finance-result.v1'||uuid(r.capture_id)!==c.id||!c.reportReadAt)fail()
 const sourceHash=hash(r.source_hash),dates=datesOf(r.dates,q,at),ready=readiness(r.readiness),reportReadAt=stagedInstant(r.report_read_at)
 if(ready!==c.readiness||Date.parse(reportReadAt)!==Date.parse(c.reportReadAt)||!Array.isArray(r.metrics)||r.metrics.length===0)fail()
 const ids=new Set<string>(),metrics:AnalysisFinanceMetric[]=r.metrics.map(raw=>{
  const m=obj(raw);keys(m,['metric_id','version','value','formula_ref','operands','readiness','scope_kind','scope_key','period_start','period_end','knowledge_mode'])
  const id=text(m.metric_id),match=/^NATIVE_FINANCE:(performance|financial_position):([a-z][a-z0-9_]*)$/.exec(id)
  if(!match||ids.has(id)||m.version!=='accepted-owner-report-1'||m.scope_kind!=='GLOBAL'||m.scope_key!=='OWNER_FINANCIAL_REPORT'||m.knowledge_mode!=='CURRENT'||m.readiness!==ready)fail()
  ids.add(id);text(m.formula_ref)
  const periodStart=day(m.period_start),periodEnd=day(m.period_end),performance=match[1]==='performance'
  if(periodStart!==(performance?dates.from:dates.asOf)||periodEnd!==(performance?dates.to:dates.asOf)||!Array.isArray(m.operands)||m.operands.length!==1)fail()
  const value=fact(m.value,sourceHash),operand=fact(m.operands[0],sourceHash)
  if(operand.state!=='KNOWN'||value.state==='KNOWN'&&value.value!==operand.value||ready==='READY'&&value.state!=='KNOWN')fail()
  return{id,value,periodStart,periodEnd}
 })
 if(!Array.isArray(r.dependencies)||r.dependencies.length!==1)fail()
 const d=obj(r.dependencies[0]);keys(d,['domain','revision','source_hash','fact_count','completeness'])
 if(d.domain!=='native_owner_financial_report'||d.revision!==sourceHash||d.source_hash!==sourceHash||d.fact_count!==1||d.completeness!==(ready==='READY'?'COMPLETE':'PARTIAL'))fail()
 if(!Array.isArray(r.warnings)||r.warnings.some(w=>typeof w!=='string'||!/^NATIVE_FINANCIAL_READINESS:[A-Z_]+$/.test(w))||ready==='READY'&&r.warnings.length!==0)fail()
 return{captureId:c.id,sourceHash,dates,reportReadAt,readiness:ready,metrics,warnings:r.warnings as string[]}
}
export function parseAnalysisFinance(v:unknown,context:{requestId:string;reference:StagedReference;query?:NativeDemandQuery}):AnalysisFinance{
 const r=obj(v);keys(r,['contract_version','request_id','job_id','query','reference','state','capture','result','production_go'])
 if(r.contract_version!=='cp7.analysis-finance-sidecar.v1'||r.production_go!==false||uuid(r.request_id)!==context.requestId)fail()
 const jobId=uuid(r.job_id),q=query(r.query),reference=parseStagedReference(r.reference)
 if(!sameReference(reference,context.reference)||context.query&&!sameQuery(q,context.query))fail()
 const state=r.state;if(state!=='RUNNING'&&state!=='READY'&&state!=='FAILED'&&state!=='ACCESS_REVOKED')fail()
 if(state==='ACCESS_REVOKED'){if(r.capture!==null||r.result!==null)fail();return{requestId:context.requestId,jobId,query:q,reference,state,capture:null,result:null}}
 const s=obj(r.capture);keys(s,['contract_version','capture_id','owner_kind','owner_id','state','units_done','units_total','report_read_at','dates','readiness','failure_code','production_go'])
 if(s.contract_version!=='cp7.finance-capture-status.v1'||s.owner_kind!=='STAGED_ANALYSIS'||uuid(s.owner_id)!==jobId||s.state!==state||s.production_go!==false)fail()
 datesOf(s.dates,q,reference.capturedAt)
 const c:AnalysisFinanceCapture={id:uuid(s.capture_id),unitsDone:count(s.units_done),unitsTotal:s.units_total===null?null:count(s.units_total),reportReadAt:s.report_read_at===null?null:stagedInstant(s.report_read_at),
  readiness:s.readiness===null?null:readiness(s.readiness),failureCode:s.failure_code===null?null:typeof s.failure_code==='string'&&/^CP7_[A-Z0-9_]+$/.test(s.failure_code)?s.failure_code:fail()}
 if(c.unitsTotal!==null&&c.unitsDone>c.unitsTotal||(state==='FAILED')!==(c.failureCode!==null)||state==='READY'&&(c.unitsTotal===null||c.unitsDone!==c.unitsTotal||c.reportReadAt===null||c.readiness===null))fail()
 const result=state==='READY'?parseResult(r.result,c,q,reference.capturedAt):r.result===null?null:fail()
 return{requestId:context.requestId,jobId,query:q,reference,state,capture:c,result}
}
export const financeFiguresVisible=(r:AnalysisFinance|null,allowed:boolean)=>allowed&&r?.state==='READY'&&r.result?.readiness==='READY'
