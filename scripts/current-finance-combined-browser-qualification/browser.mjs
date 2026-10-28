import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
const browserRoot=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
import {buildCurrentProgressFinance} from './build_3194.mjs'
import {assertCombinedProgress,PROGRESS} from './progress_oracle.mjs'
import {observeConsole,requireConsoleEvidence} from './console_evidence.mjs'
const fixture=(op,p)=>JSON.parse(execFileSync('python',[resolve(browserRoot,'scripts/current-finance-combined-browser-qualification/browser_fixture.py'),op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:32*1024*1024}).trim())
const STEP='erp_cp7_step_staged_analysis_v1'
const OP='erp_cp7_request_bounded_staged_analysis_v2',FIN='erp_cp7_request_bounded_frozen_finance_analysis_v2',GET='erp_cp7_get_staged_analysis_v1',PAGES='erp_cp7_read_staged_analysis_pages_v1'
export const IDS=['A_PROGRESS_FINANCE_BROWSER_DESKTOP_REAL_AUTH_LOST_REPLY_REPLAY_OFFICIAL24','A_PROGRESS_FINANCE_BROWSER_MOBILE_REAL_AUTH_BLOCKED_REPORT_ACCESS_REVOKED']
const money=v=>{let[whole,fraction='']=v.split('.');fraction=fraction.replace(/0+$/,'');return'Rp'+whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(fraction?','+fraction:'')}
async function readable(panel){
  const rows=await panel.evaluate(root=>{
    const rgb=v=>v.match(/[\d.]+/g).map(Number),lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0),out=[]
    for(const el of[root,...root.querySelectorAll('*')]){
      const s=getComputedStyle(el),label=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
      if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
      const layers=[];let bg=null
      for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p),v=rgb(c.backgroundColor);if(c.backgroundImage!=='none'||c.opacity!=='1')throw Error('UNMEASURED_FINANCE_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,90),tag:p.tagName,classes:p.className,backgroundImage:c.backgroundImage,opacity:c.opacity}));if(v.length===3||v[3]===1){bg=v.slice(0,3);break}layers.push(v)}
      if(!bg)throw Error('MISSING_FINANCE_SURFACE')
      for(const v of layers.reverse())bg=bg.map((x,i)=>v[i]*(v[3]??1)+x*(1-(v[3]??1)))
      const record=(label,color)=>{const f=rgb(color),fg=bg.map((x,i)=>f[i]*(f[3]??1)+x*(1-(f[3]??1))),a=lum(fg),b=lum(bg);out.push({label:label.slice(0,90),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)})}
      record(label,s.color)
      if(el.hasAttribute('data-label')){const pseudo=getComputedStyle(el,'::before');if(pseudo.display!=='none'&&pseudo.content!=='none')record(el.getAttribute('data-label'),pseudo.color)}
    }return out
  })
  assert.ok(rows.length>0&&rows.every(x=>x.ratio>=4.5),JSON.stringify(rows.filter(x=>x.ratio<4.5)))
  return rows
}
async function journey(ui,today,built,mobile){
  const user=await ui.login(mobile?'ADMIN':'OWNER',{label:'A-frozen-finance-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),page=user.page,actor=user.user.id
  const state=()=>fixture('state',{actor}),calls=[],shots=[],contrasts=[]
  const consoleCapture=observeConsole(page),expectedNetwork=[]
  let f,before,lost=null,revoked=null,other=null
  let initialFaultEnabled=!mobile;const initialFaults=[];let initialRecovery=null
  const panel=page.getByRole('region',{name:'Analisis produksi dan laporan resmi',exact:true}),quantity=page.getByRole('region',{name:'Kebutuhan seluruh produk',exact:true}),finance=page.getByRole('region',{name:'Keuangan analisis dari laporan resmi',exact:true})
  const stored=()=>page.evaluate(()=>Object.entries(localStorage).filter(([k])=>k.startsWith('erp.cp7.bounded-analysis-request.v2:')).map(([key,bytes])=>({key,bytes,value:JSON.parse(bytes)})))
  const shot=async suffix=>{mkdirSync('cp6-proof/t3',{recursive:true});const path=`cp6-proof/t3/A_PROGRESS_FINANCE_${mobile?'MOBILE':'DESKTOP'}_${suffix}.png`;await page.screenshot({path,fullPage:true});shots.push(path);if(suffix!=='FAILURE')contrasts.push({state:suffix,rows:await readable(panel)})}
  try{
    f=fixture('prepare',{today,actor,scenario:mobile?'BLOCKED_POSTED_FIXTURE':'READY_BASELINE'});before=f.before
    assert.equal(f.browser_job_created,false)
    if(mobile)assert.equal(f.source_preparation,null)
    else{
      assert.equal(f.source_preparation.after.status,'READY')
      assert.equal(f.source_preparation.readiness_rules_unchanged,true)
      assert.equal(f.source_preparation.report_output_not_fabricated,true)
      assert.deepEqual(f.source_preparation.attendance.refused,[])
    }
    await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000})
    await page.route('**/rest/v1/rpc/*',async route=>{
      const name=new URL(route.request().url()).pathname.split('/').at(-1),args=route.request().postDataJSON(),started=performance.now()
      // Labelled transport fault: actual job and all status reads remain server
      // responses. A's real large-factory SQL refusal is proved by backend3194.
      if(initialFaultEnabled&&name===STEP&&route.request().method()==='POST'){
        initialFaults.push({name,args,at:started,synthetic:true})
        expectedNetwork.push({url:route.request().url(),text:'Failed to load resource: the server responded with a status of 400 (Bad Request)',reason:'labelled exact initial-refusal transport injection'})
        await route.fulfill({status:400,contentType:'application/json',headers:{'access-control-allow-origin':new URL(built.url).origin},body:JSON.stringify({code:'55000',message:'CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED'})});return
      }
      const response=await route.fetch(),body=await response.json(),millis=performance.now()-started
      calls.push({name,args,status:response.status(),body,millis})
      // Lose only delivery of the committed real finance response.
      if(!mobile&&name===FIN&&!lost){
        lost=calls.at(-1);expectedNetwork.push({url:route.request().url(),text:'Failed to load resource: net::ERR_FAILED',reason:'deliberately lost committed finance reply'});await route.abort('failed')
      }else{
        if(mobile&&revoked&&[FIN,GET,PROGRESS].includes(name)&&response.status()===403)expectedNetwork.push({url:route.request().url(),text:'Failed to load resource: the server responded with a status of 403 (Forbidden)',reason:'verified finance access revocation'})
        await route.fulfill({response})
      }
    })
    await page.goto(built.url+'?query='+encodeURIComponent(JSON.stringify(f.query)))
    await ui.expect(panel).toBeVisible()
    const newer=quantity.getByRole('button',{name:'Hitung kebutuhan terbaru',exact:true})
    if(!mobile){
      await ui.expect.poll(()=>calls.filter(c=>c.name===GET).length,{timeout:15000}).toBeGreaterThanOrEqual(2)
      assert.equal(initialFaults.length,1)
      const held=await stored();assert.equal(held.length,1);const request=held[0].value.id
      assert.equal(initialFaults[0].args.p_request,request)
      for(const c of calls.filter(c=>c.name===GET)){assert.equal(c.status,200);assert.equal(c.body.request_id,request);assert.equal(c.body.units_done,0);assert.equal(c.body.plan_final,false)}
      await ui.expect(quantity.getByRole('progressbar')).toHaveCount(0)
      await ui.expect(quantity).toContainText('Jumlah akhir masih disusun')
      await page.reload();await ui.expect.poll(()=>initialFaults.length,{timeout:15000}).toBe(2)
      assert.deepEqual(await stored(),held)
      await ui.expect(quantity.getByRole('alert')).toContainText('Pemantauan dihentikan',{timeout:150000})
      const elapsed=performance.now()-initialFaults[1].at
      assert.ok(elapsed>=120000&&elapsed<150000,JSON.stringify({initial_observer_elapsed_ms:elapsed}))
      assert.equal(initialFaults.length,2);assert.deepEqual(await stored(),held)
      assert.ok(calls.filter(c=>c.name===GET).every(c=>c.args.p_request===request&&c.body.units_done===0))
      const stalled=state();assert.equal(stalled.jobs.length,1);assert.equal(stalled.jobs[0].request,request);assert.equal(stalled.jobs[0].state,'RUNNING');assert.deepEqual(stalled.physical,before.physical)
      await ui.expect(newer).toBeDisabled();await shot('INITIAL_OBSERVER_STOPPED')
      initialFaultEnabled=false
      const reopen=quantity.getByRole('button',{name:'Buka perhitungan tersimpan',exact:true});await ui.expect(reopen).toBeEnabled();await reopen.click()
      initialRecovery={label:'TRANSPORT_FAULT_WITH_REAL_AUTH_JOB_AND_STATUS',actual_large_server_refusal_claim:false,synthetic_refusals:initialFaults,actual_status_reads:calls.filter(c=>c.name===GET).length,request,elapsed_ms:elapsed,same_UUID_reload:true,safe_same_UUID_recovery:true,real_two_minute_observation:true}
    }
    await ui.expect(newer).toBeEnabled({timeout:180000})
    const operational=await stored();assert.equal(operational.length,1);assert.equal(operational[0].value.finance,undefined)
    if(initialRecovery)assert.equal(operational[0].value.id,initialRecovery.request)
    const initial=state();assert.equal(initial.jobs.length,1);assert.equal(initial.jobs[0].state,'DONE');assert.equal(initial.captures.length,0);assert.deepEqual(initial.physical,before.physical)
    await panel.getByRole('checkbox',{name:'Sertakan angka keuangan dari laporan resmi',exact:true}).check()
    await newer.click()
    if(!mobile){
      await ui.expect.poll(()=>lost?.status).toBe(200)
      await ui.expect(quantity.getByRole('alert')).toBeVisible();await ui.expect(newer).toBeDisabled()
      const held=await stored();assert.equal(held[0].value.id,lost.args.p_request);assert.equal(held[0].value.finance,'STAGED')
      await page.reload();await ui.expect(finance).toBeVisible({timeout:180000});assert.deepEqual(await stored(),held)
    }else await ui.expect(finance).toBeVisible({timeout:180000})
    const held=await stored();assert.equal(held.length,1);assert.equal(held[0].value.finance,'STAGED');assert.notEqual(held[0].value.id,operational[0].value.id)
    const request=held[0].value.id,progressChecks=[],exact=fixture('read',{actor,request}),pending=state()
    assert.equal(exact.job.finance_capture.state,'RUNNING');assert.equal(exact.original.financial_source,null)
    assert.equal(exact.full_reference.finance_sidecar_mode,'STAGED');assert.equal(exact.full_reference.bounded_request_contract,'cp7.bounded-analysis-request.v2')
    assert.equal(pending.jobs.length,2);assert.equal(pending.captures.length,1);assert.deepEqual(pending.physical,before.physical)
    await ui.expect(finance).toContainText('Angka keuangan sedang disiapkan')
    await ui.expect(finance.locator('[data-finance-metric]')).toHaveCount(0)
    progressChecks.push(await assertCombinedProgress(ui,page,calls,request,'RUNNING'))
    await ui.expect(quantity).toContainText('target');await shot('OPERATIONAL_DONE_FINANCE_RUNNING')
    const completed=fixture('complete_finance',{actor,request}),result=completed.job.finance_capture.result
    assert.equal(completed.private_SQL_advancement_only,true);assert.equal(completed.actual_cron_claim,false)
    assert.equal(result.metrics.length,24);assert.equal(result.readiness,mobile?'BLOCKED':'READY')
    await finance.getByRole('button',{name:'Muat ulang status keuangan',exact:true}).click()
    if(mobile){
      const unknown=result.metrics.filter(m=>m.value.state==='UNKNOWN');assert.ok(unknown.length>0)
      assert.ok(unknown.every(m=>!Object.hasOwn(m.value,'value')))
      await ui.expect(finance).toContainText('Perhitungan laporan selesai, tetapi HPP atau bukunya belum lengkap')
      await ui.expect(finance.locator('[data-finance-metric]')).toHaveCount(0)
    }else{
      await ui.expect(finance.locator('[data-finance-metric]')).toHaveCount(24)
      for(const metric of result.metrics){assert.equal(metric.value.state,'KNOWN');await ui.expect(finance.locator(`[data-finance-metric="${metric.metric_id}"] td`).nth(1)).toHaveText(money(metric.value.value))}
    }
    progressChecks.push(await assertCombinedProgress(ui,page,calls,request,mobile?'BLOCKED':'COMPLETED'))
    const readyState=state(),after=fixture('read',{actor,request})
    assert.deepEqual(after.original,exact.original);assert.deepEqual(after.page_set,exact.page_set);assert.deepEqual(after.page_metadata,exact.page_metadata)
    assert.deepEqual(readyState.physical,before.physical);assert.equal(readyState.captures.length,1)
    assert.deepEqual(await stored(),held)
    await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await shot(mobile?'CAPTURE_COMPLETE_REPORT_BLOCKED':'OFFICIAL_READY24')
    if(!mobile){
      await page.reload();await ui.expect(finance.locator('[data-finance-metric]')).toHaveCount(24,{timeout:180000})
      progressChecks.push(await assertCombinedProgress(ui,page,calls,request,'COMPLETED'))
      assert.equal(progressChecks.at(-1).elapsedMs,progressChecks.at(-2).elapsedMs)
      assert.deepEqual(await stored(),held);assert.deepEqual(state(),readyState);await shot('REOPENED_SAME_CAPTURE')
    }else{
      other=await ui.login('OWNER',{label:'A-frozen-finance-foreign'})
      const foreign=await other.rpc(GET,{p_request:request});assert.equal(foreign.status,400)
      const anon=await ui.anonRpc(GET,{p_request:request});assert.ok([401,403].includes(anon.status))
      const foreignProgress=await other.rpc(PROGRESS,{p_request:request});assert.equal(foreignProgress.status,400)
      const anonymousProgress=await ui.anonRpc(PROGRESS,{p_request:request});assert.ok([401,403].includes(anonymousProgress.status))
      revoked=fixture('withdraw_finance',{actor})
      await finance.getByRole('button',{name:'Muat ulang status keuangan',exact:true}).click()
      await ui.expect(finance).toContainText('Akun saat ini belum boleh membaca angka keuangan analisis')
      await ui.expect(finance.locator('[data-finance-metric]')).toHaveCount(0)
      progressChecks.push(await assertCombinedProgress(ui,page,calls,request,'ACCESS_REVOKED'))
      const replay=await user.rpc(FIN,{p_request:request,p_query:{...f.query,finance_mode:'STAGED'}});assert.equal(replay.status,403)
      assert.deepEqual(state(),readyState);assert.deepEqual(await stored(),held);await shot('ACCESS_REVOKED')
    }
    const requests=calls.filter(c=>c.name===FIN)
    assert.ok(requests.length>=2&&requests.every(c=>c.status===200&&c.args.p_request===request))
    for(const c of requests)assert.deepEqual(c.args.p_query,{...f.query,finance_mode:'STAGED'})
    assert.ok(calls.some(c=>c.name===PAGES&&c.status===200));assert.ok(calls.filter(c=>c.name===OP).every(c=>!Object.hasOwn(c.args.p_query,'finance_mode')))
    assert.ok(calls.every(c=>c.millis<8000));assert.deepEqual(await page.evaluate(()=>navigator.locks.query()),{held:[],pending:[]})
    assert.ok(progressChecks.length>=3)
    assert.ok(calls.some(c=>c.name===PROGRESS&&c.status===200))
    const consoleEvidence=requireConsoleEvidence(consoleCapture.errors,expectedNetwork)
    return{status:'PASS',initial_driver_recovery:initialRecovery,console_evidence:consoleEvidence,actual_progress_RPC_and_DOM:progressChecks,progress_counts_from_server:true,no_overall_fake_percent:true,fixture_source_preparation:f.source_preparation,actual_AuthProvider:true,actual_AuthGate:true,actual_Auth_PostgREST_browser:true,actual_public_finance_RPC:true,actual_operational_DEFERRED_no_capture:true,operational_DONE_finance_RUNNING:true,official_sections_and_24_metrics_equal:true,official_readiness:result.readiness,all24_READY_figures_rendered:!mobile,BLOCKED_figures_withheld_UNKNOWN_not_zero:mobile,independent_book_signature:true,private_SQL_finance_advancement_not_cron:true,actual_lost_reply_same_UUID_reopen:!mobile,actual_mobile_finance_permission_revocation:mobile,one_finance_capture:true,sealed_operational_original_unchanged:true,no_stock_money_HPP_effect:true,viewport:mobile?390:1440,no_horizontal_overflow:true,visible_text_contrasts:contrasts,shots,source_paths:built.source_paths,source_sha256:built.source_sha256,actual_call_timings:calls.map(({name,status,millis})=>({name,status,millis})),full_factory_finance_qualified:false,new_B_analog_and_cutting_qualified:false,default_application_adopted:false,production_go:false}
  }catch(error){mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/A_PROGRESS_FINANCE_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),calls,console_errors:consoleCapture.errors,expected_network_errors:expectedNetwork,alerts:await page.getByRole('alert').allTextContents().catch(()=>[])},null,2));await shot('FAILURE').catch(()=>{});throw error}
  finally{consoleCapture.stop();if(revoked)fixture('restore_finance',{actor,permission:revoked.permission});await other?.context.close();await user.context.close()}
}
export async function cases(ui,today){
  // Keep case discovery free of build/DB work; build once when a case executes.
  let built
  const get=async()=>{if(!built){built=await buildCurrentProgressFinance(ui);built.source_sha256=Object.fromEntries(built.source_paths.map(p=>[p,createHash('sha256').update(readFileSync(resolve(browserRoot,p))).digest('hex')]));assert.equal(built.prepared_choice_gate,true);const graph=JSON.parse(readFileSync(resolve(browserRoot,'scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json')));assert.deepEqual(built.source_sha256,Object.fromEntries(graph.files.map(f=>[f.path,f.sha256])))}return built}
  return IDS.map((id,index)=>[id,async()=>journey(ui,today,await get(),index===1)])
}
