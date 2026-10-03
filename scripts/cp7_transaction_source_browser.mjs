import assert from'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_transaction_source_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'transaction-source-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true})
 const state=()=>fixture('state',{fixture:f.fixture,transaction_id:f.transaction_id})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Jurnal & Transaksi Lain',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.fixture.physical.slice(0,10));await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(f.document.journals[0].number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click()
  await ui.expect(journal.locator(`[data-journal-id="${f.journal_id}"]`)).toBeVisible();await journal.locator(`[data-journal-id="${f.journal_id}"]`).click()
  const before=state();assert.equal(before.cash_delta,'-12.34')
  const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'));await journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click();const resolved=await response;assert.equal(resolved.status(),200);const result=await resolved.json();assert.equal(result.document.id,f.transaction_id);assert.equal(result.business_DML,false)
  const detail=page.getByRole('complementary',{name:'Rincian transaksi lain',exact:true});await ui.expect(detail).toContainText(f.document.number);await ui.expect(detail).toContainText('Rp12,34');assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_${suffix}.png`,fullPage:true})
  await page.getByLabel('Alasan posting atau pembalikan transaksi lain',{exact:true}).fill('Pembatalan dari transaksi asal setelah pemeriksaan');await page.getByLabel('Transaksi lain untuk posting atau pembalikan sudah diperiksa',{exact:true}).check()
  const inverse=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_save_misc_finance_v1')&&r.request().postDataJSON()?.p_action==='REVERSE');await page.getByRole('button',{name:'Balikkan transaksi lain',exact:true}).click();assert.equal((await inverse).status(),200)
  await ui.expect(detail).toContainText('Transaksi asli sudah dibalik');const after=state();assert.equal(after.document.status,'REVERSED');assert.equal(after.cash_delta,'0.00');assert.equal(after.stock_HPP_unchanged,true)
  return{status:'PASS',mobile,real_Auth_journal_exact_source_to_owner_reader:true,source_read_no_business_write:true,owning_inverse_single_Native_command:true,cash12_34_then_neutral:true,stock_HPP_unchanged:true,source_history_retained:true,screenshot:`CP7_SOURCE_${suffix}.png`}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_SOURCE_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state()},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['CP7_SOURCE_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_SOURCE_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
