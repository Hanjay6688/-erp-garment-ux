import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_supplier_payment_create_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const endpoint='**/rest/v1/rpc/erp_cp7_create_supplier_payment_v1'
async function procurementMenu(page){const open=page.getByRole('button',{name:'Buka menu',exact:true});if(await open.isVisible())await open.click();const link=page.getByRole('button',{name:'• Pembelian & Penerimaan',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function observed(page,button){const pending=page.waitForResponse(r=>r.url().endsWith('/rpc/erp_cp7_create_supplier_payment_v1'));await button.click();return pending}
async function journey(ui,today,mobile){
 const f=fixture('prepare',{today}),user=await ui.login('OWNER',{label:'supplier-payment-create-'+mobile,mobile,timezoneId:'America/Los_Angeles'}),page=user.page,suffix=mobile?'MOBILE':'DESKTOP',requests=[]
 const state=()=>fixture('state',{fixture:f.fixture}),panel=()=>page.getByRole('region',{name:'Pembayaran supplier',exact:true}),entry=()=>page.getByRole('region',{name:'Catat pembayaran supplier baru',exact:true}),form=()=>page.getByRole('form',{name:'Pembayaran supplier baru',exact:true})
 page.on('request',r=>{if(/\/rpc\/erp_cp7_create_supplier_payment_v1$/.test(r.url()))requests.push({url:r.url(),body:r.postDataJSON()})})
 async function open(){await procurementMenu(page);await page.getByLabel('Cari penerimaan',{exact:true}).fill(f.number);await page.getByRole('button',{name:'Cari penerimaan',exact:true}).click()
  await page.locator('button.cproc-receipt').filter({hasText:f.number}).click();await ui.expect(panel()).toContainText(f.number)}
 try{
  mkdirSync('cp6-proof/t3',{recursive:true});await open();const before=state();assert.equal(before.remaining,'1000.00');assert.equal(before.state.requests,0)
  await panel().getByRole('button',{name:`Bayar supplier ${f.number}`,exact:true}).click();await ui.expect(entry()).toContainText('Sisa utang sekarang Rp1.000')
  await form().getByLabel('Nominal pembayaran supplier baru',{exact:true}).fill('250')
  await form().getByLabel('Cari rekening pembayaran supplier baru',{exact:true}).fill(f.bank_code);await form().getByRole('button',{name:'Cari rekening pembayaran supplier',exact:true}).click()
  await form().getByRole('button',{name:`${f.bank_code} · ${f.bank_name}`,exact:true}).click();await form().getByLabel('Keterangan pembayaran supplier baru',{exact:true}).fill('Transfer bank sebagian untuk penerimaan ini')
  await ui.expect(entry()).toContainText('sesudah bayar Rp750');const save=form().getByRole('button',{name:'Sahkan pembayaran supplier',exact:true});await ui.expect(save).toBeDisabled()
  await form().getByLabel('Pembayaran supplier baru sudah diperiksa',{exact:true}).check();await ui.expect(save).toBeEnabled()
  let first
  if(!mobile){let intercepted;await page.route(endpoint,async route=>{try{const r=await route.fetch();intercepted={status:r.status()};if(r.status()===200){first=await r.json();await route.abort('failed')}else await route.fulfill({response:r})}catch(error){intercepted={error:String(error)};await route.abort('failed')}})
   await save.click();await ui.expect.poll(()=>intercepted!==undefined).toBe(true);assert.equal(intercepted.status,200,JSON.stringify(intercepted))
   await ui.expect(panel().getByRole('button',{name:'Periksa status pembatalan supplier',exact:true})).toBeEnabled();assert.equal(state().state.requests,1)
   const request=structuredClone(requests[0].body);await page.unroute(endpoint);await page.reload();await procurementMenu(page)
   const response=await observed(page,panel().getByRole('button',{name:'Periksa status pembatalan supplier',exact:true}));assert.equal(response.status(),200);assert.deepEqual(await response.json(),first);assert.deepEqual(requests[1].body,request)
  }else{const response=await observed(page,save);assert.equal(response.status(),200);first=await response.json()}
  assert.equal(first.remaining_after,'750.00');assert.equal(first.amount,'250.00')
  await ui.expect(panel()).toContainText('Rp750');const after=state()
  assert.equal(after.remaining,'750.00');assert.equal(after.paid,'250.00');assert.equal(after.cash_delta,'-250.00');assert.equal(after.state.requests,1);assert.equal(after.payments.length,1)
  assert.deepEqual(after.payments[0],{amount:'250.00',status:'POSTED',notes:'Transfer bank sebagian untuk penerimaan ini'});assert.equal(new Set(requests.map(r=>r.body.p_request)).size,1)
  await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:`cp6-proof/t3/CP7_SUPPLIER_PAYMENT_CREATE_${suffix}.png`,fullPage:true})
  return{status:'PASS',mobile,actual_Auth_owner_pays_250_of_1000:true,one_backend_command_one_UUID:true,actual_lost_committed_reply_exact_UUID_recovery:!mobile,Native_AP_cash_and_note_exact:true,no_horizontal_overflow:true}
 }catch(error){writeFileSync(`cp6-proof/t3/CP7_SUPPLIER_PAYMENT_CREATE_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,text:await page.locator('main').innerText().catch(()=>''),state:state(),requests},null,2));await page.screenshot({path:`cp6-proof/t3/CP7_SUPPLIER_PAYMENT_CREATE_${suffix}_FAILURE.png`,fullPage:true}).catch(()=>{});throw error}
 finally{await page.unroute(endpoint).catch(()=>{});await user.context.close()}
}
export function cases(ui,today){return[['CP7_SUPPLIER_PAYMENT_CREATE_BROWSER_DESKTOP',()=>journey(ui,today,false)],['CP7_SUPPLIER_PAYMENT_CREATE_BROWSER_MOBILE',()=>journey(ui,today,true)]]}
