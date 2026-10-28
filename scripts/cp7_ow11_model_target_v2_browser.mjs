import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {quantity,open} from './cp7_ow11_analog_browser.mjs'
const HC='erp_cp7_capture_model_history_v1',MC='erp_cp7_capture_model_evaluation_v3'
const scopedState=actor=>control('cp7_ow11_model_scoped_evaluation_browser_fixture','state',{actor})
const immutable=({current_guard,...rest})=>rest
const SAVE='erp_cp7_save_product_analog_choice_v1',GET='erp_cp7_get_product_analog_choices_v1'
const control=(name,op,p)=>JSON.parse(execFileSync('python',[`../auditor/scripts/${name}.py`,op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const fixture=(op,p)=>control('cp7_ow11_analog_browser_fixture',op,p)
async function response(page,rpc,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+rpc)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function choiceForm(ui,page,a){
 const w=await response(page,GET,()=>a.getByRole('button',{name:'Atur pilihan pembanding',exact:true}).click());assert.equal(w.status,200)
 const form=a.getByRole('region',{name:'Konfirmasi produk pembanding',exact:true});await ui.expect(form.getByRole('button',{name:'Baca ulang pilihan tersimpan',exact:true})).toBeEnabled();return form
}

function assertDemand(d,model){
 assert.equal(d.contract_version,'cp7.target-demand-provenance.v3')
 assert.equal(d.model.contract_version,'cp7.model-target-resolution.v2')
 assert.equal(d.model.forecast_applied,false);assert.equal(d.model.forecast,null)
 if(model){
  assert.equal(d.model.runtime,'SCOPED_V3');assert.equal(d.model.read_method,'erp_cp7_read_model_evaluation_v3')
  assert.equal(d.model.history_scope,'SINGLE_CURRENT_PHYSICAL_ROOT')
  assert.equal(d.model.run_id,model.run_id);assert.equal(d.model.history_run_id,model.history_run_id)
 }else{
  assert.equal(d.model.run_id,null);assert.equal(d.model.runtime,null);assert.equal(d.model.read_method,null)
 }
}
async function captureScopedModel(ui,page,f){
 const panel=page.getByRole('region',{name:'Riwayat dan model per produk',exact:true}),lost={}
 async function entry(){
  const parent=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first()
  await parent.waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await parent.click();await link.click()
  const demand=page.getByRole('region',{name:'Data permintaan ERP',exact:true})
  await demand.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
  await demand.getByLabel('Permintaan dari tanggal',{exact:true}).fill(f.query.from_date)
  await demand.getByLabel('Permintaan sampai tanggal',{exact:true}).fill(f.query.through_date)
  await demand.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()
  return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
 }
 const parent=await entry();await parent.getByRole('button',{name:'Analisis bertahap (hingga 5.000 target)',exact:true}).click()
 const staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(staged).toBeVisible({timeout:180000})
 const row=staged.locator(`[data-analysis-target="${f.target_key}"], [data-model-target="${f.target_key}"]`),select=staged.getByLabel('Pilih rentang target',{exact:true})
 const pages=await select.locator('option').count()
 for(let i=0;i<pages&&!await row.count();i++){await select.selectOption(String(i));await ui.expect(staged.locator('[data-page-index]')).toHaveAttribute('data-page-index',String(i),{timeout:60000})}
 await ui.expect(row).toHaveCount(1)
 if(!await row.isVisible())await staged.getByText('Target pada halaman ini dengan status produksi belum diperiksa',{exact:true}).click()
 await row.getByRole('button',{name:/^Riwayat dan model /}).click();await ui.expect(panel).toBeVisible()
 for(const method of[HC,MC])await page.route('**/rest/v1/rpc/'+method,async route=>{
  if(!lost[method]){const r=await route.fetch();assert.equal(r.status(),200);lost[method]={args:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()
 })
 await panel.getByRole('button',{name:'Simpan riwayat produk saat ini',exact:true}).click()
 await ui.expect(panel.getByRole('button',{name:'Periksa riwayat yang sama',exact:true})).toBeEnabled()
 await page.reload();await entry()
 const history=await response(page,HC,()=>panel.getByRole('button',{name:'Periksa riwayat yang sama',exact:true}).click())
 assert.equal(history.status,200,JSON.stringify(history.body));assert.deepEqual(history.args,lost[HC].args)
 assert.deepEqual(immutable(history.body),immutable(lost[HC].body));assert.deepEqual(history.args.p_query,{...f.query,target_key:f.target_key})
 assert.equal(history.body.history.scope,'SINGLE_CURRENT_PHYSICAL_ROOT')
 await panel.getByLabel('Hari ramalan produk',{exact:true}).fill('7')
 await panel.getByRole('button',{name:'Simpan evaluasi produk',exact:true}).click()
 await ui.expect(panel.getByRole('button',{name:'Periksa evaluasi produk yang sama',exact:true})).toBeEnabled()
 await page.reload();await entry()
 const model=await response(page,MC,()=>panel.getByRole('button',{name:'Periksa evaluasi produk yang sama',exact:true}).click())
 assert.equal(model.status,200,JSON.stringify(model.body));assert.deepEqual(model.args,lost[MC].args)
 assert.deepEqual(immutable(model.body),immutable(lost[MC].body));assert.equal(model.body.query.history_run_id,history.body.run_id)
 assert.equal(model.body.assessment.activation.state,'BASELINE_REQUIRED');assert.equal(model.body.forecast_applied,false)
 return{run_id:model.body.run_id,history_run_id:history.body.run_id}
}

async function journey(ui,today,dense){
 const f=control('cp7_ow11_consumer_browser_fixture','prepare',{today,dense})
 const user=await ui.login('OWNER',{label:'model-target-v2-'+dense,mobile:!dense,timezoneId:dense?'Asia/Jakarta':'America/Los_Angeles'}),page=user.page,actor=user.user.id
 const state=()=>fixture('state',{actor}),calls=[],shots=[],reads=[]
 const shot=async suffix=>{const path=`cp6-proof/t3/MODEL_TARGET_V2_${dense?'DESKTOP':'MOBILE'}_${suffix}.png`;await page.screenshot({path,fullPage:false});shots.push(path)}
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(dense?{width:1440,height:1000}:{width:390,height:844})
  const before=state(),modelBefore=scopedState(actor)
  const model=dense?null:await captureScopedModel(ui,page,f)
  const modelSaved=scopedState(actor)
  let q=await quantity(ui,page,f),{a,read}=await open(ui,page,q,f);reads.push(read);assertDemand(read.body.target_demand,model)
  assert.equal(read.body.target_demand.contract_version,'cp7.target-demand-provenance.v3');assert.equal(read.body.target_demand.model.state,'BASELINE_RETAINED');assert.equal(read.body.target_demand.model.forecast,null);
  assert.equal(read.body.contract_version,'cp7.product-analog-candidates-read.v2');assert.equal(read.body.target_demand.basis,'UNKNOWN')
  await ui.expect(a.getByRole('region',{name:'Dasar kebutuhan target',exact:true})).toContainText('Target rencana: belum diketahui')
  const firstJob=state().job;let form=await choiceForm(ui,page,a)
  await form.getByLabel('Produk pembanding',{exact:true}).selectOption(f.source_key)
  await form.getByLabel('Skala terhadap produk pembanding',{exact:true}).fill(f.scale)
  await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Actual browser review of Native source and physical size')
  await form.getByRole('checkbox').check()
  const saved=await response(page,SAVE,()=>form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).click())
  assert.equal(saved.status,200,JSON.stringify(saved.body));await ui.expect(form).toContainText('revisi 1 tersimpan')
  await ui.expect(form).toContainText('buat perhitungan baru')
  assert.deepEqual(state().physical,before.physical)
  await a.getByRole('button',{name:'Tutup produk pembanding',exact:true}).click()
  const request=await response(page,'erp_cp7_request_bounded_staged_analysis_v1',()=>q.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true}).click())
  assert.equal(request.status,200,JSON.stringify(request.body));assert.notEqual(request.args.p_request,firstJob.request)
  await ui.expect(q.locator('[data-quantity-target]').first()).toBeVisible({timeout:180000})
  assert.deepEqual(await q.getByRole('alert').allTextContents(),[])
  // A new calculation retains the search details state. Explicitly collapse
  // before reusing the helper that opens it; no timing or click guessing.
  const details=q.locator('details').filter({hasText:'Cari produk untuk melihat pembanding'}).first()
  if(await details.getAttribute('open')!==null)await details.locator('summary').click()
  ;({a,read}=await open(ui,page,q,f));reads.push(read)
  const d=read.body.target_demand,done=state().job;assertDemand(d,model)
  assert.equal(d.contract_version,'cp7.target-demand-provenance.v3');assert.equal(d.model.state,'BASELINE_RETAINED');assert.equal(d.model.forecast_applied,false);assert.equal(d.model.baseline_target.target_pcs,d.target_pcs);
  assert.equal(d.basis,'REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION');assert.equal(d.target_pcs,f.expected_target)
  assert.equal(d.own_total_pcs,'0');assert.equal(d.own_available_days,'0');assert.equal(d.analog.source_key,f.source_key)
  assert.equal(d.analog.choice_id,saved.body.choice_id);assert.equal(d.analog.source_total_pcs,'1');assert.equal(d.analog.available_days,f.available_days)
  const shown=a.getByRole('region',{name:'Dasar kebutuhan target',exact:true})
  await ui.expect(shown).toContainText('Penjualan asli produk ini saat stok tersedia: 0 PCS dari 0 hari')
  await ui.expect(shown).toContainText(`Target rencana: ${f.expected_target} PCS`)
  await ui.expect(shown).toContainText('Actual browser review of Native source and physical size')
  await shown.scrollIntoViewIfNeeded();await shot('TARGET')
  await page.reload();q=await quantity(ui,page,f);({a,read}=await open(ui,page,q,f));reads.push(read)
  assert.deepEqual(state().job,done);assert.deepEqual(read.body.target_demand,d)
  if(!dense){
   form=await choiceForm(ui,page,a);await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Withdraw browser comparison')
   await form.getByRole('checkbox').check();const cleared=await response(page,SAVE,()=>form.getByRole('button',{name:'Cabut pilihan pembanding',exact:true}).click());assert.equal(cleared.status,200)
   await ui.expect(form).toContainText('Pilihan dicabut pada revisi 2');await a.getByRole('button',{name:'Tutup produk pembanding',exact:true}).click()
   const latest=await response(page,'erp_cp7_request_bounded_staged_analysis_v1',()=>q.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true}).click());assert.equal(latest.status,200)
   await ui.expect(q.locator('[data-quantity-target]').first()).toBeVisible({timeout:180000})
   const nextDetails=q.locator('details').filter({hasText:'Cari produk untuk melihat pembanding'}).first()
   if(await nextDetails.getAttribute('open')!==null)await nextDetails.locator('summary').click()
   ;({a,read}=await open(ui,page,q,f));reads.push(read)
   assertDemand(read.body.target_demand,model)
   assert.equal(read.body.target_demand.model.state,'BASELINE_RETAINED');assert.equal(read.body.target_demand.model.baseline_target.target_pcs,null);
   assert.equal(read.body.target_demand.basis,'UNKNOWN');assert.equal(read.body.target_demand.target_pcs,null)
   await ui.expect(a.getByRole('region',{name:'Dasar kebutuhan target',exact:true})).toContainText('Pilihan pembanding sudah dicabut')
  }else{
   assert.equal(f.size.products,2000);assert.equal(f.size.movements,202000);assert.equal(done.raw_history_state,'INCOMPLETE');assert.ok(Number(done.raw_stock_rows)>=202000)
  }
  assert.deepEqual(state().physical,before.physical);assert.equal(state().drafts,before.drafts);assert.equal(state().receipts,before.receipts)
  const modelAfter=scopedState(actor)
  assert.equal(modelSaved.business_sha256,modelBefore.business_sha256);assert.deepEqual(modelAfter,modelSaved)
  if(!dense){
   await a.getByRole('button',{name:'Tutup produk pembanding',exact:true}).click()
   fixture('deactivate',{actor})
   const denied=await response(page,'erp_cp7_read_product_analog_candidates_v1',()=>q.getByRole('button',{name:'Lihat pembanding '+f.sku,exact:true}).click());reads.push(denied)
   assert.equal(denied.status,403);await ui.expect(q.locator('table')).toHaveCount(0)
   await ui.expect(q).toContainText('tidak memiliki izin');await shot('ACCESS_REVOKED')
  }
  assert.equal(calls.filter(n=>n==='erp_cp7_capture_netting_v1').length,0)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  return{status:'PASS',model_target_overlay_actual_Auth_browser:true,versioned_provenance_v3_and_resolution_v2:true,actual_scoped_model_reference_retained:!dense,actual_scoped_history_model_lost_reply_reload_exact_recovery:!dense,current403_hides_quantity_results:!dense,positive_model_target_qualified:false,actual_Auth_PostgREST_browser:true,actual_Native_posted_sale:true,synthetic_historical_openings:true,
   actual_confirm_then_new_request_and_target:true,expected_target_pcs:f.expected_target,own_sales_and_days_remain_zero:true,
   exact_retained_provenance_after_reload:true,CLEAR_then_new_UNKNOWN:!dense,dense2000_202000:dense,
   no_physical_money_HPP_or_draft_effect_from_choice:true,no_horizontal_overflow:true,shots,full_OW11_acceptance:false}
 }catch(e){writeFileSync(`cp6-proof/t3/MODEL_TARGET_V2_${dense?'DESKTOP':'MOBILE'}_FAILURE.json`,JSON.stringify({error:String(e),calls,reads,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw e}
 finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_MODEL_TARGET_V2_BROWSER_MOBILE_UNKNOWN_ANALOG_CLEAR',()=>journey(ui,today,false)],
 ['OW11_MODEL_TARGET_V2_BROWSER_DESKTOP_DENSE_PROVENANCE_RELOAD',()=>journey(ui,today,true)],
]}
