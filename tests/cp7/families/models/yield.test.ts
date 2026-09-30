// @vitest-environment node
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from 'vitest'

test('F04 cutting-yield kernel computes from history in a disposable database', () => {
  const proof=resolve('test-results/cp7-shell-proof'); mkdirSync(proof,{recursive:true})
  const output=execFileSync(process.execPath,['tests/cp7/families/models/yield/run.mjs'],{
    encoding:'utf8',timeout:180000,maxBuffer:16*1024*1024,
    env:{...process.env,F04_YIELD_RECEIPT_PATH:resolve(proof,'f04-yield-kernel.json')},
  })
  const receipt=JSON.parse(output.trim())
  expect(receipt.failures).toEqual([]); expect(receipt.passed).toBeGreaterThanOrEqual(40)
  expect(receipt.cleanup).toBe('CLOSED_DISPOSABLE_RUNTIME')
  if(process.env.CI)expect(receipt.runtime).toBe('NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY')
},190000)
