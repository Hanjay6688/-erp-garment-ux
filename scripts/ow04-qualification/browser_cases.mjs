import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const endpoint='**/rest/v1/rpc/erp_cp7_settle_sales_return_v1'
const readEndpoint='**/rest/v1/rpc/erp_cp7_get_sales_v1'
const fixture=(op,p={})=>JSON.parse(execFileSync('python',['../auditor/scripts/ow04-qualification/browser_fixture.py',op],
 {input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const envelope=page=>page.evaluate(()=>Object.entries(localStorage)
 .filter(([key])=>key.startsWith('erp.production.SALES.pending-mutation.v1:'))
 .map(([key,value])=>({key,value,parsed:JSON.parse(value)})))
async function menu(ui,page,group='Penjualan',name='Retur Penjualan'){
 const toggle=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await toggle.isVisible())await toggle.click()
 const button=page.getByRole('button',{name:'• '+name,exact:true})
 if(!await button.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await button.click()
}
async function stockControls(ui,page,f){
 await menu(ui,page,'Gudang','Stock Adjustment')
 await page.getByRole('navigation',{name:'Jenis persediaan'}).getByRole('button',{name:'Barang jadi',exact:true}).click()
 await page.getByLabel('Cari sumber penyesuaian FG',{exact:true}).fill(f.sku)
 await page.getByRole('button',{name:'Cari sumber FG',exact:true}).click()
 const buttons=page.locator('.cfga .cfg-position').getByRole('button')
 await ui.expect.poll(()=>buttons.count()).toBeGreaterThan(0)
 return buttons
}
async function observed(page,button){
 const pending=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_settle_sales_return_v1'))
 await button.click();return await pending
}
export async function assertNoStaleInvoiceFacts(ui,page){
 const empty=page.getByRole('complementary',{name:'Rincian invoice',exact:true})
 // The unconditional layout aside may remain; no authoritative facts or
 // transaction controls may survive inside it after a failed fresh read.
 await ui.expect(empty).toHaveText(/^Rincian invoice\s*Pilih invoice untuk memeriksa barang dan pembayaran yang tercatat\.$/)
 await ui.expect(empty.locator('[aria-label="Nilai invoice"],.cproc-item,button,input,select,textarea')).toHaveCount(0)
 await ui.expect(page.getByRole('region',{name:'Daftar invoice',exact:true}).locator('.cproc-receipt')).toHaveCount(0)
 await ui.expect(page.getByRole('region',{name:'Retur fisik invoice',exact:true})).toHaveCount(0)
 await ui.expect(page.getByRole('region',{name:'Penyelesaian nilai retur',exact:true})).toHaveCount(0)
}
async function journey(ui,today,kind){
 const mobile=kind==='REFUND',mode=mobile?'REFUND':'CREDIT',f=fixture('prepare',{today,mode})
 const user=await ui.login('OWNER',{label:'ow04-browser-'+kind.toLowerCase(),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,requests=[],quotes=[],quoteInputs=[],otherPages=[],timings=[]
 const detail=()=>page.getByRole('complementary',{name:'Rincian invoice',exact:true})
 const panel=()=>page.getByRole('region',{name:'Retur fisik invoice',exact:true})
 const section=()=>page.getByRole('region',{name:'Penyelesaian nilai retur',exact:true})
 const result=()=>page.getByRole('region',{name:'Hasil pemeriksaan penyelesaian retur',exact:true})
 const submit=()=>section().getByRole('button',{name:'Catat retur dan penyelesaian',exact:true})
 const reconcile=()=>page.getByRole('button',{name:'Reconcile transaksi',exact:true})
 const create=()=>page.getByRole('button',{name:'Buat invoice',exact:true})
 let first,firstArgs,revoked=false,other,otherButtons,lostError,normalSaveStart=null
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_settle_sales_return_v1'))requests.push(r.postDataJSON())})
 async function quote(){
  const started=performance.now()
  const next=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_sales_return_settlement_quote_v1')
   &&r.request().postDataJSON()?.p_query?.kind!=='ACCOUNT_OPTIONS')
  await section().getByRole('button',{name:'Periksa penyelesaian retur',exact:true}).click()
  const response=await next;assert.equal(response.status(),200)
  const raw=await response.json();quotes.push(raw);quoteInputs.push(response.request().postDataJSON().p_query)
  assert.equal(raw.kind,'QUOTE');assert.equal(raw.readiness.state,'READY')
  assert.equal(raw.current_credit_amount,f.credit_amount)
  assert.equal(raw.totals.after.effective_paid,'800.00');assert.equal(raw.totals.after.receivable_remaining,'0.00')
  await ui.expect(result()).toBeVisible()
  const display=value=>'Rp'+Number(value).toLocaleString('id-ID')
  await ui.expect(result().locator('output[aria-label="Hak kredit saat ini"]')).toHaveText(display(f.credit_amount))
  const table={gross_total:['1000.00','1000.00'],return_total:['0.00','200.00'],net_total:['1000.00','800.00'],
   payments_received:[f.original_paid,f.original_paid],credit_applied:['0.00','0.00'],
   credit_recognized:['0.00',f.credit_amount],effective_paid:[f.original_paid,'800.00'],
   receivable_remaining:[mobile?'100.00':'0.00','0.00']}
  for(const [key,pair]of Object.entries(table)){
   const cells=result().locator('tr[data-total="'+key+'"]').getByRole('cell')
   await ui.expect(cells).toHaveCount(2)
   await ui.expect(cells.nth(0)).toHaveText(display(pair[0]));await ui.expect(cells.nth(1)).toHaveText(display(pair[1]))
  }
  await ui.expect(result().locator('[data-return-book-date]')).toHaveText(f.return_pair[1])
  await ui.expect(result().locator('p').filter({hasText:'Tanggal pengakuan retur:'}))
   .toHaveText('Tanggal pengakuan retur: '+f.return_pair[0]+'; tanggal buku retur: '+f.return_pair[1]+'.')
  const recognition=result().getByRole('table',{name:'Tanggal pengakuan kredit retur',exact:true}).locator('tbody tr')
  await ui.expect(recognition).toHaveCount(1)
  await ui.expect(recognition.getByRole('cell').nth(0)).toHaveText(f.return_pair[0])
  await ui.expect(recognition.getByRole('cell').nth(1)).toHaveText(f.return_pair[1])
  await ui.expect(recognition.getByRole('cell').nth(2)).toHaveText(display(f.credit_amount))
  await ui.expect(section().getByText('Tanggal retur '+f.return_pair[0]+'; buku retur '+f.return_pair[1]+'.',{exact:true})).toBeVisible()
  if(mobile){
   assert.notEqual(f.refund_pair[0],f.refund_pair[1],'REOPENED physical/book axes must remain distinct')
   await ui.expect(section().locator('output[aria-label="Nominal pengembalian uang"]')).toHaveText('Rp100')
   await ui.expect(section().getByText('Tanggal pengembalian uang '+f.refund_pair[0]+'; buku pengembalian '+f.refund_pair[1]+'.',{exact:true})).toBeVisible()
   await ui.expect(result().locator('p').filter({hasText:'Batas pengembalian pada waktu dipilih:'}))
    .toContainText('Tanggal buku pengembalian: '+f.refund_pair[1]+'.')
  }
  timings.push({operation:'quote_to_complete_result',milliseconds:performance.now()-started})
  await section().getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check()
  await ui.expect(submit()).toBeEnabled()
 }
 async function lost(){
  await page.route(endpoint,async route=>{
   try{const response=await route.fetch();assert.equal(response.status(),200)
    first=await response.json();firstArgs=route.request().postDataJSON()
    await route.abort('failed')
   }catch(error){lostError=String(error);await route.abort('failed').catch(()=>{})}
  },{times:1})
  await submit().click()
  await ui.expect.poll(()=>Boolean(first)||Boolean(lostError)).toBe(true)
  assert.equal(lostError,undefined,lostError)
  await ui.expect(reconcile()).toBeEnabled()
  const saved=await envelope(page)
  assert.equal(saved.length,1);assert.equal(saved[0].parsed.id,firstArgs.p_request)
  assert.deepEqual(saved[0].parsed.payload,{document:firstArgs.p_payload,expected_version:firstArgs.p_expected})
  await ui.expect(create()).toBeDisabled()
  if(otherButtons)for(const button of await otherButtons.all())await ui.expect(button).toBeDisabled()
  // Fresh DB connection proves actual COMMIT and all original exact oracles BEFORE delivery/recovery.
  const proof=fixture('verify',{fixture:f.fixture,serialized_fixture_sha256:f.serialized_fixture_sha256,args:firstArgs,outcome:first,quote:quotes.at(-1),quote_input:quoteInputs.at(-1)})
  assert.equal(proof.status,'PASS')
  return saved
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  await menu(ui,page)
  await page.getByLabel('Cari invoice',{exact:true}).fill(f.invoice.number)
  await page.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await page.locator('[aria-label="Daftar invoice"] .cproc-receipt').filter({hasText:f.invoice.number}).click()
  await detail().getByRole('button',{name:'Retur fisik invoice',exact:true}).click()
  await ui.expect(panel()).toBeVisible()
  const draft=f.query.return_payload
  await panel().getByLabel('Nomor retur pelanggan',{exact:true}).fill(draft.return_number)
  await panel().getByLabel('Waktu retur pelanggan WIB',{exact:true}).fill(f.return_local)
  await panel().getByLabel('Cari gudang retur',{exact:true}).fill(f.destination_name)
  const locationReply=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_sales_returns_v1')
   &&r.request().postDataJSON()?.p_query?.kind==='LOCATIONS')
  await panel().getByRole('button',{name:'Cari gudang retur',exact:true}).click()
  const locationsResponse=await locationReply;assert.equal(locationsResponse.status(),200)
  const locations=(await locationsResponse.json()).page.rows
  const locationIndex=locations.findIndex(row=>row.id===draft.items[0].location_id)
  assert.ok(locationIndex>=0,'Actual fixture destination must be on the actual loaded page')
  const locationButtons=panel().getByRole('region',{name:'Pilih gudang retur',exact:true}).locator('.cproc-receipt')
  await ui.expect(locationButtons).toHaveCount(locations.length)
  await locationButtons.nth(locationIndex).click()
  const allocation=panel().getByRole('region',{name:'Pilih alokasi retur',exact:true}).locator('.cproc-receipt')
  await ui.expect(allocation).toHaveCount(1);await allocation.click()
  await panel().getByLabel('Jumlah retur 1',{exact:true}).fill('1')
  await panel().getByLabel('Nilai retur 1',{exact:true}).fill('200.00')
  await panel().getByLabel('Catatan barang retur 1',{exact:true}).fill(draft.items[0].notes??'')
  await panel().getByLabel('Catatan retur pelanggan',{exact:true}).fill(draft.notes??'')
  await panel().getByLabel('Alasan tindakan retur',{exact:true}).fill(draft.change_reason)
  await section().getByLabel('Penyelesaian nilai retur',{exact:true}).selectOption(mode)
  await section().getByLabel('Cari akun saldo kredit pelanggan',{exact:true}).fill(f.credit.code)
  await section().getByRole('button',{name:'Cari akun saldo kredit pelanggan',exact:true}).click()
  await section().locator('[data-account-id="'+f.credit.id+'"]').click()
  if(mobile){
   const picker=section().getByRole('region',{name:'Rekening pengembalian uang',exact:true})
   await picker.getByRole('button',{name:'Cari rekening pengembalian uang',exact:true}).click()
   await picker.locator('[data-account-id="'+f.query.settlement.cash_account_id+'"]').click()
   await section().getByLabel('Waktu pengembalian uang WIB',{exact:true}).fill(f.refund_local)
   await section().getByLabel('Referensi pengembalian uang',{exact:true}).fill(f.query.settlement.reference)
  }
  await quote()
  if(kind==='EDIT'){
   const amount=panel().getByLabel('Nilai retur 1',{exact:true})
   await amount.fill('199.00');await ui.expect(result()).toHaveCount(0);await ui.expect(submit()).toBeDisabled()
   await amount.fill('200.00');await ui.expect(result()).toHaveCount(0);await ui.expect(submit()).toBeDisabled()
   assert.equal(requests.length,0);await quote();assert.equal(quotes.length,2)
  }
  if(kind==='LOST'||kind==='REVOKED'){
   other=await user.context.newPage();otherPages.push(other);await other.goto(ui.origin)
   otherButtons=await stockControls(ui,other,f)
   for(const button of await otherButtons.all())await ui.expect(button).toBeEnabled()
   const saved=await lost(),committed=fixture('snapshot');let replayBaseline=committed
   assert.equal(requests.length,1)
   if(kind==='LOST'){
    await page.reload();await menu(ui,page);assert.deepEqual(await envelope(page),saved)
    const response=await observed(page,reconcile());assert.equal(response.status(),200)
    assert.deepEqual(await response.json(),first)
   }else{
    fixture('revoke',{auth_user_id:user.user.id});revoked=true
    const baseline=fixture('snapshot'),response=await observed(page,reconcile())
    assert.equal(response.status(),403);assert.equal((await response.json()).message,'CP7_SALES_ACCESS_DENIED')
    assert.deepEqual(await envelope(page),saved);assert.deepEqual(fixture('snapshot'),baseline)
    await ui.expect(reconcile()).toBeEnabled();await ui.expect(create()).toBeDisabled()
    fixture('restore',{auth_user_id:user.user.id});revoked=false
    replayBaseline=fixture('snapshot')
    // The explicit administrative revoke/restore may advance app-user metadata;
    // retain the full post-restoration baseline rather than erase those facts.
    assert.deepEqual(replayBaseline.private,committed.private)
    assert.deepEqual(await envelope(page),saved)
    let abortedReads=0
    const readFailure=page.waitForEvent('requestfailed',{predicate:r=>r.url().endsWith('/rpc/erp_cp7_get_sales_v1')})
    await page.route(readEndpoint,route=>{abortedReads++;return route.abort('failed')})
    const recovered=await observed(page,reconcile());assert.equal(recovered.status(),200)
    assert.deepEqual(await recovered.json(),first)
    await readFailure
    assert.ok(abortedReads>0,'A real postcommit invoice read must reach the abort handler')
    await ui.expect.poll(()=>envelope(page)).toHaveLength(0)
    await ui.expect(page.getByText('Aksi sudah tersimpan, tetapi refresh authoritative gagal. Jangan ulangi aksi; seluruh writer terkunci sampai Refetch berhasil.',{exact:true})).toBeVisible()
    await ui.expect(create()).toBeDisabled();await assertNoStaleInvoiceFacts(ui,page)
    for(const button of await otherButtons.all())await ui.expect(button).toBeDisabled()
    await page.unroute(readEndpoint)
    const freshRead=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_sales_v1')&&r.request().postDataJSON()?.p_query?.sale_id===f.invoice.id)
    await page.getByRole('button',{name:'Muat ulang invoice',exact:true}).click()
    const freshResponse=await freshRead;assert.equal(freshResponse.status(),200)
    const fresh=await freshResponse.json();assert.equal(fresh.detail.row_version,first.row_version)
    assert.equal(fresh.detail.financial.paid_total,'800.00');assert.equal(fresh.detail.financial.open_balance,'0.00')
   }
   for(const request of requests)assert.deepEqual(request,firstArgs)
   assert.deepEqual(fixture('snapshot'),replayBaseline)
  }else{
   normalSaveStart=performance.now()
   const response=await observed(page,submit());assert.equal(response.status(),200)
   first=await response.json();firstArgs=response.request().postDataJSON()
  }
  await ui.expect(detail()).toContainText('Pelunasan efektif invoice Rp800')
  await ui.expect(detail()).toContainText('Sisa pembayaran Rp0')
  await ui.expect(reconcile()).toHaveCount(0);await ui.expect(create()).toBeEnabled()
  if(normalSaveStart!==null)timings.push({operation:'save_to_verified_authoritative_UI',milliseconds:performance.now()-normalSaveStart})
  assert.deepEqual(await envelope(page),[])
  const proof=fixture('verify',{fixture:f.fixture,serialized_fixture_sha256:f.serialized_fixture_sha256,args:firstArgs,outcome:first,quote:quotes.at(-1),quote_input:quoteInputs.at(-1)})
  assert.equal(proof.status,'PASS')
  assert.equal(requests.length,kind==='LOST'?2:kind==='REVOKED'?3:1)
  if(mobile)await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:'cp6-proof/t3/OW04_BROWSER_'+kind+'.png',fullPage:true})
  return{status:'PASS',real_Auth_and_Enteng_build_loopback:true,mode,mobile,request_count:requests.length,
   complete_request_UUID_document_version_recovery:kind==='LOST'||kind==='REVOKED',
   real_upstream_COMMIT_before_lost_reply:kind==='LOST'||kind==='REVOKED',
   positive_other_domain_controls_then_global_pending_lock:kind==='LOST'||kind==='REVOKED',
   actual_replay_revocation_and_failed_postcommit_reload_lock:kind==='REVOKED',
   quote_A_B_A_retires_review_requires_new_request:kind==='EDIT',
   strict_original_money_date_stock_HPP:proof,complete_UI_timings:timings,
   timing_scope:'Scoped initial settlement journeys; no whole ERP performance acceptance',production_go:false}
 }catch(error){
  writeFileSync('cp6-proof/t3/OW04_BROWSER_'+kind+'_FAILURE.json',JSON.stringify({
   error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),
   requests,quotes,quoteInputs,recovery:await envelope(page).catch(()=>null)},null,2))
  await page.screenshot({path:'cp6-proof/t3/OW04_BROWSER_'+kind+'_FAILURE.png',fullPage:true}).catch(()=>{})
  throw error
 }finally{
  if(revoked)fixture('restore',{auth_user_id:user.user.id})
  await page.unroute(endpoint).catch(()=>{});await page.unroute(readEndpoint).catch(()=>{})
  for(const other of otherPages)await other.close().catch(()=>{})
  await user.context.close()
 }
}
export function cases(ui,today){return[
 ['OW04_BROWSER_CREDIT_LOST_REPLY_DESKTOP',()=>journey(ui,today,'LOST')],
 ['OW04_BROWSER_REFUND_MOBILE',()=>journey(ui,today,'REFUND')],
 ['OW04_BROWSER_QUOTE_EDIT_FENCE',()=>journey(ui,today,'EDIT')],
 ['OW04_BROWSER_PENDING_REVOCATION_RELOAD_LOCK',()=>journey(ui,today,'REVOKED')]
]}
