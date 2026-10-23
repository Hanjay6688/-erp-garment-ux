import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {openWorkPlanning,fillWorkPlanning} from './cp7_ow13c_schedule_browser.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow13c_quantity_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const SAVE='erp_cp7_save_cutting_suggestion_v1',wib=t=>new Date(Date.parse(t)+7*3600000).toISOString().slice(0,16)
async function quantity(ui,page,f){
 const work=await openWorkPlanning(ui,page,f.query)
 await work.getByRole('button',{name:'Hitung kekurangan seluruh produk',exact:true}).click()
 const q=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true})
 await ui.expect(q.locator('tbody tr').first()).toBeVisible({timeout:180000})
 return q
}
async function response(page,name,action){const reply=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/rpc/'+name));await action();return reply}
async function journey(ui,today,dense){
 const f=fixture('prepare',{today,dense}),user=await ui.login('OWNER',{label:'bounded-quantity-'+dense,mobile:!dense,timezoneId:dense?'Asia/Jakarta':'America/Los_Angeles'}),page=user.page,actor=user.user.id
 const calls=[],requests=[],shots=[];let q,lost=null
 const state=()=>fixture('state',{actor})
 const shot=async suffix=>{const path=`cp6-proof/t3/QUANTITY_${dense?'LARGE_DESKTOP':'SMALL_MOBILE'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/rpc/'))calls.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await page.setViewportSize(dense?{width:1440,height:1000}:{width:390,height:844})
  const before=state()
  if(!dense){
   const work=await openWorkPlanning(ui,page,f.query)
   await work.getByRole('button',{name:'Ambil stok proses terbaru',exact:true}).click()
   await ui.expect(work.getByLabel('Tempat kerja pilihan',{exact:true})).toBeVisible()
   await fillWorkPlanning(work,f.config)
   await work.getByRole('button',{name:'Simpan jadwal yang diperiksa',exact:true}).click()
   await ui.expect(work).toContainText('Jadwal tersimpan')
   await work.getByRole('button',{name:'Ambil stok proses terbaru',exact:true}).click()
   await ui.expect(work.getByRole('button',{name:'Hitung kekurangan seluruh produk',exact:true})).toBeEnabled()
   await work.getByRole('button',{name:'Hitung kekurangan seluruh produk',exact:true}).click()
   q=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true})
   await ui.expect(q.locator('tbody tr').first()).toBeVisible({timeout:180000})
  }else q=await quantity(ui,page,f)
  assert.equal(calls.filter(n=>n==='erp_cp7_capture_netting_v1').length,0)
  await ui.expect(q).toContainText(f.expected_targets.toLocaleString('id-ID')+' target')
  assert.ok(await q.locator('tbody tr').count()<=50)
  const after=state();assert.equal(after.job.state,'DONE');assert.equal(after.job.coverage,'COMPLETE');assert.deepEqual(after.physical,before.physical)
  if(dense){
   assert.equal(f.size.products,2000);assert.equal(f.size.movements,202000)
   assert.equal(after.job.raw_history_state,'INCOMPLETE');assert.ok(Number(after.job.raw_stock_rows)>=202000)
   await q.getByRole('button',{name:'Periksa sumber kebutuhan',exact:true}).click()
   await ui.expect(q).toContainText('sama dengan data saat itu')
   fixture('stock',{root:f.root})
   await q.getByRole('button',{name:'Periksa sumber kebutuhan',exact:true}).click()
   await ui.expect(q).toContainText('sumber sudah berubah')
   const changed=state(),old=changed.job.request
   await q.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true}).click()
   await ui.expect(q.locator('tbody tr').first()).toBeVisible({timeout:180000})
   const fresh=state();assert.notEqual(fresh.job.request,old);assert.equal(fresh.job.state,'DONE');assert.deepEqual(fresh.physical,changed.physical)
  }else{
   const row=q.locator(`[data-quantity-target="${f.target_key}"]`)
   await ui.expect(row).toHaveCount(1);await row.getByRole('button',{name:'Periksa saran potong',exact:true}).click()
   let plan=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true})
   let reply=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(reply.status(),200)
   await plan.getByLabel('Gudang bahan rencana',{exact:true}).selectOption(f.location_id)
   reply=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(reply.status(),200)
   const options=await reply.json(),roll=options.rolls.find(r=>r.material_id===f.material_id);assert.ok(roll)
   await plan.getByLabel('PO rencana',{exact:true}).selectOption(f.po_id);await plan.getByLabel('Pola rencana',{exact:true}).selectOption(options.patterns[0].id)
   await plan.getByLabel('Waktu pencatatan draf WIB',{exact:true}).fill(wib(new Date(Date.now()-3600000).toISOString()))
   await plan.getByRole('button',{name:'Pilih roll '+roll.number,exact:true}).click()
   for(const[name,value]of[['Keluar roll rencana 1','1'],['Terpakai roll rencana 1','0.5'],['Sisa roll rencana 1','0.5'],['Hasil roll rencana 1','1']])await plan.getByLabel(name,{exact:true}).fill(value)
   await plan.getByLabel('Alasan rencana Potongan',{exact:true}).fill('Actual bounded quantity browser one PCS; synthetic fixture, not owner defaults')
   await plan.getByLabel('Asumsi dan komposisi rencana sudah diperiksa',{exact:true}).check()
   await page.route('**/rest/v1/rpc/'+SAVE,async route=>{const args=route.request().postDataJSON(),reply=await route.fetch(),body=await reply.json();requests.push({args,status:reply.status(),body});if(!lost){lost=requests.at(-1);await route.abort('failed')}else await route.fulfill({response:reply})})
   await plan.getByRole('button',{name:'Simpan rencana Potongan',exact:true}).click()
   await ui.expect.poll(()=>lost?.status,{timeout:30000}).toBe(200)
   await ui.expect(plan.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   await page.reload();q=await quantity(ui,page,f)
   await q.locator(`[data-quantity-target="${f.target_key}"]`).getByRole('button',{name:'Periksa saran potong',exact:true}).click()
   plan=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true});await plan.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
   await ui.expect(plan).toContainText('Rencana tersimpan.')
   assert.equal(requests.length,2);assert.deepEqual(requests[0].args,requests[1].args);assert.deepEqual(requests[0].body,requests[1].body)
   assert.equal(requests[0].body.cutting_save_guard.feasible,true)
   const committed=state();assert.equal(committed.drafts,before.drafts+1);assert.equal(committed.receipts,before.receipts+1);assert.equal(committed.intents,before.intents);assert.deepEqual(committed.physical,before.physical)
  }
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await shot('REVIEWED')
  return{status:'PASS',actual_Auth_PostgREST_browser:true,real_Native_job_DONE:true,source_method:'BOUNDED',old_whole_netting_call_count:0,expected_targets:f.expected_targets,
   large_2000_products_202000_movements:dense,raw_history_INCOMPLETE_preserved:dense,actual_stock_change_and_new_UUID:dense,
   checked_SAVE_lost_reply_exact_UUID_payload_result_recovery:!dense,no_client_money_HPP_or_stock_effect:true,no_horizontal_overflow:true,viewport:dense?1440:390,shots}
 }catch(error){writeFileSync(`cp6-proof/t3/QUANTITY_${dense?'LARGE_DESKTOP':'SMALL_MOBILE'}_FAILURE.json`,JSON.stringify({error:String(error),calls,requests,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{await page.unrouteAll({behavior:'wait'});fixture('restore',{actor});await user.context.close()}
}
// Small first: its real checked SAVE must not inherit unreviewed volume roots.
export function cases(ui,today){return[
 ['OW13C_QUANTITY_MOBILE_CHECKED_SAVE_REPLY_RECOVERY',()=>journey(ui,today,false)],
 ['OW13C_QUANTITY_DESKTOP_DENSE2000_PAGED_FRESHNESS',()=>journey(ui,today,true)],
]}
