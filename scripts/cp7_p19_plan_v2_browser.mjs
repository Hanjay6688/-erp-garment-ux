import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// Plan v2 in the real UI: a staged run started by one trusted click, then a
// production plan for one target of its pages, drafted from the run's dated
// snapshot ("data per"), previewed with the server's live recheck, and made a
// Native cutting draft. A second plan for the same target from the same
// snapshot is shown refused (target planned after the snapshot) with the
// draft button disabled. Real Native fixture commands; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p19_plan_v2_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const names=['erp_cp7_get_plan_options_v2','erp_cp7_save_plan_draft_v2','erp_cp7_read_plan_draft_v2','erp_cp7_preview_plan_action_v2','erp_cp7_apply_plan_action_v2',
 'erp_cp7_get_plan_options_v1','erp_cp7_save_plan_draft_v1','erp_cp7_read_plan_draft_v1','erp_cp7_preview_plan_action_v1','erp_cp7_apply_plan_action_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function response(page,name,action){const[request]=await Promise.all([page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/rpc/'+name)),action()]);const result=await request.response();assert.ok(result,'P19P_NO_RESPONSE '+name);return result}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
function wib(t){return new Date(Date.parse(t)+7*3600000).toISOString().slice(0,19)}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today});const user=await ui.login('OWNER',{label:'p19p-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],shots=[]
 const state=()=>fixture('state',{actor:user.user.id})
 page.on('request',r=>{const name=names.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.deepEqual([before.drafts,before.intents],[0,0])
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  const region=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(region).toBeVisible({timeout:180000})
  // Find the fixture's target on its page (pages are contiguous ranges of the run).
  const row=region.locator(`[data-analysis-target="${f.target_key}"]`),select=region.getByLabel('Pilih rentang target',{exact:true})
  const pages=await select.locator('option').count();for(let i=0;i<pages&&!await row.count();i++){await select.selectOption(String(i));await ui.expect(region.locator('[data-page-index]')).toHaveAttribute('data-page-index',String(i),{timeout:60000})}
  await ui.expect(row).toHaveCount(1);await ui.expect(region).toContainText('Rencana Potongan dibuat per target dari halaman di bawah memakai data per ')
  await row.getByRole('button',{name:/^Rencanakan Potongan /}).click()
  const plan=page.getByRole('region',{name:'Rencana Potongan ERP',exact:true});await ui.expect(plan).toContainText('Rencana dari analisis bertahap: data per ')
  let r=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(r.status(),200)
  await plan.getByLabel('Gudang bahan rencana',{exact:true}).selectOption(f.location_id)
  r=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(r.status(),200)
  const options=await r.json();assert.equal(options.contract_version,'cp7.plan-options-staged.v1');assert.equal(options.live_recheck,'AT_PREVIEW_AND_APPLY')
  const roll=options.rolls.find(x=>x.material_id===f.material_id);assert.ok(roll,'P19P_FIXTURE_ROLL')
  await ui.expect(plan).toContainText('bukan angka saat ini')
  const fill=async(p)=>{await plan.getByLabel('PO rencana',{exact:true}).selectOption(f.po_id);await plan.getByLabel('Pola rencana',{exact:true}).selectOption(options.patterns[0].id)
   await plan.getByLabel('Waktu pencatatan draf WIB',{exact:true}).fill(wib(new Date(Date.now()-3600000).toISOString()))
   if(await plan.getByRole('button',{name:'Pilih roll '+roll.number,exact:true}).count())await plan.getByRole('button',{name:'Pilih roll '+roll.number,exact:true}).click()
   for(const[name,value]of[['Keluar roll rencana 1','1'],['Terpakai roll rencana 1','0.5'],['Sisa roll rencana 1','0.5'],['Hasil roll rencana 1','2']])await plan.getByLabel(name,{exact:true}).fill(value)
   await plan.getByLabel('Alasan rencana Potongan',{exact:true}).fill(p);const box=plan.getByLabel('Asumsi dan komposisi rencana sudah diperiksa',{exact:true});if(!await box.isChecked())await box.check()}
  await fill('P19 plan v2 browser: reviewed draft from the dated snapshot')
  r=await response(page,'erp_cp7_save_plan_draft_v2',()=>plan.getByRole('button',{name:'Simpan rencana Potongan',exact:true}).click());assert.equal(r.status(),200)
  const saved=await r.json();assert.equal(saved.contract_version,'cp7.plan-draft.v2');assert.equal('source_hash'in r.request().postDataJSON().p_payload,false)
  r=await response(page,'erp_cp7_preview_plan_action_v2',()=>plan.getByRole('button',{name:'Periksa pratinjau rencana',exact:true}).click());assert.equal(r.status(),200)
  const preview=await r.json();assert.equal(preview.live.apply_ready,true,JSON.stringify(preview.live.verdicts))
  const recheck=plan.getByRole('region',{name:'Pemeriksaan ulang rencana',exact:true});await ui.expect(recheck).toHaveAttribute('data-apply-ready','true');await ui.expect(recheck).toContainText('Kebutuhan sekarang: ')
  shots.push(await shot(ui,page,`P19P_${suffix}_PREVIEW_READY.png`))
  await plan.getByLabel('Alasan membuat draf Potongan',{exact:true}).fill('P19 plan v2 browser: one explicit Native draft');await plan.getByLabel('Pratinjau sudah diperiksa untuk membuat draf',{exact:true}).check()
  r=await response(page,'erp_cp7_apply_plan_action_v2',()=>plan.getByRole('button',{name:'Buat draf Potongan di ERP',exact:true}).click());assert.equal(r.status(),200)
  const applied=await r.json();assert.equal(applied.contract_version,'cp7.plan-apply-outcome.v2');assert.equal(applied.state,'NATIVE_DRAFT_CREATED')
  await ui.expect(plan).toContainText('draf Potongan sudah dibuat')
  let after=state();assert.deepEqual([after.drafts,after.staged_drafts,after.intents],[1,1,1]);assert.equal(after.domain_drafts,before.domain_drafts+1)
  let refused=null
  if(!mobile){
   // A second plan for the same target from the same snapshot: refused before any write.
   // The created draft retires the read options; they are read again first.
   r=await response(page,'erp_cp7_get_plan_options_v2',()=>plan.getByRole('button',{name:'Muat pilihan Potongan dari ERP',exact:true}).click());assert.equal(r.status(),200)
   await plan.getByLabel('Alasan rencana Potongan',{exact:true}).fill('P19 plan v2 browser: second plan from the same snapshot')
   r=await response(page,'erp_cp7_save_plan_draft_v2',()=>plan.getByRole('button',{name:'Simpan rencana Potongan',exact:true}).click());assert.equal(r.status(),200)
   r=await response(page,'erp_cp7_preview_plan_action_v2',()=>plan.getByRole('button',{name:'Periksa pratinjau rencana',exact:true}).click());assert.equal(r.status(),200)
   // The first plan's unposted draft also uses capacity: refused as well only when what is left is below this plan.
   const second=await r.json();refused=second.live.verdicts.filter(v=>v.status!=='OK')
   assert.deepEqual(refused.map(v=>v.code),Number(options.capacity_pcs)-2<2?['CP7_PLAN_V2_TARGET_PLANNED','CP7_PLAN_V2_CAPACITY_USED']:['CP7_PLAN_V2_TARGET_PLANNED'])
   await ui.expect(recheck).toHaveAttribute('data-apply-ready','false');await ui.expect(recheck).toContainText('Target ini sudah punya rencana lain sesudah data diambil.')
   await plan.getByLabel('Alasan membuat draf Potongan',{exact:true}).fill('Should stay disabled');await plan.getByLabel('Pratinjau sudah diperiksa untuk membuat draf',{exact:true}).check()
   await ui.expect(plan.getByRole('button',{name:'Buat draf Potongan di ERP',exact:true})).toBeDisabled()
   shots.push(await shot(ui,page,`P19P_${suffix}_REVIEW_REQUIRED.png`))
   after=state();assert.deepEqual([after.drafts,after.intents],[2,1])
  }
  assert.equal(calls.filter(c=>c.name.endsWith('_v1')).length,0,'P19P_V1_PLAN_RPC_CALLED_FOR_A_STAGED_RUN')
  assert.doesNotMatch(await region.innerText(),/terkini/i)
  return{status:'PASS',staged_run_by_click:true,plan_from_dated_snapshot:true,preview_live_recheck_ready:true,native_draft_created:true,
   second_plan_refused_target_planned:!mobile,refused,v1_rpcs_called:0,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19P_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),calls:calls.map(c=>c.name),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19P_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P19P_BROWSER_DESKTOP_PLAN',()=>journey(ui,today,false)],['P19P_BROWSER_MOBILE_PLAN',()=>journey(ui,today,true)]]}
