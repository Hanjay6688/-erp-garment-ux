// Real versioned HTTP reader and connected UI. No fulfilled business responses.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { expect } from '@playwright/test'

export async function runSelectors(c) {
  const ids=['HTTP_OWNER','HTTP_VIEW_ONLY','HTTP_NO_VIEW','HTTP_UNMAPPED','HTTP_INACTIVE','HTTP_ANON','LEGACY_LIMITS',
    'FIND_PO_201','PAGE_PO_SELECTION','FIND_DRAFT_101','FILTER_FORM_PRESERVED','DRAFT_PAGE_PRESERVED',
    'STALE_VERSION_BLOCKED','EXPLICIT_RELOAD_SAVE','POSTED_DRAFT_BLOCKED']
  const report={status:'INCOMPLETE',head:c.frontendHead,tree:c.frontendTree,backend_generation:'AN',
    planned_case_ids:ids,cases:[],production_go:false,independent_acceptance:false,successful_responses_supplied:false}
  const save=()=>writeFileSync(resolve(c.reportDir,'SELECTORS_UI.json'),JSON.stringify(report,null,2)+'\n')
  const pass=(id,detail={})=>{assert.ok(ids.includes(id)&&!report.cases.some(r=>r.id===id));report.cases.push({id,status:'PASS',...detail});save()}
  save();let page
  async function http(token,args={}) {
    const anon=process.env.SUPABASE_ANON_KEY
    const res=await fetch('http://127.0.0.1:54329/rpc/erp_get_cutting_workspace_v2',{
      method:'POST',headers:{apikey:anon,Authorization:`Bearer ${token||anon}`,'Content-Type':'application/json'},body:JSON.stringify(args)})
    return {status:res.status,body:await res.json()}
  }
  try {
    for (const kind of ['OWNER','VIEW_ONLY','NO_VIEW','UNMAPPED','INACTIVE','ANON']) {
      let token=kind==='OWNER'?c.session.access_token:null
      if(!['OWNER','ANON'].includes(kind)) {
        const user=await c.newUser('selector-'+kind.toLowerCase())
        if(kind!=='UNMAPPED')await c.mapUser(c.session.access_token,user,kind==='NO_VIEW'?['master.pattern.view']:['production.cutting.view'],kind!=='INACTIVE')
        const auth=await c.authRequest('token?grant_type=password',{email:user.email,password:user.password})
        token=auth.access_token;c.secrets.push(token)
      }
      const response=await http(token)
      if(['OWNER','VIEW_ONLY'].includes(kind)){assert.equal(response.status,200);assert.equal(response.body.contract_version,2)}
      else {assert.notEqual(response.status,200);assert.equal(response.body.code,'42501')}
      pass('HTTP_'+kind,{http_status:response.status})
    }
    const fixture=JSON.parse(execFileSync('python',[fileURLToPath(new URL('./cp6_v2620an_ui_fixture.py',import.meta.url)),c.owner.id],{encoding:'utf8',stdio:['ignore','pipe','pipe']}))
    const drafts=[]
    for(const payload of fixture.payloads)drafts.push(await c.rpc(c.session.access_token,'erp_save_cutting_group_before_sewing_v2',{
      p_payload:payload,p_client_request_id:randomUUID(),p_expected_version:null}))
    assert.equal(drafts.length,101)
    const target=drafts[0],payload={...fixture.payloads[0],id:target.cutting_group_id}
    for(const id of [fixture.po,fixture.material,target.cutting_group_id])assert.match(id,/^[0-9a-f-]{36}$/)
    const original=await c.rpc(c.session.access_token,'erp_get_cutting_workspace_v1',{
      p_roll_query:target.group_number,p_location_id:fixture.location,p_limit:200,p_offset:200})
    assert.ok(!original.orders.some(r=>r.id===fixture.po));assert.ok(!original.drafts.some(r=>r.cutting_group_id===target.cutting_group_id))
    pass('LEGACY_LIMITS',{late_po_absent:true,oldest_draft_absent:true})
    page=await c.pageFor(c.owner,false)
    const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
    const link=page.getByRole('button',{name:'• Buat Potongan',exact:true})
    if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
    await link.click();await expect(page.getByRole('heading',{name:'Buat Potongan',exact:true})).toBeVisible()
    async function search(kind,text) {
      await page.getByLabel(kind==='PO'?'Cari PO':'Cari draft Potongan',{exact:true}).fill(text)
      const [response]=await Promise.all([
        page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_cutting_workspace_v2')&&r.request().postDataJSON()?.[kind==='PO'?'p_order_query':'p_draft_query']===text),
        page.getByRole('button',{name:kind==='PO'?'Cari PO':'Cari draft',exact:true}).click()])
      assert.equal(response.status(),200)
      await expect(page.getByRole('button',{name:kind==='PO'?'Cari PO':'Cari draft',exact:true})).toBeEnabled()
    }
    await search('PO',fixture.po_number)
    const po=page.getByRole('combobox',{name:/^Production Order/})
    await po.selectOption(fixture.po);await expect(po).toHaveValue(fixture.po)
    await expect(page.locator('.ccut-size-list').getByRole('button',{name:fixture.size_code,exact:true})).toBeVisible()
    pass('FIND_PO_201')
    await search('PO',fixture.prefix)
    for(let i=1;i<=4;i++) {
      await page.getByRole('button',{name:'PO berikutnya',exact:true}).click()
      await expect(page.getByRole('button',{name:'Cari PO',exact:true})).toBeEnabled()
      await expect(po).toHaveValue(fixture.po)
    }
    pass('PAGE_PO_SELECTION',{pages:5,selected_po_unchanged:true})
    await search('DRAFT',target.group_number)
    await page.locator('.ccut-drafts').getByRole('button').filter({hasText:target.group_number}).click()
    const count=page.getByLabel(`${fixture.roll_number} Size ${fixture.size_code}`,{exact:true})
    const notes=page.getByLabel('Catatan',{exact:true})
    const saveDraft=page.getByRole('button',{name:'Simpan draft',exact:true})
    const post=page.getByRole('button',{name:'Post ke WIP Potongan',exact:true})
    await expect(post).toBeEnabled();await expect(count).toHaveValue('1');pass('FIND_DRAFT_101')
    await count.fill('2');await notes.fill('AN unsaved quantity must survive filtering')
    await search('DRAFT','AN-NO-MATCH')
    await expect(count).toHaveValue('2');await expect(notes).toHaveValue('AN unsaved quantity must survive filtering');await expect(po).toHaveValue(fixture.po)
    await expect(page.locator('.ccut-size-list').getByRole('button',{name:fixture.size_code,exact:true})).toBeVisible()
    pass('FILTER_FORM_PRESERVED')
    await search('DRAFT',fixture.po_number)
    await page.getByRole('button',{name:'Draft berikutnya',exact:true}).click();await expect(saveDraft).toBeEnabled()
    await expect(count).toHaveValue('2');await expect(notes).toHaveValue('AN unsaved quantity must survive filtering');pass('DRAFT_PAGE_PRESERVED')
    const changed=await c.rpc(c.session.access_token,'erp_save_cutting_group_before_sewing_v2',{
      p_payload:{...payload,notes:'AN changed by another session'},p_client_request_id:randomUUID(),p_expected_version:target.row_version})
    await page.getByRole('button',{name:'Refetch',exact:true}).click()
    await expect(page.getByText('Draft berubah di sesi lain.',{exact:false})).toBeVisible()
    await expect(saveDraft).toBeDisabled();await expect(post).toBeDisabled();await expect(notes).toHaveValue('AN unsaved quantity must survive filtering')
    pass('STALE_VERSION_BLOCKED',{old_version:target.row_version,current_version:changed.row_version})
    await page.getByRole('button',{name:'Muat draft terbaru',exact:true}).click()
    await expect(notes).toHaveValue('AN changed by another session');await expect(saveDraft).toBeEnabled();await expect(count).toHaveValue('1')
    await notes.fill('AN actual UI save after explicit reload')
    const [savedResponse]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_cutting_group_before_sewing_v2')),
      saveDraft.click()])
    assert.equal(savedResponse.status(),200)
    const saved=await savedResponse.json();assert.equal(savedResponse.request().postDataJSON().p_expected_version,changed.row_version)
    assert.ok(saved.row_version>changed.row_version);await expect(post).toBeDisabled()
    pass('EXPLICIT_RELOAD_SAVE',{actual_save:true,expected_version:changed.row_version})
    await search('DRAFT',target.group_number)
    await page.locator('.ccut-drafts').getByRole('button').filter({hasText:target.group_number}).click();await expect(post).toBeEnabled()
    const posted=await c.rpc(c.session.access_token,'erp_save_cutting_group_before_sewing_v2',{
      p_payload:{...payload,action:'POST'},p_client_request_id:randomUUID(),p_expected_version:saved.row_version})
    assert.equal(posted.material_issue_posted,true)
    await page.getByRole('button',{name:'Refetch',exact:true}).click()
    await expect(page.getByText('Draft sudah berubah tahap',{exact:false})).toBeVisible()
    await expect(saveDraft).toBeDisabled();await expect(post).toBeDisabled()
    assert.equal(Number(c.query(`select sum(qty_signed) from erp.material_stock_movements where material_id='${fixture.material}'`)),100)
    pass('POSTED_DRAFT_BLOCKED',{raw_stock:100,whole_clone_disposal_required:true})
    await page.screenshot({path:resolve(c.reportDir,'CUTTING_SELECTOR_STALE.png'),fullPage:true})
    assert.equal(report.cases.length,ids.length);report.status='WRITER_PASS'
  } catch(error) {
    let message=String(error.stack||error)
    for(const secret of c.secrets.filter(Boolean))message=message.split(secret).join('[REDACTED]')
    report.failure={message:message.slice(0,7500)};throw error
  } finally {save();await page?.context().close()}
  return report
}
