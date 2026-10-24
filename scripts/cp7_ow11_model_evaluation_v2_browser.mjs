import assert from 'node:assert/strict'
import {randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const CAPTURE='erp_cp7_capture_model_evaluation_v2',READ='erp_cp7_read_model_evaluation_v2'
const GET_POLICY='erp_cp7_get_model_activation_policy_v1',SAVE_POLICY='erp_cp7_save_model_activation_policy_v1'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow11_model_evaluation_v2_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const immutable=({current_guard,...rest})=>rest
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'model-v2-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const demand=page.getByRole('region',{name:'Data permintaan ERP',exact:true}),model=page.getByRole('region',{name:'Evaluasi ramalan ERP',exact:true}),panel=page.getByRole('region',{name:'Evaluasi sesuai kebijakan',exact:true}),shots=[]
 const state=()=>fixture('state',{actor});let lost=null
 const shot=async(suffix,focus=panel)=>{await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);const path=`cp6-proof/t3/MODEL_V2_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await focus.scrollIntoViewIfNeeded();await page.screenshot({path,fullPage:true});shots.push(path)}
 async function open(){
  await navigate(page);await demand.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
  const from=new Date(Date.parse(today+'T00:00:00Z')-12*86400000).toISOString().slice(0,10)
  await demand.getByLabel('Permintaan dari tanggal',{exact:true}).fill(from)
  const history=await response(page,'erp_cp7_capture_demand_history_v1',()=>demand.getByRole('button',{name:'Muat data permintaan',exact:true}).click());assert.equal(history.status,200)
  const sku=history.body.current_stock.find(x=>x.root_id===f.product).sku
  await demand.getByLabel('Cari data permintaan',{exact:true}).fill(sku);await demand.getByRole('button',{name:'Bandingkan ramalan '+sku,exact:true}).click()
  if(!await panel.isVisible())await model.getByRole('button',{name:'Bandingkan sesuai kebijakan',exact:true}).click()
  return history.body
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  await open();const before=state();assert.equal(before.v2_rows,0);assert.equal(before.model_rows,0)
  assert.equal(await panel.getByLabel('Hari ramalan sesuai kebijakan',{exact:true}).inputValue(),'')
  await panel.getByLabel('Hari ramalan sesuai kebijakan',{exact:true}).fill('7')
  await page.route('**/rest/v1/rpc/'+CAPTURE,async route=>{if(!lost){const r=await route.fetch();assert.equal(r.status(),200);lost={envelope:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()})
  await panel.getByRole('button',{name:'Simpan evaluasi sesuai kebijakan',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Periksa hasil evaluasi yang sama',exact:true})).toBeEnabled()
  const pending=state();assert.equal(pending.v2_rows,1);assert.equal(pending.business_sha256,before.business_sha256);assert.equal(pending.model_rows,0)
  await page.reload();await open()
  const replay=await response(page,CAPTURE,()=>panel.getByRole('button',{name:'Periksa hasil evaluasi yang sama',exact:true}).click());assert.equal(replay.status,200);assert.deepEqual(replay.args,lost.envelope);assert.deepEqual(immutable(replay.body),immutable(lost.body));assert.equal(replay.body.forecast_applied,false)
  await ui.expect(panel).toContainText('Gunakan metode dasar');await ui.expect(panel.getByRole('button',{name:'Periksa hasil evaluasi yang sama',exact:true})).toHaveCount(0);assert.deepEqual(state(),pending)
  const workspace=await user.rpc(GET_POLICY,{});assert.equal(workspace.status,200)
  // This independent current policy change uses actual Auth HTTP. Policy UI
  // editing has its own qualified Browser2; this journey exercises v2 reread.
  const saved=await user.rpc(SAVE_POLICY,{p_request:randomUUID(),p_payload:{contract_version:'cp7.model-activation-policy-command.v1',action:'SET',config:{minimum_training_days:'20',maximum_horizon_days:'90',allowed_methods:[],promotion:{minimum_complete_folds:'3',minimum_mae_improvement:'0',maximum_bias_worsening:'0',maximum_tail_worsening:'0',season_lag:'7'}},template_hash:workspace.body.model_template.hash,reason:'Explicit SYNTHETIC browser baseline-only policy',reviewed:true,expected_revision:workspace.body.revision,access_epoch:workspace.body.access_epoch}});assert.equal(saved.status,200,JSON.stringify(saved.body))
  const retired=await response(page,READ,()=>panel.getByRole('button',{name:'Periksa kelayakan arsip saat ini',exact:true}).click());assert.equal(retired.status,200);assert.deepEqual(immutable(retired.body),immutable(replay.body));assert.equal(retired.body.current_guard.reason,'ACTIVATION_POLICY_CHANGED');await ui.expect(panel).toContainText('Kebijakan sudah berubah');assert.equal(state().v2_hash,pending.v2_hash);await shot('POLICY_CHANGED')
  await page.reload();const fresh=await open();await panel.getByLabel('Hari ramalan sesuai kebijakan',{exact:true}).fill('7')
  const baseline=await response(page,CAPTURE,()=>panel.getByRole('button',{name:'Simpan evaluasi sesuai kebijakan',exact:true}).click());assert.equal(baseline.status,200,JSON.stringify(baseline.body));assert.equal(baseline.body.query.history_run_id,fresh.run_id);assert.equal(baseline.body.assessment.evaluation,null);assert.equal(baseline.body.assessment.evaluation_state,'NOT_REQUESTED_NO_ALLOWED_CHALLENGER');assert.deepEqual(baseline.body.assessment.policy_source.policy,saved.body.policy);assert.equal(baseline.body.assessment.source.history_run_id,fresh.run_id)
  await ui.expect(panel).toContainText('Kebijakan tidak mengizinkan model pembanding.');assert.equal(await panel.locator('table').count(),0);const frozen=state();assert.equal(frozen.v2_rows,2);assert.equal(frozen.model_rows,0);assert.equal(frozen.business_sha256,before.business_sha256);await shot('BASELINE_ONLY')
  fixture('post',{draft:f.draft});const changed=state();assert.notEqual(changed.business_sha256,before.business_sha256)
  const stale=await response(page,READ,()=>panel.getByRole('button',{name:'Periksa kelayakan arsip saat ini',exact:true}).click());assert.equal(stale.status,200);assert.deepEqual(immutable(stale.body),immutable(baseline.body));assert.equal(stale.body.current_guard.reason,'NATIVE_HISTORY_SOURCE_CHANGED');assert.equal(state().v2_hash,frozen.v2_hash);await ui.expect(panel).toContainText('Data sumber berubah');await shot('SOURCE_CHANGED')
  const dirty=page.getByLabel('Cari barang jadi',{exact:true});await dirty.fill('MODEL V2 KEEP SEARCH')
  fixture('deactivate',{actor});const denied=await response(page,READ,()=>panel.getByRole('button',{name:'Periksa kelayakan arsip saat ini',exact:true}).click());assert.equal(denied.status,403)
  await ui.expect(panel.locator('.native-model-result')).toHaveCount(0);await ui.expect(page.locator('.cfg-totals')).toHaveCount(0);assert.equal(await dirty.inputValue(),'MODEL V2 KEEP SEARCH');await ui.expect(panel).toHaveCount(0);await ui.expect(model).toHaveCount(0);await shot('REVOKED',dirty)
  return{status:'PASS',actual_Auth_PostgREST_browser:true,actual_Native_history_not_backdated:true,actual_commit_lost_reply_reload_exact_actor_UUID_method_payload:true,immutable_assessment_current_policy_guard:true,explicit_empty_allowed_models_preserve_source_no_fake_backtest:true,actual_posted_sale_retires_source_immutable_run:true,current403_retires_model_parent_FG_HPP:true,legacy_model_rows:0,model_v2_rows:2,no_evaluation_money_stock_HPP_write:true,no_horizontal_overflow:true,shots,actual_positive_model_winner:false,forecast_applied:false,full_OW11_acceptance:false}
 }catch(e){writeFileSync(`cp6-proof/t3/MODEL_V2_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),lost,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE',page.locator('body')).catch(()=>{});throw e}
 finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_MODEL_V2_BROWSER_MOBILE_EXACT_RECOVERY_POLICY_SOURCE',()=>journey(ui,today,true)],
 ['OW11_MODEL_V2_BROWSER_DESKTOP_BASELINE_CURRENT_ACCESS',()=>journey(ui,today,false)],
]}
