import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// K4 in the real UI: the server runner is registered with the real pg_cron for this disposable copy (every 5 seconds,
// labelled TEST_SCHEDULE_OVERRIDE). A staged analysis is started by one click; the page never runs a unit (its step
// requests are held open, as if the tab were closed right after asking), the panel says the server goes on and the
// page may be closed. Desktop: the tab is closed. Mobile: "Berhenti memantau" is pressed. The server finishes the
// job with no page; opening the panel again shows the result of the same job and run (same request UUID, same page-set
// identity) without a new request or a step, every unit stored once.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_k4_runner_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const SERVER='Server juga menjalankan analisis ini, jadi halaman boleh ditutup; hasilnya tampil saat bagian ini dibuka lagi.'
const STAGED_RPCS=['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_get_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
// Stage markers on stderr (job log only, no result): run 38114007484 stayed silent for 80 minutes inside the mobile
// case without saying where; a later silence names its last stage. A wait that has no Playwright limit is bounded.
const stage=(mobile,name)=>console.error(JSON.stringify({k4r_stage:name,mobile,at:new Date().toISOString()}))
const bounded=(promise,ms,code)=>{let t;return Promise.race([promise,new Promise((_,no)=>{t=setTimeout(()=>no(new Error(code)),ms)})]).finally(()=>clearTimeout(t))}
// Each reply is recorded when it arrives, in arrival order; its body is read asynchronously and awaited (settle)
// before any assertion reads it. Requests are recorded when sent (a held step never gets a reply).
function watch(page){
 const calls=[],sent=[]
 page.on('request',r=>{const name=STAGED_RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)sent.push(name)})
 page.on('response',r=>{const name=STAGED_RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,status:r.status(),body:null,ready:r.json().catch(()=>null)})})
 const settle=async(ui,name)=>{await ui.expect.poll(()=>calls.some(c=>c.name===name),{timeout:60000}).toBe(true);for(const c of calls)if(c.ready){c.body=await bounded(c.ready,60000,'K4R_RESPONSE_BODY_NOT_READ');delete c.ready}}
 return{calls,sent,settle}
}
async function journey(ui,today,mobile,other=false){
 if(other)execFileSync('python',['../auditor/scripts/cp7_p19_report_v2_browser_fixture.py','prepare'],{input:JSON.stringify({today}),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024})
 const user=await ui.login('OWNER',{label:'k4r-'+(other?'other-':'')+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),suffix=(other?'OTHER_':'')+(mobile?'MOBILE':'DESKTOP'),shots=[]
 let page=user.page,panel,runner=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  stage(mobile,'LOGGED_IN');runner=fixture('runner_on',{});stage(mobile,'RUNNER_ON')
  let w=watch(page)
  // The page never runs a unit: every step request is held open and never answered.
  await page.route('**/rpc/erp_cp7_step_staged_analysis_v1',()=>{})
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  await w.settle(ui,'erp_cp7_request_staged_analysis_v1');stage(mobile,'REQUESTED')
  const first=w.calls.find(c=>c.name==='erp_cp7_request_staged_analysis_v1');assert.equal(first.status,200);assert.equal(first.body.state,'RUNNING')
  assert.equal(first.body.server_runner.active,true,'K4R_RUNNER_NOT_REPORTED');const key=first.body.request_id
  await ui.expect(panel.getByRole('status').filter({hasText:SERVER})).toBeVisible({timeout:30000})
  shots.push(await shot(ui,page,`K4R_${suffix}_SERVER_RUNS.png`))
  const appUrl=page.url();stage(mobile,'SERVER_TEXT_SHOWN')
  if(mobile){
   await panel.getByRole('button',{name:'Berhenti memantau (server tetap menghitung)',exact:true}).click()
   await ui.expect(panel.getByRole('status').filter({hasText:'server tetap menjalankan analisis bertahap ini sampai selesai'})).toBeVisible()
   shots.push(await shot(ui,page,`K4R_${suffix}_STOPPED_WATCHING.png`))
  }else await page.close()
  stage(mobile,mobile?'STOPPED_WATCHING':'TAB_CLOSED')
  // The server finishes the job with no page.
  let state
  await ui.expect.poll(()=>{state=fixture('state',{actor:user.user.id});return state.jobs.at(-1)?.state},{timeout:240000,intervals:[2000]}).toBe('DONE')
  const job=state.jobs.at(-1);stage(mobile,'DONE_BY_SERVER');assert.equal(state.jobs.length,1,JSON.stringify(state));assert.equal(job.request_id,key)
  assert.equal(job.units_done,job.unit_count);assert.equal(job.distinct_units,job.unit_count);assert.equal(job.stored_units,job.unit_count,'K4R_UNIT_STORED_TWICE')
  assert.equal(w.sent.filter(n=>n==='erp_cp7_step_staged_analysis_v1').length>=1,true);assert.equal(w.calls.filter(c=>c.name==='erp_cp7_step_staged_analysis_v1').length,0,'K4R_PAGE_RAN_A_UNIT')
  // Open again: the same job's result, no new request and no step.
  if(mobile){await page.unroute('**/rpc/erp_cp7_step_staged_analysis_v1');w=watch(page);await page.reload()}
  else{page=await user.context.newPage();w=watch(page);await page.goto(appUrl)}
  stage(mobile,'REOPENED');panel=await openPanel(page)
  const region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(region).toBeVisible({timeout:90000})
  await w.settle(ui,'erp_cp7_read_staged_analysis_pages_v1');stage(mobile,'PAGES_READ')
  const got=w.calls.find(c=>c.name==='erp_cp7_get_staged_analysis_v1');assert.ok(got,'K4R_REOPEN_DID_NOT_READ_STATUS');assert.equal(got.body.state,'DONE');assert.equal(got.body.run_id,job.run_id)
  const ps=w.calls.filter(c=>c.name==='erp_cp7_read_staged_analysis_pages_v1'&&c.status===200).at(-1);assert.ok(ps,'K4R_NO_PAGE_SET')
  assert.equal(ps.body.run_id,job.run_id);assert.equal(ps.body.identity_hash,job.identity_hash,'K4R_REOPENED_IDENTITY_DIFFERS')
  assert.equal(w.sent.filter(n=>n==='erp_cp7_request_staged_analysis_v1'||n==='erp_cp7_step_staged_analysis_v1').length,0,'K4R_REOPEN_RECOMPUTED')
  assert.equal(w.calls.filter(c=>c.status>=400).length,0,JSON.stringify(w.calls.filter(c=>c.status>=400)))
  assert.equal(fixture('state',{actor:user.user.id}).jobs.length,1,'K4R_SECOND_JOB')
  shots.push(await shot(ui,page,`K4R_${suffix}_REOPENED_DONE_BY_SERVER.png`))
  let otherResult=null
  if(other){const result=await otherWork(ui,user,page,suffix,shots);page=result.page;otherResult=result.evidence}
  const off=fixture('runner_off',{});runner=null;stage(mobile,'RUNNER_OFF')
  assert.equal(off.removed.length,1);assert.ok(off.cron_runs>=1&&off.cron_runs===off.cron_runs_succeeded,JSON.stringify(off))
  return{status:'PASS',pg_cron:true,test_schedule_override:'5 seconds',closed:mobile?'STOPPED_WATCHING':'TAB_CLOSED',page_units:0,server_units:job.unit_count,
   same_request_and_run:true,identity_hash:job.identity_hash,no_request_or_step_on_reopen:true,every_unit_stored_once:true,cron_runs:off.cron_runs,no_horizontal_scroll:true,screenshots:shots,...(other?{other_work:otherResult}:{})}
 }catch(e){writeFileSync(`cp6-proof/t3/K4R_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/K4R_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{if(runner)try{fixture('runner_off',{})}catch{/* the case already failed; the copy is dropped after the run */}stage(mobile,'CLOSING');await bounded(user.context.close(),60000,'K4R_CONTEXT_CLOSE_TIMEOUT');stage(mobile,'CLOSED')}
}
// Real pg_cron is already active on the disposable copy. Close the tab after
// each request is committed and before the page can run a later unit. Reopen
// through the actual UI; all result reads keep the same job/run identities.
async function otherWork(ui,user,startPage,suffix,shots){
 let page=startPage
 const appUrl=page.url(),state=()=>fixture('other_state',{actor:user.user.id})
 // Observe before navigation: mount recovery is part of reopening too.
 const reopen=async()=>{page=await user.context.newPage();const calls=watchOther();await page.goto(appUrl);await openPanel(page);await ui.expect(page.getByRole('region',{name:'Hasil analisis bertahap',exact:true})).toBeVisible({timeout:90000});return calls}
 const response=(name,action)=>Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),action()]).then(async([r])=>{assert.equal(r.status(),200);return r.json()})
 const watchOther=()=>{const calls=[];page.on('request',r=>{const name=r.url().split('/rpc/')[1];if(name)calls.push(name)});return calls}
 // Business report: only publish; every page step is held before transport.
 console.error(JSON.stringify({ow02_stage:'REPORT_REQUEST',suffix}))
 await page.route('**/rpc/erp_cp7_step_report_v2',()=>{})
 let report=page.getByRole('region',{name:'Laporan analisis bertahap',exact:true})
 await report.getByLabel('Judul laporan bertahap',{exact:true}).fill('OW-02 laporan '+suffix)
 await report.getByLabel('Alasan laporan bertahap',{exact:true}).fill('Bukti laporan dilanjutkan server setelah tab ditutup')
 await report.getByLabel('Laporan bertahap sudah ditinjau',{exact:true}).check()
 const asked=await response('erp_cp7_publish_report_v2',()=>report.getByRole('button',{name:'Buat laporan dari analisis ini',exact:true}).click())
 assert.equal(asked.state,'RUNNING');await page.close()
 console.error(JSON.stringify({ow02_stage:'REPORT_TAB_CLOSED',suffix}))
 await ui.expect.poll(()=>state().reports.at(-1)?.state,{timeout:180000,intervals:[2000]}).toBe('DONE')
 const saved=state().reports.at(-1);assert.equal(saved.request_id,asked.request_id);assert.equal(saved.identity_hash,asked.identity_hash)
 assert.equal(saved.units_done,saved.unit_count);assert.equal(saved.sections,saved.page_count);assert.equal(saved.publications,1)
 const reportCalls=await reopen();report=page.getByRole('region',{name:'Laporan analisis bertahap',exact:true})
 await report.getByRole('button',{name:'Periksa hasil laporan yang tertunda',exact:true}).click()
 await ui.expect(report.getByRole('article',{name:'Isi laporan bertahap',exact:true})).toHaveAttribute('data-report-id',saved.publication_id,{timeout:60000})
 const article=report.getByRole('article',{name:'Isi laporan bertahap',exact:true})
 await ui.expect(article).toContainText(saved.run_id);await ui.expect(article).toContainText(saved.identity_hash);await ui.expect(article).toContainText(saved.report_hash)
 await ui.expect(article.getByLabel('Ringkasan laporan bertahap',{exact:true})).toHaveText(saved.summary)
 assert.equal(reportCalls.includes('erp_cp7_step_report_v2')||reportCalls.includes('erp_cp7_publish_report_v2'),false)
 shots.push(await shot(ui,page,`K4R_${suffix}_REPORT_REOPENED.png`))
 console.error(JSON.stringify({ow02_stage:'REPORT_REOPENED_SAME_RESULT',suffix}))
 // Condition set: the first call creates it; all later page units are held.
 let steps=0
 await page.route('**/rpc/erp_cp7_step_reminder_conditions_v2',route=>++steps===1?route.continue():undefined)
 let rem=page.getByRole('region',{name:'Pengingat dari analisis bertahap',exact:true})
 const preparing=await response('erp_cp7_step_reminder_conditions_v2',()=>rem.getByRole('button',{name:'Siapkan daftar pengingat',exact:true}).click())
 assert.equal(preparing.state,'RUNNING');assert.equal(preparing.units_done,1);await page.close()
 console.error(JSON.stringify({ow02_stage:'REMINDER_TAB_CLOSED',suffix}))
 await ui.expect.poll(()=>state().reminders.at(-1)?.state,{timeout:180000,intervals:[2000]}).toBe('DONE')
 const ready=state().reminders.at(-1);assert.equal(ready.run_id,preparing.run_id);assert.equal(ready.identity_hash,preparing.identity_hash)
 assert.equal(ready.units_done,ready.unit_count);assert.match(ready.set_hash,/^[0-9a-f]{64}$/);assert.equal(ready.claims,0)
 const remCalls=await reopen();rem=page.getByRole('region',{name:'Pengingat dari analisis bertahap',exact:true})
 const workspace=await response('erp_cp7_get_reminder_workspace_v2',()=>rem.getByRole('button',{name:'Muat hasil pengingat tersimpan',exact:true}).click())
 await ui.expect(rem).toHaveAttribute('data-set-state','DONE')
 assert.equal(workspace.conditions.set_hash,ready.set_hash);assert.equal(remCalls.includes('erp_cp7_step_reminder_conditions_v2'),false)
 assert.equal(remCalls.some(n=>n.includes('claim_reminder')||n.includes('finish_reminder')),false)
 shots.push(await shot(ui,page,`K4R_${suffix}_REMINDERS_REOPENED.png`))
 console.error(JSON.stringify({ow02_stage:'REMINDER_REOPENED_SAME_RESULT',suffix}))
 // Single background analysis: request is committed, worker call never sent.
 await page.route('**/rpc/erp_cp7_run_analysis_job_v1',()=>{})
 const panel=page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
 const analysis=await response('erp_cp7_request_operational_analysis_job_v1',()=>panel.getByRole('button',{name:'Hitung di latar belakang',exact:true}).click())
 assert.equal(analysis.state,'WAITING');await page.close()
 console.error(JSON.stringify({ow02_stage:'SINGLE_TAB_CLOSED',suffix}))
 await ui.expect.poll(()=>state().analyses.at(-1)?.state,{timeout:180000,intervals:[2000]}).toBe('DONE')
 const done=state().analyses.at(-1);assert.equal(done.request_id,analysis.request_id);assert.equal(done.documents,1)
 page=await user.context.newPage();const analysisCalls=watchOther();await page.goto(appUrl);await openPanel(page)
 await ui.expect(page.locator('.native-analysis-result')).toBeVisible({timeout:90000})
 await ui.expect(page.locator('.native-analysis-run span')).toHaveText(done.run_id)
 await ui.expect(page.locator('.native-analysis-result')).toHaveAttribute('data-semantic-hash',done.semantic_hash)
 await ui.expect(page.locator('.native-analysis-result .responsive-table').first().locator('tbody tr')).toHaveCount(done.targets_total)
 assert.equal(analysisCalls.some(n=>n==='erp_cp7_run_analysis_job_v1'||n==='erp_cp7_request_operational_analysis_job_v1'||n==='erp_cp7_request_analysis_job_v1'),false)
 const final=state();assert.deepEqual([final.reports.length,final.reminders.length,final.analyses.length],[1,1,1])
 assert.equal(final.analyses[0].run_id,done.run_id);assert.equal(final.reminders[0].claims,0)
 shots.push(await shot(ui,page,`K4R_${suffix}_SINGLE_ANALYSIS_REOPENED.png`))
 console.error(JSON.stringify({ow02_stage:'SINGLE_REOPENED_SAME_RESULT',suffix}))
 return{page,evidence:{actual_tabs_closed:3,report_request:asked.request_id,report_run:saved.run_id,publication:saved.publication_id,
  reminder_run:ready.run_id,condition_set_hash:ready.set_hash,analysis_request:analysis.request_id,analysis_run:done.run_id,
  page_report_units:0,page_reminder_units:1,page_analysis_workers:0,one_result_each:true,no_claim_or_send:true}}
}
export function cases(ui,today){return[['K4R_BROWSER_DESKTOP_CLOSED_PAGE_FINISHES',()=>journey(ui,today,false)],['K4R_BROWSER_MOBILE_CLOSED_PAGE_FINISHES',()=>journey(ui,today,true)],
 ['K4R_BROWSER_DESKTOP_OTHER_WORK_CLOSED',()=>journey(ui,today,false,true)],['K4R_BROWSER_MOBILE_OTHER_WORK_CLOSED',()=>journey(ui,today,true,true)]]}
