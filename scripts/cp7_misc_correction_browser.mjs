import assert from'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_misc_correction_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const endpoint='**/rest/v1/rpc/erp_cp7_correct_misc_finance_v1'
async function journalMenu(page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Jurnal & Transaksi Lain',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'misc-correction-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 const state=()=>fixture('state',{fixture:f.fixture,transaction_id:f.transaction_id}),requests=[]
 page.on('request',r=>{if(/\/rpc\/erp_cp7_(?:correct_misc_finance|save_misc_finance)_v1$/.test(r.url()))requests.push({url:r.url(),body:r.postDataJSON()})})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await journalMenu(page)
  const journal=page.getByRole('main',{name:'Jurnal keuangan dari buku',exact:true})
  await journal.getByLabel('Periode jurnal dari',{exact:true}).fill(f.fixture.physical.slice(0,10));await journal.getByLabel('Periode jurnal sampai',{exact:true}).fill(today)
  await journal.getByLabel('Cari sumber jurnal',{exact:true}).fill(f.document.journals[0].number);await journal.getByRole('button',{name:'Tampilkan jurnal',exact:true}).click()
  await ui.expect(journal.locator(`[data-journal-id="${f.journal_id}"]`)).toBeVisible();await journal.locator(`[data-journal-id="${f.journal_id}"]`).click();await journal.getByRole('button',{name:'Buka transaksi asal',exact:true}).click()
  const detail=page.getByRole('complementary',{name:'Rincian transaksi lain',exact:true});await ui.expect(detail).toContainText(f.document.number);assert.equal(state().cash_delta,'-12.34')
  await page.getByRole('button',{name:'Koreksi transaksi tercatat',exact:true}).click()
  const form=page.getByRole('form',{name:'Koreksi pendapatan atau biaya lain',exact:true})
  await form.getByLabel('Nominal transaksi lain',{exact:true}).fill('9.99');await form.getByLabel('Alasan simpan transaksi lain',{exact:true}).fill('Nominal sumber diperbaiki setelah diperiksa di lapangan');await form.getByLabel('Koreksi transaksi lain sudah diperiksa',{exact:true}).check()
  let first
  if(!mobile){
   // Let the actual server commit, then drop only its reply. No fake outcome.
   await page.route(endpoint,async route=>{const response=await route.fetch();assert.equal(response.status(),200);first=await response.json();await route.abort('failed')})
   await form.getByRole('button',{name:'Simpan koreksi transaksi lain',exact:true}).click()
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();assert.equal(state().cash_delta,'-9.99');assert.equal(state().chain.length,1)
   const originalRequest=structuredClone(requests[0].body);await page.unroute(endpoint);await page.reload();await journalMenu(page)
   const replay=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_correct_misc_finance_v1'));await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();const response=await replay;assert.equal(response.status(),200);assert.deepEqual(await response.json(),first);assert.deepEqual(requests[1].body,originalRequest)
  }else{
   const response=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_correct_misc_finance_v1'));await form.getByRole('button',{name:'Simpan koreksi transaksi lain',exact:true}).click();const r=await response;assert.equal(r.status(),200);first=await r.json()
  }
  await ui.expect(detail).toContainText(first.document.number);await ui.expect(detail).toContainText('Rp9,99');assert.equal(first.document.physical_at,f.document.physical_at);assert.match(first.document.physical_at,/123456/)
  const after=state();assert.equal(after.original.status,'REVERSED');assert.equal(after.original.amount,'12.34');assert.equal(after.cash_delta,'-9.99');assert.equal(after.chain.length,1);assert.equal(after.stock_HPP_unchanged,true)
  await page.getByRole('button',{name:'Buka dokumen sebelum koreksi',exact:true}).click();await ui.expect(detail).toContainText(f.document.number);await ui.expect(detail).toContainText('Transaksi ini sudah diganti melalui koreksi')
  await page.getByRole('button',{name:'Buka dokumen pengganti',exact:true}).click();await ui.expect(detail).toContainText(first.document.number)
  // Rollback uses another reviewed atomic correction, keeping both histories.
  await page.getByRole('button',{name:'Pulihkan nilai sebelum koreksi',exact:true}).click();await ui.expect(form.getByLabel('Nominal transaksi lain',{exact:true})).toHaveValue('12.34')
  await form.getByLabel('Alasan simpan transaksi lain',{exact:true}).fill('Nilai sebelum koreksi dipulihkan setelah pemeriksaan ulang');await form.getByLabel('Koreksi transaksi lain sudah diperiksa',{exact:true}).check()
  const restored=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_correct_misc_finance_v1'));await form.getByRole('button',{name:'Simpan koreksi transaksi lain',exact:true}).click();const response=await restored;assert.equal(response.status(),200);const result=await response.json();await ui.expect(detail).toContainText(result.document.number)
  const final=state();assert.equal(final.chain.length,2);assert.equal(final.current.amount,'12.34');assert.equal(final.cash_delta,'-12.34');assert.equal(final.current.physical_at,f.document.physical_at);assert.equal(final.stock_HPP_unchanged,true)
  assert.equal(requests.length,mobile?2:3);assert.equal(requests.filter(r=>r.url.endsWith('/erp_cp7_save_misc_finance_v1')).length,0)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_MISC_CORRECTION_${suffix}.png`,fullPage:true})
  return{status:'PASS',mobile,real_Auth_exact_source_to_atomic_posted_edit:true,original12_34_new9_99_then_prior12_34_restored:true,single_backend_command_each_no_browser_writer_chain:true,actual_lost_committed_reply_exact_UUID_recovery:!mobile,two_immutable_linked_corrections:true,microseconds_and_stock_HPP_preserved:true,screenshot:`CP7_MISC_CORRECTION_${suffix}.png`}
 }catch(e){writeFileSync(`cp6-proof/t3/CP7_MISC_CORRECTION_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),stack:e.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),requests},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_MISC_CORRECTION_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{await page.unroute(endpoint).catch(()=>{});await user.context.close()}
}
export function cases(ui,today){return[['CP7_MISC_CORRECTION_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_MISC_CORRECTION_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
