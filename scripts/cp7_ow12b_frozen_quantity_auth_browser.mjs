// Real Auth UI drives the actual public request, units, result pages and source check.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {buildPreparedQuantity} from './cp7_ow12b_frozen_quantity_auth_build.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow12b_frozen_quantity_auth_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:24*1024*1024}).trim())
const REQUEST='erp_cp7_request_bounded_staged_analysis_v2',STEP='erp_cp7_step_staged_analysis_v1',PAGES='erp_cp7_read_staged_analysis_pages_v1',PAGE='erp_cp7_read_staged_analysis_page_v1',CHECK='erp_cp7_check_staged_analysis_source_v1',ANALOG='erp_cp7_read_product_analog_candidates_v2'
const fields={'Stok fisik':'actual_fg','Target':'target_qty','Kurang sebelum pembagian global':'q_base','Kurang sesudah pembagian global':'q_conditional','Saran sebelum cek bahan dan kapasitas':'suggested_new','Tambahan kelipatan':'rounding_extra','Produksi baru layak':'feasible_new'}
// Independent rendering expectation, no arithmetic or forecast recomputation.
const fact=f=>f.state==='UNKNOWN'?'Belum diketahui':f.state==='CONFLICT'?'Data bertentangan':f.state==='NOT_APPLICABLE'?'Tidak berlaku':f.value.split('.').map((part,i)=>i?part:part.replace(/\B(?=(\d{3})+(?!\d))/g,'.')).join(',')+' '+f.unit+(f.state==='ASSUMED'?' · asumsi':'')
async function response(page,name,action){const[r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name)),Promise.resolve().then(action)]);return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function readable(panel){
 const rows=await panel.evaluate(root=>{
  const rgb=v=>v.match(/[\d.]+/g).map(Number),lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0)
  const out=[]
  for(const el of[root,...root.querySelectorAll('*')]){
   const s=getComputedStyle(el),label=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
   if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
   const layers=[];let bg=null
   for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p),v=rgb(c.backgroundColor);if(c.backgroundImage!=='none'||c.opacity!=='1')throw Error('UNMEASURED_QUANTITY_TEXT_SURFACE');if(v.length===3||v[3]===1){bg=v.slice(0,3);break}layers.push(v)}
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
 const user=await ui.login('OWNER',{label:'frozen-quantity-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
 const f=fixture('prepare',{today,actor}),state=()=>fixture('state',{actor}),before=state(),calls=[],shots=[],textContrasts=[];let lost=null,other=null
 assert.equal(f.browser_job_created,false);assert.equal(before.jobs.length,0)
 const panel=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true}),rows=()=>panel.locator('[data-quantity-target]'),url=built.url+'?query='+encodeURIComponent(JSON.stringify(f.query))
 const stored=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.cp7.bounded-analysis-request.v2:')).map(([key,bytes])=>({key,bytes,value:JSON.parse(bytes)})))
 const click=name=>panel.getByRole('button',{name,exact:true}).click()
 const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/FROZEN_QUANTITY_AUTH_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path);if(suffix!=='FAILURE')textContrasts.push({state:suffix,rows:await readable(panel)})}
 try{
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  // Only lose delivery of the first real committed response; never fabricate a result.
  await page.route('**/rest/v1/rpc/*',async route=>{
   const name=new URL(route.request().url()).pathname.split('/').at(-1),args=route.request().postDataJSON(),r=await route.fetch(),body=await r.json();calls.push({name,args,status:r.status(),body})
   if(!mobile&&name===REQUEST&&!lost){lost=calls.at(-1);await route.abort('failed')}else await route.fulfill({response:r})
  })
  await page.goto(url);await ui.expect(panel).toBeVisible()
  if(!mobile){
   await ui.expect.poll(()=>lost?.status).toBe(200);await ui.expect(panel.getByRole('alert')).toBeVisible();await ui.expect(panel.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true})).toBeDisabled()
   const held=await stored();assert.equal(held.length,1);assert.equal(held[0].value.id,lost.args.p_request);assert.deepEqual(held[0].value.q,lost.args.p_query);assert.equal(held[0].value.method,'cp7.bounded-analysis-request.v2')
   const interrupted=state();assert.equal(interrupted.jobs.length,1);assert.equal(interrupted.jobs[0].state,'RUNNING');assert.deepEqual(interrupted.physical,before.physical)
   await page.reload();await ui.expect(rows().first()).toBeVisible({timeout:180000});assert.deepEqual(await stored(),held)
  }else await ui.expect(rows().first()).toBeVisible({timeout:180000})
  const held=await stored();assert.equal(held.length,1);const request=held[0].value.id,after=state(),exact=fixture('read',{actor,request})
  assert.equal(after.jobs.length,1);assert.equal(after.jobs[0].request,request);assert.equal(after.jobs[0].state,'DONE');assert.equal(after.jobs[0].reference.bounded_request_contract,'cp7.bounded-analysis-request.v2');assert.equal(after.jobs[0].reference.bounded_input_coverage,'PENDING');assert.equal(after.jobs[0].reference.bounded_history_inputs,null)
  assert.deepEqual(after.physical,before.physical);assert.deepEqual(after.choices,before.choices)
  const req=calls.filter(c=>c.name===REQUEST);assert.ok(req.length>=2&&req.every(c=>c.status===200&&c.args.p_request===request))
  for(const c of req)assert.deepEqual(c.args.p_query,f.query)
  assert.ok(calls.some(c=>c.name===STEP&&c.status===200));assert.ok(calls.some(c=>c.name===PAGES&&c.status===200));assert.equal(calls.some(c=>c.name==='erp_cp7_request_bounded_staged_analysis_v1'),false)
  for(const c of req)assert.deepEqual(c.body.reference,req[0].body.reference)
  assert.equal(exact.page_set.page_count,1);assert.ok(exact.recommendations.length>0&&exact.recommendations.length<=50)
  await ui.expect(rows()).toHaveCount(exact.recommendations.length)
  let unknown=0
  for(const item of exact.recommendations){const row=panel.locator(`[data-quantity-target="${item.target.key}"]`);for(const[label,key]of Object.entries(fields)){await ui.expect(row.locator(`[data-label="${label}"]`)).toHaveText(fact(item[key]));if(item[key].state==='UNKNOWN')unknown++}}
  assert.ok(unknown>0);assert.deepEqual(await stored(),held)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await shot('READY')
  if(!mobile){
   const target=panel.locator(`[data-quantity-target="${f.target}"]`);await ui.expect(target).toBeVisible()
   const read=await response(page,ANALOG,()=>target.getByRole('button',{name:'Lihat produk pembanding',exact:true}).click());assert.equal(read.status,200);assert.equal(read.body.request_id,request);assert.equal(read.body.run_id,exact.page_set.run_id);assert.equal(read.body.bounded_request_contract,'cp7.bounded-analysis-request.v2');assert.deepEqual(read.body.reference,exact.page_set.reference);assert.equal(read.body.identity_hash,exact.page_set.identity_hash);assert.equal(read.body.actor_scope_id,actor)
   await ui.expect(page.getByRole('region',{name:'Kandidat produk pembanding',exact:true})).toBeVisible();await shot('ANALOG');await page.getByRole('button',{name:'Tutup produk pembanding',exact:true}).click()
   await page.reload();await ui.expect(rows().first()).toBeVisible({timeout:180000});assert.deepEqual(await stored(),held);assert.deepEqual(state(),after);await shot('RECOVERED')
  }else{
   fixture('stock',{root:f.root});const posted=state(),stale=await response(page,CHECK,()=>click('Periksa sumber kebutuhan'));assert.equal(stale.status,200);assert.equal(stale.body.source_state,'ARCHIVED_STALE');await ui.expect(panel).toContainText('sumber sudah berubah; hitung kebutuhan terbaru.');assert.deepEqual(await stored(),held);assert.deepEqual(state(),posted);await shot('STALE')
   other=await ui.login('OWNER',{label:'frozen-quantity-other'});const foreign=await other.rpc(PAGES,{p_run:exact.page_set.run_id});assert.equal(foreign.status,403);const anon=await ui.anonRpc(PAGES,{p_run:exact.page_set.run_id});assert.ok([401,403].includes(anon.status))
   fixture('deactivate',{actor});const denied=await response(page,CHECK,()=>click('Periksa sumber kebutuhan'));assert.equal(denied.status,403);await ui.expect(rows()).toHaveCount(0);await ui.expect(panel.getByRole('searchbox')).toHaveCount(0);assert.deepEqual(await stored(),held);assert.deepEqual(state(),posted);await shot('ACCESS_REVOKED')
  }
  assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]})
  return{status:'PASS',actual_AuthProvider:true,actual_AuthGate:true,actual_Auth_PostgREST_browser:true,actual_public_v2_request_units_DONE_pages:true,actual_reply_loss_reload_exact_method_query_UUID_one_job:!mobile,all_displayed_facts_equal_full_Native_Original:true,unknown_facts:unknown,actual_frozen_analog_handoff:!mobile,actual_Native_stock_post_stale_source:mobile,actual_anon_foreign_current_access_refusals:mobile,actual403_clears_quantities_retains_original_request:mobile,reference_microseconds_preserved:true,no_physical_or_choice_effect:true,viewport:mobile?390:1440,no_horizontal_overflow:true,visible_text_contrasts:textContrasts,request_calls:calls.filter(c=>c.name===REQUEST).length,step_calls:calls.filter(c=>c.name===STEP).length,source_paths:built.source_paths,source_sha256:built.source_sha256,shots,full_factory3600_qualified:false,cutting_SAVE_qualified:false,default_application_adopted:false,production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/FROZEN_QUANTITY_AUTH_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),calls,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{fixture('restore',{actor});await other?.context.close();await user.context.close()}
}
export async function cases(ui,today){const built=await buildPreparedQuantity(ui);built.source_sha256=Object.fromEntries(built.source_paths.map(p=>[p,createHash('sha256').update(readFileSync(p)).digest('hex')]));return[
 ['OW12B_FROZEN_QUANTITY_AUTH_BROWSER_DESKTOP_DONE_RECOVERY_ANALOG',()=>journey(ui,today,built,false)],
 ['OW12B_FROZEN_QUANTITY_AUTH_BROWSER_MOBILE_STALE_CURRENT_ACCESS',()=>journey(ui,today,built,true)],
]}
