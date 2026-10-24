import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {quantity,open} from './cp7_ow11_analog_browser.mjs'
const SAVE='erp_cp7_save_product_analog_choice_v1',GET='erp_cp7_get_product_analog_choices_v1'
const control=(script,op,p)=>JSON.parse(execFileSync('python',[`../auditor/scripts/${script}.py`,op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const fixture=(op,p)=>control('cp7_ow11_analog_browser_fixture',op,p)
const choice=(op,p)=>control('cp7_ow11_choice_browser_fixture',op,p)
async function response(page,rpc,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+rpc)),Promise.resolve().then(action)]);return{status:r.status(),body:await r.json()}}
async function review(ui,page,a){
 const read=await response(page,GET,()=>a.getByRole('button',{name:'Atur pilihan pembanding',exact:true}).click())
 assert.equal(read.status,200,JSON.stringify(read.body))
 const form=a.getByRole('region',{name:'Konfirmasi produk pembanding',exact:true})
 await ui.expect(form.getByRole('button',{name:'Baca ulang pilihan tersimpan',exact:true})).toBeEnabled()
 return form
}
async function fill(form,key,reason){
 await form.getByLabel('Produk pembanding',{exact:true}).selectOption(key)
 await form.getByLabel('Skala terhadap produk pembanding',{exact:true}).fill('1.25')
 await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill(reason)
 await form.getByRole('checkbox').check()
}
async function journey(ui,today,dense){
 const f=fixture('prepare',{today,dense}),user=await ui.login('OWNER',{label:'analog-choice-'+dense,mobile:!dense,timezoneId:dense?'Asia/Jakarta':'America/Los_Angeles'}),page=user.page,actor=user.user.id
 const requests=[],shots=[],calls=[];let lost=null
 const state=()=>fixture('state',{actor}),metadata=()=>choice('state',{actor,target:f.target_key})
 const shot=async suffix=>{const path=`cp6-proof/t3/CHOICE_${dense?'DESKTOP':'MOBILE'}_${suffix}.png`;await page.screenshot({path,fullPage:false});shots.push(path)}
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(dense?{width:1440,height:1000}:{width:390,height:844})
  const before=state(),metaBefore=metadata();let q=await quantity(ui,page,f),{a,read}=await open(ui,page,q,f),form=await review(ui,page,a)
  const done=state().job;assert.equal(done.state,'DONE');assert.equal(done.coverage,'COMPLETE')
  await ui.expect(form.getByLabel('Skala terhadap produk pembanding',{exact:true})).toHaveValue('')
  await ui.expect(form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true})).toBeDisabled()
  await page.route('**/rest/v1/rpc/'+SAVE,async route=>{
   const start=performance.now(),args=route.request().postDataJSON(),reply=await route.fetch(),body=await reply.json()
   requests.push({args,status:reply.status(),body,millis:performance.now()-start})
   if(!dense&&!lost&&reply.status()===200){lost=requests.at(-1);await route.abort('failed')}
   else await route.fulfill({response:reply})
  })
  await fill(form,read.body.result.candidates[0].target_key,'Explicit browser fixture review; not owner factory policy')
  await form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).click()
  await ui.expect.poll(()=>requests.length,{timeout:30000}).toBe(1)
  assert.equal(requests[0].status,200,JSON.stringify(requests[0].body))
  assert.equal(requests[0].body.state,'CONFIRMED_ASSUMPTION');assert.equal(requests[0].body.forecast_applied,false)
  const first=metadata();assert.equal(first.rows.length,metaBefore.rows.length+1);assert.equal(first.commands,metaBefore.commands+1)
  assert.deepEqual(state().physical,before.physical)
  if(!dense){
   await ui.expect(form.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true})).toBeEnabled()
   await ui.expect(form.locator('fieldset')).toHaveAttribute('disabled','')
   for(const control of await form.locator('fieldset select,fieldset input,fieldset textarea,fieldset button').all())await ui.expect(control).toBeDisabled()
   await page.reload();q=await quantity(ui,page,f);({a,read}=await open(ui,page,q,f));form=await review(ui,page,a)
   assert.deepEqual(state().job,done)
   await form.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true}).click()
   await ui.expect(form).toContainText('revisi 1 tersimpan')
   assert.equal(requests.length,2);assert.deepEqual(requests[0].args,requests[1].args);assert.deepEqual(requests[0].body,requests[1].body)
   assert.deepEqual(metadata(),first)
   fixture('expire',{run:done.run})
   await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Withdraw fixture choice after its source snapshot expired')
   await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Cabut pilihan pembanding',exact:true}).click()
   await ui.expect(form).toContainText('Pilihan dicabut pada revisi 2')
   assert.equal(requests.length,3);assert.equal(requests[2].body.state,'CLEARED')
   assert.equal(requests[2].args.p_payload.source_request,null);assert.equal(requests[2].args.p_payload.scale_factor,null)
   const old=await user.rpc(SAVE,requests[0].args);assert.equal(old.status,200);assert.deepEqual(old.body,requests[0].body)
   const final=metadata();assert.equal(final.rows.length,metaBefore.rows.length+2);assert.equal(final.commands,metaBefore.commands+2)
   assert.deepEqual(state().physical,before.physical)
  }else{
   await ui.expect(form).toContainText('revisi 1 tersimpan')
   assert.equal(f.size.products,2000);assert.equal(f.size.movements,202000);assert.equal(done.raw_history_state,'INCOMPLETE');assert.ok(Number(done.raw_stock_rows)>=202000)
   const changed=choice('change',{target:f.target_key});assert.equal(changed.actual_Native_stock_change,true)
   await fill(form,read.body.result.candidates[0].target_key,'Same captured source after real Native stock changed')
   await form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).click()
   await ui.expect.poll(()=>requests.length,{timeout:30000}).toBe(2)
   assert.equal(requests[1].body.code,'40001');assert.equal(requests[1].body.message,'CP7_ANALOG_CHOICE_SOURCE_CHANGED')
   await ui.expect(form.getByRole('alert')).toBeVisible();await ui.expect(form.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true})).toHaveCount(0)
   assert.deepEqual(metadata(),first);assert.deepEqual(state().physical,changed.physical)
   await form.scrollIntoViewIfNeeded();await shot('STALE_REFUSED')
   fixture('deactivate',{actor})
   const denied=await response(page,GET,()=>form.getByRole('button',{name:'Baca ulang pilihan tersimpan',exact:true}).click())
   assert.equal(denied.status,403);await ui.expect(q.locator('table')).toHaveCount(0)
   assert.equal((await user.rpc(SAVE,requests[0].args)).status,403)
   fixture('restore',{actor});assert.deepEqual(metadata(),first)
  }
  assert.equal(state().drafts,before.drafts);assert.equal(state().receipts,before.receipts)
  assert.equal(calls.filter(n=>n==='erp_cp7_capture_netting_v1').length,0)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await shot('REVIEWED')
  return{status:'PASS',actual_Auth_PostgREST_browser:true,actual_choice_metadata_write:true,exact_lost_reply_reload_UUID_payload_result:!dense,clear_after_actual_K2_expiry:!dense,
   actual_dense2000_202000:dense,actual_Native_stock_change_refuses_stale_confirmation:dense,current_deactivated_read_and_committed_replay_refused:dense,
   no_physical_money_HPP_effect_from_confirmation:true,no_draft_or_cutting_receipt_effect:true,no_old_whole_netting:true,no_horizontal_overflow:true,
   write_millis:requests.map(r=>r.millis),viewport:dense?1440:390,shots,forecast_applied:false,full_OW11_acceptance:false}
 }catch(error){writeFileSync(`cp6-proof/t3/CHOICE_${dense?'DESKTOP':'MOBILE'}_FAILURE.json`,JSON.stringify({error:String(error),calls,requests,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{await page.unrouteAll({behavior:'wait'});fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_CHOICE_BROWSER_MOBILE_LOSS_RELOAD_REPLAY_CLEAR',()=>journey(ui,today,false)],
 ['OW11_CHOICE_BROWSER_DESKTOP_DENSE_STALE_AND_REVOKED',()=>journey(ui,today,true)],
]}
