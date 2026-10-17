// R3-03 (owner D16-1): Riwayat Pelanggan on real data, desktop and phone, real Auth and PostgREST on the committed copy.
// The fixture is the native cases' one (scripts/cp7_r3_history_cases.py browser_fixture): an invoice of Rp80 (4 pcs) paid
// Rp30, a return of 1 pc for Rp20, and a second draft of the customer cancelled. As OWNER the screen finds the customer,
// shows exactly those five events newest first with their amounts, the invoice balance Rp30 and the customer's open
// balance Rp30, and downloads only the rows it shows. As SALES_KASIR (sales.history.view without finance.ar.view and
// without sales.history.export) it shows the same five events with no amount and no download. Nothing is written: the
// Native rows and the audit rows about these documents are read before and after (fixture r303_history_state).
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
async function historyPage(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Riwayat Pelanggan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click();await link.click()
 await ui.expect(page.locator('.chistory').getByRole('heading',{name:'Riwayat Pelanggan',exact:true})).toBeVisible()
}
async function openCustomer(ui,page,f){
 await historyPage(ui,page)
 await page.getByLabel('Cari pelanggan riwayat',{exact:true}).fill(f.tag);await page.getByRole('button',{name:'Cari pelanggan',exact:true}).click()
 const row=page.locator(`[data-customer-id="${f.customer}"]`);await ui.expect(row).toHaveCount(1)
 await ui.expect(row).toContainText('2 invoice · 1 pembayaran · 1 retur · 1 pembatalan')
 await row.click()
 const list=page.getByRole('list',{name:'Riwayat '+f.name,exact:true});await ui.expect(list.locator('li')).toHaveCount(5)
 return{row,list}
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_03_HISTORY_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r303_history',{today}),requests=[],seen={}
 const state=()=>h.fixture('r303_history_state',f)
 const owner=await ui.login('OWNER',{label:'cp17-r3-03-'+(mobile?'mobile':'desktop'),mobile});let kasir=null,page=owner.page
 const watch=p=>p.on('request',r=>{const u=r.url();if(u.includes('/rest/v1/rpc/'))requests.push({rpc:u.split('/rpc/')[1],body:r.postDataJSON()})})
 watch(page)
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.deepEqual(before.events.map(e=>e[0]),['CANCELLATION','RETURN','PAYMENT','INVOICE','INVOICE'])
  assert.equal(before.totals.open,'30.00')
  const{row,list}=await openCustomer(ui,page,f)
  await ui.expect(row).toContainText('Sisa tagihan');await ui.expect(row).toContainText('Rp30')
  const items=list.locator('li')
  // Exactly the five events, newest first, with the Native numbers.
  await ui.expect(items.nth(0)).toContainText(`Draf invoice ${f.draft} dibatalkan`);await ui.expect(items.nth(0)).toContainText('Rp40')
  await ui.expect(items.nth(1)).toContainText(`Retur ${f.ret}`);await ui.expect(items.nth(1)).toContainText('1 pcs dari invoice '+f.invoice);await ui.expect(items.nth(1)).toContainText('Rp20')
  await ui.expect(items.nth(2)).toContainText(`Pembayaran ${f.payment}`);await ui.expect(items.nth(2)).toContainText('Rp30')
  await ui.expect(items.nth(3)).toContainText(`Draf invoice ${f.draft}`);await ui.expect(items.nth(3)).toContainText('bukan piutang aktif')
  await ui.expect(items.nth(4)).toContainText(`Invoice ${f.invoice}`);await ui.expect(items.nth(4)).toContainText('Dibayar sebagian')
  await ui.expect(items.nth(4)).toContainText('nilai Rp80 · retur Rp20 · dibayar Rp30 · sisa tagihan Rp30')
  for(let n=0;n<5;n++)await ui.expect(items.nth(n).locator('time')).toContainText('WIB')
  const totals=page.locator(`[aria-label="Ringkasan uang ${f.name}"]`)
  for(const t of['Nilai invoice aktifRp80','Retur tercatatRp20','Pembayaran tercatatRp30','Sisa tagihanRp30'])await ui.expect(totals).toContainText(t)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_OWNER.png`,fullPage:true})
  // The download holds the rows on screen only (captured from the Blob the page hands to the browser).
  await page.evaluate(()=>{const make=URL.createObjectURL.bind(URL);window.__cp17Exports=[];URL.createObjectURL=b=>{b.text().then(t=>window.__cp17Exports.push(t));return make(b)}})
  await page.getByRole('button',{name:'Unduh riwayat yang tampil (CSV)',exact:true}).click()
  await ui.expect(page.getByText('5 baris yang tampil (kejadian 1–5) sudah diunduh.')).toBeVisible()
  await ui.expect.poll(()=>page.evaluate(()=>window.__cp17Exports.length)).toBe(1)
  const csv=await page.evaluate(()=>window.__cp17Exports[0]),lines=csv.trim().split('\r\n')
  assert.equal(lines.length,6,csv);assert.ok(lines[0].includes('"Nilai (Rp)"'),lines[0])
  assert.deepEqual(lines.slice(1).map(l=>l.split('","')[3]),f.events.map(e=>e[2]),csv)
  assert.ok(lines[3].includes('"30.00"')&&lines[2].includes('"20.00"')&&lines[5].includes('"80.00"'),csv)
  const after=seen.owner=state();assert.deepEqual(after,before)
  // SALES_KASIR: the same events, no amount, no download.
  kasir=await ui.login('SALES_KASIR',{label:'cp17-r3-03-kasir-'+(mobile?'mobile':'desktop'),mobile});page=kasir.page;watch(page)
  const k=await openCustomer(ui,page,f)
  await ui.expect(page.locator('.chistory')).toContainText('Nilai uang tidak ditampilkan')
  for(let n=0;n<5;n++)await ui.expect(k.list.locator('li').nth(n)).toContainText(['Draf invoice '+f.draft+' dibatalkan','Retur '+f.ret,'Pembayaran '+f.payment,'Draf invoice '+f.draft,'Invoice '+f.invoice][n])
  assert.equal((await page.locator('.chistory').innerText()).includes('Rp'),false)
  await ui.expect(page.getByRole('button',{name:'Unduh riwayat yang tampil (CSV)',exact:true})).toHaveCount(0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_SALES_KASIR.png`,fullPage:true})
  assert.deepEqual(seen.kasir=state(),before)
  // Reads only: four history reads (owner list + customer, cashier list + customer) and no writer of any kind.
  assert.ok(requests.filter(r=>r.rpc==='erp_cp7_get_customer_history_v1').length>=4,JSON.stringify(requests))
  assert.ok(requests.every(r=>/^erp_(cp7_)?(get|list|resolve|search)_/.test(r.rpc)),JSON.stringify(requests.map(r=>r.rpc)))
  return{status:'PASS',finding:'R3-03',phone:mobile,owner:{events:5,invoice_balance:'30',customer_open_balance:'30',download_rows:5},
   sales_kasir:{events:5,amounts:false,download:false},read_only:true,rpc_calls:requests.length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await owner.context.close();if(kasir)await kasir.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_HISTORY_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_03_HISTORY_MOBILE',()=>journey(ui,today,true,h)]]
}
