import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// K2 in the real UI: a staged run started by one click says how long its result
// is kept (7 days after it finished). After the run is aged (labelled SYNTHETIC:
// its finish time moved back 8 days), reopening the last result reads no page and
// says the result expired, asking for a new analysis.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_k2_retention_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,today,mobile){
 fixture('prepare',{today});const user=await ui.login('OWNER',{label:'k2-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',shots=[],pageReads=[]
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_read_staged_analysis_pages_v1')||r.url().endsWith('/rpc/erp_cp7_read_staged_analysis_page_v1'))pageReads.push(r.url())})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  const staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(staged).toBeVisible({timeout:180000})
  const kept=panel.locator('[data-retention="KEPT"]');await ui.expect(kept).toContainText('Hasil ini disimpan sampai ');await ui.expect(kept).toContainText('(7 hari sesudah analisis selesai); sesudah itu kedaluwarsa dan perlu dibuat ulang.')
  shots.push(await shot(ui,page,`K2_${suffix}_KEPT.png`))
  const aged=fixture('age',{actor:user.user.id});assert.ok(aged.aged>=1,JSON.stringify(aged))
  await page.reload();pageReads.length=0
  panel=await openPanel(page);await panel.getByRole('button',{name:'Buka hasil analisis bertahap terakhir',exact:true}).click()
  await ui.expect(panel).toContainText('Hasil analisis ini sudah kedaluwarsa sejak ',{timeout:60000});await ui.expect(panel).toContainText('hasil disimpan 7 hari sesudah selesai. Buat analisis baru.')
  await ui.expect(page.getByRole('region',{name:'Hasil analisis bertahap',exact:true})).toHaveCount(0)
  assert.equal(pageReads.length,0,'K2_EXPIRED_RESULT_PAGES_READ')
  shots.push(await shot(ui,page,`K2_${suffix}_EXPIRED.png`))
  return{status:'PASS',kept_until_shown:true,expired_message_after_aging:true,expired_pages_read:0,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/K2_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/K2_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['K2_BROWSER_DESKTOP_RETENTION',()=>journey(ui,today,false)],['K2_BROWSER_MOBILE_RETENTION',()=>journey(ui,today,true)]]}
