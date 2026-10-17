// R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Pengaturan ERP page, desktop and phone, real Auth and PostgREST
// on the committed copy. The owner sees every policy of the Aksesori and Laundry pages with the status and version of its Native
// row and the cutover date read only; sets ACC-DEC01 and LAU-DEC04 on the page, each through its own page's Native writer
// (erp_save_accessory_service_action_v1 / erp_save_laundry_bd_action_v1, SET_POLICY) with the version that was read, a reason and
// one request UUID; only that policy and one event change. An auditor (settings.erp.view, not owner/admin) then sees statuses
// without values and no edit control. State is read from the Native rows (fixture r303_settings_state), never from the command's
// answer; both policies are put back through the same writers at the end (fixture r303_settings_restore).
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const SET='Ditetapkan di aplikasi'
async function settingsPage(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Pengaturan ERP',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Pengaturan ERP',exact:true})).toBeVisible()
 await ui.expect(page.getByRole('article',{name:'Kebijakan LAU-DEC06',exact:true})).toBeVisible()
}
const card=(page,key)=>page.getByRole('article',{name:'Kebijakan '+key,exact:true})
async function save(ui,page,key,fill,reason,preview){
 const c=card(page,key);await c.getByRole('button',{name:'Ubah '+key,exact:true}).click()
 const editor=c.getByRole('region',{name:'Ubah kebijakan '+key,exact:true})
 const go=editor.getByRole('button',{name:'Tetapkan '+key,exact:true}),check=editor.getByLabel('Perubahan '+key+' sudah diperiksa',{exact:true})
 await ui.expect(go).toBeDisabled();await ui.expect(check).toBeDisabled()
 await fill(editor);await editor.getByLabel('Alasan perubahan '+key,{exact:true}).fill(reason)
 await ui.expect(editor).toContainText('Akan ditetapkan: '+preview+'.')
 await check.check();return go
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_03_ERP_SETTINGS_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r303_settings',{today}),requests=[],seen={}
 const state=()=>h.fixture('r303_settings_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-03-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 let reader=null
 page.on('request',r=>{const u=r.url();if(u.endsWith('/rpc/erp_save_accessory_service_action_v1')||u.endsWith('/rpc/erp_save_laundry_bd_action_v1'))requests.push({rpc:u.split('/rpc/')[1],body:r.postDataJSON()})})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=f.before,next=key=>String(Number(before[key].version)+1)
  assert.equal(Object.keys(before).length,13)
  await settingsPage(ui,page)
  // Every policy of both pages, with the status and version of its Native row; the cutover date only read here.
  for(const[key,row]of Object.entries(before)){
   await ui.expect(card(page,key)).toContainText('Versi '+row.version+' · tercatat')
   if(row.status==='SET')await ui.expect(card(page,key)).toContainText(SET);else await ui.expect(card(page,key)).not.toContainText(SET)
  }
  const cutover=page.getByRole('region',{name:'Tanggal mulai pakai aplikasi',exact:true})
  await ui.expect(cutover).toContainText('Owner mengubahnya di menu Impor data awal');await ui.expect(cutover.locator('input')).toHaveCount(0)
  // ACC-DEC01 through the Aksesori writer.
  let go=await save(ui,page,'ACC-DEC01',async()=>{},'CP17 R3-03 garis waktu dari layar','Cara: Tanggal fisik dan pencatatan terpisah')
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await go.click()
  await ui.expect(page.getByText(`ACC-DEC01 tersimpan: ditetapkan, versi ${next('ACC-DEC01')}. Pengaturan dibaca ulang dari server.`,{exact:true})).toBeVisible()
  const s1=seen.accessory=state()
  assert.equal(requests.length,1);assert.equal(requests[0].rpc,'erp_save_accessory_service_action_v1');assert.equal(requests[0].body.p_action,'SET_POLICY')
  assert.deepEqual(requests[0].body.p_payload,{policy_key:'ACC_DEC01',operation:'SET',expected_version:before['ACC-DEC01'].version,reason:'CP17 R3-03 garis waktu dari layar',value:{mode:'BOTH_REAL_TIMELINES'}})
  assert.deepEqual([s1['ACC-DEC01'].status,s1['ACC-DEC01'].value,s1['ACC-DEC01'].version,s1['ACC-DEC01'].events],['SET',{mode:'BOTH_REAL_TIMELINES'},next('ACC-DEC01'),before['ACC-DEC01'].events+1])
  assert.equal(s1['ACC-DEC01'].last.request_id,requests[0].body.p_client_request_id);assert.equal(s1['ACC-DEC01'].last.reason,'CP17 R3-03 garis waktu dari layar')
  for(const k of Object.keys(before))if(k!=='ACC-DEC01')assert.deepEqual(s1[k],before[k],k)
  await ui.expect(card(page,'ACC-DEC01')).toContainText(SET);await ui.expect(card(page,'ACC-DEC01')).toContainText('Versi '+next('ACC-DEC01')+' · tercatat')
  // LAU-DEC04 through the Laundry writer.
  go=await save(ui,page,'LAU-DEC04',async e=>{await e.getByLabel('Penjualan',{exact:true}).selectOption('ALLOW_PENDING')},'CP17 R3-03 jual dengan HPP belum final','Penjualan: Boleh; HPP belum final')
  assert.deepEqual(state(),s1);assert.equal(requests.length,1)
  await go.click()
  await ui.expect(page.getByText(`LAU-DEC04 tersimpan: ditetapkan, versi ${next('LAU-DEC04')}. Pengaturan dibaca ulang dari server.`,{exact:true})).toBeVisible()
  const s2=seen.laundry=state()
  assert.equal(requests.length,2);assert.equal(requests[1].rpc,'erp_save_laundry_bd_action_v1');assert.equal(requests[1].body.p_action,'SET_POLICY')
  assert.deepEqual(requests[1].body.p_payload,{policy_key:'LAU-DEC04',operation:'SET',expected_version:before['LAU-DEC04'].version,reason:'CP17 R3-03 jual dengan HPP belum final',value:{sale_with_unknown_laundry:'ALLOW_PENDING'}})
  assert.deepEqual([s2['LAU-DEC04'].status,s2['LAU-DEC04'].value,s2['LAU-DEC04'].version,s2['LAU-DEC04'].events],['SET',{sale_with_unknown_laundry:'ALLOW_PENDING'},next('LAU-DEC04'),before['LAU-DEC04'].events+1])
  assert.equal(s2['LAU-DEC04'].last.request_id,requests[1].body.p_client_request_id)
  for(const k of Object.keys(before))if(k!=='LAU-DEC04')assert.deepEqual(s2[k],s1[k],k)
  assert.notEqual(requests[0].body.p_client_request_id,requests[1].body.p_client_request_id)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  // A limited reader: settings.erp.view without owner/admin. Statuses only, no values, no edit control, no cutover date.
  reader=await ui.login('AUDITOR_VIEW_ONLY',{label:'cp17-r3-03-auditor-'+(mobile?'mobile':'desktop'),mobile});const rp=reader.page
  await settingsPage(ui,rp)
  await ui.expect(card(rp,'ACC-DEC01')).toContainText(SET);await ui.expect(card(rp,'ACC-DEC01')).toContainText('Rincian hanya terlihat owner/admin')
  await ui.expect(card(rp,'ACC-DEC01')).not.toContainText('Tanggal fisik dan pencatatan terpisah');await ui.expect(card(rp,'LAU-DEC04')).not.toContainText('Boleh; HPP belum final')
  await ui.expect(rp.getByRole('button',{name:/^Ubah /})).toHaveCount(0)
  await ui.expect(rp.getByRole('region',{name:'Tanggal mulai pakai aplikasi',exact:true})).toContainText('hanya terlihat oleh owner dan admin')
  await h.noSideScroll(ui,rp);await rp.screenshot({path:`cp6-proof/t3/${name}_AUDITOR.png`,fullPage:true})
  assert.deepEqual(state(),s2)
  return{status:'PASS',finding:'R3-03',owner_decision:'D16-1',phone:mobile,policies_shown:13,
   accessory:{writer:'erp_save_accessory_service_action_v1',version:s2['ACC-DEC01'].version},laundry:{writer:'erp_save_laundry_bd_action_v1',version:s2['LAU-DEC04'].version},
   only_that_policy_changed:true,auditor_statuses_only:true,requests:requests.length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{try{seen.restored=h.fixture('r303_settings_restore',f)}finally{await user.context.close();if(reader)await reader.context.close()}}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_ERP_SETTINGS_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_03_ERP_SETTINGS_MOBILE',()=>journey(ui,today,true,h)]]
}
