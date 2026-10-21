import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const command='**/rest/v1/rpc/erp_cp7_customer_credit_command_v1'
const fixture=(op,args={})=>JSON.parse(execFileSync('python',['../auditor/scripts/ow04-consumer-ui-qualification/browser_fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const envelope=page=>page.evaluate(()=>Object.entries(localStorage).filter(([key])=>key.startsWith('erp.production.SALES.pending-mutation.v1:'))
 .map(([key,value])=>({key,value,parsed:JSON.parse(value)})))
async function menu(page,group='Penjualan',name='Retur Penjualan'){
 const toggle=page.getByRole('button',{name:'Buka menu',exact:true});if(await toggle.isVisible())await toggle.click()
 const button=page.getByRole('button',{name:'• '+name,exact:true})
 if(!await button.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:group}).click()
 await button.click()
}
async function otherWriter(ui,page,f){
 await menu(page,'Gudang','Stock Adjustment')
 await page.getByRole('navigation',{name:'Jenis persediaan'}).getByRole('button',{name:'Barang jadi',exact:true}).click()
 await page.getByLabel('Cari sumber penyesuaian FG',{exact:true}).fill(f.sku)
 await page.getByRole('button',{name:'Cari sumber FG',exact:true}).click()
 const controls=page.locator('.cfga .cfg-position').getByRole('button')
 await ui.expect.poll(()=>controls.count()).toBeGreaterThan(0)
 for(const button of await controls.all())await ui.expect(button).toBeEnabled()
 return controls
}
async function journey(ui,today,kind){
 const mobile=kind==='REFUND'||kind==='INITIAL_UNDO',action=kind==='REFUND'?'REFUND':kind==='INITIAL_UNDO'?'UNDO':'APPLY'
 const f=fixture('prepare',{today,action}),user=await ui.login('OWNER',{label:'ow04-consumer-'+kind.toLowerCase(),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,requests=[],reviews=[],reviewInputs=[],reads=[],otherPages=[],timings=[]
 const panel=()=>page.getByRole('region',{name:'Saldo kredit pelanggan',exact:true})
 const result=()=>page.getByRole('region',{name:'Pemeriksaan transaksi kredit',exact:true})
 const reconcile=()=>page.getByRole('button',{name:'Reconcile transaksi',exact:true})
 let outcome,args,proof,revoked=false,lostError,otherControls,saveStarted=null
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_customer_credit_command_v1'))requests.push(r.postDataJSON())})
 const verify=()=>fixture('verify',{fixture:f.fixture,fixture_sha256:f.fixture_sha256,args,outcome,actor:user.user.id,review:reviews.at(-1),review_input:reviewInputs.at(-1)})
 async function load(name,kind){
  const before=fixture('snapshot'),started=performance.now()
  const waiting=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_customer_credit_workspace_v1')&&r.request().postDataJSON().p_query.kind===kind)
  await panel().getByRole('button',{name,exact:true}).click();const response=await waiting
  assert.equal(response.status(),200,await response.text());const data=await response.json()
  assert.equal(data.kind,kind);assert.equal(data.actor_scope_id,user.user.id);assert.equal(data.read_only,true);assert.equal(data.business_DML,false)
  reads.push({query:response.request().postDataJSON().p_query,data})
  const marker={COHORTS:'data-credit-cohort-id',TARGETS:'data-credit-target-id',CASH:'data-credit-cash-id',EVENTS:'data-credit-event-id'}[kind]
  await ui.expect(panel().locator('['+marker+']')).toHaveCount(data.page.rows.length)
  const elapsed=performance.now()-started
  assert.deepEqual(fixture('snapshot'),before,'Actual workspace navigation performed business/private DML')
  timings.push({operation:'workspace_to_visible_'+kind,milliseconds:elapsed})
  return data
 }
 async function quote(){
  const before=fixture('snapshot'),started=performance.now()
  const waiting=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_get_customer_credit_review_v1'))
  await panel().getByRole('button',{name:'Periksa transaksi kredit',exact:true}).click();const response=await waiting
  assert.equal(response.status(),200,await response.text());const data=await response.json()
  reviews.push(data);reviewInputs.push(response.request().postDataJSON().p_payload)
  assert.equal(data.selection.action,action);assert.equal(data.selection.cohort_id,f.cohort_id)
  assert.equal(data.available_credit_after,action==='UNDO'?'200.00':'120.00')
  await ui.expect(result()).toBeVisible()
  await ui.expect(result()).toContainText('Saldo sesudah transaksi ini: Rp'+(action==='UNDO'?'200':'120'))
  await ui.expect(result()).toContainText('tanggal transaksi '+data.economic_date+' · tanggal buku '+data.transaction_date)
  timings.push({operation:'quote_to_visible_review',milliseconds:performance.now()-started})
  assert.deepEqual(fixture('snapshot'),before,'Actual consumer quote performed business/private DML')
  await result().getByLabel('Transaksi kredit sudah diperiksa',{exact:true}).check()
  await ui.expect(result().getByRole('button',{name:'Simpan transaksi kredit',exact:true})).toBeEnabled()
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await menu(page)
  await page.getByLabel('Cari invoice',{exact:true}).fill(f.source_number);await page.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await page.locator('[aria-label="Daftar invoice"] .cproc-receipt').filter({hasText:f.source_number}).click()
  await page.getByRole('complementary',{name:'Rincian invoice',exact:true}).getByRole('button',{name:'Saldo kredit pelanggan',exact:true}).click()
  await ui.expect(panel()).toBeVisible();await ui.expect(panel().getByLabel('Waktu transaksi saldo kredit WIB',{exact:true})).toHaveValue('')
  if(action==='UNDO'){
   const history=await load('Periksa riwayat kredit','EVENTS')
   const original=history.page.rows.find(r=>r.id===f.original_event_id)
   assert.ok(original);assert.equal(original.amount,'200.00');assert.equal(original.kind,'REFUND');assert.equal(original.undone_by,null)
   await panel().locator('[data-credit-event-id="'+f.original_event_id+'"]').getByRole('button').click()
  }else{
   const cohorts=await load('Periksa saldo dari retur','COHORTS')
   assert.equal(cohorts.page.rows.find(r=>r.id===f.cohort_id).available_credit,'200.00')
   await panel().locator('[data-credit-cohort-id="'+f.cohort_id+'"]').click()
   await panel().getByLabel('Tindakan saldo kredit',{exact:true}).selectOption(action)
   await panel().getByLabel('Nominal saldo kredit',{exact:true}).fill('80.00')
   if(action==='APPLY'){
    await panel().getByLabel('Cari invoice tujuan kredit',{exact:true}).fill(f.target_number)
    const targets=await load('Cari invoice tujuan kredit','TARGETS')
    assert.equal(targets.page.rows.find(r=>r.id===f.target_id).open_balance,'500.00')
    await panel().locator('[data-credit-target-id="'+f.target_id+'"]').click()
   }else{
    await panel().getByLabel('Cari rekening kredit',{exact:true}).fill(f.bank_code)
    const cash=await load('Cari rekening kredit','CASH')
    assert.ok(cash.page.rows.some(r=>r.id===f.bank_id));await panel().locator('[data-credit-cash-id="'+f.bank_id+'"]').click()
   }
  }
  await panel().getByLabel('Waktu transaksi saldo kredit WIB',{exact:true}).fill(f.physical_local)
  await panel().getByLabel('Alasan tindakan saldo kredit',{exact:true}).fill(f.prospective_payload.reason)
  await quote()
  if(kind==='LOST'){
   const amount=panel().getByLabel('Nominal saldo kredit',{exact:true})
   // A legitimate Native-sized amount must never lose its last cent in an
   // HTML maxlength. It exceeds this fixture's target, so no save is allowed.
   await amount.fill('999999999999999999.99');await ui.expect(amount).toHaveValue('999999999999999999.99')
   await ui.expect(result()).toHaveCount(0);await ui.expect(panel().getByRole('button',{name:'Periksa transaksi kredit',exact:true})).toBeDisabled()
   await panel().getByLabel('Nominal saldo kredit',{exact:true}).fill('81.00');await ui.expect(result()).toHaveCount(0)
   await panel().getByLabel('Nominal saldo kredit',{exact:true}).fill('80.00');await ui.expect(result()).toHaveCount(0)
   assert.equal(requests.length,0);await quote()
  }
  if(kind==='LOST'||kind==='REVOKED'){
   const other=await user.context.newPage();otherPages.push(other);await other.goto(ui.origin);otherControls=await otherWriter(ui,other,f)
   await page.route(command,async route=>{
    try{const response=await route.fetch();assert.equal(response.status(),200,await response.text());outcome=await response.json();args=route.request().postDataJSON();await route.abort('failed')}
    catch(error){lostError=String(error);await route.abort('failed').catch(()=>{})}
   },{times:1})
   await result().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click()
   await ui.expect.poll(()=>Boolean(outcome)||Boolean(lostError)).toBe(true);assert.equal(lostError,undefined,lostError)
   await ui.expect(reconcile()).toBeEnabled()
   const saved=await envelope(page);assert.equal(saved.length,1);assert.equal(saved[0].parsed.id,args.p_request)
   assert.equal(saved[0].parsed.action,'CREDIT_'+action)
   assert.deepEqual(saved[0].parsed.payload,{document:args.p_payload,review:reviews.at(-1)})
   await ui.expect(page.getByRole('button',{name:'Buat invoice',exact:true})).toBeDisabled()
   for(const button of await otherControls.all())await ui.expect(button).toBeDisabled()
   proof=verify();assert.equal(proof.status,'PASS') // Actual COMMIT before any delivery/reconciliation.
   if(kind==='REVOKED'){
    fixture('revoke',{auth_user_id:user.user.id});revoked=true
    const before=fixture('snapshot'),waiting=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_customer_credit_command_v1'))
    await reconcile().click();const response=await waiting;assert.equal(response.status(),403)
    assert.equal((await response.json()).message,'CP7_SALES_ACCESS_DENIED')
    assert.deepEqual(await envelope(page),saved);assert.deepEqual(fixture('snapshot'),before)
    fixture('restore',{auth_user_id:user.user.id});revoked=false
   }
   await page.reload();await menu(page);assert.deepEqual(await envelope(page),saved)
   const waiting=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_customer_credit_command_v1'))
   await reconcile().click();const response=await waiting;assert.equal(response.status(),200);assert.deepEqual(await response.json(),outcome)
   await ui.expect.poll(()=>envelope(page)).toEqual([])
   assert.equal(reviews.length,kind==='LOST'?2:1)
   for(const request of requests)assert.deepEqual(request,args)
   proof=verify();assert.equal(proof.status,'PASS')
  }else{
   saveStarted=performance.now();const waiting=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_customer_credit_command_v1'))
   await result().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click();const response=await waiting
   assert.equal(response.status(),200,await response.text());outcome=await response.json();args=response.request().postDataJSON()
   await ui.expect(panel()).toHaveCount(0);await ui.expect.poll(()=>envelope(page)).toEqual([])
   assert.equal(requests.length,1);proof=verify();assert.equal(proof.status,'PASS')
  }
  await ui.expect(page.getByRole('button',{name:'Saldo kredit pelanggan',exact:true})).toBeEnabled()
  if(saveStarted!==null)timings.push({operation:'save_to_authoritative_refreshed_UI_with_readback',milliseconds:performance.now()-saveStarted})
  await page.getByRole('button',{name:'Saldo kredit pelanggan',exact:true}).click()
  const fresh=await load('Periksa saldo dari retur','COHORTS')
  assert.equal(fresh.page.rows.find(r=>r.id===f.cohort_id).available_credit,action==='UNDO'?'200.00':'120.00')
  const history=await load('Periksa riwayat kredit','EVENTS')
  const savedEvent=history.page.rows.find(r=>r.id===outcome.consumption_event_id)
  assert.ok(savedEvent);assert.equal(savedEvent.amount,action==='UNDO'?'-200.00':'80.00')
  if(action==='UNDO')assert.equal(history.page.rows.find(r=>r.id===f.original_event_id).undone_by,savedEvent.id)
  if(mobile)await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:'cp6-proof/t3/CONSUMER_BROWSER_'+kind+'.png',fullPage:true})
  return {status:'PASS',real_Auth_product_build_loopback:true,product_responses_mocked:false,action,mobile,
   request_count:requests.length,lost_reply_after_actual_COMMIT:kind==='LOST'||kind==='REVOKED',
   exact_original_envelope_replayed_after_reload:kind==='LOST'||kind==='REVOKED',
   revoked_pending_replay_denied_without_clearing_envelope:kind==='REVOKED',
   other_domain_positive_controls_then_global_lock:kind==='LOST'||kind==='REVOKED',
   source_choices_from_fresh_pages_after_reload:true,proof,timings,
   timing_scope:'Bounded consumer journey only; no whole3600 money/HPP performance acceptance',production_go:false}
 }catch(error){
  writeFileSync('cp6-proof/t3/CONSUMER_BROWSER_'+kind+'_FAILURE.json',JSON.stringify({error:String(error),stack:error.stack,
   text:await page.locator('main').innerText().catch(()=>''),requests,reviews,reviewInputs,reads,recovery:await envelope(page).catch(()=>null)},null,2))
  await page.screenshot({path:'cp6-proof/t3/CONSUMER_BROWSER_'+kind+'_FAILURE.png',fullPage:true}).catch(()=>{})
  throw error
 }finally{
  if(revoked)fixture('restore',{auth_user_id:user.user.id})
  await page.unroute(command).catch(()=>{});for(const other of otherPages)await other.close().catch(()=>{})
  await user.context.close()
 }
}
export function cases(ui,today){return[
 ['OW04_CONSUMER_BROWSER_APPLY_LOST_REPLY_DESKTOP',()=>journey(ui,today,'LOST')],
 ['OW04_CONSUMER_BROWSER_REFUND_MOBILE',()=>journey(ui,today,'REFUND')],
 ['OW04_CONSUMER_BROWSER_INITIAL_REFUND_UNDO_MOBILE',()=>journey(ui,today,'INITIAL_UNDO')],
 ['OW04_CONSUMER_BROWSER_REVOKED_PENDING_REPLAY',()=>journey(ui,today,'REVOKED')],
]}
