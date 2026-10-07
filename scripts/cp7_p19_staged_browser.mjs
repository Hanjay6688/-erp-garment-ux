import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {armStagedResultOpen,readStagedResultOpen} from './cp7_p19_staged_load_browser.mjs'
// P19 staged analysis in the real UI: one trusted click starts the staged job,
// the page steps it one unit per request with real progress, a reload resumes
// the same job (never a second request UUID), and the result is read as pages
// "Target a–b dari N" with whole-run totals from the server. Real Native
// fixture commands of the accepted analysis browser suite; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f05_analysis_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const names=['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_get_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1','erp_cp7_check_staged_analysis_source_v1','erp_cp7_capture_operational_analysis_v1','erp_cp7_capture_analysis_v1','erp_cp7_request_operational_analysis_job_v1','erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_read_analysis_v1','erp_cp7_read_analysis_manifest_v1']
const STAGED='Analisis bertahap (hingga 5.000 target)',KEY_PREFIX='erp.cp7.analysis-staged.v1:'
const DOWNSTREAM=/pengingat|laporan|AI/i
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page,measurement=null){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();const button=history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true});if(measurement)await armStagedResultOpen(button,measurement.key,measurement.runId);await button.click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
const stagedKeys=page=>page.evaluate(prefix=>Object.keys(localStorage).filter(k=>k.startsWith(prefix)),KEY_PREFIX)
async function journey(ui,today,mobile){
 fixture('prepare',{today});const user=await ui.login('OWNER',{label:'p19g-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],replies=[],shots=[]
 const state=()=>fixture('staged_state',{actor:user.user.id})
 page.on('request',r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 page.on('response',async r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name&&name.includes('staged')){try{replies.push({name,status:r.status(),body:await r.json()})}catch{replies.push({name,status:r.status(),body:null})}}})
 let panel,progress=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});panel=await openPanel(page);const before=state();assert.equal(before.jobs.length,0)
  await panel.getByRole('button',{name:STAGED,exact:true}).click()
  // Real progress from the stored job: stage and unit counts, start time in WIB.
  const status=panel.getByRole('status').filter({hasText:'Analisis bertahap: tahap'})
  await ui.expect(status).toBeVisible({timeout:30000});progress=await status.innerText()
  assert.match(progress,/^Analisis bertahap: tahap \d+ dari \d+/);assert.match(progress,/unit \d+ dari \d+/);assert.match(progress,/dimulai jam \d{2}[.:]\d{2}[.:]\d{2} WIB/)
  const requested=calls.filter(c=>c.name==='erp_cp7_request_staged_analysis_v1');assert.equal(requested.length,1);const requestId=requested[0].body.p_request
  assert.equal(calls.filter(c=>/^erp_cp7_(capture|request)_(operational_)?analysis(_job)?_v1$/.test(c.name)).length,0,'P19G_STAGED_CLICK_STARTED_A_SINGLE_PATH_CALL')
  let resumed=false
  if(!mobile){
   // Leave mid-job: the stored request resumes after a reload, never a new UUID.
   // Stop the old page's driver before marking the reload boundary. A step
   // already sent can commit; it must never be counted as the reload's call.
   await panel.getByRole('button',{name:'Jeda analisis bertahap',exact:true}).click()
   await ui.expect(panel.getByRole('button',{name:'Tutup analisis bersama',exact:true})).toBeEnabled()
   await ui.expect.poll(()=>replies.filter(r=>r.name==='erp_cp7_step_staged_analysis_v1'&&r.status===200).length).toBeGreaterThan(0)
   assert.equal((await stagedKeys(page)).length,1)
   const mark=calls.length
   await page.reload();panel=await openPanel(page);resumed=true
   await ui.expect(page.getByRole('region',{name:'Hasil analisis bertahap',exact:true})).toBeVisible({timeout:120000})
   const after=calls.slice(mark).filter(c=>c.name.includes('_staged_'))
   // The reload reads the stored job's status first, then continues the same job.
   assert.equal(after[0]?.name,'erp_cp7_get_staged_analysis_v1');assert.deepEqual(after[0].body,{p_request:requestId})
   assert.ok(calls.filter(c=>c.name==='erp_cp7_request_staged_analysis_v1').every(c=>c.body.p_request===requestId),'P19G_RELOAD_STARTED_A_NEW_REQUEST')
   assert.ok(after.filter(c=>c.body?.p_request).every(c=>c.body.p_request===requestId))
  }
  const region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true})
  await ui.expect(region).toBeVisible({timeout:120000})
  const done=replies.filter(r=>r.body?.state==='DONE').pop()?.body;assert.ok(done&&done.run_id,'P19G_DONE_NOT_OBSERVED');assert.equal(done.request_id,requestId)
  const set=replies.find(r=>r.name==='erp_cp7_read_staged_analysis_pages_v1')?.body;assert.ok(set,'P19G_PAGE_SET_NOT_READ');assert.equal(set.run_id,done.run_id)
  const pageCalls=calls.filter(c=>c.name==='erp_cp7_read_staged_analysis_page_v1');assert.ok(pageCalls.length>=1&&pageCalls.every(c=>c.body.p_run===done.run_id&&c.body.p_access===set.access_epoch))
  const total=set.targets_total,first=set.pages[0]
  await ui.expect(region).toContainText(`Target ${first.target_lo.toLocaleString('id-ID')}–${first.target_hi.toLocaleString('id-ID')} dari ${total.toLocaleString('id-ID')}`)
  const next=region.getByRole('button',{name:'Halaman berikutnya',exact:true}),prev=region.getByRole('button',{name:'Halaman sebelumnya',exact:true})
  await ui.expect(prev).toBeDisabled();if(set.page_count===1)await ui.expect(next).toBeDisabled();else{await next.click();await ui.expect(region).toContainText(`Target ${set.pages[1].target_lo.toLocaleString('id-ID')}–`)}
  // Downstream features are stated unavailable for a staged run (no fake buttons).
  const text=await region.innerText();assert.match(text,/belum tersedia untuk analisis bertahap\./);assert.match(text,DOWNSTREAM)
  await region.getByRole('button',{name:'Cek sumber',exact:true}).click();await ui.expect(region).toContainText('Sumber belum berubah sejak')
  assert.equal(calls.filter(c=>c.name==='erp_cp7_check_staged_analysis_source_v1').length,1)
  // A staged run is never read through a whole reader.
  assert.equal(calls.filter(c=>c.name==='erp_cp7_read_analysis_v1'||c.name==='erp_cp7_read_analysis_manifest_v1').length,0)
  assert.equal((await stagedKeys(page)).length,0,'P19G_STORED_REQUEST_LEFT_AFTER_DONE')
  // A completed pointer survives reopening, with server access and hashes
  // reverified. A DONE run is never computed again.
  const completedMark=calls.length;await page.reload();panel=await openPanel(page,{key:'completed',runId:done.run_id})
  const completedLoad=await readStagedResultOpen(page,'completed')
  const reopened=calls.slice(completedMark).filter(c=>c.name.includes('_staged_'))
  assert.equal(reopened[0]?.name,'erp_cp7_get_staged_analysis_v1');assert.equal(reopened[0]?.body.p_request,requestId)
  assert.equal(reopened.filter(c=>c.name==='erp_cp7_request_staged_analysis_v1'||c.name==='erp_cp7_step_staged_analysis_v1').length,0,'P19G_DONE_REOPEN_RECOMPUTED')
  const after=state();assert.equal(after.jobs.length,1);assert.equal(after.jobs[0].state,'DONE');assert.equal(after.jobs[0].request_id,requestId)
  assert.equal(after.pages,set.page_count);assert.equal(after.analysis_count,before.analysis_count);assert.deepEqual(after.business,before.business)
  shots.push(await shot(ui,page,`P19G_${suffix}_STAGED_RESULT.png`))
  const steps=calls.filter(c=>c.name==='erp_cp7_step_staged_analysis_v1').length
  return{status:'PASS',progress_text:progress,reload_resumed_same_request:resumed,one_job_one_request:true,steps,page_count:set.page_count,targets_total:total,
   identity_hash:set.identity_hash,completed_open:completedLoad,completed_open_target_ms:3000,load_target_mandatory:false,whole_readers_not_called:true,downstream_unavailable_stated:true,source_check_unchanged:true,business_unchanged:true,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19G_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),progress,calls:calls.map(c=>c.name),replies:replies.map(r=>({name:r.name,status:r.status,state:r.body?.state,failure:r.body?.failure})),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19G_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P19G_BROWSER_DESKTOP_STAGED_RELOAD',()=>journey(ui,today,false)],['P19G_BROWSER_MOBILE_STAGED',()=>journey(ui,today,true)]]}
