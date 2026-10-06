// Re-execute the unchanged five CP6 UI oracles on the installed full CP7 F03 stack.
// Keep every source/cost/quantity/refusal assertion; no CP6 result is relabelled.
import assert from 'node:assert/strict'
import {cases as readiness} from './cp6_readiness_browser.mjs'
import {cases as laundry} from './cp6_bd_revision_browser.mjs'

export const required = [
  'READINESS_BROWSER:DESKTOP_NATIVE_POLICY_STATES_FINANCE_NOTE',
  'READINESS_BROWSER:MOBILE_NATIVE_POLICY_STATES_FINANCE_NOTE',
  'BD_BROWSER:LAU_T36_PHONE_MIXED_COVERAGE',
  'BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP',
  'BD_REV_BROWSER:WAIVED_MASTER_THEN_PHYSICAL_MOBILE',
]
export async function cases(ui, today) {
  const all = [...await readiness(ui, today), ...await laundry(ui, today)]
  const selected = required.map(id => {
    const rows = all.filter(([key]) => key === id)
    assert.equal(rows.length, 1, 'PRE_FREEZE_EXACT_REQUIRED_CASE: ' + id)
    return rows[0]
  })
  assert.deepEqual(selected.map(([id]) => id), required)
  return selected
}
