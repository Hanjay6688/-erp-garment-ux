import assert from 'node:assert/strict'
import { cases as policy } from './policy.mjs'
import { cases as evaluation } from './evaluation.mjs'
const ids=[...(await policy({},'2026-10-24')),...(await evaluation({},'2026-10-24'))].map(([id,fn])=>{assert.equal(typeof fn,'function');return id})
assert.deepEqual(ids,['OW11_MODEL_POLICY_BROWSER_MOBILE_EXACT_RECOVERY_SUSPEND','OW11_MODEL_POLICY_BROWSER_DESKTOP_REVIEW_ACCESS_REVOKED','OW11_MODEL_V2_BROWSER_MOBILE_EXACT_RECOVERY_POLICY_SOURCE','OW11_MODEL_V2_BROWSER_DESKTOP_BASELINE_CURRENT_ACCESS'])
console.log(JSON.stringify({status:'PASS',actual_ESM_modules_loaded:2,case_ids:ids,browser_executed:false}))
