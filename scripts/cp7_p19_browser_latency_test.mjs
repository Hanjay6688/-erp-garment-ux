import assert from 'node:assert/strict'
import {beginClickMeasurement,budgetResult,clearClickMeasurements,currentClickMeasurements} from './cp7_p19_browser_latency.mjs'
assert.equal(budgetResult('ROUTINE_READ',999.999).meets_limit,true)
assert.equal(budgetResult('ROUTINE_READ',1000).meets_limit,false)
assert.equal(budgetResult('HEAVY_COMPLETE',3000).meets_limit,true)
assert.equal(budgetResult('HEAVY_COMPLETE',3000.001).meets_limit,false)
for(const bad of [NaN,Infinity,-1,null,undefined])assert.throws(()=>budgetResult('ROUTINE_READ',bad))
assert.throws(()=>budgetResult('GENERAL_5_SECONDS',1000))
console.log(JSON.stringify({status:'PASS',classification:'LOADING_BOUNDARY_TOOL_CONTROLS_ONLY',Native_case_credit_added:0}))

if (process.argv.includes('--browser')) {
 const {chromium} = await import('playwright')
 const browser = await chromium.launch()
 try {
  const page = await browser.newPage()
  await page.setContent('<main><button>Filter</button><div class="result">Target</div></main>')
  const button = page.getByRole('button',{name:'Filter',exact:true})
  await beginClickMeasurement(button,{id:'operator-filter',mode:'OPERATOR_RESULT',
    scope:'main',result:'.result',text:'Target'})
  await button.click()
  await page.evaluate(() => {
   const main = document.querySelector('main')
   const hidden = document.createElement('div')
   hidden.className = 'result'
   hidden.textContent = 'Target'
   hidden.hidden = true
   main.prepend(hidden)
   const wrong = document.createElement('div')
   wrong.className = 'result'
   wrong.textContent = 'Wrong record'
   main.prepend(wrong)
  })
  assert.equal((await currentClickMeasurements(page))[0].status,'RUNNING')
  await page.evaluate(() => {
   const original = [...document.querySelectorAll('.result')].find(el=>!el.hidden&&el.textContent==='Target')
   original.replaceWith(original.cloneNode(true))
  })
  await page.waitForFunction(()=>window.__cp7WriterLatency['operator-filter'].status==='OBSERVED')
  const [sample] = await currentClickMeasurements(page)
  assert.equal(sample.trusted_click,true)
  assert.equal(sample.rendered.operator_result_visible,true)
  assert.ok(Number.isFinite(sample.elapsed_ms) && sample.elapsed_ms>=0)
  await clearClickMeasurements(page)
  assert.deepEqual(await currentClickMeasurements(page),[])
  console.log(JSON.stringify({status:'PASS',classification:'CHROMIUM_OPERATOR_LATENCY_TOOL_CONTROL',
   stale_result_ignored:true,hidden_or_wrong_result_ignored:true,actual_ERP_cases:0}))
 } finally {
  await browser.close()
 }
}
