// Actual UI -> local Auth -> original RPCs -> disposable AL database.
// Faults affect only transport after a real commit or a read response.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { expect } from '@playwright/test'

export async function runFrontendRecovery(c) {
  const ids = ['CUT_RAW_COUNT', 'CUT_LOST_REPLY', 'SHARED_PENDING_READABLE_QC', 'CUT_EXACT_REPLAY',
    'PICKUP_REFETCH_FAILURE', 'PICKUP_READ_RECOVERY', 'WIP_REAL_CONTRACT', 'BS_GATEWAY_503', 'BS_EXACT_REPLAY']
  const report = { status: 'INCOMPLETE', classification: 'WRITER_REAL_AUTH_UI_HTTP_DATABASE', candidate_head: c.frontendHead,
    candidate_tree: c.frontendTree, backend_generation: process.env.CP6_RUNTIME_GENERATION || 'AL', production_go: false, independent_acceptance: false,
    schema_acl_modified: false, supplied_successful_business_responses: false, planned: ids, cases: [],
    source_sha256: createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex') }
  const save = () => writeFileSync(resolve(c.reportDir, 'FRONTEND_RECOVERY.json'), JSON.stringify(report, null, 2)+'\n')
  const pass = (id, detail) => { assert.ok(ids.includes(id)); assert.ok(!report.cases.some(x=>x.id===id)); report.cases.push({id,status:'PASS',...detail}); save() }
  let page, other
  save()
  try {
    const fixture = JSON.parse(execFileSync('python', [fileURLToPath(new URL('./cp6_frontend_recovery_fixture.py', import.meta.url)), c.owner.id], { encoding: 'utf8', stdio:['ignore','pipe','pipe'] }))
    const cutDraft = await c.rpc(c.session.access_token, 'erp_save_cutting_group_before_sewing_v2', {
      p_payload: fixture.cut_payload, p_client_request_id: randomUUID(), p_expected_version: null,
    })
    fixture.group = cutDraft.cutting_group_id
    fixture.group_number = cutDraft.group_number
    for (const name of ['po','group','roll','material']) assert.match(fixture[name],/^[0-9a-f-]{36}$/)
    const facts = () => JSON.parse(c.query(`select jsonb_build_object(
      'stock',(select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id='${fixture.material}'),
      'wip',(select coalesce(sum(debit-credit),0) from erp.journal_lines where po_id='${fixture.po}' and account_id=erp.account_id('WIP')),
      'journal_rows',(select count(*) from erp.journal_lines where po_id='${fixture.po}'),
      'pickup_count',(select count(*) from erp.cutting_pickups where cutting_group_id='${fixture.group}' and status='POSTED'),
      'allocated',(select coalesce(sum(a.qty_pcs),0) from erp.cutting_distribution_allocations a join erp.cutting_distribution_batches b on b.id=a.batch_id join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id='${fixture.group}' and p.status='POSTED'))`))
    async function nav(target, name, heading=name) {
      const menu=target.getByRole('button',{name:'Buka menu',exact:true})
      if(await menu.isVisible()) await menu.click()
      const link=target.getByRole('button',{name:`• ${name}`,exact:true})
      if(!await link.isVisible()) await target.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
      await link.click(); await expect(target.getByRole('heading',{name:heading,exact:true})).toBeVisible()
    }
    page = await c.pageFor(c.owner, false)
    await nav(page, 'Buat Potongan')
    // This wrapping label includes its select's option text in label matching.
    await page.getByRole('combobox',{name:/^Gudang bahan/}).selectOption(fixture.location)
    await page.locator('.ccut-drafts').getByRole('button').filter({hasText:fixture.group_number}).click()
    const count = page.getByLabel(`${fixture.roll_number} Size ${fixture.size_code}`,{exact:true})
    const post = page.getByRole('button',{name:'Post ke WIP Potongan',exact:true})
    const requests=[]
    page.on('request', request=>{
      if(request.method()==='POST' && /\/rpc\/erp_save_(cutting|bs_resolution)/.test(request.url())) requests.push({path:new URL(request.url()).pathname,args:request.postDataJSON()})
    })
    for (const raw of ['-2','1,5','1.5','1e3','','2147483648']) {
      await count.fill(raw); await expect(count).toHaveValue(raw); await expect(post).toBeDisabled()
    }
    const measure=page.getByLabel(`${fixture.roll_number} terpakai`,{exact:true})
    await measure.fill('-1,5'); await expect(measure).toHaveValue('-1,5'); await expect(post).toBeDisabled()
    await measure.fill('10'); await count.fill('10'); await expect(post).toBeEnabled()
    assert.equal(requests.length,0)
    const before = facts(); assert.equal(before.stock,10); assert.equal(before.wip,0)
    pass('CUT_RAW_COUNT',{invalid_values_preserved:true,write_requests:0,before})
    let cutRequest
    await page.route('**/rpc/erp_save_cutting_group_before_sewing_v2',async route=>{
      cutRequest=route.request().postDataJSON()
      const reply=await route.fetch(); assert.equal(reply.status(),200)
      assert.equal((await reply.json()).material_issue_posted,true)
      await route.abort('connectionreset')
    },{times:1})
    await post.click(); await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
    const cutFacts=facts(); assert.equal(cutFacts.stock,0); assert.equal(cutFacts.wip,100)
    assert.equal(cutFacts.pickup_count,0)
    pass('CUT_LOST_REPLY',{request_id:cutRequest.p_client_request_id,observed:cutFacts})
    other = await page.context().newPage(); await other.goto(page.url())
    await nav(other, 'QC & Final SKU')
    await expect(other.getByText(/Transaksi Buat Potongan belum selesai/)).toBeVisible()
    await expect(other.getByRole('button',{name:'Muat ulang data',exact:true})).toBeEnabled()
    await other.getByRole('button',{name:'Muat ulang data',exact:true}).click()
    await expect(other.getByText(/Transaksi Buat Potongan belum selesai/)).toBeVisible()
    assert.deepEqual(facts(),cutFacts)
    pass('SHARED_PENDING_READABLE_QC',{scope:'same actor/project, different live tab/domain',observed:cutFacts})
    await page.reload(); await nav(page,'Buat Potongan')
    const [replayReply]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_cutting_group_before_sewing_v2')),
      page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click(),
    ])
    assert.equal(replayReply.status(),200)
    assert.deepEqual(replayReply.request().postDataJSON(),cutRequest)
    await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
    assert.deepEqual(facts(),cutFacts)
    pass('CUT_EXACT_REPLAY',{same_uuid_payload_version:true,observed:cutFacts})

    await nav(page,'Bagi Potongan')
    await page.getByPlaceholder('Nomor Potongan, PO, model, Pola, Mandor…').fill(fixture.group_number)
    await page.locator('.cpick-search').getByRole('button',{name:'Cari',exact:true}).click()
    await expect(page.locator('.cpick-selected h2')).toContainText(fixture.group_number)
    const pickupPost=page.getByRole('button',{name:'Catat pickup & masuk Sewing',exact:true})
    await expect(pickupPost).toBeEnabled()
    let postCommitted=false
    await page.route('**/rpc/erp_save_cutting_pickup_v1',async route=>{
      const reply=await route.fetch();assert.equal(reply.status(),200);assert.equal((await reply.json()).status,'POSTED')
      postCommitted=true;await route.fulfill({response:reply})
    },{times:1})
    await page.route('**/rpc/erp_get_cutting_pickup_queue_v1',async route=>{
      if(postCommitted) await route.abort('connectionreset');else await route.continue()
    })
    await pickupPost.click()
    await expect(page.getByText(/Aksi sudah tersimpan, tetapi refresh authoritative gagal/)).toBeVisible()
    await expect(page.locator('.cpick-actions')).toHaveCount(0)
    const pickupFacts=facts();assert.equal(pickupFacts.pickup_count,1);assert.equal(pickupFacts.allocated,10)
    assert.equal(pickupFacts.stock,0);assert.equal(pickupFacts.wip,100)
    const pickupRequests=requests.filter(x=>x.path.endsWith('erp_save_cutting_pickup_v1')).length
    assert.equal(pickupRequests,1)
    pass('PICKUP_REFETCH_FAILURE',{observed:pickupFacts,write_requests:pickupRequests,form_retired:true})
    await page.unroute('**/rpc/erp_get_cutting_pickup_queue_v1')
    await page.getByRole('button',{name:'Refetch',exact:true}).click()
    await expect(page.getByText(/Aksi sudah tersimpan, tetapi refresh authoritative gagal/)).toHaveCount(0)
    assert.equal(requests.filter(x=>x.path.endsWith('erp_save_cutting_pickup_v1')).length,1)
    assert.deepEqual(facts(),pickupFacts)
    pass('PICKUP_READ_RECOVERY',{observed:pickupFacts,no_second_write:true})
    const [wipReply]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_get_wip_control_v1')),
      nav(page,'WIP & Sewing','WIP & Sewing'),
    ])
    assert.equal(wipReply.status(),200)
    await expect(page.locator('.connected-wip-page')).toContainText(fixture.group_number)
    await expect(page.locator('.connected-wip-page [role="alert"]')).toHaveCount(0)
    pass('WIP_REAL_CONTRACT',{strict_parser_accepted_original_response:true,group_id:fixture.group})

    await nav(page,'Barang BS & Rework')
    await page.getByRole('button',{name:'BS legacy',exact:true}).click()
    const number='CP6-REC-BS-'+randomUUID().slice(0,12)
    await page.getByLabel('NOMOR BS · OPSIONAL',{exact:true}).fill(number)
    await page.getByLabel('REFERENSI LEGACY · WAJIB',{exact:true}).fill('Synthetic physical count '+number)
    await page.getByLabel('QTY PCS',{exact:true}).fill('2')
    await page.getByLabel('ALASAN PENCATATAN · WAJIB',{exact:true}).fill('Recovery native gateway after commit')
    let bsRequest, bsId
    await page.route('**/rpc/erp_save_bs_resolution_action_v1',async route=>{
      bsRequest=route.request().postDataJSON()
      const reply=await route.fetch();assert.equal(reply.status(),200)
      const result=await reply.json();bsId=result.result.bs_case_id;assert.match(bsId,/^[0-9a-f-]{36}$/)
      await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Injected disposable gateway failure after real commit'})})
    },{times:1})
    await page.getByRole('button',{name:'Simpan kasus authoritative',exact:true}).click()
    await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
    assert.equal(Number(c.query(`select count(*) from erp.bs_cases where id='${bsId}' and qty_pcs=2`)),1)
    pass('BS_GATEWAY_503',{request_id:bsRequest.p_client_request_id,bs_case_id:bsId,real_commit_count:1})
    const [bsReply]=await Promise.all([
      page.waitForResponse(r=>r.url().endsWith('/rpc/erp_save_bs_resolution_action_v1')),
      page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click(),
    ])
    assert.equal(bsReply.status(),200);assert.deepEqual(bsReply.request().postDataJSON(),bsRequest)
    assert.equal((await bsReply.json()).result.bs_case_id,bsId)
    await expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
    assert.equal(Number(c.query(`select count(*) from erp.bs_cases where bs_number='${number}'`)),1)
    assert.deepEqual(facts(),pickupFacts)
    pass('BS_EXACT_REPLAY',{same_uuid_payload_version:true,real_commit_count:1,cut_pickup_facts_unchanged:true})
    assert.equal(report.cases.length,ids.length)
    report.status='WRITER_PASS'
  } catch(error) {
    let message=String(error.stack||error)
    for(const secret of c.secrets.filter(Boolean))message=message.split(secret).join('[REDACTED]')
    report.failure=message.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]').slice(0,9000)
    // Visible synthetic UI only: no storage, request headers, or Auth responses.
    let visible=await page?.locator('body').innerText().catch(()=> 'UI unavailable')
    if(visible){
      for(const secret of c.secrets.filter(Boolean))visible=visible.split(secret).join('[REDACTED]')
      report.visible_ui=visible.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT REDACTED]').slice(0,24000)
    }
    throw error
  } finally {
    await other?.close();await page?.context().close();save()
  }
  return report
}
