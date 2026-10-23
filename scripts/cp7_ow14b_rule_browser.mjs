import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {cases as retainedCases} from './cp7_wa_forward_browser.mjs'

const fixture=(operation,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow14b_rule_browser_fixture.py',operation],
  {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const saveName='erp_cp7_save_material_reorder_v1'
async function navigate(ui,page,f){
  const main=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first()
  await main.waitFor({state:'attached'})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible())await menu.click()
  const link=page.getByRole('button',{name:'• Bahan & Roll',exact:true})
  if(!await link.isVisible())await main.click()
  await link.click()
  const panel=page.getByRole('region',{name:'Titik pesan ulang kain',exact:true})
  await ui.expect(panel).toBeVisible()
  await panel.getByLabel('Cari kain untuk titik pesan ulang',{exact:true}).fill(f.sku)
  await panel.getByRole('button',{name:'Cari',exact:true}).click()
}
const intents=page=>page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('cp7:material-reorder:pending:v1:')).map(k=>{
  try{return JSON.parse(localStorage.getItem(k))}catch{return {corrupt:true}}
}))
async function journey(ui,today,mobile){
  const f=fixture('prepare',{today})
  const user=await ui.login('OWNER',{label:'ow14b-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const page=user.page,actor=user.user.id,suffix=mobile?'MOBILE':'DESKTOP',sent=[],losses=[],shots=[]
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  const panel=page.getByRole('region',{name:'Titik pesan ulang kain',exact:true})
  const row=panel.getByRole('article',{name:`Titik pesan ulang ${f.name} (SKU ${f.sku})`,exact:true})
  const recovery=panel.getByRole('button',{name:`Ulangi simpan bahan yang sama: ${f.name}`,exact:true})
  const state=(with_source=false)=>fixture('state',{fixture:f,actor,with_source})
  const shot=async tag=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/OW14B_${suffix}_${tag}.png`;await page.screenshot({path,fullPage:true});shots.push(path);return path}
  let loseNext=true
  try{
    await navigate(ui,page,f)
    const before=state()
    await panel.getByRole('button',{name:'Hitung sekarang',exact:true}).click()
    await ui.expect(row).toBeVisible()
    await ui.expect(row.locator('[data-cmr="legacy"]')).toContainText('500 YD')
    await row.getByRole('button',{name:'Atur lama kirim',exact:true}).click()
    await row.getByLabel('Lama kirim (hari)',{exact:true}).fill('6')
    await row.getByLabel('Aturan kain yang akan dipakai',{exact:true}).selectOption('FORMULA')
    await row.getByLabel('Alasan perubahan bahan',{exact:true}).fill('OW14b reviewed formula')
    await page.route('**/rest/v1/rpc/'+saveName,async route=>{
      const args=route.request().postDataJSON();sent.push(args)
      const stored=await intents(page)
      assert.ok(stored.some(x=>x.id===args.p_request&&JSON.stringify(x.payload)===JSON.stringify(args.p_payload)), 'INTENT_DURABLE_BEFORE_NETWORK')
      if(loseNext){
        loseNext=false
        const response=await route.fetch();assert.equal(response.status(),200)
        losses.push({args,status:response.status(),body:await response.json()})
        await route.abort('failed')
      }else await route.continue()
    })
    await row.getByRole('button',{name:'Simpan',exact:true}).click()
    await ui.expect(recovery).toBeEnabled()
    assert.equal(state().revisions,1);assert.equal(sent[0].p_payload.fabric_rule,'FORMULA')
    await shot('FORMULA_REPLY_LOST')
    await page.reload();await navigate(ui,page,f)
    await ui.expect(row).toBeVisible();await ui.expect(recovery).toBeEnabled()
    await row.getByRole('button',{name:'Atur lama kirim',exact:true}).click()
    await row.getByLabel('Aturan kain yang akan dipakai',{exact:true}).selectOption('LEGACY_MINIMUM')
    await row.getByLabel('Alasan perubahan bahan',{exact:true}).fill('OW14b later choice not sent')
    await row.getByRole('button',{name:'Simpan',exact:true}).click()
    await ui.expect(row).toContainText('hasilnya belum jelas');assert.equal(sent.length,1)
    const response=page.waitForResponse(r=>r.url().endsWith('/rpc/'+saveName))
    await recovery.click();assert.equal((await response).status(),200)
    await ui.expect(recovery).toHaveCount(0)
    assert.deepEqual(sent[1],sent[0]);assert.equal(state().revisions,1)
    await ui.expect(row.getByLabel('Alasan perubahan bahan',{exact:true})).toHaveValue('OW14b later choice not sent')
    await ui.expect(row.getByLabel('Aturan kain yang akan dipakai',{exact:true})).toHaveValue('LEGACY_MINIMUM')
    const formula=state(true)
    assert.equal(formula.settings.fabric_rule,'FORMULA');assert.equal(Number(formula.evaluation.point),Number(f.point));assert.equal(formula.alerts.length,0)
    assert.equal(formula.native_hash,before.native_hash)
    await shot('ONE_FORMULA_DIRTY_CHOICE_RETAINED')
    loseNext=true
    await row.getByRole('button',{name:'Simpan',exact:true}).click()
    await ui.expect(recovery).toBeEnabled()
    const chosen=state(true)
    assert.equal(chosen.revisions,2);assert.equal(chosen.settings.fabric_rule,'LEGACY_MINIMUM');assert.equal(Number(chosen.evaluation.point),500)
    assert.equal(chosen.alerts.length,1);assert.equal(Number(chosen.alerts[0].detail.reorder_point_qty),500)
    assert.equal(chosen.native_hash,before.native_hash);assert.notEqual(sent[2].p_request,sent[0].p_request)
    fixture('deactivate',{actor})
    const denied=page.waitForResponse(r=>r.url().endsWith('/rpc/'+saveName)&&r.status()===403)
    await recovery.click();await denied
    await ui.expect(panel.locator('.cfr-row')).toHaveCount(0)
    assert.ok((await intents(page)).some(x=>x.id===sent[2].p_request),'403_PRESERVES_COMMITTED_UNKNOWN_INTENT')
    if(await panel.isVisible())await ui.expect(panel).toContainText('sampai akses akun dipulihkan')
    await shot('CURRENT_ACCESS_DENIED_FACTS_RETIRED')
    fixture('restore',{actor})
    await page.reload();await navigate(ui,page,f);await ui.expect(recovery).toBeEnabled()
    const restored=page.waitForResponse(r=>r.url().endsWith('/rpc/'+saveName))
    await recovery.click();assert.equal((await restored).status(),200)
    await ui.expect(recovery).toHaveCount(0)
    assert.equal(sent.length,5);assert.deepEqual(sent[3],sent[2]);assert.deepEqual(sent[4],sent[2])
    assert.equal(state().revisions,2)
    await ui.expect(row).toContainText('Minimum lama yang dipilih')
    assert.equal(await row.locator('[data-cmr="legacy"] input').count(),0)
    await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
    await shot('LEGACY_ONE_RULE_RESTORED')
    return {status:'PASS',actual_Auth_PostgREST_Native:true,readonly_reference:500,independent_formula_point:f.point,
      two_policy_revisions_only:true,one_active_rule:true,intent_saved_before_network:true,reload_same_UUID:true,
      changed_body_fenced:true,dirty_form_preserved:true,current403_keeps_intent_and_retires_facts:true,
      restored_access_recovers_same_UUID:true,settings_do_not_write_Native_business:true,no_horizontal_overflow:true,
      viewport:mobile?390:1440,shots,policy_values:'TEST_FIXTURE_ONLY_NOT_OWNER_OR_ENTENG'}
  }catch(error){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/OW14B_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),sent,losses,fixture:f,
      panel:await panel.innerText().catch(()=>''),alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2))
    await shot('FAILURE').catch(()=>{});throw error
  }finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return retainedCases(ui).concat([
  ['OW14B_BROWSER_DESKTOP_CHOICE_RELOAD_UUID',()=>journey(ui,today,false)],
  ['OW14B_BROWSER_MOBILE_CHOICE_RELOAD_CURRENT_ACCESS',()=>journey(ui,today,true)]])}
