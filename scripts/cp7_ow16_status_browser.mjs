import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {openCutting} from './cp7_cutting_yield_browser.mjs'

const fixture=(operation,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_ow16_status_browser_fixture.py',operation],
  {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
async function select(ui,page,f,mobile){
  await openCutting(ui,page,mobile)
  await page.getByLabel('Cari draft Potongan',{exact:true}).fill(f.group_number)
  const search=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_cutting_workspace_v2')&&r.request().postDataJSON().p_draft_query===f.group_number)
  await page.getByRole('button',{name:'Cari draft',exact:true}).click();assert.equal((await search).status(),200)
  await page.locator('.ccut-drafts button').filter({hasText:f.group_number}).click()
  await ui.expect(page.getByRole('button',{name:'Post ke WIP Potongan',exact:true})).toBeEnabled()
}
async function journey(ui,today,mobile){
  const user=await ui.login('OWNER',{label:'ow16-status-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  const page=user.page,actor=user.user.id
  await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
  const f=fixture('prepare',{today}),state=()=>fixture('state',{fixture:f,actor})
  const panel=page.getByRole('region',{name:'Status hasil potong otomatis',exact:true})
  let lost=null
  try{
    await select(ui,page,f,mobile)
    await ui.expect(panel).toContainText('Potongan belum disahkan atau sudah dibatalkan.')
    const before=state();assert.equal(Number(before.raw_qty),70);assert.equal(before.posted,false)
    await panel.locator('summary').click()
    await panel.getByLabel('Cakupan rentang riwayat (%)',{exact:true}).fill('80')
    await panel.getByLabel('Minimum kelompok pembanding',{exact:true}).fill('3')
    await panel.getByLabel('Alasan perubahan',{exact:true}).fill('Aturan OWNER fixture browser OW16')
    await panel.getByRole('checkbox',{name:'Saya sudah memeriksa cakupan dan minimum riwayat ini.',exact:true}).check()
    const saveName='erp_cp7_save_cutting_status_policy_v1'
    if(mobile)await page.route('**/rest/v1/rpc/'+saveName,async route=>{
      const response=await route.fetch();lost={args:route.request().postDataJSON(),status:response.status(),body:await response.json()}
      await route.abort('failed')
    })
    const saved=mobile?null:page.waitForResponse(r=>r.url().endsWith('/rpc/'+saveName))
    await panel.getByRole('button',{name:'Simpan aturan hasil potong',exact:true}).click()
    if(mobile){
      await ui.expect.poll(()=>lost?.status).toBe(200)
      await ui.expect(panel).toContainText('Penyimpanan aturan belum dipastikan')
      assert.equal(state().native_hash,before.native_hash)
      await page.unroute('**/rest/v1/rpc/'+saveName)
      await page.reload();await openCutting(ui,page,mobile)
      const recovering=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_cutting_status_policy_request_v1'))
      await panel.getByRole('button',{name:/Periksa aturan tertunda/}).click()
      const recovered=await recovering;assert.equal(recovered.status(),200)
      assert.deepEqual(recovered.request().postDataJSON(),lost.args);assert.deepEqual(await recovered.json(),lost.body)
      await select(ui,page,f,mobile)
    }else assert.equal((await saved).status(),200)
    await ui.expect(panel).toContainText('minimal 3 kelompok')
    const afterPolicy=state();assert.equal(afterPolicy.native_hash,before.native_hash);assert.equal(afterPolicy.own_requests,1)
    const posted=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_cutting_group_before_sewing_v2'))
    await page.getByRole('button',{name:'Post ke WIP Potongan',exact:true}).click();assert.equal((await posted).status(),200)
    // No status/learning capture button: the render triggered by Native POST
    // performs its own read of the now-posted physical group.
    await ui.expect(panel).toContainText('Wajar menurut riwayat')
    await ui.expect(panel).toContainText('Total hasil: 40 pcs')
    await ui.expect(panel).toContainText('20–60 pcs')
    const afterPost=state();assert.equal(afterPost.posted,true);assert.equal(Number(afterPost.raw_qty),60);assert.equal(Number(afterPost.raw_value),600)
    assert.equal(afterPost.physical_at,before.physical_at)
    await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)
    // Real current403 while the client identity is still AUTHORIZED.
    fixture('deactivate',{actor});const deactivated=state()
    const denied=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_cutting_status_v1')&&r.status()===403)
    await page.evaluate(()=>dispatchEvent(new Event('focus')));await denied
    await ui.expect(panel).not.toContainText('Wajar menurut riwayat')
    await ui.expect(panel.locator('.ccut-status-list')).toHaveCount(0)
    assert.equal(state().native_hash,deactivated.native_hash)
    return {status:'PASS',actual_Auth_POSTgREST_and_Native_POST:true,automatic_status_without_manual_capture:true,
      native_raw70_to60_value700_to600:true,current_total_pcs40_range20_to60:true,
      physical_WIB_instant_unchanged_with_foreign_browser_timezone:mobile,
      lost_reply_same_UUID_lookup:mobile,only_one_policy_effect:true,current403_retires_status:true,
      no_horizontal_overflow:true,viewport:mobile?390:1440}
  }catch(error){
    mkdirSync('cp6-proof/t3',{recursive:true})
    writeFileSync('cp6-proof/t3/OW16_BROWSER_'+(mobile?'MOBILE':'DESKTOP')+'_FAILURE.json',JSON.stringify({error:String(error),
      panel:await panel.innerText().catch(()=>''),alerts:await page.getByRole('alert').allTextContents().catch(()=>[]),lost},null,2))
    throw error
  }finally{fixture('restore',{actor});await user.context.close()}
}
export function cases(ui,today){return [['OW16_BROWSER_DESKTOP_AUTO_AFTER_POST',()=>journey(ui,today,false)],
  ['OW16_BROWSER_MOBILE_UUID_RECOVERY',()=>journey(ui,today,true)]]}
