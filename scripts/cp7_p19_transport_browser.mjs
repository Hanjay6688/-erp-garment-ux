import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// Real Native fixture commands of the accepted analysis browser suite; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f05_analysis_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const names=['erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_get_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1','erp_cp7_capture_analysis_v1']
const runEndpoint='**/rest/v1/rpc/erp_cp7_run_analysis_job_v1'
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'p19t-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],shots=[]
 const state=()=>fixture('state',{actor:user.user.id})
 page.on('request',r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 let panel,first=null,seenSince=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});panel=await openPanel(page);const before=state();assert.equal(before.analysis_count,0)
  // The worker request is held until the operator can see when it started.
  await page.route(runEndpoint,async route=>{
   try{await ui.expect(panel.getByRole('status').filter({hasText:'Sedang dihitung sejak jam'})).toBeVisible();seenSince=await panel.getByRole('status').filter({hasText:'Sedang dihitung sejak jam'}).innerText()
    if(mobile)return await route.continue()
    const r=await route.fetch();first={status:r.status(),body:await r.json()};await route.abort('failed')}catch(error){first={error:String(error)};await route.abort('failed').catch(()=>{})}})
  await panel.getByRole('button',{name:'Hitung di latar belakang',exact:true}).click()
  await ui.expect.poll(()=>seenSince).toBeTruthy();assert.match(seenSince,/^Sedang dihitung sejak jam \d{2}[.:]\d{2}[.:]\d{2} WIB/)
  const requestId=calls.find(c=>c.name==='erp_cp7_request_analysis_job_v1').body.p_request
  if(!mobile){
   await ui.expect.poll(()=>first).toBeTruthy();assert.equal(first.status,200,JSON.stringify(first));assert.equal(first.body.state,'DONE');assert.equal(first.body.request_id,requestId)
   await ui.expect(panel.getByRole('button',{name:'Lanjutkan perhitungan yang sama',exact:true})).toBeVisible();assert.equal(state().analysis_count,1)
   shots.push(await shot(ui,page,`P19T_${suffix}_LOST_REPLY.png`))
   await page.unroute(runEndpoint);const runsBefore=calls.filter(c=>c.name==='erp_cp7_run_analysis_job_v1').length
   await page.reload();panel=await openPanel(page)
   await ui.expect(panel.locator('.native-analysis-result')).toBeVisible({timeout:30000})
   const after=calls.slice(calls.findIndex(c=>c.name==='erp_cp7_get_analysis_job_v1'))
   assert.deepEqual(after[0].body,{p_request:requestId});assert.equal(calls.filter(c=>c.name==='erp_cp7_run_analysis_job_v1').length,runsBefore)
   const manifest=after.find(c=>c.name==='erp_cp7_read_analysis_manifest_v1');assert.deepEqual(manifest.body,{p_run:first.body.run_id})
  }else{
   await ui.expect(panel.locator('.native-analysis-result')).toBeVisible({timeout:30000});await page.unroute(runEndpoint)
   assert.deepEqual(calls.map(c=>c.name).slice(0,4),['erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1'])
  }
  const manifests=calls.filter(c=>c.name==='erp_cp7_read_analysis_manifest_v1'),segments=calls.filter(c=>c.name==='erp_cp7_read_analysis_segment_v1');assert.equal(manifests.length,1)
  assert.deepEqual(segments.map(c=>c.body.p_index),[...Array(segments.length).keys()]);assert.ok(segments.length>=1&&segments.every(c=>c.body.p_run===manifests[0].body.p_run&&/^[0-9a-f]{64}$/.test(c.body.p_access)))
  assert.equal(calls.filter(c=>c.name==='erp_cp7_capture_analysis_v1').length,0)
  assert.equal(await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('erp.cp7.analysis-job.v1:')).length),0)
  const after=state();assert.equal(after.analysis_count,1);assert.deepEqual(after.business,before.business)
  shots.push(await shot(ui,page,`P19T_${suffix}_RESULT.png`))
  return{status:'PASS',background_status_shown_with_WIB_start:seenSince,lost_committed_run_reply_recovered_after_reload:!mobile,one_Original:true,
   no_second_worker_after_reload:!mobile,segments_read:segments.length,business_unchanged:true,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19T_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),first,calls:calls.map(c=>c.name),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19T_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P19T_BROWSER_DESKTOP_RELOAD_RECOVERY',()=>journey(ui,today,false)],['P19T_BROWSER_MOBILE_BACKGROUND',()=>journey(ui,today,true)]]}
