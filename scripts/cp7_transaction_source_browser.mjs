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
  await ui.expect(form.getByRole('heading')).toContainText(f.issue_number+' · REVERSED');await ui.expect(form).toContainText('nota ini tidak lagi ditagih');await ui.expect(form.getByRole('columnheader',{name:'Sisa ditagih',exact:true})).toHaveCount(0);const after=state();assert.deepEqual(after.observation.stock,f.before.stock);assert.deepEqual(after.observation.accounts,f.before.accounts);assert.deepEqual(after.observation.source,f.before.source);assert.equal(after.observation.document.id,before.observation.document.id);assert.equal(after.observation.document.physical_local,before.observation.document.physical_local);assert.deepEqual(after.observation.document.items.map(({payroll_status,...item})=>item),before.observation.document.items.map(({payroll_status,...item})=>item));assert.equal(after.inverses.length,2)
  const inverse=after.inverses.find(j=>j.original_id===original.id);assert.ok(inverse);await openJournal(inverse.id,inverse.number);response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);result=await response.json();assert.equal(result.document.id,f.issue.id)
  await ui.expect(form.getByRole('heading')).toContainText('REVERSED');await ui.expect(form.getByRole('button',{name:'Periksa pembatalan',exact:true})).toHaveCount(0);assert.deepEqual(state(),after)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_ACCESSORY_INVERSE_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_ACCESSORY_INVERSE_${suffix}.png`)
  return{status:'PASS',mobile,real_Auth_journal_to_exact_Native_note_outside_history50:true,source_and_review_no_business_DML:true,owning_Native_inverse_once_after_explicit_review:true,issued7_at3_25_stock20_3_and_receivable22_75:true,all_source_stock_and_accounts_restored:true,original_note_child_date_and_inverse_history_retained:true,actual_committed_inverse_reply_loss_reload_identical_UUID_one_effect:!mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_SOURCE_ACCESSORY_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_ACCESSORY_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
async function productionMenu(page,name){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()
}
async function reworkJourney(ui,today,mobile){
 const f=fixture('prepare-rework',{today}),user=await ui.login('OWNER',{label:'transaction-source-rework-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true}),screenshots=[]
 const state=()=>fixture('state-rework',{fixture:f}),sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),saveResponse=r=>r.url().endsWith('/rpc/erp_save_bs_resolution_action_v1')
 const exactOrder=()=>page.locator(`[data-case-id="${f.bs}"] [data-rework-id="${f.rework}"]`)
 let lost=null
 const openJournal=async(id,number)=>{
  await financeMenu(page,'• Jurnal & Transaksi Lain');await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.journal.date);await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click();const row=journal.locator(`[data-journal-id="${id}"]`);await ui.expect(row).toBeVisible();await row.click()
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await openJournal(f.journal.id,f.journal.number)
  const before=state();assert.equal(before.lot_qty,'2');assert.equal(before.source.focus.page_offset,f.first_offset)
  let response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);let resolved=await response.json()
  assert.equal(resolved.document.domain,'BS_REWORK');assert.equal(resolved.document.id,f.bs);assert.equal(resolved.document.focus.id,f.rework);assert.equal(resolved.document.focus.page_offset,f.first_offset);assert.equal(resolved.business_DML,false)
  await ui.expect(exactOrder()).toHaveAttribute('data-source-focus','true');await ui.expect(exactOrder()).toContainText(f.number);await ui.expect(exactOrder()).toContainText('2 Good · 0 BS');await ui.expect(page.locator('.cbsr-pagination')).toContainText(String(f.first_offset+1)+'–')
  await ui.expect(exactOrder().getByRole('button',{name:'Sahkan pembatalan hasil',exact:true})).toHaveCount(0);assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_REWORK_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_REWORK_${suffix}.png`)
  await exactOrder().getByLabel('Alasan pembatalan hasil rework',{exact:true}).fill('Hasil repair tidak terjadi setelah pemeriksaan barang dan upah')
  await exactOrder().getByRole('button',{name:'Periksa pembatalan hasil',exact:true}).click();await ui.expect(exactOrder().getByRole('region',{name:'Pemeriksaan pembatalan hasil rework',exact:true})).toContainText('Batalkan hasil 2 Good dan 0 BS');assert.deepEqual(state(),before)
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_save_bs_resolution_action_v1',async route=>{if(route.request().postDataJSON()?.p_action==='REVERSE_REWORK_COMPLETION'&&!lost){const r=await route.fetch();assert.equal(r.status(),200);lost={envelope:route.request().postDataJSON(),body:await r.json()};await route.abort('failed')}else await route.continue()})
   await exactOrder().getByRole('button',{name:'Sahkan pembatalan hasil',exact:true}).click();await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled();const committed=state();assert.equal(committed.order.status,'CANCELLED');assert.ok(lost)
   await page.reload();await productionMenu(page,'• Barang BS & Rework');await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_client_request_id===lost.envelope.p_client_request_id,()=>page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click());assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),lost.envelope);assert.deepEqual(await response.json(),lost.body);assert.deepEqual(state(),committed)
  }else{
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_action==='REVERSE_REWORK_COMPLETION',()=>exactOrder().getByRole('button',{name:'Sahkan pembatalan hasil',exact:true}).click());assert.equal(response.status(),200);assert.equal(response.request().postDataJSON().p_payload.rework_order_id,f.rework)
   await ui.expect(exactOrder()).toHaveAttribute('data-source-focus','true');await ui.expect(page.locator('.cbsr-pagination')).toContainText('1–')
  }
  await ui.expect(exactOrder()).toContainText('CANCELLED');const after=state();assert.equal(after.lot_qty,'0');assert.equal(after.order.id,before.order.id);assert.equal(after.order.bs_case_id,before.order.bs_case_id);assert.equal(after.order.physical_sent_at,before.order.physical_sent_at);assert.deepEqual(after.original_movement,before.original_movement);assert.equal(after.inverses.length,1);assert.notEqual(after.source.focus.page_offset,f.first_offset)
  const inverse=after.inverses[0];await openJournal(inverse.id,inverse.number);response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);resolved=await response.json();assert.equal(resolved.document.id,f.bs);assert.equal(resolved.document.focus.id,f.rework)
  await ui.expect(exactOrder()).toHaveAttribute('data-source-focus','true');await ui.expect(exactOrder()).toContainText('CANCELLED');await ui.expect(exactOrder().getByRole('button',{name:'Periksa pembatalan hasil',exact:true})).toHaveCount(0);assert.deepEqual(state(),after)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_REWORK_INVERSE_${suffix}.png`,fullPage:true});screenshots.push(`CP7_SOURCE_REWORK_INVERSE_${suffix}.png`)
  return{status:'PASS',mobile,real_Auth_journal_to_exact_Native_rework_bs_outside50:true,opening_and_inverse_review_no_business_DML:true,original_order_and_FG_movement_retained_when_resolution_deleted:true,actual_repaired2_and_labor60_inverse_zero_lot_qty:true,closed_case_repositions_to_open_owning_page:true,inverse_journal_reopens_same_cancelled_child:true,actual_committed_inverse_reply_loss_reload_identical_UUID_one_effect:!mobile,screenshots}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_SOURCE_REWORK_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_REWORK_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
async function productionReadJourney(ui,today,mobile){
 const f=fixture('prepare-production-read',{today}),user=await ui.login('ADMIN',{label:'transaction-production-current-read-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',screenshots=[],observations=[]
 const rpc='erp_get_laundry_qc_workspace_v1',path='**/rest/v1/rpc/'+rpc,boundary=()=>fixture('production-boundary',{})
 const ownReason='Operator draft '+suffix,ownTime=today+'T09:15',writes=[]
 page.on('request',request=>{if(request.url().endsWith('/rpc/erp_save_laundry_qc_action_v1'))writes.push(request.postDataJSON())})
 const permission=(key,allowed)=>fixture('production-permission',{role:f.admin_role,permission:key,allowed})
 const responseFor=scope=>r=>r.url().endsWith('/rpc/'+rpc)&&r.request().postDataJSON()?.p_scope===scope
 let releaseHeld=null,qcFirstSize=null
 const freshFacts=async(scope,response)=>{
  assert.equal(response.status(),200);const actual=await response.json(),expected=fixture('production-read',{actor:user.user.id,scope,query:f.group_number})
  // Compare every actual Native member for the same actual Auth actor. The
  // independent SQL and HTTP statements have different capture times only.
  for(const value of [actual,expected])assert.ok(Number.isFinite(Date.parse(value.generated_at)))
  const {generated_at:actualAt,...actualFacts}=actual,{generated_at:expectedAt,...expectedFacts}=expected
  assert.deepEqual(actualFacts,expectedFacts);assert.equal(actual.scope,scope)
  if(scope==='LAUNDRY'){
   const delivery=actual.deliveries.find(d=>d.delivery_id===f.delivery_id);assert.ok(delivery);assert.equal(delivery.cutting_group_id,f.group_id);assert.equal(delivery.qty_sent_pcs,20)
   assert.deepEqual(delivery.sizes.map(s=>s.qty_sent_pcs),f.actual_qty_by_size);await ui.expect(page.locator('.clq-history')).toContainText(f.delivery_number);await ui.expect(page.locator('.clq-history')).toContainText(f.group_number)
  }else{
   const rows=actual.qc_queue.filter(r=>r.cutting_group_id===f.group_id);assert.equal(rows.length,4);assert.equal(rows.reduce((n,r)=>n+r.available_for_qc_qty_pcs,0),20)
   assert.equal(typeof rows[0].size_code,'string');assert.ok(rows[0].size_code.length);qcFirstSize=rows[0].size_code
   assert.deepEqual(rows.map(r=>r.available_for_qc_qty_pcs),f.actual_qty_by_size);await ui.expect(page.locator(`.clq-panel option[value="${f.group_id}"]`)).toHaveCount(1)
  }
  await ui.expect(page.locator('.clq-kpis [data-kpi-state="KNOWN"]')).toHaveCount(4)
 }
 const retiredFacts=async()=>{
  await ui.expect(page.locator('.clq-kpis [data-kpi-state="UNKNOWN"]')).toHaveCount(4)
  await ui.expect(page.locator('.clq-kpis strong')).toHaveText(['—','—','—','—'])
  await ui.expect(page.locator('.clq-history article')).toHaveCount(0);await ui.expect(page.locator(`.clq-panel option[value="${f.group_id}"]`)).toHaveCount(0)
  assert.ok(!(await page.locator('.connected-laundry-qc-page').innerText()).includes(f.group_number))
 }
 const ownInput=scope=>scope==='LAUNDRY'?page.locator('.clq-reversal input').first():page.getByRole('textbox',{name:'ALASAN / BUKTI HASIL QC',exact:true})
 const enterOwn=async scope=>{
  await ui.expect(ownInput(scope)).toBeEnabled();await ownInput(scope).fill(ownReason)
  if(scope==='QC'){
   await page.locator('.clq-form-grid select').first().selectOption(f.group_id)
   await page.getByLabel('WAKTU FISIK QC',{exact:true}).fill(ownTime)
   await page.getByRole('textbox',{name:`Good final size ${qcFirstSize}`,exact:true}).fill('0002')
   await page.getByRole('textbox',{name:`BS QC size ${qcFirstSize}`,exact:true}).fill('00')
   await page.locator('.clq-confirm input').check()
  }
 }
 const retainedOwn=async scope=>{
  await ui.expect(ownInput(scope)).toHaveValue(ownReason)
  if(scope==='QC'){
   await ui.expect(page.locator('.clq-form-grid select').first()).toHaveValue(f.group_id)
   await ui.expect(page.getByLabel('WAKTU FISIK QC',{exact:true})).toHaveValue(ownTime)
   await ui.expect(page.getByRole('textbox',{name:`Good final size ${qcFirstSize}`,exact:true})).toHaveValue('0002')
   await ui.expect(page.getByRole('textbox',{name:`BS QC size ${qcFirstSize}`,exact:true})).toHaveValue('00')
   await ui.expect(page.locator('.clq-confirm input')).not.toBeChecked()
   await ui.expect(page.getByRole('button',{name:'Post QC + Final SKU atomic',exact:true})).toBeDisabled()
  }
  assert.equal(writes.length,0)
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  for(const [scope,menu,view]of [['LAUNDRY','• Laundry','production.laundry.view'],['QC','• QC & Final SKU','production.final_sku.view']]){
   let response=await observed(page,responseFor(scope),()=>productionMenu(page,menu));assert.equal(response.status(),200)
   if(scope==='LAUNDRY')await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click()
   const before=boundary();response=await observed(page,responseFor(scope),()=>page.locator('.clq-tabs input').fill(f.group_number));await freshFacts(scope,response);assert.deepEqual(boundary(),before)
   await enterOwn(scope);assert.deepEqual(boundary(),before)
   await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);const currentName=`CP7_PRODUCTION_READ_${scope}_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+currentName,fullPage:true});screenshots.push(currentName)
   let upstreamResolve,upstreamReject,heldReply=null
   const upstream=new Promise((resolve,reject)=>{upstreamResolve=resolve;upstreamReject=reject});upstream.catch(()=>{})
   const gate=new Promise(resolve=>{releaseHeld=resolve})
   const hold=async route=>{
    try{heldReply=await route.fetch();assert.equal(heldReply.status(),200);upstreamResolve();await gate;await route.fulfill({response:heldReply})}
    catch(e){upstreamReject(e);await route.abort('failed').catch(()=>{})}
   }
   await page.route(path,hold,{times:1})
   const oldReply=page.waitForResponse(responseFor(scope));oldReply.catch(()=>{})
   await page.getByRole('button',{name:'Muat ulang data',exact:true}).click();await retiredFacts();await upstream
   await page.evaluate(()=>window.dispatchEvent(new StorageEvent('storage',{key:null})))
   releaseHeld();releaseHeld=null;assert.equal((await oldReply).status(),200);await retiredFacts();assert.deepEqual(boundary(),before)
   response=await observed(page,responseFor(scope),()=>page.getByRole('button',{name:'Muat ulang data',exact:true}).click());await freshFacts(scope,response);await retainedOwn(scope);assert.deepEqual(boundary(),before)
   // Revoke the actual ordinary ADMIN view in PostgreSQL. No substitute 403
   // response and no protected OWNER permission is used for this observation.
   if(scope==='QC')await page.locator('.clq-confirm input').check()
   permission(view,false);const revoked=boundary()
   response=await observed(page,responseFor(scope),()=>page.getByRole('button',{name:'Muat ulang data',exact:true}).click());assert.equal(response.status(),403);assert.equal((await response.json()).code,'42501');await retiredFacts();await ui.expect(page.locator('.clq-alert.error')).toBeVisible();assert.deepEqual(boundary(),revoked)
   const deniedName=`CP7_PRODUCTION_READ_${scope}_DENIED_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+deniedName,fullPage:true});screenshots.push(deniedName)
   permission(view,true);const restored=boundary();response=await observed(page,responseFor(scope),()=>page.getByRole('button',{name:'Muat ulang data',exact:true}).click());await freshFacts(scope,response);await retainedOwn(scope);assert.deepEqual(boundary(),restored)
   observations.push({scope,same_actual_Auth_Native_SQL_and_HTTP_facts:true,actual_unequal_size_qtys:[5,8,3,4],total20:true,read_start_retires_old_facts_and_KPIs:true,held_actual200_after_shared_storage_invalidation_not_painted:true,current_Native403_retires_facts_not_zero:true,explicit_fresh_recovery:true,own_unsent_reason_retained_through_held200_and_actual403:true,QC_raw_0002_00_and_physical_time_retained_confirmation_reset:scope==='QC',zero_Laundry_QC_writer_requests:true,all_ERP_platform_Auth_schema_rows_unchanged_by_reads:true})
  }
  return{status:'PASS',mobile,scopes:observations,screenshots,no_business_writer_or_substituted_reply:true}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_PRODUCTION_READ_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('.connected-laundry-qc-page').innerText().catch(()=>''),state:boundary(),observations},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_PRODUCTION_READ_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{if(releaseHeld)releaseHeld();for(const [key,allowed]of Object.entries(f.original_permissions))permission(key,allowed);await user.context.close()}
}
async function supplierPaymentJourney(ui,today,mobile){
 const f=fixture('prepare-supplier-payment',{today}),user=await ui.login('OWNER',{label:'source-supplier-payment-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true}),payments=page.getByRole('region',{name:'Pembayaran supplier',exact:true})
 const sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),saveResponse=r=>r.url().endsWith('/rpc/erp_cp7_reverse_supplier_payment_v1')
 const state=()=>{
  const result=fixture('state-supplier-payment',{fixture:f})
  assert.ok(Number.isFinite(Date.parse(result.workspace.captured_at)))
  const {captured_at,...facts}=result.workspace
  return{...result,workspace:facts}
 }
 const openJournal=async(id,number)=>{
  await financeMenu(page,'• Jurnal & Transaksi Lain');await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.day);await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click()
  const row=journal.locator(`[data-journal-id="${id}"]`);await ui.expect(row).toBeVisible();await row.click()
 }
 const owningRow=()=>payments.locator(`[data-supplier-payment-id="${f.target}"][data-source-focus="true"]`)
 let lost=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state(),original=before.payment
  assert.equal(before.workspace.page.offset,25);assert.equal(before.workspace.Native_AP.paid,'260.00');assert.equal(before.workspace.Native_AP.remaining,'740.00');assert.equal(before.cash_delta,'-260.00');assert.equal(before.requests,0)
  await openJournal(original.journal.id,original.journal.number)
  let response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200)
  let resolved=await response.json();assert.equal(resolved.business_DML,false);assert.equal(resolved.document.id,f.receipt.purchase_id);assert.deepEqual(resolved.document.focus,{kind:'SUPPLIER_PAYMENT',id:f.target,page_offset:25})
  await ui.expect(owningRow()).toContainText(original.number);await ui.expect(owningRow()).toContainText('Pembayaran asal dari buku transaksi');await ui.expect(payments).toContainText('Rp740');assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  let filename=`CP7_SOURCE_SUPPLIER_PAYMENT_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  await owningRow().getByRole('button',{name:'Tinjau pembatalan '+original.number,exact:true}).click()
  await payments.getByLabel('Alasan pembatalan pembayaran supplier',{exact:true}).fill('Pembayaran asal dibalik setelah jumlah tanggal dan sumber kas diperiksa')
  await payments.getByLabel('Pembayaran supplier sudah diperiksa',{exact:true}).check();assert.deepEqual(state(),before)
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_cp7_reverse_supplier_payment_v1',async route=>{
    if(!lost){const result=await route.fetch();assert.equal(result.status(),200);lost={envelope:route.request().postDataJSON(),body:await result.json()};await route.abort('failed')}
    else await route.continue()
   })
   await payments.getByRole('button',{name:'Balikkan pembayaran supplier sekarang',exact:true}).click();await ui.expect(payments.getByRole('button',{name:'Periksa status pembatalan supplier',exact:true})).toBeEnabled()
   assert.ok(lost);assert.equal(state().requests,1);assert.equal(await payments.getByText('Sisa utang',{exact:true}).count(),0)
   await page.reload()
   const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
   const link=page.getByRole('button',{name:'• Pembelian & Penerimaan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()
   await ui.expect(payments.getByRole('button',{name:'Periksa status pembatalan supplier',exact:true})).toBeEnabled()
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_request===lost.envelope.p_request,()=>payments.getByRole('button',{name:'Periksa status pembatalan supplier',exact:true}).click())
   assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),lost.envelope);assert.deepEqual(await response.json(),lost.body)
  }else{
   response=await observed(page,saveResponse,()=>payments.getByRole('button',{name:'Balikkan pembayaran supplier sekarang',exact:true}).click());assert.equal(response.status(),200);assert.equal(response.request().postDataJSON().p_payload.payment_id,f.target)
  }
  await ui.expect(owningRow()).toContainText('Sudah dibalik');await ui.expect(payments).toContainText('Rp750')
  const after=state();assert.equal(after.workspace.Native_AP.final_ap,'1000.00');assert.equal(after.workspace.Native_AP.paid,'250.00');assert.equal(after.workspace.Native_AP.remaining,'750.00');assert.equal(after.cash_delta,'-250.00');assert.equal(after.requests,1)
  assert.equal(after.payment.id,f.target);assert.equal(after.payment.status,'REVERSED');assert.equal(after.payment.payment_date,original.payment_date);assert.equal(after.payment.cash_account_id,original.cash_account_id);assert.equal(after.payment.journal.id,original.journal.id);assert.equal(after.payment.inverse.accounting_date,today)
  assert.equal(after.stock_HPP_unchanged,true)
  await openJournal(after.payment.inverse.id,after.payment.inverse.number);response=await observed(page,sourceResponse,()=>journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);resolved=await response.json();assert.equal(resolved.document.id,f.receipt.purchase_id);assert.deepEqual(resolved.document.focus,{kind:'SUPPLIER_PAYMENT',id:f.target,page_offset:25})
  await ui.expect(owningRow()).toContainText('Sudah dibalik');await ui.expect(owningRow().getByRole('button',{name:'Tinjau pembatalan '+original.number,exact:true})).toHaveCount(0);assert.deepEqual(state(),after)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);filename=`CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  return{status:'PASS',mobile,real_Auth_Native_journal_to_actual26th_payment_and_page25:true,full_Native_rows_unchanged_by_source_and_review:true,Native_AP1000_paid260_to250_remaining740_to750_cash260_to250:true,original_payment_date_cash_and_journal_preserved:true,inverse_journal_reopens_same_reversed_child:true,one_Native_inverse_one_request_no_stock_HPP_change:true,actual_committed_reply_loss_reload_identical_UUID_and_payload:!mobile,screenshots}
 }catch(e){let actual=null;try{actual=state()}catch(failure){actual={observation_error:String(failure)}}writeFileSync(`cp6-proof/t3/CP7_SOURCE_SUPPLIER_PAYMENT_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:actual,lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_SUPPLIER_PAYMENT_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
async function warehouseMenu(page,name){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()
}
async function qcSourceJourney(ui,today,mobile){
 const f=fixture('prepare-qc-source',{today}),user=await ui.login('OWNER',{label:'transaction-source-qc-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const state=()=>fixture('state-qc-source',{fixture:f}),sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),saveResponse=r=>r.url().endsWith('/rpc/erp_save_laundry_qc_action_v1')&&r.request().postDataJSON()?.p_action==='REVERSE_FINAL_SKU'
 const row=()=>page.locator(`[data-qc-inspection-id="${f.qc}"]`)
 const statusFits=()=>ui.expect.poll(()=>row().locator('header em').evaluate(el=>{
  const badge=el.getBoundingClientRect(),card=el.closest('article').getBoundingClientRect()
  return badge.left>=card.left&&badge.right<=card.right&&el.scrollWidth<=el.clientWidth+1
 })).toBe(true)
 let lost=null
 const openLedger=async()=>{
  await warehouseMenu(page,'• Kartu Stok FG');await page.getByLabel('Cari barang jadi',{exact:true}).fill(f.lot_number);await page.getByRole('checkbox',{name:'Sertakan stok habis',exact:true}).check();await page.getByRole('button',{name:'Cari stok',exact:true}).click()
  const position=page.locator('.cfg-position').filter({hasText:f.lot_number});await ui.expect(position).toHaveCount(1)
  const response=await observed(page,r=>r.url().endsWith('/rpc/erp_cp7_get_fg_ledger_v2')&&r.request().postDataJSON()?.p_query?.lot_id===f.lot,()=>position.getByRole('button',{name:/^Lihat mutasi /}).click());assert.equal(response.status(),200)
  const body=await response.json();assert.equal(body.position.product_id,f.product);assert.equal(body.position.lot_id,f.lot)
  const original=body.page.rows.find(m=>m.id===f.movement);assert.ok(original);assert.equal(original.source_type,'QC_ITEM');assert.equal(original.source_id,f.item)
  return body
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.lot_qty,'1');await openLedger();assert.deepEqual(state(),before)
  let response=await observed(page,sourceResponse,()=>page.locator(`[data-fg-movement-id="${f.movement}"]`).getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);let resolved=await response.json()
  assert.equal(resolved.business_DML,false);assert.equal(resolved.document.domain,'QC');assert.equal(resolved.document.route,'qc');assert.equal(resolved.document.id,f.qc);assert.equal(resolved.document.focus,null)
  await ui.expect(row()).toHaveAttribute('data-source-focus','true');await ui.expect(row()).toContainText(f.number);await ui.expect(row()).toContainText('Good 1 · BS 0');assert.deepEqual(state(),before)
  await statusFits()
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);let filename=`CP7_SOURCE_QC_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  await row().getByLabel('Alasan reversal '+f.number,{exact:true}).fill('Finalisasi salah setelah pemeriksaan fisik sumber QC');assert.deepEqual(state(),before)
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_save_laundry_qc_action_v1',async route=>{
    if(route.request().postDataJSON()?.p_action==='REVERSE_FINAL_SKU'&&!lost){const result=await route.fetch();assert.equal(result.status(),200);lost={envelope:route.request().postDataJSON(),body:await result.json()};await route.abort('failed')}
    else await route.continue()
   })
   await row().getByRole('button',{name:'Batalkan finalisasi',exact:true}).click();await ui.expect(page.getByRole('button',{name:'Reconcile UUID lama',exact:true})).toBeEnabled();assert.ok(lost)
   const committed=state();assert.equal(committed.inspection.status,'REVERSED');assert.equal(committed.inverse_movements.length,1)
   await page.reload()
   // This owning CP6 hook automatically reconciles its persisted envelope on
   // mount. Observe the actual replay before navigating; do not create a UUID.
   response=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_client_request_id===lost.envelope.p_client_request_id,()=>productionMenu(page,'• QC & Final SKU'))
   assert.equal(response.status(),200);assert.deepEqual(response.request().postDataJSON(),lost.envelope);assert.deepEqual(await response.json(),lost.body);assert.deepEqual(state(),committed)
   await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click();await page.getByPlaceholder('Cari PO, Potongan, receipt, atau histori…',{exact:true}).fill(f.number)
  }else{
   response=await observed(page,saveResponse,()=>row().getByRole('button',{name:'Batalkan finalisasi',exact:true}).click());assert.equal(response.status(),200);assert.equal(response.request().postDataJSON().p_payload.qc_inspection_id,f.qc)
  }
  await ui.expect(row()).toContainText('Dibatalkan');await ui.expect(row().getByRole('button',{name:'Batalkan finalisasi',exact:true})).toBeDisabled()
  const after=state();assert.equal(after.inspection.status,'REVERSED');assert.equal(after.lot_qty,'0');assert.deepEqual(after.items,before.items);assert.deepEqual(after.original_movements,before.original_movements);assert.equal(after.inverse_movements.length,1)
  const inverse=after.inverse_movements[0];assert.equal(inverse.reversal_of_id,f.movement);assert.equal(inverse.qty_signed,-1);assert.equal(inverse.source_type,'FG_MOVEMENT_REVERSAL');assert.equal(inverse.source_id,f.movement)
  const ledger=await openLedger();assert.equal(ledger.balances.physical_qty,'0');assert.equal(ledger.page.rows.find(m=>m.id===f.movement).physical_balance,'1');assert.equal(ledger.page.rows.find(m=>m.id===inverse.id).physical_balance,'0');assert.deepEqual(state(),after)
  response=await observed(page,sourceResponse,()=>page.locator(`[data-fg-movement-id="${inverse.id}"]`).getByRole('button',{name:'Buka transaksi asal',exact:true}).click());assert.equal(response.status(),200);resolved=await response.json();assert.equal(resolved.document.id,f.qc);assert.equal(resolved.document.status,'REVERSED')
  await ui.expect(row()).toHaveAttribute('data-source-focus','true');await ui.expect(row().getByRole('button',{name:'Batalkan finalisasi',exact:true})).toBeDisabled();assert.deepEqual(state(),after)
  await statusFits()
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);filename=`CP7_SOURCE_QC_INVERSE_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  return{status:'PASS',mobile,actual_Native_QC_GOOD_movement_to_exact_inspection_parent:true,source_and_own_reason_no_DML:true,unchanged_Native_owning_inverse_one_PCS_and_original_history:true,FG_inverse_link_reopens_same_reversed_QC:true,chronological_physical_balance1_then0:true,actual_committed_reply_loss_reload_identical_UUID_payload_and_version:!mobile,screenshots}
 }catch(e){let actual=null;try{actual=state()}catch(failure){actual={observation_error:String(failure)}}writeFileSync(`cp6-proof/t3/CP7_SOURCE_QC_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:actual,lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_QC_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
async function laundrySourceJourney(ui,today,mobile){
 const f=fixture('prepare-laundry-source',{today}),user=await ui.login('OWNER',{label:'transaction-source-laundry-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const state=()=>fixture('state-laundry-source',{fixture:f}),sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),saveResponse=r=>r.url().endsWith('/rpc/erp_save_laundry_qc_action_v1')&&r.request().postDataJSON()?.p_action==='REVERSE_RECEIPT'
 const row=()=>page.locator(`[data-laundry-receipt-id="${f.receipt}"]`)
 let lost=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.receipt.status,'POSTED');assert.equal(before.original_WIP.length,1);assert.equal(before.original_WIP[0].qty_pcs,30);assert.equal(before.inverse_WIP.length,0)
  await productionMenu(page,'• QC & Final SKU');await page.getByPlaceholder('Cari PO, Potongan, receipt, atau histori…',{exact:true}).fill(f.group_number)
  const sourceRow=page.locator(`[data-qc-source-receipt-id="${f.receipt}"]`);await ui.expect(sourceRow).toHaveCount(1);await ui.expect(sourceRow).toContainText(f.receipt_number)
  const response=await observed(page,sourceResponse,()=>sourceRow.getByRole('button',{name:'Buka penerimaan asal',exact:true}).click());assert.equal(response.status(),200);const resolved=await response.json()
  assert.equal(resolved.business_DML,false);assert.equal(resolved.document.domain,'LAUNDRY');assert.equal(resolved.document.route,'laundry');assert.equal(resolved.document.id,f.delivery);assert.equal(resolved.document.number,f.delivery_number)
  assert.deepEqual(resolved.document.focus,{kind:'LAUNDRY_RECEIPT',id:f.receipt,page_offset:0})
  await ui.expect(page.locator(`[data-laundry-delivery-id="${f.delivery}"]`)).toHaveAttribute('data-source-focus','true');await ui.expect(row()).toHaveAttribute('data-source-focus','true');await ui.expect(row()).toContainText(f.receipt_number)
  await ui.expect(row().getByRole('button',{name:'Batalkan penerimaan',exact:true})).toBeDisabled();assert.deepEqual(state(),before)
  await row().getByLabel('Alasan reversal '+f.receipt_number,{exact:true}).fill('Penerimaan salah setelah pemeriksaan fisik sumber Laundry');assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);let filename=`CP7_SOURCE_LAUNDRY_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  if(!mobile){
   await page.route('**/rest/v1/rpc/erp_save_laundry_qc_action_v1',async route=>{
    if(route.request().postDataJSON()?.p_action==='REVERSE_RECEIPT'&&!lost){const result=await route.fetch();assert.equal(result.status(),200);lost={envelope:route.request().postDataJSON(),body:await result.json()};await route.abort('failed')}
    else await route.continue()
   })
   await row().getByRole('button',{name:'Batalkan penerimaan',exact:true}).click();await ui.expect(page.getByRole('button',{name:'Reconcile UUID lama',exact:true})).toBeEnabled();assert.ok(lost)
   const committed=state();assert.equal(committed.receipt.status,'REVERSED');assert.equal(committed.inverse_WIP.length,1)
   await page.reload()
   const replay=await observed(page,r=>saveResponse(r)&&r.request().postDataJSON()?.p_client_request_id===lost.envelope.p_client_request_id,()=>productionMenu(page,'• Laundry'))
   assert.equal(replay.status(),200);assert.deepEqual(replay.request().postDataJSON(),lost.envelope);assert.deepEqual(await replay.json(),lost.body);assert.deepEqual(state(),committed)
   await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click();await page.getByPlaceholder('Cari PO, Potongan, atau vendor…',{exact:true}).fill(f.delivery_number)
  }else{
   const inverse=await observed(page,saveResponse,()=>row().getByRole('button',{name:'Batalkan penerimaan',exact:true}).click());assert.equal(inverse.status(),200);assert.equal(inverse.request().postDataJSON().p_payload.receipt_id,f.receipt)
  }
  await ui.expect(row()).toContainText('Dibatalkan');await ui.expect(row().getByRole('button',{name:'Batalkan penerimaan',exact:true})).toBeDisabled()
  const after=state();assert.equal(after.receipt.status,'REVERSED');assert.deepEqual(after.receipt_lines,before.receipt_lines);assert.deepEqual(after.receipt_sizes,before.receipt_sizes);assert.deepEqual(after.original_WIP,before.original_WIP);assert.equal(after.inverse_WIP.length,1)
  const inverse=after.inverse_WIP[0];assert.equal(inverse.source_id,before.original_WIP[0].id);assert.equal(inverse.qty_pcs,30);assert.equal(inverse.stage_from,'QC');assert.equal(inverse.stage_to,'LAUNDRY')
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);filename=`CP7_SOURCE_LAUNDRY_INVERSE_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  return{status:'PASS',mobile,actual_QC_queue_to_exact_Laundry_delivery_and_receipt:true,source_open_and_own_reason_no_business_DML:true,unchanged_Native_inverse_exact30_PCS_WIP_and_original_lines:true,actual_committed_reply_loss_reload_identical_UUID_payload_and_version:!mobile,screenshots}
 }catch(e){let actual=null;try{actual=state()}catch(failure){actual={observation_error:String(failure)}}writeFileSync(`cp6-proof/t3/CP7_SOURCE_LAUNDRY_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:actual,lost},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_LAUNDRY_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
async function laundryDependencyJourney(ui,today,mobile){
 const f=fixture('prepare-laundry-dependencies',{today}),user=await ui.login('OWNER',{label:'transaction-laundry-QC-dependency-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',screenshots=[]
 const state=()=>fixture('state-laundry-dependencies',{fixture:f}),receipt=()=>page.locator(`[data-laundry-receipt-id="${f.receipt}"]`),qc=()=>page.locator(`[data-qc-inspection-id="${f.qc}"]`)
 const sourceResponse=r=>r.url().endsWith('/rpc/erp_cp7_resolve_transaction_source_v1'),dependencyResponse=r=>r.url().endsWith('/rpc/erp_cp7_get_transaction_dependencies_v1')
 const saveResponse=action=>r=>r.url().endsWith('/rpc/erp_save_laundry_qc_action_v1')&&r.request().postDataJSON()?.p_action===action
 const openReceipt=async()=>{
  await page.getByRole('button',{name:'Antrean finalisasi',exact:true}).click()
  await page.getByPlaceholder('Cari PO, Potongan, receipt, atau histori…',{exact:true}).fill(f.group_number)
  const source=page.locator(`[data-qc-source-receipt-id="${f.receipt}"]`);await ui.expect(source).toHaveCount(1)
  const r=await observed(page,sourceResponse,()=>source.getByRole('button',{name:'Buka penerimaan asal',exact:true}).click())
  assert.equal(r.status(),200);const d=(await r.json()).document;assert.equal(d.id,f.delivery);assert.equal(d.focus.id,f.receipt)
  await ui.expect(receipt()).toHaveAttribute('data-source-focus','true')
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.qc.lot_qty,'1');assert.equal(before.qc.inspection.status,'POSTED')
  await productionMenu(page,'• QC & Final SKU');await openReceipt()
  await ui.expect(receipt()).toContainText('QC');await ui.expect(receipt().getByRole('button',{name:'Batalkan penerimaan',exact:true})).toBeDisabled()
  let r=await observed(page,dependencyResponse,()=>receipt().getByRole('button',{name:'Lihat QC terkait',exact:true}).click())
  assert.equal(r.status(),200);const d=await r.json();assert.equal(d.business_DML,false);assert.equal(d.parent.id,f.receipt);assert.deepEqual(d.page,{offset:0,limit:25,total:1,has_more:false});assert.equal(d.dependencies[0].source_id,f.qc)
  const related=receipt().locator(`[data-laundry-qc-dependency-id="${f.qc}"]`);await ui.expect(related).toContainText(f.qc_number);assert.deepEqual(state(),before)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  let filename=`CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  r=await observed(page,sourceResponse,()=>related.getByRole('button',{name:'Buka QC terkait',exact:true}).click())
  assert.equal(r.status(),200);const target=(await r.json()).document;assert.equal(target.domain,'QC');assert.equal(target.id,f.qc);assert.equal(target.number,f.qc_number)
  await ui.expect(qc()).toHaveAttribute('data-source-focus','true');await ui.expect(qc()).toContainText(f.qc_number);assert.deepEqual(state(),before)
  await qc().getByLabel('Alasan reversal '+f.qc_number,{exact:true}).fill('Hasil QC salah setelah sumber penerimaan diperiksa')
  r=await observed(page,saveResponse('REVERSE_FINAL_SKU'),()=>qc().getByRole('button',{name:'Batalkan finalisasi',exact:true}).click())
  assert.equal(r.status(),200);assert.equal(r.request().postDataJSON().p_payload.qc_inspection_id,f.qc)
  await ui.expect(qc().getByRole('button',{name:'Batalkan finalisasi',exact:true})).toBeDisabled()
  const corrected=state();assert.equal(corrected.qc.inspection.status,'REVERSED');assert.equal(corrected.qc.lot_qty,'0');assert.deepEqual(corrected.qc.items,before.qc.items);assert.deepEqual(corrected.qc.original_movements,before.qc.original_movements);assert.equal(corrected.qc.inverse_movements.length,1)
  await openReceipt();await ui.expect(receipt().locator('.clq-dependencies')).toHaveCount(0);assert.deepEqual(state(),corrected)
  await receipt().getByLabel('Alasan reversal '+f.receipt_number,{exact:true}).fill('Penerimaan salah setelah pembatalan QC terkait selesai')
  r=await observed(page,saveResponse('REVERSE_RECEIPT'),()=>receipt().getByRole('button',{name:'Batalkan penerimaan',exact:true}).click())
  assert.equal(r.status(),200);assert.equal(r.request().postDataJSON().p_payload.receipt_id,f.receipt)
  await ui.expect(receipt().getByRole('button',{name:'Batalkan penerimaan',exact:true})).toBeDisabled()
  const after=state();assert.equal(after.laundry.receipt.status,'REVERSED');assert.deepEqual(after.laundry.receipt_lines,before.laundry.receipt_lines);assert.deepEqual(after.laundry.receipt_sizes,before.laundry.receipt_sizes);assert.deepEqual(after.laundry.original_WIP,before.laundry.original_WIP);assert.equal(after.laundry.inverse_WIP.length,1);assert.equal(after.qc.inverse_movements.length,1);assert.equal(after.qc.lot_qty,'0')
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  filename=`CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_INVERSE_${suffix}.png`;await page.screenshot({path:'cp6-proof/t3/'+filename,fullPage:true});screenshots.push(filename)
  return{status:'PASS',mobile,actual_blocked_receipt_lists_exact_QC_FK_no_DML:true,current_QC_target_rechecked_by_owning_reader:true,explicit_owning_QC_then_receipt_inverses_with_original_history:true,one_PCS_FG_and30_PCS_receipt_WIP_inverses_once:true,two_Native_commands_not_claimed_one_atomic_chain:true,screenshots}
 }catch(e){let actual=null;try{actual=state()}catch(failure){actual={observation_error:String(failure)}}writeFileSync(`cp6-proof/t3/CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:actual},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['CP7_SOURCE_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_SOURCE_BROWSER_MOBILE',()=>journey(ui,today,true)],['CP7_SOURCE_PAYROLL_BROWSER_DESKTOP',()=>payrollJourney(ui,today,false)],['CP7_SOURCE_PAYROLL_BROWSER_MOBILE',()=>payrollJourney(ui,today,true)],['CP7_SOURCE_ACCESSORY_BROWSER_DESKTOP',()=>accessoryJourney(ui,today,false)],['CP7_SOURCE_ACCESSORY_BROWSER_MOBILE',()=>accessoryJourney(ui,today,true)],['CP7_SOURCE_REWORK_BROWSER_DESKTOP',()=>reworkJourney(ui,today,false)],['CP7_SOURCE_REWORK_BROWSER_MOBILE',()=>reworkJourney(ui,today,true)],['CP7_PRODUCTION_READ_BROWSER_DESKTOP',()=>productionReadJourney(ui,today,false)],['CP7_PRODUCTION_READ_BROWSER_MOBILE',()=>productionReadJourney(ui,today,true)],['CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_DESKTOP',()=>supplierPaymentJourney(ui,today,false)],['CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_MOBILE',()=>supplierPaymentJourney(ui,today,true)],['CP7_SOURCE_QC_BROWSER_DESKTOP',()=>qcSourceJourney(ui,today,false)],['CP7_SOURCE_QC_BROWSER_MOBILE',()=>qcSourceJourney(ui,today,true)],['CP7_SOURCE_LAUNDRY_BROWSER_DESKTOP',()=>laundrySourceJourney(ui,today,false)],['CP7_SOURCE_LAUNDRY_BROWSER_MOBILE',()=>laundrySourceJourney(ui,today,true)],['CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_BROWSER_DESKTOP',()=>laundryDependencyJourney(ui,today,false)],['CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_BROWSER_MOBILE',()=>laundryDependencyJourney(ui,today,true)]]}
