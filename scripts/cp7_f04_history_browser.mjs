import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f04_history_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function navigate(page){
 await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'})
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()
}
async function capture(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'p05-history-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,panel=page.getByRole('region',{name:'Data permintaan ERP',exact:true}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 let lost=null,original=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await navigate(page)
  const dirty=page.getByLabel('Cari barang jadi',{exact:true});await dirty.fill('FORM ASLI MASIH KOTOR')
  await panel.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();assert.equal(await dirty.inputValue(),'FORM ASLI MASIH KOTOR')
  await page.route('**/rest/v1/rpc/erp_cp7_capture_demand_history_v1',async route=>{if(!lost){const r=await route.fetch();assert.equal(r.status(),200);lost={envelope:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()})
  await panel.getByRole('button',{name:'Muat data permintaan',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Ulangi permintaan yang sama',exact:true})).toBeEnabled();assert.equal(await panel.locator('table').count(),0)
  const state=()=>fixture('state',{fixture:f,today,actor:user.user.id});assert.equal(state().native_rows,1)
  await capture(ui,page,`P05_UNCERTAIN_${suffix}.png`);screenshots.push(`P05_UNCERTAIN_${suffix}.png`)
  await page.reload();await navigate(page);const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_capture_demand_history_v1'));await panel.getByRole('button',{name:'Ulangi permintaan yang sama',exact:true}).click();const replied=await response
  assert.equal(replied.status(),200);assert.deepEqual(replied.request().postDataJSON(),lost.envelope);assert.deepEqual(await replied.json(),lost.body);original=lost.body
  await panel.getByLabel('Cari data permintaan',{exact:true}).fill(original.current_stock.find(r=>r.root_id===f.product).sku)
  const row=panel.locator('tbody tr');await ui.expect(row).toHaveCount(1);await ui.expect(row).toContainText('100 PCS');await ui.expect(row).toContainText('24 PCS');await ui.expect(row).toContainText('76 PCS');assert.equal(state().native_rows,1)
  await capture(ui,page,`P05_CURRENT_${suffix}.png`);screenshots.push(`P05_CURRENT_${suffix}.png`)
  fixture('post',{fixture:f});await panel.getByRole('button',{name:'Periksa sumber arsip',exact:true}).click();await ui.expect(panel).toContainText('Arsip lama: sumber ERP sudah berubah.');await ui.expect(row).toContainText('100 PCS')
  await capture(ui,page,`P05_STALE_${suffix}.png`);screenshots.push(`P05_STALE_${suffix}.png`)
  await panel.getByRole('button',{name:'Muat data permintaan',exact:true}).click();await ui.expect(panel).toContainText('Sumber sesuai saat diperiksa.');await ui.expect(row).toContainText('0 PCS');await ui.expect(row).toContainText('76 PCS');assert.equal(fixture('state',{fixture:f,today,actor:user.user.id,posted:true}).native_rows,2)
  await capture(ui,page,`P05_POSTED_${suffix}.png`);screenshots.push(`P05_POSTED_${suffix}.png`)
  if(mobile){fixture('deactivate',{actor:user.user.id});const refused=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_read_demand_history_v1'));await panel.getByRole('button',{name:'Periksa sumber arsip',exact:true}).click();assert.equal((await refused).status(),403);await ui.expect(panel.locator('table')).toHaveCount(0);await capture(ui,page,`P05_REVOKED_${suffix}.png`);screenshots.push(`P05_REVOKED_${suffix}.png`)}
  return{status:'PASS',real_Auth_native_source:true,committed_reply_loss_same_UUID_replay_one_run:true,original_stock_search_preserved:true,native_draft100_reserved24_available76:true,native_post76_no_second_subtraction:true,archive_immutable_stale_after_native_post:true,current_deactivation403_no_old_facts:mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/P05_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel.innerText().catch(()=>''),lost,original},null,2));await page.screenshot({path:`cp6-proof/t3/P05_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P05_BROWSER_DESKTOP_NATIVE_HISTORY',()=>journey(ui,today,false)],['P05_BROWSER_MOBILE_CURRENT_AUTH',()=>journey(ui,today,true)]]}
