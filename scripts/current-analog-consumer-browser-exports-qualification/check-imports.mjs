import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const pins=JSON.parse(readFileSync(new URL('./SOURCE.json',import.meta.url),'utf8'))
const observed=[]
for(const name of ['return','consumer','choice']){
 const module=await import(`./${name}.mjs`)
 assert.equal(typeof module.cases,'function')
 observed.push(...(await module.cases(null,'2026-10-24')).map(([id,run])=>{assert.equal(typeof run,'function');return id}))
}
assert.deepEqual(observed,pins.case_ids)
console.log(JSON.stringify({status:'PASS',actual_ESM_modules_loaded:3,exact_case_ids:observed,browser_executed:false}))
