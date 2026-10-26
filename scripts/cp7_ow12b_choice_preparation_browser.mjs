// Real Chromium, actual prepared B components, controlled identity and HTTP RPC.
// This is client recovery evidence, never Native/Auth/K4/financial qualification.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium,expect} from '@playwright/test'

const panel='scripts/cp7_frozen_choice_preparation/client/PreparedFrozenAnalogPanel.tsx'
const fixture='scripts/cp7_frozen_choice_ui/client/fixtures.ts'
const self='scripts/cp7_ow12b_choice_preparation_browser.mjs'
const out=process.env.CP7_CHOICE_PREPARATION_BROWSER_REPORT_PATH??'cp6-proof/t3/CHOICE_PREPARATION_BROWSER6.json'
const ids=['PREPARATION_REOPEN_TWO_TABS_GET_ONLY','PREPARATION_MOBILE_HELD_STEP_CLOSE_USABLE','PREPARATION_LOST_ENQUEUE_RELOAD_SAME_WORK','PREPARATION_TERMINAL_FAILURE_AND_EXPIRY','PREPARATION_REVOKED_ACCESS_REDACTS','PREPARATION_HELD_STATUS_BOUNDED_RECOVERY']
const contractPath='docs/cp7/d17-14/ow12b/CHOICE_PREPARATION_BROWSER6_CONTRACT.json'
const declaration=JSON.parse(await readFile(contractPath,'utf8'))
assert.deepEqual(declaration.required_case_ids,ids);assert.equal(declaration.expected_case_count,6)
const hash=bytes=>createHash('sha256').update(bytes).digest('hex')
const report={contract:'cp7.choice-preparation-real-browser6.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),required_case_ids:ids,expected_case_count:6,cases:[],status:'INCOMPLETE',controlled_identity:true,controlled_HTTP_RPC:true,actual_Native:false,actual_Auth_HTTP_credit:false,actual_K4:false,actual_finance_HPP:false,default_adopted:false,production_go:false,source_sha256:{}}
const entry=`import React from 'react';import{createRoot}from'react-dom/client';import Panel from '/${panel}';import{frozenChoiceUIFixture}from'/${fixture}';import{prepReply}from'/scripts/cp7_frozen_choice_preparation/client/preparationFixture.ts';import{recoveryIdentity}from'/tests/fixtures/productionRecovery.ts';
const f=frozenChoiceUIFixture(1),auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.context.actor,rowVersion:1,roleRowVersion:1});auth.identity.permissions.push('master.product.view','master.product.manage','warehouse.stock.view','sales.invoice.view');
const p=window.proof={f,auth};p.client={rpc:async(name,args)=>{const r=await fetch('/proof-rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,args})});return await r.json()}};
await fetch('/proof-fixture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({context:f.context,raw:f.raw,candidates:f.reply(),preparation:{...prepReply(),source_request:f.context.requestId,run_id:f.context.runId,reference:{captured_at:f.context.reference.capturedAt,source_hash:f.context.reference.sourceHash}}})});
const root=createRoot(document.getElementById('panel'));p.close=()=>root.unmount();p.lost=message=>{document.getElementById('access').textContent=message;root.unmount()};root.render(React.createElement(Panel,{context:f.context,label:'Produk baru',onClose:p.close,onAccessLost:p.lost}));window.ready=true;`
const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Uji terpisah persiapan B</title><style>body{margin:0;background:#f6f7f4;color:#172c24;font:16px system-ui}main{max-width:1100px;margin:auto;padding:16px}button{padding:9px 12px;font:inherit}*{box-sizing:border-box}</style></head><body><main><label>Catatan halaman lain<input id="other" aria-label="Catatan halaman lain"></label><p id="access" role="alert"></p><div id="panel"></div></main><script type="module" src="/preparation-proof-entry.tsx"></script></body></html>'
let server,browser,context,origin,fixtureData,state=null,denied=false,holdStep=false,holdGet=false,loseRequest=false,creations=0
const served=new Set(),calls=[],held=[],pageErrors=[]
const reply=()=>({...fixtureData.preparation,state,worker_active:state==='RUNNING',units_done:state==='READY'?1:0,unit_attempts:state==='FAILED'?3:0,failure_code:state==='FAILED'?'CP7_CHOICE_PREPARATION_TIME_LIMIT':null,failure_sqlstate:state==='FAILED'?'57014':null})
const send=(res,data,status=200)=>{if(res.destroyed)return;res.statusCode=status;res.setHeader('Content-Type','application/json');res.end(JSON.stringify(data))}
const release=()=>{for(const item of held.splice(0))send(item.res,{data:item.data,error:null})}
const readBody=async req=>{let bytes='';for await(const chunk of req){bytes+=chunk;assert.ok(bytes.length<100000,'PROOF_REQUEST_TOO_LARGE')}return JSON.parse(bytes)}
const prepCalls=()=>calls.filter(c=>c.name.includes('_frozen_choice_preparation_'))
const assertSameSource=()=>{assert.ok(prepCalls().length>0);for(const c of prepCalls())assert.deepEqual(c.args,{p_source_request:fixtureData.context.requestId,p_access:fixtureData.context.accessEpoch})}
const open=async page=>{page.on('pageerror',error=>pageErrors.push(String(error)));await page.goto(origin+'/preparation-proof');await page.waitForFunction(()=>window.ready===true)}
const reset=async(viewport={width:1365,height:900})=>{release();await context?.close();state=null;denied=holdStep=holdGet=loseRequest=false;creations=0;calls.length=0;pageErrors.length=0;context=await browser.newContext({viewport,timezoneId:'Asia/Jakarta'});return await context.newPage()}
const finish=(id,details)=>{assert.deepEqual(pageErrors,[]);assertSameSource();report.cases.push({id,status:'PASS',...details,preparation_calls:structuredClone(prepCalls()),controlled_work_creations:creations});console.log(JSON.stringify({case:id,status:'PASS',completed:report.cases.length,total:ids.length}))}
try{
 const plugin={name:'isolated-preparation-browser',enforce:'pre',resolveId(id){if(id==='/preparation-proof-entry.tsx')return'\0preparation-proof-entry';if(id==='../../../src/auth/AuthProvider')return'\0controlled-auth';if(id==='../../../src/lib/supabase')return'\0controlled-rpc'},load(id){if(id==='\0preparation-proof-entry')return entry;if(id==='\0controlled-auth')return'export const useAuth=()=>window.proof.auth';if(id==='\0controlled-rpc')return'export const getUatSupabaseClient=()=>window.proof.client'},transform(_code,id){const p=id.split('?')[0];if(p.startsWith(process.cwd()+'/')&&!p.includes('/node_modules/'))served.add(p.slice(process.cwd().length+1))},configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url==='/preparation-proof'){res.setHeader('Content-Type','text/html;charset=utf-8');res.end(html);return}if(!['/proof-fixture','/proof-rpc'].includes(req.url)){next();return}void(async()=>{
  const body=await readBody(req)
  if(req.url==='/proof-fixture'){if(fixtureData)assert.deepEqual(body,fixtureData);else fixtureData=body;send(res,{ok:true});return}
  const{name,args}=body;calls.push({name,args})
  if(denied){send(res,{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}},403);return}
  if(name==='erp_cp7_get_product_analog_choices_v1'){send(res,{data:fixtureData.raw,error:null});return}
  if(name==='erp_cp7_read_product_analog_candidates_v2'){assert.equal(state,'READY','CANDIDATES_BEFORE_READY');send(res,{data:fixtureData.candidates,error:null});return}
  assert.deepEqual(args,{p_source_request:fixtureData.context.requestId,p_access:fixtureData.context.accessEpoch})
  if(name==='erp_cp7_request_frozen_choice_preparation_v1'){if(state===null){state='QUEUED';creations++}if(loseRequest){loseRequest=false;res.destroy();return}send(res,{data:reply(),error:null});return}
  if(name==='erp_cp7_step_frozen_choice_preparation_v1'){assert.notEqual(state,null);state='READY';if(holdStep){held.push({res,data:reply()});return}send(res,{data:reply(),error:null});return}
  assert.equal(name,'erp_cp7_get_frozen_choice_preparation_v1','UNEXPECTED_RPC')
  if(state===null){send(res,{data:null,error:{message:'CP7_CHOICE_PREPARATION_NOT_STARTED'}});return}
  if(holdGet){held.push({res,data:reply()});return}send(res,{data:reply(),error:null})
 })().catch(error=>{pageErrors.push(String(error));send(res,{data:null,error:{message:'CONTROLLED_HARNESS_ERROR'}},500)})})}}
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',oxc:{jsx:{runtime:'automatic',refresh:false}},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[plugin]});await server.listen();origin='http://127.0.0.1:'+server.httpServer.address().port
 for(const path of['/preparation-proof','/preparation-proof-entry.tsx','/'+panel,'/scripts/cp7_frozen_choice_preparation/client/PreparedFrozenChoicePanel.tsx','/scripts/cp7_frozen_choice_preparation/client/nativeFrozenChoicePreparation.ts']){const r=await fetch(origin+path);assert.equal(r.status,200,path);assert.ok((await r.text()).length>100)}
 if(process.env.CP7_CHOICE_PREPARATION_BROWSER_PREFLIGHT_ONLY==='1'){report.status='SOURCE_SERVING_ONLY'}
 else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version()
  let page=await reset();state='RUNNING';await open(page);await expect(page.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible();await page.reload();await expect(page.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible()
  const other=await context.newPage();await open(other);await expect(other.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible();state='READY'
  for(const p of[page,other]){await expect(p.getByText('Persiapan selesai. Pilihan belum disimpan.',{exact:true})).toBeVisible();await expect(p.locator('[data-analog-target]')).toHaveCount(1)}
  assert.ok(prepCalls().every(c=>c.name==='erp_cp7_get_frozen_choice_preparation_v1'));assert.equal(creations,0);finish(ids[0],{real_tabs:2,real_reload:true,get_only:true,no_save:true,actual_server_dedup_credit:false})

  page=await reset({width:390,height:844});holdStep=true;await open(page);await page.getByRole('button',{name:'Siapkan pemeriksaan pilihan',exact:true}).click();await expect.poll(()=>held.length).toBe(1)
  await page.getByLabel('Catatan halaman lain').fill('Halaman tetap bisa dipakai');await expect(page.getByLabel('Catatan halaman lain')).toHaveValue('Halaman tetap bisa dipakai');await expect(page.getByRole('button',{name:'Tutup persiapan pembanding',exact:true})).toBeEnabled();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
  await page.getByRole('button',{name:'Tutup persiapan pembanding',exact:true}).click();release();await page.waitForTimeout(2200);await expect(page.locator('#panel')).toBeEmpty();assert.equal(calls.filter(c=>c.name==='erp_cp7_read_product_analog_candidates_v2').length,0);finish(ids[1],{viewport:[390,844],real_input_while_step_held:true,close_enabled:true,late_step_retired:true,no_document_overflow:true})

  page=await reset();loseRequest=true;await open(page);await page.getByRole('button',{name:'Siapkan pemeriksaan pilihan',exact:true}).click();await expect(page.locator('#panel [role=alert]')).toBeVisible();assert.equal(creations,1)
  await page.reload();await expect(page.getByText('Persiapan mengantre.',{exact:true})).toBeVisible();assert.equal(creations,1);await page.getByRole('button',{name:'Lanjutkan persiapan yang sama',exact:true}).click();await expect(page.getByText('Persiapan selesai. Pilihan belum disimpan.',{exact:true})).toBeVisible();assert.equal(creations,1)
  const requests=prepCalls().filter(c=>c.name==='erp_cp7_request_frozen_choice_preparation_v1');assert.equal(requests.length,2);assert.deepEqual(requests[0],requests[1]);finish(ids[2],{actual_connection_lost_after_controlled_enqueue:true,real_reload:true,exact_request_reused:true,actual_Native_idempotency_credit:false})

  page=await reset();state='RUNNING';await open(page);await expect(page.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible();state='FAILED';await expect(page.getByText('Persiapan gagal. Pilihan belum disimpan.',{exact:true})).toBeVisible();await expect(page.getByText(/tiga percobaan pada langkah yang sama/)).toBeVisible();const n=prepCalls().length;await page.waitForTimeout(2200);assert.equal(prepCalls().length,n)
  state='EXPIRED';await page.reload();await expect(page.getByText('Acuan sudah kedaluwarsa.',{exact:true})).toBeVisible();await expect(page.locator('[data-analog-target]')).toHaveCount(0);assert.ok(prepCalls().every(c=>c.name==='erp_cp7_get_frozen_choice_preparation_v1'));finish(ids[3],{failure_and_expiry_observed:true,no_automatic_restart:true,no_partial_success:true})

  page=await reset();state='RUNNING';await open(page);await expect(page.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible();denied=true;await expect(page.locator('#access')).not.toBeEmpty();await expect(page.locator('#panel')).toBeEmpty();const deniedCalls=calls.length;await page.waitForTimeout(2200);assert.equal(calls.length,deniedCalls);finish(ids[4],{controlled_403:true,protected_panel_removed:true,no_post_retirement_reads:true})

  page=await reset();state='RUNNING';await open(page);await expect(page.getByText('Menyiapkan data pembanding…',{exact:true})).toBeVisible();holdGet=true;await expect.poll(()=>held.length).toBe(1);const start=performance.now(),count=prepCalls().length
  await page.getByLabel('Catatan halaman lain').fill('Tetap bisa digunakan');await expect(page.locator('#panel [role=alert]')).toContainText('Hasil permintaan belum diketahui',{timeout:35000});const elapsed=performance.now()-start;assert.ok(elapsed>=29000&&elapsed<35000,'EXISTING_30S_REPLY_BOUND_CHANGED')
  await expect(page.getByRole('button',{name:'Lanjutkan persiapan yang sama',exact:true})).toBeEnabled();release();await page.waitForTimeout(2200);assert.equal(prepCalls().length,count);await expect(page.locator('[data-analog-target]')).toHaveCount(0);finish(ids[5],{real_elapsed_after_held_reply_ms:Math.round(elapsed),single_outstanding_status_read:true,monitor_stopped_without_declaring_server_failed:true,no_timeout_increased:true})
  assert.deepEqual(report.cases.map(c=>c.id),ids)
  for(const p of[panel,'scripts/cp7_frozen_choice_preparation/client/PreparedFrozenChoicePanel.tsx','scripts/cp7_frozen_choice_preparation/client/nativeFrozenChoicePreparation.ts','scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait.ts'])assert.ok(served.has(p),'ACTUAL_MODULE_NOT_SERVED:'+p)
  report.actual_served_module_graph=true;report.status='PASS'
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{release();await context?.close();await browser?.close();await server?.close();report.served_source_paths=[...served].sort();for(const p of[...served,self,contractPath,'.github/workflows/cp7-ow12b-choice-preparation-browser.yml'])report.source_sha256[p]=hash(await readFile(p));await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:report.cases.length,error:report.error,report:out}))}
