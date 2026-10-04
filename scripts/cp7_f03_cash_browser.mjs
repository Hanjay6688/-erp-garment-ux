import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {reportDateCases} from './cp7_f03_report_dates_browser.mjs'
import {financeOverviewCases} from './cp7_f03_finance_overview_browser.mjs'
import {receivableCases} from './cp7_f03_receivables_browser.mjs'
import {journalCases} from './cp7_f03_journal_browser.mjs'

// Preserve both complete native pages without Linux's per-argument128KiB cap.
// stdin transports the full JSON; the16MiB output cap still refuses truncation.
const fixture=(operation,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_cash_browser_fixture.py',operation],{input:JSON.stringify(payload),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function screen(ui,page,name){
 mkdirSync('cp6-proof/t3',{recursive:true})
 await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})
}
async function journey(ui,f,mobile){
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'f03-cash-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 const cash=page.getByRole('main',{name:'Kas dan bank dari jurnal',exact:true}),observed=[],screenshots=[]
 const source=()=>{const value=fixture('read',f);for(const report of value.pages)delete report.captured_at;return value}
 try{
  await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached()
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Kas & Bank',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await ui.expect(cash.getByRole('button',{name:'Tampilkan kas',exact:true})).toBeEnabled()
  await cash.getByLabel('Periode kas dari',{exact:true}).fill(f.query.from);await cash.getByLabel('Periode kas sampai',{exact:true}).fill(f.query.to)
  const before=source()
  let response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_analysis_v1')&&r.request().postDataJSON()?.p_query?.from===f.query.from&&r.request().postDataJSON()?.p_query?.to===f.query.to&&r.request().postDataJSON()?.p_query?.offset===0)
  await cash.getByRole('button',{name:'Tampilkan kas',exact:true}).click()
  let result=await response;assert.equal(result.status(),200);observed.push(await result.json())
  await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(25)
  const metric=label=>cash.locator('.cproc-total').filter({has:page.getByText(label,{exact:true})}).locator('strong')
  await ui.expect(metric('Perubahan kas bersih')).toHaveText('Rp137,5')
  await ui.expect(metric('Debit rekening kas/bank')).toHaveText('Rp1.337,5');await ui.expect(metric('Kredit rekening kas/bank')).toHaveText('Rp1.200')
  await ui.expect(cash).toContainText('Saldo dan jurnal kas cocok.');await ui.expect(cash).toContainText('Penerimaan kas tidak otomatis menjadi penjualan')
  await screen(ui,page,`F03_CASH_PAGE1_${suffix}.png`);screenshots.push(`F03_CASH_PAGE1_${suffix}.png`)
  response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_analysis_v1')&&r.request().postDataJSON()?.p_query?.offset===25)
  await cash.getByRole('button',{name:'Jurnal berikutnya',exact:true}).click()
  result=await response;assert.equal(result.status(),200);observed.push(await result.json())
  await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(8)
  await ui.expect(metric('Perubahan kas bersih')).toHaveText('Rp137,5');await ui.expect(cash).toContainText('Total 33 jurnal')
  assert.equal(fixture('verify-pages',{...f,pages:observed}).status,'PASS')
  const actualIds=await cash.locator('[data-journal-id]').evaluateAll(rows=>rows.map(row=>row.getAttribute('data-journal-id')))
  assert.deepEqual(actualIds,observed[1].cash.entries.rows.map(row=>row.id))
  assert.deepEqual(source(),before)
  const pageIds=[...actualIds].sort();await cash.getByLabel('Urutkan halaman jurnal kas',{exact:true}).selectOption('LABEL_DESC')
  assert.deepEqual((await cash.locator('[data-journal-id]').evaluateAll(rows=>rows.map(row=>row.getAttribute('data-journal-id')))).sort(),pageIds)
  const exactNumber=observed[1].cash.entries.rows[0].journal_number
  await cash.getByLabel('Cari jurnal kas di halaman',{exact:true}).fill(exactNumber)
  response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_analysis_v1')&&r.request().postDataJSON()?.p_query?.offset===25)
  await cash.getByRole('button',{name:'Tampilkan kas',exact:true}).click();assert.equal((await response).status(),200);await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(1);await ui.expect(metric('Perubahan kas bersih')).toHaveText('Rp137,5');await ui.expect(cash).toContainText('Total 33 jurnal')
  response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_analysis_v1')&&r.request().postDataJSON()?.p_query?.offset===25)
  await cash.getByRole('button',{name:'Browse halaman ini',exact:true}).click();assert.equal((await response).status(),200);await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(8)
  assert.deepEqual(source(),before)
  await screen(ui,page,`F03_CASH_PAGE2_${suffix}.png`);screenshots.push(`F03_CASH_PAGE2_${suffix}.png`)
  if(mobile){
   fixture('revoke',f)
   response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_finance_analysis_v1'))
   await cash.getByRole('button',{name:'Tampilkan kas',exact:true}).click();result=await response;assert.equal(result.status(),403)
  }else{
   await page.route('**/rest/v1/rpc/erp_cp7_get_finance_analysis_v1',route=>route.abort('failed'))
   await cash.getByRole('button',{name:'Tampilkan kas',exact:true}).click()
  }
  await ui.expect(cash.getByRole('alert')).toBeVisible();await ui.expect(cash.locator('[data-journal-id]')).toHaveCount(0)
  assert.ok(!(await cash.innerText()).includes('Rp'))
  await ui.expect(cash.getByLabel('Periode kas dari',{exact:true})).toHaveValue(f.query.from)
  assert.deepEqual(source(),before)
  await screen(ui,page,`F03_CASH_RETIRED_${suffix}.png`);screenshots.push(`F03_CASH_RETIRED_${suffix}.png`)
  return {status:'PASS',mobile,actual_connected_cash_route:true,real_auth_native_read:true,source_pages:[25,8],source_count:33,
   O14_cash137_50_debit1337_50_credit1200:true,transfer1000_net0:true,complete_public_rows_match_native:true,
   no_business_read_side_effect:true,failed_network_or_current403_clears_all_old_money_and_rows:true,
   actual_server_revocation:mobile,financial_writer_claim:false,screenshots}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true})
  writeFileSync(`cp6-proof/t3/F03_CASH_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await cash.innerText().catch(()=>''),native_source:source()},null,2))
  await page.screenshot({path:`cp6-proof/t3/F03_CASH_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){
 const f=fixture('prepare',{today})
 return [['F03_CASH_BROWSER_DESKTOP',()=>journey(ui,f,false)],['F03_CASH_BROWSER_MOBILE_CURRENT_AUTH',()=>journey(ui,f,true)],...reportDateCases(ui,f),...financeOverviewCases(ui,f),...receivableCases(ui,f),...journalCases(ui,today)]
}
