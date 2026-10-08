import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// Reminders v2 in the real UI: a staged run started by one trusted click, its
// reminder conditions prepared step by step from the run's dated snapshot, one
// production condition rechecked now, a local destination and a policy saved,
// then a local preview claimed after the server's recheck: its text states the
// snapshot time and the recheck, and nothing leaves the ERP. Only the v2
// reminder RPCs are called. Real Native fixture commands; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p19_reminder_v2_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const v2=['erp_cp7_step_reminder_conditions_v2','erp_cp7_read_reminder_conditions_v2','erp_cp7_get_reminder_obligations_v2','erp_cp7_recheck_reminder_v2','erp_cp7_get_reminder_workspace_v2',
 'erp_cp7_save_reminder_policy_v2','erp_cp7_save_reminder_binding_v2','erp_cp7_claim_reminder_v2','erp_cp7_finish_reminder_v2','erp_cp7_resolve_reminder_claim_v2','erp_cp7_get_reminder_request_v2']
const v1=['erp_cp7_get_rule_conditions_v1','erp_cp7_get_local_reminders_v1','erp_cp7_claim_local_preview_v1','erp_cp7_save_local_binding_v1','erp_cp7_get_reminder_policy_v1','erp_cp7_save_reminder_policy_v1','erp_cp7_read_analysis_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function response(page,name,action){const[request]=await Promise.all([page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/rpc/'+name)),action()]);const result=await request.response();assert.ok(result,'P19M_NO_RESPONSE '+name);return result}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today});const user=await ui.login('OWNER',{label:'p19m-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],shots=[]
 const state=()=>fixture('state',{actor:user.user.id})
 page.on('request',r=>{const name=[...v2,...v1].find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.deepEqual([before.sets,before.claims,before.rechecks],[0,0,0])
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  const staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(staged).toBeVisible({timeout:180000})
  await ui.expect(staged).toContainText('Laporan, Tanya AI dan pengingat dibuat dari analisis ini di bagian bawah')
  const rem=page.getByRole('region',{name:'Pengingat dari analisis bertahap',exact:true});await ui.expect(rem).toContainText('data analisis per ');await ui.expect(rem).toContainText('yang sudah selesai sejak analisis tidak ditagih')
  await rem.getByRole('button',{name:'Siapkan daftar pengingat',exact:true}).click();await ui.expect(rem).toHaveAttribute('data-set-state','DONE',{timeout:120000})
  await ui.expect(rem).toContainText('Daftar pengingat siap: ')
  await rem.getByLabel('Jenis pengingat',{exact:true}).selectOption('PRODUCTION_GAP')
  // The set's first page (every rule) is already on screen: each read is
  // searched only after the panel has settled on that read's own page.
  const list=rem.getByRole('list',{name:'Daftar pengingat dari analisis',exact:true}),show=rem.getByRole('button',{name:'Tampilkan pengingat',exact:true})
  const settled=async()=>{await ui.expect(show).toBeEnabled();await ui.expect(list.locator('[data-condition-key]:not([data-condition-key^="PRODUCTION_GAP:"])')).toHaveCount(0)}
  let r=await response(page,'erp_cp7_read_reminder_conditions_v2',()=>show.click());assert.equal(r.status(),200);await settled()
  const item=rem.locator(`[data-condition-key="PRODUCTION_GAP:${f.target_key}"]`)
  for(let i=0;i<200&&!await item.count();i++){const next=rem.getByRole('button',{name:'Halaman pengingat berikutnya',exact:true})
   if(!await next.count())assert.fail('P19M_FIXTURE_TARGET_NOT_LISTED '+JSON.stringify(fixture('condition',{actor:user.user.id,key:'PRODUCTION_GAP:'+f.target_key})))
   r=await response(page,'erp_cp7_read_reminder_conditions_v2',()=>next.click());assert.equal(r.status(),200);await settled()}
  await ui.expect(item).toHaveCount(1)
  r=await response(page,'erp_cp7_recheck_reminder_v2',()=>item.getByRole('button',{name:/^Periksa ulang sekarang /}).click());assert.equal(r.status(),200)
  const recheck=await r.json();assert.equal(recheck.verdict,'STILL_OPEN',JSON.stringify(recheck));assert.equal(recheck.recorded,false)
  await ui.expect(item.locator('[data-verdict="STILL_OPEN"]')).toContainText('Masih perlu: kurang sedikitnya ')
  const settings=rem.locator('details').filter({hasText:'Tujuan dan pengaturan pengingat'});await settings.locator('summary').click()
  await settings.getByLabel('Alasan tujuan pratinjau',{exact:true}).fill('P19 reminders v2 browser: local preview destination only')
  r=await response(page,'erp_cp7_save_reminder_binding_v2',()=>settings.getByRole('button',{name:'Simpan tujuan pratinjau lokal',exact:true}).click());assert.equal(r.status(),200)
  await ui.expect(rem).toContainText('Tujuan pratinjau lokal tersimpan')
  await settings.getByLabel('Aturan pengaturan pengingat',{exact:true}).selectOption('PRODUCTION_GAP')
  await settings.getByLabel('Batas pengingat',{exact:true}).fill('1');await settings.getByLabel('Jeda pengingat',{exact:true}).fill('0')
  await settings.getByLabel('Alasan pengaturan pengingat',{exact:true}).fill('P19 reminders v2 browser: explicit fixture threshold, not an operating value')
  r=await response(page,'erp_cp7_save_reminder_policy_v2',()=>settings.getByRole('button',{name:'Simpan pengaturan pengingat',exact:true}).click());assert.equal(r.status(),200)
  await ui.expect(rem).toContainText('Pengaturan pengingat tersimpan')
  r=await response(page,'erp_cp7_claim_reminder_v2',()=>item.getByRole('button',{name:/^Buat pratinjau lokal /}).click());assert.equal(r.status(),200)
  const claimed=await r.json();assert.equal(claimed.result.outcome,'CLAIMED',JSON.stringify(claimed.result));assert.equal(claimed.recheck.verdict,'STILL_OPEN');assert.equal(claimed.sent,false)
  const preview=rem.getByRole('article',{name:'Pratinjau lokal pengingat',exact:true});await ui.expect(preview).toContainText('PRATINJAU LOKAL — BELUM DIKIRIM')
  await ui.expect(preview).toContainText('Data analisis per ');await ui.expect(preview).toContainText('Diperiksa ulang ')
  if(!mobile){
   const row=rem.locator(`[data-claim-id="${claimed.result.claim_id}"]`);await ui.expect(row).toHaveAttribute('data-claim-status','CLAIMED')
   r=await response(page,'erp_cp7_finish_reminder_v2',()=>row.getByRole('button',{name:'Catat pratinjau lokal',exact:true}).click());assert.equal(r.status(),200)
   const finished=await r.json();assert.equal(finished.claim.status,'LOCAL_SINK_CAPTURED',JSON.stringify(finished.claim));assert.equal(finished.recheck.phase,'FINISH')
   await ui.expect(rem.locator(`[data-claim-id="${claimed.result.claim_id}"]`)).toHaveAttribute('data-claim-status','LOCAL_SINK_CAPTURED')
  }
  const after=state();assert.equal(after.sets,1);assert.equal(after.claims,1);assert.equal(after.v1_claims,0);assert.ok(after.rechecks>=(mobile?1:2),JSON.stringify(after))
  assert.equal(calls.filter(c=>v1.includes(c.name)).length,0,'P19M_V1_OR_WHOLE_READER_CALLED_FOR_A_STAGED_RUN')
  for(const c of calls.filter(c=>c.name==='erp_cp7_claim_reminder_v2'||c.name==='erp_cp7_save_reminder_binding_v2'))assert.match(c.body.p_payload.identity_hash,/^[0-9a-f]{64}$/)
  assert.doesNotMatch(await rem.innerText(),/terkini/i);assert.doesNotMatch(await staged.innerText(),/terkini/i)
  shots.push(await shot(ui,page,`P19M_${suffix}_PREVIEW.png`))
  return{status:'PASS',staged_run_by_click:true,conditions_prepared_step_by_step:true,recheck_still_open:true,destination_and_policy_saved:true,
   preview_claimed_after_recheck:true,recorded:!mobile,v1_rpcs_called:0,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19M_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),calls:calls.map(c=>c.name),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19M_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['P19M_BROWSER_DESKTOP_REMINDERS',()=>journey(ui,today,false)],['P19M_BROWSER_MOBILE_REMINDERS',()=>journey(ui,today,true)]]}
