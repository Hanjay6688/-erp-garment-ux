// Actual prepared React panel in Chromium; controlled identity/RPC, no Auth or Native credit.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname,resolve} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'

const panel='scripts/cp7_frozen_analysis_work_v2/client/NativeFrozenSchedulePanel.tsx',form='scripts/cp7_frozen_analysis_work_v2/client/FrozenScheduleForm.tsx'
const actor='11111111-1111-4111-8111-111111111111',scope='work-schedule:cp6-disposable'
const out=process.env.CP7_FROZEN_WORK_UI_REPORT_PATH??'cp6-proof/t3/FROZEN_WORK_UI_BROWSER4.json'
const ids=['FROZEN_WORK_UI_DESKTOP_PENDING_CUSTOMER_AND_EXACT_SAVE_RECOVERY','FROZEN_WORK_UI_MOBILE_LAYOUT_UNKNOWN_AND_STALE_REVIEW','FROZEN_WORK_UI_REAL_STORAGE_EVENT_RETIRES_PENDING_REPLY','FROZEN_WORK_UI_PERMISSION_CHANGE_RETIRES_HELD_SAVE']
const report={contract:'cp7.frozen-work-prepared-ui-browser4.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),required_case_ids:ids,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_identity:true,controlled_RPC_replies:true,actual_Native:false,actual_Auth_HTTP_credit:false,default_application_adopted:false,production_go:false}
const entry=`import React from 'react';import{createRoot}from'react-dom/client';import Panel from '/${panel}';
import{recoveryIdentity}from'/tests/fixtures/productionRecovery.ts';
import{boundedWorkspaceWire,boundedScheduleOutcome,scheduleJobWire,planningQuery,scheduleConfig}from'/tests/fixtures/nativeProductionPlanning.ts';
import * as work from '/scripts/cp7_frozen_analysis_work_v2/client/nativeFrozenWork.ts';
import * as analysis from '/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts';
const actor=${JSON.stringify(actor)},scope=${JSON.stringify(scope)},v2={bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2'};
const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:actor,rowVersion:1,roleRowVersion:1});auth.identity.permissions.push('master.product.view','master.product.manage','production.wip.view','warehouse.stock.view','sales.invoice.view');
const w=(id)=>({...boundedWorkspaceWire(id,true),...v2,contract_version:'cp7.planning-schedule-staged-bounded.v2',history_input_coverage:'PENDING'});
const result=(id)=>({...boundedScheduleOutcome(id,'2'),...v2,contract_version:'cp7.planning-schedule-staged-bounded-outcome.v2'});
const p=window.proof={auth,work,analysis,actor,scope,planningQuery,scheduleConfig,calls:[],mode:'normal',began:0,ended:0};
p.client={rpc:async(name,args)=>{p.calls.push({name,args:structuredClone(args)});if(name==='erp_cp7_request_bounded_staged_analysis_v2')return{data:scheduleJobWire(args.p_request),error:null};
if(name==='erp_cp7_get_staged_production_schedule_v1'){let data=w(args.p_source_request);if(p.mode==='held-read')return await new Promise(r=>{p.release=()=>r({data,error:null})});if(p.mode==='unknown')Object.assign(data,{production_capture_state:'UNKNOWN',position_requirements:[]});if(p.mode==='new-revision'){data.revision='2';data.plan.revision='2';data.plan.config.unit_minutes='4'}return{data,error:null}}
if(name==='erp_cp7_save_staged_production_schedule_v1'){if(p.mode==='reply-loss')throw Error('CONTROLLED_REPLY_LOST');if(p.mode==='held-save')return await new Promise(r=>{p.release=()=>r({data:result(args.p_request),error:null})});return{data:result(args.p_request),error:null}}throw Error('UNEXPECTED_RPC:'+name)}};
const root=createRoot(document.getElementById('root')),start=()=>{p.began++},end=()=>{p.ended++};p.render=()=>root.render(React.createElement(Panel,{query:planningQuery,onSourceReadStart:start,onSourceReadEnd:end,onClose:()=>root.unmount()}));p.render();window.ready=true;`
const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jadwal produksi — pengujian terpisah</title><style>body{margin:0;background:#f6f7f4;color:#172c24;font:16px system-ui}main{max-width:1100px;margin:auto;padding:16px}button{padding:9px 12px;font:inherit}h2{margin-top:0}.eyebrow{font-size:12px;letter-spacing:.06em}*{box-sizing:border-box}</style></head><body><main id="root"></main><script type="module" src="/frozen-work-entry.tsx"></script></body></html>'
let server,browser,context
try{
 const plugin={name:'isolated-frozen-work-ui',enforce:'pre',resolveId(id){
  if(id==='/frozen-work-entry.tsx')return'\0frozen-work-entry'
  if(id==='../../../src/auth/AuthProvider')return'\0controlled-auth'
  if(id==='../../../src/lib/supabase')return'\0controlled-rpc'
 },load(id){if(id==='\0frozen-work-entry')return entry;if(id==='\0controlled-auth')return'export const useAuth=()=>window.proof.auth';if(id==='\0controlled-rpc')return'export const getUatSupabaseClient=()=>window.proof.client'},configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url!=='/frozen-work-ui'){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(html)})}}
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',oxc:{jsx:{runtime:'automatic',refresh:false}},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[plugin]})
 await server.listen();const origin='http://127.0.0.1:'+server.httpServer.address().port,url=origin+'/frozen-work-ui'
 for(const p of['/frozen-work-ui','/frozen-work-entry.tsx','/'+panel,'/'+form]){const r=await fetch(origin+p);assert.equal(r.status,200,p);const text=await r.text();assert.ok(text.length>100);if(p==='/'+panel)assert.match(text,/(?:react\/jsx|react_jsx)/)}
 if(process.env.CP7_FROZEN_WORK_UI_PREFLIGHT_ONLY==='1'){report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true}
 else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version();context=await browser.newContext({viewport:{width:1365,height:900}})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)));const go=async()=>{await page.goto(url);await page.waitForFunction(()=>window.ready);await page.getByRole('button',{name:'Ambil stok proses terbaru',exact:true}).waitFor()}
  const click=async name=>page.getByRole('button',{name,exact:true}).click(),mode=async value=>page.evaluate(value=>{window.proof.mode=value},value)
  const saved=async()=>page.evaluate(()=>window.proof.work.readFrozenScheduleRequest(window.proof.scope,window.proof.actor))
  const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
  await mkdir(dirname(out),{recursive:true});await go();await click('Ambil stok proses terbaru');await page.locator('form').waitFor()
  assert.match(await page.locator('section').innerText(),/Riwayat stok sedang disiapkan/);assert.match(await page.locator('section').innerText(),/tidak menambah stok perusahaan/);await noOverflow()
  await page.getByRole('textbox',{name:'Alasan jadwal',exact:true}).fill('Browser checked original schedule');await mode('reply-loss');await click('Simpan jadwal yang diperiksa')
  await page.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true}).waitFor();const held=await saved(),original=await page.evaluate(()=>window.proof.calls.at(-1))
  assert.equal(held.pending.sourceMethod,'FROZEN_V2');assert.equal(held.pending.payload.config.through_at,'2026-10-02T12:00:00.123456Z');assert.deepEqual(held.pending.payload.config,await page.evaluate(()=>window.proof.scheduleConfig))
  await page.screenshot({path:resolve(dirname(out),'frozen-schedule-desktop.png'),fullPage:true});await go();await click('Ulangi simpan jadwal yang sama');await page.getByText('Jadwal tersimpan. Ambil sumber terbaru untuk memeriksa versi jadwal.',{exact:true}).waitFor()
  assert.deepEqual(await page.evaluate(()=>window.proof.calls.at(-1)),original);assert.equal((await saved()).pending,null)
  report.cases.push({id:ids[0],status:'PASS',viewport:[1365,900],exact_reload_recovery_and_microseconds:true,actual_form_submission:true,no_horizontal_overflow:true})

  await page.setViewportSize({width:390,height:844});await go();await mode('unknown');await click('Ambil stok proses terbaru');await page.getByText('Jumlah stok proses belum dapat dicocokkan. Jadwal belum bisa disimpan.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).isDisabled(),true);await noOverflow()
  await go();await click('Ambil stok proses terbaru');await page.locator('form').waitFor();await page.getByRole('textbox',{name:'Waktu satu PCS baru',exact:true}).fill('3');await mode('new-revision');await click('Periksa sumber stok proses');await page.getByRole('button',{name:'Gunakan sumber jadwal terbaru',exact:true}).waitFor()
  assert.equal(await page.getByRole('textbox',{name:'Waktu satu PCS baru',exact:true}).inputValue(),'3');assert.equal(await page.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).isDisabled(),true);await click('Gunakan sumber jadwal terbaru');assert.equal(await page.getByRole('textbox',{name:'Waktu satu PCS baru',exact:true}).inputValue(),'4');await noOverflow()
  await page.screenshot({path:resolve(dirname(out),'frozen-schedule-mobile.png'),fullPage:true});report.cases.push({id:ids[1],status:'PASS',viewport:[390,844],UNKNOWN_not_zero:true,dirty_form_preserved_until_explicit_adoption:true,no_horizontal_overflow:true})

  await go();await mode('held-read');await click('Ambil stok proses terbaru');await page.waitForFunction(()=>typeof window.proof.release==='function');const other=await context.newPage();await other.goto(url);await other.waitForFunction(()=>window.ready)
  const replacement=await other.evaluate(()=>{const p=window.proof,r={id:crypto.randomUUID(),actor:p.actor,q:p.planningQuery,method:p.analysis.FROZEN_ANALYSIS_REQUEST};localStorage.setItem(p.analysis.frozenAnalysisRequestKey(p.actor,p.scope),JSON.stringify(r));return r})
  await page.getByText('Catatan jadwal berubah di tab lain. Periksa permintaan tersimpan dan sumber terbaru.',{exact:true}).waitFor();await page.evaluate(()=>window.proof.release());await page.evaluate(()=>new Promise(requestAnimationFrame))
  assert.equal(await page.locator('form').count(),0);assert.deepEqual(await page.evaluate(()=>window.proof.analysis.readFrozenAnalysisRequest(window.proof.actor,window.proof.scope).pending),replacement);assert.deepEqual(await page.evaluate(()=>[window.proof.began,window.proof.ended]),[1,1]);await other.close()
  report.cases.push({id:ids[2],status:'PASS',actual_tabs:2,actual_storage_event:true,late_reply_ignored:true,replacement_retained_exactly:true})

  await go();await click('Ulangi pembacaan stok proses');await page.locator('form').waitFor();await page.getByRole('textbox',{name:'Alasan jadwal',exact:true}).fill('held save');await mode('held-save');await click('Simpan jadwal yang diperiksa');await page.waitForFunction(()=>typeof window.proof.release==='function');const heldSave=await saved()
  await page.evaluate(()=>{const p=window.proof;p.auth.identity.permissions=p.auth.identity.permissions.filter(x=>x!=='master.product.manage');p.render()});await page.getByText('Hak mengubah aturan produk diperlukan untuk menyimpan jadwal.',{exact:true}).waitFor();await page.evaluate(()=>window.proof.release());await page.evaluate(()=>new Promise(requestAnimationFrame))
  assert.equal(await page.locator('form').count(),0);assert.deepEqual(await saved(),heldSave);assert.equal(await page.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true}).isDisabled(),true);assert.deepEqual(await page.evaluate(()=>[window.proof.began,window.proof.ended]),[2,2]);assert.deepEqual(errors,[])
  const locks=await page.evaluate(()=>navigator.locks.query());assert.deepEqual(locks,{held:[],pending:[]});report.cases.push({id:ids[3],status:'PASS',held_reply_retired_on_permission_change:true,exact_durable_save_retained:true,no_remaining_locks:true})
  assert.deepEqual(report.cases.map(c=>c.id),ids);report.status='PASS';report.browser_page_errors=[]
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{
 const paths=new Set([panel,form,'scripts/cp7_ow12b_frozen_work_ui_browser.mjs','scripts/cp7_frozen_analysis_work_v2/client/nativeFrozenWork.ts','scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts','tests/fixtures/nativeProductionPlanning.ts','tests/fixtures/productionRecovery.ts','src/nativeProductionPlanning.ts','src/native-production-planning.css'])
 for(const m of server?.environments.client.moduleGraph.idToModuleMap.values()??[]){if(m.file?.startsWith(process.cwd()+'/')&&!m.file.includes('/node_modules/'))paths.add(m.file.slice(process.cwd().length+1))}
 for(const p of [...paths].sort())report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
 await context?.close();await browser?.close();await server?.close();await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:report.cases.length,error:report.error,report:out}))
}
