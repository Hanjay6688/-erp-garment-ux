// Real Chromium tabs/Web Locks/localStorage, controlled RPC replies only.
// This does not qualify Auth, Native idempotency or the production UI.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'

const source='scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts'
const actor='11111111-1111-4111-8111-111111111111',id1='22222222-2222-4222-8222-222222222222',id2='33333333-3333-4333-8333-333333333333'
const q={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'}
const request=id=>({id,actor,q,method:'cp7.bounded-analysis-request.v2'})
const scope='frozen-real-tabs',path=process.env.CP7_FROZEN_BROWSER_REPORT_PATH??'cp6-proof/t3/FROZEN_RECOVERY_BROWSER3.json'
const IDs=['FROZEN_REAL_TABS_SINGLE_DURABLE_CREATION','FROZEN_REAL_TABS_SEND_BLOCKS_REPLACEMENT_AND_QUEUED_SEND_REREADS','FROZEN_REAL_TABS_REPLY_LOSS_RELOAD_EXACT_RETRY']
const report={contract:'cp7.frozen-recovery-real-browser3.v2',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
 required_case_ids:IDs,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_RPC_replies:true,
 actual_browser_locks_qualified:false,actual_Native:false,actual_Auth_HTTP_credit:false,production_UI_qualified:false,production_go:false}
for(const p of[source,'scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait.ts','scripts/cp7_ow12b_frozen_recovery_browser.mjs'])report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
const html=`<!doctype html><html><head><meta charset="utf-8"><title>Isolated request recovery proof</title></head><body><main>Request recovery test</main><script type="module">import * as api from '/${source}';window.api=api;window.ready=true;</script></body></html>`
const served=new Set()
let server,browser,context
try{
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',server:{host:'127.0.0.1',port:0},plugins:[{name:'isolated-frozen-recovery',transform(_code,id){const path=id.split('?')[0];if(path.startsWith(process.cwd()+'/')&&!path.includes('/node_modules/'))served.add(path.slice(process.cwd().length+1))},configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url!=='/frozen-recovery-proof'){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(html)})}}]})
 await server.listen();const url='http://127.0.0.1:'+server.httpServer.address().port+'/frozen-recovery-proof'
 const document=await fetch(url),module=await fetch(new URL('/'+source,url));assert.equal(document.status,200);assert.equal(module.status,200)
 assert.match(await module.text(),/erp_cp7_request_bounded_staged_analysis_v2/)
 if(process.env.CP7_FROZEN_BROWSER_PREFLIGHT_ONLY==='1'){
  report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true
 }else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version()
  context=await browser.newContext();const a=await context.newPage(),b=await context.newPage()
  const ready=async page=>{await page.goto(url);await page.waitForFunction(()=>window.ready===true);assert.equal(await page.evaluate(()=>isSecureContext&&!!navigator.locks),true)}
  await ready(a);await ready(b)
  const reset=async()=>{await a.evaluate(()=>localStorage.clear());await ready(a);await ready(b)}
  const result=async(page,name)=>{await page.waitForFunction(name=>window[name]!==undefined,name);return page.evaluate(name=>window[name],name)}
  const queued=async count=>{await a.waitForFunction(async({actor,scope,count})=>{const key=window.api.frozenAnalysisRequestKey(actor,scope),x=await navigator.locks.query();return x.held.filter(l=>l.name===key).length===1&&x.pending.filter(l=>l.name===key).length===count},{actor,scope,count})}
  const persist=async(page,id,name)=>page.evaluate(({actor,scope,r,name})=>{window.api.persistFrozenAnalysisRequest(actor,scope,r).then(()=>{window[name]={status:'FULFILLED'}},error=>{window[name]={status:'REFUSED',message:String(error)}})},{actor,scope,r:request(id),name})
  const key=await a.evaluate(({actor,scope})=>window.api.frozenAnalysisRequestKey(actor,scope),{actor,scope})

  await a.evaluate(key=>{navigator.locks.request(key,{mode:'exclusive'},()=>new Promise(resolve=>{window.releaseGate=resolve;window.gateHeld=true}))},key)
  await a.waitForFunction(()=>window.gateHeld===true)
  await persist(a,id1,'createdA');await persist(b,id2,'createdB');await queued(2)
  assert.equal(await a.evaluate(key=>localStorage.getItem(key),key),null)
  await a.evaluate(()=>window.releaseGate())
  const creations=[await result(a,'createdA'),await result(b,'createdB')]
  assert.deepEqual(creations.map(x=>x.status).sort(),['FULFILLED','REFUSED'])
  const bytesA=await a.evaluate(key=>localStorage.getItem(key),key),bytesB=await b.evaluate(key=>localStorage.getItem(key),key)
  assert.equal(bytesA,bytesB);assert.deepEqual(JSON.parse(bytesA),request(creations[0].status==='FULFILLED'?id1:id2))
  report.cases.push({id:IDs[0],status:'PASS',actual_tabs:2,observed_real_pending_locks:2,single_creation:true,exact_shared_bytes:true})

  await reset();await persist(a,id1,'persisted');assert.equal((await result(a,'persisted')).status,'FULFILLED')
  await a.evaluate(({actor,scope})=>{window.calls=[];window.api.requestFrozenAnalysis({rpc:(method,args)=>{window.calls.push({method,args});return new Promise(resolve=>{window.reply=resolve})}},actor,scope).then(value=>{window.sent={status:'FULFILLED',value}},error=>{window.sent={status:'REFUSED',message:String(error)}})},{actor,scope})
  await a.waitForFunction(()=>window.calls?.length===1)
  await b.evaluate(({actor,scope,before,after})=>{window.api.replaceFrozenAnalysisRequest(actor,scope,before,after).then(()=>{window.replaced={status:'FULFILLED'}},error=>{window.replaced={status:'REFUSED',message:String(error)}});window.calls=[];window.api.requestFrozenAnalysis({rpc:async(method,args)=>{window.calls.push({method,args});return{data:{state:'RUNNING'},error:null}}},actor,scope).then(value=>{window.sent={status:'FULFILLED',value}},error=>{window.sent={status:'REFUSED',message:String(error)}})},{actor,scope,before:request(id1),after:request(id2)})
  await queued(2);assert.deepEqual(await b.evaluate(()=>window.calls),[])
  assert.deepEqual(JSON.parse(await b.evaluate(key=>localStorage.getItem(key),key)),request(id1))
  await a.evaluate(()=>window.reply({data:{state:'RUNNING'},error:null}))
  assert.equal((await result(a,'sent')).status,'FULFILLED');assert.equal((await result(b,'replaced')).status,'FULFILLED');assert.equal((await result(b,'sent')).status,'FULFILLED')
  const exact=id=>[{method:'erp_cp7_request_bounded_staged_analysis_v2',args:{p_query:q,p_request:id}}]
  assert.deepEqual(await a.evaluate(()=>window.calls),exact(id1));assert.deepEqual(await b.evaluate(()=>window.calls),exact(id2))
  assert.deepEqual(JSON.parse(await a.evaluate(key=>localStorage.getItem(key),key)),request(id2))
  report.cases.push({id:IDs[1],status:'PASS',actual_tabs:2,observed_real_pending_locks:2,send_holds_mutation_lock:true,queued_send_rereads_new_exact_UUID_payload:true,actor_not_transmitted:true})

  await reset();await persist(a,id1,'persisted');await result(a,'persisted')
  const original=await a.evaluate(key=>localStorage.getItem(key),key)
  await a.evaluate(({actor,scope})=>{window.calls=[];window.api.requestFrozenAnalysis({rpc:async(method,args)=>{window.calls.push({method,args});throw Error('CONTROLLED_REPLY_LOST_AFTER_SEND')}},actor,scope).then(()=>{window.lost={status:'UNEXPECTED_SUCCESS'}},error=>{window.lost={status:'REFUSED',message:String(error)}})},{actor,scope})
  assert.match((await result(a,'lost')).message,/CONTROLLED_REPLY_LOST_AFTER_SEND/)
  const beforeReload=await a.evaluate(()=>window.calls);await ready(b)
  assert.equal(await b.evaluate(key=>localStorage.getItem(key),key),original)
  await b.evaluate(({actor,scope})=>{window.calls=[];window.api.requestFrozenAnalysis({rpc:async(method,args)=>{window.calls.push({method,args});return{data:{state:'RUNNING'},error:null}}},actor,scope).then(value=>{window.retry={status:'FULFILLED',value}},error=>{window.retry={status:'REFUSED',message:String(error)}})},{actor,scope})
  assert.equal((await result(b,'retry')).status,'FULFILLED');assert.deepEqual(await b.evaluate(()=>window.calls),beforeReload)
  assert.equal(await b.evaluate(key=>localStorage.getItem(key),key),original)
  report.cases.push({id:IDs[2],status:'PASS',actual_reload:true,reply_loss_controlled:true,same_method_UUID_query_and_retained_bytes:true,no_Native_idempotency_credit:true})
  const remaining=await a.evaluate(()=>navigator.locks.query());assert.deepEqual(remaining,{held:[],pending:[]})
  assert.deepEqual(report.cases.map(c=>c.id),IDs);assert.ok(served.has('scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait.ts'),'COMMON_WAIT_HELPER_NOT_SERVED');report.actual_served_module_graph=true;report.status='PASS';report.actual_browser_locks_qualified=true;report.actual_tabs=2;report.no_remaining_locks=true
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{await context?.close();await browser?.close();await server?.close();report.served_source_paths=[...served].sort();report.served_source_sha256={};for(const p of report.served_source_paths){const hash=createHash('sha256').update(await readFile(p)).digest('hex');report.served_source_sha256[p]=hash;report.source_sha256[p]=hash}await mkdir(dirname(path),{recursive:true});await writeFile(path,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,counts:report.cases.reduce((r,c)=>(r[c.status]=(r[c.status]??0)+1,r),{}),actual_browser_locks_qualified:report.actual_browser_locks_qualified,error:report.error,report:path}))}
