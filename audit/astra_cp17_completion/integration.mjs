import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
const fixture=(op,p)=>JSON.parse(execFileSync('python',[fileURLToPath(new URL('./integration_fixture.py',import.meta.url)),op,JSON.stringify(p)],{encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
const numeric=x=>x.map(Number)
async function nav(ui,p,section,label){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:section})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+label,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:section}).click();await link.click()
}
async function run(ui,today,name,prepare,body){
 const f=fixture(prepare,{today}),user=await ui.login('OWNER',{label:name.toLowerCase()}),p=user.page,trace=[],requests=[]
 p.on('response',r=>{if(r.url().includes('/rpc/'))requests.push({rpc:new URL(r.url()).pathname.split('/').at(-1),status:r.status()})})
 mkdirSync('cp6-proof/t3',{recursive:true})
 try{const result=await body(p,f,trace);await p.screenshot({path:`cp6-proof/t3/${name}.png`,fullPage:true});return{status:'PASS',evidence_origin:'ASTRA_OWN_REAL_BROWSER_CHAIN',...result,trace,requests,screenshot:name+'.png'}}
 catch(error){const detail={status:'INCOMPLETE',evidence_origin:'ASTRA_OWN_REAL_BROWSER_CHAIN',error:String(error),stack:error.stack,fixture:f,trace,requests,body:await p.locator('body').innerText().catch(()=>'' )};writeFileSync(`cp6-proof/t3/${name}_FAILURE.json`,JSON.stringify(detail,null,2));await p.screenshot({path:`cp6-proof/t3/${name}_FAILURE.png`,fullPage:true}).catch(()=>{});return detail}
 finally{await user.context.close()}
}
async function production(ui,today){return run(ui,today,'ASTRA_CHAIN_CUT_TO_FG','production_prepare',async(p,f,trace)=>{
 const state=()=>fixture('production_read',f),at=h=>f.production_day+'T'+String(h).padStart(2,'0')+':00'
 assert.deepEqual(numeric(f.before.raw),[100,1000]);assert.equal(f.before.fg,0)
 await nav(ui,p,'Produksi','Buat Potongan')
 await p.getByLabel('Cari draft Potongan',{exact:true}).fill(f.group_number);await p.getByRole('button',{name:'Cari draft',exact:true}).click()
 await p.locator('.ccut-drafts button').filter({hasText:f.group_number}).click()
 await p.getByRole('button',{name:'Post ke WIP Potongan',exact:true}).click()
 await ui.expect.poll(()=>numeric(state().raw),{timeout:20000}).toEqual([40,400]);trace.push({stage:'CUT_POST',state:state()})
 await nav(ui,p,'Produksi','Bagi Potongan')
 await p.getByLabel('Cari distribusi potongan',{exact:true}).fill(f.group_number);await p.getByRole('button',{name:'Cari Potongan',exact:true}).click()
 await p.locator('.cpick-queue button').filter({hasText:f.group_number}).click()
 const mandor=p.locator('.cpick-setup').getByRole('combobox',{name:/^Mandor/});await ui.expect(mandor).toHaveCount(1);if(await mandor.isEnabled())await mandor.selectOption(f.contractor);await ui.expect(mandor).toHaveValue(f.contractor)
 await p.getByLabel('Waktu fisik diambil (WIB)',{exact:true}).fill(at(9))
 await p.getByRole('button',{name:'Catat pickup & masuk Sewing',exact:true}).click()
 await ui.expect.poll(()=>state().batches.length).toBe(1);const batch=state().batches[0][0];trace.push({stage:'PICKUP_POST',state:state()})
 await nav(ui,p,'Produksi','WIP & Sewing');await p.getByLabel('Cari WIP',{exact:true}).fill(f.group_number);await p.getByLabel('Cari WIP',{exact:true}).press('Enter')
 const card=p.locator('.cwip-list>article').filter({hasText:f.group_number}),sewing=card.getByRole('region',{name:'Selesai jahit '+f.group_number,exact:true})
 await sewing.getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
 await sewing.getByLabel('Jumlah selesai dijahit '+f.group_number,{exact:true}).fill('60')
 await sewing.getByLabel('Waktu selesai jahit '+f.group_number,{exact:true}).fill(at(10))
 await sewing.getByLabel('Catatan selesai jahit '+f.group_number,{exact:true}).fill('Astra enam puluh pcs selesai jahit dari pickup browser')
 await sewing.getByLabel('Selesai jahit '+f.group_number+' sudah diperiksa',{exact:true}).check()
 await sewing.getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
 await ui.expect.poll(()=>numeric(state().work)).toEqual([60,120]);trace.push({stage:'SEWING_POST',state:state()})
 await nav(ui,p,'Produksi','Laundry');await ui.expect(p.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
 await p.getByRole('button',{name:'Kirim ke Laundry',exact:true}).click()
 await p.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE',{exact:true}).selectOption(batch)
 await p.getByRole('button',{name:'Isi dari sisa siap',exact:true}).click()
 await p.getByRole('combobox',{name:/^VENDOR LAUNDRY/}).selectOption(f.vendor)
 await p.getByLabel('PROSES CUCI TARGET',{exact:true}).selectOption(f.process)
 await p.getByLabel('WARNA TARGET',{exact:true}).fill('E01 NAVY')
 await p.getByLabel('WAKTU FISIK KELUAR',{exact:true}).fill(at(11))
 await p.getByLabel('ALASAN / BUKTI SERAH TERIMA',{exact:true}).fill('Astra kirim hasil jahit browser enam puluh pcs')
 await p.locator('.clq-confirm input').check();await p.getByRole('button',{name:'Post pengiriman atomic',exact:true}).click()
 const delivery=()=>ui.sql(`select coalesce((select id::text from erp.laundry_deliveries where vendor_id='${f.vendor}' and status='POSTED' limit 1),'')`)
 await ui.expect.poll(delivery).not.toBe('');const sent=delivery();trace.push({stage:'LAUNDRY_SEND',delivery:sent})
 await ui.expect(p.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
 await p.getByRole('button',{name:'Terima kembali',exact:true}).click();await p.getByLabel('SURAT KIRIM AKTIF',{exact:true}).selectOption(sent)
 await p.getByLabel('PROSES AKTUAL',{exact:true}).selectOption(f.process);await p.getByLabel('WAKTU FISIK KEMBALI',{exact:true}).fill(at(13))
 await p.getByLabel('ALASAN / BUKTI PENERIMAAN',{exact:true}).fill('Astra terima lengkap enam puluh pcs dari laundry browser')
 await p.getByLabel('Good kembali size '+f.size_code,{exact:true}).fill('60');await p.locator('.clq-confirm input').check()
 await p.getByRole('button',{name:'Post penerimaan atomic',exact:true}).click()
 await ui.expect.poll(()=>ui.sql(`select count(*) from erp.laundry_receipts where delivery_id='${sent}' and status='POSTED'`)).toBe('1');trace.push({stage:'LAUNDRY_RECEIVE',receipt_count:1})
 await nav(ui,p,'Produksi','QC & Final SKU');await ui.expect(p.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
 await p.getByLabel('POTONGAN DENGAN GOOD LAUNDRY SIAP QC',{exact:true}).selectOption(f.group)
 await p.getByLabel('LOKASI FG TUJUAN',{exact:true}).selectOption(f.destination)
 await p.getByLabel('WAKTU FISIK QC',{exact:true}).fill(at(15));await p.getByLabel('ALASAN / BUKTI HASIL QC',{exact:true}).fill('Astra enam puluh barang sesuai ukuran dan SKU dari rantai browser')
 await p.getByRole('button',{name:'Isi semua sebagai Good',exact:true}).click()
 await p.getByLabel('Cari Final SKU size '+f.size_code,{exact:true}).fill(f.sku);await p.getByRole('button',{name:'Cari SKU',exact:true}).click()
 await p.getByLabel('Final SKU size '+f.size_code,{exact:true}).selectOption(f.product)
 await p.locator('.clq-confirm input').check();await p.getByRole('button',{name:'Post QC + Final SKU atomic',exact:true}).click()
 await ui.expect.poll(()=>state().fg,{timeout:20000}).toBe(60);const final=state();assert.deepEqual(numeric(final.raw),[40,400]);assert.deepEqual(numeric(final.work),[60,120]);trace.push({stage:'QC_FINAL_SKU',state:final})
 return{same_po:f.po,same_group:f.group,raw_remaining:40,raw_value:400,sewn:60,wages:120,FG:60,source_setup:'Native receipt and draft only; all six bridge posts actual browser',not_claimed:'Supplier payment, laundry invoice, finish, sale and period close are separate existing cases'}
})}
async function payroll(ui,today){return run(ui,today,'ASTRA_CHAIN_ACCESSORY_NOTA_TO_CASH','payroll_prepare',async(p,f,trace)=>{
 const read=()=>fixture('payroll_read',f)
 await p.clock.setFixedTime(new Date(today+'T00:00:00+07:00'))
 await nav(ui,p,'Keuangan','Nota Ambil Aksesori');await ui.expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled()
 await p.getByRole('button',{name:'Nota baru',exact:true}).click();const form=p.getByRole('region',{name:'Form nota aksesori',exact:true})
 await form.getByLabel('Nomor nota aksesori',{exact:true}).fill(f.issue_number);await form.getByLabel('Mandor aksesori',{exact:true}).selectOption(f.contractor)
 await form.getByLabel('Gudang aksesori',{exact:true}).selectOption(f.other);await form.getByLabel('Waktu ambil aksesori',{exact:true}).fill(f.issue_at.slice(0,16))
 await form.getByLabel('Cari barang aksesori',{exact:true}).fill(f.code);await form.getByRole('button',{name:'Perbarui harga dan stok',exact:true}).click()
 await ui.expect(form.getByLabel('Tambah aksesori',{exact:true})).toBeEnabled();await form.getByLabel('Tambah aksesori',{exact:true}).selectOption(f.material)
 await form.getByLabel('Jumlah PCS 1',{exact:true}).fill('7');await form.getByLabel('Harga per PCS 1',{exact:true}).fill('3.25')
 await form.getByRole('button',{name:'Simpan draft',exact:true}).click();await ui.expect.poll(()=>read().accessory.document?.status).toBe('DRAFT')
 assert.deepEqual(read().accessory.stock,f.before.stock)
 await form.getByRole('button',{name:'Periksa pengesahan',exact:true}).click();await form.getByRole('button',{name:'Sahkan nota',exact:true}).click()
 await ui.expect.poll(()=>read().accessory.document?.status).toBe('POSTED');const issued=read();assert.equal(Number(issued.accessory.document.total),22.75);assert.deepEqual(Object.fromEntries(Object.entries(issued.accessory.stock).map(([k,v])=>[k,Number(v)])),{main:20,other:3});trace.push({stage:'ACCESSORY_POST',actual:issued})
 await nav(ui,p,'Produksi','Susun Nota FG');await p.getByLabel('Cari kartu nota',{exact:true}).fill(f.label);await p.getByRole('button',{name:'Cari kartu',exact:true}).click()
 const panel=p.locator('.cnota');await ui.expect(panel.locator('.cnota-source')).toHaveCount(2)
 await panel.locator('.cnota-source').first().getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
 await panel.locator('.cnota-source').last().getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
 await ui.expect(panel.locator('.cnota-selected article')).toHaveCount(2);await p.getByRole('button',{name:'Simpan draft nota',exact:true}).click()
 await ui.expect(panel.locator('.cnota-review')).toContainText('Draft');await p.getByLabel('Nota sudah diperiksa',{exact:true}).check();await p.getByRole('button',{name:'Posting ke payroll',exact:true}).click()
 await ui.expect.poll(()=>read().notes[0]?.[1]).toBe('POSTED');trace.push({stage:'NOTA_POST',actual:read()})
 await nav(ui,p,'Keuangan','Payroll & Kasbon');const pay=p.locator('.cpay'),detail=pay.getByRole('region',{name:'Rincian payroll'})
 await pay.getByLabel('Cari payroll',{exact:true}).fill(f.label);await pay.getByRole('button',{name:'Cari payroll',exact:true}).click();await ui.expect(pay.locator('.cproc-receipt')).toHaveCount(1);await pay.locator('.cproc-receipt').click()
 await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click();await ui.expect.poll(()=>Number(read().payroll[0]?.net_payable)).toBe(5977.25)
 const prepared=read();assert.equal(Number(prepared.payroll[0].deduction_total),22.75);assert.equal(Number(prepared.payroll[0].labor_total),6000);trace.push({stage:'PAYROLL_PREPARE',actual:prepared})
 async function confirm(label,setup){await detail.getByRole('button',{name:label,exact:true}).click();const region=detail.getByRole('region',{name:'Periksa tindakan payroll'});if(setup)await setup(region);await region.getByLabel('Alasan tindakan payroll',{exact:true}).fill('Astra nota aksesori dan kartu upah direkonsiliasi sampai pembayaran');await region.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check();await region.getByRole('button',{name:label+' sekarang',exact:true}).click()}
 await confirm('Setujui payroll');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled()
 await confirm('Lunasi payroll',async r=>{await r.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(f.bank_code);await r.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click();await ui.expect(r.locator('.cpay-cash-row')).toHaveCount(1);await r.locator('.cpay-cash-row').click()})
 await ui.expect.poll(()=>read().payroll[0]?.status).toBe('PAID');const final=read();assert.equal(final.payroll.length,1);assert.equal(Number(final.payroll[0].net_payable),5977.25);assert.deepEqual(final.accessory.stock,issued.accessory.stock);assert.deepEqual(final.physical,issued.physical)
 assert.equal(Number(final.gl[f.bank_coa]??0)-Number(issued.gl[f.bank_coa]??0),-5977.25)
 assert.equal(Number(final.payment[0][1]),5977.25);assert.equal(Number(final.payment[0][2]),5977.25);assert.deepEqual(numeric(final.deduction_journal[0]),[2,22.75,22.75]);trace.push({stage:'CASH_PAID',actual:final})
 return{same_contractor:f.contractor,accessory:'7 x 3.25 = 22.75',labor:6000,deduction:22.75,cash:5977.25,stock_main:20,stock_other:3,balanced_payment:5977.25,source_setup:'Native receipt, transfer and repair work only; accessory save/post, Nota save/post, prepare, approve and pay actual Chromium',not_claimed:'The earlier BS/rework source creation is a fixture, not a UI action in this case'}
})}
export function cases(ui,today){const rows=[['ASTRA_CHAIN_CUT_TO_FG',()=>production(ui,today)],['ASTRA_CHAIN_ACCESSORY_NOTA_TO_CASH',()=>payroll(ui,today)]];return process.env.ASTRA_COMPLETION_SUITE==='production-qualified'?rows.slice(0,1):rows}
