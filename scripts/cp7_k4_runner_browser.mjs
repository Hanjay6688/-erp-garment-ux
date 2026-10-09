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
// Each reply is recorded when it arrives, in arrival order; its body is read asynchronously and awaited (settle)
// before any assertion reads it. Requests are recorded when sent (a held step never gets a reply).
function watch(page){
 const calls=[],sent=[]
 page.on('request',r=>{const name=STAGED_RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)sent.push(name)})
 page.on('response',r=>{const name=STAGED_RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,status:r.status(),body:null,ready:r.json().catch(()=>null)})})
 const settle=async(ui,name)=>{await ui.expect.poll(()=>calls.some(c=>c.name===name),{timeout:60000}).toBe(true);for(const c of calls)if(c.ready){c.body=await c.ready;delete c.ready}}
 return{calls,sent,settle}
}
async function journey(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'k4r-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),suffix=mobile?'MOBILE':'DESKTOP',shots=[]
 let page=user.page,panel,runner=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  runner=fixture('runner_on',{})
  let w=watch(page)
  // The page never runs a unit: every step request is held open and never answered.
  await page.route('**/rpc/erp_cp7_step_staged_analysis_v1',()=>{})
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  await w.settle(ui,'erp_cp7_request_staged_analysis_v1')
  const first=w.calls.find(c=>c.name==='erp_cp7_request_staged_analysis_v1');assert.equal(first.status,200);assert.equal(first.body.state,'RUNNING')
  assert.equal(first.body.server_runner.active,true,'K4R_RUNNER_NOT_REPORTED');const key=first.body.request_id
  await ui.expect(panel.getByRole('status').filter({hasText:SERVER})).toBeVisible({timeout:30000})
  shots.push(await shot(ui,page,`K4R_${suffix}_SERVER_RUNS.png`))
  const appUrl=page.url()
  if(mobile){
   await panel.getByRole('button',{name:'Berhenti memantau (server tetap menghitung)',exact:true}).click()
   await ui.expect(panel.getByRole('status').filter({hasText:'server tetap menjalankan analisis bertahap ini sampai selesai'})).toBeVisible()
   shots.push(await shot(ui,page,`K4R_${suffix}_STOPPED_WATCHING.png`))
  }else await page.close()
  // The server finishes the job with no page.
  let state
  await ui.expect.poll(()=>{state=fixture('state',{actor:user.user.id});return state.jobs.at(-1)?.state},{timeout:240000,intervals:[2000]}).toBe('DONE')
  const job=state.jobs.at(-1);assert.equal(state.jobs.length,1,JSON.stringify(state));assert.equal(job.request_id,key)
  assert.equal(job.units_done,job.unit_count);assert.equal(job.distinct_units,job.unit_count);assert.equal(job.stored_units,job.unit_count,'K4R_UNIT_STORED_TWICE')
  assert.equal(w.sent.filter(n=>n==='erp_cp7_step_staged_analysis_v1').length>=1,true);assert.equal(w.calls.filter(c=>c.name==='erp_cp7_step_staged_analysis_v1').length,0,'K4R_PAGE_RAN_A_UNIT')
  // Open again: the same job's result, no new request and no step.
  if(mobile){await page.unroute('**/rpc/erp_cp7_step_staged_analysis_v1');w=watch(page);await page.reload()}
  else{page=await user.context.newPage();w=watch(page);await page.goto(appUrl)}
  panel=await openPanel(page)
  const region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(region).toBeVisible({timeout:90000})
  await w.settle(ui,'erp_cp7_read_staged_analysis_pages_v1')
  const got=w.calls.find(c=>c.name==='erp_cp7_get_staged_analysis_v1');assert.ok(got,'K4R_REOPEN_DID_NOT_READ_STATUS');assert.equal(got.body.state,'DONE');assert.equal(got.body.run_id,job.run_id)
  const ps=w.calls.filter(c=>c.name==='erp_cp7_read_staged_analysis_pages_v1'&&c.status===200).at(-1);assert.ok(ps,'K4R_NO_PAGE_SET')
  assert.equal(ps.body.run_id,job.run_id);assert.equal(ps.body.identity_hash,job.identity_hash,'K4R_REOPENED_IDENTITY_DIFFERS')
  assert.equal(w.sent.filter(n=>n==='erp_cp7_request_staged_analysis_v1'||n==='erp_cp7_step_staged_analysis_v1').length,0,'K4R_REOPEN_RECOMPUTED')
  assert.equal(w.calls.filter(c=>c.status>=400).length,0,JSON.stringify(w.calls.filter(c=>c.status>=400)))
  assert.equal(fixture('state',{actor:user.user.id}).jobs.length,1,'K4R_SECOND_JOB')
  shots.push(await shot(ui,page,`K4R_${suffix}_REOPENED_DONE_BY_SERVER.png`))
  const off=fixture('runner_off',{});runner=null
  assert.equal(off.removed.length,1);assert.ok(off.cron_runs>=1&&off.cron_runs===off.cron_runs_succeeded,JSON.stringify(off))
  return{status:'PASS',pg_cron:true,test_schedule_override:'5 seconds',closed:mobile?'STOPPED_WATCHING':'TAB_CLOSED',page_units:0,server_units:job.unit_count,
   same_request_and_run:true,identity_hash:job.identity_hash,no_request_or_step_on_reopen:true,every_unit_stored_once:true,cron_runs:off.cron_runs,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/K4R_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/K4R_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{if(runner)try{fixture('runner_off',{})}catch{/* the case already failed; the copy is dropped after the run */}await user.context.close()}
}
export function cases(ui,today){return[['K4R_BROWSER_DESKTOP_CLOSED_PAGE_FINISHES',()=>journey(ui,today,false)],['K4R_BROWSER_MOBILE_CLOSED_PAGE_FINISHES',()=>journey(ui,today,true)]]}
