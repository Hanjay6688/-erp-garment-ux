// P19 full-application scale ladder in the browser: real Auth, real PostgREST,
// candidate UI on one committed copy grown 100 -> 300 -> 1000 -> 5000 targets
// through ordinary Native writers (seeding reported apart, never in latency).
// One trusted click per (size, history days, control) in a fresh signed-in
// desktop context; click, first status, progress and completion all use the
// page's monotonic clock. A refusal rendered by the panel (a declared cap or
// the existing 8 s limit) is the measured result for that size. Nothing is
// raised, sampled or cut. Kernel stand-in benchmarks are separate evidence.
// After a size's clicks the fixture's `measure` runs that size's SQL ladder and
// phase profile on the same committed copy in a rolled-back transaction, so no
// profiling ever precedes a measured click.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {budgetResult} from './cp7_p19_browser_latency.mjs'

const declaration=JSON.parse(readFileSync('docs/cp7/p19/P19_SCALE.json','utf8'))
assert.equal(declaration.contract,'cp7.p19.full-application-scale.v1')
assert.equal(declaration.evidence_kind,'FULL_APPLICATION_NATIVE')
const {sizes,history_days:historyDays,caps}=declaration,ids=declaration.required_case_ids.browser
assert.deepEqual(ids,sizes.map(n=>'P19S_BROWSER_DESKTOP_'+n))
// The stock screen's default analysis is operational-only (no ledger read);
// the owner's explicit choice of financial figures is measured as its own control.
const FINANCE='Sertakan angka keuangan (menunggu buku besar)'
const CONTROLS=[['CAPTURE','Ambil analisis ERP terbaru',false],['BACKGROUND','Hitung di latar belakang',false],['CAPTURE_WITH_FINANCE','Ambil analisis ERP terbaru',true]]
assert.deepEqual(CONTROLS.map(c=>(c[2]?FINANCE+' + ':'')+c[1]),declaration.browser.controls)
// Driver bounds only. Neither is an application limit nor enters a latency figure.
const OBSERVATION_WINDOW_MS=180000,SEED_PROCESS_MS=3600000,FIXTURE_PROCESS_MS=600000,MEASURE_PROCESS_MS=2700000
const RPCS=['erp_cp7_capture_operational_analysis_v1','erp_cp7_capture_analysis_v1','erp_cp7_read_analysis_v1','erp_cp7_request_operational_analysis_job_v1','erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_get_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1']
const SMALL=new Set(['erp_cp7_request_operational_analysis_job_v1','erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_get_analysis_job_v1','erp_cp7_read_analysis_manifest_v1'])
const fixture=(op,p,timeout=FIXTURE_PROCESS_MS)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p19_scale_browser_fixture.py',op],{input:JSON.stringify(p),cwd:'../writer',encoding:'utf8',maxBuffer:64*1024*1024,timeout}).trim())
const dir='cp6-proof/t3/'
const save=(name,observed)=>{mkdirSync(dir,{recursive:true});writeFileSync(dir+'P19S_BROWSER_'+name+'.json',JSON.stringify({contract:declaration.contract,evidence_kind:'FULL_APPLICATION_NATIVE',stage_witness_only:true,Native_case_credit:0,kernel_evidence_reused:false,limits_raised:false,owner_latency_acceptance:false,production_go:false,observed},null,2)+'\n');return 'P19S_BROWSER_'+name+'.json'}
const shift=(day,n)=>{const d=new Date(day+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-n);return d.toISOString().slice(0,10)}
const capOf=code=>Object.entries(caps).find(([,c])=>c.codes.includes(code))?.[0]??null

async function navigate(page){await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).waitFor({state:'attached'});const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click();const link=page.getByRole('button',{name:'• Ringkasan Barang Jadi',exact:true});if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()}
async function openPanel(page,from,through){
 await navigate(page);const history=page.getByRole('region',{name:'Data permintaan ERP',exact:true})
 await history.getByRole('button',{name:'Data permintaan & stok',exact:true}).click()
 const lo=history.getByLabel('Permintaan dari tanggal',{exact:true}),hi=history.getByLabel('Permintaan sampai tanggal',{exact:true})
 await lo.fill(from);await hi.fill(through);assert.deepEqual([await lo.inputValue(),await hi.inputValue()],[from,through])
 await history.getByRole('button',{name:'Analisis, laporan & pengingat seluruh produk',exact:true}).click()
 return page.getByRole('region',{name:'Analisis ERP bersama',exact:true})
}

// Capturing listener on the trusted click, then a DOM observer: first status
// while busy, 'Sedang dihitung sejak jam', segment progress, and completion
// two frames after the panel is idle with a new run and its product count, or
// with a rendered refusal. Driver polling never sets a timestamp.
async function arm(button,id){
 await button.evaluate((element,id)=>{
  const root=element.closest('[aria-label="Analisis ERP bersama"]');if(!root||element.disabled)throw Error('P19S_ENABLED_OWNING_CONTROL_REQUIRED')
  const all=window.__p19Scale??=Object.create(null);if(all[id])throw Error('P19S_DUPLICATE_MEASUREMENT')
  const r=all[id]={id,status:'NOT_CLICKED',clock:'BROWSER_PERFORMANCE_MONOTONIC',marks:{},status_texts:[]}
  const texts=sel=>[...root.querySelectorAll(sel)].map(n=>(n.textContent||'').trim()).filter(Boolean)
  const busy=()=>{const close=[...root.querySelectorAll('header button')].find(b=>b.textContent==='Tutup analisis bersama');return!close||close.disabled}
  const run=()=>root.querySelector('.native-analysis-result .native-analysis-run span')?.textContent||null
  const mark=(k,text)=>{if(!(k in r.marks)){r.marks[k]=performance.now()-r.t0;r.marks[k+'_text']=text}}
  let observer,queued=false
  const final=()=>{
   if(busy())return null
   const alerts=texts('[role="alert"]'),current=run()
   if(alerts.length)return{status:'REFUSAL_RENDERED',alerts,run_id:current!==r.previous_run?current:null}
   const summary=texts('p').find(t=>/^\d+ dari \d+ produk\./.test(t))
   return current&&current!==r.previous_run&&summary?{status:'RESULT_RENDERED',run_id:current,summary}:null
  }
  const inspect=()=>{
   if(r.status!=='RUNNING')return
   const statuses=texts('[role="status"]');for(const t of statuses)if(!r.status_texts.includes(t))r.status_texts.push(t)
   if(busy()&&statuses.length)mark('acknowledged_ms',statuses[0])
   const since=statuses.find(t=>t.startsWith('Sedang dihitung sejak jam'));if(since)mark('computing_since_ms',since)
   const progress=statuses.find(t=>t.startsWith('Mengambil hasil lengkap'));if(progress)mark('segment_progress_ms',progress)
   if(queued||!final())return
   queued=true
   requestAnimationFrame(()=>requestAnimationFrame(()=>{queued=false;const f=final();if(!f||r.status!=='RUNNING')return
    r.elapsed_ms=performance.now()-r.t0;Object.assign(r,f);observer.disconnect()}))
  }
  element.addEventListener('click',event=>{r.status='RUNNING';r.trusted_click=event.isTrusted;r.t0=performance.now();r.time_origin_epoch_ms=performance.timeOrigin
   r.previous_run=run();observer=new MutationObserver(inspect);observer.observe(root,{subtree:true,childList:true,attributes:true,characterData:true});inspect()},{capture:true,once:true})
 },id)
}

async function record(request,rpc){
 const response=await request.response(),body=response?await response.body():Buffer.alloc(0),status=response?.status()??null
 let small=null;if(SMALL.has(rpc)||status>=400){try{small=JSON.parse(body.toString('utf8'))}catch{small=null}}
 if(rpc==='erp_cp7_read_analysis_manifest_v1'&&small)small={document:small.document,source_state:small.source_state,run_id:small.run_id}
 // The panel switches to segments when JSON.stringify(analysis) exceeds the
 // single-body bound; Node's JSON.stringify gives the same compact bytes.
 let analysisBytes=null;if(status===200&&(rpc==='erp_cp7_capture_operational_analysis_v1'||rpc==='erp_cp7_capture_analysis_v1'||rpc==='erp_cp7_read_analysis_v1')){try{analysisBytes=Buffer.byteLength(JSON.stringify(JSON.parse(body.toString('utf8')).analysis??null))}catch{analysisBytes=null}}
 return{rpc,status,request:request.postDataJSON(),complete_body_utf8_bytes:body.length,body_sha256:createHash('sha256').update(body).digest('hex'),analysis_json_utf8_bytes:analysisBytes,timing:request.timing(),body:small}
}

// The first server refusal in request order: an HTTP error body or a FAILED job.
function serverRefusal(network){
 for(const n of network){
  if(n.failed)return{rpc:n.rpc,code:'NETWORK_FAILED',detail:n.failed}
  if(n.status>=400){const m=typeof n.body?.message==='string'?n.body.message:'';return{rpc:n.rpc,http_status:n.status,code:/^CP7_[A-Z0-9_]+/.exec(m)?.[0]??n.body?.code??null,sqlstate:n.body?.code??null,message:m.slice(0,2000)}}
  if(n.rpc==='erp_cp7_run_analysis_job_v1'&&n.body?.state==='FAILED')return{rpc:n.rpc,http_status:n.status,code:n.body.failure.code,sqlstate:n.body.failure.sqlstate}
 }
 return null
}

function verdict(m,expected){
 const structural=expected.filter(c=>c!=='STATEMENT_TIMEOUT_8S'),refused=m.server_refusal
 if(m.ui.status==='RESULT_RENDERED'){
  if(refused)return{kind:'RESULT_RENDERED_DESPITE_SERVER_REFUSAL',acceptable:false,counterexample:true}
  if(structural.length)return{kind:'BEYOND_CAP_NOT_REFUSED',caps:structural,acceptable:false,counterexample:true}
  const failed=Object.entries(m.checks).filter(([,v])=>v!==true).map(([k])=>k)
  return failed.length?{kind:'RESULT_DEFECT',failed,acceptable:false,counterexample:true}:{kind:'COMPLETE_RESULT',acceptable:true,counterexample:false}
 }
 if(!refused){
  const tooLarge=m.db.original?.client_document_bound_exceeded===true
  return tooLarge?{kind:'HONEST_CAP_REFUSAL',cap:'CLIENT_DOCUMENT_64000000_BYTES',acceptable:true,counterexample:false}
   :{kind:'CLIENT_REFUSED_SERVER_RESULT',alerts:m.ui.alerts,acceptable:false,counterexample:true}
 }
 const cap=capOf(refused.code),base={phase:refused.rpc,code:refused.code,cap,time_to_refusal_rendered_ms:m.ui.elapsed_ms}
 if(m.checks.no_result_saved_for_refused_compute===false)return{...base,kind:'REFUSAL_SAVED_A_RESULT',acceptable:false,counterexample:true}
 if(expected.includes(cap))return{...base,kind:'HONEST_CAP_REFUSAL',structural_caps_also_apply:structural.filter(c=>c!==cap),acceptable:true,counterexample:false}
 if(cap)return{...base,kind:'DECLARED_CAP_NOT_PREDICTED',acceptable:false,counterexample:false}
 return{...base,kind:'REFUSAL_OUTSIDE_DECLARED_CAPS',acceptable:false,counterexample:true}
}

async function measure(ui,today,size,days,[control,label,finance],seed){
 const name=`${size}_${days}_${control}`,from=shift(today,days),through=shift(today,1),expected=seed.expected_caps_by_days[String(days)]
 const user=await ui.login('OWNER',{label:`p19s-${size}-${days}-${control.toLowerCase()}`}),page=user.page,network=[],pending=[]
 page.on('requestfinished',request=>{const rpc=RPCS.find(n=>request.url().endsWith('/rpc/'+n));if(rpc)pending.push(record(request,rpc).then(r=>network.push(r)))})
 page.on('requestfailed',request=>{const rpc=RPCS.find(n=>request.url().endsWith('/rpc/'+n));if(rpc)network.push({rpc,failed:request.failure()?.errorText??'FAILED',request:request.postDataJSON(),timing:request.timing()})})
 let panel,sample=null
 try{
  panel=await openPanel(page,from,through)
  if(finance)await panel.getByRole('checkbox',{name:FINANCE,exact:true}).check()
  const button=panel.getByRole('button',{name:label,exact:true})
  await arm(button,name);await button.click()
  await page.waitForFunction(id=>{const r=window.__p19Scale?.[id];return Boolean(r)&&!['NOT_CLICKED','RUNNING'].includes(r.status)},name,{timeout:OBSERVATION_WINDOW_MS,polling:250})
  sample=await page.evaluate(id=>window.__p19Scale[id],name)
  await Promise.all(pending);network.sort((a,b)=>a.timing.startTime-b.timing.startTime)
  assert.equal(sample.trusted_click,true,'P19S_TRUSTED_CLICK_REQUIRED')
  const requests=[...new Set(network.map(n=>n.request?.p_request).filter(Boolean))]
  const queries=network.map(n=>n.request?.p_query).filter(Boolean)
  const db=fixture('observe',{actor:user.user.id,requests,run_id:sample.run_id??null,label:name})
  const refused=serverRefusal(network),computeRefused=refused&&['erp_cp7_capture_operational_analysis_v1','erp_cp7_capture_analysis_v1','erp_cp7_request_operational_analysis_job_v1','erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1'].includes(refused.rpc)
  const recommendations=sample.summary?Number(/dari (\d+) produk/.exec(sample.summary)[1]):null
  const checks={
   query_is_declared_window:queries.length>0&&queries.every(q=>q.from_date===from&&q.through_date===through&&q.group_mode==='AS_SOLD'),
   ...(sample.status==='RESULT_RENDERED'?{
    rendered_run_is_stored:db.runs.some(r=>r.run_id===sample.run_id&&requests.includes(r.request_id)),
    rendered_count_equals_stored_recommendations:recommendations===db.original?.recommendations,
    stored_source_equals_current_targets:db.coverage?.complete===true&&db.original?.source_products===seed.total_targets,
    segments_read_when_single_body_exceeded:!network.some(n=>n.analysis_json_utf8_bytes>caps.BODY_8000000_BYTES.value)||network.some(n=>n.rpc==='erp_cp7_read_analysis_segment_v1')}:{}),
   ...(computeRefused?{no_result_saved_for_refused_compute:requests.every(r=>db.requests[r]?.runs===0)}:{})}
  const ack=sample.marks?.acknowledged_ms
  assert.ok(Number.isFinite(ack),'P19S_FIRST_VISIBLE_ACKNOWLEDGEMENT_NOT_OBSERVED')
  // The control's own path: the operational RPCs without the finance choice, the full ones with it.
  const capturedBy=network.filter(n=>/^erp_cp7_(capture|request)_/.test(n.rpc)).map(n=>n.rpc)
  checks.finance_path_matches_control=capturedBy.length>0&&capturedBy.every(n=>n.includes('_operational_')!==finance)
  const m={size,history_days:days,control,financial_figures:finance,button:label,query:{from_date:from,through_date:through,group_mode:'AS_SOLD'},
   ui:{status:sample.status,elapsed_ms:sample.elapsed_ms,marks:sample.marks,status_texts:sample.status_texts,alerts:sample.alerts??[],run_id:sample.run_id??null,summary:sample.summary??null},
   owner_budgets:{first_visible_acknowledgement:budgetResult('ROUTINE_READ',ack),complete_or_refusal_rendered:budgetResult('HEAVY_COMPLETE',sample.elapsed_ms),
    progress_status_visible_by_3000ms:Number.isFinite(sample.marks?.computing_since_ms)&&sample.marks.computing_since_ms<=3000,
    owner_named_background_exception:false,owner_latency_acceptance:false},
   network,server_refusal:refused,db,checks,
   device:declaration.browser.device,context:declaration.browser.context,expected_caps:expected,evidence_kind:'FULL_APPLICATION_NATIVE'}
  m.verdict=verdict(m,expected)
  // Explicit server refusal: the RPC, HTTP status, code, SQLSTATE, the job's own
  // FAILED state and the stored job row, and which declared cap it is.
  const job=network.filter(n=>['erp_cp7_run_analysis_job_v1','erp_cp7_get_analysis_job_v1'].includes(n.rpc)&&n.body).map(n=>n.body).pop()??null
  m.refusal=refused?{...refused,job_state:job?.state??null,job_failure:job?.failure??null,
   stored_job:(db.jobs||[]).find(j=>requests.includes(j.request_id))??null,cap:m.verdict.cap??null}:null
  Object.assign(m,{refusal_code:refused?.code??null,refusal_sqlstate:refused?.sqlstate??null,refused_by_rpc:refused?.rpc??null,
   refusal_http_status:refused?.http_status??null,cap:m.verdict.cap??null})
  m.screenshot=`P19S_${name}.png`;await page.screenshot({path:dir+m.screenshot})
  m.witness=save(name,m)
  return m
 }catch(e){save(name+'_FAILURE',{error:String(e?.stack||e).slice(0,4000),sample,network:network.map(n=>({rpc:n.rpc,status:n.status,failed:n.failed,bytes:n.complete_body_utf8_bytes})),text:await panel?.innerText().catch(()=>'')});await page.screenshot({path:dir+`P19S_${name}_FAILURE.png`}).catch(()=>{});throw e}
 finally{await user.context.close()}
}

async function sizeCase(ui,today,size,state){
 // A size whose seeding stopped part-way leaves committed writer calls behind;
 // no later size is measured on that data.
 if(state.seed_failed)throw Error(`P19S_PRIOR_SIZE_SEED_INCOMPLETE_${state.seed_failed}`)
 let seed
 try{seed=fixture('prepare',{today,size,wip_done:state.wip_done},SEED_PROCESS_MS)}
 catch(e){state.seed_failed=size;save(`SEED_${size}_FAILURE`,{error:String(e?.stack||e).slice(0,4000)});throw e}
 state.wip_done=true;save(`SEED_${size}`,seed)
 const rows=[]
 for(const days of historyDays)for(const control of CONTROLS)rows.push(await measure(ui,today,size,days,control,seed))
 // Every click of this size is done; only now the SQL ladder and its phase profile.
 let sql=null,sqlError=null
 try{sql=fixture('measure',{today,size},MEASURE_PROCESS_MS);save(`SQL_LADDER_${size}`,sql)}
 catch(e){sqlError=String(e?.stack||e).slice(0,4000);save(`SQL_LADDER_${size}_FAILURE`,{error:sqlError})}
 const verdicts=rows.map(r=>r.verdict),cap=caps.HISTORY_SOURCE_PRODUCTS_1000.value,h=seed.history_source
 // The shared refusal code is attributed only when the source read proves which bound was met.
 const sourceConsistent=h.history_source_products_read===Math.min(size,cap+1)&&h.other_collections_within_50000===true&&(h.history_source_status==='COMPLETE')===(size<=cap)
 const counterexample=verdicts.some(v=>v.counterexample)||sql?.status==='COUNTEREXAMPLE'
 return{status:counterexample?'COUNTEREXAMPLE':sourceConsistent&&verdicts.every(v=>v.acceptable)&&sql?.status==='PASS'?'PASS':'INCOMPLETE',
  evidence_kind:'FULL_APPLICATION_NATIVE',size,source_model_consistent:sourceConsistent,
  sql_ladder:sql?{status:sql.status,where:sql.where,verdict_counts:sql.verdict_counts,source_model_consistent:sql.source_model_consistent,
   phase_profile_complete:sql.phase_profile_complete,Native_business_unchanged_by_measurement:sql.Native_business_unchanged_by_measurement,
   points:sql.points.map(p=>({path:p.path,history_days:p.history_days,grid_boundary_witness:p.grid_boundary_witness??false,verdict:p.verdict,
    request_to_result_ms:p.request_to_result_ms??null,request_to_terminal_ms:p.request_to_terminal_ms??null,
    manifest_and_segments_ms:p.manifest_and_segments_ms??null,original_utf8_bytes:p.original?.original_utf8_bytes??null})),
   dominant_layer_by_days:Object.fromEntries(Object.entries(sql.phase_profile||{}).map(([d,v])=>[d,{layer:v.summary?.dominant_layer??null,own_ms:v.summary?.dominant_own_ms??null,
    first_stopped_phase:v.summary?.first_stopped_phase??null,original_bytes_per_target:v.original_bytes_per_target??null,
    // Diagnostic only (PHASE_PROFILE_NOT_APP_LATENCY): every layer's own cost and every returned phase's server time,
    // so the log carries the whole profile and not only the dominant layer.
    own_ms_by_layer:Object.fromEntries((v.summary?.own_costs||[]).map(r=>[r.layer,r.own_ms])),
    server_ms_by_phase:Object.fromEntries((v.phases||[]).filter(p=>p.outcome==='RETURNED').map(p=>[p.name,p.server_ms])),
    capture_path_estimate_ms:v.summary?.capture_path_estimate_ms??null}])),
   step_attribution:Object.fromEntries(Object.entries(sql.step_attribution||{}).map(([d,v])=>[d,v.attribution])),witness:sql.witness}:null,
  sql_ladder_error:sqlError,
  seed:{total_targets:seed.total_targets,preexisting_targets:seed.preexisting_targets,seeded_targets:seed.seeded_targets,seed_ms_not_app_latency:seed.seed_ms,
   writer_phases:seed.writer_phases,calendar_review:seed.calendar_review,supply_scope:seed.supply_scope,history_source:seed.history_source},
  measurements:rows.map(r=>({history_days:r.history_days,control:r.control,ui_status:r.ui.status,click_to_first_status_ms:r.ui.marks.acknowledged_ms,
   click_to_computing_since_ms:r.ui.marks.computing_since_ms??null,click_to_segment_progress_ms:r.ui.marks.segment_progress_ms??null,click_to_complete_ms:r.ui.elapsed_ms,
   owner_budgets:r.owner_budgets,verdict:r.verdict,refusal:r.refusal,refusal_code:r.refusal_code,refusal_sqlstate:r.refusal_sqlstate,
   refused_by_rpc:r.refused_by_rpc,refusal_http_status:r.refusal_http_status,cap:r.cap,original_sha256:r.db.original?.original_sha256??null,original_utf8_bytes:r.db.original?.original_utf8_bytes??null,
   segments_read:r.network.filter(n=>n.rpc==='erp_cp7_read_analysis_segment_v1').length,
   response_utf8_bytes:r.network.reduce((s,n)=>s+(n.complete_body_utf8_bytes||0),0),witness:r.witness})),
  limits_raised:false,data_sampled_or_truncated:false,owner_latency_acceptance:false,full_P19_acceptance:false,production_go:false}
}

export function cases(ui,today){const state={wip_done:false};return sizes.map((size,i)=>[ids[i],()=>sizeCase(ui,today,size,state)])}
