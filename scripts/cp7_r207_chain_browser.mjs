// R2-07 (FABLE-016, ASTRA-C17-07, Sol BROWSER-CHAIN): one chain on the screens only, real Auth and PostgREST on the
// committed copy, starting from data the screens create, not SQL. "Impor data awal" creates the masters (model, size, two
// brands with one product each, FG warehouse, Mandor, laundry, customer), the open PO and its opening WIP; "Rincian produksi
// awal" turns 4 of the 8 WIP pieces into finished goods of brand A; "Ganti Merek" moves 2 of them to brand B; the owner
// closes the books through that day on "Laporan & Tutup Buku"; the chain then sells the 2 brand-B pieces on "Penjualan &
// Invoice" and records the customer's payment into a bank, while the closed days' books stay exactly as closed; the books
// are reopened on the same screen. The fixture gives only a bank account (no screen creates one) and the test harness
// state (the chain's own month opened, the seed's open items for those days cleared, restored at the end).
// The second chain starts the same way, then: the Mandor's work component and rate for the imported model on "Master Data
// → Mandor", 3 opening WIP pieces split off as BS ("Pisahkan sebagai BS"), a rework order to that Mandor with the
// component as wage basis on "Barang BS & Rework" and its result, the rework wage taken into a Nota on "Susun Nota FG" and
// posted to payroll, and the payroll counted, approved and paid from a bank on "Payroll & Kasbon". Its fixture adds the
// owner capital for exactly that wage (no capital screen is part of this chain; D14-3 keeps an empty bank empty).
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const csv=rows=>{const keys=Object.keys(rows[0]);return[keys.join(','),...rows.map(r=>keys.map(k=>r[k]).join(','))].join('\n')+'\n'}
const wibNow=minutes=>new Date(Date.now()+7*3600*1000-minutes*60*1000).toISOString().slice(0,16)
async function nav(ui,page,item,group){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await link.click()
}
async function importAction(ui,page,label,act){
 const reply=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_initial_import_action_v1')&&r.request().postDataJSON()?.p_action===act)
 await page.getByRole('button',{name:label,exact:true}).click()
 const r=await reply,body=await r.json();assert.equal(r.status(),200,`${act} ${JSON.stringify(body).slice(0,800)}`)
 await ui.expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
 return body
}
async function importBatch(ui,page,f,list){
 await nav(ui,page,'Impor data awal','Pengaturan & Audit');await ui.expect(page.getByRole('heading',{name:'Impor data awal',exact:true})).toBeVisible()
 await ui.expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
 await page.getByLabel('Kode batch',{exact:true}).fill(f.code);await page.getByLabel('Tanggal saldo awal',{exact:true}).fill(f.day)
 await importAction(ui,page,'Buat draft','CREATE')
 for(const[entity,data]of Object.entries(list)){
  await page.getByRole('combobox',{name:/^Jenis data/}).selectOption(entity)
  await page.getByLabel('Pilih file CSV',{exact:true}).setInputFiles({name:entity+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv(data))})
  await importAction(ui,page,'Simpan perubahan draft','SAVE_FILE');await ui.expect(page.getByRole('button',{name:'Simpan perubahan draft',exact:true})).toHaveCount(0)
 }
 const checked=await importAction(ui,page,'Periksa seluruh draft','VALIDATE')
 await ui.expect(page.getByRole('button',{name:'Sahkan data awal',exact:true})).toBeEnabled()
 await importAction(ui,page,'Sahkan data awal','FINALIZE');await ui.expect(page.getByText(/Sudah disahkan/).first()).toBeVisible()
 return checked
}
async function wipPanel(ui,page,s,values,mode){
 await page.getByRole('combobox',{name:'Batch impor',exact:true}).selectOption(s.batch.id)
 await ui.expect(page.getByLabel('Rincian produksi awal',{exact:true})).toBeVisible();await page.getByLabel('Rincian produksi awal',{exact:true}).selectOption(s.wip_item)
 if(mode)await page.getByLabel('Jenis catatan WIP awal',{exact:true}).selectOption(mode)
 for(const[label,value]of values)await page.getByLabel(label,{exact:true}).fill(value)
}
function rows(c){
 return{
  MODEL:[{model_code:c,model_name:'R2-07 model '+c}],SIZE:[{size_code:c}],
  BRAND:[{brand_code:c+'A',brand_name:'R2-07 merek A '+c},{brand_code:c+'B',brand_name:'R2-07 merek B '+c}],
  PRODUCT:[{sku:c+'A',product_name:'R2-07 produk A',model_code:c,brand_code:c+'A',color_name:'Blue',size_code:c},
   {sku:c+'B',product_name:'R2-07 produk B',model_code:c,brand_code:c+'B',color_name:'Blue',size_code:c}],
  CONTRACTOR:[{contractor_code:c,contractor_name:'R2-07 mandor '+c,contractor_type:'MANDOR'}],
  LAUNDRY_VENDOR:[{vendor_code:c,vendor_name:'R2-07 laundry '+c}],
  LOCATION:[{location_code:c+'F',location_name:'R2-07 gudang FG '+c,location_type:'FG_WAREHOUSE'}],
  CUSTOMER:[{customer_code:c,customer_name:'R2-07 pelanggan '+c}],
  OPEN_PO:[{po_number:c,model_code:c,contractor_code:c,target_qty_pcs:'10',status:'SEWING',current_stage:'SEWING'}],
  OPENING_BALANCE_ITEM:[{balance_type:'WIP',po_number:c,size_code:c,contractor_code:c,vendor_code:c,accessory_cost_included:'true',stage:'SEWING',
   qty:'8',unit_cost:'5',amount:'40.00',opening_source_key:'WIP',control_key:'WIP'}],
  OPENING_CONTROL:[{control_key:'WIP',balance_type:'WIP',qty:'8',amount:'40.00'}],
 }
}
async function chain(ui,today,h){
 const name='CP17_BROWSER_R2_07_IMPORT_WIP_BRAND_SALE_CASH_CLOSE',f=h.fixture('r207_prepare',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r207_state',f),c=f.code
 const user=await ui.login('OWNER',{label:'cp17-r2-07-chain',mobile:false}),page=user.page
 page.on('request',r=>{if(/\/rpc\/erp_(save_initial_import_action_v1|save_product_conversion_action_v1|cp7_save_period_control_v1|cp7_save_sale_v1)$/.test(r.url()))requests.push(r.url().split('/rpc/')[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  // 1. Masters, open PO and opening WIP through the import screen (CSV files, check, post).
  seen.step='import';seen.validate=await importBatch(ui,page,f,rows(c))
  let s=seen.imported=state();assert.equal(s.batch.status,'POSTED');assert.equal(Object.keys(s.products).length,2);assert.ok(s.wip_item&&s.location&&s.customer,JSON.stringify(s))
  // 2. Four of the eight opening WIP pieces become brand-A finished goods (Rincian produksi awal).
  seen.step='wip_output'
  await wipPanel(ui,page,s,[['Hasil WIP baik','4'],['Produk hasil WIP',c+'A'],['Merek hasil WIP',c+'A'],['Gudang hasil WIP',c+'F'],['Tanggal hasil WIP',f.output_day],['Catatan hasil WIP','R2-07 hasil WIP awal jadi barang jadi']])
  await importAction(ui,page,'Sahkan hasil WIP awal','WIP_OUTPUT')
  s=seen.output=state();assert.deepEqual([s.stock_a,s.stock_b,s.lots_a.length],[4,0,1])
  // 3. Two brand-A pieces change to brand B (Ganti Merek), physically on the same day.
  seen.step='brand_change';await nav(ui,page,'Ganti Merek','Gudang')
  const ready=()=>ui.expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
  await ready();await page.getByLabel('Cari lot / SKU',{exact:true}).fill(c+'A');await page.getByRole('button',{name:'Cari lot',exact:true}).click();await ready()
  await page.getByLabel(/^Lot dan gudang/).selectOption(s.lots_a[0]+':'+s.location);await ready()
  await page.getByLabel('Cari SKU tujuan',{exact:true}).fill(c+'B');await page.getByRole('button',{name:'Cari tujuan',exact:true}).click();await ready()
  await page.getByLabel(/^SKU tujuan/).selectOption(s.products[c+'B'])
  await page.getByLabel('Jumlah PCS',{exact:true}).fill('2');await page.getByLabel('Waktu fisik · WIB',{exact:true}).fill(f.output_day+'T15:00')
  await page.getByLabel('Alasan',{exact:true}).fill('R2-07 dua potong ganti merek')
  await page.getByRole('button',{name:'Lihat pratinjau',exact:true}).click()
  const post=page.getByRole('button',{name:'Catat konversi fisik',exact:true});await ui.expect(post).toBeEnabled({timeout:20000});await post.click()
  await ui.expect.poll(()=>state().stock_b,{timeout:20000}).toBe(2)
  s=seen.converted=state();assert.equal(s.stock_a,2);assert.deepEqual(s.conversions.map(x=>x[0]),['POSTED'])
  // 4. The owner closes the books through that day, in the middle of the chain.
  seen.step='close';await nav(ui,page,'Laporan & Tutup Buku','Keuangan');await ui.expect(page.getByRole('heading',{name:'Laporan & Tutup Buku',exact:true})).toBeVisible()
  const panel=page.getByRole('region',{name:'Kelola periode pembukuan',exact:true})
  await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(f.output_day)
  try{await ui.expect(panel).toContainText('Penghalang: 0.',{timeout:20000})}catch(e){seen.period_panel=await panel.innerText().catch(()=>'');throw e}
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill('R2-07 tutup buku di tengah rantai')
  const reviewed=panel.getByLabel('Saya sudah memeriksa tanggal, penghalang, dan alasan perubahan periode.',{exact:true});await reviewed.check()
  await panel.getByRole('button',{name:'Tutup buku dan simpan arsip',exact:true}).click()
  await ui.expect.poll(()=>state().closed_through,{timeout:20000}).toBe(f.output_day);await ui.expect(panel).toContainText('Periode tertutup sampai '+f.output_day)
  const closed=seen.closed=state();await page.screenshot({path:`cp6-proof/t3/${name}_CLOSED.png`,fullPage:true})
  // 5. The chain goes on after the closed day: sell the two brand-B pieces and record the customer's payment.
  seen.step='sale';await nav(ui,page,'Penjualan & Invoice','Penjualan')
  const ws=page.locator('.csales');await ui.expect(ws.getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
  const form=ws.getByRole('form',{name:'Draft invoice'}),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
  await ws.getByRole('button',{name:'Buat invoice',exact:true}).click()
  await form.getByLabel('Nomor draft invoice',{exact:true}).fill(c);await form.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(wibNow(5))
  await form.getByLabel('Cari pelanggan draft',{exact:true}).fill(c);await form.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click()
  const customer=form.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt');await ui.expect(customer).toHaveCount(1);await customer.click()
  await form.getByLabel('Cari barang draft',{exact:true}).fill(c+'B');await form.getByRole('button',{name:'Cari barang draft',exact:true}).click()
  const item=form.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt');await ui.expect(item).toHaveCount(1);await item.click()
  await form.getByLabel('Jumlah invoice 1',{exact:true}).fill('2');await form.getByLabel('Harga invoice 1',{exact:true}).fill('15000')
  await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('R2-07 jual dua potong merek B');await form.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
  await form.getByRole('button',{name:'Simpan draft invoice',exact:true}).click();await ui.expect(form).toHaveCount(0)
  await detail.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await detail.getByRole('button',{name:'Sahkan invoice',exact:true}).click()
  await ui.expect(detail).toContainText('Sisa pembayaran Rp30.000')
  seen.step='payment';const pay=ws.getByRole('region',{name:'Pembayaran invoice',exact:true}),pform=pay.getByRole('form',{name:'Catat pembayaran pelanggan'})
  await detail.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
  await pform.getByLabel('Nomor pembayaran pelanggan',{exact:true}).fill(c+'-PAY');await pform.getByLabel('Nominal pembayaran pelanggan',{exact:true}).fill('30000')
  await pform.getByLabel('Cari rekening pembayaran pelanggan',{exact:true}).fill(f.bank_code);await pform.getByRole('button',{name:'Cari rekening pelanggan',exact:true}).click()
  const banks=pform.getByRole('region',{name:'Pilih rekening pembayaran pelanggan'}).locator('.cproc-receipt');await ui.expect(banks).toHaveCount(1);await banks.click()
  await pform.getByLabel('Referensi pembayaran pelanggan',{exact:true}).fill('TRF-R207');await pform.getByLabel('Catatan pembayaran pelanggan',{exact:true}).fill('Transfer pelanggan diperiksa')
  await pform.getByLabel('Pembayaran pelanggan sudah diperiksa',{exact:true}).check();await pform.getByRole('button',{name:'Catat pembayaran pelanggan',exact:true}).click()
  await ui.expect(pay).toHaveCount(0);await ui.expect(detail).toContainText('Sisa pembayaran Rp0')
  s=seen.paid=state()
  assert.equal(s.sale.status,'PAID');assert.equal(s.sale.qty,2);assert.equal(s.stock_b,0);assert.equal(Number(s.bank_debit),30000)
  // The books on and before the closed day are exactly as closed although the chain went on.
  assert.deepEqual(s.books_through,closed.books_through);assert.equal(s.fg_through,closed.fg_through);assert.equal(s.closed_through,f.output_day)
  await page.screenshot({path:`cp6-proof/t3/${name}_PAID.png`,fullPage:true})
  // 6. Reopen to where the chain's month began, on the same screen.
  seen.step='reopen';await nav(ui,page,'Laporan & Tutup Buku','Keuangan')
  await panel.getByLabel('Tanggal pemeriksaan tutup buku',{exact:true}).fill(f.output_day);await ui.expect(panel.getByLabel('Tindakan periode',{exact:true})).toBeEnabled()
  await panel.getByLabel('Tindakan periode',{exact:true}).selectOption('REOPEN')
  await panel.getByLabel('Periode tetap tertutup sampai',{exact:true}).fill(f.opened_closed)
  await panel.getByLabel('Alasan perubahan periode',{exact:true}).fill('R2-07 buka kembali sesudah rantai');await reviewed.check()
  await panel.getByRole('button',{name:'Buka kembali periode',exact:true}).click()
  await ui.expect.poll(()=>state().closed_through,{timeout:20000}).toBe(f.opened_closed)
  return{status:'PASS',finding:'R2-07',screens:['Impor data awal (masters, PO, WIP)','Rincian produksi awal','Ganti Merek','Laporan & Tutup Buku (tutup)','Penjualan & Invoice','Pembayaran invoice','Laporan & Tutup Buku (buka)'],
   fixture_only:['bank account (no screen)','books opened to the chain month and seed open items cleared (harness state, restored)'],
   wip_to_fg:4,brand_changed:2,sold:2,paid:'30000',closed_books_unchanged_after_later_steps:true,requests:requests.length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{h.fixture('r207_restore',f);await user.context.close()}
}
const tag=()=>Math.random().toString(36).slice(2,8).toUpperCase()
async function fillAll(scope,values){
 for(const[label,value]of Object.entries(values)){const el=scope.getByLabel(label,{exact:true});if(typeof value==='object'||await el.evaluate(e=>e.tagName)==='SELECT')await el.selectOption(value);else await el.fill(value)}
}
async function rework(ui,today,h){
 const name='CP17_BROWSER_R2_07_BS_REWORK_NOTA_PAYROLL_PAY',f=h.fixture('r207b_prepare',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r207b_state',f),c=f.code,mandor='R2-07 mandor '+c
 const user=await ui.login('OWNER',{label:'cp17-r2-07-rework',mobile:false}),page=user.page
 page.on('request',r=>{const m=r.url().match(/\/rpc\/(erp_[a-z0-9_]+)$/);if(m&&/save|post/.test(m[1]))requests.push(m[1])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  // 1. Masters, open PO and opening WIP through the import screen.
  seen.step='import';const list=rows(c);delete list.CUSTOMER;seen.validate=await importBatch(ui,page,f,list)
  let s=seen.imported=state();assert.equal(s.batch.status,'POSTED');assert.ok(s.wip_item&&s.location&&s.mandor,JSON.stringify(s))
  // 2. The imported Mandor's work component and rate for the imported model (Master Data → Mandor).
  seen.step='rate';await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Master Data'})).toBeAttached()
  await nav(ui,page,'Mandor','Master Data');await ui.expect(page.getByRole('heading',{name:'Mandor & tarif upah',exact:true})).toBeVisible()
  const panel=page.locator('section.cmd-panel[aria-label="Mandor"]')
  await panel.getByLabel('Cari mandor',{exact:true}).fill(c);await panel.getByRole('button',{name:'Cari',exact:true}).click()
  await panel.getByRole('button',{name:'Pilih mandor '+c,exact:true}).click()
  const rates=page.getByRole('region',{name:'Tarif upah mandor',exact:true});await ui.expect(rates).toContainText('Mandor: '+c)
  await rates.getByLabel('Cari model',{exact:true}).fill(c);await rates.getByRole('button',{name:'Cari model',exact:true}).click()
  await rates.getByRole('button',{name:'Pilih model '+c,exact:true}).click()
  const comp='RWK-'+tag(),nc=rates.locator('section.cmd-form[aria-label="Komponen kerja baru"]')
  await fillAll(nc,{'Kode komponen kerja':comp,'Nama komponen kerja':'Jahit ulang','Jenis komponen kerja':'LABOR','Alasan komponen kerja baru':'Komponen kerja model impor'})
  await nc.getByRole('button',{name:'Tambah komponen kerja',exact:true}).click();await ui.expect(rates.locator('.cmd-done')).toHaveText(`Tersimpan: komponen kerja ${comp} dibuat.`)
  await rates.getByRole('button',{name:'Ubah komponen kerja model',exact:true}).click();const bom=rates.locator('section.cmd-form[aria-label="Komponen kerja model"]')
  await bom.getByRole('button',{name:'Tambah baris komponen',exact:true}).click()
  await fillAll(bom,{'Komponen 1':{label:`${comp} · Jahit ulang`},'Tarif bawaan 1':'1000','Komponen kerja berlaku mulai':f.day,'Alasan komponen kerja':'Komponen kerja model dari layar'})
  await bom.getByLabel('Komponen kerja sudah diperiksa',{exact:true}).check();await bom.getByRole('button',{name:'Simpan komponen kerja model',exact:true}).click()
  await ui.expect(rates.locator('.cmd-done')).toHaveText('Tersimpan: komponen kerja model diperbarui.')
  const row=rates.getByRole('region',{name:`Tarif upah ${comp}`,exact:true})
  await fillAll(row,{[`Tarif ${comp}`]:'1000',[`Tarif ${comp} berlaku mulai`]:f.day,[`Alasan tarif ${comp}`]:'Tarif mandor rework'});await row.getByLabel(`Tarif ${comp} sudah diperiksa`,{exact:true}).check()
  await row.getByRole('button',{name:`Simpan tarif ${comp}`,exact:true}).click();await ui.expect(rates.locator('.cmd-done')).toHaveText(`Tersimpan: tarif Rp1.000/pcs berlaku mulai ${f.day}.`)
  // 3. Three opening WIP pieces are split off as BS (the import page's WIP panel).
  seen.step='split_bs';await nav(ui,page,'Impor data awal','Pengaturan & Audit');await ui.expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
  await wipPanel(ui,page,s,[['Hasil WIP baik','3'],['Produk hasil WIP',c+'A'],['Merek hasil WIP',c+'A'],['Tanggal hasil WIP',f.output_day],['Catatan hasil WIP','R2-07 tiga potong BS dari WIP awal']],'SPLIT_BS')
  await importAction(ui,page,'Pisahkan sebagai BS','WIP_OUTPUT')
  s=seen.split=state();assert.ok(s.bs&&s.bs.qty===3,JSON.stringify(s.bs))
  // 4. Rework of the 3 BS pieces by the Mandor, the component as wage basis, all 3 back good.
  seen.step='rework';await nav(ui,page,'Barang BS & Rework','Produksi');await ui.expect(page.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled({timeout:20000})
  await page.locator('.cbsr-tabs').getByRole('button',{name:'Semua',exact:true}).click()
  const search=page.getByRole('form',{name:'Cari, browse, urutkan dan filter BS dan claim',exact:true})
  await search.getByLabel('Cari BS atau claim',{exact:true}).fill(s.bs.number);await search.getByRole('button',{name:'Cari kasus',exact:true}).click()
  await page.locator('.cbsr-list button').filter({hasText:s.bs.number}).click()
  await page.locator('.cbsr-route-tabs').getByRole('button',{name:'Rework',exact:true}).click()
  const form=page.locator('.cbsr-route-form'),order=c+'-RW'
  await form.getByLabel('NOMOR ORDER · WAJIB',{exact:true}).fill(order);await form.getByLabel(/^MANDOR REWORK/).selectOption(s.mandor)
  await form.getByLabel('QTY DIKIRIM',{exact:true}).fill('3');await form.getByLabel('WAKTU FISIK · WIB',{exact:true}).fill(f.rework_day+'T09:00')
  await form.getByLabel(/^GUDANG FG BILA GOOD/).selectOption(s.location);await form.getByLabel('CATATAN / ALASAN',{exact:true}).fill('R2-07 rework tiga potong ke mandor')
  await form.locator('fieldset.cbsr-checks').filter({has:page.getByText('KOMPONEN KERJA YANG DIULANG · DASAR UPAH REWORK',{exact:true})}).getByRole('checkbox').first().check()
  for(const box of await form.locator('.cbsr-accessories input[type=checkbox]').all())await box.uncheck()
  await form.getByRole('button',{name:'Buat order rework',exact:true}).click()
  const completion=page.locator('.cbsr-completion-form').filter({hasText:order});await ui.expect(completion).toBeVisible({timeout:20000})
  await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill('3');await completion.getByLabel('BS KUMULATIF',{exact:true}).fill('0')
  await completion.getByLabel('WAKTU SELESAI · WIB',{exact:true}).fill(f.rework_day+'T15:00');await completion.getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('R2-07 tiga potong kembali bagus')
  await completion.getByRole('button',{name:'Post hasil & recovery',exact:true}).click()
  await ui.expect.poll(()=>state().rework?.status,{timeout:20000}).toBe('COMPLETED')
  s=seen.reworked=state();assert.deepEqual([s.rework.good,s.rework.bs],[3,0])
  // 5. The rework wage into a Nota, posted to payroll (Susun Nota FG).
  seen.step='nota';await nav(ui,page,'Susun Nota FG','Produksi');const nota=page.locator('.cnota');await ui.expect(nota.getByRole('heading',{name:'Susun Nota FG',exact:true})).toBeVisible()
  await page.getByLabel('Cari kartu nota',{exact:true}).fill(mandor);await page.getByRole('button',{name:'Cari kartu',exact:true}).click()
  await ui.expect(nota.locator('.cnota-source')).toHaveCount(1);await ui.expect(nota.locator('.cnota-source')).toContainText('Bikin Bagus · rework')
  await nota.locator('.cnota-source').getByRole('button',{name:'Tambahkan ke nota',exact:true}).click();await ui.expect(nota.locator('.cnota-selected article')).toHaveCount(1)
  await page.getByRole('button',{name:'Simpan draft nota',exact:true}).click();await ui.expect(nota.locator('.cnota-review')).toContainText('Draft')
  await page.getByLabel('Nota sudah diperiksa',{exact:true}).check();await page.getByRole('button',{name:'Posting ke payroll',exact:true}).click()
  await ui.expect.poll(()=>state().note?.status,{timeout:20000}).toBe('POSTED')
  s=seen.noted=state();assert.ok(s.payroll,JSON.stringify(s))
  // 6. The payroll counted, approved and paid from the bank (Payroll & Kasbon).
  seen.step='payroll';await nav(ui,page,'Payroll & Kasbon','Keuangan');const pay=page.locator('.cpay');await ui.expect(pay.getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
  const detail=pay.getByRole('region',{name:'Rincian payroll'})
  await pay.getByLabel('Cari payroll',{exact:true}).fill(mandor);await pay.getByRole('button',{name:'Cari payroll',exact:true}).click()
  await ui.expect(pay.locator('.cproc-receipt')).toHaveCount(1);await pay.locator('.cproc-receipt').click()
  await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click();await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp3.000')
  const confirm=async(label,setup)=>{
   await detail.getByRole('button',{name:label,exact:true}).click()
   const box=detail.getByRole('region',{name:'Periksa tindakan payroll'}),commit=box.getByRole('button',{name:label+' sekarang',exact:true})
   if(setup)await setup(box)
   await box.getByLabel('Alasan tindakan payroll',{exact:true}).fill('R2-07 upah rework diperiksa');await box.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check()
   await ui.expect(commit).toBeEnabled();await commit.click()
  }
  await confirm('Setujui payroll');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled()
  await confirm('Lunasi payroll',async box=>{
   await box.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(f.bank_code);await box.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click()
   await ui.expect(box.locator('.cpay-cash-row')).toHaveCount(1);await box.locator('.cpay-cash-row').click()
  })
  await ui.expect.poll(()=>state().payroll?.status,{timeout:20000}).toBe('PAID')
  s=seen.paid=state();assert.deepEqual([Number(s.payroll.labor),Number(s.payroll.net),Number(s.bank_balance)],[3000,3000,0])
  await page.screenshot({path:`cp6-proof/t3/${name}_PAID.png`,fullPage:true})
  return{status:'PASS',finding:'R2-07',screens:['Impor data awal (masters, PO, WIP)','Master Data → Mandor (komponen kerja + tarif)','Pisahkan sebagai BS','Barang BS & Rework (order + hasil)','Susun Nota FG','Payroll & Kasbon (hitung, setujui, lunasi)'],
   fixture_only:['bank account (no screen)','owner capital 3000 for exactly the wage (D14-3)','harness state (chain month opened, seed open items cleared, restored)'],
   bs:3,rework_good:3,rework_wage:'3000',payroll_paid:'3000',requests:requests.length}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{h.fixture('r207_restore',f);await user.context.close()}
}
export function cases(ui,today,h){return[['CP17_BROWSER_R2_07_IMPORT_WIP_BRAND_SALE_CASH_CLOSE',()=>chain(ui,today,h)],['CP17_BROWSER_R2_07_BS_REWORK_NOTA_PAYROLL_PAY',()=>rework(ui,today,h)]]}
