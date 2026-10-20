// Usage: node read_fault_schedule_recheck.mjs SOURCE_BROWSER_CASES OUTPUT_JSON
// Executes only a copied test clause with synthetic locators/events. No product,
// Playwright browser, Auth, HTTP, or database is started or imported.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {createHash} from 'node:crypto'
assert.equal(process.argv.length,4,'Usage: node read_fault_schedule_recheck.mjs SOURCE_BROWSER_CASES OUTPUT_JSON')
const sourcePath=resolve(process.argv[2]),outputPath=resolve(process.argv[3])
const source=readFileSync(sourcePath,'utf8')
const begin=source.indexOf('let abortedReads=0')
const endNeedle="assert.equal(fresh.detail.financial.open_balance,'0.00')"
const end=source.indexOf(endNeedle,begin)+endNeedle.length
assert.ok(begin>=0&&end>=begin,'Fixed read-fault clause markers required')
const clause=source.slice(begin,end)
const expected=[
 {schedule:'read_deferred_beyond_fault_observation',expected:'REFUSE'},
 {schedule:'requestfailed_event_without_abort_handler',expected:'REFUSE'},
 {schedule:'actual_abort_event_settled_error_then_verified_reload',expected:'COMPLETE'},
]
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor
const run=new AsyncFunction('assert','page','ui','readEndpoint','observed','reconcile','envelope','create','detail','first','otherButtons','f',clause)
const result=[]
for(const literal of expected){
 const trace=[];let handler,failedPredicate,resolveFailed,rejectFailed,resolveFresh,freshPredicate
 let abortedReads=0,eventObserved=false,faultRemoved=false
 const first={row_version:'2'},f={invoice:{id:'synthetic-source-sale'}},readEndpoint='synthetic-read-endpoint'
 const request={url:()=>'/rpc/erp_cp7_get_sales_v1',postDataJSON:()=>({p_query:{sale_id:f.invoice.id}})}
 const fakePage={
  waitForEvent:(name,options)=>{assert.equal(name,'requestfailed');failedPredicate=options.predicate;return new Promise((ok,no)=>{resolveFailed=ok;rejectFailed=no})},
  route:async(_p,fn)=>{handler=fn;trace.push('fault_registered')},
  unroute:async()=>{handler=undefined;faultRemoved=true;trace.push('fault_removed')},
  waitForResponse:predicate=>{freshPredicate=predicate;return new Promise(ok=>{resolveFresh=ok})},
  getByText:text=>({visible:abortedReads>0&&eventObserved,text}),
  getByRole:()=>({click:async()=>{
   assert.equal(faultRemoved,true);trace.push('explicit_reload_clicked')
   const response={url:request.url,request:()=>request,status:()=>200,json:async()=>({detail:{row_version:first.row_version,financial:{paid_total:'800.00',open_balance:'0.00'}}})}
   assert.equal(freshPredicate(response),true);resolveFresh(response)
  }}),
 }
 const observed=async()=>{
  if(literal.schedule==='actual_abort_event_settled_error_then_verified_reload'){
   assert.ok(handler);await handler({abort:async()=>{abortedReads++;trace.push('abort_handler_called');assert.equal(failedPredicate(request),true);eventObserved=true;resolveFailed(request)}})
  }else if(literal.schedule==='requestfailed_event_without_abort_handler'){
   assert.equal(failedPredicate(request),true);eventObserved=true;resolveFailed(request);trace.push('foreign_failure_event_without_handler')
  }else setImmediate(()=>{trace.push('no_failed_read_observed');rejectFailed(new Error('SYNTHETIC_REQUESTFAILED_TIMEOUT'))})
  return {status:()=>200,json:async()=>first}
 }
 const expect=actual=>({toBeVisible:async()=>assert.equal(actual.visible,true),toBeDisabled:async()=>assert.equal(actual.disabled,true),toHaveCount:async n=>assert.equal(actual.count,n)})
 expect.poll=fn=>({toHaveLength:async n=>assert.equal((await fn()).length,n)})
 let observedVerdict,error
 try{await run(assert,fakePage,{expect},readEndpoint,observed,()=>({}),async()=>[],()=>({disabled:true}),()=>({count:0}),first,{all:async()=>[{disabled:true}]},f);observedVerdict='COMPLETE'}
 catch(e){observedVerdict='REFUSE';error=String(e.message)}
 result.push({...literal,observed:observedVerdict,agrees:literal.expected===observedVerdict,actual_abort_handler_calls:abortedReads,failed_event_observed:eventObserved,fault_removed:faultRemoved,trace,...(error?{error}:{})})
}
const expression=source.match(/document\.documentElement\.scrollWidth<=innerWidth(?:\+\d+)?/)?.[0]
assert.ok(expression)
const widthExpected=[{scroll:390,viewport:390,expected:true},{scroll:391,viewport:390,expected:false}]
const widths=widthExpected.map(v=>({...v,observed:new Function('document','innerWidth','return '+expression)({documentElement:{scrollWidth:v.scroll}},v.viewport)}))
assert.ok(result.every(v=>v.agrees));assert.ok(widths.every(v=>v.observed===v.expected))
const report={classification:'PURE_SYNTHETIC_FIXED_TEST_CLAUSE_RECHECK_NOT_BROWSER_OR_PRODUCT_RUNTIME',source:sourcePath,source_sha256:createHash('sha256').update(source).digest('hex'),clause_sha256:createHash('sha256').update(clause).digest('hex'),expected_before_execution:expected,results:result,width_expression:expression,widths,all_expected_controls_satisfied:true}
mkdirSync(dirname(outputPath),{recursive:true});writeFileSync(outputPath,JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report))
