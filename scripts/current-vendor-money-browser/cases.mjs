// A OW08b money page only; reuses existing CP6 host/login/navigation/public RPC.
// Prepared, no real browser claim until the exact complete backend11 is admitted.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readable } from './visual.mjs'
import { observeConsole, requireConsoleEvidence } from '../current-finance-combined-browser-qualification/console_evidence.mjs'

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
export const IDS=['VENDOR_MONEY_BROWSER_DESKTOP_REFUND_INVERSE_HISTORY','VENDOR_MONEY_BROWSER_MOBILE_REFUND_ACCESS_HIDDEN']
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['-B',resolve(ROOT,'scripts/current-vendor-money-browser/browser_fixture.py'),op],
 {input:JSON.stringify(payload),cwd:ROOT,encoding:'utf8',maxBuffer:4*1024*1024}).trim())
const money=v=>{const[w,f='']=v.split('.');return'Rp'+w.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+','+f.padEnd(2,'0')}

async function pricing(ui,user,vendor){
 const page=user.page,menu=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Laundry',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
 await link.click();await ui.expect(page.getByRole('heading',{name:'Laundry',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
 await ui.expect(page.getByRole('heading',{name:'Harga laundry dan invoice vendor',exact:true})).toBeVisible()
 await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
 if(vendor===null)return page.getByRole('region',{name:'Harga dan tagihan laundry',exact:true})
 await page.getByLabel('Vendor harga laundry',{exact:true}).selectOption(vendor)
 await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
 await page.getByRole('button',{name:'Pembayaran vendor',exact:true}).click()
 return page.getByRole('region',{name:'Pembayaran vendor laundry',exact:true})
}

async function journey(ui,today,mobile){
 const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'A-vendor-money-'+mobile,mobile}),page=user.page
 let f;const state=()=>fixture('state',f),shots=[],contrasts=[]
 const consoleCapture=observeConsole(page),expectedNetwork=[],refundRequests=[],lostReplyTrace={}
 const writeRpc='erp_save_laundry_bd_action_v1'
 const isRefund=request=>request.url().endsWith('/rest/v1/rpc/'+writeRpc)&&request.method()==='POST'&&request.postDataJSON()?.p_action==='RECEIVE_VENDOR_REFUND'
 const recordRequest=request=>{if(isRefund(request))refundRequests.push(request.postDataJSON())}
 page.on('request',recordRequest)
 const shot=async label=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/A_VENDOR_MONEY_${mobile?'MOBILE':'DESKTOP'}_${label}.png`;await page.screenshot({path,fullPage:true});shots.push(path)}
 try{
  f=fixture('prepare',{today})
  const box=await pricing(ui,user,f.fixture.vendor)
  const value=()=>box.locator('dl > div').filter({has:page.locator('dt').filter({hasText:/^Piutang ke vendor$/})}).locator('dd')
  await ui.expect(value()).toHaveText(money('3000.00').replace('Rp','Rp '))
  await ui.expect(box.getByRole('status')).toContainText('+ piutang ke vendor')
  const refund=box.getByRole('region',{name:'Pengembalian piutang vendor',exact:true}),amount=mobile?'750.10':'1000.25',remaining=mobile?'2249.90':'1999.75'
  await refund.getByLabel('Piutang vendor dikembalikan',{exact:true}).selectOption(f.credit_id)
  await refund.getByLabel('Rekening penerima pengembalian vendor',{exact:true}).selectOption(f.fixture.cash)
  await refund.getByLabel('Nominal pengembalian vendor',{exact:true}).fill(amount.replace('.',','))
  await refund.getByLabel('Tanggal pengembalian vendor',{exact:true}).fill(today)
  await refund.getByLabel('Alasan pengembalian vendor',{exact:true}).fill('Uang vendor diterima di bank lewat layar')
  const save=refund.getByRole('button',{name:'Catat uang diterima dari vendor',exact:true})
  if(mobile)await save.click()
  else{
   let finishReply,timer,replyError,args,committed
   const replyDone=new Promise(resolve=>{finishReply=resolve})
   await page.route('**/rest/v1/rpc/'+writeRpc,async route=>{
    const started=performance.now();lostReplyTrace.route_started=true
    try{
     assert.ok(isRefund(route.request()));args=route.request().postDataJSON()
     const response=await route.fetch({timeout:30000,maxRetries:0})
     lostReplyTrace.response_status=response.status();assert.equal(response.status(),200,await response.text())
     committed=await response.json();assert.equal(committed.refund_id,args.p_client_request_id)
     assert.equal(committed.amount,amount);assert.equal(committed.remaining,remaining)
     expectedNetwork.push({url:route.request().url(),text:'Failed to load resource: net::ERR_FAILED',reason:'Actual committed vendor refund response deliberately lost once'})
    }catch(error){replyError=String(error)}
    finally{
     lostReplyTrace.fetch_elapsed_ms=performance.now()-started
     try{await route.abort('failed');lostReplyTrace.reply_aborted=true}catch(error){replyError??=String(error)}
     finishReply()
    }
   },{times:1})
   try{
    await save.click()
    await Promise.race([replyDone,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('ACTUAL_VENDOR_REFUND_CALLBACK_NOT_COMPLETED_35S '+JSON.stringify(lostReplyTrace))),35000)})])
   }finally{clearTimeout(timer)}
   assert.equal(replyError,undefined,replyError);assert.ok(committed);assert.ok(args)
   await ui.expect(page.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()
   const committedState=state();assert.equal(committedState.refunds.length,1);assert.equal(committedState.refunds[0].id,args.p_client_request_id)
   assert.equal(committedState.ar,remaining);assert.equal(committedState.cash,amount)
   await page.reload();await pricing(ui,user,null)
   const responseDone=page.waitForResponse(response=>isRefund(response.request()))
   await page.getByRole('button',{name:'Reconcile transaksi',exact:true}).click()
   const response=await responseDone;assert.equal(response.status(),200,await response.text())
   const replay=await response.json();assert.deepEqual(response.request().postDataJSON(),args)
   assert.deepEqual(replay,{...committed,replayed:true});assert.deepEqual(state(),committedState)
   await ui.expect(page.getByLabel('Vendor harga laundry',{exact:true})).toBeEnabled()
   await page.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.fixture.vendor)
   await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
   await page.getByRole('button',{name:'Pembayaran vendor',exact:true}).click()
   lostReplyTrace.exact_same_UUID_and_payload_after_reload=true
   lostReplyTrace.committed=committed;lostReplyTrace.replay=replay
   lostReplyTrace.one_refund_and_unchanged_money_after_replay=true
  }
  await ui.expect.poll(()=>state().ar,{timeout:20000}).toBe(remaining)
  await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
  const after=state();assert.equal(after.cash,amount);assert.equal(after.refunds.length,1);assert.equal(after.refunds[0].amount,amount);assert.deepEqual(after.origin,f.before.origin);assert.equal(after.ledger.matches,true)
  await ui.expect(value()).toHaveText(money(remaining).replace('Rp','Rp '))
  const row=refund.getByRole('table',{name:'Riwayat pengembalian vendor',exact:true}).locator('tbody tr').filter({hasText:f.credit_number})
  await ui.expect(row).toContainText('Diposting');contrasts.push({state:'REFUND',rows:await readable(box)});await shot('REFUND')
  let final,revocation=null
  if(mobile){
   revocation=fixture('revoke',{actor:user.user.id})
   await page.getByRole('button',{name:'Muat ulang harga',exact:true}).click()
   await ui.expect(page.getByText('Hak melihat nominal diperlukan untuk pembayaran vendor.',{exact:true})).toBeVisible()
   await ui.expect(page.getByRole('region',{name:'Pengembalian piutang vendor',exact:true})).not.toBeVisible()
   await ui.expect(box).not.toBeVisible();final=state();assert.deepEqual(final,after);await shot('ACCESS_HIDDEN')
  }else{
   await refund.getByLabel('Alasan pembatalan pengembalian vendor',{exact:true}).fill('Batal bukti penerimaan salah dari layar')
   await refund.getByRole('button',{name:'Batalkan pengembalian '+f.credit_number,exact:true}).click()
   await ui.expect.poll(()=>state().ar,{timeout:20000}).toBe('3000.00')
   await ui.expect(page.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
   final=state();assert.equal(final.cash,'0.00');assert.equal(final.refunds.length,1);assert.equal(final.refunds[0].status,'REVERSED');assert.deepEqual(final.origin,f.before.origin);assert.equal(final.ledger.matches,true)
   await ui.expect(row).toContainText('Dibatalkan');contrasts.push({state:'INVERSE',rows:await readable(box)});await shot('INVERSE')
  }
  const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));assert.ok(width.page<=width.viewport,JSON.stringify(width))
  assert.equal(refundRequests.length,mobile?1:2)
  if(!mobile)assert.deepEqual(refundRequests[0],refundRequests[1])
  const consoleEvidence=requireConsoleEvidence(consoleCapture.errors,expectedNetwork)
  return{status:'PASS',console_evidence:consoleEvidence,lost_reply_trace:lostReplyTrace,refund_requests:refundRequests,actual_Auth_login_and_public_RPC:true,actual_refund_posted_from_screen:true,actual_refund_inverse_from_screen:!mobile,actual_access_revoked_and_money_hidden:mobile,
   before:f.before,after,final,revocation,width,shots,visible_text_contrasts:contrasts,fixture_source:f.fixture_source,
   invoice_and_credit_creation_from_screen_claim:false,actual_committed_reply_lost_reload_same_UUID_once:!mobile,B_combined_analysis_browser_repeated:false,production_go:false}
 }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/A_VENDOR_MONEY_${mobile?'MOBILE':'DESKTOP'}_FIRST_FAILURE.json`,JSON.stringify({error:String(error),lost_reply_trace:lostReplyTrace,refund_requests:refundRequests,console_errors:consoleCapture.errors,expected_network_errors:expectedNetwork,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
 finally{consoleCapture.stop();page.off('request',recordRequest);await user.context.close()}
}

export async function cases(ui,today){return IDS.map((key,i)=>[key,()=>journey(ui,today,Boolean(i))])}
