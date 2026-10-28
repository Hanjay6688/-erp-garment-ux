// Actual unknown-price posting and one-time pricing, using the existing host.
import assert from 'node:assert/strict'
import {execFileSync}from 'node:child_process'
import {mkdirSync,writeFileSync}from 'node:fs'
import {dirname,resolve}from 'node:path'
import {fileURLToPath}from 'node:url'
import {readable}from '../current-vendor-money-browser/visual.mjs'
import {observeConsole,requireConsoleEvidence}from '../current-finance-combined-browser-qualification/console_evidence.mjs'
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const fixture=(op,p)=>JSON.parse(execFileSync('python',['-B',resolve(ROOT,'scripts/current-ow08-source-browser/wash_fixture.py'),op],{input:JSON.stringify(p),cwd:ROOT,encoding:'utf8',maxBuffer:8*1024*1024}).trim())
const cents=v=>{assert.match(v,/^-?\d+\.\d{2}$/);return BigInt(v.replace('.',''))}
export const IDS=['OW08_UNKNOWN_WASH_SCREEN_PRICE_DESKTOP','OW08_UNKNOWN_WASH_SCREEN_PRICE_MOBILE']
async function laundry(ui,page){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Laundry',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Laundry',exact:true})).toBeVisible()
}
async function pricePage(ui,page,f){
 await page.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
 await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
 await page.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.fixture.vendor)
 await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
 await page.getByRole('button',{name:'Harga belum diketahui',exact:true}).click()
 return page.getByRole('region',{name:'Cuci gagal harga belum diketahui',exact:true})
}
async function journey(ui,today,mobile){
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'ow08-wash-'+mobile,mobile}),page=user.page,observed=observeConsole(page)
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[],contrasts=[],writes=[];let f,response,unknown,priced
 const state=()=>fixture('state',{...f,response})
 const shot=async(label,box)=>{mkdirSync('cp6-proof/t3',{recursive:true});await box.scrollIntoViewIfNeeded();for(const[scope,target]of[['PAGE',page],['FOCUS',box]]){const path=`cp6-proof/t3/OW08_WASH_${suffix}_${label}_${scope}.png`;await target.screenshot({path,...(scope==='PAGE'?{fullPage:true}:{})});shots.push(path)}}
 try{
  f=fixture('prepare',{today});await laundry(ui,page)
  await page.getByPlaceholder('Cari PO, Potongan, atau vendor…',{exact:true}).fill(f.number)
  await page.getByRole('button',{name:'Cuci gagal berbayar',exact:true}).click()
  const form=page.locator('section.clq-panel').filter({has:page.getByRole('heading',{name:'Catat attempt yang benar-benar ditagih vendor',exact:true})})
  await form.getByLabel('SURAT KIRIM GAGAL CUCI',{exact:true}).selectOption(f.fixture.delivery)
  await form.getByLabel('PROSES GAGAL CUCI',{exact:true}).selectOption(f.fixture.failed)
  await form.getByLabel('POSISI FISIK GAGAL CUCI',{exact:true}).selectOption('RETRY_AT_VENDOR')
  await form.getByLabel('WAKTU GAGAL CUCI',{exact:true}).fill(f.physical_local)
  await form.getByRole('button',{name:'Isi seluruh yang di vendor',exact:true}).click()
  await form.getByLabel('ALASAN TAGIHAN GAGAL CUCI',{exact:true}).fill('Tagihan jasa gagal nyata, tarif vendor menyusul')
  await form.getByLabel('Tarif vendor belum diketahui',{exact:true}).check()
  await form.getByRole('checkbox',{name:/Saya sudah mencocokkan bukti tagihan/}).check()
  await ui.expect(form).toContainText('biaya belum dihitung, bukan nol')
  const rpc=page.waitForResponse(r=>r.url().endsWith('/rest/v1/rpc/erp_save_laundry_qc_action_v1')&&r.request().postDataJSON()?.p_action==='POST_FAILED_WASH')
  await form.getByRole('button',{name:'Post jasa gagal cuci atomic',exact:true}).click()
  const saved=await rpc;assert.equal(saved.status(),200,await saved.text());response=await saved.json();writes.push({request:saved.request().postDataJSON(),response})
  assert.equal(response.cost_status,'PRICE_UNKNOWN');assert.equal(response.rate_per_pcs,null);assert.equal(response.actual_cost,null)
  assert.equal(response.hpp_effect,'FAILED_WASH_COST_UNKNOWN_HPP_NOT_FINAL')
  unknown=state();assert.deepEqual(unknown.line,[null,null,'PENDING']);assert.deepEqual(unknown.money,f.money_before)
  assert.equal(unknown.own_close_blockers.length,1);assert.equal(unknown.price_rows.length,1);assert.equal(unknown.price_rows[0][0],'UNKNOWN')
  let box=await pricePage(ui,page,f)
  let row=box.getByRole('row').filter({hasText:unknown.receipt_number});await ui.expect(row).toHaveCount(1)
  await ui.expect(row).toContainText('Belum diketahui · biaya belum dihitung · HPP belum final')
  contrasts.push({state:'UNKNOWN',rows:await readable(box)});await shot('UNKNOWN',box)
  await box.getByLabel('Alasan harga cuci gagal',{exact:true}).fill('Invoice vendor memastikan tarif tiga rupiah per PCS')
  await box.getByLabel('Harga per PCS cuci gagal '+unknown.receipt_number,{exact:true}).fill('3,00')
  const priceRPC=page.waitForResponse(r=>r.url().endsWith('/rest/v1/rpc/erp_save_laundry_bd_action_v1')&&r.request().postDataJSON()?.p_action==='SET_FAILED_WASH_PRICE')
  await box.getByRole('button',{name:'Isi harga cuci gagal '+unknown.receipt_number,exact:true}).click()
  const savedPrice=await priceRPC;assert.equal(savedPrice.status(),200,await savedPrice.text());const result=await savedPrice.json();writes.push({request:savedPrice.request().postDataJSON(),response:result})
  assert.equal(result.actual_cost,'30.00');assert.equal(result.rate_per_pcs,'3.00');assert.equal(result.economic_date,f.fixture.day)
  await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
  priced=state();assert.deepEqual(priced.line,['3.00','30.00','ESTIMATED']);assert.deepEqual(priced.physical,unknown.physical)
  assert.equal(cents(priced.money.desired)-cents(unknown.money.desired),3000n);assert.equal(cents(priced.money.accrued)-cents(unknown.money.accrued),3000n)
  assert.equal(priced.own_close_blockers.length,0);assert.equal(priced.price_rows.length,1);assert.equal(priced.price_rows[0][0],'KNOWN');assert.equal(priced.price_rows[0][3],true);assert.equal(priced.price_rows[0][4],true)
  await page.reload();await laundry(ui,page);box=await pricePage(ui,page,f)
  row=box.getByRole('row').filter({hasText:unknown.receipt_number});await ui.expect(row).toHaveCount(1);await ui.expect(row).toContainText('biaya Rp 30,00')
  await ui.expect(box.getByRole('button',{name:'Isi harga cuci gagal '+unknown.receipt_number,exact:true})).toHaveCount(0)
  assert.deepEqual(state(),priced,'Reload is read-only and cannot price twice')
  contrasts.push({state:'PRICED_REOPEN',rows:await readable(box)});await shot('PRICED_REOPEN',box)
  const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));assert.ok(width.page<=width.viewport)
  return{status:'PASS',actual_screen_failed_attempt_unknown:true,unknown_is_not_zero:true,actual_screen_price_once:true,physical_unchanged_by_price:true,
   own_period_blocker_removed_after_price:true,full_period_close_claim:false,actual_existing_finished_lot_recost_claim:false,
   writes,unknown,priced,visible_text_contrasts:contrasts,shots,width,console_evidence:requireConsoleEvidence(observed.errors,[]),production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/OW08_WASH_${suffix}_FIRST_FAILURE.json`,JSON.stringify({error:String(error),writes,unknown,priced,fixture:f,console:observed.errors},null,2));await page.screenshot({path:`cp6-proof/t3/OW08_WASH_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{observed.stop();await user.context.close()}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>journey(ui,today,Boolean(i))])}
