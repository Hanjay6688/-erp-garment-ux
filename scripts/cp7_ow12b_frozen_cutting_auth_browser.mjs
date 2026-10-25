// PREPARED, NOT WIRED: actual Auth/browser checked cutting journeys.
// Existing AuthProvider/AuthGate/client/form/recovery; no mocked RPC or identity.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {buildPreparedCutting} from './cp7_ow12b_frozen_cutting_auth_build.mjs'

export const IDS=['OW12B_FROZEN_CUTTING_AUTH_BROWSER_DESKTOP_SAVE_LOST_REPLY_REPLAY',
 'OW12B_FROZEN_CUTTING_AUTH_BROWSER_MOBILE_CURRENT_ACCESS_RETAINS_COMMAND']
const REQUEST='erp_cp7_request_bounded_staged_analysis_v2',OPTIONS='erp_cp7_get_plan_options_v2',SAVE='erp_cp7_save_cutting_suggestion_v1'
const GROWING=['cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_cutting_checked.receipts']
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow12b_frozen_cutting_auth_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:24*1024*1024}).trim())
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
function decimal(value){assert.equal(typeof value,'string');assert.match(value,/^\d+(?:\.\d+)?$/);return value.replace(/^0+(?=\d)/,'').replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'')}
function noPhysical(before,after,delta){
 assert.deepEqual(after.physical,before.physical)
 for(const[table,value]of Object.entries(before.rows)){
  if(GROWING.includes(table)&&delta)assert.equal(after.rows[table][0],value[0]+delta,table)
  else assert.deepEqual(after.rows[table],value,table)
 }
}
function checked(result,request,source,target){
 assert.equal(result.contract_version,'cp7.plan-draft.v2');assert.equal(result.state,'SAVED');assert.equal(result.request_id,request)
 assert.equal(result.run_id,source.run_id);assert.equal(result.target_key,target);assert.equal(result.identity_hash,source.identity_hash)
 assert.deepEqual(Object.keys(result.cutting_save_guard).sort(),['contract_version','run_id','target_key','identity_hash','checked_at','feasible'].sort())
 assert.equal(result.cutting_save_guard.contract_version,'cp7.cutting-checked-save.v1');assert.equal(result.cutting_save_guard.feasible,true)
 assert.equal(result.cutting_save_guard.run_id,source.run_id);assert.equal(result.cutting_save_guard.target_key,target);assert.equal(result.cutting_save_guard.identity_hash,source.identity_hash)
 assert.equal(result.production_go,false)
}

async function readable(panel){
 const rows=await panel.evaluate(root=>{
  const rgb=v=>v.match(/[\d.]+/g).map(Number),lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0)
  const out=[]
  for(const el of[root,...root.querySelectorAll('*')]){
   const s=getComputedStyle(el),direct=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
   const value=el.tagName==='SELECT'?el.selectedOptions[0]?.textContent:el.tagName==='TEXTAREA'||el.tagName==='INPUT'&&!['checkbox','radio','hidden'].includes(el.type)?el.value||el.getAttribute('placeholder'):''
   const label=direct||value
   if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
   const layers=[];let bg=null
   for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p),v=rgb(c.backgroundColor);if(c.backgroundImage!=='none'||c.opacity!=='1')throw Error('UNMEASURED_QUANTITY_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,90),tag:p.tagName,classes:p.className,backgroundImage:c.backgroundImage,opacity:c.opacity}));if(v.length===3||v[3]===1){bg=v.slice(0,3);break}layers.push(v)}
   if(!bg)throw Error('MISSING_QUANTITY_SURFACE')
   for(const v of layers.reverse())bg=bg.map((x,i)=>v[i]*(v[3]??1)+x*(1-(v[3]??1)))
   const record=(label,color)=>{const f=rgb(color),fg=bg.map((x,i)=>f[i]*(f[3]??1)+x*(1-(f[3]??1))),a=lum(fg),b=lum(bg);out.push({label:label.slice(0,90),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)})}
   record(label,s.color)
   if(el.hasAttribute('data-label')){const pseudo=getComputedStyle(el,'::before');if(pseudo.display!=='none'&&pseudo.content!=='none')record(el.getAttribute('data-label'),pseudo.color)}
  }
  return out
 });assert.ok(rows.length>0&&rows.every(x=>x.ratio>=4.5),JSON.stringify(rows.filter(x=>x.ratio<4.5)));return rows
}

async function journey(ui,today,built,mobile){
 const user=await ui.login('OWNER',{label:'frozen-cutting-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const f=fixture('prepare',{today,actor}),before=fixture('state',{actor}),calls=[],shots=[],contrasts=[];let lost=null,other=null
 assert.equal(f.browser_request_precreated,false);assert.deepEqual(before.jobs.map(j=>j.request),f.setup_requests)
 const panel=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true}),form=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true})
 const row=panel.locator(`[data-quantity-target="${f.target}"]`),url=built.url+'?query='+encodeURIComponent(JSON.stringify(f.query))
 const storedAnalysis=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.cp7.bounded-analysis-request.v2:')).map(([key,bytes])=>({key,bytes,value:JSON.parse(bytes)})))
 const pending=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.PLAN_APPLY_STAGED.pending-mutation.v1:')).map(([key,bytes])=>({key,bytes,value:JSON.parse(bytes)})))
 const state=()=>fixture('state',{actor})
 const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/FROZEN_CUTTING_AUTH_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path);if(suffix!=='FAILURE')contrasts.push({state:suffix,rows:await readable(panel)})}
 try{
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  await page.route('**/rest/v1/rpc/*',async route=>{
   const name=new URL(route.request().url()).pathname.split('/').at(-1),args=route.request().postDataJSON(),r=await route.fetch(),body=await r.json()
   calls.push({name,args,status:r.status(),body})
   if(!mobile&&name===SAVE&&!lost){assert.equal(r.status(),200);lost=calls.at(-1);await route.abort('failed')}
   else await route.fulfill({response:r})
  })
  await page.goto(url);await ui.expect(row).toBeVisible({timeout:180000})
  const analysis=await storedAnalysis();assert.equal(analysis.length,1);const request=analysis[0].value.id
  assert.equal(f.setup_requests.includes(request),false);assert.deepEqual(analysis[0].value.q,f.query);assert.equal(analysis[0].value.method,'cp7.bounded-analysis-request.v2')
  const captured=state(),exact=fixture('read',{actor,request});assert.equal(captured.jobs.length,before.jobs.length+1)
  const job=captured.jobs.find(j=>j.request===request);assert.ok(job);assert.equal(job.state,'DONE');assert.deepEqual(job.reference,exact.reference)
  for(const old of before.jobs)assert.deepEqual(captured.jobs.find(j=>j.request===old.request).reference,old.reference)
  assert.ok(calls.some(c=>c.name===REQUEST&&c.status===200&&c.args.p_request===request));assert.equal(calls.some(c=>c.name==='erp_cp7_request_bounded_staged_analysis_v1'),false)
  noPhysical(before.metadata,captured.metadata,0)
  await row.getByRole('button',{name:'Periksa saran potong',exact:true}).click();await ui.expect(form).toBeVisible()
  let loaded=await response(page,OPTIONS,()=>form.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(loaded.status,200)
  await form.getByLabel('Gudang bahan rencana',{exact:true}).selectOption(f.location)
  loaded=await response(page,OPTIONS,()=>form.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(loaded.status,200)
  const o=loaded.body,rec=exact.recommendations.find(r=>r.target.key===f.target);assert.ok(rec);assert.notEqual(rec.q_conditional.state,'UNKNOWN')
  assert.equal(decimal(o.needed_pcs),decimal(rec.q_conditional.value));assert.equal(o.run_id,exact.page_set.run_id);assert.equal(o.target_key,f.target);assert.equal(o.identity_hash,exact.page_set.identity_hash)
  assert.ok(o.orders.some(x=>x.id===f.po)&&o.patterns.length>0)
  const rolls=o.rolls.filter(r=>r.material_id===f.material);assert.equal(rolls.length,1);const roll=rolls[0]
  await form.getByLabel('PO rencana',{exact:true}).selectOption(f.po);await form.getByLabel('Pola rencana',{exact:true}).selectOption(o.patterns[0].id)
  await form.getByLabel('Waktu pencatatan draf WIB',{exact:true}).fill(f.cut_at_wib)
  await form.getByRole('button',{name:'Pilih roll '+roll.number,exact:true}).click()
  for(const[label,value]of [['Keluar roll rencana 1','1'],['Terpakai roll rencana 1','0.5'],['Sisa roll rencana 1','0.5'],['Hasil roll rencana 1','2'],['Alasan rencana Potongan','Actual Auth reviewed cutting draft; physical stock remains unchanged']])await form.getByLabel(label,{exact:true}).fill(value)
  const reviewed=form.getByRole('checkbox',{name:'Asumsi dan komposisi rencana sudah diperiksa',exact:true});await reviewed.check()
  const box=await reviewed.boundingBox();assert.ok(box&&box.width>=20&&box.height>=20)
  const submit=form.getByRole('button',{name:'Simpan rencana Potongan',exact:true});await ui.expect(submit).toBeEnabled()
  if(mobile){
   const boxes=await form.locator('input,select,textarea,button').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>{const r=n.getBoundingClientRect();return{left:r.left,right:r.right}}))
   assert.ok(boxes.length&&boxes.every(r=>r.left>=0&&r.right<=391))
  }
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);await shot('READY')
  if(!mobile){
   await submit.click();await ui.expect.poll(()=>lost?.status).toBe(200);await ui.expect(form.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   const held=await pending();assert.equal(held.length,1);assert.equal(held[0].value.id,lost.args.p_request);assert.deepEqual(held[0].value.payload,lost.args.p_payload)
   assert.equal(held[0].value.payload.cutting_save_contract,'cp7.cutting-checked-save.v1');checked(lost.body,held[0].value.id,exact.page_set,f.target)
   const committed=state();noPhysical(captured.metadata,committed.metadata,1)
   const native=fixture('receipt',{actor,request:held[0].value.id});assert.deepEqual(native.result,lost.body);assert.deepEqual(native.payload,lost.args.p_payload);assert.equal(native.current_draft.state,'SAVED')
   await page.reload();await ui.expect(row).toBeVisible({timeout:180000});assert.deepEqual(await storedAnalysis(),analysis);assert.deepEqual(await pending(),held)
   await row.getByRole('button',{name:'Periksa saran potong',exact:true}).click();await ui.expect(form).toBeVisible()
   const replay=await response(page,SAVE,()=>form.getByRole('button',{name:'Reconcile transaksi',exact:true}).click());assert.equal(replay.status,200);assert.deepEqual(replay.args,lost.args);assert.deepEqual(replay.body,lost.body)
   await ui.expect(form).toContainText('Rencana tersimpan.');await ui.expect.poll(pending).toEqual([]);assert.deepEqual(state(),committed);await shot('RECOVERED')
  }else{
   other=await ui.login('OWNER',{label:'frozen-cutting-foreign'})
   assert.equal((await other.rpc(OPTIONS,loaded.args)).status,403);assert.ok([401,403].includes((await ui.anonRpc(OPTIONS,loaded.args)).status))
   fixture('deactivate',{actor});const prior=state(),denied=await response(page,SAVE,()=>submit.click());assert.equal(denied.status,403)
   const held=await pending();assert.equal(held.length,1);assert.equal(held[0].value.id,denied.args.p_request);assert.deepEqual(held[0].value.payload,denied.args.p_payload)
   await ui.expect(form).toHaveCount(0);await ui.expect(panel.locator('[data-quantity-target]')).toHaveCount(0)
   assert.deepEqual(await storedAnalysis(),analysis);assert.deepEqual(state(),prior);noPhysical(captured.metadata,prior.metadata,0);assert.deepEqual(await pending(),held);await shot('ACCESS_REVOKED')
  }
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]})
  return{status:'PASS',actual_AuthProvider:true,actual_AuthGate:true,actual_Auth_PostgREST_browser:true,
   actual_browser_created_distinct_v2_request_and_completed_DONE:true,setup_jobs_retained_without_deletion:true,
   actual_existing_checked_form:true,displayed_need_equals_own_Native_Original:true,actual_committed_SAVE_and_exact_replyloss_recovery:!mobile,
   actual_current_foreign_anon_access_refused:mobile,current403_retires_quantities_and_form_preserves_original_command:mobile,
   no_physical_stock_money_HPP_effect:true,viewport:mobile?390:1440,no_horizontal_overflow:true,form_checkbox_min20px:true,
   visible_text_contrasts:contrasts,source_paths:built.source_paths,source_sha256:built.source_sha256,shots,
   default_application_adopted:false,full_factory3600_qualified:false,production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/FROZEN_CUTTING_AUTH_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),calls,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{fixture('restore',{actor});await other?.context.close();await user.context.close()}
}

export async function cases(ui,today){const built=await buildPreparedCutting(ui);built.source_sha256=Object.fromEntries(built.source_paths.map(p=>[p,createHash('sha256').update(readFileSync(p)).digest('hex')]));return IDS.map((id,index)=>[id,()=>journey(ui,today,built,index===1)])}
