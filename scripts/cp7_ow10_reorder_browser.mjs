import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow10_reorder_browser_fixture.py',op],
  {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const save='erp_cp7_save_fg_reorder_manual_v1'
async function navigate(ui,page){
  const parent=page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).first()
  await parent.waitFor({state:'attached'})
  const menu=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await menu.isVisible()){await menu.click();await ui.expect(page.locator('.sidebar')).toHaveClass(/sidebar-open/)}
  const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true})
  if(!await link.isVisible())await parent.click()
  await link.click()
  await ui.expect(page.getByRole('region',{name:'Titik pesan ulang',exact:true})).toBeVisible()
}
async function journey(ui,today,mobile){
  const user=await ui.login('OWNER',{label:'ow10r-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const page=user.page,actor=user.user.id,requests=[],shots=[]
  let lost=null,f
  const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/OW10R_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`
    await page.screenshot({path,fullPage:true});shots.push(path)}
  try{
    f=fixture('prepare',{today,actor})
    await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
    await page.route('**/rest/v1/rpc/'+save,async route=>{
      const args=route.request().postDataJSON(),response=await route.fetch(),body=await response.json()
      requests.push({args,status:response.status(),body})
      if(mobile&&!lost){lost={args,status:response.status(),body};await route.abort('failed')}
      else await route.fulfill({response})
    })
    await navigate(ui,page)
    const panel=page.getByRole('region',{name:'Titik pesan ulang',exact:true})
    const item=panel.locator('article[data-target-key="'+f.target+'"]')
    await ui.expect(item.locator('[data-cfr="point"]')).toHaveText('10 pcs')
    await ui.expect(item).toContainText('Perkiraan tepat waktu')
    await ui.expect(item).toContainText('Target rencana: 24 pcs')
    await ui.expect(item).toContainText('Stok diperiksa')
    await item.getByRole('button',{name:'Atur angka manual',exact:true}).click()
    await item.getByLabel('Titik pesan ulang manual (pcs)',{exact:true}).fill('25')
    await item.getByLabel('Alasan angka manual',{exact:true}).fill('OW10R Native browser fixture, not owner policy')
    await item.getByRole('button',{name:'Simpan angka manual',exact:true}).click()
    if(mobile){
      await ui.expect(item).toContainText('Jawaban server tidak sampai')
      await item.getByRole('button',{name:'Simpan angka manual',exact:true}).click()
      await ui.expect(item).toContainText('Permintaan ini ternyata sudah tersimpan sebelumnya')
      assert.equal(lost?.status,200)
      assert.equal(requests.length,2);assert.deepEqual(requests[0].args,requests[1].args)
    }
    await ui.expect(item.locator('[data-cfr="point"]')).toHaveText('25 pcs')
    const stored=fixture('state',{product:f.product})
    assert.equal(stored.revisions,1);assert.equal(stored.row.projection.target_pcs,'24')
    await shot('SAVED')
    await page.reload();await navigate(ui,page)
    await ui.expect(item.locator('[data-cfr="point"]')).toHaveText('25 pcs')
    await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
    fixture('deactivate',{actor})
    await panel.getByRole('button',{name:'Muat ulang titik pesan ulang',exact:true}).click()
    await ui.expect(item).toHaveCount(0)
    assert.equal(fixture('state',{product:f.product}).revisions,1)
    await shot('REVOKED')
    return{status:'PASS',actual_Auth_PostgREST_Native:true,manual25_preserves_target24:true,
      lost_response_same_UUID:mobile,one_revision_after_reload:true,current_revocation_hides_rows:true,
      viewport:mobile?390:1440,no_horizontal_overflow:true,shots,fixture_policy_not_owner_default:true}
  }catch(error){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync(`cp6-proof/t3/OW10R_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),requests,lost,
      alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2))
    await shot('FAILURE').catch(()=>{});throw error
  }finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return[
  ['OW10R_BROWSER_DESKTOP_NATIVE_V2',()=>journey(ui,today,false)],
  ['OW10R_BROWSER_MOBILE_LOST_REPLY',()=>journey(ui,today,true)],
]}
