import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// AI v2 in the real UI: a staged run started by one trusted click, one target
// chosen for AI in the run's table, then "Periksa & salin": the bounded brief
// of the run is read and the checked text says the analysis time and that it
// is not current; on desktop the owner finance report is read at question
// time and named as such. The app sends nothing to an AI. No business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p19_report_v2_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const watched=['erp_cp7_get_staged_ai_brief_v1','erp_cp7_get_finance_report_v1','erp_cp7_read_analysis_v1','erp_cp7_read_analysis_manifest_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,today,mobile){
 fixture('prepare',{today});const user=await ui.login('OWNER',{label:'p19a-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],shots=[]
 page.on('request',r=>{const name=watched.find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  const staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(staged).toBeVisible({timeout:180000})
  const row=staged.locator('[data-analysis-target]').first();await ui.expect(row).toBeVisible();const key=await row.getAttribute('data-analysis-target')
  const pick=row.getByRole('button',{name:/^Pilih untuk AI /});await pick.click();await ui.expect(row.getByRole('button',{name:/^Batal pilih AI /})).toHaveAttribute('aria-pressed','true')
  const ai=page.getByRole('region',{name:'Tanya AI dari analisis bertahap',exact:true});await ui.expect(ai).toContainText('1 target dipilih')
  await ui.expect(ai).toContainText('bukan angka saat ini')
  if(!mobile)await ai.getByLabel('Sertakan keuangan dan HPP untuk AI',{exact:true}).check()
  await ai.getByLabel('Pertanyaan untuk AI dari analisis bertahap',{exact:true}).fill('P19 AI v2 browser: apa yang perlu diperiksa dulu?')
  await ai.getByRole('button',{name:'Periksa & salin pertanyaan untuk AI',exact:true}).click()
  const text=ai.getByLabel('Salinan pertanyaan dan ringkasan analisis bertahap',{exact:true});await ui.expect(text).toBeVisible({timeout:60000})
  const value=await text.inputValue();assert.match(value,/Angka analisis adalah keadaan per .* WIB \(data analisis bertahap\), bukan angka saat ini\./);assert.ok(value.includes(key),'P19A_SELECTED_TARGET_NOT_IN_PROMPT')
  assert.match(value,mobile?/Keuangan dan HPP tidak disertakan/:/Angka keuangan dan HPP berasal dari laporan keuangan ERP yang dibaca /)
  const briefs=calls.filter(c=>c.name==='erp_cp7_get_staged_ai_brief_v1');assert.equal(briefs.length,1);assert.deepEqual(briefs[0].body.p_targets,[key])
  assert.equal(calls.filter(c=>c.name==='erp_cp7_get_finance_report_v1').length,mobile?0:1)
  assert.equal(calls.filter(c=>c.name.startsWith('erp_cp7_read_analysis')).length,0,'P19A_WHOLE_READER_CALLED_FOR_A_STAGED_RUN')
  assert.doesNotMatch(value,/terkini/i);assert.doesNotMatch(await ai.innerText(),/terkini/i);assert.doesNotMatch(await staged.innerText(),/terkini/i)
  shots.push(await shot(ui,page,`P19A_${suffix}_PROMPT.png`))
  return{status:'PASS',staged_run_by_click:true,target_chosen_in_table:true,brief_calls:1,finance_read:!mobile,prompt_labelled:true,whole_readers_called:0,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19A_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),calls:calls.map(c=>c.name),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19A_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['P19A_BROWSER_DESKTOP_AI',()=>journey(ui,today,false)],['P19A_BROWSER_MOBILE_AI',()=>journey(ui,today,true)]]}
