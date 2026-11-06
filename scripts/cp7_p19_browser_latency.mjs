// Writer timing witnesses for the existing real Auth P18 browser journeys.
// Browser click and rendered DOM use one monotonic clock. No product RPC,
// request, business assertion, timeout or Native case budget is changed.
import assert from 'node:assert/strict'

export const BUDGETS=Object.freeze({ROUTINE_READ:{ms:1000,inclusive:false},HEAVY_COMPLETE:{ms:3000,inclusive:true}})
export function budgetResult(kind,elapsed){
 const budget=BUDGETS[kind];assert.ok(budget,'UNDECLARED_BROWSER_LOADING_CLASS')
 assert.ok(Number.isFinite(elapsed)&&elapsed>=0,'INVALID_BROWSER_ELAPSED_TIME')
 return{class:kind,limit_ms:budget.ms,inclusive:budget.inclusive,elapsed_ms:elapsed,
  meets_limit:budget.inclusive?elapsed<=budget.ms:elapsed<budget.ms}
}

export async function beginClickMeasurement(button,options){
 assert.ok(['CAPTURE','STOCK_POPUP','OPERATOR_RESULT'].includes(options.mode))
 if (options.mode === 'OPERATOR_RESULT') {
  assert.ok(typeof options.scope === 'string' && options.scope.trim())
  assert.ok(typeof options.result === 'string' && options.result.trim())
  assert.ok(options.text === undefined || typeof options.text === 'string' && options.text.trim())
 } else {
  assert.ok(BUDGETS[options.kind])
 }
 await button.evaluate((element,options)=>{
  const operator = options.mode === 'OPERATOR_RESULT'
  const root = element.closest(operator ? options.scope : '[aria-label="Analisis ERP bersama"]')
  if(!root||element.disabled)throw Error('P19_LATENCY_ENABLED_OWNING_CONTROL_REQUIRED')
  const records=window.__cp7WriterLatency??=Object.create(null)
  if(records[options.id])throw Error('P19_LATENCY_DUPLICATE_ID')
  const record={id:options.id,mode:options.mode,status:'NOT_CLICKED'};records[options.id]=record
  let observer,queued=false
  let previousResult
  const findOperatorResult = () => [...root.querySelectorAll(options.result)].find(node => {
   const text = node.textContent.trim()
   return text && (!options.text || text.includes(options.text)) &&
    node.checkVisibility({visibilityProperty:true,opacityProperty:true}) &&
    !node.closest('[aria-hidden="true"]')
  })
  const ready=()=>{
   if (operator) {
    const current = findOperatorResult()
    return current && current !== previousResult ? {operator_result_visible:true} : null
   }
   const capture=[...root.querySelectorAll('.native-analysis-actions button')].find(b=>b.textContent==='Ambil analisis ERP terbaru')
   if(!capture||capture.disabled)return null
   if(options.mode==='CAPTURE'){
    const run=root.querySelector('.native-analysis-result .native-analysis-run span')
    return run&&run.textContent&&run.textContent!==record.previous_run?{run_id:run.textContent}:null
   }
   const popup=root.querySelector('dialog.native-analysis-popup[open]')
   if(!popup||popup.dataset.analysisTarget!==options.target||popup.dataset.runId!==options.run)return null
   const facts=['actual_fg','target_qty','q_base','q_conditional','feasible_new']
   if(facts.some(f=>!popup.querySelector('[data-fact="'+f+'"][data-native-fact]')))return null
   return{run_id:popup.dataset.runId,target:popup.dataset.analysisTarget,
    source_hash:popup.dataset.sourceHash,semantic_hash:popup.dataset.semanticHash}
  }
  const inspect=()=>{
   if(record.status!=='RUNNING'||queued||!ready())return
   queued=true
   requestAnimationFrame(()=>requestAnimationFrame(()=>{
    queued=false;const current=ready();if(!current||record.status!=='RUNNING')return
    record.elapsed_ms=performance.now()-record.click_monotonic_ms
    record.status='OBSERVED';record.rendered=current;observer.disconnect()
   }))
  }
  element.addEventListener('click',event=>{
   record.status='RUNNING';record.trusted_click=event.isTrusted
   record.click_monotonic_ms=performance.now();record.time_origin_epoch_ms=performance.timeOrigin;record.clock='BROWSER_PERFORMANCE_MONOTONIC'
   if (operator) previousResult = findOperatorResult()
   else record.previous_run=root.querySelector('.native-analysis-run span')?.textContent??null
   observer=new MutationObserver(inspect);record.disconnect=()=>observer.disconnect()
   observer.observe(root,{subtree:true,childList:true,attributes:true,characterData:true});inspect()
  },{capture:true,once:true})
 },options)
}

export async function readClickMeasurement(page,id,response,kind){
 // DOM correctness is already asserted by the owning Native case. Flush frames
 // only to retrieve its independent click→paint witness; driver assertion time
 // is excluded because the observer recorded its own completion timestamp.
 const sample=await page.evaluate(async id=>{
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))
  const r=window.__cp7WriterLatency?.[id];if(!r)return null
  return Object.fromEntries(Object.entries(r).filter(([key])=>key!=='disconnect'))
 },id)
 assert.equal(sample?.status,'OBSERVED','P19_LATENCY_COMPLETE_RENDER_WITNESS_REQUIRED')
 assert.equal(sample.trusted_click,true)
 assert.equal(await response.finished(),null)
 const body=await response.body(),request=response.request()
 const timing=request.timing();assert.ok(timing.responseEnd>=0)
 const operator = sample.mode === 'OPERATOR_RESULT'
 if (operator) {
  assert.equal(response.ok(),true,'CP7_OPERATOR_LATENCY_SUCCESSFUL_RESPONSE_REQUIRED')
  assert.ok(sample.rendered.operator_result_visible)
 }
 const budget = operator ? {} : {budget:budgetResult(kind,sample.elapsed_ms)}
 return{...sample,...budget,
  http:{rpc:new URL(response.url()).pathname.split('/rpc/')[1],status:response.status(),
   complete_body_utf8_bytes:body.length,timing},
  classification:'BOUNDED_CI_LOOPBACK_REAL_AUTH_CLICK_TO_RENDER',
  fixture_specific:true,factory_SLA_acceptance:false,Native_case_credit_added:0}
}

export async function currentClickMeasurements(page){
 return page.evaluate(()=>Object.values(window.__cp7WriterLatency??{}).map(r=>
  Object.fromEntries(Object.entries(r).filter(([key])=>key!=='disconnect'))))
}

export async function clearClickMeasurements(page){
 await page.evaluate(()=>{for(const r of Object.values(window.__cp7WriterLatency??{}))r.disconnect?.();delete window.__cp7WriterLatency})
}
