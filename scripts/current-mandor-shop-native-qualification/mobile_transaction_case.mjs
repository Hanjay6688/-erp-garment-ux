// Select the original mobile callback. The original App, Auth and case assertions run unchanged.
import assert from 'node:assert/strict'
import { cases as originalCases, IDS } from '../../../auditor/scripts/current-mandor-shop-native-qualification/browser.mjs'

export async function cases(ui, today) {
  const planned = await originalCases(ui, today)
  assert.deepEqual(planned.map(([id]) => id), IDS)
  assert.equal(planned[1][0], 'MANDOR_BROWSER_MOBILE390_NORMAL_PAYROLL_STALE_INPUT_FRESH_READ_RELEASE')
  return [planned[1]]
}
