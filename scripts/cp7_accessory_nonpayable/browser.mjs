// Prepared normal-App journeys. Real Auth and the complete owning copy are mandatory.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {observeConsole,requireConsoleEvidence,readable} from '../current-sku-pair-browser-qualification/evidence.mjs'
import {observeResponseWaits} from '../current-s03-sku-s05-composite-qualification/response_waits.mjs'

export const IDS=[
  'NONPAYABLE_BROWSER_DESKTOP_POSTED_USE_REFUSAL_LOST_REPLY_TWO_TABS',
  'NONPAYABLE_BROWSER_MOBILE390_CANCEL_LATE_SAVE_OWNER_AND_ADMIN_READ_ONLY',
]
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const HERE=resolve(ROOT,'scripts/cp7_accessory_nonpayable')
const READ='erp_cp7_get_good_policy_dates_v1',WRITE='erp_cp7_save_good_policy_date_v1'
const sha=raw=>createHash('sha256').update(raw).digest('hex')
const requestIs=(name,r)=>r.url().endsWith('/rpc/'+name)&&r.request().method()==='POST'
const panel=page=>page.getByRole('region',{name:'Tanggal berlaku kategori gratis untuk GOOD',exact:true})
const reason=page=>panel(page).getByLabel('Alasan pencatatan tanggal berlaku',{exact:true})
const day=page=>panel(page).getByLabel('Berlaku untuk GOOD mulai tanggal (WIB)',{exact:true})
const review=page=>panel(page).getByRole('checkbox',{name:/Saya memastikan versi kategori, tanggal berlaku/})
const save=page=>panel(page).getByRole('button',{name:'Simpan tanggal berlaku yang ditinjau',exact:true})
const retry=page=>panel(page).getByRole('button',{name:'Periksa hasil tanggal yang sama',exact:true})
const cancel=page=>panel(page).getByRole('button',{name:'Batalkan permintaan jika belum tersimpan',exact:true})
const observe=label=>JSON.parse(execFileSync('python',['-B',resolve(HERE,'browser_fixture.py'),'observe'],
  {cwd:ROOT,input:JSON.stringify({label}),encoding:'utf8',maxBuffer:32*1024*1024,timeout:60000}).trim())

async function bounded(promise,label){
  let timer
  try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(label)),20000)})])}
  finally{clearTimeout(timer)}
}

function admitted(){
  // The source-only parent gate runs before creating any browser/Auth user.
  const gate=JSON.parse(execFileSync('python',['-B',resolve(HERE,'browser_prepare.py'),'--admit'],
    {cwd:ROOT,encoding:'utf8',maxBuffer:4*1024*1024,timeout:30000,stdio:['ignore','pipe','pipe']}).trim())
  assert.equal(gate.status,'ACTUAL_FREE3_PARENT_ADMITTED_BEFORE_BROWSER')
  assert.deepEqual(gate.source.browser_case_ids,IDS)
  const sourceRaw=readFileSync(resolve(HERE,'SOURCE.json')),source=JSON.parse(sourceRaw)
  for(const[path,pin]of Object.entries(source.files)){
    const raw=readFileSync(resolve(ROOT,path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256,'AFUI_BROWSER_OWN_SOURCE_CHANGED:'+path)
  }
  const ui=JSON.parse(readFileSync(resolve(HERE,'UI_SOURCE.json')))
  for(const[path,pin]of Object.entries(ui.files)){
    const raw=readFileSync(resolve(ROOT,path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256,'AFUI_BROWSER_UI_SOURCE_CHANGED:'+path)
  }
  const raw=readFileSync(resolve(ROOT,'cp6-proof/t3/AFUI_BROWSER_NATIVE_PREREQUISITE.json'))
  assert.equal(sha(raw),process.env.AFUI_BROWSER_FIXTURE_SHA256)
  const prepared=JSON.parse(raw);assert.equal(prepared.status,'ACTUAL_NATIVE_NONPAYABLE_BROWSER_PREREQUISITE_PREPARED')
  assert.equal(prepared.expected_positive_HPP,'20');assert.equal(prepared.expected_reimbursement,'0')
  assert.equal(prepared.expected_new_entitlements,0)
  return{prepared,source_sha256:sha(sourceRaw),fixture_sha256:sha(raw),actual_parent_head:gate.head}
}

function appended(before,after,key,added){
  const a=new Map(before.map(row=>[row[key],row])),b=new Map(after.map(row=>[row[key],row]))
  assert.equal(a.size,before.length);assert.equal(b.size,after.length);assert.equal(new Set(added).size,added.length)
  assert.ok(added.every(id=>!a.has(id)))
  assert.deepEqual([...b.keys()].sort(),[...a.keys(),...added].sort(),'AFUI_BROWSER_EXTRA_OR_ERASED_HISTORY')
  for(const[id,row]of a)assert.deepEqual(b.get(id),row,'AFUI_BROWSER_CHANGED_POSTED_HISTORY')
}

export function dateChanges(before,after,{requests=[],versions=[]}={}){
  for(const value of[before,after]){
    assert.equal(value.catalog_groups,22);assert.deepEqual(value.dropped_catalog_fields,[])
    assert.deepEqual(value.dropped_data_or_sequence_keys,[])
  }
  assert.equal(before.catalog_sha256,after.catalog_sha256,'AFUI_BROWSER_CHANGED_ALL22')
  assert.deepEqual(before.active_good,after.active_good,'AFUI_BROWSER_CHANGED_ACTIVE_GOOD_HPP_REIMBURSEMENT_OR_PHYSICAL_STOCK')
  const a=before.data_and_sequences,b=after.data_and_sequences
  assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),'AFUI_BROWSER_CHANGED_CENSUS_MEMBERS')
  const changed=Object.keys(a).filter(k=>JSON.stringify(a[k])!==JSON.stringify(b[k])).sort()
  const allowed=[]
  if(requests.length)allowed.push('cp7_accessory_nonpayable.date_requests_v1')
  if(versions.length)allowed.push('cp7_accessory_nonpayable.category_versions_v1')
  assert.deepEqual(changed,allowed.sort(),'AFUI_BROWSER_CHANGED_UNRELATED_MONEY_STOCK_ACCESS_OR_SEQUENCE')
  appended(before.date_requests,after.date_requests,'request_id',requests)
  appended(before.date_versions,after.date_versions,'id',versions)
  return{status:'PASS',actual_changed_tables:changed,original_before:before.original,original_after:after.original}
}

async function menu(ui,page){
  const toggle=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await toggle.isVisible()&&!await page.locator('.sidebar').evaluate(e=>e.classList.contains('sidebar-open')))await toggle.click()
  const link=page.getByRole('button',{name:'• Pengaturan ERP',exact:true})
  if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Pengaturan & Audit'}).click()
  await link.click();await ui.expect(page.getByRole('heading',{name:'Pengaturan ERP',exact:true})).toBeVisible()
}

async function open(ui,page){
  const pending=page.waitForResponse(r=>requestIs(READ,r))
  await menu(ui,page);const response=await pending;assert.equal(response.status(),200,await response.text())
  const value=await response.json();await ui.expect(panel(page)).toHaveAttribute('aria-busy','false');return value
}

async function fill(ui,page,date,text){
  await day(page).fill(date);await reason(page).fill(text)
  await ui.expect(save(page)).toBeDisabled();await review(page).check();await ui.expect(save(page)).toBeEnabled()
}

async function responseTo(page,action){
  const pending=page.waitForResponse(r=>requestIs(WRITE,r));await action();const response=await pending
  return{status:response.status(),body:await response.json(),request:response.request().postDataJSON(),url:response.url()}
}

async function journey(ui,mobile,source){
  const suffix=mobile?'MOBILE390':'DESKTOP',run=source.prepared.fixture.contractor.replaceAll('-','').toUpperCase()
  const contexts=[],observers=[],stoppers=[],calls=[],proofs=[],screenshots=[],visuals=[],expectedNetwork=[]
  const progress={},routeErrors=[];let serial=0,activeRoute,activePage,primaryError
  const state=label=>observe(`AFUI_${suffix}_${run}_${String(++serial).padStart(2,'0')}_${label}`)
  function track(page){
    observers.push(observeConsole(page));stoppers.push(observeResponseWaits(page))
    page.on('request',request=>{if(request.url().endsWith('/rpc/'+WRITE))calls.push(request.postDataJSON())})
  }
  async function visual(page,label){
    const size=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}))
    assert.equal(size.viewport,mobile?390:1440);assert.ok(size.width<=size.viewport,JSON.stringify(size))
    visuals.push({label,size,contrast:await readable(panel(page))})
    const path=`cp6-proof/t3/AFUI_${suffix}_${run}_${label}.png`
    await page.screenshot({path,fullPage:true});screenshots.push(path)
  }
  async function loseReply(page,forward){
    let resolveSeen,rejectSeen
    const seen=new Promise((resolve,reject)=>{resolveSeen=resolve;rejectSeen=reject});void seen.catch(()=>{})
    activePage=page
    activeRoute=async route=>{
      try{
        const request=route.request().postDataJSON();let actual=null
        if(forward){const result=await route.fetch();assert.equal(result.status(),200,await result.text());actual=await result.json()}
        await route.abort('failed');resolveSeen({request,actual,forwarded_to_actual_server:forward})
      }catch(error){routeErrors.push(String(error));rejectSeen(error);await route.abort('failed').catch(()=>{})}
    }
    await page.route('**/rest/v1/rpc/'+WRITE,activeRoute)
    expectedNetwork.push({url:ui.api+'/rest/v1/rpc/'+WRITE,text:'Failed to load resource: net::ERR_FAILED',reason:'INTENTIONALLY_LOST_REAL_REQUEST_OR_REPLY'})
    await save(page).click();const value=await bounded(seen,'AFUI_REAL_REQUEST_INTERCEPTION_DID_NOT_COMPLETE')
    await page.unroute('**/rest/v1/rpc/'+WRITE,activeRoute);activeRoute=null
    await ui.expect(retry(page)).toBeVisible();await ui.expect(retry(page)).toBeEnabled()
    return value
  }
  mkdirSync(resolve(ROOT,'cp6-proof/t3'),{recursive:true})
  const owner=await ui.login('OWNER',{label:'AFUI-'+suffix,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
  contexts.push(owner.context);const page=owner.page;track(page)
  try{
    const workspace=await open(ui,page);assert.equal(workspace.can_write,true)
    await ui.expect(save(page)).toBeDisabled();await visual(page,'INITIAL_OWNER')
    if(!mobile){
      const before=state('BEFORE_POSTED_USE_REFUSAL')
      await fill(ui,page,source.prepared.physical_GOOD_day,'Review date touching an already posted GOOD')
      const refused=await responseTo(page,()=>save(page).click())
      assert.equal(refused.status,400);assert.equal(refused.body.code,'P0001')
      assert.match(refused.body.message,/^NONPAYABLE_POSTED_GOOD_POLICY_REVIEW_REQUIRED:/)
      expectedNetwork.push({url:refused.url,text:'Failed to load resource: the server responded with a status of 400 (Bad Request)',reason:'ACTUAL_POSTED_GOOD_DATE_REFUSAL'})
      await ui.expect(panel(page).getByRole('alert')).toContainText('Koreksi atau balik hasil terkait melalui alur yang sah')
      await ui.expect(panel(page)).toHaveAttribute('aria-busy','false')
      proofs.push(dateChanges(before,state('AFTER_POSTED_USE_REFUSAL')));progress.posted_use=refused
      const other=await owner.context.newPage();other.setDefaultTimeout(20000);track(other)
      await other.goto(ui.origin);await open(ui,other)
      const beforeSave=state('BEFORE_LOST_REPLY')
      await fill(ui,page,source.prepared.explicit_review_day,'Reviewed future GOOD date through normal App')
      const lost=await loseReply(page,true);assert.equal(lost.actual.status,'SAVED')
      await ui.expect(retry(other)).toBeVisible();await ui.expect(day(other)).toBeDisabled()
      const saved=state('AFTER_ACTUAL_SAVE_LOST_REPLY')
      proofs.push(dateChanges(beforeSave,saved,{requests:[lost.request.p_request],versions:[lost.actual.id]}))
      const replay=await responseTo(other,()=>retry(other).click())
      assert.equal(replay.status,200);assert.deepEqual(replay.body,lost.actual)
      assert.deepEqual(replay.request,lost.request,'AFUI_UI_RETRY_MUST_KEEP_EXACT_REQUEST_UUID_AND_INTENT')
      await ui.expect(retry(other)).toHaveCount(0);await ui.expect(retry(page)).toHaveCount(0)
      proofs.push(dateChanges(saved,state('AFTER_SECOND_TAB_EXACT_REPLAY')))
      await ui.expect(panel(other)).toHaveAttribute('aria-busy','false')
      const read=other.waitForResponse(r=>requestIs(READ,r))
      await panel(other).getByRole('button',{name:'Baca ulang tanggal berlaku',exact:true}).click();assert.equal((await read).status(),200)
      await panel(other).locator('summary').filter({hasText:/Riwayat tanggal berlaku/}).click()
      await ui.expect(panel(other)).toContainText('Reviewed future GOOD date through normal App')
      await visual(other,'TWO_TAB_RECONCILED_HISTORY')
      progress.lost_reply={actual_server_response:lost.actual,actual_replay:replay.body,one_request:lost.request.p_request,
        second_tab_pending_lock:true,server_reply_mocked:false,source_and_date:selectedDate(lost.request)}
    }else{
      const date=new Date(source.prepared.explicit_review_day+'T00:00:00Z');date.setUTCDate(date.getUTCDate()+1)
      const selected=date.toISOString().slice(0,10),before=state('BEFORE_CANCELLED_ABSENT_REQUEST')
      await fill(ui,page,selected,'Cancel an uncertain date request before it reaches server')
      const lost=await loseReply(page,false);assert.equal(lost.actual,null)
      proofs.push(dateChanges(before,state('AFTER_UNFORWARDED_REQUEST_LOST')))
      const cancelled=await responseTo(page,()=>cancel(page).click())
      assert.equal(cancelled.status,200);assert.equal(cancelled.body.status,'CANCELLED')
      assert.equal(cancelled.request.p_request,lost.request.p_request);assert.equal(cancelled.request.p_cancel,true)
      assert.deepEqual(cancelled.request.p_payload,lost.request.p_payload)
      const afterCancel=state('AFTER_CANCEL_TOMBSTONE')
      proofs.push(dateChanges(before,afterCancel,{requests:[lost.request.p_request]}))
      const late=await owner.rpc(WRITE,lost.request);assert.equal(late.status,200);assert.deepEqual(late.body,cancelled.body)
      proofs.push(dateChanges(afterCancel,state('AFTER_LATE_CANCELLED_REQUEST')))
      await ui.expect(retry(page)).toHaveCount(0);await ui.expect(panel(page)).toHaveAttribute('aria-busy','false')
      await fill(ui,page,selected,'Reviewed future GOOD date on phone in a different display timezone')
      const posted=await responseTo(page,()=>save(page).click());assert.equal(posted.status,200);assert.equal(posted.body.status,'SAVED')
      assert.notEqual(posted.request.p_request,lost.request.p_request);assert.equal(posted.request.p_payload.effective_from,selected)
      proofs.push(dateChanges(afterCancel,state('AFTER_MOBILE_OWNER_SAVE'),{requests:[posted.request.p_request],versions:[posted.body.id]}))
      await ui.expect(panel(page)).toHaveAttribute('aria-busy','false')
      await visual(page,'OWNER_DATE_SAVED');progress.cancel={actual_cancel:cancelled.body,actual_late_arrival:late.body,server_reply_mocked:false}
      progress.owner_save={actual_response:posted.body,explicit_WIB_date:posted.request.p_payload.effective_from}
      const admin=await ui.login('ADMIN',{label:'AFUI-MOBILE-ADMIN',mobile:true,timezoneId:'America/Los_Angeles'})
      contexts.push(admin.context);track(admin.page)
      const adminBefore=state('ADMIN_BEFORE_READS'),adminWorkspace=await open(ui,admin.page),writes=calls.length
      assert.equal(adminWorkspace.can_write,false);await ui.expect(day(admin.page)).toBeDisabled()
      await ui.expect(save(admin.page)).toBeDisabled()
      await ui.expect(panel(admin.page)).toContainText('Admin dapat membaca riwayat')
      const read=admin.page.waitForResponse(r=>requestIs(READ,r))
      await panel(admin.page).getByRole('button',{name:'Baca ulang tanggal berlaku',exact:true}).click()
      assert.equal((await read).status(),200);assert.equal(calls.length,writes)
      proofs.push(dateChanges(adminBefore,state('ADMIN_AFTER_READS')));await visual(admin.page,'ADMIN_READ_ONLY')
      progress.admin_read_only={actual_real_Auth_role:'ADMIN',no_write_attempts:true,disabled_date_and_save:true}
    }
    assert.deepEqual(routeErrors,[])
    return{status:'PASS',normal_App_menu:true,real_Auth:true,viewport:mobile?390:1440,source,
      progress,complete_census_proofs:proofs,requests:calls,visuals,screenshots,
      console_evidence:observers.map(capture=>requireConsoleEvidence(capture,expectedNetwork)),
      actual_Native_case_credit:0,fixture_screen_creation_claim:false,actual_Auth_HTTP_case_credit:0,
      all_stock_HPP_journals_entitlements_and_existing_history_unchanged:true,full_outer_restore_and_Auth_cleanup_required:true,
      production_go:false,independent_acceptance:false}
  }catch(error){
    primaryError=error
    writeFileSync(resolve(ROOT,`cp6-proof/t3/AFUI_${suffix}_${run}_FIRST_FAILURE.json`),JSON.stringify({error:String(error.stack||error),progress,calls,proofs,routeErrors,
      console_errors:observers.map(v=>v.errors),page_errors:observers.map(v=>v.pageErrors),text:await page.locator('main').innerText().catch(()=>'')},null,2)+'\n')
    await page.screenshot({path:resolve(ROOT,`cp6-proof/t3/AFUI_${suffix}_${run}_FIRST_FAILURE.png`),fullPage:true}).catch(()=>{})
    throw error
  }finally{
    const failures=[]
    for(const fn of[()=>activeRoute?activePage.unroute('**/rest/v1/rpc/'+WRITE,activeRoute):undefined,...stoppers,...observers.map(v=>()=>v.stop()),...contexts.map(c=>()=>c.close())]){
      try{await fn()}catch(error){failures.push(String(error))}
    }
    if(failures.length){
      writeFileSync(resolve(ROOT,`cp6-proof/t3/AFUI_${suffix}_${run}_CLEANUP_FAILURE.json`),JSON.stringify({primary_error:String(primaryError||''),failures},null,2)+'\n')
      if(!primaryError)throw Error('AFUI_BROWSER_CLEANUP_FAILED:'+failures.join('; '))
    }
  }
}

function selectedDate(request){return{source_event_id:request.p_payload.source_event_id,effective_from:request.p_payload.effective_from}}
export function cases(ui){const source=admitted();return IDS.map((id,index)=>[id,()=>journey(ui,index===1,source)])}
