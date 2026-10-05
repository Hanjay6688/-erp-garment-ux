// @vitest-environment node
import {execFileSync} from 'node:child_process'
import {resolve} from 'node:path'
import {expect,test} from 'vitest'

test('one physical roll/location is one plan budget without a second deduction after posting',()=>{
 const output=execFileSync(process.execPath,['tests/cp7/families/f04/material-pool.mjs'],{
  encoding:'utf8',timeout:90_000,maxBuffer:16*1024*1024,
  env:{...process.env,F04_RECEIPT_PATH:resolve('test-results/cp7-shell-proof/material-pool.json')},
 })
 const receipt=JSON.parse(output.trim());expect(receipt.status).toBe('PASS');expect(receipt.passed).toBe(12)
 expect(receipt.Native_business_case_credit).toBe(0);expect(receipt.stock_reservation_created).toBe(false)
 if(process.env.CI)expect(receipt.runtime).toBe('NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY')
},100_000)
