import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {cases as retainedCases} from './cp7_ow14b_rule_browser.mjs'
const fixture=(operation,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow13a_initial_browser_fixture.py',operation],
 {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const request='erp_cp7_request_staged_analysis_v1'
async function navigate(ui,page){
 const parent=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first();await parent.waitFor({state:'attached'})
 // A reload/new page may still be mounting Auth/App. Check the actual menu
 // after the sidebar exists, as the retained mobile navigation does.
 const menu=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await menu.isVisible()){await menu.click();await ui.expect(page.locator('.sidebar')).toHaveClass(/sidebar-open/)}
 const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await parent.click()
 await link.click();await ui.expect(page.getByRole('region',{name:'Analisis awal otomatis',exact:true})).toBeVisible()
}
async function journey(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'ow13a-initial-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 let page=user.page;const actor=user.user.id,requests=[],shots=[];let lost=null
 const state=()=>fixture('state',{actor}),panel=()=>page.getByRole('region',{name:'Analisis awal otomatis',exact:true})
 const watch=async p=>p.route('**/rest/v1/rpc/'+request,async route=>{
  const args=route.request().postDataJSON(),response=await route.fetch(),body=await response.json()
  requests.push({args,status:response.status(),body})
  if(mobile&&!lost&&args.p_query?.initial_auto==='ENSURE'){
   lost={args,status:response.status(),body};await route.abort('failed')
  }else await route.fulfill({response})
 })
 const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/OW13A_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 try{
  fixture('prepare',{today,actor});const before=state();await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  await watch(page);await navigate(ui,page)
  if(!mobile){
   await ui.expect(panel()).toContainText('Yang masih perlu dilengkapi:')
   const first=requests.find(x=>x.args.p_query?.initial_auto==='STATUS'&&x.status===200)?.body
   assert.equal(first?.state,'NOT_READY',JSON.stringify(first))
   const candidate=first.readiness.candidates.find(p=>!p.profile_ready);assert.ok(candidate)
   await panel().getByRole('button',{name:'Lengkapi target '+candidate.sku,exact:true}).click()
   const config=page.getByRole('region',{name:'Aturan dan target produksi',exact:true})
   await ui.expect(config.getByLabel('Dasar permintaan',{exact:true})).toBeVisible()
   await config.getByLabel('Dasar permintaan',{exact:true}).selectOption('SELECTED_MANUAL')
   await config.getByLabel('Permintaan pilihan PCS per hari',{exact:true}).fill('10')
   await config.getByLabel('Minimal hari riwayat tersedia',{exact:true}).fill('14')
   await config.getByLabel('Waktu proses pilihan (hari kalender)',{exact:true}).fill('3')
   await config.getByLabel('Jarak pemeriksaan (hari kalender)',{exact:true}).fill('7')
   await config.getByLabel('Cadangan waktu (hari kalender)',{exact:true}).fill('2')
   await config.getByLabel('Alasan aturan target',{exact:true}).fill('OW13a browser fixture, not an owner production policy')
   const saved=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_save_planning_profile_v1'))
   await config.getByRole('button',{name:'Simpan aturan target',exact:true}).click();assert.equal((await saved).status(),200)
  }
  await ui.expect.poll(()=>requests.filter(x=>x.args.p_query?.initial_auto==='ENSURE'&&x.status===200).length,{timeout:30000}).toBe(1)
  const created=requests.find(x=>x.args.p_query?.initial_auto==='ENSURE').body,key=created.job?.request_id
  assert.equal(created.state,'RUNNING',JSON.stringify(created));assert.ok(key);assert.equal(created.job_query.group_mode,'AS_SOLD')
  if(mobile){
   assert.equal(lost?.status,200);await page.reload();await navigate(ui,page)
   await ui.expect(panel().getByRole('button',{name:'Buka analisis awal yang berjalan',exact:true})).toBeVisible()
   assert.equal(state().job.request_id,key);assert.equal(requests.filter(x=>x.args.p_query?.initial_auto==='ENSURE').length,1)
  }else await ui.expect(panel().getByRole('button',{name:'Buka analisis awal yang berjalan',exact:true})).toBeVisible()
  const stored=state();assert.equal(stored.native_hash,before.native_hash);assert.equal(stored.own_intents,1)
  await shot('SAVED');const url=page.url();await page.close()
  const tick=fixture('worker',{actor});const advanced=state()
  assert.equal(advanced.job.request_id,key);assert.ok(advanced.job.units_done>stored.job.units_done,JSON.stringify({tick,stored,advanced}))
  page=await user.context.newPage();await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000});await watch(page);await page.goto(url);await navigate(ui,page)
  await ui.expect(panel()).toContainText('Analisis bertahap:')
  assert.equal(state().job.request_id,key);assert.equal(state().own_intents,1)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  if(mobile){
   fixture('deactivate',{actor});await panel().getByRole('button',{name:'Periksa kesiapan lagi',exact:true}).click()
   await ui.expect(panel().getByRole('button',{name:'Buka analisis awal yang berjalan',exact:true})).toHaveCount(0)
   assert.equal(state().own_intents,1)
  }
  await shot('REOPENED')
  return{status:'PASS',actual_Auth_PostgREST_Native:true,initial_UUID:key,missing_config_to_existing_target_form:!mobile,
   nullable_conditional_ensure_once:true,reply_loss_recovers_same_UUID:mobile,Native_business_unchanged:true,
   actual_K4_worker_advanced_with_page_closed:true,worker_tick_invoked_by_test_not_cron:true,remount_same_server_job:true,
   current_revocation_hides_facts:mobile,viewport:mobile?390:1440,no_horizontal_overflow:true,shots,
   policy_values:'TEST_FIXTURE_ONLY_NOT_OWNER_OR_ENTENG'}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/OW13A_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),requests,lost,
  panel:await panel().innerText().catch(()=>''),alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error
 }finally{fixture('restore',{actor});await user.context.close()}
}
// First: the missing-minimum journey starts before retained controls add their
// own reviewed metadata. Every retained113 case stays in the declared set.
export function cases(ui,today){return[
 ['OW13A_BROWSER_DESKTOP_MINIMUM_TO_AUTO',()=>journey(ui,today,false)],
 ['OW13A_BROWSER_MOBILE_LOST_REPLY_SAME_JOB',()=>journey(ui,today,true)],
 ...retainedCases(ui,today)]}
