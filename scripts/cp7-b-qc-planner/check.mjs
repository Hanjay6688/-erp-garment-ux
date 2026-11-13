import assert from 'node:assert/strict'
import { cases } from './cases.mjs'

for (const target of ['postgresql://example.invalid/cp6_auditor_browser', 'postgresql://127.0.0.1/erp']) {
  process.env.AUDITOR_BROWSER_DB_URL = target
  assert.throws(() => cases({}, '2026-11-13'), /DISPOSABLE_BROWSER_COPY_ONLY/)
}
process.env.AUDITOR_BROWSER_DB_URL = 'postgresql://127.0.0.1/cp6_auditor_browser'
process.env.AUDITOR_UI_MODE = 'ENTENG'
assert.throws(() => cases({}, '2026-11-13'), /DISPOSABLE/)
process.env.AUDITOR_UI_MODE = 'DISPOSABLE'
assert.deepEqual(cases({}, '2026-11-13').map(c => c[0]), ['B_QC_SNAPSHOT_REPORT_OWNER', 'B_PLANNER_SECOND_SKU_ADMIN'])
console.log('Disposable host guards and case registration PASS')
