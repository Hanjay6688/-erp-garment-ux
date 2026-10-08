import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// K3b in the real UI: a staged run started by one click finishes; the server
// schedule's cleanup entry (run exactly as pg_cron runs it) removes the run's
// temporary work after verifying its result; the page is reloaded and the panel
// reopens the last result by itself: it reads the same pages (same identity hash), sends no
// request or step, shows the kept-until label, and a Potongan plan is started
// from the reopened result with its options loaded from the server.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_k3_cleanup_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const STAGED_RPCS=['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_get_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function response(page,name,action){const[request]=await Promise.all([page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/rpc/'+name)),action()]);const result=await request.response();assert.ok(result,'K3C_NO_RESPONSE '+name);return result}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function findTarget(ui,region,key){
 const row=region.locator(`[data-analysis-target="${key}"]`),select=region.getByLabel('Pilih rentang target',{exact:true})
 const pages=await select.locator('option').count();for(let i=0;i<pages&&!await row.count();i++){await select.selectOption(String(i));await ui.expect(region.locator('[data-page-index]')).toHaveAttribute('data-page-index',String(i),{timeout:60000})}
 await ui.expect(row).toHaveCount(1);return row
}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today});const user=await ui.login('OWNER',{label:'k3c-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',shots=[],calls=[]
 page.on('response',async r=>{const name=STAGED_RPCS.find(n=>r.url().endsWith('/rpc/'+n));if(name){let body=null;try{body=await r.json()}catch{}calls.push({name,status:r.status(),body})}})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  let region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(region).toBeVisible({timeout:180000})
  const first=calls.filter(c=>c.name==='erp_cp7_read_staged_analysis_pages_v1'&&c.status===200).at(-1);assert.ok(first,'K3C_NO_PAGE_SET')
  const identity=first.body.identity_hash,pages=first.body.page_count
  const before=fixture('state',{actor:user.user.id});assert.equal(before.done.length,1);assert.equal(before.logs,0);assert.ok(before.temporary.outputs>0,JSON.stringify(before))
  const cleaned=fixture('clean',{});assert.ok(cleaned.cleaned.includes(before.done[0]),JSON.stringify(cleaned))
  const after=fixture('state',{actor:user.user.id});assert.equal(after.logs,1);assert.deepEqual(Object.values(after.temporary),[0,0,0,0,0])
  await page.reload();calls.length=0
  // Opening the panel reopens the last finished result by itself (NativeAnalysisPanel mount effect); no click is needed.
  panel=await openPanel(page)
  region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(region).toBeVisible({timeout:60000})
  await ui.expect(panel.getByRole('button',{name:'Buka hasil analisis bertahap terakhir',exact:true})).toHaveCount(0)
  const reread=calls.filter(c=>c.name==='erp_cp7_read_staged_analysis_pages_v1'&&c.status===200).at(-1);assert.ok(reread,'K3C_REOPEN_READ_NO_PAGE_SET')
  assert.equal(reread.body.identity_hash,identity,'K3C_REOPENED_IDENTITY_DIFFERS');assert.equal(reread.body.page_count,pages)
  assert.equal(calls.filter(c=>c.name==='erp_cp7_request_staged_analysis_v1'||c.name==='erp_cp7_step_staged_analysis_v1').length,0,'K3C_REOPEN_RECOMPUTED')
  assert.equal(calls.filter(c=>c.status>=400).length,0,JSON.stringify(calls.filter(c=>c.status>=400)))
  await ui.expect(panel.locator('[data-retention="KEPT"]')).toContainText('Hasil ini disimpan sampai ')
  const row=await findTarget(ui,region,f.target_key)
  await row.getByRole('button',{name:/^Rencanakan Potongan /}).click()
  const plan=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true});await ui.expect(plan).toContainText('Rencana dari analisis bertahap: data per ')
  await plan.getByLabel('Gudang bahan rencana',{exact:true}).selectOption(f.location_id)
  const r=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(r.status(),200)
  const options=await r.json();assert.equal(options.contract_version,'cp7.plan-options-staged.v1');assert.equal(options.identity_hash,identity)
  assert.ok(options.rolls.some(x=>x.material_id===f.material_id),'K3C_FIXTURE_ROLL')
  shots.push(await shot(ui,page,`K3C_${suffix}_REOPENED_AFTER_CLEANUP.png`))
  return{status:'PASS',cleaned_by_schedule_entry:true,reopened_on_panel_open:true,reopened_same_identity:identity,pages,no_request_or_step_on_reopen:true,plan_options_after_cleanup:true,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/K3C_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/K3C_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['K3C_BROWSER_DESKTOP_REOPEN_AFTER_CLEANUP',()=>journey(ui,today,false)],['K3C_BROWSER_MOBILE_REOPEN_AFTER_CLEANUP',()=>journey(ui,today,true)]]}
