// Real Chromium UI and storage; controlled identity/RPC, no Native or Auth credit.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {dirname,resolve} from 'node:path'
import {execFileSync} from 'node:child_process'
import {createServer} from 'vite'
import {chromium} from '@playwright/test'
const panel='scripts/cp7_frozen_choice_ui/client/NativeFrozenAnalogPanel.tsx',choice='scripts/cp7_frozen_choice_ui/client/NativeFrozenChoicePanel.tsx',fixture='scripts/cp7_frozen_choice_ui/client/fixtures.ts'
const out=process.env.CP7_FROZEN_CHOICE_UI_REPORT_PATH??'cp6-proof/t3/FROZEN_CHOICE_UI_BROWSER4.json'
const ids=['FROZEN_CHOICE_UI_DESKTOP_PAGES_FORM_EXACT_RECOVERY','FROZEN_CHOICE_UI_MOBILE_INSUFFICIENT_AND_REVIEW','FROZEN_CHOICE_UI_REAL_STORAGE_RETIRES_HELD_REPLY','FROZEN_CHOICE_UI_PERMISSION_CHANGE_RETAINS_PENDING']
const report={contract:'cp7.frozen-choice-prepared-ui-browser4.v1',head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),required_case_ids:ids,cases:[],source_sha256:{},status:'INCOMPLETE',controlled_identity:true,controlled_RPC_replies:true,actual_Native:false,actual_Auth_HTTP_credit:false,default_application_adopted:false,production_go:false}
const entry=`import React from 'react';import{createRoot}from'react-dom/client';import Panel from '/${panel}';import{frozenChoiceUIFixture}from'/${fixture}';
import{recoveryIdentity}from'/tests/fixtures/productionRecovery.ts';import*as recovery from'/scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts';
const f=frozenChoiceUIFixture(51),auth=structuredClone(recoveryIdentity),scope='product-analog:cp6-disposable';Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.context.actor,rowVersion:1,roleRowVersion:1});auth.identity.permissions.push('master.product.view','master.product.manage','warehouse.stock.view','sales.invoice.view');
const p=window.proof={f,auth,scope,recovery,calls:[],mode:'normal'};
p.client={rpc:async(name,args)=>{p.calls.push({name,args:structuredClone(args)});
if(name==='erp_cp7_read_product_analog_candidates_v2'){const r=f.reply(args.p_offset);if(p.mode==='insufficient')Object.assign(r.result,{total:0,suggested:0,candidates:[],state:'INSUFFICIENT_REVIEWABLE_HISTORY'});return{data:r,error:null}}
if(name==='erp_cp7_get_product_analog_choices_v1')return{data:f.raw,error:null};
if(name==='erp_cp7_save_product_analog_choice_v2'){const data={...f.outcome,request_id:args.p_request,reason:args.p_payload.reason};if(p.mode==='reply-loss')throw Error('CONTROLLED_REPLY_LOST');if(p.mode==='held-save')return await new Promise(resolve=>{p.release=()=>resolve({data,error:null})});return{data,error:null}}throw Error('UNEXPECTED_RPC:'+name)}};
const root=createRoot(document.getElementById('root')),lost=message=>{p.lost=message};p.render=()=>root.render(React.createElement(Panel,{context:f.context,label:'Produk baru',onClose:()=>root.unmount(),onAccessLost:lost}));p.render();window.ready=true;`
const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Produk pembanding — pengujian terpisah</title><style>body{margin:0;background:#f6f7f4;color:#172c24;font:16px system-ui}main{max-width:1100px;margin:auto;padding:16px}button{padding:9px 12px;font:inherit}*{box-sizing:border-box}</style></head><body><main id="root"></main><script type="module" src="/frozen-choice-entry.tsx"></script></body></html>'
let server,browser,context
try{
 const plugin={name:'isolated-frozen-choice-ui',enforce:'pre',resolveId(id){if(id==='/frozen-choice-entry.tsx')return'\0frozen-choice-entry';if(id==='../../../src/auth/AuthProvider')return'\0controlled-auth';if(id==='../../../src/lib/supabase')return'\0controlled-rpc'},load(id){if(id==='\0frozen-choice-entry')return entry;if(id==='\0controlled-auth')return'export const useAuth=()=>window.proof.auth';if(id==='\0controlled-rpc')return'export const getUatSupabaseClient=()=>window.proof.client'},configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url!=='/frozen-choice-ui'){next();return}res.setHeader('Content-Type','text/html;charset=utf-8');res.end(html)})}}
 server=await createServer({configFile:false,root:process.cwd(),logLevel:'error',oxc:{jsx:{runtime:'automatic',refresh:false}},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[plugin]});await server.listen()
 const origin='http://127.0.0.1:'+server.httpServer.address().port,url=origin+'/frozen-choice-ui'
 for(const p of['/frozen-choice-ui','/frozen-choice-entry.tsx','/'+panel,'/'+choice,'/'+fixture]){const r=await fetch(origin+p);assert.equal(r.status,200,p);const text=await r.text();assert.ok(text.length>100);if(p==='/'+panel)assert.match(text,/(?:react\/jsx|react_jsx)/)}
 if(process.env.CP7_FROZEN_CHOICE_UI_PREFLIGHT_ONLY==='1'){report.status='SOURCE_SERVING_ONLY';report.source_serving_verified=true}
 else{
  browser=await chromium.launch({headless:true});report.browser_version=browser.version();context=await browser.newContext({viewport:{width:1365,height:900},timezoneId:'America/Los_Angeles'})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)))
  const go=async()=>{await page.goto(url);await page.waitForFunction(()=>window.ready);await page.locator('[data-analog-target]').first().waitFor()}
  const click=async name=>page.getByRole('button',{name,exact:true}).click(),mode=async v=>page.evaluate(v=>{window.proof.mode=v},v)
  const stored=()=>page.evaluate(()=>{const p=window.proof;return p.recovery.readAnalogChoiceRequest(p.scope,p.f.context.actor,p.f.context.targetKey)})
  const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
  const open=async()=>{await click('Atur pilihan pembanding');await page.getByRole('button',{name:'Baca ulang pilihan tersimpan',exact:true}).waitFor();await page.getByText('Belum ada pilihan yang dikonfirmasi.',{exact:true}).waitFor()}
  const fill=async()=>{await page.getByLabel('Produk pembanding',{exact:true}).selectOption({label:'PEMBANDING-0 · Produk pembanding 0'});await page.getByLabel('Skala terhadap produk pembanding',{exact:true}).fill('1.25');await page.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Ukuran, model dan kain telah diperiksa');await page.getByRole('checkbox').check()}
  await mkdir(dirname(out),{recursive:true});await go();assert.equal(await page.locator('[data-analog-target]').count(),50);await click('50 kandidat berikutnya');await page.getByText('Kandidat 51–51 dari 51.',{exact:true}).waitFor();assert.equal(await page.locator('[data-analog-target]').count(),1);await click('50 kandidat sebelumnya');await page.getByText('Kandidat 1–50 dari 51.',{exact:true}).waitFor()
  await page.screenshot({path:resolve(dirname(out),'frozen-choice-desktop-candidates.png'),fullPage:false});await open();await fill();await noOverflow();await mode('reply-loss');await click('Simpan pilihan pembanding');await page.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true}).waitFor();const pending=await stored(),first=await page.evaluate(()=>window.proof.calls.find(c=>c.name==='erp_cp7_save_product_analog_choice_v2'))
  assert.equal(pending.pending.payload.contract_version,'cp7.product-analog-choice-command.v2');assert.equal(pending.pending.review.context.reference.capturedAt,'2026-01-20T12:00:00.123456Z');await page.locator('.native-analog-choice').screenshot({path:resolve(dirname(out),'frozen-choice-desktop-recovery.png')})
  await go();await open();await click('Periksa hasil konfirmasi yang sama');await page.getByText(/Bukti konfirmasi revisi 1 tersimpan/).waitFor();assert.equal((await stored()).pending,null);assert.deepEqual(await page.evaluate(()=>window.proof.calls.find(c=>c.name==='erp_cp7_save_product_analog_choice_v2')),first)
  report.cases.push({id:ids[0],status:'PASS',viewport:[1365,900],all51_candidates_paged:true,actual_form_submission:true,exact_method_UUID_payload_review_recovery:true,original_microseconds:true,no_horizontal_overflow:true})

  await page.setViewportSize({width:390,height:844});await go();await mode('insufficient');await click('50 kandidat berikutnya');await page.getByRole('alert').waitFor();await click('Baca ulang kandidat');await page.getByText('Data pembanding belum cukup. Nilai yang belum diketahui tetap belum diketahui.',{exact:true}).waitFor();await open();assert.equal(await page.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).isDisabled(),true);await noOverflow();await page.screenshot({path:resolve(dirname(out),'frozen-choice-mobile-insufficient.png'),fullPage:true})
  await go();await open();await fill();await noOverflow();await page.locator('.native-analog-choice').screenshot({path:resolve(dirname(out),'frozen-choice-mobile-review.png')});report.cases.push({id:ids[1],status:'PASS',viewport:[390,844],insufficient_not_zero:true,explicit_scale_reason_review_required:true,no_horizontal_overflow:true})

  await mode('held-save');await click('Simpan pilihan pembanding');await page.waitForFunction(()=>typeof window.proof.release==='function');const old=(await stored()).pending;const other=await context.newPage();await other.goto(url);await other.waitForFunction(()=>window.ready)
  const replacement=await other.evaluate(old=>{const p=window.proof,r={...old,requestId:crypto.randomUUID()};localStorage.setItem(p.recovery.analogChoiceRequestKey(p.scope,p.f.context.actor,p.f.context.targetKey),JSON.stringify(r));return r},old)
  await page.getByText('Catatan konfirmasi berubah di tab lain. Baca ulang pilihan dan periksa permintaan tersimpan.',{exact:true}).waitFor();await page.evaluate(()=>window.proof.release());await page.evaluate(()=>new Promise(requestAnimationFrame));assert.deepEqual((await stored()).pending,replacement);assert.equal(await page.getByText(/Bukti konfirmasi revisi 1 tersimpan/).count(),0);await other.close()
  report.cases.push({id:ids[2],status:'PASS',actual_tabs:2,actual_storage_event:true,external_replacement_retained_exactly:true,late_response_retired:true})

  await go();await open();await mode('held-save');await click('Periksa hasil konfirmasi yang sama');await page.waitForFunction(()=>typeof window.proof.release==='function');const held=await stored()
  await page.evaluate(()=>{const p=window.proof;p.auth.identity.permissions=p.auth.identity.permissions.filter(x=>x!=='master.product.manage');p.render()});await page.locator('[data-analog-target]').first().waitFor();await open();await page.getByText('Izin mengelola produk diperlukan untuk mengubah pilihan.',{exact:true}).waitFor();await page.evaluate(()=>window.proof.release());await page.evaluate(()=>new Promise(requestAnimationFrame))
  assert.deepEqual(await stored(),held);assert.equal(await page.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true}).isDisabled(),true);assert.equal(await page.getByText(/Bukti konfirmasi revisi 1 tersimpan/).count(),0)
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]});assert.deepEqual(errors,[]);report.cases.push({id:ids[3],status:'PASS',permission_change_retires_held_reply:true,exact_pending_command_retained:true,no_remaining_locks:true})
  assert.deepEqual(report.cases.map(c=>c.id),ids);report.status='PASS';report.browser_page_errors=[]
 }
}catch(error){report.error=String(error);report.stack=error.stack;process.exitCode=1}
finally{
 const paths=new Set([panel,choice,fixture,'scripts/cp7_ow12b_frozen_choice_ui_browser.mjs','scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts','scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts','tests/fixtures/nativeProductAnalog.ts','tests/fixtures/nativeProductAnalogChoice.ts','tests/fixtures/nativeTargetDemandSql.json','tests/fixtures/productionRecovery.ts','scripts/cp7_frozen_choice_ui/client/frozen-choice.css'])
 for(const m of server?.environments.client.moduleGraph.idToModuleMap.values()??[]){if(m.file?.startsWith(process.cwd()+'/')&&!m.file.includes('/node_modules/'))paths.add(m.file.slice(process.cwd().length+1))}
 for(const p of [...paths].sort())report.source_sha256[p]=createHash('sha256').update(await readFile(p)).digest('hex')
 await context?.close();await browser?.close();await server?.close();await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:report.cases.length,error:report.error,report:out}))
}
