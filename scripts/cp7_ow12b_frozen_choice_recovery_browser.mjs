// Real Chromium tabs/Web Locks/localStorage, controlled RPC replies only.
// This does not qualify Auth, Native idempotency or the production UI.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'

const source='scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts'
const id1='22222222-2222-4222-8222-222222222222',id2='33333333-3333-4333-8333-333333333333'
let actor,targetKey,payload,baseCommand,baseOutcome
const request=id=>({...structuredClone(baseCommand),requestId:id})
const outcome=id=>({...structuredClone(baseOutcome),request_id:id})
const scope='frozen-choice-real-tabs',path=process.env.CP7_FROZEN_CHOICE_BROWSER_REPORT_PATH??'cp6-proof/t3/FROZEN_CHOICE_RECOVERY_BROWSER3.json'
const IDs=['FROZEN_CHOICE_REAL_TABS_SINGLE_DURABLE_CREATION','FROZEN_CHOICE_REAL_TABS_SEND_BLOCKS_CLEAR_AND_QUEUED_SEND_REREADS_EMPTY','FROZEN_CHOICE_REAL_TABS_REPLY_LOSS_RELOAD_EXACT_RETRY']
const report={contract:'cp7.frozen-choice-recovery-real-browser3.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
 required_case_ids:IDs,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_RPC_replies:true,
 actual_browser_locks_qualified:false,actual_Native:false,actual_Auth_HTTP_credit:false,production_UI_qualified:false,production_go:false}
for(const p of[source,'scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait.ts','src/nativeProductAnalog.ts','src/nativeProductAnalogChoice.ts','tests/fixtures/nativeProductAnalog.ts','tests/fixtures/nativeProductAnalogChoice.ts','scripts/cp7_ow12b_frozen_choice_recovery_browser.mjs'])report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
const html=`<!doctype html><html><head><meta charset="utf-8"><title>Isolated request recovery proof</title></head><body><main>Request recovery test</main><script type="module">import * as api from '/${source}';import{analogChoiceFixture}from'/tests/fixtures/nativeProductAnalogChoice.ts';const f=analogChoiceFixture();f.context.sourceMethod='FROZEN_V2';f.candidates.sourceMethod='FROZEN_V2';f.command=api.prepareAnalogConfirmation(f.context,f.candidates,f.workspace,f.candidates.rows[0].key,'1.2500',' Ukuran dan model ditinjau ',true,f.command.requestId);f.outcome.contract_version='cp7.product-analog-choice-outcome.v2';window.api=api;window.fixture=f;window.ready=true;</script></body></html>`
const served=new Set()
let server,browser,context
try{
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',server:{host:'127.0.0.1',port:0},plugins:[{name:'isolated-frozen-recovery',transform(_code,id){const path=id.split('?')[0];if(path.startsWith(process.cwd()+'/')&&!path.includes('/node_modules/'))served.add(path.slice(process.cwd().length+1))},configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url!=='/frozen-recovery-proof'){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(html)})}}]})
 await server.listen();const url='http://127.0.0.1:'+server.httpServer.address().port+'/frozen-recovery-proof'
 const document=await fetch(url),module=await fetch(new URL('/'+source,url));assert.equal(document.status,200);assert.equal(module.status,200)
 assert.match(await module.text(),/erp_cp7_save_product_analog_choice_v2/)
 if(process.env.CP7_FROZEN_CHOICE_BROWSER_PREFLIGHT_ONLY==='1'){
  report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true
 }else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version()
  context=await browser.newContext();const a=await context.newPage(),b=await context.newPage()
  const ready=async page=>{await page.goto(url);await page.waitForFunction(()=>window.ready===true);assert.equal(await page.evaluate(()=>isSecureContext&&!!navigator.locks),true)}
  await ready(a);await ready(b)
  ;({actor,targetKey,payload,baseCommand,baseOutcome}=await a.evaluate(()=>{const f=window.fixture;return{actor:f.context.actor,targetKey:f.context.targetKey,payload:f.command.payload,baseCommand:f.command,baseOutcome:f.outcome}}))
  const reset=async()=>{await a.evaluate(()=>localStorage.clear());await ready(a);await ready(b)}
  const result=async(page,name)=>{await page.waitForFunction(name=>window[name]!==undefined,name);return page.evaluate(name=>window[name],name)}
  const queued=async count=>{await a.waitForFunction(async({actor,scope,targetKey,count})=>{const key=window.api.analogChoiceRequestKey(scope,actor,targetKey),x=await navigator.locks.query();return x.held.filter(l=>l.name===key).length===1&&x.pending.filter(l=>l.name===key).length===count},{actor,scope,targetKey,count})}
  const persist=async(page,id,name)=>page.evaluate(({actor,scope,targetKey,r,name})=>{window.api.persistAnalogChoiceRequest(scope,r).then(()=>{window[name]={status:'FULFILLED'}},error=>{window[name]={status:'REFUSED',message:String(error)}})},{actor,scope,targetKey,r:request(id),name})
  const key=await a.evaluate(({actor,scope,targetKey})=>window.api.analogChoiceRequestKey(scope,actor,targetKey),{actor,scope,targetKey})

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
  await a.evaluate(({actor,scope,targetKey})=>{window.calls=[];window.api.saveProductAnalogChoice({rpc:(method,args)=>{window.calls.push({method,args});return new Promise(resolve=>{window.reply=resolve})}},scope,actor,targetKey).then(value=>{window.sent={status:'FULFILLED',value}},error=>{window.sent={status:'REFUSED',message:String(error)}})},{actor,scope,targetKey})
  await a.waitForFunction(()=>window.calls?.length===1)
  await b.evaluate(({actor,scope,targetKey,before,wire})=>{window.api.clearAnalogChoiceRequest(scope,before).then(()=>{window.cleared={status:'FULFILLED'}},error=>{window.cleared={status:'REFUSED',message:String(error)}});window.calls=[];window.api.saveProductAnalogChoice({rpc:async(method,args)=>{window.calls.push({method,args});return{data:wire,error:null}}},scope,actor,targetKey).then(value=>{window.sent={status:'FULFILLED',value}},error=>{window.sent={status:'REFUSED',message:String(error)}})},{actor,scope,targetKey,before:request(id1),wire:outcome(id1)})
  await queued(2);assert.deepEqual(await b.evaluate(()=>window.calls),[])
  assert.deepEqual(JSON.parse(await b.evaluate(key=>localStorage.getItem(key),key)),request(id1))
  await a.evaluate(wire=>window.reply({data:wire,error:null}),outcome(id1))
  assert.equal((await result(a,'sent')).status,'FULFILLED');assert.equal((await result(b,'cleared')).status,'FULFILLED');assert.equal((await result(b,'sent')).status,'REFUSED')
  const exact=id=>[{method:'erp_cp7_save_product_analog_choice_v2',args:{p_payload:payload,p_request:id}}]
  assert.deepEqual(await a.evaluate(()=>window.calls),exact(id1));assert.deepEqual(await b.evaluate(()=>window.calls),[])
  assert.equal(await a.evaluate(key=>localStorage.getItem(key),key),null)
  report.cases.push({id:IDs[1],status:'PASS',actual_tabs:2,observed_real_pending_locks:2,send_holds_mutation_lock:true,queued_send_rereads_empty_and_refuses_before_RPC:true,actor_not_transmitted:true})

  await reset();await persist(a,id1,'persisted');await result(a,'persisted')
  const original=await a.evaluate(key=>localStorage.getItem(key),key)
  await a.evaluate(({actor,scope,targetKey})=>{window.calls=[];window.api.saveProductAnalogChoice({rpc:async(method,args)=>{window.calls.push({method,args});throw Error('CONTROLLED_REPLY_LOST_AFTER_SEND')}},scope,actor,targetKey).then(()=>{window.lost={status:'UNEXPECTED_SUCCESS'}},error=>{window.lost={status:'REFUSED',message:String(error)}})},{actor,scope,targetKey})
  assert.match((await result(a,'lost')).message,/CONTROLLED_REPLY_LOST_AFTER_SEND/)
  const beforeReload=await a.evaluate(()=>window.calls);await ready(b)
  assert.equal(await b.evaluate(key=>localStorage.getItem(key),key),original)
  await b.evaluate(({actor,scope,targetKey,wire})=>{window.calls=[];window.api.saveProductAnalogChoice({rpc:async(method,args)=>{window.calls.push({method,args});return{data:wire,error:null}}},scope,actor,targetKey).then(value=>{window.retry={status:'FULFILLED',value}},error=>{window.retry={status:'REFUSED',message:String(error)}})},{actor,scope,targetKey,wire:outcome(id1)})
  assert.equal((await result(b,'retry')).status,'FULFILLED');assert.deepEqual(await b.evaluate(()=>window.calls),beforeReload)
  assert.equal(await b.evaluate(key=>localStorage.getItem(key),key),original)
  report.cases.push({id:IDs[2],status:'PASS',actual_reload:true,reply_loss_controlled:true,same_method_actor_UUID_payload_and_retained_bytes:true,no_Native_idempotency_credit:true})
  const remaining=await a.evaluate(()=>navigator.locks.query());assert.deepEqual(remaining,{held:[],pending:[]})
  assert.deepEqual(report.cases.map(c=>c.id),IDs);assert.ok(served.has('scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait.ts'),'COMMON_WAIT_HELPER_NOT_SERVED');report.actual_served_module_graph=true;report.status='PASS';report.actual_browser_locks_qualified=true;report.actual_tabs=2;report.no_remaining_locks=true
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{await context?.close();await browser?.close();await server?.close();report.served_source_paths=[...served].sort();report.served_source_sha256={};for(const p of report.served_source_paths){const hash=createHash('sha256').update(await readFile(p)).digest('hex');report.served_source_sha256[p]=hash;report.source_sha256[p]=hash}await mkdir(dirname(path),{recursive:true});await writeFile(path,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,counts:report.cases.reduce((r,c)=>(r[c.status]=(r[c.status]??0)+1,r),{}),actual_browser_locks_qualified:report.actual_browser_locks_qualified,error:report.error,report:path}))}
