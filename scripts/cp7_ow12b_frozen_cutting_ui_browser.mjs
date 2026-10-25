// Actual Chromium/locks/tabs; controlled identity and RPC. No Native SAVE credit.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname,resolve} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'
const panel='scripts/cp7_frozen_cutting_ui/client/NativeFrozenCuttingPanel.tsx'
const out=process.env.CP7_FROZEN_CUTTING_UI_REPORT_PATH??'cp6-proof/t3/FROZEN_CUTTING_UI_BROWSER4.json'
const ids=['FROZEN_CUTTING_UI_DESKTOP_VERIFIED_SOURCE_EXISTING_FORM','FROZEN_CUTTING_UI_MOBILE_FORM_TEXT_AND_INPUTS','FROZEN_CUTTING_UI_REAL_STORAGE_RETIRES_DIRTY_FORM','FROZEN_CUTTING_UI_CURRENT_ACCESS_RETIRES_PARENT_RETAINS_REPLAY']
const report={contract:'cp7.frozen-cutting-prepared-ui-browser4.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),required_case_ids:ids,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_identity:true,controlled_RPC_replies:true,actual_Native:false,actual_Auth_HTTP_credit:false,default_application_adopted:false,actual_cutting_SAVE_qualified:false,production_go:false}
const entry=`import React from'react';import{createRoot}from'react-dom/client';import Panel from'/${panel}';import{stagedRun}from'/tests/fixtures/nativeAnalysisPages.ts';import{recoveryIdentity}from'/tests/fixtures/productionRecovery.ts';import*as plan from'/tests/fixtures/nativePlan.ts';import*as request from'/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts';import*as recovery from'/src/productionRecovery.ts';import'/src/styles.css';import'/src/auth/auth.css';
async function main(){
const f=await stagedRun({targets:1,capturedAt:'2026-10-07T09:00:00.123456Z'}),auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.actor,rowVersion:1,roleRowVersion:1});auth.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','production.cutting.view');
const p=window.proof={f,auth,request,recovery,calls:[],scope:'frozen-quantity:cp6-disposable:actor-1',productionScope:'cp6-disposable:actor-1',mode:'normal',sourceReads:0,sourceEnds:0};
p.client={rpc:async(name,args)=>{p.calls.push({name,args:structuredClone(args)});if(name==='erp_cp7_request_bounded_staged_analysis_v2'){if(p.f.pageSet.request_id!==args.p_request)p.f=await stagedRun({targets:1,requestId:args.p_request,capturedAt:'2026-10-07T09:00:00.123456Z'});return{data:p.f.job('DONE'),error:null}}
if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:p.f.pageSet,error:null};if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:p.f.page(args.p_index),error:null};
if(name==='erp_cp7_check_staged_analysis_source_v1')return{data:{source_state:'ARCHIVED_STALE',checked_at:'2026-10-25T19:00:00.123457Z'},error:null};
if(p.mode==='denied'&&['erp_cp7_get_plan_options_v2','erp_cp7_save_cutting_suggestion_v1'].includes(name))return{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}};
if(name==='erp_cp7_get_plan_options_v2'){const r=p.f.original.analysis.recommendations[0];return{data:{...plan.stagedOptions(),actor_scope_id:p.f.actor,run_id:p.f.runId,target_key:p.f.headerDoc.product_labels[0].target_key,identity_hash:p.f.identityHash,data_as_of:p.f.reference.captured_at,size_id:p.f.headerDoc.product_labels[0].target_key.split(':')[1],needed_pcs:r.q_conditional.value,available_fg_pcs:r.actual_fg.value},error:null}}
throw Error('UNEXPECTED_CONTROLLED_RPC:'+name)}};
const root=createRoot(document.getElementById('root'));root.render(React.createElement(Panel,{query:f.query,onSourceReadStart:()=>{p.sourceReads++},onSourceReadEnd:()=>{p.sourceEnds++},onClose:()=>root.unmount()}));window.ready=true;
}main().catch(e=>{window.startError=String(e)});`
const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saran potong — pengujian terpisah</title><style>body{margin:0;font:16px system-ui}main{max-width:1100px;margin:auto;padding:12px}*{box-sizing:border-box}</style></head><body><main id="root"></main><script type="module" src="/frozen-cutting-entry.tsx"></script></body></html>'
let server,browser,context
try{
 const plugin={name:'isolated-frozen-cutting-ui',enforce:'pre',resolveId(id,importer){if(id==='/frozen-cutting-entry.tsx')return'\0frozen-cutting-entry';if(id.startsWith('.')&&importer&&!importer.startsWith('\0')){const path=resolve(dirname(importer),id).replace(/\.tsx?$/,'');if(path===resolve('src/auth/AuthProvider'))return'\0controlled-auth';if(path===resolve('src/lib/supabase'))return'\0controlled-rpc'}},load(id){if(id==='\0frozen-cutting-entry')return entry;if(id==='\0controlled-auth')return'export const useAuth=()=>window.proof.auth';if(id==='\0controlled-rpc')return'export const getUatSupabaseClient=()=>window.proof.client'},configureServer(s){s.middlewares.use((req,res,next)=>{const path=new URL(req.url,'http://localhost').pathname;if(!['/frozen-cutting-ui','/frozen-cutting-storage'].includes(path)){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(path==='/frozen-cutting-storage'?'<!doctype html><title>Storage peer</title>':html)})}}
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',oxc:{jsx:{runtime:'automatic',refresh:false}},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[plugin]});await server.listen()
 const origin='http://127.0.0.1:'+server.httpServer.address().port,url=origin+'/frozen-cutting-ui'
 for(const p of['/frozen-cutting-ui','/frozen-cutting-entry.tsx','/'+panel,'/src/NativePlanDraftPanel.tsx']){const r=await fetch(origin+p);assert.equal(r.status,200,p);assert.ok((await r.text()).length>100)}
 if(process.env.CP7_FROZEN_CUTTING_UI_PREFLIGHT_ONLY==='1'){report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true}
 else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version();context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Los_Angeles'})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)))
  const form=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true}),rows=()=>page.locator('[data-quantity-target]'),click=name=>page.getByRole('button',{name,exact:true}).click()
  const ready=async()=>{await page.goto(url);await page.waitForFunction(()=>window.ready===true||window.startError);assert.equal(await page.evaluate(()=>window.startError),undefined);await rows().first().waitFor()}
  const open=async()=>{await click('Periksa saran potong');await form.waitFor()}
  const stored=()=>page.evaluate(()=>{const p=window.proof,key=p.request.frozenAnalysisRequestKey(p.f.actor,p.scope);return{key,bytes:localStorage.getItem(key),pending:p.request.readFrozenAnalysisRequest(p.f.actor,p.scope).pending}})
  const shape=async()=>{assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);const controls=await form.locator('input,select,textarea,button').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>{const r=n.getBoundingClientRect();return{left:r.left,right:r.right}}));assert.ok(controls.length&&controls.every(r=>r.left>=0&&r.right<=390+1))}
  await mkdir(dirname(out),{recursive:true});await ready();await open();const original=await stored();await click('Muat pilihan Potongan dari ERP');await form.locator('.native-plan-result').waitFor()
  assert.match(await form.innerText(),/Kebutuhan setelah pembagian: 0 PCS/);assert.equal(await page.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true}).isDisabled(),true)
  await form.getByLabel('Alasan rencana Potongan',{exact:true}).fill('Controlled editable draft; no SAVE claim')
  const source=await page.evaluate(()=>{const p=window.proof,call=p.calls.find(c=>c.name==='erp_cp7_get_plan_options_v2');return{run:p.f.runId,target:p.f.headerDoc.product_labels[0].target_key,clock:p.f.reference.captured_at,query:call.args.p_query,writer_calls:p.calls.filter(c=>c.name.includes('save_')).length}})
  assert.equal(source.query.run_id,source.run);assert.equal(source.query.target_key,source.target);assert.equal(source.clock,'2026-10-07T09:00:00.123456Z');assert.equal(source.writer_calls,0);assert.deepEqual(await stored(),original)
  await page.screenshot({path:resolve(dirname(out),'frozen-cutting-desktop.png'),fullPage:true});report.cases.push({id:ids[0],status:'PASS',actual_existing_form:true,verified_v2_source_exact_clock:true,displayed_zero_need_exact:true,editable_reason:true,no_writer_sent:true})
  await page.setViewportSize({width:390,height:844});await shape();await page.screenshot({path:resolve(dirname(out),'frozen-cutting-mobile.png'),fullPage:true});const text=await readable(form)
  const box=await form.getByRole('checkbox').boundingBox();assert.ok(box&&box.width>=20&&box.height>=20);report.cases.push({id:ids[1],status:'PASS',viewport:390,all_controls_inside_viewport:true,visible_text_contrasts:text,checkbox_min20px:true})
  const peer=await context.newPage();await peer.goto(origin+'/frozen-cutting-storage');const replacement={...original.pending,id:'00000000-0000-4000-8000-000000000999'}
  await peer.evaluate(({key,replacement})=>localStorage.setItem(key,JSON.stringify(replacement)),{key:original.key,replacement});await form.waitFor({state:'detached'});assert.equal(await rows().count(),0);assert.deepEqual((await stored()).pending,replacement);await peer.close()
  await ready();await click('Periksa sumber kebutuhan');await page.getByText(/sumber sudah berubah; hitung kebutuhan terbaru/).waitFor();assert.equal(await page.getByRole('button',{name:'Periksa saran potong',exact:true}).isDisabled(),true)
  report.cases.push({id:ids[2],status:'PASS',actual_tabs:2,actual_StorageEvent:true,dirty_form_retired:true,replacement_UUID_preserved:true,stale_source_refuses_new_form:true})
  await ready();await open();const held=await stored();await page.evaluate(()=>{window.proof.mode='denied'});await click('Muat pilihan Potongan dari ERP');await form.waitFor({state:'detached'});assert.equal(await rows().count(),0);assert.deepEqual(await stored(),held)
  await ready();await open();const pending=await page.evaluate(()=>{const p=window.proof,payload={run_id:p.f.runId,target_key:p.f.headerDoc.product_labels[0].target_key,identity_hash:p.f.identityHash,cutting_save_contract:'cp7.cutting-checked-save.v1'},input={action:'SAVE_DRAFT',payload,expectedVersion:null},envelope={...input,id:crypto.randomUUID(),createdAt:new Date().toISOString(),fingerprint:JSON.stringify(input)};if(!p.recovery.persistProductionEnvelope(p.productionScope,'PLAN_APPLY_STAGED',envelope))throw Error('CONTROLLED_ENVELOPE_FAILED');p.mode='denied';return{envelope,key:p.recovery.productionKey(p.productionScope,'PLAN_APPLY_STAGED')}})
  await click('Reconcile transaksi');await form.waitFor({state:'detached'});assert.equal(await rows().count(),0);assert.deepEqual(await page.evaluate(key=>JSON.parse(localStorage.getItem(key)),pending.key),pending.envelope)
  const sent=await page.evaluate(()=>window.proof.calls.filter(c=>c.name==='erp_cp7_save_cutting_suggestion_v1'));assert.equal(sent.length,1);assert.deepEqual(sent[0].args,{p_payload:pending.envelope.payload,p_request:pending.envelope.id})
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]});assert.deepEqual(errors,[]);report.cases.push({id:ids[3],status:'PASS',controlled_options403_and_replay403:true,parent_and_form_retired:true,original_checked_UUID_payload_retained:true,actual_locks_released:true})
  assert.deepEqual(report.cases.map(c=>c.id),ids);report.status='PASS';report.browser_page_errors=[]
 }
}catch(e){report.error=String(e);report.stack=e.stack;process.exitCode=1}
finally{
 const paths=new Set([panel,'scripts/cp7_ow12b_frozen_cutting_ui_browser.mjs','scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity.ts','tests/fixtures/nativePlan.ts','tests/fixtures/nativeAnalysisPages.ts','tests/fixtures/nativeAnalysisStandin.json','tests/fixtures/productionRecovery.ts'])
 for(const m of server?.environments.client.moduleGraph.idToModuleMap.values()??[])if(m.file?.startsWith(process.cwd()+'/')&&!m.file.includes('/node_modules/'))paths.add(m.file.slice(process.cwd().length+1))
 for(const p of [...paths].sort())report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
 await context?.close();await browser?.close();await server?.close();await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:report.cases.length,error:report.error,report:out}))
}
async function readable(panel){
 const rows=await panel.evaluate(root=>{
  const rgb=v=>v.match(/[\d.]+/g).map(Number),lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0)
  const out=[]
  for(const el of[root,...root.querySelectorAll('*')]){
   const s=getComputedStyle(el),label=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
   if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
   const layers=[];let bg=null
   for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p),v=rgb(c.backgroundColor);if(c.backgroundImage!=='none'||c.opacity!=='1')throw Error('UNMEASURED_CUTTING_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,90),tag:p.tagName,classes:p.className,backgroundImage:c.backgroundImage,opacity:c.opacity}));if(v.length===3||v[3]===1){bg=v.slice(0,3);break}layers.push(v)}
   if(!bg)throw Error('MISSING_CUTTING_SURFACE')
   for(const v of layers.reverse())bg=bg.map((x,i)=>v[i]*(v[3]??1)+x*(1-(v[3]??1)))
   const record=(label,color)=>{const f=rgb(color),fg=bg.map((x,i)=>f[i]*(f[3]??1)+x*(1-(f[3]??1))),a=lum(fg),b=lum(bg);out.push({label:label.slice(0,90),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)})}
   record(label,s.color)
   if(el.hasAttribute('data-label')){const pseudo=getComputedStyle(el,'::before');if(pseudo.display!=='none'&&pseudo.content!=='none')record(el.getAttribute('data-label'),pseudo.color)}
  }
  return out
 });assert.ok(rows.length>0&&rows.every(x=>x.ratio>=4.5),JSON.stringify(rows.filter(x=>x.ratio<4.5)));return rows
}
