import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// Business Report v2 in the real UI: a staged run started by one trusted click,
// then a reviewed report of it published from the staged view, built by the
// server step by step (the panel shows the real progress) and sealed: the
// summary says "Data analisis per", its freshness and, on desktop, the finance
// and HPP read from the ERP finance report for the report date; one section is
// read on demand. Real Native fixture commands; no business DML.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p19_report_v2_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const STAGED='Analisis bertahap (hingga 5.000 target)'
const v2=['erp_cp7_publish_report_v2','erp_cp7_get_report_request_v2','erp_cp7_step_report_v2','erp_cp7_read_report_v2','erp_cp7_read_report_section_v2','erp_cp7_list_reports_v2']
const v1=['erp_cp7_publish_report_v1','erp_cp7_get_report_request_v1','erp_cp7_read_report_v1','erp_cp7_list_reports_v1','erp_cp7_compare_reports_v1']
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page){await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true});await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click();return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})}
async function shot(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function journey(ui,today,mobile){
 fixture('prepare',{today});const user=await ui.login('OWNER',{label:'p19r-'+(mobile?'mobile':'desktop'),mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',calls=[],replies=[],shots=[]
 page.on('request',r=>{const name=[...v2,...v1].find(n=>r.url().endsWith('/rpc/'+n));if(name)calls.push({name,body:r.postDataJSON()})})
 page.on('response',async r=>{const name=v2.find(n=>r.url().endsWith('/rpc/'+n));if(name&&r.request().method()==='POST')replies.push({name,status:r.status(),body:await r.json().catch(()=>null)})})
 let panel
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=fixture('state',{actor:user.user.id});assert.deepEqual([before.jobs,before.publications],[0,0])
  panel=await openPanel(page);await panel.getByRole('button',{name:STAGED,exact:true}).click()
  const staged=page.getByRole('region',{name:'Hasil analisis bertahap',exact:true});await ui.expect(staged).toBeVisible({timeout:180000})
  await ui.expect(staged).toContainText('Laporan dibuat dari analisis ini di bagian Laporan dari analisis bertahap di bawah')
  const report=page.getByRole('region',{name:'Laporan analisis bertahap',exact:true});await ui.expect(report).toContainText('Laporan memakai data analisis per ')
  await report.getByLabel('Judul laporan bertahap',{exact:true}).fill('P19 report v2 browser '+suffix.toLowerCase())
  await report.getByLabel('Alasan laporan bertahap',{exact:true}).fill('P19 report v2 browser: reviewed report of the dated staged snapshot')
  const finance=report.getByLabel('Sertakan keuangan dan HPP pada laporan bertahap',{exact:true})
  if(!mobile)await finance.check()
  await report.getByLabel('Laporan bertahap sudah ditinjau',{exact:true}).check()
  await report.getByRole('button',{name:'Buat laporan dari analisis ini',exact:true}).click()
  const article=report.getByRole('article',{name:'Isi laporan bertahap',exact:true});await ui.expect(article).toBeVisible({timeout:120000})
  const steps=replies.filter(r=>r.name==='erp_cp7_step_report_v2'),last=steps.at(-1)?.body
  assert.ok(last&&last.state==='DONE'&&last.publication_id,'P19R_DONE_NOT_OBSERVED');assert.equal(steps.length,last.unit_count)
  assert.deepEqual(steps.map(r=>r.body.units_done),Array.from({length:last.unit_count},(_,i)=>i+1),'P19R_ONE_UNIT_PER_STEP')
  const doc=replies.find(r=>r.name==='erp_cp7_read_report_v2')?.body;assert.ok(doc&&doc.id===last.publication_id)
  assert.equal(doc.finance,mobile?'DEFERRED':'INCLUDED');await ui.expect(article).toHaveAttribute('data-freshness-state',doc.freshness.state)
  const summary=report.getByLabel('Ringkasan laporan bertahap',{exact:true});await ui.expect(summary).toContainText('Data analisis per ')
  await ui.expect(summary).toContainText(mobile?'Keuangan dan HPP tidak dimasukkan ke laporan ini.':'Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan '+doc.report_date)
  await ui.expect(article).toContainText('Stok barang jadi aktual dibaca ')
  shots.push(await shot(ui,page,`P19R_${suffix}_REPORT_SEALED.png`))
  await report.getByRole('button',{name:'Buka bagian laporan',exact:true}).click()
  const section=report.getByLabel('Bagian laporan bertahap',{exact:true});await ui.expect(section).toContainText('BAGIAN 1 dari ')
  await ui.expect(section).toContainText('stok fisik aktual per ')
  const read=calls.find(c=>c.name==='erp_cp7_read_report_section_v2');assert.deepEqual(read.body,{p_id:doc.id,p_index:0,p_access:doc.access_epoch})
  shots.push(await shot(ui,page,`P19R_${suffix}_SECTION.png`))
  assert.equal(calls.filter(c=>v1.includes(c.name)).length,0,'P19R_V1_REPORT_RPC_CALLED_FOR_A_STAGED_RUN')
  assert.doesNotMatch(await report.innerText(),/terkini/i);assert.doesNotMatch(await staged.innerText(),/terkini/i)
  const after=fixture('state',{actor:user.user.id});assert.deepEqual([after.jobs,after.publications,after.finance,after.v1_publications],[1,1,mobile?0:1,before.v1_publications])
  assert.equal(await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('erp.cp7.report-request.v2:')).length),0,'P19R_PENDING_REQUEST_LEFT')
  return{status:'PASS',staged_run_by_click:true,report_steps:steps.length,sealed_with_data_as_of:true,freshness:doc.freshness.state,finance:doc.finance,
   section_read_with_access_epoch:true,v1_rpcs_called:0,no_horizontal_scroll:true,screenshots:shots}
 }catch(e){writeFileSync(`cp6-proof/t3/P19R_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),calls:calls.map(c=>c.name),text:await panel?.innerText().catch(()=>'')},null,2));await page.screenshot({path:`cp6-proof/t3/P19R_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['P19R_BROWSER_DESKTOP_REPORT',()=>journey(ui,today,false)],['P19R_BROWSER_MOBILE_REPORT',()=>journey(ui,today,true)]]}
