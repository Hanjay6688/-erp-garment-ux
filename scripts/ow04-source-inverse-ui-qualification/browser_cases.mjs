import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const rpc=(name,action)=>r=>r.url().endsWith('/rpc/'+name)&&(!action||r.request().postDataJSON().p_action===action)
const helper=(file,op,args)=>JSON.parse(execFileSync('python',['../auditor/scripts/'+file,op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const fixed=(op,args)=>helper('ow04-consumer-ui-qualification/browser_fixture.py',op,args)
const proof=(op,args)=>helper('ow04-source-inverse-ui-qualification/source_fixture.py',op,args)

async function journey(ui,today){
 const f=fixed('prepare',{today,action:'UNDO'})
 const user=await ui.login('OWNER',{label:'ow04-consumer-source-inverse',mobile:true,timezoneId:'America/Los_Angeles'})
 const page=user.page,sourceArgs={fixture:f.fixture,fixture_sha256:f.fixture_sha256},writes=[]
 const credit=()=>page.getByRole('region',{name:'Saldo kredit pelanggan',exact:true})
 const returns=()=>page.getByRole('region',{name:'Retur fisik invoice',exact:true})
 const review=()=>page.getByRole('region',{name:'Pemeriksaan transaksi kredit',exact:true})
 page.on('request',r=>{if(r.url().endsWith('/rpc/erp_cp7_save_sale_v1')||r.url().endsWith('/rpc/erp_cp7_customer_credit_command_v1'))writes.push(r.postDataJSON())})
 async function source(){
  await page.getByLabel('Cari invoice',{exact:true}).fill(f.source_number)
  await page.getByRole('button',{name:'Cari invoice',exact:true}).click()
  await page.locator('[aria-label="Daftar invoice"] .cproc-receipt').filter({hasText:f.source_number}).click()
  await ui.expect(page.getByRole('button',{name:'Saldo kredit pelanggan',exact:true})).toBeEnabled()
 }
 async function dependencies(total){
  const response=page.waitForResponse(rpc('erp_cp7_get_sales_credit_dependencies_v1'))
  await page.getByRole('button',{name:'Lihat penggunaan saldo kredit',exact:true}).click()
  const r=await response;assert.equal(r.status(),200,await r.text())
  const data=await r.json();assert.equal(data.page.total,total);assert.equal(data.read_only,true);assert.equal(data.business_DML,false)
  return data
 }
 async function reverse(initial){
  if(await returns().count()===0)await page.getByRole('button',{name:'Retur fisik invoice',exact:true}).click()
  await returns().locator('[data-return-id="'+initial.return_id+'"]').getByRole('button',{name:'Koreksi retur '+initial.return_number,exact:true}).click()
  await ui.expect(returns()).toContainText('Periksa riwayat kredit')
  await returns().getByLabel('Alasan tindakan retur',{exact:true}).fill('Pembatalan retur asal setelah pengembalian uang diperiksa')
  await returns().getByLabel('Retur pelanggan sudah diperiksa',{exact:true}).check()
  const response=page.waitForResponse(rpc('erp_cp7_save_sale_v1','RETURN_REVERSE'))
  await returns().getByRole('button',{name:'Batalkan retur tercatat',exact:true}).click()
  return await response
 }
 try{
  const toggle=page.getByRole('button',{name:'Buka menu',exact:true});if(await toggle.isVisible())await toggle.click()
  const menu=page.getByRole('button',{name:'• Retur Penjualan',exact:true})
  if(!await menu.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
  await menu.click();await source()
  const initial=proof('initial',sourceArgs)
  const before=await dependencies('1');assert.equal(before.dependencies[0].event_id,f.original_event_id)
  await ui.expect(page.getByRole('list',{name:'Langkah membatalkan penggunaan saldo kredit'})).toBeVisible()
  await page.getByRole('button',{name:'Buka retur asal '+initial.return_number,exact:true}).click()
  await ui.expect(returns()).toBeVisible()
  const denied=await reverse(initial)
  assert.equal(denied.status(),400)
  assert.equal((await denied.json()).message,'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO')
  await ui.expect(page.getByRole('alert').filter({hasText:'Saldo kredit pelanggan → Periksa riwayat kredit'}).first()).toBeVisible()
  const blocked=proof('blocked',{...sourceArgs,initial_sha256:initial.initial_sha256});assert.equal(blocked.status,'PASS')
  await returns().getByRole('button',{name:'Tutup retur invoice',exact:true}).click()
  await source()
  await page.getByRole('button',{name:'Saldo kredit pelanggan',exact:true}).click()
  await ui.expect(credit().getByLabel('Waktu transaksi saldo kredit WIB',{exact:true})).toHaveValue('')
  await credit().getByRole('button',{name:'Periksa riwayat kredit',exact:true}).click()
  await credit().locator('[data-credit-event-id="'+f.original_event_id+'"]').getByRole('button',{name:'Periksa pembatalan pengembalian uang '+initial.return_number,exact:true}).click()
  await credit().getByLabel('Waktu transaksi saldo kredit WIB',{exact:true}).fill(f.physical_local)
  await credit().getByLabel('Alasan tindakan saldo kredit',{exact:true}).fill(f.prospective_payload.reason)
  const quoteResponse=page.waitForResponse(rpc('erp_cp7_get_customer_credit_review_v1'))
  await credit().getByRole('button',{name:'Periksa transaksi kredit',exact:true}).click()
  const quoted=await quoteResponse;assert.equal(quoted.status(),200,await quoted.text());const quote=await quoted.json()
  assert.equal(quote.selection.amount,'-200.00');assert.equal(quote.selection.restores_event_id,f.original_event_id)
  await review().getByLabel('Transaksi kredit sudah diperiksa',{exact:true}).check()
  const undoResponse=page.waitForResponse(rpc('erp_cp7_customer_credit_command_v1'))
  await review().getByRole('button',{name:'Simpan transaksi kredit',exact:true}).click()
  const undoneResponse=await undoResponse;assert.equal(undoneResponse.status(),200,await undoneResponse.text())
  const undoneOutcome=await undoneResponse.json()
  await ui.expect(credit()).toHaveCount(0)
  const undo=fixed('verify',{...sourceArgs,args:undoneResponse.request().postDataJSON(),outcome:undoneOutcome,
   actor:user.user.id,review:quote,review_input:quoted.request().postDataJSON().p_payload})
  assert.equal(undo.status,'PASS')
  const seal=proof('undone',sourceArgs);assert.equal(seal.status,'PASS')
  await source();await dependencies('0')
  await ui.expect(page.getByRole('list',{name:'Langkah membatalkan penggunaan saldo kredit'})).toHaveCount(0)
  const accepted=await reverse(initial);assert.equal(accepted.status(),200,await accepted.text())
  const acceptedOutcome=await accepted.json()
  await ui.expect(returns()).toHaveCount(0)
  const final=proof('verify_inverse',{...sourceArgs,undone_sha256:seal.undone_sha256,args:accepted.request().postDataJSON(),outcome:acceptedOutcome,actor:user.user.id})
  assert.equal(final.status,'PASS')
  await source();await dependencies('0')
  await page.getByRole('button',{name:'Retur fisik invoice',exact:true}).click()
  await ui.expect(returns().locator('[data-return-id="'+initial.return_id+'"]')).toContainText(initial.return_number+' · Dibatalkan')
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  assert.equal(writes.length,3)
  assert.equal(writes.filter(x=>x.p_action==='RETURN_REVERSE').length,2)
  mkdirSync('cp6-proof/t3',{recursive:true})
  await page.screenshot({path:'cp6-proof/t3/SOURCE_REFUND_UNDO_RETURN_REVERSE_MOBILE.png',fullPage:true})
  return{status:'PASS',actual_product_browser_Auth:true,product_responses_mocked:false,
   active_dependency_guidance_then_real_source_refusal:true,full_refusal_state_unchanged:true,
   named_original_refund_undo_from_history:true,dependency_empty_only_after_actual_undo:true,
   source_return_inverse_retried_and_committed_from_UI:true,final,production_go:false}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true})
  writeFileSync('cp6-proof/t3/SOURCE_INVERSE_UI_FAILURE.json',JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),writes},null,2))
  await page.screenshot({path:'cp6-proof/t3/SOURCE_INVERSE_UI_FAILURE.png',fullPage:true}).catch(()=>{})
  throw error
 }finally{await user.context.close()}
}

export function cases(ui,today){return[
 ['OW04_SOURCE_REFUND_UNDO_RETURN_REVERSE_MOBILE',()=>journey(ui,today)],
]}
