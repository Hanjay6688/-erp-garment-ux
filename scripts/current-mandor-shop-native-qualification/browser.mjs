// Normal App, actual Auth and actual public RPC. No mocked successful response.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {randomUUID} from 'node:crypto'
import {mkdirSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {observeConsole,requireConsoleEvidence,readable,cents} from '../current-sku-pair-browser-qualification/evidence.mjs'
import {observeResponseWaits} from '../current-s03-sku-s05-composite-qualification/response_waits.mjs'

export const IDS=[
 'MANDOR_BROWSER_DESKTOP_NORMAL_PAYROLL_LOST_REPLY_SAME_UUID_TWO_TABS_RELEASE',
 'MANDOR_BROWSER_MOBILE390_NORMAL_PAYROLL_STALE_INPUT_FRESH_READ_RELEASE',
]
const HERE=dirname(fileURLToPath(import.meta.url)),ROOT=resolve(HERE,'../..')
const READ='erp_cp7_get_mandor_shop_payroll_v1',WRITE='erp_cp7_save_mandor_shop_allocation_v1'
const PAYROLL='erp_cp7_get_payroll_workspace_v1'
const panel=page=>page.getByRole('region',{name:'Tagihan belanja mandor',exact:true})
const dialog=page=>page.getByRole('dialog',{name:'Pasang tagihan belanja',exact:true})
const amount=page=>dialog(page).getByLabel('Nominal potongan belanja',{exact:true})
const reviewed=page=>dialog(page).getByRole('checkbox',{name:'Saya sudah memeriksa nota, nominal, mandor, dan minggu payroll.',exact:true})
const reserve=page=>dialog(page).getByRole('button',{name:'Pasang tagihan ke payroll',exact:true})
const reconcile=page=>panel(page).getByRole('button',{name:'Periksa status pemasangan tagihan',exact:true})
const requestIs=(name,r)=>r.url().endsWith('/rpc/'+name)&&r.request().method()==='POST'
const observed=(label,actor)=>JSON.parse(execFileSync('python',['-B',resolve(HERE,'browser_observer.py'),'observe'],
 {cwd:ROOT,input:JSON.stringify({label,actor}),encoding:'utf8',maxBuffer:32*1024*1024,timeout:90000}).trim())
const ALLOWED=['cp7_mandor_shop.payroll_identities','cp7_mandor_shop.allocations','cp7_mandor_shop.allocation_events',
 'cp7_mandor_shop.allocation_states','cp7_mandor_shop.deduction_links','cp7_mandor_shop.requests',
 'erp.payroll_deductions','erp.payroll_settlements','erp.audit_logs','sequence:erp.audit_logs_id_seq']

function changes(before,after,allowed=[]){
 for(const v of[before,after]){
  assert.equal(v.catalog_groups,22);assert.deepEqual(v.dropped_catalog_fields,[])
  assert.deepEqual(v.dropped_data_or_sequence_keys,[]);assert.equal(v.Native_overlay_applied,false)
 }
 assert.equal(before.catalog_sha256,after.catalog_sha256)
 assert.deepEqual(before.invoice,after.invoice,'MANDOR_BROWSER_RESERVATION_CANNOT_PAY_INVOICE')
 assert.deepEqual(before.actor,after.actor);assert.deepEqual(before.actor_audits,after.actor_audits)
 const left=before.full_data_and_sequences,right=after.full_data_and_sequences
 assert.deepEqual(Object.keys(left).sort(),Object.keys(right).sort())
 const changed=Object.keys(left).filter(k=>JSON.stringify(left[k])!==JSON.stringify(right[k])).sort()
 assert.ok(changed.every(k=>allowed.includes(k)),'MANDOR_BROWSER_UNRELATED_WRITES:'+changed.join(','))
 if(!allowed.length){
  const withoutOriginal=({original,...value})=>value
  assert.deepEqual(withoutOriginal(before),withoutOriginal(after),'MANDOR_BROWSER_EXACT_NO_EFFECT_REQUIRED')
 }
 return{status:'PASS',changed_tables:changed,allowed_tables:[...allowed].sort(),
  original_before:before.original,original_after:after.original}
}

function held(before,after,reply,request){
 assert.equal(reply.kind,'COMMITTED_OUTCOME');assert.equal(reply.invoice_settled_by_this_command,false)
 assert.equal(reply.request_id,request.p_request);assert.equal(reply.action,'RESERVE')
 assert.equal(after.deductions.length,before.deductions.length+1)
 assert.equal(after.payroll[0],'CALCULATED');assert.equal(cents(after.payroll[1]),190000000n)
 const rows=after.allocation_states.filter(r=>r.allocation_id===reply.allocation_id)
 assert.equal(rows.length,1);assert.equal(rows[0].state,'RESERVED')
 const old=new Map(before.requests.map(r=>[r.request_id,r])),next=new Map(after.requests.map(r=>[r.request_id,r]))
 assert.deepEqual([...next.keys()].sort(),[...old.keys(),request.p_request].sort())
 for(const[key,value]of old)assert.deepEqual(next.get(key),value)
 assert.deepEqual(next.get(request.p_request).response,reply);assert.deepEqual(next.get(request.p_request).payload,request.p_payload)
}

async function menu(ui,page){
 const toggle=page.getByRole('button',{name:'Buka menu',exact:true})
 if(await toggle.isVisible()&&!await page.locator('.sidebar').evaluate(e=>e.classList.contains('sidebar-open')))await toggle.click()
 const target=page.getByRole('button',{name:'• Payroll & Kasbon',exact:true})
 if(!await target.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
 await target.click();await ui.expect(page.getByRole('heading',{name:'Payroll & Kasbon',exact:true})).toBeVisible()
}

async function choosePayroll(ui,page,f){
 await menu(ui,page)
 await page.getByLabel('Cari payroll',{exact:true}).fill(f.payroll_number)
 await page.getByRole('button',{name:'Cari payroll',exact:true}).click()
 const selected=page.locator('button.cproc-receipt').filter({hasText:f.payroll_number})
 await ui.expect(selected).toHaveCount(1);await selected.click()
 await ui.expect(panel(page).getByRole('button',{name:'Pasang tagihan belanja',exact:true})).toBeEnabled()
 const response=page.waitForResponse(r=>requestIs(READ,r))
 await panel(page).getByRole('button',{name:'Pasang tagihan belanja',exact:true}).click()
 const actual=await response;assert.equal(actual.status(),200,await actual.text())
 const value=await actual.json();assert.equal(value.payroll_id,f.payroll_id)
 await ui.expect(dialog(page)).toBeVisible()
 await ui.expect(dialog(page).getByRole('article',{name:'Nota '+f.sale_number,exact:true})).toBeVisible()
 return value
}

async function selectAmount(ui,page,f,value){
 await dialog(page).getByRole('button',{name:'Pilih nota '+f.sale_number,exact:true}).click()
 await amount(page).fill(value);await ui.expect(reserve(page)).toBeDisabled()
 await reviewed(page).check();await ui.expect(reserve(page)).toBeEnabled()
}

async function responseTo(page,operation){
 const pending=page.waitForResponse(r=>requestIs(WRITE,r));await operation();const response=await pending
 return{status:response.status(),body:await response.json(),request:response.request().postDataJSON(),url:response.url()}
}

async function fresh(ui,page,f){
 const pending=page.waitForResponse(r=>requestIs(READ,r)&&r.request().postDataJSON().p_payroll===f.payroll_id)
 await dialog(page).getByRole('button',{name:'Muat ulang tagihan',exact:true}).click()
 const response=await pending;assert.equal(response.status(),200,await response.text())
 assert.equal((await response.json()).payroll_id,f.payroll_id)
 await ui.expect(dialog(page).getByText('Memuat kartu tagihan…',{exact:true})).toHaveCount(0)
}

async function journey(ui,mobile,source){
 const f=source.fixture,suffix=mobile?'MOBILE390':'DESKTOP',run=f.payroll_id.replaceAll('-','').toUpperCase()
 const contexts=[],captures=[],stoppers=[],expected=[],visuals=[],screenshots=[],proofs=[],calls=[]
 let sequence=0,routeHandler,routePage
 const owner=await ui.login('OWNER',{label:'MANDOR-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 contexts.push(owner.context);const page=owner.page
 const state=label=>observed(`MANDOR_${suffix}_${run}_${String(++sequence).padStart(2,'0')}_${label}`,owner.user.id)
 function track(p){captures.push(observeConsole(p));stoppers.push(observeResponseWaits(p));p.on('request',r=>{if(r.url().endsWith('/rpc/'+WRITE))calls.push(r.postDataJSON())})}
 async function visual(p,label,width=mobile?390:1440){
  const size=await p.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}))
  assert.equal(size.viewport,width);assert.ok(size.width<=width,JSON.stringify(size))
  visuals.push({label,size,contrast:await readable(dialog(p))})
  const path=`cp6-proof/t3/MANDOR_${suffix}_${run}_${label}.png`;await p.screenshot({path,fullPage:true});screenshots.push(path)
 }
 track(page);let outcome
 try{
  const workspace=await choosePayroll(ui,page,f);assert.equal(workspace.can_change,true)
  await visual(page,'INITIAL')
  if(mobile){
   for(const width of[320,768]){await page.setViewportSize({width,height:844});await visual(page,'WIDTH'+width,width)}
   await page.setViewportSize({width:390,height:844})
  }
  const before=state('BEFORE_SELECTION')
  await selectAmount(ui,page,f,'100000.00')
  await dialog(page).getByRole('button',{name:'Batal memilih tagihan',exact:true}).click()
  proofs.push(changes(before,state('AFTER_CANCELLED_SELECTION')))
  let first,request,saved
  if(!mobile){
   const other=await owner.context.newPage();other.setDefaultTimeout(20000);track(other)
   await other.goto(ui.origin);await choosePayroll(ui,other,f)
   await selectAmount(ui,page,f,'100000.00')
   let seenResolve,seenReject
   const seen=new Promise((resolve,reject)=>{seenResolve=resolve;seenReject=reject});void seen.catch(()=>{})
   routePage=page;routeHandler=async route=>{
    try{
     const actual=await route.fetch({timeout:20000});assert.equal(actual.status(),200,await actual.text())
     const value={body:await actual.json(),request:route.request().postDataJSON()}
     await route.abort('failed');seenResolve(value)
    }catch(error){seenReject(error);await route.abort('failed').catch(()=>{})}
   }
   expected.push({url:ui.api+'/rest/v1/rpc/'+WRITE,text:'Failed to load resource: net::ERR_FAILED',reason:'INTENTIONALLY_LOST_ACTUAL_COMMITTED_REPLY'})
   await page.route('**/rest/v1/rpc/'+WRITE,routeHandler)
   await reserve(page).click()
   let timer
   try{outcome=await Promise.race([seen,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('MANDOR_BROWSER_BOUNDED_LOST_REPLY')),25000)})])}
   finally{clearTimeout(timer)}
   await page.unroute('**/rest/v1/rpc/'+WRITE,routeHandler);routeHandler=null
   first=outcome.body;request=outcome.request
   await ui.expect(reconcile(page)).toBeVisible();await ui.expect(reconcile(other)).toBeVisible()
   await ui.expect(amount(other)).toHaveCount(0)
   saved=state('AFTER_ACTUAL_SAVE_LOST_REPLY');held(before,saved,first,request)
   proofs.push(changes(before,saved,ALLOWED));await visual(page,'PENDING')
   // Native modal focus makes the parent recovery notice inert until the
   // cards are closed. Use the real visible close control before recovery.
   await other.getByRole('button',{name:'Tutup kartu tagihan',exact:true}).click()
   const retry=await responseTo(other,()=>reconcile(other).click())
   assert.equal(retry.status,200);assert.deepEqual(retry.request,request);assert.deepEqual(retry.body,first)
   await ui.expect(reconcile(other)).toHaveCount(0);await ui.expect(reconcile(page)).toHaveCount(0)
   proofs.push(changes(saved,state('AFTER_EXACT_SECOND_TAB_REPLAY')))
   await fresh(ui,page,f)
   outcome={lost_reply:outcome,exact_second_tab_replay:retry,second_tab_new_input_removed:true}
  }else{
   await selectAmount(ui,page,f,'200000.00')
   const cards=workspace.cards.filter(r=>r.sale_id===f.sale_id);assert.equal(cards.length,1)
   request={p_action:'RESERVE',p_payload:{contract_version:'cp7.mandor-shop-allocation-command.v1',payroll_id:f.payroll_id,
    sale_id:f.sale_id,review_token:cards[0].review_token,amount:'100000.00'},p_request:randomUUID()}
   const external=await owner.rpc(WRITE,request);assert.equal(external.status,200);first=external.body
   saved=state('AFTER_REAL_CONCURRENT_RESERVATION');held(before,saved,first,request)
   proofs.push(changes(before,saved,ALLOWED))
   const stale=await responseTo(page,()=>reserve(page).click())
   assert.equal(stale.status,400);assert.equal(stale.body.code,'P0001');assert.equal(stale.body.message,'CP7_MANDOR_SHOP_REVIEW_CHANGED')
   expected.push({url:stale.url,text:'Failed to load resource: the server responded with a status of 400 (Bad Request)',reason:'ACTUAL_STALE_REVIEW_REFUSAL'})
   await ui.expect(amount(page)).toHaveCount(0)
   proofs.push(changes(saved,state('AFTER_STALE_INPUT_REFUSED')))
   await fresh(ui,page,f);outcome={actual_concurrent_response:external,actual_stale_response:stale,stale_input_removed:true}
  }
  await ui.expect(dialog(page).getByRole('button',{name:'Lepas nota '+f.sale_number,exact:true})).toBeEnabled()
  await visual(page,'AUTHORITATIVE_READ')
  await dialog(page).getByRole('button',{name:'Lepas nota '+f.sale_number,exact:true}).click()
  const release=dialog(page).getByRole('button',{name:'Lepas tagihan dari payroll',exact:true})
  await ui.expect(release).toBeDisabled();await reviewed(page).check()
  const released=await responseTo(page,()=>release.click());assert.equal(released.status,200)
  assert.equal(released.body.allocation_id,first.allocation_id)
  await ui.expect(dialog(page).getByRole('button',{name:'Pilih nota '+f.sale_number,exact:true})).toBeEnabled()
  const after=state('AFTER_EXPLICIT_RELEASE');proofs.push(changes(saved,after,ALLOWED))
  assert.deepEqual(after.deductions,before.deductions);assert.equal(cents(after.payroll[1]),200000000n)
  assert.equal(after.allocation_states.find(r=>r.allocation_id===first.allocation_id).state,'RELEASED')
  await visual(page,'RELEASED')
  return{status:'PASS',normal_App_menu:true,real_Auth:true,actual_browser_viewport:mobile?390:1440,
   source,actual_first_reply:first,actual_first_request:request,actual_release:released,journey:outcome,
   exact_future_payroll_id:f.payroll_id,invoice_settled:false,complete_census_proofs:proofs,
   screenshots,visuals,actual_write_requests:calls,console_evidence:captures.map(c=>requireConsoleEvidence(c,expected)),
   all_stock_HPP_journals_entitlements_and_existing_history_unchanged:true,product_responses_mocked:false,
   actual_Native_case_credit:0,actual_Auth_HTTP_case_credit:0,actual_two_session_case_credit:0}
 }finally{
  if(routeHandler)await routePage.unroute('**/rest/v1/rpc/'+WRITE,routeHandler).catch(()=>{})
  for(const stop of stoppers)stop();for(const capture of captures)capture.stop()
  for(const context of contexts)await context.close()
 }
}

export async function cases(ui,today){
 const source=JSON.parse(execFileSync('python',['-B',resolve(HERE,'browser_observer.py'),'--admit'],
  {cwd:ROOT,encoding:'utf8',maxBuffer:2*1024*1024,timeout:60000}).trim())
 assert.equal(source.status,'ACTUAL_AFUI_PARENT_AND_MANDOR_COMMITTED_BROWSER_SOURCE_ADMITTED')
 assert.equal(source.physical_GOOD_day,today)
 mkdirSync(resolve(ROOT,'cp6-proof/t3'),{recursive:true})
 return[[IDS[0],()=>journey(ui,false,source)],[IDS[1],()=>journey(ui,true,source)]]
}
