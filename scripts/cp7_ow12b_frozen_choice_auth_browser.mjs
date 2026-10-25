import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {buildPreparedChoice} from './cp7_ow12b_frozen_choice_auth_build.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow12b_frozen_choice_auth_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const SAVE='erp_cp7_save_product_analog_choice_v2',GET='erp_cp7_get_product_analog_choices_v1',READ='erp_cp7_read_product_analog_candidates_v2'
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function journey(ui,today,built,mobile){
 const user=await ui.login('OWNER',{label:'frozen-choice-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const observed=[],shots=[];let other=null,lost=null
 const panel=page.getByRole('region',{name:'Kandidat produk pembanding',exact:true}),form=panel.getByRole('region',{name:'Konfirmasi produk pembanding',exact:true})
 const pending=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.cp7.analog-choice.v2:')).map(([,v])=>JSON.parse(v)))
 const state=()=>fixture('state',{actor}),shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/FROZEN_CHOICE_AUTH_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 const open=async f=>{const read=await response(page,READ,()=>page.goto(built.url+'?context='+encodeURIComponent(JSON.stringify(f.context))));observed.push(read);assert.equal(read.status,200,JSON.stringify(read));assert.deepEqual(read.body,f.exact_read);await ui.expect(panel).toBeVisible();return read}
 const choices=async()=>{const r=await response(page,GET,()=>panel.getByRole('button',{name:'Atur pilihan pembanding',exact:true}).click());observed.push(r);assert.equal(r.status,200);await ui.expect(form.getByRole('button',{name:'Baca ulang pilihan tersimpan',exact:true})).toBeEnabled()}
 const fill=async source=>{await form.getByLabel('Produk pembanding',{exact:true}).selectOption(source);await form.getByLabel('Skala terhadap produk pembanding',{exact:true}).fill('1.25');await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Actual Auth review of matching physical size and captured history');await form.getByRole('checkbox').check()}
 try{
  const f=fixture('prepare',{today,actor}),before=state();assert.equal(f.actual_Native_frozen_DONE,true)
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000});const first=await open(f)
  assert.equal(first.body.contract_version,'cp7.product-analog-candidates-read.v3');assert.equal(first.body.target_demand.basis,'UNKNOWN');assert.equal(first.body.target_demand.target_pcs,null)
  const source=first.body.result.candidates.find(x=>x.target_key===f.source);assert.ok(source);assert.match(source.observed_available_daily_mean,/^0(?:\.0+)?$/);assert.ok(source.available_days>0)
  assert.ok(first.body.result.candidates.every(x=>x.size_id===f.context.targetKey.split(':')[1]));await choices();await fill(f.source)
  const contrasts=await panel.locator('button').evaluateAll(buttons=>buttons.map(button=>{const s=getComputedStyle(button),luminance=color=>{const c=color.match(/[\d.]+/g).slice(0,3).map(x=>Number(x)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722},a=luminance(s.color),b=luminance(s.backgroundColor);return{label:button.textContent.trim(),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),opacity:s.opacity}}));assert.ok(contrasts.length>0&&contrasts.every(x=>x.label&&x.ratio>=4.5&&x.opacity==='1'),JSON.stringify(contrasts))
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await shot('READY')
  if(!mobile){
   await page.route('**/rest/v1/rpc/'+SAVE,async route=>{const args=route.request().postDataJSON(),r=await route.fetch(),body=await r.json();observed.push({args,status:r.status(),body});if(!lost){lost=observed.at(-1);await route.abort('failed')}else await route.fulfill({response:r})})
   await form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).click();await ui.expect.poll(()=>lost?.status).toBe(200)
   const retry=form.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true});await ui.expect(retry).toBeEnabled()
   const held=await pending();assert.equal(held.length,1);assert.equal(held[0].requestId,lost.args.p_request);assert.deepEqual(held[0].payload,lost.args.p_payload);assert.deepEqual(held[0].review.context,f.context)
   const committed=state();assert.equal(committed.choices,before.choices+1);assert.equal(committed.commands,before.commands+1);assert.deepEqual(committed.physical,before.physical)
   // The original archived view stays readable after its confirmation changes current inputs.
   await open(f);await choices();await retry.click();await ui.expect(form).toContainText('Bukti konfirmasi revisi 1 tersimpan.')
   assert.deepEqual(observed.filter(x=>x.args?.p_request===lost.args.p_request).at(-1),lost);assert.deepEqual(state(),committed);assert.deepEqual(await pending(),[])
   const fresh=fixture('capture',{today,actor,target:f.context.targetKey}),next=await open(fresh)
   assert.equal(next.body.target_demand.basis,'REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION');assert.equal(next.body.target_demand.target_pcs,'0');assert.equal(next.body.target_demand.analog.choice_id,lost.body.choice_id)
   await ui.expect(panel).toContainText('perkiraan berbasis produk pembanding');await shot('CONFIRMED');await choices()
   await form.getByLabel('Alasan kesamaan atau pencabutan',{exact:true}).fill('Withdraw reviewed frozen assumption');await form.getByRole('checkbox').check()
   const cleared=await response(page,SAVE,()=>form.getByRole('button',{name:'Cabut pilihan pembanding',exact:true}).click());assert.equal(cleared.status,200);assert.equal(cleared.body.revision,'2');await ui.expect(form).toContainText('Pilihan dicabut pada revisi 2.')
   const after=fixture('capture',{today,actor,target:f.context.targetKey});const unknown=await open(after);assert.equal(unknown.body.target_demand.basis,'UNKNOWN');assert.equal(unknown.body.target_demand.target_pcs,null);assert.deepEqual(state().physical,before.physical)
   // Replay remains exact after CLEAR; the currently visible revision is not overwritten.
   const replay=await user.rpc(SAVE,lost.args);assert.equal(replay.status,200);assert.deepEqual(replay.body,lost.body);assert.equal(state().choices,before.choices+2);assert.equal(state().commands,before.commands+2);await shot('CLEARED_UNKNOWN')
  }else{
   fixture('stock',{root:f.root});const posted=state(),refused=await response(page,SAVE,()=>form.getByRole('button',{name:'Simpan pilihan pembanding',exact:true}).click());observed.push(refused)
   assert.equal(refused.status,500);assert.equal(refused.body.code,'40001');assert.deepEqual(state(),posted);const held=await pending();assert.equal(held.length,1);assert.deepEqual(held[0].payload,refused.args.p_payload)
   await ui.expect(form.getByLabel('Skala terhadap produk pembanding',{exact:true})).toHaveValue('1.25')
   const args={p_request:f.context.requestId,p_target:f.context.targetKey,p_offset:0,p_limit:50,p_access:f.context.accessEpoch}
   other=await ui.login('OWNER',{label:'frozen-choice-other'});assert.equal((await other.rpc(READ,args)).status,403);assert.ok([401,403].includes((await ui.anonRpc(READ,args)).status))
   fixture('deactivate',{actor});const denied=await response(page,SAVE,()=>form.getByRole('button',{name:'Periksa hasil konfirmasi yang sama',exact:true}).click());observed.push(denied);assert.equal(denied.status,403)
   await ui.expect(form).toHaveCount(0);await ui.expect(panel.locator('[data-analog-target]')).toHaveCount(0);assert.deepEqual(await pending(),held);assert.deepEqual(state(),posted);await shot('ACCESS_REVOKED')
  }
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]})
  return{status:'PASS',actual_Auth_PostgREST_browser:true,actual_AuthProvider:true,actual_AuthGate:true,actual_Native_frozen_DONE:true,actual_form_submission:true,visible_button_contrasts:contrasts,exact_frozen_candidate_envelope:true,same_physical_size_AVAILABLE_zero_not_UNKNOWN:true,viewport:mobile?390:1440,no_horizontal_overflow:true,actual_confirm_lost_reply_exact_recovery:!mobile,fresh_zero_target_then_CLEAR_UNKNOWN:!mobile,committed_receipt_exact_after_CLEAR:!mobile,actual_Native_stock_post_stale_refusal:mobile,dirty_form_durable_command_retained:mobile,actual_anon_foreign_revoked_access_refused:mobile,actual403_clears_candidates_and_form:mobile,no_money_stock_HPP_effect_by_choice:true,source_paths:built.source_paths,source_sha256:built.source_sha256,shots,default_application_adopted:false,production_go:false}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/FROZEN_CHOICE_AUTH_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),observed,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw e}
 finally{fixture('restore',{actor});await other?.context.close();await user.context.close()}
}
export async function cases(ui,today){const built=await buildPreparedChoice(ui);built.source_sha256=Object.fromEntries(built.source_paths.map(p=>[p,createHash('sha256').update(readFileSync(p)).digest('hex')]));return[
 ['OW12B_FROZEN_CHOICE_AUTH_BROWSER_DESKTOP_CONFIRM_RECOVERY_CLEAR',()=>journey(ui,today,built,false)],
 ['OW12B_FROZEN_CHOICE_AUTH_BROWSER_MOBILE_STALE_AND_CURRENT_ACCESS',()=>journey(ui,today,built,true)],
]}
