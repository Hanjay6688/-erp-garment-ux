// R3-05 (auditor Fable FABLE-016 remainder, S3): "Posting QC & Final SKU and the deduction of Nota Ambil Aksesori into payroll
// were only tested through SQL or the frozen CP6 UI." Browser cases on the connected screens, real Auth and PostgREST on the
// committed copy; every oracle is the Native rows read by cp7_r3_qc_note_cases.py (fixtures r305_qc_state / r305_note_state),
// never a facade's answer.
// QC (desktop 1440 and phone 390): ten pieces back GOOD from laundry. First a seeded role that may view QC & Final SKU but not
// post it opens the connected page (App.tsx page 'qc', runtime.qcFinalMode CONNECTED -> ConnectedQcFinalPage): it sees the
// queue, every input and the post button locked, the "Mode lihat saja" notice; the screen sends no write and the same write
// sent with its own token is refused by the server (42501); nothing changes. Then OWNER posts the ten as GOOD under a fresh
// Final SKU into an FG warehouse; the Native rows hold exactly one QC inspection numbered from the screen's request UUID, one
// item, one PRODUCTION lot, one QC_GOOD movement of 10, no BS, the PO at QC, the WIP stage events unchanged, ready-for-QC
// 10 -> 0, and PO_HPP_GL_SYNC journals Dr FG / Cr WIP equal to the lot's current HPP. Desktop loses the answer on the way
// back: the screen's own check ("Cek status transaksi") resends the same UUID and payload; phone posts straight. Both then
// resend the captured request once more with the user's token: the same answer, no second effect.
// Note to payroll (desktop): on "Nota Ambil Aksesori" OWNER posts note B (3 x 500) and cancels it on the screen, then posts
// note A (7 x 300 = 2100) for the same Mandor; on "Payroll & Kasbon" the count deducts A only (MATERIAL_KASBON 2100, net
// 3900 = 6000 - 2100); while the payroll is active the screen refuses to cancel A; approve and pay from a bank holding owner
// capital of exactly 3900: bank 0, deduction and payment journals, the Mandor's receivable back to 0.
import assert from'node:assert/strict'
import{randomUUID}from'node:crypto'
import{mkdirSync}from'node:fs'
const SAVE_QC='/rpc/erp_save_laundry_qc_action_v1'
const POST_QC='Post QC + Final SKU atomic'
const CONFIRM_QC='Saya sudah mencocokkan hasil QC fisik, ukuran, Merek/Nomor SKU/Model, jumlah Good/BS, lokasi, dan waktu.'
const cents=v=>Math.round(Number(v)*100)
// The page's own money text (procurementContract formatReceiptDecimal): 3900.00 -> Rp3.900, 12.50 -> Rp12,5.
const rp=v=>{const[w,c='']=String(v).split('.'),f=c.replace(/0+$/,'');return'Rp'+w.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(f?','+f:'')}
async function nav(ui,page,item,group){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await link.click()
}
async function qcPage(ui,page,f){
 await nav(ui,page,'QC & Final SKU','Produksi');await ui.expect(page.getByRole('heading',{name:'QC & Final SKU',exact:true})).toBeVisible()
 await ui.expect(page.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled({timeout:20000})
 // Search by the PO number: a filtered queue then still proves every ready piece of this Potongan (qcQueueSourceComplete).
 await page.locator('nav.clq-tabs input').fill(f.query)
 const potongan=page.getByRole('combobox',{name:/^POTONGAN DENGAN GOOD LAUNDRY SIAP QC/})
 await ui.expect(potongan.locator(`option[value="${f.group}"]`)).toHaveCount(1,{timeout:20000})
 return potongan
}
function qcBody(f,reason){
 return{p_action:'POST_FINAL_SKU',p_client_request_id:randomUUID(),p_expected_version:f.group_version,p_payload:{cutting_group_id:f.group,
  destination_location_id:f.location,physical_at:f.qc_iso,reason,good_qty_pcs:10,completion_mode:'ALL_READY',
  lines:[{final_product_id:f.product,qty_good_pcs:10,qty_bs_pcs:0,source_laundry_receipt_line_id:f.receipt_line,source_laundry_receipt_batch_size_line_id:f.receipt_size,notes:'R3-05 role check'}]}}
}
// What one QC post of the ten pieces must have written, from the Native rows only.
function qcPosted(s,before,f,request){
 const day=f.qc_local.slice(2,10).replaceAll('-','')
 assert.equal(s.inspections.length,1,JSON.stringify(s.inspections));const[qc]=s.inspections
 assert.deepEqual([qc.number,qc.status,qc.location,qc.physical_local],['FGP-'+day+'-'+request.replaceAll('-','').toUpperCase(),'POSTED',f.location,f.qc_local])
 assert.equal(s.items.length,1);const[item]=s.items
 assert.deepEqual([item.inspection,item.product,item.good,item.bs,item.receipt_line],[qc.id,f.product,10,0,f.receipt_line])
 assert.equal(s.lots.length,1);const[lot]=s.lots;assert.deepEqual([lot.product,lot.qc_item,lot.origin],[f.product,item.id,'PRODUCTION'])
 assert.deepEqual(s.movements.map(m=>[m.lot,m.location,m.qty,m.movement_type,m.source_type,m.source_id,m.reversal_of]),[[lot.id,f.location,10,'QC_GOOD','QC_ITEM',item.id,null]])
 assert.deepEqual([s.fg_stock,s.bs_cases,s.po],[10,0,['QC','QC']])
 // The QC writer moves no WIP stage (the LAUNDRY -> QC return stays as it was); the pieces leave the ready-for-QC count.
 assert.deepEqual(s.stage_events,before.stage_events);assert.deepEqual([s.received_good,s.qc_accounted,s.ready],[10,10,0])
 const old=new Set(before.journals.map(j=>j.id)),fresh=s.journals.filter(j=>!old.has(j.id))
 assert.ok(fresh.length&&fresh.every(j=>j.balanced),JSON.stringify(fresh))
 const sync=fresh.filter(j=>j.source_type==='PO_HPP_GL_SYNC'&&j.status==='POSTED');assert.ok(sync.length>=1,JSON.stringify(fresh))
 assert.ok(sync.every(j=>j.economic_date===f.qc_day&&Object.keys(j.nets).every(k=>['FG_INVENTORY','WIP'].includes(k))),JSON.stringify(sync))
 const fg=sync.reduce((a,j)=>a+cents(j.nets.FG_INVENTORY??'0'),0),wip=sync.reduce((a,j)=>a+cents(j.nets.WIP??'0'),0)
 assert.ok(fg>0);assert.equal(wip,-fg);assert.equal(cents(s.fg_balance)-cents(before.fg_balance),fg)
 assert.equal(s.fg_balance,s.hpp_fg_value,JSON.stringify({fg:s.fg_balance,hpp:s.hpp}))
 return{qc,item,lot,fg_value:s.fg_balance,sync_journals:sync.length,other_new_journals:fresh.filter(j=>!sync.includes(j)).map(j=>j.source_type)}
}
async function qcFinal(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_05_QC_FINAL_SKU_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r305_qc',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r305_qc_state',f)
 let page=null,owner=null,limited=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.deepEqual([before.inspections.length,before.lots.length,before.fg_stock,before.ready,before.fg_balance],[0,0,0,10,'0.00'],JSON.stringify(before))
  // 1. A seeded role with QC & Final SKU view but not post: read-only screen, no write sent, the server refuses one too.
  seen.step='limited';limited=await ui.login(f.limited_role,{label:'cp17-r3-05-qc-limited-'+(mobile?'mobile':'desktop'),mobile});page=limited.page
  const blocked=[];page.on('request',r=>{if(r.url().endsWith(SAVE_QC))blocked.push(r.postDataJSON())})
  let potongan=await qcPage(ui,page,f)
  await ui.expect(page.getByRole('status').filter({hasText:'Mode lihat saja untuk finalisasi QC.'})).toBeVisible()
  await ui.expect(page.getByRole('region',{name:'Hak akses aktif',exact:true})).toContainText('Terkunci · perlu Post Final SKU')
  await ui.expect(potongan).toBeDisabled();await ui.expect(page.getByLabel('LOKASI FG TUJUAN',{exact:true})).toBeDisabled()
  await ui.expect(page.getByLabel(CONFIRM_QC,{exact:true})).toBeDisabled();await ui.expect(page.getByRole('button',{name:POST_QC,exact:true})).toBeDisabled()
  await ui.expect(page.locator(`button[aria-label="${POST_QC}"]:enabled`)).toHaveCount(0)
  const forced=seen.forced=await limited.rpc('erp_save_laundry_qc_action_v1',qcBody(f,'R3-05 role tanpa izin post'))
  assert.equal(forced.status,403,JSON.stringify(forced));assert.match(JSON.stringify(forced.body),/PERMISSION_DENIED: production\.final_sku\.post/)
  assert.deepEqual(state(),before);assert.equal(blocked.length,0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_LIMITED.png`,fullPage:true})
  await limited.context.close();limited=null
  // 2. OWNER posts the ten pieces as GOOD under the fresh Final SKU.
  seen.step='owner';owner=await ui.login('OWNER',{label:'cp17-r3-05-qc-'+(mobile?'mobile':'desktop'),mobile});page=owner.page
  page.on('request',r=>{if(r.url().endsWith(SAVE_QC))requests.push(r.postDataJSON())})
  potongan=await qcPage(ui,page,f)
  await potongan.selectOption(f.group);const editor=page.locator('.clq-qc-editor');await ui.expect(editor).toContainText(f.group_number)
  await page.getByLabel('LOKASI FG TUJUAN',{exact:true}).selectOption(f.location)
  await page.getByLabel('WAKTU FISIK QC',{exact:true}).fill(f.qc_local)
  await page.getByLabel('ALASAN / BUKTI HASIL QC',{exact:true}).fill('R3-05 hitung fisik dan label SKU sudah cocok')
  await page.getByLabel(`Good final size ${f.size_code}`,{exact:true}).fill('10')
  const row=editor.locator('article').filter({hasText:'Ukuran '+f.size_code})
  await row.getByLabel(`Cari Final SKU size ${f.size_code}`,{exact:true}).fill(f.sku);await row.getByRole('button',{name:'Cari SKU',exact:true}).click()
  const sku=row.getByLabel(`Final SKU size ${f.size_code}`,{exact:true})
  await ui.expect(sku.locator(`option[value="${f.product}"]`)).toHaveCount(1,{timeout:20000});await sku.selectOption(f.product)
  await ui.expect(page.locator('.clq-impact')).toContainText('Good 10 · BS 0 · dipilih 10 dari 10 pcs terlihat')
  await ui.expect(page.locator('.clq-impact')).toContainText('Seluruh barang yang sudah siap QC dipilih.')
  await page.getByLabel(CONFIRM_QC,{exact:true}).check()
  const post=page.getByRole('button',{name:POST_QC,exact:true});await ui.expect(post).toBeEnabled()
  assert.deepEqual(state(),before);assert.equal(requests.length,0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_REVIEW.png`,fullPage:true})
  let answer=null,lostState=null
  if(!mobile){
   // The answer is lost on the way back: the server has committed, the screen does not know it yet.
   // What the interception saw is kept (CI 39019699925: the answer stayed null on desktop while the phone path passed).
   const intercept=seen.intercept=[]
   await page.route('**/rest/v1/rpc/erp_save_laundry_qc_action_v1',async route=>{
    if(answer)return route.continue()
    let reply
    try{reply=await route.fetch()}catch(error){intercept.push({fetch_error:String(error).slice(0,500)});throw error}
    const text=await reply.text();intercept.push({status:reply.status(),body:text.slice(0,800)})
    if(reply.status()!==200){await route.fulfill({response:reply});return}
    answer=JSON.parse(text);await route.abort('failed')
   })
   await post.click()
   const check=page.getByRole('button',{name:'Reconcile UUID lama',exact:true});await ui.expect(check).toBeVisible({timeout:20000})
   await ui.expect(page.locator(`button[aria-label="${POST_QC}"]:enabled`)).toHaveCount(0)
   assert.ok(answer&&answer.committed===true,JSON.stringify({answer,intercept,alert:await page.locator('.clq-alert').allInnerTexts()}))
   lostState=seen.lost_state=state();seen.lost=qcPosted(lostState,before,f,requests[0].p_client_request_id)
   await check.click()
   await ui.expect(page.locator('.clq-alert.notice')).toContainText('Transaksi sudah direconcile dengan UUID lama; workspace authoritative dimuat ulang.')
  }else{
   const replied=page.waitForResponse(r=>r.url().endsWith(SAVE_QC)&&r.request().method()==='POST')
   await post.click();const reply=await replied;assert.equal(reply.status(),200);answer=await reply.json()
   await ui.expect(page.locator('.clq-alert.notice')).toContainText('Workspace authoritative sudah dimuat ulang.')
  }
  const posted=seen.posted=state(),proof=qcPosted(posted,before,f,requests[0].p_client_request_id)
  if(lostState)assert.deepEqual(posted,lostState)  // the screen's resend of the same UUID changed nothing
  assert.equal(answer.qc_inspection_id,proof.qc.id);assert.equal(answer.client_request_id,requests[0].p_client_request_id)
  // What the screen sent: this Potongan, all ten as GOOD under the chosen Final SKU, the version it read.
  const p=requests[0];assert.equal(p.p_action,'POST_FINAL_SKU');assert.equal(p.p_expected_version,f.group_version)
  assert.deepEqual([p.p_payload.cutting_group_id,p.p_payload.destination_location_id,p.p_payload.good_qty_pcs,p.p_payload.completion_mode],[f.group,f.location,10,'ALL_READY'])
  assert.deepEqual(p.p_payload.lines.map(l=>[l.final_product_id,l.qty_good_pcs,l.qty_bs_pcs,l.source_laundry_receipt_line_id,l.source_laundry_receipt_batch_size_line_id]),[[f.product,10,0,f.receipt_line,f.receipt_size]])
  assert.equal(requests.length,mobile?1:2);assert.ok(requests.every(r=>r.p_client_request_id===p.p_client_request_id&&JSON.stringify(r.p_payload)===JSON.stringify(p.p_payload)&&r.p_expected_version===p.p_expected_version))
  // The same request once more with the user's own token: the same answer and no second effect.
  const again=seen.again=await owner.rpc('erp_save_laundry_qc_action_v1',p);assert.equal(again.status,200,JSON.stringify(again));assert.deepEqual(again.body,answer)
  assert.deepEqual(state(),posted)
  // The screen reads it back: the Potongan has left the queue; the history shows the inspection.
  await ui.expect(potongan.locator(`option[value="${f.group}"]`)).toHaveCount(0)
  await page.locator('nav.clq-tabs').getByRole('button',{name:'Riwayat & koreksi',exact:true}).click()
  const card=page.locator(`[data-qc-inspection-id="${proof.qc.id}"]`);await ui.expect(card).toContainText(`${proof.qc.number} · ${f.po_number}`)
  await ui.expect(card).toContainText('Good 10 · BS 0');await ui.expect(card).toContainText('Tersimpan')
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_COMMITTED.png`,fullPage:true})
  return{status:'PASS',finding:'FABLE-016',round:'R3-05',phone:mobile,screen:'QC & Final SKU (ConnectedQcFinalPage)',
   limited_role:f.limited_role,limited_role_post_locked_and_server_refused:true,qc_inspection:proof.qc.number,good:10,bs:0,fg_lot:proof.lot.id,
   fg_movement_qty:10,ready_for_qc:[10,0],wip_stage_events_unchanged:true,fg_value_equals_lot_hpp:proof.fg_value,sync_journals:proof.sync_journals,
   other_new_journals:proof.other_new_journals,lost_answer_resent_same_uuid:!mobile,same_request_replayed_no_second_effect:true,sends:requests.length+1}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};if(page)await h.failure(page,name,error,seen,requests);throw error}
 finally{if(limited)await limited.context.close();if(owner)await owner.context.close()}
}
async function notePage(ui,page){
 await nav(ui,page,'Nota Ambil Aksesori','Keuangan');await ui.expect(page.getByRole('heading',{name:'Nota Ambil Aksesori',exact:true})).toBeVisible()
 await ui.expect(page.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
}
async function postNote(ui,page,f,n,reason){
 const form=page.getByRole('region',{name:'Form nota aksesori',exact:true}),title=form.getByRole('heading',{level:2})
 await page.getByRole('button',{name:'Nota baru',exact:true}).click();await ui.expect(title).toContainText('Nota baru')
 await form.getByLabel('Nomor nota aksesori',{exact:true}).fill(n.number)
 await form.getByLabel('Mandor aksesori',{exact:true}).selectOption(f.contractor)
 await form.getByLabel('Gudang aksesori',{exact:true}).selectOption(f.location)
 await form.getByLabel('Waktu ambil aksesori',{exact:true}).fill(f.note_local)
 await form.getByLabel('Cari barang aksesori',{exact:true}).fill(f.material_code)
 await form.getByRole('button',{name:'Perbarui harga dan stok',exact:true}).click()
 const add=form.getByLabel('Tambah aksesori',{exact:true});await ui.expect(add).toBeEnabled({timeout:20000});await add.selectOption(f.material)
 await form.getByLabel('Jumlah PCS 1',{exact:true}).fill(String(n.qty));await form.getByLabel('Harga per PCS 1',{exact:true}).fill(n.price)
 await form.getByLabel('Alasan nota aksesori',{exact:true}).fill(reason)
 await form.getByRole('button',{name:'Periksa pengesahan',exact:true}).click()
 const review=form.getByRole('region',{name:'Konfirmasi nota',exact:true});await ui.expect(review).toContainText(`Sahkan pengeluaran ${n.qty} PCS`)
 await review.getByRole('button',{name:'Sahkan nota',exact:true}).click();await ui.expect(title).toContainText(n.number+' · POSTED',{timeout:20000})
 return form
}
async function payrollPage(ui,page,f){
 await nav(ui,page,'Payroll & Kasbon','Keuangan');const pay=page.locator('.cpay');await ui.expect(pay.getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
 await pay.getByLabel('Cari payroll',{exact:true}).fill(f.label);await pay.getByRole('button',{name:'Cari payroll',exact:true}).click()
 await ui.expect(pay.locator('.cproc-receipt')).toHaveCount(1,{timeout:20000});await pay.locator('.cproc-receipt').click()
 const detail=pay.getByRole('region',{name:'Rincian payroll'});await ui.expect(detail.locator('.cpay-reference').first()).toHaveText(f.payroll_number)
 return detail
}
async function noteToPayroll(ui,today,h){
 const name='CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP',f=h.fixture('r305_note',{today}),seen={prepared:f},requests=[]
 const state=()=>h.fixture('r305_note_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-05-note-payroll',mobile:false}),page=user.page
 page.on('request',r=>{const m=r.url().match(/\/rpc\/(erp_save_accessory_issue_action_v1|erp_cp7_save_payroll_v1)$/);if(m)requests.push([m[1],r.postDataJSON().p_action])})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.ok(['DRAFT','CALCULATED','REVIEW'].includes(before.payroll.status),before.payroll.status)
  assert.deepEqual([before.payroll.labor,before.payroll.deduction,before.payroll.net,before.deductions,before.notes.a,before.notes.b],[f.labor,'0.00',f.labor,[],null,null])
  assert.deepEqual([before.receivable,before.bank,before.stock,before.collectible],['0.00',f.net,f.stock,'0.00'])
  // 1. Note B is posted, then cancelled on the screen before any payroll is counted.
  seen.step='note_b';await notePage(ui,page)
  let form=await postNote(ui,page,f,f.b,'R3-05 nota yang nanti dibatalkan')
  let s=seen.b_posted=state();assert.deepEqual([s.notes.b.status,s.notes.b.contractor,s.notes.b.location,s.notes.b.physical_local],['POSTED',f.contractor,f.location,f.note_local])
  assert.deepEqual(s.notes.b.items.map(i=>[i.material,i.qty,i.amount]),[[f.material,f.b.qty,f.b.total]]);assert.deepEqual([s.receivable,s.stock],[f.b.total,f.stock-f.b.qty])
  await form.getByLabel('Alasan pembatalan nota',{exact:true}).fill('R3-05 salah catat, barang kembali ke gudang')
  await form.getByRole('button',{name:'Periksa pembatalan',exact:true}).click();await form.getByRole('button',{name:'Sahkan pembatalan nota',exact:true}).click()
  await ui.expect(form.getByRole('heading',{level:2})).toContainText(f.b.number+' · REVERSED',{timeout:20000})
  await ui.expect(form.getByRole('status').filter({hasText:'Nota dibatalkan.'})).toBeVisible()
  s=seen.b_reversed=state();assert.deepEqual([s.notes.b.status,s.receivable,s.stock,s.collectible],['REVERSED','0.00',f.stock,'0.00'])
  // 2. Note A for the same Mandor and day: the one the payroll must deduct.
  seen.step='note_a';form=await postNote(ui,page,f,f.a,'R3-05 ambil aksesori untuk payroll')
  s=seen.a_posted=state();assert.equal(s.notes.a.status,'POSTED');assert.deepEqual(s.notes.a.items.map(i=>[i.material,i.qty,i.amount]),[[f.material,f.a.qty,f.a.total]])
  assert.deepEqual([s.receivable,s.stock,s.collectible,s.payroll],[f.a.total,f.stock-f.a.qty,f.a.total,before.payroll])
  const itemA=s.notes.a.items[0].id,itemB=s.notes.b.items[0].id
  await page.screenshot({path:`cp6-proof/t3/${name}_NOTE.png`,fullPage:true})
  // 3. Payroll & Kasbon: the count takes note A only.
  seen.step='count';let detail=await payrollPage(ui,page,f)
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payroll'+rp(f.labor))
  await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click();await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payroll'+rp(f.net),{timeout:20000})
  s=seen.counted=state()
  assert.deepEqual(s.deductions,[['MATERIAL_KASBON',itemA,f.a.total]]);assert.ok(!s.deductions.some(d=>d[1]===itemB))
  assert.deepEqual([s.payroll.labor,s.payroll.deduction,s.payroll.net,s.collectible],[f.labor,f.a.total,f.net,f.a.total])
  assert.equal(cents(s.payroll.labor)-cents(s.payroll.deduction),cents(s.payroll.net));assert.deepEqual([s.receivable,s.bank],[f.a.total,f.net])
  await detail.getByRole('group',{name:'Jenis rincian payroll'}).getByRole('button',{name:/^Potongan & kasbon/}).click()
  const lines=detail.locator('.cpay-lines .cpay-line');await ui.expect(lines).toHaveCount(1,{timeout:20000})
  await ui.expect(lines.first()).toContainText('MATERIAL KASBON');await ui.expect(lines.first()).toContainText(rp(f.a.total))
  await page.screenshot({path:`cp6-proof/t3/${name}_COUNTED.png`,fullPage:true})
  // 4. While that payroll is active the note page does not let note A be cancelled.
  seen.step='locked';await notePage(ui,page)
  const search=page.getByRole('form',{name:'Cari, browse, urutkan dan filter nota aksesori',exact:true})
  await search.getByLabel('Cari nota aksesori',{exact:true}).fill(f.a.number);await search.getByRole('button',{name:'Cari nota',exact:true}).click()
  await page.getByRole('region',{name:'Riwayat nota aksesori',exact:true}).getByRole('button',{name:'Buka '+f.a.number,exact:true}).click()
  form=page.getByRole('region',{name:'Form nota aksesori',exact:true});await ui.expect(form.getByRole('heading',{level:2})).toContainText(f.a.number+' · POSTED',{timeout:20000})
  await ui.expect(form).toContainText('Nota sudah terkait payroll aktif. Selesaikan pembatalan payroll terkait terlebih dahulu.')
  await ui.expect(form.getByLabel('Alasan pembatalan nota',{exact:true})).toBeDisabled();await ui.expect(form.getByRole('button',{name:'Periksa pembatalan',exact:true})).toBeDisabled()
  assert.deepEqual(state(),s)
  // 5. Approve, then pay from the bank that holds exactly the net.
  seen.step='approve';detail=await payrollPage(ui,page,f);await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payroll'+rp(f.net))
  const confirm=async(label,setup)=>{
   await detail.getByRole('button',{name:label,exact:true}).click()
   const box=detail.getByRole('region',{name:'Periksa tindakan payroll'}),commit=box.getByRole('button',{name:label+' sekarang',exact:true})
   if(setup)await setup(box)
   await box.getByLabel('Alasan tindakan payroll',{exact:true}).fill('R3-05 potongan nota aksesori diperiksa');await box.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check()
   await ui.expect(commit).toBeEnabled();await commit.click()
  }
  await confirm('Setujui payroll');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled({timeout:20000})
  s=seen.approved=state();assert.equal(s.payroll.status,'APPROVED');assert.deepEqual(s.deductions,seen.counted.deductions);assert.equal(s.bank,f.net)
  seen.step='pay'
  await confirm('Lunasi payroll',async box=>{
   await box.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(f.bank_code);await box.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click()
   await ui.expect(box.locator('.cpay-cash-row')).toHaveCount(1,{timeout:20000});await box.locator('.cpay-cash-row').click()
  })
  await ui.expect.poll(()=>state().payroll.status,{timeout:20000}).toBe('PAID')
  const paid=seen.paid=state()
  assert.deepEqual([paid.payroll.labor,paid.payroll.deduction,paid.payroll.net,paid.payroll.payment_date,paid.payroll.cash_account],[f.labor,f.a.total,f.net,f.today,f.bank])
  assert.deepEqual(paid.deductions,[['MATERIAL_KASBON',itemA,f.a.total]])
  assert.deepEqual(paid.payroll_journals,{material_deduction:[2,f.a.total,f.a.total],payment:[2,f.net,f.net]})
  assert.deepEqual([paid.bank,paid.receivable,paid.stock],['0.00','0.00',f.stock-f.a.qty])
  assert.equal(cents(paid.payable)-cents(before.payable),cents(f.labor))
  assert.deepEqual([paid.notes.a.status,paid.notes.b.status],['POSTED','REVERSED'])
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah dilunasi'+rp(f.net),{timeout:20000})
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_PAID.png`,fullPage:true})
  const actions=requests.map(r=>r.join(':'))
  assert.deepEqual(actions,['erp_save_accessory_issue_action_v1:POST','erp_save_accessory_issue_action_v1:REVERSE','erp_save_accessory_issue_action_v1:POST',
   'erp_cp7_save_payroll_v1:PREPARE','erp_cp7_save_payroll_v1:APPROVE','erp_cp7_save_payroll_v1:PAY'])
  return{status:'PASS',finding:'FABLE-016',round:'R3-05',screens:['Nota Ambil Aksesori (sahkan, batalkan, sahkan)','Payroll & Kasbon (hitung, setujui, lunasi)'],
   fixture_only:['work-only payroll draft 6000 (Native Nota)','accessory stock 1000 PCS','bank with owner capital of exactly the net (D14-3)'],
   reversed_note:{number:f.b.number,amount:f.b.total,deducted:false},kept_note:{number:f.a.number,amount:f.a.total},labor:f.labor,deduction:f.a.total,net:f.net,
   cancel_refused_while_payroll_active:true,bank_after:'0.00',receivable_after:'0.00',journals:paid.payroll_journals,requests:actions}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP',()=>qcFinal(ui,today,false,h)],['CP17_BROWSER_R3_05_QC_FINAL_SKU_MOBILE',()=>qcFinal(ui,today,true,h)],
  ['CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP',()=>noteToPayroll(ui,today,h)]]
}
