// Actual Chromium, Web Locks and tabs; controlled identity/RPC, no Native credit.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname,resolve} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'
const panel='scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel.tsx',helper='scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity.ts'
const out=process.env.CP7_FROZEN_QUANTITY_UI_REPORT_PATH??'cp6-proof/t3/FROZEN_QUANTITY_UI_BROWSER4.json'
const ids=['FROZEN_QUANTITY_UI_DESKTOP_ALL_PAGES_LABELS_UNKNOWN','FROZEN_QUANTITY_UI_MOBILE_READABLE_SOURCE_STATUS','FROZEN_QUANTITY_UI_LOST_REPLY_RELOAD_ORIGINAL_METHOD_QUERY_UUID','FROZEN_QUANTITY_UI_REAL_STORAGE_AND_ACCESS_RETIRE_HELD_PAGE']
const report={contract:'cp7.frozen-quantity-prepared-ui-browser4.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),required_case_ids:ids,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_identity:true,controlled_RPC_replies:true,actual_Native:false,actual_Auth_HTTP_credit:false,default_application_adopted:false,cutting_SAVE_qualified:false,production_go:false}
const entry=`import React from'react';import{createRoot}from'react-dom/client';import Panel from'/${panel}';import{stagedRun}from'/tests/fixtures/nativeAnalysisPages.ts';import{recoveryIdentity}from'/tests/fixtures/productionRecovery.ts';import*as recovery from'/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts';
async function main(){
const auth=structuredClone(recoveryIdentity),scope='frozen-quantity:cp6-disposable:actor-1',f=await stagedRun({targets:1200,pageSizes:[500,450,250]});Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.actor,rowVersion:1,roleRowVersion:1});auth.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');
const p=window.proof={auth,scope,recovery,f,calls:[],mode:new URL(location.href).searchParams.get('mode')??'normal',sourceReads:0,sourceEnds:0};
p.client={rpc:async(name,args)=>{p.calls.push({name,args:structuredClone(args)});
if(name==='erp_cp7_request_bounded_staged_analysis_v2'){if(p.mode==='reply-loss')throw Error('CONTROLLED_REPLY_LOST');if(p.f.pageSet.request_id!==args.p_request)p.f=await stagedRun({targets:1200,pageSizes:[500,450,250],requestId:args.p_request});return{data:p.f.job('DONE'),error:null}}
if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:p.f.pageSet,error:null};
if(name==='erp_cp7_read_staged_analysis_page_v1'){const reply={data:p.f.page(args.p_index),error:null};if(p.mode==='held-page')return await new Promise(resolve=>{p.release=()=>resolve(reply)});return reply}
if(name==='erp_cp7_check_staged_analysis_source_v1'){if(p.mode==='denied')return{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}};return{data:{source_state:'ARCHIVED_STALE',checked_at:'2026-10-25T19:00:00.123456Z'},error:null}}
throw Error('UNEXPECTED_RPC:'+name)}};
const root=createRoot(document.getElementById('root')),start=()=>{p.sourceReads++},end=()=>{p.sourceEnds++};p.render=()=>root.render(React.createElement(Panel,{query:p.f.query,onSourceReadStart:start,onSourceReadEnd:end,onClose:()=>root.unmount()}));p.render();window.ready=true;
}main().catch(error=>{window.startError=String(error)});`
const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kebutuhan produk — pengujian terpisah</title><style>body{margin:0;background:#f6f7f4;color:#172c24;font:16px system-ui}main{max-width:1200px;margin:auto;padding:12px}*{box-sizing:border-box}</style></head><body><main id="root"></main><script type="module" src="/frozen-quantity-entry.tsx"></script></body></html>'
let server,browser,context
try{
 const plugin={name:'isolated-frozen-quantity-ui',enforce:'pre',resolveId(id){if(id==='/frozen-quantity-entry.tsx')return'\0frozen-quantity-entry';if(id==='../../../src/auth/AuthProvider')return'\0controlled-auth';if(id==='../../../src/lib/supabase')return'\0controlled-rpc'},load(id){if(id==='\0frozen-quantity-entry')return entry;if(id==='\0controlled-auth')return'export const useAuth=()=>window.proof.auth';if(id==='\0controlled-rpc')return'export const getUatSupabaseClient=()=>window.proof.client'},configureServer(s){s.middlewares.use((req,res,next)=>{const path=new URL(req.url,'http://localhost').pathname;if(!['/frozen-quantity-ui','/frozen-quantity-storage'].includes(path)){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(path==='/frozen-quantity-storage'?'<!doctype html><title>Storage event peer</title>':html)})}}
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',oxc:{jsx:{runtime:'automatic',refresh:false}},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[plugin]});await server.listen()
 const origin='http://127.0.0.1:'+server.httpServer.address().port,url=origin+'/frozen-quantity-ui'
 for(const p of['/frozen-quantity-ui','/frozen-quantity-entry.tsx','/'+panel,'/'+helper]){const r=await fetch(origin+p);assert.equal(r.status,200,p);const text=await r.text();assert.ok(text.length>100);if(p==='/'+panel)assert.match(text,/(?:react\/jsx|react_jsx)/)}
 if(process.env.CP7_FROZEN_QUANTITY_UI_PREFLIGHT_ONLY==='1'){report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true}
 else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version();context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Los_Angeles'})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)))
  const ready=async(mode='normal')=>{await page.goto(url+'?mode='+mode);await page.waitForFunction(()=>window.ready===true||window.startError);assert.equal(await page.evaluate(()=>window.startError),undefined)}
  const rows=()=>page.locator('[data-quantity-target]'),click=async name=>page.getByRole('button',{name,exact:true}).click()
  const loaded=async()=>{await rows().first().waitFor();assert.equal(await rows().count(),50)}
  const stored=()=>page.evaluate(()=>{const p=window.proof;return{bytes:localStorage.getItem(p.recovery.frozenAnalysisRequestKey(p.f.actor,p.scope)),parsed:p.recovery.readFrozenAnalysisRequest(p.f.actor,p.scope)}})
  const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
  await mkdir(dirname(out),{recursive:true});await ready();await loaded();const original=await stored()
  assert.equal(original.parsed.pending.method,'cp7.bounded-analysis-request.v2');await page.getByText('Target 1–500 dari 1.200',{exact:true}).waitFor()
  assert.match(await rows().first().locator('[data-label="Produksi baru layak"]').innerText(),/Belum diketahui/);assert.match(await rows().first().locator('[data-label="Stok fisik"]').innerText(),/76/);assert.match(await rows().first().locator('[data-label="Kurang sesudah pembagian global"]').innerText(),/0/)
  await click('50 saran berikutnya');await page.getByText('Saran 51–100 dari 500 baris pada halaman target ini.',{exact:true}).waitFor();await click('Sumber berikutnya');await page.getByText('Target 501–950 dari 1.200',{exact:true}).waitFor();await click('Sumber berikutnya');await page.getByText('Target 951–1.200 dari 1.200',{exact:true}).waitFor()
  await page.getByText('Cari produk untuk melihat pembanding',{exact:true}).click();await page.getByRole('searchbox').fill('SKU-1199');await page.getByRole('button',{name:'Lihat pembanding SKU-1199',exact:true}).waitFor();assert.equal(await page.locator('[data-analog-choice]').count(),1)
  assert.deepEqual(await stored(),original);await noOverflow();await page.screenshot({path:resolve(dirname(out),'frozen-quantity-desktop.png'),fullPage:false})
  assert.equal(await page.evaluate(()=>window.proof.calls.some(c=>c.name==='erp_cp7_request_bounded_staged_analysis_v1'||c.name==='erp_cp7_capture_netting_v1')),false)
  report.cases.push({id:ids[0],status:'PASS',viewport:[1440,1000],all1200_labels_searchable:true,three_exact_source_pages:true,only50_visible_rows:true,physical76_known_zero_and_UNKNOWN_distinct:true,exact_durable_request_retained:true,no_horizontal_overflow:true})

  await page.setViewportSize({width:390,height:844});await ready();await loaded();await click('Periksa sumber kebutuhan');await page.getByText(/sumber sudah berubah; hitung kebutuhan terbaru/).waitFor();await noOverflow()
  const contrasts=await page.locator('section[aria-label="Kebutuhan seluruh produk"] button').evaluateAll(buttons=>buttons.map(button=>{const s=getComputedStyle(button),lum=color=>{const c=color.match(/[\d.]+/g).slice(0,3).map(x=>Number(x)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722},a=lum(s.color),b=lum(s.backgroundColor);return{ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),opacity:s.opacity}}));assert.ok(contrasts.length&&contrasts.every(x=>x.ratio>=4.5&&x.opacity==='1'))
  await page.screenshot({path:resolve(dirname(out),'frozen-quantity-mobile-source.png'),fullPage:false});await rows().first().screenshot({path:resolve(dirname(out),'frozen-quantity-mobile-row.png')});assert.deepEqual(await stored(),original)
  report.cases.push({id:ids[1],status:'PASS',viewport:[390,844],archived_source_explicit:true,old_quantities_immutable:true,no_horizontal_overflow:true,button_contrasts:contrasts})

  await page.evaluate(()=>localStorage.clear());await ready('reply-loss');await page.getByRole('alert').waitFor();const pending=await stored(),first=await page.evaluate(()=>window.proof.calls[0]);assert.equal(await page.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true}).isDisabled(),true)
  await ready();await loaded();assert.deepEqual(await stored(),pending);const requests=await page.evaluate(()=>window.proof.calls.filter(c=>c.name==='erp_cp7_request_bounded_staged_analysis_v2'));assert.equal(requests.length,2);assert.deepEqual(requests,[first,first])
  report.cases.push({id:ids[2],status:'PASS',actual_reload:true,controlled_reply_loss:true,exact_v2_method_query_UUID_bytes:true,server_method_reaffirmed_before_pages:true})

  await ready('held-page');await page.waitForFunction(()=>typeof window.proof.release==='function');const before=await stored(),peer=await context.newPage();await peer.goto(origin+'/frozen-quantity-storage')
  const key=await page.evaluate(()=>{const p=window.proof;return p.recovery.frozenAnalysisRequestKey(p.f.actor,p.scope)}),replacement={...before.parsed.pending,id:'00000000-0000-4000-8000-000000000999'}
  await peer.evaluate(({key,replacement})=>localStorage.setItem(key,JSON.stringify(replacement)),{key,replacement});await page.getByText('Catatan perhitungan berubah di tab lain. Periksa permintaan tersimpan.',{exact:true}).waitFor();await page.evaluate(()=>window.proof.release());await page.evaluate(()=>new Promise(requestAnimationFrame));assert.equal(await rows().count(),0);assert.deepEqual((await stored()).parsed.pending,replacement);await peer.close()
  await ready();await loaded();const retained=await stored();await page.evaluate(()=>{window.proof.mode='denied'});await click('Periksa sumber kebutuhan');await page.getByRole('alert').waitFor();assert.equal(await rows().count(),0);assert.equal(await page.getByRole('searchbox').count(),0);assert.deepEqual(await stored(),retained)
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]});assert.deepEqual(errors,[])
  report.cases.push({id:ids[3],status:'PASS',actual_tabs:2,actual_StorageEvent:true,held_page_retired:true,replacement_preserved:true,current_access_refusal_clears_quantities:true,no_remaining_locks:true})
  assert.deepEqual(report.cases.map(c=>c.id),ids);report.status='PASS';report.browser_page_errors=[]
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{
 const paths=new Set([panel,helper,'scripts/cp7_ow12b_frozen_quantity_ui_browser.mjs','scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts','tests/fixtures/nativeAnalysisPages.ts','tests/fixtures/nativeAnalysisStandin.json','tests/fixtures/productionRecovery.ts','scripts/cp7_frozen_choice_ui/client/frozen-choice.css'])
 for(const m of server?.environments.client.moduleGraph.idToModuleMap.values()??[]){if(m.file?.startsWith(process.cwd()+'/')&&!m.file.includes('/node_modules/'))paths.add(m.file.slice(process.cwd().length+1))}
 for(const p of [...paths].sort())report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
 await context?.close();await browser?.close();await server?.close();await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:report.cases.length,error:report.error,report:out}))
}
