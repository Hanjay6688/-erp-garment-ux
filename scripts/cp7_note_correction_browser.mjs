import assert from 'node:assert/strict'
import {execFileSync,spawn} from 'node:child_process'
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_note_correction_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p,title='Penjualan & Invoice',section='Penjualan'){
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:section})).toBeAttached()
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+title,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:section}).click();await link.click()
}
async function flow(ui,today,mobile,micro=false){
 const f=fixture('prepare',{today,microsecond_guard:micro}),user=await ui.login('OWNER',{label:'note-'+mobile+'-'+micro,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales'),suffix=(mobile?'MOBILE':'DESKTOP')+(micro?'_MICROSECOND':'')
 let peer,first,replay,trace,traceFinished,lost=false,routeDone=false;const replies=[];const peerErrors=[];let peerWrites=0
 const select=async page=>{const w=page.locator('.csales');await w.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await w.getByRole('button',{name:'Cari invoice',exact:true}).click();const row=w.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt');await ui.expect(row).toHaveCount(1);await row.click();await ui.expect(w.getByRole('complementary',{name:'Rincian invoice'})).toContainText('Sisa pembayaran Rp175')}
 try{
  const before=fixture('read',f);assert.equal(before.available,45);assert.equal(before.document.qty_pcs,'20')
  await open(ui,p);await select(p)
  if(mobile&&!micro){peer=await user.context.newPage();peer.on('pageerror',e=>peerErrors.push(String(e)));peer.on('console',m=>{if(m.type()==='error')peerErrors.push(m.text())});peer.on('request',r=>{if(r.url().includes('/rest/v1/rpc/erp_cp7_correct_note_v1'))peerWrites++});await peer.goto(ui.origin);await open(ui,peer);await select(peer)}
  await ws.getByRole('button',{name:'Benerin nota',exact:true}).click();const form=ws.getByRole('form',{name:'Benerin nota',exact:true})
  await ui.expect(form.getByLabel('Nomor draft invoice',{exact:true})).toHaveAttribute('readonly','');await ui.expect(form.getByLabel('Waktu draft invoice WIB',{exact:true})).toHaveAttribute('readonly','')
  await form.getByLabel('Jumlah invoice 1',{exact:true}).fill('16');await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('Jumlah yang benar16 PCS; pembayaran dan retur tetap sama')
  await ui.expect(form.getByRole('button',{name:'Simpan pembetulan nota',exact:true})).toBeDisabled();await form.getByLabel('Pembetulan nota sudah diperiksa',{exact:true}).check()
  if(micro||mobile)await p.route('**/rest/v1/rpc/erp_cp7_correct_note_v1',async route=>{
   try{
    const body=route.request().postDataJSON();if(lost){replay=body;await route.continue();return}
    first=body;const response=await route.fetch(),actual=await response.json();replies.push({status:response.status(),body:actual})
    if(response.status()!==200){await route.fulfill({response});return}
    lost=true
    if(micro){assert.notEqual(actual.effective_at,f.bad_effective_at);await route.fulfill({response,json:{...actual,effective_at:f.bad_effective_at}})}
    else await route.abort('failed')
   }catch(e){replies.push({route_error:String(e)});await route.abort('failed').catch(()=>{})}
   finally{routeDone=true}
  })
  // The form is retired after the owning transaction's actual reply is
  // validated. Five seconds of an in-flight transaction is not a failed save.
  const committed=mobile||micro?null:p.waitForResponse(r=>r.url().includes('/rest/v1/rpc/erp_cp7_correct_note_v1')&&r.request().method()==='POST',{timeout:20000})
  trace=spawn('python',['../auditor/scripts/cp7_note_http_trace.py',suffix],{cwd:'../writer',stdio:['ignore','pipe','ignore']})
  traceFinished=new Promise(resolve=>{trace.once('exit',resolve);trace.once('error',resolve)})
  await new Promise(resolve=>{const timer=setTimeout(resolve,2000);const ready=()=>{clearTimeout(timer);resolve()};trace.stdout.once('data',ready);trace.once('exit',ready);trace.once('error',ready)})
  await form.getByRole('button',{name:'Simpan pembetulan nota',exact:true}).click()
  if(committed){const response=await committed;assert.equal(response.status(),200);const body=await response.json();assert.equal(body.kind,'COMMITTED_OUTCOME');assert.equal(body.action,'CORRECT');assert.equal(body.request_id,response.request().postDataJSON().p_request);assert.equal(body.previous_sale_id,f.root_sale);assert.equal(body.revision,'1')}
  if(mobile&&!micro){
   await ui.expect.poll(()=>routeDone,{timeout:20000}).toBe(true);assert.equal(replies[0]?.status,200,JSON.stringify(replies));assert.equal(lost,true);const other=peer.locator('.csales');await ui.expect(other.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await ui.expect(other.getByRole('button',{name:'Benerin nota',exact:true})).toBeDisabled()
   await other.getByRole('button',{name:'Muat ulang invoice',exact:true}).click();const pending=await peer.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.SALES.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)));assert.equal(pending.length,1);assert.equal(pending[0].action,'CORRECT');assert.equal(pending[0].id,first.p_request);assert.deepEqual(pending[0].payload.document,first.p_payload)
   await p.reload();await open(ui,p);await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.deepEqual(replay,first);assert.equal(peerWrites,0);assert.deepEqual(peerErrors,[])
  }
  if(micro){
   await ui.expect.poll(()=>routeDone,{timeout:20000}).toBe(true);assert.equal(replies[0]?.status,200,JSON.stringify(replies));assert.equal(lost,true);await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible()
   const actual=fixture('read',f);assert.equal(actual.history.history.length,1);assert.equal(actual.available,49)
   const pending=await p.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.SALES.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)));assert.equal(pending.length,1);assert.equal(pending[0].id,first.p_request);assert.deepEqual(pending[0].payload.document,first.p_payload)
   await ws.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(ws.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0);assert.deepEqual(replay,first);assert.equal(fixture('read',f).history.history.length,1)
  }
  await ui.expect(form).toHaveCount(0);const detail=ws.getByRole('complementary',{name:'Rincian invoice'});await ui.expect(detail).toContainText('16 PCS dalam invoice');await ui.expect(detail).toContainText('Sisa pembayaran Rp75');await ui.expect(detail).toContainText('Pembayaran tercatat Rp200')
  await ws.getByRole('button',{name:'Riwayat pembetulan nota',exact:true}).click();await ui.expect(ws.getByRole('region',{name:'Riwayat pembetulan nota',exact:true})).toContainText('Pembetulan 1');await ui.expect(ws.getByRole('region',{name:'Riwayat pembetulan nota',exact:true})).toContainText('Dibetulkan oleh');await ui.expect(ws.getByRole('region',{name:'Riwayat pembetulan nota',exact:true})).toContainText(f.tag)
  const after=fixture('read',f);assert.equal(after.available,49);assert.equal(Number(after.fg_value),735);assert.equal(after.document.financial.net_total,'275.00');assert.equal(after.document.financial.paid_total,'200.00');assert.equal(after.document.financial.open_balance,'75.00');assert.equal(after.history.history.length,1);assert.deepEqual(after.original_facts,f.original_facts)
  const source=Object.values(after.book).find(r=>r.original_physical_delta==='-20'&&r.correction_count==='1');assert.ok(source);assert.equal(source.physical_delta,'-16');assert.equal(source.reservation_delta,'0');assert.equal(Date.parse(source.physical_at),Date.parse(f.sale_at))
  mkdirSync('cp6-proof/t3',{recursive:true});await ui.expect.poll(()=>ws.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true);await p.screenshot({path:`cp6-proof/t3/NOTE_CORRECTION_${suffix}.png`,fullPage:true})
  await open(ui,p,'Mutasi Barang Jadi · Vivo','Gudang');const fg=p.locator('.cfgb');const brand=fg.locator('.cfgb-filter').first();if(!await brand.getAttribute('open'))await brand.locator('summary').click();const clear=brand.getByRole('button',{name:'Semua merek',exact:true});if(await clear.isEnabled())await clear.click();await brand.locator('summary').click()
  await fg.getByLabel('Cari buku mutasi',{exact:true}).fill(f.sku);await fg.getByRole('button',{name:'Terapkan filter buku',exact:true}).click();await ui.expect(fg).toContainText('Nota dibetulkan 1 kali');await ui.expect(fg.locator('[role="alert"]')).toHaveCount(0);await ui.expect.poll(()=>fg.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true);await p.screenshot({path:`cp6-proof/t3/NOTE_CORRECTED_BOOK_${suffix}.png`,fullPage:true})
  await open(ui,p,'Kartu Stok FG','Gudang');const lotCard=p.locator('.cfg');await lotCard.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku);await lotCard.getByLabel('Sertakan stok habis',{exact:true}).check();await lotCard.getByRole('button',{name:'Cari stok',exact:true}).click();assert.ok(after.lot_cards.length)
  for(const target of after.lot_cards){
   const position=lotCard.locator('.cfg-position').filter({hasText:target.lot_number});await ui.expect(position).toHaveCount(1);await position.locator('button').click();const ledger=lotCard.locator('.cfg-ledger');await ui.expect(ledger).toContainText(target.lot_number);await ui.expect(ledger).toContainText('Nota dibetulkan 1 kali')
   for(const row of target.sale_rows){await ui.expect(ledger).toContainText(`perubahan asal di lot ini ${Number(row.original_physical_delta)} PCS`);await ui.expect(ledger).toContainText(String(Number(row.physical_delta)))}
   await ui.expect(ledger.locator('[role="alert"]')).toHaveCount(0)
  }
  assert.equal(after.lot_cards.flatMap(x=>x.sale_rows).reduce((sum,r)=>sum+Number(r.original_physical_delta),0),-20);assert.equal(after.lot_cards.flatMap(x=>x.sale_rows).reduce((sum,r)=>sum+Number(r.physical_delta),0),-16);await p.screenshot({path:`cp6-proof/t3/NOTE_CORRECTED_LOT_${suffix}.png`,fullPage:true})
  return{status:'PASS',mobile,real_UI_Auth_HTTP_native_owning_correction:true,native_production_fixture_not_browser_production_claim:true,qty20_to16:true,cash200_and_return125_retained:true,AR75_COGS165_FG49_value735:true,immutable_original_and_one_revision:true,corrected_source_main_book:true,corrected_lot_card_original_and_effective:true,current_actor_display_visible:true,dedicated_actual_browser_one_microsecond_guard_identical_UUID_recovery:micro,lost_commit_reply_identical_UUID_reconcile:mobile?true:null,other_tab_cannot_write_or_clear_uncertain_request:mobile?true:null,screenshots:[`NOTE_CORRECTION_${suffix}.png`,`NOTE_CORRECTED_BOOK_${suffix}.png`]}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});let observed;try{observed=fixture('read',f)}catch(e){observed={error:String(e)}}writeFileSync(`cp6-proof/t3/NOTE_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,first,replay,lost,routeDone,replies,text:await p.locator('body').innerText().catch(()=>''),observed},null,2));await p.screenshot({path:`cp6-proof/t3/NOTE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{if(trace&&trace.exitCode===null){trace.kill('SIGUSR1');await traceFinished}if(peer)await peer.close().catch(()=>{});await user.context.close()}
}
async function duplicateFlow(ui,today){
 const f=fixture('prepare_duplicate',{today}),user=await ui.login('OWNER',{label:'note-duplicate-lines',mobile:false,timezoneId:'Asia/Jakarta'}),p=user.page,ws=p.locator('.csales')
 let request,reply
 try{
  const before=fixture('read_duplicate',f);assert.equal(before.available,85);assert.equal(Number(before.document.qty_pcs),15)
  const second=before.document.items.findIndex(i=>i.id===f.source_lines[1].item_id);assert.ok(second>=0)
  await open(ui,p);await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag);await ws.getByRole('button',{name:'Cari invoice',exact:true}).click()
  const invoice=ws.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt');await ui.expect(invoice).toHaveCount(1);await invoice.click()
  await ws.getByRole('button',{name:'Benerin nota',exact:true}).click();const form=ws.getByRole('form',{name:'Benerin nota',exact:true})
  await ui.expect(form.getByLabel(`Jumlah invoice ${second+1}`,{exact:true})).toHaveValue('10');await form.getByLabel(`Jumlah invoice ${second+1}`,{exact:true}).fill('6')
  await form.getByLabel('Alasan simpan invoice',{exact:true}).fill('SKU sama dua baris: baris lima tetap, baris sepuluh sebenarnya enam')
  await form.getByLabel('Pembetulan nota sudah diperiksa',{exact:true}).check()
  const committed=p.waitForResponse(r=>r.url().includes('/rest/v1/rpc/erp_cp7_correct_note_v1')&&r.request().method()==='POST',{timeout:20000})
  await form.getByRole('button',{name:'Simpan pembetulan nota',exact:true}).click();const response=await committed;request=response.request().postDataJSON();reply={status:response.status(),body:await response.json()}
  assert.equal(reply.status,200,JSON.stringify(reply));assert.equal(reply.body.kind,'COMMITTED_OUTCOME');assert.equal(reply.body.request_id,request.p_request);assert.equal(reply.body.previous_sale_id,f.root_sale)
  assert.deepEqual(request.p_payload.item_lineage,before.document.items.map(i=>i.id));await ui.expect(form).toHaveCount(0)
  await ui.expect(ws.getByRole('complementary',{name:'Rincian invoice'})).toContainText('11 PCS dalam invoice')
  const after=fixture('read_duplicate',f);assert.equal(after.available,89);assert.equal(after.history.history.length,1);assert.deepEqual(after.original_facts,f.original_facts)
  assert.deepEqual(after.main.map(r=>Number(r.physical_delta)),[-5,-6]);assert.deepEqual(after.main.map(r=>Number(r.book_physical_after)),[95,89]);assert.deepEqual(after.lot.map(r=>Number(r.physical_delta)),[-5,-6])
  await open(ui,p,'Mutasi Barang Jadi · Vivo','Gudang');const fg=p.locator('.cfgb'),brand=fg.locator('.cfgb-filter').first()
  if(!await brand.getAttribute('open'))await brand.locator('summary').click();const clear=brand.getByRole('button',{name:'Semua merek',exact:true});if(await clear.isEnabled())await clear.click();await brand.locator('summary').click()
  await fg.getByLabel('Cari buku mutasi',{exact:true}).fill(f.sku);await fg.getByRole('button',{name:'Terapkan filter buku',exact:true}).click()
  for(let index=0;index<f.source_lines.length;index++){
   const card=fg.locator(`[data-movement-id="${f.source_lines[index].movement_id}"]`);await ui.expect(card).toHaveCount(1);await ui.expect(card).toContainText('Nota dibetulkan 1 kali')
   await ui.expect(card.locator('.cfgb-balances > div').filter({has:p.getByText('Perubahan fisik',{exact:true})}).locator('dd')).toHaveText(`${[-5,-6][index]} PCS`)
   await ui.expect(card.locator('.cfgb-balances > div').filter({has:p.getByText('Akhir buku',{exact:true})}).locator('dd')).toHaveText(`${[95,89][index]} PCS`)
  }
  await ui.expect(fg.locator('[role="alert"]')).toHaveCount(0);mkdirSync('cp6-proof/t3',{recursive:true});await p.screenshot({path:'cp6-proof/t3/NOTE_DUPLICATE_SKU_MAIN_BOOK.png',fullPage:true})
  await open(ui,p,'Kartu Stok FG','Gudang');const stock=p.locator('.cfg');await stock.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku);await stock.getByLabel('Sertakan stok habis',{exact:true}).check();await stock.getByRole('button',{name:'Cari stok',exact:true}).click()
  const position=stock.locator('.cfg-position');await ui.expect(position).toHaveCount(1);await position.locator('button').click();const ledger=stock.locator('.cfg-ledger')
  for(let index=0;index<2;index++){
   const card=ledger.locator('.cfg-movement').filter({hasText:`perubahan asal di lot ini ${[-5,-10][index]} PCS`});await ui.expect(card).toHaveCount(1)
   await ui.expect(card.locator('dl > div').filter({has:p.getByText('Perubahan fisik',{exact:true})}).locator('dd')).toHaveText(String([-5,-6][index]))
  }
  await ui.expect(ledger.locator('[role="alert"]')).toHaveCount(0);await p.screenshot({path:'cp6-proof/t3/NOTE_DUPLICATE_SKU_LOT_CARD.png',fullPage:true})
  writeFileSync('cp6-proof/t3/NOTE_DUPLICATE_SKU_NATIVE_PROOF.json',JSON.stringify({request,reply,before,after},null,2))
  return{status:'PASS',real_UI_Auth_HTTP_native_owning_correction:true,same_SKU_two_native_lines5_10_to5_6:true,exact_original_item_ids_sent:true,two_main_DOM_deltas_minus5_minus6:true,two_main_DOM_balances95_89:true,two_lot_DOM_deltas_minus5_minus6:true,current_stock89_and_originals_immutable:true,screenshots:['NOTE_DUPLICATE_SKU_MAIN_BOOK.png','NOTE_DUPLICATE_SKU_LOT_CARD.png']}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});let observed;try{observed=fixture('read_duplicate',f)}catch(e){observed={error:String(e)}}writeFileSync('cp6-proof/t3/NOTE_DUPLICATE_SKU_FAILURE.json',JSON.stringify({error:String(error),stack:error.stack,request,reply,text:await p.locator('body').innerText().catch(()=>''),observed},null,2));await p.screenshot({path:'cp6-proof/t3/NOTE_DUPLICATE_SKU_FAILURE.png',fullPage:true}).catch(()=>{});throw error}
 finally{await user.context.close()}
}
export async function cases(ui,today){const tests=[['NOTE_BROWSER_DESKTOP',()=>flow(ui,today,false)],['NOTE_BROWSER_MOBILE_LOST_REPLY',()=>flow(ui,today,true)],['NOTE_BROWSER_DESKTOP_MICROSECOND_GUARD',()=>flow(ui,today,false,true)],['NOTE_BROWSER_MOBILE_MICROSECOND_GUARD',()=>flow(ui,today,true,true)],['NOTE_BROWSER_DUPLICATE_SKU_LINES',()=>duplicateFlow(ui,today)]];const manifest=JSON.parse(readFileSync(new URL('./cp7_note_correction_manifest.json',import.meta.url),'utf8'));assert.deepEqual(tests.map(([name])=>name),manifest.groups.browser);return tests}
