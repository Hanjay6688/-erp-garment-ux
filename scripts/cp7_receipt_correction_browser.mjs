import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_receipt_correction_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim().split('\n').at(-1))
async function open(ui,p,title='Pembelian & Penerimaan',heading='Pembelian & penerimaan'){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+title,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:heading,exact:true})).toBeVisible()
}
async function flow(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'receipt-fix-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,suffix=mobile?'MOBILE':'DESKTOP'
 let lost=false,first=null,replay=null
 const select=async page=>{await page.getByLabel('Cari penerimaan',{exact:true}).fill(f.purchase_number);await page.getByRole('button',{name:'Cari penerimaan',exact:true}).click();const row=page.locator('.cproc-receipt').filter({hasText:f.purchase_number});await ui.expect(row.first()).toBeVisible();await row.first().click();await ui.expect(page.locator('.cproc-detail')).toContainText(f.purchase_number)}
 try{
  const before=fixture('read',f);assert.deepEqual(before.raw.map(Number),[40,400]);assert.equal(before.workspace.can_correct,true)
  await open(ui,p);await select(p)
  const panel=p.getByRole('region',{name:'Benerin penerimaan',exact:true});await panel.scrollIntoViewIfNeeded()
  await panel.getByRole('button',{name:'Buka pembetulan',exact:true}).click();await ui.expect(panel).toContainText(f.purchase_number)
  await panel.getByRole('button',{name:'Benerin penerimaan',exact:true}).click()
  const qty=panel.getByLabel('Jumlah roll benar 1.1',{exact:true});await ui.expect(qty).toHaveValue('100');await ui.expect(panel).toContainText('sudah terpakai 60')
  await qty.fill('50');await panel.getByLabel('Alasan pembetulan penerimaan',{exact:true}).fill('Surat jalan asli 80 yard, salah ketik 100')
  await ui.expect(panel.getByRole('alert')).toContainText('sudah terpakai 60.000000');await qty.fill('80')
  const save=panel.getByRole('button',{name:'Simpan pembetulan',exact:true});await ui.expect(save).toBeDisabled()
  await panel.getByLabel('Pembetulan penerimaan sudah diperiksa',{exact:true}).check();await ui.expect(save).toBeEnabled()
  const route='**/rest/v1/rpc/erp_cp7_correct_receipt_v1'
  if(mobile)await p.route(route,async r=>{const body=r.request().postDataJSON();if(!lost){first=body;const response=await r.fetch();if(response.status()!==200){await r.fulfill({response});return}lost=true;await r.abort('failed')}else{replay=body;await r.continue()}})
  const committed=mobile?null:p.waitForResponse(r=>r.url().includes('/rest/v1/rpc/erp_cp7_correct_receipt_v1')&&r.request().method()==='POST',{timeout:30000})
  await save.click()
  if(committed){const response=await committed;assert.equal(response.status(),200);const body=await response.json();assert.equal(body.kind,'COMMITTED_OUTCOME');assert.equal(body.previous_purchase_id,f.purchase);assert.equal(body.revision,'1')}
  if(mobile){
   await ui.expect.poll(()=>lost,{timeout:30000}).toBe(true)
   const pending=await p.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.production.RECEIPT_CORRECTION.pending-mutation.v1:')).map(([,v])=>JSON.parse(v)))
   assert.equal(pending.length,1);assert.equal(pending[0].action,'CORRECT');assert.equal(pending[0].id,first.p_request);assert.deepEqual(pending[0].payload.document,first.p_payload)
   await p.reload();await open(ui,p);await select(p);const again=p.getByRole('region',{name:'Benerin penerimaan',exact:true})
   await again.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(again.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
   assert.deepEqual(replay,first)
  }
  await ui.expect.poll(()=>fixture('read',f).workspace.history.length,{timeout:30000}).toBe(1)
  const after=fixture('read',f);assert.deepEqual(after.raw.map(Number),[20,200]);assert.deepEqual(after.hpp.slice(0,2).map(Number),[900,15]);assert.deepEqual(after.facts,f.facts);assert.equal(after.requests,1)
  const first_row=after.card.at(-1);assert.equal(first_row.qty_signed,'80.000000');assert.equal(first_row.original_qty_signed,'100.000000');assert.equal(after.card[0].running_qty,'20.000000')
  const detail=p.locator('.cproc-detail');await ui.expect(detail).toContainText('80 ')
  mkdirSync('cp6-proof/t3',{recursive:true});await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await p.screenshot({path:`cp6-proof/t3/RECEIPT_CORRECTION_${suffix}.png`,fullPage:true})
  await open(ui,p,'Bahan & Roll','Bahan & roll');const m=p.locator('.cmat')
  await m.getByLabel('Cari stok bahan',{exact:true}).fill(f.roll_number);await m.getByRole('button',{name:'Cari stok',exact:true}).click()
  await m.getByRole('button',{name:'Mutasi '+f.roll_number,exact:true}).first().click()
  const card=m.locator('.cmat-ledger');await ui.expect(card).toContainText('Dibetulkan · jumlah asli');await ui.expect(card).toContainText('jumlah yang berlaku 80')
  let renamed=null
  if(!mobile){
   // Name typo on the same material: only the name changes (no new material, no stock effect).
   const name=card.getByRole('region',{name:'Benerin nama bahan',exact:true});await name.getByRole('button',{name:'Salah ketik nama?',exact:true}).click()
   const input=name.getByLabel('Nama bahan yang benar',{exact:true});await ui.expect(input).toHaveValue(f.material_name)
   renamed=f.material_name+' Combed';await input.fill(renamed);await name.getByLabel('Alasan pembetulan nama bahan',{exact:true}).fill('Salah ketik nama di master bahan')
   const keep=name.getByRole('button',{name:'Simpan nama',exact:true});await ui.expect(keep).toBeDisabled();await name.getByLabel('Nama bahan sudah diperiksa',{exact:true}).check();await keep.click()
   await ui.expect.poll(()=>fixture('read',f).material_name,{timeout:30000}).toBe(renamed)
   const named=fixture('read',f);assert.equal(named.name_requests,1);assert.deepEqual(named.raw.map(Number),[20,200]);assert.deepEqual(named.card,after.card)
   await ui.expect(m).toContainText(renamed)
  }
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await p.screenshot({path:`cp6-proof/t3/RECEIPT_CORRECTED_CARD_${suffix}.png`,fullPage:true})
  return{status:'PASS',mobile,real_UI_Auth_HTTP_native_receipt_correction:true,used_60_guard_visible_and_refused_50:true,received_100_corrected_80:true,remaining_20_value_200_hpp_900:true,original_receipt_immutable:true,one_request_one_effect:true,lost_commit_reply_identical_UUID_reconcile:mobile?true:null,effective_card_first_row_80_original_100:true,
   effective_card_visible_in_materials_page:true,material_name_typo_fixed_same_material_no_stock_effect:mobile?null:true,screenshots:[`RECEIPT_CORRECTION_${suffix}.png`,`RECEIPT_CORRECTED_CARD_${suffix}.png`]}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});let observed;try{observed=fixture('read',f)}catch(e){observed={error:String(e)}}writeFileSync(`cp6-proof/t3/RECEIPT_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await p.locator('body').innerText().catch(()=>''),observed},null,2));await p.screenshot({path:`cp6-proof/t3/RECEIPT_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await user.context.close()}
}
export async function cases(ui,today){const tests=[['RF_BROWSER_DESKTOP',()=>flow(ui,today,false)],['RF_BROWSER_MOBILE',()=>flow(ui,today,true)]];const manifest=JSON.parse(readFileSync(new URL('./cp7_receipt_correction_manifest.json',import.meta.url),'utf8'));assert.deepEqual(tests.map(([name])=>name),manifest.groups.browser);return tests}
