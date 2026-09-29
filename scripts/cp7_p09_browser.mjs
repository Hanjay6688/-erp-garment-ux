import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import assert from 'node:assert/strict'
const fixture = (op,payload) => JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p09_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p,materials=false) {
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:materials==='count'?'• Stock Adjustment':materials?'• Bahan & Roll':'• Pembelian & Penerimaan',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:materials==='count'?'Penyesuaian bahan':materials?'Bahan & roll':'Pembelian & penerimaan',exact:true})).toBeVisible()
}

async function receipt(ui,today,mobile) {
 const f=fixture('create',{today}),user=await ui.login('OWNER',{label:'cp7-p09-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try {
  const p=user.page;await openPage(ui,p)
  const create=p.getByRole('button',{name:'Penerimaan baru',exact:true});await ui.expect(create).toBeEnabled();await create.click()
  await p.getByLabel('Nomor surat jalan',{exact:true}).fill(f.tag)
  await p.getByLabel('Waktu barang datang WIB',{exact:true}).fill(f.day+'T10:00')
  async function choose(label,query,id) {
   const search=p.getByLabel('Cari '+label,{exact:true});await search.fill(query);await search.press('Enter')
   const select=p.getByLabel(label,{exact:true});await ui.expect(select.locator(`option[value="${id}"]`)).toBeAttached();await ui.expect(select).toBeEnabled();await select.selectOption(id)
  }
  await choose('Supplier penerimaan',f.supplier_name,f.payload.supplier_id)
  await choose('Gudang penerimaan',f.tag,f.location)
  await choose('Bahan 1',f.material_code,f.material)
  await p.getByLabel('Jumlah barang 1',{exact:true}).fill('10')
  await p.getByLabel('Nomor roll 1.1',{exact:true}).fill(f.tag+'-ROLL')
  await p.getByLabel('Jumlah roll 1.1',{exact:true}).fill('10')
  await p.getByLabel('Dasar harga 1',{exact:true}).selectOption('MANUAL_ESTIMATE')
  await p.getByLabel('Harga barang 1',{exact:true}).fill('10')
  await p.getByRole('button',{name:'Simpan draft penerimaan',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).document?.status,{timeout:20000}).toBe('DRAFT')
  let read=fixture('read',f);if(Number(read.qty)!==0||read.movement_count!==0)throw Error('Draft unexpectedly changed stock')
  const post=p.getByRole('button',{name:'Sahkan penerimaan ke gudang',exact:true});await ui.expect(post).toBeEnabled()
  let lost=false,firstRequest=null,replayedRequest=null
  const route='**/rest/v1/rpc/erp_cp7_save_procurement_v1'
  if(mobile)await p.route(route,async handler=>{
   const body=handler.request().postDataJSON()
   if(body.p_action==='POST'&&!lost){firstRequest=body;const reply=await handler.fetch();if(reply.status()!==200)throw Error('Expected committed POST before lost reply');lost=true;await handler.abort('failed')}
   else {if(body.p_action==='POST')replayedRequest=body;await handler.continue()}
  })
  await post.click()
  await ui.expect.poll(()=>fixture('read',f).document?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()}
  await ui.expect(p.locator('.cproc-detail')).toContainText('Penerimaan sudah tercatat',{timeout:20000})
  read=fixture('read',f)
  if(Date.parse(read.document.physical_at)!==Date.parse(f.payload.physical_at))throw Error('Receipt did not preserve WIB business time')
  if(Number(read.qty)!==10||read.movement_count!==1||Number(read.document.ap)!==0||Number(read.document.grni)!==100||read.contexts!==0)throw Error('Receipt stock/value/context read-back mismatch '+JSON.stringify(read))
  if(mobile&&(!lost||JSON.stringify(firstRequest)!==JSON.stringify(replayedRequest)))throw Error('Recovery did not reuse the identical request')
  await ui.expect.poll(()=>p.locator('.cproc').evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0))
  mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:`cp6-proof/t3/P09_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,qty:read.qty,stock_movements:1,grni:read.document.grni,final_ap:read.document.ap,recovery_identical_request:mobile?true:null,browser_timezone:mobile?'America/Los_Angeles':'Asia/Jakarta',screenshot:`P09_${mobile?'MOBILE':'DESKTOP'}.png`}
 } finally {await user.context.close()}
}
async function transfer(ui,today,mobile,kind='FABRIC') {
 const f=fixture(kind==='FABRIC'?'create_transfer':'create_transfer_unrolled',{today,kind}),user=await ui.login('OWNER',{label:'cp7-material-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try {
  const p=user.page;await openPage(ui,p,true)
  await p.getByLabel('Cari stok bahan',{exact:true}).fill(f.material_code);await p.getByRole('button',{name:'Cari stok',exact:true}).click()
  const roll=kind==='FABRIC'?f.tag+'-R':f.material_name
  const source=p.locator('.cmat-roll').filter({hasText:f.material_code})
  await ui.expect(source).toHaveCount(1)
  await ui.expect(source.getByRole('button',{name:'Pindahkan '+roll,exact:true})).toBeEnabled()
  await source.getByRole('button',{name:'Mutasi '+roll,exact:true}).click();await ui.expect(p.locator('.cmat-ledger')).toContainText('Saldo 10')
  await source.getByRole('button',{name:'Pindahkan '+roll,exact:true}).click()
  await p.getByLabel('Nomor transfer',{exact:true}).fill(f.tag+'-UI-TRANSFER')
  await p.getByLabel('Waktu transfer WIB',{exact:true}).fill(f.day+'T11:00')
  const search=p.getByLabel('Cari gudang tujuan',{exact:true});await search.fill(f.tag+'-TO');await search.press('Enter')
  const select=p.getByLabel('Gudang tujuan transfer',{exact:true});await ui.expect(select.locator(`option[value="${f.destination}"]`)).toBeAttached();await ui.expect(select).toBeEnabled();await select.selectOption(f.destination)
  await p.getByLabel('Jumlah transfer',{exact:true}).fill('4')
  await p.getByRole('button',{name:'Simpan draft transfer',exact:true}).click()
  await ui.expect.poll(()=>fixture('read_transfer',f).document?.status,{timeout:20000}).toBe('DRAFT')
  let read=fixture('read_transfer',f);if(Number(read.balances[f.location])!==10||Number(read.balances[f.destination]??0)!==0||read.document.movements!==0)throw Error('Draft transfer moved stock')
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_materials_v1',async handler=>{
   const body=handler.request().postDataJSON()
   if(body.p_action==='POST_TRANSFER'&&!lost){first=body;const response=await handler.fetch();if(response.status()!==200){await handler.fulfill({response});return}lost=true;await handler.abort('failed')}
   else{if(body.p_action==='POST_TRANSFER')replay=body;await handler.continue()}
  })
  const post=p.getByRole('button',{name:'Sahkan perpindahan stok',exact:true});await ui.expect(post).toBeEnabled();await post.click()
  await ui.expect.poll(()=>fixture('read_transfer',f).document?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p,true);await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()}
  await ui.expect(p.locator('.cmat-transfer-detail')).toContainText('Stok sudah dipindahkan',{timeout:20000})
  read=fixture('read_transfer',f)
  if(Number(read.balances[f.location])!==6||Number(read.balances[f.destination])!==4||read.document.movements!==2||Number(read.document.net_qty)!==0||Number(read.document.net_value)!==0||Number(read.total_value)!==100||read.contexts!==0)throw Error('Transfer native conservation mismatch '+JSON.stringify(read))
  if(Date.parse(read.document.physical_at)!==Date.parse(f.day+'T11:00:00+07:00'))throw Error('Transfer WIB time changed')
  if(mobile&&(!lost||JSON.stringify(first)!==JSON.stringify(replay)))throw Error('Transfer recovery created another request')
  await p.getByRole('button',{name:'Stok per gudang',exact:true}).click()
  await p.getByLabel('Cari stok bahan',{exact:true}).fill(f.material_code);await p.getByRole('button',{name:'Cari stok',exact:true}).click()
  await ui.expect(p.locator('.cmat-roll')).toHaveCount(2);await ui.expect(p.locator('.cmat-roll').filter({hasText:f.tag+' destination'})).toContainText('4 '+f.unit)
  await ui.expect.poll(()=>p.locator('.cmat').evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_MATERIAL_${kind==='FABRIC'?'':kind+'_'}${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await p.getByRole('button',{name:'Transfer gudang',exact:true}).click()
  await p.getByLabel('Saya sudah memeriksa alasan pembatalan transfer ini.',{exact:true}).check()
  await p.getByLabel('Catatan transfer',{exact:true}).fill('Barang kembali ke gudang asal sesuai pemeriksaan')
  await p.getByRole('button',{name:'Batalkan transfer',exact:true}).click()
  await ui.expect(p.locator('.cmat-transfer-detail')).toContainText('Transfer sudah dibatalkan',{timeout:20000})
  read=fixture('read_transfer',f)
  if(Number(read.balances[f.location])!==10||Number(read.balances[f.destination])!==0||read.document.movements!==4||Number(read.total_value)!==100)throw Error('Transfer reverse native mismatch')
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,draft_no_stock:true,posted_source:6,posted_destination:4,total_value:100,transfer_net_value:0,reversed_source:10,reversed_destination:0,movements_with_inverse:4,recovery_identical_request:mobile?true:null,screenshot:`P09_MATERIAL_${kind==='FABRIC'?'':kind+'_'}${mobile?'MOBILE':'DESKTOP'}.png`}
 } finally {await user.context.close()}
}
async function supplierInvoice(ui,today,mobile) {
 const f=fixture('create_invoice',{today}),user=await ui.login('OWNER',{label:'cp7-invoice-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try {
  const p=user.page;await openPage(ui,p)
  await p.getByLabel('Cari penerimaan',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari penerimaan',exact:true}).click()
  const receipt=p.locator('.cproc-receipt').filter({hasText:f.tag});await ui.expect(receipt).toHaveCount(1);await ui.expect(receipt).toBeEnabled();await receipt.click()
  const panel=p.locator('.cproc-invoices');await ui.expect(panel).toContainText('Penerimaan '+f.tag)
  async function enter(n,qty,price) {
   const add=panel.getByRole('button',{name:'Catat invoice supplier',exact:true});await ui.expect(add).toBeEnabled();await add.click()
   await panel.getByLabel('Nomor invoice supplier',{exact:true}).fill(f.tag+'-UI-INVOICE-'+n)
   await panel.getByLabel('Tanggal invoice supplier',{exact:true}).fill(f.day)
   await panel.getByLabel('Waktu invoice diterima WIB',{exact:true}).fill(f.invoice_received_day+'T15:00')
   await panel.getByLabel('Jumlah invoice 1',{exact:true}).fill(qty)
   await panel.getByLabel('Harga invoice 1',{exact:true}).fill(price)
   const post=panel.getByRole('button',{name:'Sahkan invoice supplier',exact:true});await ui.expect(post).toBeDisabled()
   await panel.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await ui.expect(post).toBeEnabled()
   return post
  }
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_purchase_invoice_v1',async handler=>{
   const body=handler.request().postDataJSON()
   if(body.p_action==='FINALIZE'&&!lost){first=body;const response=await handler.fetch();if(response.status()!==200)throw Error('Expected committed invoice before lost reply');lost=true;await handler.abort('failed')}
   else{if(body.p_action==='FINALIZE'&&replay===null)replay=body;await handler.continue()}
  })
  const firstPost=await enter(1,'4','12.5');await firstPost.click()
  await ui.expect.poll(()=>fixture('read_invoice',f).invoices.length,{timeout:20000}).toBe(1)
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()}
  await ui.expect(panel).toContainText('Nilai dokumen Rp50',{timeout:20000})
  function verify(expectedAp,expectedGrni,expectedValue,count) {
   const r=fixture('read_invoice',f)
   if(Number(r.document_ap)!==expectedAp||Number(r.grni)!==expectedGrni||Number(r.ap_gl)!==expectedAp||Number(r.material_value)!==expectedValue||Number(r.qty)!==10||Number(r.balances[f.location])!==6||Number(r.balances[f.destination])!==4||r.invoices.length!==count)throw Error('Invoice native conservation mismatch '+JSON.stringify(r))
   for(const d of r.invoices)if(Date.parse(d.received_at)!==Date.parse(f.invoice_received_day+'T15:00:00+07:00'))throw Error('Invoice received WIB time changed')
   return r
  }
  verify(50,60,110,1)
  if(mobile){
   // Invoice data can already be visible from the reload's read before the
   // replay response arrives. Wait for the completed recovery, not that data.
   await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
   await ui.expect(panel).toContainText('Invoice supplier sudah diperbarui.')
   if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Invoice recovery did not reuse the exact request')
  }
  await ui.expect(p.locator('.cproc-detail')).toContainText(f.tag)
  await ui.expect(p.locator('.cproc-detail')).toContainText('invoice sebagian')
  const secondPost=await enter(2,'6','7.5');await secondPost.click()
  await ui.expect.poll(()=>fixture('read_invoice',f).invoices.length,{timeout:20000}).toBe(2)
  await ui.expect(panel).toContainText('Nilai dokumen Rp45',{timeout:20000});verify(95,0,95,2)
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_INVOICE_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  for(const n of [2,1]) {
   const inspect=panel.getByRole('button',{name:'Tinjau pembatalan '+f.tag+'-UI-INVOICE-'+n,exact:true});await ui.expect(inspect).toBeEnabled();await inspect.click()
   await panel.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('Dokumen invoice diganti sesuai pemeriksaan supplier')
   await panel.getByLabel('Konfirmasi pembatalan invoice',{exact:true}).check()
   const cancel=panel.getByRole('button',{name:'Batalkan invoice supplier',exact:true});await ui.expect(cancel).toBeEnabled();await cancel.click()
   await ui.expect.poll(()=>fixture('read_invoice',f).invoices.find(d=>d.number.endsWith('-'+n))?.status,{timeout:20000}).toBe('REVERSED')
   await ui.expect(panel.getByRole('button',{name:'Muat ulang invoice',exact:true})).toBeEnabled()
   verify(n===2?50:0,n===2?60:100,n===2?110:100,2)
  }
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,staged_invoice_qty:[4,6],staged_ap_gl:[50,95],staged_grni:[60,0],staged_material_value:[110,95],reverse_value:[110,100],stock_locations_always:[6,4],invoice_count_after_replay:1,invoice_count_after_two_documents:2,recovery_identical_request:mobile?true:null,browser_timezone:mobile?'America/Los_Angeles':'Asia/Jakarta',screenshot:`P09_INVOICE_${mobile?'MOBILE':'DESKTOP'}.png`}
 } finally {await user.context.close()}
}
async function supplierReturn(ui,today,mobile) {
 const f=fixture('create_return',{today}),user=await ui.login('OWNER',{label:'cp7-return-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try {
  const p=user.page,panel=p.locator('.cproc-returns')
  async function selectReceipt(){await openPage(ui,p);await p.getByLabel('Cari penerimaan',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari penerimaan',exact:true}).click();const r=p.locator('.cproc-receipt').filter({hasText:f.tag}).filter({hasNotText:'-UI-RETURN'});await ui.expect(r).toHaveCount(1);await ui.expect(r).toBeEnabled();await r.click();await ui.expect(panel).toContainText('Sumber '+f.tag)}
  await selectReceipt()
  await panel.getByLabel('Cari gudang retur',{exact:true}).fill(f.tag+'-TO');await panel.getByRole('button',{name:'Cari gudang retur',exact:true}).click()
  const warehouse=panel.getByLabel('Gudang pengirim retur',{exact:true});await ui.expect(warehouse.locator(`option[value="${f.destination}"]`)).toBeAttached();await ui.expect(warehouse).toBeEnabled();await warehouse.selectOption(f.destination)
  const create=panel.getByRole('button',{name:'Buat retur supplier',exact:true});await ui.expect(create).toBeEnabled();await create.click()
  await panel.getByLabel('Nomor retur supplier',{exact:true}).fill(f.tag+'-UI-RETURN')
  await panel.getByLabel('Waktu retur supplier WIB',{exact:true}).fill(f.return_day+'T16:00')
  await panel.getByLabel('Roll retur 1',{exact:true}).selectOption(f.roll)
  await panel.getByLabel('Jumlah retur 1',{exact:true}).fill('2')
  await panel.getByRole('button',{name:'Simpan draft retur',exact:true}).click()
  await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Draft retur')
  let before=fixture('read_return',f);if(Number(before.qty)!==10||Number(before.source_ap)!==100||Number(before.target_ap)!==100||before.document.movement_count!==0)throw Error('Return draft changed stock/AP')
  const inspect=panel.getByRole('button',{name:'Tinjau pengiriman retur',exact:true});await ui.expect(inspect).toBeEnabled();await inspect.click()
  const post=panel.getByRole('button',{name:'Sahkan pengiriman retur',exact:true});await ui.expect(post).toBeDisabled();await panel.getByLabel('Retur sudah diperiksa',{exact:true}).check();await ui.expect(post).toBeEnabled()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_supplier_return_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='POST'&&!lost){first=body;const r=await route.fetch();if(r.status()!==200)throw Error('Expected committed supplier return before lost reply');lost=true;await route.abort('failed')}else{if(body.p_action==='POST'&&replay===null)replay=body;await route.continue()}})
  await post.click();await ui.expect.poll(()=>fixture('read_return',f).document?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);await ui.expect(panel).toContainText('Data retur supplier sudah diperbarui.');if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Return recovery did not reuse the exact request')}
  await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Retur sudah dikirim');await ui.expect(panel.getByRole('button',{name:'Muat ulang retur',exact:true})).toBeEnabled()
  await ui.expect(panel.getByLabel('Gudang pengirim retur',{exact:true})).toHaveValue(f.destination)
  const posted=fixture('read_return',f)
  if(Number(posted.qty)!==8||Number(posted.material_value)!==80||Number(posted.source_ap)!==80||Number(posted.target_ap)!==100||Number(posted.ap_gl)!==Number(f.ap_before)-20||Number(posted.balances[f.location])!==6||Number(posted.balances[f.destination])!==2||posted.document.movement_count!==1||Number(posted.document.credit)!==20||posted.contexts!==0)throw Error('Return native conservation mismatch '+JSON.stringify(posted))
  if(Date.parse(posted.document.physical_at)!==Date.parse(f.return_day+'T16:00:00+07:00'))throw Error('Return WIB time changed')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_RETURN_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const creditLink=p.getByRole('button',{name:'• Hutang Supplier & Vendor',exact:true});if(!await creditLink.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await creditLink.click()
  await ui.expect(p.getByRole('heading',{name:'Utang & kredit retur supplier',exact:true})).toBeVisible()
  const supplier=p.getByLabel('Supplier kredit',{exact:true});await ui.expect(supplier.locator(`option[value="${f.payload.supplier_id}"]`)).toBeAttached();await ui.expect(supplier).toBeEnabled();await supplier.selectOption(f.payload.supplier_id)
  async function allocate(amount,sourceAp,targetAp){
   const edit=p.getByRole('button',{name:'Atur alokasi '+f.tag+'-UI-RETURN',exact:true});await ui.expect(edit).toBeEnabled();await edit.click()
   await p.getByLabel('Kredit untuk '+f.target_tag,{exact:true}).fill(amount)
   await p.getByLabel('Alasan pengalihan kredit',{exact:true}).fill(amount?'Supplier menyetujui pemotongan pembelian berikutnya':'Kredit dikembalikan ke pembelian asal')
   await p.getByLabel('Saya sudah memeriksa pembelian asal, tujuan, dan nominal kredit.',{exact:true}).check()
   await p.getByRole('button',{name:'Simpan alokasi kredit',exact:true}).click()
   await ui.expect.poll(()=>Number(fixture('read_return',f).target_ap),{timeout:20000}).toBe(targetAp)
   await ui.expect(edit).toBeEnabled()
   const r=fixture('read_return',f)
   if(Number(r.source_ap)!==sourceAp||Number(r.target_ap)!==targetAp||r.ap_gl!==posted.ap_gl||JSON.stringify(r.movements)!==JSON.stringify(posted.movements))throw Error('Portable credit changed total AP/stock/cost '+JSON.stringify(r))
  }
  await allocate('20',100,80);await allocate('',80,100)
  await selectReceipt();const card=panel.locator('.cproc-receipt').filter({hasText:f.tag+'-UI-RETURN'});await ui.expect(card).toBeEnabled();await card.click()
  await panel.getByRole('button',{name:'Tinjau pembatalan retur',exact:true}).click()
  await panel.getByLabel('Alasan tindakan retur',{exact:true}).fill('Barang kembali setelah alokasi kredit dipulihkan')
  await panel.getByLabel('Retur sudah diperiksa',{exact:true}).check();await panel.getByRole('button',{name:'Batalkan retur supplier',exact:true}).click()
  await ui.expect(panel.locator('.cproc-return-detail')).toContainText('Retur dibatalkan')
  const reversed=fixture('read_return',f)
  if(Number(reversed.qty)!==10||Number(reversed.material_value)!==100||Number(reversed.source_ap)!==100||Number(reversed.target_ap)!==100||Number(reversed.ap_gl)!==Number(f.ap_before)||Number(reversed.balances[f.location])!==6||Number(reversed.balances[f.destination])!==4||reversed.document.movement_count!==2)throw Error('Return inverse native mismatch '+JSON.stringify(reversed))
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,source_stock_before:[6,4],source_stock_returned:[6,2],source_ap:80,credit_shifted:[100,80],credit_restored:[80,100],allocation_stock_cost_ap_unchanged:true,return_inverse_stock:[6,4],return_inverse_ap:[100,100],recovery_identical_request:mobile?true:null,browser_timezone:mobile?'America/Los_Angeles':'Asia/Jakarta',screenshot:`P09_RETURN_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
async function receiptReversal(ui,today,mobile){
 const f=fixture('create_reverse',{today,final:mobile}),user=await ui.login('OWNER',{label:'cp7-p09-reverse-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p)
  await p.getByLabel('Cari penerimaan',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari penerimaan',exact:true}).click()
  const card=p.locator('.cproc-history .cproc-receipt').filter({hasText:f.tag});await ui.expect(card).toBeEnabled();await card.click()
  const detail=p.locator('.cproc-detail');await ui.expect(detail).toContainText('Penerimaan sudah tercatat')
  await p.getByRole('button',{name:'Tinjau pembatalan penerimaan',exact:true}).click()
  const submit=p.getByRole('button',{name:'Batalkan penerimaan',exact:true});await ui.expect(submit).toBeDisabled()
  await p.getByLabel('Alasan pembatalan penerimaan',{exact:true}).fill('Penerimaan tercatat ganda setelah pemeriksaan gudang')
  await ui.expect(submit).toBeDisabled();await p.getByLabel('Pembatalan penerimaan sudah diperiksa',{exact:true}).check();await ui.expect(submit).toBeEnabled()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_procurement_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='REVERSE'&&!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}else{if(body.p_action==='REVERSE')replay=body;await route.continue()}})
  await submit.click();await ui.expect.poll(()=>fixture('read_reverse',f).status,{timeout:20000}).toBe('REVERSED')
  if(mobile){await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Receipt inverse changed request on recovery')}
  await ui.expect(detail).toContainText('Penerimaan sudah dibatalkan');await ui.expect(p.getByRole('button',{name:'Batalkan penerimaan',exact:true})).toHaveCount(0)
  const r=fixture('read_reverse',f)
  if(Number(r.qty)!==0||r.movement_count!==2||r.inverse_count!==1||JSON.stringify(r.ledger)!==JSON.stringify(f.ledger_before))throw Error('Receipt inverse stock/journal mismatch '+JSON.stringify(r))
  await ui.expect.poll(()=>detail.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_RECEIPT_REVERSE_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  return {status:'PASS',mobile,direct_final:mobile,real_ui_auth_rpc_database:true,one_inverse:true,remaining_stock:0,all_account_balances_restored:true,recovery_identical_request:mobile?true:null,screenshot:`P09_RECEIPT_REVERSE_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
async function purchaseUom(ui,today,mobile){
 const f=fixture('create_uom',{today,mobile}),user=await ui.login('OWNER',{label:'cp7-p09-uom-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p)
  await p.getByRole('button',{name:'Penerimaan baru',exact:true}).click()
  await p.getByLabel('Nomor surat jalan',{exact:true}).fill(f.tag);await p.getByLabel('Waktu barang datang WIB',{exact:true}).fill(f.day+'T10:00')
  async function choose(label,query,id){const search=p.getByLabel('Cari '+label,{exact:true});await search.fill(query);await search.press('Enter');const select=p.getByLabel(label,{exact:true});await ui.expect(select.locator(`option[value="${id}"]`)).toBeAttached();await ui.expect(select).toBeEnabled();await select.selectOption(id)}
  await choose('Supplier penerimaan',f.supplier_name,f.payload.supplier_id);await choose('Gudang penerimaan',f.tag,f.location);await choose('Bahan 1',f.material_code,f.material)
  const unit=mobile?'GROSS':'LUSIN',quantity=mobile?'0.5':'2',price=mobile?'1440':'120',stock=mobile?72:24,value=mobile?720:240
  const units=p.getByLabel('Satuan pembelian 1',{exact:true});await ui.expect(units).toBeEnabled();await units.selectOption(unit)
  await p.getByLabel('Jumlah barang 1',{exact:true}).fill(quantity);await p.getByLabel('Dasar harga 1',{exact:true}).selectOption(mobile?'SUPPLIER_INVOICE':'MANUAL_ESTIMATE');await p.getByLabel('Harga barang 1',{exact:true}).fill(price)
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_procurement_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='SAVE_DRAFT'&&!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}else{if(body.p_action==='SAVE_DRAFT'&&replay===null)replay=body;await route.continue()}})
  await p.getByRole('button',{name:'Simpan draft penerimaan',exact:true}).click();await ui.expect.poll(()=>fixture('read_uom',f).document?.status,{timeout:20000}).toBe('DRAFT')
  if(mobile){await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('UOM draft recovery changed intent');for(const key of ['qty','unit_price','purchase_uom_factor_snapshot'])if(key in first.p_payload.lines[0])throw Error('Browser sent derived UOM economics')}
  const detail=p.locator('.cproc-detail');await ui.expect(detail).toContainText(stock+' '+f.unit);await ui.expect(detail).toContainText('Di surat jalan: '+quantity.replace('.',',')+' '+unit)
  let r=fixture('read_uom',f);if(Number(r.qty)!==0||r.movement_count!==0||Number(r.document.line[0])!==stock||Number(r.document.line[1])!==10||Number(r.document.line[2])!==value||Number(r.document.line[3])!==Number(quantity)||r.document.line[4]!==unit||Number(r.document.line[6])!==Number(price))throw Error('UOM draft conversion mismatch '+JSON.stringify(r))
  await p.getByRole('button',{name:'Perbaiki draft',exact:true}).click();await ui.expect(units).toHaveValue(unit);await ui.expect(p.getByLabel('Jumlah barang 1',{exact:true})).toHaveValue(mobile?'0.500000':'2.000000');await ui.expect(p.getByLabel('Harga barang 1',{exact:true})).toHaveValue(price+'.000000')
  await p.getByLabel('Alasan pencatatan penerimaan',{exact:true}).fill('Satuan dan harga surat jalan diperiksa kembali');await p.getByRole('button',{name:'Simpan draft penerimaan',exact:true}).click();await ui.expect(p.getByRole('button',{name:'Sahkan penerimaan ke gudang',exact:true})).toBeEnabled();await p.getByRole('button',{name:'Sahkan penerimaan ke gudang',exact:true}).click()
  await ui.expect(detail).toContainText('Penerimaan sudah tercatat');r=fixture('read_uom',f)
  if(Number(r.qty)!==stock||r.movement_count!==1||Number(r.document.ap)!==(mobile?value:0)||Number(r.document.grni)!==(mobile?0:value)||Number(r.document.line[6])!==Number(price))throw Error('UOM posting mismatch '+JSON.stringify(r))
  if(Date.parse(r.document.physical_at)!==Date.parse(f.day+'T10:00:00+07:00'))throw Error('UOM receipt WIB time changed')
  await ui.expect.poll(()=>detail.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_UOM_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  return {status:'PASS',mobile,unit,purchase_quantity:quantity,price_per_purchase_unit:price,base_stock:stock,value,real_ui_auth_rpc_database:true,draft_edit_preserves_entered_units:true,recovery_identical_request:mobile?true:null,screenshot:`P09_UOM_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P09_BROWSER_RECEIPT_DESKTOP',()=>receipt(ui,today,false)],['P09_BROWSER_LOST_REPLY_MOBILE',()=>receipt(ui,today,true)],['P09_BROWSER_TRANSFER_DESKTOP',()=>transfer(ui,today,false)],['P09_BROWSER_TRANSFER_LOST_REPLY_MOBILE',()=>transfer(ui,today,true)],['P09_BROWSER_INVOICE_DESKTOP',()=>supplierInvoice(ui,today,false)],['P09_BROWSER_INVOICE_LOST_REPLY_MOBILE',()=>supplierInvoice(ui,today,true)],['P09_BROWSER_RETURN_CREDIT_DESKTOP',()=>supplierReturn(ui,today,false)],['P09_BROWSER_RETURN_CREDIT_LOST_REPLY_MOBILE',()=>supplierReturn(ui,today,true)],['P09_BROWSER_RECEIPT_REVERSE_DESKTOP',()=>receiptReversal(ui,today,false)],['P09_BROWSER_RECEIPT_REVERSE_LOST_REPLY_MOBILE',()=>receiptReversal(ui,today,true)],['P09_BROWSER_UOM_DESKTOP',()=>purchaseUom(ui,today,false)],['P09_BROWSER_UOM_LOST_DRAFT_REPLY_MOBILE',()=>purchaseUom(ui,today,true)],['P09_BROWSER_ACCESSORY_TRANSFER_DESKTOP',()=>transfer(ui,today,false,'ACCESSORY')],['P09_BROWSER_OTHER_TRANSFER_MOBILE',()=>transfer(ui,today,true,'OTHER')],['P09_BROWSER_COUNT_DESKTOP',()=>materialCount(ui,today,false)],['P09_BROWSER_COUNT_LOST_REPLY_MOBILE',()=>materialCount(ui,today,true)],['P09_BROWSER_COMBINED_INVOICE_DESKTOP',()=>combinedInvoice(ui,today,false)],['P09_BROWSER_COMBINED_INVOICE_LOST_REPLY_MOBILE',()=>combinedInvoice(ui,today,true)],['P09_BROWSER_COUNT_MULTI_DESKTOP',()=>materialCountMulti(ui,today,false)],['P09_BROWSER_COUNT_MULTI_MOBILE_RECOVERY',()=>materialCountMulti(ui,today,true)]]}

async function materialCount(ui,today,mobile){
 const f=fixture('create_count',{today,mobile}),user=await ui.login('OWNER',{label:'cp7-material-count-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page;await openPage(ui,p,'count')
  await p.getByLabel('Cari bahan hitung fisik',{exact:true}).fill(f.material_code);await p.getByRole('button',{name:'Cari bahan',exact:true}).click()
  const source=p.locator('.cmat-roll').filter({hasText:f.material_code});await ui.expect(source).toHaveCount(1)
  const choose=source.getByRole('button',{name:'Hitung '+(f.roll?f.tag+'-R':f.material_name),exact:true});await ui.expect(choose).toBeEnabled();await choose.click()
  await p.getByLabel('Nomor hitung fisik',{exact:true}).fill(f.tag+'-COUNT-UI')
  await p.getByLabel('Waktu hitung WIB',{exact:true}).fill(f.count_day+'T10:00');await p.getByLabel('Jumlah fisik bahan',{exact:true}).fill(mobile?'12':'8')
  await p.getByLabel('Alasan hitung fisik',{exact:true}).selectOption(mobile?'FOUND':'COUNT_CORRECTION');await p.getByLabel('Catatan hitung fisik',{exact:true}).fill('Hitung ulang bersama petugas dan cocokkan foto gudang')
  await p.getByRole('button',{name:'Periksa selisih',exact:true}).click();const form=p.locator('.cmat-count-form');await ui.expect(form).toContainText('Saldo pada waktu hitung 10')
  if(mobile)await p.getByLabel('Harga satuan hasil hitung',{exact:true}).fill('10')
  const save=p.getByRole('button',{name:'Simpan draft hitung fisik',exact:true});await ui.expect(save).toBeEnabled();await save.click()
  const detail=p.locator('.cmat-count-detail');await ui.expect(detail).toContainText('Draft belum mengubah stok.')
  let read=fixture('read_count',f);if(Number(read.qty)!==10||read.movements!==1||Number(read.document.items[0].qty_signed)!==(mobile?2:-2))throw Error('Count draft changed stock or server delta')
  const originalCount=read.document
  await p.getByRole('button',{name:'Edit draft hitung fisik',exact:true}).click()
  await ui.expect(p.getByLabel('Jumlah fisik bahan',{exact:true})).toHaveValue(mobile?'12':'8')
  await p.getByLabel('Catatan hitung fisik',{exact:true}).fill('Diperiksa ulang sebelum disahkan; jumlah dan waktu tetap sama')
  await p.getByRole('button',{name:'Periksa selisih',exact:true}).click();await ui.expect(p.locator('.cmat-count-form')).toContainText('Saldo pada waktu hitung 10')
  if(mobile)await ui.expect(p.getByLabel('Harga satuan hasil hitung',{exact:true})).toHaveValue('10')
  await p.getByRole('button',{name:'Simpan draft hitung fisik',exact:true}).click();await ui.expect(p.locator('.cmat-count-form')).toHaveCount(0)
  read=fixture('read_count',f)
  if(read.document.id!==originalCount.id||BigInt(read.document.version)<=BigInt(originalCount.version)||read.document.physical_at!==originalCount.physical_at||Number(read.qty)!==10||read.movements!==1)throw Error('Draft edit lost original identity, time or quantity')
  const review=p.getByLabel('Saya sudah memeriksa jumlah dan alasan tindakan ini.',{exact:true});await review.check()
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_material_count_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='POST'&&!lost){first=body;const response=await route.fetch();if(response.status()!==200){await route.fulfill({response});return}lost=true;await route.abort('failed')}else{if(body.p_action==='POST')replay=body;await route.continue()}})
  const post=p.getByRole('button',{name:'Sahkan hitung fisik',exact:true});await ui.expect(post).toBeEnabled();await post.click()
  await ui.expect.poll(()=>fixture('read_count',f).document?.status,{timeout:20000}).toBe('POSTED')
  if(mobile){await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p,'count');await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Count replay changed request')}
  await ui.expect(detail).toContainText('Penyesuaian stok sudah disahkan.');read=fixture('read_count',f)
  if(Number(read.qty)!==(mobile?12:8)||read.movements!==2||Number(read.document.items[0].valuation.restated_value)!==(mobile?20:-20))throw Error('Count native quantity/value mismatch')
  if(Date.parse(read.document.physical_at)!==Date.parse(f.count_day+'T10:00:00+07:00'))throw Error('Count WIB date changed')
  await ui.expect.poll(()=>detail.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_COUNT_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await review.check();await p.getByRole('button',{name:'Batalkan hitung fisik',exact:true}).click();await ui.expect(detail).toContainText('Penyesuaian sudah dibatalkan dengan mutasi pembalik.')
  read=fixture('read_count',f);if(Number(read.qty)!==10||read.movements!==3||JSON.stringify(read.ledger)!==JSON.stringify(f.ledger_before))throw Error('Count inverse failed to restore stock/accounts')
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,physical_input:true,draft_edit_preserves_id_time_and_quantity:true,server_delta:mobile?2:-2,posted_stock:mobile?12:8,posted_value_delta:mobile?20:-20,restored_stock:10,all_accounts_restored:true,recovery_identical_request:mobile?true:null,screenshot:`P09_COUNT_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
async function combinedInvoice(ui,today,mobile){
 const f=fixture('create_combined_invoice',{today}),user=await ui.login('OWNER',{label:'cp7-combined-invoice-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try{
  const p=user.page,panel=p.locator('.cproc-invoices'),number=f.tag+'-UI-COMBINED'
  await openPage(ui,p);await p.getByLabel('Cari penerimaan',{exact:true}).fill(f.tag);await p.getByRole('button',{name:'Cari penerimaan',exact:true}).click()
  const receipt=p.locator('.cproc-receipt').filter({hasText:f.tag});await ui.expect(receipt).toHaveCount(1);await ui.expect(receipt).toBeEnabled();await receipt.click()
  await ui.expect(panel).toContainText('Penerimaan '+f.tag);await panel.getByRole('button',{name:'Gabungkan penerimaan dalam invoice',exact:true}).click()
  await panel.getByLabel('Nomor invoice supplier',{exact:true}).fill(number);await panel.getByLabel('Tanggal invoice supplier',{exact:true}).fill(f.day)
  await panel.getByLabel('Waktu invoice diterima WIB',{exact:true}).fill(f.invoice_day+'T15:00');await panel.getByLabel('Jatuh tempo invoice supplier',{exact:true}).fill(f.invoice_day)
  await panel.getByLabel('Cari penerimaan invoice',{exact:true}).fill(f.other.tag);await panel.getByRole('button',{name:'Cari penerimaan invoice',exact:true}).click()
  const add=panel.getByRole('button',{name:'Tambahkan '+f.other.tag,exact:true});await ui.expect(add).toBeEnabled();await add.click()
  await panel.getByLabel('Jumlah invoice 1',{exact:true}).fill('4');await panel.getByLabel('Harga invoice 1',{exact:true}).fill('12.5')
  await panel.getByLabel('Jumlah invoice 2',{exact:true}).fill('6');await panel.getByLabel('Harga invoice 2',{exact:true}).fill('7.5')
  await panel.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await panel.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
  await ui.expect(panel).toContainText('Draft invoice');let read=fixture('read_combined_invoice',f),original=read.documents[0]
  if(read.documents.length!==1||original.line_count!=='2'||JSON.stringify(read.ledger)!==JSON.stringify(f.ledger_before)||read.receipts.some(r=>Number(r.ap)!==0||Number(r.value)!==100))throw Error('Combined invoice draft changed money or lost a source')
  await panel.getByRole('button',{name:'Edit draft '+number,exact:true}).click();await panel.getByLabel('Catatan invoice supplier',{exact:true}).fill('Dua surat jalan diperiksa; catatan draft diperbaiki')
  await panel.getByLabel('Invoice sudah diperiksa',{exact:true}).check();await panel.getByRole('button',{name:'Simpan draft invoice',exact:true}).click()
  await ui.expect(panel.locator('.cproc-editor')).toHaveCount(0);read=fixture('read_combined_invoice',f)
  if(read.documents[0].id!==original.id||BigInt(read.documents[0].row_version)<=BigInt(original.row_version)||read.documents[0].received_at!==original.received_at||read.documents[0].lines.some(l=>!l.purchase_id)||JSON.stringify(read.ledger)!==JSON.stringify(f.ledger_before))throw Error('Combined draft edit changed identity/time/money')
  let lost=false,first=null,replay=null
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_purchase_invoice_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='POST_DOCUMENT'&&!lost){first=body;const r=await route.fetch();if(r.status()!==200){await route.fulfill({response:r});return}lost=true;await route.abort('failed')}else{if(body.p_action==='POST_DOCUMENT')replay=body;await route.continue()}})
  await panel.getByRole('button',{name:'Tinjau pengesahan '+number,exact:true}).click();await panel.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('Semua penerimaan dan harga sudah dicocokkan')
  await panel.getByLabel('Konfirmasi pengesahan invoice',{exact:true}).check();await panel.getByRole('button',{name:'Sahkan draft invoice supplier',exact:true}).click()
  if(mobile){await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p);await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Combined invoice recovery changed request')}
  await ui.expect(panel).toContainText('Invoice disahkan');await ui.expect(panel).toContainText('Nilai dokumen Rp95')
  read=fixture('read_combined_invoice',f)
  for(const [i,r] of read.receipts.entries())if(Number(r.ap)!==[50,45][i]||Number(r.grni)!==[60,40][i]||Number(r.qty)!==10||Number(r.value)!==[110,85][i])throw Error('Combined invoice recognition mismatch')
  if(read.documents.length!==1||read.documents[0].lines.length!==2)throw Error('Combined invoice replay duplicated or truncated document')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_COMBINED_INVOICE_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await panel.getByRole('button',{name:'Tinjau pembatalan '+number,exact:true}).click();await panel.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('Invoice gabungan diganti oleh supplier')
  await panel.getByLabel('Konfirmasi pembatalan invoice',{exact:true}).check();await panel.getByRole('button',{name:'Batalkan invoice supplier',exact:true}).click();await ui.expect(panel).toContainText('Invoice dibatalkan')
  read=fixture('read_combined_invoice',f);if(JSON.stringify(read.ledger)!==JSON.stringify(f.ledger_before)||read.receipts.some(r=>Number(r.ap)!==0||Number(r.grni)!==100||Number(r.qty)!==10||Number(r.value)!==100))throw Error('Combined invoice inverse did not restore both receipts/accounts')
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,complete_receipts:2,draft_edit_preserves_id_time_money:true,ap:[50,45],grni:[60,40],stock_values:[110,85],all_accounts_restored:true,recovery_identical_request:mobile?true:null,screenshot:`P09_COMBINED_INVOICE_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}

async function materialCountMulti(ui,today,mobile){
 const f=fixture('create_count_multi',{today}),user=await ui.login('OWNER',{label:'cp7-count-multi-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const label=x=>x.material_name+' '+x.material_code
 try{
  const p=user.page;await openPage(ui,p,'count')
  for(const item of [f,f.other]){
   await p.getByLabel('Cari bahan hitung fisik',{exact:true}).fill(item.material_code);await p.getByRole('button',{name:'Cari bahan',exact:true}).click()
   const card=p.locator('.cmat-roll').filter({hasText:item.material_code}).filter({hasText:f.location_name});await ui.expect(card).toHaveCount(1)
   await card.getByRole('button',{name:'Hitung '+item.material_name,exact:true}).click()
  }
  const form=p.locator('.cmat-count-form');await ui.expect(form.locator('.cmat-count-input')).toHaveCount(2)
  await p.getByLabel('Nomor hitung fisik',{exact:true}).fill(f.tag+'-COUNT-UI');await p.getByLabel('Waktu hitung WIB',{exact:true}).fill(f.count_day+'T10:00')
  await p.getByLabel('Jumlah fisik '+label(f),{exact:true}).fill(mobile?'12':'8');await p.getByLabel('Jumlah fisik '+label(f.other),{exact:true}).fill('10')
  await p.getByLabel('Catatan hitung fisik',{exact:true}).fill('Dua bahan diperiksa; satu jumlah sesuai tetap tercatat')
  await p.getByRole('button',{name:'Periksa selisih',exact:true}).click();await ui.expect(form).toContainText('Hasil hitung tetap disimpan tanpa mutasi penyesuaian.')
  if(mobile)await p.getByLabel('Harga satuan hasil hitung '+label(f),{exact:true}).fill('10')
  let first=null,replay=null,lost=false
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_material_count_v1',async route=>{
   const body=route.request().postDataJSON()
   if(body.p_action==='SAVE'&&!lost){first=body;const response=await route.fetch();assert.equal(response.status(),200);lost=true;await route.abort('failed')}
   else{if(body.p_action==='SAVE'&&replay===null)replay=body;await route.continue()}
  })
  await p.getByRole('button',{name:'Simpan draft hitung fisik',exact:true}).click();await ui.expect.poll(()=>fixture('read_count',f).document?.status).toBe('DRAFT')
  if(mobile){
   await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p,'count')
   await p.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(p.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.ok(lost);assert.deepEqual(replay,first)
  }
  let actual=fixture('read_count',f);const original=actual.document;assert.equal(actual.input_count,2);assert.equal(original.items.length,1);assert.equal(Number(actual.qty),10);assert.equal(Number(actual.other_qty),10);assert.deepEqual(actual.ledger,f.ledger_before)
  await p.getByRole('button',{name:'Edit draft hitung fisik',exact:true}).click();await ui.expect(form.locator('.cmat-count-input')).toHaveCount(2)
  await ui.expect(p.getByLabel('Jumlah fisik '+label(f.other),{exact:true})).toHaveValue('10')
  await p.getByLabel('Jumlah fisik '+label(f),{exact:true}).fill(mobile?'13':'7');await p.getByRole('button',{name:'Periksa selisih',exact:true}).click()
  if(mobile)await ui.expect(p.getByLabel('Harga satuan hasil hitung '+label(f),{exact:true})).toHaveValue('10')
  await ui.expect.poll(()=>form.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:`cp6-proof/t3/P09_COUNT_MULTI_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await p.getByRole('button',{name:'Simpan draft hitung fisik',exact:true}).click();await ui.expect(form).toHaveCount(0)
  actual=fixture('read_count',f);assert.equal(actual.document.id,original.id);assert.equal(actual.document.physical_at,original.physical_at);assert.ok(BigInt(actual.document.version)>BigInt(original.version));assert.equal(actual.input_count,2)
  await p.getByLabel('Saya sudah memeriksa jumlah dan alasan tindakan ini.',{exact:true}).check();await p.getByRole('button',{name:'Sahkan hitung fisik',exact:true}).click()
  await ui.expect.poll(()=>fixture('read_count',f).document?.status).toBe('POSTED');actual=fixture('read_count',f);assert.equal(Number(actual.qty),mobile?13:7);assert.equal(Number(actual.other_qty),10);assert.equal(actual.document.items.length,1);assert.equal(actual.input_count,2)
  await ui.expect(p.locator('.cmat-count-detail')).toContainText('Penyesuaian stok sudah disahkan.')
  await p.getByLabel('Saya sudah memeriksa jumlah dan alasan tindakan ini.',{exact:true}).check();await p.getByRole('button',{name:'Batalkan hitung fisik',exact:true}).click()
  await ui.expect.poll(()=>fixture('read_count',f).document?.status).toBe('REVERSED');actual=fixture('read_count',f);assert.equal(Number(actual.qty),10);assert.equal(Number(actual.other_qty),10);assert.deepEqual(actual.ledger,f.ledger_before)
  return {status:'PASS',mobile,ordinary_multi_input_browser_save_edit_post_reverse:true,zero_difference_input_preserved:true,native_movement_count:1,physical_inputs:2,edited_quantity:mobile?'13':'7',original_document_time_retained:true,price_preserved:mobile,exact_lost_save_reply:mobile?true:null,final_stock_and_all_accounts_restored:true,screenshot:`P09_COUNT_MULTI_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
