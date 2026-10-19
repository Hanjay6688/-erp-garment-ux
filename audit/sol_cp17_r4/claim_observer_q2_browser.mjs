// Sol's declared one-lineage missing-claim B5/B6 continuation: one Native starting lineage,
// then actual screen commands through sewing, Laundry, QC, invoice and cash.
// No route stubbing, injected success, direct business RPC or business retry.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync, writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
const helper=fileURLToPath(new URL('./invoice_observer_q2_fixture.py',import.meta.url))
const fixture=(op,p)=>JSON.parse(execFileSync('python',[helper,'claim_'+op],{input:JSON.stringify(p),encoding:'utf8',maxBuffer:16*1024*1024}))
const confirmQc='Saya sudah mencocokkan hasil QC fisik, ukuran, Merek/Nomor SKU/Model, jumlah Good/BS, lokasi, dan waktu.'
const cents=s=>{assert.match(s,/^-?\d+\.\d{2}$/);return BigInt(s.replace('.',''))}
async function nav(ui,p,item,group){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+item,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:item,exact:true})).toBeVisible()
}
async function ready(ui,p){await ui.expect(p.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled({timeout:20000})}
async function pricing(ui,p,f,section){
 await nav(ui,p,'Laundry','Produksi');await ready(ui,p)
 await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
 const root=p.getByRole('region',{name:'Harga dan tagihan laundry',exact:true})
 await ui.expect(root.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
 await root.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor)
 await ui.expect(root.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
 await root.getByRole('button',{name:section,exact:true}).click()
 return root
}
async function journey(ui,today,mode){
 const id='SOL_R4_B5_B6_CLAIM_'+mode
 const f=fixture('prepare',{today}),seen={fixture:f},requests=[]
 const user=await ui.login('OWNER',{label:'sol-r4-journey-'+mode.toLowerCase(),mobile:mode==='MOBILE'})
 const p=user.page
 if(mode==='IPAD_VIEWPORT')await p.setViewportSize({width:820,height:1180})
 p.on('request',r=>{if(r.url().includes('/rest/v1/rpc/')&&r.method()==='POST')requests.push({url:r.url().split('/rpc/')[1],body:r.postDataJSON()})})
 const state=()=>fixture('observe',f)
 const take=name=>{const s=state();seen[name]=s;assert.equal(s.all_journals_balanced,true);return s}
 const wait=async(test,value)=>ui.expect.poll(()=>test(state()),{timeout:20000}).toEqual(value)
 const samePhysical=(a,b)=>assert.deepEqual([a.qc.fg_stock,a.qc.hpp,a.qc.movements,a.qc.stage_events,a.qc.fg_balance,a.qc.wip_balance],[b.qc.fg_stock,b.qc.hpp,b.qc.movements,b.qc.stage_events,b.qc.fg_balance,b.qc.wip_balance])
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const initial=take('initial');assert.deepEqual([initial.sewn,initial.ready,initial.work.length,initial.deliveries.length,initial.receipts.length,initial.qc.fg_stock,initial.invoices.length,initial.ap,initial.bank],[0,0,0,0,0,0,0,'0.00','8.00'])
  // Record five of ten physical pieces. Over-eleven is blocked before a write.
  await nav(ui,p,'WIP & Sewing','Produksi')
  await p.getByLabel('Cari WIP',{exact:true}).fill(f.number);await p.getByLabel('Cari WIP',{exact:true}).press('Enter')
  const sewing=p.getByRole('region',{name:'Selesai jahit '+f.number,exact:true})
  await sewing.getByRole('button',{name:'Catat selesai jahit',exact:true}).click()
  await sewing.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('11')
  await ui.expect(sewing.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true})).toBeDisabled()
  assert.deepEqual(take('over_eleven'),initial)
  await sewing.getByLabel('Jumlah selesai dijahit '+f.number,{exact:true}).fill('5')
  await sewing.getByLabel('Waktu selesai jahit '+f.number,{exact:true}).fill(f.sewing_local)
  await sewing.getByLabel('Catatan selesai jahit '+f.number,{exact:true}).fill('Sol five-piece source with one missing return')
  await ui.expect(sewing).toContainText('5 pcs × Rp4 = Rp20')
  await sewing.getByLabel('Selesai jahit '+f.number+' sudah diperiksa',{exact:true}).check()
  await sewing.getByRole('button',{name:'Simpan selesai jahit',exact:true}).click()
  await wait(s=>[s.sewn,s.ready,s.work.length],[5,5,1])
  const sewn=take('sewn');assert.deepEqual(sewn.work[0].slice(1),['POSTED',['20.00','20.00','1']])
  // Send this exact batch, not whichever unrelated ready batch happens to show.
  await nav(ui,p,'Laundry','Produksi');await ready(ui,p)
  await p.getByRole('button',{name:'Kirim ke Laundry',exact:true}).click()
  await p.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE',{exact:true}).selectOption(f.batch)
  await p.getByRole('button',{name:'Isi dari sisa siap',exact:true}).click()
  await p.getByRole('combobox',{name:/^VENDOR LAUNDRY/}).selectOption(f.vendor)
  await p.getByLabel('PROSES CUCI TARGET',{exact:true}).selectOption(f.process)
  await p.getByLabel('WARNA TARGET',{exact:true}).fill('NAVY')
  await p.getByLabel('WAKTU FISIK KELUAR',{exact:true}).fill(f.send_local)
  await p.getByLabel('ALASAN / BUKTI SERAH TERIMA',{exact:true}).fill('Sol send the five pieces sewn above')
  await p.locator('.clq-confirm input').check();await p.getByRole('button',{name:'Post pengiriman atomic',exact:true}).click()
  await wait(s=>[s.deliveries.length,s.ready],[1,0]);const sent=take('sent'),delivery=sent.deliveries[0][0]
  // Receive four of five GOOD, then use the receipt's actual lineage for final SKU.
  await ready(ui,p);await p.getByRole('button',{name:'Terima kembali',exact:true}).click()
  await p.getByLabel('SURAT KIRIM AKTIF',{exact:true}).selectOption(delivery)
  await p.getByLabel('PROSES AKTUAL',{exact:true}).selectOption(f.process)
  await p.getByLabel('WAKTU FISIK KEMBALI',{exact:true}).fill(f.receive_local)
  await p.getByLabel('ALASAN / BUKTI PENERIMAAN',{exact:true}).fill('Sol four GOOD physically returned')
  await p.getByLabel('Good kembali size '+f.size_code,{exact:true}).fill('4')
  await p.locator('.clq-confirm input').check();await p.getByRole('button',{name:'Post penerimaan atomic',exact:true}).click()
  await wait(s=>[s.receipts.length,s.qc.ready],[1,4]);const received=take('received'),receiptLine=received.receipts[0][3]
  await nav(ui,p,'QC & Final SKU','Produksi');await ready(ui,p)
  await p.locator('nav.clq-tabs input').fill(f.po_number)
  const q=p.getByRole('combobox',{name:/^POTONGAN DENGAN GOOD LAUNDRY SIAP QC/})
  await ui.expect(q.locator(`option[value="${f.group}"]`)).toHaveCount(1);await q.selectOption(f.group)
  await p.getByLabel('LOKASI FG TUJUAN',{exact:true}).selectOption(f.location)
  await p.getByLabel('WAKTU FISIK QC',{exact:true}).fill(f.qc_local)
  await p.getByLabel('ALASAN / BUKTI HASIL QC',{exact:true}).fill('Sol exact four GOOD to own final SKU')
  await p.getByLabel('Good final size '+f.size_code,{exact:true}).fill('4')
  const row=p.locator('.clq-qc-editor article').filter({hasText:'Ukuran '+f.size_code})
  await row.getByLabel('Cari Final SKU size '+f.size_code,{exact:true}).fill(f.sku);await row.getByRole('button',{name:'Cari SKU',exact:true}).click()
  await row.getByLabel('Final SKU size '+f.size_code,{exact:true}).selectOption(f.product)
  await p.getByLabel(confirmQc,{exact:true}).check();await p.getByRole('button',{name:'Post QC + Final SKU atomic',exact:true}).click()
  await wait(s=>[s.qc.fg_stock,s.qc.qc_accounted,s.qc.ready],[4,4,0]);const final=take('final_sku')
  assert.equal(final.qc.inspections.length,1);assert.equal(final.qc.lots.length,1)
  assert.deepEqual(final.qc.items.map(x=>[x.product,x.good,x.bs,x.receipt_line]),[[f.product,4,0,receiptLine]])
  assert.equal(cents(final.qc.fg_balance)+cents(final.qc.wip_balance),13000n)
  // Enter an ordinary vendor invoice on this very receipt, edit its draft, post.
  let prices=await pricing(ui,p,f,'Invoice vendor'),box=prices.getByRole('region',{name:'Invoice vendor laundry',exact:true})
  await box.getByLabel('Nomor invoice vendor',{exact:true}).fill(f.invoice_number)
  await box.getByLabel('Tanggal invoice',{exact:true}).fill(f.day)
  await box.getByLabel('Total invoice',{exact:true}).fill('8')
  await box.getByRole('button',{name:'Tambah baris',exact:true}).click()
  await box.getByLabel('Sumber baris 1',{exact:true}).selectOption('r:'+receiptLine)
  await box.getByLabel('Qty baris 1',{exact:true}).fill('4');await box.getByLabel('Nominal baris 1',{exact:true}).fill('8')
  await box.getByRole('button',{name:'Simpan draf invoice',exact:true}).click()
  await wait(s=>s.invoices.map(x=>x[2]),['DRAFT']);const draft=take('draft')
  assert.equal(draft.ap,'0.00');samePhysical(final,draft)
  await box.getByRole('button',{name:'Ubah draf '+f.invoice_number,exact:true}).click()
  await box.getByLabel('Jatuh tempo',{exact:true}).fill(f.day)
  await box.getByRole('button',{name:'Simpan draf invoice',exact:true}).click()
  await ui.expect(prices.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
  await box.getByRole('button',{name:'Posting '+f.invoice_number,exact:true}).click()
  await wait(s=>s.ap,'8.00');const invoiced=take('invoiced');samePhysical(final,invoiced);assert.equal(invoiced.invoices[0][3],'8.00')
  // Missing one of the five sent: actual claim screen, same delivery/vendor.
  await nav(ui,p,'Barang BS & Rework','Produksi')
  await ui.expect(p.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
  await p.getByRole('button',{name:'Claim Laundry',exact:true}).click()
  const claimForm=p.getByRole('dialog',{name:'Buat claim Laundry',exact:true})
  await claimForm.getByLabel('JENIS',{exact:true}).selectOption('MISSING')
  await claimForm.getByLabel('SURAT KIRIM',{exact:true}).selectOption(delivery)
  await claimForm.getByLabel('NOMOR CLAIM',{exact:true}).fill(f.claim_number)
  await claimForm.getByLabel(/^QTY CLAIM/).fill('1')
  await claimForm.getByLabel('NILAI KOMPENSASI',{exact:true}).fill('2')
  await claimForm.getByLabel('WAKTU DIBUKA · WIB',{exact:true}).fill(f.qc_local)
  await claimForm.getByLabel('ALASAN / BUKTI · WAJIB',{exact:true}).fill('Sol one actual missing piece from own delivery')
  await claimForm.getByRole('button',{name:'Simpan claim',exact:true}).click()
  await wait(s=>s.claims.map(c=>c[2]),['OPEN'])
  const claimPanel=async()=>{
   await nav(ui,p,'Barang BS & Rework','Produksi')
   await ui.expect(p.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
   await p.locator('.cbsr-tabs').getByRole('button',{name:'Semua',exact:true}).click()
   const search=p.getByRole('form',{name:'Cari, browse, urutkan dan filter BS dan claim',exact:true})
   await search.getByLabel('Cari BS atau claim',{exact:true}).fill(f.claim_number)
   await search.getByRole('button',{name:'Cari kasus',exact:true}).click()
   await p.locator('.cbsr-list button').filter({hasText:f.claim_number}).click()
   const panel=p.locator('.cbsr-actions.claim')
   await panel.getByLabel('ALASAN / BUKTI · WAJIB',{exact:true}).fill('Sol lawful own claim lifecycle')
   return panel
  }
  let claim=await claimPanel()
  await claim.getByRole('button',{name:'Terima claim',exact:true}).click()
  await wait(s=>s.claims[0][2],'ACCEPTED')
  await ui.expect(claim.getByRole('button',{name:'Resolve',exact:true})).toBeEnabled()
  await claim.getByRole('button',{name:'Resolve',exact:true}).click()
  await wait(s=>[s.claims[0][2],s.ap],['SETTLED','6.00'])
  const resolved=take('claim_resolved');samePhysical(final,resolved)
  assert.equal(resolved.claims[0][3],'2.00');assert.equal(resolved.claims[0][4],f.today)
  prices=await pricing(ui,p,f,'Pembayaran vendor')
  box=prices.getByRole('region',{name:'Pembayaran vendor laundry',exact:true})
  await box.getByLabel('Tagihan dilunasi',{exact:true}).selectOption(invoiced.invoices[0][0])
  await box.getByLabel('Tanggal pelunasan',{exact:true}).fill(f.today)
  await box.getByLabel('Alasan pelunasan',{exact:true}).fill('Sol apply accepted claim to own invoice')
  await box.getByLabel('Kredit klaim dipakai',{exact:true}).selectOption(resolved.claims[0][0])
  await box.getByLabel('Nominal kredit klaim',{exact:true}).fill('2')
  await box.getByRole('button',{name:'Pakai kredit klaim',exact:true}).click()
  await wait(s=>s.payments.filter(x=>x[1]==='POSTED'&&x[3]==='CLAIM_CREDIT').length,1)
  const credited=take('claim_credit_applied');assert.equal(credited.ap,'6.00');assert.equal(credited.bank,'8.00');samePhysical(final,credited)
  // Two exact cash installments, then inverse both through the payment screen.
  await prices.getByRole('button',{name:'Pembayaran vendor',exact:true}).click()
  box=prices.getByRole('region',{name:'Pembayaran vendor laundry',exact:true})
  const pay=async amount=>{
   await box.getByLabel('Tagihan dilunasi',{exact:true}).selectOption(invoiced.invoices[0][0])
   await box.getByLabel('Tanggal pelunasan',{exact:true}).fill(f.today)
   await box.getByLabel('Alasan pelunasan',{exact:true}).fill('Sol exact ordinary cash installment')
   await box.getByLabel('Rekening kas pembayaran',{exact:true}).selectOption(f.bank)
   await box.getByLabel('Nominal bayar kas',{exact:true}).fill(amount)
   await box.getByRole('button',{name:'Bayar kas',exact:true}).click()
  }
  await pay('2.25');await wait(s=>[s.ap,s.bank],['3.75','5.75']);const partial=take('partial');samePhysical(invoiced,partial)
  await ui.expect(box.getByRole('status')).toContainText('Cocok')
  await pay('3.75');await wait(s=>[s.ap,s.bank],['0.00','2.00']);const paid=take('paid');samePhysical(invoiced,paid)
  await ui.expect(box.getByRole('table',{name:'Tagihan vendor',exact:true}).getByText('Lunas',{exact:true})).toBeVisible()
  await box.getByLabel('Alasan pembatalan',{exact:true}).fill('Sol inverse the lawful posted settlements')
  const payments=box.getByRole('table',{name:'Riwayat pelunasan vendor',exact:true})
  // Select by immutable payment amount, not unstable row order.
  for(const [amount,expected] of [['3,75',['3.75','5.75']],['2,25',['6.00','8.00']]]){
   const r=payments.locator('tbody tr').filter({hasText:amount});await ui.expect(r).toHaveCount(1)
   await r.getByRole('button',{name:/^Batalkan /}).click();await wait(s=>[s.ap,s.bank],expected)
   await ui.expect(prices.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
  }
  const undonePay=take('payments_reversed');samePhysical(invoiced,undonePay)
  assert.equal(undonePay.payments.filter(x=>x[1]==='REVERSED').length,2)
  const creditRow=payments.locator('tbody tr').filter({hasText:'Kredit klaim'})
  await ui.expect(creditRow).toHaveCount(1);await creditRow.getByRole('button',{name:/^Batalkan /}).click()
  await wait(s=>s.payments.filter(x=>x[1]==='POSTED').length,0)
  const released=take('credit_application_reversed');assert.equal(released.ap,'6.00');assert.equal(released.bank,'8.00')
  claim=await claimPanel();await claim.getByRole('button',{name:'Reverse resolution',exact:true}).click()
  await wait(s=>s.ap,'8.00');const claimReversed=take('claim_resolution_reversed');samePhysical(final,claimReversed)
  prices=await pricing(ui,p,f,'Invoice vendor')

  box=prices.getByRole('region',{name:'Invoice vendor laundry',exact:true})
  await box.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('Sol lawful invoice inverse after cash inverses')
  await box.getByRole('button',{name:'Batalkan invoice '+f.invoice_number,exact:true}).click()
  await wait(s=>s.ap,'0.00');const undoneInvoice=take('invoice_reversed');samePhysical(final,undoneInvoice)
  assert.equal(undoneInvoice.invoices[0][2],'REVERSED')
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  const writes=requests.filter(r=>r.url.startsWith('erp_cp7_save_sewing_')||r.url==='erp_save_laundry_qc_action_v1'||r.url==='erp_save_laundry_bd_action_v1'||r.url==='erp_save_bs_resolution_action_v1')
  assert.deepEqual(writes.map(r=>[r.url,r.body.p_action??r.body.p_payload?.action]),[
   ['erp_cp7_save_sewing_completion_v1','RECORD'],['erp_save_laundry_qc_action_v1','POST_DELIVERY'],['erp_save_laundry_qc_action_v1','POST_RECEIPT'],['erp_save_laundry_qc_action_v1','POST_FINAL_SKU'],
   ['erp_save_laundry_bd_action_v1','SAVE_INVOICE_DRAFT'],['erp_save_laundry_bd_action_v1','SAVE_INVOICE_DRAFT'],['erp_save_laundry_bd_action_v1','POST_INVOICE'],
   ['erp_save_bs_resolution_action_v1','SAVE_CLAIM'],['erp_save_bs_resolution_action_v1','SAVE_CLAIM'],['erp_save_bs_resolution_action_v1','RESOLVE_CLAIM'],['erp_save_laundry_bd_action_v1','APPLY_CLAIM_CREDIT'],
   ['erp_save_laundry_bd_action_v1','PAY_VENDOR_DOCUMENT'],['erp_save_laundry_bd_action_v1','PAY_VENDOR_DOCUMENT'],['erp_save_laundry_bd_action_v1','REVERSE_VENDOR_SETTLEMENT'],['erp_save_laundry_bd_action_v1','REVERSE_VENDOR_SETTLEMENT'],['erp_save_laundry_bd_action_v1','REVERSE_VENDOR_SETTLEMENT'],['erp_save_bs_resolution_action_v1','REVERSE_CLAIM_RESOLUTION'],['erp_save_laundry_bd_action_v1','REVERSE_INVOICE']])
  assert.equal(writes.filter(r=>r.url==='erp_save_laundry_qc_action_v1'&&r.body.p_action==='POST_DELIVERY').length,1)
  const signature={sewn:sewn.sewn,wage:'20.00',received:received.qc.received_good,fg:final.qc.fg_stock,total_fg_wip:'130.00',invoice:invoiced.invoices[0][3],partial_ap:partial.ap,partial_cash:partial.bank,paid_ap:paid.ap,paid_cash:paid.bank,final_ap:undoneInvoice.ap,final_cash:undoneInvoice.bank}
  writeFileSync(`cp6-proof/t3/${id}_OBSERVATIONS.json`,JSON.stringify({id,mode,signature,seen,requests},null,2))
  return{status:'PASS',case_id:id,mode,viewport:p.viewportSize(),signature,one_lineage:true,all_business_continuations_on_screen:true,fixture_only_before_sewing:true,claim_created_accepted_resolved_applied_and_reversed_on_screen:true,rewash_is_separate_component_case:true,physical_and_HPP_unchanged_by_settlement:true,posted_originals_and_two_inverses_retained:true,write_requests:writes.length}
 }catch(error){
  try{seen.failure_state=state()}catch(observation){seen.observation_error=String(observation)}
  writeFileSync(`cp6-proof/t3/${id}_FAILURE.json`,JSON.stringify({id,error:String(error),stack:error.stack,seen,requests,screen:await p.locator('main').innerText().catch(()=>''),alerts:await p.locator('[role="alert"],[role="status"]').allInnerTexts().catch(()=>[])},null,2))
  throw error
 }finally{await user.context.close()}
}
export function cases(ui,today){return [['SOL_R4_B5_B6_CLAIM_MOBILE',()=>journey(ui,today,'MOBILE')]]}
