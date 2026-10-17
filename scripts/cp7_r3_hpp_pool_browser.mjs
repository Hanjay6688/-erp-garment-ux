// R3-04 (Sol KNOWN-R2-POOL-UI, Astra ASTRA-C17-07; owner D16-1): the attendance HPP pool ("Pool HPP absensi") on the connected
// HPP & Rekalkulasi page, desktop 1440 and phone 390, real Auth and PostgREST on the committed copy. One journey on the screens:
// Pratinjau of one payroll period (the Native numbers equal the oracle's own figures from erp rows) -> "Buat draf pool" ->
// "Aktifkan" -> "Batalkan" -> the source corrected on Master Data -> Mandor (Mandor C gets his HPP policy from the day before)
// -> "Buat pool pengganti" (correction_of the cancelled pool, 20 pcs now) -> "Aktifkan". Every state is read from the Native
// rows (fixture r304_hpp_pool_state), never from the command's answer; no horizontal overflow at either width. A limited role
// (KEUANGAN: HPP rights, not Owner/Admin) opens the same page and sees no pool section, and its browser never calls the facade.
import assert from'node:assert/strict'
import{mkdirSync}from'node:fs'
const months=['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']
const dayText=d=>{const[y,m,x]=d.split('-').map(Number);return`${x} ${months[m-1]} ${y}`}
const rupiah=v=>{const[w,f='']=v.split('.'),t=f.replace(/0+$/,'');return'Rp'+w.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(t?','+t.padEnd(2,'0'):'')}
// The Native unit cost: numerator / pieces stored as numeric(28,12), rounded half up; computed here from the oracle's figures.
function unitCost(cost,pcs){
 const[w,f='']=cost.split('.'),cents=BigInt(w+f.padEnd(2,'0').slice(0,2)),n=BigInt(pcs),scaled=cents*10n**10n
 let q=scaled/n;if(2n*(scaled%n)>=n)q+=1n
 const s=q.toString().padStart(13,'0');return s.slice(0,-12)+'.'+s.slice(-12)
}
const esc=t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
async function hppPage(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached();const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• HPP & Rekalkulasi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'HPP per SKU',exact:true})).toBeVisible()
}
// The source correction on the screen that owns it: Master Data -> Mandor, an HPP policy (regular Mandor, attendance required)
// for Mandor C from the day before the period (cp7-src/master/master.sql through the Native policy writer).
async function mandorPolicy(ui,page,f){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Master Data'})).toBeAttached();const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click()
 const link=page.getByRole('button',{name:'• Mandor',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Master Data'}).click();await link.click()
 await ui.expect(page.getByRole('heading',{name:'Mandor & tarif upah',exact:true})).toBeVisible()
 const panel=page.locator('section.cmd-panel[aria-label="Mandor"]')
 await panel.getByLabel('Cari mandor',{exact:true}).fill(f.c_code);await panel.getByRole('button',{name:'Cari',exact:true}).click()
 await panel.getByRole('button',{name:`Pilih mandor ${f.c_code}`,exact:true}).click()
 await panel.locator(`section.cmd-view[aria-label="mandor ${f.c_code}"]`).getByRole('button',{name:'Ubah',exact:true}).click()
 const form=panel.locator('section.cmd-form[aria-label="Form mandor"]')
 await ui.expect(form.getByLabel('Wajib absensi',{exact:true})).toBeChecked();await ui.expect(form.getByLabel('Mandor Special',{exact:true})).not.toBeChecked()
 await form.getByLabel('Absensi/Special berlaku mulai (WIB)',{exact:true}).fill(f.correction_from)
 await form.getByLabel('Alasan simpan mandor',{exact:true}).fill('Mandor ini ikut pool absensi');await form.getByLabel('simpan mandor sudah diperiksa',{exact:true}).check()
 await form.getByRole('button',{name:'Simpan mandor',exact:true}).click()
 await ui.expect(panel.locator('.cmd-done')).toHaveText(`Tersimpan: perubahan mandor ${f.c_code} · ${f.c_code}.`)
}
async function act(ui,item,number,verb,reason){
 const title=verb==='aktifkan'?'Aktifkan':'Batalkan'
 await item.getByRole('button',{name:`${title} pool ${number}`,exact:true}).click()
 const go=item.getByRole('button',{name:`Simpan: ${verb} pool`,exact:true});await ui.expect(go).toBeDisabled()
 await item.getByLabel(`Alasan ${verb} pool ${number}`,{exact:true}).fill(reason);await ui.expect(go).toBeDisabled()
 await item.getByLabel(`${title} pool ${number} sudah diperiksa`,{exact:true}).check();await go.click()
}
async function journey(ui,today,mobile,h){
 const name=`CP17_BROWSER_R3_04_HPP_POOL_${mobile?'MOBILE':'DESKTOP'}`,f=h.fixture('r304_hpp_pool',{today,offset:mobile?13:11}),requests=[],seen={fixture:f}
 const state=()=>h.fixture('r304_hpp_pool_state',f)
 const user=await ui.login('OWNER',{label:'cp17-r3-04-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_hpp_pool_v1'))requests.push(r.postDataJSON())})
 let limited=null
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=seen.before=state()
  assert.deepEqual([before.pools.length,before.c_policies,before.cost,before.pcs],[0,0,f.cost,f.pcs]);assert.deepEqual([f.cost,f.pcs],['1000.00',10])
  await hppPage(ui,page);const panel=page.getByRole('region',{name:'Pool HPP absensi',exact:true});await ui.expect(panel).toBeVisible()
  await panel.getByLabel('Mulai periode pool',{exact:true}).fill(f.day);await panel.getByLabel('Akhir periode pool',{exact:true}).fill(f.day)
  await panel.getByRole('button',{name:'Pratinjau',exact:true}).click()
  let preview=panel.getByRole('region',{name:'Pratinjau pool',exact:true})
  await ui.expect(preview).toContainText(`Pratinjau periode ${dayText(f.day)}`)
  await ui.expect(preview.locator('.hpool-facts dd').nth(0)).toHaveText(rupiah(before.cost))
  await ui.expect(preview.locator('.hpool-facts dd').nth(1)).toHaveText(`${before.pcs} pcs`)
  await ui.expect(preview.locator('.hpool-facts dd').nth(2)).toHaveText(rupiah(unitCost(before.cost,before.pcs)))
  await ui.expect(preview).toContainText(`${f.po_a_number}: 10 pcs`);await ui.expect(preview).toContainText('Siap dibuat sebagai draf')
  await preview.getByRole('button',{name:'Buat draf pool',exact:true}).click()
  let form=preview.getByRole('region',{name:'Buat draf pool',exact:true}),create=form.getByRole('button',{name:'Buat draf pool',exact:true})
  await ui.expect(create).toBeDisabled();await form.getByLabel('Alasan buat draf pool',{exact:true}).fill('Gaji absensi mandor periode ini')
  await form.getByLabel('Draf pool sudah diperiksa',{exact:true}).check();assert.deepEqual(state().pools,[]);assert.equal(requests.length,0)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_PREVIEW.png`,fullPage:true})
  await create.click()
  await ui.expect(panel.getByText(new RegExp(`^Draf pool \\S+ dibuat untuk periode ${esc(dayText(f.day))}\\.`))).toBeVisible()
  let s=seen.created=state();assert.equal(s.pools.length,1);const first=s.pools[0]
  assert.deepEqual([first.status,first.numerator,first.denominator,first.correction_of,first.reason],['DRAFT',before.cost,before.pcs,null,'Gaji absensi mandor periode ini'])
  assert.equal(requests[0].p_action,'CREATE');assert.deepEqual(Object.keys(requests[0].p_payload).sort(),['correction_of_pool_id','period_end','period_start','reason','review_token'])
  assert.deepEqual([requests[0].p_payload.period_start,requests[0].p_payload.period_end,requests[0].p_payload.correction_of_pool_id],[f.day,f.day,null])
  const item=panel.getByRole('article',{name:'Pool '+first.number,exact:true});await ui.expect(item.locator('.hpool-status')).toHaveText('Draf')
  await act(ui,item,first.number,'aktifkan','Angka sudah dicek')
  await ui.expect(panel.getByText(`Pool ${first.number} aktif. Jurnal biaya absensi ke PO sudah dibuat dan HPP PO terkait dihitung ulang.`,{exact:true})).toBeVisible()
  s=seen.activated=state();assert.deepEqual([s.pools[0].status,s.pools[0].journal,s.pools[0].allocations],['ACTIVE','POSTED',{[f.po_a]:before.cost}])
  await ui.expect(item.locator('.hpool-status')).toHaveText('Aktif');await ui.expect(item).toContainText(`${f.po_a_number}: 10 pcs → ${rupiah(before.cost)}`)
  await act(ui,item,first.number,'batalkan','Mandor C belum punya aturan HPP')
  await ui.expect(panel.getByText(new RegExp(`^Pool ${esc(first.number)} dibatalkan\\. Jurnal pembalik sudah dibuat`))).toBeVisible()
  s=seen.cancelled=state();assert.deepEqual([s.pools[0].status,s.pools[0].journal,s.pools[0].reversal,s.pools[0].cancellation_reason],['CANCELLED','REVERSED','POSTED','Mandor C belum punya aturan HPP'])
  await ui.expect(item.locator('.hpool-status')).toHaveText('Dibatalkan')
  await ui.expect(item.getByRole('button',{name:'Buat pool pengganti untuk '+first.number,exact:true})).toBeVisible()
  await page.screenshot({path:`cp6-proof/t3/${name}_CANCELLED.png`,fullPage:true})
  // The source correction on its own screen, then back to the pool.
  await mandorPolicy(ui,page,f)
  const corrected=seen.corrected=state();assert.equal(corrected.c_policies,1);assert.deepEqual([corrected.cost,corrected.pcs],[before.cost,20])
  await hppPage(ui,page)
  await panel.getByRole('article',{name:'Pool '+first.number,exact:true}).getByRole('button',{name:'Buat pool pengganti untuk '+first.number,exact:true}).click()
  preview=panel.getByRole('region',{name:'Pratinjau pool',exact:true})
  await ui.expect(preview.locator('.hpool-facts dd').nth(1)).toHaveText(`${corrected.pcs} pcs`)
  await ui.expect(preview.locator('.hpool-facts dd').nth(2)).toHaveText(rupiah(unitCost(corrected.cost,corrected.pcs)))
  await ui.expect(preview).toContainText(`${f.po_c_number}: 10 pcs`)
  form=preview.getByRole('region',{name:'Buat draf pool',exact:true});create=form.getByRole('button',{name:'Buat draf pool pengganti',exact:true})
  await ui.expect(form).toContainText(`Pool ini akan mengganti pool ${first.number} yang sudah dibatalkan.`);await ui.expect(create).toBeDisabled()
  await form.getByLabel('Alasan buat draf pool',{exact:true}).fill('Pengganti sesudah aturan mandor C diisi');await form.getByLabel('Draf pool sudah diperiksa',{exact:true}).check()
  await create.click()
  await ui.expect(panel.getByText(new RegExp(`dibuat untuk periode ${esc(dayText(f.day))} sebagai pengganti pool yang dibatalkan\\.`))).toBeVisible()
  s=seen.replacement=state();assert.equal(s.pools.length,2);const second=s.pools[1]
  assert.deepEqual([second.status,second.correction_of,second.denominator],['DRAFT',first.id,corrected.pcs]);assert.equal(requests.at(-1).p_payload.correction_of_pool_id,first.id)
  const item2=panel.getByRole('article',{name:'Pool '+second.number,exact:true});await ui.expect(item2).toContainText(`Mengganti pool ${first.number} yang dibatalkan.`)
  await act(ui,item2,second.number,'aktifkan','Pengganti sudah dicek')
  await ui.expect(panel.getByText(`Pool ${second.number} aktif. Jurnal biaya absensi ke PO sudah dibuat dan HPP PO terkait dihitung ulang.`,{exact:true})).toBeVisible()
  const after=seen.after=state();const active=after.pools[1]
  assert.deepEqual([after.pools[0].status,active.status,active.journal],['CANCELLED','ACTIVE','POSTED'])
  assert.deepEqual(active.allocations,{[f.po_a]:'500.00',[f.po_c]:'500.00'})
  await ui.expect(panel.getByRole('article',{name:'Pool '+first.number,exact:true})).toContainText(`Diganti oleh pool ${second.number} (Aktif).`)
  assert.deepEqual(requests.map(r=>r.p_action),['CREATE','ACTIVATE','CANCEL','CREATE','ACTIVATE']);assert.equal(new Set(requests.map(r=>r.p_request)).size,5)
  await h.noSideScroll(ui,page);await page.screenshot({path:`cp6-proof/t3/${name}_REPLACEMENT.png`,fullPage:true})
  // A limited role: KEUANGAN holds the HPP rights but is not Owner/Admin; the page opens without the pool section.
  limited=await ui.login('KEUANGAN',{label:'cp17-r3-04-keuangan-'+(mobile?'mobile':'desktop'),mobile});const lp=limited.page,limitedRequests=[]
  lp.on('request',r=>{if(r.url().includes('/rpc/erp_cp7_'))limitedRequests.push(r.url().split('/rpc/')[1])})
  await hppPage(ui,lp);await ui.expect(lp.getByRole('region',{name:'Pool HPP absensi',exact:true})).toHaveCount(0)
  assert.ok(!limitedRequests.includes('erp_cp7_get_hpp_pools_v1')&&!limitedRequests.includes('erp_cp7_save_hpp_pool_v1'),limitedRequests)
  await h.noSideScroll(ui,lp);await lp.screenshot({path:`cp6-proof/t3/${name}_KEUANGAN.png`,fullPage:true})
  return{status:'PASS',finding:'R3-04',owner_decision:'D16-1',phone:mobile,period:f.day,first:{number:first.number,states:['DRAFT','ACTIVE','CANCELLED']},
   source_correction:'Master Data -> Mandor policy for Mandor C',replacement:{number:second.number,correction_of:first.id,pcs:corrected.pcs,allocations:active.allocations},
   requests:requests.length,distinct_request_ids:5,keuangan_sees_no_pool_section:true,no_side_scroll:true}
 }catch(error){try{seen.actual=state()}catch(e){seen.observation_error=String(e)};await h.failure(page,name,error,seen,requests);throw error}
 finally{await user.context.close();if(limited)await limited.context.close()}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R3_04_HPP_POOL_DESKTOP',()=>journey(ui,today,false,h)],['CP17_BROWSER_R3_04_HPP_POOL_MOBILE',()=>journey(ui,today,true,h)]]
}
