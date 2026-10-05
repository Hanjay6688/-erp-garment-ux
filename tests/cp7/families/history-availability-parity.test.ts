// @vitest-environment node
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {expect,test} from 'vitest'

test('whole Native history availability preserves WIB opening and intraday minimum at every root',()=>{
 const output=execFileSync(process.execPath,['tests/cp7/families/f04/history-availability-parity.mjs'],{
  encoding:'utf8',timeout:90_000,maxBuffer:16*1024*1024,
  env:{...process.env,F04_RECEIPT_PATH:resolve('test-results/cp7-shell-proof/history-availability-parity.json')},
 })
 const receipt=JSON.parse(output.trim())
 expect(receipt.status).toBe('PASS');expect(receipt.passed).toBe(28)
 expect(receipt.operational_boundary_unchanged).toBe(true)
 expect(receipt.Native_business_case_credit).toBe(0)
 if(process.env.CI)expect(receipt.runtime).toBe('NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY')
},100_000)
