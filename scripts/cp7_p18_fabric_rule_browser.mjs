import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
// P18 fabric rule on the actual Native Auth/HTTP/browser host. The fixture is
// the P08 bound journey (external 126 with an on-time PO); the browser saves one
// explicit fixture policy and records one condition check. No delivery.
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_fabric_physical_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function journey(ui,today,mobile){
 const user=await ui.login('OWNER',{label:'p18-fabric-rule-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',f=fixture('prepare',{today,actor:user.user.id})
 const panel=page.getByRole('region',{name:'Analisis ERP bersama',exact:true}),history=page.getByRole('region',{name:'Data permintaan ERP',exact:true}),policies=panel.getByRole('region',{name:'Pengaturan aturan pengingat',exact:true}),conditions=panel.getByRole('region',{name:'Kondisi masalah dan pratinjau lokal',exact:true}),shots=[]
 let captured=null,source=null,observed=null
 async function shot(name){await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});shots.push(name)}
 async function click(region,label,name){const response=page.waitForResponse(r=>r.url().endsWith('/rpc/'+name));await region.getByRole('button',{name:label,exact:true}).click();const r=await response;assert.equal(r.status(),200,name);return r.json()}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await navigate(page);await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click();await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()
  const before=fixture('state',{actor:user.user.id})
  captured=await click(panel,'Ambil analisis ERP terbaru','erp_cp7_capture_analysis_v1')
  const need=captured.analysis.material_needs.find(m=>m.target_key===f.target&&m.material_key===`FABRIC_MATERIAL:${f.material}`);assert.ok(need);assert.equal(need.additional_external.state,'ASSUMED');assert.equal(need.additional_external.value,f.expected.external)
  const unit=need.additional_external.unit,key=`FABRIC_NEED:${f.target}:FABRIC_MATERIAL:${f.material}`
  await panel.getByRole('tab',{name:'Pengingat',exact:true}).click()
  await click(policies,'Muat pengaturan pengingat','erp_cp7_get_reminder_policy_v1');await policies.getByLabel('Aturan yang diperiksa',{exact:true}).selectOption('FABRIC_NEED')
  await policies.getByLabel('Status aturan',{exact:true}).selectOption('true');await policies.getByLabel('Batas pengingat',{exact:true}).fill('100');await policies.getByLabel('Satuan dasar kain',{exact:true}).fill(unit)
  await policies.getByLabel('Jeda pengingat dalam menit',{exact:true}).fill('0');await policies.getByLabel('Waktu tenang',{exact:true}).selectOption('false')
  await policies.getByLabel('Alasan perubahan pengingat',{exact:true}).fill('Nilai uji fixture P18 kain, bukan keputusan pemilik '+suffix);await policies.getByLabel('Pengaturan pengingat sudah ditinjau',{exact:true}).check()
  const saved=await click(policies,'Simpan versi pengaturan pengingat','erp_cp7_save_reminder_policy_v1');assert.equal(saved.request_result.status,'COMMITTED')
  source=await click(conditions,'Periksa kondisi masalah ERP','erp_cp7_get_rule_conditions_v1')
  const row=source.rows.find(r=>r.key===key);assert.ok(row);assert.equal(row.rule_id,'FABRIC_NEED');assert.equal(row.state,'ACTIVE');assert.deepEqual(row.value,need.additional_external);assert.equal(row.eligibility,'LOCAL_PREVIEW_ELIGIBLE');assert.equal(row.business_resolved,false)
  const article=conditions.getByRole('article',{name:'Kondisi '+key,exact:true})
  for(let i=0;i<200&&!await article.count();i++)await conditions.getByRole('button',{name:'Kondisi berikutnya',exact:true}).click()
  for(const text of['Kebutuhan kain','Masih perlu ditangani',`${f.expected.external} ${unit} · asumsi`,'Perlu tambahan kain dari luar menurut asumsi resep; ini bukan perintah beli.','Bisa ditinjau secara lokal'])await ui.expect(article).toContainText(text)
  await shot(`P18_FABRIC_RULE_ACTIVE_${suffix}.png`)
  observed=await click(conditions,'Catat pemeriksaan kondisi ERP','erp_cp7_evaluate_rule_episodes_v1')
  const o=observed.result.rows.find(r=>r.condition.key===key);assert.ok(o);assert.equal(o.transition,'OPENED');assert.equal(o.episode.state,'ACTIVE');assert.equal(o.episode.freshness,'ASSUMED')
  await ui.expect(conditions.getByRole('region',{name:'Catatan pemeriksaan kondisi',exact:true})).toContainText('masih terbuka')
  assert.deepEqual(fixture('state',{actor:user.user.id}).business,before.business)
  await shot(`P18_FABRIC_RULE_EPISODE_${suffix}.png`)
  return{status:'PASS',actual_Auth_HTTP_FABRIC_NEED_ACTIVE_external126_ASSUMED_copied_exactly:true,explicit_fixture_policy100_same_unit_LOCAL_PREVIEW_ELIGIBLE:true,episode_opened_ACTIVE_ASSUMED_not_resolved:true,reads_and_reminder_metadata_leave_Native_business_unchanged:true,screenshots:shots,complete_condition:row,complete_observation:o}
 }catch(e){writeFileSync(`cp6-proof/t3/P18_FABRIC_RULE_${suffix}_FAILURE.json`,JSON.stringify({error:String(e),text:await panel.innerText().catch(()=>''),captured,source,observed},null,2));await page.screenshot({path:`cp6-proof/t3/P18_FABRIC_RULE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw e}
 finally{fixture('restore',{today,actor:user.user.id});await user.context.close()}
}
export function cases(ui,today){return[['P18_FABRIC_RULE_BROWSER_DESKTOP',()=>journey(ui,today,false)],['P18_FABRIC_RULE_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
