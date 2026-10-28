// Prepared targeted OW08b source journeys. Existing CP6 host/Auth/navigation;
// no new installer, ledger or browser runner and no actual PASS claim yet.
import assert from 'node:assert/strict'
import {execFileSync}from 'node:child_process'
import {mkdirSync,writeFileSync}from 'node:fs'
import {dirname,resolve}from 'node:path'
import {fileURLToPath}from 'node:url'
import {readable}from '../current-vendor-money-browser/visual.mjs'
import {observeConsole,requireConsoleEvidence}from '../current-finance-combined-browser-qualification/console_evidence.mjs'
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const fixture=(op,p)=>JSON.parse(execFileSync('python',['-B',resolve(ROOT,'scripts/current-ow08-source-browser/fixture.py'),op],{input:JSON.stringify(p),cwd:ROOT,encoding:'utf8',maxBuffer:16*1024*1024}).trim())
export const IDS=['OW08_KASBON_JOURNAL_SOURCE_DESKTOP','OW08_KASBON_JOURNAL_SOURCE_MOBILE']
async function journalPage(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Jurnal & Transaksi Lain',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Jurnal Keuangan',exact:true})).toBeVisible()
 return page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true})
}
async function kasbonSources(ui,today,mobile){
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'ow08-kasbon-source-'+mobile,mobile}),page=user.page,observed=observeConsole(page)
 const shots=[],opened=[],contrasts=[],suffix=mobile?'MOBILE':'DESKTOP';let fixtureData
 try{
  fixtureData=fixture('kasbon',{today});const before=fixture('state',{})
  for(const row of fixtureData.rows){
   const panel=await journalPage(ui,page)
   await panel.getByLabel('Periode jurnal dari',{exact:true}).fill(row.date)
   await panel.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
   await panel.getByLabel('Cari sumber jurnal',{exact:true}).fill(row.journal_number)
   await panel.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click()
   const item=panel.locator('[data-journal-id="'+row.journal_id+'"]');await ui.expect(item).toBeVisible();await item.click()
   const detail=panel.getByRole('complementary',{name:'Rincian akun jurnal',exact:true})
   await ui.expect(detail).toContainText(row.journal_number)
   const responseReady=page.waitForResponse(r=>r.url().endsWith('/rest/v1/rpc/erp_cp7_resolve_transaction_source_v1')&&r.request().method()==='POST')
   await detail.getByRole('button',{name:'Buka transaksi asal',exact:true}).click()
   const response=await responseReady;assert.equal(response.status(),200,await response.text())
   assert.deepEqual(response.request().postDataJSON(),{p_source:{source_type:row.source_type,source_id:row.source_id}})
   const answer=await response.json();assert.equal(answer.status,'AVAILABLE');assert.equal(answer.business_DML,false)
   assert.equal(answer.document.id,row.kasbon_id);assert.equal(answer.document.domain,'KASBON');assert.equal(answer.document.status,row.status)
   assert.equal(answer.document.focus.parent_id,row.contractor_id)
   const target=page.getByRole('article',{name:'Kasbon '+row.kasbon_number,exact:true})
   await ui.expect(target).toBeVisible();await ui.expect(target).toHaveAttribute('aria-current','true')
   await ui.expect(target).toContainText(row.status==='CANCELLED'?'Dibatalkan':'1.200,00')
   assert.deepEqual(fixture('state',{}),before,'Source navigation must not change any business table or sequence')
   contrasts.push({state:row.status,rows:await readable(target)})
   mkdirSync('cp6-proof/t3',{recursive:true});await target.scrollIntoViewIfNeeded()
   for(const[scope,locator]of[['PAGE',page],['FOCUS',target]]){const path=`cp6-proof/t3/OW08_KASBON_${suffix}_${row.status}_${scope}.png`;await locator.screenshot({path,...(scope==='PAGE'?{fullPage:true}:{})});shots.push(path)}
   opened.push({journal:row.journal_id,source:response.request().postDataJSON(),document:answer.document})
  }
  const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));assert.ok(width.page<=width.viewport)
  const consoleEvidence=requireConsoleEvidence(observed.errors,[])
  return{status:'PASS',actual_real_Auth_public_source_RPC:true,actual_ledger_click_opens_given_and_cancelled_kasbon:true,all_business_rows_and_sequences_unchanged:true,
   observed:opened,visible_text_contrasts:contrasts,width,shots,console_evidence:consoleEvidence,fixture_source:fixtureData.fixture_source,screen_creation_claim:false,production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/OW08_KASBON_${suffix}_FIRST_FAILURE.json`,JSON.stringify({error:String(error),observed:opened,console:observed.errors,fixture:fixtureData},null,2));await page.screenshot({path:`cp6-proof/t3/OW08_KASBON_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{observed.stop();await user.context.close()}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>kasbonSources(ui,today,Boolean(i))])}
