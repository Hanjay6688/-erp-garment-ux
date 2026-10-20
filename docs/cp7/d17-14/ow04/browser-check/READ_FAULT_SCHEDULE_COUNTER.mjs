// Pure synthetic schedule over the actual read-fault test clause. No browser,
// database, Auth, HTTP, or product function executes in this counter.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const sourcePath='/workspace/scratch/9442228ed2dc/ow04-proposals/browser/BEFORE_IMPLEMENTATION_browser_cases.mjs'
const source=readFileSync(sourcePath,'utf8')
const begin=source.indexOf("await page.route(readEndpoint,route=>route.abort('failed'))")
const endNeedle="await page.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()"
const end=source.indexOf(endNeedle,begin)+endNeedle.length
assert.ok(begin>=0&&end>=begin)
const clause=source.slice(begin,end)
const expected=[{schedule:'read_request_deferred_until_fault_is_removed',expected:'REFUSE_UNOBSERVED_READ_FAILURE'},
 {schedule:'read_request_already_failed_before_state_checks',expected:'CLAUSE_COMPLETES'}]
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor
const run=new AsyncFunction('assert','page','ui','readEndpoint','observed','reconcile','envelope','create','detail','first',clause)
const results=[]
for(const literal of expected){
 let handler,abortedReads=0,readStarted=false;const trace=[]
 const first={kind:'SYNTHETIC_COMMITTED_RESULT'}
 const reader=async()=>{readStarted=true;trace.push(handler?'read_under_fault':'read_after_fault_removed');if(handler)await handler({abort:async()=>{abortedReads++;trace.push('actual_abort_handler_called')}})}
 const page={route:async(_p,fn)=>{handler=fn;trace.push('fault_registered')},unroute:async()=>{handler=undefined;trace.push('fault_removed');if(!readStarted)await reader()},getByRole:()=>({click:async()=>trace.push('explicit_reload_clicked')})}
 const observed=async()=>{if(literal.schedule==='read_request_already_failed_before_state_checks')await reader();return{status:()=>200,json:async()=>first}}
 const expect=actual=>({toBeDisabled:async()=>assert.equal(actual.disabled,true),toHaveCount:async n=>assert.equal(actual.count,n)})
 expect.poll=fn=>({toHaveLength:async n=>assert.equal((await fn()).length,n)})
 await run(assert,page,{expect},'readEndpoint',observed,()=>({}),async()=>[],()=>({disabled:true}),()=>({count:0}),first)
 const observedVerdict='CLAUSE_COMPLETES'
 results.push({...literal,observed:observedVerdict,agrees:literal.expected===observedVerdict,actual_abort_handler_calls:abortedReads,trace})
}
const relaxed=source.match(/document\.documentElement\.scrollWidth<=innerWidth\+1/)?.[0]
assert.ok(relaxed)
const dimensions={scrollWidth:391,innerWidth:390}
const overflow={expected:false,observed:new Function('document','innerWidth','return '+relaxed)({documentElement:{scrollWidth:391}},390),dimensions,actual_source_expression:relaxed}
const report={classification:'PURE_SYNTHETIC_TEST_CLAUSE_NOT_BROWSER_OR_PRODUCT_RUNTIME',source_sha256:createHash('sha256').update(source).digest('hex'),clause_sha256:createHash('sha256').update(clause).digest('hex'),expected_before_execution:expected,results,one_pixel_overflow:overflow}
writeFileSync('/workspace/scratch/9442228ed2dc/ow04-proposals/browser/READ_FAULT_SCHEDULE_RESULT.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report))
