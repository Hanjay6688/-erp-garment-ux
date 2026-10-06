// Re-execute every applicable CP6 UI oracle on the installed full CP7 F03 stack.
// Keep every source/cost/quantity/refusal assertion; no CP6 result is relabelled.
import assert from 'node:assert/strict'
import {cases as legacy} from './cp6_bf_vendor_browser.mjs'
import {cases as connectedDrafts} from './cp7_p11_drafts_browser.mjs'

export const required = [
  'READINESS_BROWSER:DESKTOP_NATIVE_POLICY_STATES_FINANCE_NOTE',
  'READINESS_BROWSER:MOBILE_NATIVE_POLICY_STATES_FINANCE_NOTE',
  'BD_BROWSER:LAU_T36_PHONE_MIXED_COVERAGE',
  'BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP',
  'BD_REV_BROWSER:WAIVED_MASTER_THEN_PHYSICAL_MOBILE',
]
export async function cases(ui, today) {
  const all = await legacy(ui, today)
  const retired=['BF_BROWSER:SALES_MANUAL_13_DESKTOP','BF_BROWSER:SALES_MANUAL_13_MOBILE']
  assert.equal(all.length,31,'EXACT_LEGACY_BROWSER_INVENTORY')
  for(const id of [...required,...retired]){
    const rows = all.filter(([key]) => key === id)
    assert.equal(rows.length, 1, 'PRE_FREEZE_EXACT_REQUIRED_CASE: ' + id)
  }
  const replacements=await connectedDrafts(ui,today)
  assert.deepEqual(replacements.map(([id])=>id),['P11_DRAFT_BROWSER_DESKTOP','P11_DRAFT_BROWSER_MOBILE_RECOVERY'])
  const selected=[...all.filter(([id])=>!retired.includes(id)),...replacements]
  assert.equal(selected.length,31,'EXACT_CP7_MIGRATION_BROWSER_INVENTORY')
  assert.equal(new Set(selected.map(([id])=>id)).size,31)
  return selected
}
