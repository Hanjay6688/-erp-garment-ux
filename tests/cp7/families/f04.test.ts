// @vitest-environment node
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from 'vitest'

test('F04 private SQL kernels pass independent numeric fixtures in a disposable runtime', () => {
  // The existing CP7 workflow already uploads this proof directory. No CI edits.
  const proofDirectory = resolve('test-results/cp7-shell-proof')
  mkdirSync(proofDirectory, { recursive: true })
  const output = execFileSync(process.execPath, ['tests/cp7/families/f04/run.mjs'], {
    encoding: 'utf8', timeout: 180_000, maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, F04_RECEIPT_PATH: resolve(proofDirectory, 'f04-private-kernels.json') },
  })
  const receipt = JSON.parse(output.trim())
  expect(receipt.failures).toEqual([])
  expect(receipt.passed).toBeGreaterThan(50)
  expect(receipt.cleanup).toBe('CLOSED_DISPOSABLE_RUNTIME')
  if (process.env.CI) expect(receipt.runtime).toBe('NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY')
  console.log(`F04 ${receipt.passed} cases: ${receipt.runtime}; ${receipt.version}`)
}, 190_000)
