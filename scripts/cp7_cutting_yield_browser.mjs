import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import * as history from './cp7_f04_history_browser.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f04_history_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function capture(ui,page,name){mkdirSync('cp6-proof/t3',{recursive:true});await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function readableCutting(page){
 const measured=await page.evaluate(()=>{
  const rgb=color=>color.match(/[\d.]+/g).slice(0,3).map(Number),luminance=color=>{const c=color.map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722}
  return [...document.querySelectorAll('.ccut-hero h1,.ccut-hero p,.ccut-hero span,.ccut-card>.cutting-pattern-picker>header strong,.ccut-card>.cutting-pattern-picker>header span,.ccut-card>.cutting-pattern-picker>header small')].map(el=>{
   let surface=el;while(surface&&Number(getComputedStyle(surface).backgroundColor.match(/[\d.]+/g)?.[3]??1)===0)surface=surface.parentElement
   if(!surface)throw Error('Cutting text has no measurable background')
   const fg=luminance(rgb(getComputedStyle(el).color)),bg=luminance(rgb(getComputedStyle(surface).backgroundColor))
   return{text:el.textContent,ratio:(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05)}
  })
 })
 assert.equal(measured.length,6,'All six actual cutting heading and pattern text surfaces must be measured')
 for(const x of measured)assert.ok(x.ratio>=4.5,`Cutting text contrast ${x.ratio}: ${x.text}`)
 return measured
}
export async function openCutting(ui,page,mobile){
 // Reload first restores Auth. Checking isVisible before that completed can
 // miss the mobile menu and try to click the off-canvas sidebar. Wait for the
 // real menu control and use the ordinary navigation without force clicks.
 if(mobile){const menu=page.getByRole('button',{name:'Buka menu',exact:true});await ui.expect(menu).toBeVisible();await menu.click()}
 const link=page.getByRole('button',{name:'• Buat Potongan',exact:true})
 if(!await link.isVisible()){const branch=page.locator('.sidebar .nav-main').filter({hasText:'Produksi'});await ui.expect(branch).toBeVisible();await branch.click()}
 await ui.expect(link).toBeVisible();await link.click()
}
async function cuttingJourney(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'native-cutting-yield-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,f=fixture('cut_prepare',{today}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const panel=page.getByRole('region',{name:'Sumber hasil potong',exact:true});let lost=null
 const state=()=>fixture('cut_state',{fixture:f,actor:user.user.id})
 try{
  await openCutting(ui,page,mobile)
  await page.getByLabel('Cari draft Potongan',{exact:true}).fill(f.group_number);const searched=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_cutting_workspace_v2')&&r.request().postDataJSON().p_draft_query===f.group_number);await page.getByRole('button',{name:'Cari draft',exact:true}).click();assert.equal((await searched).status(),200)
  await page.locator('.ccut-drafts button').filter({hasText:f.group_number}).click();await ui.expect(page.getByRole('button',{name:'Post ke WIP Potongan',exact:true})).toBeEnabled();await readableCutting(page)
  const notes=page.getByLabel('Catatan',{exact:true});await notes.fill('ISIAN OPERATOR TETAP ADA');const beforeDraft=state();assert.equal(Number(beforeDraft.raw_qty),100);assert.equal(beforeDraft.posted,false)
  await panel.getByRole('button',{name:'Muat hasil potong tersimpan',exact:true}).click();await ui.expect(panel).toContainText('Potongan belum diposting');assert.equal(await notes.inputValue(),'ISIAN OPERATOR TETAP ADA');assert.equal(state().native_hash,beforeDraft.native_hash)
  await ui.expect(page.getByRole('button',{name:'Post ke WIP Potongan',exact:true})).toBeEnabled();const posted=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_cutting_group_before_sewing_v2'));await page.getByRole('button',{name:'Post ke WIP Potongan',exact:true}).click();assert.equal((await posted).status(),200)
  await ui.expect(page.locator('.ccut-message.success')).toContainText('terposting. Form lama ditutup');const afterPost=state();assert.equal(Number(afterPost.raw_qty),40);assert.equal(Number(afterPost.raw_value),400);assert.equal(Number(afterPost.cut_pcs),60);assert.equal(afterPost.posted,true)
  await page.route('**/rest/v1/rpc/erp_cp7_capture_cutting_yield_v1',async route=>{if(!lost){const reply=await route.fetch();assert.equal(reply.status(),200);lost={envelope:route.request().postDataJSON(),body:await reply.json()};await route.abort('failed')}else await route.continue()})
  await panel.getByRole('button',{name:'Muat hasil potong tersimpan',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Pulihkan pembacaan hasil potong',exact:true})).toBeEnabled();assert.equal(state().native_hash,afterPost.native_hash);assert.equal(state().own_runs,2)
  await capture(ui,page,`CUTTING_SOURCE_UNCERTAIN_${suffix}.png`);screenshots.push(`CUTTING_SOURCE_UNCERTAIN_${suffix}.png`)
  await page.reload();await openCutting(ui,page,mobile)
  await ui.expect(panel.getByRole('button',{name:'Pulihkan pembacaan hasil potong',exact:true})).toBeEnabled();const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_capture_cutting_yield_v1'));await panel.getByRole('button',{name:'Pulihkan pembacaan hasil potong',exact:true}).click();const reply=await response;assert.equal(reply.status(),200);assert.deepEqual(reply.request().postDataJSON(),lost.envelope);assert.deepEqual(await reply.json(),lost.body)
  await ui.expect(panel.locator('[data-cutting-actual]')).toContainText('hasil potong 60 PCS');await ui.expect(panel).toContainText('Belum dapat dinilai.');assert.equal(lost.body.rows[0].interval,null);assert.equal(lost.body.rows[0].recorded_width_cm,null);assert.equal(lost.body.rows[0].planned_mix,null);assert.equal(state().native_hash,afterPost.native_hash);assert.equal(state().own_runs,2)
  const text_contrast=await readableCutting(page);await capture(ui,page,`CUTTING_SOURCE_RECOVERED_${suffix}.png`);screenshots.push(`CUTTING_SOURCE_RECOVERED_${suffix}.png`)
  fixture('deactivate',{actor:user.user.id});const afterDeactivation=state();assert.equal(Number(afterDeactivation.raw_qty),40);assert.equal(Number(afterDeactivation.raw_value),400);const denied=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_read_cutting_yield_v1'));await panel.getByRole('button',{name:'Periksa sumber hasil potong',exact:true}).click();assert.equal((await denied).status(),403);await ui.expect(panel.locator('[data-cutting-actual]')).toHaveCount(0);assert.equal(state().native_hash,afterDeactivation.native_hash)
  await capture(ui,page,`CUTTING_SOURCE_CURRENT_AUTH_${suffix}.png`);screenshots.push(`CUTTING_SOURCE_CURRENT_AUTH_${suffix}.png`)
  return{status:'PASS',actual_Native_draft_to_POST60_raw100_to40_value1000_to400:true,source_read_leaves_dirty_form_and_native_economics_unchanged:true,lost_committed_read_identical_UUID_replay_one_Original_after_posted_draft_leaves_picker:true,source_width_mix_range_missingness_not_imputed:true,current_deactivation403_retires_source_facts:true,text_contrast,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/CUTTING_SOURCE_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel.innerText().catch(()=>''),lost},null,2));await page.screenshot({path:`cp6-proof/t3/CUTTING_SOURCE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return history.cases(ui,today).concat([['CUTTING_SOURCE_BROWSER_DESKTOP',()=>cuttingJourney(ui,today,false)],['CUTTING_SOURCE_BROWSER_MOBILE',()=>cuttingJourney(ui,today,true)]])}
