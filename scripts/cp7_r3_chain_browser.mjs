// R3-03 / auditor Fable's oracle 3 (owner D16-1): screen-only chains, real Auth and PostgREST on the committed copy. Fable
// (verbatim): "Screen chains in the Enteng build: (a) sewing -> Nota -> payroll -> pay -> Kas & Bank -> report -> close;
// (b) FG -> invoice -> customer payment -> cash -> AR zero; (c) the D14-2, D14-3/D15-1 and D15-5 guards still refuse."
// The harness runs every CP17 browser case again on the Enteng build (AUDITOR_UI_MODE=ENTENG, ids suffixed _ENTENG).
// (a) desktop: the sewing is recorded on WIP & Sewing dated on the chain day, its wage taken into a Nota on Susun Nota FG and
//     posted to payroll, the payroll counted, approved and paid from the bank on Payroll & Kasbon (seeded ADMIN reads it but
//     cannot pay it and has no Tutup Buku tab), the payment read on Kas & Bank, the report read on Laporan & Tutup Buku, the
//     books closed through the chain day on its Tutup Buku tab, then reopened to restore.
// (b) phone 390: finished goods in stock (fixture) invoiced on Penjualan & Invoice, paid in full into a bank, the receipt read
//     on Kas & Bank and the customer's receivable zero on Piutang Pelanggan, with no horizontal overflow on any of them.
// (c) desktop: on Payroll & Kasbon a payment dated before the wage accrual (D14-2), a payment from an empty bank (D14-3) and a
//     kasbon that fits the bank's economic-date balance but not its book-date balance (D15-1) are refused with the server's
//     plain sentence and nothing changes; the lawful payment then posts; on Jurnal & Transaksi Lain an income dated the day
//     before the official cutover date is refused (D15-5) and nothing changes.
// Every amount asserted on screen is compared with an oracle read from the Native rows by the fixture (journal lines,
// payroll, work completion lines, sales, payments, kasbon, misc transactions), never with an RPC answer.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const wibNow=minutes=>new Date(Date.now()+7*3600*1000-minutes*60*1000).toISOString().slice(0,16)
// The screens' own number formats, applied to the oracle's numbers: formatReceiptDecimal (procurementContract.ts) and the
// sewing panel's rupiah (id-ID, at most 2 decimals).
const idr=v=>{const[whole,fraction='']=String(v).split('.');const f=fraction.replace(/0+$/,'');return whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(f?','+f:'')}
const rp=v=>'Rp'+Number(v).toLocaleString('id-ID',{minimumFractionDigits:0,maximumFractionDigits:2})
const money=v=>'Rp'+idr(v)
async function nav(ui,page,item,group){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await link.click()
}
// A row on a paged list (25 per page): the next page until the row shows, the page counted as loaded when its first row changed.
async function findRow(ui,scope,attr,id,nextLabel){
 for(let i=0;i<80;i++){
  const found=scope.locator(`[${attr}="${id}"]`);if(await found.count())return found
  const next=scope.getByRole('button',{name:nextLabel,exact:true});if(!await next.count()||!await next.isEnabled())break
  const first=()=>scope.locator(`[${attr}]`).first().getAttribute(attr,{timeout:20000})
  const was=await first();await next.click();await ui.expect.poll(first,{timeout:20000}).not.toBe(was)
 }
 throw new Error(`CP17_R3_03_ROW_NOT_ON_ANY_PAGE:${attr}=${id}`)
}
async function openPayroll(ui,page,label){
 await nav(ui,page,'Payroll & Kasbon','Keuangan');const pay=page.locator('.cpay');await ui.expect(pay.getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
 await pay.getByLabel('Cari payroll',{exact:true}).fill(label);await pay.getByRole('button',{name:'Cari payroll',exact:true}).click()
 await ui.expect(pay.locator('.cproc-receipt')).toHaveCount(1);await pay.locator('.cproc-receipt').click()
 const detail=pay.getByRole('region',{name:'Rincian payroll'});await ui.expect(detail).toContainText(label)
 return{pay,detail}
}
// One payroll action through its review box (Periksa tindakan payroll); setup fills what the action needs first.
async function payrollAction(ui,detail,label,reason,setup){
 const open=detail.getByRole('button',{name:label,exact:true});await ui.expect(open).toBeEnabled({timeout:20000});await open.click()
 const box=detail.getByRole('region',{name:'Periksa tindakan payroll'}),commit=box.getByRole('button',{name:label+' sekarang',exact:true})
 if(setup)await setup(box)
 await box.getByLabel('Alasan tindakan payroll',{exact:true}).fill(reason);await box.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check()
 await ui.expect(commit).toBeEnabled();await commit.click()
}
const payFrom=(ui,date,code)=>async box=>{
 await box.getByLabel('Tanggal pembayaran payroll',{exact:true}).fill(date)
 await box.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(code);await box.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click()
 await ui.expect(box.locator('.cpay-cash-row')).toHaveCount(1);await box.locator('.cpay-cash-row').click()
}
async function cashPage(ui,page,day){
 await nav(ui,page,'Kas & Bank','Keuangan');const cash=page.locator('.ccash');await ui.expect(cash.getByRole('heading',{name:'Kas & Bank',exact:true})).toBeVisible()
 await cash.getByLabel('Periode kas dari',{exact:true}).fill(day);await cash.getByLabel('Periode kas sampai',{exact:true}).fill(day)
 await cash.getByRole('button',{name:'Tampilkan kas',exact:true}).click();await ui.expect(cash).toContainText(`Periode ${day}–${day}.`,{timeout:20000})
 return cash
}
const cashText=j=>`Debit ${money(j.cash_debit)} · kredit ${money(j.cash_credit)} · bersih ${money(j.cash_net)}.`

async function sewingChain(ui,today,h){
 const name='CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE',f=h.fixture('r3c_sewing_prepare',{today}),seen={prepared:f},requests=[],adminRequests=[]
 const state=()=>h.fixture('r3c_sewing_state',f),day=f.day
 const user=await ui.login('OWNER',{label:'cp17-r3-03-chain-sewing',mobile:false}),page=user.page;let admin=null
 const writes=list=>r=>{const m=r.url().match(/\/rpc\/(erp_[a-z0-9_]+)$/);if(m&&/save|post|set|correct|reverse/.test(m[1]))list.push(m[1])}
 page.on('request',writes(requests))
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  let s=seen.before=state()
  assert.deepEqual([s.posted_work,s.note,s.payroll,s.closed_through],[0,null,null,f.opened_closed],JSON.stringify(s))
  assert.equal(Number(s.bank_balance),Number(f.wage),'owner capital for exactly the wage');assert.equal(s.capital.transaction_date,day)
  // 1. WIP & Sewing: the Mandor's 10 pieces finished on the chain day at 14:00 WIB (pickup_fixture cuts 10 at 08:00, picks up at 09:00).
  seen.step='sewing';await nav(ui,page,'WIP & Sewing','Produksi');await ui.expect(page.getByRole('heading',{name:'WIP & Sewing',exact:true})).toBeVisible()
  await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
  const card=page.locator('.cwip-list>article').filter({hasText:f.number});await ui.expect(card).toHaveCount(1)
  const sew=card.getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
  await sew.getByRole('button',{name:'Catat selesai jahit',exact:true}).click();await ui.expect(sew).toContainText('0 / 10 pcs',{timeout:20000})
  await sew.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill(String(f.qty))
  await sew.getByLabel('Waktu selesai jahit '+f.number,{exact:true}).fill(f.sewn_local)
  await sew.getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('R3-03 setoran jahit pada hari rantai')
  // Oracle: the Work BOM valid at that time and the Mandor's rates (Native master rows).
  await ui.expect(sew).toContainText(`Upah yang akan dicatat: ${f.qty} pcs × ${rp(f.per_pcs)} = ${rp(f.wage)}.`)
  await sew.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
  await sew.getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
  await ui.expect(page.getByText(`${f.number}: ${f.qty} pcs tercatat selesai dijahit. Upah mandor ${rp(f.wage)} masuk hutang mandor; ${f.qty} pcs siap dikirim ke laundry.`)).toBeVisible()
  s=seen.sewn=state()
  assert.deepEqual([s.sewn,s.posted_work,s.completion.day,s.completion.qty],[f.qty,1,day,f.qty],JSON.stringify(s.completion))
  assert.deepEqual(s.completion.rates.map(Number),f.rates.map(Number));assert.deepEqual(s.wage_journal,[[f.wage,f.wage,'1']])
  // 2. Susun Nota FG: that wage into a Nota dated on the chain day, posted to payroll.
  seen.step='nota';await nav(ui,page,'Susun Nota FG','Produksi');const nota=page.locator('.cnota');await ui.expect(nota.getByRole('heading',{name:'Susun Nota FG',exact:true})).toBeVisible()
  await page.getByLabel('Cari kartu nota',{exact:true}).fill(f.mandor_label);await page.getByRole('button',{name:'Cari kartu',exact:true}).click()
  const source=nota.locator('.cnota-source');await ui.expect(source).toHaveCount(1);await ui.expect(source).toContainText('Reguler');await ui.expect(source).toContainText('Jumlah kartu '+money(f.wage))
  await source.getByRole('button',{name:'Tambahkan ke nota',exact:true}).click();await ui.expect(nota.locator('.cnota-selected article')).toHaveCount(1)
  for(const label of['Tanggal nota WIB','Awal periode nota','Akhir periode nota'])await page.getByLabel(label,{exact:true}).fill(day)
  await page.getByRole('button',{name:'Simpan draft nota',exact:true}).click();await ui.expect(nota.locator('.cnota-review')).toContainText('Draft')
  await ui.expect(nota.locator('.cnota-total')).toHaveText(money(f.wage))
  await page.getByLabel('Nota sudah diperiksa',{exact:true}).check();await page.getByRole('button',{name:'Posting ke payroll',exact:true}).click()
  await ui.expect.poll(()=>state().note?.status,{timeout:20000}).toBe('POSTED')
  s=seen.noted=state();assert.ok(s.payroll,JSON.stringify(s));assert.equal(s.note.payroll,s.payroll.id);assert.deepEqual([s.payroll.period_start,s.payroll.period_end],[day,day])
  // 3. Payroll & Kasbon: counted and approved.
  seen.step='payroll';const{detail}=await openPayroll(ui,page,f.mandor_label)
  await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click();await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payroll'+money(f.wage))
  await payrollAction(ui,detail,'Setujui payroll','R3-03 upah jahit diperiksa');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled({timeout:20000})
  s=seen.approved=state();assert.deepEqual([s.payroll.status,Number(s.payroll.net),Number(s.payroll.labor)],['APPROVED',Number(f.wage),Number(f.wage)])
  // Limited role: seeded ADMIN (no finance.payroll.pay, no finance.period_close.manage) reads the approved payroll but has no
  // way to pay it, and the report without the Tutup Buku tab; it sends no write.
  seen.step='admin';admin=await ui.login('ADMIN',{label:'cp17-r3-03-chain-admin',mobile:false});const ap=admin.page;ap.on('request',writes(adminRequests))
  const{detail:adminDetail}=await openPayroll(ui,ap,f.mandor_label)
  await ui.expect(adminDetail).toContainText('Disetujui');await ui.expect(adminDetail.locator('.cpay-net')).toHaveText('Bersih payroll'+money(f.wage))
  await ui.expect(adminDetail.getByRole('button',{name:'Lunasi payroll',exact:true})).toHaveCount(0)
  await nav(ui,ap,'Laporan & Tutup Buku','Keuangan');await ui.expect(ap.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
  await ui.expect(ap.getByRole('region',{name:'Posisi keuangan tercatat',exact:true})).toBeVisible();await ui.expect(ap.getByRole('tab',{name:'Tutup Buku',exact:true})).toHaveCount(0)
  assert.deepEqual(adminRequests,[]);assert.deepEqual(state().payroll,s.payroll)
  await admin.context.close();admin=null
  // OWNER pays it on the chain day from the bank that holds exactly the wage.
  seen.step='pay';await payrollAction(ui,detail,'Lunasi payroll','R3-03 upah jahit dibayar',payFrom(ui,day,f.bank_code))
  await ui.expect.poll(()=>state().payroll?.status,{timeout:20000}).toBe('PAID')
  s=seen.paid=state()
  assert.deepEqual([s.payroll.payment_date,s.payroll.bank,Number(s.bank_balance),Number(s.mandor_payable)],[day,f.bank,0,0])
  assert.deepEqual([s.payment.economic_date,s.payment.transaction_date,Number(s.payment.cash_credit),Number(s.payment.cash_debit)],[day,day,Number(f.wage),0])
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah dilunasi'+money(f.wage))
  // 4. Kas & Bank on the chain day: the capital in, the payment out, and the day's totals of every cash/bank account.
  seen.step='cash';const cash=await cashPage(ui,page,day)
  const metric=label=>cash.getByRole('region',{name:'Saldo dan perubahan kas',exact:true}).locator('.cproc-total').filter({hasText:label}).locator('strong')
  await ui.expect(metric('Debit rekening kas/bank')).toHaveText(money(s.cash_day.debit));await ui.expect(metric('Kredit rekening kas/bank')).toHaveText(money(s.cash_day.credit))
  const paid=await findRow(ui,cash,'data-journal-id',s.payment.id,'Jurnal berikutnya')
  await ui.expect(paid).toContainText(`${s.payment.source_type} · pembukuan ${day} · kejadian ${day}`);await ui.expect(paid).toContainText(cashText(s.payment))
  const capital=await findRow(ui,cash,'data-journal-id',s.capital.id,'Jurnal berikutnya');await ui.expect(capital).toContainText(cashText(s.capital))
  await page.screenshot({path:`cp6-proof/t3/${name}_CASH.png`,fullPage:true})
  // 5. Laporan & Tutup Buku, Laporan tab, as of the chain day: cash and WIP equal the journal lines booked on or before it.
  seen.step='report';await nav(ui,page,'Laporan & Tutup Buku','Keuangan');await ui.expect(page.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
  for(const label of['Periode laporan dari','Periode laporan sampai','Posisi laporan pada'])await page.getByLabel(label,{exact:true}).fill(day)
  await page.getByRole('button',{name:'Tampilkan laporan',exact:true}).click()
  const position=page.getByRole('region',{name:'Posisi keuangan tercatat',exact:true});await ui.expect(position).toContainText(`Sampai ${day}.`,{timeout:20000})
  const total=label=>position.locator('.cproc-total').filter({hasText:label}).locator('strong')
  await ui.expect(total('Kas dan bank')).toHaveText(money(s.report.cash));await ui.expect(total('Barang dalam proses')).toHaveText(money(s.report.wip))
  // 6. Tutup Buku tab: the books closed through the chain day (owner D16-5).
  seen.step='close';await page.getByRole('tab',{name:'Tutup Buku',exact:true}).click()
  const panel=page.getByRole('region',{name:'Kelola periode pembukuan',exact:true})
  await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(day)
  try{await ui.expect(panel).toContainText('Penghalang: 0.',{timeout:20000})}catch(e){seen.period_panel=await panel.innerText().catch(()=>'');throw e}
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill('R3-03 tutup buku sesudah upah jahit dibayar')
  const reviewed=panel.getByLabel('Saya sudah memeriksa tanggal, penghalang, dan alasan perubahan periode.',{exact:true});await reviewed.check()
  await panel.getByRole('button',{name:'Tutup buku dan simpan arsip',exact:true}).click()
  await ui.expect.poll(()=>state().closed_through,{timeout:20000}).toBe(day);await ui.expect(panel).toContainText('Periode tertutup sampai '+day)
  const closed=seen.closed=state();assert.equal(closed.filings_on_day,s.filings_on_day+1);assert.deepEqual([closed.payroll,closed.report],[s.payroll,s.report])
  await page.screenshot({path:`cp6-proof/t3/${name}_CLOSED.png`,fullPage:true})
  // 7. Reopen to where the chain began, on the same tab.
  seen.step='reopen';await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(day);await ui.expect(panel.getByLabel('Tindakan periode',{exact:true})).toBeEnabled({timeout:20000})
  await panel.getByLabel('Tindakan periode',{exact:true}).selectOption('REOPEN');await panel.getByLabel('Periode tetap tertutup sampai',{exact:true}).fill(f.opened_closed)
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill('R3-03 buka kembali sesudah rantai');await reviewed.check()
  await panel.getByRole('button',{name:'Buka kembali periode',exact:true}).click()
  await ui.expect.poll(()=>state().closed_through,{timeout:20000}).toBe(f.opened_closed)
  return{status:'PASS',finding:'R3-03',auditor_oracle:'Fable oracle 3 (a)',owner_decision:'D16-1',chain_day:day,
   screens:['WIP & Sewing','Susun Nota FG','Payroll & Kasbon (hitung, setujui, lunasi)','Kas & Bank','Laporan & Tutup Buku (laporan, tutup, buka)'],
   fixture_only:['posted cutting picked up by the Mandor, Work BOM and Mandor rate (no screen in this chain)','bank with owner capital for exactly the wage (D14-3)','harness state (chain month opened, seed open items cleared, restored)'],
   sewn:f.qty,wage:f.wage,per_pcs:f.per_pcs,payroll_paid_on:day,bank_after:'0',report_cash:s.report.cash,report_wip:s.report.wip,closed_through:day,reopened_to:f.opened_closed,
   limited_role:'ADMIN reads the approved payroll, no pay button, no Tutup Buku tab, no write',writes:requests.length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{h.fixture('r3c_restore',f);if(admin)await admin.context.close();await user.context.close()}
}

async function saleChain(ui,today,h){
 const name='CP17_BROWSER_R3_03_CHAIN_FG_TO_AR_ZERO',f=h.fixture('r3c_sale_prepare',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r3c_sale_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-03-chain-sale',mobile:true}),page=user.page
 page.on('request',r=>{if(/\/rpc\/erp_cp7_save_sale_v1$/.test(r.url()))requests.push(r.postDataJSON()?.p_action)})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  let s=seen.before=state();assert.deepEqual([s.sale,s.stock,Number(s.ar.balance),Number(s.bank_balance),s.receipt],[null,f.stock,0,0,null],JSON.stringify(s))
  // 1. Penjualan & Invoice: two of the five pieces in stock, invoiced and posted.
  seen.step='invoice';await nav(ui,page,'Penjualan & Invoice','Penjualan')
  const ws=page.locator('.csales');await ui.expect(ws.getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
  const form=ws.getByRole('form',{name:'Draft invoice'}),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
  await ws.getByRole('button',{name:'Buat invoice',exact:true}).click()
  await form.getByLabel('Nomor draft invoice',{exact:true}).fill(f.code);await form.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(wibNow(5))
  await form.getByLabel('Cari pelanggan draft',{exact:true}).fill(f.code);await form.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click()
  const customer=form.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt');await ui.expect(customer).toHaveCount(1);await customer.click()
  await form.getByLabel('Cari barang draft',{exact:true}).fill(f.sku);await form.getByRole('button',{name:'Cari barang draft',exact:true}).click()
  const item=form.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt');await ui.expect(item).toHaveCount(1);await item.click()
  await form.getByLabel('Jumlah invoice 1',{exact:true}).fill(String(f.qty));await form.getByLabel('Harga invoice 1',{exact:true}).fill(f.price)
  await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('R3-03 jual dua potong barang jadi');await form.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
  await h.noSideScroll(ui,page)
  await form.getByRole('button',{name:'Simpan draft invoice',exact:true}).click();await ui.expect(form).toHaveCount(0)
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
  await ui.expect(detail).toContainText('Sisa pembayaran '+money(f.total))
  s=seen.posted=state();assert.deepEqual([s.sale.status,s.sale.qty,Number(s.sale.total),Number(s.ar.balance)],['POSTED',f.qty,Number(f.total),Number(f.total)])
  await h.noSideScroll(ui,page)
  // 2. The full customer payment into the bank.
  seen.step='payment';const pay=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}),pform=pay.getByRole('form',{name:'Catat pembayaran pelanggan'})
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
  await pform.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(f.code+'-PAY');await pform.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill(String(Number(f.total)))
  await pform.getByLabel('Cari rekening pembayaran pelanggan',{exact:true}).fill(f.bank_code);await pform.getByRole('button',{name:'Cari rekening pelanggan',exact:true}).click()
  const banks=pform.getByRole('region',{name:'Pilih rekening pembayaran pelanggan'}).locator('.cproc-receipt');await ui.expect(banks).toHaveCount(1);await banks.click()
  await pform.getByLabel('Referensi pembayaran pelanggan',{exact:true}).fill('TRF-R303');await pform.getByLabel('Catatan pembayaran pelanggan',{exact:true}).fill('Transfer pelanggan diperiksa')
  await pform.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await h.noSideScroll(ui,page)
  await pform.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click()
  await ui.expect(pay).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp0')
  s=seen.paid=state()
  assert.deepEqual([s.sale.status,s.payments.map(([n,a,st,b])=>[n,Number(a),st,b]),Number(s.bank_balance),s.stock],['PAID',[[f.code+'-PAY',Number(f.total),'POSTED',f.bank]],Number(f.total),f.stock-f.qty])
  assert.deepEqual([Number(s.ar.debit),Number(s.ar.credit),Number(s.ar.balance)],[Number(f.total),Number(f.total),0])
  assert.ok(s.receipt&&Number(s.receipt.cash_debit)===Number(f.total)&&Number(s.receipt.cash_credit)===0,JSON.stringify(s.receipt))
  // 3. Kas & Bank on the receipt's book date: the receipt row.
  seen.step='cash';const cash=await cashPage(ui,page,s.receipt.transaction_date)
  const row=await findRow(ui,cash,'data-journal-id',s.receipt.id,'Jurnal berikutnya')
  await ui.expect(row).toContainText(`${s.receipt.source_type} · pembukuan ${s.receipt.transaction_date} · kejadian ${s.receipt.economic_date}`);await ui.expect(row).toContainText(cashText(s.receipt))
  await h.noSideScroll(ui,page)
  // 4. Piutang Pelanggan: the customer's invoice is paid, nothing left to collect.
  seen.step='receivable';await nav(ui,page,'Piutang Pelanggan','Keuangan');const ar=page.locator('.creceivables')
  await ui.expect(ar.getByRole('heading',{name:'Piutang Pelanggan',exact:true})).toBeVisible()
  await ar.getByLabel('Cari sumber piutang',{exact:true}).fill(f.code);await ar.getByRole('button',{name:'Cari piutang',exact:true}).click()
  const source=ar.locator(`[data-sale-id="${s.sale.id}"]`);await ui.expect(source).toHaveCount(1,{timeout:20000})
  await ui.expect(source).toContainText('Lunas');await ui.expect(source).toContainText('Sisa tagihan');await ui.expect(source.locator('strong').last()).toHaveText('Rp0')
  await source.click();const aside=ar.getByRole('complementary',{name:'Rincian sumber piutang'});await ui.expect(aside).toContainText(f.code)
  const total=label=>aside.locator('.cproc-total').filter({hasText:label}).locator('strong')
  await ui.expect(total('Nilai invoice')).toHaveText(money(f.total));await ui.expect(total('Pembayaran tercatat')).toHaveText(money(f.total));await ui.expect(total('Sisa tagihan')).toHaveText('Rp0')
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_AR_ZERO.png`,fullPage:true})
  return{status:'PASS',finding:'R3-03',auditor_oracle:'Fable oracle 3 (b)',owner_decision:'D16-1',phone:true,
   screens:['Penjualan & Invoice','Pembayaran invoice','Kas & Bank','Piutang Pelanggan'],fixture_only:['finished goods found at opname (no screen in this chain)','customer and bank masters'],
   sold:f.qty,invoice:f.total,paid:f.total,bank_after:s.bank_balance,customer_ar_debit:s.ar.debit,customer_ar_credit:s.ar.credit,customer_ar_balance:s.ar.balance,
   no_horizontal_overflow:true,sale_requests:requests}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}

async function guards(ui,today,h){
 const name='CP17_BROWSER_R3_03_GUARDS_REFUSE',f=h.fixture('r3c_guard_prepare',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r3c_guard_state',f);let cutover=null
 const user=await ui.login('OWNER',{label:'cp17-r3-03-guards',mobile:false}),page=user.page
 page.on('request',r=>{const m=r.url().match(/\/rpc\/(erp_cp7_(?:save_payroll|save_kasbon|save_misc_finance)_v1)$/);if(m)requests.push([m[1],r.postDataJSON()?.p_action])})
 const unchanged=(before,what)=>{const now=state();seen[what]=now;assert.deepEqual(now,before,'CP17_R3_03_REFUSAL_CHANGED_NATIVE_ROWS:'+what)}
 const cashSentence=(bankName,code,minus,day,basis)=>`Saldo ${bankName} (${code}) menjadi minus ${minus} pada ${basis==='book'?'tanggal buku':'tanggal'} ${day} atau sesudahnya (${basis==='book'?'laporan kas harian':'tanggal ekonomi'}). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.`
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const s0=seen.before=state()
  assert.deepEqual([s0.payroll.status,s0.payroll_journals.some(j=>j[0]==='PAYROLL_PAYMENT'),s0.kasbon,s0.misc],['APPROVED',false,0,null],JSON.stringify(s0))
  assert.deepEqual([Number(s0.banks.bank_f.balance),Number(s0.banks.bank_e.balance),Number(s0.banks.bank_k.balance)],[Number(f.net),0,2500])
  // Oracle of the D15-1 setup: the capital of bank K is dated on the kasbon day but booked later (first open day then).
  assert.ok(s0.banks.bank_k.book.length===1&&s0.banks.bank_k.book[0][1]===f.kasbon_day&&s0.banks.bank_k.book[0][0]>f.kasbon_day,JSON.stringify(s0.banks.bank_k))
  const{pay,detail}=await openPayroll(ui,page,f.mandor_label);await ui.expect(detail).toContainText('Disetujui')
  const alert=text=>pay.getByRole('alert').filter({hasText:text})
  // 1. D14-2: paid one day before the wage was recognised (the accrual day is read from the Native accrual journals), from a
  //    bank that already holds the money then, so only the payment-date rule can refuse.
  seen.step='d14_2';await payrollAction(ui,detail,'Lunasi payroll','R3-03 bayar sebelum upah tercatat',payFrom(ui,f.early,f.bank_f_code))
  await ui.expect(alert('hanya lewat kasbon')).toHaveText(`Tanggal bayar ${f.early} sebelum utang upah terakhir di payroll ini tercatat (${f.accrued}). Bayar sebelum itu hanya lewat kasbon.`,{timeout:20000})
  unchanged(s0,'after_d14_2')
  // 2. D14-3: on the accrual day from an empty bank.
  seen.step='d14_3';await payrollAction(ui,detail,'Lunasi payroll','R3-03 bayar dari bank kosong',payFrom(ui,f.accrued,f.bank_e_code))
  await ui.expect(alert('tanggal ekonomi')).toHaveText(cashSentence(f.bank_e_name,f.bank_e_code,f.e_minus,f.accrued,'economic'),{timeout:20000})
  unchanged(s0,'after_d14_3')
  // 3. D15-1: a kasbon from bank K on its capital's own date fits the economic-date balance (0) but takes the book-date
  //    balance of that day below zero (the capital is booked later), so the owner's daily cash report would go negative.
  seen.step='d15_1';const kas=page.getByRole('region',{name:'Kasbon tunai',exact:true})
  await kas.getByRole('button',{name:'Lihat kasbon mandor ini',exact:true}).click();await ui.expect(kas).toContainText('Mandor ini belum punya kasbon.')
  await kas.getByRole('button',{name:'Beri kasbon',exact:true}).click();const kform=kas.getByRole('region',{name:'Periksa kasbon',exact:true})
  await kform.getByLabel('Nominal kasbon',{exact:true}).fill(String(Number(f.kasbon_amount)));await kform.getByLabel('Tanggal kasbon',{exact:true}).fill(f.kasbon_day)
  await kform.getByLabel('Rekening kasbon',{exact:true}).selectOption(f.bank_k);await kform.getByLabel('Alasan kasbon',{exact:true}).fill('R3-03 kasbon sebelum modal dibukukan')
  await kform.getByLabel('Kasbon sudah diperiksa',{exact:true}).check();await kform.getByRole('button',{name:'Simpan kasbon',exact:true}).click()
  await ui.expect(kas.getByRole('alert').filter({hasText:'laporan kas harian'})).toHaveText(cashSentence(f.bank_k_name,f.bank_k_code,f.k_minus,f.kasbon_day,'book'),{timeout:20000})
  unchanged(s0,'after_d15_1')
  await page.screenshot({path:`cp6-proof/t3/${name}_REFUSED.png`,fullPage:true})
  // 4. The lawful payment: on the accrual day from the bank that holds the money.
  seen.step='lawful';await payrollAction(ui,detail,'Lunasi payroll','R3-03 bayar pada hari upah tercatat',payFrom(ui,f.accrued,f.bank_f_code))
  await ui.expect.poll(()=>state().payroll.status,{timeout:20000}).toBe('PAID')
  const s4=seen.paid=state()
  assert.deepEqual([s4.payroll.payment_date,s4.payroll.bank,Number(s4.banks.bank_f.balance),s4.banks.bank_e,s4.banks.bank_k,s4.kasbon],[f.accrued,f.bank_f,0,s0.banks.bank_e,s0.banks.bank_k,0])
  // 5. D15-5: the official cutover date at the first operational day; an income dated the day before is refused on Jurnal &
  //    Transaksi Lain (its draft saves; posting it would write a journal before the cutover).
  seen.step='d15_5';cutover=seen.cutover=h.fixture('r3c_guard_cutover',f)
  await nav(ui,page,'Jurnal & Transaksi Lain','Keuangan');await ui.expect(page.getByRole('heading',{name:'Jurnal Keuangan',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Buka pendapatan dan biaya lain',exact:true}).click()
  const misc=page.getByRole('region',{name:'Pendapatan dan biaya lain',exact:true}),create=misc.getByRole('button',{name:'Buat transaksi lain',exact:true})
  await ui.expect(create).toBeEnabled({timeout:20000});await create.click()
  const mform=misc.getByRole('form',{name:'Draft pendapatan atau biaya lain'})
  await mform.getByLabel('Jenis transaksi lain',{exact:true}).selectOption('OTHER_INCOME')
  await (await findRow(ui,mform.getByRole('region',{name:'Kategori transaksi lain',exact:true}),'data-misc-category-id',f.category,'Kategori berikutnya')).click()
  await (await findRow(ui,mform.getByRole('region',{name:'Rekening transaksi lain',exact:true}),'data-misc-cash-id',f.bank_e,'Rekening transaksi lain berikutnya')).click()
  await mform.getByLabel('Nomor transaksi lain',{exact:true}).fill(f.misc_number);await mform.getByLabel('Waktu transaksi lain WIB',{exact:true}).fill(cutover.before_day+'T09:00')
  await mform.getByLabel('Nominal transaksi lain',{exact:true}).fill('1000');await mform.getByLabel('Alasan simpan transaksi lain',{exact:true}).fill('R3-03 pendapatan sebelum tanggal mulai pakai')
  await mform.getByLabel('Draft transaksi lain sudah diperiksa',{exact:true}).check();await mform.getByRole('button',{name:'Simpan draft transaksi lain',exact:true}).click()
  await ui.expect.poll(()=>state().misc?.status,{timeout:20000}).toBe('DRAFT')
  const drafted=seen.drafted=state();assert.deepEqual([drafted.misc.day,drafted.misc.journals,drafted.cutover],[cutover.before_day,0,{version:cutover.version,date:cutover.cutover_date}])
  const aside=misc.getByRole('complementary',{name:'Rincian transaksi lain'});await ui.expect(aside).toContainText(f.misc_number)
  await aside.getByLabel('Alasan posting atau pembalikan transaksi lain',{exact:true}).fill('R3-03 posting pendapatan sebelum cutover')
  await aside.getByLabel('Transaksi lain untuk posting atau pembalikan sudah diperiksa',{exact:true}).check();await aside.getByRole('button',{name:'Posting transaksi lain',exact:true}).click()
  await ui.expect(misc.getByRole('alert').filter({hasText:'cutover resmi'})).toHaveText(`Transaksi bertanggal ${cutover.before_day} jatuh sebelum tanggal mulai pakai aplikasi ${cutover.cutover_date} (cutover resmi). Data sebelum tanggal itu masuk lewat Impor Saldo Awal; dokumen lama dibetulkan lewat jalur koreksinya.`,{timeout:20000})
  unchanged(drafted,'after_d15_5')
  await page.screenshot({path:`cp6-proof/t3/${name}_CUTOVER.png`,fullPage:true})
  return{status:'PASS',finding:'R3-03',auditor_oracle:'Fable oracle 3 (c)',owner_decisions:['D14-2','D14-3','D15-1','D15-5','D16-1'],
   refused:{d14_2_paid_before_accrual:{payment_date:f.early,accrued:f.accrued},d14_3_empty_bank:{bank:f.bank_e_code,would_be:f.e_minus},
    d15_1_book_date:{bank:f.bank_k_code,kasbon_day:f.kasbon_day,capital_booked:s0.banks.bank_k.book[0][0]},d15_5_before_cutover:{dated:cutover.before_day,cutover:cutover.cutover_date}},
   native_rows_unchanged_after_each_refusal:true,lawful_payment_on_accrual_day_paid:true,writes:requests}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{try{if(cutover)h.fixture('cutover_reset',{})}finally{h.fixture('r3c_restore',f);await user.context.close()}}
}

export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE',()=>sewingChain(ui,today,h)],['CP17_BROWSER_R3_03_CHAIN_FG_TO_AR_ZERO',()=>saleChain(ui,today,h)],
  ['CP17_BROWSER_R3_03_GUARDS_REFUSE',()=>guards(ui,today,h)]]
}
