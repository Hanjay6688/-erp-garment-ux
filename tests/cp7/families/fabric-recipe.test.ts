// @vitest-environment node
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {expect,test} from 'vitest'
test('effective fabric review preserves source identity, recording clock, CAS, UNKNOWN and metadata boundaries',()=>{
 const output=execFileSync(process.execPath,['tests/cp7/families/f04/fabric-recipe.mjs'],{encoding:'utf8',timeout:90_000,maxBuffer:16*1024*1024,env:{...process.env,F04_FABRIC_RECEIPT_PATH:resolve('test-results/cp7-shell-proof/fabric-recipe.json')}})
 const receipt=JSON.parse(output.trim());expect(receipt.status).toBe('PASS');expect(receipt.passed).toBe(28)
 expect(receipt.Native_business_case_credit).toBe(0);expect(receipt.Auth_HTTP_credit).toBe(0);expect(receipt.race_credit).toBe(0)
 if(process.env.CI)expect(receipt.runtime).toBe('NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY')
},100_000)
