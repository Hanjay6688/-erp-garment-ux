import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// PL-5 B in the real UI: the history yield policy panel under "Data permintaan &
// stok" shows the package the owner approved on 8 Oct 2026 prefilled and not in
// force, saves it as a new version with a reason, and shows the saved version
// with its role and time. Only the two policy RPCs write; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_pl5_history_yield_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function response(page,name,action){const[request]=await Promise.all([page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/rpc/'+name)),action()]);const result=await request.response();assert.ok(result,'PL5H_NO_RESPONSE '+name);return result}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,mobile){
 const user=await ui.login('OWNER',{label:'pl5h-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',shots=[]
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=fixture('state',{})
  await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
  let r=await response(page,'erp_cp7_get_history_yield_policy_v1',()=>history.getByRole('button',{name:'Kebijakan yield histori',exact:true}).click());assert.equal(r.status(),200)
  panel=page.getByRole('region',{name:'Kebijakan yield histori',exact:true});await ui.expect(panel).toBeVisible()
  await ui.expect(panel).toContainText('Batas bawah satu sisi 90%');await ui.expect(panel).toContainText('Tidak pernah dari model lain dan tidak pernah dianggap 100%')
  if(before.revisions===0){
   await ui.expect(panel.locator('[data-policy-state]')).toHaveAttribute('data-policy-state','PENDING_POLICY_VALUE')
   await ui.expect(panel).toContainText('Paket keputusan owner 8 Okt 2026: 180 hari, minimal 5 grup selesai dan 200 PCS potong, batas bawah 90%. Berlaku setelah disimpan.')
   for(const[label,value]of[['Jendela histori hari','180'],['Minimal grup selesai','5'],['Minimal PCS potong','200']])await ui.expect(panel.getByLabel(label,{exact:true})).toHaveValue(value)
  }
  await panel.getByLabel('Status kebijakan yield',{exact:true}).selectOption('ACTIVE')
  await panel.getByLabel('Alasan kebijakan yield',{exact:true}).fill('PL-5 B browser: paket keputusan owner 8 Okt 2026 disimpan sebagai versi')
  r=await response(page,'erp_cp7_save_history_yield_policy_v1',()=>panel.getByRole('button',{name:'Simpan kebijakan yield',exact:true}).click());assert.equal(r.status(),200)
  const saved=await r.json();assert.equal(saved.policy.revision,String(before.latest+1));assert.equal(saved.policy.actor_role,'OWNER');assert.equal(saved.policy.confidence,'0.90')
  await ui.expect(panel).toContainText(`Kebijakan versi ${before.latest+1} tersimpan (aktif).`)
  await ui.expect(panel.locator('[data-policy-state]')).toHaveAttribute('data-policy-state','ACTIVE')
  await ui.expect(panel).toContainText(`Versi ${before.latest+1}: 180 hari, minimal 5 grup selesai dan 200 PCS potong. Disimpan oleh pemilik`)
  const after=fixture('state',{});assert.deepEqual([after.revisions,after.commands,after.state],[before.revisions+1,before.commands+1,'ACTIVE'])
  shots.push(await shot(ui,page,`PL5H_${suffix}_POLICY.png`))
  return{status:'PASS',package_prefilled_not_in_force:before.revisions===0,saved_version:saved.policy.revision,role:'OWNER',no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/PL5H_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/PL5H_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['PL5H_BROWSER_DESKTOP_POLICY',()=>journey(ui,false)],['PL5H_BROWSER_MOBILE_POLICY',()=>journey(ui,true)]]}
