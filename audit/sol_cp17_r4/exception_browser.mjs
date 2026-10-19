// Two distinct missing exception continuations, declared before execution.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {writeFileSync,mkdirSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {cases as claimCases} from './claim_browser.mjs'
const helper=fileURLToPath(new URL('./exception_fixture.py',import.meta.url))
const fixture=(op,p)=>JSON.parse(execFileSync('python',[helper,op],{input:JSON.stringify(p),encoding:'utf8',maxBuffer:16*1024*1024}))
async function rewash(ui,today){
 const id='SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP',f=fixture('rewash_prepare',{today}),seen={fixture:f},requests=[]
 const owner=await ui.login('OWNER',{label:'sol-r4-free-rewash'}),p=owner.page,state=()=>fixture('rewash_observe',f)
 const snapshot=name=>seen[name]=state()
 p.on('request',r=>{if(r.url().endsWith('/rpc/erp_save_bs_resolution_action_v1'))requests.push(r.postDataJSON())})
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});const before=snapshot('before');assert.deepEqual(before.orders,[])
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Barang BS & Rework',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click();await link.click()
  await ui.expect(p.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled()
  await p.locator('.cbsr-tabs').getByRole('button',{name:'Semua',exact:true}).click()
  const search=p.getByRole('form',{name:'Cari, browse, urutkan dan filter BS dan claim',exact:true})
  await search.getByLabel('Cari BS atau claim',{exact:true}).fill(f.bs_number);await search.getByRole('button',{name:'Cari kasus',exact:true}).click()
  await p.locator('.cbsr-list button').filter({hasText:f.bs_number}).click()
  await p.locator('.cbsr-route-tabs').getByRole('button',{name:'Rewash',exact:true}).click()
  const form=p.locator('.cbsr-route-form')
  await form.getByLabel('NOMOR ORDER · WAJIB',{exact:true}).fill(f.number)
  await form.getByLabel(/^VENDOR REWASH/).selectOption(f.vendor)
  await form.getByLabel('QTY DIKIRIM',{exact:true}).fill('2')
  await form.getByLabel('WAKTU FISIK · WIB',{exact:true}).fill(f.send_local)
  await form.getByLabel(/^GUDANG FG BILA GOOD/).selectOption(f.location)
  await form.getByLabel('CATATAN / ALASAN',{exact:true}).fill('Sol free rewash of the same source product')
  for(const b of await form.locator('.cbsr-accessories input[type=checkbox]').all())await b.uncheck()
  // Hasil GOOD menjadi SKU lain is left off: D06 free same-product rewash.
  await ui.expect(form.getByRole('checkbox',{name:'Hasil GOOD menjadi SKU lain',exact:true})).not.toBeChecked()
  await form.getByRole('button',{name:'Buat order rewash',exact:true}).click()
  const completion=p.locator('.cbsr-completion-form').filter({hasText:f.number})
  await ui.expect(completion).toBeVisible()
  await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill('1')
  await completion.getByLabel('BS KUMULATIF',{exact:true}).fill('0')
  await completion.getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('Sol one physically returned, no completed FG yet')
  await completion.getByRole('button',{name:'Simpan partial',exact:true}).click()
  await ui.expect.poll(()=>state().orders[0]?.good).toBe(1)
  const partial=snapshot('partial');assert.equal(partial.orders[0].stock,0);assert.equal(partial.orders[0].lot,null)
  await completion.getByLabel('GOOD KUMULATIF',{exact:true}).fill('2')
  await completion.getByLabel('WAKTU SELESAI · WIB',{exact:true}).fill(f.complete_local)
  await completion.getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('Sol final two GOOD, same SKU, no vendor fee')
  await completion.getByRole('button',{name:'Post hasil & recovery',exact:true}).click()
  await ui.expect.poll(()=>state().orders[0]?.stock).toBe(2)
  const completed=snapshot('completed'),order=completed.orders[0]
  assert.deepEqual([order.status,order.qty,order.good,order.bs,order.stock,order.product,order.work_components,order.journals],['COMPLETED',2,2,0,2,f.product,0,0])
  assert.deepEqual([completed.vendor_ap,completed.vendor_lines],[before.vendor_ap,before.vendor_lines])
  const done=p.locator('.cbsr-rework-complete')
  await done.getByLabel('Alasan pembatalan hasil rework',{exact:true}).fill('Sol lawful inverse of free same-product recovery')
  await done.getByRole('button',{name:'Periksa pembatalan hasil',exact:true}).click()
  const review=done.getByRole('region',{name:'Pemeriksaan pembatalan hasil rework',exact:true})
  await ui.expect(review).toContainText('Batalkan hasil 2 Good dan 0 BS')
  await review.getByRole('button',{name:'Sahkan pembatalan hasil',exact:true}).click()
  await ui.expect.poll(()=>state().orders[0]?.stock).toBe(0)
  const inverse=snapshot('inverse');assert.deepEqual([inverse.vendor_ap,inverse.vendor_lines],[before.vendor_ap,before.vendor_lines])
  assert.deepEqual(requests.map(r=>r.p_action),['SAVE_REWORK','SAVE_REWORK','COMPLETE_REWORK','REVERSE_REWORK_COMPLETION'])
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  writeFileSync(`cp6-proof/t3/${id}_OBSERVATIONS.json`,JSON.stringify({id,seen,requests},null,2))
  return{status:'PASS',case_id:id,fixture_origin:'WRITER_SG03_NATIVE_BEFORE_REWASH_ORDER',oracle_origin:'SOL_D06_LITERAL_PHYSICAL_AND_MONEY_CONTROL',signature:{sent:2,partial_good:1,partial_fg:0,final_good:2,final_fg:2,inverse_fg:0,vendor_ap_changed:false,vendor_lines_changed:false,new_wage_components:0,new_rework_journals:0,same_product:true},all_rewash_continuations_on_screen:true,earlier_sewing_laundry_QC_are_explicit_Native_fixture:true,requests:4}
 }catch(error){
  try{seen.failure=state()}catch(observation){seen.observation_error=String(observation)}
  writeFileSync(`cp6-proof/t3/${id}_FAILURE.json`,JSON.stringify({id,error:String(error),stack:error.stack,seen,requests,screen:await p.locator('main').innerText().catch(()=>'')},null,2));throw error
 }finally{await owner.context.close()}
}
export function cases(ui,today){return [...claimCases(ui,today),['SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP',()=>rewash(ui,today)]]}
