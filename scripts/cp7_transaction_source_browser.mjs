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
async function financeMenu(page,name){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
}
// Register the rejection handler before clicking so a failed assertion still
// reaches the context/Auth cleanup rather than leaving an unhandled waiter.
async function observed(page,predicate,click){const response=page.waitForResponse(predicate);response.catch(()=>{});await click();return response}
async function payrollJourney(ui,today,mobile){
 const f=fixture('prepare-payroll',{today,mobile}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'transaction-source-payroll-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true}),payments=page.getByRole('region',{name:'Pembayaran gaji',exact:true}),screenshots=[]
 const state=()=>fixture('state-payroll',{fixture:f.fixture})
 const sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1')
 const saveResponse=r=>r.url().endsWith('/rpc/erp_cp7_save_payroll_installment_v1')
 let lost=null
 const openJournal=async(id,number)=>{
  await financeMenu(page,'• Jurnal & Transaksi Lain');await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.fixture.payment_date);await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click();const row=journal.locator(`[data-journal-id="${id}"]`);await ui.expect(row).toBeVisible();await row.click()
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await openJournal(f.payment.journal_id,f.payment.journal_number)
  const before=state();assert.equal(before.document.paid_amount,'260.00');assert.equal(before.document.remaining_amount,'740.00');assert.equal(before.requests,26)
  let response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);let resolved=await response.json()
  assert.equal(resolved.business_DML,false);assert.equal(resolved.document.id,f.fixture.payroll);assert.deepEqual(resolved.document.focus,{kind:'PAYROLL_INSTALLMENT',id:f.payment.id,page_offset:25})
  const row=payments.locator(`[data-payment-id="${f.payment.id}"][data-source-focus="true"]`);await ui.expect(row).toContainText('Pembayaran asal dari buku');await ui.expect(row).toContainText(f.payment.journal_number);await ui.expect(payments).toContainText(f.fixture.approved.payroll_number);await ui.expect(payments.getByRole('button',{name:'Balikkan pembayaran sekarang',exact:true})).toHaveCount(0);assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_PAYROLL_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_PAYROLL_${suffix}.png`)
  await row.getByRole('button',{name:'Balikkan pembayaran '+f.payment.journal_number,exact:true}).click();await payments.getByLabel('Alasan pembayaran gaji',{exact:true}).fill('Balikkan pembayaran asal setelah nomor jumlah dan tanggal diperiksa');await payments.getByLabel('Pembayaran gaji sudah diperiksa',{exact:true}).check()
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_cp7_save_payroll_installment_v1',async route=>{if(route.request().postDataJSON()?.p_action==='REVERSE_PAYMENT'&&!lost){const result=await route.fetch();assert.equal(result.status(),200);lost={envelope:route.request().postDataJSON(),body:await result.json()};await route.abort('failed')}else await route.continue()})
   await payments.getByRole('button',{name:'Balikkan pembayaran sekarang',exact:true}).click();await ui.expect(payments.getByRole('button',{name:'Periksa status pembayaran gaji',exact:true})).toBeEnabled();assert.ok(!(await page.locator('.cpay').innerText()).includes('Rp'));assert.equal(state().requests,27)
   await page.reload();await financeMenu(page,'• Payroll & Kasbon');await ui.expect(payments.getByRole('button',{name:'Periksa status pembayaran gaji',exact:true})).toBeEnabled()
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_request===lost.envelope.p_request,()=>payments.getByRole('button',{name:'Periksa status pembayaran gaji',exact:true}).click());assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),lost.envelope);assert.deepEqual(await response.json(),lost.body);assert.equal(state().requests,27)
  }else{response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_action==='REVERSE_PAYMENT',()=>payments.getByRole('button',{name:'Balikkan pembayaran sekarang',exact:true}).click());assert.equal(response.status(),200);assert.equal(response.request().postDataJSON().p_payload.payment_id,f.payment.id)}
  await ui.expect(payments.locator('.cpay-net')).toHaveText(/Sisa gaji\s*Rp750/);const after=state();assert.equal(after.document.approved_net,'1000.00');assert.equal(after.document.paid_amount,'250.00');assert.equal(after.document.remaining_amount,'750.00');assert.equal(after.payments.rows[0].status,'REVERSED');assert.equal(after.payments.rows[0].id,f.payment.id);assert.equal(after.payments.rows[0].payment_date,f.payment.payment_date);assert.equal(after.requests,27)
  // An inverse journal still leads to the same immutable payment, not a new
  // guessed payroll UUID or a different first-page payment.
  await openJournal(after.payments.rows[0].reversal_journal_id,after.payments.rows[0].reversal_journal_number);response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);resolved=await response.json();assert.deepEqual(resolved.document.focus,{kind:'PAYROLL_INSTALLMENT',id:f.payment.id,page_offset:25});await ui.expect(row).toContainText('Dibalik');await ui.expect(row.getByRole('button',{name:'Balikkan pembayaran '+f.payment.journal_number,exact:true})).toHaveCount(0);assert.deepEqual(state(),after)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_PAYROLL_INVERSE_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_PAYROLL_INVERSE_${suffix}.png`)
  return{status:'PASS',mobile,real_Auth_journal_to_actual_payroll_and26th_payment:true,exact_second_page_not_client_scan:true,source_read_no_business_DML:true,reviewed_owning_inverse10_preserves_original_date_and_history:true,approved1000_paid260_then250_remaining740_then750:true,inverse_journal_reopens_same_reversed_child:true,stock_HPP_and_approved_cost_unchanged:true,actual_committed_inverse_reply_loss_reload_identical_UUID_one_effect:!mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_SOURCE_PAYROLL_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_PAYROLL_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{if(mobile)fixture('restore-payroll-admin',{original:f.fixture.admin_pay_original});await user.context.close()}
}
async function accessoryJourney(ui,today,mobile){
 const f=fixture('prepare-accessory',{today}),user=await ui.login('OWNER',{label:'transaction-source-accessory-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true}),form=page.getByRole('region',{name:'Form nota aksesori',exact:true}),screenshots=[]
 const state=()=>fixture('state-accessory',{fixture:f}),sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),saveResponse=r=>r.url().endsWith('/rpc/erp_save_accessory_issue_action_v1')
 let lost=null
 const openJournal=async(id,number)=>{
  await financeMenu(page,'• Jurnal & Transaksi Lain');await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.issue_at.slice(0,10));await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click();const row=journal.locator(`[data-journal-id="${id}"]`);await ui.expect(row).toBeVisible();await row.click()
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const original=f.journals.find(j=>j.source_type==='CONTRACTOR_MATERIAL_RECEIVABLE');assert.ok(original);await openJournal(original.id,original.number)
  const before=state();assert.deepEqual(Object.fromEntries(Object.entries(before.observation.stock).map(([key,value])=>[key,Number(value)])),{main:20,other:3});assert.equal(before.observation.document.total,'22.75')
  let response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);let result=await response.json()
  assert.equal(result.business_DML,false);assert.equal(result.document.id,f.issue.id);assert.equal(result.document.domain,'ACCESSORY_ISSUE');assert.equal(result.document.route,'contractor-issue');assert.equal(result.document.focus,null)
  await ui.expect(form.getByRole('heading')).toContainText(f.issue_number+' · POSTED');await ui.expect(form).toContainText('Rp 22,75');await ui.expect(page.getByRole('region',{name:'Riwayat nota aksesori',exact:true}).getByRole('button',{name:'Buka '+f.issue_number,exact:true})).toHaveCount(0)
  await ui.expect(form.getByRole('button',{name:'Sahkan pembatalan nota',exact:true})).toHaveCount(0);assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_ACCESSORY_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_ACCESSORY_${suffix}.png`)
  await form.getByLabel('Alasan pembatalan nota',{exact:true}).fill('Koreksi sumber pengambilan setelah barang dan nilai diperiksa');await form.getByRole('button',{name:'Periksa pembatalan',exact:true}).click();assert.deepEqual(state(),before)
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_save_accessory_issue_action_v1',async route=>{if(route.request().postDataJSON()?.p_action==='REVERSE'&&!lost){const r=await route.fetch();assert.equal(r.status(),200);lost={envelope:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()})
   await form.getByRole('button',{name:'Sahkan pembatalan nota',exact:true}).click();await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled();const committed=state();assert.equal(committed.observation.document.status,'REVERSED');assert.ok(lost)
   await page.reload();await financeMenu(page,'• Nota Ambil Aksesori');await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_client_request_id===lost.envelope.p_client_request_id,()=>page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click());assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),lost.envelope);assert.deepEqual(await response.json(),lost.body);assert.deepEqual(state(),committed)
  }else{
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_action==='REVERSE',()=>form.getByRole('button',{name:'Sahkan pembatalan nota',exact:true}).click());assert.equal(response.status(),200);assert.equal(response.request().postDataJSON().p_payload.id,f.issue.id)
  }
  await ui.expect(form.getByRole('heading')).toContainText(f.issue_number+' · REVERSED');const after=state();assert.deepEqual(after.observation.stock,f.before.stock);assert.deepEqual(after.observation.accounts,f.before.accounts);assert.deepEqual(after.observation.source,f.before.source);assert.equal(after.observation.document.id,before.observation.document.id);assert.equal(after.observation.document.physical_local,before.observation.document.physical_local);assert.deepEqual(after.observation.document.items.map(({payroll_status,...item})=>item),before.observation.document.items.map(({payroll_status,...item})=>item));assert.equal(after.inverses.length,2)
  const inverse=after.inverses.find(j=>j.original_id===original.id);assert.ok(inverse);await openJournal(inverse.id,inverse.number);response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);result=await response.json();assert.equal(result.document.id,f.issue.id)
  await ui.expect(form.getByRole('heading')).toContainText('REVERSED');await ui.expect(form.getByRole('button',{name:'Periksa pembatalan',exact:true})).toHaveCount(0);assert.deepEqual(state(),after)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_ACCESSORY_INVERSE_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_ACCESSORY_INVERSE_${suffix}.png`)
  return{status:'PASS',mobile,real_Auth_journal_to_exact_Native_note_outside_history50:true,source_and_review_no_business_DML:true,owning_Native_inverse_once_after_explicit_review:true,issued7_at3_25_stock20_3_and_receivable22_75:true,all_source_stock_and_accounts_restored:true,original_note_child_date_and_inverse_history_retained:true,actual_committed_inverse_reply_loss_reload_identical_UUID_one_effect:!mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_SOURCE_ACCESSORY_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_ACCESSORY_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['CP7_SOURCE_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_SOURCE_BROWSER_MOBILE',()=>journey(ui,today,true)],['CP7_SOURCE_PAYROLL_BROWSER_DESKTOP',()=>payrollJourney(ui,today,false)],['CP7_SOURCE_PAYROLL_BROWSER_MOBILE',()=>payrollJourney(ui,today,true)],['CP7_SOURCE_ACCESSORY_BROWSER_DESKTOP',()=>accessoryJourney(ui,today,false)],['CP7_SOURCE_ACCESSORY_BROWSER_MOBILE',()=>accessoryJourney(ui,today,true)]]}
