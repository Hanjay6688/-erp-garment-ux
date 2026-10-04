import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_payment_correction_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const endpoint='**/rest/v1/rpc/erp_cp7_correct_sales_payment_v1'
async function observed(page,button){
 const result=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_correct_sales_payment_v1')).then(response=>({response}),error=>({error}))
 await button.click();const r=await result;if(r.error)throw r.error;return r.response
}
async function salesMenu(page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Pembayaran Pelanggan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click();await link.click()
}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'payment-correction-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',requests=[]
 const state=()=>fixture('state',{fixture:f.fixture})
 page.on('request',r=>{if(/\/rpc\/erp_cp7_(?:correct_sales_payment|save_sale)_v1$/.test(r.url()))requests.push({url:r.url(),body:r.postDataJSON()})})
 const panel=()=>page.getByRole('region',{name:'Pembayaran invoice',exact:true})
 const row=id=>panel().locator(`[data-payment-id="${id}"]`)
 async function openPayments(){await page.getByRole('button',{name:'Pembayaran invoice',exact:true}).click();await ui.expect(panel()).toBeVisible()}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await salesMenu(page)
  await page.getByLabel('Cari invoice',{exact:true}).fill(f.document.number);await page.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await page.locator('[aria-label="Daftar invoice"] .cproc-receipt').filter({hasText:f.document.number}).click();await openPayments()
  await row(f.payment.id).getByRole('button',{name:`Edit pembayaran ${f.payment.number}`,exact:true}).click()
  const form=page.getByRole('form',{name:'Edit pembayaran pelanggan',exact:true})
  await ui.expect(form.getByLabel('Nominal koreksi pembayaran',{exact:true})).toHaveValue('30.01')
  await form.getByLabel('Nominal koreksi pembayaran',{exact:true}).fill('20.01');await form.getByLabel('Alasan koreksi pembayaran',{exact:true}).fill('Pembayaran salah nominal diperbaiki setelah pemeriksaan lapangan');await form.getByLabel('Koreksi pembayaran sudah diperiksa',{exact:true}).check()
  let first
  if(!mobile){
   let intercepted
   await page.route(endpoint,async route=>{try{const r=await route.fetch(),status=r.status();if(status===200){first=await r.json();await route.abort('failed')}else await route.fulfill({response:r});intercepted={status}}catch(error){intercepted={status:null,error:String(error)};await route.abort('failed').catch(()=>{})}})
   await form.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}).click();await ui.expect.poll(()=>intercepted!==undefined).toBe(true);assert.equal(intercepted.status,200,JSON.stringify(intercepted))
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();assert.equal(state().cash_received,'20.01');assert.equal(state().chain.length,1)
   const originalRequest=structuredClone(requests[0].body);await page.unroute(endpoint);await page.reload();await salesMenu(page)
   const r=await observed(page,page.getByRole('button',{name:'Reconcile transaksi',exact:true}));assert.equal(r.status(),200);assert.deepEqual(await r.json(),first);assert.deepEqual(requests[1].body,originalRequest)
  }else{const r=await observed(page,form.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}));assert.equal(r.status(),200);first=await r.json()}
  await ui.expect(page.getByRole('complementary',{name:'Rincian invoice',exact:true})).toContainText('Rp20,01')
  const after=state();assert.equal(after.original.amount,'30.01');assert.equal(after.original.status,'REVERSED');assert.equal(after.current.amount,'20.01');assert.equal(after.current.physical_at,f.payment.physical_at);assert.match(after.current.physical_at,/123456/);assert.equal(after.stock_HPP_unchanged,true);assert.equal(after.original_posting_fact_unchanged,true)
  await openPayments();await row(first.payment_id).getByRole('button',{name:`Lihat perubahan pembayaran ${after.current.number}`,exact:true}).click()
  const history=page.getByRole('region',{name:'Koreksi pembayaran tercatat',exact:true});await ui.expect(history.getByRole('region',{name:'Pembayaran sebelum koreksi',exact:true})).toContainText(f.payment.number)
  // The real resolver opens the exact old child; its current Native parent
  // revision/page is re-read. No caller supplies a guessed page or revision.
  await history.getByRole('button',{name:'Buka pembayaran sebelum koreksi',exact:true}).click()
  await ui.expect(panel().locator('[data-source-selected="true"]')).toHaveCount(1);await ui.expect(row(f.payment.id)).toHaveAttribute('data-source-selected','true')
  await row(f.payment.id).getByRole('button',{name:`Lihat perubahan pembayaran ${f.payment.number}`,exact:true}).click()
  await ui.expect(history.getByRole('region',{name:'Pembayaran pengganti',exact:true})).toContainText(after.current.number)
  await history.getByRole('button',{name:'Buka pembayaran pengganti',exact:true}).click();await ui.expect(row(first.payment_id)).toHaveAttribute('data-source-selected','true')
  await row(first.payment_id).getByRole('button',{name:`Lihat perubahan pembayaran ${after.current.number}`,exact:true}).click()
  await history.getByRole('button',{name:'Pulihkan isi pembayaran sebelum koreksi',exact:true}).click();await ui.expect(form.getByLabel('Nominal koreksi pembayaran',{exact:true})).toHaveValue('30.01')
  await form.getByLabel('Alasan koreksi pembayaran',{exact:true}).fill('Isi pembayaran sebelum koreksi dipulihkan setelah pemeriksaan ulang');await form.getByLabel('Koreksi pembayaran sudah diperiksa',{exact:true}).check()
  const result=await observed(page,form.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}));assert.equal(result.status(),200);const second=await result.json()
  await ui.expect(page.getByRole('complementary',{name:'Rincian invoice',exact:true})).toContainText('Rp30,01')
  const final=state();assert.equal(final.chain.length,2);assert.equal(final.current.id,second.payment_id);assert.equal(final.current.amount,'30.01');assert.equal(final.cash_received,'30.01');assert.equal(final.current.physical_at,f.payment.physical_at);assert.equal(final.stock_HPP_unchanged,true);assert.equal(final.original_posting_fact_unchanged,true)
  assert.equal(requests.length,mobile?2:3);assert.equal(requests.filter(r=>r.url.endsWith('/erp_cp7_save_sale_v1')).length,0)
  await openPayments();await row(second.payment_id).getByRole('button',{name:`Lihat perubahan pembayaran ${final.current.number}`,exact:true}).click();await ui.expect(history).toContainText('Rp20,01')
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_PAYMENT_CORRECTION_${suffix}.png`,fullPage:true})
  return{status:'PASS',mobile,actual_Auth_original30_01_new20_01_restore30_01:true,single_backend_command_each:true,actual_lost_committed_reply_exact_UUID_recovery:!mobile,actual_exact_original_replacement_source_focus:true,immutable_two_link_history:true,Native_microseconds_and_stock_HPP_preserved:true,screenshot:`CP7_PAYMENT_CORRECTION_${suffix}.png`}
 }catch(error){writeFileSync(`cp6-proof/t3/CP7_PAYMENT_CORRECTION_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),requests},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_PAYMENT_CORRECTION_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await page.unroute(endpoint).catch(()=>{});await user.context.close()}
}
export function cases(ui,today){return[['CP7_PAYMENT_CORRECTION_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_PAYMENT_CORRECTION_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
