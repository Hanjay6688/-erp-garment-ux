import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// P08 physical fabric journey on the actual Native Auth/HTTP/browser host. The
// fixture only uses unchanged public commands; the browser only reads/captures.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_fabric_physical_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function journey(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'p08-physical-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',f=fixture('prepare',{today,actor:user.user.id})
 const panel=page.getByRole('region',{name:'Analisis ERP bersama',exact:true}),history=page.getByRole('region',{name:'Data permintaan ERP',exact:true}),materials=panel.getByRole('region',{name:'Kebutuhan bahan dari BOM ERP',exact:true}),shots=[]
 let first=null,second=null
 async function open(){await navigate(page);await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()}
 async function shot(name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});shots.push(name)}
 async function capture(){const pending=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_capture_analysis_v1'));await panel.getByRole('button',{name:'Ambil analisis ERP terbaru',exact:true}).click();const response=await pending;assert.equal(response.status(),200);return response.json()}
 const keys=['installed_proven','unused_allocated_proven','additional_external']
 function row(e,unused,external){const m=e.analysis.material_needs.find(m=>m.target_key===f.target&&m.material_key===`FABRIC_MATERIAL:${f.material}`);assert.ok(m)
  assert.equal(m.gross.value,f.expected.gross);assert.deepEqual(keys.map(k=>[m[k].state,Number(m[k].value)]),[['ASSUMED',0],['ASSUMED',Number(unused)],['ASSUMED',Number(external)]])
  assert.ok(m.unused_allocated_proven.refs.some(r=>r.kind==='CP7_FABRIC_FREE_STOCK'));assert.ok(m.additional_external.refs.some(r=>r.kind==='CP7_FABRIC_OPEN_COMMITMENTS'))
  assert.equal(e.analysis.recommendations.find(r=>r.target.key===f.target).feasible_new.state,'UNKNOWN');return m}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await open();const before=fixture('state',{today,actor:user.user.id})
  first=await capture();const m=row(first,f.expected.unused,f.expected.external)
  assert.deepEqual(fixture('state',{today,actor:user.user.id}).business,before.business)
  const label=first.product_labels.find(l=>l.target_key===f.target).sku;await panel.getByLabel('Cari hasil analisis bersama',{exact:true}).fill(label)
  for(const text of['Kebutuhan kain','Terpasang terbukti: 0','Sisa layak yang sudah dialokasikan: 10','Tambahan dari luar: 126','PO terbuka','bukan reservasi stok','PO di luar ERP tidak terlihat','Kemampuan produksi global belum terbukti'])await ui.expect(materials).toContainText(text)
  await shot(`P08_PHYSICAL_ALLOCATED10_EXTERNAL126_${suffix}.png`)
  const count=fixture('state',{today,actor:user.user.id}).analyses;await panel.getByRole('tab',{name:'Laporan',exact:true}).click();const report=await panel.getByLabel('Isi laporan ERP',{exact:true}).innerText()
  for(const text of['CP7_FABRIC_FREE_STOCK','CP7_FABRIC_OPEN_COMMITMENTS','tambahan eksternal 126'])assert.ok(report.includes(text),text)
  await panel.getByRole('tab',{name:'Tanya AI',exact:true}).click();const prompt=await panel.getByLabel('Pertanyaan dan sumber ERP',{exact:true}).innerText()
  for(const text of['CP7_FABRIC_FREE_STOCK','CP7_FABRIC_OPEN_COMMITMENTS'])assert.ok(prompt.includes(text),text)
  assert.equal(fixture('state',{today,actor:user.user.id}).analyses,count)
  // Actual second receipt of the same fabric: the immutable Original is stale,
  // never silently refreshed; a fresh capture counts the new roll once.
  fixture('receive',{today,actor:user.user.id,material:f.material,roll:f.roll,location:f.location})
  const checked=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_read_analysis_v1'));await panel.getByRole('tab',{name:'Produksi',exact:true}).click();await panel.getByRole('button',{name:'Periksa sumber analisis',exact:true}).click()
  const read=await checked;assert.equal(read.status(),200);const stale=await read.json();assert.equal(stale.source_state,'ARCHIVED_STALE');assert.deepEqual(stale.analysis,first.analysis)
  await ui.expect(panel).toContainText('Arsip lama: sumber berubah. Ambil analisis baru.');await shot(`P08_PHYSICAL_RECEIPT_STALE_${suffix}.png`)
  second=await capture();row(second,f.after_receipt.unused,f.after_receipt.external)
  await panel.getByLabel('Cari hasil analisis bersama',{exact:true}).fill(label);await ui.expect(materials).toContainText('Sisa layak yang sudah dialokasikan: 30');await ui.expect(materials).toContainText('Tambahan dari luar: 106')
  await shot(`P08_PHYSICAL_ALLOCATED30_EXTERNAL106_${suffix}.png`)
  return{status:'PASS',actual_Auth_HTTP_bound_gap93_installed0_unique_free_stock10_on_time_open_commitment50_external126:true,shared_production_report_AI_same_physical_refs:true,reads_do_not_change_Native_business:true,
   actual_second_receipt_archives_immutable_original:true,fresh_capture_allocated30_external106:true,global_feasibility_UNKNOWN:true,screenshots:shots,complete_material_row:m,complete_first:first,complete_second:second}
 }catch(e){writeFileSync(`cp6-proof/t3/P08_PHYSICAL_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel.innerText().catch(()=>''),first,second},null,2));await page.screenshot({path:`cp6-proof/t3/P08_PHYSICAL_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{today,actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P08_PHYSICAL_BROWSER_DESKTOP',()=>journey(ui,today,false)],['P08_PHYSICAL_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
