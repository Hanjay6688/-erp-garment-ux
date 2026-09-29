import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
const fixture = (op,payload) => JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p09_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p,materials=false) {
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:materials?'• Bahan & Roll':'• Pembelian & Penerimaan',exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:materials?'Bahan & roll':'Pembelian & penerimaan',exact:true})).toBeVisible()
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
async function transfer(ui,today,mobile) {
 const f=fixture('create_transfer',{today}),user=await ui.login('OWNER',{label:'cp7-material-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 try {
  const p=user.page;await openPage(ui,p,true)
  await p.getByLabel('Cari stok bahan',{exact:true}).fill(f.material_code);await p.getByRole('button',{name:'Cari stok',exact:true}).click()
  const roll=f.tag+'-R';await ui.expect(p.getByRole('button',{name:'Pindahkan '+roll,exact:true})).toBeEnabled()
  await p.getByRole('button',{name:'Mutasi '+roll,exact:true}).click();await ui.expect(p.locator('.cmat-ledger')).toContainText('Saldo 10')
  await p.getByRole('button',{name:'Pindahkan '+roll,exact:true}).click()
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
   if(body.p_action==='POST_TRANSFER'&&!lost){first=body;const response=await handler.fetch();if(response.status()!==200)throw Error('Expected committed transfer');lost=true;await handler.abort('failed')}
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
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P09_MATERIAL_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  await p.getByRole('button',{name:'Transfer gudang',exact:true}).click()
  await p.getByLabel('Saya sudah memeriksa alasan pembatalan transfer ini.',{exact:true}).check()
  await p.getByLabel('Catatan transfer',{exact:true}).fill('Barang kembali ke gudang asal sesuai pemeriksaan')
  await p.getByRole('button',{name:'Batalkan transfer',exact:true}).click()
  await ui.expect(p.locator('.cmat-transfer-detail')).toContainText('Transfer sudah dibatalkan',{timeout:20000})
  read=fixture('read_transfer',f)
  if(Number(read.balances[f.location])!==10||Number(read.balances[f.destination])!==0||read.document.movements!==4||Number(read.total_value)!==100)throw Error('Transfer reverse native mismatch')
  return {status:'PASS',mobile,real_ui_auth_rpc_database:true,draft_no_stock:true,posted_source:6,posted_destination:4,total_value:100,transfer_net_value:0,reversed_source:10,reversed_destination:0,movements_with_inverse:4,recovery_identical_request:mobile?true:null,screenshot:`P09_MATERIAL_${mobile?'MOBILE':'DESKTOP'}.png`}
 } finally {await user.context.close()}
}
export async function cases(ui,today){return [['P09_BROWSER_RECEIPT_DESKTOP',()=>receipt(ui,today,false)],['P09_BROWSER_LOST_REPLY_MOBILE',()=>receipt(ui,today,true)],['P09_BROWSER_TRANSFER_DESKTOP',()=>transfer(ui,today,false)],['P09_BROWSER_TRANSFER_LOST_REPLY_MOBILE',()=>transfer(ui,today,true)]]}
