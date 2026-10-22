import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

export const IDS=['OW05B_DESKTOP_GUIDE_OPEN_NOTA_CANCEL_CORRECT_HISTORY','OW05B_MOBILE390_GUIDE_OPEN_NOTA_CANCEL_CORRECT_HISTORY']
const fixed=(op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/ow05b-browser-qualification/fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:8*1024*1024}).trim())
const rpc=name=>r=>r.url().endsWith('/rpc/'+name)
const STALE=['layar Nota/Gaji','WIP & Jahit','layar PO','Bahan Mandor','layar BS','layar Pool HPP','layar Kain Kantong']
async function response(promise){const r=await promise;assert.equal(r.status(),200,await r.text());return r.json()}
async function menu(page,section,item){
 const sidebar=page.locator('.sidebar'),toggle=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await toggle.isVisible()&&!await sidebar.evaluate(e=>e.classList.contains('sidebar-open')))await toggle.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:section}).click()
 await link.click()}

async function journey(ui,today,mobile){
 const f=fixed('prepare',{today}),suffix=mobile?'MOBILE390':'DESKTOP'
 const user=await ui.login('OWNER',{label:'ow05b-'+(mobile?'phone':'desktop'),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,expect=ui.expect,writes=[],progress={}
 const writers=['erp_cp7_correct_mandor_v1','erp_cp7_save_sewing_completion_v1','erp_cp7_save_payroll_v1']
 page.on('request',r=>{const name=r.url().split('/').at(-1);if(writers.includes(name))writes.push({rpc:name,args:r.postDataJSON()})})
 const card=()=>page.locator('.cwip-list>article').filter({hasText:f.number})
 const correction=()=>card().getByRole('region',{name:'Koreksi mandor sesudah jahit',exact:true})
 const sewing=()=>card().getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
 async function wip(){await menu(page,'Produksi','WIP & Sewing')
  await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
  await expect(card()).toHaveCount(1)}
 async function open(){const waiting=page.waitForResponse(rpc('erp_cp7_get_mandor_correction_v1'))
  await correction().getByRole('button',{name:'Koreksi mandor sesudah jahit',exact:true}).click();return response(waiting)}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await wip()
  // 1. Locked: every blocker names a real menu; the nota opens through the source reader; redo steps and empty history shown.
  const blocked=await open()
  assert.equal(blocked.eligible,false)
  assert.deepEqual(blocked.blockers.map(b=>b.kind).filter(k=>['PAYROLL','SEWING','WORK','WORK_JOURNAL'].includes(k)),['PAYROLL','SEWING','WORK','WORK_JOURNAL'])
  const text=await correction().innerText()
  for(const old of STALE)assert.ok(!text.includes(old),old)
  for(const name of['Keuangan › Payroll & Kasbon','Produksi › WIP & Sewing'])assert.ok(text.includes(name),name)
  const steps=correction().getByRole('list',{name:'Langkah sesudah koreksi mandor',exact:true})
  await expect(steps.locator('li')).toHaveCount(9)
  await expect(steps.locator('li').first()).toContainText('Produksi › WIP & Sewing')
  await expect(correction().getByRole('region',{name:'Riwayat koreksi mandor PO ini',exact:true})).toContainText('belum pernah dikoreksi')
  await expect(correction().getByRole('button',{name:'Ganti pembagian ke mandor yang benar',exact:true})).toBeDisabled()
  let waiting=page.waitForResponse(rpc('erp_cp7_resolve_transaction_source_v1'))
  await correction().getByRole('button',{name:'Buka '+f.payroll_number,exact:true}).click()
  const resolved=await response(waiting)
  assert.equal(resolved.status,'AVAILABLE');assert.equal(resolved.document.route,'finance-payroll');assert.equal(resolved.document.id,f.payroll)
  await expect(page.locator('main')).toContainText(f.payroll_number)
  progress.blocker_link_opened_payroll=true
  // 2. Cancel the nota on the Payroll & Kasbon screen it opened.
  await page.getByRole('button',{name:'Batalkan payroll',exact:true}).click()
  const action=page.getByRole('region',{name:'Periksa tindakan payroll',exact:true})
  await action.getByLabel('Alasan tindakan payroll',{exact:true}).fill('Salah mandor; nota dibatalkan sebelum koreksi')
  await action.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check()
  waiting=page.waitForResponse(rpc('erp_cp7_save_payroll_v1'))
  await action.getByRole('button',{name:'Batalkan payroll sekarang',exact:true}).click()
  await response(waiting)
  assert.equal(fixed('observe',{fixture:f}).payroll_status,'REVERSED')
  // 3. Back to WIP & Sewing: undo the old sewing, then correct the whole PO.
  await wip()
  await sewing().getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await sewing().getByRole('button',{name:'Batalkan 4 pcs',exact:true}).click()
  await sewing().getByLabel('Alasan batal selesai jahit '+f.number,{exact:true}).fill('Mandor salah; batalkan upah asal sebelum koreksi')
  waiting=page.waitForResponse(rpc('erp_cp7_save_sewing_completion_v1'))
  await sewing().getByRole('button',{name:'Batalkan catatan selesai jahit',exact:true}).click()
  await response(waiting)
  const undone=fixed('observe',{fixture:f})
  assert.equal(undone.old_work_status,'REVERSED');assert.equal(Number(undone.old_payable),0)
  const eligible=await open();assert.equal(eligible.eligible,true);assert.deepEqual(eligible.history,[])
  await correction().getByLabel('Mandor yang benar',{exact:true}).selectOption(f.target)
  await correction().getByLabel('Alasan koreksi mandor',{exact:true}).fill('Ganti seluruh PO ke mandor yang mengerjakan jahitan')
  await correction().getByLabel('Koreksi seluruh PO sudah diperiksa',{exact:true}).check()
  waiting=page.waitForResponse(rpc('erp_cp7_correct_mandor_v1'))
  await correction().getByRole('button',{name:'Ganti pembagian ke mandor yang benar',exact:true}).click()
  const changed=await response(waiting);assert.equal(changed.status,'PICKUPS_REPLACED')
  await expect(page.locator('.cwip-sewing-done')).toContainText('Catat ulang hasil jahit di Produksi › WIP & Sewing')
  await expect(page.locator('.cwip-sewing-done')).toContainText('Keuangan › Payroll & Kasbon')
  // 4. The stored correction is visible: when, old → new Mandor, by whom, why.
  const assigned=fixed('observe',{fixture:f})
  assert.equal(assigned.current_mandor,f.target);assert.equal(assigned.history.length,1);assert.equal(assigned.context_count,0)
  assert.deepEqual(assigned.preserved,undone.preserved)
  const h=assigned.history[0]
  assert.equal(h.old_contractor_name,f.mandor_name);assert.equal(h.new_contractor_name,f.target_name)
  assert.equal(h.reason,'Ganti seluruh PO ke mandor yang mengerjakan jahitan');assert.ok(h.actor_name)
  const reopened=await open();assert.deepEqual(reopened.history,assigned.history)
  const row=correction().getByRole('region',{name:'Riwayat koreksi mandor PO ini',exact:true}).locator('li')
  await expect(row).toHaveCount(1)
  for(const part of[`${f.mandor_name} → ${f.target_name}`,h.actor_name,h.reason,'WIB'])await expect(row).toContainText(part)
  progress.history_visible=true
  // 5. Sewing recorded again for the right Mandor (rate choice NEW, original physical time).
  await sewing().getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await sewing().getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('4')
  await sewing().getByLabel('Waktu selesai jahit '+f.number,{exact:true}).fill(f.physical_local)
  await sewing().getByLabel('Tarif baru (berlaku pada waktu jahit) '+f.number,{exact:true}).check()
  await sewing().getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Catat ulang empat pcs pada waktu fisik aslinya')
  await sewing().getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
  waiting=page.waitForResponse(rpc('erp_cp7_save_sewing_completion_v1'))
  await sewing().getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
  const posted=await response(waiting);assert.equal(Number(posted.result.wage_amount),24)
  const final=fixed('observe',{fixture:f})
  assert.equal(Number(final.old_payable),0);assert.equal(Number(final.new_payable),24);assert.equal(Number(final.wip_increment),24)
  assert.equal(final.posted_work_count,1);assert.equal(final.history.length,1)
  assert.deepEqual(writes.map(w=>w.rpc),['erp_cp7_save_payroll_v1','erp_cp7_save_sewing_completion_v1','erp_cp7_correct_mandor_v1','erp_cp7_save_sewing_completion_v1'])
  const viewport=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}))
  assert.ok(viewport.scroll<=viewport.width+1,JSON.stringify(viewport));if(mobile)assert.equal(viewport.width,390)
  await page.screenshot({path:`cp6-proof/t3/CP7_OW05B_GUIDANCE_${suffix}.png`,fullPage:true})
  return {status:'PASS',real_login:true,fixture_created_by_Native_SQL:true,all_journey_writes_from_actual_UI:true,
   timezone:'America/Los_Angeles',mobile,viewport,progress,blocker_menus_real:true,old_screen_names_absent:STALE,
   nota_opened_from_blocker_and_cancelled_on_its_screen:true,redo_steps:9,history_row:h,
   old_mandor_payable:'0.00',new_mandor_payable:'24.00',WIP_increment:'24.00',production_go:false}
 }catch(error){writeFileSync(`cp6-proof/t3/CP7_OW05B_GUIDANCE_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,
   text:await page.locator('main').innerText().catch(()=>''),state:(()=>{try{return fixed('observe',{fixture:f})}catch(e){return String(e)}})(),writes},null,2))
  await page.screenshot({path:`cp6-proof/t3/CP7_OW05B_GUIDANCE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await user.context.close()}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>journey(ui,today,Boolean(i))])}
