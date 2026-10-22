import assert from 'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const helper=(file,op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/'+file,op],{cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const fixed=(op,p)=>helper('ow04-consumer-ui-qualification/browser_fixture.py',op,p)
const proof=(op,p)=>helper('ow04-payment-browser-races-qualification/browser_fixture.py',op,p)
const isRpc=name=>r=>r.url().endsWith('/rpc/'+name)
async function menu(page){
 const toggle=page.getByRole('button',{name:'Buka menu',exact:true});if(await toggle.isVisible())await toggle.click()
 const link=page.getByRole('button',{name:'• Pembayaran Pelanggan',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click()
}
async function journey(ui,today,action){
 const f=fixed('prepare',{today,action}),mobile=action==='REFUND'
 const user=await ui.login('OWNER',{label:'ow04-payment-current-'+action.toLowerCase(),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,credit=()=>page.getByRole('region',{name:'Saldo kredit pelanggan',exact:true})
 const review=()=>page.getByRole('region',{name:'Pemeriksaan transaksi kredit',exact:true}),requests=[]
 const correctionRpc='erp_cp7_correct_sales_payment_v1',creditRpc='erp_cp7_customer_credit_command_v1'
 const lostReplyTrace={route_started:false,response_parsed:false,reply_aborted:false}
 page.on('request',r=>{if(isRpc(correctionRpc)(r)||isRpc(creditRpc)(r))requests.push({rpc:r.url().split('/').at(-1),args:r.postDataJSON()})})
 const observed=(op,args,outcome)=>proof(op,{fixture:f.fixture,fixture_sha256:f.fixture_sha256,actor:user.user.id,args,outcome})
 async function source(){
  await menu(page);await page.getByLabel('Cari invoice',{exact:true}).fill(f.source_number)
  await page.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await page.locator('[aria-label="Daftar invoice"] .cproc-receipt').filter({hasText:f.source_number}).click()
 }
 async function spend(amount,balance){
  await page.getByRole('complementary',{name:'Rincian invoice',exact:true}).getByRole('button',{name:'Saldo kredit pelanggan',exact:true}).click()
  let waiting=page.waitForResponse(isRpc('erp_cp7_get_customer_credit_workspace_v1'))
  await credit().getByRole('button',{name:'Periksa saldo dari retur',exact:true}).click()
  let response=await waiting;assert.equal(response.status(),200,await response.text());let data=await response.json()
  assert.equal(data.page.rows.find(r=>r.id===f.cohort_id).available_credit,balance)
  await credit().locator('[data-credit-cohort-id="'+f.cohort_id+'"]').click()
  await credit().getByLabel('Tindakan saldo kredit',{exact:true}).selectOption(action)
  await credit().getByLabel('Nominal saldo kredit',{exact:true}).fill(amount)
  waiting=page.waitForResponse(isRpc('erp_cp7_get_customer_credit_workspace_v1'))
  if(action==='APPLY'){
   await credit().getByLabel('Cari invoice tujuan kredit',{exact:true}).fill(f.target_number)
   await credit().getByRole('button',{name:'Cari invoice tujuan kredit',exact:true}).click()
   response=await waiting;assert.equal(response.status(),200,await response.text())
   await credit().locator('[data-credit-target-id="'+f.target_id+'"]').click()
  }else{
   await credit().getByLabel('Cari rekening kredit',{exact:true}).fill(f.bank_code)
   await credit().getByRole('button',{name:'Cari rekening kredit',exact:true}).click()
   response=await waiting;assert.equal(response.status(),200,await response.text())
   await credit().locator('[data-credit-cash-id="'+f.bank_id+'"]').click()
  }
  await credit().getByLabel('Waktu transaksi saldo kredit WIB',{exact:true}).fill(f.physical_local)
  await credit().getByLabel('Alasan tindakan saldo kredit',{exact:true}).fill('Pemakaian saldo diperiksa setelah koreksi pembayaran sumber')
  waiting=page.waitForResponse(isRpc('erp_cp7_get_customer_credit_review_v1'))
  await credit().getByRole('button',{name:'Periksa transaksi kredit',exact:true}).click()
  response=await waiting;assert.equal(response.status(),200,await response.text())
  data=await response.json();assert.equal(data.available_credit_after,amount==='80.00'?'120.00':'0.00')
  await review().getByLabel('Transaksi kredit sudah diperiksa',{exact:true}).check()
  waiting=page.waitForResponse(isRpc(creditRpc));await review().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click()
  response=await waiting;assert.equal(response.status(),200,await response.text())
  return{args:response.request().postDataJSON(),outcome:await response.json()}
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await source()
  const first=await spend('80.00','200.00'),initial=observed('first80',first.args,first.outcome)
  await source();await page.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
  const payments=page.getByRole('region',{name:'Pembayaran invoice',exact:true})
  await payments.locator('[data-payment-id="'+initial.payment_id+'"]').getByRole('button',{name:'Edit pembayaran '+initial.payment_number,exact:true}).click()
  const form=page.getByRole('form',{name:'Edit pembayaran pelanggan',exact:true})
  await form.getByLabel('Nominal koreksi pembayaran',{exact:true}).fill('900.00')
  await form.getByLabel('Alasan koreksi pembayaran',{exact:true}).fill('Pembayaran sumber diperbaiki setelah pemakaian saldo kredit pelanggan')
  await form.getByLabel('Koreksi pembayaran sudah diperiksa',{exact:true}).check()
  let corrected,args,replyLostError
  const endpoint='**/rest/v1/rpc/'+correctionRpc
  if(!mobile){
   // Await the actual one-shot callback through fetch, parsed answer and lost
   // delivery. The product's eight-second UNKNOWN budget remains unchanged.
   // This bounded observation is not a two-second save/performance pass.
   let finishReply,timer
   const replyDone=new Promise(resolve=>{finishReply=resolve})
   await page.route(endpoint,async route=>{
    const started=performance.now();lostReplyTrace.route_started=true
    try{
     args=route.request().postDataJSON()
     const response=await route.fetch({timeout:30000,maxRetries:0})
     lostReplyTrace.response_status=response.status()
     assert.equal(response.status(),200,await response.text())
     corrected=await response.json();lostReplyTrace.response_parsed=true
    }catch(error){replyLostError=String(error)}
    finally{
     lostReplyTrace.fetch_elapsed_ms=performance.now()-started
     try{await route.abort('failed');lostReplyTrace.reply_aborted=true}
     catch(error){replyLostError??=String(error)}
     finishReply()
    }
   },{times:1})
   try{
    await form.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}).click()
    await Promise.race([replyDone,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('ACTUAL_CORRECTION_ROUTE_CALLBACK_NOT_COMPLETED_35S '+JSON.stringify(lostReplyTrace))),35000)})])
   }finally{clearTimeout(timer)}
   assert.equal(replyLostError,undefined,replyLostError);assert.ok(corrected);assert.ok(args)
   assert.equal(lostReplyTrace.reply_aborted,true)
   observed('correction',args,corrected)
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   await page.reload();await menu(page)
   const waiting=page.waitForResponse(isRpc(correctionRpc));await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
   const response=await waiting;assert.equal(response.status(),200,await response.text());assert.deepEqual(await response.json(),corrected);assert.deepEqual(response.request().postDataJSON(),args)
  }else{
   const waiting=page.waitForResponse(isRpc(correctionRpc));await form.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}).click()
   const response=await waiting;assert.equal(response.status(),200,await response.text());corrected=await response.json();args=response.request().postDataJSON()
  }
  const correctionProof=observed('correction',args,corrected)
  await source();const second=await spend('20.00','20.00'),final=observed('second20',second.args,second.outcome)
  assert.equal(requests.filter(x=>x.rpc===creditRpc).length,2)
  assert.equal(requests.filter(x=>x.rpc===correctionRpc).length,mobile?1:2)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await page.screenshot({path:'cp6-proof/t3/PAYMENT_CURRENT_'+action+'.png',fullPage:true})
  return{status:'PASS',mobile,actual_Auth_product_UI_C80_then_1000_to900_then_C20:true,all_business_writes_from_UI:true,
   original_payment_C80_journal_stock_HPP_retained:true,actual_committed_reply_lost_then_exact_replay:!mobile,
   correctionProof,final,lostReplyTrace,production_go:false}
 }catch(error){
  writeFileSync('cp6-proof/t3/PAYMENT_CURRENT_'+action+'_FAILURE.json',JSON.stringify({error:String(error),stack:error.stack,requests,lostReplyTrace,text:await page.locator('main').innerText().catch(()=> '')},null,2))
  await page.screenshot({path:'cp6-proof/t3/PAYMENT_CURRENT_'+action+'_FAILURE.png',fullPage:true}).catch(()=>{});throw error
 }finally{await user.context.close()}
}
export function cases(ui,today){return[
 ['OW04_PAYMENT_CURRENT_UI_APPLY80_CORRECT900_LOST_REPLY_APPLY20',()=>journey(ui,today,'APPLY')],
 ['OW04_PAYMENT_CURRENT_UI_MOBILE_REFUND80_CORRECT900_REFUND20',()=>journey(ui,today,'REFUND')],
]}
