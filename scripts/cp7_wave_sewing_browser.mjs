// Sol R2-10 (KNOWN-BF-WAVE): SELESAI DIJAHIT per SKU for a Potongan bound to SKU waves, on the connected WIP & Sewing page,
// desktop and phone, real Auth and PostgREST on the committed copy. The fixture is the native cases' wave (SKU A on sizes
// S+M with 11 pieces, SKU B on L with 3; Jahit 10 on A and 30 on B, Obras 1 from the base Work BOM). The screen shows each
// SKU's rate at the sewing time, keeps the save closed for more than a SKU can take, and records both SKUs in one request;
// the state is read from the Native rows (fixture wave_sewing_state), never from the command's answer.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function wipPage(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• WIP & Sewing',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'WIP & Sewing',exact:true})).toBeVisible()
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R2_10_WAVE_SEWING_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('wave_sewing',{today}),requests=[],seen={}
 const state=()=>h.fixture('wave_sewing_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r2-10-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_sewing_completion_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state();assert.deepEqual([before.sewn,before.ready,before.posted.length,before.history],[0,0,0,0])
  await wipPage(ui,page);await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
  const card=page.locator('.cwip-list>article').filter({hasText:f.number});await ui.expect(card).toHaveCount(1)
  const panel=card.getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
  await panel.getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await ui.expect(panel).toContainText('Potongan ini memakai tarif mandor per SKU (wave).')
  await ui.expect(panel).toContainText('0 / 14 pcs')
  const rows=panel.getByRole('list',{name:'Selesai jahit per SKU '+f.number,exact:true})
  const rowA=rows.locator('li').filter({hasText:'SKU '+f.A.sku}),rowB=rows.locator('li').filter({hasText:'SKU '+f.B.sku})
  await ui.expect(rowA).toContainText('bisa dicatat 11 pcs');await ui.expect(rowA).toContainText('= Rp11')
  await ui.expect(rowB).toContainText('bisa dicatat 3 pcs');await ui.expect(rowB).toContainText('= Rp31')
  const qtyA=panel.getByLabel(`Jumlah selesai dijahit ${f.number} SKU ${f.A.sku}`,{exact:true}),qtyB=panel.getByLabel(`Jumlah selesai dijahit ${f.number} SKU ${f.B.sku}`,{exact:true})
  const check=panel.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}),save=panel.getByRole('button',{name:'Simpan selesai jahit',exact:true})
  await ui.expect(save).toBeDisabled()
  // More than SKU B can take keeps the review closed; nothing is sent.
  await qtyB.fill('4');await panel.getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Setoran mandor per SKU')
  await ui.expect(check).toBeDisabled()
  await qtyA.fill('5');await qtyB.fill('2')
  await ui.expect(panel).toContainText(`Upah yang akan dicatat: SKU ${f.A.sku} 5 pcs × Rp11 + SKU ${f.B.sku} 2 pcs × Rp31 = Rp117.`)
  await check.check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await save.click()
  // The lines are named in the screen's SKU order (the server's sort); either order of the two is the same outcome.
  const esc=t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),a=esc(`SKU ${f.A.sku} 5 pcs`),b=esc(`SKU ${f.B.sku} 2 pcs`)
  await ui.expect(page.getByText(new RegExp(`${esc(f.number)}: 7 pcs tercatat selesai dijahit \\((${a}, ${b}|${b}, ${a})\\)\\. Upah mandor Rp117 masuk hutang mandor; 7 pcs siap dikirim ke laundry\\.`))).toBeVisible()
  const after=seen.after=state()
  assert.deepEqual([after.sewn,after.ready,after.history],[7,7,2])
  assert.deepEqual(Object.fromEntries(after.posted.map(([sku,q,wage])=>[sku,[q,wage]])),{[f.A.sku]:[5,['55.00','55.00','1']],[f.B.sku]:[2,['62.00','62.00','1']]})
  assert.equal(requests.length,1);const p=requests[0].p_payload
  assert.equal(p.action,'RECORD_WAVE');assert.equal(p.group_id,f.group)
  assert.deepEqual(Object.fromEntries(p.lines.map(l=>[l.sku_id,l.qty_pcs])),{[f.A.id]:'5',[f.B.id]:'2'})
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',finding:'R2-10',phone:mobile,recorded:{A:5,B:2},wage:{A:'55 (Jahit 10 + Obras 1)',B:'62 (Jahit 30 + Obras 1)'},over_sku_kept_off:true,one_request:true}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R2_10_WAVE_SEWING_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R2_10_WAVE_SEWING_MOBILE',()=>journey(ui,today,true,h)]]
}
