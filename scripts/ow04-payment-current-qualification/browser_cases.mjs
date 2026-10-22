import assert from 'node:assert/strict'
import{execFileSync}from'node:child_process'
import{mkdirSync,writeFileSync}from'node:fs'
const helper=(file,op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/'+file,op],{cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const fixed=(op,p)=>helper('ow04-consumer-ui-qualification/browser_fixture.py',op,p)
const proof=(op,p)=>helper('ow04-payment-browser-races-qualification/browser_fixture.py',op,p)
const restoredProof=(op,p)=>helper('ow04-payment-current-qualification/browser_restore_fixture.py',op,p)
const isRpc=name=>r=>r.url().endsWith('/rpc/'+name)
async function menu(page){
 const toggle=page.getByRole('button',{name:'Buka menu',exact:true});if(await toggle.isVisible())await toggle.click()
 const link=page.getByRole('button',{name:'• Pembayaran Pelanggan',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click()
}
async function journey(ui,today,action,restore=false){
 const f=fixed('prepare',{today,action}),mobile=action==='REFUND'
 const user=await ui.login('OWNER',{label:'ow04-payment-current-'+action.toLowerCase()+(restore?'-restore':'-down'),mobile,timezoneId:'America/Los_Angeles'})
 const page=user.page,credit=()=>page.getByRole('region',{name:'Saldo kredit pelanggan',exact:true})
 const review=()=>page.getByRole('region',{name:'Pemeriksaan transaksi kredit',exact:true}),requests=[]
 const correctionRpc='erp_cp7_correct_sales_payment_v1',creditRpc='erp_cp7_customer_credit_command_v1'
 const lostReplyTrace={route_started:false,response_parsed:false,reply_aborted:false}
 const secondReplyTrace={route_started:false,response_parsed:false,reply_aborted:false}
 const journeyProgress={}
 const restoreTrace={route_started:false,response_parsed:false,reply_aborted:false}
 let functionProfile
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
  if(!mobile&&amount==='20.00'){
   // Observe the actual slow command through completion, lose that reply,
   // then use the product's exact UUID recovery. No response body is mocked.
   const before=helper('ow04-payment-current-qualification/function_stats.py','snapshot',{})
   let completed,commandArgs,commandError,finish,timer
   const done=new Promise(resolve=>{finish=resolve})
   await page.route('**/rest/v1/rpc/'+creditRpc,async route=>{
    const started=performance.now();secondReplyTrace.route_started=true
    try{
     commandArgs=route.request().postDataJSON()
     const response=await route.fetch({timeout:60000,maxRetries:0});secondReplyTrace.response_status=response.status()
     assert.equal(response.status(),200,await response.text());completed=await response.json();secondReplyTrace.response_parsed=true
    }catch(error){commandError=String(error).split('\n')[0]}
    finally{
     secondReplyTrace.fetch_elapsed_ms=performance.now()-started
     try{await route.abort('failed');secondReplyTrace.reply_aborted=true}catch(error){commandError??=String(error)}
     finish()
    }
   },{times:1})
   try{
    await review().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click()
    await Promise.race([done,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('ACTUAL_CONSUMER20_CALLBACK_NOT_COMPLETED_65S '+JSON.stringify(secondReplyTrace))),65000)})])
   }finally{
    clearTimeout(timer)
    await new Promise(resolve=>setTimeout(resolve,1100))
    const after=helper('ow04-payment-current-qualification/function_stats.py','snapshot',{})
    const deltas=Object.entries(after.functions).map(([name,row])=>{
     const prev=before.functions[name]??{calls:0,total_ms:0,self_ms:0}
     return{name,calls:row.calls-prev.calls,total_ms:row.total_ms-prev.total_ms,self_ms:row.self_ms-prev.self_ms}
    }).filter(row=>row.calls>0)
    functionProfile={diagnostic_only:true,application_latency_acceptance:false,includes_concurrent_background_requests:true,
     track_functions_before:before.track_functions,track_functions_after:after.track_functions,
     top_self:deltas.sort((a,b)=>b.self_ms-a.self_ms).slice(0,40),top_total:[...deltas].sort((a,b)=>b.total_ms-a.total_ms).slice(0,20)}
   }
   assert.equal(commandError,undefined,commandError);assert.ok(completed);assert.ok(commandArgs)
   observed('second20',commandArgs,completed)
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   await page.reload();await menu(page)
   waiting=page.waitForResponse(isRpc(creditRpc),{timeout:60000})
   await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
   const response=await waiting;assert.equal(response.status(),200,await response.text())
   assert.deepEqual(await response.json(),completed);assert.deepEqual(response.request().postDataJSON(),commandArgs)
   return{args:commandArgs,outcome:completed}
  }
  waiting=page.waitForResponse(isRpc(creditRpc));await review().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click()
  response=await waiting;assert.equal(response.status(),200,await response.text())
  return{args:response.request().postDataJSON(),outcome:await response.json()}
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await source()
  const first=await spend('80.00','200.00'),initial=observed('first80',first.args,first.outcome)
  journeyProgress.first80={...first,proof:initial}
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
    }catch(error){replyLostError=String(error).split('\n')[0]}
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
  journeyProgress.correction={args,outcome:corrected,proof:correctionProof,exact_replay_completed:!mobile}
  await source();const second=await spend('20.00','20.00');let final=observed('second20',second.args,second.outcome)
  if(restore){
   const proofArgs={fixture:f.fixture,fixture_sha256:f.fixture_sha256,actor:user.user.id}
   restoredProof('capture900',{...proofArgs,args,outcome:corrected})
   await source();await page.getByRole('button',{name:'Pembayaran invoice',exact:true}).click()
   const row=page.getByRole('region',{name:'Pembayaran invoice',exact:true}).locator('[data-payment-id="'+corrected.payment_id+'"]')
   await row.getByRole('button',{name:/^Edit pembayaran /}).click()
   const edit=page.getByRole('form',{name:'Edit pembayaran pelanggan',exact:true})
   await page.getByRole('button',{name:'Pulihkan isi pembayaran sebelum koreksi',exact:true}).click()
   await ui.expect(edit.getByLabel('Nominal koreksi pembayaran',{exact:true})).toHaveValue('1000.00')
   await edit.getByLabel('Alasan koreksi pembayaran',{exact:true}).fill('Pembayaran sumber dipulihkan setelah saldo dan bukti pembayaran diperiksa')
   await edit.getByLabel('Koreksi pembayaran sudah diperiksa',{exact:true}).check()
   let restored,restoreArgs,restoreError,finish,timer
   const done=new Promise(resolve=>{finish=resolve})
   await page.route(endpoint,async route=>{
    const start=performance.now();restoreTrace.route_started=true
    try{restoreArgs=route.request().postDataJSON();const response=await route.fetch({timeout:60000,maxRetries:0});restoreTrace.response_status=response.status();assert.equal(response.status(),200,await response.text());restored=await response.json();restoreTrace.response_parsed=true}
    catch(error){restoreError=String(error).split('\n')[0]}
    finally{restoreTrace.fetch_elapsed_ms=performance.now()-start;try{await route.abort('failed');restoreTrace.reply_aborted=true}catch(error){restoreError??=String(error).split('\n')[0]}finish()}
   },{times:1})
   try{await edit.getByRole('button',{name:'Simpan koreksi pembayaran',exact:true}).click();await Promise.race([done,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('ACTUAL_RESTORE1000_CALLBACK_NOT_COMPLETED_65S '+JSON.stringify(restoreTrace))),65000)})])}finally{clearTimeout(timer)}
   assert.equal(restoreError,undefined,restoreError);assert.ok(restored);assert.ok(restoreArgs)
   final=restoredProof('restored1000',{...proofArgs,args:restoreArgs,outcome:restored})
   journeyProgress.restoration={args:restoreArgs,outcome:restored,proof:final}
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   await page.reload();await menu(page)
   const waiting=page.waitForResponse(isRpc(correctionRpc),{timeout:60000});await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
   const response=await waiting;assert.equal(response.status(),200,await response.text());assert.deepEqual(await response.json(),restored);assert.deepEqual(response.request().postDataJSON(),restoreArgs)
   final=restoredProof('restored1000',{...proofArgs,args:restoreArgs,outcome:restored});journeyProgress.restoration.exact_replay_completed=true
  }
  assert.equal(requests.filter(x=>x.rpc===creditRpc).length,mobile?2:3)
  assert.equal(requests.filter(x=>x.rpc===correctionRpc).length,(mobile?1:2)+(restore?2:0))
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  await page.screenshot({path:'cp6-proof/t3/PAYMENT_CURRENT_'+action+(restore?'_RESTORE':'')+'.png',fullPage:true})
  return{status:'PASS',mobile,actual_Auth_product_UI_C80_then_1000_to900_then_C20:true,all_business_writes_from_UI:true,
   original_payment_C80_journal_stock_HPP_retained:true,actual_committed_reply_lost_then_exact_replay:!mobile,
   correctionProof,final,lostReplyTrace,secondReplyTrace,restoreTrace,functionProfile,actual_UI_restore1000:restore,
   additional_consumer20_actual_commit_lost_reply_exact_UI_replay:!mobile,production_go:false}
 }catch(error){
  writeFileSync('cp6-proof/t3/PAYMENT_CURRENT_'+action+(restore?'_RESTORE':'')+'_FAILURE.json',JSON.stringify({error:String(error),stack:error.stack,requests,lostReplyTrace,secondReplyTrace,restoreTrace,functionProfile,journeyProgress,text:await page.locator('main').innerText().catch(()=> '')},null,2))
  await page.screenshot({path:'cp6-proof/t3/PAYMENT_CURRENT_'+action+(restore?'_RESTORE':'')+'_FAILURE.png',fullPage:true}).catch(()=>{});throw error
 }finally{await user.context.close()}
}
export function cases(ui,today){return[
 ['OW04_PAYMENT_CURRENT_UI_APPLY80_CORRECT900_LOST_REPLY_APPLY20',()=>journey(ui,today,'APPLY')],
 ['OW04_PAYMENT_CURRENT_UI_MOBILE_REFUND80_CORRECT900_REFUND20',()=>journey(ui,today,'REFUND')],
]}

export function positiveCases(ui,today){return[
 ['OW04_CURRENT_UI_APPLY100_RESTORE1000_LOST_REPLY',()=>journey(ui,today,'APPLY',true)],
 ['OW04_CURRENT_UI_MOBILE_REFUND100_RESTORE1000_LOST_REPLY',()=>journey(ui,today,'REFUND',true)],
]}
