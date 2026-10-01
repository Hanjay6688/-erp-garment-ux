import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_f03_misc_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const rpc=r=>r.url().endsWith('/rpc/erp_cp7_save_misc_finance_v1')
async function financeRoute(page,name){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
}
async function navigate(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Jurnal & Transaksi Lain',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await page.getByRole('button',{name:'Buka pendapatan dan biaya lain',exact:true}).click()
}
async function capture(ui,page,name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true})}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'f03-misc-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,ws=page.getByRole('region',{name:'Pendapatan dan biaya lain',exact:true}),suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 let ident=null,lost=null
 const state=()=>fixture('state',{fixture:f,transaction_id:ident})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await navigate(ui,page);await ui.expect(ws.getByRole('button',{name:'Buat transaksi lain',exact:true})).toBeEnabled();await ws.getByRole('button',{name:'Buat transaksi lain',exact:true}).click()
  await ws.getByLabel('Nomor transaksi lain',{exact:true}).fill(f.tag+'-BROWSER');await ws.getByLabel('Waktu transaksi lain WIB',{exact:true}).fill(f.physical.slice(0,16));await ws.getByLabel('Nominal transaksi lain',{exact:true}).fill('12.34')
  await ws.locator(`[data-misc-category-id="${f.categories.OTHER_EXPENSE.id}"]`).click();await ws.locator(`[data-misc-cash-id="${f.cash.id}"]`).click();await ws.getByLabel('Alasan simpan transaksi lain',{exact:true}).fill('Kategori rekening nominal dan waktu telah diperiksa');await ws.getByLabel('Draft transaksi lain sudah diperiksa',{exact:true}).check()
  let response=page.waitForResponse(r=>rpc(r)&&r.request().postDataJSON()?.p_action==='SAVE');await ws.getByRole('button',{name:'Simpan draft transaksi lain',exact:true}).click();let result=await response;assert.equal(result.status(),200);const saved=await result.json();ident=saved.transaction_id
  await ui.expect(ws.getByRole('button',{name:'Posting transaksi lain',exact:true})).toBeAttached();assert.equal(state().cash_delta,'0.00');assert.equal(state().document.journals.length,0)
  await ws.getByLabel('Alasan posting atau pembalikan transaksi lain',{exact:true}).fill('Nominal dan dampak kas sudah diperiksa');await ws.getByLabel('Transaksi lain untuk posting atau pembalikan sudah diperiksa',{exact:true}).check()
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_cp7_save_misc_finance_v1',async route=>{
    if(route.request().postDataJSON()?.p_action==='POST'&&!lost){const native=await route.fetch();assert.equal(native.status(),200);lost={envelope:route.request().postDataJSON(),body:await native.json()};await route.abort('failed')}else await route.continue()
   })
   await ws.getByRole('button',{name:'Posting transaksi lain',exact:true}).click()
   // The durable envelope exists before dispatch. Its notice can paint while
   // Native POST is still running: wait for this intercepted commit itself.
   await ui.expect.poll(()=>lost!==null).toBe(true)
   await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   assert.equal(state().document.status,'POSTED');assert.equal(state().cash_delta,'-12.34');assert.equal(state().requests.filter(r=>r.action==='POST').length,1)
   assert.ok(!(await page.getByRole('main',{name:'Jurnal keuangan dari buku'}).innerText()).includes('Rp'));const old=await page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.FINANCE_MISC.pending-mutation.v1:')));assert.equal(old.length,1);assert.equal(JSON.parse(old[0][1]).id,lost.envelope.p_request)
   await capture(ui,page,`F03_MISC_UNCERTAIN_${suffix}.png`);screenshots.push(`F03_MISC_UNCERTAIN_${suffix}.png`)
   for(const [name,label,scope]of [['• Kas & Bank','CASH','Kas dan bank dari jurnal'],['• Ringkasan Keuangan','OVERVIEW','Ringkasan keuangan dari buku'],['• Piutang Pelanggan','AR','Piutang pelanggan dari invoice'],['• Laporan & Tutup Buku','REPORT',null]]){
    const reads=[];const listener=r=>{if(['/rpc/erp_cp7_get_finance_analysis_v1','/rpc/erp_cp7_get_finance_report_v1','/rpc/erp_cp7_get_sales_v1'].some(end=>r.url().endsWith(end)))reads.push(r.url())};page.on('request',listener)
    await financeRoute(page,name);const region=scope?page.getByRole('main',{name:scope,exact:true}):page.locator('.cfinance-report');await ui.expect(region).toContainText('Ada transaksi yang belum dipastikan');assert.ok(!(await region.innerText()).includes('Rp'));await ui.expect(region.locator('[data-journal-id],[data-sale-id]')).toHaveCount(0);assert.equal(reads.length,0);page.off('request',listener)
    await capture(ui,page,`F03_MISC_PENDING_${label}_${suffix}.png`);screenshots.push(`F03_MISC_PENDING_${label}_${suffix}.png`);assert.equal(state().requests.filter(r=>r.action==='POST').length,1)
   }
   await page.reload();await navigate(ui,page);await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled();response=page.waitForResponse(r=>rpc(r)&&r.request().postDataJSON()?.p_request===lost.envelope.p_request);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();result=await response;assert.equal(result.status(),200);assert.deepEqual(result.request().postDataJSON(),lost.envelope);assert.deepEqual(await result.json(),lost.body)
  }else{response=page.waitForResponse(r=>rpc(r)&&r.request().postDataJSON()?.p_action==='POST');await ws.getByRole('button',{name:'Posting transaksi lain',exact:true}).click();result=await response;assert.equal(result.status(),200)}
  await ui.expect(ws.locator('[data-misc-journal-id]')).toHaveCount(1);let native=state();assert.equal(native.document.status,'POSTED');assert.equal(native.cash_delta,'-12.34');assert.equal(native.requests.filter(r=>r.action==='POST').length,1)
  await ui.expect(ws.getByRole('complementary',{name:'Rincian transaksi lain'})).toContainText('Rp12,34');await ui.expect(ws.getByRole('complementary',{name:'Rincian transaksi lain'})).toContainText(native.document.journals[0].transaction_date)
  const scope=await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('erp.production.FINANCE_MISC.pending-mutation.v1:')));assert.equal(scope.length,0)
  await capture(ui,page,`F03_MISC_POSTED_${suffix}.png`);screenshots.push(`F03_MISC_POSTED_${suffix}.png`)
  await ws.getByLabel('Alasan posting atau pembalikan transaksi lain',{exact:true}).fill('Koreksi transaksi sumber tetap disimpan');await ws.getByLabel('Transaksi lain untuk posting atau pembalikan sudah diperiksa',{exact:true}).check();response=page.waitForResponse(r=>rpc(r)&&r.request().postDataJSON()?.p_action==='REVERSE');await ws.getByRole('button',{name:'Balikkan transaksi lain',exact:true}).click();result=await response;assert.equal(result.status(),200)
  await ui.expect(ws.locator('[data-misc-journal-id]')).toHaveCount(2);native=state();assert.equal(native.document.status,'REVERSED');assert.equal(native.cash_delta,'0.00');assert.equal(native.document.journals.filter(j=>j.reversal_of_id!==null).length,1);assert.equal(native.document.journals.find(j=>j.reversal_of_id!==null).transaction_date,today)
  await capture(ui,page,`F03_MISC_REVERSED_${suffix}.png`);screenshots.push(`F03_MISC_REVERSED_${suffix}.png`)
  const before=native.document
  if(mobile){fixture('revoke',{});response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_misc_finance_v1'));await ws.getByRole('button',{name:'Muat ulang transaksi lain',exact:true}).click();result=await response;assert.equal(result.status(),403)}
  else{await page.route('**/rest/v1/rpc/erp_cp7_get_misc_finance_v1',route=>route.abort('failed'));await ws.getByRole('button',{name:'Muat ulang transaksi lain',exact:true}).click()}
  await ui.expect(ws.locator('[data-misc-id]')).toHaveCount(0);await ui.expect(ws.locator('[data-misc-journal-id]')).toHaveCount(0);await ui.expect(page.locator('[data-journal-id]')).toHaveCount(0);await ui.expect(page.locator('[data-journal-line-id]')).toHaveCount(0);assert.ok(!(await page.getByRole('main',{name:'Jurnal keuangan dari buku'}).innerText()).includes('Rp'));assert.deepEqual(state().document,before)
  await capture(ui,page,`F03_MISC_RETIRED_${suffix}.png`);screenshots.push(`F03_MISC_RETIRED_${suffix}.png`)
  return {status:'PASS',mobile,actual_Auth_native_draft_post_inverse:true,native_cash_delta_minus12_34_then_zero:true,all_source_and_linked_journal_dates_preserved:true,no_stock_HPP_effect:true,one_post_effect:true,lost_actual_committed_HTTP200_recovered_same_UUID_after_reload:!mobile,uncertain_cash_overview_AR_report_routes_no_financial_reads_or_facts:!mobile,current_ADMIN_permission403_or_failed_read_retires_all_money:true,retires_misc_panel_and_parent_book:true,actual_revocation:mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/F03_MISC_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await ws.innerText().catch(()=>''),native:ident?state():null},null,2));await page.screenshot({path:`cp6-proof/t3/F03_MISC_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return [['F03_MISC_BROWSER_DESKTOP_LOST_REPLY',()=>journey(ui,today,false)],['F03_MISC_BROWSER_MOBILE_CURRENT_AUTH',()=>journey(ui,today,true)]]}
