import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const GET='erp_cp7_get_model_activation_policy_v1',SAVE='erp_cp7_save_model_activation_policy_v1'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow11_model_policy_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'model-policy-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const demand=page.getByRole('region',{name:'Data permintaan ERP',exact:true}),model=page.getByRole('region',{name:'Evaluasi ramalan ERP',exact:true}),panel=page.getByRole('region',{name:'Kebijakan penggunaan model',exact:true}),shots=[]
 const state=()=>fixture('state',{actor});let lost=null
 const shot=async suffix=>{await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);const path=`cp6-proof/t3/MODEL_POLICY_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await panel.scrollIntoViewIfNeeded();await page.screenshot({path,fullPage:true});shots.push(path)}
 async function open(){
  await navigate(page);await demand.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
  const from=new Date(Date.parse(today+'T00:00:00Z')-12*86400000).toISOString().slice(0,10)
  await demand.getByLabel('Permintaan dari tanggal',{exact:true}).fill(from)
  const history=await response(page,'erp_cp7_capture_demand_history_v1',()=>demand.getByRole('button',{name:'Muat data permintaan',exact:true}).click());assert.equal(history.status,200)
  const sku=history.body.current_stock.find(x=>x.root_id===f.product).sku
  await demand.getByLabel('Cari data permintaan',{exact:true}).fill(sku);await demand.getByRole('button',{name:'Bandingkan ramalan '+sku,exact:true}).click()
  const read=await response(page,GET,()=>model.getByRole('button',{name:'Tinjau syarat penggunaan model',exact:true}).click());assert.equal(read.status,200,JSON.stringify(read.body));return read.body
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  const initial=await open(),before=state(),rev=BigInt(initial.revision)
  assert.equal(await panel.getByLabel('Minimum hari pelatihan (Hari)',{exact:true}).inputValue(),'')
  assert.equal(before.model_rows,0);assert.equal(await panel.getByRole('checkbox',{name:'Nilai terakhir',exact:true}).isChecked(),false)
  for(const[label,value]of[['Minimum hari pelatihan (Hari)','20'],['Maksimum hari ramalan (Hari)','90'],['Minimum putaran pembanding lengkap (Putaran)','3'],['Minimum perbaikan kesalahan rata-rata (PCS)','0'],['Batas tambahan bias absolut (PCS)','0'],['Batas tambahan kesalahan seluruh periode (PCS)','0'],['Jarak musiman untuk pembandingan (Hari)','7']])await panel.getByLabel(label,{exact:true}).fill(value)
  await panel.getByRole('checkbox',{name:'Nilai terakhir',exact:true}).check()
  await panel.getByLabel('Alasan kebijakan atau pencabutan',{exact:true}).fill('Explicit SYNTHETIC browser policy review')
  await panel.getByRole('checkbox',{name:'Saya telah meninjau syarat bukti, model yang diizinkan, parameter tetap, dan alasan perubahan ini.',exact:true}).check()
  await page.route('**/rest/v1/rpc/'+SAVE,async route=>{if(!lost){const r=await route.fetch();assert.equal(r.status(),200);lost={envelope:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()})
  await panel.getByRole('button',{name:'Simpan kebijakan yang ditinjau',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Periksa hasil kebijakan yang sama',exact:true})).toBeEnabled()
  const pending=state();assert.equal(pending.policy_rows,before.policy_rows+1);assert.equal(pending.command_rows,before.command_rows+1);assert.equal(pending.registry_rows,before.registry_rows+1);assert.equal(pending.business_sha256,before.business_sha256)
  await page.reload();await open()
  const replay=await response(page,SAVE,()=>panel.getByRole('button',{name:'Periksa hasil kebijakan yang sama',exact:true}).click());assert.equal(replay.status,200);assert.deepEqual(replay.args,lost.envelope);assert.deepEqual(replay.body,lost.body);assert.equal(replay.body.policy.revision,(rev+1n).toString());assert.equal(replay.body.forecast_applied,false)
  await ui.expect(panel).toContainText(`Kebijakan revisi ${rev+1n} tersimpan`);assert.deepEqual(state(),pending)
  await panel.getByRole('button',{name:'Isi dari kebijakan tersimpan',exact:true}).click();assert.equal(await panel.getByLabel('Minimum hari pelatihan (Hari)',{exact:true}).inputValue(),'20');await shot('REVIEW')
  await panel.getByLabel('Alasan kebijakan atau pencabutan',{exact:true}).fill('Explicit browser withdrawal')
  await panel.getByRole('checkbox',{name:'Saya telah meninjau syarat bukti, model yang diizinkan, parameter tetap, dan alasan perubahan ini.',exact:true}).check()
  const withdrawn=await response(page,SAVE,()=>panel.getByRole('button',{name:'Cabut kebijakan model',exact:true}).click());assert.equal(withdrawn.status,200);assert.equal(withdrawn.body.policy.state,'SUSPENDED');assert.equal(withdrawn.body.policy.revision,(rev+2n).toString());assert.deepEqual(withdrawn.body.policy.config,lost.body.policy.config)
  await ui.expect(panel).toContainText(`Kebijakan revisi ${rev+2n} dicabut`);const after=state();assert.equal(after.business_sha256,before.business_sha256);assert.equal(after.model_rows,0)
  const dirty=page.getByLabel('Cari barang jadi',{exact:true});await dirty.fill('MODEL POLICY KEEP SEARCH')
  fixture('deactivate',{actor});const denied=await response(page,GET,()=>panel.getByRole('button',{name:'Baca ulang kebijakan',exact:true}).click());assert.equal(denied.status,403)
  await ui.expect(panel.locator('dl')).toHaveCount(0);await ui.expect(page.locator('.cfg-totals')).toHaveCount(0);assert.equal(await dirty.inputValue(),'MODEL POLICY KEEP SEARCH')
  await shot('REVOKED')
  return{status:'PASS',actual_Auth_PostgREST_browser:true,explicit_fields_no_default_threshold:true,actual_policy_registry_command_pair:true,lost_reply_reload_exact_UUID_payload_receipt:true,append_suspend_old_configuration_preserved:true,current403_retires_policy_parent_FG_HPP:true,no_business_write_or_model_forecast_activation:true,model_rows:0,no_horizontal_overflow:true,shots,full_OW11_acceptance:false}
 }catch(e){writeFileSync(`cp6-proof/t3/MODEL_POLICY_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),lost,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw e}
 finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_MODEL_POLICY_BROWSER_MOBILE_EXACT_RECOVERY_SUSPEND',()=>journey(ui,today,true)],
 ['OW11_MODEL_POLICY_BROWSER_DESKTOP_REVIEW_ACCESS_REVOKED',()=>journey(ui,today,false)],
]}
