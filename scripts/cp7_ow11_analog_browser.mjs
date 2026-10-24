import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {openCuttingMenu} from './cp7_ow13c_checked_browser.mjs'
const RPC='erp_cp7_read_product_analog_candidates_v1'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow11_analog_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function quantity(ui,page,f){
 await openCuttingMenu(ui,page,'Produksi','Buat Potongan')
 const panel=page.getByRole('region',{name:'Saran potong',exact:true})
 await panel.getByLabel('Penjualan mulai untuk saran potong',{exact:true}).fill(f.query.from_date)
 await panel.getByLabel('Penjualan sampai untuk saran potong',{exact:true}).fill(f.query.through_date)
 await panel.getByRole('button',{name:'Buka saran potong',exact:true}).click()
 const q=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true})
 await ui.expect(q.locator('tbody tr,[role="alert"]').first()).toBeVisible({timeout:180000})
 assert.deepEqual(await q.getByRole('alert').allTextContents(),[],'ANALOG_QUANTITY_ERROR')
 await ui.expect(q.locator('[data-quantity-target]').first()).toBeVisible()
 return q
}
async function reply(page,action){const pending=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+RPC));await action();const r=await pending;return{status:r.status(),args:r.request().postDataJSON(),body:await r.json()}}
async function open(ui,page,q,f){
 await q.locator('summary').filter({hasText:'Cari produk untuk melihat pembanding'}).click()
 await q.getByLabel('Cari SKU atau nama produk yang memerlukan pembanding',{exact:true}).fill(f.sku)
 const read=await reply(page,()=>q.getByRole('button',{name:'Lihat pembanding '+f.sku,exact:true}).click())
 assert.equal(read.status,200,JSON.stringify(read.body))
 const a=q.getByRole('region',{name:'Kandidat produk pembanding',exact:true})
 await ui.expect(a.locator('[data-analog-target]').first()).toBeVisible()
 assert.deepEqual(await a.getByRole('alert').allTextContents(),[])
 return{a,read}
}
async function journey(ui,today,dense){
 const f=fixture('prepare',{today,dense}),user=await ui.login('OWNER',{label:'analog-reader-'+dense,mobile:!dense,timezoneId:dense?'Asia/Jakarta':'America/Los_Angeles'}),page=user.page,actor=user.user.id
 let foreign=null;const calls=[],shots=[],observed=[]
 const state=()=>fixture('state',{actor}),shot=async suffix=>{const path=`cp6-proof/t3/ANALOG_${dense?'DESKTOP':'MOBILE'}_${suffix}.png`;await page.screenshot({path,fullPage:false});shots.push(path)}
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(dense?{width:1440,height:1000}:{width:390,height:844})
  const before=state();let q=await quantity(ui,page,f),{a,read}=await open(ui,page,q,f)
  observed.push(read);assert.equal(read.body.result.target_key,f.target_key)
  assert.equal(read.body.source_state,'CAPTURED_NOT_CHECKED');assert.equal(read.body.forecast_applied,false)
  assert.equal(read.body.result.minimum_available_days,'1');assert.equal(read.args.p_access,read.body.access_epoch)
  assert.equal(read.args.p_request,read.body.request_id);assert.equal(read.body.actor_scope_id,actor)
  const done=state().job;assert.equal(done.state,'DONE');assert.equal(done.coverage,'COMPLETE')
  assert.equal(read.body.request_id,done.request);assert.equal(read.body.run_id,done.run)
  assert.equal(calls.filter(n=>n==='erp_cp7_capture_netting_v1').length,0)
  await ui.expect(a).toContainText('Kandidat belum dipilih dan belum mengubah target produksi')
  await ui.expect(q.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true})).toBeDisabled()
  if(dense){
   assert.equal(f.size.products,2000);assert.equal(f.size.movements,202000)
   assert.equal(done.raw_history_state,'INCOMPLETE');assert.ok(Number(done.raw_stock_rows)>=202000)
   assert.equal(read.body.result.total,1999);assert.equal(read.body.result.candidates.length,50)
   const second=await reply(page,()=>a.getByRole('button',{name:'50 kandidat berikutnya',exact:true}).click());observed.push(second)
   await ui.expect(a).toContainText('Kandidat 51–100 dari 1999')
   assert.equal(second.status,200);assert.equal(second.body.result.candidates.length,50)
   assert.equal(new Set([...read.body.result.candidates,...second.body.result.candidates].map(r=>r.target_key)).size,100)
   for(const field of['request_id','run_id','identity_hash','access_epoch','producer_hash'])assert.equal(second.body[field],read.body[field])
   await a.locator('h4').scrollIntoViewIfNeeded();await shot('PAGED_REVIEWED')
   await page.reload();q=await quantity(ui,page,f);({a,read}=await open(ui,page,q,f));observed.push(read)
   assert.deepEqual(state().job,done,'ANALOG_RELOAD_MUST_KEEP_THE_SAME_DONE_JOB')
   assert.deepEqual(read.body,observed[0].body,'ANALOG_RELOAD_MUST_KEEP_THE_SAME_CAPTURED_READ')
   fixture('expire',{run:done.run})
   const expired=await reply(page,()=>a.getByRole('button',{name:'50 kandidat berikutnya',exact:true}).click());observed.push(expired)
   assert.ok(expired.status>=400);assert.equal(expired.body.message,'CP7_ANALYSIS_RESULT_EXPIRED')
   await ui.expect(a.locator('[data-analog-target]')).toHaveCount(0)
   await ui.expect(a.getByRole('alert')).toBeVisible()
  }else{
   assert.equal(f.imported_products,11);assert.equal(f.other_physical_targets.length,9)
   const rows=read.body.result.candidates;assert.equal(read.body.result.total,1);assert.equal(rows.length,1)
   assert.equal(Number(rows[0].observed_available_daily_mean),0);assert.equal(rows[0].available_days,1)
   assert.equal(rows[0].size_id,f.target_key.split(':')[1]);assert.ok(!f.other_physical_targets.includes(rows[0].target_key))
   const bad=await user.rpc(RPC,{...read.args,p_access:'0'.repeat(64)});assert.equal(bad.status,403);assert.equal(bad.body.message,'CP7_ANALYSIS_ACCESS_CHANGED')
   const anon=await ui.anonRpc(RPC,read.args);assert.ok([401,403].includes(anon.status))
   foreign=await ui.login('OWNER',{label:'analog-other-owner'});const wrong=await foreign.rpc(RPC,read.args);assert.equal(wrong.status,403)
   await a.locator('h4').scrollIntoViewIfNeeded();await shot('AVAILABLE_ZERO_REVIEWED')
   await a.getByRole('button',{name:'Tutup produk pembanding',exact:true}).click()
   fixture('deactivate',{actor})
   const denied=await reply(page,()=>q.getByRole('button',{name:'Lihat pembanding '+f.sku,exact:true}).click());observed.push(denied)
   assert.equal(denied.status,403);await ui.expect(q.locator('table')).toHaveCount(0)
   await ui.expect(q).toContainText('tidak memiliki izin');fixture('restore',{actor})
  }
  assert.deepEqual(state().physical,before.physical);assert.equal(state().drafts,before.drafts);assert.equal(state().receipts,before.receipts)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  return{status:'PASS',actual_Auth_PostgREST_browser:true,real_Native_DONE_snapshot:true,source_state:'CAPTURED_NOT_CHECKED',
   actual_available_zero_and_nine_other_sizes_excluded:!dense,actual_anon_foreign_bad_epoch_and_deactivated_denied:!dense,
   actual_dense2000_202000_pages_unique100:dense,actual_reload_same_request_result:dense,actual_K2_expired_refused_and_rows_cleared:dense,
   no_stock_money_HPP_or_draft_receipt_write_by_reader:true,no_old_whole_netting:true,no_horizontal_overflow:true,viewport:dense?1440:390,shots,
   selected:false,reviewed:false,forecast_applied:false,full_OW11_acceptance:false}
 }catch(error){writeFileSync(`cp6-proof/t3/ANALOG_${dense?'DESKTOP':'MOBILE'}_FAILURE.json`,JSON.stringify({error:String(error),calls,observed,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{fixture('restore',{actor});if(foreign)await foreign.context.close();await user.context.close()}
}
export function cases(ui,today){return[
 ['OW11_ANALOG_BROWSER_MOBILE_AVAILABLE_ZERO_SIZE_ACCESS',()=>journey(ui,today,false)],
 ['OW11_ANALOG_BROWSER_DESKTOP_DENSE_PAGES_RELOAD_K2',()=>journey(ui,today,true)],
]}
