import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const HC='erp_cp7_capture_model_history_v1',MC='erp_cp7_capture_model_evaluation_v3',MR='erp_cp7_read_model_evaluation_v3'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow11_model_scoped_evaluation_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const immutable=({current_guard,...rest})=>rest
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function open(page,q){
 const parent=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first()
 await parent.waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await parent.click();await link.click()
 const demand=page.getByRole('region',{name:'Data permintaan ERP',exact:true})
 await demand.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
 await demand.getByLabel('Permintaan dari tanggal',{exact:true}).fill(q.from_date)
 await demand.getByLabel('Permintaan sampai tanggal',{exact:true}).fill(q.through_date)
 await demand.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()
 return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'scoped-model-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const panel=page.getByRole('region',{name:'Riwayat dan model per produk',exact:true}),staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true}),calls=[],shots=[],lost={}
 const state=()=>fixture('state',{actor})
 const shot=async suffix=>{await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);const path=`cp6-proof/t3/SCOPED_MODEL_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  const before=state();assert.deepEqual([before.history_rows,before.model_rows,before.legacy_v2_rows],[0,0,0])
  const parent=await open(page,f.query)
  await parent.getByRole('button',{name:'Analisis bertahap (hingga 5.000 target)',exact:true}).click()
  await ui.expect(staged).toBeVisible({timeout:180000})
  const row=staged.locator(`[data-analysis-target="${f.query.target_key}"], [data-model-target="${f.query.target_key}"]`),select=staged.getByLabel('Pilih rentang target',{exact:true})
  const pages=await select.locator('option').count()
  for(let i=0;i<pages&&!await row.count();i++){await select.selectOption(String(i));await ui.expect(staged.locator('[data-page-index]')).toHaveAttribute('data-page-index',String(i),{timeout:60000})}
  await ui.expect(row).toHaveCount(1)
  if(!await row.isVisible())await staged.getByText('Target pada halaman ini dengan status produksi belum diperiksa',{exact:true}).click()
  await row.getByRole('button',{name:/^Riwayat dan model /}).click()
  await ui.expect(panel).toBeVisible();assert.equal(state().history_rows,0);assert.equal(calls.filter(n=>n===HC||n===MC).length,0)
  if(mobile)for(const method of[HC,MC])await page.route('**/rest/v1/rpc/'+method,async route=>{
   if(!lost[method]){const r=await route.fetch();assert.equal(r.status(),200);lost[method]={args:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()
  })
  let history
  if(mobile){
   await panel.getByRole('button',{name:'Simpan riwayat produk saat ini',exact:true}).click()
   await ui.expect(panel.getByRole('button',{name:'Periksa riwayat yang sama',exact:true})).toBeEnabled()
   assert.equal(state().history_rows,1);assert.equal(state().model_rows,0)
   await page.reload();await open(page,f.query)
   history=await response(page,HC,()=>panel.getByRole('button',{name:'Periksa riwayat yang sama',exact:true}).click())
   assert.deepEqual(history.args,lost[HC].args);assert.deepEqual(immutable(history.body),immutable(lost[HC].body))
  }else history=await response(page,HC,()=>panel.getByRole('button',{name:'Simpan riwayat produk saat ini',exact:true}).click())
  assert.equal(history.status,200,JSON.stringify(history.body));assert.deepEqual(history.args.p_query,f.query)
  assert.equal(history.body.history.scope,'SINGLE_CURRENT_PHYSICAL_ROOT');assert.equal(history.body.history.history.rows.length,1)
  await ui.expect(panel).toContainText('Penjualan tercatat 0 PCS');assert.equal(state().history_rows,1)
  await panel.getByLabel('Hari ramalan produk',{exact:true}).fill('7')
  let model
  if(mobile){
   await panel.getByRole('button',{name:'Simpan evaluasi produk',exact:true}).click()
   await ui.expect(panel.getByRole('button',{name:'Periksa evaluasi produk yang sama',exact:true})).toBeEnabled()
   assert.equal(state().model_rows,1)
   await page.reload();await open(page,f.query)
   model=await response(page,MC,()=>panel.getByRole('button',{name:'Periksa evaluasi produk yang sama',exact:true}).click())
   assert.deepEqual(model.args,lost[MC].args);assert.deepEqual(immutable(model.body),immutable(lost[MC].body))
  }else model=await response(page,MC,()=>panel.getByRole('button',{name:'Simpan evaluasi produk',exact:true}).click())
  assert.equal(model.status,200,JSON.stringify(model.body));assert.equal(model.body.contract_version,'cp7.scoped-model-run.v3')
  assert.equal(model.body.query.history_run_id,history.body.run_id);assert.equal(model.body.assessment.source.history_run_id,history.body.run_id)
  assert.equal(model.body.query.target_key,f.query.target_key);assert.equal(model.body.assessment.activation.state,'BASELINE_REQUIRED');assert.equal(model.body.forecast_applied,false)
  await ui.expect(panel).toContainText('Gunakan metode dasar');await ui.expect(panel).toContainText('Belum ada kebijakan penggunaan model pada riwayat ini.')
  await ui.expect(panel).toContainText('Nilai yang belum diketahui tidak dianggap nol.');await ui.expect(panel).toContainText('Evaluasi ini belum diterapkan pada target produksi.')
  const saved=state();assert.equal(saved.business_sha256,before.business_sha256);assert.deepEqual([saved.history_rows,saved.model_rows,saved.legacy_v2_rows],[1,1,0]);await shot('RETAINED_BASELINE')
  fixture('post',{draft:f.draft});assert.notEqual(state().business_sha256,before.business_sha256)
  const stale=await response(page,MR,()=>panel.getByRole('button',{name:'Periksa sumber dan kelayakan arsip',exact:true}).click())
  assert.equal(stale.status,200);assert.deepEqual(immutable(stale.body),immutable(model.body));assert.equal(stale.body.current_guard.reason,'NATIVE_HISTORY_SOURCE_CHANGED')
  assert.equal(state().model_hash,saved.model_hash);assert.equal(state().history_hash,saved.history_hash)
  await ui.expect(panel).toContainText('Sumber berubah sejak evaluasi disimpan.');await shot('SOURCE_CHANGED')
  if(!mobile){
   const fresh=await response(page,HC,()=>panel.getByRole('button',{name:'Simpan riwayat produk saat ini',exact:true}).click());assert.equal(fresh.status,200)
   assert.equal(fresh.body.history.history.rows[0].gross_observed_pcs,'24');assert.equal(fresh.body.history.current_stock[0].native_available_pcs,'76')
   assert.ok(Date.parse(fresh.body.captured_at)>=Date.parse(history.body.captured_at));await ui.expect(panel).toContainText('Penjualan tercatat 24 PCS')
   const next=await response(page,MC,()=>panel.getByRole('button',{name:'Simpan evaluasi produk',exact:true}).click());assert.equal(next.status,200)
   assert.equal(next.body.query.history_run_id,fresh.body.run_id);assert.notEqual(next.body.run_id,model.body.run_id)
   assert.deepEqual([state().history_rows,state().model_rows],[2,2])
  }
  fixture('deactivate',{actor})
  const denied=await response(page,MR,()=>panel.getByRole('button',{name:'Periksa sumber dan kelayakan arsip',exact:true}).click());assert.equal(denied.status,403)
  await ui.expect(panel).not.toContainText('Rata-rata dasar');await ui.expect(panel.getByRole('button',{name:'Simpan riwayat produk saat ini',exact:true})).toBeDisabled()
  await ui.expect(staged).toHaveCount(0);await shot('REVOKED')
  assert.equal(calls.filter(n=>n==='erp_cp7_capture_demand_history_v1'||n==='erp_cp7_capture_model_evaluation_v2').length,0)
  return{status:'PASS',actual_Auth_PostgREST_browser:true,bounded_page_target_entry:true,no_history_or_model_capture_on_mount:true,
   actual_scoped_history_and_retained_model:true,actual_history_and_model_lost_reply_reload_exact_recovery:mobile,
   current_posted_sale_archives_immutable_assessment:true,fresh_history_gross24_available76:!mobile,
   no_legacy_global_history_or_v2_model_capture:true,current403_hides_model_and_staged_results:true,
   no_business_write_by_history_or_model:true,no_horizontal_overflow:true,shots,positive_model_target_qualified:false,forecast_applied:false,full_OW11_acceptance:false}
 }catch(e){writeFileSync(`cp6-proof/t3/SCOPED_MODEL_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),calls,lost,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw e}
 finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_SCOPED_MODEL_BROWSER_MOBILE_HISTORY_MODEL_EXACT_RECOVERY',()=>journey(ui,today,true)],
 ['OW11_SCOPED_MODEL_BROWSER_DESKTOP_BOUNDED_ENTRY_SOURCE_ACCESS',()=>journey(ui,today,false)],
]}
