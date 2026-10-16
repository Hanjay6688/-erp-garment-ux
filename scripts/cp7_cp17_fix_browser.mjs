// CP17 browser cases on the Bagi Potongan page, real Auth and PostgREST on the committed copy:
// SG-01 reverse a posted pickup before sewing (desktop), SG-02 fabric back to the warehouse (phone); and the
// D14-6 kasbon on the Payroll & Kasbon page (give from a funded bank, cut from the Mandor's payroll draft); and D14-5
// dozens over one size series on the Penjualan & Invoice draft (desktop and phone); D14-14 G1 SELESAI DIJAHIT on the
// WIP & Sewing page (desktop and phone); owner D15-3 master screens and the Mandor + rate -> Bagi Potongan -> sewing chain;
// owner D15-6 Buat Potongan with the PO made automatically; owner D15-5 the official cutover date; Sol R2-10 sewing per SKU of a
// wave Potongan.
import assert from'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
import*as master from'./cp7_master_browser.mjs'
import*as autoPo from'./cp7_auto_po_browser.mjs'
import*as cutover from'./cp7_cutover_browser.mjs'
import*as wave from'./cp7_wave_sewing_browser.mjs'
const fixture=(operation,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_cp17_fix_browser_fixture.py',operation],{input:JSON.stringify(payload),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function menu(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click();const link=page.getByRole('button',{name:'• Bagi Potongan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()}
async function openGroup(ui,page,number,group){
 await menu(page);await page.locator('.cpick-tabs').getByRole('button',{name:'Semua',exact:true}).click()
 await page.getByLabel('Cari distribusi potongan',{exact:true}).fill(number);await page.getByRole('button',{name:'Cari Potongan',exact:true}).click()
 await page.locator('.cpick-queue button').filter({hasText:number}).click();await ui.expect(page.locator('[data-cutting-group-id]')).toHaveAttribute('data-cutting-group-id',group)
}
async function noSideScroll(ui,page){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)}
async function failure(page,name,error,state,requests){writeFileSync(`cp6-proof/t3/${name}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),state,requests},null,2))
 // The artifact is not always reachable from where the log is read: the alerts and status lines on screen go to the log too.
 const shown=await page.locator('[role="alert"],[role="status"]').allInnerTexts().catch(()=>[])
 console.error(JSON.stringify({failed_case:name,failure_screen:shown.map(t=>t.slice(0,300)).slice(0,12),requests:(requests??[]).length}))
await page.screenshot({path:`cp6-proof/t3/${name}_FAILURE.png`,fullPage:true}).catch(()=>{})}
async function pickupReversal(ui,today){
 const f=fixture('pickup',{today}),user=await ui.login('OWNER',{label:'cp17-pickup-reversal'}),page=user.page,requests=[],name='CP17_SG01_PICKUP_REVERSAL_DESKTOP'
 const state=()=>fixture('pickup_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_reverse_pickup_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.pickup_status,'POSTED');assert.equal(before.po[2],f.mandor)
  await openGroup(ui,page,f.number,f.group)
  const panel=page.getByRole('region',{name:'Batal Bagi Potongan',exact:true})
  await panel.getByRole('button',{name:'Batalkan Bagi Potongan ini',exact:true}).click()
  await ui.expect(panel).toContainText('Mandor di PO dikosongkan');await ui.expect(panel.getByRole('button',{name:'Batalkan Bagi Potongan',exact:true})).toBeDisabled()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await panel.getByLabel('Alasan batal Bagi Potongan',{exact:true}).fill('Salah mandor, potongan dibagi ulang')
  await panel.getByLabel('Pembatalan Bagi Potongan sudah diperiksa',{exact:true}).check()
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await panel.getByRole('button',{name:'Batalkan Bagi Potongan',exact:true}).click()
  await ui.expect(page.getByText(f.number+': Bagi Potongan dibatalkan.')).toBeVisible()
  const after=state()
  assert.equal(after.pickup_status,'REVERSED');assert.equal(after.reversal_reason,'Salah mandor, potongan dibagi ulang');assert.equal(after.group_status,'CUT')
  assert.equal(after.picked_up_at,null);assert.equal(after.fabric_posted,true);assert.equal(after.executor,f.executor);assert.deepEqual(after.po,f.po_before)
  assert.equal(after.history,1);assert.equal(after.active_pickups,0);assert.equal(requests.length,1)
  assert.equal(requests[0].p_payload.group_id,f.group);assert.equal(requests[0].p_payload.pickup_id,f.pickup)
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',pickup:'REVERSED',cutting_group:'CUT with fabric still posted',po_restored:after.po,mandor_cleared:after.po[2]===null,one_request:true,history_rows:1}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
async function fabricReturn(ui,today){
 const f=fixture('fabric',{today}),user=await ui.login('OWNER',{label:'cp17-fabric-return',mobile:true}),page=user.page,requests=[],name='CP17_SG02_FABRIC_RETURN_MOBILE'
 const state=()=>fixture('fabric_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_return_cutting_fabric_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.returns,0);assert.equal(before.return_posted,false)
  await openGroup(ui,page,f.number,f.group)
  const panel=page.getByRole('region',{name:'Kain kembali ke gudang',exact:true})
  await panel.getByRole('button',{name:'Catat kain kembali ke gudang',exact:true}).click()
  const qty=panel.getByLabel('Kain kembali roll '+f.roll_number,{exact:true});await ui.expect(qty).toBeEnabled()
  await qty.fill('3.5');await ui.expect(panel).toContainText('melebihi sisa yang dicatat saat potong')
  await qty.fill('2');await panel.getByLabel('Alasan kain kembali',{exact:true}).fill('Sisa kain dikembalikan ke gudang bahan')
  await panel.getByLabel('Jumlah kain kembali sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await panel.getByRole('button',{name:'Simpan kain kembali ke gudang',exact:true}).click()
  await ui.expect(page.getByText(/kain kembali ke gudang sudah tercatat/)).toBeVisible()
  const after=state()
  assert.equal(Number(after.stock)-Number(before.stock),2);assert.equal(after.returns,1);assert.equal(after.return_posted,true);assert.equal(after.history,1)
  assert.equal(requests.length,1);assert.equal(requests[0].p_payload.rolls.length,1);assert.equal(requests[0].p_payload.rolls[0].qty_returned,'2')
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',over_remainder_refused_on_screen:true,stock_up_by:2,one_return_movement:true,once_per_cutting:true,one_request:true,phone:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
// D14-10: a recorded return (2) corrected to the right quantity (3) from the screen, in one save; the first return and
// its reversal stay in the books; more than the remainder is refused on screen first.
async function fabricReturnCorrect(ui,today){
 const f=fixture('fabric',{today}),user=await ui.login('OWNER',{label:'cp17-fabric-correct'}),page=user.page,requests=[],name='CP17_SG02_FABRIC_RETURN_CORRECT_DESKTOP'
 const state=()=>fixture('fabric_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_reverse_cutting_return_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.returns,0)
  await openGroup(ui,page,f.number,f.group)
  const panel=page.getByRole('region',{name:'Kain kembali ke gudang',exact:true})
  await panel.getByRole('button',{name:'Catat kain kembali ke gudang',exact:true}).click()
  await panel.getByLabel('Kain kembali roll '+f.roll_number,{exact:true}).fill('2');await panel.getByLabel('Alasan kain kembali',{exact:true}).fill('Sisa kain dikembalikan ke gudang bahan')
  await panel.getByLabel('Jumlah kain kembali sudah diperiksa',{exact:true}).check();await panel.getByRole('button',{name:'Simpan kain kembali ke gudang',exact:true}).click()
  await ui.expect(page.getByText(/kain kembali ke gudang sudah tercatat/)).toBeVisible()
  const recorded=state();assert.equal(Number(recorded.stock)-Number(before.stock),2);assert.equal(recorded.active,1)
  await openGroup(ui,page,f.number,f.group)
  const rev=page.getByRole('region',{name:'Batal atau betulkan kain kembali',exact:true})
  await rev.getByRole('button',{name:'Batal / betulkan kain kembali',exact:true}).click();await ui.expect(rev).toContainText(f.roll_number)
  await rev.getByLabel('Betulkan jumlahnya').check()
  const right=rev.getByLabel('Jumlah benar roll '+f.roll_number,{exact:true})
  await right.fill('3.5');await ui.expect(rev).toContainText('melebihi sisa yang dicatat saat potong')
  await right.fill('3');await rev.getByLabel('Alasan batal kain kembali',{exact:true}).fill('Jumlah sebenarnya tiga, bukan dua')
  await rev.getByLabel('Batal kain kembali sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),recorded);assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await rev.getByRole('button',{name:'Simpan pembetulan kain kembali',exact:true}).click()
  await ui.expect(page.getByText(/kain kembali dibetulkan/)).toBeVisible()
  const after=state()
  assert.equal(Number(after.stock)-Number(before.stock),3);assert.equal(after.active,1);assert.equal(Number(after.active_qty),3)
  assert.equal(after.returns,2);assert.equal(after.history,1);assert.equal(after.reversal_history,1);assert.equal(after.return_posted,true)
  assert.equal(requests.length,1);assert.deepEqual(requests[0].p_payload.replacement_rolls.map(r=>r.qty_returned),['3'])
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',owner_decision:'D14-10',recorded:2,corrected_to:3,stock_net_up_by:3,first_return_kept_and_reversed:true,one_request:true,over_remainder_refused_on_screen:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
async function kasbon(ui,today){
 const f=fixture('kasbon',{today}),user=await ui.login('OWNER',{label:'cp17-kasbon'}),page=user.page,requests=[],name='CP17_KASBON_GIVE_DEDUCT_DESKTOP'
 const state=()=>fixture('kasbon_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_kasbon_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.advances.length,0);assert.deepEqual(before.payroll,['CALCULATED','0.00','6000.00'])
  const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
  const link=page.getByRole('button',{name:'• Payroll & Kasbon',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
  const list=page.locator('.cpay');await list.getByLabel('Cari payroll',{exact:true}).fill(f.label);await list.getByRole('button',{name:'Cari payroll',exact:true}).click()
  await ui.expect(list.locator('.cproc-receipt')).toHaveCount(1);await list.locator('.cproc-receipt').click()
  const panel=page.getByRole('region',{name:'Kasbon tunai',exact:true})
  await panel.getByRole('button',{name:'Lihat kasbon mandor ini',exact:true}).click();await ui.expect(panel).toContainText('Mandor ini belum punya kasbon.')
  // Give 2500 from the funded bank, dated today (WIB): money leaves the bank, the Mandor owes it.
  await panel.getByRole('button',{name:'Beri kasbon',exact:true}).click()
  const form=panel.getByRole('region',{name:'Periksa kasbon',exact:true})
  await form.getByLabel('Nominal kasbon',{exact:true}).fill('2500');await form.getByLabel('Rekening kasbon',{exact:true}).selectOption(f.bank)
  await form.getByLabel('Alasan kasbon',{exact:true}).fill('Kasbon tunai untuk kebutuhan mandor');await form.getByLabel('Kasbon sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_GIVE_REVIEW.png`,fullPage:true})
  await form.getByRole('button',{name:'Simpan kasbon',exact:true}).click()
  await ui.expect(panel.getByRole('status').filter({hasText:/Kasbon KB-.* Rp2\.500,00 tercatat\./})).toBeVisible()
  const given=state();assert.equal(given.advances.length,1);assert.deepEqual(given.advances[0].slice(1,3),['2500.00','GIVEN'])
  assert.equal(Number(given.bank)-Number(before.bank),-2500);assert.equal(Number(given.receivable)-Number(before.receivable),2500);assert.equal(given.kasbon_journals,1)
  assert.deepEqual(given.payroll,before.payroll);assert.equal(requests.length,1);assert.equal(requests[0].p_action,'GIVE');assert.equal(requests[0].p_payload.amount,'2500.00')
  // Cut it from this Mandor's payroll draft: prefilled with what the kasbon and the payroll can take.
  await panel.getByRole('button',{name:'Potong dari payroll '+f.payroll_number,exact:true}).click()
  await ui.expect(form.getByLabel('Nominal kasbon',{exact:true})).toHaveValue('2500.00')
  await form.getByLabel('Kasbon sudah diperiksa',{exact:true}).check();await form.getByRole('button',{name:'Simpan potongan kasbon',exact:true}).click()
  await ui.expect(panel.getByRole('status').filter({hasText:/Sisa kasbon Rp0,00\./})).toBeVisible()
  const cut=state();assert.deepEqual(cut.payroll.slice(1),['2500.00','3500.00']);assert.ok(['DRAFT','CALCULATED','REVIEW'].includes(cut.payroll[0]),cut.payroll[0]);assert.equal(cut.links,1);assert.equal(cut.bank,given.bank);assert.equal(cut.receivable,given.receivable)
  assert.equal(requests.length,2);assert.equal(requests[1].p_action,'ALLOCATE');assert.equal(requests[1].p_payload.payroll_id,f.payroll)
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',kasbon:'2500.00',bank_down_by:2500,mandor_owes:2500,one_journal:true,payroll_net_before:'6000.00',deducted:'2500.00',payroll_net_after:'3500.00',saved_message_kept_after_reload:true,requests:2,owner_decision:'D14-6'}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
async function salesPage(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Penjualan & Invoice',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click();await link.click()
 await ui.expect(page.locator('.csales').getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
}
// Owner D14-5, in the owner's own examples: picking one size of a three-size SKU brings the whole series already at
// 1 lusin = 4/4/4; typed by hand 3/5/4 reads "1 lusin" and 4/5/4 "1 lusin 1 potong"; an uneven split is refused on
// screen; a one-size SKU at 1 lusin is 12 PCS in that size. The draft saved from the screen holds 3/5/4 and 12, the
// stock is reserved by exactly that, and the reopened draft reads both series back as 1 lusin.
async function seriesDozens(ui,today,mobile){
 const f=fixture('series',{today}),name=`CP17_D14_5_SERIES_DOZENS_${mobile?'MOBILE':'DESKTOP'}`,user=await ui.login('OWNER',{label:'cp17-d145-'+(mobile?'mobile':'desktop'),mobile}),page=user.page,requests=[]
 const state=()=>fixture('series_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_sale_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.equal(before.sale,null);assert.deepEqual(before.stock,{27:20,31:10,32:11,33:12});assert.equal(before.other_brand_stock,5)
  await salesPage(ui,page);const ws=page.locator('.csales'),form=ws.getByRole('form',{name:'Draft invoice'}),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
  await ws.getByRole('button',{name:'Buat invoice',exact:true}).click()
  await form.getByLabel('Nomor draft invoice',{exact:true}).fill(f.tag);await form.getByLabel('Waktu draft invoice WIB',{exact:true}).fill(new Date(new Date(f.sale_at).getTime()+7*60*60*1000).toISOString().slice(0,16))
  await form.getByLabel('Cari pelanggan draft',{exact:true}).fill(f.tag);await form.getByRole('button',{name:'Cari pelanggan draft',exact:true}).click()
  const customer=form.getByRole('region',{name:'Pilih pelanggan invoice'}).locator('.cproc-receipt');await ui.expect(customer).toHaveCount(1);await customer.click()
  // R2-06 (ASTRA-C17-01): the same series SKU also exists for a second brand; rows are told apart by the brand shown.
  const pick=async(sku,count,nth,brand,brandCount)=>{await form.getByLabel('Cari barang draft',{exact:true}).fill(sku);await form.getByRole('button',{name:'Cari barang draft',exact:true}).click();const all=form.getByRole('region',{name:'Pilih barang invoice'}).locator('.cproc-receipt');await ui.expect(all).toHaveCount(count);const rows=brand?all.filter({hasText:' · '+brand+' · '}):all;if(brand)await ui.expect(rows).toHaveCount(brandCount);await rows.nth(nth).click()}
  const seri=(sku,brand=f.brand)=>`${sku} · ${brand}`
  const qty=n=>form.getByLabel(`Jumlah invoice ${n}`,{exact:true}),values=n=>Promise.all(n.map(i=>qty(i).inputValue()))
  const three=form.getByRole('region',{name:'Seri '+seri(f.series_sku),exact:true}),split=three.getByRole('button',{name:'Bagi rata ke 3 ukuran seri '+seri(f.series_sku),exact:true})
  const dozens=form.getByLabel('Lusin seri '+seri(f.series_sku),{exact:true}),pieces=form.getByLabel('Sisa potong seri '+seri(f.series_sku),{exact:true})
  await pick(f.series_sku,4,1,f.brand,3)
  await ui.expect(three).toContainText('3 ukuran (31/32/33)');await ui.expect(three.locator('article')).toHaveCount(3);await ui.expect(form.getByRole('region',{name:'Seri '+seri(f.series_sku,f.other_brand),exact:true})).toHaveCount(0);for(const n of[1,2,3])await ui.expect(qty(n)).toHaveValue('4')
  await ui.expect(three).toContainText('Total seri: 1 lusin (12 PCS)');await ui.expect(dozens).toHaveValue('1');await ui.expect(three).toContainText('stok 10 PCS')
  // Compact like the UX demo (owner 15 Oct, "ya"): the three sizes of the series sit side by side, also on a phone.
  const tops=await three.locator('article').evaluateAll(es=>es.map(e=>Math.round(e.getBoundingClientRect().top)));assert.equal(new Set(tops).size,1,'CP17_D14_5_SIZES_NOT_SIDE_BY_SIDE:'+tops)
  for(const [n,v] of [[1,'3'],[2,'5'],[3,'4']])await qty(n).fill(v);await ui.expect(three).toContainText('Total seri: 1 lusin (12 PCS)')
  await qty(1).fill('4');await ui.expect(three).toContainText('Total seri: 1 lusin 1 potong (13 PCS)')
  await dozens.fill('1');await pieces.fill('1');await split.click()
  await ui.expect(three.getByRole('alert')).toHaveText('1 lusin 1 potong (13 PCS) tidak bisa dibagi rata ke 3 ukuran. Isi per ukuran, atau ubah jumlahnya.');assert.deepEqual(await values([1,2,3]),['4','5','4'])
  await pieces.fill('');await dozens.fill('2');await split.click();for(const n of[1,2,3])await ui.expect(qty(n)).toHaveValue('8');await ui.expect(three).toContainText('Total seri: 2 lusin (24 PCS)')
  for(const [n,v] of [[1,'3'],[2,'5'],[3,'4']])await qty(n).fill(v);await ui.expect(three).toContainText('Total seri: 1 lusin (12 PCS)')
  await pick(f.single_sku,1,0);const one=form.getByRole('region',{name:'Seri '+seri(f.single_sku),exact:true})
  await ui.expect(one).toContainText('1 ukuran (27)');await ui.expect(qty(4)).toHaveValue('12');await ui.expect(one).toContainText('Total seri: 1 lusin (12 PCS)')
  for(const n of[1,2,3,4])await form.getByLabel(`Harga invoice ${n}`,{exact:true}).fill('10')
  await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('D14-5 satu seri 3/5/4 dan satu ukuran 1 lusin');await form.getByLabel('Draft invoice sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await noSideScroll(ui,page);await three.scrollIntoViewIfNeeded();await page.screenshot({path:`cp6-proof/t3/${name}_FORM.png`,fullPage:true})
  await form.getByRole('button',{name:'Simpan draft invoice',exact:true}).click();await ui.expect(form).toHaveCount(0);await ui.expect(detail).toContainText('24 PCS masih dipesan')
  const after=state()
  assert.equal(after.status,'DRAFT');assert.equal(after.lines,4);assert.deepEqual(after.qty,{27:12,31:3,32:5,33:4});assert.deepEqual(after.stock,{27:8,31:7,32:6,33:8});assert.equal(after.other_brand_stock,5);assert.deepEqual(after.gl,before.gl)
  assert.equal(requests.length,1);assert.equal(requests[0].p_action,'CREATE');assert.equal(requests[0].p_payload.items.length,4)
  await detail.getByRole('button',{name:'Edit draft invoice',exact:true}).click();await ui.expect(form).toBeVisible()
  await ui.expect(form.getByRole('region',{name:'Seri '+seri(f.series_sku),exact:true})).toContainText('Total seri: 1 lusin (12 PCS)');await ui.expect(form.getByRole('region',{name:'Seri '+seri(f.single_sku),exact:true})).toContainText('Total seri: 1 lusin (12 PCS)')
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_READBACK.png`,fullPage:true})
  return{status:'PASS',phone:mobile,three_sizes_added_by_one_pick:['31','32','33'],picked_at_one_dozen:'4/4/4',manual_3_5_4:'1 lusin',sizes_side_by_side:true,manual_4_5_4:'1 lusin 1 potong',uneven_refused_kept:'4/5/4',two_dozen:'8/8/8',one_size_one_dozen:12,saved_qty:after.qty,reserved_stock:after.stock,other_brand_same_sku_left_out:true,other_brand_stock:after.other_brand_stock,gl_unchanged:true,one_request:true,reopened_reads_1_lusin_each:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
// D14-14 G1: SELESAI DIJAHIT on the connected WIP & Sewing page (like the demo card), desktop and phone.
async function wipPage(ui,page){
 const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• WIP & Sewing',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'WIP & Sewing',exact:true})).toBeVisible()
}
async function sewing(ui,today,mobile){
 const f=fixture('sewing',{today}),name=`CP17_G1_SEWING_${mobile?'MOBILE':'DESKTOP'}`,user=await ui.login('OWNER',{label:'cp17-g1-'+(mobile?'mobile':'desktop'),mobile}),page=user.page,requests=[]
 const state=()=>fixture('sewing_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_sewing_completion_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.deepEqual([before.sewn,before.ready,before.posted_work],[0,0,0])
  await wipPage(ui,page);await page.getByLabel('Cari WIP',{exact:true}).fill(f.number);await page.getByLabel('Cari WIP',{exact:true}).press('Enter')
  const card=page.locator('.cwip-list>article').filter({hasText:f.number});await ui.expect(card).toHaveCount(1)
  const panel=card.getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
  await panel.getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await ui.expect(panel).toContainText('0 / 10 pcs');await ui.expect(panel).toContainText('Rp4')
  const save=panel.getByRole('button',{name:'Simpan selesai jahit',exact:true});await ui.expect(save).toBeDisabled()
  await panel.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('11')
  await ui.expect(panel.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true})).toBeDisabled()
  await panel.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('4')
  await panel.getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Setoran pagi mandor')
  await ui.expect(panel).toContainText('4 pcs × Rp4 = Rp16')
  await panel.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await save.click()
  await ui.expect(page.getByText(f.number+': 4 pcs tercatat selesai dijahit. Upah mandor Rp16 masuk hutang mandor; 4 pcs siap dikirim ke laundry.')).toBeVisible()
  const after=state()
  assert.deepEqual([after.sewn,after.ready,after.posted_work,after.history],[4,4,1,1]);assert.deepEqual(after.wage,[['16.00','16.00','1']])
  assert.equal(requests.length,1);assert.equal(requests[0].p_payload.action,'RECORD');assert.equal(requests[0].p_payload.qty_pcs,'4');assert.equal(requests[0].p_payload.group_id,f.group)
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',phone:mobile,recorded:4,over_remaining_kept_off:true,wage:'16 (Mandor 3 + Obras 1 per pcs)',ready_for_laundry:4,one_request:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
// D14-14 G2: finish a PO and lock its HPP on the connected HPP & Rekalkulasi page, desktop and phone.
async function hppPage(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached();const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• HPP & Rekalkulasi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'HPP per SKU',exact:true})).toBeVisible()
}
const hppStatusText={SEMENTARA:'Sementara \\(PO belum selesai\\)',BELUM_LENGKAP:'Belum lengkap, masih bisa berubah',LENGKAP_BERDASARKAN_DATA_SAAT_INI:'Final, lengkap menurut data saat ini'}
const esc=t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
async function finishPo(ui,today,mobile){
 const f=fixture('finish',{today}),name=`CP17_G2_FINISH_${mobile?'MOBILE':'DESKTOP'}`,user=await ui.login('OWNER',{label:'cp17-g2-'+(mobile?'mobile':'desktop'),mobile}),page=user.page,requests=[]
 const state=()=>fixture('finish_state',f)
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_finish_po_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=state();assert.notEqual(before.status,'FINISHED');assert.equal(before.history,0)
  await hppPage(ui,page);const panel=page.getByRole('region',{name:'Selesaikan PO',exact:true})
  await panel.getByLabel('Cari nomor PO',{exact:true}).fill(f.number);await panel.getByRole('button',{name:'Cari PO',exact:true}).click()
  await panel.getByRole('button',{name:'Pilih PO '+f.number,exact:true}).click()
  const detail=panel.getByRole('region',{name:'Selesai PO '+f.number,exact:true})
  await ui.expect(detail).toContainText('dikirim 10 · kembali 10');await ui.expect(detail).toContainText('10 dari 10 pcs GOOD laundry');await ui.expect(detail).toContainText('Sementara (PO belum selesai)')
  const save=detail.getByRole('button',{name:'Selesaikan PO',exact:true});await ui.expect(save).toBeDisabled()
  await ui.expect(detail.getByLabel('PO '+f.number+' sudah diperiksa',{exact:true})).toBeDisabled()
  await detail.getByLabel('Catatan selesai PO '+f.number,{exact:true}).fill('Semua barang sudah QC')
  await detail.getByLabel('PO '+f.number+' sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await save.click()
  await ui.expect(panel.getByText(new RegExp('^'+f.number.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+': PO selesai pada '))).toBeVisible()
  const after=state()
  assert.equal(after.status,'FINISHED');assert.equal(after.wip,'0.00');assert.equal(after.history,1)
  assert.equal(requests.length,1);assert.equal(requests[0].p_payload.action,'FINISH');assert.equal(requests[0].p_payload.po_id,f.po)
  // Astra ASTRA-C17-05: how final the HPP is follows the server's display_status, never the PO status alone.
  await ui.expect(panel.getByText(new RegExp('HPP Rp'+after.per_pcs_text+'/pcs untuk 10 pcs'))).toBeVisible()
  await ui.expect(panel.getByText(new RegExp(hppStatusText[after.display_status]))).toBeVisible()
  if(after.display_status!=='LENGKAP_BERDASARKAN_DATA_SAAT_INI')await ui.expect(panel.getByText(/Final/)).toHaveCount(0)
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',phone:mobile,po:f.number,finished:true,wip_after:after.wip,hpp_per_pcs:after.per_pcs,hpp_display_status:after.display_status,one_request:true}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
// R2-05 (owner D15-4, Fable FABLE-014): finish a PO, reopen it on the same page, then finish it again: same HPP.
async function reopenPo(ui,today,mobile){
 const f=fixture('finish',{today}),name=`CP17_R2_PO_REOPEN_${mobile?'MOBILE':'DESKTOP'}`,user=await ui.login('OWNER',{label:'cp17-r2-reopen-'+(mobile?'mobile':'desktop'),mobile}),page=user.page,requests=[]
 const state=()=>fixture('finish_state',f)
 page.on('request',r=>{const m=r.url().match(/\/rpc\/(erp_cp7_(?:finish|reopen)_po_v1)$/);if(m)requests.push([m[1],r.postDataJSON()])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await hppPage(ui,page);const panel=page.getByRole('region',{name:'Selesaikan PO',exact:true})
  const open=async()=>{await panel.getByLabel('Cari nomor PO',{exact:true}).fill(f.number);await panel.getByRole('button',{name:'Cari PO',exact:true}).click();await panel.getByRole('button',{name:'Pilih PO '+f.number,exact:true}).click()}
  const finish=async note=>{
   await open();const detail=panel.getByRole('region',{name:'Selesai PO '+f.number,exact:true})
   await detail.getByLabel('Catatan selesai PO '+f.number,{exact:true}).fill(note);await detail.getByLabel('PO '+f.number+' sudah diperiksa',{exact:true}).check()
   await detail.getByRole('button',{name:'Selesaikan PO',exact:true}).click();await ui.expect(panel.getByText(new RegExp('^'+esc(f.number)+': PO selesai pada '))).toBeVisible()}
  await finish('Semua barang sudah QC');const first=state();assert.equal(first.status,'FINISHED');assert.equal(first.wip,'0.00')
  await open();const reopen=panel.getByRole('region',{name:'Buka ulang PO '+f.number,exact:true});await ui.expect(reopen).toContainText('0 dari 10 pcs')
  const go=reopen.getByRole('button',{name:'Buka ulang PO '+f.number,exact:true});await ui.expect(go).toBeDisabled()
  await reopen.getByLabel('Alasan buka ulang PO '+f.number,{exact:true}).fill('Biaya laundry ternyata belum masuk')
  await ui.expect(go).toBeDisabled();await reopen.getByLabel('Buka ulang PO '+f.number+' sudah diperiksa',{exact:true}).check()
  assert.deepEqual(state(),first);assert.equal(requests.length,1)
  await noSideScroll(ui,page);await reopen.scrollIntoViewIfNeeded();await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  await go.click();await ui.expect(panel.getByText(new RegExp('^'+esc(f.number)+': PO dibuka ulang pada '))).toBeVisible()
  const reopened=state()
  assert.notEqual(reopened.status,'FINISHED');assert.equal(reopened.reopen_history,1);assert.equal(reopened.posted_closes,0);assert.equal(reopened.wip,reopened.reversed_residual)
  await page.screenshot({path:`cp6-proof/t3/${name}_REOPENED.png`,fullPage:true})
  await finish('Selesai lagi tanpa transaksi baru');const again=state()
  assert.equal(again.status,'FINISHED');assert.equal(again.wip,'0.00');assert.equal(again.per_pcs,first.per_pcs);assert.equal(again.history,2)
  assert.deepEqual(requests.map(r=>[r[0],r[1].p_payload.action,r[1].p_payload.po_id]),[['erp_cp7_finish_po_v1','FINISH',f.po],['erp_cp7_reopen_po_v1','REOPEN',f.po],['erp_cp7_finish_po_v1','FINISH',f.po]])
  await noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_FINISHED_AGAIN.png`,fullPage:true})
  return{status:'PASS',phone:mobile,po:f.number,first_hpp_per_pcs:first.per_pcs,reopened_status:reopened.status,returned_to_wip:reopened.wip,hpp_after_refinish:again.per_pcs,requests:3}
 }catch(error){let actual;try{actual=state()}catch(e){actual={observation_error:String(e)}};await failure(page,name,error,actual,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today){return[['CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP',()=>pickupReversal(ui,today)],['CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE',()=>fabricReturn(ui,today)],['CP17_BROWSER_KASBON_GIVE_DEDUCT_DESKTOP',()=>kasbon(ui,today)],
 ['CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP',()=>seriesDozens(ui,today,false)],['CP17_BROWSER_D14_5_SERIES_DOZENS_MOBILE',()=>seriesDozens(ui,today,true)],
 ['CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP',()=>fabricReturnCorrect(ui,today)],
 ['CP17_BROWSER_G1_SEWING_DESKTOP',()=>sewing(ui,today,false)],['CP17_BROWSER_G1_SEWING_MOBILE',()=>sewing(ui,today,true)],
 ['CP17_BROWSER_G2_FINISH_DESKTOP',()=>finishPo(ui,today,false)],['CP17_BROWSER_G2_FINISH_MOBILE',()=>finishPo(ui,today,true)],
 ['CP17_BROWSER_R2_PO_REOPEN_DESKTOP',()=>reopenPo(ui,today,false)],['CP17_BROWSER_R2_PO_REOPEN_MOBILE',()=>reopenPo(ui,today,true)],
 // Owner D15-3: master screens and the screen-only chain (cp7_master_browser.mjs), with this harness's fixture and page helpers.
 ...master.cases(ui,today,{fixture,openGroup,wipPage,noSideScroll,failure}),
 // Owner D15-6: Buat Potongan with the PO made automatically (cp7_auto_po_browser.mjs).
 ...autoPo.cases(ui,today,{fixture,noSideScroll,failure}),
 // Owner D15-5: the official cutover date on the Impor data awal page (cp7_cutover_browser.mjs).
 ...cutover.cases(ui,today,{fixture,noSideScroll,failure}),
 // Sol R2-10: SELESAI DIJAHIT per SKU of a wave Potongan (cp7_wave_sewing_browser.mjs).
 ...wave.cases(ui,today,{fixture,noSideScroll,failure})]}
