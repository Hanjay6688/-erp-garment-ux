// Owner D15-5 (Fable FABLE-011): the owner sets the official cutover date on the Impor data awal page, desktop and phone,
// real Auth and PostgREST on the committed copy. The screen names the latest date allowed (the first day already in the
// books); a date one day later is refused by the server with its reason, the allowed date is saved with its history. The
// case ends with the date moved back to 2000-01-03 (fixture cutover_reset), so later cases are not limited by it.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const day=(iso,offset)=>{const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10)}
const longDate=iso=>new Intl.DateTimeFormat('id-ID',{dateStyle:'long',timeZone:'UTC'}).format(new Date(iso+'T00:00:00Z'))
async function openImport(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Impor data awal',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Impor data awal',exact:true})).toBeVisible()
}
async function journey(ui,mobile,h){
 const name=`CP17_BROWSER_R2_D15_5_CUTOVER_${mobile?'MOBILE':'DESKTOP'}`,seen={},requests=[]
 const user=await ui.login('OWNER',{label:'cp17-r2-cutover-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_set_cutover_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const s0=seen.before=h.fixture('cutover_state',{}),L=s0.latest_allowed
  await openImport(ui,page)
  const panel=page.getByRole('region',{name:'Tanggal mulai pakai aplikasi',exact:true})
  await ui.expect(panel).toContainText(`Paling lambat ${longDate(L)}`)
  const input=panel.getByLabel('Tanggal mulai pakai aplikasi (WIB)',{exact:true}),reason=panel.getByLabel('Alasan tanggal mulai pakai aplikasi',{exact:true})
  const check=panel.getByLabel('Tanggal mulai pakai aplikasi sudah diperiksa',{exact:true}),save=panel.getByRole('button',{name:'Sahkan tanggal mulai pakai',exact:true})
  // One day after the first day in the books: the screen says why and keeps the save closed; nothing is sent.
  await input.fill(day(L,1));await reason.fill('Mulai pakai aplikasi di Enteng')
  await ui.expect(panel.locator('.cmd-problems')).toContainText(`Paling lambat ${longDate(L)}`);await ui.expect(check).toBeDisabled();await ui.expect(save).toBeDisabled()
  assert.equal(requests.length,0)
  // The allowed day itself.
  await input.fill(L);await check.check();await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true});await save.click()
  await ui.expect(panel.getByRole('status')).toHaveText(`Tersimpan: tanggal mulai pakai aplikasi ${longDate(L)}. Transaksi operasional bertanggal sebelumnya ditolak server.`)
  await ui.expect(panel).toContainText(`Berlaku: ${longDate(L)}`)
  const s1=seen.after=h.fixture('cutover_state',{});assert.deepEqual([s1.version,s1.cutover_date],[s0.version+1,L])
  assert.equal(requests.length,1);assert.deepEqual(requests[0].p_payload,{action:'SET',expected_version:s0.version,cutover_date:L,reason:'Mulai pakai aplikasi di Enteng'})
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',owner_decision:'D15-5',phone:mobile,latest_allowed_shown:L,one_day_later_held_on_screen:true,set_on_screen:L,history_version:s1.version}
 }catch(error){await h.failure(page,name,error,seen,requests);throw error}
 finally{h.fixture('cutover_reset',{});await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R2_D15_5_CUTOVER_DESKTOP',()=>journey(ui,false,h)],['CP17_BROWSER_R2_D15_5_CUTOVER_MOBILE',()=>journey(ui,true,h)]]
}
