// Owner D15-3 (FABLE-017, ASTRA-C17-04): the connected master screens on desktop and phone, real Auth and PostgREST on the
// committed copy, and Fable's screen-only chain: a new Mandor and his rates from Master Data -> Bagi Potongan -> "Catat
// selesai jahit" pays the rate valid on the sewing date; a rate saved later leaves the recorded wage as it was.
// Every write goes through the screens; the fixtures only give each case its own records (a fresh model, a customer with an
// open sales draft, a stocked warehouse, a posted cutting without a Mandor) and read the Native tables back directly.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const tag=()=>Math.random().toString(36).slice(2,8).toUpperCase()
const day=(today,offset)=>{const d=new Date(today+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10)}
const titles={Pelanggan:'Pelanggan','Supplier & Vendor':'Supplier & Vendor',Mandor:'Mandor & tarif upah','Gudang & Lokasi':'Gudang & Lokasi','Kain & Benchmark':'Kain & harga acuan','Aksesori & Harga Mandor':'Aksesori & harga mandor'}
async function masterPage(ui,page,label){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Master Data'})).toBeAttached()
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• '+label,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Master Data'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:titles[label],exact:true})).toBeVisible()
}
const panelOf=(page,plural)=>page.locator(`section.cmd-panel[aria-label="${plural}"]`)
async function fill(scope,values){
 for(const[label,value]of Object.entries(values)){
  const el=scope.getByLabel(label,{exact:true})
  if(typeof value==='boolean'){if(value)await el.check();else await el.uncheck()}
  else if(typeof value==='object')await el.selectOption(value)
  else if(await el.evaluate(e=>e.tagName)==='SELECT')await el.selectOption(value)
  else await el.fill(value)
 }
}
async function review(scope,what,reason){await scope.getByLabel(`Alasan ${what}`,{exact:true}).fill(reason);await scope.getByLabel(`${what} sudah diperiksa`,{exact:true}).check()}
async function done(ui,scope,text){await ui.expect(scope.locator('.cmd-done')).toHaveText(text)}
function watch(page){
 const requests=[]
 page.on('request',r=>{const m=r.url().match(/\/rpc\/(erp_cp7_save_(?:master|work_rate)_v1)$/);if(m)requests.push([m[1],r.postDataJSON()])})
 return requests
}
async function run(h,ui,name,label,mobile,body){
 const user=await ui.login('OWNER',{label:'cp17-r2-'+label+'-'+(mobile?'mobile':'desktop'),mobile}),page=user.page,requests=watch(page),seen={}
 try{mkdirSync('cp6-proof/t3',{recursive:true});const out=await body(page,requests,seen);await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true});return out}
 catch(error){await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}

// Pelanggan: create, correct the name, deactivate; a customer already on an open sales draft keeps its code and cannot be
// deactivated, and the screen says why.
async function customers(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_CUSTOMERS_${mobile?'MOBILE':'DESKTOP'}`,code='CUS-'+tag(),used=h.fixture('master_used_customer',{today})
 const state=c=>h.fixture('master_state',{kind:'CUSTOMER',code:c})
 return run(h,ui,name,'master-customers',mobile,async(page,requests,seen)=>{
  assert.equal(state(code).found,false);await masterPage(ui,page,'Pelanggan');const panel=panelOf(page,'Pelanggan')
  await panel.getByRole('button',{name:'Tambah pelanggan',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form pelanggan"]'),save=form.getByRole('button',{name:'Simpan pelanggan',exact:true})
  await ui.expect(save).toBeDisabled();await fill(form,{Kode:code,'Nama pelanggan':'Toko CP17 Layar',Telepon:'0812 1111'})
  await ui.expect(save).toBeDisabled();await review(form,'simpan pelanggan','Pelanggan baru dari layar master');assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await save.click();await done(ui,panel,`Tersimpan: pelanggan ${code} · Toko CP17 Layar dibuat dan langsung bisa dipakai.`)
  let s=seen.created=state(code);assert.deepEqual([s.found,s.name,s.active,s.a,s.history],[true,'Toko CP17 Layar',true,'0812 1111',1])
  const view=panel.locator(`section.cmd-view[aria-label="pelanggan ${code}"]`)
  await view.getByRole('button',{name:'Ubah',exact:true}).click();await form.getByLabel('Nama pelanggan',{exact:true}).fill('Toko CP17 Layar Jaya')
  await review(form,'simpan pelanggan','Nama toko dibetulkan');await save.click();await done(ui,panel,`Tersimpan: perubahan pelanggan ${code} · Toko CP17 Layar Jaya.`)
  s=seen.updated=state(code);assert.deepEqual([s.name,s.history],['Toko CP17 Layar Jaya',2])
  await view.getByRole('button',{name:'Nonaktifkan',exact:true}).click();const off=panel.locator('section.cmd-form[aria-label="Nonaktifkan pelanggan"]')
  await review(off,'nonaktif','Toko tutup permanen');await off.getByRole('button',{name:'Nonaktifkan pelanggan',exact:true}).click()
  await done(ui,panel,`Tersimpan: pelanggan ${code} · Toko CP17 Layar Jaya dinonaktifkan. Transaksi lamanya tetap tercatat.`)
  s=seen.deactivated=state(code);assert.deepEqual([s.active,s.history,s.history_actions],[false,3,['CREATE','UPDATE','DEACTIVATE']])
  // The customer on an open sales draft (Native sales draft from the fixture).
  await panel.getByLabel('Cari pelanggan',{exact:true}).fill(used.code);await panel.getByRole('button',{name:'Cari',exact:true}).click()
  await panel.getByRole('button',{name:`Pilih pelanggan ${used.code}`,exact:true}).click()
  const usedView=panel.locator(`section.cmd-view[aria-label="pelanggan ${used.code}"]`);await ui.expect(usedView).toContainText('Draf penjualan: 1')
  await usedView.getByRole('button',{name:'Nonaktifkan',exact:true}).click()
  await ui.expect(usedView.getByRole('alert')).toContainText('Masih ada 1 draf penjualan untuk pelanggan ini.')
  await ui.expect(usedView.getByRole('button',{name:'Nonaktifkan pelanggan',exact:true})).toHaveCount(0)
  await usedView.getByRole('button',{name:'Batal',exact:true}).click();await usedView.getByRole('button',{name:'Ubah',exact:true}).click()
  await ui.expect(form.getByLabel('Kode',{exact:true})).toBeDisabled();await ui.expect(form).toContainText('Kode tetap karena sudah dipakai transaksi.')
  const u=seen.used=state(used.code);assert.deepEqual([u.active,u.history],[true,0])
  assert.deepEqual(requests.map(([f,r])=>[f,r.p_kind,r.p_payload.action]),[['erp_cp7_save_master_v1','CUSTOMER','CREATE'],['erp_cp7_save_master_v1','CUSTOMER','UPDATE'],['erp_cp7_save_master_v1','CUSTOMER','DEACTIVATE']])
  return{status:'PASS',phone:mobile,created:code,name_corrected:true,deactivated:true,history:3,used_customer_code_locked:true,used_customer_deactivate_blocked_on_screen:'OPEN_SALES_DRAFT',requests:3}
 })
}

// Supplier & Vendor: a supplier of a chosen type, the same code again refused on screen with nothing written, a laundry vendor
// created and deactivated.
async function partners(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_PARTNERS_${mobile?'MOBILE':'DESKTOP'}`,sup='SUP-'+tag(),ven='LDY-'+tag()
 return run(h,ui,name,'master-partners',mobile,async(page,requests,seen)=>{
  await masterPage(ui,page,'Supplier & Vendor');let panel=panelOf(page,'Supplier')
  await panel.getByRole('button',{name:'Tambah supplier',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form supplier"]'),save=form.getByRole('button',{name:'Simpan supplier',exact:true})
  await fill(form,{Kode:sup,'Nama supplier':'Supplier CP17 Layar','Jenis supplier':'ACCESSORY',Telepon:'021 555'});await review(form,'simpan supplier','Supplier baru dari layar')
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await save.click();await done(ui,panel,`Tersimpan: supplier ${sup} · Supplier CP17 Layar dibuat dan langsung bisa dipakai.`)
  let s=seen.supplier=h.fixture('master_state',{kind:'SUPPLIER',code:sup});assert.deepEqual([s.name,s.a,s.active,s.history],['Supplier CP17 Layar','ACCESSORY',true,1])
  await panel.getByRole('button',{name:'Tambah supplier',exact:true}).click()
  await fill(form,{Kode:sup.toLowerCase(),'Nama supplier':'Supplier dobel'});await review(form,'simpan supplier','Supplier dobel dari tab lain');await save.click()
  await ui.expect(panel.getByRole('alert').filter({hasText:'Kode itu sudah dipakai data lain. Pakai kode lain.'})).toBeVisible()
  s=seen.duplicate=h.fixture('master_state',{kind:'SUPPLIER',code:sup});assert.deepEqual([s.count,s.name,s.history],[1,'Supplier CP17 Layar',1])
  await page.getByRole('tab',{name:'Vendor laundry',exact:true}).click();panel=panelOf(page,'Vendor laundry')
  await panel.getByRole('button',{name:'Tambah vendor laundry',exact:true}).click()
  const vform=panel.locator('section.cmd-form[aria-label="Form vendor laundry"]')
  await fill(vform,{Kode:ven,'Nama vendor':'Laundry CP17 Layar',Telepon:'022 777',Catatan:'cuci batu'});await review(vform,'simpan vendor laundry','Vendor laundry baru')
  await vform.getByRole('button',{name:'Simpan vendor laundry',exact:true}).click();await done(ui,panel,`Tersimpan: vendor laundry ${ven} · Laundry CP17 Layar dibuat dan langsung bisa dipakai.`)
  const view=panel.locator(`section.cmd-view[aria-label="vendor laundry ${ven}"]`);await view.getByRole('button',{name:'Nonaktifkan',exact:true}).click()
  const off=panel.locator('section.cmd-form[aria-label="Nonaktifkan vendor laundry"]');await review(off,'nonaktif','Vendor berhenti kerja sama')
  await off.getByRole('button',{name:'Nonaktifkan vendor laundry',exact:true}).click()
  await done(ui,panel,`Tersimpan: vendor laundry ${ven} · Laundry CP17 Layar dinonaktifkan. Transaksi lamanya tetap tercatat.`)
  s=seen.vendor=h.fixture('master_state',{kind:'LAUNDRY_VENDOR',code:ven});assert.deepEqual([s.active,s.b,s.history_actions],[false,'cuci batu',['CREATE','DEACTIVATE']])
  assert.deepEqual(requests.map(([,r])=>[r.p_kind,r.p_payload.action]),[['SUPPLIER','CREATE'],['SUPPLIER','CREATE'],['LAUNDRY_VENDOR','CREATE'],['LAUNDRY_VENDOR','DEACTIVATE']])
  return{status:'PASS',phone:mobile,supplier:sup,supplier_type:'ACCESSORY',duplicate_code_refused_on_screen:true,one_supplier_per_code:true,vendor:ven,vendor_deactivated:true}
 })
}

// Mandor & tarif upah: a Mandor with a dated attendance/Special policy, then on a fresh model a work component, the model's
// work components and a dated rate; an earlier start than the latest version is refused on screen; a stop from a date.
async function workforce(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_WORKFORCE_RATES_${mobile?'MOBILE':'DESKTOP'}`,code='MDR-'+tag(),comp='JHT-'+tag(),model=h.fixture('master_model',{today})
 const d30=day(today,-30),d10=day(today,-10),d8=day(today,-8),d5=day(today,-5),d1=day(today,1)
 return run(h,ui,name,'master-workforce',mobile,async(page,requests,seen)=>{
  await masterPage(ui,page,'Mandor');const panel=panelOf(page,'Mandor')
  await panel.getByRole('button',{name:'Tambah mandor',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form mandor"]'),save=form.getByRole('button',{name:'Simpan mandor',exact:true})
  await fill(form,{Kode:code,'Nama mandor':'Mandor CP17 Layar'});await review(form,'simpan mandor','Mandor baru dari layar')
  await ui.expect(form).toContainText('Tanggal mulai berlaku absensi/Special wajib diisi untuk mandor baru.');await ui.expect(save).toBeDisabled()
  await fill(form,{'Wajib absensi':false,'Absensi/Special berlaku mulai (WIB)':d30});await review(form,'simpan mandor','Mandor baru dari layar')
  await save.click();await done(ui,panel,`Tersimpan: mandor ${code} · Mandor CP17 Layar dibuat dan langsung bisa dipakai.`)
  let s=seen.created=h.fixture('master_state',{kind:'MANDOR',code});assert.deepEqual([s.active,s.a,s.b,s.policies],[true,false,'MANDOR',[[false,d30,null]]])
  const view=panel.locator(`section.cmd-view[aria-label="mandor ${code}"]`);await view.getByRole('button',{name:'Ubah',exact:true}).click()
  await fill(form,{'Mandor Special':true,'Absensi/Special berlaku mulai (WIB)':d5});await review(form,'simpan mandor','Mandor jadi Special mulai tanggal itu')
  await save.click();await done(ui,panel,`Tersimpan: perubahan mandor ${code} · Mandor CP17 Layar.`)
  s=seen.special=h.fixture('master_state',{kind:'MANDOR',code});assert.deepEqual(s.policies,[[false,d30,day(today,-6)],[true,d5,null]])
  await ui.expect(panel.getByRole('button',{name:`Pilih mandor ${code}`,exact:true})).toContainText('Special')
  // Rates on a fresh model with no work components yet.
  const rates=page.getByRole('region',{name:'Tarif upah mandor',exact:true});await ui.expect(rates).toContainText(`Mandor: ${code} · Mandor CP17 Layar · Special`)
  await rates.getByLabel('Cari model',{exact:true}).fill(model.code);await rates.getByRole('button',{name:'Cari model',exact:true}).click()
  await rates.getByRole('button',{name:`Pilih model ${model.code}`,exact:true}).click();await ui.expect(rates).toContainText('Belum ada komponen kerja yang berlaku.')
  const nc=rates.locator('section.cmd-form[aria-label="Komponen kerja baru"]')
  await fill(nc,{'Kode komponen kerja':comp,'Nama komponen kerja':'Jahit layar','Jenis komponen kerja':'LABOR','Alasan komponen kerja baru':'Komponen kerja baru dari layar'})
  await nc.getByRole('button',{name:'Tambah komponen kerja',exact:true}).click();await done(ui,rates,`Tersimpan: komponen kerja ${comp} dibuat.`)
  await rates.getByRole('button',{name:'Ubah komponen kerja model',exact:true}).click();const bom=rates.locator('section.cmd-form[aria-label="Komponen kerja model"]')
  await bom.getByRole('button',{name:'Tambah baris komponen',exact:true}).click()
  await fill(bom,{'Komponen 1':{label:`${comp} · Jahit layar`},'Tarif bawaan 1':'2','Komponen kerja berlaku mulai':d10,'Alasan komponen kerja':'Komponen kerja model dari layar'})
  await bom.getByLabel('Komponen kerja sudah diperiksa',{exact:true}).check();await bom.getByRole('button',{name:'Simpan komponen kerja model',exact:true}).click()
  await done(ui,rates,'Tersimpan: komponen kerja model diperbarui.')
  const row=rates.getByRole('region',{name:`Tarif upah ${comp}`,exact:true});await ui.expect(row).toContainText('upah memakai tarif bawaan model Rp2/pcs')
  const rate=async(value,date,why)=>{await fill(row,{[`Tarif ${comp}`]:value,[`Tarif ${comp} berlaku mulai`]:date,[`Alasan tarif ${comp}`]:why});await row.getByLabel(`Tarif ${comp} sudah diperiksa`,{exact:true}).check()}
  await rate('1500',d5,'Tarif mandor baru');await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await row.getByRole('button',{name:`Simpan tarif ${comp}`,exact:true}).click();await done(ui,rates,`Tersimpan: tarif Rp1.500/pcs berlaku mulai ${d5}.`)
  await ui.expect(row).toContainText(`Berlaku sekarang: Rp1.500/pcs sejak ${d5}`)
  await rate('1400',d8,'Sisip tarif lebih awal');await row.getByRole('button',{name:`Simpan tarif ${comp}`,exact:true}).click()
  await ui.expect(rates.getByRole('alert').filter({hasText:'Sudah ada tarif yang mulai lebih lambat.'})).toBeVisible()
  let r=seen.after_refusal=h.fixture('rate_state',{mandor_code:code,model:model.model});assert.deepEqual(r.rates,[[comp,'1500.00',d5,null]])
  await rate('1500',d1,'Mandor berhenti model ini');await row.getByRole('button',{name:`Hentikan tarif ${comp} mulai tanggal itu`,exact:true}).click()
  await done(ui,rates,`Tersimpan: tarif berhenti mulai ${d1}.`)
  r=seen.rates=h.fixture('rate_state',{mandor_code:code,model:model.model});assert.deepEqual(r,{rates:[[comp,'1500.00',d5,d1]],bom:[[1,d10,comp,'2.00']]})
  assert.deepEqual(requests.map(([f,p])=>f==='erp_cp7_save_master_v1'?p.p_payload.action:p.p_action),['CREATE','UPDATE','CREATE_COMPONENT','SAVE_BOM','SET_RATE','SET_RATE','STOP_RATE'])
  return{status:'PASS',phone:mobile,mandor:code,special_from:d5,component:comp,model:model.code,bom_from:d10,rate:'1500 from '+d5,earlier_start_refused_on_screen:true,stopped_from:d1}
 })
}

// Gudang & Lokasi: create, change the type while unused, deactivate; a stocked warehouse keeps its code and type and cannot
// be deactivated, and the screen says why.
async function locations(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_LOCATIONS_${mobile?'MOBILE':'DESKTOP'}`,code='GDG-'+tag(),stocked=h.fixture('master_stocked_location',{today})
 return run(h,ui,name,'master-locations',mobile,async(page,requests,seen)=>{
  await masterPage(ui,page,'Gudang & Lokasi');const panel=panelOf(page,'Gudang & lokasi')
  await panel.getByRole('button',{name:'Tambah gudang/lokasi',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form gudang/lokasi"]'),save=form.getByRole('button',{name:'Simpan gudang/lokasi',exact:true})
  await fill(form,{Kode:code,'Nama lokasi':'Gudang CP17 Layar','Jenis lokasi':'RAW_MATERIAL_WAREHOUSE'});await review(form,'simpan gudang/lokasi','Gudang baru dari layar')
  await save.click();await done(ui,panel,`Tersimpan: gudang/lokasi ${code} · Gudang CP17 Layar dibuat dan langsung bisa dipakai.`)
  const view=panel.locator(`section.cmd-view[aria-label="gudang/lokasi ${code}"]`);await view.getByRole('button',{name:'Ubah',exact:true}).click()
  await fill(form,{'Jenis lokasi':'FG_WAREHOUSE'});await review(form,'simpan gudang/lokasi','Belum dipakai, jenis dibetulkan');await save.click()
  await done(ui,panel,`Tersimpan: perubahan gudang/lokasi ${code} · Gudang CP17 Layar.`)
  let s=seen.changed=h.fixture('master_state',{kind:'LOCATION',code});assert.deepEqual([s.a,s.active],['FG_WAREHOUSE',true])
  await view.getByRole('button',{name:'Nonaktifkan',exact:true}).click();const off=panel.locator('section.cmd-form[aria-label="Nonaktifkan gudang/lokasi"]')
  await review(off,'nonaktif','Gudang tidak dipakai lagi');await off.getByRole('button',{name:'Nonaktifkan gudang/lokasi',exact:true}).click()
  await done(ui,panel,`Tersimpan: gudang/lokasi ${code} · Gudang CP17 Layar dinonaktifkan. Transaksi lamanya tetap tercatat.`)
  s=seen.deactivated=h.fixture('master_state',{kind:'LOCATION',code});assert.deepEqual([s.active,s.history_actions],[false,['CREATE','UPDATE','DEACTIVATE']])
  await panel.getByLabel('Cari gudang/lokasi',{exact:true}).fill(stocked.code);await panel.getByRole('button',{name:'Cari',exact:true}).click()
  await panel.getByRole('button',{name:`Pilih gudang/lokasi ${stocked.code}`,exact:true}).click()
  const sv=panel.locator(`section.cmd-view[aria-label="gudang/lokasi ${stocked.code}"]`);await sv.getByRole('button',{name:'Nonaktifkan',exact:true}).click()
  await ui.expect(sv.getByRole('alert')).toContainText('Lokasi masih berisi stok');await sv.getByRole('button',{name:'Batal',exact:true}).click()
  await sv.getByRole('button',{name:'Ubah',exact:true}).click();await ui.expect(form.getByLabel('Kode',{exact:true})).toBeDisabled()
  await fill(form,{'Jenis lokasi':'OTHER'});await review(form,'simpan gudang/lokasi','Coba ganti jenis gudang berisi stok');await save.click()
  await ui.expect(panel.getByRole('alert').filter({hasText:'Jenis lokasi tidak bisa diganti karena lokasi ini sudah punya mutasi stok'})).toBeVisible()
  s=seen.stocked=h.fixture('master_state',{kind:'LOCATION',code:stocked.code});assert.deepEqual([s.a,s.active,s.history],['RAW_MATERIAL_WAREHOUSE',true,0])
  assert.deepEqual(requests.map(([,r])=>r.p_payload.action),['CREATE','UPDATE','DEACTIVATE','UPDATE'])
  return{status:'PASS',phone:mobile,created:code,type_changed_while_unused:'FG_WAREHOUSE',deactivated:true,stocked_location_code_locked:true,stocked_deactivate_blocked_on_screen:true,stocked_type_change_refused_unchanged:true}
 })
}

// Kain & harga acuan: a fabric with its profile, the name and code locked in the edit form (renamed only through the audited
// rename), the width corrected, a benchmark price from today.
async function fabric(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_FABRIC_${mobile?'MOBILE':'DESKTOP'}`,code='KAIN-'+tag()
 return run(h,ui,name,'master-fabric',mobile,async(page,requests,seen)=>{
  await masterPage(ui,page,'Kain & Benchmark');const panel=panelOf(page,'Kain')
  await panel.getByRole('button',{name:'Tambah kain',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form kain"]'),save=form.getByRole('button',{name:'Simpan kain',exact:true})
  const unit=await form.getByLabel('Satuan',{exact:true}).locator('option').nth(1).getAttribute('value');assert.ok(unit)
  await fill(form,{'Kode kain':code,'Nama kain':'Kain CP17 Layar',Satuan:unit,Kategori:'Denim',Warna:'Indigo','Lebar (cm)':'150'})
  await review(form,'simpan kain','Kain baru dari layar');await save.click();await done(ui,panel,`Tersimpan: kain ${code} · Kain CP17 Layar dibuat dan langsung bisa dipakai.`)
  let s=seen.created=h.fixture('master_state',{kind:'FABRIC',code});assert.deepEqual([s.a,s.active,s.profile],[unit,true,['150.000','Indigo','Denim',null]])
  const view=panel.locator(`section.cmd-view[aria-label="kain ${code}"]`);await view.getByRole('button',{name:'Ubah',exact:true}).click()
  await ui.expect(form.getByLabel('Kode kain',{exact:true})).toBeDisabled();await ui.expect(form.getByLabel('Nama kain',{exact:true})).toBeDisabled()
  await ui.expect(form).toContainText('Nama dan kode bahan dibetulkan lewat "Benerin nama bahan".')
  await fill(form,{'Lebar (cm)':'152.5',Komposisi:'Katun 100%'});await review(form,'simpan kain','Lebar diukur ulang');await save.click()
  await done(ui,panel,`Tersimpan: perubahan kain ${code} · Kain CP17 Layar.`)
  s=seen.updated=h.fixture('master_state',{kind:'FABRIC',code});assert.deepEqual(s.profile,['152.500','Indigo','Denim','Katun 100%'])
  await view.getByRole('button',{name:'Harga acuan baru',exact:true}).click();const price=panel.locator('section.cmd-form[aria-label="Harga acuan baru"]')
  await ui.expect(price.getByLabel('Harga berlaku mulai',{exact:true})).toHaveValue(today)
  await fill(price,{'Harga acuan':'48500'});await review(price,'harga acuan','Harga acuan bulan ini');await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await price.getByRole('button',{name:'Simpan harga acuan',exact:true}).click();await done(ui,panel,`Tersimpan: harga acuan baru untuk kain ${code} · Kain CP17 Layar.`)
  await ui.expect(view).toContainText(`Rp48.500/${unit} mulai ${today}`)
  s=seen.priced=h.fixture('master_state',{kind:'FABRIC',code});assert.deepEqual([s.benchmarks,s.history_actions],[[['48500.000000',today]],['CREATE','UPDATE','SET_BENCHMARK']])
  assert.deepEqual(requests.map(([,r])=>r.p_payload.action),['CREATE','UPDATE','SET_BENCHMARK'])
  return{status:'PASS',phone:mobile,fabric:code,unit,profile_saved:true,name_code_locked_in_edit:true,width_corrected:'152.500',benchmark:'48500 from '+today}
 })
}

// Aksesori & harga mandor: a category in PCS with a general Mandor price, a variant under it, and the category refused
// deactivation while its variant is active.
async function accessory(ui,today,mobile,h){
 const name=`CP17_R2_MASTER_ACCESSORY_${mobile?'MOBILE':'DESKTOP'}`,cat='KCG-'+tag(),variant=cat+'-HITAM'
 return run(h,ui,name,'master-accessory',mobile,async(page,requests,seen)=>{
  await masterPage(ui,page,'Aksesori & Harga Mandor');let panel=panelOf(page,'Kategori aksesori')
  await panel.getByRole('button',{name:'Tambah kategori aksesori',exact:true}).click()
  const form=panel.locator('section.cmd-form[aria-label="Form kategori aksesori"]')
  await fill(form,{'Kode kategori':cat,'Nama kategori':'Kancing CP17 Layar','Satuan dasar':'PCS'});await review(form,'simpan kategori aksesori','Kategori aksesori baru')
  await form.getByRole('button',{name:'Simpan kategori aksesori',exact:true}).click();await done(ui,panel,`Tersimpan: kategori aksesori ${cat} · Kancing CP17 Layar dibuat dan langsung bisa dipakai.`)
  const view=panel.locator(`section.cmd-view[aria-label="kategori aksesori ${cat}"]`);await view.getByRole('button',{name:'Harga ke mandor',exact:true}).click()
  const price=panel.locator('section.cmd-form[aria-label="Harga aksesori ke mandor"]')
  await ui.expect(price.getByLabel('Satuan harga ke mandor',{exact:true})).toHaveValue('PCS')
  await fill(price,{'Harga ke mandor':'495'});await review(price,'harga ke mandor','Harga mandor umum')
  await price.getByRole('button',{name:'Simpan harga ke mandor',exact:true}).click()
  await done(ui,panel,`Tersimpan: harga aksesori ke mandor untuk kategori aksesori ${cat} · Kancing CP17 Layar.`)
  let s=seen.category=h.fixture('master_state',{kind:'ACCESSORY_CATEGORY',code:cat});assert.deepEqual([s.a,s.prices],['PCS',[[null,'495.0000','PCS']]])
  await page.getByRole('tab',{name:'Varian aksesori',exact:true}).click();panel=panelOf(page,'Varian aksesori')
  await panel.getByRole('button',{name:'Tambah varian aksesori',exact:true}).click();const vform=panel.locator('section.cmd-form[aria-label="Form varian aksesori"]')
  await fill(vform,{'Kode varian':variant,'Nama varian':'Kancing hitam layar',Kategori:{label:`${cat} · Kancing CP17 Layar`}});await review(vform,'simpan varian aksesori','Varian kancing baru')
  await vform.getByRole('button',{name:'Simpan varian aksesori',exact:true}).click();await done(ui,panel,`Tersimpan: varian aksesori ${variant} · Kancing hitam layar dibuat dan langsung bisa dipakai.`)
  s=seen.variant=h.fixture('master_state',{kind:'ACCESSORY',code:variant});assert.deepEqual([s.a,s.active],[seen.category.id,true])
  await page.getByRole('tab',{name:'Kategori aksesori',exact:true}).click();panel=panelOf(page,'Kategori aksesori')
  await panel.getByLabel('Cari kategori aksesori',{exact:true}).fill(cat);await panel.getByRole('button',{name:'Cari',exact:true}).click()
  await panel.getByRole('button',{name:`Pilih kategori aksesori ${cat}`,exact:true}).click()
  const cv=panel.locator(`section.cmd-view[aria-label="kategori aksesori ${cat}"]`);await cv.getByRole('button',{name:'Nonaktifkan',exact:true}).click()
  await ui.expect(cv.getByRole('alert')).toContainText('Kategori ini masih punya 1 varian aktif. Nonaktifkan variannya dulu.')
  s=seen.blocked=h.fixture('master_state',{kind:'ACCESSORY_CATEGORY',code:cat});assert.deepEqual([s.active,s.active_variants],[true,1])
  assert.deepEqual(requests.map(([,r])=>[r.p_kind,r.p_payload.action]),[['ACCESSORY_CATEGORY','CREATE'],['ACCESSORY_CATEGORY','SET_MANDOR_PRICE'],['ACCESSORY','CREATE']])
  return{status:'PASS',phone:mobile,category:cat,mandor_price:'495/PCS for every Mandor',variant,category_with_active_variant_blocked_on_screen:true}
 })
}

// Fable D15-3 chain, screens only: a new Mandor and his rates (Master Data), Bagi Potongan to him, "Catat selesai jahit" on
// the cutting day. Rates: from the cutting day, and a higher one for the first component from today; the screen must preview
// and the wage must pay the cutting-day rate. A rate saved afterwards leaves the recorded wage unchanged.
async function chain(ui,today,h){
 const name='CP17_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP',f=h.fixture('chain',{today}),code='MDR-'+tag(),fmt=n=>'Rp'+n.toLocaleString('id-ID')
 return run(h,ui,name,'chain-d15-3',false,async(page,requests,seen)=>{
  // The model's work components valid on the sewing day are the ones valid now (fixture assumption, checked, not relied on).
  assert.deepEqual(f.bom_now,f.bom_at_sewing,'CP17_D15_3_CHAIN_BOM_CHANGES_BETWEEN_SEWING_AND_NOW')
  await masterPage(ui,page,'Mandor');const panel=panelOf(page,'Mandor')
  await panel.getByRole('button',{name:'Tambah mandor',exact:true}).click();const form=panel.locator('section.cmd-form[aria-label="Form mandor"]')
  await fill(form,{Kode:code,'Nama mandor':'Mandor Rantai CP17','Wajib absensi':false,'Absensi/Special berlaku mulai (WIB)':day(f.day,-30)})
  await review(form,'simpan mandor','Mandor baru dari layar master');await form.getByRole('button',{name:'Simpan mandor',exact:true}).click()
  await done(ui,panel,`Tersimpan: mandor ${code} · Mandor Rantai CP17 dibuat dan langsung bisa dipakai.`)
  const rates=page.getByRole('region',{name:'Tarif upah mandor',exact:true});await ui.expect(rates).toContainText(`Mandor: ${code} · Mandor Rantai CP17`)
  await rates.getByLabel('Cari model',{exact:true}).fill(f.model_code);await rates.getByRole('button',{name:'Cari model',exact:true}).click()
  await rates.getByRole('button',{name:`Pilih model ${f.model_code}`,exact:true}).click()
  let components=f.bom_at_sewing,bomMade=false
  if(!components.length){
   // No work components for the model yet: one through the rate screen, valid from the day before the cutting.
   const comp='JHT-'+tag(),nc=rates.locator('section.cmd-form[aria-label="Komponen kerja baru"]')
   await fill(nc,{'Kode komponen kerja':comp,'Nama komponen kerja':'Jahit rantai','Jenis komponen kerja':'LABOR','Alasan komponen kerja baru':'Komponen kerja model baru'})
   await nc.getByRole('button',{name:'Tambah komponen kerja',exact:true}).click();await done(ui,rates,`Tersimpan: komponen kerja ${comp} dibuat.`)
   await rates.getByRole('button',{name:'Ubah komponen kerja model',exact:true}).click();const bom=rates.locator('section.cmd-form[aria-label="Komponen kerja model"]')
   await bom.getByRole('button',{name:'Tambah baris komponen',exact:true}).click()
   await fill(bom,{'Komponen 1':{label:`${comp} · Jahit rantai`},'Tarif bawaan 1':'2','Komponen kerja berlaku mulai':day(f.day,-1),'Alasan komponen kerja':'Komponen kerja model dari layar'})
   await bom.getByLabel('Komponen kerja sudah diperiksa',{exact:true}).check();await bom.getByRole('button',{name:'Simpan komponen kerja model',exact:true}).click()
   await done(ui,rates,'Tersimpan: komponen kerja model diperbarui.');components=[comp];bomMade=true
  }
  const typed=Object.fromEntries(components.map((c,i)=>[c,i===0?1500:500])),per=Object.values(typed).reduce((a,b)=>a+b,0)
  const setRate=async(c,value,date,why)=>{
   const row=rates.getByRole('region',{name:`Tarif upah ${c}`,exact:true})
   await fill(row,{[`Tarif ${c}`]:String(value),[`Tarif ${c} berlaku mulai`]:date,[`Alasan tarif ${c}`]:why});await row.getByLabel(`Tarif ${c} sudah diperiksa`,{exact:true}).check()
   await row.getByRole('button',{name:`Simpan tarif ${c}`,exact:true}).click()
  }
  for(const c of components){await setRate(c,typed[c],f.day,'Tarif mandor baru');await done(ui,rates,`Tersimpan: tarif ${fmt(typed[c])}/pcs berlaku mulai ${f.day}.`)}
  await setRate(components[0],1700,today,'Tarif naik mulai hari ini');await done(ui,rates,`Tersimpan: tarif ${fmt(1700)}/pcs berlaku mulai ${today}.`)
  seen.rates=h.fixture('rate_state',{mandor_code:code,model:f.model})
  // Bagi Potongan to the new Mandor, on the cutting day.
  await h.openGroup(ui,page,f.number,f.group)
  const setup=page.locator('.cpick-setup')
  await setup.locator('select').first().selectOption({label:`${code} · Mandor Rantai CP17`})
  await setup.locator('input[type="datetime-local"]').fill(`${f.day}T09:00`)
  const fewer=setup.getByRole('button',{name:'−',exact:true});while(await fewer.isEnabled())await fewer.click()
  await page.getByLabel(`${f.roll_number} ${f.size_code} Batch 1`,{exact:true}).fill('10')
  await page.getByRole('button',{name:'Catat pickup & masuk Sewing',exact:true}).click()
  await ui.expect(page.getByText('Pickup terposting · 1 batch / 10 pcs masuk Sewing.')).toBeVisible()
  let s=seen.picked=h.fixture('chain_state',f);assert.deepEqual([s.po_mandor,s.posted_pickups,s.sewn,s.posted_work],[code,1,0,0])
  // Catat selesai jahit on the cutting day: the cutting-day rates, not today's.
  await h.wipPage(ui,page);await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
  const card=page.locator('.cwip-list>article').filter({hasText:f.number});await ui.expect(card).toHaveCount(1)
  const sew=card.getByRole('region',{name:'Selesai jahit '+f.number,exact:true});await sew.getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await sew.getByLabel('Waktu selesai jahit '+f.number,{exact:true}).fill(`${f.day}T10:00`)
  await ui.expect(sew).toContainText(`= ${fmt(per)}.`);await ui.expect(sew).not.toContainText(`= ${fmt(per+200)}.`)
  await sew.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('10');await ui.expect(sew).toContainText(`Upah yang akan dicatat: 10 pcs × ${fmt(per)} = ${fmt(per*10)}.`)
  await sew.getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Setoran jahit mandor baru');await sew.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await sew.getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
  await ui.expect(page.getByText(`${f.number}: 10 pcs tercatat selesai dijahit. Upah mandor ${fmt(per*10)} masuk hutang mandor; 10 pcs siap dikirim ke laundry.`)).toBeVisible()
  s=seen.sewn=h.fixture('chain_state',f)
  assert.deepEqual([s.sewn,s.posted_work,s.wage],[10,1,[[(per*10).toFixed(2),(per*10).toFixed(2),'1']]])
  assert.deepEqual(s.snapshots.map(([c,r])=>[c,Number(r)]),components.map(c=>[c,typed[c]]))
  // A rate saved afterwards (the unused version from today corrected) does not touch the recorded wage.
  await masterPage(ui,page,'Mandor');await panel.getByLabel('Cari mandor',{exact:true}).fill(code);await panel.getByRole('button',{name:'Cari',exact:true}).click()
  await panel.getByRole('button',{name:`Pilih mandor ${code}`,exact:true}).click();await ui.expect(rates).toContainText(`Mandor: ${code}`)
  await rates.getByLabel('Cari model',{exact:true}).fill(f.model_code);await rates.getByRole('button',{name:'Cari model',exact:true}).click()
  await rates.getByRole('button',{name:`Pilih model ${f.model_code}`,exact:true}).click()
  await ui.expect(rates.getByRole('region',{name:`Tarif upah ${components[0]}`,exact:true})).toContainText(`dipakai upah sampai ${f.day}`)
  await setRate(components[0],1500,f.day,'Ubah tarif yang sudah dipakai');await ui.expect(rates.getByRole('alert').filter({hasText:'sudah dipakai upah'})).toBeVisible()
  await setRate(components[0],1800,today,'Tarif hari ini dibetulkan');await done(ui,rates,`Tersimpan: tarif ${fmt(1800)}/pcs berlaku mulai ${today}.`)
  const after=seen.after=h.fixture('chain_state',f);assert.deepEqual([after.wage,after.snapshots],[s.wage,s.snapshots])
  return{status:'PASS',owner_decision:'D15-3',mandor_from_master_screen:code,bom_written_from_rate_screen:bomMade,rates_from_cutting_day:typed,later_rate_from_today:1700,
   pickup_from_bagi_potongan_screen:true,screen_preview_per_pcs:per,wage:(per*10).toFixed(2),used_rate_change_refused_on_screen:true,later_correction_keeps_wage:true}
 })
}

export function cases(ui,today,h){
 const screens=[['CUSTOMERS',customers],['PARTNERS',partners],['WORKFORCE_RATES',workforce],['LOCATIONS',locations],['FABRIC',fabric],['ACCESSORY',accessory]]
 return[...screens.flatMap(([id,fn])=>[[`CP17_BROWSER_R2_MASTER_${id}_DESKTOP`,()=>fn(ui,today,false,h)],[`CP17_BROWSER_R2_MASTER_${id}_MOBILE`,()=>fn(ui,today,true,h)]]),
  ['CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP',()=>chain(ui,today,h)]]
}
