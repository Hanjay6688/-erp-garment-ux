import assert from 'node:assert/strict'
import {budgetResult} from './cp7_p19_browser_latency.mjs'
assert.equal(budgetResult('ROUTINE_READ',999.999).meets_limit,true)
assert.equal(budgetResult('ROUTINE_READ',1000).meets_limit,false)
assert.equal(budgetResult('HEAVY_COMPLETE',3000).meets_limit,true)
assert.equal(budgetResult('HEAVY_COMPLETE',3000.001).meets_limit,false)
for(const bad of [NaN,Infinity,-1,null,undefined])assert.throws(()=>budgetResult('ROUTINE_READ',bad))
assert.throws(()=>budgetResult('GENERAL_5_SECONDS',1000))
console.log(JSON.stringify({status:'PASS',classification:'LOADING_BOUNDARY_TOOL_CONTROLS_ONLY',Native_case_credit_added:0}))
