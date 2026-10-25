import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {buildPreparedSchedule} from './cp7_ow12b_frozen_work_auth_build.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow12b_frozen_work_auth_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const SAVE='erp_cp7_save_staged_production_schedule_v1',GET='erp_cp7_get_staged_production_schedule_v1',REQUEST='erp_cp7_request_bounded_staged_analysis_v2'
const wib=t=>new Date(Date.parse(t)+7*3600000).toISOString().slice(0,19)
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function fill(panel,c){
 await panel.getByLabel('Tempat kerja pilihan',{exact:true}).fill(c.work_centre_key)
 await panel.getByLabel('Batas jadwal WIB',{exact:true}).fill(wib(c.through_at))
 await panel.getByLabel('Waktu satu PCS baru',{exact:true}).fill(c.unit_minutes??'')
 for(let i=0;i<c.windows.length;i++){
  if(!await panel.getByLabel(`Mulai kerja ${i+1} WIB`,{exact:true}).count())await panel.getByRole('button',{name:'Tambah waktu kerja',exact:true}).click()
  const v=c.windows[i];await panel.getByLabel(`Mulai kerja ${i+1} WIB`,{exact:true}).fill(wib(v.starts_at));await panel.getByLabel(`Selesai kerja ${i+1} WIB`,{exact:true}).fill(wib(v.ends_at));await panel.getByLabel(`Beban lain ${i+1}`,{exact:true}).fill(v.other_load_minutes??'')
 }
 for(const p of c.positions){
  await panel.getByLabel('Jumlah '+p.position_key,{exact:true}).fill(p.eligible_input_pcs)
  const target=panel.getByLabel('Tujuan '+p.position_key,{exact:true})
  if(await target.count()){await target.selectOption(p.target_key??'');await panel.getByLabel('Bagus '+p.position_key,{exact:true}).fill(p.yield_numerator??'');await panel.getByLabel('Acuan '+p.position_key,{exact:true}).fill(p.yield_denominator??'')}
  for(const s of p.remaining_steps)await panel.getByLabel(s.stage+' menit '+p.position_key,{exact:true}).fill(s.remaining_minutes??'')
 }
 await panel.getByLabel('Alasan jadwal',{exact:true}).fill('Actual Auth frozen schedule review; synthetic fixture assumptions')
}
async function journey(ui,today,built,mobile){
 const user=await ui.login('OWNER',{label:'frozen-work-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const f=fixture('prepare',{today}),state=()=>fixture('state',{actor}),before=state(),observed=[],shots=[];let other=null,lost=null
 const url=built.url+'?query='+encodeURIComponent(JSON.stringify(f.query)),panel=page.getByRole('region',{name:'Jadwal produksi',exact:true})
 const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/FROZEN_AUTH_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 const pending=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.cp7.schedule-request.v2:')).map(([,v])=>JSON.parse(v)))
 try{
  await page.goto(url);await ui.expect(panel).toBeVisible();await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  const[request,read]=await Promise.all([response(page,REQUEST,()=>panel.getByRole('button',{name:'Ambil stok proses terbaru',exact:true}).click()),response(page,GET,()=>{})]);observed.push(request,read)
  assert.equal(request.status,200,JSON.stringify(request));assert.equal(read.status,200,JSON.stringify(read))
  assert.equal(read.body.contract_version,'cp7.planning-schedule-staged-bounded.v2');assert.equal(read.body.history_input_coverage,'PENDING');assert.equal(read.body.analysis_state,'RUNNING');assert.equal(read.body.production_capture_state,'COMPLETE')
  assert.equal(f.actual_Native_import_customer_work,true);const customer=read.body.position_requirements.find(p=>p.position_key===f.customer_position);assert.ok(customer);assert.equal(customer.ownership,'CUSTOMER');assert.equal(customer.eligible_company_wip,false);assert.equal(customer.remaining_pcs,'8');assert.deepEqual(customer.target_candidates,[]);
  const job=state().job;assert.equal(job.request,request.args.p_request);assert.equal(job.request_contract,'cp7.bounded-analysis-request.v2');assert.equal(job.reference_contract,'cp7.bounded-analysis-reference.v2')
  await ui.expect(panel.locator('form')).toBeVisible();await fill(panel,f.config);await ui.expect(panel).toContainText('tidak menambah stok perusahaan');await ui.expect(panel.getByLabel('Tujuan '+f.customer_position,{exact:true})).toHaveCount(0);await ui.expect(panel.getByLabel('Bagus '+f.customer_position,{exact:true})).toHaveCount(0)
  const contrasts=await panel.locator('button').evaluateAll(buttons=>buttons.map(button=>{const s=getComputedStyle(button),luminance=color=>{const c=color.match(/[\d.]+/g).slice(0,3).map(x=>Number(x)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722},a=luminance(s.color),b=luminance(s.backgroundColor);return{label:button.textContent.trim(),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),opacity:s.opacity}}));assert.ok(contrasts.length>0&&contrasts.every(x=>x.label&&x.ratio>=4.5&&x.opacity==='1'),JSON.stringify(contrasts))
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await shot('READY')
  if(!mobile){
   await page.route('**/rest/v1/rpc/'+SAVE,async route=>{const args=route.request().postDataJSON(),r=await route.fetch(),body=await r.json();observed.push({args,status:r.status(),body});if(!lost){lost=observed.at(-1);await route.abort('failed')}else await route.fulfill({response:r})})
   await panel.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).click();await ui.expect.poll(()=>lost?.status).toBe(200)
   const retry=panel.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true});await ui.expect(retry).toBeEnabled()
   const held=await pending();assert.equal(held.length,1);assert.equal(held[0].id,lost.args.p_request);assert.deepEqual(held[0].payload,lost.args.p_payload);assert.equal(held[0].actor,actor);assert.equal(held[0].sourceMethod,'FROZEN_V2')
   const committed=state();assert.equal(committed.plans,before.plans+1);assert.equal(committed.commands,before.commands+1);assert.deepEqual(committed.physical,before.physical)
   await page.reload();await ui.expect(retry).toBeEnabled();await retry.click();await ui.expect(panel).toContainText('Jadwal tersimpan.')
   assert.deepEqual(observed.at(-1),lost);assert.deepEqual(state(),committed);assert.deepEqual(await pending(),[]);await shot('RECOVERED')
  }else{
   await panel.getByLabel('Waktu satu PCS baru',{exact:true}).fill('3');fixture('stock',{root:f.root});const posted=state()
   const refused=await response(page,SAVE,()=>panel.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).click());observed.push(refused)
   assert.equal(refused.status,500);assert.equal(refused.body.code,'40001');assert.equal(posted.plans,before.plans);assert.equal(posted.commands,before.commands);assert.deepEqual(state(),posted)
   await ui.expect(panel.getByLabel('Waktu satu PCS baru',{exact:true})).toHaveValue('3');const held=await pending();assert.equal(held.length,1);assert.deepEqual(held[0].payload,refused.args.p_payload)
   other=await ui.login('OWNER',{label:'frozen-work-other'});const foreign=await other.rpc(GET,{p_source_request:job.request});assert.equal(foreign.status,403)
   const anon=await ui.anonRpc(GET,{p_source_request:job.request});assert.ok([401,403].includes(anon.status))
   fixture('deactivate',{actor});const denied=await response(page,SAVE,()=>panel.getByRole('button',{name:'Ulangi simpan jadwal yang sama',exact:true}).click());observed.push(denied);assert.equal(denied.status,403)
   await ui.expect(panel.locator('form')).toHaveCount(0);assert.deepEqual(await pending(),held);assert.deepEqual(state(),posted);await shot('ACCESS_REVOKED')
  }
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]})
  return{status:'PASS',actual_Auth_PostgREST_browser:true,actual_AuthProvider:true,actual_AuthGate:true,actual_pending_v2_source:true,actual_form_submission:true,actual_Native_import_customer_work:true,customer8_uses45_minutes_no_company_yield:true,visible_button_contrasts:contrasts,viewport:mobile?390:1440,no_horizontal_overflow:true,actual_reply_loss_reload_same_UUID_payload_one_receipt:!mobile,actual_Native_stock_post_stale_refusal:mobile,dirty_form_and_durable_request_retained:mobile,actual_anon_foreign_current_access_refusals:mobile,actual403_clears_form:mobile,no_physical_effect_by_schedule:true,source_paths:built.source_paths,source_sha256:built.source_sha256,shots,default_application_adopted:false,production_go:false}
 }catch(e){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/FROZEN_AUTH_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(e),observed,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw e}
 finally{fixture('restore',{actor});await other?.context.close();await user.context.close()}
}
export async function cases(ui,today){const built=await buildPreparedSchedule(ui);built.source_sha256=Object.fromEntries(built.source_paths.map(p=>[p,createHash('sha256').update(readFileSync(p)).digest('hex')]));return[
 ['OW12B_FROZEN_WORK_AUTH_BROWSER_DESKTOP_PENDING_SAVE_EXACT_RECOVERY',()=>journey(ui,today,built,false)],
 ['OW12B_FROZEN_WORK_AUTH_BROWSER_MOBILE_STALE_AND_CURRENT_ACCESS',()=>journey(ui,today,built,true)],
]}
