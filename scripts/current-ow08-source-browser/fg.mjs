// Existing QC blockers and inverse FG source, through actual app navigation.
import assert from 'node:assert/strict'
import {execFileSync}from 'node:child_process'
import {mkdirSync,writeFileSync}from 'node:fs'
import {dirname,resolve}from 'node:path'
import {fileURLToPath}from 'node:url'
import {readable}from '../current-vendor-money-browser/visual.mjs'
import {observeConsole,requireConsoleEvidence}from '../current-finance-combined-browser-qualification/console_evidence.mjs'
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const fixture=(op,p)=>JSON.parse(execFileSync('python',['-B',resolve(ROOT,'scripts/current-ow08-source-browser/fg_fixture.py'),op],{input:JSON.stringify(p),cwd:ROOT,encoding:'utf8',maxBuffer:16*1024*1024}).trim())
export const IDS=['OW08_FG_INVERSE_QC_BLOCKERS_DESKTOP','OW08_FG_INVERSE_QC_BLOCKERS_MOBILE']
async function navigate(ui,page,section,item,heading){
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• '+item,exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:section}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible()
}
async function journey(ui,today,mobile){
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'ow08-fg-source-'+mobile,mobile}),page=user.page,observed=observeConsole(page)
 const suffix=mobile?'MOBILE':'DESKTOP',shots=[],contrasts=[];let f,answer
 const shot=async(label,box)=>{mkdirSync('cp6-proof/t3',{recursive:true});await box.scrollIntoViewIfNeeded();for(const[scope,target]of[['PAGE',page],['FOCUS',box]]){const path=`cp6-proof/t3/OW08_FG_${suffix}_${label}_${scope}.png`;await target.screenshot({path,...(scope==='PAGE'?{fullPage:true}:{})});shots.push(path)}}
 try{
  f=fixture('prepare',{today});const before=fixture('state',{})
  await navigate(ui,page,'Produksi','QC & Final SKU','QC & Final SKU')
  await page.getByPlaceholder('Cari PO, Potongan, receipt, atau histori…',{exact:true}).fill(f.blocked.qc_number)
  await page.getByRole('button',{name:'Riwayat & koreksi',exact:true}).click()
  const qc=page.locator('[data-qc-inspection-id="'+f.blocked.qc_id+'"]');await ui.expect(qc).toBeVisible()
  await ui.expect(qc).toContainText(f.blocked.blocker);await ui.expect(qc).toContainText(f.blocked.sale);await ui.expect(qc).toContainText(f.blocked.adjustment)
  await ui.expect(qc).toContainText('Gudang › Stock Adjustment');await ui.expect(qc).toContainText('Penjualan › Penjualan & Invoice')
  await ui.expect(qc.getByRole('button',{name:'Batalkan finalisasi',exact:true})).toBeDisabled()
  contrasts.push({state:'QC_NAMED_BLOCKERS',rows:await readable(qc)});await shot('QC_NAMED_BLOCKERS',qc)
  assert.deepEqual(fixture('state',{}),before)
  await navigate(ui,page,'Gudang','Kartu Stok FG','Kartu stok barang jadi')
  await page.getByLabel('Cari barang jadi',{exact:true}).fill(f.inverse.lot_number)
  await page.getByRole('button',{name:'Cari stok',exact:true}).click()
  const position=page.locator('.cfg-position').filter({hasText:f.inverse.lot_number});await ui.expect(position).toHaveCount(1)
  await position.getByRole('button',{name:/^Lihat mutasi /}).click()
  const movement=page.locator('[data-fg-movement-id="'+f.inverse.movement_id+'"]');await ui.expect(movement).toBeVisible()
  await ui.expect(movement).toContainText('Pembalik transaksi sebelumnya')
  const sourceRPC=page.waitForResponse(r=>r.url().endsWith('/rest/v1/rpc/erp_cp7_resolve_transaction_source_v1')&&r.request().method()==='POST')
  await movement.getByRole('button',{name:'Buka transaksi asal',exact:true}).click()
  const response=await sourceRPC;assert.equal(response.status(),200,await response.text());answer=await response.json()
  assert.deepEqual(response.request().postDataJSON(),{p_source:{source_type:f.inverse.source_type,source_id:f.inverse.source_id}})
  assert.equal(answer.status,'AVAILABLE');assert.equal(answer.business_DML,false);assert.equal(answer.document.domain,'FG_ADJUSTMENT')
  assert.equal(answer.document.id,f.inverse.adjustment_id);assert.equal(answer.document.number,f.inverse.number);assert.equal(answer.document.status,'REVERSED')
  await ui.expect(page.getByRole('heading',{name:'Penyesuaian barang jadi',exact:true})).toBeVisible()
  const detail=page.locator('aside.cfga-detail');await ui.expect(detail.getByRole('heading',{name:f.inverse.number,exact:true})).toBeVisible()
  await ui.expect(detail).toContainText('Dibatalkan');await ui.expect(detail.getByRole('button',{name:'Batalkan koreksi FG',exact:true})).toHaveCount(0)
  assert.deepEqual(fixture('state',{}),before,'Source navigation must not alter any business row or sequence')
  contrasts.push({state:'FG_INVERSE_SOURCE',rows:await readable(detail)});await shot('FG_INVERSE_SOURCE',detail)
  const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));assert.ok(width.page<=width.viewport)
  return{status:'PASS',actual_QC_screen_names_sale_and_adjustment:true,blocked_QC_action_disabled:true,actual_inverse_FG_click_opens_same_reversed_adjustment:true,
   all_business_rows_and_sequences_unchanged:true,screen_creation_or_QC_inverse_claim:false,fixture_source:f.fixture_source,source_response:answer,
   visible_text_contrasts:contrasts,shots,width,console_evidence:requireConsoleEvidence(observed.errors,[]),production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/OW08_FG_${suffix}_FIRST_FAILURE.json`,JSON.stringify({error:String(error),fixture:f,source_response:answer,console:observed.errors},null,2));await page.screenshot({path:`cp6-proof/t3/OW08_FG_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{observed.stop();await user.context.close()}
}
export async function cases(ui,today){return IDS.map((id,i)=>[id,()=>journey(ui,today,Boolean(i))])}
