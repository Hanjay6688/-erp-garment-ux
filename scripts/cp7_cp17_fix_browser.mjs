// CP17 browser cases on the Bagi Potongan page, real Auth and PostgREST on the committed copy:
// SG-01 reverse a posted pickup before sewing (desktop), SG-02 fabric back to the warehouse (phone).
import assert from'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const fixture=(operation,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_cp17_fix_browser_fixture.py',operation],{input:JSON.stringify(payload),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function menu(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click();const link=page.getByRole('button',{name:'• Bagi Potongan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()}
async function openGroup(ui,page,number,group){
 await menu(page);await page.locator('.cpick-tabs').getByRole('button',{name:'Semua',exact:true}).click()
 await page.getByLabel('Cari distribusi potongan',{exact:true}).fill(number);await page.getByRole('button',{name:'Cari Potongan',exact:true}).click()
 await page.locator('.cpick-queue button').filter({hasText:number}).click();await ui.expect(page.locator('[data-cutting-group-id]')).toHaveAttribute('data-cutting-group-id',group)
}
async function noSideScroll(ui,page){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)}
async function failure(page,name,error,state,requests){writeFileSync(`cp6-proof/t3/${name}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),state,requests},null,2));await page.screenshot({path:`cp6-proof/t3/${name}_FAILURE.png`,fullPage:true}).catch(()=>{})}
async function pickupReversal(ui,today){
 const f=fixture('pickup',{today}),user=await ui.login('OWNER',{label:'cp17-pickup-reversal'}),page=user.page,requests=[],name='CP17_SG01_PICKUP_REVERSAL_DESKTOP'
 const state=()=>fixture('pickup_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_reverse_pickup_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.pickup_status,'POSTED');assert.equal(before.po[2],f.mandor)
  await openGroup(ui,page,f.number,f.group)
  const panel=page.getByRole('region',{name:'Batal Bagi Potongan',exact:true})
  await panel.getByRole('button',{name:'Batalkan Bagi Potongan ini',exact:true}).click()
  await ui.expect(panel).toContainText('Mandor di PO dikosongkan');await ui.expect(panel.getByRole('button',{name:'Batalkan Bagi Potongan',exact:true})).toBeDisabled()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await panel.getByLabel('Alasan batal Bagi Potongan',{exact:true}).fill('Salah mandor, potongan dibagi ulang')
  await panel.getByLabel('Pembatalan Bagi Potongan sudah diperiksa',{exact:true}).check()
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await panel.getByRole('button',{name:'Batalkan Bagi Potongan',exact:true}).click()
  await ui.expect(page.getByText(f.number+': Bagi Potongan dibatalkan.')).toBeVisible()
  const after=state()
  assert.equal(after.pickup_status,'REVERSED');assert.equal(after.reversal_reason,'Salah mandor, potongan dibagi ulang');assert.equal(after.group_status,'CUT')
  assert.equal(after.picked_up_at,null);assert.equal(after.fabric_posted,true);assert.equal(after.executor,f.executor);assert.deepEqual(after.po,f.po_before)
  assert.equal(after.history,1);assert.equal(after.active_pickups,0);assert.equal(requests.length,1)
  assert.equal(requests[0].p_payload.group_id,f.group);assert.equal(requests[0].p_payload.pickup_id,f.pickup)
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',pickup:'REVERSED',group:'CUT with fabric still posted',po_restored:after.po,mandor_cleared:after.po[2]===null,one_request:true,history_rows:1}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
async function fabricReturn(ui,today){
 const f=fixture('fabric',{today}),user=await ui.login('OWNER',{label:'cp17-fabric-return',mobile:true}),page=user.page,requests=[],name='CP17_SG02_FABRIC_RETURN_MOBILE'
 const state=()=>fixture('fabric_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_return_cutting_fabric_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.returns,0);assert.equal(before.return_posted,false)
  await openGroup(ui,page,f.number,f.group)
  const panel=page.getByRole('region',{name:'Kain kembali ke gudang',exact:true})
  await panel.getByRole('button',{name:'Catat kain kembali ke gudang',exact:true}).click()
  const qty=panel.getByLabel('Kain kembali roll '+f.roll_number,{exact:true});await ui.expect(qty).toBeEnabled()
  await qty.fill('3.5');await ui.expect(panel).toContainText('melebihi sisa yang dicatat saat potong')
  await qty.fill('2');await panel.getByLabel('Alasan kain kembali',{exact:true}).fill('Sisa kain dikembalikan ke gudang bahan')
  await panel.getByLabel('Jumlah kain kembali sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await panel.getByRole('button',{name:'Simpan kain kembali ke gudang',exact:true}).click()
  await ui.expect(page.getByText(/kain kembali ke gudang sudah tercatat/)).toBeVisible()
  const after=state()
  assert.equal(Number(after.stock)-Number(before.stock),2);assert.equal(after.returns,1);assert.equal(after.return_posted,true);assert.equal(after.history,1)
  assert.equal(requests.length,1);assert.equal(requests[0].p_payload.rolls.length,1);assert.equal(requests[0].p_payload.rolls[0].qty_returned,'2')
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',over_remainder_refused_on_screen:true,stock_up_by:2,one_return_movement:true,once_per_cutting:true,one_request:true,phone:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP',()=>pickupReversal(ui,today)],['CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE',()=>fabricReturn(ui,today)]]}
