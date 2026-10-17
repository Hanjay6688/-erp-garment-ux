// R3-09 (owner D16-2, D16-3, D16-4): the old or the new Mandor rate when sewing is finished, on the connected WIP & Sewing
// page, desktop and phone, real Auth and PostgREST on the committed copy. The fixture is the native cases' one: a first record
// locked Jahit 3 + Obras 1 for the PO, then the Mandor's Jahit rate became 5 from the next WIB day. The screen shows both rates
// with their wage for a sewing time after the change and keeps the save closed until one is chosen; the choice goes to the
// server; "Pakai tarif baru seterusnya" switches the PO once; the next record takes the new rate without asking. The state is
// read from the Native rows (fixture r309_rate_state), never from the command's answer.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function wipPage(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• WIP & Sewing',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'WIP & Sewing',exact:true})).toBeVisible()
}
async function openPanel(ui,page,f){
 await wipPage(ui,page);await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
 const card=page.locator('.cwip-list>article').filter({hasText:f.number});await ui.expect(card).toHaveCount(1)
 const panel=card.getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
 await panel.getByRole('button',{name:'Catat selesai jahit',exact:true}).click();await ui.expect(panel).toContainText('Bisa dicatat')
 return panel
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_09_RATE_CHOICE_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r309_rate',{today}),requests=[],seen={}
 const state=()=>h.fixture('r309_rate_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-09-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_sewing_completion_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.deepEqual([before.records.length,before.records[0].rates,before.revisions,before.switched],[1,['3.00','1.00'],0,0])
  let panel=await openPanel(ui,page,f)
  await ui.expect(panel).toContainText('Upah mandor per pcs: Jahit')
  const qty=()=>panel.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}),when=()=>panel.getByLabel('Waktu selesai jahit '+f.number,{exact:true})
  const note=()=>panel.getByLabel('Catatan selesai jahit '+f.number,{exact:true}),check=()=>panel.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true})
  const save=()=>panel.getByRole('button',{name:'Simpan selesai jahit',exact:true})
  await qty().fill('2');await note().fill('Setoran sesudah tarif naik');await when().fill(f.later)
  // Both rates with their wage; nothing can be reviewed or saved before a choice.
  const choice=panel.getByRole('group',{name:'Pilih tarif '+f.number,exact:true})
  await ui.expect(choice).toContainText('Tarif lama PO: Jahit Rp3 + Obras Rp1 = Rp4 · upah 2 pcs = Rp8')
  await ui.expect(choice).toContainText('Tarif baru (berlaku pada waktu jahit): Jahit Rp5 + Obras Rp1 = Rp6 · upah 2 pcs = Rp12')
  await ui.expect(check()).toBeDisabled();await ui.expect(save()).toBeDisabled()
  await panel.getByLabel('Tarif baru (berlaku pada waktu jahit) '+f.number,{exact:true}).check()
  await ui.expect(panel).toContainText('Upah yang akan dicatat: 2 pcs × Rp6 = Rp12.')
  await check().check();assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_CHOICE.png`,fullPage:true})
  await save().click()
  await ui.expect(page.getByText(f.number+': 2 pcs tercatat selesai dijahit. Upah mandor Rp12 dengan tarif baru masuk hutang mandor; 6 pcs siap dikirim ke laundry.')).toBeVisible()
  const recorded=seen.recorded=state()
  assert.equal(recorded.records.length,2);assert.deepEqual(recorded.records[1].rates,['5.00','1.00']);assert.deepEqual(recorded.records[1].revised,[true,false])
  assert.deepEqual(recorded.records[1].wage,['12.00','12.00','1']);assert.equal(recorded.revisions,1);assert.deepEqual(recorded.records[0].rates,['3.00','1.00'])
  assert.equal(requests.length,1);assert.equal(requests[0].p_payload.action,'RECORD');assert.equal(requests[0].p_payload.rate_choice,'NEW')
  // The PO switch: once, with a reason and a review.
  panel=await openPanel(ui,page,f)
  await panel.getByRole('button',{name:'Pakai tarif baru seterusnya',exact:true}).click()
  const go=panel.getByRole('button',{name:'Simpan: pakai tarif baru seterusnya',exact:true});await ui.expect(go).toBeDisabled()
  await panel.getByLabel('Alasan tarif baru seterusnya '+f.number,{exact:true}).fill('Tarif mandor naik, pakai yang baru')
  await panel.getByLabel('Tarif baru seterusnya '+f.number+' sudah diperiksa',{exact:true}).check()
  await page.screenshot({path:`cp6-proof/t3/${name}_SWITCH.png`,fullPage:true})
  await go.click()
  await ui.expect(page.getByText(f.number+': PO ini sekarang memakai tarif mandor yang berlaku pada waktu jahit untuk setiap catatan selesai jahit berikutnya. Upah yang sudah tercatat tidak berubah.')).toBeVisible()
  const switched=seen.switched=state();assert.equal(switched.switched,1);assert.deepEqual(switched.records,recorded.records)
  assert.deepEqual(Object.keys(requests[1].p_payload).sort(),['action','change_reason','group_id','review_token']);assert.equal(requests[1].p_payload.action,'USE_NEW_RATES')
  // After the switch: no choice, the new rate, and no switch button any more.
  panel=await openPanel(ui,page,f)
  await ui.expect(panel).toContainText('PO '+f.po_number+' memakai tarif mandor yang berlaku pada waktu jahit untuk setiap catatan')
  await ui.expect(panel.getByRole('button',{name:'Pakai tarif baru seterusnya',exact:true})).toHaveCount(0)
  await qty().fill('1');await note().fill('Setoran sesudah pindah tarif');await when().fill(f.later2)
  await ui.expect(panel.getByRole('group',{name:'Pilih tarif '+f.number,exact:true})).toHaveCount(0)
  await ui.expect(panel).toContainText('Upah yang akan dicatat: 1 pcs × Rp6 = Rp6.')
  await check().check();await save().click()
  await ui.expect(page.getByText(f.number+': 1 pcs tercatat selesai dijahit. Upah mandor Rp6 dengan tarif baru masuk hutang mandor; 7 pcs siap dikirim ke laundry.')).toBeVisible()
  const after=seen.after=state()
  assert.equal(after.records.length,3);assert.deepEqual(after.records[2].rates,['5.00','1.00']);assert.deepEqual(after.records[2].wage,['6.00','6.00','1'])
  assert.equal(after.revisions,2);assert.equal(after.switched,1)
  assert.equal(requests.length,3);assert.equal(requests[2].p_payload.rate_choice,undefined)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_AFTER_SWITCH.png`,fullPage:true})
  return{status:'PASS',finding:'R3-09',phone:mobile,shown:{locked:'Jahit 3 + Obras 1',new:'Jahit 5 + Obras 1'},choice_required_before_save:true,
   new_rate_record:{pcs:2,wage:'12'},switched_once:true,after_switch_without_choice:{pcs:1,wage:'6'},requests:3}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_09_RATE_CHOICE_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_09_RATE_CHOICE_MOBILE',()=>journey(ui,today,true,h)]]
}
